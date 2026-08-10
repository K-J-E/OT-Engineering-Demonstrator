"""I2 conformance gates for topology, load and OMS customer consequences."""

from pathlib import Path

import pytest

from ot_demo.domain.enums import FreshnessStatus, SwitchState, TelemetryQuality
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.modules.configuration.models import LoadedConfiguration
from ot_demo.modules.outage import OutageService
from ot_demo.modules.topology import BoundaryObservation, TopologyInputs, TopologyService


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def loader() -> JsonConfigurationLoader:
    return JsonConfigurationLoader(REPOSITORY_ROOT / "config/network")


def calculate(
    loaded: LoadedConfiguration,
    *,
    device_overrides: dict[str, SwitchState] | None = None,
    active_fault: str | None = None,
):
    service = TopologyService()
    normal = service.normal_inputs(loaded.data)
    states = dict(normal.device_states)
    states.update(device_overrides or {})
    observations = (
        {
            device.entity_id: BoundaryObservation(
                device_id=device.entity_id,
                observed_state=states[device.entity_id],
                quality=TelemetryQuality.GOOD,
                freshness_status=FreshnessStatus.FRESH,
            )
            for device in loaded.data.switching_devices
        }
        if active_fault
        else {}
    )
    topology = service.calculate(
        loaded,
        TopologyInputs(
            device_states=states,
            source_availability=dict(normal.source_availability),
            faulted_section_ids=(frozenset({active_fault}) if active_fault else frozenset()),
            active_fault_section_id=active_fault,
            boundary_observations=observations,
        ),
    )
    outage = OutageService().calculate(loaded.data, topology)
    return topology, outage


@pytest.mark.i2
def test_v11_normal_answer_key_has_no_outage(loader: JsonConfigurationLoader) -> None:
    topology, outage = calculate(loader.load("v1.1"))

    assert all(section.energised for section in topology.sections)
    assert outage.de_energised_section_ids == ()
    assert outage.affected_customer_zones == ()
    assert outage.affected_customer_count == 0


@pytest.mark.i2
def test_v11_breaker_trip_derives_approved_n1_850_customer_outage(
    loader: JsonConfigurationLoader,
) -> None:
    topology, outage = calculate(
        loader.load("v1.1"),
        device_overrides={"BRK-A": SwitchState.OPEN},
        active_fault="SEC-A2",
    )
    sections = {state.section_id: state for state in topology.sections}
    loads = {item.feeder_id: item for item in topology.feeder_loads}

    assert outage.de_energised_section_ids == (
        "SEC-A1", "SEC-A2", "SEC-A3", "SEC-A4"
    )
    assert tuple(zone.customer_zone_id for zone in outage.affected_customer_zones) == (
        "CZ-A1", "CZ-A2", "CZ-A3", "CZ-A4"
    )
    assert outage.affected_customer_count == 850
    assert "EDGE-BRK-A-1" not in topology.active_edge_ids
    assert "EDGE-BRK-A-2" not in topology.active_edge_ids
    assert topology.available_source_feeder_ids == ("FDR-A", "FDR-B")
    assert topology.active_source_feeder_ids == ("FDR-B",)
    assert all(not sections[f"SEC-A{index}"].energised for index in range(1, 5))
    assert all(sections[f"SEC-B{index}"].energised for index in range(1, 5))
    assert loads["FDR-A"].configured_normal_load_kw == 3200
    assert loads["FDR-A"].currently_supplied_load_kw == 0
    assert loads["FDR-B"].configured_normal_load_kw == 4200
    assert loads["FDR-B"].currently_supplied_load_kw == 4200


@pytest.mark.i2
def test_v10_same_breaker_trip_derives_defective_400_customer_consequence(
    loader: JsonConfigurationLoader,
) -> None:
    topology, outage = calculate(
        loader.load("v1.0"),
        device_overrides={"BRK-A": SwitchState.OPEN},
        active_fault="SEC-A2",
    )
    sections = {state.section_id: state for state in topology.sections}
    loads = {item.feeder_id: item for item in topology.feeder_loads}

    assert outage.de_energised_section_ids == ("SEC-A1", "SEC-A2")
    assert tuple(zone.customer_zone_id for zone in outage.affected_customer_zones) == (
        "CZ-A1", "CZ-A2"
    )
    assert outage.affected_customer_count == 400
    assert sections["SEC-A3"].source_feeder_ids == ("FDR-B",)
    assert sections["SEC-A4"].source_feeder_ids == ("FDR-B",)
    assert sections["SEC-A3"].source_paths[0].node_ids == (
        "ZS-01", "BRK-B", "SEC-B1", "SW-B12", "SEC-B2", "SW-B23",
        "SEC-B3", "SW-A23", "SEC-A3",
    )
    assert loads["FDR-A"].configured_normal_load_kw == 3200
    assert loads["FDR-A"].currently_supplied_load_kw == 0
    assert loads["FDR-B"].configured_normal_load_kw == 4200
    assert loads["FDR-B"].currently_supplied_load_kw == 5700


@pytest.mark.i2
def test_v10_normal_uses_configuration_derived_load_not_nominal_load(
    loader: JsonConfigurationLoader,
) -> None:
    topology, outage = calculate(loader.load("v1.0"))
    loads = {item.feeder_id: item for item in topology.feeder_loads}

    assert outage.affected_customer_count == 0
    assert loads["FDR-A"].configured_normal_load_kw == 3200
    assert loads["FDR-A"].currently_supplied_load_kw == 1700
    assert loads["FDR-B"].configured_normal_load_kw == 4200
    assert loads["FDR-B"].currently_supplied_load_kw == 5700


@pytest.mark.i2
def test_outage_recalculation_reports_restored_customer_delta(
    loader: JsonConfigurationLoader,
) -> None:
    loaded = loader.load("v1.1")
    n1_topology, n1_outage = calculate(
        loaded,
        device_overrides={"BRK-A": SwitchState.OPEN},
        active_fault="SEC-A2",
    )
    normal_topology, _ = calculate(loaded)
    restored = OutageService().calculate(
        loaded.data,
        normal_topology,
        previous=n1_outage,
    )

    assert n1_topology.configuration_id == normal_topology.configuration_id
    assert restored.affected_customer_count == 0
    assert restored.restored_customer_delta == 850
