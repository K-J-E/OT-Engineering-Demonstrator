"""Build the DC-006/DC-007 Validation Catalogue v1.2 candidate package.

The accepted Validation Plan v1.4 Section 21 is the controlled source for the
exact method and criterion definitions.  This utility promotes the active v1.1
catalogue without changing its 24 test IDs, 124 requirements, 286 RTM
relationships, or engineering answer keys.  It uses only the Python standard
library and is intentionally not part of the runtime dependency set.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS = ROOT / "validation/test-definitions"
CATALOGUE = DEFINITIONS / "catalogue.json"
MANIFEST = DEFINITIONS / "manifest.json"
REVISIONS = DEFINITIONS / "revisions.json"
VALIDATION_PLAN = ROOT / "01-engineering-source-documents/OT Project Validation Plan.docx"

ACCEPTED_V1_1_CATALOGUE_SHA256 = "28bfe69131c40857c08f175abba42be3eb36514924b6de416b4e72bbefe35865"
ACCEPTED_V1_1_MANIFEST_SHA256 = "45cb015f58af1d453be0255cdbbb857c08901877c416e830f26bb2fe6ecf60a3"
ACCEPTED_VALIDATION_PLAN_SHA256 = "0cf0d383786a057b402d0a0f97597ecaafb2b86074a2ef93f238b688b21e4f5f"
ACCEPTED_CATALOGUE_AUTHORITY = (
    "Accepted Validation Plan v1.4 Section 21 / DC-006 + DC-007"
)
SUPERSEDED_UNACCEPTED_V1_2_CANDIDATES = (
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
)
FIXED_NOTICE = "Simulated operation only — no real equipment control"
CONTROLLED_SURFACES = [
    ("Start / Run Setup", "Fixed notice; mode; test and Validation Catalogue identity; Network Configuration identity; Exploration fault selection where applicable; backend build identity; initial-condition preview; full run identity after creation."),
    ("Operational Workspace", "Fixed notice; full run identity; mode; Network Configuration identity; selected/controlled fault; workflow/N-state; state revision; evidence class; backend build identity."),
    ("Telemetry & Events", "Fixed notice; full run identity; telemetry value/quality/timestamp/age/freshness/reasons; exact event type/sequence/time/revision/source identity."),
    ("Restoration Assessment", "Fixed notice; full run and Network Configuration identities; assessment/candidate identities; bound revisions/evidence; permissives; calculation inputs/results; outcome/status."),
    ("Formal Validation", "Fixed notice; Validation Catalogue/test/method/criterion identities; execution/run/Network Configuration/build identities; FORMAL evidence class; checkpoints/findings/result."),
    ("Evidence Library", "Fixed notice; evidence/package identities and class; source catalogue/configuration/execution/build identities; separate generation-build identity; immutable hashes/links."),
    ("Defect Investigation", "Fixed notice; Network Configuration v1.0 failure, DEF-001, COR-001, corrected v1.1 repeat/regression identities; same-build and source-catalogue provenance."),
    ("Engineering Basis", "Fixed notice; authoritative artefact/version/hash; requirement/source/module/view traceability; build metadata; read-only/no operational action."),
]
STRUCTURAL_RECORDS = {
    "configuration": ["ConfigurationCatalogEntry", "NetworkEntity", "ConnectivityEdge", "LoadCapacity", "CustomerZoneMapping", "ConfigurationManifest"],
    "scenario": ["ScenarioRun"],
    "telemetry": ["TelemetryPoint", "TelemetryValidity", "Alarm", "TelemetrySnapshot"],
    "topology/outage": ["TopologySnapshot", "SectionDerivedState", "IsolationProof", "OutageSnapshot", "CalculationTrace"],
    "restoration": ["RestorationCandidate", "PermissiveResult", "RestorationAssessment", "AssessmentInvalidation", "RestorationExecutionBinding"],
    "events": ["OperationalEvent"],
    "validation": ["TestDefinition", "ValidationExecution", "EvidenceSnapshot", "ExecutedValidationResult", "DefectRecord", "CorrectionRecord", "RepeatLink"],
    "validation_assurance": ["ConstituentCaseDefinition", "CompositeValidationResult", "CompositeConstituentLink", "AcceptedCatalogueRevision", "ValidationSuspensionCondition", "ValidationSuspensionRecord", "SuspensionEvidenceRecord", "ValidationAttempt", "ValidationTargetSelection", "DeterminationMethodDefinition", "CriterionDefinition", "DeterminationContext", "CriterionFinding", "EngineeringReviewProposal", "EngineeringReviewFinalisation"],
    "evidence_export": ["EvidencePackage"],
}
EVENT_TYPES = [
    "SCENARIO_INITIALISED", "CONFIGURATION_SELECTED", "FAULT_INITIATED", "TELEMETRY_UPDATED", "DEVICE_STATE_CHANGE",
    "ALARM_GENERATED", "ALARM_ACKNOWLEDGED", "SWITCHING_ACTION", "TOPOLOGY_RECALCULATED",
    "OUTAGE_UPDATED", "RESTORATION_CANDIDATE_IDENTIFIED", "RESTORATION_NO_CANDIDATE",
    "RESTORATION_ASSESSED", "RESTORATION_ASSESSMENT_INVALIDATED", "SCENARIO_RESET",
]

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
DIRECT_HEADING = re.compile(r"^21\.3\.\d+ (VT-[A-Z0-9-]+)\b")
PARENT_HEADING = re.compile(r"^21\.4\.\d+ (VT-EXP-(?:ALL|ROLE)-001)\b")
CASE_HEADING = re.compile(r"^21\.4\.\d+\.\d+ (EXP-(?:ALL|ROLE)-[A-Z0-9-]+)\b")
CRITERION_PATTERN = re.compile(
    r"^Kind: (?P<kind>[A-Z_]+) "
    r"Context/checkpoint: (?P<checkpoint>.*?) "
    r"Expected value/proposition: (?P<expected>.*?) "
    r"Source type/selector: (?P<source>.*?) "
    r"Operator: (?P<operator>[A-Z_]+) "
    r"Normalisation: (?P<normalisation>.*?) "
    r"Required evidence: (?P<required_evidence>.*?); method evidence roles: "
    r"(?P<evidence_roles>.*?) requirement_ids: (?P<requirement_ids>REQ-.*)$"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def definition_hash(value: dict[str, Any], hash_field: str) -> str:
    payload = {key: item for key, item in value.items() if key != hash_field}
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def blocks(path: Path) -> list[tuple[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find("w:body", NS)
    assert body is not None
    result: list[tuple[str, Any]] = []
    for child in body:
        kind = child.tag.rsplit("}", 1)[-1]
        if kind == "p":
            value = text(child)
            if value:
                result.append(("p", value))
        elif kind == "tbl":
            rows: list[list[str]] = []
            for row in child.findall("w:tr", NS):
                rows.append([
                    " ".join(
                        item for item in (text(paragraph) for paragraph in cell.findall(".//w:p", NS))
                        if item
                    )
                    for cell in row.findall("w:tc", NS)
                ])
            result.append(("table", rows))
    return result


def split_roles(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def next_version(value: str) -> str:
    major, minor = (int(item) for item in value.split("."))
    return f"{major}.{minor + 1}"


def parse_methods() -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    direct: dict[str, dict[str, Any]] = {}
    cases: dict[tuple[str, str], dict[str, Any]] = {}
    current_test: str | None = None
    current_case: str | None = None
    active = False
    for kind, value in blocks(VALIDATION_PLAN):
        if kind == "p":
            if value == "21. Accepted Controlled Amendment — DC-006 Controlled Validation Test Determination Methods":
                active = True
                continue
            if not active:
                continue
            match = DIRECT_HEADING.match(value)
            if match:
                current_test, current_case = match.group(1), None
                direct[current_test] = {"metadata": {}, "criteria": []}
                continue
            match = PARENT_HEADING.match(value)
            if match:
                current_test, current_case = match.group(1), None
                continue
            match = CASE_HEADING.match(value)
            if match:
                if current_test is None:
                    raise ValueError("case heading encountered without parent")
                current_case = match.group(1)
                cases[(current_test, current_case)] = {"metadata": {}, "criteria": []}
                continue
            continue
        if not active or current_test is None or not value:
            continue
        header = value[0]
        target = direct[current_test] if current_case is None and current_test in direct else cases.get((current_test, current_case or ""))
        if target is None:
            continue
        if header[:2] == ["Controlled field", "Authoritative value / rule"]:
            target["metadata"].update({row[0]: row[1] for row in value[1:] if len(row) >= 2})
        elif header[:2] == ["Criterion", "Controlled criterion definition"]:
            for row in value[1:]:
                if len(row) < 2:
                    continue
                match = CRITERION_PATTERN.match(row[1])
                if match is None:
                    raise ValueError(f"unparsed criterion {current_test}/{current_case}/{row[0]}")
                fields = match.groupdict()
                criterion = {
                    "criterion_id": row[0],
                    "version": "1.0",
                    "criterion_sha256": "0" * 64,
                    "kind": fields["kind"],
                    "test_id": current_test,
                    "case_id": current_case,
                    "context_checkpoint": fields["checkpoint"],
                    "expected_value": fields["expected"],
                    "source_selector": fields["source"],
                    "operator": fields["operator"],
                    "normalisation": fields["normalisation"],
                    "required_evidence": fields["required_evidence"],
                    "evidence_roles": split_roles(fields["evidence_roles"]),
                    "requirement_ids": [item.strip() for item in fields["requirement_ids"].split(",")],
                }
                criterion["criterion_sha256"] = definition_hash(criterion, "criterion_sha256")
                target["criteria"].append(criterion)
    return direct, cases


def make_method(test: dict[str, Any], parsed: dict[str, Any], case_id: str | None) -> dict[str, Any]:
    metadata = parsed["metadata"]
    criteria = parsed["criteria"]
    if case_id is None:
        context_kind = metadata["Context kind"]
        context_roles = split_roles(metadata["Required context roles"])
        checkpoint_roles = split_roles(metadata["Checkpoint/member roles"])
        procedure = metadata["Controlled procedure"]
        aggregate = metadata["Aggregate rule"]
    else:
        context_kind = "SCENARIO_EXECUTION"
        context_roles = ["EXPLORATION_SCENARIO_RUN", "VALIDATION_EXECUTION", "CONTROLLED_RESULT"]
        checkpoint_roles = [metadata["Checkpoint"]]
        procedure = test["procedure_steps"]
        aggregate = metadata["Case aggregate"]
    suffix = test["test_id"].removeprefix("VT-")
    method_id = f"DM-{suffix}" if case_id is None else f"DM-{suffix}-{case_id}"
    method = {
        "method_id": method_id,
        "version": "1.0",
        "method_sha256": "0" * 64,
        "test_id": test["test_id"],
        "case_id": case_id,
        "evidence_class": test["evidence_class"],
        "context_kind": context_kind,
        "required_context_roles": context_roles,
        "checkpoint_roles": checkpoint_roles,
        "controlled_procedure": procedure,
        "aggregate_rule": aggregate,
        "source_references": test["source_references"],
        "criterion_ids": [item["criterion_id"] for item in criteria],
        "criteria": criteria,
        "controlled_fixture": None,
    }
    if context_kind == "CONTROLLED_FIXTURE_EXECUTION":
        fixture = {
            "fixture_id": f"FIX-{test['test_id'].removeprefix('VT-')}",
            "version": "1.0",
            "fixture_sha256": "0" * 64,
            "test_id": test["test_id"],
            "method_id": method_id,
            "network_configuration_id": "network-configuration-v1.1",
            "network_configuration_version": "1.1",
            "controlled_inputs": test["controlled_inputs"],
            "procedure_steps": test["procedure_steps"],
            "expected_result_statement": test["expected_result_statement"],
        }
        fixture["fixture_sha256"] = definition_hash(fixture, "fixture_sha256")
        method["controlled_fixture"] = fixture
    method["method_sha256"] = definition_hash(method, "method_sha256")
    return method


def apply_dc007_version_increments(test: dict[str, Any]) -> None:
    """Apply only the controlled DC-007 identity increments to VT-TOP-DEF-001."""

    if test["test_id"] != "VT-TOP-DEF-001":
        return
    method = test["determination_method"]
    if method is None:
        raise ValueError("VT-TOP-DEF-001 must own its direct determination method")
    test["version"] = next_version(test["version"])
    method["version"] = next_version(method["version"])
    for criterion in method["criteria"]:
        if criterion["criterion_id"] in {"DEF-02", "DEF-03", "DEF-04"}:
            criterion["version"] = next_version(criterion["version"])
            criterion["criterion_sha256"] = definition_hash(
                criterion, "criterion_sha256"
            )
    method["method_sha256"] = definition_hash(method, "method_sha256")


def audit(catalogue: dict[str, Any]) -> None:
    methods: list[dict[str, Any]] = []
    rtm: set[tuple[str, str]] = set()
    requirements: set[str] = set()
    for test in catalogue["definitions"]:
        parent = set(test["requirement_ids"])
        rtm.update((test["test_id"], item) for item in parent)
        requirements.update(parent)
        if test["test_id"] in {"VT-EXP-ALL-001", "VT-EXP-ROLE-001"}:
            if test.get("determination_method") is not None:
                raise ValueError("DC-004 composite parent cannot own a direct DC-006 method")
            union: set[str] = set()
            for case in test["constituent_cases"]:
                method = case["determination_method"]
                methods.append(method)
                case_union = {rid for criterion in method["criteria"] for rid in criterion["requirement_ids"]}
                if not case_union <= parent:
                    raise ValueError(f"out-of-parent case mapping: {test['test_id']}/{case['case_id']}")
                union |= case_union
            if union != parent:
                raise ValueError(f"composite criterion coverage mismatch: {test['test_id']}")
        else:
            method = test["determination_method"]
            methods.append(method)
            union = {rid for criterion in method["criteria"] for rid in criterion["requirement_ids"]}
            if union != parent:
                raise ValueError(f"direct criterion coverage mismatch: {test['test_id']}")
    criteria = [criterion for method in methods for criterion in method["criteria"]]
    direct_count = sum(len(test["determination_method"]["criteria"]) for test in catalogue["definitions"] if test.get("determination_method"))
    if (len(catalogue["definitions"]), len(requirements), len(rtm)) != (24, 124, 286):
        raise ValueError("24/124/286 invariant failed")
    if (len(methods), len(criteria), direct_count, len(criteria) - direct_count) != (35, 214, 147, 67):
        raise ValueError("35-method/214-criterion identity failed")
    if len({item["criterion_id"] for item in criteria}) != 214:
        raise ValueError("criterion IDs must be globally unique")
    fixtures = [method["controlled_fixture"] for method in methods if method["controlled_fixture"]]
    if len(fixtures) != 8:
        raise ValueError("accepted DC-006 package requires exactly eight fixture definitions")
    registries = catalogue["controlled_registries"]
    structural_count = sum(len(items) for items in registries["structural_record_set"].values())
    if len(registries["controlled_surface_set"]) != 8 or structural_count != 45:
        raise ValueError("exact eight-surface/45-record registry identity failed")


def main() -> None:
    if sha256(VALIDATION_PLAN) != ACCEPTED_VALIDATION_PLAN_SHA256:
        raise SystemExit("accepted Validation Plan identity mismatch")
    history = DEFINITIONS / "history/v1.1"
    active_is_v1_1 = (
        sha256(CATALOGUE) == ACCEPTED_V1_1_CATALOGUE_SHA256
        and sha256(MANIFEST) == ACCEPTED_V1_1_MANIFEST_SHA256
    )
    if history.exists():
        if sha256(history / "catalogue.json") != ACCEPTED_V1_1_CATALOGUE_SHA256 or sha256(history / "manifest.json") != ACCEPTED_V1_1_MANIFEST_SHA256:
            raise SystemExit("history/v1.1 collision does not match accepted source package")
        source_catalogue_path = history / "catalogue.json"
    elif active_is_v1_1:
        history.mkdir(parents=True)
        shutil.copyfile(CATALOGUE, history / "catalogue.json")
        shutil.copyfile(MANIFEST, history / "manifest.json")
        source_catalogue_path = history / "catalogue.json"
    else:
        raise SystemExit("accepted v1.1 source package is unavailable")
    direct, cases = parse_methods()
    source = json.loads(source_catalogue_path.read_text(encoding="utf-8"))
    for test in source["definitions"]:
        test["version"] = next_version(test["version"])
        if test["test_id"] in direct:
            test["determination_method"] = make_method(test, direct[test["test_id"]], None)
            apply_dc007_version_increments(test)
        else:
            test["determination_method"] = None
            for case in test["constituent_cases"]:
                case["version"] = next_version(case["version"])
                case["determination_method"] = make_method(
                    test, cases[(test["test_id"], case["case_id"])], case["case_id"]
                )
    source["catalogue_id"] = "VALIDATION-CATALOGUE-V1.2"
    source["catalogue_version"] = "1.2"
    source["authority"] = ACCEPTED_CATALOGUE_AUTHORITY
    source["controlled_registries"] = {
        "context_kinds": ["SCENARIO_EXECUTION", "CONTROLLED_FIXTURE_EXECUTION", "PRESERVED_RECORD_SET", "ENGINEERING_REVIEW"],
        "operators": ["SCALAR_EQUAL", "NUMERIC_EQUAL", "BOOLEAN_EQUAL", "CANONICAL_SET_EQUAL", "ORDERED_SEQUENCE_EQUAL", "PRESENT", "ABSENT", "IDENTITY_HASH_AGREEMENT", "CANONICAL_RECORD_EQUAL", "REVIEW_FINDING_EQUAL"],
        "fixed_simulation_notice": FIXED_NOTICE,
        "controlled_surface_set": [
            {"surface_id": name, "required_identity_profile": profile}
            for name, profile in CONTROLLED_SURFACES
        ],
        "structural_record_set": STRUCTURAL_RECORDS,
        "operational_event_type_ids": EVENT_TYPES,
    }
    audit(source)

    CATALOGUE.write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    catalogue_sha = sha256(CATALOGUE)
    manifest = {
        "catalogue_id": source["catalogue_id"],
        "catalogue_version": source["catalogue_version"],
        "definition_count": 24,
        "method_count": 35,
        "criterion_count": 214,
        "catalogue_file": "catalogue.json",
        "catalogue_sha256": catalogue_sha,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    revisions = json.loads(REVISIONS.read_text(encoding="utf-8"))
    unaccepted = revisions.setdefault("superseded_unaccepted_candidates", [])
    for candidate in SUPERSEDED_UNACCEPTED_V1_2_CANDIDATES:
        if not any(
            item.get("catalogue_sha256") == candidate["catalogue_sha256"]
            and item.get("manifest_sha256") == candidate["manifest_sha256"]
            for item in unaccepted
        ):
            unaccepted.append(candidate)
    if revisions.get("active_catalogue_version") == "1.2":
        revisions["revisions"] = [
            item for item in revisions["revisions"] if item["catalogue_version"] != "1.2"
        ]
    revisions["active_catalogue_version"] = "1.2"
    revisions["revisions"][-1]["catalogue_path"] = "history/v1.1/catalogue.json"
    revisions["revisions"][-1]["status"] = "IMMUTABLE_HISTORICAL"
    revisions["revisions"].append({
        "catalogue_version": "1.2",
        "catalogue_sha256": catalogue_sha,
        "manifest_sha256": sha256(MANIFEST),
        "catalogue_path": "catalogue.json",
        "status": "ACTIVE_PENDING_INDEPENDENT_REVIEW",
    })
    REVISIONS.write_text(json.dumps(revisions, indent=2) + "\n", encoding="utf-8")
    print(f"DC006_CATALOGUE_OK catalogue_sha256={catalogue_sha} manifest_sha256={sha256(MANIFEST)}")


if __name__ == "__main__":
    main()
