"""I4 formal restoration assessment, binding and simulated execution gates."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from ot_demo.application.scenario_coordinator import ScenarioCoordinator
from ot_demo.domain.enums import (
    NetworkStateLabel,
    OperationalEventType,
    PermissiveStatus,
    RestorationCriterion,
    RestorationOutcome,
    ScenarioCommandType,
    ScenarioMode,
    ScenarioRunStatus,
    SwitchState,
    TelemetryQuality,
)
from ot_demo.infrastructure.build_identity import (
    ApplicationBuildManifest,
    BuildIdentityPayload,
)
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ot_demo.infrastructure.scenario_repository import ScenarioRepository
from ot_demo.modules.restoration import RestorationService
from ot_demo.modules.scenario.models import InitialiseRunRequest, ScenarioCommandRequest


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "app/backend/ot_demo/infrastructure/migrations"
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


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def service(tmp_path: Path, *, failure_hook=None) -> ScenarioCoordinator:
    return ScenarioCoordinator(
        ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS),
        JsonConfigurationLoader(ROOT / "config/network"),
        application_build_manifest=MANIFEST,
        failure_hook=failure_hook,
    )


def request(
    number: int,
    run_id: UUID,
    revision: int,
    kind: ScenarioCommandType,
    time: datetime,
    *,
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
        command_type=kind,
        scenario_time=time,
        target_entity_id=target,
        requested_state=state,
        alarm_id=alarm_id,
        assessment_id=assessment_id,
    )


def n3(coordinator: ScenarioCoordinator):
    initial = coordinator.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=1),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
        )
    )
    run_id = initial.snapshot.run.scenario_run_id
    fault = coordinator.execute(
        run_id,
        request(2, run_id, 0, ScenarioCommandType.INITIATE_FAULT, at(10)),
    )
    coordinator.execute(
        run_id,
        request(
            3,
            run_id,
            1,
            ScenarioCommandType.ACKNOWLEDGE_ALARM,
            at(11),
            alarm_id=fault.snapshot.alarms[0].alarm_id,
        ),
    )
    coordinator.execute(
        run_id,
        request(
            4,
            run_id,
            1,
            ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            at(20),
            target="SW-A12",
            state=SwitchState.OPEN,
        ),
    )
    coordinator.execute(
        run_id,
        request(
            5,
            run_id,
            2,
            ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            at(30),
            target="SW-A23",
            state=SwitchState.OPEN,
        ),
    )
    result = coordinator.execute(
        run_id,
        request(
            6,
            run_id,
            3,
            ScenarioCommandType.RESTORE_NORMAL_SOURCE,
            at(40),
            target="BRK-A",
            state=SwitchState.CLOSED,
        ),
    )
    return run_id, result


def assess(coordinator: ScenarioCoordinator, run_id: UUID, time: datetime, number=7):
    return coordinator.execute(
        run_id,
        request(
            number,
            run_id,
            4,
            ScenarioCommandType.ASSESS_RESTORATION,
            time,
        ),
    )


@pytest.mark.i4
def test_formal_n4_assessment_matches_approved_answer_key_without_revision(
    tmp_path: Path,
) -> None:
    coordinator = service(tmp_path)
    run_id, before = n3(coordinator)
    result = assess(coordinator, run_id, at(50))
    assessment = result.snapshot.restoration_assessments[-1]

    assert result.accepted is True
    assert result.prior_revision == result.current_revision == 4
    assert result.snapshot.run.network_state_label is NetworkStateLabel.N4
    assert result.snapshot.outage == before.snapshot.outage
    assert assessment.outcome is RestorationOutcome.PERMITTED
    assert assessment.candidate is not None
    assert assessment.candidate.proposed_section_ids == ("SEC-A3", "SEC-A4")
    assert assessment.candidate.transferable_load_kw == 1500
    assert assessment.candidate.proposed_restored_customer_count == 450
    assert assessment.calculation is not None
    assert assessment.calculation.existing_supplied_load_kw == 4200
    assert assessment.calculation.resulting_load_kw == 5700
    assert assessment.calculation.feeder_capacity_kw == 6000
    assert assessment.calculation.resulting_loading_percent == 95
    assert assessment.calculation.capacity_pass is True
    assert len(assessment.telemetry_evidence) == 9
    assert {item.status for item in assessment.permissives} == {
        PermissiveStatus.PASS
    }
    assert [event.event_type for event in result.snapshot.events[-2:]] == [
        OperationalEventType.RESTORATION_CANDIDATE_IDENTIFIED,
        OperationalEventType.RESTORATION_ASSESSED,
    ]
    assert all(event.assessment_id == assessment.assessment_id for event in result.snapshot.events[-2:])


@pytest.mark.i4
def test_formal_n5_executes_only_bound_permitted_assessment_through_i2(
    tmp_path: Path,
) -> None:
    coordinator = service(tmp_path)
    run_id, _ = n3(coordinator)
    n4 = assess(coordinator, run_id, at(50))
    assessment = n4.snapshot.restoration_assessments[-1]
    n5 = coordinator.execute(
        run_id,
        request(
            8,
            run_id,
            4,
            ScenarioCommandType.EXECUTE_RESTORATION,
            at(55),
            assessment_id=assessment.assessment_id,
        ),
    )

    assert n5.accepted is True
    assert n5.snapshot.run.network_state_label is NetworkStateLabel.N5
    assert n5.snapshot.run.status is ScenarioRunStatus.RUN_COMPLETE
    assert n5.snapshot.run.state_revision == 5
    assert n5.snapshot.outage.affected_customer_count == 220
    assert n5.snapshot.outage.restored_customer_delta == 450
    sections = {item.section_id: item for item in n5.snapshot.topology.sections}
    assert sections["SEC-A2"].faulted and not sections["SEC-A2"].energised
    assert sections["SEC-A3"].source_feeder_ids == ("FDR-B",)
    assert sections["SEC-A4"].source_feeder_ids == ("FDR-B",)
    assert n5.snapshot.topology.radiality_status.value == "RADIAL"
    tie = next(item for item in n5.snapshot.telemetry if item.entity_id == "TS-01")
    assert tie.value is SwitchState.CLOSED


@pytest.mark.i4
@pytest.mark.parametrize(
    ("assessment_time", "outcome"),
    [(at(60), RestorationOutcome.PERMITTED), (at(60.001), RestorationOutcome.BLOCKED)],
)
def test_restoration_uses_inclusive_telemetry_freshness_boundary(
    tmp_path: Path,
    assessment_time: datetime,
    outcome: RestorationOutcome,
) -> None:
    coordinator = service(tmp_path)
    run_id, _ = n3(coordinator)
    result = assess(coordinator, run_id, assessment_time)
    assert result.snapshot.restoration_assessments[-1].outcome is outcome


@pytest.mark.i4
def test_open_trustworthy_alternate_breaker_rejects_existing_candidate(
    tmp_path: Path,
) -> None:
    coordinator = service(tmp_path)
    run_id, _ = n3(coordinator)
    repository = ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS)
    with repository.transaction() as unit:
        point = next(item for item in unit.list_telemetry(run_id) if item.entity_id == "BRK-B")
        unit.put_telemetry(
            run_id,
            point.model_copy(
                update={
                    "value": SwitchState.OPEN,
                    "last_update_scenario_time": at(50),
                    "revision": 4,
                }
            ),
        )
    result = assess(coordinator, run_id, at(50))
    assessment = result.snapshot.restoration_assessments[-1]
    assert assessment.candidate is not None
    assert assessment.outcome is RestorationOutcome.REJECTED
    source = next(
        item
        for item in assessment.permissives
        if item.criterion is RestorationCriterion.ALTERNATE_SOURCE
    )
    assert source.status is PermissiveStatus.FAIL


@pytest.mark.i4
def test_untrustworthy_alternate_breaker_blocks_instead_of_rejecting_candidate(
    tmp_path: Path,
) -> None:
    coordinator = service(tmp_path)
    run_id, _ = n3(coordinator)
    repository = ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS)
    with repository.transaction() as unit:
        point = next(item for item in unit.list_telemetry(run_id) if item.entity_id == "BRK-B")
        unit.put_telemetry(
            run_id,
            point.model_copy(
                update={
                    "quality": TelemetryQuality.BAD,
                    "last_update_scenario_time": at(50),
                    "revision": 4,
                }
            ),
        )
    assessment = assess(coordinator, run_id, at(50)).snapshot.restoration_assessments[-1]
    assert assessment.candidate is not None
    assert assessment.outcome is RestorationOutcome.BLOCKED


@pytest.mark.i4
@pytest.mark.parametrize(
    ("quality", "timestamp"),
    [
        (TelemetryQuality.UNCERTAIN, at(50)),
        (TelemetryQuality.GOOD, at(50.001)),
    ],
)
def test_uncertain_or_future_required_evidence_blocks_restoration(
    tmp_path: Path,
    quality: TelemetryQuality,
    timestamp: datetime,
) -> None:
    coordinator = service(tmp_path)
    run_id, _ = n3(coordinator)
    repository = ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS)
    with repository.transaction() as unit:
        point = next(item for item in unit.list_telemetry(run_id) if item.entity_id == "BRK-B")
        unit.put_telemetry(
            run_id,
            point.model_copy(
                update={
                    "quality": quality,
                    "last_update_scenario_time": timestamp,
                    "revision": 4,
                }
            ),
        )
    assessment = assess(coordinator, run_id, at(50)).snapshot.restoration_assessments[-1]
    assert assessment.outcome is RestorationOutcome.BLOCKED


@pytest.mark.i4
def test_time_only_binding_change_invalidates_old_assessment_without_revision(
    tmp_path: Path,
) -> None:
    coordinator = service(tmp_path)
    run_id, _ = n3(coordinator)
    n4 = assess(coordinator, run_id, at(50))
    assessment = n4.snapshot.restoration_assessments[-1]
    result = coordinator.execute(
        run_id,
        request(
            8,
            run_id,
            4,
            ScenarioCommandType.EXECUTE_RESTORATION,
            at(61),
            assessment_id=assessment.assessment_id,
        ),
    )

    assert result.accepted is False
    assert result.reason_code == "RESTORATION_ASSESSMENT_INVALIDATED"
    assert result.snapshot.run.state_revision == 4
    assert result.snapshot.run.network_state_label is NetworkStateLabel.N4
    assert len(result.snapshot.restoration_assessments) == 1
    assert result.snapshot.restoration_invalidations[-1].assessment_id == assessment.assessment_id
    assert result.snapshot.events[-1].event_type is OperationalEventType.RESTORATION_ASSESSMENT_INVALIDATED
    execution = next(
        item
        for item in result.snapshot.allowed_actions
        if item.command_type is ScenarioCommandType.EXECUTE_RESTORATION
    )
    assert execution.available is False


@pytest.mark.i4
def test_capacity_boundary_is_exact_integer_arithmetic() -> None:
    passing = RestorationService.calculate_capacity(
        alternate_feeder_id="FDR-B",
        existing_load_kw=4500,
        transferable_load_kw=1500,
        capacity_kw=6000,
    )
    failing = RestorationService.calculate_capacity(
        alternate_feeder_id="FDR-B",
        existing_load_kw=4501,
        transferable_load_kw=1500,
        capacity_kw=6000,
    )
    assert passing.resulting_load_kw == 6000 and passing.capacity_pass
    assert failing.resulting_load_kw == 6001 and not failing.capacity_pass


@pytest.mark.i4
def test_restoration_execution_is_atomic_and_idempotent(tmp_path: Path) -> None:
    armed = False

    def fail(stage: str) -> None:
        if armed and stage == "AFTER_PRIMARY_MUTATION":
            raise RuntimeError("injected I4 failure")

    coordinator = service(tmp_path, failure_hook=fail)
    run_id, _ = n3(coordinator)
    n4 = assess(coordinator, run_id, at(50))
    assessment = n4.snapshot.restoration_assessments[-1]
    execution = request(
        8,
        run_id,
        4,
        ScenarioCommandType.EXECUTE_RESTORATION,
        at(55),
        assessment_id=assessment.assessment_id,
    )
    armed = True
    with pytest.raises(RuntimeError, match="injected I4 failure"):
        coordinator.execute(run_id, execution)
    rolled_back = coordinator.snapshot(run_id)
    assert rolled_back.run.network_state_label is NetworkStateLabel.N4
    assert rolled_back.run.state_revision == 4
    assert next(item for item in rolled_back.telemetry if item.entity_id == "TS-01").value is SwitchState.OPEN
    armed = False
    first = coordinator.execute(run_id, execution)
    duplicate = coordinator.execute(run_id, execution)
    assert duplicate == first
    assert first.snapshot.run.network_state_label is NetworkStateLabel.N5


@pytest.mark.i4
def test_repeated_controlled_runs_have_equal_restoration_engineering_outputs(
    tmp_path: Path,
) -> None:
    outputs = []
    for name in ("first", "repeat"):
        coordinator = service(tmp_path / name)
        run_id, _ = n3(coordinator)
        n4 = assess(coordinator, run_id, at(50))
        assessment = n4.snapshot.restoration_assessments[-1]
        n5 = coordinator.execute(
            run_id,
            request(
                8,
                run_id,
                4,
                ScenarioCommandType.EXECUTE_RESTORATION,
                at(55),
                assessment_id=assessment.assessment_id,
            ),
        )
        outputs.append(
            (
                assessment.candidate,
                assessment.telemetry_evidence,
                assessment.permissives,
                assessment.calculation,
                assessment.outcome,
                n5.snapshot.topology,
                n5.snapshot.outage,
            )
        )
    assert outputs[0] == outputs[1]
