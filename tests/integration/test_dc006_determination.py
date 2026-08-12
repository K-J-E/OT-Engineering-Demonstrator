"""DC-006 source-origin, determination and lifecycle assurance."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace
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
from ot_demo.modules.evidence_export.service import EvidenceExportService
from ot_demo.modules.scenario.models import InitialiseRunRequest, ScenarioCommandRequest
from ot_demo.modules.telemetry.service import TelemetryValidityService
from ot_demo.modules.restoration.service import RestorationService
from ot_demo.modules.restoration.models import PermissiveResult
from ot_demo.domain.enums import PermissiveStatus, RestorationCriterion
from ot_demo.modules.validation.actor_roles import (
    CONTROLLED_LOCAL_ACTOR_ROLES,
    controlled_actor_role,
)
from ot_demo.modules.validation.catalogue import ValidationCatalogueResolver
from ot_demo.modules.validation.catalogue import ValidationCatalogueLoader
from ot_demo.modules.validation.determination import DeterminationBoundaryError, DeterminationService
from ot_demo.modules.validation.service import ValidationService
from ot_demo.modules.validation.models import ValidationExecutionLinks
from ot_demo.modules.validation.source_authority import (
    RegisteredSourceAuthority,
    SourceAuthorityDependencies,
)
from ot_demo.modules.validation.source_adapters import derive_combined_observation
from ot_demo.modules.validation.structural_registry import resolved_structural_registry


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
    validation_database: Path | None = None,
    catalogue_path: Path = CATALOGUE,
    package_archive_root: Path | None = None,
    structural_registry: dict[str, dict[str, str]] | None = None,
    restoration: RestorationService | None = None,
) -> Harness:
    tmp_path.mkdir(parents=True, exist_ok=True)
    loader = JsonConfigurationLoader(configuration_root or ROOT / "config/network")
    scenarios = ScenarioCoordinator(
        ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS),
        loader,
        application_build_manifest=BUILD,
    )
    catalogue = ValidationCatalogueResolver(
        catalogue_path,
        tuple(
            item for item in (
                CATALOGUE.parent / "history/v1.0/catalogue.json",
                CATALOGUE.parent / "history/v1.1/catalogue.json",
            )
            if item != catalogue_path
        ),
    )
    validation_path = validation_database or tmp_path / "validation.sqlite3"
    validation_records = ValidationRepository(validation_path, MIGRATIONS)
    validation = ValidationService(
        validation_records,
        catalogue,
        scenarios,
        loader,
        application_build_manifest=BUILD,
    )
    determinations = DeterminationRepository(validation_path, MIGRATIONS)
    investigation_records = InvestigationRepository(validation_path, MIGRATIONS)
    packages = EvidencePackageRepository(validation_path, MIGRATIONS)
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
        package_archive_root=package_archive_root,
        structural_registry=structural_registry,
        restoration=restoration or RestorationService(),
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


def execute_available(
    h: Harness,
    run_id: UUID,
    command_type: ScenarioCommandType,
    *,
    command_id: int,
    target: str | None = None,
):
    snapshot = h.scenarios.snapshot(run_id)
    action = next(
        item for item in snapshot.allowed_actions
        if item.command_type is command_type
        and item.available
        and (target is None or item.target_entity_id == target)
    )
    seconds = {
        ScenarioCommandType.INITIATE_FAULT: 10,
        ScenarioCommandType.ACKNOWLEDGE_ALARM: 11,
        ScenarioCommandType.RESTORE_NORMAL_SOURCE: 40,
        ScenarioCommandType.ASSESS_RESTORATION: 50,
        ScenarioCommandType.EXECUTE_RESTORATION: 55,
    }.get(command_type, 20 if target == "SW-A12" else 30)
    return h.scenarios.execute(run_id, ScenarioCommandRequest(
        command_id=UUID(int=command_id),
        scenario_run_id=run_id,
        actor="Graduate Engineer",
        expected_revision=snapshot.run.state_revision,
        command_type=action.command_type,
        scenario_time=T0 + timedelta(seconds=seconds),
        target_entity_id=action.target_entity_id,
        requested_state=action.requested_state,
        alarm_id=action.alarm_id,
        assessment_id=action.assessment_id,
    ))


def full_formal_context(
    h: Harness,
    *,
    command_id: int = 20_000,
    repeat_of_execution_id: UUID | None = None,
):
    initial = initialise(h, command_id=command_id)
    run_id = initial.snapshot.run.scenario_run_id
    execution = h.validation.start_execution(
        "VT-FML-N0-N5-001", run_id,
        links=ValidationExecutionLinks(
            repeat_of_execution_id=repeat_of_execution_id
        ),
    )
    h.validation.capture_checkpoint(execution.validation_execution_id, "N0")
    steps = (
        (ScenarioCommandType.INITIATE_FAULT, None, "N1"),
        (ScenarioCommandType.ACKNOWLEDGE_ALARM, None, None),
        (ScenarioCommandType.OPERATE_ISOLATION_DEVICE, "SW-A12", None),
        (ScenarioCommandType.OPERATE_ISOLATION_DEVICE, "SW-A23", "N2"),
        (ScenarioCommandType.RESTORE_NORMAL_SOURCE, "BRK-A", "N3"),
        (ScenarioCommandType.ASSESS_RESTORATION, None, "N4"),
        (ScenarioCommandType.EXECUTE_RESTORATION, None, "N5"),
    )
    for offset, (command_type, target, checkpoint) in enumerate(steps, 1):
        execute_available(
            h, run_id, command_type,
            command_id=command_id + offset,
            target=target,
        )
        if checkpoint:
            h.validation.capture_checkpoint(execution.validation_execution_id, checkpoint)
    return h.determination.prepare_context(
        validation_attempt_id=execution.validation_attempt_id,
        scenario_run_id=run_id,
        validation_execution_id=execution.validation_execution_id,
        frozen_at=T0 + timedelta(seconds=56),
    )


def finalise_determined(h: Harness, context, *, at: datetime):
    evaluate(h, context, at=at)
    result = h.determination.finalise_result(
        context.determination_context_id,
        finalised_at=at + timedelta(milliseconds=3),
    )
    return result


def fixture_context(
    h: Harness,
    test_id: str,
    *,
    at: datetime,
    repeat_of_execution_id: UUID | None = None,
):
    _, attempt = h.validation.create_target_selection(test_id, created_at=at)
    return h.determination.prepare_context(
        validation_attempt_id=attempt.validation_attempt_id,
        repeat_of_execution_id=repeat_of_execution_id,
        frozen_at=at + timedelta(milliseconds=1),
    )


def corrected_post_trip_context(
    h: Harness,
    *,
    command_id: int,
    repeat_of_execution_id: UUID | None = None,
):
    initial = initialise(h, command_id=command_id)
    run_id = initial.snapshot.run.scenario_run_id
    execution = h.validation.start_execution(
        "VT-TOP-DEF-001", run_id,
        links=ValidationExecutionLinks(
            repeat_of_execution_id=repeat_of_execution_id
        ),
    )
    execute_available(
        h, run_id, ScenarioCommandType.INITIATE_FAULT,
        command_id=command_id + 1,
    )
    h.validation.capture_checkpoint(execution.validation_execution_id, "POST_TRIP")
    return h.determination.prepare_context(
        validation_attempt_id=execution.validation_attempt_id,
        scenario_run_id=run_id,
        validation_execution_id=execution.validation_execution_id,
        frozen_at=T0 + timedelta(seconds=11),
    )


def exploration_determination_context(
    h: Harness,
    *,
    test_id: str,
    case_id: str,
    section_id: str,
    command_base: int,
):
    initial = h.scenarios.initialise(InitialiseRunRequest(
        command_id=UUID(int=command_base),
        actor="Graduate Engineer",
        mode=ScenarioMode.EXPLORATION,
        configuration_version="1.1",
        fault_section_id=section_id,
        scenario_time=T0,
    ))
    run_id = initial.snapshot.run.scenario_run_id
    execution = h.validation.start_execution(test_id, run_id, case_id=case_id)

    def execute(command_type, number: int, seconds: float, target=None):
        snapshot = h.scenarios.snapshot(run_id)
        action = next(
            item for item in snapshot.allowed_actions
            if item.command_type is command_type and item.available
            and (target is None or item.target_entity_id == target)
        )
        return h.scenarios.execute(run_id, ScenarioCommandRequest(
            command_id=UUID(int=number),
            scenario_run_id=run_id,
            actor="Graduate Engineer",
            expected_revision=snapshot.run.state_revision,
            command_type=action.command_type,
            scenario_time=T0 + timedelta(seconds=seconds),
            target_entity_id=action.target_entity_id,
            requested_state=action.requested_state,
            alarm_id=action.alarm_id,
            assessment_id=action.assessment_id,
        ))

    fault = execute(ScenarioCommandType.INITIATE_FAULT, command_base + 1, 10)
    if case_id == "EXP-ALL-A4-STALE-OPEN":
        execute(ScenarioCommandType.ACKNOWLEDGE_ALARM, command_base + 2, 60.001)
    elif test_id == "VT-EXP-ROLE-001":
        number = command_base + 2
        seconds = 20
        while True:
            snapshot = h.scenarios.snapshot(run_id)
            isolation = next((
                item for item in snapshot.allowed_actions
                if item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
                and item.available
            ), None)
            if isolation is None:
                break
            execute(
                ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
                number, seconds, isolation.target_entity_id,
            )
            number += 1
            seconds += 10
        snapshot = h.scenarios.snapshot(run_id)
        restore = next((
            item for item in snapshot.allowed_actions
            if item.command_type is ScenarioCommandType.RESTORE_NORMAL_SOURCE
            and item.available
        ), None)
        if restore is not None:
            execute(
                ScenarioCommandType.RESTORE_NORMAL_SOURCE,
                number, 40, restore.target_entity_id,
            )
            number += 1
        execute(ScenarioCommandType.ASSESS_RESTORATION, number, 50)
        number += 1
        snapshot = h.scenarios.snapshot(run_id)
        if any(
            item.command_type is ScenarioCommandType.EXECUTE_RESTORATION
            and item.available for item in snapshot.allowed_actions
        ):
            execute(ScenarioCommandType.EXECUTE_RESTORATION, number, 55)
    h.validation.capture_checkpoint(execution.validation_execution_id, "CONTROLLED_RESULT")
    return h.determination.prepare_context(
        validation_attempt_id=execution.validation_attempt_id,
        scenario_run_id=run_id,
        validation_execution_id=execution.validation_execution_id,
        frozen_at=T0 + timedelta(seconds=62),
    )


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
    shutil.copytree(ROOT / "app/frontend/src", root / "app/frontend/src")
    if not complete:
        registry_path = root / "app/frontend/src/controlled-surfaces.v1.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["surfaces"][3]["fixed_notice"] = "Uncontrolled substitute notice"
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
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


@pytest.mark.dc006
def test_full_formal_n0_n5_campaign_uses_real_run_and_satisfies_all_controlled_criteria(
    tmp_path: Path,
) -> None:
    h = harness(tmp_path)
    context = full_formal_context(h)
    findings = evaluate(h, context, at=T0 + timedelta(seconds=56))
    assert len(findings) == 8
    assert {item.status for item in findings} == {CriterionFindingStatus.SATISFIED}


class NonconformingTelemetryAuthority(TelemetryValidityService):
    def classify(self, point, scenario_time):
        return super().classify(point, scenario_time - timedelta(milliseconds=1))


class NonconformingRadialityAuthority(RestorationService):
    @staticmethod
    def evaluate_radiality(proposed, evidence_point_ids=()):
        return PermissiveResult(
            criterion=RestorationCriterion.RADIAL_TOPOLOGY,
            status=PermissiveStatus.PASS,
            reason_codes=("TOPOLOGY_RADIAL",),
            evidence_point_ids=evidence_point_ids,
        )


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
def test_radial_fixture_builds_a_real_energised_loop_and_uses_restoration_authority(
    tmp_path: Path,
) -> None:
    valid = harness(tmp_path / "valid")
    context = prepare_record_context(valid, "VT-RST-RADIAL-001")
    findings = evaluate(valid, context)
    assert {item.status for item in findings} == {CriterionFindingStatus.SATISFIED}

    changed = harness(
        tmp_path / "changed",
        restoration=NonconformingRadialityAuthority(),
    )
    changed_context = prepare_record_context(changed, "VT-RST-RADIAL-001")
    changed_findings = evaluate(changed, changed_context)
    assert finding(changed_findings, "RAD-03").status is CriterionFindingStatus.NOT_SATISFIED
    assert finding(changed_findings, "RAD-04").status is CriterionFindingStatus.NOT_SATISFIED


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

    valid.investigation.start_failure("Graduate Engineer")
    ambiguous_context = prepare_record_context(
        valid, "VT-CFG-INV-001", at=T0 + timedelta(hours=2)
    )
    ambiguous_findings = evaluate(
        valid, ambiguous_context, at=T0 + timedelta(hours=2)
    )
    assert finding(
        ambiguous_findings, "INV-01"
    ).status is CriterionFindingStatus.NOT_SATISFIED

    changed_root = altered_configuration_root(tmp_path / "altered")
    changed = harness(tmp_path / "changed-db", configuration_root=changed_root)
    _, _, failed = run_configuration_determination(changed, at=T0)
    assert failed.verdict is ValidationVerdict.FAIL
    changed_context = prepare_record_context(changed, "VT-CFG-INV-001", at=T0 + timedelta(hours=1))
    changed_findings = evaluate(changed, changed_context, at=T0 + timedelta(hours=1))
    assert finding(changed_findings, "INV-01").status is CriterionFindingStatus.NOT_SATISFIED


@pytest.mark.dc006
def test_repeat_producer_uses_exact_three_linked_pairs_and_rejects_incomplete_membership(tmp_path: Path) -> None:
    empty = harness(tmp_path / "empty")
    empty_context = prepare_record_context(
        empty, "VT-DET-REPEAT-001", at=T0 - timedelta(hours=1)
    )
    empty_findings = evaluate(empty, empty_context, at=T0 - timedelta(hours=1))
    assert {item.status for item in empty_findings} == {
        CriterionFindingStatus.NOT_EVALUATED
    }
    with pytest.raises(DeterminationBoundaryError, match="incomplete"):
        empty.determination.finalise_result(
            empty_context.determination_context_id,
            finalised_at=T0 - timedelta(minutes=59),
        )

    shared = tmp_path / "valid/validation.sqlite3"
    valid = harness(tmp_path / "valid/formal-one", validation_database=shared)
    formal_one = full_formal_context(valid, command_id=30_000)
    formal_one_result = finalise_determined(valid, formal_one, at=T0 + timedelta(seconds=56))
    valid = harness(tmp_path / "valid/formal-two", validation_database=shared)
    formal_two = full_formal_context(
        valid, command_id=31_000,
        repeat_of_execution_id=formal_one_result.validation_execution_id,
    )
    finalise_determined(valid, formal_two, at=T0 + timedelta(seconds=57))

    valid = harness(tmp_path / "valid/negative-one", validation_database=shared)
    negative_one = fixture_context(valid, "VT-TEL-STALE-001", at=T0 + timedelta(hours=1))
    negative_one_result = finalise_determined(valid, negative_one, at=T0 + timedelta(hours=1))
    valid = harness(tmp_path / "valid/negative-two", validation_database=shared)
    negative_two = fixture_context(
        valid, "VT-TEL-STALE-001", at=T0 + timedelta(hours=1),
        repeat_of_execution_id=negative_one_result.validation_execution_id,
    )
    finalise_determined(valid, negative_two, at=T0 + timedelta(hours=1, seconds=1))

    investigation = harness(
        tmp_path / "valid/investigation", validation_database=shared
    )
    failure = investigation.investigation.start_failure("Graduate Engineer")
    failure_id = failure.original_failure.execution.validation_execution_id
    investigation.investigation.record_defect(
        failure_id, "Independent Reviewer", InvestigationService.REVIEW_STEP_IDS
    )
    investigation.investigation.record_correction(
        failure_id, "Independent Reviewer"
    )
    valid = harness(tmp_path / "valid/corrected-one", validation_database=shared)
    corrected_one = corrected_post_trip_context(valid, command_id=32_000)
    corrected_one_result = finalise_determined(valid, corrected_one, at=T0 + timedelta(hours=2))
    valid = harness(tmp_path / "valid/corrected-two", validation_database=shared)
    corrected_two = corrected_post_trip_context(
        valid, command_id=33_000,
        repeat_of_execution_id=corrected_one_result.validation_execution_id,
    )
    finalise_determined(valid, corrected_two, at=T0 + timedelta(hours=2, seconds=1))

    valid = harness(tmp_path / "valid/repeat", validation_database=shared)
    context = prepare_record_context(valid, "VT-DET-REPEAT-001", at=T0 + timedelta(hours=3))
    findings = evaluate(valid, context, at=T0 + timedelta(hours=3))
    assert {item.status for item in findings} == {CriterionFindingStatus.SATISFIED}

    third = harness(tmp_path / "valid/formal-three", validation_database=shared)
    third_context = full_formal_context(third, command_id=34_000)
    finalise_determined(third, third_context, at=T0 + timedelta(hours=3, seconds=1))
    ambiguous = harness(tmp_path / "valid/ambiguous", validation_database=shared)
    ambiguous_context = prepare_record_context(
        ambiguous, "VT-DET-REPEAT-001", at=T0 + timedelta(hours=4)
    )
    ambiguous_findings = evaluate(
        ambiguous, ambiguous_context, at=T0 + timedelta(hours=4)
    )
    assert {item.status for item in ambiguous_findings} == {
        CriterionFindingStatus.NOT_EVALUATED
    }

    incomplete = harness(tmp_path / "incomplete")
    only_one = fixture_context(incomplete, "VT-TEL-STALE-001", at=T0)
    finalise_determined(incomplete, only_one, at=T0)
    incomplete_context = prepare_record_context(
        incomplete, "VT-DET-REPEAT-001", at=T0 + timedelta(hours=1)
    )
    incomplete_findings = evaluate(
        incomplete, incomplete_context, at=T0 + timedelta(hours=1)
    )
    assert {item.status for item in incomplete_findings} == {
        CriterionFindingStatus.NOT_EVALUATED
    }


@pytest.mark.dc006
def test_repeat_pair_identity_or_preservation_mismatch_remains_incomplete(
    tmp_path: Path, monkeypatch,
) -> None:
    h = harness(tmp_path)
    context = prepare_record_context(h, "VT-DET-REPEAT-001")
    method = h.catalogue.get_method("VT-DET-REPEAT-001")
    authority = h.determination._source_authority  # controlled test boundary
    member = {
        "execution_id": "10000000-0000-0000-0000-000000000001",
        "repeat_of_execution_id": None,
        "identity_resolved": True,
        "input_fingerprint": {
            "test_id": "VT-TOP-DEF-001",
            "build_id": BUILD.application_build_id,
            "configuration_id": "network-configuration-v1.1",
            "configuration_version": "1.1",
            "catalogue_version": "1.2",
            "catalogue_sha256": "1" * 64,
            "method_id": "DM-TOP-DEF-001",
            "method_sha256": "2" * 64,
            "fixture_id": None,
            "controlled_clock": T0.isoformat(),
        },
        "preservation": {
            "stored_execution_sha256": "3" * 64,
            "resolved_execution_sha256": "3" * 64,
            "stored_evidence_sha256": "4" * 64,
            "resolved_evidence_sha256": "4" * 64,
            "stored_result_sha256": "5" * 64,
            "resolved_result_sha256": "5" * 64,
            "stored_correction_sha256": "6" * 64,
            "resolved_correction_sha256": "6" * 64,
        },
    }
    repeat = json.loads(json.dumps(member))
    repeat["execution_id"] = "10000000-0000-0000-0000-000000000002"
    repeat["repeat_of_execution_id"] = member["execution_id"]
    exact = authority._repeat_pair_is_exact(
        (member, repeat),
        configuration_id="network-configuration-v1.1",
        configuration_version="1.1",
        fixture_id=None,
        application_build_id=BUILD.application_build_id,
        correction_required=True,
    )
    assert exact is True
    mutations = (
        ("mixed_build", lambda item: item["input_fingerprint"].update(build_id="wrong")),
        ("mixed_catalogue_method", lambda item: item["input_fingerprint"].update(method_sha256="0" * 64)),
        ("unequal_clock", lambda item: item["input_fingerprint"].update(controlled_clock=(T0 + timedelta(seconds=1)).isoformat())),
        ("wrong_configuration", lambda item: item["input_fingerprint"].update(configuration_version="1.0")),
        ("duplicate_link", lambda item: item.update(repeat_of_execution_id=None)),
        ("altered_preservation", lambda item: item["preservation"].update(resolved_evidence_sha256="0" * 64)),
    )
    for _name, mutate in mutations:
        changed = json.loads(json.dumps(repeat))
        mutate(changed)
        assert authority._repeat_pair_is_exact(
            (member, changed),
            configuration_id="network-configuration-v1.1",
            configuration_version="1.1",
            fixture_id=None,
            application_build_id=BUILD.application_build_id,
            correction_required=True,
        ) is False


def export_service(h: Harness, output_root: Path) -> EvidenceExportService:
    return EvidenceExportService(
        h.packages,
        h.validation_records,
        h.investigation_records,
        h.scenarios,
        JsonConfigurationLoader(ROOT / "config/network"),
        h.catalogue,
        h.determinations,
        application_build_manifest=BUILD,
        output_directory=output_root / "evidence/exports",
    )


@pytest.mark.dc006
def test_evidence_package_producer_uses_exact_formal_and_historical_defect_archives(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "campaign"
    database = output_root / "validation.sqlite3"

    formal = harness(
        tmp_path / "formal", validation_database=database,
        package_archive_root=output_root,
    )
    formal_context = full_formal_context(formal, command_id=40_000)
    formal_result = finalise_determined(
        formal, formal_context, at=T0 + timedelta(seconds=56)
    )
    formal_package = export_service(formal, output_root).generate(
        formal_result.validation_execution_id
    )

    historical = harness(
        tmp_path / "historical",
        validation_database=database,
        catalogue_path=CATALOGUE.parent / "history/v1.1/catalogue.json",
        package_archive_root=output_root,
    )
    failure = historical.investigation.start_failure("Graduate Engineer")
    failure_execution = failure.original_failure.execution
    assert failure_execution.verdict is ValidationVerdict.FAIL
    defect_package = export_service(historical, output_root).generate(
        failure_execution.validation_execution_id
    )

    valid = harness(
        tmp_path / "verification", validation_database=database,
        package_archive_root=output_root,
    )
    context = prepare_record_context(valid, "VT-PKG-EVIDENCE-001")
    findings = evaluate(valid, context)
    assert {item.status for item in findings} == {CriterionFindingStatus.SATISFIED}
    assert formal_package.package_id != defect_package.package_id
    assert {item.package_id for item in valid.packages.list()} == {
        formal_package.package_id, defect_package.package_id,
    }
    assert valid.validation_records.get_execution(
        formal_result.validation_execution_id
    ).executed_result_id == formal_result.executed_result_id
    assert valid.validation_records.get_execution(
        failure_execution.validation_execution_id
    ).verdict is ValidationVerdict.FAIL

    archive = output_root / defect_package.archive_path
    archive.write_bytes(archive.read_bytes() + b"tampered")
    changed = harness(
        tmp_path / "tampered", validation_database=database,
        package_archive_root=output_root,
    )
    changed_context = prepare_record_context(
        changed, "VT-PKG-EVIDENCE-001", at=T0 + timedelta(hours=1)
    )
    changed_findings = evaluate(
        changed, changed_context, at=T0 + timedelta(hours=1)
    )
    assert finding(changed_findings, "PKG-03").status is CriterionFindingStatus.NOT_SATISFIED


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

    wrong_profile_root = nfr_repository(tmp_path / "wrong-profile", complete=True)
    surface_path = wrong_profile_root / "app/frontend/src/controlled-surfaces.v1.json"
    surface_payload = json.loads(surface_path.read_text(encoding="utf-8"))
    surface_payload["surfaces"][0]["required_identity_profile"] = "Wrong profile"
    surface_path.write_text(json.dumps(surface_payload, indent=2) + "\n", encoding="utf-8")
    wrong_profile = harness(tmp_path / "wrong-profile-db", repository_root=wrong_profile_root)
    wrong_profile_context = prepare_record_context(wrong_profile, "VT-NFR-REVIEW-001")
    wrong_profile_findings = evaluate(wrong_profile, wrong_profile_context)
    assert finding(wrong_profile_findings, "NFR-M06").status is CriterionFindingStatus.NOT_SATISFIED

    broken_binding_root = nfr_repository(tmp_path / "broken-binding", complete=True)
    component = broken_binding_root / "app/frontend/src/features/run-setup/RunSetup.tsx"
    component.write_text(
        component.read_text(encoding="utf-8").replace(
            "bootstrap.application_build_id", "bootstrap.default_configuration_id"
        ),
        encoding="utf-8",
    )
    broken_binding = harness(
        tmp_path / "broken-binding-db", repository_root=broken_binding_root
    )
    broken_context = prepare_record_context(
        broken_binding, "VT-NFR-REVIEW-001"
    )
    broken_findings = evaluate(broken_binding, broken_context)
    assert finding(
        broken_findings, "NFR-M06"
    ).status is CriterionFindingStatus.NOT_SATISFIED


@pytest.mark.dc006
@pytest.mark.parametrize("mutation", ["concentrated", "extra", "substituted"])
def test_nfr_surface_registry_rejects_concentrated_notices_and_wrong_exact_membership(
    tmp_path: Path, mutation: str,
) -> None:
    root = nfr_repository(tmp_path / mutation, complete=True)
    registry_path = root / "app/frontend/src/controlled-surfaces.v1.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if mutation == "concentrated":
        app_path = root / "app/frontend/src/App.tsx"
        source = app_path.read_text(encoding="utf-8")
        first_id = registry["surfaces"][0]["surface_id"]
        for surface in registry["surfaces"][1:]:
            source = source.replace(
                f'<Surface id="{surface["surface_id"]}">',
                f'<Surface id="{first_id}">',
            )
        app_path.write_text(source, encoding="utf-8")
    elif mutation == "extra":
        extra = dict(registry["surfaces"][-1])
        extra["surface_id"] = "Uncontrolled Extra Surface"
        registry["surfaces"].append(extra)
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    else:
        registry["surfaces"][-1]["surface_id"] = "Substituted Engineering Surface"
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    h = harness(tmp_path / f"{mutation}-db", repository_root=root)
    context = prepare_record_context(h, "VT-NFR-REVIEW-001")
    findings = evaluate(h, context)
    assert finding(findings, "NFR-M03").status is CriterionFindingStatus.NOT_SATISFIED


@pytest.mark.dc006
@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong_owner"])
def test_nfr_structural_registry_detects_missing_extra_and_wrong_owner(
    tmp_path: Path, mutation: str,
) -> None:
    registry = resolved_structural_registry()
    if mutation == "missing":
        registry.pop("EvidencePackage")
    elif mutation == "extra":
        registry["UncontrolledRecord"] = {
            "owner": "validation",
            "symbol": "ot_demo.modules.validation.models.ValidationExecution",
        }
    else:
        registry["EvidencePackage"]["owner"] = "validation"
    h = harness(tmp_path, structural_registry=registry)
    context = prepare_record_context(h, "VT-NFR-REVIEW-001")
    findings = evaluate(h, context)
    assert finding(findings, "NFR-M04").status is CriterionFindingStatus.NOT_SATISFIED
    assert finding(findings, "NFR-M07").status is CriterionFindingStatus.NOT_SATISFIED


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
def test_all_35_methods_and_214_criteria_have_exactly_one_producer_role_selector_path(
    tmp_path: Path,
) -> None:
    """Catalogue-wide QA-053 producer→role→selector closure gate."""

    methods = []
    for loaded in ValidationCatalogueLoader(CATALOGUE).load():
        definition = loaded.definition
        methods.extend(
            (definition.determination_method,)
            if definition.determination_method is not None
            else tuple(case.determination_method for case in definition.constituent_cases)
        )
    assert len(methods) == 35
    assert sum(len(method.criteria) for method in methods) == 214

    command_id = 10_000
    contexts = []
    criterion_total = 0
    for method in methods:
        h = harness(tmp_path / f"method-{command_id}")
        if method.context_kind is not DeterminationContextKind.SCENARIO_EXECUTION:
            _, attempt = h.validation.create_target_selection(
                method.test_id,
                case_id=method.case_id,
                created_at=T0,
            )
            context = h.determination.prepare_context(
                validation_attempt_id=attempt.validation_attempt_id,
                frozen_at=T0 + timedelta(milliseconds=1),
            )
            contexts.append(context)
            criterion_total += len(method.criteria)
            command_id += 1
            continue

        mode = EvidenceClass.EXPLORATORY if method.evidence_class is EvidenceClass.EXPLORATORY else EvidenceClass.FORMAL
        section = "SEC-A2"
        if method.case_id:
            for candidate in ("A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4"):
                if f"-{candidate}" in method.case_id:
                    section = f"SEC-{candidate}"
                    break
        initial = h.scenarios.initialise(InitialiseRunRequest(
            command_id=UUID(int=command_id),
            actor="Graduate Engineer",
            mode=(ScenarioMode.EXPLORATION if mode is EvidenceClass.EXPLORATORY else ScenarioMode.FORMAL),
            configuration_version="1.1",
            fault_section_id=section if mode is EvidenceClass.EXPLORATORY else None,
            scenario_time=T0,
        ))
        execution = h.validation.start_execution(
            method.test_id,
            initial.snapshot.run.scenario_run_id,
            case_id=method.case_id,
        )
        context = h.determination.prepare_context(
            validation_attempt_id=execution.validation_attempt_id,
            scenario_run_id=initial.snapshot.run.scenario_run_id,
            validation_execution_id=execution.validation_execution_id,
            frozen_at=T0 + timedelta(seconds=1),
        )
        contexts.append(context)
        criterion_total += len(method.criteria)
        command_id += 1

    assert len(contexts) == 35
    assert criterion_total == 214


@pytest.mark.dc006
@pytest.mark.parametrize(("test_id", "case_id", "section_id"), (
    ("VT-EXP-ALL-001", "EXP-ALL-A1", "SEC-A1"),
    ("VT-EXP-ALL-001", "EXP-ALL-A2", "SEC-A2"),
    ("VT-EXP-ALL-001", "EXP-ALL-A3", "SEC-A3"),
    ("VT-EXP-ALL-001", "EXP-ALL-A4-FRESH", "SEC-A4"),
    ("VT-EXP-ALL-001", "EXP-ALL-B1", "SEC-B1"),
    ("VT-EXP-ALL-001", "EXP-ALL-B2", "SEC-B2"),
    ("VT-EXP-ALL-001", "EXP-ALL-B3", "SEC-B3"),
    ("VT-EXP-ALL-001", "EXP-ALL-B4", "SEC-B4"),
    ("VT-EXP-ALL-001", "EXP-ALL-A4-STALE-OPEN", "SEC-A4"),
    ("VT-EXP-ROLE-001", "EXP-ROLE-A2", "SEC-A2"),
    ("VT-EXP-ROLE-001", "EXP-ROLE-B2", "SEC-B2"),
    ("VT-EXP-ROLE-001", "EXP-ROLE-A1", "SEC-A1"),
    ("VT-EXP-ROLE-001", "EXP-ROLE-A4", "SEC-A4"),
))
def test_dc004_exact_cases_are_determined_from_actual_scenario_sources(
    tmp_path: Path, test_id: str, case_id: str, section_id: str,
) -> None:
    h = harness(tmp_path / case_id)
    context = exploration_determination_context(
        h,
        test_id=test_id,
        case_id=case_id,
        section_id=section_id,
        command_base=40_000 + sum(ord(item) for item in case_id),
    )
    findings = evaluate(h, context, at=T0 + timedelta(seconds=62))
    assert {item.status for item in findings} == {
        CriterionFindingStatus.SATISFIED
    }, [
        (item.criterion_id, item.status.value, item.observed_value)
        for item in findings if item.status is not CriterionFindingStatus.SATISFIED
    ]


@pytest.mark.dc006
def test_every_compound_selector_family_exposes_changed_actual_facts() -> None:
    cases = (
        (
            "ScenarioRun.checkpoints + OperationalEvent.sequence",
            {"ScenarioRun.checkpoints": {}, "OperationalEvent.sequence": []}, (),
        ),
        (
            "IsolationProof.isolated + ActionProjection",
            {"IsolationProof.isolated": True, "ActionProjection": {}}, (),
        ),
        (
            "AlarmAdapter.acknowledgement + ScenarioSnapshot.state_revision + OperationalEvent.sequence",
            {"AlarmAdapter.acknowledgement": {"acknowledged_by": "Reviewer", "acknowledged_scenario_time": "2030-01-01T00:00:11Z"}, "ScenarioSnapshot.state_revision": 2, "OperationalEvent.sequence": []}, (),
        ),
        (
            "OperationalEventAdapter.events + ValidationEvidenceAdapter.records",
            {"OperationalEventAdapter.events": [{"event_id": "shared", "event_sequence": 1}], "ValidationEvidenceAdapter.records": [{"evidence_snapshot_id": "shared"}]}, (),
        ),
        (
            "IsolationProof.boundary_evidence[TS-01] + ActionProjection",
            {"IsolationProof.boundary_evidence[TS-01]": {"observed_state": "OPEN", "quality": "GOOD", "freshness": "STALE", "age_ms": 61_000, "evidence_state": "UNPROVEN", "reason_codes": ["FRESHNESS_STALE"]}, "ActionProjection": {"by_device": {"TS-01": {"available": False}}}},
            (SimpleNamespace(record_type="IsolationProof", canonical_payload={"isolated": False}),),
        ),
        (
            "ScenarioRun + ValidationExecution.provenance",
            {"ScenarioRun": {"run": {"scenario_run_id": "run", "configuration_id": "network-configuration-v1.0"}, "selected_fault_section_id": "SEC-A2", "fault_type": "DISTRIBUTION_SECTION_FAULT", "mode": "EXPLORATION"}, "ValidationExecution.provenance": {"scenario_run_id": "run", "evidence_class": "EXPLORATORY"}}, (),
        ),
        (
            "ActionProjection + CommandResult + DeviceState[TS-01]",
            {"ActionProjection": {"execute_restoration": {"available": False}}, "CommandResult": {"results": []}, "DeviceState[TS-01]": "OPEN"},
            (SimpleNamespace(record_type="RestorationAssessment", canonical_payload={"outcome": "PERMITTED", "candidate": {"tie_device_id": "TS-01"}}),),
        ),
        (
            "ScenarioSnapshot.before_after + CommandAvailability",
            {"ScenarioSnapshot.before_after": {"command_snapshots": [{"device_states": {"TS-01": "CLOSED"}, "new_event_types": ["RESTORATION_EXECUTED"]}]}, "CommandAvailability": {"execute_restoration": {"available": False}}}, (),
        ),
    )
    for selector, selected, records in cases:
        assert derive_combined_observation(selector, selected, records) == selected


@pytest.mark.dc006
def test_missing_command_and_assessment_lifecycle_remains_incomplete(
    tmp_path: Path,
) -> None:
    h = harness(tmp_path)
    initial = h.scenarios.initialise(InitialiseRunRequest(
        command_id=UUID(int=77_000), actor="Graduate Engineer",
        mode=ScenarioMode.EXPLORATION, configuration_version="1.1",
        fault_section_id="SEC-A2", scenario_time=T0,
    ))
    execution = h.validation.start_execution(
        "VT-EXP-ROLE-001", initial.snapshot.run.scenario_run_id,
        case_id="EXP-ROLE-A2",
    )
    context = h.determination.prepare_context(
        validation_attempt_id=execution.validation_attempt_id,
        scenario_run_id=initial.snapshot.run.scenario_run_id,
        validation_execution_id=execution.validation_execution_id,
        frozen_at=T0 + timedelta(seconds=1),
    )
    findings = evaluate(h, context)
    assert CriterionFindingStatus.NOT_EVALUATED in {
        item.status for item in findings
    }
    with pytest.raises(DeterminationBoundaryError, match="incomplete"):
        h.determination.finalise_result(
            context.determination_context_id,
            finalised_at=T0 + timedelta(seconds=2),
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
