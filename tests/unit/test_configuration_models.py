"""I1 schema tests: REQ-NET-001–011, REQ-NFR-002/004/009; VT-CFG-BASE-001."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ot_demo.domain.configuration import NetworkConfigurationData
from ot_demo.modules.configuration.models import ConfigurationManifest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.i1
def test_checked_in_json_schema_matches_strict_domain_model() -> None:
    expected = NetworkConfigurationData.model_json_schema()
    actual = json.loads(
        (
            REPOSITORY_ROOT
            / "config/network/schema/v1/network-configuration.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert actual == expected


@pytest.mark.i1
def test_configuration_records_are_immutable() -> None:
    payload = (
        REPOSITORY_ROOT / "config/network/v1.1/network.json"
    ).read_bytes()
    configuration = NetworkConfigurationData.model_validate_json(payload, strict=True)

    with pytest.raises(ValidationError):
        configuration.schema_version = "2.0.0"  # type: ignore[misc]


@pytest.mark.i1
def test_unknown_configuration_field_is_rejected() -> None:
    payload = json.loads(
        (REPOSITORY_ROOT / "config/network/v1.1/network.json").read_text(
            encoding="utf-8"
        )
    )
    payload["stored_energisation_result"] = "ENERGISED"

    with pytest.raises(ValidationError):
        NetworkConfigurationData.model_validate(payload, strict=True)


@pytest.mark.i1
def test_manifest_rejects_configuration_id_that_does_not_match_version() -> None:
    payload = json.loads(
        (REPOSITORY_ROOT / "config/network/v1.1/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    payload["configuration_id"] = "network-configuration-v1.0"

    with pytest.raises(
        ValidationError,
        match="configuration_id must correspond to the declared version",
    ):
        ConfigurationManifest.model_validate_json(json.dumps(payload), strict=True)
