"""QA-051 definition-owned normalisation conformance."""

import json
from pathlib import Path

import pytest

from ot_demo.modules.validation.normalisation import (
    NormalisationError,
    SUPPORTED_NORMALISATION_PROFILES,
    normalise,
)


ROOT = Path(__file__).resolve().parents[2]


def test_exact_catalogue_normalisation_registry_is_executable() -> None:
    catalogue = json.loads(
        (ROOT / "validation/test-definitions/catalogue.json").read_text()
    )
    profiles = {
        criterion["normalisation"]
        for definition in catalogue["definitions"]
        for method in (
            ([definition["determination_method"]] if definition.get("determination_method") else [])
            + [
                case["determination_method"]
                for case in definition.get("constituent_cases", [])
                if case.get("determination_method")
            ]
        )
        for criterion in method["criteria"]
    }
    assert profiles == SUPPORTED_NORMALISATION_PROFILES
    with pytest.raises(NormalisationError, match="unsupported"):
        normalise("implementation-selected profile", 1, expected=False)


def test_numeric_units_precision_boolean_and_controlled_sets() -> None:
    assert normalise("6000 kW integer", "Capacity is 6,000 kW.", expected=True) == 6000
    assert normalise("6000 kW integer", 6000, expected=False) == 6000
    assert normalise(
        "MW two decimals; percent one decimal",
        "Result is 6.00 MW and 100.0%.",
        expected=True,
    ) == (6, 100)
    assert normalise(
        "MW two decimals; percent one decimal",
        {"resulting_load_mw": "6.00", "resulting_loading_percent": "100.0"},
        expected=False,
    ) == (6, 100)
    assert normalise("true", "controlled proposition", expected=True) is True
    assert normalise("true", True, expected=False) is True
    assert normalise("empty; stable identity sort", "none", expected=True) == ()
    assert normalise("empty; stable identity sort", set(), expected=False) == ()


def test_set_canonicalisation_and_ordered_sequence_treatment_are_distinct() -> None:
    left = normalise("empty; stable record-name sort", ["B", "A"], expected=False)
    right = normalise("empty; stable record-name sort", ["A", "B"], expected=False)
    assert left == right
    assert normalise("exact canonical representation", ["B", "A"], expected=False) != normalise(
        "exact canonical representation", ["A", "B"], expected=False
    )


def test_det03_excludes_only_controlled_generated_identities() -> None:
    pair = {
        "left": {
            "scenario_run_id": "run-a",
            "validation_execution_id": "execution-a",
            "engineering_output": {"affected_customer_count": 850},
        },
        "right": {
            "scenario_run_id": "run-b",
            "validation_execution_id": "execution-b",
            "engineering_output": {"affected_customer_count": 850},
        },
    }
    assert normalise(
        "controlled exclusion profile", pair, expected=False
    ) == "CONTROLLED_OUTPUTS_EQUAL"
    changed = {
        **pair,
        "right": {
            **pair["right"],
            "engineering_output": {"affected_customer_count": 400},
        },
    }
    assert normalise(
        "controlled exclusion profile", changed, expected=False
    ) != "CONTROLLED_OUTPUTS_EQUAL"
