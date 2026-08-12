"""Independent static gates for the promoted DC-006 catalogue revision."""

import json
import hashlib
from pathlib import Path

import pytest

from ot_demo.domain.enums import (
    DeterminationContextKind,
    DeterminationOperator,
    OperationalEventType,
)
from ot_demo.infrastructure.hashing import sha256_file
from ot_demo.modules.validation.catalogue import ValidationCatalogueLoader
from ot_demo.modules.validation.models import ValidationCatalogue


ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS = ROOT / "validation/test-definitions"
CATALOGUE = DEFINITIONS / "catalogue.json"
CRITERION_REQUIREMENT_FINGERPRINT = (
    "cd08f985a1ff2826da5e66f9b26b6723bd179bb9d59b4180b0bac93eacedbf9b"
)
ACCEPTED_CATALOGUE_AUTHORITY = (
    "Accepted Validation Plan v1.4 Section 21 / DC-006 + DC-007"
)


@pytest.mark.dc006
def test_v11_is_byte_identical_history_and_v12_is_active() -> None:
    assert sha256_file(DEFINITIONS / "history/v1.1/catalogue.json") == (
        "28bfe69131c40857c08f175abba42be3eb36514924b6de416b4e72bbefe35865"
    )
    assert sha256_file(DEFINITIONS / "history/v1.1/manifest.json") == (
        "45cb015f58af1d453be0255cdbbb857c08901877c416e830f26bb2fe6ecf60a3"
    )
    revisions = json.loads((DEFINITIONS / "revisions.json").read_text())
    assert revisions["active_catalogue_version"] == "1.2"
    assert [item["catalogue_version"] for item in revisions["revisions"]] == [
        "1.0",
        "1.1",
        "1.2",
    ]
    assert revisions["revisions"][-1] == {
        "catalogue_version": "1.2",
        "catalogue_sha256": "f224a8826f4c02dd0c4bb5c22f3ab7351cd4eb17106b78541aeaf3b1c1d9cbe4",
        "manifest_sha256": "ef30f4e17a67dadefce5141edb3335544804bf512e4d76e85f351bc4fa0ee4c9",
        "catalogue_path": "catalogue.json",
        "status": "ACTIVE_PENDING_INDEPENDENT_REVIEW",
    }
    assert revisions["superseded_unaccepted_candidates"] == [
        {
            "catalogue_version": "1.2",
            "catalogue_sha256": "51c6079aeecdb04e11ad1fe9aa3b293e8517fbc7e961c2f1520864d7eada6de3",
            "manifest_sha256": "a9b7b91e903d1277433a049b99ec9a0324e0b32cd59a3bd8f24899ef86f49754",
            "status": "SUPERSEDED_UNACCEPTED_CANDIDATE",
            "reason": "Replaced before acceptance by the DC-007 current-run provenance correction.",
        },
        {
            "catalogue_version": "1.2",
            "catalogue_sha256": "2ebe3400a480fcd31c9317551316d20df4b1d828eb325cf131c73ee13ec970a1",
            "manifest_sha256": "4e7bd40a7e44d97d6cd995011f18d1257ed58f8cc1be57329c04123aa04fed42",
            "status": "SUPERSEDED_UNACCEPTED_CANDIDATE",
            "reason": "Superseded before acceptance because the active catalogue authority metadata still identified Validation Plan v1.3 after DC-007/Validation Plan v1.4 adoption.",
        },
    ]


@pytest.mark.dc006
def test_active_catalogue_names_exact_accepted_v14_dc007_authority() -> None:
    payload = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    assert payload["authority"] == ACCEPTED_CATALOGUE_AUTHORITY


@pytest.mark.dc006
def test_exact_method_criterion_context_operator_and_fixture_counts() -> None:
    definitions = ValidationCatalogueLoader(CATALOGUE).load()
    methods = [
        method
        for loaded in definitions
        for method in (
            (loaded.definition.determination_method,)
            if loaded.definition.determination_method is not None
            else tuple(case.determination_method for case in loaded.definition.constituent_cases)
        )
    ]
    assert len(methods) == 35
    assert sum(len(method.criteria) for method in methods) == 214
    assert sum(
        len(method.criteria)
        for method in methods
        if method.case_id is None
    ) == 147
    assert sum(
        len(method.criteria)
        for method in methods
        if method.case_id is not None
    ) == 67
    assert {method.context_kind for method in methods} == set(DeterminationContextKind)
    assert {
        criterion.operator for method in methods for criterion in method.criteria
    } <= set(DeterminationOperator)
    fixtures = [method.controlled_fixture for method in methods if method.controlled_fixture]
    assert len(fixtures) == 8
    assert all(
        "SCENARIO_RUN" not in role
        for method in methods
        if method.controlled_fixture
        for role in method.required_context_roles
    )


