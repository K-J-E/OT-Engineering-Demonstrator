"""Approved formal N0-N3 workflow inputs, separate from network configuration."""

from typing import Annotated

from pydantic import Field

from ...domain.base import FrozenModel
from ...domain.value_objects import EngineeringId


class FormalScenarioDefinition(FrozenModel):
    fault_section_id: EngineeringId
    isolation_device_sequence: Annotated[
        tuple[EngineeringId, ...], Field(min_length=1)
    ]


FORMAL_N0_N3_DEFINITION = FormalScenarioDefinition(
    fault_section_id="SEC-A2",
    isolation_device_sequence=("SW-A12", "SW-A23"),
)
