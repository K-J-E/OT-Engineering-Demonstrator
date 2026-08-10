"""OMS-style outage/customer consequence processing from derived energisation."""

from ...domain.configuration import NetworkConfigurationData
from ..topology.models import TopologyResult
from .models import AffectedCustomerZone, OutageResult


class OutageService:
    """Map de-energised sections to configured customer zones without fault inference."""

    def calculate(
        self,
        configuration: NetworkConfigurationData,
        topology: TopologyResult,
        *,
        previous: OutageResult | None = None,
    ) -> OutageResult:
        section_ids = {section.entity_id for section in configuration.sections}
        topology_section_ids = {state.section_id for state in topology.sections}
        if topology_section_ids != section_ids:
            raise ValueError("topology result does not cover the selected configuration")

        de_energised = tuple(
            state.section_id for state in topology.sections if not state.energised
        )
        de_energised_set = set(de_energised)
        mappings = tuple(
            AffectedCustomerZone(
                section_id=mapping.section_id,
                customer_zone_id=mapping.customer_zone_id,
                customer_count=mapping.customer_count,
            )
            for mapping in sorted(
                configuration.customer_zone_mappings,
                key=lambda item: item.section_id,
            )
            if mapping.section_id in de_energised_set
        )
        affected = sum(mapping.customer_count for mapping in mappings)
        restored_delta = (
            max(previous.affected_customer_count - affected, 0)
            if previous is not None
            else 0
        )
        return OutageResult(
            configuration_id=topology.configuration_id,
            de_energised_section_ids=de_energised,
            affected_customer_zones=mappings,
            affected_customer_count=affected,
            restored_customer_delta=restored_delta,
        )
