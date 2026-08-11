"""Resolve one immutable DC-005 suspension to its complete preserved source set."""

from __future__ import annotations

from dataclasses import dataclass

from ...application.scenario_coordinator import ScenarioCoordinator
from ...domain.enums import (
    SuspensionLifecyclePosition,
    SuspensionRecordStatus,
    ValidationAttemptStatus,
)
from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ...infrastructure.validation_repository import ValidationRepository
from ..scenario.models import RunContext
from .models import (
    EvidenceSnapshot,
    ValidationAttempt,
    ValidationExecution,
    ValidationSuspensionRecord,
    ValidationTargetSelection,
)


class SuspensionProvenanceError(ValueError):
    """Raised when a finalised suspension no longer resolves bidirectionally."""


@dataclass(frozen=True)
class ResolvedSuspensionSource:
    suspension: ValidationSuspensionRecord
    target: ValidationTargetSelection
    attempt: ValidationAttempt
    execution: ValidationExecution | None
    run: RunContext | None
    evidence_snapshots: tuple[EvidenceSnapshot, ...]


def resolve_suspension_source(
    repository: ValidationRepository,
    scenarios: ScenarioCoordinator,
    suspension: ValidationSuspensionRecord,
) -> ResolvedSuspensionSource:
    target = repository.get_target(suspension.target_selection_id)
    attempt = repository.get_attempt(suspension.validation_attempt_id)
    if (
        suspension.status is not SuspensionRecordStatus.FINALISED
        or attempt.status is not ValidationAttemptStatus.SUSPENDED
        or attempt.target_selection_id != target.target_selection_id
        or suspension.target_selection_id != target.target_selection_id
        or suspension.target_selection_sha256 != target.canonical_selection_sha256
        or suspension.intended_test_id != target.test_id
        or suspension.intended_case_id != target.case_id
        or repository.has_executed_result_for_attempt(attempt.validation_attempt_id)
        or any(
            item.condition_id is not suspension.condition_id
            or item.payload_sha256 != sha256_bytes(canonical_json_bytes(item.payload))
            for item in suspension.evidence
        )
    ):
        raise SuspensionProvenanceError(
            "suspension target/attempt/evidence provenance is inconsistent"
        )

    if suspension.lifecycle_position is SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY:
        if any((attempt.scenario_run_id, attempt.validation_execution_id,
                suspension.scenario_run_id, suspension.validation_execution_id)):
            raise SuspensionProvenanceError(
                "pre-entry suspension must not resolve a run or execution"
            )
        return ResolvedSuspensionSource(
            suspension, target, attempt, None, None, ()
        )

    if (
        suspension.scenario_run_id is None
        or suspension.validation_execution_id is None
        or attempt.scenario_run_id != suspension.scenario_run_id
        or attempt.validation_execution_id != suspension.validation_execution_id
    ):
        raise SuspensionProvenanceError(
            "post-entry suspension does not bind the attempt's actual run/execution"
        )
    execution = repository.get_execution(suspension.validation_execution_id)
    run = scenarios.run_context(suspension.scenario_run_id)
    evidence = repository.list_evidence(execution.validation_execution_id)
    if (
        execution.validation_attempt_id != attempt.validation_attempt_id
        or execution.target_selection_id != target.target_selection_id
        or execution.validation_execution_id != attempt.validation_execution_id
        or execution.scenario_run_id != attempt.scenario_run_id
        or execution.test_id != target.test_id
        or execution.case_id != target.case_id
        or execution.evidence_class is not target.evidence_class
        or (target.catalogue_version is not None and execution.catalogue_version != target.catalogue_version)
        or (target.catalogue_sha256 is not None and execution.catalogue_sha256 != target.catalogue_sha256)
        or (target.test_definition_version is not None and execution.test_definition_version != target.test_definition_version)
        or (target.test_definition_sha256 is not None and execution.test_definition_sha256 != target.test_definition_sha256)
        or (target.case_definition_version is not None and execution.case_definition_version != target.case_definition_version)
        or (target.case_definition_sha256 is not None and execution.case_definition_sha256 != target.case_definition_sha256)
        or (target.configuration_id is not None and execution.configuration_id != target.configuration_id)
        or (target.configuration_version is not None and execution.configuration_version != target.configuration_version)
        or (target.target_application_build_id is not None and execution.application_build_id != target.target_application_build_id)
        or run.scenario_run_id != execution.scenario_run_id
        or run.mode is not execution.scenario_mode
        or run.evidence_class is not execution.evidence_class
        or run.configuration_id != execution.configuration_id
        or run.configuration_version != execution.configuration_version
        or run.application_build_id != execution.application_build_id
    ):
        raise SuspensionProvenanceError(
            "post-entry attempt/execution/run provenance is inconsistent"
        )
    for snapshot in evidence:
        if (
            snapshot.validation_execution_id != execution.validation_execution_id
            or snapshot.scenario_run_id != run.scenario_run_id
            or snapshot.test_id != execution.test_id
            or snapshot.case_id != execution.case_id
            or snapshot.catalogue_version != execution.catalogue_version
            or snapshot.catalogue_sha256 != execution.catalogue_sha256
            or snapshot.test_definition_version != execution.test_definition_version
            or snapshot.test_definition_sha256 != execution.test_definition_sha256
            or snapshot.case_definition_version != execution.case_definition_version
            or snapshot.case_definition_sha256 != execution.case_definition_sha256
            or snapshot.scenario_mode is not execution.scenario_mode
            or snapshot.evidence_class is not execution.evidence_class
            or snapshot.configuration_id != execution.configuration_id
            or snapshot.configuration_version != execution.configuration_version
            or snapshot.application_build_id != execution.application_build_id
        ):
            raise SuspensionProvenanceError(
                "post-entry suspension evidence provenance is inconsistent"
            )
    if (
        suspension.lifecycle_position is SuspensionLifecyclePosition.EVIDENCE_FINALISATION
        and not evidence
    ):
        raise SuspensionProvenanceError(
            "evidence-finalisation suspension requires preserved execution evidence"
        )
    return ResolvedSuspensionSource(
        suspension, target, attempt, execution, run, evidence
    )