@pytest.mark.dc006
def test_exact_accepted_criterion_to_requirement_relationship_fingerprint() -> None:
    """Protect the reviewed 214-definition mapping independently of runtime unions."""

    definitions = ValidationCatalogueLoader(CATALOGUE).load()
    relationships = sorted(
        (method.test_id, method.case_id or "", criterion.criterion_id, requirement_id)
        for loaded in definitions
        for method in (
            (loaded.definition.determination_method,)
            if loaded.definition.determination_method is not None
            else tuple(case.determination_method for case in loaded.definition.constituent_cases)
        )
        for criterion in method.criteria
        for requirement_id in criterion.requirement_ids
    )
    assert len(relationships) == 676
    payload = "\n".join("|".join(item) for item in relationships).encode("utf-8")
    assert hashlib.sha256(payload).hexdigest() == CRITERION_REQUIREMENT_FINGERPRINT


@pytest.mark.dc006
def test_catalogue_rejects_unknown_composite_case_even_if_counts_are_preserved() -> None:
    payload = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    parent = next(
        item for item in payload["definitions"] if item["test_id"] == "VT-EXP-ROLE-001"
    )
    parent["constituent_cases"][0]["case_id"] = "EXP-ROLE-UNKNOWN"
    parent["constituent_cases"][0]["determination_method"]["case_id"] = "EXP-ROLE-UNKNOWN"
    for criterion in parent["constituent_cases"][0]["determination_method"]["criteria"]:
        criterion["case_id"] = "EXP-ROLE-UNKNOWN"
        criterion["criterion_sha256"] = _definition_hash(criterion, "criterion_sha256")
    method = parent["constituent_cases"][0]["determination_method"]
    method["method_sha256"] = _definition_hash(method, "method_sha256")
    with pytest.raises(ValueError, match="required constituent-case set is not exact"):
        ValidationCatalogue.model_validate_json(json.dumps(payload), strict=True)


