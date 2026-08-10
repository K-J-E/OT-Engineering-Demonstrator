"""I1 package integrity: REQ-NET-001–011, REQ-CFG-001–003/006/008–010."""

import json
import shutil
from pathlib import Path

import pytest

from ot_demo.domain.enums import ConfigurationStatus, SwitchState
from ot_demo.infrastructure.configuration_loader import (
    ConfigurationIntegrityError,
    JsonConfigurationLoader,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def loader() -> JsonConfigurationLoader:
    return JsonConfigurationLoader(REPOSITORY_ROOT / "config/network")


@pytest.mark.i1
@pytest.mark.parametrize(
    ("directory", "configuration_id", "status"),
    [
        ("v1.0", "network-configuration-v1.0", ConfigurationStatus.DEFECTIVE_TEST_INPUT),
        ("v1.1", "network-configuration-v1.1", ConfigurationStatus.CORRECTED_BASELINE),
    ],
)
def test_package_loads_with_controlled_identity_and_hashes(
    loader: JsonConfigurationLoader,
    directory: str,
    configuration_id: str,
    status: ConfigurationStatus,
) -> None:
    loaded = loader.load(directory)

    assert loaded.catalog_entry.configuration_id == configuration_id
    assert loaded.catalog_entry.status is status
    assert len(loaded.catalog_entry.package_sha256) == 64
    assert len(loaded.catalog_entry.data_sha256) == 64
    assert len(loaded.catalog_entry.schema_sha256) == 64


@pytest.mark.i1
def test_network_model_values_and_stable_identifiers(loader: JsonConfigurationLoader) -> None:
    loaded = loader.load("v1.1").data
    feeders = {item.entity_id: item for item in loaded.feeders}
    sections = {item.entity_id: item for item in loaded.sections}
    devices = {item.entity_id: item for item in loaded.switching_devices}
    mappings = {item.section_id: item for item in loaded.customer_zone_mappings}

    assert [item.entity_id for item in loaded.sources] == ["ZS-01"]
    assert set(feeders) == {"FDR-A", "FDR-B"}
    assert set(sections) == {
        "SEC-A1", "SEC-A2", "SEC-A3", "SEC-A4",
        "SEC-B1", "SEC-B2", "SEC-B3", "SEC-B4",
    }
    assert set(devices) == {
        "BRK-A", "BRK-B", "SW-A12", "SW-A23", "SW-A34",
        "SW-B12", "SW-B23", "SW-B34", "TS-01",
    }
    assert feeders["FDR-A"].capacity_kw == 5500
    assert feeders["FDR-A"].normal_connected_load_kw == 3200
    assert feeders["FDR-B"].capacity_kw == 6000
    assert feeders["FDR-B"].normal_connected_load_kw == 4200
    assert sum(item.load_kw for item in sections.values() if item.feeder_id == "FDR-A") == 3200
    assert sum(item.load_kw for item in sections.values() if item.feeder_id == "FDR-B") == 4200
    assert sum(item.customer_count for item in mappings.values() if item.section_id.startswith("SEC-A")) == 850
    assert sum(item.customer_count for item in mappings.values() if item.section_id.startswith("SEC-B")) == 960
    assert devices["TS-01"].normal_state is SwitchState.OPEN
    assert all(
        device.normal_state is SwitchState.CLOSED
        for device_id, device in devices.items()
        if device_id != "TS-01"
    )
    assert all(device.monitored for device in devices.values())


@pytest.mark.i1
def test_package_loader_rejects_tampered_data(tmp_path: Path) -> None:
    controlled_root = tmp_path / "config/network"
    shutil.copytree(REPOSITORY_ROOT / "config/network", controlled_root)
    data_path = controlled_root / "v1.1/network.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    payload["sections"][0]["load_kw"] = 751
    data_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ConfigurationIntegrityError, match="data SHA-256 mismatch"):
        JsonConfigurationLoader(controlled_root).load("v1.1")
