"""DC-006 source-origin, determination and lifecycle assurance."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from uuid import UUID

import pytest

from ot_demo.application.investigation_service import InvestigationService
from ot_demo.application.scenario_coordinator import ScenarioCoordinator
from ot_demo.domain.enums import (
    CriterionFindingStatus,
    DeterminationContextKind,
    EvidenceClass,
    ScenarioCommandType,
    ScenarioMode,
    ValidationVerdict,
)
from ot_demo.infrastructure.build_identity import ApplicationBuildManifest, BuildIdentityPayload
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.infrastructure.determination_repository import DeterminationRepository
from ot_demo.infrastructure.evidence_package_repository import EvidencePackageRepository
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ot_demo.infrastructure.investigation_repository import InvestigationRepository
from ot_demo.infrastructure.scenario_repository import ScenarioRepository
from ot_demo.infrastructure.validation_repository import ValidationRepository
from ot_demo.modules.evidence_export.models import EvidencePackage
from ot_demo.modules.scenario.models import InitialiseRunRequest, ScenarioCommandRequest
from ot_demo.modules.telemetry.service import TelemetryValidityService
from ot_demo.modules.validation.actor_roles import (
    CONTROLLED_LOCAL_ACTOR_ROLES,
    controlled_actor_role,
)
from ot_demo.modules.validation.catalogue import ValidationCatalogueResolver
from ot_demo.modules.validation.determination import DeterminationBoundaryError, DeterminationService
from ot_demo.modules.validation.service import ValidationService
from ot_demo.modules.validation.source_authority import (
    RegisteredSourceAuthority,
    SourceAuthorityDependencies,
)


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
BUILD = ApplicationBuildManifest(
    application_build_id=sha256_bytes(canonical_json_bytes(IDENTITY.model_dump(mode="json"))),
    identity=IDENTITY,
)


@dataclass
class Harness:
    scenarios: ScenarioCoordinator
    catalogue: ValidationCatalogueResolver
    validation: ValidationService
    determination: DeterminationService
    determinations: DeterminationRepository
    validation_records: ValidationRepository
    investigation: InvestigationService
    investigation_records: InvestigationRepository
    packages: EvidencePackageRepository


def harness(
    tmp_path: Path,
    *,
    configuration_root: Path | None = None,
    repository_root: Path = ROOT,
    telemetry: TelemetryValidityService | None = None,
) -> Harness:
    tmp_path.mkdir(parents=True, exist_ok=True)
    loader = JsonConfigurationLoader(configuration_root or ROOT / "config/network")
    scenarios = ScenarioCoordinator(
        ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS),
        loader,
        application_build_manifest=BUILD,
    )
    catalogue = ValidationCatalogueResolver(
        CATALOGUE,
        (
            CATALOGUE.parent / "history/v1.0/catalogue.json",
            CATALOGUE.parent / "history/v1.1/catalogue.json",
        ),
    )
    validation_records = ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS)
    validation = ValidationService(
        validation_records,
        catalogue,
        scenarios,
        loader,
        application_build_manifest=BUILD,
    )
    determinations = DeterminationRepository(tmp_path / "validation.sqlite3", MIGRATIONS)
    investigation_records = InvestigationRepository(tmp_path / "validation.sqlite3", MIGRATIONS)
    packages = EvidencePackageRepository(tmp_path / "validation.sqlite3", MIGRATIONS)
    authority = RegisteredSourceAuthority(SourceAuthorityDependencies(
        repository_root=repository_root,
        build=BUILD,
        configurations=loader,
        catalogue=catalogue,
        validation=validation_records,
        scenarios=scenarios,
        investigation=investigation_records,
        packages=packages,
        determination=determinations,
        telemetry=telemetry or TelemetryValidityService(),
    ))
    determination = DeterminationService(
        determinations,
        validation_records,
        catalogue,
        application_build_manifest=BUILD,
        source_authority=authority,
    )
    investigation = InvestigationService(
        investigation_records,
        loader,
        scenarios,
        validation,
        application_build_manifest=BUILD,
    )
    return Harness(
        scenarios, catalogue, validation, determination, determinations,
        validation_records, investigation, investigation_records, packages,
    )


def prepare_record_context(h: Harness, test_id: str, *, at: datetime = T0):
    _, attempt = h.validation.create_target_selection(test_id, created_at=at)
    return h.determination.prepare_context(
        validation_attempt_id=attempt.validation_attempt_id,
        frozen_at=at + timedelta(milliseconds=1),
    )


def evaluate(h: Harness, context, *, at: datetime = T0):
    return h.determination.evaluate_machine_criteria(
        context.determination_context_id,
        evaluated_at=at + timedelta(milliseconds=2),
    )


def finding(findings, criterion_id: str):
    return next(item for item in findings if item.criterion_id == criterion_id)


def run_configuration_determination(h: Harness, *, at: datetime):
    context = prepare_record_context(h, "VT-CFG-BASE-001", at=at)
    findings = evaluate(h, context, at=at)
    result = h.determination.finalise_result(
        context.determination_context_id,
        finalised_at=at + timedelta(milliseconds=3),
    )
    return context, findings, result


def initialise(h: Harness, *, command_id: int, at: datetime = T0):
    return h.scenarios.initialise(InitialiseRunRequest(
        command_id=UUID(int=command_id),
        actor="Graduate Engineer",
        mode=ScenarioMode.FORMAL,
        configuration_version="1.1",
        scenario_time=at,
    ))


def start_scenario_context(h: Harness, test_id: str, *, command_id: int, trip: bool):
    initial = initialise(h, command_id=command_id)
    run_id = initial.snapshot.run.scenario_run_id
    execution = h.validation.start_execution(test_id, run_id)
    if trip:
        h.scenarios.execute(run_id, ScenarioCommandRequest(
            command_id=UUID(int=command_id + 100),
            scenario_run_id=run_id,
            actor="Graduate Engineer",
            expected_revision=0,
            command_type=ScenarioCommandType.INITIATE_FAULT,
            scenario_time=T0 + timedelta(seconds=10),
        ))
    h.validation.capture_checkpoint(execution.validation_execution_id, "CONTROLLED_RESULT")
    context = h.determination.prepare_context(
        validation_attempt_id=execution.validation_attempt_id,
        scenario_run_id=run_id,
        validation_execution_id=execution.validation_execution_id,
        frozen_at=T0 + timedelta(seconds=11),
    )
    return context


def altered_configuration_root(tmp_path: Path) -> Path:
    destination = tmp_path / "config/network"
    shutil.copytree(ROOT / "config/network", destination)
    network_path = destination / "v1.1/network.json"
    network = json.loads(network_path.read_text(encoding="utf-8"))
    network["feeders"][0]["normal_connected_load_kw"] += 1
    network_path.write_text(json.dumps(network, indent=2) + "\n", encoding="utf-8")
    manifest_path = destination / "v1.1/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["data_file"]["sha256"] = hashlib.sha256(network_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return destination


def nfr_repository(tmp_path: Path, *, complete: bool) -> Path:
    root = tmp_path / "review-root"
    (root / "validation/test-definitions").mkdir(parents=True)
    shutil.copy2(CATALOGUE, root / "validation/test-definitions/catalogue.json")
    (root / "app/backend/ot_demo/api").mkdir(parents=True)
    (root / "app/backend/ot_demo/api/runtime.py").write_text(
        "LOCAL_RUNTIME = True\n", encoding="utf-8"
    )
    (root / "app/frontend").mkdir(parents=True)
    (root / "app/frontend/playwright.config.ts").write_text(
        "const baseURL = 'http://127.0.0.1:8000'\n", encoding="utf-8"
    )
    (root / "app/frontend/src").mkdir(parents=True)
    probes = (
        "RunSetup workspace-main TelemetryView RestorationView ValidationView "
        "EvidenceLibrary InvestigationWorkspace Engineering Basis"
    )
    notice = "Simulated operation only — no real equipment control."
    (root / "app/frontend/src/review.tsx").write_text(
        probes + "\n" + "\n".join([notice] * (8 if complete else 7)),
        encoding="utf-8",
    )
    return root


@pytest.mark.dc006
def test_configuration_producer_derives_pass_from_real_packages_and_mismatch_from_altered_package(tmp_path: Path) -> None:
    valid = harness(tmp_path / "valid")
    context = prepare_record_context(valid, "VT-CFG-BASE-001")
    valid_findings = evaluate(valid, context)
    assert {item.status for item in valid_findings} == {CriterionFindingStatus.SATISFIED}

    changed_root = altered_configuration_root(tmp_path / "altered")
    changed = harness(tmp_path / "changed-db", configuration_root=changed_root)
    changed_context = prepare_record_context(changed, "VT-CFG-BASE-001")
    changed_findings = evaluate(changed, changed_context)
    assert finding(changed_findings, "CFG-01").status is CriterionFindingStatus.NOT_SATISFIED
    assert finding(changed_findings, "CFG-03").status is CriterionFindingStatus.NOT_SATISFIED
    assert finding(changed_findings, "CFG-05").status is CriterionFindingStatus.NOT_SATISFIED


@pytest.mark.dc006
def test_scenario_producer_reads_actual_topology_outage_and_detects_post_trip_mismatch(tmp_path: Path) -> None:
    normal = harness(tmp_path / "normal")
    normal_context = start_scenario_context(normal, "VT-TOP-NORMAL-001", command_id=1, trip=False)
    normal_findings = evaluate(normal, normal_context)
    assert {item.status for item in normal_findings} == {CriterionFindingStatus.SATISFIED}

    post_trip = harness(tmp_path / "post-trip")
    post_trip_context = start_scenario_context(post_trip, "VT-TOP-NORMAL-001", command_id=2, trip=True)
    post_trip_findings = evaluate(post_trip, post_trip_context)
    assert finding(post_trip_findings, "TOP-N0-02").status is CriterionFindingStatus.NOT_SATISFIED
    assert finding(post_trip_findings, "TOP-N0-06").status is CriterionFindingStatus.NOT_SATISFIED


class NonconformingTelemetryAuthority(TelemetryValidityService):
    def classify(self, point, scenario_time):
        return super().classify(point, scenario_time - timedelta(milliseconds=1))


@pytest.mark.dc006
def test_fixture_producer_executes_real_telemetry_authority_and_detects_changed_service_output(tmp_path: Path) -> None:
    valid = harness(tmp_path / "valid")
    context = prepare_record_context(valid, "VT-TEL-STALE-001")
    valid_findings = evaluate(valid, context)
    assert {item.status for item in valid_findings} == {CriterionFindingStatus.SATISFIED}
    result = valid.determination.finalise_result(context.determination_context_id, finalised_at=T0 + timedelta(seconds=1))
    execution = valid.validation_records.get_execution(result.validation_execution_id)
    assert execution.context_kind is DeterminationContextKind.CONTROLLED_FIXTURE_EXECUTION
    assert execution.scenario_run_id is None

    changed = harness(tmp_path / "changed", telemetry=NonconformingTelemetryAuthority())
    changed_context = prepare_record_context(changed, "VT-TEL-STALE-001")
    changed_findings = evaluate(changed, changed_context)
    assert finding(changed_findings, "TEL-ST-01").status is CriterionFindingStatus.NOT_SATISFIED
    assert finding(changed_findings, "TEL-ST-02").status is CriterionFindingStatus.NOT_SATISFIED


@pytest.mark.dc006
def test_event_producer_reads_actual_registry_history_for_pass_and_missing_switching_mismatch(tmp_path: Path) -> None:
    h = harness(tmp_path)
    context = start_scenario_context(h, "VT-ALM-EVT-001", command_id=3, trip=True)
    findings = evaluate(h, context)
    assert finding(findings, "EVT-04").status is CriterionFindingStatus.SATISFIED
    assert finding(findings, "EVT-06").status is CriterionFindingStatus.NOT_SATISFIED


@pytest.mark.dc006
def test_investigation_producer_reads_real_failure_history_and_detects_wrong_failure_source(tmp_path: Path) -> None:
    valid = harness(tmp_path / "valid")
    valid.investigation.start_failure("Graduate Engineer")
    context = prepare_record_context(valid, "VT-CFG-INV-001", at=T0 + timedelta(hours=1))
    findings = evaluate(valid, context, at=T0 + timedelta(hours=1))
    assert finding(findings, "INV-01").status is CriterionFindingStatus.SATISFIED

    changed_root = altered_configuration_root(tmp_path / "altered")
    changed = harness(tmp_path / "changed-db", configuration_root=changed_root)
    _, _, failed = run_configuration_determination(changed, at=T0)
    assert failed.verdict is ValidationVerdict.FAIL
    changed_context = prepare_record_context(changed, "VT-CFG-INV-001", at=T0 + timedelta(hours=1))
    changed_findings = evaluate(changed, changed_context, at=T0 + timedelta(hours=1))
    assert finding(changed_findings, "INV-01").status is CriterionFindingStatus.NOT_SATISFIED


@pytest.mark.dc006
def test_repeat_producer_reads_finalised_execution_findings_and_detects_engineering_change(tmp_path: Path) -> None:
    valid = harness(tmp_path / "valid")
    run_configuration_determination(valid, at=T0)
    run_configuration_determination(valid, at=T0 + timedelta(seconds=1))
    context = prepare_record_context(valid, "VT-DET-REPEAT-001", at=T0 + timedelta(seconds=2))
    findings = evaluate(valid, context, at=T0 + timedelta(seconds=2))
    assert finding(findings, "DET-03").status is CriterionFindingStatus.SATISFIED

    config_root = tmp_path / "mutable/config/network"
    shutil.copytree(ROOT / "config/network", config_root)
    changed = harness(tmp_path / "changed-db", configuration_root=config_root)
    run_configuration_determination(changed, at=T0)
    altered_configuration_root(tmp_path / "replacement")
    replacement = tmp_path / "replacement/config/network"
    shutil.copy2(replacement / "v1.1/network.json", config_root / "v1.1/network.json")
    shutil.copy2(replacement / "v1.1/manifest.json", config_root / "v1.1/manifest.json")
    run_configuration_determination(changed, at=T0 + timedelta(seconds=1))
    changed_context = prepare_record_context(changed, "VT-DET-REPEAT-001", at=T0 + timedelta(seconds=2))
    changed_findings = evaluate(changed, changed_context, at=T0 + timedelta(seconds=2))
    assert finding(changed_findings, "DET-03").status is CriterionFindingStatus.NOT_SATISFIED


def insert_package(h: Harness, archive: Path, *, command_id: int, package_id: str) -> None:
    initial = initialise(h, command_id=command_id)
    execution = h.validation.start_execution(
        "VT-FML-N0-N5-001", initial.snapshot.run.scenario_run_id
    )
    h.packages.insert(EvidencePackage(
        package_id=package_id,
        validation_execution_id=execution.validation_execution_id,
        test_id="VT-FML-N0-N5-001",
        test_definition_version="1.0",
        test_definition_sha256="a" * 64,
        source_catalogue_version="1.1",
        source_catalogue_sha256="b" * 64,
        evidence_class=EvidenceClass.FORMAL,
        scenario_run_id=initial.snapshot.run.scenario_run_id,
        configuration_id="network-configuration-v1.1",
        configuration_version="1.1",
        application_build_id=BUILD.application_build_id,
        generation_application_build_id=BUILD.application_build_id,
        evidence_snapshot_ids=(UUID(int=302),),
        manifest_sha256="c" * 64,
        archive_sha256="d" * 64,
        archive_path=str(archive),
        verification_status="VERIFIED",
        source_record_references=("records/validation-execution.json",),
    ))


@pytest.mark.dc006
def test_evidence_package_producer_reads_repository_and_detects_missing_archive(tmp_path: Path) -> None:
    valid = harness(tmp_path / "valid")
    archive = tmp_path / "valid/package.zip"
    archive.write_bytes(b"controlled package")
    insert_package(valid, archive, command_id=301, package_id="PKG-000000000001")
    context = prepare_record_context(valid, "VT-PKG-EVIDENCE-001")
    findings = evaluate(valid, context)
    assert finding(findings, "PKG-04").status is CriterionFindingStatus.SATISFIED

    missing = harness(tmp_path / "missing")
    insert_package(missing, tmp_path / "missing/not-created.zip", command_id=401, package_id="PKG-000000000002")
    missing_context = prepare_record_context(missing, "VT-PKG-EVIDENCE-001")
    missing_findings = evaluate(missing, missing_context)
    assert finding(missing_findings, "PKG-04").status is CriterionFindingStatus.NOT_SATISFIED


@pytest.mark.dc006
def test_nfr_producer_reads_build_surface_and_structural_sources_for_pass_and_notice_mismatch(tmp_path: Path) -> None:
    complete_root = nfr_repository(tmp_path / "complete", complete=True)
    valid = harness(tmp_path / "valid-db", repository_root=complete_root)
    context = prepare_record_context(valid, "VT-NFR-REVIEW-001")
    findings = evaluate(valid, context)
    machine = [item for item in findings if item.criterion_id.startswith("NFR-M")]
    assert {item.status for item in machine} == {CriterionFindingStatus.SATISFIED}

    incomplete_root = nfr_repository(tmp_path / "incomplete", complete=False)
    changed = harness(tmp_path / "changed-db", repository_root=incomplete_root)
    changed_context = prepare_record_context(changed, "VT-NFR-REVIEW-001")
    changed_findings = evaluate(changed, changed_context)
    assert finding(changed_findings, "NFR-M06").status is CriterionFindingStatus.NOT_SATISFIED


@pytest.mark.dc006
def test_backend_produces_unique_attempt_role_membership_and_caller_cannot_select_source_ids(tmp_path: Path) -> None:
    h = harness(tmp_path)
    _, attempt = h.validation.create_target_selection("VT-CFG-BASE-001", created_at=T0)
    h.determination.prepare_context(
        validation_attempt_id=attempt.validation_attempt_id,
        frozen_at=T0 + timedelta(milliseconds=1),
    )
    assert not hasattr(h.determination, "capture_authoritative_source")
    assert not hasattr(h.determination, "capture_configuration_package_sources")
    with pytest.raises(Exception, match="attempt/role already owns"):
        h.determination.prepare_context(
            validation_attempt_id=attempt.validation_attempt_id,
            frozen_at=T0 + timedelta(milliseconds=2),
        )


@pytest.mark.dc006
def test_engineering_review_uses_shared_actor_authority_and_backend_verdict(tmp_path: Path) -> None:
    review_root = nfr_repository(tmp_path, complete=True)
    h = harness(tmp_path / "db", repository_root=review_root)
    context = prepare_record_context(h, "VT-NFR-REVIEW-001")
    evaluate(h, context)
    method = h.catalogue.get_method("VT-NFR-REVIEW-001")
    for index, criterion in enumerate(item for item in method.criteria if item.kind.value == "ENGINEERING_REVIEW"):
        proposal = h.determination.propose_review_finding(
            context.determination_context_id,
            criterion.criterion_id,
            proposed_finding=CriterionFindingStatus.SATISFIED,
            proposer_actor_id="graduate-engineer",
            reason="Fixed proposition is supported by the frozen exact review membership.",
            proposed_at=T0 + timedelta(seconds=1 + index),
        )
        h.determination.finalise_review_finding(
            proposal.review_proposal_id,
            reviewer_actor_id="independent-reviewer",
            final_finding=CriterionFindingStatus.SATISFIED,
            reason="Independent criterion finding accepted against frozen evidence.",
            finalised_at=T0 + timedelta(seconds=10 + index),
        )
    result = h.determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=20)
    )
    assert result.verdict is ValidationVerdict.PASS
    assert controlled_actor_role("independent-reviewer") == "INDEPENDENT_ENGINEERING_REVIEWER"
    assert ValidationService._ACTOR_ROLES is CONTROLLED_LOCAL_ACTOR_ROLES


@pytest.mark.dc006
def test_context_result_source_origin_and_procedure_execution_are_database_immutable(tmp_path: Path) -> None:
    h = harness(tmp_path)
    context = prepare_record_context(h, "VT-CFG-BASE-001")
    evaluate(h, context)
    result = h.determination.finalise_result(context.determination_context_id, finalised_at=T0 + timedelta(seconds=1))
    with sqlite3.connect(h.determinations.database_path) as connection:
        for statement in (
            "UPDATE procedure_validation_executions SET verdict='FAIL' WHERE validation_execution_id=?",
            "UPDATE criterion_findings SET status='NOT_SATISFIED' WHERE determination_context_id=?",
            "UPDATE determination_source_origin_bindings SET origin_identity='changed' WHERE validation_attempt_id=?",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(statement, (str(result.validation_execution_id if "procedure" in statement else context.determination_context_id if "criterion" in statement else context.validation_attempt_id),))


@pytest.mark.dc006
def test_pre_entry_suspension_remains_only_no_execution_route(tmp_path: Path) -> None:
    h = harness(tmp_path)
    _, attempt = h.validation.create_target_selection("VT-CFG-BASE-001", created_at=T0)
    assert attempt.validation_execution_id is None
    with pytest.raises(DeterminationBoundaryError, match="exact context membership"):
        h.determination.bind_context(
            validation_attempt_id=attempt.validation_attempt_id,
            frozen_at=T0 + timedelta(seconds=1),
        )
