"""Observed SCADA-style telemetry and alarm records owned by I3."""

from uuid import UUID

from pydantic import Field, model_validator
from typing_extensions import Self

from ...domain.base import FrozenModel
from ...domain.enums import (
    AlarmAcknowledgementState,
    AlarmType,
    FreshnessStatus,
    SwitchState,
    TelemetryQuality,
)
from ...domain.value_objects import EngineeringId, UtcMillisecondInstant


class TelemetryPoint(FrozenModel):
    point_id: EngineeringId
    entity_id: EngineeringId
    value: SwitchState
    quality: TelemetryQuality
    last_update_scenario_time: UtcMillisecondInstant
    revision: int = Field(ge=0)


class TelemetryValidity(FrozenModel):
    point_id: EngineeringId
    age_ms: int
    freshness: FreshnessStatus
    quality: TelemetryQuality
    quality_valid: bool
    timestamp_valid: bool
    overall_valid: bool
    reason_codes: tuple[str, ...]

    @model_validator(mode="after")
    def validate_classification(self) -> Self:
        if self.timestamp_valid != (self.freshness is not FreshnessStatus.INVALID_TIMESTAMP):
            raise ValueError("timestamp_valid must match freshness classification")
        if self.quality_valid != (self.quality is TelemetryQuality.GOOD):
            raise ValueError("quality_valid must match telemetry quality")
        expected = (
            self.timestamp_valid
            and self.quality_valid
            and self.freshness is FreshnessStatus.FRESH
        )
        if self.overall_valid != expected:
            raise ValueError("overall_valid must preserve quality/freshness separation")
        return self


class AlarmRecord(FrozenModel):
    alarm_id: UUID
    scenario_run_id: UUID
    entity_id: EngineeringId
    alarm_type: AlarmType
    active: bool
    acknowledgement_state: AlarmAcknowledgementState
    generated_scenario_time: UtcMillisecondInstant
    acknowledged_scenario_time: UtcMillisecondInstant | None = None
    acknowledged_by: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_acknowledgement(self) -> Self:
        acknowledged = (
            self.acknowledgement_state is AlarmAcknowledgementState.ACKNOWLEDGED
        )
        if acknowledged != (self.acknowledged_scenario_time is not None):
            raise ValueError("acknowledgement time must match acknowledgement state")
        if acknowledged != (self.acknowledged_by is not None):
            raise ValueError("acknowledgement actor must match acknowledgement state")
        if (
            self.acknowledged_scenario_time is not None
            and self.acknowledged_scenario_time < self.generated_scenario_time
        ):
            raise ValueError("alarm cannot be acknowledged before generation")
        return self
