"""I3 atomic formal N0-N3 scenario, command and reset conformance gates."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from ot_demo.api.main import create_app
from ot_demo.application.scenario_coordinator import (
    ScenarioCommandConflict,
    ScenarioCoordinator,
)
from ot_demo.domain.enums import (
    AlarmAcknowledgementState,
    NetworkStateLabel,
    OperationalEventType,
    ScenarioCommandType,
    ScenarioMode,
    ScenarioRunStatus,
    SwitchState,
)
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.infrastructure.scenario_repository import ScenarioRepository
from ot_demo.modules.scenario.models import (
    InitialiseRunRequest,
    ScenarioCommandRequest,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY_ROOT / "app/backend/ot_demo/infrastructure/migrations"
T0 = datetime(2030, 1, 1, tzinfo=timezone.utc)
BUILD_ID = "a" * 64


def at(seconds: int) -> datetime:
    return T0 + timedelta(seconds=seconds)


def coordinator(
    tmp_path: Path,
    *,
    failure_hook=None,
) -> ScenarioCoordinator:
    return ScenarioCoordinator(
        ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS),
        JsonConfigurationLoader(REPOSITORY_ROOT / "config/network"),
        failure_hook=failure_hook,
    )


def initialise(service: ScenarioCoordinator, command_number: int = 1):
    return service.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=command_number),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
            application_build_id=BUILD_ID,
        )
    )


def command(
    *,
    number: int,
    run_id: UUID,
    revision: int,
    command_type: ScenarioCommandType,
    scenario_time: datetime,
    target: str | None = None,
    state: SwitchState | None = None,
    alarm_id: UUID | None = None,
    actor: str = "Graduate Engineer",
) -> ScenarioCommandRequest:
    return ScenarioCommandRequest(
        command_id=UUID(int=number),
        scenario_run_id=run_id,
        actor=actor,
        expected_revision=revision,
        command_type=command_type,
        scenario_time=scenario_time,
        target_entity_id=target,
        requested_state=state,
        alarm_id=alarm_id,
    )


def execute_n0_n3(service: ScenarioCoordinator):
    n0 = initialise(service)
    run_id = n0.snapshot.run.scenario_run_id
    n1 = service.execute(
        run_id,
        command(
            number=2,
            run_id=run_id,
            revision=0,
            command_type=ScenarioCommandType.INITIATE_FAULT,
            scenario_time=at(10),
        ),
    )
    alarm_id = n1.snapshot.alarms[0].alarm_id
    acknowledged = service.execute(
        run_id,
        command(
            number=3,
            run_id=run_id,
            revision=1,
            command_type=ScenarioCommandType.ACKNOWLEDGE_ALARM,
            scenario_time=at(11),
            alarm_id=alarm_id,
        ),
    )
    isolation_one = service.execute(
        run_id,
        command(
            number=4,
            run_id=run_id,
            revision=1,
            command_type=ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            scenario_time=at(20),
            target="SW-A12",
            state=SwitchState.OPEN,
        ),
    )
    n2 = service.execute(
        run_id,
        command(
            number=5,
            run_id=run_id,
            revision=2,
            command_type=ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            scenario_time=at(30),
            target="SW-A23",
            state=SwitchState.OPEN,
        ),
    )
    n3 = service.execute(
        run_id,
        command(
            number=6,
            run_id=run_id,
            revision=3,
            command_type=ScenarioCommandType.RESTORE_NORMAL_SOURCE,
            scenario_time=at(40),
            target="BRK-A",
            state=SwitchState.CLOSED,
        ),
    )
    return n0, n1, acknowledged, isolation_one, n2, n3


@pytest.mark.i3
def test_approved_n0_n3_transactions_and_alarm_chronology(tmp_path: Path) -> None:
    service = coordinator(tmp_path)
    n0, n1, acknowledged, isolation_one, n2, n3 = execute_n0_n3(service)

    assert n0.snapshot.run.network_state_label is NetworkStateLabel.N0
    assert n0.snapshot.outage.affected_customer_count == 0
    assert n0.snapshot.run.state_revision == 0
    assert [event.event_sequence for event in n0.snapshot.events] == [1, 2, 3, 4]
    assert len({event.scenario_time for event in n0.snapshot.events}) == 1

    assert n1.snapshot.run.network_state_label is NetworkStateLabel.N1
    assert n1.snapshot.run.state_revision == 1
    assert n1.snapshot.outage.affected_customer_count == 850
    assert n1.snapshot.alarms[0].acknowledgement_state is (
        AlarmAcknowledgementState.UNACKNOWLEDGED
    )

    assert acknowledged.snapshot.run.state_revision == 1
    assert acknowledged.snapshot.run.network_state_label is NetworkStateLabel.N1
    assert acknowledged.snapshot.outage.affected_customer_count == 850
    assert acknowledged.snapshot.alarms[0].acknowledgement_state is (
        AlarmAcknowledgementState.ACKNOWLEDGED
    )

    assert isolation_one.snapshot.run.state_revision == 2
    assert isolation_one.snapshot.run.network_state_label is NetworkStateLabel.N1
    assert isolation_one.snapshot.outage.affected_customer_count == 850

    assert n2.snapshot.run.state_revision == 3
    assert n2.snapshot.run.network_state_label is NetworkStateLabel.N2
    assert n2.snapshot.topology.isolation_proof is not None
    assert n2.snapshot.topology.isolation_proof.isolated is True
    assert n2.snapshot.outage.affected_customer_count == 850

    assert n3.snapshot.run.state_revision == 4
    assert n3.snapshot.run.network_state_label is NetworkStateLabel.N3
    assert n3.snapshot.outage.affected_customer_count == 670
    assert n3.snapshot.outage.restored_customer_delta == 180
    sections = {item.section_id: item for item in n3.snapshot.topology.sections}
    assert sections["SEC-A1"].source_feeder_ids == ("FDR-A",)
    assert sections["SEC-A2"].faulted is True
    assert sections["SEC-A2"].energised is False

    assert [event.event_type for event in n3.snapshot.events] == [
        OperationalEventType.SCENARIO_INITIALISED,
        OperationalEventType.CONFIGURATION_SELECTED,
        OperationalEventType.TOPOLOGY_RECALCULATED,
        OperationalEventType.OUTAGE_UPDATED,
        OperationalEventType.FAULT_INITIATED,
        OperationalEventType.TELEMETRY_UPDATED,
        OperationalEventType.DEVICE_STATE_CHANGE,
        OperationalEventType.ALARM_GENERATED,
        OperationalEventType.TOPOLOGY_RECALCULATED,
        OperationalEventType.OUTAGE_UPDATED,
        OperationalEventType.ALARM_ACKNOWLEDGED,
        OperationalEventType.SWITCHING_ACTION,
        OperationalEventType.TELEMETRY_UPDATED,
        OperationalEventType.DEVICE_STATE_CHANGE,
        OperationalEventType.TOPOLOGY_RECALCULATED,
        OperationalEventType.OUTAGE_UPDATED,
        OperationalEventType.SWITCHING_ACTION,
        OperationalEventType.TELEMETRY_UPDATED,
        OperationalEventType.DEVICE_STATE_CHANGE,
        OperationalEventType.TOPOLOGY_RECALCULATED,
        OperationalEventType.OUTAGE_UPDATED,
        OperationalEventType.SWITCHING_ACTION,
        OperationalEventType.TELEMETRY_UPDATED,
        OperationalEventType.DEVICE_STATE_CHANGE,
        OperationalEventType.TOPOLOGY_RECALCULATED,
        OperationalEventType.OUTAGE_UPDATED,
    ]
    assert [event.event_sequence for event in n3.snapshot.events] == list(range(1, 27))
    assert all(
        event.event_type
        not in {
            "PASS",
            "FAIL",
            "DEFECT_RECORDED",
            "CORRECTION_APPROVED",
        }
        for event in n3.snapshot.events
    )


@pytest.mark.i3
def test_stale_revision_and_duplicate_command_leave_engineering_state_unchanged(
    tmp_path: Path,
) -> None:
    service = coordinator(tmp_path)
    n0 = initialise(service)
    run_id = n0.snapshot.run.scenario_run_id
    fault_request = command(
        number=2,
        run_id=run_id,
        revision=0,
        command_type=ScenarioCommandType.INITIATE_FAULT,
        scenario_time=at(10),
    )
    first = service.execute(run_id, fault_request)
    duplicate = service.execute(run_id, fault_request)

    assert duplicate == first
    assert len(service.events(run_id)) == 10

    stale_request = command(
        number=7,
        run_id=run_id,
        revision=0,
        command_type=ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
        scenario_time=at(20),
        target="SW-A12",
        state=SwitchState.OPEN,
    )
    stale = service.execute(run_id, stale_request)
    repeated_stale = service.execute(run_id, stale_request)
    current = service.snapshot(run_id)

    assert stale.accepted is False
    assert stale.reason_code == "STALE_EXPECTED_REVISION"
    assert repeated_stale == stale
    assert current.run.state_revision == 1
    assert current.run.network_state_label is NetworkStateLabel.N1
    assert len(current.events) == 10
    assert next(point for point in current.telemetry if point.entity_id == "SW-A12").value is (
        SwitchState.CLOSED
    )


@pytest.mark.i3
@pytest.mark.parametrize(("age_ms", "accepted"), [(60_000, True), (60_001, False)])
def test_isolation_action_uses_inclusive_freshness_boundary(
    tmp_path: Path,
    age_ms: int,
    accepted: bool,
) -> None:
    service = coordinator(tmp_path)
    run_id = initialise(service).snapshot.run.scenario_run_id
    service.execute(
        run_id,
        command(
            number=2,
            run_id=run_id,
            revision=0,
            command_type=ScenarioCommandType.INITIATE_FAULT,
            scenario_time=at(10),
        ),
    )
    result = service.execute(
        run_id,
        command(
            number=10,
            run_id=run_id,
            revision=1,
            command_type=ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            scenario_time=T0 + timedelta(milliseconds=age_ms),
            target="SW-A12",
            state=SwitchState.OPEN,
        ),
    )

    assert result.accepted is accepted
    assert result.current_revision == (2 if accepted else 1)
    if not accepted:
        assert result.reason_code == "ISOLATION_ACTION_UNAVAILABLE"
        assert "UNPROVEN" in result.reason
        assert len(result.snapshot.events) == 10


@pytest.mark.i3
def test_reused_command_id_with_different_content_is_rejected(tmp_path: Path) -> None:
    service = coordinator(tmp_path)
    run_id = initialise(service).snapshot.run.scenario_run_id
    accepted = command(
        number=2,
        run_id=run_id,
        revision=0,
        command_type=ScenarioCommandType.INITIATE_FAULT,
        scenario_time=at(10),
    )
    service.execute(run_id, accepted)
    changed = command(
        number=2,
        run_id=run_id,
        revision=0,
        command_type=ScenarioCommandType.INITIATE_FAULT,
        scenario_time=at(10),
        actor="Different Actor",
    )

    with pytest.raises(ScenarioCommandConflict, match="different request content"):
        service.execute(run_id, changed)
    assert len(service.events(run_id)) == 10

    wrong_run = accepted.model_copy(update={"scenario_run_id": UUID(int=999)})
    with pytest.raises(ScenarioCommandConflict, match="run identity"):
        service.execute(run_id, wrong_run)
    assert len(service.events(run_id)) == 10


@pytest.mark.i3
def test_injected_failure_rolls_back_run_telemetry_alarm_event_and_command(
    tmp_path: Path,
) -> None:
    armed = False

    def fail_after_mutation(stage: str) -> None:
        if armed and stage == "AFTER_PRIMARY_MUTATION":
            raise RuntimeError("injected transaction failure")

    service = coordinator(tmp_path, failure_hook=fail_after_mutation)
    n0 = initialise(service)
    run_id = n0.snapshot.run.scenario_run_id
    request = command(
        number=2,
        run_id=run_id,
        revision=0,
        command_type=ScenarioCommandType.INITIATE_FAULT,
        scenario_time=at(10),
    )
    armed = True
    with pytest.raises(RuntimeError, match="injected transaction failure"):
        service.execute(run_id, request)
    rolled_back = service.snapshot(run_id)

    assert rolled_back.run.state_revision == 0
    assert rolled_back.run.network_state_label is NetworkStateLabel.N0
    assert rolled_back.alarms == ()
    assert len(rolled_back.events) == 4
    assert next(point for point in rolled_back.telemetry if point.entity_id == "BRK-A").value is (
        SwitchState.CLOSED
    )

    armed = False
    retry = service.execute(run_id, request)
    assert retry.accepted is True
    assert retry.snapshot.run.state_revision == 1


@pytest.mark.i3
def test_reset_creates_new_run_and_repeat_is_deterministic(tmp_path: Path) -> None:
    service = coordinator(tmp_path)
    n0 = initialise(service)
    old_run_id = n0.snapshot.run.scenario_run_id
    first_fault = service.execute(
        old_run_id,
        command(
            number=2,
            run_id=old_run_id,
            revision=0,
            command_type=ScenarioCommandType.INITIATE_FAULT,
            scenario_time=at(10),
        ),
    )
    reset = service.execute(
        old_run_id,
        command(
            number=8,
            run_id=old_run_id,
            revision=1,
            command_type=ScenarioCommandType.RESET_RUN,
            scenario_time=at(60),
        ),
    )
    new_run_id = reset.snapshot.run.scenario_run_id

    assert new_run_id != old_run_id
    assert reset.snapshot.run.state_revision == 0
    assert reset.snapshot.run.network_state_label is NetworkStateLabel.N0
    assert reset.snapshot.run.scenario_time == T0
    assert reset.snapshot.events[0].event_sequence == 1
    assert len(reset.snapshot.events) == 4
    old = service.snapshot(old_run_id)
    assert old.run.status is ScenarioRunStatus.CLOSED
    assert old.events[-1].event_type is OperationalEventType.SCENARIO_RESET
    assert [event.event_sequence for event in old.events] == list(range(1, 12))

    repeated_fault = service.execute(
        new_run_id,
        command(
            number=9,
            run_id=new_run_id,
            revision=0,
            command_type=ScenarioCommandType.INITIATE_FAULT,
            scenario_time=at(10),
        ),
    )
    assert repeated_fault.snapshot.topology.model_dump(mode="json") == (
        first_fault.snapshot.topology.model_dump(mode="json")
    )
    assert repeated_fault.snapshot.outage.model_dump(mode="json") == (
        first_fault.snapshot.outage.model_dump(mode="json")
    )
    first_canonical = [
        (
            event.event_sequence,
            event.scenario_time,
            event.state_revision,
            event.source,
            event.event_type,
            event.affected_entity_id,
            event.previous_value,
            event.new_value,
        )
        for event in first_fault.snapshot.events
    ]
    repeated_canonical = [
        (
            event.event_sequence,
            event.scenario_time,
            event.state_revision,
            event.source,
            event.event_type,
            event.affected_entity_id,
            event.previous_value,
            event.new_value,
        )
        for event in repeated_fault.snapshot.events
    ]
    assert repeated_canonical == first_canonical


@pytest.mark.i3
def test_api_factory_exposes_only_the_i3_run_query_and_command_foundations(
    tmp_path: Path,
) -> None:
    application = create_app(coordinator(tmp_path))
    paths = set(application.openapi()["paths"])

    assert paths == {
        "/api/v1/runs",
        "/api/v1/runs/{scenario_run_id}/commands",
        "/api/v1/runs/{scenario_run_id}/snapshot",
        "/api/v1/runs/{scenario_run_id}/events",
    }
    assert all(
        token not in path
        for path in paths
        for token in ("restoration", "validation", "defect", "exploration")
    )
