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
from uuid import UUID

from ...domain.enums import DeterminationSourceAdapterKind
from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes
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
            }
        ),
    ),
    DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT: SourceAdapterDefinition(
        "deterministic-repeat-authority",
        frozenset({"DeterministicRepeatAdapter"}),
    ),
    DeterminationSourceAdapterKind.EVIDENCE_PACKAGE: SourceAdapterDefinition(
        "evidence-package-authority",
        frozenset({"EvidencePackageAdapter", "HistoricalCatalogueResolver"}),
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
                if close < 0 or not isinstance(value, dict):
                    raise SourceAdapterError(f"invalid field-set selector: {selector}")
                if "__controlled_projection__" in value:
                    value = value["__controlled_projection__"]
                    suffix = suffix[close + 1:]
                    continue
                fields = [item.strip() for item in suffix[1:close].split(",")]
                projections = value.get("__field_set_projections__", {})
                projection_key = ",".join(fields)
                if projection_key in projections:
                    value = projections[projection_key]
                    suffix = suffix[close + 1:]
                    continue
                value = {field: value[field] for field in fields}
                suffix = suffix[close + 1:]
            elif suffix.startswith("["):
                close = suffix.find("]")
                if close < 0:
                    raise SourceAdapterError(f"invalid indexed selector: {selector}")
                key = suffix[1:close]
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
        if isinstance(value, dict) and "__controlled_projection__" in value:
            return value["__controlled_projection__"]
        return value


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


def freeze_authoritative_record(
    *,
    record_type: str,
    record_id: str,
    owner_module: str,
    payload: Any,
    application_build_id: str,
    evidence_class,
    configuration_id: str | None = None,
    configuration_version: str | None = None,
    scenario_run_id: UUID | None = None,
    validation_execution_id: UUID | None = None,
) -> AuthoritativeRecordSnapshot:
    """Hash one already-produced controlling-module record for adapter capture."""

    return AuthoritativeRecordSnapshot(
        record_type=record_type,
        record_id=record_id,
        record_version="1.0",
        owner_module=owner_module,
        application_build_id=application_build_id,
        configuration_id=configuration_id,
        configuration_version=configuration_version,
        scenario_run_id=scenario_run_id,
        validation_execution_id=validation_execution_id,
        evidence_class=evidence_class,
        canonical_payload=payload,
        canonical_payload_sha256=sha256_bytes(canonical_json_bytes(payload)),
    )
