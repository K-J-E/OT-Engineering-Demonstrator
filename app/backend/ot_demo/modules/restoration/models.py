"""Immutable I4 candidate, assessment, invalidation and execution contracts."""

from decimal import Decimal
from uuid import UUID

from pydantic import Field

from ...domain.base import FrozenModel
from ...domain.enums import (
    PermissiveStatus,
    RestorationCriterion,
    RestorationOutcome,
    SourceAvailability,
    SwitchState,
    TelemetryQuality,
    FreshnessStatus,
)
from ...domain.value_objects import (
    ConfigurationId,
    EngineeringId,
    NonNegativeKilowatts,
    Sha256Digest,
    UtcMillisecondInstant,
)


class RestorationCandidate(FrozenModel):
    candidate_id: UUID
    affected_feeder_id: EngineeringId
    alternate_feeder_id: EngineeringId
    alternate_source_id: EngineeringId
    alternate_source_breaker_id: EngineeringId
    tie_device_id: EngineeringId
    requested_tie_state: SwitchState = SwitchState.CLOSED
    proposed_section_ids: tuple[EngineeringId, ...]
    proposed_path_edge_ids: tuple[EngineeringId, ...]
    transferable_load_kw: NonNegativeKilowatts
    proposed_restored_customer_count: int = Field(ge=0)


class RestorationTelemetryEvidence(FrozenModel):
    point_id: EngineeringId
    entity_id: EngineeringId
    value: SwitchState
    quality: TelemetryQuality
    timestamp: UtcMillisecondInstant
    revision: int = Field(ge=0)
    age_ms: int
    freshness: FreshnessStatus
    overall_valid: bool
    reason_codes: tuple[str, ...]


class RestorationCalculation(FrozenModel):
    alternate_feeder_id: EngineeringId
    existing_supplied_load_kw: NonNegativeKilowatts
    transferable_load_kw: NonNegativeKilowatts
    resulting_load_kw: NonNegativeKilowatts
    feeder_capacity_kw: NonNegativeKilowatts
    resulting_loading_percent: Decimal = Field(ge=0)
    capacity_pass: bool


class PermissiveResult(FrozenModel):
    criterion: RestorationCriterion
    status: PermissiveStatus
    reason_codes: tuple[str, ...]
    evidence_point_ids: tuple[EngineeringId, ...] = ()


class RestorationAssessment(FrozenModel):
    assessment_id: UUID
    assessment_sequence: int = Field(ge=1)
    scenario_run_id: UUID
    configuration_id: ConfigurationId
    state_revision: int = Field(ge=0)
    scenario_time: UtcMillisecondInstant
    candidate: RestorationCandidate | None
    telemetry_snapshot_sha256: Sha256Digest
    source_availability_sha256: Sha256Digest
    telemetry_evidence: tuple[RestorationTelemetryEvidence, ...]
    source_availability: dict[EngineeringId, SourceAvailability]
    permissives: tuple[PermissiveResult, ...]
    calculation: RestorationCalculation | None
    outcome: RestorationOutcome
    reason_codes: tuple[str, ...]


class AssessmentInvalidation(FrozenModel):
    invalidation_id: UUID
    assessment_id: UUID
    scenario_run_id: UUID
    superseding_state_revision: int = Field(ge=0)
    superseding_scenario_time: UtcMillisecondInstant
    reason_code: str = Field(min_length=1, max_length=160)
    event_id: UUID


class RestorationExecutionBinding(FrozenModel):
    assessment_id: UUID
    scenario_run_id: UUID
    configuration_id: ConfigurationId
    candidate_id: UUID
    state_revision: int = Field(ge=0)
    telemetry_snapshot_sha256: Sha256Digest
    source_availability_sha256: Sha256Digest
    tie_device_id: EngineeringId
    requested_tie_state: SwitchState
