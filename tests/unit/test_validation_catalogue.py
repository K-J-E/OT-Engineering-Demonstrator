"""Accepted Step 9 catalogue and 124-row RTM machine-counterpart gates."""

from collections import Counter
from pathlib import Path

import pytest

from ot_demo.domain.enums import EvidenceClass
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from ot_demo.modules.validation.catalogue import (
    ValidationCatalogueError,
    ValidationCatalogueLoader,
    ValidationCatalogueResolver,
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

# Independent test oracle calculated directly from the accepted Validation Plan
# v1.0 Section 15 RTM table (286 sorted test↔requirement relationships). It is
# deliberately not derived from validation/test-definitions/catalogue.json.
ACCEPTED_SECTION_15_RTM_SHA256 = (
    "53ecf30a7f59bb294410a1b5abbd0b9e014f02ea294f674d9a0ba22ddaf604c8"
)


def relationship_fingerprint(relationships: set[tuple[str, str]]) -> str:
    return sha256_bytes(canonical_json_bytes(sorted(relationships)))


def assert_exact_section_15_relationship(
    relationships: set[tuple[str, str]],
) -> None:
    assert len(relationships) == 286
    assert relationship_fingerprint(relationships) == ACCEPTED_SECTION_15_RTM_SHA256


@pytest.mark.i5
def test_catalogue_contains_exactly_the_24_accepted_definitions() -> None:
    loaded = ValidationCatalogueLoader(CATALOGUE).load()

    assert len(loaded) == 24
    assert {item.definition.test_id for item in loaded} == ACCEPTED_TEST_IDS
    versions = {item.definition.test_id: item.definition.version for item in loaded}
    assert versions["VT-EXP-ALL-001"] == "1.1"
    assert versions["VT-EXP-ROLE-001"] == "1.1"
    assert all(
        version == "1.0"
        for test_id, version in versions.items()
        if test_id not in {"VT-EXP-ALL-001", "VT-EXP-ROLE-001"}
    )
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
def test_catalogue_matches_exact_accepted_section_15_rtm_relationship() -> None:
    definitions = ValidationCatalogueLoader(CATALOGUE).load()
    relationships = {
        (item.definition.test_id, requirement_id)
        for item in definitions
        for requirement_id in item.definition.requirement_ids
    }

    assert_exact_section_15_relationship(relationships)


@pytest.mark.i5
def test_wrong_test_mapping_fails_even_when_all_124_requirements_remain() -> None:
    definitions = ValidationCatalogueLoader(CATALOGUE).load()
    relationships = {
        (item.definition.test_id, requirement_id)
        for item in definitions
        for requirement_id in item.definition.requirement_ids
    }
    mutated = set(relationships)
    mutated.remove(("VT-CFG-BASE-001", "REQ-NET-001"))
    mutated.add(("VT-NFR-REVIEW-001", "REQ-NET-001"))

    assert len({requirement_id for _test_id, requirement_id in mutated}) == 124
    assert len(mutated) == len(relationships) == 286
    with pytest.raises(AssertionError):
        assert_exact_section_15_relationship(mutated)


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


@pytest.mark.i5
def test_dc004_preserves_v10_and_promotes_exact_case_sets_with_unchanged_rtm() -> None:
    history = CATALOGUE.parent / "history/v1.0/catalogue.json"
    history_manifest = history.with_name("manifest.json")
    assert sha256_file(history) == (
        "e4b1fb616fb4f0605c19129f18746bfae48278ed35fbb971aac4f690fd32bcc1"
    )
    assert sha256_file(history_manifest) == (
        "8bc2f16e6dd475a56a5c5dc3ed52ca46caafc77c08bd858de3f2d748c4dfe714"
    )
    resolver = ValidationCatalogueResolver(CATALOGUE, (history,))
    all_cases = resolver.get("VT-EXP-ALL-001").definition.constituent_cases
    role_cases = resolver.get("VT-EXP-ROLE-001").definition.constituent_cases
    assert tuple(item.case_id for item in all_cases) == (
        "EXP-ALL-A1",
        "EXP-ALL-A2",
        "EXP-ALL-A3",
        "EXP-ALL-A4-FRESH",
        "EXP-ALL-B1",
        "EXP-ALL-B2",
        "EXP-ALL-B3",
        "EXP-ALL-B4",
        "EXP-ALL-A4-STALE-OPEN",
    )
    assert tuple(item.case_id for item in role_cases) == (
        "EXP-ROLE-A2",
        "EXP-ROLE-B2",
        "EXP-ROLE-A1",
        "EXP-ROLE-A4",
    )
    forbidden_provenance = {
        "application_build_id",
        "catalogue_sha256",
        "test_definition_sha256",
        "case_definition_sha256",
    }
    assert all(
        forbidden_provenance.isdisjoint(item.comparison_expected_values)
        for item in (*all_cases, *role_cases)
    )
    relationships = {
        (item.definition.test_id, requirement_id)
        for item in resolver.load()
        for requirement_id in item.definition.requirement_ids
    }
    assert_exact_section_15_relationship(relationships)


@pytest.mark.i5
def test_historical_resolver_selects_exact_stored_identity_and_rejects_tamper(
    tmp_path: Path,
) -> None:
    history = CATALOGUE.parent / "history/v1.0/catalogue.json"
    resolver = ValidationCatalogueResolver(CATALOGUE, (history,))
    old = ValidationCatalogueLoader(history).get("VT-EXP-ALL-001")
    current = resolver.get("VT-EXP-ALL-001")
    resolved = resolver.resolve(
        test_id=old.definition.test_id,
        catalogue_version=old.catalogue_version,
        catalogue_sha256=old.catalogue_sha256,
        test_definition_version=old.definition.version,
        test_definition_sha256=old.definition_sha256,
    )
    assert resolved == old
    assert old.definition_sha256 != current.definition_sha256
    assert old.catalogue_sha256 != current.catalogue_sha256

    tampered_directory = tmp_path / "v1.0"
    tampered_directory.mkdir()
    tampered = tampered_directory / "catalogue.json"
    tampered.write_bytes(history.read_bytes().replace(b"SEC-A2", b"SEC-A9", 1))
    tampered.with_name("manifest.json").write_bytes(
        history.with_name("manifest.json").read_bytes()
    )
    with pytest.raises(ValidationCatalogueError, match="SHA-256 mismatch"):
        ValidationCatalogueResolver(CATALOGUE, (tampered,))
