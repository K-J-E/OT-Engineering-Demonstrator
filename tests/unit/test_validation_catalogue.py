"""Accepted Step 9 catalogue and 124-row RTM machine-counterpart gates."""

from collections import Counter
from pathlib import Path

import pytest

from ot_demo.domain.enums import EvidenceClass
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ot_demo.modules.validation.catalogue import (
    ValidationCatalogueError,
    ValidationCatalogueLoader,
)


ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "validation/test-definitions/catalogue.json"

ACCEPTED_TEST_IDS = {
    "VT-CFG-BASE-001",
    "VT-TOP-NORMAL-001",
    "VT-FML-N0-N5-001",
    "VT-TOP-DEF-001",
    "VT-CFG-INV-001",
    "VT-TEL-FRESH-001",
    "VT-TEL-STALE-001",
    "VT-TEL-UNCERTAIN-001",
    "VT-TEL-BAD-001",
    "VT-TEL-FUTURE-001",
    "VT-RST-ISOLATION-001",
    "VT-RST-SOURCE-001",
    "VT-RST-RADIAL-001",
    "VT-RST-CAP-EQUAL-001",
    "VT-RST-CAP-OVER-001",
    "VT-RST-BINDING-001",
    "VT-ALM-EVT-001",
    "VT-VAL-RECORD-001",
    "VT-EXP-ALL-001",
    "VT-EXP-ROLE-001",
    "VT-EXP-SEPARATION-001",
    "VT-NFR-REVIEW-001",
    "VT-DET-REPEAT-001",
    "VT-PKG-EVIDENCE-001",
}


@pytest.mark.i5
def test_catalogue_contains_exactly_the_24_accepted_definitions() -> None:
    loaded = ValidationCatalogueLoader(CATALOGUE).load()

    assert len(loaded) == 24
    assert {item.definition.test_id for item in loaded} == ACCEPTED_TEST_IDS
    assert all(item.definition.version == "1.0" for item in loaded)
    assert all(len(item.definition_sha256) == 64 for item in loaded)
    assert len({item.catalogue_sha256 for item in loaded}) == 1


@pytest.mark.i5
def test_catalogue_preserves_exact_124_requirement_coverage() -> None:
    definitions = ValidationCatalogueLoader(CATALOGUE).load()
    requirement_ids = {
        requirement_id
        for item in definitions
        for requirement_id in item.definition.requirement_ids
    }
    group_counts = Counter(
        requirement_id.split("-")[1] for requirement_id in requirement_ids
    )

    assert len(requirement_ids) == 124
    assert group_counts == {
        "NET": 11,
        "TOP": 9,
        "TEL": 10,
        "ALM": 5,
        "OUT": 7,
        "RST": 29,
        "EXP": 7,
        "EVT": 11,
        "VAL": 14,
        "CFG": 12,
        "NFR": 9,
    }
    assert all(
        item.definition.requirement_ids
        and item.definition.source_references
        and item.definition.checkpoint_obligations
        and item.definition.evidence_requirements
        for item in definitions
    )


@pytest.mark.i5
def test_controlled_expected_results_and_evidence_classes_are_not_weakened() -> None:
    loader = ValidationCatalogueLoader(CATALOGUE)
    defect = loader.get("VT-TOP-DEF-001").definition
    stale = loader.get("VT-TEL-STALE-001").definition
    exploration = loader.get("VT-EXP-ALL-001").definition

    assert "v1.0 FAIL" in defect.expected_result_statement
    assert "400 affected" in defect.expected_result_statement
    assert "v1.1 PASS" in defect.expected_result_statement
    assert "850 affected" in defect.expected_result_statement
    assert defect.comparison_expected_values == {
        "de_energised_section_ids": ["SEC-A1", "SEC-A2", "SEC-A3", "SEC-A4"],
        "affected_customer_count": 850,
        "section_source_feeder_ids": {
            "SEC-A1": [],
            "SEC-A2": [],
            "SEC-A3": [],
            "SEC-A4": [],
        },
    }
    assert "Operational result is BLOCKED" in stale.expected_result_statement
    assert "validation verdict is PASS" in stale.expected_result_statement
    assert stale.evidence_class is EvidenceClass.FORMAL
    assert exploration.evidence_class is EvidenceClass.EXPLORATORY


@pytest.mark.i5
def test_definition_hash_is_over_canonical_definition_content() -> None:
    loaded = ValidationCatalogueLoader(CATALOGUE).get("VT-VAL-RECORD-001")

    assert loaded.definition_sha256 == sha256_bytes(
        canonical_json_bytes(loaded.definition.model_dump(mode="json"))
    )


@pytest.mark.i5
def test_catalogue_byte_tamper_is_rejected_by_controlled_manifest(tmp_path: Path) -> None:
    copied_catalogue = tmp_path / "catalogue.json"
    copied_manifest = tmp_path / "manifest.json"
    copied_catalogue.write_bytes(
        CATALOGUE.read_bytes().replace(b"400 affected", b"401 affected", 1)
    )
    copied_manifest.write_bytes(CATALOGUE.with_name("manifest.json").read_bytes())

    with pytest.raises(ValidationCatalogueError, match="SHA-256 mismatch"):
        ValidationCatalogueLoader(copied_catalogue).load()
