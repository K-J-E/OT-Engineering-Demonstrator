"""I8 corrected-v1.1 Exploration Mode and immutable evidence-package gates."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
from zipfile import ZipFile

import pytest

from ot_demo.application.scenario_coordinator import (
    ScenarioBoundaryError,
    ScenarioCoordinator,
)
from ot_demo.application.investigation_service import InvestigationService
from ot_demo.domain.enums import (
    BoundaryProofStatus,
    EvidenceClass,
    RestorationOutcome,
    ScenarioCommandType,
    ScenarioMode,
    ScenarioRunStatus,
    SwitchState,
    TelemetryQuality,
    ValidationVerdict,
    SuspensionLifecyclePosition,
    ValidationAttemptStatus,
    ValidationSuspensionCondition,
    CompositeConstituentSourceKind,
    SuspensionEvaluationType,
)
from ot_demo.infrastructure.build_identity import (
    ApplicationBuildManifest,
    BuildIdentityPayload,
)
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.infrastructure.evidence_package_repository import EvidencePackageRepository
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from ot_demo.infrastructure.investigation_repository import InvestigationRepository
from ot_demo.infrastructure.scenario_repository import ScenarioRepository
from ot_demo.infrastructure.validation_repository import (
    ValidationRecordNotFound,
    ValidationRepository,
)
from ot_demo.modules.evidence_export.service import EvidenceExportService
from ot_demo.modules.scenario.models import InitialiseRunRequest, ScenarioCommandRequest
from ot_demo.modules.validation.catalogue import ValidationCatalogueLoader
from ot_demo.modules.validation.service import ValidationBoundaryError, ValidationService
from ot_demo.modules.validation.assurance import (
    ControlledArtifact, ControlledConflictReview, ControlledDesignQuestion,
    ControlledEngineeringRegistry, ControlledSourceAssertion, ControlledTimeReview,
    EngineeringAssuranceRegistryData, IdentityResolutionAuthority,
    IntegrityVerificationAuthority, RuntimeTimeAuthority,
)


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "app/backend/ot_demo/infrastructure/migrations"
CONFIGURATIONS = ROOT / "config/network"
CATALOGUE = ROOT / "validation/test-definitions/catalogue.json"
T0 = datetime(2030, 1, 1, tzinfo=timezone.utc)
IDENTITY = BuildIdentityPayload(
    git_commit="8" * 40,
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


def at_milliseconds(milliseconds: int) -> datetime:
    return T0 + timedelta(milliseconds=milliseconds)


def scenario(tmp_path: Path, name: str = "scenario") -> ScenarioCoordinator:
    return ScenarioCoordinator(
        ScenarioRepository(tmp_path / f"{name}.sqlite3", MIGRATIONS),
        JsonConfigurationLoader(CONFIGURATIONS),
        application_build_manifest=MANIFEST,
    )


def initialise_exploration(
    service: ScenarioCoordinator,
    section_id: str,
    command_number: int = 1,
):
    return service.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=command_number),
            actor="Graduate Engineer",
            mode=ScenarioMode.EXPLORATION,
            configuration_version="1.1",
            fault_section_id=section_id,
            scenario_time=T0,
        )
    )


def request(
    *,
    number: int,
    run_id: UUID,
    revision: int,
    command_type: ScenarioCommandType,
    scenario_time: datetime,
    target: str | None = None,
    state: SwitchState | None = None,
    alarm_id: UUID | None = None,
    assessment_id: UUID | None = None,
) -> ScenarioCommandRequest:
    return ScenarioCommandRequest(
        command_id=UUID(int=number),
        scenario_run_id=run_id,
        actor="Graduate Engineer",
        expected_revision=revision,
        command_type=command_type,
        scenario_time=scenario_time,
        target_entity_id=target,
        requested_state=state,
        alarm_id=alarm_id,
        assessment_id=assessment_id,
    )


def execute_available(
    service: ScenarioCoordinator,
    run_id: UUID,
    command_type: ScenarioCommandType,
    number: int,
    scenario_time: datetime,
):
    snapshot = service.snapshot(run_id)
    action = next(
        item
        for item in snapshot.allowed_actions
        if item.command_type is command_type and item.available
    )
    return service.execute(
        run_id,
        request(
            number=number,
            run_id=run_id,
            revision=snapshot.run.state_revision,
            command_type=command_type,
            scenario_time=scenario_time,
            target=action.target_entity_id,
            state=action.requested_state,
            alarm_id=action.alarm_id,
            assessment_id=action.assessment_id,
        ),
    )


def run_to_assessment(service: ScenarioCoordinator, section_id: str):
    initial = initialise_exploration(service, section_id)
    run_id = initial.snapshot.run.scenario_run_id
    execute_available(service, run_id, ScenarioCommandType.INITIATE_FAULT, 2, at(10))
    operation_number = 3
    isolation_time = 20
    while any(
        item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
        and item.available
        for item in service.snapshot(run_id).allowed_actions
    ):
        execute_available(
            service,
            run_id,
            ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            operation_number,
            at(isolation_time),
        )
        operation_number += 1
        isolation_time += 10
    if any(
        item.command_type is ScenarioCommandType.RESTORE_NORMAL_SOURCE
        and item.available
        for item in service.snapshot(run_id).allowed_actions
    ):
        execute_available(
            service,
            run_id,
            ScenarioCommandType.RESTORE_NORMAL_SOURCE,
            operation_number,
            at(40),
        )
        operation_number += 1
    assessed = execute_available(
        service,
        run_id,
        ScenarioCommandType.ASSESS_RESTORATION,
        operation_number,
        at(50),
    )
    return run_id, assessed


@pytest.mark.i8
def test_all_eight_sections_use_v11_transient_selection_and_generic_incidence(
    tmp_path: Path,
) -> None:
    expected = {
        "SEC-A1": ("FDR-A", "BRK-A", {"BRK-A", "SW-A12"}),
        "SEC-A2": ("FDR-A", "BRK-A", {"SW-A12", "SW-A23"}),
        "SEC-A3": ("FDR-A", "BRK-A", {"SW-A23", "SW-A34"}),
        "SEC-A4": ("FDR-A", "BRK-A", {"SW-A34", "TS-01"}),
        "SEC-B1": ("FDR-B", "BRK-B", {"BRK-B", "SW-B12"}),
        "SEC-B2": ("FDR-B", "BRK-B", {"SW-B12", "SW-B23"}),
        "SEC-B3": ("FDR-B", "BRK-B", {"SW-B23", "SW-B34"}),
        "SEC-B4": ("FDR-B", "BRK-B", {"SW-B34", "TS-01"}),
    }
    canonical_before = (ROOT / "config/network/v1.1/network.json").read_bytes()
    for index, (section_id, (feeder_id, breaker_id, boundaries)) in enumerate(
        expected.items(), start=1
    ):
        service = scenario(tmp_path, f"scenario-{index}")
        initial = initialise_exploration(service, section_id)
        assert initial.snapshot.run.mode is ScenarioMode.EXPLORATION
        assert initial.snapshot.run.evidence_class is EvidenceClass.EXPLORATORY
        assert initial.snapshot.run.configuration_version == "1.1"
        assert initial.snapshot.run.fault_section_id == section_id
        fault = execute_available(
            service,
            initial.snapshot.run.scenario_run_id,
            ScenarioCommandType.INITIATE_FAULT,
            100 + index,
            at(10),
        )
        proof = fault.snapshot.topology.isolation_proof
        assert proof is not None
        assert set(proof.incident_boundary_device_ids) == boundaries
        alarm = fault.snapshot.alarms[0]
        assert alarm.entity_id == breaker_id
        assert next(
            point for point in fault.snapshot.telemetry if point.entity_id == breaker_id
        ).value is SwitchState.OPEN
        section = next(
            item for item in fault.snapshot.topology.sections if item.section_id == section_id
        )
        assert section.faulted
        configured_feeder = next(
            item.feeder_id
            for item in JsonConfigurationLoader(CONFIGURATIONS)
            .load("v1.1")
            .data.sections
            if item.entity_id == section_id
        )
        assert configured_feeder == feeder_id
    assert (ROOT / "config/network/v1.1/network.json").read_bytes() == canonical_before


@pytest.mark.i8
def test_sec_a4_trustworthy_and_untrustworthy_open_tie_follow_dc003(
    tmp_path: Path,
) -> None:
    fresh_service = scenario(tmp_path, "fresh")
    fresh_run = initialise_exploration(fresh_service, "SEC-A4").snapshot.run.scenario_run_id
    fresh = execute_available(
        fresh_service, fresh_run, ScenarioCommandType.INITIATE_FAULT, 2, at(10)
    )
    fresh_proof = fresh.snapshot.topology.isolation_proof
    assert fresh_proof is not None
    tie = next(
        item for item in fresh_proof.boundary_evaluations if item.boundary_device_id == "TS-01"
    )
    assert tie.proof_status is BoundaryProofStatus.PROVEN_OPEN
    assert not any(
        item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
        and item.target_entity_id == "TS-01"
        and item.available
        for item in fresh.snapshot.allowed_actions
    )
    assert any(
        item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
        and item.target_entity_id == "SW-A34"
        and item.available
        for item in fresh.snapshot.allowed_actions
    )

    stale_service = scenario(tmp_path, "stale")
    stale_run = initialise_exploration(stale_service, "SEC-A4").snapshot.run.scenario_run_id
    fault = execute_available(
        stale_service, stale_run, ScenarioCommandType.INITIATE_FAULT, 3, at(10)
    )
    stale = stale_service.execute(
        stale_run,
        request(
            number=4,
            run_id=stale_run,
            revision=1,
            command_type=ScenarioCommandType.ACKNOWLEDGE_ALARM,
            scenario_time=at(61),
            alarm_id=fault.snapshot.alarms[0].alarm_id,
        ),
    )
    stale_proof = stale.snapshot.topology.isolation_proof
    assert stale_proof is not None and not stale_proof.isolated
    stale_tie = next(
        item for item in stale_proof.boundary_evaluations if item.boundary_device_id == "TS-01"
    )
    assert stale_tie.observed_state is SwitchState.OPEN
    assert stale_tie.proof_status is BoundaryProofStatus.UNPROVEN
    assert not any(
        item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
        and item.target_entity_id == "TS-01"
        and item.available
        for item in stale.snapshot.allowed_actions
    )


@pytest.mark.i8
@pytest.mark.parametrize(
    ("unproven_boundary", "proven_closed_boundary"),
    [
        ("SW-A12", "SW-A23"),
        ("SW-A23", "SW-A12"),
    ],
)
def test_exploration_boundary_action_eligibility_is_independent_per_incident_boundary(
    tmp_path: Path,
    unproven_boundary: str,
    proven_closed_boundary: str,
) -> None:
    service = scenario(tmp_path, f"qa040-{unproven_boundary}")
    run_id = initialise_exploration(service, "SEC-A2").snapshot.run.scenario_run_id
    fault = execute_available(
        service, run_id, ScenarioCommandType.INITIATE_FAULT, 2, at(10)
    )
    repository = ScenarioRepository(
        tmp_path / f"qa040-{unproven_boundary}.sqlite3", MIGRATIONS
    )
    with repository.transaction() as unit:
        points = {
            item.entity_id: item for item in unit.list_telemetry(run_id)
        }
        unit.put_telemetry(
            run_id,
            points[unproven_boundary].model_copy(
                update={
                    "quality": TelemetryQuality.BAD,
                    "last_update_scenario_time": at(10),
                }
            ),
        )
        unit.put_telemetry(
            run_id,
            points[proven_closed_boundary].model_copy(
                update={
                    "quality": TelemetryQuality.GOOD,
                    "last_update_scenario_time": at(10),
                }
            ),
        )

    asymmetric = service.snapshot(run_id)
    proof = asymmetric.topology.isolation_proof
    assert proof is not None and not proof.isolated
    proof_by_boundary = {
        item.boundary_device_id: item for item in proof.boundary_evaluations
    }
    assert (
        proof_by_boundary[unproven_boundary].proof_status
        is BoundaryProofStatus.UNPROVEN
    )
    assert (
        proof_by_boundary[proven_closed_boundary].proof_status
        is BoundaryProofStatus.PROVEN_CLOSED
    )
    actions = {
        item.target_entity_id: item
        for item in asymmetric.allowed_actions
        if item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
    }
    assert not actions[unproven_boundary].available
    assert "UNPROVEN" in actions[unproven_boundary].reason
    assert actions[proven_closed_boundary].available

    operated = service.execute(
        run_id,
        request(
            number=3,
            run_id=run_id,
            revision=fault.snapshot.run.state_revision,
            command_type=ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            scenario_time=at(20),
            target=proven_closed_boundary,
            state=SwitchState.OPEN,
        ),
    )
    assert operated.accepted
    recalculated = operated.snapshot.topology.isolation_proof
    assert recalculated is not None and not recalculated.isolated
    recalculated_by_boundary = {
        item.boundary_device_id: item
        for item in recalculated.boundary_evaluations
    }
    assert (
        recalculated_by_boundary[proven_closed_boundary].proof_status
        is BoundaryProofStatus.PROVEN_OPEN
    )
    assert (
        recalculated_by_boundary[unproven_boundary].proof_status
        is BoundaryProofStatus.UNPROVEN
    )
    recalculated_actions = {
        item.target_entity_id: item
        for item in operated.snapshot.allowed_actions
        if item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
    }
    assert not recalculated_actions[proven_closed_boundary].available
    assert "already proven OPEN" in recalculated_actions[proven_closed_boundary].reason
    assert not recalculated_actions[unproven_boundary].available
    assert "UNPROVEN" in recalculated_actions[unproven_boundary].reason


@pytest.mark.i8
@pytest.mark.parametrize(
    ("section_id", "outcome", "transfer_kw", "alternate", "result_kw", "capacity_kw", "percent"),
    [
        ("SEC-A2", RestorationOutcome.PERMITTED, 1500, "FDR-B", 5700, 6000, 95),
        ("SEC-B2", RestorationOutcome.PERMITTED, 1900, "FDR-A", 5100, 5500, 92.7),
        ("SEC-A1", RestorationOutcome.REJECTED, 2450, "FDR-B", 6650, 6000, 110.8),
        ("SEC-A4", RestorationOutcome.NO_CANDIDATE, None, None, None, None, None),
    ],
)
def test_representative_role_reversal_and_non_guaranteed_outcomes(
    tmp_path: Path,
    section_id: str,
    outcome: RestorationOutcome,
    transfer_kw: int | None,
    alternate: str | None,
    result_kw: int | None,
    capacity_kw: int | None,
    percent: float | None,
) -> None:
    _, assessed = run_to_assessment(scenario(tmp_path), section_id)
    assessment = assessed.snapshot.restoration_assessments[-1]
    assert assessment.outcome is outcome
    if outcome is RestorationOutcome.NO_CANDIDATE:
        assert assessment.candidate is None
        assert assessment.calculation is None
        return
    assert assessment.candidate is not None
    assert assessment.candidate.transferable_load_kw == transfer_kw
    assert assessment.candidate.alternate_feeder_id == alternate
    assert assessment.calculation is not None
    assert assessment.calculation.resulting_load_kw == result_kw
    assert assessment.calculation.feeder_capacity_kw == capacity_kw
    assert float(assessment.calculation.resulting_loading_percent) == percent
    if section_id == "SEC-B2":
        assert assessment.candidate.affected_feeder_id == "FDR-B"
        assert assessment.candidate.alternate_feeder_id == "FDR-A"
        assert assessment.candidate.proposed_section_ids == ("SEC-B3", "SEC-B4")


@pytest.mark.i8
def test_equivalent_exploration_runs_have_new_identity_and_repeatable_engineering(
    tmp_path: Path,
) -> None:
    first_run_id, first = run_to_assessment(
        scenario(tmp_path, "repeat-one"), "SEC-B2"
    )
    second_run_id, second = run_to_assessment(
        scenario(tmp_path, "repeat-two"), "SEC-B2"
    )

    assert first_run_id != second_run_id
    first_assessment = first.snapshot.restoration_assessments[-1]
    second_assessment = second.snapshot.restoration_assessments[-1]
    assert first_assessment.assessment_id != second_assessment.assessment_id
    assert first_assessment.outcome is second_assessment.outcome
    assert first_assessment.candidate is not None
    assert second_assessment.candidate is not None
    assert (
        first_assessment.candidate.affected_feeder_id,
        first_assessment.candidate.alternate_feeder_id,
        first_assessment.candidate.proposed_section_ids,
        first_assessment.candidate.transferable_load_kw,
        first_assessment.calculation,
    ) == (
        second_assessment.candidate.affected_feeder_id,
        second_assessment.candidate.alternate_feeder_id,
        second_assessment.candidate.proposed_section_ids,
        second_assessment.candidate.transferable_load_kw,
        second_assessment.calculation,
    )
    assert first.snapshot.topology.sections == second.snapshot.topology.sections
    assert first.snapshot.outage.de_energised_section_ids == (
        second.snapshot.outage.de_energised_section_ids
    )
    assert first.snapshot.outage.affected_customer_count == (
        second.snapshot.outage.affected_customer_count
    )


@pytest.mark.i8
def test_formal_and_exploratory_execution_classes_cannot_cross(
    tmp_path: Path,
) -> None:
    service = scenario(tmp_path)
    run = initialise_exploration(service, "SEC-B2").snapshot.run
    validation = ValidationService(
        ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        ValidationCatalogueLoader(CATALOGUE),
        service,
        application_build_manifest=MANIFEST,
    )
    exploratory = validation.start_execution(
        "VT-EXP-ROLE-001", run.scenario_run_id, case_id="EXP-ROLE-B2"
    )
    assert exploratory.evidence_class is EvidenceClass.EXPLORATORY
    with pytest.raises(ValidationBoundaryError, match="evidence class"):
        validation.start_execution("VT-FML-N0-N5-001", run.scenario_run_id)

    with pytest.raises(ScenarioBoundaryError, match="v1.1"):
        scenario(tmp_path, "defective-exploration").initialise(
            InitialiseRunRequest(
                command_id=UUID(int=99),
                actor="Graduate Engineer",
                mode=ScenarioMode.EXPLORATION,
                configuration_version="1.0",
                fault_section_id="SEC-B2",
                scenario_time=T0,
            )
        )


@pytest.mark.i8
def test_exploration_selection_is_required_and_starts_a_separate_preserved_run(
    tmp_path: Path,
) -> None:
    service = scenario(tmp_path)
    formal = service.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=1),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
        )
    ).snapshot.run

    exploration = service.initialise_next_run(
        InitialiseRunRequest(
            command_id=UUID(int=2),
            actor="Graduate Engineer",
            mode=ScenarioMode.EXPLORATION,
            configuration_version="1.1",
            fault_section_id="SEC-B2",
            scenario_time=T0,
        )
    ).snapshot.run

    assert exploration.scenario_run_id != formal.scenario_run_id
    assert exploration.mode is ScenarioMode.EXPLORATION
    assert exploration.evidence_class is EvidenceClass.EXPLORATORY
    assert exploration.fault_section_id == "SEC-B2"
    preserved_formal = service.run_context(formal.scenario_run_id)
    assert preserved_formal.status is ScenarioRunStatus.CLOSED
    assert preserved_formal.mode is ScenarioMode.FORMAL
    assert preserved_formal.evidence_class is EvidenceClass.FORMAL
    assert preserved_formal.fault_section_id == "SEC-A2"

    for selected in (None, "SEC-Z9"):
        isolated_service = scenario(tmp_path, f"invalid-{selected}")
        with pytest.raises(ScenarioBoundaryError, match="exploration"):
            isolated_service.initialise(
                InitialiseRunRequest(
                    command_id=UUID(int=3),
                    actor="Graduate Engineer",
                    mode=ScenarioMode.EXPLORATION,
                    configuration_version="1.1",
                    fault_section_id=selected,
                    scenario_time=T0,
                )
            )


def export_service(
    tmp_path: Path,
    scenarios: ScenarioCoordinator,
) -> tuple[ValidationService, EvidenceExportService]:
    validation_repository = ValidationRepository(
        tmp_path / "validation.sqlite3", MIGRATIONS
    )
    catalogue = ValidationCatalogueLoader(CATALOGUE)
    validation = ValidationService(
        validation_repository,
        catalogue,
        scenarios,
        application_build_manifest=MANIFEST,
    )
    export = EvidenceExportService(
        EvidencePackageRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        validation_repository,
        InvestigationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        scenarios,
        JsonConfigurationLoader(CONFIGURATIONS),
        catalogue,
        application_build_manifest=MANIFEST,
        output_directory=tmp_path / "evidence/exports",
    )
    return validation, export


@pytest.mark.i8
def test_exploratory_export_is_new_self_contained_and_independently_hash_verified(
    tmp_path: Path,
) -> None:
    scenarios = scenario(tmp_path)
    validation, export = export_service(tmp_path, scenarios)
    initial = initialise_exploration(scenarios, "SEC-B2")
    source_run_id = initial.snapshot.run.scenario_run_id
    execution = validation.start_execution(
        "VT-EXP-ROLE-001", source_run_id, case_id="EXP-ROLE-B2"
    )
    _, assessed = run_to_assessment_on_existing(scenarios, source_run_id)
    evidence = validation.capture_checkpoint(
        execution.validation_execution_id, "CONTROLLED_RESULT"
    )
    reset = scenarios.execute(
        source_run_id,
        request(
            number=90,
            run_id=source_run_id,
            revision=assessed.snapshot.run.state_revision,
            command_type=ScenarioCommandType.RESET_RUN,
            scenario_time=at(60),
        ),
    )
    assert reset.snapshot.run.scenario_run_id != source_run_id
    assert scenarios.run_context(source_run_id).status is ScenarioRunStatus.CLOSED

    first = export.generate(execution.validation_execution_id)
    second = export.generate(execution.validation_execution_id)
    assert first.package_id != second.package_id
    assert first.archive_path != second.archive_path
    assert first.evidence_class is EvidenceClass.EXPLORATORY
    assert first.evidence_snapshot_ids == (evidence.evidence_snapshot_id,)
    first_path = tmp_path / first.archive_path
    second_path = tmp_path / second.archive_path
    assert first_path.is_file() and second_path.is_file()
    assert sha256_file(first_path) == first.archive_sha256
    assert first_path.read_bytes() != second_path.read_bytes()

    with ZipFile(first_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["evidence_class"] == "EXPLORATORY"
        assert manifest["evidence_notice"] == "NOT FORMAL VALIDATION EVIDENCE"
        assert manifest["source_validation_execution_id"] == str(
            execution.validation_execution_id
        )
        assert manifest["source_scenario_run_id"] == str(source_run_id)
        assert manifest["source_application_build_id"] == MANIFEST.application_build_id
        assert len(manifest["files"]) >= 14
        for entry in manifest["files"]:
            payload = archive.read(entry["path"])
            assert len(payload) == entry["byte_size"]
            assert sha256_bytes(payload) == entry["sha256"]
        assert sha256_bytes(archive.read("manifest.json")) == first.manifest_sha256
        report = archive.read("report.html").decode()
        readme = archive.read("README.txt").decode()
        assert "NOT FORMAL VALIDATION EVIDENCE" in report
        assert "NOT FORMAL VALIDATION EVIDENCE" in readme
        assert str(source_run_id) in report
        assert "figures/network-evidence.svg" in archive.namelist()
        assert f"records/evidence-snapshots/{evidence.evidence_snapshot_id}.json" in archive.namelist()

    database_path = tmp_path / "validation.sqlite3"
    with sqlite3.connect(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE evidence_packages SET archive_path = ? WHERE package_id = ?",
                ("evidence/exports/replaced.zip", first.package_id),
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM evidence_packages WHERE package_id = ?",
                (first.package_id,),
            )
        connection.rollback()
        assert connection.execute(
            "SELECT COUNT(*) FROM evidence_packages WHERE package_id IN (?, ?)",
            (first.package_id, second.package_id),
        ).fetchone()[0] == 2


def run_to_assessment_on_existing(
    service: ScenarioCoordinator,
    run_id: UUID,
):
    execute_available(service, run_id, ScenarioCommandType.INITIATE_FAULT, 20, at(10))
    number = 21
    seconds = 20
    while any(
        item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
        and item.available
        for item in service.snapshot(run_id).allowed_actions
    ):
        execute_available(
            service,
            run_id,
            ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            number,
            at(seconds),
        )
        number += 1
        seconds += 10
    if any(
        item.command_type is ScenarioCommandType.RESTORE_NORMAL_SOURCE
        and item.available
        for item in service.snapshot(run_id).allowed_actions
    ):
        execute_available(
            service,
            run_id,
            ScenarioCommandType.RESTORE_NORMAL_SOURCE,
            number,
            at(40),
        )
        number += 1
    assessed = execute_available(
        service,
        run_id,
        ScenarioCommandType.ASSESS_RESTORATION,
        number,
        at(50),
    )
    return run_id, assessed


@pytest.mark.i8
def test_formal_i7_chain_export_preserves_fail_correction_pass_and_active_regression(
    tmp_path: Path,
) -> None:
    loader = JsonConfigurationLoader(CONFIGURATIONS)
    scenarios = scenario(tmp_path)
    validation_repository = ValidationRepository(
        tmp_path / "validation.sqlite3", MIGRATIONS
    )
    catalogue = ValidationCatalogueLoader(CATALOGUE)
    validation = ValidationService(
        validation_repository,
        catalogue,
        scenarios,
        application_build_manifest=MANIFEST,
    )
    investigation_repository = InvestigationRepository(
        tmp_path / "validation.sqlite3", MIGRATIONS
    )
    investigation = InvestigationService(
        investigation_repository,
        loader,
        scenarios,
        validation,
        application_build_manifest=MANIFEST,
    )
    chain = investigation.start_failure("Graduate Engineer")
    failure_id = chain.original_failure.execution.validation_execution_id
    investigation.record_defect(
        failure_id,
        "Independent Reviewer",
        InvestigationService.REVIEW_STEP_IDS,
    )
    investigation.record_correction(failure_id, "Independent Reviewer")
    chain = investigation.run_direct_repeat(failure_id, "Graduate Engineer")
    assert chain.direct_repeat is not None
    direct_id = chain.direct_repeat.execution.validation_execution_id
    chain = investigation.run_regression(failure_id, "Graduate Engineer")
    assert chain.regression is not None
    assert chain.regression.execution.verdict is None

    export = EvidenceExportService(
        EvidencePackageRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        validation_repository,
        investigation_repository,
        scenarios,
        loader,
        catalogue,
        application_build_manifest=MANIFEST,
        output_directory=tmp_path / "evidence/exports",
    )
    package = export.generate(direct_id)
    assert package.evidence_class is EvidenceClass.FORMAL
    with ZipFile(tmp_path / package.archive_path) as archive:
        chain_record = json.loads(archive.read("records/investigation-chain.json"))
        executions = {
            item["execution"]["validation_execution_id"]: item
            for item in chain_record["executions"]
        }
        assert len(executions) == 3
        failure = executions[str(failure_id)]["execution"]
        repeat = executions[str(direct_id)]["execution"]
        regression = executions[
            str(chain.regression.execution.validation_execution_id)
        ]["execution"]
        assert failure["configuration_version"] == "1.0"
        assert failure["verdict"] == "FAIL"
        assert failure["observed_result"]["affected_customer_count"] == 400
        assert repeat["configuration_version"] == "1.1"
        assert repeat["verdict"] == "PASS"
        assert repeat["observed_result"]["affected_customer_count"] == 850
        assert regression["status"] == "ACTIVE"
        assert regression["verdict"] is None
        assert len(executions[str(chain.regression.execution.validation_execution_id)]["evidence_snapshots"]) == 6
        assert chain_record["defect"]["defect_id"] == "DEF-001"
        assert chain_record["correction"]["correction_id"] == "COR-001"
        assert len(chain_record["repeat_links"]) == 2


def execute_dc004_case(
    scenarios: ScenarioCoordinator,
    validation: ValidationService,
    *,
    test_id: str,
    case_id: str,
    section_id: str,
    command_base: int,
    assess_role: bool = True,
    stale_age_ms: int = 60_001,
):
    initial = scenarios.initialise_next_run(
        InitialiseRunRequest(
            command_id=UUID(int=command_base),
            actor="Graduate Engineer",
            mode=ScenarioMode.EXPLORATION,
            configuration_version="1.1",
            fault_section_id=section_id,
            scenario_time=T0,
        )
    )
    run_id = initial.snapshot.run.scenario_run_id
    execution = validation.start_execution(test_id, run_id, case_id=case_id)
    fault = execute_available(
        scenarios, run_id, ScenarioCommandType.INITIATE_FAULT, command_base + 1, at(10)
    )
    if case_id == "EXP-ALL-A4-STALE-OPEN":
        scenarios.execute(
            run_id,
            request(
                number=command_base + 2,
                run_id=run_id,
                revision=fault.snapshot.run.state_revision,
                command_type=ScenarioCommandType.ACKNOWLEDGE_ALARM,
                scenario_time=at_milliseconds(stale_age_ms),
                alarm_id=fault.snapshot.alarms[0].alarm_id,
            ),
        )
    if test_id == "VT-EXP-ROLE-001" and assess_role:
        number = command_base + 2
        seconds = 20
        while any(
            item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
            and item.available
            for item in scenarios.snapshot(run_id).allowed_actions
        ):
            execute_available(
                scenarios,
                run_id,
                ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
                number,
                at(seconds),
            )
            number += 1
            seconds += 10
        if any(
            item.command_type is ScenarioCommandType.RESTORE_NORMAL_SOURCE
            and item.available
            for item in scenarios.snapshot(run_id).allowed_actions
        ):
            execute_available(
                scenarios,
                run_id,
                ScenarioCommandType.RESTORE_NORMAL_SOURCE,
                number,
                at(40),
            )
            number += 1
        execute_available(
            scenarios,
            run_id,
            ScenarioCommandType.ASSESS_RESTORATION,
            number,
            at(50),
        )
    validation.capture_checkpoint(execution.validation_execution_id, "CONTROLLED_RESULT")
    return validation.finalise_execution(
        execution.validation_execution_id, "CONTROLLED_RESULT"
    )


@pytest.mark.i8
def test_qa041_exact_stale_age_is_compared_and_61000_ms_substitution_fails(
    tmp_path: Path,
) -> None:
    scenarios = scenario(tmp_path, "qa041-exact-age")
    validation = ValidationService(
        ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        ValidationCatalogueLoader(CATALOGUE),
        scenarios,
        application_build_manifest=MANIFEST,
    )
    exact = execute_dc004_case(
        scenarios,
        validation,
        test_id="VT-EXP-ALL-001",
        case_id="EXP-ALL-A4-STALE-OPEN",
        section_id="SEC-A4",
        command_base=9000,
    )
    assert exact.verdict is ValidationVerdict.PASS
    assert exact.observed_result is not None
    exact_boundary = exact.observed_result["boundary_evidence"]["TS-01"]
    assert exact_boundary == {
        "observed_value": "OPEN",
        "quality": "GOOD",
        "freshness": "STALE",
        "age_ms": 60_001,
        "proof_status": "UNPROVEN",
        "open_action_eligible": False,
        "reason_codes": ["FRESHNESS_STALE"],
    }
    substituted = execute_dc004_case(
        scenarios,
        validation,
        test_id="VT-EXP-ALL-001",
        case_id="EXP-ALL-A4-STALE-OPEN",
        section_id="SEC-A4",
        command_base=9100,
        stale_age_ms=61_000,
    )
    assert substituted.verdict is ValidationVerdict.FAIL
    mismatches = [item for item in substituted.calculations["comparisons"] if not item["match"]]
    assert mismatches == [
        {
            "field": "boundary_evidence.TS-01.age_ms",
            "expected": 60_001,
            "observed": 61_000,
            "match": False,
        }
    ]
    boundary_at_limit = execute_dc004_case(
        scenarios,
        validation,
        test_id="VT-EXP-ALL-001",
        case_id="EXP-ALL-A4-STALE-OPEN",
        section_id="SEC-A4",
        command_base=9200,
        stale_age_ms=60_000,
    )
    limit_evidence = boundary_at_limit.observed_result["boundary_evidence"]["TS-01"]
    assert limit_evidence["age_ms"] == 60_000
    assert limit_evidence["freshness"] == "FRESH"
    assert boundary_at_limit.verdict is ValidationVerdict.FAIL


def assurance_registry() -> ControlledEngineeringRegistry:
    sources = (
        ControlledSourceAssertion(assertion_id="SRC-VP", source_id="VP", path="01-engineering-source-documents/OT Project Validation Plan.docx", version="1.2", sha256=sha256_file(ROOT / "01-engineering-source-documents/OT Project Validation Plan.docx"), location="Section 20"),
        ControlledSourceAssertion(assertion_id="SRC-DD", source_id="DD", path="01-engineering-source-documents/OT Project Demonstrator Design.docx", version="0.4", sha256=sha256_file(ROOT / "01-engineering-source-documents/OT Project Demonstrator Design.docx"), location="Section 37"),
    )
    return ControlledEngineeringRegistry(EngineeringAssuranceRegistryData(
        authority="test-only controlled assurance fixture",
        source_assertions=sources,
        design_questions=(ControlledDesignQuestion(record_id="DQ-TEST-OPEN", status="OPEN", test_id="VT-EXP-ROLE-001", case_id="EXP-ROLE-A2", field_id="comparison_expected_values", source_assertion_ids=("SRC-VP",), review_record_id="TEST-REVIEW"),),
        conflict_reviews=(ControlledConflictReview(record_id="CR-TEST-OPEN", status="UNRESOLVED", test_id="VT-EXP-ALL-001", case_id="EXP-ALL-A1", field_id="expected_customer_impact", source_assertion_ids=("SRC-VP", "SRC-DD"), review_record_id="TEST-REVIEW"),),
        time_reviews=(ControlledTimeReview(record_id="TR-TEST-OPEN", status="OPEN", test_id="VT-EXP-ROLE-001", case_id="EXP-ROLE-A2", step_reference="pre-entry-clock", source_assertion_ids=("SRC-VP",), review_record_id="TEST-REVIEW"),),
    ), ROOT)


@pytest.mark.i8
def test_dc005_exact_conditions_authority_immutability_and_composite_union(
    tmp_path: Path,
) -> None:
    scenarios = scenario(tmp_path, "dc005")
    repository = ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS)
    validation = ValidationService(
        repository,
        ValidationCatalogueLoader(CATALOGUE),
        scenarios,
        application_build_manifest=MANIFEST,
        engineering_registry=assurance_registry(),
    )
    assert {item.value for item in ValidationSuspensionCondition} == {
        "VSC-001", "VSC-002", "VSC-003", "VSC-004", "VSC-005"
    }
    cases = ("EXP-ROLE-A2", "EXP-ROLE-B2", "EXP-ROLE-A1", "EXP-ROLE-A4")
    records = []
    for index, case_id in enumerate(cases):
        target, attempt = validation.create_target_selection(
            "VT-EXP-ROLE-001", case_id=case_id, created_at=at(2000 + index),
            requested_fixture_identity="unknown-fixture",
        )
        record = validation.evaluate_suspension(
            attempt.validation_attempt_id,
            trusted_target_selection_id=target.target_selection_id,
            evaluation_type=SuspensionEvaluationType.IDENTITY_RESOLUTION,
            lifecycle_position=SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY,
            reference_id="fixture", field_id=None, source_assertion_ids=(),
            proposer_actor_id=None, reviewer_actor_id=None,
            finalised_at=at(2100 + index),
        )
        assert record.condition_id.value == "VSC-003"
        assert record.reason_code == "BLOCKED-TEST/VSC-003/PRE_EXECUTION_ENTRY"
        assert record.scenario_run_id is None
        assert record.validation_execution_id is None
        assert repository.get_attempt(attempt.validation_attempt_id).status is ValidationAttemptStatus.SUSPENDED
        records.append(record)

    # The remaining stable condition is independently classifiable under its exact contract.
    target, attempt = validation.create_target_selection(
        "VT-EXP-ALL-001", case_id="EXP-ALL-A1", created_at=at(2200)
    )
    inconsistent = validation.evaluate_suspension(
        attempt.validation_attempt_id,
        trusted_target_selection_id=target.target_selection_id,
        evaluation_type=SuspensionEvaluationType.BASELINE_CONFLICT,
        lifecycle_position=SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY,
        reference_id="CR-TEST-OPEN", field_id="expected_customer_impact",
        source_assertion_ids=("SRC-VP", "SRC-DD"),
        proposer_actor_id="graduate-engineer",
        reviewer_actor_id="independent-reviewer",
        finalised_at=at(2201),
    )
    assert inconsistent.condition_id.value == "VSC-002"

    composite = validation.assemble_composite(
        "VT-EXP-ROLE-001",
        (),
        suspension_record_ids=tuple(item.suspension_record_id for item in records),
        created_at=at(2300),
    )
    assert composite.completeness.status.value == "COMPLETE"
    assert all(
        item.source_kind is CompositeConstituentSourceKind.SUSPENSION_RESULT
        for item in composite.constituent_links
    )
    final = validation.finalise_composite(composite.composite_result_id, finalised_at=at(2301))
    assert final.determination is ValidationVerdict.BLOCKED_TEST

    export = EvidenceExportService(
        EvidencePackageRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        repository,
        InvestigationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        scenarios,
        JsonConfigurationLoader(CONFIGURATIONS),
        ValidationCatalogueLoader(CATALOGUE),
        application_build_manifest=MANIFEST,
        output_directory=tmp_path / "evidence/exports",
    )
    package = export.generate_composite(final.composite_result_id)
    assert package.constituent_execution_ids == ()
    assert set(package.constituent_suspension_record_ids) == {
        item.suspension_record_id for item in records
    }
    with ZipFile(tmp_path / package.archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert set(manifest["constituent_suspension_record_ids"]) == {
            str(item.suspension_record_id) for item in records
        }
        for record in records:
            base = f"records/constituents/{record.suspension_record_id}"
            assert f"{base}/validation-suspension.json" in archive.namelist()
            assert f"{base}/validation-target-selection.json" in archive.namelist()
            assert f"{base}/validation-attempt.json" in archive.namelist()

    mixed_pass = tuple(
        execute_dc004_case(
            scenarios,
            validation,
            test_id="VT-EXP-ROLE-001",
            case_id=case_id,
            section_id=section_id,
            command_base=10000 + index * 100,
        )
        for index, (case_id, section_id) in enumerate(
            (("EXP-ROLE-A2", "SEC-A2"), ("EXP-ROLE-B2", "SEC-B2"), ("EXP-ROLE-A1", "SEC-A1"))
        )
    )
    mixed = validation.assemble_composite(
        "VT-EXP-ROLE-001",
        tuple(item.validation_execution_id for item in mixed_pass),
        suspension_record_ids=(records[3].suspension_record_id,),
        created_at=at(2400),
    )
    assert validation.finalise_composite(
        mixed.composite_result_id, finalised_at=at(2401)
    ).determination is ValidationVerdict.BLOCKED_TEST

    failed_b2 = execute_dc004_case(
        scenarios,
        validation,
        test_id="VT-EXP-ROLE-001",
        case_id="EXP-ROLE-B2",
        section_id="SEC-B2",
        command_base=11000,
        assess_role=False,
    )
    assert failed_b2.verdict is ValidationVerdict.FAIL
    fail_dominates = validation.assemble_composite(
        "VT-EXP-ROLE-001",
        (
            mixed_pass[0].validation_execution_id,
            failed_b2.validation_execution_id,
            mixed_pass[2].validation_execution_id,
        ),
        suspension_record_ids=(records[3].suspension_record_id,),
        created_at=at(2402),
    )
    assert validation.finalise_composite(
        fail_dominates.composite_result_id, finalised_at=at(2403)
    ).determination is ValidationVerdict.FAIL
    with pytest.raises(ValidationRecordNotFound):
        validation.assemble_composite(
            "VT-EXP-ROLE-001", (),
            suspension_record_ids=(UUID(int=55555),), created_at=at(2404)
        )

    with sqlite3.connect(tmp_path / "validation.sqlite3") as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE validation_suspension_records SET reason_code='changed' WHERE suspension_record_id=?",
                (str(records[0].suspension_record_id),),
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="terminal validation attempt"):
            connection.execute(
                "UPDATE validation_attempts SET status='ACTIVE' WHERE validation_attempt_id=?",
                (str(records[0].validation_attempt_id),),
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="cannot acquire evidence"):
            connection.execute(
                "INSERT INTO validation_suspension_evidence VALUES (?,?,?,?,?,?,?)",
                (str(UUID(int=9999)), str(records[0].suspension_record_id), "VSC-001", "LATE", "LATE", "3" * 64, "{}"),
            )


@pytest.mark.i8
def test_dc005_three_lifecycle_positions_and_missing_evidence_boundary(
    tmp_path: Path,
) -> None:
    scenarios = scenario(tmp_path, "dc005-lifecycle")
    repository = ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS)
    controlled_artifact = tmp_path / "controlled.json"
    controlled_artifact.write_text('{"status":"healthy"}\n', encoding="utf-8")
    validation = ValidationService(
        repository,
        ValidationCatalogueLoader(CATALOGUE),
        scenarios,
        application_build_manifest=MANIFEST,
        engineering_registry=assurance_registry(),
        integrity_authority=IntegrityVerificationAuthority((ControlledArtifact(
            artifact_reference="test-evidence", path=controlled_artifact,
            expected_sha256=sha256_file(controlled_artifact),
        ),)),
    )
    run2 = initialise_exploration(scenarios, "SEC-A2", 12000).snapshot.run
    execution = validation.start_execution(
        "VT-EXP-ROLE-001", run2.scenario_run_id, case_id="EXP-ROLE-A2"
    )
    in_progress = validation.evaluate_suspension(
        execution.validation_attempt_id,
        trusted_target_selection_id=execution.target_selection_id,
        evaluation_type=SuspensionEvaluationType.ENGINEERING_BEHAVIOUR,
        lifecycle_position=SuspensionLifecyclePosition.EXECUTION_IN_PROGRESS,
        reference_id="DQ-TEST-OPEN", field_id="comparison_expected_values",
        source_assertion_ids=("SRC-VP",),
        proposer_actor_id="graduate-engineer",
        reviewer_actor_id="independent-reviewer",
        scenario_run_id=run2.scenario_run_id,
        validation_execution_id=execution.validation_execution_id,
        finalised_at=at(2),
    )
    assert in_progress.validation_execution_id == execution.validation_execution_id
    assert repository.get_execution(execution.validation_execution_id).verdict is None

    run2 = scenarios.initialise_next_run(
        InitialiseRunRequest(
            command_id=UUID(int=12001), actor="Graduate Engineer",
            mode=ScenarioMode.EXPLORATION, configuration_version="1.1",
            fault_section_id="SEC-A2", scenario_time=T0,
        )
    ).snapshot.run
    execution = validation.start_execution(
        "VT-EXP-ROLE-001", run2.scenario_run_id, case_id="EXP-ROLE-A2"
    )
    validation.capture_checkpoint(execution.validation_execution_id, "CONTROLLED_RESULT")
    controlled_artifact.write_text('{"status":"tampered"}\n', encoding="utf-8")
    mid = validation.evaluate_suspension(
        execution.validation_attempt_id,
        trusted_target_selection_id=execution.target_selection_id,
        evaluation_type=SuspensionEvaluationType.INTEGRITY,
        lifecycle_position=SuspensionLifecyclePosition.EVIDENCE_FINALISATION,
        reference_id="test-evidence", field_id=None, source_assertion_ids=(),
        proposer_actor_id=None, reviewer_actor_id=None,
        scenario_run_id=run2.scenario_run_id,
        validation_execution_id=execution.validation_execution_id,
        finalised_at=at(3),
    )
    assert mid.validation_execution_id == execution.validation_execution_id
    with pytest.raises(ValidationBoundaryError, match="cannot capture"):
        validation.capture_checkpoint(execution.validation_execution_id, "CONTROLLED_RESULT")
    assert repository.get_execution(execution.validation_execution_id).verdict is None

    run3 = scenarios.initialise_next_run(
        InitialiseRunRequest(
            command_id=UUID(int=12002), actor="Graduate Engineer",
            mode=ScenarioMode.EXPLORATION, configuration_version="1.1",
            fault_section_id="SEC-A2", scenario_time=T0,
        )
    ).snapshot.run
    incomplete = validation.start_execution(
        "VT-EXP-ROLE-001", run3.scenario_run_id, case_id="EXP-ROLE-A2"
    )
    with pytest.raises(ValidationRecordNotFound, match="evidence checkpoint"):
        validation.finalise_execution(incomplete.validation_execution_id, "CONTROLLED_RESULT")
    assert repository.get_attempt(incomplete.validation_attempt_id).status is ValidationAttemptStatus.ACTIVE
    assert len(validation.list_suspensions()) == 2


@pytest.mark.i8
def test_qa043_qa044_backend_facts_and_controlled_record_resolution(tmp_path: Path) -> None:
    scenarios = scenario(tmp_path, "qa043-044")
    repository = ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS)
    artifact = tmp_path / "controlled.json"
    artifact.write_text('{"identity":"controlled"}\n', encoding="utf-8")
    expected_hash = sha256_file(artifact)
    validation = ValidationService(
        repository, ValidationCatalogueLoader(CATALOGUE), scenarios,
        application_build_manifest=MANIFEST,
        integrity_authority=IntegrityVerificationAuthority((ControlledArtifact(
            artifact_reference="controlled-fixture", path=artifact,
            expected_sha256=expected_hash,
        ),)),
        time_authority=RuntimeTimeAuthority({"runtime-clock": {"wall_clock_reference": "backend-observed-host-now"}}),
    )

    healthy_target, healthy_attempt = validation.create_target_selection(
        "VT-EXP-ROLE-001", case_id="EXP-ROLE-A2", created_at=at(3000)
    )
    with pytest.raises(ValidationBoundaryError, match="resolves uniquely"):
        validation.evaluate_suspension(
            healthy_attempt.validation_attempt_id,
            trusted_target_selection_id=healthy_target.target_selection_id,
            evaluation_type=SuspensionEvaluationType.IDENTITY_RESOLUTION,
            lifecycle_position=SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY,
            reference_id="fixture", field_id=None, source_assertion_ids=(),
            proposer_actor_id=None, reviewer_actor_id=None, finalised_at=at(3001),
        )
    with pytest.raises(ValidationBoundaryError, match="passed integrity"):
        validation.evaluate_suspension(
            healthy_attempt.validation_attempt_id,
            trusted_target_selection_id=healthy_target.target_selection_id,
            evaluation_type=SuspensionEvaluationType.INTEGRITY,
            lifecycle_position=SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY,
            reference_id="controlled-fixture", field_id=None, source_assertion_ids=(),
            proposer_actor_id=None, reviewer_actor_id=None, finalised_at=at(3001),
        )
    with pytest.raises(ValidationBoundaryError, match="does not exist"):
        validation.evaluate_suspension(
            healthy_attempt.validation_attempt_id,
            trusted_target_selection_id=healthy_target.target_selection_id,
            evaluation_type=SuspensionEvaluationType.ENGINEERING_BEHAVIOUR,
            lifecycle_position=SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY,
            reference_id="DQ-MADE-UP", field_id="anything", source_assertion_ids=(),
            proposer_actor_id="graduate-engineer", reviewer_actor_id="independent-reviewer",
            finalised_at=at(3001),
        )
    with pytest.raises(ValidationBoundaryError, match="not open"):
        validation.evaluate_suspension(
            healthy_attempt.validation_attempt_id,
            trusted_target_selection_id=healthy_target.target_selection_id,
            evaluation_type=SuspensionEvaluationType.ENGINEERING_BEHAVIOUR,
            lifecycle_position=SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY,
            reference_id="DQ-001", field_id="exploration_fault_isolation_action_derivation",
            source_assertion_ids=("SRC-NETWORK-MODEL-18", "SRC-DEMONSTRATOR-DESIGN-37"),
            proposer_actor_id="graduate-engineer", reviewer_actor_id="independent-reviewer",
            finalised_at=at(3001),
        )

    unknown_target, unknown_attempt = validation.create_target_selection(
        "VT-EXP-ROLE-001", case_id="EXP-ROLE-A2", created_at=at(3010),
        requested_fixture_identity="not-registered",
    )
    with pytest.raises(ValidationBoundaryError, match="cannot supply backend"):
        validation.evaluate_suspension(
            unknown_attempt.validation_attempt_id,
            trusted_target_selection_id=unknown_target.target_selection_id,
            evaluation_type=SuspensionEvaluationType.IDENTITY_RESOLUTION,
            lifecycle_position=SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY,
            reference_id="fixture", field_id=None, source_assertion_ids=(),
            proposer_actor_id="backend-integrity-monitor",
            reviewer_actor_id="backend-assurance-reviewer", finalised_at=at(3011),
        )
    identity_record = validation.evaluate_suspension(
        unknown_attempt.validation_attempt_id,
        trusted_target_selection_id=unknown_target.target_selection_id,
        evaluation_type=SuspensionEvaluationType.IDENTITY_RESOLUTION,
        lifecycle_position=SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY,
        reference_id="fixture", field_id=None, source_assertion_ids=(),
        proposer_actor_id=None, reviewer_actor_id=None, finalised_at=at(3011),
    )
    assert identity_record.evidence[0].failure_code == "UNKNOWN_IDENTITY"
    assert identity_record.authority.proposer_actor_id == "backend-integrity-monitor"
    missing_target = healthy_target.model_copy(update={
        "canonical_selection_payload": {**healthy_target.canonical_selection_payload, "requested_fixture_identity": None}
    })
    assert IdentityResolutionAuthority().evaluate(missing_target, "fixture")[0] == "MISSING_IDENTITY"
    ambiguous_target = healthy_target.model_copy(update={
        "canonical_selection_payload": {**healthy_target.canonical_selection_payload, "requested_fixture_identity": "duplicate"}
    })
    assert IdentityResolutionAuthority(("duplicate", "duplicate")).evaluate(ambiguous_target, "fixture")[0] == "AMBIGUOUS_IDENTITY"

    runtime_run = initialise_exploration(scenarios, "SEC-A2", 3050).snapshot.run
    runtime_execution = validation.start_execution(
        "VT-EXP-ROLE-001", runtime_run.scenario_run_id, case_id="EXP-ROLE-A2"
    )
    time_record = validation.evaluate_suspension(
        runtime_execution.validation_attempt_id,
        trusted_target_selection_id=runtime_execution.target_selection_id,
        evaluation_type=SuspensionEvaluationType.TIME_AUTHORITY,
        lifecycle_position=SuspensionLifecyclePosition.EXECUTION_IN_PROGRESS,
        reference_id="runtime-clock", field_id=None, source_assertion_ids=(),
        proposer_actor_id=None, reviewer_actor_id=None,
        scenario_run_id=runtime_run.scenario_run_id,
        validation_execution_id=runtime_execution.validation_execution_id,
        finalised_at=at(3051),
    )
    assert time_record.condition_id is ValidationSuspensionCondition.VSC_004
    assert time_record.authority.proposer_role == "BACKEND_ASSURANCE_PROPOSER"

    artifact.write_text('{"identity":"tampered"}\n', encoding="utf-8")
    tamper_target, tamper_attempt = validation.create_target_selection(
        "VT-EXP-ROLE-001", case_id="EXP-ROLE-B2", created_at=at(3020)
    )
    integrity_record = validation.evaluate_suspension(
        tamper_attempt.validation_attempt_id,
        trusted_target_selection_id=tamper_target.target_selection_id,
        evaluation_type=SuspensionEvaluationType.INTEGRITY,
        lifecycle_position=SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY,
        reference_id="controlled-fixture", field_id=None, source_assertion_ids=(),
        proposer_actor_id=None, reviewer_actor_id=None, finalised_at=at(3021),
    )
    assert integrity_record.evidence[0].failure_code == "HASH_MISMATCH"
    assert integrity_record.evidence[0].payload["evidence"]["observed_failure"] == sha256_file(artifact)

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{not-json}\n", encoding="utf-8")
    schema_authority = IntegrityVerificationAuthority((ControlledArtifact(
        artifact_reference="invalid-json", path=invalid_json,
        expected_sha256=sha256_file(invalid_json),
    ),))
    assert schema_authority.evaluate("invalid-json")[0] == "SCHEMA_INVALID"
    canonical_json = tmp_path / "canonical.json"
    canonical_json.write_text('{ "value": 1 }\n', encoding="utf-8")
    canonical_authority = IntegrityVerificationAuthority((ControlledArtifact(
        artifact_reference="canonical-json", path=canonical_json,
        expected_sha256=sha256_file(canonical_json), expected_canonical_sha256="0" * 64,
    ),))
    assert canonical_authority.evaluate("canonical-json")[0] == "CANONICAL_PAYLOAD_MISMATCH"
    unreadable_authority = IntegrityVerificationAuthority((ControlledArtifact(
        artifact_reference="missing", path=tmp_path / "not-present.json",
        expected_sha256="0" * 64,
    ),))
    assert unreadable_authority.evaluate("missing")[0] == "UNREADABLE"


@pytest.mark.i8
def test_dc004_exact_constituents_finalise_and_complete_campaigns_pass(
    tmp_path: Path,
) -> None:
    scenarios = scenario(tmp_path, "dc004-campaign")
    validation_repository = ValidationRepository(
        tmp_path / "validation.sqlite3", MIGRATIONS
    )
    validation = ValidationService(
        validation_repository,
        ValidationCatalogueLoader(CATALOGUE),
        scenarios,
        application_build_manifest=MANIFEST,
    )
    all_case_inputs = (
        ("EXP-ALL-A1", "SEC-A1"),
        ("EXP-ALL-A2", "SEC-A2"),
        ("EXP-ALL-A3", "SEC-A3"),
        ("EXP-ALL-A4-FRESH", "SEC-A4"),
        ("EXP-ALL-B1", "SEC-B1"),
        ("EXP-ALL-B2", "SEC-B2"),
        ("EXP-ALL-B3", "SEC-B3"),
        ("EXP-ALL-B4", "SEC-B4"),
        ("EXP-ALL-A4-STALE-OPEN", "SEC-A4"),
    )
    all_executions = tuple(
        execute_dc004_case(
            scenarios,
            validation,
            test_id="VT-EXP-ALL-001",
            case_id=case_id,
            section_id=section_id,
            command_base=1000 + index * 100,
        )
        for index, (case_id, section_id) in enumerate(all_case_inputs)
    )
    assert all(item.verdict is ValidationVerdict.PASS for item in all_executions), [
        (
            item.case_id,
            item.verdict,
            [row for row in item.calculations["comparisons"] if not row["match"]],
        )
        for item in all_executions
        if item.verdict is not ValidationVerdict.PASS
    ]
    incomplete = validation.assemble_composite(
        "VT-EXP-ALL-001",
        tuple(item.validation_execution_id for item in all_executions[:-1]),
        created_at=at(1000),
    )
    assert incomplete.completeness.status.value == "INCOMPLETE"
    assert incomplete.determination is None
    assert incomplete.completeness.missing_case_ids == (
        "EXP-ALL-A4-STALE-OPEN",
    )
    with pytest.raises(ValidationBoundaryError, match="incomplete"):
        validation.finalise_composite(incomplete.composite_result_id, finalised_at=at(1001))

    assembled_all = validation.assemble_composite(
        "VT-EXP-ALL-001",
        tuple(item.validation_execution_id for item in all_executions),
        created_at=at(1002),
    )
    final_all = validation.finalise_composite(
        assembled_all.composite_result_id, finalised_at=at(1003)
    )
    assert final_all.determination is ValidationVerdict.PASS
    assert len(final_all.constituent_links) == 9

    role_case_inputs = (
        ("EXP-ROLE-A2", "SEC-A2"),
        ("EXP-ROLE-B2", "SEC-B2"),
        ("EXP-ROLE-A1", "SEC-A1"),
        ("EXP-ROLE-A4", "SEC-A4"),
    )
    role_executions = tuple(
        execute_dc004_case(
            scenarios,
            validation,
            test_id="VT-EXP-ROLE-001",
            case_id=case_id,
            section_id=section_id,
            command_base=3000 + index * 100,
        )
        for index, (case_id, section_id) in enumerate(role_case_inputs)
    )
    assert all(item.verdict is ValidationVerdict.PASS for item in role_executions)
    assembled_role = validation.assemble_composite(
        "VT-EXP-ROLE-001",
        tuple(item.validation_execution_id for item in role_executions),
        created_at=at(1004),
    )
    final_role = validation.finalise_composite(
        assembled_role.composite_result_id, finalised_at=at(1005)
    )
    assert final_role.determination is ValidationVerdict.PASS
    assert len(final_role.constituent_links) == 4
    assert final_role.application_build_id == MANIFEST.application_build_id
    assert final_role.configuration_id == "network-configuration-v1.1"

    export = EvidenceExportService(
        EvidencePackageRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        validation_repository,
        InvestigationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        scenarios,
        JsonConfigurationLoader(CONFIGURATIONS),
        ValidationCatalogueLoader(CATALOGUE),
        application_build_manifest=MANIFEST,
        output_directory=tmp_path / "evidence/exports",
    )
    composite_package = export.generate_composite(final_role.composite_result_id)
    assert composite_package.evidence_class is EvidenceClass.EXPLORATORY
    assert set(composite_package.constituent_execution_ids) == {
        item.validation_execution_id for item in role_executions
    }
    with ZipFile(tmp_path / composite_package.archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["source_composite_result_id"] == str(
            final_role.composite_result_id
        )
        assert manifest["evidence_notice"] == "NOT FORMAL VALIDATION EVIDENCE"
        assert set(manifest["constituent_execution_ids"]) == {
            str(item.validation_execution_id) for item in role_executions
        }
        assert "records/composite-validation-result.json" in archive.namelist()
        for entry in manifest["files"]:
            assert sha256_bytes(archive.read(entry["path"])) == entry["sha256"]

    with sqlite3.connect(tmp_path / "validation.sqlite3") as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE composite_validation_results SET determination = 'FAIL' "
                "WHERE composite_result_id = ?",
                (str(final_role.composite_result_id),),
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "DELETE FROM composite_validation_constituents "
                "WHERE composite_result_id = ?",
                (str(final_role.composite_result_id),),
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="finalised composite"):
            connection.execute(
                "INSERT INTO composite_validation_constituents VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(final_role.composite_result_id),
                    "EXP-ROLE-LATE",
                    str(role_executions[0].validation_execution_id),
                    str(role_executions[0].scenario_run_id),
                    role_executions[0].case_definition_sha256,
                    role_executions[0].verdict.value,
                    "{}",
                ),
            )
        connection.rollback()

    unfinished_run = scenarios.initialise_next_run(
        InitialiseRunRequest(
            command_id=UUID(int=3900),
            actor="Graduate Engineer",
            mode=ScenarioMode.EXPLORATION,
            configuration_version="1.1",
            fault_section_id="SEC-A2",
            scenario_time=T0,
        )
    ).snapshot.run
    unfinished_execution = validation.start_execution(
        "VT-EXP-ROLE-001",
        unfinished_run.scenario_run_id,
        case_id="EXP-ROLE-A2",
    )
    unfinished_composite = validation.assemble_composite(
        "VT-EXP-ROLE-001",
        (unfinished_execution.validation_execution_id,),
        created_at=at(1007),
    )
    assert unfinished_composite.completeness.status.value == "INCOMPLETE"
    assert any(
        "Unfinished constituent cases" in item
        for item in unfinished_composite.completeness.reasons
    )
    assert unfinished_composite.determination is None

    with pytest.raises(ValidationBoundaryError, match="more than once"):
        validation.assemble_composite(
            "VT-EXP-ROLE-001",
            (
                role_executions[0].validation_execution_id,
                role_executions[0].validation_execution_id,
            ),
            created_at=at(1006),
        )


@pytest.mark.i8
def test_dc004_complete_mismatch_fails_and_aggregate_precedence_is_exact(
    tmp_path: Path,
) -> None:
    scenarios = scenario(tmp_path, "dc004-fail")
    validation = ValidationService(
        ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        ValidationCatalogueLoader(CATALOGUE),
        scenarios,
        application_build_manifest=MANIFEST,
    )
    case_inputs = (
        ("EXP-ROLE-A2", "SEC-A2", True),
        ("EXP-ROLE-B2", "SEC-B2", False),
        ("EXP-ROLE-A1", "SEC-A1", True),
        ("EXP-ROLE-A4", "SEC-A4", True),
    )
    executions = tuple(
        execute_dc004_case(
            scenarios,
            validation,
            test_id="VT-EXP-ROLE-001",
            case_id=case_id,
            section_id=section_id,
            command_base=5000 + index * 100,
            assess_role=assess,
        )
        for index, (case_id, section_id, assess) in enumerate(case_inputs)
    )
    assert [item.verdict for item in executions].count(ValidationVerdict.FAIL) == 1
    assembled = validation.assemble_composite(
        "VT-EXP-ROLE-001",
        tuple(item.validation_execution_id for item in executions),
        created_at=at(1100),
    )
    finalised = validation.finalise_composite(
        assembled.composite_result_id, finalised_at=at(1101)
    )
    assert finalised.determination is ValidationVerdict.FAIL
    assert ValidationService._aggregate_verdict(
        (ValidationVerdict.PASS, ValidationVerdict.BLOCKED_TEST)
    )[0] is ValidationVerdict.BLOCKED_TEST
    assert ValidationService._aggregate_verdict(
        (ValidationVerdict.FAIL, ValidationVerdict.BLOCKED_TEST)
    )[0] is ValidationVerdict.FAIL


@pytest.mark.i8
def test_dc004_historical_execution_is_resolved_exported_and_active_old_work_is_read_only(
    tmp_path: Path,
) -> None:
    scenarios = scenario(tmp_path, "dc004-history")
    repository = ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS)
    historical_catalogue = CATALOGUE.parent / "history/v1.0/catalogue.json"
    old_service = ValidationService(
        repository,
        ValidationCatalogueLoader(historical_catalogue),
        scenarios,
        application_build_manifest=MANIFEST,
    )
    first = scenarios.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=7000),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
        )
    )
    old_final = old_service.start_execution(
        "VT-TOP-DEF-001", first.snapshot.run.scenario_run_id
    )
    scenarios.execute(
        first.snapshot.run.scenario_run_id,
        request(
            number=7001,
            run_id=first.snapshot.run.scenario_run_id,
            revision=0,
            command_type=ScenarioCommandType.INITIATE_FAULT,
            scenario_time=at(10),
        ),
    )
    old_service.capture_checkpoint(old_final.validation_execution_id, "POST_TRIP")
    old_final = old_service.finalise_execution(
        old_final.validation_execution_id, "POST_TRIP"
    )
    second = scenarios.initialise_next_run(
        InitialiseRunRequest(
            command_id=UUID(int=7100),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
        )
    )
    old_active = old_service.start_execution(
        "VT-TOP-DEF-001", second.snapshot.run.scenario_run_id
    )

    promoted = ValidationService(
        repository,
        ValidationCatalogueLoader(CATALOGUE),
        scenarios,
        application_build_manifest=MANIFEST,
    )
    assert promoted.get_execution(old_final.validation_execution_id).execution == old_final
    with pytest.raises(ValidationBoundaryError, match="historical catalogue"):
        promoted.capture_checkpoint(old_active.validation_execution_id, "POST_TRIP")
    with pytest.raises(ValidationBoundaryError, match="historical catalogue"):
        promoted.finalise_execution(old_active.validation_execution_id, "POST_TRIP")

    export = EvidenceExportService(
        EvidencePackageRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        repository,
        InvestigationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        scenarios,
        JsonConfigurationLoader(CONFIGURATIONS),
        ValidationCatalogueLoader(CATALOGUE),
        application_build_manifest=MANIFEST,
        output_directory=tmp_path / "evidence/exports",
    )
    package = export.generate(old_final.validation_execution_id)
    assert package.source_catalogue_version == "1.0"
    assert package.source_catalogue_sha256 == (
        "e4b1fb616fb4f0605c19129f18746bfae48278ed35fbb971aac4f690fd32bcc1"
    )
    assert package.application_build_id == old_final.application_build_id
    assert package.generation_application_build_id == MANIFEST.application_build_id
    with ZipFile(tmp_path / package.archive_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        definition = json.loads(archive.read("records/test-definition.json"))
        assert manifest["source_catalogue_version"] == "1.0"
        assert manifest["catalogue_sha256"] == old_final.catalogue_sha256
        assert definition["catalogue_version"] == "1.0"
        assert definition["catalogue_sha256"] == old_final.catalogue_sha256

    third = scenarios.initialise_next_run(
        InitialiseRunRequest(
            command_id=UUID(int=7200),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
        )
    )
    new_execution = promoted.start_execution(
        "VT-TOP-DEF-001", third.snapshot.run.scenario_run_id
    )
    assert new_execution.catalogue_version == "1.1"
    assert new_execution.catalogue_sha256 != old_final.catalogue_sha256
