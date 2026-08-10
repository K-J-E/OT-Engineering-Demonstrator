"""I5 immutable validation execution, evidence and direct DEF-001 comparison gates."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from ot_demo.application.scenario_coordinator import ScenarioCoordinator
from ot_demo.domain.enums import (
    EvidenceClass,
    ScenarioCommandType,
    ScenarioMode,
    ValidationExecutionStatus,
    ValidationVerdict,
)
from ot_demo.infrastructure.build_identity import (
    ApplicationBuildManifest,
    BuildIdentityPayload,
)
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ot_demo.infrastructure.scenario_repository import ScenarioRepository
from ot_demo.infrastructure.validation_repository import ValidationRepository
from ot_demo.modules.scenario.models import InitialiseRunRequest, ScenarioCommandRequest
from ot_demo.modules.validation.catalogue import ValidationCatalogueLoader
from ot_demo.modules.validation.models import (
    StartValidationExecutionRequest,
    ValidationExecutionLinks,
)
from ot_demo.modules.validation.service import ValidationBoundaryError, ValidationService


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "app/backend/ot_demo/infrastructure/migrations"
CATALOGUE = ROOT / "validation/test-definitions/catalogue.json"
T0 = datetime(2030, 1, 1, tzinfo=timezone.utc)
IDENTITY = BuildIdentityPayload(
    git_commit="1" * 40,
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
    application_build_id=sha256_bytes(
        canonical_json_bytes(IDENTITY.model_dump(mode="json"))
    ),
    identity=IDENTITY,
)


def at(seconds: int) -> datetime:
    return T0 + timedelta(seconds=seconds)


def scenario(tmp_path: Path, name: str) -> ScenarioCoordinator:
    return ScenarioCoordinator(
        ScenarioRepository(tmp_path / f"{name}.sqlite3", MIGRATIONS),
        JsonConfigurationLoader(ROOT / "config/network"),
        application_build_manifest=MANIFEST,
    )


def validation(
    tmp_path: Path,
    scenarios: ScenarioCoordinator,
) -> ValidationService:
    return ValidationService(
        ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        ValidationCatalogueLoader(CATALOGUE),
        scenarios,
        application_build_manifest=MANIFEST,
    )


def initialise_and_fault(
    coordinator: ScenarioCoordinator,
    configuration_version: str,
    command_base: int,
):
    initial = coordinator.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=command_base),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version=configuration_version,
            scenario_time=T0,
        )
    )
    run_id = initial.snapshot.run.scenario_run_id
    fault = coordinator.execute(
        run_id,
        ScenarioCommandRequest(
            command_id=UUID(int=command_base + 1),
            scenario_run_id=run_id,
            actor="Graduate Engineer",
            expected_revision=0,
            command_type=ScenarioCommandType.INITIATE_FAULT,
            scenario_time=at(10),
        ),
    )
    return initial, fault


def execute_defect_test(
    tmp_path: Path,
    name: str,
    version: str,
    command_base: int,
    *,
    links: ValidationExecutionLinks,
):
    coordinator = scenario(tmp_path, name)
    initial = coordinator.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=command_base),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version=version,
            scenario_time=T0,
        )
    )
    service = validation(tmp_path, coordinator)
    execution = service.start_execution(
        "VT-TOP-DEF-001",
        initial.snapshot.run.scenario_run_id,
        links=links,
    )
    coordinator.execute(
        initial.snapshot.run.scenario_run_id,
        ScenarioCommandRequest(
            command_id=UUID(int=command_base + 1),
            scenario_run_id=initial.snapshot.run.scenario_run_id,
            actor="Graduate Engineer",
            expected_revision=0,
            command_type=ScenarioCommandType.INITIATE_FAULT,
            scenario_time=at(10),
        ),
    )
    evidence = service.capture_checkpoint(
        execution.validation_execution_id,
        "POST_TRIP",
    )
    finalised = service.finalise_execution(
        execution.validation_execution_id,
        "POST_TRIP",
    )
    return coordinator, service, evidence, finalised


@pytest.mark.i5
def test_same_build_v1_0_fail_and_linked_v1_1_pass_are_separate_and_immutable(
    tmp_path: Path,
) -> None:
    old_coordinator, old_service, old_evidence, failure = execute_defect_test(
        tmp_path,
        "defective",
        "1.0",
        1,
        links=ValidationExecutionLinks(defect_id="DEF-001"),
    )
    assert failure.status is ValidationExecutionStatus.FINALISED
    assert failure.verdict is ValidationVerdict.FAIL
    assert failure.observed_result["affected_customer_count"] == 400
    assert failure.observed_result["de_energised_section_ids"] == [
        "SEC-A1",
        "SEC-A2",
    ]
    assert failure.observed_result["section_source_feeder_ids"]["SEC-A3"] == [
        "FDR-B"
    ]
    assert failure.observed_result["section_source_feeder_ids"]["SEC-A4"] == [
        "FDR-B"
    ]

    corrected_coordinator, corrected_service, corrected_evidence, passed = (
        execute_defect_test(
            tmp_path,
            "corrected",
            "1.1",
            101,
            links=ValidationExecutionLinks(
                repeat_of_execution_id=failure.validation_execution_id,
                defect_id="DEF-001",
                correction_id="COR-001",
            ),
        )
    )
    assert passed.verdict is ValidationVerdict.PASS
    assert passed.observed_result["affected_customer_count"] == 850
    assert passed.observed_result["de_energised_section_ids"] == [
        "SEC-A1",
        "SEC-A2",
        "SEC-A3",
        "SEC-A4",
    ]
    assert passed.application_build_id == failure.application_build_id
    assert passed.test_definition_sha256 == failure.test_definition_sha256
    assert passed.validation_execution_id != failure.validation_execution_id
    assert passed.links.repeat_of_execution_id == failure.validation_execution_id
    assert passed.links.defect_id == "DEF-001"
    assert passed.links.correction_id == "COR-001"
    assert corrected_evidence.canonical_payload_sha256 == sha256_bytes(
        canonical_json_bytes(corrected_evidence.canonical_payload)
    )

    old_summary = corrected_service.get_execution(failure.validation_execution_id)
    assert old_summary.execution == failure
    assert old_summary.evidence_snapshots == (old_evidence,)
    assert old_service.get_execution(failure.validation_execution_id) == old_summary
    assert corrected_coordinator.events(passed.scenario_run_id)
    assert all(
        "VALIDATION" not in event.event_type.value
        and event.event_type.value not in {"PASS", "FAIL"}
        for event in corrected_coordinator.events(passed.scenario_run_id)
    )
    assert old_coordinator.events(failure.scenario_run_id)


@pytest.mark.i5
def test_evidence_is_captured_from_actual_revision_and_survives_reset(
    tmp_path: Path,
) -> None:
    coordinator, service, evidence, execution = execute_defect_test(
        tmp_path,
        "reset",
        "1.1",
        201,
        links=ValidationExecutionLinks(),
    )
    before_payload = evidence.canonical_payload
    before_hash = evidence.canonical_payload_sha256
    reset = coordinator.execute(
        execution.scenario_run_id,
        ScenarioCommandRequest(
            command_id=UUID(int=203),
            scenario_run_id=execution.scenario_run_id,
            actor="Graduate Engineer",
            expected_revision=1,
            command_type=ScenarioCommandType.RESET_RUN,
            scenario_time=at(20),
        ),
    )

    preserved = service.get_execution(execution.validation_execution_id)
    assert reset.snapshot.run.scenario_run_id != execution.scenario_run_id
    assert preserved.execution == execution
    assert preserved.evidence_snapshots[0].canonical_payload == before_payload
    assert preserved.evidence_snapshots[0].canonical_payload_sha256 == before_hash
    assert preserved.evidence_snapshots[0].state_revision == 1
    assert preserved.evidence_snapshots[0].observed_values[
        "affected_customer_count"
    ] == 850


@pytest.mark.i5
def test_finalised_execution_verdict_and_evidence_rewrite_delete_are_rejected(
    tmp_path: Path,
) -> None:
    _coordinator, _service, evidence, execution = execute_defect_test(
        tmp_path,
        "immutable",
        "1.1",
        301,
        links=ValidationExecutionLinks(),
    )
    database = tmp_path / "validation.sqlite3"
    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="finalised"):
            connection.execute(
                "UPDATE validation_executions SET verdict = 'FAIL' "
                "WHERE validation_execution_id = ?",
                (str(execution.validation_execution_id),),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable history"):
            connection.execute(
                "DELETE FROM validation_executions WHERE validation_execution_id = ?",
                (str(execution.validation_execution_id),),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE validation_evidence_snapshots SET checkpoint_id = 'OTHER' "
                "WHERE evidence_snapshot_id = ?",
                (str(evidence.evidence_snapshot_id),),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM validation_evidence_snapshots "
                "WHERE evidence_snapshot_id = ?",
                (str(evidence.evidence_snapshot_id),),
            )


@pytest.mark.i5
def test_repeat_has_new_identity_equal_canonical_observation_and_explicit_link(
    tmp_path: Path,
) -> None:
    _first_scenario, _first_service, _first_evidence, first = execute_defect_test(
        tmp_path,
        "repeat-one",
        "1.1",
        401,
        links=ValidationExecutionLinks(),
    )
    _second_scenario, second_service, _second_evidence, second = execute_defect_test(
        tmp_path,
        "repeat-two",
        "1.1",
        501,
        links=ValidationExecutionLinks(
            repeat_of_execution_id=first.validation_execution_id
        ),
    )

    assert first.verdict is second.verdict is ValidationVerdict.PASS
    assert first.validation_execution_id != second.validation_execution_id
    assert first.scenario_run_id != second.scenario_run_id
    assert first.observed_result == second.observed_result
    assert first.calculations == second.calculations
    assert second.links.repeat_of_execution_id == first.validation_execution_id
    assert len(second_service.list_executions(test_id="VT-TOP-DEF-001")) == 2


@pytest.mark.i5
def test_backend_provenance_and_formal_exploratory_separation_are_enforced(
    tmp_path: Path,
) -> None:
    coordinator = scenario(tmp_path, "boundary")
    initial = coordinator.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=601),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
        )
    )
    service = validation(tmp_path, coordinator)

    with pytest.raises(ValidationBoundaryError, match="evidence class"):
        service.start_execution(
            "VT-EXP-ALL-001",
            initial.snapshot.run.scenario_run_id,
        )

    false_manifest = MANIFEST.model_copy(
        update={"application_build_id": "f" * 64}
    )
    false_service = ValidationService(
        ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        ValidationCatalogueLoader(CATALOGUE),
        coordinator,
        application_build_manifest=false_manifest,
    )
    with pytest.raises(ValidationBoundaryError, match="backend-controlled build"):
        false_service.start_execution(
            "VT-VAL-RECORD-001",
            initial.snapshot.run.scenario_run_id,
        )
    assert service.list_executions(evidence_class=EvidenceClass.EXPLORATORY) == ()

    with pytest.raises(ValidationError, match="application_build_id"):
        StartValidationExecutionRequest.model_validate(
            {
                "test_id": "VT-VAL-RECORD-001",
                "scenario_run_id": initial.snapshot.run.scenario_run_id,
                "application_build_id": "f" * 64,
            },
            strict=True,
        )


@pytest.mark.i5
def test_missing_automated_comparison_stops_instead_of_inventing_verdict(
    tmp_path: Path,
) -> None:
    coordinator = scenario(tmp_path, "no-guess")
    initial = coordinator.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=701),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
        )
    )
    service = validation(tmp_path, coordinator)
    execution = service.start_execution(
        "VT-VAL-RECORD-001",
        initial.snapshot.run.scenario_run_id,
    )
    service.capture_checkpoint(execution.validation_execution_id, "CONTROLLED_RESULT")

    with pytest.raises(ValidationBoundaryError, match="do not invent a verdict"):
        service.finalise_execution(
            execution.validation_execution_id,
            "CONTROLLED_RESULT",
        )
    assert service.get_execution(execution.validation_execution_id).execution.status is (
        ValidationExecutionStatus.ACTIVE
    )


@pytest.mark.i5
def test_checkpoint_replacement_is_rejected_without_overwriting_evidence(
    tmp_path: Path,
) -> None:
    coordinator = scenario(tmp_path, "checkpoint-replacement")
    initial, _fault = initialise_and_fault(coordinator, "1.1", 801)
    service = validation(tmp_path, coordinator)
    execution = service.start_execution(
        "VT-TOP-DEF-001",
        initial.snapshot.run.scenario_run_id,
    )
    first = service.capture_checkpoint(execution.validation_execution_id, "POST_TRIP")

    with pytest.raises(ValidationBoundaryError, match="cannot be replaced"):
        service.capture_checkpoint(execution.validation_execution_id, "POST_TRIP")
    assert service.get_execution(execution.validation_execution_id).evidence_snapshots == (
        first,
    )
