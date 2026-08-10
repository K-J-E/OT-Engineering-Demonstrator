"""Pure outage read model derived from topology and configuration mappings."""

from ...domain.base import FrozenModel
from ...domain.value_objects import ConfigurationId, EngineeringId, PositiveCustomerCount


class AffectedCustomerZone(FrozenModel):
    section_id: EngineeringId
    customer_zone_id: EngineeringId
    customer_count: PositiveCustomerCount


class OutageResult(FrozenModel):
    configuration_id: ConfigurationId
    de_energised_section_ids: tuple[EngineeringId, ...]
    affected_customer_zones: tuple[AffectedCustomerZone, ...]
    affected_customer_count: int
    restored_customer_delta: int
