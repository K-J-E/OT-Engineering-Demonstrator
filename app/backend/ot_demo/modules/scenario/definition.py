"""Approved formal N0-N3 workflow inputs, separate from network configuration."""

from typing import Annotated

from pydantic import Field

from ...domain.base import FrozenModel
from ...domain.value_objects import EngineeringId
from ...domain.enums import ScenarioCommandType


class FormalScenarioDefinition(FrozenModel):
    fault_section_id: EngineeringId
    isolation_device_sequence: Annotated[
        tuple[EngineeringId, ...], Field(min_length=1)
    ]


FORMAL_N0_N3_DEFINITION = FormalScenarioDefinition(
    fault_section_id="SEC-A2",
    isolation_device_sequence=("SW-A12", "SW-A23"),
)


def formal_action_offset_seconds(
    command_type: ScenarioCommandType,
    target_entity_id: EngineeringId | None = None,
) -> int | None:
    """Return the accepted Step 9 formal schedule offset for one action."""

    if command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE:
        return {"SW-A12": 20, "SW-A23": 30}.get(target_entity_id)
    return {
        ScenarioCommandType.INITIATE_FAULT: 10,
        ScenarioCommandType.ACKNOWLEDGE_ALARM: 11,
        ScenarioCommandType.RESTORE_NORMAL_SOURCE: 40,
        ScenarioCommandType.ASSESS_RESTORATION: 50,
        ScenarioCommandType.EXECUTE_RESTORATION: 55,
    }.get(command_type)
