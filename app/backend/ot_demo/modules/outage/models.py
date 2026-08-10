"""Pure outage read model derived from topology and configuration mappings."""

from pydantic import Field, model_validator
from typing_extensions import Self

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
    affected_customer_count: int = Field(ge=0)
    restored_customer_delta: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_customer_summary(self) -> Self:
        mapped_sections = tuple(
            zone.section_id for zone in self.affected_customer_zones
        )
        if self.de_energised_section_ids != mapped_sections:
            raise ValueError(
                "de-energised sections must match affected customer-zone sections"
            )
        if self.affected_customer_count != sum(
            zone.customer_count for zone in self.affected_customer_zones
        ):
            raise ValueError(
                "affected_customer_count must equal the affected-zone customer sum"
            )
        return self
