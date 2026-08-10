"""Read-only I6 workspace contracts that preserve information ownership."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from ...domain.base import FrozenModel
from ...domain.enums import (
    ConfigurationStatus,
    EvidenceClass,
    FreshnessStatus,
    RadialityStatus,
    ScenarioCommandType,
    ScenarioMode,
    SourceAvailability,
    SwitchState,
    TelemetryQuality,
)
from ...domain.value_objects import (
    ConfigurationId,
    EngineeringId,
    SemanticVersion,
    Sha256Digest,
    UtcMillisecondInstant,
)
from ..events.models import OperationalEvent
from ..restoration.models import AssessmentInvalidation, RestorationAssessment
from ..scenario.models import RunContext
from ..telemetry.models import AlarmRecord
from ..topology.models import IsolationProof
from ..validation.models import (
    CompositeValidationResult,
    LoadedValidationDefinition,
    ValidationExecutionSummary,
)


class PresentationPosition(FrozenModel):
    x: int
    y: int


class ConfiguredEntityView(FrozenModel):
    entity_id: EngineeringId
    entity_type: Literal["SOURCE", "SWITCHING_DEVICE", "SECTION"]
    name: str
    feeder_id: EngineeringId | None = None
    device_type: str | None = None
    normal_state: SwitchState | None = None
    normal_source_availability: SourceAvailability | None = None
    configured_load_kw: int | None = Field(default=None, ge=0)
    customer_zone_id: EngineeringId | None = None
    customer_count: int | None = Field(default=None, ge=0)


class ObservedEntityView(FrozenModel):
    point_id: EngineeringId
    value: SwitchState
    quality: TelemetryQuality
    timestamp: UtcMillisecondInstant
    age_ms: int
    freshness: FreshnessStatus
    overall_valid: bool
    reason_codes: tuple[str, ...]


class DerivedEntityView(FrozenModel):
    energised: bool | None = None
    source_feeder_ids: tuple[EngineeringId, ...] = ()
    source_path_node_ids: tuple[tuple[EngineeringId, ...], ...] = ()
    current_source_availability: SourceAvailability | None = None


class WorkspaceNetworkNode(FrozenModel):
    entity_id: EngineeringId
    position: PresentationPosition
    configured: ConfiguredEntityView
    observed: ObservedEntityView | None = None
    derived: DerivedEntityView
    fault_status: Literal["FAULTED", "NOT_FAULTED", "NOT_APPLICABLE"]


class WorkspaceNetworkEdge(FrozenModel):
    edge_id: EngineeringId
    endpoint_a_id: EngineeringId
    endpoint_b_id: EngineeringId
    semantics: str
    active: bool


class WorkspaceFeederView(FrozenModel):
    feeder_id: EngineeringId
    name: str
    source_id: EngineeringId
    source_breaker_id: EngineeringId
    section_ids: tuple[EngineeringId, ...]
    configured_capacity_kw: int = Field(ge=0)
    configured_normal_load_kw: int = Field(ge=0)
    derived_currently_supplied_load_kw: int | None = Field(default=None, ge=0)
    derived_load_attribution_complete: bool
    derived_supplied_section_ids: tuple[EngineeringId, ...]


class TelemetryWorkspaceRow(FrozenModel):
    point_id: EngineeringId
    entity_id: EngineeringId
    value: SwitchState
    quality: TelemetryQuality
    timestamp: UtcMillisecondInstant
    age_ms: int
    freshness: FreshnessStatus
    quality_valid: bool
    timestamp_valid: bool
    overall_valid: bool
    reason_codes: tuple[str, ...]


class WorkspaceSummary(FrozenModel):
    de_energised_section_ids: tuple[EngineeringId, ...]
    affected_customer_count: int = Field(ge=0)
    restored_customer_delta: int = Field(ge=0)
    active_alarm_count: int = Field(ge=0)
    unacknowledged_alarm_count: int = Field(ge=0)
    current_assessment_status: str
    current_assessment_id: UUID | None = None
    current_assessment_invalidated: bool
    radiality_status: RadialityStatus


class WorkspaceAction(FrozenModel):
    action_id: str = Field(min_length=1)
    command_type: ScenarioCommandType
    target_entity_id: EngineeringId | None = None
    requested_state: SwitchState | None = None
    alarm_id: UUID | None = None
    assessment_id: UUID | None = None
    available: bool
    reason_code: str
    reason: str
    expected_revision: int = Field(ge=0)
    proposed_scenario_time: UtcMillisecondInstant
    confirmation_required: bool
    confirmation_text: str | None = None


class ValidationProgress(FrozenModel):
    definition_count: int = Field(ge=0)
    definitions_without_execution_count: int = Field(ge=0)
    execution_count: int = Field(ge=0)
    active_execution_count: int = Field(ge=0)
    finalised_execution_count: int = Field(ge=0)
    pass_count: int = Field(ge=0)
    fail_count: int = Field(ge=0)
    blocked_test_count: int = Field(ge=0)


class ValidationWorkspaceAction(FrozenModel):
    action_type: Literal["START_EXECUTION", "CAPTURE_CHECKPOINT", "FINALISE_EXECUTION"]
    available: bool
    reason_code: str
    reason: str
    test_id: str
    case_id: str | None = None
    validation_execution_id: UUID | None = None
    checkpoint_id: str | None = None


class ValidationWorkspaceView(FrozenModel):
    definitions: tuple[LoadedValidationDefinition, ...]
    run_executions: tuple[ValidationExecutionSummary, ...]
    library_executions: tuple[ValidationExecutionSummary, ...]
    composites: tuple[CompositeValidationResult, ...]
    progress: ValidationProgress
    actions: tuple[ValidationWorkspaceAction, ...]


class WorkspaceBootstrap(FrozenModel):
    application_build_id: Sha256Digest
    default_actor: str
    default_mode: ScenarioMode
    default_evidence_class: EvidenceClass
    default_configuration_id: ConfigurationId
    default_configuration_version: SemanticVersion
    default_scenario_time: UtcMillisecondInstant
    formal_test_id: str
    formal_definition: LoadedValidationDefinition
    exploration_section_ids: tuple[EngineeringId, ...]
    definition_count: int = Field(ge=1)
    conceptual_boundary_notice: str


class WorkspaceProjection(FrozenModel):
    application_build_id: Sha256Digest
    run: RunContext
    configuration_status: ConfigurationStatus
    summary: WorkspaceSummary
    network_nodes: tuple[WorkspaceNetworkNode, ...]
    network_edges: tuple[WorkspaceNetworkEdge, ...]
    feeders: tuple[WorkspaceFeederView, ...]
    telemetry: tuple[TelemetryWorkspaceRow, ...]
    alarms: tuple[AlarmRecord, ...]
    events: tuple[OperationalEvent, ...]
    isolation_proof: IsolationProof | None
    restoration_assessments: tuple[RestorationAssessment, ...]
    restoration_invalidations: tuple[AssessmentInvalidation, ...]
    allowed_actions: tuple[WorkspaceAction, ...]
    validation: ValidationWorkspaceView
    conceptual_boundary_notice: str
