"""Atomic I3 command coordinator for the approved formal N0-N3 workflow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ..domain.enums import (
    AlarmAcknowledgementState,
    AlarmType,
    BoundaryProofStatus,
    EvidenceClass,
    FaultType,
    NetworkStateLabel,
    OperationalEventSource,
    OperationalEventType,
    ScenarioCommandType,
    ScenarioMode,
    ScenarioRunStatus,
    SwitchState,
    TelemetryQuality,
    WorkflowStage,
)
from ..infrastructure.build_identity import ApplicationBuildManifest
from ..infrastructure.configuration_loader import JsonConfigurationLoader
from ..infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ..infrastructure.scenario_repository import (
    ScenarioRecordNotFound,
    ScenarioRepository,
    ScenarioUnitOfWork,
)
from ..modules.configuration.models import LoadedConfiguration
from ..modules.events.models import OperationalEvent
from ..modules.outage import OutageResult, OutageService
from ..modules.scenario.definition import (
    FORMAL_N0_N3_DEFINITION,
    FormalScenarioDefinition,
)
from ..modules.scenario.models import (
    AllowedAction,
    CommandResult,
    InitialiseRunRequest,
    RunContext,
    ScenarioCommandRequest,
    ScenarioSnapshot,
)
from ..modules.telemetry.models import AlarmRecord, TelemetryPoint, TelemetryValidity
from ..modules.telemetry.service import TelemetryValidityService
from ..modules.topology import BoundaryObservation, TopologyInputs, TopologyResult, TopologyService


class ScenarioCommandConflict(ValueError):
    """Raised when a command identity is reused with different content."""


class ScenarioBoundaryError(ValueError):
    """Raised when a request attempts behaviour outside the I3 baseline."""


FailureHook = Callable[[str], None]


@dataclass(frozen=True)
class _EventSpec:
    source: OperationalEventSource
    event_type: OperationalEventType
    affected_entity_id: str | None
    description: str
    previous_value: str | None = None
    new_value: str | None = None
    alarm_id: UUID | None = None


class ScenarioCoordinator:
    """Coordinate state without taking topology or outage authority from I2."""

    def __init__(
        self,
        repository: ScenarioRepository,
        configuration_loader: JsonConfigurationLoader,
        *,
        application_build_manifest: ApplicationBuildManifest,
        definition: FormalScenarioDefinition = FORMAL_N0_N3_DEFINITION,
        failure_hook: FailureHook | None = None,
    ) -> None:
        self._repository = repository
        self._configuration_loader = configuration_loader
        self._application_build_manifest = application_build_manifest
        self._definition = definition
        self._failure_hook = failure_hook
        self._topology = TopologyService()
        self._outage = OutageService()
        self._telemetry_validity = TelemetryValidityService()

    def initialise(self, request: InitialiseRunRequest) -> CommandResult:
        request_sha = self._request_sha(request)
        with self._repository.transaction() as unit:
            duplicate = self._return_duplicate(unit, request.command_id, request_sha)
            if duplicate is not None:
                return duplicate
            if request.mode is not ScenarioMode.FORMAL:
                raise ScenarioBoundaryError(
                    "Exploration Mode orchestration is reserved for I8"
                )
            if unit.has_mutable_run():
                raise ScenarioBoundaryError(
                    "a mutable run already exists; use RESET_RUN to preserve history"
                )

            loaded = self._configuration_loader.load(
                f"v{request.configuration_version}"
            )
            self._validate_definition(loaded)
            run = self._new_run(
                loaded=loaded,
                scenario_time=request.scenario_time,
                application_build_id=(
                    self._application_build_manifest.application_build_id
                ),
            )
            unit.insert_run(run)
            telemetry = self._normal_telemetry(loaded, run)
            for point in telemetry:
                unit.put_telemetry(run.scenario_run_id, point)

            topology, outage, _ = self._derive(
                loaded,
                run,
                telemetry,
                previous_outage=None,
            )
            unit.insert_derived_snapshots(
                run.scenario_run_id,
                run.state_revision,
                topology,
                outage,
            )
            events = self._initial_events(
                unit,
                run,
                request.command_id,
                request.actor,
            )
            unit.insert_events(events)
            self._invoke_failure_hook("BEFORE_COMMIT")
            snapshot = self._assemble_snapshot(unit, run, loaded)
            result = CommandResult(
                command_id=request.command_id,
                accepted=True,
                reason_code="RUN_INITIALISED",
                reason="Controlled formal run initialised at N0.",
                prior_revision=0,
                current_revision=0,
                run_status=run.status,
                new_event_ids=tuple(event.event_id for event in events),
                snapshot=snapshot,
            )
            unit.insert_command_result(
                command_id=request.command_id,
                scenario_run_id=run.scenario_run_id,
                request_sha256=request_sha,
                result=result,
            )
            return result

    def execute(
        self,
        scenario_run_id: UUID,
        request: ScenarioCommandRequest,
    ) -> CommandResult:
        request_sha = self._request_sha(request)
        with self._repository.transaction() as unit:
            if request.scenario_run_id != scenario_run_id:
                raise ScenarioCommandConflict(
                    "command run identity does not match the requested run"
                )
            duplicate = self._return_duplicate(unit, request.command_id, request_sha)
            if duplicate is not None:
                return duplicate

            run = unit.get_run(scenario_run_id)
            loaded = self._configuration_loader.load(
                f"v{run.configuration_version}"
            )
            if request.expected_revision != run.state_revision:
                return self._reject(
                    unit,
                    run,
                    loaded,
                    request,
                    request_sha,
                    "STALE_EXPECTED_REVISION",
                    (
                        f"Requested revision {request.expected_revision} does not match "
                        f"current revision {run.state_revision}."
                    ),
                )
            if request.scenario_time < run.scenario_time:
                return self._reject(
                    unit,
                    run,
                    loaded,
                    request,
                    request_sha,
                    "SCENARIO_TIME_BEFORE_CURRENT",
                    "Controlled request time cannot move backwards within a run.",
                )
            if run.status is ScenarioRunStatus.CLOSED:
                return self._reject(
                    unit,
                    run,
                    loaded,
                    request,
                    request_sha,
                    "RUN_CLOSED",
                    "The preserved run is closed and cannot be mutated.",
                )

            if request.command_type is ScenarioCommandType.INITIATE_FAULT:
                return self._initiate_fault(
                    unit, run, loaded, request, request_sha
                )
            if request.command_type is ScenarioCommandType.ACKNOWLEDGE_ALARM:
                return self._acknowledge_alarm(
                    unit, run, loaded, request, request_sha
                )
            if request.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE:
                return self._operate_isolation_device(
                    unit, run, loaded, request, request_sha
                )
            if request.command_type is ScenarioCommandType.RESTORE_NORMAL_SOURCE:
                return self._restore_normal_source(
                    unit, run, loaded, request, request_sha
                )
            if request.command_type is ScenarioCommandType.RESET_RUN:
                return self._reset_run(unit, run, loaded, request, request_sha)
            raise AssertionError(f"unhandled command: {request.command_type}")

    def snapshot(self, scenario_run_id: UUID) -> ScenarioSnapshot:
        with self._repository.transaction() as unit:
            run = unit.get_run(scenario_run_id)
            loaded = self._configuration_loader.load(
                f"v{run.configuration_version}"
            )
            return self._assemble_snapshot(unit, run, loaded)

    def events(self, scenario_run_id: UUID) -> tuple[OperationalEvent, ...]:
        with self._repository.transaction() as unit:
            unit.get_run(scenario_run_id)
            return unit.list_events(scenario_run_id)

    def _initiate_fault(
        self,
        unit: ScenarioUnitOfWork,
        run: RunContext,
        loaded: LoadedConfiguration,
        request: ScenarioCommandRequest,
        request_sha: str,
    ) -> CommandResult:
        if run.network_state_label is not NetworkStateLabel.N0 or run.fault_active:
            return self._reject(
                unit,
                run,
                loaded,
                request,
                request_sha,
                "FAULT_INITIATION_UNAVAILABLE",
                "Fault initiation is available only from controlled N0.",
            )

        feeder, breaker_id = self._affected_feeder_and_breaker(loaded, run)
        points = self._telemetry_map(unit, run.scenario_run_id)
        previous = points[breaker_id]
        if previous.value is not SwitchState.CLOSED:
            return self._reject(
                unit,
                run,
                loaded,
                request,
                request_sha,
                "AFFECTED_BREAKER_NOT_CLOSED",
                "The defined protection transition requires a CLOSED affected breaker.",
            )

        next_revision = run.state_revision + 1
        changed_point = previous.model_copy(
            update={
                "value": SwitchState.OPEN,
                "quality": TelemetryQuality.GOOD,
                "last_update_scenario_time": request.scenario_time,
                "revision": next_revision,
            }
        )
        points[breaker_id] = changed_point
        alarm = AlarmRecord(
            alarm_id=uuid4(),
            scenario_run_id=run.scenario_run_id,
            entity_id=breaker_id,
            alarm_type=AlarmType.FEEDER_TRIP,
            active=True,
            acknowledgement_state=AlarmAcknowledgementState.UNACKNOWLEDGED,
            generated_scenario_time=request.scenario_time,
        )
        updated_run = run.model_copy(
            update={
                "scenario_time": request.scenario_time,
                "state_revision": next_revision,
                "workflow_stage": WorkflowStage.POST_FAULT,
                "network_state_label": NetworkStateLabel.N1,
                "status": ScenarioRunStatus.ACTIVE,
                "fault_active": True,
            }
        )
        unit.update_run(updated_run)
        unit.put_telemetry(run.scenario_run_id, changed_point)
        unit.insert_alarm(alarm)
        self._invoke_failure_hook("AFTER_PRIMARY_MUTATION")

        topology, outage, _ = self._derive(
            loaded,
            updated_run,
            tuple(points.values()),
            previous_outage=unit.get_outage_snapshot(
                run.scenario_run_id, run.state_revision
            ),
        )
        unit.insert_derived_snapshots(
            run.scenario_run_id, next_revision, topology, outage
        )
        specs = (
            _EventSpec(
                OperationalEventSource.SCENARIO_CONTROL,
                OperationalEventType.FAULT_INITIATED,
                run.fault_section_id,
                "The controlled abstract distribution-section fault became active.",
                previous_value="NOT_FAULTED",
                new_value="FAULTED",
            ),
            _EventSpec(
                OperationalEventSource.SCADA,
                OperationalEventType.TELEMETRY_UPDATED,
                breaker_id,
                "Affected feeder-breaker telemetry was refreshed by protection operation.",
                previous_value=previous.value.value,
                new_value=changed_point.value.value,
            ),
            _EventSpec(
                OperationalEventSource.SCADA,
                OperationalEventType.DEVICE_STATE_CHANGE,
                breaker_id,
                "Affected feeder breaker changed state following protection operation.",
                previous_value=previous.value.value,
                new_value=changed_point.value.value,
            ),
            _EventSpec(
                OperationalEventSource.SCADA,
                OperationalEventType.ALARM_GENERATED,
                breaker_id,
                f"Feeder-trip alarm generated for {feeder.entity_id}.",
                alarm_id=alarm.alarm_id,
            ),
            *self._derived_event_specs(topology, outage),
        )
        return self._complete_accepted(
            unit,
            prior_run=run,
            updated_run=updated_run,
            loaded=loaded,
            request=request,
            request_sha=request_sha,
            reason_code="FAULT_INITIATED",
            reason="Fault/protection transaction completed atomically at N1.",
            event_specs=specs,
        )

    def _acknowledge_alarm(
        self,
        unit: ScenarioUnitOfWork,
        run: RunContext,
        loaded: LoadedConfiguration,
        request: ScenarioCommandRequest,
        request_sha: str,
    ) -> CommandResult:
        alarms = {alarm.alarm_id: alarm for alarm in unit.list_alarms(run.scenario_run_id)}
        alarm = alarms.get(request.alarm_id)
        if (
            alarm is None
            or not alarm.active
            or alarm.acknowledgement_state
            is AlarmAcknowledgementState.ACKNOWLEDGED
        ):
            return self._reject(
                unit,
                run,
                loaded,
                request,
                request_sha,
                "ALARM_ACKNOWLEDGEMENT_UNAVAILABLE",
                "The alarm is absent, inactive or already acknowledged.",
            )

        updated_alarm = alarm.model_copy(
            update={
                "acknowledgement_state": AlarmAcknowledgementState.ACKNOWLEDGED,
                "acknowledged_scenario_time": request.scenario_time,
                "acknowledged_by": request.actor,
            }
        )
        updated_run = run.model_copy(update={"scenario_time": request.scenario_time})
        unit.update_alarm(updated_alarm)
        unit.update_run(updated_run)
        self._invoke_failure_hook("AFTER_PRIMARY_MUTATION")
        return self._complete_accepted(
            unit,
            prior_run=run,
            updated_run=updated_run,
            loaded=loaded,
            request=request,
            request_sha=request_sha,
            reason_code="ALARM_ACKNOWLEDGED",
            reason=(
                "Alarm acknowledgement recorded without changing topology revision."
            ),
            event_specs=(
                _EventSpec(
                    OperationalEventSource.OPERATOR,
                    OperationalEventType.ALARM_ACKNOWLEDGED,
                    alarm.entity_id,
                    "Active feeder-trip alarm acknowledged by the operator.",
                    previous_value=AlarmAcknowledgementState.UNACKNOWLEDGED.value,
                    new_value=AlarmAcknowledgementState.ACKNOWLEDGED.value,
                    alarm_id=alarm.alarm_id,
                ),
            ),
        )

    def _operate_isolation_device(
        self,
        unit: ScenarioUnitOfWork,
        run: RunContext,
        loaded: LoadedConfiguration,
        request: ScenarioCommandRequest,
        request_sha: str,
    ) -> CommandResult:
        gate_topology = self._gate_topology(unit, loaded, run, request.scenario_time)
        next_target, gate_reason = self._next_isolation_target(run, gate_topology)
        if (
            request.requested_state is not SwitchState.OPEN
            or request.target_entity_id != next_target
        ):
            return self._reject(
                unit,
                run,
                loaded,
                request,
                request_sha,
                "ISOLATION_ACTION_UNAVAILABLE",
                gate_reason,
            )

        points = self._telemetry_map(unit, run.scenario_run_id)
        previous = points[request.target_entity_id]
        next_revision = run.state_revision + 1
        changed_point = previous.model_copy(
            update={
                "value": SwitchState.OPEN,
                "quality": TelemetryQuality.GOOD,
                "last_update_scenario_time": request.scenario_time,
                "revision": next_revision,
            }
        )
        points[request.target_entity_id] = changed_point
        provisional_run = run.model_copy(
            update={
                "scenario_time": request.scenario_time,
                "state_revision": next_revision,
                "workflow_stage": WorkflowStage.ISOLATING,
                "status": ScenarioRunStatus.ACTIVE,
            }
        )
        unit.put_telemetry(run.scenario_run_id, changed_point)
        self._invoke_failure_hook("AFTER_PRIMARY_MUTATION")
        topology, outage, _ = self._derive(
            loaded,
            provisional_run,
            tuple(points.values()),
            previous_outage=unit.get_outage_snapshot(
                run.scenario_run_id, run.state_revision
            ),
        )
        isolated = bool(topology.isolation_proof and topology.isolation_proof.isolated)
        updated_run = provisional_run.model_copy(
            update={
                "workflow_stage": (
                    WorkflowStage.FAULT_ISOLATED
                    if isolated
                    else WorkflowStage.ISOLATING
                ),
                "network_state_label": (
                    NetworkStateLabel.N2 if isolated else NetworkStateLabel.N1
                ),
            }
        )
        unit.update_run(updated_run)
        unit.insert_derived_snapshots(
            run.scenario_run_id, next_revision, topology, outage
        )
        specs = (
            _EventSpec(
                OperationalEventSource.OPERATOR,
                OperationalEventType.SWITCHING_ACTION,
                request.target_entity_id,
                "Authorised simulated isolation OPEN operation accepted.",
                previous_value=previous.value.value,
                new_value=changed_point.value.value,
            ),
            _EventSpec(
                OperationalEventSource.SCADA,
                OperationalEventType.TELEMETRY_UPDATED,
                request.target_entity_id,
                "Switching-device telemetry refreshed after simulated operation.",
                previous_value=previous.value.value,
                new_value=changed_point.value.value,
            ),
            _EventSpec(
                OperationalEventSource.SCADA,
                OperationalEventType.DEVICE_STATE_CHANGE,
                request.target_entity_id,
                "Switching device changed state after simulated isolation operation.",
                previous_value=previous.value.value,
                new_value=changed_point.value.value,
            ),
            *self._derived_event_specs(topology, outage),
        )
        return self._complete_accepted(
            unit,
            prior_run=run,
            updated_run=updated_run,
            loaded=loaded,
            request=request,
            request_sha=request_sha,
            reason_code=("FAULT_ISOLATED" if isolated else "ISOLATION_ACTION_ACCEPTED"),
            reason=(
                "Isolation proof completed at N2."
                if isolated
                else "Isolation action completed; another approved boundary remains."
            ),
            event_specs=specs,
        )

    def _restore_normal_source(
        self,
        unit: ScenarioUnitOfWork,
        run: RunContext,
        loaded: LoadedConfiguration,
        request: ScenarioCommandRequest,
        request_sha: str,
    ) -> CommandResult:
        gate_topology = self._gate_topology(unit, loaded, run, request.scenario_time)
        _, breaker_id = self._affected_feeder_and_breaker(loaded, run)
        proof = gate_topology.isolation_proof
        available = (
            run.network_state_label is NetworkStateLabel.N2
            and proof is not None
            and proof.isolated
            and request.target_entity_id == breaker_id
            and request.requested_state is SwitchState.CLOSED
        )
        if not available:
            return self._reject(
                unit,
                run,
                loaded,
                request,
                request_sha,
                "NORMAL_SOURCE_RESTORE_UNAVAILABLE",
                "Current topology must prove fault isolation before source reclose.",
            )

        points = self._telemetry_map(unit, run.scenario_run_id)
        previous = points[breaker_id]
        if previous.value is not SwitchState.OPEN:
            return self._reject(
                unit,
                run,
                loaded,
                request,
                request_sha,
                "NORMAL_SOURCE_BREAKER_NOT_OPEN",
                "The approved N2 to N3 transition requires an OPEN source breaker.",
            )
        next_revision = run.state_revision + 1
        changed_point = previous.model_copy(
            update={
                "value": SwitchState.CLOSED,
                "quality": TelemetryQuality.GOOD,
                "last_update_scenario_time": request.scenario_time,
                "revision": next_revision,
            }
        )
        points[breaker_id] = changed_point
        updated_run = run.model_copy(
            update={
                "scenario_time": request.scenario_time,
                "state_revision": next_revision,
                "workflow_stage": WorkflowStage.UPSTREAM_RESTORED,
                "network_state_label": NetworkStateLabel.N3,
                "status": ScenarioRunStatus.ACTIVE,
            }
        )
        unit.update_run(updated_run)
        unit.put_telemetry(run.scenario_run_id, changed_point)
        self._invoke_failure_hook("AFTER_PRIMARY_MUTATION")
        topology, outage, _ = self._derive(
            loaded,
            updated_run,
            tuple(points.values()),
            previous_outage=unit.get_outage_snapshot(
                run.scenario_run_id, run.state_revision
            ),
        )
        unit.insert_derived_snapshots(
            run.scenario_run_id, next_revision, topology, outage
        )
        specs = (
            _EventSpec(
                OperationalEventSource.OPERATOR,
                OperationalEventType.SWITCHING_ACTION,
                breaker_id,
                "Authorised simulated normal-source reclose accepted.",
                previous_value=previous.value.value,
                new_value=changed_point.value.value,
            ),
            _EventSpec(
                OperationalEventSource.SCADA,
                OperationalEventType.TELEMETRY_UPDATED,
                breaker_id,
                "Source-breaker telemetry refreshed after simulated operation.",
                previous_value=previous.value.value,
                new_value=changed_point.value.value,
            ),
            _EventSpec(
                OperationalEventSource.SCADA,
                OperationalEventType.DEVICE_STATE_CHANGE,
                breaker_id,
                "Source breaker changed state after simulated normal restoration.",
                previous_value=previous.value.value,
                new_value=changed_point.value.value,
            ),
            *self._derived_event_specs(topology, outage),
        )
        return self._complete_accepted(
            unit,
            prior_run=run,
            updated_run=updated_run,
            loaded=loaded,
            request=request,
            request_sha=request_sha,
            reason_code="NORMAL_SOURCE_RESTORED",
            reason="Approved N2 to N3 normal-source restoration completed.",
            event_specs=specs,
        )

    def _reset_run(
        self,
        unit: ScenarioUnitOfWork,
        run: RunContext,
        loaded: LoadedConfiguration,
        request: ScenarioCommandRequest,
        request_sha: str,
    ) -> CommandResult:
        closed_run = run.model_copy(
            update={
                "scenario_time": request.scenario_time,
                "status": ScenarioRunStatus.CLOSED,
            }
        )
        unit.update_run(closed_run)
        reset_event = self._events_from_specs(
            unit,
            closed_run,
            request.command_id,
            request.actor,
            (
                _EventSpec(
                    OperationalEventSource.SCENARIO_CONTROL,
                    OperationalEventType.SCENARIO_RESET,
                    None,
                    "Run closed for controlled reset; prior history is preserved.",
                ),
            ),
        )
        unit.insert_events(reset_event)
        self._invoke_failure_hook("AFTER_PRIMARY_MUTATION")

        new_run = self._new_run(
            loaded=loaded,
            scenario_time=run.initial_scenario_time,
            application_build_id=run.application_build_id,
        )
        unit.insert_run(new_run)
        telemetry = self._normal_telemetry(loaded, new_run)
        for point in telemetry:
            unit.put_telemetry(new_run.scenario_run_id, point)
        topology, outage, _ = self._derive(
            loaded,
            new_run,
            telemetry,
            previous_outage=None,
        )
        unit.insert_derived_snapshots(
            new_run.scenario_run_id, 0, topology, outage
        )
        initial_events = self._initial_events(
            unit,
            new_run,
            request.command_id,
            request.actor,
        )
        unit.insert_events(initial_events)
        self._invoke_failure_hook("BEFORE_COMMIT")
        snapshot = self._assemble_snapshot(unit, new_run, loaded)
        all_events = (*reset_event, *initial_events)
        result = CommandResult(
            command_id=request.command_id,
            accepted=True,
            reason_code="RUN_RESET",
            reason="Prior run closed and a clean N0 run created without rewriting history.",
            prior_revision=run.state_revision,
            current_revision=0,
            run_status=new_run.status,
            new_event_ids=tuple(event.event_id for event in all_events),
            snapshot=snapshot,
        )
        unit.insert_command_result(
            command_id=request.command_id,
            scenario_run_id=run.scenario_run_id,
            request_sha256=request_sha,
            result=result,
        )
        return result

    def _complete_accepted(
        self,
        unit: ScenarioUnitOfWork,
        *,
        prior_run: RunContext,
        updated_run: RunContext,
        loaded: LoadedConfiguration,
        request: ScenarioCommandRequest,
        request_sha: str,
        reason_code: str,
        reason: str,
        event_specs: tuple[_EventSpec, ...],
    ) -> CommandResult:
        events = self._events_from_specs(
            unit,
            updated_run,
            request.command_id,
            request.actor,
            event_specs,
        )
        unit.insert_events(events)
        self._invoke_failure_hook("BEFORE_COMMIT")
        snapshot = self._assemble_snapshot(unit, updated_run, loaded)
        result = CommandResult(
            command_id=request.command_id,
            accepted=True,
            reason_code=reason_code,
            reason=reason,
            prior_revision=prior_run.state_revision,
            current_revision=updated_run.state_revision,
            run_status=updated_run.status,
            new_event_ids=tuple(event.event_id for event in events),
            snapshot=snapshot,
        )
        unit.insert_command_result(
            command_id=request.command_id,
            scenario_run_id=prior_run.scenario_run_id,
            request_sha256=request_sha,
            result=result,
        )
        return result

    def _reject(
        self,
        unit: ScenarioUnitOfWork,
        run: RunContext,
        loaded: LoadedConfiguration,
        request: ScenarioCommandRequest,
        request_sha: str,
        reason_code: str,
        reason: str,
    ) -> CommandResult:
        snapshot = self._assemble_snapshot(unit, run, loaded)
        result = CommandResult(
            command_id=request.command_id,
            accepted=False,
            reason_code=reason_code,
            reason=reason,
            prior_revision=run.state_revision,
            current_revision=run.state_revision,
            run_status=run.status,
            new_event_ids=(),
            snapshot=snapshot,
        )
        unit.insert_command_result(
            command_id=request.command_id,
            scenario_run_id=run.scenario_run_id,
            request_sha256=request_sha,
            result=result,
        )
        return result

    def _assemble_snapshot(
        self,
        unit: ScenarioUnitOfWork,
        run: RunContext,
        loaded: LoadedConfiguration,
    ) -> ScenarioSnapshot:
        telemetry = unit.list_telemetry(run.scenario_run_id)
        validities = tuple(
            self._telemetry_validity.classify(point, run.scenario_time)
            for point in telemetry
        )
        # The persisted revision snapshot remains immutable historical evidence.
        # The current projection must instead evaluate time-sensitive isolation
        # evidence at the run's current controlled scenario time.
        current_topology, _, _ = self._derive(
            loaded,
            run,
            telemetry,
            previous_outage=None,
        )
        outage = unit.get_outage_snapshot(run.scenario_run_id, run.state_revision)
        alarms = unit.list_alarms(run.scenario_run_id)
        return ScenarioSnapshot(
            run=run,
            telemetry=telemetry,
            telemetry_validity=validities,
            alarms=alarms,
            topology=current_topology,
            outage=outage,
            events=unit.list_events(run.scenario_run_id),
            allowed_actions=self._allowed_actions(
                run, loaded, current_topology, alarms
            ),
        )

    def _derive(
        self,
        loaded: LoadedConfiguration,
        run: RunContext,
        telemetry: tuple[TelemetryPoint, ...],
        *,
        previous_outage: OutageResult | None,
    ) -> tuple[TopologyResult, OutageResult, tuple[TelemetryValidity, ...]]:
        validities = tuple(
            self._telemetry_validity.classify(point, run.scenario_time)
            for point in sorted(telemetry, key=lambda item: item.point_id)
        )
        validity_by_point = {item.point_id: item for item in validities}
        topology = self._topology.calculate(
            loaded,
            TopologyInputs(
                device_states={point.entity_id: point.value for point in telemetry},
                source_availability=run.source_availability,
                faulted_section_ids=(
                    frozenset({run.fault_section_id})
                    if run.fault_active
                    else frozenset()
                ),
                active_fault_section_id=(
                    run.fault_section_id if run.fault_active else None
                ),
                boundary_observations={
                    point.entity_id: BoundaryObservation(
                        device_id=point.entity_id,
                        observed_state=point.value,
                        quality=point.quality,
                        freshness_status=validity_by_point[point.point_id].freshness,
                    )
                    for point in telemetry
                },
            ),
        )
        outage = self._outage.calculate(
            loaded,
            topology,
            previous=previous_outage,
        )
        return topology, outage, validities

    def _gate_topology(
        self,
        unit: ScenarioUnitOfWork,
        loaded: LoadedConfiguration,
        run: RunContext,
        scenario_time: datetime,
    ) -> TopologyResult:
        gate_run = run.model_copy(update={"scenario_time": scenario_time})
        topology, _, _ = self._derive(
            loaded,
            gate_run,
            unit.list_telemetry(run.scenario_run_id),
            previous_outage=None,
        )
        return topology

    def _allowed_actions(
        self,
        run: RunContext,
        loaded: LoadedConfiguration,
        gate_topology: TopologyResult,
        alarms: tuple[AlarmRecord, ...],
    ) -> tuple[AllowedAction, ...]:
        mutable = run.status is not ScenarioRunStatus.CLOSED
        actions: list[AllowedAction] = [
            AllowedAction(
                command_type=ScenarioCommandType.INITIATE_FAULT,
                available=(
                    mutable
                    and run.network_state_label is NetworkStateLabel.N0
                    and not run.fault_active
                ),
                reason_code=(
                    "AVAILABLE"
                    if mutable
                    and run.network_state_label is NetworkStateLabel.N0
                    and not run.fault_active
                    else "REQUIRES_N0_NO_ACTIVE_FAULT"
                ),
                reason="Available only from controlled N0 with no active fault.",
            )
        ]
        unacknowledged = tuple(
            alarm
            for alarm in alarms
            if alarm.active
            and alarm.acknowledgement_state
            is AlarmAcknowledgementState.UNACKNOWLEDGED
        )
        if unacknowledged:
            actions.extend(
                AllowedAction(
                    command_type=ScenarioCommandType.ACKNOWLEDGE_ALARM,
                    alarm_id=alarm.alarm_id,
                    available=mutable,
                    reason_code="AVAILABLE" if mutable else "RUN_CLOSED",
                    reason="Active unacknowledged alarm may be acknowledged.",
                )
                for alarm in unacknowledged
            )
        else:
            actions.append(
                AllowedAction(
                    command_type=ScenarioCommandType.ACKNOWLEDGE_ALARM,
                    available=False,
                    reason_code="NO_ACTIVE_UNACKNOWLEDGED_ALARM",
                    reason="No active unacknowledged alarm exists.",
                )
            )

        next_target, next_reason = self._next_isolation_target(run, gate_topology)
        proof = gate_topology.isolation_proof
        actual_boundaries = (
            self._ordered_isolation_boundaries(proof.incident_boundary_device_ids)
            if proof is not None
            else self._definition.isolation_device_sequence
        )
        for device_id in actual_boundaries:
            actions.append(
                AllowedAction(
                    command_type=ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
                    target_entity_id=device_id,
                    requested_state=SwitchState.OPEN,
                    available=mutable and device_id == next_target,
                    reason_code=(
                        "AVAILABLE"
                        if mutable and device_id == next_target
                        else "ISOLATION_ACTION_UNAVAILABLE"
                    ),
                    reason=(
                        "Approved formal isolation action is available."
                        if mutable and device_id == next_target
                        else next_reason
                    ),
                )
            )

        _, breaker_id = self._affected_feeder_and_breaker(loaded, run)
        restore_available = (
            mutable
            and run.network_state_label is NetworkStateLabel.N2
            and proof is not None
            and proof.isolated
        )
        actions.append(
            AllowedAction(
                command_type=ScenarioCommandType.RESTORE_NORMAL_SOURCE,
                target_entity_id=breaker_id,
                requested_state=SwitchState.CLOSED,
                available=restore_available,
                reason_code=(
                    "AVAILABLE" if restore_available else "ISOLATION_NOT_PROVEN_AT_N2"
                ),
                reason="Requires current derived isolation proof at N2.",
            )
        )
        actions.append(
            AllowedAction(
                command_type=ScenarioCommandType.RESET_RUN,
                available=mutable,
                reason_code="AVAILABLE" if mutable else "RUN_CLOSED",
                reason="Creates a new clean run while preserving prior history.",
            )
        )
        return tuple(actions)

    def _next_isolation_target(
        self,
        run: RunContext,
        topology: TopologyResult,
    ) -> tuple[str | None, str]:
        if run.network_state_label is not NetworkStateLabel.N1:
            return None, "Isolation actions require the post-fault N1 workflow state."
        proof = topology.isolation_proof
        if proof is None:
            return None, "No active-fault isolation proof is available."
        evaluation_by_id = {
            item.boundary_device_id: item for item in proof.boundary_evaluations
        }
        for device_id in self._ordered_isolation_boundaries(
            proof.incident_boundary_device_ids
        ):
            evaluation = evaluation_by_id.get(device_id)
            if evaluation is None:
                return None, "The formal isolation boundary is absent from configuration incidence."
            if evaluation.proof_status is BoundaryProofStatus.PROVEN_OPEN:
                continue
            if evaluation.proof_status is BoundaryProofStatus.PROVEN_CLOSED:
                return device_id, "Approved formal isolation action is available."
            return None, (
                f"Boundary {device_id} is UNPROVEN; trustworthy fresh evidence is required."
            )
        return None, "All formal isolation boundaries are already proven OPEN."

    def _ordered_isolation_boundaries(
        self,
        boundary_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Apply the formal procedure order only to boundaries derived by I2."""

        procedure_index = {
            device_id: index
            for index, device_id in enumerate(
                self._definition.isolation_device_sequence
            )
        }
        return tuple(
            sorted(
                boundary_ids,
                key=lambda device_id: (
                    procedure_index.get(device_id, len(procedure_index)),
                    device_id,
                ),
            )
        )

    def _initial_events(
        self,
        unit: ScenarioUnitOfWork,
        run: RunContext,
        command_id: UUID,
        actor: str,
    ) -> tuple[OperationalEvent, ...]:
        return self._events_from_specs(
            unit,
            run,
            command_id,
            actor,
            (
                _EventSpec(
                    OperationalEventSource.SCENARIO_CONTROL,
                    OperationalEventType.SCENARIO_INITIALISED,
                    None,
                    "New controlled scenario run initialised.",
                ),
                _EventSpec(
                    OperationalEventSource.GIS,
                    OperationalEventType.CONFIGURATION_SELECTED,
                    None,
                    "Immutable network configuration selected for the run.",
                    new_value=run.configuration_id,
                ),
                _EventSpec(
                    OperationalEventSource.ADMS_TOPOLOGY,
                    OperationalEventType.TOPOLOGY_RECALCULATED,
                    None,
                    "Initial topology and energisation derived from controlled inputs.",
                ),
                _EventSpec(
                    OperationalEventSource.OMS,
                    OperationalEventType.OUTAGE_UPDATED,
                    None,
                    "Initial outage and customer impact derived from topology.",
                ),
            ),
        )

    @staticmethod
    def _derived_event_specs(
        topology: TopologyResult,
        outage: OutageResult,
    ) -> tuple[_EventSpec, _EventSpec]:
        return (
            _EventSpec(
                OperationalEventSource.ADMS_TOPOLOGY,
                OperationalEventType.TOPOLOGY_RECALCULATED,
                None,
                (
                    "Topology, source paths, energisation and radiality recalculated "
                    f"for configuration {topology.configuration_id}."
                ),
            ),
            _EventSpec(
                OperationalEventSource.OMS,
                OperationalEventType.OUTAGE_UPDATED,
                None,
                (
                    "Outage/customer consequence recalculated: "
                    f"{outage.affected_customer_count} affected."
                ),
            ),
        )

    @staticmethod
    def _events_from_specs(
        unit: ScenarioUnitOfWork,
        run: RunContext,
        command_id: UUID,
        actor: str,
        specs: tuple[_EventSpec, ...],
    ) -> tuple[OperationalEvent, ...]:
        first_sequence = unit.next_event_sequence(run.scenario_run_id)
        return tuple(
            OperationalEvent(
                event_id=uuid4(),
                scenario_run_id=run.scenario_run_id,
                event_sequence=first_sequence + offset,
                scenario_time=run.scenario_time,
                state_revision=run.state_revision,
                source=spec.source,
                event_type=spec.event_type,
                affected_entity_id=spec.affected_entity_id,
                description=spec.description,
                actor=actor,
                previous_value=spec.previous_value,
                new_value=spec.new_value,
                command_id=command_id,
                alarm_id=spec.alarm_id,
            )
            for offset, spec in enumerate(specs)
        )

    def _new_run(
        self,
        *,
        loaded: LoadedConfiguration,
        scenario_time: datetime,
        application_build_id: str,
    ) -> RunContext:
        normal_inputs = self._topology.normal_inputs(loaded.data)
        return RunContext(
            scenario_run_id=uuid4(),
            mode=ScenarioMode.FORMAL,
            configuration_id=loaded.catalog_entry.configuration_id,
            configuration_version=loaded.catalog_entry.version,
            fault_section_id=self._definition.fault_section_id,
            fault_type=FaultType.DISTRIBUTION_SECTION_FAULT,
            initial_scenario_time=scenario_time,
            scenario_time=scenario_time,
            state_revision=0,
            workflow_stage=WorkflowStage.NORMAL,
            network_state_label=NetworkStateLabel.N0,
            evidence_class=EvidenceClass.FORMAL,
            application_build_id=application_build_id,
            status=ScenarioRunStatus.INITIALISED,
            fault_active=False,
            source_availability=dict(normal_inputs.source_availability),
        )

    @staticmethod
    def _normal_telemetry(
        loaded: LoadedConfiguration,
        run: RunContext,
    ) -> tuple[TelemetryPoint, ...]:
        return tuple(
            TelemetryPoint(
                point_id=device.entity_id,
                entity_id=device.entity_id,
                value=device.normal_state,
                quality=TelemetryQuality.GOOD,
                last_update_scenario_time=run.initial_scenario_time,
                revision=0,
            )
            for device in sorted(
                loaded.data.switching_devices,
                key=lambda item: item.entity_id,
            )
        )

    @staticmethod
    def _telemetry_map(
        unit: ScenarioUnitOfWork,
        scenario_run_id: UUID,
    ) -> dict[str, TelemetryPoint]:
        return {
            point.entity_id: point
            for point in unit.list_telemetry(scenario_run_id)
        }

    def _affected_feeder_and_breaker(
        self,
        loaded: LoadedConfiguration,
        run: RunContext,
    ):
        section = next(
            item
            for item in loaded.data.sections
            if item.entity_id == run.fault_section_id
        )
        feeder = next(
            item
            for item in loaded.data.feeders
            if item.entity_id == section.feeder_id
        )
        return feeder, feeder.source_breaker_id

    def _validate_definition(self, loaded: LoadedConfiguration) -> None:
        section_ids = {section.entity_id for section in loaded.data.sections}
        device_ids = {device.entity_id for device in loaded.data.switching_devices}
        if self._definition.fault_section_id not in section_ids:
            raise ScenarioBoundaryError(
                "formal fault section is absent from the selected configuration"
            )
        unknown_devices = sorted(
            set(self._definition.isolation_device_sequence) - device_ids
        )
        if unknown_devices:
            raise ScenarioBoundaryError(
                f"formal isolation devices are absent: {unknown_devices}"
            )

    def _return_duplicate(
        self,
        unit: ScenarioUnitOfWork,
        command_id: UUID,
        request_sha: str,
    ) -> CommandResult | None:
        stored = unit.get_command_result(command_id)
        if stored is None:
            return None
        stored_sha, result = stored
        if stored_sha != request_sha:
            raise ScenarioCommandConflict(
                "command_id was already used with different request content"
            )
        return result

    @staticmethod
    def _request_sha(request: InitialiseRunRequest | ScenarioCommandRequest) -> str:
        return sha256_bytes(
            canonical_json_bytes(request.model_dump(mode="json"))
        )

    def _invoke_failure_hook(self, stage: str) -> None:
        if self._failure_hook is not None:
            self._failure_hook(stage)


__all__ = [
    "ScenarioBoundaryError",
    "ScenarioCommandConflict",
    "ScenarioCoordinator",
    "ScenarioRecordNotFound",
]
