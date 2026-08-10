"""I1 controlled-difference test: REQ-CFG-001–003/008–010; VT-CFG-BASE-001."""

from pathlib import Path

import pytest

from ot_demo.infrastructure.configuration_comparison import (
    ConfigurationDifference,
    compare_engineering_content,
)
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.i1
def test_v1_0_and_v1_1_have_exactly_one_engineering_content_difference() -> None:
    loader = JsonConfigurationLoader(REPOSITORY_ROOT / "config/network")
    defective = loader.load("v1.0")
    corrected = loader.load("v1.1")

    assert compare_engineering_content(defective.data, corrected.data) == (
        ConfigurationDifference(
            path="connectivity_edges.EDGE-SW-A23-1.endpoint_a_id",
            before="SEC-B3",
            after="SEC-A2",
        ),
    )
