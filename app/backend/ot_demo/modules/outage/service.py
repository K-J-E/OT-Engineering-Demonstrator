"""OMS-style outage/customer consequence processing from derived energisation."""

from ..configuration.models import LoadedConfiguration
from ..topology.models import TopologyResult
from .models import AffectedCustomerZone, OutageResult


class OutageConfigurationMismatch(ValueError):
    """Raised when outage inputs do not share one controlled configuration identity."""


class OutageService:
    """Map de-energised sections to configured customer zones without fault inference."""

    def calculate(
        self,
        loaded: LoadedConfiguration,
        topology: TopologyResult,
        *,
        previous: OutageResult | None = None,
    ) -> OutageResult:
        configuration_id = loaded.catalog_entry.configuration_id
        if topology.configuration_id != configuration_id:
            raise OutageConfigurationMismatch(
                "topology and customer mappings use different configuration identities"
            )
        if previous is not None and previous.configuration_id != configuration_id:
            raise OutageConfigurationMismatch(
                "previous and current outage states use different configurations"
            )

        configuration = loaded.data
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
        current_zone_identities = {
            (zone.section_id, zone.customer_zone_id) for zone in mappings
        }
        restored_delta = 0
        if previous is not None:
            restored_delta = sum(
                zone.customer_count
                for zone in previous.affected_customer_zones
                if (zone.section_id, zone.customer_zone_id)
                not in current_zone_identities
            )
        return OutageResult(
            configuration_id=configuration_id,
            de_energised_section_ids=de_energised,
            affected_customer_zones=mappings,
            affected_customer_count=affected,
            restored_customer_delta=restored_delta,
        )
