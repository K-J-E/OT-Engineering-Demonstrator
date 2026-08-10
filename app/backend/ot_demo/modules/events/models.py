"""Typed operational events kept separate from validation and defect records."""

from uuid import UUID

from pydantic import Field

from ...domain.base import FrozenModel
from ...domain.enums import OperationalEventSource, OperationalEventType
from ...domain.value_objects import EngineeringId, UtcMillisecondInstant


class OperationalEvent(FrozenModel):
    event_id: UUID
    scenario_run_id: UUID
    event_sequence: int = Field(ge=1)
    scenario_time: UtcMillisecondInstant
    state_revision: int = Field(ge=0)
    source: OperationalEventSource
    event_type: OperationalEventType
    affected_entity_id: EngineeringId | None = None
    description: str = Field(min_length=1, max_length=500)
    actor: str | None = Field(default=None, min_length=1, max_length=120)
    previous_value: str | None = Field(default=None, max_length=160)
    new_value: str | None = Field(default=None, max_length=160)
    command_id: UUID | None = None
    alarm_id: UUID | None = None
    assessment_id: UUID | None = None