def _definition_hash(value: dict, hash_field: str) -> str:
    controlled = {key: item for key, item in value.items() if key != hash_field}
    encoded = json.dumps(
        controlled, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@pytest.mark.dc006
def test_exact_direct_and_composite_requirement_unions() -> None:
    definitions = ValidationCatalogueLoader(CATALOGUE).load()
    for loaded in definitions:
        definition = loaded.definition
        parent = set(definition.requirement_ids)
        if definition.determination_method is not None:
            assert {
                requirement
                for criterion in definition.determination_method.criteria
                for requirement in criterion.requirement_ids
            } == parent
            continue
        union: set[str] = set()
        for case in definition.constituent_cases:
            assert case.determination_method is not None
            case_union = {
                requirement
                for criterion in case.determination_method.criteria
                for requirement in criterion.requirement_ids
            }
            assert case_union <= parent
            union |= case_union
        assert union == parent


@pytest.mark.dc006
def test_exact_nfr_surface_structural_and_event_registries() -> None:
    payload = json.loads(CATALOGUE.read_text())
    registries = payload["controlled_registries"]
    assert len(registries["controlled_surface_set"]) == 8
    assert [item["surface_id"] for item in registries["controlled_surface_set"]] == [
        "Start / Run Setup",
        "Operational Workspace",
        "Telemetry & Events",
        "Restoration Assessment",
        "Formal Validation",
        "Evidence Library",
        "Defect Investigation",
        "Engineering Basis",
    ]
    records = [
        record
        for members in registries["structural_record_set"].values()
        for record in members
    ]
    assert len(records) == len(set(records)) == 45
    assert set(registries["operational_event_type_ids"]) == {
        item.value for item in OperationalEventType
    }


@pytest.mark.dc006
def test_every_machine_selector_root_has_a_registered_authoritative_adapter() -> None:
    import re

    from ot_demo.modules.validation.source_adapters import SOURCE_ADAPTER_REGISTRY

    definitions = ValidationCatalogueLoader(CATALOGUE).load()
    controlled_roots = {
        re.split(r"[.\[]", part.strip(), maxsplit=1)[0]
        for loaded in definitions
        for method in (
            (loaded.definition.determination_method,)
            if loaded.definition.determination_method is not None
            else tuple(
                case.determination_method
                for case in loaded.definition.constituent_cases
                if case.determination_method is not None
            )
        )
        for criterion in method.criteria
        if criterion.kind.value == "MACHINE_COMPARISON"
        for part in criterion.source_selector.split(" + ")
    }
    registered = {
        record_type
        for definition in SOURCE_ADAPTER_REGISTRY.values()
        for record_type in definition.record_types
    }
    assert controlled_roots <= registered


@pytest.mark.dc006
def test_vt_top_def_preserves_one_execution_method_and_no_meta_result() -> None:
    method = ValidationCatalogueLoader(CATALOGUE).get_method("VT-TOP-DEF-001")
    assert method.context_kind is DeterminationContextKind.SCENARIO_EXECUTION
    assert method.required_context_roles == (
        "CURRENT_POST_TRIP_RUN",
        "POST_TRIP_CHECKPOINT",
        "CURRENT_EXECUTION_PROVENANCE",
    )
    assert all("CORRECTED_POST_TRIP_RUN" not in role for role in method.required_context_roles)
    assert str(method.version) == "1.1"
    criteria = {item.criterion_id: item for item in method.criteria}
    assert {
        criterion_id: str(criteria[criterion_id].version)
        for criterion_id in ("DEF-02", "DEF-03", "DEF-04")
    } == {"DEF-02": "1.1", "DEF-03": "1.1", "DEF-04": "1.1"}
    assert criteria["DEF-02"].expected_value == (
        "The current post-trip run uses corrected Network Configuration v1.1 with "
        "BRK-A GOOD/FRESH/OPEN and the controlled formal fault/input fingerprint."
    )
    assert criteria["DEF-03"].expected_value == (
        "For the current run, A1–A4 are de-energised, no A3/A4 source attribution "
        "exists and exactly 850 customers are affected."
    )
    assert criteria["DEF-04"].expected_value == (
        "The current source-path/configuration evidence contains the corrected SW-A23 "
        "endpoint SEC-A2 and no active path from FDR-B through SEC-B3/SW-A23 to A3/A4."
    )
    assert {
        criterion_id: (
            criteria[criterion_id].source_selector,
            criteria[criterion_id].operator.value,
            criteria[criterion_id].normalisation,
            criteria[criterion_id].requirement_ids,
        )
        for criterion_id in ("DEF-02", "DEF-03", "DEF-04")
    } == {
        "DEF-02": (
            "CurrentScenarioExecutionAdapter.{configuration_identity,post_trip_input_fingerprint,telemetry[BRK-A]}",
            "CANONICAL_RECORD_EQUAL",
            "exact canonical representation",
            (
                "REQ-VAL-011", "REQ-VAL-012", "REQ-CFG-006", "REQ-CFG-008",
                "REQ-CFG-009", "REQ-CFG-010", "REQ-CFG-012",
            ),
        ),
        "DEF-03": (
            "CurrentScenarioExecutionAdapter.post_trip.{topology,outage,expected_observed_comparison}",
            "CANONICAL_RECORD_EQUAL",
            "exact canonical representation",
            (
                "REQ-TOP-003", "REQ-OUT-001", "REQ-OUT-002", "REQ-OUT-003",
                "REQ-OUT-007", "REQ-CFG-004", "REQ-CFG-005", "REQ-CFG-012",
            ),
        ),
        "DEF-04": (
            "CurrentScenarioExecutionAdapter.{configuration_difference_role,source_paths}",
            "CANONICAL_RECORD_EQUAL",
            "exact canonical representation",
            ("REQ-CFG-001", "REQ-CFG-004", "REQ-CFG-007", "REQ-CFG-008"),
        ),
    }
    expected = " ".join(str(item.expected_value) for item in method.criteria)
    assert "separate execution deterministically FAILS" not in expected
    assert "corrected v1.1 satisfies this criterion and can PASS" not in expected
