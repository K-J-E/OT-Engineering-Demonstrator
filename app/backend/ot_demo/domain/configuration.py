"""Immutable network-configuration records and referential validation.

These records validate configuration shape and identity only. They do not build an
active graph or derive energisation, outage, restoration, or scenario behaviour.
"""

from collections import Counter
from typing import Annotated

from pydantic import Field, model_validator
from typing_extensions import Self

from .base import FrozenModel
from .enums import EdgeSemantics, SourceAvailability, SwitchState, SwitchingDeviceType
from .value_objects import EngineeringId, NonNegativeKilowatts, PositiveCustomerCount, SemanticVersion


class ZoneSubstation(FrozenModel):
    entity_id: EngineeringId
    name: str = Field(min_length=1, max_length=160)
    normal_source_availability: SourceAvailability


class Feeder(FrozenModel):
    entity_id: EngineeringId
    name: str = Field(min_length=1, max_length=160)
    source_id: EngineeringId
    source_breaker_id: EngineeringId
    capacity_kw: NonNegativeKilowatts
    normal_connected_load_kw: NonNegativeKilowatts
    section_ids: Annotated[tuple[EngineeringId, ...], Field(min_length=1)]
    sectionalising_switch_ids: Annotated[tuple[EngineeringId, ...], Field(min_length=1)]


class DistributionSection(FrozenModel):
    entity_id: EngineeringId
    name: str = Field(min_length=1, max_length=160)
    feeder_id: EngineeringId
    load_kw: NonNegativeKilowatts


class SwitchingDevice(FrozenModel):
    entity_id: EngineeringId
    name: str = Field(min_length=1, max_length=160)
    device_type: SwitchingDeviceType
    feeder_id: EngineeringId | None
    normal_state: SwitchState
    monitored: bool

    @model_validator(mode="after")
    def validate_feeder_ownership(self) -> Self:
        if self.device_type is SwitchingDeviceType.TIE_SWITCH and self.feeder_id is not None:
            raise ValueError("a tie switch is not owned by one feeder")
        if self.device_type is not SwitchingDeviceType.TIE_SWITCH and self.feeder_id is None:
            raise ValueError("breaker and sectionalising switch records require feeder_id")
        return self


class ConnectivityEdge(FrozenModel):
    edge_id: EngineeringId
    endpoint_a_id: EngineeringId
    endpoint_b_id: EngineeringId
    semantics: EdgeSemantics

    @model_validator(mode="after")
    def reject_self_connection(self) -> Self:
        if self.endpoint_a_id == self.endpoint_b_id:
            raise ValueError("connectivity edge endpoints must be different")
        return self


class CustomerZoneMapping(FrozenModel):
    section_id: EngineeringId
    customer_zone_id: EngineeringId
    customer_count: PositiveCustomerCount


class NetworkConfigurationData(FrozenModel):
    schema_version: SemanticVersion
    sources: Annotated[tuple[ZoneSubstation, ...], Field(min_length=1)]
    feeders: Annotated[tuple[Feeder, ...], Field(min_length=1)]
    sections: Annotated[tuple[DistributionSection, ...], Field(min_length=1)]
    switching_devices: Annotated[tuple[SwitchingDevice, ...], Field(min_length=1)]
    connectivity_edges: Annotated[tuple[ConnectivityEdge, ...], Field(min_length=1)]
    customer_zone_mappings: Annotated[tuple[CustomerZoneMapping, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_references_and_consistency(self) -> Self:
        source_ids = {item.entity_id for item in self.sources}
        feeder_ids = {item.entity_id for item in self.feeders}
        section_ids = {item.entity_id for item in self.sections}
        device_ids = {item.entity_id for item in self.switching_devices}
        engineering_entity_ids = [
            *(item.entity_id for item in self.sources),
            *(item.entity_id for item in self.feeders),
            *(item.entity_id for item in self.sections),
            *(item.entity_id for item in self.switching_devices),
        ]
        duplicates = sorted(item for item, count in Counter(engineering_entity_ids).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate engineering entity IDs: {duplicates}")

        edge_ids = [edge.edge_id for edge in self.connectivity_edges]
        duplicate_edges = sorted(item for item, count in Counter(edge_ids).items() if count > 1)
        if duplicate_edges:
            raise ValueError(f"duplicate connectivity edge IDs: {duplicate_edges}")

        devices_by_id = {item.entity_id: item for item in self.switching_devices}
        sections_by_id = {item.entity_id: item for item in self.sections}

        for feeder in self.feeders:
            if feeder.source_id not in source_ids:
                raise ValueError(f"{feeder.entity_id} references unknown source {feeder.source_id}")
            breaker = devices_by_id.get(feeder.source_breaker_id)
            if breaker is None or breaker.device_type is not SwitchingDeviceType.FEEDER_SOURCE_BREAKER:
                raise ValueError(f"{feeder.entity_id} source breaker reference is invalid")
            if breaker.feeder_id != feeder.entity_id:
                raise ValueError(f"{feeder.entity_id} source breaker ownership is inconsistent")
            if set(feeder.section_ids) != {
                section.entity_id for section in self.sections if section.feeder_id == feeder.entity_id
            }:
                raise ValueError(f"{feeder.entity_id} section list is inconsistent")
            if set(feeder.sectionalising_switch_ids) != {
                device.entity_id
                for device in self.switching_devices
                if device.feeder_id == feeder.entity_id
                and device.device_type is SwitchingDeviceType.SECTIONALISING_SWITCH
            }:
                raise ValueError(f"{feeder.entity_id} sectionalising switch list is inconsistent")

        for section in self.sections:
            if section.feeder_id not in feeder_ids:
                raise ValueError(f"{section.entity_id} references unknown feeder {section.feeder_id}")

        for device in self.switching_devices:
            if device.feeder_id is not None and device.feeder_id not in feeder_ids:
                raise ValueError(f"{device.entity_id} references unknown feeder {device.feeder_id}")

        terminal_ids = source_ids | section_ids
        incident_counts: Counter[str] = Counter()
        for edge in self.connectivity_edges:
            endpoints = {edge.endpoint_a_id, edge.endpoint_b_id}
            device_endpoints = endpoints & device_ids
            terminal_endpoints = endpoints & terminal_ids
            if len(device_endpoints) != 1 or len(terminal_endpoints) != 1:
                raise ValueError(
                    f"{edge.edge_id} must connect one switching device to one source or section"
                )
            incident_counts.update(device_endpoints)
        invalid_incidence = sorted(
            device_id for device_id in device_ids if incident_counts[device_id] != 2
        )
        if invalid_incidence:
            raise ValueError(
                "each switching device requires exactly two configured terminal edges: "
                f"{invalid_incidence}"
            )

        mapping_sections = [mapping.section_id for mapping in self.customer_zone_mappings]
        mapping_zones = [mapping.customer_zone_id for mapping in self.customer_zone_mappings]
        if len(mapping_sections) != len(set(mapping_sections)):
            raise ValueError("a section may have only one customer-zone mapping")
        if len(mapping_zones) != len(set(mapping_zones)):
            raise ValueError("customer-zone IDs must be unique")
        unknown_mapping_sections = sorted(set(mapping_sections) - section_ids)
        if unknown_mapping_sections:
            raise ValueError(f"customer mappings reference unknown sections: {unknown_mapping_sections}")
        if set(mapping_sections) != set(sections_by_id):
            raise ValueError("every represented section requires one customer-zone mapping")

        return self
