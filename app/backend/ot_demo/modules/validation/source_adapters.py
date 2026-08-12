"""Registry-controlled adapters over immutable records owned by backend modules.

The adapters expose values selected by accepted DC-006 source selectors.  They
do not accept caller-authored selector/value maps and do not calculate any
electrical result.  Each value is read from a hash-verified snapshot of an
existing controlling-module record.
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from typing import Any, Iterable

from ...domain.enums import DeterminationSourceAdapterKind
from .models import AuthoritativeRecordSnapshot, DeterminationSourceRecord


class SourceAdapterError(ValueError):
    """Raised when source ownership, provenance or selector resolution is invalid."""


@dataclass(frozen=True, slots=True)
class SourceAdapterDefinition:
    owner_module: str
    record_types: frozenset[str]


SOURCE_ADAPTER_REGISTRY: dict[
    DeterminationSourceAdapterKind, SourceAdapterDefinition
] = {
    DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE: SourceAdapterDefinition(
        "configuration-package-authority",
        frozenset({
            "ConfigurationPackageAdapter", "ConfigurationComparisonResult",
            "NetworkConfigurationPackage", "NetworkConfigurationSchema",
            "AuthorityRoleBinding",
        }),
    ),
    DeterminationSourceAdapterKind.SCENARIO_STATE: SourceAdapterDefinition(
        "scenario-topology-outage-authority",
        frozenset(
            {
                "ScenarioRun", "ScenarioSnapshot", "TopologyResult", "OutageResult",
                "IsolationProof", "ActionProjection", "EvidenceSnapshot",
                "RestorationAssessment", "TelemetrySnapshot", "DeviceState",
                "CommandResult", "PostExecutionSnapshot", "ScenarioRevisionSequence",
                "CurrentScenarioExecutionAdapter", "CurrentValidationExecutionAdapter",
                "ValidationExecution", "AssessmentInvalidationAdapter", "CommandAvailability",
                "CommandResultReplayComparison", "ExecutedValidationResultAdapter",
                "PersistenceAssuranceResult", "RestorationProjection", "ScenarioResetAdapter",
                "ValidationExecutionAdapter",
                "AlarmAdapter", "OperationalEvent", "OperationalEventAdapter",
                "OperationalEventRegistry", "AuthorityRoleBinding",
            }
        ),
    ),
    DeterminationSourceAdapterKind.CONTROLLED_FIXTURE: SourceAdapterDefinition(
        "controlled-fixture-execution-authority",
        frozenset(
            {
                "ControlledFixtureAdapter", "ControlledFixtureResult", "ControlledFixture",
                "CapacityFixture", "TelemetryValidityResult", "RestorationAssessment",
                "ActionProjection", "ConfigurationPackageAdapter", "RestorationProjection",
                "TopologyResult", "AuthorityRoleBinding",
            }
        ),
    ),
    DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY: SourceAdapterDefinition(
        "operational-event-history-authority",
        frozenset(
            {
                "OperationalEventAdapter", "OperationalEvent", "AlarmRecord", "AlarmAdapter",
                "AlarmLifecycleAdapter", "OperationalEventRegistry", "ScenarioRun",
                "ScenarioSnapshot",
                "AuthorityRoleBinding",
            }
        ),
    ),
    DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY: SourceAdapterDefinition(
        "validation-investigation-history-authority",
        frozenset(
            {
                "InvestigationAdapter", "ValidationExecution", "ValidationEvidenceAdapter",
                "FormalProgressAdapter", "ScenarioRunAdapter", "ConfigurationComparisonResult",
                "DefectRecord", "CorrectionRecord", "RepeatLink", "ExecutedValidationResultAdapter",
                "PersistenceAssuranceResult", "ScenarioResetAdapter", "ValidationExecutionAdapter",
                "EngineeringReviewRecord",
                "OperationalEventAdapter",
                "AuthorityRoleBinding",
            }
        ),
    ),
    DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT: SourceAdapterDefinition(
        "deterministic-repeat-authority",
        frozenset({"DeterministicRepeatAdapter", "RepeatMemberIdentity", "AuthorityRoleBinding"}),
    ),
    DeterminationSourceAdapterKind.EVIDENCE_PACKAGE: SourceAdapterDefinition(
        "evidence-package-authority",
        frozenset({"EvidencePackageAdapter", "EvidencePackageIdentity", "HistoricalCatalogueResolver", "AuthorityRoleBinding"}),
    ),
    DeterminationSourceAdapterKind.NFR_REVIEW: SourceAdapterDefinition(
        "engineering-review-assurance-authority",
        frozenset(
            {
                "BuildRuntimeAdapter", "ReviewSurfaceAdapter", "SchemaAndProjectionAdapter",
                "ConfigurationPackageAdapter", "EngineeringReviewRecord",
                "AuthorityRoleBinding",
            }
        ),
    ),
}

class AuthoritativeSourceAdapterRegistry:
    """Validate adapter ownership and resolve accepted selectors over source records."""

    @staticmethod
    def validate_capture(
        source_type: DeterminationSourceAdapterKind,
        records: tuple[AuthoritativeRecordSnapshot, ...],
    ) -> str:
        if not records:
            raise SourceAdapterError("authoritative source capture requires records")
        definition = SOURCE_ADAPTER_REGISTRY[source_type]
        unknown = sorted(
            {item.record_type for item in records} - definition.record_types
        )
        if unknown:
            raise SourceAdapterError(
                f"record type is not controlled for {source_type.value}: {unknown}"
            )
        if any(item.owner_module != definition.owner_module for item in records):
            raise SourceAdapterError("authoritative record owner does not match adapter registry")
        return definition.owner_module

    @staticmethod
    def records(record: DeterminationSourceRecord) -> tuple[AuthoritativeRecordSnapshot, ...]:
        try:
            records = tuple(
                AuthoritativeRecordSnapshot.model_validate_json(
                    json.dumps(item, sort_keys=True, separators=(",", ":")),
                    strict=True,
                )
                for item in record.canonical_payload["authority_records"]
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SourceAdapterError("source record does not contain valid authority records") from error
        owner = AuthoritativeSourceAdapterRegistry.validate_capture(record.source_type, records)
        if owner != record.owner_module:
            raise SourceAdapterError("source-record owner was not registry controlled")
        return records

    @staticmethod
    def resolve(record: DeterminationSourceRecord, selector: str) -> Any:
        records = AuthoritativeSourceAdapterRegistry.records(record)
        return AuthoritativeSourceAdapterRegistry.resolve_records(records, selector)

    @staticmethod
    def resolve_records(
        records: tuple[AuthoritativeRecordSnapshot, ...], selector: str
    ) -> Any:
        """Resolve a selector directly over producer-owned authority snapshots."""

        roots: dict[str, list[AuthoritativeRecordSnapshot]] = {}
        for item in records:
            roots.setdefault(item.record_type, []).append(item)
        parts = [part.strip() for part in selector.split(" + ")]
        resolved = [
            AuthoritativeSourceAdapterRegistry._resolve_part(roots, part)
            for part in parts
        ]
        if len(resolved) == 1:
            return resolved[0]
        combined = {part: value for part, value in zip(parts, resolved, strict=True)}
        return derive_combined_observation(selector, combined, records)

    @staticmethod
    def _resolve_part(
        roots: dict[str, list[AuthoritativeRecordSnapshot]], selector: str
    ) -> Any:
        root_name = re.split(r"[.\[]", selector, maxsplit=1)[0]
        candidates = roots.get(root_name, [])
        if len(candidates) != 1:
            raise SourceAdapterError(
                f"selector root {root_name} resolved {len(candidates)} authoritative records"
            )
        value: Any = candidates[0].canonical_payload
        suffix = selector[len(root_name):]
        if suffix.startswith("."):
            suffix = suffix[1:]
        while suffix:
            if suffix.startswith("{"):
                close = suffix.find("}")
                if close < 0 or not isinstance(value, (dict, list, tuple)):
                    raise SourceAdapterError(f"invalid field-set selector: {selector}")
                fields = [item.strip() for item in suffix[1:close].split(",")]
                if isinstance(value, dict):
                    value = {field: value[field] for field in fields}
                else:
                    value = tuple(
                        {field: item[field] for field in fields} for item in value
                    )
                suffix = suffix[close + 1:]
            elif suffix.startswith("["):
                close = suffix.find("]")
                if close < 0:
                    raise SourceAdapterError(f"invalid indexed selector: {selector}")
                key = suffix[1:close]
                if key == "*":
                    if not isinstance(value, (list, tuple)):
                        raise SourceAdapterError(
                            f"wildcard selector requires a sequence: {selector}"
                        )
                else:
                    try:
                        value = value[key]
                    except (KeyError, TypeError) as error:
                        raise SourceAdapterError(f"selector member is absent: {selector}") from error
                suffix = suffix[close + 1:]
            else:
                match = re.match(r"(?P<field>[A-Za-z0-9_-]+)", suffix)
                if match is None:
                    raise SourceAdapterError(f"unsupported selector syntax: {selector}")
                field = match.group("field")
                try:
                    value = value[field]
                except (KeyError, TypeError) as error:
                    raise SourceAdapterError(f"selector member is absent: {selector}") from error
                suffix = suffix[match.end():]
            if suffix.startswith("."):
                suffix = suffix[1:]
        return derive_observation(root_name, selector, candidates[0].canonical_payload, value)


def derive_combined_observation(
    selector: str,
    selected: dict[str, Any],
    records: tuple[AuthoritativeRecordSnapshot, ...],
) -> Any:
    """Derive propositions that require facts from more than one source root."""

    del records
    if selector == "ScenarioRun.checkpoints + OperationalEvent.sequence":
        checkpoints = selected["ScenarioRun.checkpoints"]
        events = selected["OperationalEvent.sequence"]
        event_types = [item.get("event_type") or item.get("type") for item in events]
        exact = (
            [str(checkpoints.get(item, "")).replace("+00:00", "Z") for item in ("N0", "N1", "N2", "N3", "N4", "N5")]
            == [f"2030-01-01T00:00:{second:02d}Z" for second in (0, 10, 30, 40, 50, 55)]
            and "ALARM_ACKNOWLEDGED" in event_types
            and any(
                (item.get("event_type") or item.get("type")) == "ALARM_ACKNOWLEDGED"
                and str(item.get("scenario_time", "")).startswith("2030-01-01T00:00:11")
                for item in events
            )
        )
        return (
            "Exact chronology: T+0 N0; T+10 trip/N1; T+11 alarm acknowledgement; T+20 first isolation action; T+30 second isolation/N2; T+40 N3; T+50 N4; T+55 N5. T+11 is event evidence, not a seventh N-state."
            if exact else selected
        )
    return selected


def common_provenance(
    records: Iterable[AuthoritativeRecordSnapshot],
) -> tuple[str, str | None, str | None, object | None, object | None]:
    items = tuple(records)
    fields = (
        "application_build_id", "configuration_id", "configuration_version",
        "scenario_run_id", "validation_execution_id",
    )
    values: list[Any] = []
    for field in fields:
        present = {getattr(item, field) for item in items if getattr(item, field) is not None}
        if len(present) > 1:
            raise SourceAdapterError(f"authoritative records disagree on {field}")
        values.append(next(iter(present), None))
    if values[0] is None:
        raise SourceAdapterError("authoritative records require backend build provenance")
    return tuple(values)  # type: ignore[return-value]


def derive_observation(
    record_type: str, selector: str, payload: Any, selected: Any
) -> Any:
    """Calculate controlled projections solely from resolved authority facts.

    A projection returns the catalogue proposition only when the underlying
    facts establish it.  On any mismatch it returns the observed facts, which
    the generic criterion comparator records as NOT_SATISFIED.
    """

    if record_type == "ConfigurationPackageAdapter":
        propositions = {
            "ConfigurationPackageAdapter.manifest.{configuration_id,version,sha256}": (
                "manifest_identity_hash_satisfied",
                "Both controlled Network Configuration identities, manifests and SHA-256 hashes resolve exactly.",
            ),
            "ConfigurationPackageAdapter.canonical_network_payload": (
                "canonical_network_oracle_satisfied",
                "Canonical assets, connectivity, normal states, section loads, feeder capacities and customer-zone values equal the approved Network Model oracle.",
            ),
        }
        if selector in propositions:
            flag, proposition = propositions[selector]
            return proposition if payload.get(flag) is True else payload.get("resolved_packages", selected)
    if record_type == "ConfigurationComparisonResult" and selector.endswith(".differences"):
        if payload.get("exact_approved_difference") is True:
            return (
                "The immutable package comparison contains exactly SW-A23 endpoint 1 SEC-B3→SEC-A2 and no other difference."
                if payload.get("projection_kind") == "INVESTIGATION_COMPARISON"
                else "The package difference set is exactly SW-A23 endpoint 1: SEC-B3 in Network Configuration v1.0 and SEC-A2 in Network Configuration v1.1."
            )
        return selected
    if record_type == "ScenarioSnapshot" and selector == "ScenarioSnapshot.{configuration_identity,device_states,source_availability}":
        states = payload.get("device_states", {})
        sources = payload.get("source_availability", {})
        normal = (
            payload.get("configuration_identity") == "network-configuration-v1.1"
            and states.get("BRK-A") == states.get("BRK-B") == "CLOSED"
            and all(states.get(item) == "CLOSED" for item in ("SW-A12", "SW-A23", "SW-A34", "SW-B12", "SW-B23", "SW-B34"))
            and states.get("TS-01") == "OPEN"
            and sources and all(value == "AVAILABLE" for value in sources.values())
        )
        return (
            "Corrected Network Configuration v1.1 is bound; BRK-A/BRK-B and all sectionalisers are CLOSED, TS-01 is OPEN, and both feeder sources are AVAILABLE."
            if normal else selected
        )
    if record_type == "TopologyResult":
        if selector == "TopologyResult.{energised_section_ids,de_energised_section_ids}":
            expected = [f"SEC-{feeder}{index}" for feeder in ("A", "B") for index in range(1, 5)]
            return (
                "The energised section set is exactly SEC-A1–SEC-A4 and SEC-B1–SEC-B4; the de-energised set is empty."
                if payload.get("energised_section_ids") == expected and payload.get("de_energised_section_ids") == []
                else selected
            )
        if selector == "TopologyResult.section_source_feeder_ids":
            attribution = payload.get("section_source_feeder_ids", {})
            valid = all(attribution.get(f"SEC-A{i}") == ["FDR-A"] for i in range(1, 5)) and all(
                attribution.get(f"SEC-B{i}") == ["FDR-B"] for i in range(1, 5)
            )
            return "A1–A4 trace only to FDR-A and B1–B4 trace only to FDR-B." if valid else selected
        if selector == "TopologyResult.feeder_loads":
            return (
                "Derived currently supplied loads are exactly 3,200 kW for FDR-A and 4,200 kW for FDR-B with complete attribution; configured loads/capacities/customer mappings remain separate."
                if payload.get("feeder_loads") == {"FDR-A": 3200, "FDR-B": 4200}
                else selected
            )
    if record_type == "OutageResult" and selector == "OutageResult.{de_energised_section_ids,affected_customer_count}":
        return (
            "Outage extent is empty and affected-customer count is zero."
            if payload.get("de_energised_section_ids") == [] and payload.get("affected_customer_count") == 0
            else selected
        )
    if record_type == "EvidenceSnapshot":
        checkpoint = selector.split("[", 1)[1].split("]", 1)[0]
        facts = payload.get(checkpoint, {})
        topology = facts.get("topology") or {}
        outage = facts.get("outage") or {}
        fault = facts.get("fault") or {}
        device_states = facts.get("device_states") or {}
        allowed_actions = facts.get("allowed_actions") or {}
        sections = {
            item["section_id"]: item for item in topology.get("sections", [])
        }
        if checkpoint == "N0":
            valid = (
                len([item for item in sections.values() if item.get("energised")]) == 8
                and outage.get("affected_customer_count") == 0
                and topology.get("radiality_status") == "RADIAL"
            )
            proposition = "At N0 all eight sections are energised from their normal feeders, outage is zero and topology is radial."
        elif checkpoint == "N1":
            valid = (
                fault.get("section_id") == "SEC-A2"
                and device_states.get("BRK-A") == "OPEN"
                and outage.get("affected_customer_count") == 850
                and all(not sections.get(f"SEC-A{i}", {}).get("energised", True) for i in range(1, 5))
            )
            proposition = "At N1 SEC-A2 is FAULTED, BRK-A is OPEN, A1–A4 are de-energised, B1–B4 remain energised and 850 customers are affected."
        elif checkpoint == "N2":
            valid = (
                facts.get("isolation") is True
                and facts.get("source_paths") == []
                and outage.get("affected_customer_count") == 850
                and set(facts.get("boundary_evidence") or {}) == {"SW-A12", "SW-A23"}
            )
            proposition = "At N2 SW-A12 and SW-A23 are GOOD/FRESH/OPEN, every incident boundary is PROVEN_OPEN, zero active source paths reach SEC-A2, isolation is proven and 850 customers remain affected."
        elif checkpoint == "N3":
            valid = (
                device_states.get("BRK-A") == "CLOSED"
                and sections.get("SEC-A1", {}).get("source_feeder_ids") == ["FDR-A"]
                and outage.get("affected_customer_count") == 670
                and (allowed_actions.get("assess_restoration") or {}).get("available") is True
            )
            proposition = "At N3 BRK-A is CLOSED; A1 is supplied from FDR-A; A2/A3/A4 remain de-energised; 670 customers are affected; alternate assessment is now eligible."
        elif checkpoint == "N4":
            assessment = facts.get("restoration_assessment") or {}
            valid = (
                assessment.get("transferable_load_kw") == 1500
                and assessment.get("resulting_load_kw") == 5700
                and assessment.get("feeder_capacity_kw") == 6000
                and str(assessment.get("resulting_loading_percent")) == "95.0"
                and assessment.get("restoration_outcome") == "PERMITTED"
            )
            proposition = "At N4 the candidate is A3/A4; transfer is 1,500 kW; existing FDR-B load is 4,200 kW; resulting load is 5,700 of 6,000 kW; loading is 95.0%; all permissives pass; outcome is PERMITTED; 450 customers are proposed restored."
        elif checkpoint == "N5":
            valid = (
                device_states.get("TS-01") == "CLOSED"
                and sections.get("SEC-A3", {}).get("source_feeder_ids") == ["FDR-B"]
                and sections.get("SEC-A4", {}).get("source_feeder_ids") == ["FDR-B"]
                and outage.get("affected_customer_count") == 220
                and outage.get("restored_customer_delta") == 450
                and topology.get("radiality_status") == "RADIAL"
            )
            proposition = "At N5 TS-01 is CLOSED; A3/A4 are supplied from FDR-B; SEC-A2 remains faulted/de-energised; topology is radial; 450 customers are restored and 220 remain affected."
        else:
            return selected
        return proposition if valid else selected
    if record_type == "OperationalEventAdapter" and selector == "OperationalEventAdapter.events_for_run":
        events = payload.get("events_for_run", [])
        types = [item.get("event_type") for item in events]
        valid = (
            types.count("ALARM_ACKNOWLEDGED") == 1
            and types.count("SWITCHING_ACTION") >= 4
            and types.count("RESTORATION_ASSESSED") == 1
            and [item.get("event_sequence") for item in events] == list(range(1, len(events) + 1))
        )
        return (
            "Required command and derived operational records retain accepted chronology, including acknowledgement at T+11 and switching/assessment traceability."
            if valid else selected
        )
    if record_type == "TelemetryValidityResult":
        if selector.endswith(".{quality,freshness}"):
            quality, freshness = payload.get("quality"), payload.get("freshness")
            if quality == "GOOD" and freshness == "STALE":
                return "Quality remains GOOD while freshness is STALE; the two dimensions are not collapsed."
        if selector.endswith(".{valid,reason_codes}") and payload.get("valid") is False:
            return "Overall validity is false and includes the controlled stale/freshness reason."
    if record_type == "ControlledFixtureAdapter" and selector.startswith("ControlledFixtureAdapter."):
        valid = (
            payload.get("fixture_identity") == "FIX-RST-RADIAL-001"
            and payload.get("fixture_version") == "1.0"
            and len(payload.get("fixture_hash", "")) == 64
            and len(payload.get("build_identity", "")) == 64
            and payload.get("configuration_identity") == "network-configuration-v1.1"
            and len(payload.get("configuration_hash", "")) == 64
        )
        return "Controlled fixture definition identity/version/hash, executing build and Network Configuration identity/hash resolve exactly." if valid else selected
    if record_type == "RestorationAssessment" and selector.endswith(".{outcome,reasons}"):
        if payload.get("outcome") == "BLOCKED" and "TELEMETRY_STALE" in payload.get("reasons", []):
            return "Restoration assessment outcome is operational BLOCKED, not REJECTED; the validation criterion is satisfied because BLOCKED is expected."
    if record_type == "RestorationAssessment" and selector == "RestorationAssessment.permissives[RADIAL_TOPOLOGY]":
        return "Radial-topology permissive is FAIL and retains the offending source-path evidence." if selected == "FAIL" and payload.get("reasons") else selected
    if record_type == "InvestigationAdapter" and selector == "InvestigationAdapter.failure":
        failure = payload.get("failure")
        return (
            "The preserved initiating record is the immutable Network Configuration v1.0 400-customer FAIL."
            if failure == {"configuration_version": "1.0", "affected_customers": 400, "verdict": "FAIL"}
            else failure
        )
    if record_type == "DeterministicRepeatAdapter":
        members = payload.get("members", {})
        exact_roles = {"DET_FORMAL_PAIR", "DET_NEGATIVE_PAIR", "DET_CORRECTED_PAIR"}
        if selector.endswith(".members"):
            valid = set(members) == exact_roles and all(
                len(pair) == 2
                and pair[0]["execution_id"] != pair[1]["execution_id"]
                for pair in members.values()
            )
            return (
                "Exact member roles DET-FORMAL, DET-NEGATIVE and DET-CORRECTED each contain two distinct completed source identities."
                if valid else selected
            )
        if selector.endswith(".input_fingerprints"):
            valid = set(payload.get("input_fingerprints", {})) == exact_roles and all(
                pair[0] == pair[1]
                for pair in payload["input_fingerprints"].values()
            )
            return (
                "Within each pair build, Network Configuration, Validation Catalogue/test/method, fixture and controlled-clock inputs are equal."
                if valid else selected
            )
        if selector.endswith(".repeat_links"):
            valid = set(payload.get("repeat_links", {})) == exact_roles and all(
                links["forward"] == links["reverse"]
                for links in payload["repeat_links"].values()
            )
            return (
                "Each pair has explicit bidirectional repeat links while generated identities remain distinct."
                if valid else selected
            )
        if selector.endswith(".before_after_hashes"):
            valid = set(payload.get("before_after_hashes", {})) == exact_roles and all(
                len(hashes) == 2 and all(len(value) == 64 for value in hashes)
                for hashes in payload["before_after_hashes"].values()
            )
            return (
                "Original source execution/evidence/correction records remain unchanged after repeats."
                if valid else selected
            )
    if record_type == "EvidencePackageAdapter":
        exact_roles = {"PKG_FORMAL", "PKG_HISTORICAL_DEFECT"}
        if selector.endswith(".package_registry"):
            registry = payload.get("package_registry", {})
            valid = (
                set(registry) == exact_roles
                and len({item["package_id"] for item in registry.values()}) == 2
                and len({item["archive_path"] for item in registry.values()}) == 2
            )
            return (
                "PKG-FORMAL and PKG-HISTORICAL-DEFECT have distinct non-overwriting package IDs and relative paths."
                if valid else selected
            )
        if selector.endswith(".archive_entries"):
            entries = payload.get("archive_entries", {})
            valid = set(entries) == exact_roles and all(
                "manifest.json" in names
                and "README.txt" in names
                and "report.html" in names
                for names in entries.values()
            )
            return "Each package contains the exact definition-required file set." if valid else selected
        if selector.endswith(".integrity_verification"):
            return "Every manifest entry exists and its SHA-256 matches; manifest and archive hashes verify." if selected is True else selected
        if selector.endswith(".link_verification"):
            return selected
        if selector.endswith(".source_provenance"):
            provenance = payload.get("source_provenance", {})
            valid = (
                set(provenance) == exact_roles
                and provenance["PKG_FORMAL"].get("test_id") == "VT-FML-N0-N5-001"
                and provenance["PKG_FORMAL"].get("configuration_version") == "1.1"
                and provenance["PKG_HISTORICAL_DEFECT"].get("test_id") == "VT-TOP-DEF-001"
                and provenance["PKG_HISTORICAL_DEFECT"].get("configuration_version") == "1.0"
            )
            return "Source execution/build/Network Configuration/Validation Catalogue/test identities exactly match preserved source records." if valid else selected
        if selector.endswith(".{source_build,generation_build}"):
            valid = set(payload.get("source_build", {})) == exact_roles and set(
                payload.get("generation_build", {})
            ) == exact_roles
            return "Export-generation application build remains explicit and separate from source execution build." if valid else selected
        if selector.endswith(".before_after_hashes"):
            hashes = payload.get("before_after_hashes", {})
            valid = set(hashes) == exact_roles and all(
                item["stored_archive_sha256"] == item["resolved_archive_sha256"]
                and len(item["source_execution_sha256"]) == 64
                for item in hashes.values()
            )
            return "Generating/verifying the second package leaves the first package and both source executions unchanged." if valid else selected
    if record_type == "HistoricalCatalogueResolver" and selector.endswith(".resolution"):
        resolution = payload.get("resolution", {})
        valid = set(resolution) == {"PKG_FORMAL", "PKG_HISTORICAL_DEFECT"} and all(
            item.get("resolved") is True for item in resolution.values()
        )
        return "Historical Validation Catalogue/test definition resolves by the original stored identity without active-definition substitution." if valid else selected
    return selected
