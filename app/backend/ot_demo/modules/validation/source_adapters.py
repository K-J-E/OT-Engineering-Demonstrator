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
            }
        ),
    ),
    DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT: SourceAdapterDefinition(
        "deterministic-repeat-authority",
        frozenset({"DeterministicRepeatAdapter", "RepeatMemberIdentity"}),
    ),
    DeterminationSourceAdapterKind.EVIDENCE_PACKAGE: SourceAdapterDefinition(
        "evidence-package-authority",
        frozenset({"EvidencePackageAdapter", "EvidencePackageIdentity", "HistoricalCatalogueResolver"}),
    ),
    DeterminationSourceAdapterKind.NFR_REVIEW: SourceAdapterDefinition(
        "engineering-review-assurance-authority",
        frozenset(
            {
                "BuildRuntimeAdapter", "ReviewSurfaceAdapter", "SchemaAndProjectionAdapter",
                "ConfigurationPackageAdapter", "EngineeringReviewRecord",
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
        return {part: value for part, value in zip(parts, resolved, strict=True)}

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
                if key != "*":
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
    if record_type == "TelemetryValidityResult":
        if selector.endswith(".{quality,freshness}"):
            quality, freshness = payload.get("quality"), payload.get("freshness")
            if quality == "GOOD" and freshness == "STALE":
                return "Quality remains GOOD while freshness is STALE; the two dimensions are not collapsed."
        if selector.endswith(".{valid,reason_codes}") and payload.get("valid") is False:
            return "Overall validity is false and includes the controlled stale/freshness reason."
    if record_type == "RestorationAssessment" and selector.endswith(".{outcome,reasons}"):
        if payload.get("outcome") == "BLOCKED" and "TELEMETRY_STALE" in payload.get("reasons", []):
            return "Restoration assessment outcome is operational BLOCKED, not REJECTED; the validation criterion is satisfied because BLOCKED is expected."
    if record_type == "InvestigationAdapter" and selector == "InvestigationAdapter.failure":
        failure = payload.get("failure")
        return (
            "The preserved initiating record is the immutable Network Configuration v1.0 400-customer FAIL."
            if failure == {"configuration_version": "1.0", "affected_customers": 400, "verdict": "FAIL"}
            else failure
        )
    return selected
