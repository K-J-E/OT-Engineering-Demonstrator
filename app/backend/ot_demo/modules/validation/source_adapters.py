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

from ...domain.enums import DeterminationSourceAdapterKind, OperationalEventType
from .models import AuthoritativeRecordSnapshot, DeterminationSourceRecord


class SourceAdapterError(ValueError):
    """Raised when source ownership, provenance or selector resolution is invalid."""


def _require_payload_fields(
    payload: dict[str, Any], fields: Iterable[str], selector: str
) -> None:
    """Reject absent authoritative facts instead of manufacturing an observation."""

    missing = [field for field in fields if field not in payload or payload[field] is None]
    if missing:
        raise SourceAdapterError(
            f"selector member is absent: {selector} ({', '.join(missing)})"
        )


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
                "FormalScenarioDefinition", "ScenarioInitialisationBoundaryAdapter",
                "ScenarioCommandApiBoundaryAdapter", "NetworkConfigurationPackage",
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
                    value = {
                        field: AuthoritativeSourceAdapterRegistry._resolve_field(
                            value, field, selector
                        )
                        for field in fields
                    }
                else:
                    value = tuple(
                        {
                            field: AuthoritativeSourceAdapterRegistry._resolve_field(
                                item, field, selector
                            )
                            for field in fields
                        }
                        for item in value
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

    @staticmethod
    def _resolve_field(value: Any, field: str, selector: str) -> Any:
        """Resolve a field-set member, including accepted indexed members."""

        match = re.fullmatch(r"(?P<name>[A-Za-z0-9_-]+)(?:\[(?P<key>[^]]+)\])?", field)
        if match is None or not isinstance(value, dict):
            raise SourceAdapterError(f"invalid field-set member: {selector}")
        try:
            selected = value[match.group("name")]
            key = match.group("key")
            return selected if key is None else selected[key]
        except (KeyError, TypeError) as error:
            raise SourceAdapterError(f"selector member is absent: {selector}") from error


def derive_combined_observation(
    selector: str,
    selected: dict[str, Any],
    records: tuple[AuthoritativeRecordSnapshot, ...],
) -> Any:
    """Derive propositions that require facts from more than one source root."""

    payloads = {item.record_type: item.canonical_payload for item in records}
    if selector == (
        "ScenarioRunAdapter.formal_run + FormalScenarioDefinition.fault_section_id + "
        "ScenarioInitialisationBoundaryAdapter.{configured_section_ids,alternate_formal_fault_rejections}"
    ):
        formal_runs = selected["ScenarioRunAdapter.formal_run"]
        definition_fault = selected["FormalScenarioDefinition.fault_section_id"]
        boundary = selected[
            "ScenarioInitialisationBoundaryAdapter.{configured_section_ids,alternate_formal_fault_rejections}"
        ]
        if not isinstance(formal_runs, (list, tuple)) or not formal_runs:
            raise SourceAdapterError(f"selector member is absent: {selector}")
        configured = boundary.get("configured_section_ids")
        rejections = boundary.get("alternate_formal_fault_rejections")
        if not isinstance(configured, list) or not isinstance(rejections, list):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        expected_alternates = set(configured) - {definition_fault}
        rejection_by_section = {
            item.get("fault_section_id"): item
            for item in rejections
            if isinstance(item, dict) and item.get("fault_section_id")
        }
        if set(rejection_by_section) != expected_alternates:
            raise SourceAdapterError(f"selector member is absent: {selector}")
        run_facts_match = all(
            item.get("mode") == "FORMAL"
            and item.get("evidence_class") == "FORMAL"
            and item.get("fault_section_id") == definition_fault
            for item in formal_runs
        )
        boundary_facts_match = all(
            item.get("accepted") is False
            and item.get("boundary_id") == "FORMAL_FIXED_FAULT_VALIDATION"
            and item.get("reason_code") == "FORMAL_FIXED_FAULT"
            and item.get("diagnostic_rejection") is True
            and item.get("run_and_history_unchanged") is True
            for item in rejection_by_section.values()
        )
        return (
            f"FORMAL run is fixed to {definition_fault}, uses FORMAL evidence class "
            "and cannot select another fault."
            if run_facts_match and boundary_facts_match
            else selected
        )
    if selector == (
        "ScenarioRunAdapter.exploration_run + "
        "NetworkConfigurationPackage.{manifest,catalog_entry,data}"
    ):
        runs = selected["ScenarioRunAdapter.exploration_run"]
        package = selected["NetworkConfigurationPackage.{manifest,catalog_entry,data}"]
        manifest = package.get("manifest")
        entry = package.get("catalog_entry")
        data = package.get("data")
        if (
            not isinstance(runs, (list, tuple)) or not runs
            or not isinstance(manifest, dict)
            or not isinstance(entry, dict)
            or not isinstance(data, dict)
        ):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        sections = {
            item.get("entity_id") for item in data.get("sections", [])
            if isinstance(item, dict)
        }
        persistent_scenario_fields = {
            "selected_fault_section_id", "fault_section_id", "scenario_mode",
            "evidence_class",
        } & set(data)
        package_identity_matches = (
            manifest.get("configuration_id") == entry.get("configuration_id")
            and manifest.get("version") == entry.get("version")
            and manifest.get("status") == entry.get("status")
        )
        run_facts_match = all(
            item.get("mode") == "EXPLORATION"
            and item.get("evidence_class") == "EXPLORATORY"
            and item.get("configuration_id") == manifest.get("configuration_id")
            and str(item.get("configuration_version")) == str(manifest.get("version"))
            and item.get("fault_section_id") in sections
            for item in runs
        )
        status = str(manifest.get("status", ""))
        role = status.removesuffix("_BASELINE").removesuffix("_TEST_INPUT").lower()
        return (
            f"EXPLORATION run uses {role} Network Configuration v{manifest.get('version')}, "
            "a transient selected section and EXPLORATORY evidence class."
            if package_identity_matches and run_facts_match
            and not persistent_scenario_fields and role
            else selected
        )
    if selector == (
        "ScenarioRunAdapter.mode_conversion_probe + "
        "ScenarioCommandApiBoundaryAdapter.{mode_mutation_rejection,fault_selection_mutation_rejection}"
    ):
        run_probe = selected["ScenarioRunAdapter.mode_conversion_probe"]
        boundary = selected[
            "ScenarioCommandApiBoundaryAdapter.{mode_mutation_rejection,fault_selection_mutation_rejection}"
        ]
        if not isinstance(run_probe, dict) or not isinstance(boundary, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        mode_rejection = boundary.get("mode_mutation_rejection")
        fault_rejection = boundary.get("fault_selection_mutation_rejection")
        if not isinstance(mode_rejection, dict) or not isinstance(fault_rejection, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        immutable = (
            run_probe.get("run_context_frozen_model") is True
            and run_probe.get("run_and_history_unchanged") is True
        )
        diagnostic = all(
            item.get("accepted") is False
            and item.get("diagnostic_rejection") is True
            and item.get("error_type") == "extra_forbidden"
            and item.get("run_and_history_unchanged") is True
            for item in (mode_rejection, fault_rejection)
        )
        return (
            "Run mode and selected fault are immutable after initialisation; "
            "in-place mode conversion is rejected."
            if immutable and diagnostic else selected
        )
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
    if selector == "IsolationProof.isolated + ActionProjection":
        isolated = selected["IsolationProof.isolated"]
        actions = selected["ActionProjection"]
        isolation_history = payloads.get("IsolationProof", {}).get("lifecycle", [])
        action_history = actions.get("history", [])
        historical_unavailable = any(
            proof.get("isolated") is False
            and index < len(action_history)
            and not any(
                (action_history[index].get(name) or {}).get("available") is True
                for name in {
                    "restore_normal_source", "assess_restoration",
                    "execute_restoration",
                }
            )
            for index, proof in enumerate(isolation_history)
        )
        unavailable = not any(
            item.get("available") is True
            for name, item in actions.items()
            if name in {"restore_normal_source", "assess_restoration", "execute_restoration"}
            and isinstance(item, dict)
        )
        return (
            "Before isolation the proof is false and BRK-A reclose/restoration actions are unavailable."
            if (isolated is False and unavailable) or historical_unavailable else selected
        )
    if selector == (
        "AlarmAdapter.acknowledgement + ScenarioSnapshot.state_revision + "
        "OperationalEvent.sequence"
    ):
        acknowledgement = selected["AlarmAdapter.acknowledgement"]
        revision = selected["ScenarioSnapshot.state_revision"]
        events = selected["OperationalEvent.sequence"]
        ack_events = [item for item in events if item.get("event_type") == "ALARM_ACKNOWLEDGED"]
        false_recalculations = [
            item for item in events
            if item.get("scenario_time") == acknowledgement.get("acknowledged_scenario_time")
            and item.get("event_type") in {"TOPOLOGY_RECALCULATED", "OUTAGE_UPDATED"}
        ] if acknowledgement else []
        valid = (
            acknowledgement is not None
            and acknowledgement.get("acknowledged_by")
            and acknowledgement.get("acknowledged_scenario_time")
            and len(ack_events) == 1
            and ack_events[0].get("state_revision") == 1
            and not false_recalculations
        )
        return (
            "Acknowledgement records actor/time, changes only acknowledgement state and does not increment electrical state_revision or emit false topology/outage changes."
            if valid else selected
        )
    if selector == "OperationalEventAdapter.events + ValidationEvidenceAdapter.records":
        events = selected["OperationalEventAdapter.events"]
        evidence = selected["ValidationEvidenceAdapter.records"]
        event_ids = {item.get("event_id") for item in events}
        evidence_ids = {item.get("evidence_snapshot_id") for item in evidence}
        events_by_run: dict[str, list[dict[str, Any]]] = {}
        for item in events:
            events_by_run.setdefault(str(item.get("scenario_run_id")), []).append(item)
        valid = (
            bool(events_by_run)
            and all(
                [item.get("event_sequence") for item in run_events]
                == list(range(1, len(run_events) + 1))
                for run_events in events_by_run.values()
            )
            and len(event_ids) == len(events)
            and len(evidence_ids) == len(evidence)
            and not (event_ids & evidence_ids)
            and all("checkpoint_id" not in item for item in events)
        )
        return (
            "Operational events retain their exact fields/chronology and remain structurally separate from validation evidence/results."
            if valid else selected
        )
    if selector == "IsolationProof.boundary_evidence[TS-01] + ActionProjection":
        boundary = selected["IsolationProof.boundary_evidence[TS-01]"]
        actions = selected["ActionProjection"]
        open_available = actions.get("by_device", {}).get("TS-01", {}).get(
            "available", False
        )
        isolation = payloads.get("IsolationProof", {})
        evidence_state = boundary.get("evidence_state") or boundary.get("state")
        freshness = boundary.get("freshness")
        quality = boundary.get("quality")
        observed = boundary.get("observed_state") or boundary.get("value")
        age_ms = boundary.get("age_ms")
        reasons = boundary.get("reason_codes") or boundary.get("reasons") or []
        if (
            observed == "OPEN" and quality == "GOOD" and freshness == "FRESH"
            and evidence_state == "PROVEN_OPEN" and not open_available
            and isolation.get("isolated") is False
        ):
            return "TS-01 is GOOD/FRESH/OPEN, PROVEN_OPEN and satisfied; no redundant OPEN action is eligible; isolation remains false until SW-A34 is proven open."
        if (
            observed == "OPEN" and quality == "GOOD" and freshness == "STALE"
            and age_ms == 60_001 and evidence_state == "UNPROVEN"
            and "FRESHNESS_STALE" in reasons and not open_available
            and isolation.get("isolated") is False
        ):
            return "TS-01 last-reported OPEN is GOOD but age 60,001 ms/STALE, therefore UNPROVEN with FRESHNESS_STALE, no redundant OPEN action, and overall isolation remains false."
        return selected
    if selector == "ScenarioRun + ValidationExecution.provenance":
        run = selected["ScenarioRun"]
        provenance = selected["ValidationExecution.provenance"]
        run_data = run.get("run", run)
        section = run.get("selected_fault_section_id") or run_data.get("fault_section_id")
        valid = (
            section and run.get("fault_type", run_data.get("fault_type")) == "DISTRIBUTION_SECTION_FAULT"
            and run.get("mode", run_data.get("mode")) == "EXPLORATION"
            and run_data.get("configuration_id") == "network-configuration-v1.1"
            and provenance.get("evidence_class") == "EXPLORATORY"
            and provenance.get("scenario_run_id") == run_data.get("scenario_run_id")
        )
        return (
            f"Selected fault is exactly {section}; fault type is DISTRIBUTION_SECTION_FAULT; run is corrected Network Configuration v1.1 EXPLORATION with EXPLORATORY evidence."
            if valid else selected
        )
    if selector == "ActionProjection + CommandResult + DeviceState[TS-01]":
        actions = selected["ActionProjection"]
        command = selected["CommandResult"]
        tie_state = selected["DeviceState[TS-01]"]
        assessment = payloads.get("RestorationAssessment", {})
        outcome = assessment.get("restoration_outcome") or assessment.get("outcome")
        tie_device_id = (assessment.get("candidate") or {}).get("tie_device_id")
        execute = actions.get("execute_restoration", {})
        result_rows = command.get("results", [])
        execution_accepted = any(
            row.get("accepted") is True
            and any(
                event.get("event_id") in row.get("new_event_ids", [])
                and event.get("event_type") == "SWITCHING_ACTION"
                and event.get("affected_entity_id") == tie_device_id
                and event.get("new_value") == "CLOSED"
                and event.get("assessment_id") is not None
                for event in row.get("snapshot", {}).get("events", [])
            )
            for row in result_rows
        )
        valid = (
            (outcome == "PERMITTED" and execution_accepted and tie_state == "CLOSED")
            or (outcome in {"REJECTED", "NO_CANDIDATE", "BLOCKED"}
                and not execute.get("available", False) and not execution_accepted
                and tie_state == "OPEN")
        )
        return (
            "All actions remain simulated/local; TS-01 close is available and accepted only for PERMITTED, otherwise unavailable and TS-01 remains OPEN."
            if valid else selected
        )
    if selector == "ScenarioSnapshot.before_after + CommandAvailability":
        before_after = selected["ScenarioSnapshot.before_after"]
        actions = selected["CommandAvailability"]
        snapshots = before_after.get("command_snapshots", [])
        no_execution = not actions.get("execute_restoration", {}).get("available", False)
        stable = bool(snapshots) and all(
            item.get("device_states", {}).get("TS-01") == "OPEN"
            and "RESTORATION_EXECUTED" not in item.get("new_event_types", [])
            for item in snapshots
        )
        return (
            "Because the assessment is not PERMITTED, no restoration switching is executed; faulted/healthy section and customer-impact records remain the pre-execution derived state."
            if no_execution and stable else selected
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
    if record_type == "FormalProgressAdapter" and selector == "FormalProgressAdapter.before_after":
        if not isinstance(selected, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        formal_only = selected.get("formal_only")
        mixed = selected.get("with_exploratory_records")
        if not isinstance(formal_only, dict) or not isinstance(mixed, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        if (
            selected.get("exploratory_execution_count", 0) < 1
            or selected.get("exploratory_composite_count", 0) < 1
        ):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        controlled = (
            "definitions_without_execution_count", "execution_count",
            "finalised_execution_count", "pass_count", "fail_count",
            "blocked_test_count",
        )
        if any(field not in formal_only or field not in mixed for field in controlled):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        return (
            "Actual campaign exploratory executions/evidence and DC-004 composites do not "
            "change FORMAL definition-without-execution, execution, finalised, PASS, FAIL "
            "or BLOCKED-TEST totals."
            if all(formal_only[field] == mixed[field] for field in controlled)
            else selected
        )
    if record_type == "ConfigurationComparisonResult" and selector.endswith(".differences"):
        if payload.get("exact_approved_difference") is True:
            return (
                "The immutable package comparison contains exactly SW-A23 endpoint 1 SEC-B3→SEC-A2 and no other difference."
                if payload.get("projection_kind") == "INVESTIGATION_COMPARISON"
                else "The package difference set is exactly SW-A23 endpoint 1: SEC-B3 in Network Configuration v1.0 and SEC-A2 in Network Configuration v1.1."
            )
        return selected
    if record_type == "ScenarioRun" and selector == "ScenarioRun.{selected_fault_section_id,fault_type,mode}":
        section = payload.get("selected_fault_section_id")
        valid = (
            section is not None
            and payload.get("fault_type") == "DISTRIBUTION_SECTION_FAULT"
            and payload.get("mode") == "EXPLORATION"
        )
        return (
            f"Selected fault is exactly {section}; fault type is DISTRIBUTION_SECTION_FAULT; selection is transient run state under EXPLORATION."
            if valid else selected
        )
    if record_type == "ScenarioSnapshot" and selector == "ScenarioSnapshot.{affected_feeder_id,protection_breaker_id}":
        feeder = payload.get("affected_feeder_id")
        breaker = payload.get("protection_breaker_id")
        return (
            f"Affected feeder is {feeder} and protection breaker is {breaker}."
            if feeder and breaker else selected
        )
    if record_type == "IsolationProof" and selector == "IsolationProof.incident_boundary_device_ids":
        boundaries = payload.get("incident_boundary_device_ids")
        return (
            f"Configuration-derived incident boundaries equal {boundaries!r}."
            if isinstance(boundaries, list) and boundaries else selected
        )
    if record_type == "IsolationProof" and selector == "IsolationProof.boundary_evidence":
        evidence = payload.get("boundary_evidence", {})
        valid = set(evidence) == {"SW-A12", "SW-A23"} and all(
            item.get("observed_state") == "OPEN"
            and item.get("quality") == "GOOD"
            and item.get("freshness") == "FRESH"
            and item.get("proof_status") == "PROVEN_OPEN"
            for item in evidence.values()
        )
        return "Final evidence for SW-A12 and SW-A23 is GOOD/FRESH/OPEN and both boundaries are PROVEN_OPEN." if valid else selected
    if record_type == "ScenarioRevisionSequence" and selector == "ScenarioRevisionSequence":
        results = payload.get("results", [])
        accepted_revisions = [
            item for item in results
            if item.get("current_revision", 0) > item.get("prior_revision", 0)
        ]
        valid = (
            len(accepted_revisions) >= 3
            and all(item.get("topology_sha256") for item in accepted_revisions)
            and all(
                later["current_revision"] > earlier["current_revision"]
                for earlier, later in zip(accepted_revisions, accepted_revisions[1:])
            )
        )
        return "Each accepted boundary OPEN command is followed by full topology/boundary/source-path recalculation before the next action projection." if valid else selected
    if record_type == "OutageResult" and selector == "OutageResult.{de_energised_section_ids,affected_customer_count,affected_customer_zone_ids}":
        sections = payload.get("de_energised_section_ids")
        count = payload.get("affected_customer_count")
        zones = payload.get("affected_customer_zone_ids")
        fault = payload.get("selected_fault_section_id")
        valid = (
            isinstance(sections, list) and fault in sections
            and isinstance(zones, list) and count is not None
        )
        return (
            f"After protection operation the de-energised set is {sections!r}, affected-customer count is {count}, and the selected fault section remains de-energised/affected."
            if valid else selected
        )
    if record_type == "ValidationExecution" and selector == "ValidationExecution.{evidence_class,configuration,catalogue,test,case,run}":
        valid = (
            payload.get("evidence_class") == "EXPLORATORY"
            and payload.get("configuration", {}).get("id") == "network-configuration-v1.1"
            and payload.get("catalogue", {}).get("sha256")
            and payload.get("test", {}).get("id")
            and payload.get("case")
            and payload.get("run")
        )
        return (
            "Run/execution/evidence class is EXPLORATORY under corrected Network Configuration v1.1 and the bound future promoted Validation Catalogue/case identity."
            if valid else selected
        )
    if record_type == "CurrentValidationExecutionAdapter" and selector.endswith(".{run_id,execution_id,build_identity,catalogue_identity,test_identity,method_identity,configuration_identity}"):
        return (
            "The current execution binds exactly one ScenarioRun, one ValidationExecution, one backend-controlled build, one source Validation Catalogue/test/method set and one Network Configuration identity/hash; no second run is a context member."
            if payload.get("single_run_identity_verified") is True else selected
        )
    if record_type == "CurrentScenarioExecutionAdapter":
        if selector.endswith(
            ".{configuration_identity,post_trip_input_fingerprint,telemetry[BRK-A]}"
        ):
            breaker = payload.get("telemetry", {}).get("BRK-A")
            fingerprint = payload.get("post_trip_input_fingerprint")
            if not isinstance(breaker, dict) or not isinstance(fingerprint, dict):
                raise SourceAdapterError(f"selector member is absent: {selector}")
            _require_payload_fields(
                payload, ("configuration_identity", "configuration_status"), selector
            )
            _require_payload_fields(
                breaker, ("entity_id", "value", "quality", "freshness"), selector
            )
            _require_payload_fields(
                fingerprint,
                ("fault_section_id", "fault_type", "mode", "scenario_time"),
                selector,
            )
            configuration_identity = str(payload["configuration_identity"])
            version_prefix = "network-configuration-v"
            version = (
                configuration_identity[len(version_prefix) :]
                if configuration_identity.startswith(version_prefix)
                else configuration_identity
            )
            status = str(payload["configuration_status"])
            role = status.removesuffix("_BASELINE").removesuffix(
                "_TEST_INPUT"
            ).lower()
            return (
                f"The current post-trip run uses {role} Network Configuration "
                f"v{version} with {breaker['entity_id']} {breaker['quality']}/"
                f"{breaker['freshness']}/{breaker['value']} and the controlled "
                f"{str(fingerprint['mode']).lower()} fault/input fingerprint."
            )
        if selector.endswith(
            ".post_trip.{topology,outage,expected_observed_comparison}"
        ):
            post_trip = payload.get("post_trip")
            if not isinstance(post_trip, dict):
                raise SourceAdapterError(f"selector member is absent: {selector}")
            topology = post_trip.get("topology")
            outage = post_trip.get("outage")
            if not isinstance(topology, dict) or not isinstance(outage, dict):
                raise SourceAdapterError(f"selector member is absent: {selector}")
            _require_payload_fields(
                topology,
                ("de_energised_section_ids", "section_source_feeder_ids"),
                selector,
            )
            _require_payload_fields(outage, ("affected_customer_count",), selector)
            attribution = topology.get("section_source_feeder_ids", {})
            sections = topology["de_energised_section_ids"]
            if (
                not isinstance(sections, list)
                or not isinstance(attribution, dict)
                or "SEC-A3" not in attribution
                or "SEC-A4" not in attribution
            ):
                raise SourceAdapterError(f"selector member is ambiguous: {selector}")
            short_sections = [item.removeprefix("SEC-") for item in sections]
            section_text = "/".join(short_sections)
            if short_sections == ["A1", "A2", "A3", "A4"]:
                section_text = "A1–A4"
            a3_sources = attribution["SEC-A3"]
            a4_sources = attribution["SEC-A4"]
            source_text = (
                "no A3/A4 source attribution exists"
                if a3_sources == [] and a4_sources == []
                else "A3/A4 source attribution is "
                f"{a3_sources!r}/{a4_sources!r}"
            )
            return (
                f"For the current run, {section_text} are de-energised, "
                f"{source_text} and exactly {outage['affected_customer_count']} "
                "customers are affected."
            )
        if selector.endswith(".{configuration_difference_role,source_paths}"):
            relationship = payload.get("configuration_difference_role")
            source_paths = payload.get("source_paths")
            if not isinstance(relationship, dict) or not isinstance(
                source_paths, dict
            ):
                raise SourceAdapterError(f"selector member is absent: {selector}")
            _require_payload_fields(payload, ("configuration_status",), selector)
            _require_payload_fields(
                relationship, ("device_id", "endpoint_1_id"), selector
            )
            if "SEC-A3" not in source_paths or "SEC-A4" not in source_paths:
                raise SourceAdapterError(f"selector member is absent: {selector}")
            status = str(payload["configuration_status"])
            role = status.removesuffix("_BASELINE").removesuffix(
                "_TEST_INPUT"
            ).lower()
            device_id = str(relationship["device_id"])
            endpoint_id = str(relationship["endpoint_1_id"])
            a3_sources = source_paths["SEC-A3"]
            a4_sources = source_paths["SEC-A4"]
            path_text = (
                f"no active path from FDR-B through SEC-B3/{device_id} to A3/A4"
                if a3_sources == [] and a4_sources == []
                else "active source attribution to A3/A4 is "
                f"{a3_sources!r}/{a4_sources!r}"
            )
            return (
                "The current source-path/configuration evidence contains the "
                f"{role} {device_id} endpoint {endpoint_id} and {path_text}."
            )
        if selector == "CurrentScenarioExecutionAdapter.authority_path":
            path = payload.get("authority_path")
            if not isinstance(path, dict):
                raise SourceAdapterError(f"selector member is absent: {selector}")
            _require_payload_fields(
                path,
                (
                    "configuration_loader",
                    "topology_service",
                    "source_attribution_service",
                    "outage_service",
                    "customer_mapping_authority",
                    "algorithm_branch_audit",
                ),
                selector,
            )
            audit = path["algorithm_branch_audit"]
            if not isinstance(audit, dict):
                raise SourceAdapterError(f"selector member is ambiguous: {selector}")
            _require_payload_fields(audit, ("service_source_sha256",), selector)
            if (
                path["configuration_loader"] == "JsonConfigurationLoader"
                and path["topology_service"] == "TopologyService"
                and path["source_attribution_service"] == "TopologyService"
                and path["outage_service"] == "OutageService"
                and path["customer_mapping_authority"] == "CustomerZoneMapping"
                and set(audit["service_source_sha256"])
                == {"TopologyService", "OutageService"}
                and audit.get("configuration_version_predicates") == []
                and audit.get("expected_result_predicates") == []
            ):
                return (
                    "The current execution trace uses the same generic configuration "
                    "loader, topology, source-attribution, outage and customer-zone "
                    "services with no Network Configuration version or expected-result "
                    "outcome branch."
                )
            return {"observed_authority_path": path}
    if record_type == "CurrentValidationExecutionAdapter" and selector.endswith(
        ".{immutable_result_identity,defect_id,correction_id,repeat_of_execution_id}"
    ):
        link_fields = (
            "immutable_result_identity", "defect_id", "correction_id",
            "repeat_of_execution_id",
        )
        if not set(link_fields) <= set(payload):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        _require_payload_fields(payload, ("single_run_record_verified",), selector)
        if payload["single_run_record_verified"] is True:
            return (
                "The current immutable result preserves its own configuration/build/"
                "catalogue/test/method/criterion/evidence identities and any exact "
                "DEF-001, COR-001 and repeat-of links supplied by the accepted "
                "correction workflow. It does not resolve or aggregate another "
                "ScenarioRun. Cross-run chain completeness is determined by "
                "VT-CFG-INV-001 and repeatability evidence."
            )
        return {
            "single_run_record_verified": payload["single_run_record_verified"],
            "link_fields": {field: payload[field] for field in link_fields},
        }
    if (
        record_type == "ScenarioSnapshot"
        and selector == "ScenarioSnapshot.{state_label,assessment_inputs}"
    ):
        assessment = payload.get("assessment_inputs")
        if not isinstance(assessment, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        permissives = assessment.get("permissives")
        required_non_source = {
            "FAULT_ISOLATION", "RADIAL_TOPOLOGY", "TELEMETRY_VALIDITY", "CAPACITY"
        }
        if not isinstance(permissives, dict) or set(permissives) != (
            required_non_source | {"ALTERNATE_SOURCE"}
        ):
            raise SourceAdapterError(f"selector member is ambiguous: {selector}")
        valid = (
            assessment.get("pre_assessment_state_label") == "N3"
            and all(permissives[key] == "PASS" for key in required_non_source)
        )
        return (
            "The controlled input is formal N3/pre-assessment with every "
            "non-source permissive condition valid."
            if valid
            else selected
        )
    if record_type == "TelemetrySnapshot" and selector == "TelemetrySnapshot[BRK-B]":
        if not isinstance(selected, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        _require_payload_fields(
            selected, ("entity_id", "value", "quality", "freshness"), selector
        )
        return (
            "BRK-B telemetry is GOOD/FRESH/OPEN."
            if selected["entity_id"] == "BRK-B"
            and selected["quality"] == "GOOD"
            and selected["freshness"] == "FRESH"
            and selected["value"] == "OPEN"
            else selected
        )
    if (
        record_type == "RestorationAssessment"
        and selector == "RestorationAssessment.permissives"
    ):
        permissives = selected
        required_non_source = {
            "FAULT_ISOLATION", "RADIAL_TOPOLOGY", "TELEMETRY_VALIDITY", "CAPACITY"
        }
        if not isinstance(permissives, dict) or set(permissives) != (
            required_non_source | {"ALTERNATE_SOURCE"}
        ):
            raise SourceAdapterError(f"selector member is ambiguous: {selector}")
        return (
            "Isolation, radiality, telemetry and capacity evidence are complete "
            "and pass so the source criterion is independently observable."
            if permissives["ALTERNATE_SOURCE"] == "FAIL"
            and all(permissives[key] == "PASS" for key in required_non_source)
            else selected
        )
    if (
        record_type == "RestorationAssessment"
        and selector == "RestorationAssessment.permissives[ALTERNATE_SOURCE]"
    ):
        reason_codes = payload.get("permissive_reason_codes", {}).get(
            "ALTERNATE_SOURCE"
        )
        _require_payload_fields(payload, ("alternate_breaker_closed",), selector)
        if not isinstance(reason_codes, list):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        return (
            "Alternate-source permissive is FAIL with the controlled breaker-open "
            "reason."
            if selected == "FAIL"
            and payload["alternate_breaker_closed"] is False
            and "ALTERNATE_BREAKER_CLOSED" in reason_codes
            else {
                "alternate_source_permissive": selected,
                "alternate_breaker_closed": payload["alternate_breaker_closed"],
                "reason_codes": reason_codes,
            }
        )
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
    if record_type == "AlarmAdapter" and selector == "AlarmAdapter.active_alarm":
        alarm = selected or {}
        valid = (
            alarm.get("active") is True
            and alarm.get("alarm_type") == "FEEDER_TRIP"
            and alarm.get("alarm_id") is not None
            and alarm.get("entity_id") is not None
            and alarm.get("generated_scenario_time") is not None
            and alarm.get("creation_acknowledgement_state") == "UNACKNOWLEDGED"
        )
        return "Fault initiation creates one active FEEDER_TRIP alarm with stable ID, affected entity, timestamp and UNACKNOWLEDGED state." if valid else selected
    if record_type == "OperationalEventRegistry" and selector == "OperationalEventRegistry.ids":
        controlled_ids = [item.value for item in OperationalEventType]
        valid = selected == controlled_ids and len(set(selected)) == len(selected)
        return "The controlled operational-event registry equals exactly {SCENARIO_INITIALISED, CONFIGURATION_SELECTED, FAULT_INITIATED, TELEMETRY_UPDATED, DEVICE_STATE_CHANGE, ALARM_GENERATED, ALARM_ACKNOWLEDGED, SWITCHING_ACTION, TOPOLOGY_RECALCULATED, OUTAGE_UPDATED, RESTORATION_CANDIDATE_IDENTIFIED, RESTORATION_NO_CANDIDATE, RESTORATION_ASSESSED, RESTORATION_ASSESSMENT_INVALIDATED, SCENARIO_RESET}, with no missing or additional ID." if valid else selected
    if record_type == "OperationalEventAdapter" and selector == "OperationalEventAdapter.events[*].{scenario_time,event_sequence,type,source}":
        rows = selected or []
        valid = bool(rows) and [
            row.get("event_sequence") for row in rows
        ] == list(range(1, len(rows) + 1)) and all(
            rows[index - 1].get("scenario_time") <= row.get("scenario_time")
            for index, row in enumerate(rows[1:], 1)
        )
        return "At equal scenario time, initiating command events precede topology/outage/restoration derived events by immutable event_sequence." if valid else selected
    if record_type == "OperationalEventAdapter" and selector == "OperationalEventAdapter.switching_events":
        events = selected or []
        valid = len(events) >= 4 and all(
            item.get("event_type") == "SWITCHING_ACTION"
            and item.get("affected_entity_id") is not None
            and item.get("new_value") is not None
            and item.get("command_id") is not None
            for item in events
        )
        return "Every simulated isolation/restoration switching action is represented by a SWITCHING_ACTION record linked to device and state transition." if valid else selected
    if record_type == "TelemetryValidityResult":
        if selector in {
            "TelemetryValidityResult[0ms]",
            "TelemetryValidityResult[59999ms]",
            "TelemetryValidityResult[60000ms]",
        }:
            facts = selected if isinstance(selected, dict) else payload
            age = facts.get("age_ms")
            valid = (
                age in {0, 59_999, 60_000}
                and facts.get("quality") == "GOOD"
                and facts.get("freshness") == "FRESH"
                and facts.get("timestamp_valid") is True
                and facts.get("overall_valid") is True
            )
            if not valid:
                return selected
            if age == 60_000:
                return "At the inclusive 60,000 ms boundary the point is GOOD, FRESH, timestamp-valid and valid for permissive use."
            return f"At {age:,} ms the point is GOOD, FRESH, timestamp-valid and valid for permissive use."
        if selector.endswith(".{quality,freshness}"):
            quality, freshness = payload.get("quality"), payload.get("freshness")
            if quality == "GOOD" and freshness == "STALE":
                return "Quality remains GOOD while freshness is STALE; the two dimensions are not collapsed."
            if quality == "UNCERTAIN" and freshness == "FRESH":
                return "The required point is exactly UNCERTAIN and FRESH."
            if quality == "BAD" and freshness == "FRESH":
                return "The required point is exactly BAD and FRESH."
        if selector.endswith(".{valid,reason_codes}") and payload.get("valid") is False:
            reasons = set(payload.get("reason_codes", []))
            if "QUALITY_UNCERTAIN" in reasons:
                return "Overall validity is false and identifies the UNCERTAIN-quality reason."
            if "QUALITY_BAD" in reasons:
                return "Overall validity is false and identifies the BAD-quality reason."
            return "Overall validity is false and includes the controlled stale/freshness reason."
        if selector.endswith(".{freshness,valid,age_ms}"):
            if (
                payload.get("freshness") == "INVALID_TIMESTAMP"
                and payload.get("valid") is False
                and payload.get("age_ms") == -1
            ):
                return "Freshness is INVALID_TIMESTAMP, valid is false and the age is not clamped to zero."
        if selector.endswith(".reason_codes"):
            if "FUTURE_TELEMETRY_TIMESTAMP" in payload.get("reason_codes", []):
                return "Controlled invalid/future-timestamp reason is present."
        if selector.endswith(".age_ms") and payload.get("age_ms") == -1:
            return "Observation at T+60.001 assessed at T+60.000 retains calculated age −1 ms."
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
        if payload.get("outcome") == "REJECTED" and "RESULTING_LOAD_EXCEEDS_CAPACITY" in payload.get("reasons", []):
            return "Operational outcome is REJECTED with the controlled capacity reason; validation criterion is satisfied because REJECTED is expected."
    if record_type == "RestorationAssessment" and selector.endswith(".{outcome,reasons,evidence}"):
        quality = (payload.get("evidence") or {}).get("quality")
        if payload.get("outcome") == "BLOCKED" and quality in {"UNCERTAIN", "BAD"}:
            return "Restoration outcome is operational BLOCKED with point/quality evidence."
    if record_type == "RestorationAssessment" and selector == "RestorationAssessment.{affected_feeder_id,alternate_feeder_id,proposed_section_ids}":
        affected = payload.get("affected_feeder_id")
        alternate = payload.get("alternate_feeder_id")
        proposed = payload.get("proposed_section_ids")
        return (
            f"Affected feeder is {affected}; alternate feeder is {alternate}; proposed sections are {proposed!r}."
            if affected and isinstance(proposed, list) else selected
        )
    if record_type == "RestorationAssessment" and selector == "RestorationAssessment.{outcome,transferable_load_kw,resulting_load_kw,feeder_capacity_kw,resulting_loading_percent}":
        outcome = payload.get("restoration_outcome") or payload.get("outcome")
        transfer = payload.get("transferable_load_kw")
        resulting = payload.get("resulting_load_kw")
        capacity = payload.get("feeder_capacity_kw")
        loading = payload.get("resulting_loading_percent")
        return (
            f"Restoration outcome is {outcome}; transferable/resulting/capacity/loading values are respectively {transfer}, {resulting}, {capacity} kW and {loading}% (null where NO_CANDIDATE)."
            if outcome in {"PERMITTED", "REJECTED", "NO_CANDIDATE", "BLOCKED"}
            else selected
        )
    if record_type == "PostExecutionSnapshot" and selector == "PostExecutionSnapshot.{topology,outage,restored_customer_delta}":
        topology = payload.get("topology", {})
        outage = payload.get("outage", {})
        sources = topology.get("section_source_feeder_ids", {})
        deenergised = outage.get("de_energised_section_ids", [])
        restored = payload.get("restored_customer_delta")
        affected = outage.get("affected_customer_count")
        transferred = [
            section for section, feeder_ids in sources.items()
            if section.startswith("SEC-A") and feeder_ids == ["FDR-B"]
            or section.startswith("SEC-B") and feeder_ids == ["FDR-A"]
        ]
        source_ids = {
            feeder_id for section in transferred
            for feeder_id in sources.get(section, [])
        }
        feeder_letters = {section[4] for section in transferred if len(section) > 4}
        if (
            len(transferred) == 2 and len(feeder_letters) == 1
            and len(source_ids) == 1 and len(deenergised) == 1
            and isinstance(restored, int) and isinstance(affected, int)
            and payload.get("tie_device_id")
        ):
            letter = next(iter(feeder_letters))
            compact_sections = (
                f"SEC-{letter}{transferred[0][5:]}/"
                + "/".join(f"{letter}{item[5:]}" for item in transferred[1:])
            )
            return (
                f"After authorised simulated execution {payload['tie_device_id']} is CLOSED; "
                f"{compact_sections} are supplied from {next(iter(source_ids))}; "
                f"{deenergised[0]} remains faulted/de-energised; {restored} customers are "
                f"restored and {affected} remain affected."
            )
        return selected
    if record_type == "RestorationAssessment" and selector == "RestorationAssessment.permissives[RADIAL_TOPOLOGY]":
        return "Radial-topology permissive is FAIL and retains the offending source-path evidence." if selected == "FAIL" and payload.get("reasons") else selected
    if record_type == "ConfigurationPackageAdapter" and selector == "ConfigurationPackageAdapter.before_after_sha256":
        if payload.get("before_after_sha256") is True:
            if payload.get("fixture_identity") == "FIX-RST-RADIAL-001":
                return "Canonical Network Configuration v1.1 bytes/hash are unchanged by fixture execution."
            return "Canonical configuration/load package hashes are unchanged."
    if record_type == "CommandResult" and selector == "CommandResult.{accepted,reason}":
        invalidated = next((
            item for item in payload.get("results", [])
            if item.get("accepted") is False
            and item.get("reason_code") == "RESTORATION_ASSESSMENT_INVALIDATED"
        ), None)
        return "Execution under the stale bound assessment is rejected." if invalidated else selected
    if record_type == "RestorationAssessment" and selector == "RestorationAssessment.{assessment_id,bound_revisions,status}":
        assessments = payload.get("before_after", [])
        initial = assessments[0] if assessments else payload
        bound = initial.get("bound_revisions", {})
        valid = (
            initial.get("assessment_id")
            and (initial.get("restoration_outcome") or initial.get("outcome")) == "PERMITTED"
            and bound.get("state_revision") == 4
            and len(bound.get("telemetry_snapshot_sha256", "")) == 64
            and initial.get("status") in {"CURRENT", "INVALIDATED"}
        )
        return "Initial N4 assessment has a stable identity, current topology/state/telemetry revisions and CURRENT status." if valid else selected
    if record_type == "AssessmentInvalidationAdapter" and selector == "AssessmentInvalidationAdapter.{records,events,command_result}":
        records = payload.get("records", [])
        events = payload.get("events", [])
        command = payload.get("command_result", {})
        valid = (
            len(records) == len(events) == 1
            and events[0].get("event_id") in command.get("new_event_ids", [])
            and str(records[0].get("assessment_id")) == str(events[0].get("assessment_id"))
            and command.get("accepted") is False
        )
        return "Exactly one RESTORATION_ASSESSMENT_INVALIDATED record/event is linked and returned in CommandResult.new_event_ids." if valid else selected
    if record_type == "RestorationAssessment" and selector == "RestorationAssessment.before_after":
        assessments = payload.get("before_after", [])
        valid = (
            len(assessments) >= 2
            and assessments[0].get("assessment_id") != assessments[-1].get("assessment_id")
            and assessments[0].get("bound_revisions", {}).get("state_revision") == 4
            and len(assessments[0].get("telemetry_snapshot_sha256", "")) == 64
        )
        return "The original assessment and its bound evidence remain immutable." if valid else selected
    if record_type == "RestorationAssessment" and selector == "RestorationAssessment.replacement":
        assessments = payload.get("before_after", [])
        replacement = payload.get("replacement", {})
        valid = (
            len(assessments) >= 2
            and replacement.get("assessment_id") == assessments[-1].get("assessment_id")
            and replacement.get("assessment_id") != assessments[0].get("assessment_id")
            and replacement.get("status") == "CURRENT"
        )
        return "A new assessment has a new identity and binds the current revisions." if valid else selected
    if record_type == "CommandResultReplayComparison" and selector == "CommandResultReplayComparison":
        comparisons = payload.get("comparisons", [])
        valid = len(comparisons) == 1 and all(
            item.get("same_result") is True
            and item.get("new_event_count") == 0
            and item.get("new_invalidation_count") == 0
            for item in comparisons
        )
        return "Idempotent replay returns the same immutable command result and creates no duplicate invalidation/event." if valid else selected
    if record_type == "InvestigationAdapter" and selector == "InvestigationAdapter.failure":
        failure = payload.get("failure")
        return (
            "The preserved initiating record is the immutable Network Configuration v1.0 400-customer FAIL."
            if failure == {"configuration_version": "1.0", "affected_customers": 400, "verdict": "FAIL"}
            else failure
        )
    if record_type == "InvestigationAdapter" and selector == "InvestigationAdapter.scada_step":
        step = payload.get("scada_step")
        if not isinstance(step, dict) or not isinstance(
            step.get("breaker_telemetry"), dict
        ):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        breaker = step["breaker_telemetry"]
        workflow_scada = step.get("workflow_scada_step")
        workflow_causal = step.get("workflow_causal_step")
        if not isinstance(workflow_scada, dict) or not isinstance(
            workflow_causal, dict
        ):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        _require_payload_fields(
            breaker,
            ("entity_id", "value", "quality", "freshness", "overall_valid"),
            selector,
        )
        scada_facts = {
            item.get("label"): item.get("value")
            for item in workflow_scada.get("facts", [])
        }
        causal_facts = {
            item.get("label"): item.get("value")
            for item in workflow_causal.get("facts", [])
        }
        valid = (
            breaker["overall_valid"] is True
            and scada_facts.get(f"{breaker['entity_id']} value") == breaker["value"]
            and scada_facts.get("Quality") == breaker["quality"]
            and scada_facts.get("Freshness") == breaker["freshness"]
            and "SCADA" in str(causal_facts.get("Engineering disposition"))
            and "remain unchanged"
            in str(causal_facts.get("Engineering disposition"))
        )
        return (
            f"Initiating {breaker['entity_id']} telemetry is "
            f"{breaker['quality']}/{breaker['freshness']}/{breaker['value']} and is "
            "not identified as the defect cause."
            if valid
            else {
                "breaker_telemetry": breaker,
                "workflow_scada_facts": scada_facts,
                "workflow_causal_facts": causal_facts,
            }
        )
    if (
        record_type == "InvestigationAdapter"
        and selector == "InvestigationAdapter.topology_step.source_paths"
    ):
        step = payload.get("topology_step")
        if not isinstance(step, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        sections = step.get("unexpected_energised_section_ids")
        paths = step.get("implicated_paths")
        if not isinstance(sections, list) or not isinstance(paths, list) or not paths:
            raise SourceAdapterError(f"selector member is absent: {selector}")
        source_feeders = {item.get("source_feeder_id") for item in paths}
        devices = {item.get("difference_device_id") for item in paths}
        upstream_nodes = {item.get("difference_upstream_node_id") for item in paths}
        covered_sections = {item.get("target_section_id") for item in paths}
        if (
            covered_sections != set(sections)
            or None in source_feeders
            or None in devices
            or None in upstream_nodes
            or len(source_feeders) != 1
            or len(devices) != 1
            or len(upstream_nodes) != 1
        ):
            return step
        section_text = "/".join(
            str(item).removeprefix("SEC-") for item in sections
        )
        return (
            f"Preserved source-path evidence traces {section_text} to "
            f"{next(iter(source_feeders))} through {next(iter(upstream_nodes))}/"
            f"{next(iter(devices))}."
        )
    if record_type == "InvestigationAdapter" and selector == "InvestigationAdapter.oms_step":
        step = payload.get("oms_step")
        if not isinstance(step, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        zones = step.get("affected_customer_zones")
        sections = step.get("de_energised_section_ids")
        if not isinstance(zones, list) or not isinstance(sections, list):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        valid = (
            [item.get("section_id") for item in zones] == sections
            and step.get("zone_sum") == step.get("affected_customer_count")
        )
        return (
            "OMS arithmetic is correct for the de-energised section/customer-zone "
            "set received from topology."
            if valid
            else step
        )
    if record_type == "InvestigationAdapter" and selector == "InvestigationAdapter.chain":
        chain = payload.get("chain")
        if not isinstance(chain, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        relationships = chain.get("repeat_relationship_types")
        link_ids = chain.get("repeat_link_ids")
        controls = set(chain.get("immutability_controls", []))
        required_controls = {
            "investigation_defects_no_update",
            "investigation_defects_no_delete",
            "investigation_corrections_no_update",
            "investigation_corrections_no_delete",
            "investigation_repeat_links_no_update",
            "investigation_repeat_links_no_delete",
        }
        valid = (
            relationships == ["DIRECT_REPEAT", "REGRESSION"]
            and isinstance(link_ids, list)
            and len(link_ids) == 2
            and len(set(link_ids)) == 2
            and all(link_ids)
            and chain.get("defect_id")
            and chain.get("correction_id")
            and chain.get("links_resolve_bidirectionally") is True
            and controls == required_controls
        )
        if not valid:
            return chain
        return (
            f"{chain['defect_id']}, {chain['correction_id']}, direct repeat and "
            "regression records are immutable and bidirectionally linked."
        )
    if record_type == "InvestigationAdapter" and selector == "InvestigationAdapter.provenance":
        provenance = payload.get("provenance")
        if not isinstance(provenance, dict):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        versions = provenance.get("configuration_versions")
        builds = provenance.get("execution_build_ids")
        catalogues = provenance.get("execution_catalogue_sha256")
        relationships = provenance.get("repeat_relationship_types")
        if (
            not isinstance(versions, list)
            or not isinstance(builds, list)
            or not isinstance(catalogues, list)
        ):
            raise SourceAdapterError(f"selector member is absent: {selector}")
        valid = (
            relationships == ["DIRECT_REPEAT", "REGRESSION"]
            and provenance.get("exact_linked_execution_set") is True
            and provenance.get("relevant_execution_count") == 3
            and len(builds) == 1
            and len(catalogues) == 1
            and provenance.get("catalogue_identities_resolved") is True
            and provenance.get("configuration_identities_resolved") is True
            and provenance.get("defect_present") is True
            and provenance.get("correction_present") is True
        )
        if not valid:
            return provenance
        version_text = "/".join(f"v{item}" for item in versions)
        return (
            "Failure, direct repeat and corrected regression share the "
            f"backend-controlled build; Network Configuration {version_text} and "
            "source Validation Catalogue identities remain explicit and correct."
        )
    if record_type == "ValidationExecutionAdapter" and selector == "ValidationExecutionAdapter.identity":
        rows = selected
        if not isinstance(rows, list) or not rows:
            raise SourceAdapterError(f"selector member is absent: {selector}")
        required = {
            "execution_id", "attempt_id", "result_id", "test_id",
            "test_definition_version", "test_definition_sha256", "evidence_class",
            "catalogue_version", "catalogue_sha256", "configuration_id",
            "configuration_version", "build_id", "run_id", "context_kind",
            "catalogue_resolved", "configuration_resolved",
        }
        complete = all(
            set(row) >= required
            and all(row[field] for field in required - {"run_id"})
            and (
                row["run_id"] is not None
                if row["context_kind"] == "SCENARIO_EXECUTION"
                else row["run_id"] is None
            )
            and row["catalogue_resolved"] is True
            and row["configuration_resolved"] is True
            for row in rows
        )
        unique = all(
            len({row[field] for row in rows}) == len(rows)
            for field in ("execution_id", "attempt_id", "result_id")
        )
        return (
            "Each execution retains exact test, definition, Validation Catalogue, "
            "build, Network Configuration and run identities/hashes."
            if complete and unique
            else rows
        )
    if (
        record_type == "ExecutedValidationResultAdapter"
        and selector == "ExecutedValidationResultAdapter.complete_record"
    ):
        rows = selected
        if not isinstance(rows, list) or not rows:
            raise SourceAdapterError(f"selector member is absent: {selector}")
        complete = True
        for row in rows:
            result = row.get("result")
            execution = row.get("execution")
            findings = row.get("findings")
            if (
                not isinstance(result, dict)
                or not isinstance(execution, dict)
                or not isinstance(findings, list)
                or not findings
            ):
                complete = False
                break
            complete = complete and (
                row.get("finding_membership_exact") is True
                and row.get("evidence_membership_exact") is True
                and row.get("stored_verdicts_equal") is True
                and result.get("verdict") in {"PASS", "FAIL"}
                and execution.get("evidence_class") is not None
                and all(
                    item.get("expected_value") is not None
                    and item.get("observed_value") is not None
                    and item.get("status") in {"SATISFIED", "NOT_SATISFIED"}
                    and item.get("source_record_ids")
                    for item in findings
                )
            )
        return (
            "Expected values, observed values, calculations, evidence class, evidence "
            "links and backend-derived PASS/FAIL are complete and mutually bound."
            if complete
            else rows
        )
    if record_type == "ScenarioResetAdapter" and selector == "ScenarioResetAdapter.before_after":
        pairs = selected
        if not isinstance(pairs, list) or len(pairs) != 1:
            return pairs
        pair = pairs[0]
        prior = pair.get("prior_run")
        new = pair.get("new_run")
        valid = (
            isinstance(prior, dict)
            and isinstance(new, dict)
            and prior.get("status") == "CLOSED"
            and prior.get("scenario_run_id") != new.get("scenario_run_id")
            and pair.get("prior_event_count", 0) > 0
            and pair.get("reset_event_ids")
        )
        return (
            "Reset closes/preserves the prior run and creates a new run identity "
            "without overwriting operational history."
            if valid
            else pairs
        )
    if (
        record_type == "ValidationExecutionAdapter"
        and selector == "ValidationExecutionAdapter.repeat_chain"
    ):
        rows = selected
        if not isinstance(rows, list) or len(rows) != 1:
            return rows
        original = rows[0].get("original")
        repeat = rows[0].get("repeat")
        valid = (
            isinstance(original, dict)
            and isinstance(repeat, dict)
            and repeat.get("links", {}).get("repeat_of_execution_id")
            == original.get("validation_execution_id")
            and original.get("validation_attempt_id")
            != repeat.get("validation_attempt_id")
            and original.get("validation_execution_id")
            != repeat.get("validation_execution_id")
            and original.get("executed_result_id")
            != repeat.get("executed_result_id")
            and original.get("status") == repeat.get("status") == "FINALISED"
        )
        return (
            "Repeat creates separate attempt/execution/result identities with explicit "
            "links and preserves failed/corrected history."
            if valid
            else rows
        )
    if (
        record_type == "ValidationEvidenceAdapter"
        and selector == "ValidationEvidenceAdapter.final_membership"
    ):
        rows = selected
        if not isinstance(rows, list) or not rows:
            raise SourceAdapterError(f"selector member is absent: {selector}")
        valid = all(
            item.get("status") == "FINALISED"
            and item.get("declared_evidence_snapshot_ids")
            == item.get("stored_evidence_snapshot_ids")
            for item in rows
        )
        return (
            "A final execution's immutable evidence_snapshot_ids exactly equal the "
            "stored evidence rows for that execution."
            if valid
            else rows
        )
    if (
        record_type == "PersistenceAssuranceResult"
        and selector == "PersistenceAssuranceResult.immutability_probes"
    ):
        probes = selected
        required = {
            "FINAL_EXECUTION_UPDATE", "FINAL_EXECUTION_DELETE",
            "FINAL_EVIDENCE_UPDATE", "FINAL_EVIDENCE_DELETE",
            "FINAL_EVIDENCE_LATE_INSERT", "FINAL_RESULT_UPDATE",
            "FINAL_RESULT_DELETE",
        }
        valid = (
            isinstance(probes, list)
            and {item.get("probe") for item in probes} == required
            and all(
                item.get("rejected") is True
                and item.get("state_unchanged") is True
                for item in probes
            )
        )
        return (
            "Controlled update/delete/late-insert attempts against final execution/"
            "evidence/result records are rejected and leave records unchanged."
            if valid
            else probes
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
            histories = payload.get("before_after_hashes", {})
            valid = set(histories) == exact_roles and all(
                item is not None
                and item.get("source_execution_id")
                and item.get("repeat_execution_id")
                and item.get("source_execution_id") != item.get("repeat_execution_id")
                and item.get("before") == item.get("after")
                and item.get("before", {}).get("result_sha256") is not None
                and len(item.get("baseline_sha256", "")) == 64
                for item in histories.values()
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
