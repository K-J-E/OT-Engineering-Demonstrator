"""I7 DEF-001 investigation/correction chain and immutability gates."""

import sqlite3
from pathlib import Path

import pytest

from ot_demo.application.investigation_service import InvestigationBoundaryError, InvestigationService
from ot_demo.application.scenario_coordinator import ScenarioCoordinator
from ot_demo.domain.enums import OperationalEventType, RepeatRelationshipType, ValidationExecutionStatus, ValidationVerdict
from ot_demo.infrastructure.build_identity import ApplicationBuildManifest, BuildIdentityPayload
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ot_demo.infrastructure.investigation_repository import InvestigationRepository
from ot_demo.infrastructure.scenario_repository import ScenarioRepository
from ot_demo.infrastructure.validation_repository import ValidationRepository
from ot_demo.modules.validation.catalogue import ValidationCatalogueLoader
from ot_demo.modules.validation.service import ValidationService


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "app/backend/ot_demo/infrastructure/migrations"
CONFIGURATIONS = ROOT / "config/network"
CATALOGUE = ROOT / "validation/test-definitions/catalogue.json"
IDENTITY = BuildIdentityPayload(
    git_commit="7" * 40,
    git_dirty=False,
    python_version="3.13.15",
    node_version="24.19.0",
    npm_version="11.17.0",
    dependency_lock_sha256={
        "requirements.lock": "2" * 64,
        "app/frontend/package-lock.json": "3" * 64,
    },
    backend_source_sha256="4" * 64,
    frontend_bundle_sha256="5" * 64,
)
MANIFEST = ApplicationBuildManifest(
    application_build_id=sha256_bytes(canonical_json_bytes(IDENTITY.model_dump(mode="json"))),
    identity=IDENTITY,
)


def service(tmp_path: Path) -> InvestigationService:
    loader = JsonConfigurationLoader(CONFIGURATIONS)
    scenarios = ScenarioCoordinator(
        ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS),
        loader,
        application_build_manifest=MANIFEST,
    )
    validation_repository = ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS)
    validation = ValidationService(
        validation_repository,
        ValidationCatalogueLoader(CATALOGUE),
        scenarios,
        application_build_manifest=MANIFEST,
    )
    return InvestigationService(
        InvestigationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        loader,
        scenarios,
        validation,
        application_build_manifest=MANIFEST,
    )


@pytest.mark.i7
def test_complete_consequence_to_source_correction_repeat_and_regression(tmp_path: Path) -> None:
    investigation = service(tmp_path)
    chain = investigation.start_failure("Graduate Engineer")
    failure = chain.original_failure.execution
    failure_evidence = chain.original_failure.evidence_snapshots[0]

    assert failure.verdict is ValidationVerdict.FAIL
    assert failure.configuration_version == "1.0"
    assert failure.observed_result["affected_customer_count"] == 400
    assert failure.observed_result["de_energised_section_ids"] == ["SEC-A1", "SEC-A2"]
    assert failure.observed_result["section_source_feeder_ids"]["SEC-A3"] == ["FDR-B"]
    assert failure.observed_result["section_source_feeder_ids"]["SEC-A4"] == ["FDR-B"]
    assert tuple(step.step_id for step in chain.steps) == InvestigationService.REVIEW_STEP_IDS
    assert [fact.value for fact in chain.steps[1].facts[:3]] == ["OPEN", "GOOD", "FRESH"]
    assert "SEC-A3 → SW-A23 → SEC-B3" in chain.steps[4].facts[0].value
    difference = chain.configuration_comparison.differences[0]
    assert difference.path == "connectivity_edges.EDGE-SW-A23-1.endpoint_a_id"
    assert (difference.before, difference.after) == ("SEC-B3", "SEC-A2")

    with pytest.raises(InvestigationBoundaryError, match="seven"):
        investigation.record_defect(failure.validation_execution_id, "Reviewer", ("INV-01",))

    chain = investigation.record_defect(
        failure.validation_execution_id,
        "Independent Reviewer",
        InvestigationService.REVIEW_STEP_IDS,
    )
    assert chain.defect_record is not None
    assert chain.defect_record.defect_id == "DEF-001"
    chain = investigation.record_correction(failure.validation_execution_id, "Independent Reviewer")
    assert chain.correction_record is not None
    assert chain.correction_record.correction_id == "COR-001"
    assert chain.correction_record.defective_configuration.data_sha256 == "67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3"
    assert chain.correction_record.corrected_configuration.data_sha256 == "7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281"

    chain = investigation.run_direct_repeat(failure.validation_execution_id, "Graduate Engineer")
    assert chain.direct_repeat is not None
    repeat = chain.direct_repeat.execution
    assert repeat.verdict is ValidationVerdict.PASS
    assert repeat.configuration_version == "1.1"
    assert repeat.observed_result["affected_customer_count"] == 850
    assert repeat.application_build_id == failure.application_build_id
    assert repeat.test_definition_sha256 == failure.test_definition_sha256
    assert repeat.validation_execution_id != failure.validation_execution_id
    assert chain.same_build_proven
    assert chain.original_failure.execution == failure
    assert chain.original_failure.evidence_snapshots[0] == failure_evidence

    chain = investigation.run_regression(failure.validation_execution_id, "Graduate Engineer")
    assert chain.regression is not None
    regression = chain.regression
    assert regression.execution.status is ValidationExecutionStatus.ACTIVE
    assert regression.execution.verdict is None
    assert [item.checkpoint_id for item in regression.evidence_snapshots] == ["N0", "N1", "N2", "N3", "N4", "N5"]
    by_checkpoint = {item.checkpoint_id: item for item in regression.evidence_snapshots}
    assert by_checkpoint["N1"].observed_values["affected_customer_count"] == 850
    assert by_checkpoint["N3"].observed_values["affected_customer_count"] == 670
    assert by_checkpoint["N4"].observed_values["restoration_outcome"] == "PERMITTED"
    assert by_checkpoint["N5"].observed_values["affected_customer_count"] == 220
    assert by_checkpoint["N5"].observed_values["restored_customer_delta"] == 450
    assert by_checkpoint["N5"].observed_values["radiality_status"] == "RADIAL"
    assert chain.same_build_proven
    assert [link.relationship_type for link in chain.repeat_links] == [RepeatRelationshipType.DIRECT_REPEAT, RepeatRelationshipType.REGRESSION]
    assert len({item.value for item in OperationalEventType}) == 15
    assert not {"PASS", "FAIL", "DEFECT_RECORDED", "CORRECTION_RECORDED"} & {item.value for item in OperationalEventType}


@pytest.mark.i7
def test_defect_correction_and_repeat_rows_reject_update_and_delete(tmp_path: Path) -> None:
    investigation = service(tmp_path)
    chain = investigation.start_failure("Graduate Engineer")
    failure_id = chain.original_failure.execution.validation_execution_id
    investigation.record_defect(failure_id, "Reviewer", InvestigationService.REVIEW_STEP_IDS)
    investigation.record_correction(failure_id, "Reviewer")
    investigation.run_direct_repeat(failure_id, "Graduate Engineer")

    with sqlite3.connect(tmp_path / "validation.sqlite3") as connection:
        for table in ("investigation_defect_records", "investigation_correction_records", "investigation_repeat_links"):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(f"UPDATE {table} SET payload_json = '{{}}'")
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(f"DELETE FROM {table}")
