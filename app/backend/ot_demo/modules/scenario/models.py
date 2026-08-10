"""Typed I3 run, command, action and complete-snapshot contracts."""

from uuid import UUID

from pydantic import Field, model_validator
from typing_extensions import Self

from ...domain.base import FrozenModel
from ...domain.enums import (
    EvidenceClass,
    FaultType,
    NetworkStateLabel,
    ScenarioCommandType,
    ScenarioMode,
    ScenarioRunStatus,
    SourceAvailability,
    SwitchState,
    WorkflowStage,
)
from ...domain.value_objects import (
    ConfigurationId,
    EngineeringId,
    SemanticVersion,
    Sha256Digest,
    UtcMillisecondInstant,
)
from ..events.models import OperationalEvent
from ..outage.models import OutageResult
from ..telemetry.models import AlarmRecord, TelemetryPoint, TelemetryValidity
from ..topology.models import TopologyResult


class RunContext(FrozenModel):
    scenario_run_id: UUID
    mode: ScenarioMode
    configuration_id: ConfigurationId
    configuration_version: SemanticVersion
    fault_section_id: EngineeringId
    fault_type: FaultType
    initial_scenario_time: UtcMillisecondInstant
    scenario_time: UtcMillisecondInstant
    state_revision: int = Field(ge=0)
    workflow_stage: WorkflowStage
    network_state_label: NetworkStateLabel
    evidence_class: EvidenceClass
    application_build_id: Sha256Digest
    status: ScenarioRunStatus
    fault_active: bool
    source_availability: dict[EngineeringId, SourceAvailability]


class InitialiseRunRequest(FrozenModel):
    command_id: UUID
    actor: str = Field(min_length=1, max_length=120)
    expected_revision: int = Field(default=0, ge=0, le=0)
    mode: ScenarioMode
    configuration_version: SemanticVersion
    scenario_time: UtcMillisecondInstant
    application_build_id: Sha256Digest


class ScenarioCommandRequest(FrozenModel):
    command_id: UUID
    scenario_run_id: UUID
    actor: str = Field(min_length=1, max_length=120)
    expected_revision: int = Field(ge=0)
    command_type: ScenarioCommandType
    scenario_time: UtcMillisecondInstant
    target_entity_id: EngineeringId | None = None
    requested_state: SwitchState | None = None
    alarm_id: UUID | None = None

    @model_validator(mode="after")
    def validate_target_shape(self) -> Self:
        switching = self.command_type in {
            ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            ScenarioCommandType.RESTORE_NORMAL_SOURCE,
        }
        if switching != (self.target_entity_id is not None):
            raise ValueError("switching commands require one target entity")
        if switching != (self.requested_state is not None):
            raise ValueError("switching commands require one requested state")
        acknowledging = self.command_type is ScenarioCommandType.ACKNOWLEDGE_ALARM
        if acknowledging != (self.alarm_id is not None):
            raise ValueError("alarm acknowledgement requires one alarm ID")
        return self


class AllowedAction(FrozenModel):
    command_type: ScenarioCommandType
    target_entity_id: EngineeringId | None = None
    requested_state: SwitchState | None = None
    alarm_id: UUID | None = None
    available: bool
    reason_code: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=500)


class ScenarioSnapshot(FrozenModel):
    run: RunContext
    telemetry: tuple[TelemetryPoint, ...]
    telemetry_validity: tuple[TelemetryValidity, ...]
    alarms: tuple[AlarmRecord, ...]
    topology: TopologyResult
    outage: OutageResult
    events: tuple[OperationalEvent, ...]
    allowed_actions: tuple[AllowedAction, ...]


class CommandResult(FrozenModel):
    command_id: UUID
    accepted: bool
    reason_code: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=500)
    prior_revision: int = Field(ge=0)
    current_revision: int = Field(ge=0)
    run_status: ScenarioRunStatus
    new_event_ids: tuple[UUID, ...]
    snapshot: ScenarioSnapshot
