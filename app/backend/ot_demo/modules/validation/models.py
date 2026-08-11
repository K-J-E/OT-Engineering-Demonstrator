"""Immutable I5 validation-definition, execution and evidence contracts."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator
from typing_extensions import Self

from ...domain.base import FrozenModel
from ...domain.enums import (
    CompositeConstituentSourceKind,
    CompositeCompletenessStatus,
    CompositeResultStatus,
    EvidenceClass,
    ScenarioMode,
    ValidationDefinitionStatus,
    ValidationExecutionStatus,
    ValidationAttemptStatus,
    ValidationSuspensionCondition,
    SuspensionAuthorityKind,
    SuspensionLifecyclePosition,
    SuspensionRecordStatus,
    RequiredInputRole,
    ClassifierGateOutcomeStatus,
    ValidationVerdict,
)
from ...domain.value_objects import (
    ConfigurationId,
    EngineeringId,
    SemanticVersion,
    Sha256Digest,
    UtcMillisecondInstant,
)


class CheckpointObligation(FrozenModel):
    checkpoint_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    required_content: tuple[str, ...] = Field(min_length=1)


class ConstituentCaseDefinition(FrozenModel):
    case_id: str = Field(pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    test_id: str = Field(pattern=r"^VT-EXP-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_title: str = Field(min_length=1)
    version: SemanticVersion
    selected_fault_section_id: EngineeringId
    initial_conditions: dict[str, Any]
    comparison_expected_values: dict[str, Any]
    checkpoint_obligations: tuple[CheckpointObligation, ...] = Field(min_length=1)


class ValidationTestDefinition(FrozenModel):
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    title: str = Field(min_length=1)
    version: SemanticVersion
    status: ValidationDefinitionStatus
    evidence_class: EvidenceClass
    requirement_ids: tuple[str, ...] = Field(min_length=1)
    source_references: tuple[str, ...] = Field(min_length=1)
    objective: str = Field(min_length=1)
    method: str = Field(min_length=1)
    preconditions: tuple[str, ...] = Field(min_length=1)
    controlled_inputs: tuple[str, ...] = Field(min_length=1)
    procedure_steps: tuple[str, ...] = Field(min_length=1)
    checkpoint_obligations: tuple[CheckpointObligation, ...] = Field(min_length=1)
    expected_result_statement: str = Field(min_length=1)
    comparison_expected_values: dict[str, Any] | None
    evidence_requirements: tuple[str, ...] = Field(min_length=1)
    verdict_rule: str = Field(min_length=1)
    reset_repeat_rule: str = Field(min_length=1)
    constituent_cases: tuple[ConstituentCaseDefinition, ...] = ()

    @model_validator(mode="after")
    def validate_controlled_identity(self) -> Self:
        if len(set(self.requirement_ids)) != len(self.requirement_ids):
            raise ValueError("requirement_ids must not contain duplicates")
        checkpoints = [item.checkpoint_id for item in self.checkpoint_obligations]
        if len(set(checkpoints)) != len(checkpoints):
            raise ValueError("checkpoint obligations must have unique IDs")
        expected_class = (
            EvidenceClass.EXPLORATORY
            if self.test_id.startswith("VT-EXP-")
            else EvidenceClass.FORMAL
        )
        if self.evidence_class is not expected_class:
            raise ValueError("catalogue evidence class contradicts the accepted test family")
        case_ids = [item.case_id for item in self.constituent_cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("constituent case IDs must be unique within a test")
        if any(item.test_id != self.test_id for item in self.constituent_cases):
            raise ValueError("constituent case parent test identity is inconsistent")
        return self


class ValidationCatalogue(FrozenModel):
    catalogue_id: str = Field(pattern=r"^VALIDATION-CATALOGUE-V\d+\.\d+$")
    catalogue_version: SemanticVersion
    authority: str = Field(min_length=1)
    definition_count: int = Field(ge=1)
    definitions: tuple[ValidationTestDefinition, ...]

    @model_validator(mode="after")
    def validate_exact_catalogue(self) -> Self:
        if self.definition_count != 24 or len(self.definitions) != 24:
            raise ValueError("the accepted Step 9 catalogue must contain exactly 24 tests")
        identifiers = [item.test_id for item in self.definitions]
        if len(set(identifiers)) != 24:
            raise ValueError("catalogue test IDs must be unique")
        return self


class ValidationCatalogueManifest(FrozenModel):
    catalogue_id: str = Field(pattern=r"^VALIDATION-CATALOGUE-V\d+\.\d+$")
    catalogue_version: SemanticVersion
    definition_count: int = Field(ge=1)
    catalogue_file: str = Field(pattern=r"^catalogue\.json$")
    catalogue_sha256: Sha256Digest


class LoadedValidationDefinition(FrozenModel):
    definition: ValidationTestDefinition
    definition_sha256: Sha256Digest
    catalogue_id: str = Field(
        default="VALIDATION-CATALOGUE-V1.0",
        pattern=r"^VALIDATION-CATALOGUE-V\d+\.\d+$",
    )
    catalogue_version: SemanticVersion = "1.0"
    catalogue_sha256: Sha256Digest


class LoadedConstituentCase(FrozenModel):
    definition: ConstituentCaseDefinition
    definition_sha256: Sha256Digest


class ValidationExecutionLinks(FrozenModel):
    repeat_of_execution_id: UUID | None = None
    defect_id: EngineeringId | None = None
    correction_id: EngineeringId | None = None


class ValidationExecution(FrozenModel):
    validation_execution_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    test_definition_version: SemanticVersion
    test_definition_sha256: Sha256Digest
    catalogue_version: SemanticVersion = "1.0"
    catalogue_sha256: Sha256Digest
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    case_definition_version: SemanticVersion | None = None
    case_definition_sha256: Sha256Digest | None = None
    scenario_run_id: UUID
    scenario_mode: ScenarioMode
    evidence_class: EvidenceClass
    configuration_id: ConfigurationId
    configuration_version: SemanticVersion
    application_build_id: Sha256Digest
    status: ValidationExecutionStatus
    started_scenario_time: UtcMillisecondInstant
    finalised_scenario_time: UtcMillisecondInstant | None = None
    expected_result_statement: str = Field(min_length=1)
    expected_comparison_values: dict[str, Any] | None = None
    observed_result: dict[str, Any] | None = None
    calculations: dict[str, Any] | None = None
    evidence_snapshot_ids: tuple[UUID, ...] = ()
    verdict: ValidationVerdict | None = None
    verdict_reason: str | None = None
    links: ValidationExecutionLinks = ValidationExecutionLinks()
    validation_attempt_id: UUID | None = None
    target_selection_id: UUID | None = None
    executed_result_id: UUID | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        case_fields = (
            self.case_id,
            self.case_definition_version,
            self.case_definition_sha256,
        )
        if any(value is not None for value in case_fields) and not all(
            value is not None for value in case_fields
        ):
            raise ValueError("case-bound execution identity must be complete")
        finalised = self.status is ValidationExecutionStatus.FINALISED
        final_fields_present = all(
            value is not None
            for value in (
                self.finalised_scenario_time,
                self.observed_result,
                self.calculations,
                self.verdict,
                self.verdict_reason,
            )
        ) and bool(self.evidence_snapshot_ids)
        if finalised != final_fields_present:
            raise ValueError(
                "finalised executions require observed result, calculations, evidence, verdict and time"
            )
        if finalised and self.verdict not in {
            ValidationVerdict.PASS,
            ValidationVerdict.FAIL,
        }:
            raise ValueError("executed validation results are PASS/FAIL only")
        return self


class ValidationTargetSelection(FrozenModel):
    selection_schema_version: SemanticVersion = "1.0"
    target_selection_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    test_definition_version: SemanticVersion | None
    test_definition_sha256: Sha256Digest | None
    catalogue_version: SemanticVersion | None
    catalogue_sha256: Sha256Digest | None
    case_definition_version: SemanticVersion | None = None
    case_definition_sha256: Sha256Digest | None = None
    evidence_class: EvidenceClass
    configuration_id: ConfigurationId | None
    configuration_version: SemanticVersion | None
    target_application_build_id: Sha256Digest | None
    unresolved_required_role: RequiredInputRole | None = None
    intended_identity_evidence: dict[str, dict[str, Any]] = Field(default_factory=dict)
    requested_identity_evidence: dict[str, dict[str, Any]] = Field(default_factory=dict)
    resolved_identity_evidence: dict[str, dict[str, Any]] = Field(default_factory=dict)
    assurance_verifier_application_build_id: Sha256Digest | None = None
    canonical_selection_payload: dict[str, Any]
    canonical_selection_sha256: Sha256Digest
    selected_by_actor_id: str = Field(min_length=1)
    selected_by_role: str = Field(min_length=1)
    created_at: UtcMillisecondInstant

    @model_validator(mode="after")
    def validate_exact_unresolved_role(self) -> Self:
        if not self.intended_identity_evidence:
            if self.unresolved_required_role is not None:
                raise ValueError("legacy target cannot declare unresolved identity without evidence")
            return self
        role_fields = {
            RequiredInputRole.APPLICATION_BUILD: (self.target_application_build_id,),
            RequiredInputRole.CONFIGURATION: (self.configuration_id, self.configuration_version),
            RequiredInputRole.CATALOGUE: (self.catalogue_version, self.catalogue_sha256),
            RequiredInputRole.TEST_DEFINITION: (self.test_definition_version, self.test_definition_sha256),
            RequiredInputRole.CASE_DEFINITION: (self.case_definition_version, self.case_definition_sha256),
        }
        for role, values in role_fields.items():
            applicable = role is not RequiredInputRole.CASE_DEFINITION or self.case_id is not None
            if not applicable:
                continue
            resolved = all(item is not None for item in values)
            if role is self.unresolved_required_role:
                if resolved:
                    raise ValueError("the explicitly unresolved required role must not carry resolved identity")
            elif not resolved:
                raise ValueError("only the explicitly unresolved required role may omit provenance")
        if self.unresolved_required_role is RequiredInputRole.CONTROLLED_FIXTURE:
            if RequiredInputRole.CONTROLLED_FIXTURE.value in self.resolved_identity_evidence:
                raise ValueError("unresolved fixture must not appear resolved")
        if self.unresolved_required_role is not None and self.unresolved_required_role.value not in self.requested_identity_evidence:
            raise ValueError("unresolved required role must retain presented identity evidence")
        return self


class ValidationAttempt(FrozenModel):
    validation_attempt_id: UUID
    target_selection_id: UUID
    status: ValidationAttemptStatus
    scenario_run_id: UUID | None = None
    validation_execution_id: UUID | None = None
    created_at: UtcMillisecondInstant
    updated_at: UtcMillisecondInstant


class ExecutedValidationResult(FrozenModel):
    executed_result_id: UUID
    validation_attempt_id: UUID
    validation_execution_id: UUID
    verdict: ValidationVerdict
    evidence_snapshot_ids: tuple[UUID, ...] = Field(min_length=1)
    result_sha256: Sha256Digest
    finalised_at: UtcMillisecondInstant

    @model_validator(mode="after")
    def validate_pass_fail_only(self) -> Self:
        if self.verdict not in {ValidationVerdict.PASS, ValidationVerdict.FAIL}:
            raise ValueError("ExecutedValidationResult permits PASS or FAIL only")
        if self.result_sha256 != self.recomputed_sha256():
            raise ValueError("ExecutedValidationResult controlled payload hash is invalid")
        return self

    def controlled_payload(self) -> dict[str, Any]:
        return {
            "validation_attempt_id": str(self.validation_attempt_id),
            "validation_execution_id": str(self.validation_execution_id),
            "verdict": self.verdict.value,
            "evidence_snapshot_ids": [str(item) for item in self.evidence_snapshot_ids],
            "finalised_at": self.finalised_at.isoformat(),
        }

    def recomputed_sha256(self) -> str:
        from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes
        return sha256_bytes(canonical_json_bytes(self.controlled_payload()))


class ValidationSuspensionEvidence(FrozenModel):
    evidence_id: UUID
    condition_id: ValidationSuspensionCondition
    evidence_type: str = Field(min_length=1)
    failure_code: str = Field(pattern=r"^[A-Z0-9_]+$")
    payload: dict[str, Any]
    payload_sha256: Sha256Digest


class ValidationSuspensionAuthority(FrozenModel):
    authority_kind: SuspensionAuthorityKind
    proposer_actor_id: str = Field(min_length=1)
    proposer_role: str = Field(min_length=1)
    reviewer_actor_id: str = Field(min_length=1)
    reviewer_role: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_separation(self) -> Self:
        if self.proposer_actor_id == self.reviewer_actor_id:
            raise ValueError("suspension proposer and reviewer must be distinct actors")
        return self


class ClassifierGateOutcome(FrozenModel):
    gate_id: Literal[
        "TRUSTED_TARGET",
        "INTEGRITY",
        "INPUT_IDENTITY",
        "BASELINE_CONFLICT",
        "UNSPECIFIED_BEHAVIOUR",
        "CONTROLLED_TIME",
    ]
    status: ClassifierGateOutcomeStatus
    selected_condition_id: ValidationSuspensionCondition | None = None
    failure_code: str | None = Field(default=None, pattern=r"^[A-Z0-9_]+$")
    outcome_payload_sha256: Sha256Digest | None = None

    @model_validator(mode="after")
    def validate_failure_shape(self) -> Self:
        failed = self.status is ClassifierGateOutcomeStatus.FAIL
        if failed != (
            self.selected_condition_id is not None
            and self.failure_code is not None
            and self.outcome_payload_sha256 is not None
        ):
            raise ValueError("only a failed classifier gate carries selected failure provenance")
        return self


class ValidationSuspensionRecord(FrozenModel):
    record_schema_version: SemanticVersion = "1.0"
    classifier_version: SemanticVersion = "1.0"
    suspension_record_id: UUID
    validation_attempt_id: UUID
    target_selection_id: UUID
    condition_id: ValidationSuspensionCondition
    lifecycle_position: SuspensionLifecyclePosition
    status: SuspensionRecordStatus
    reason_code: str = Field(pattern=r"^BLOCKED-TEST/VSC-00[1-5]/[A-Z_]+$")
    deterministic_fingerprint: Sha256Digest
    verifier_application_build_id: Sha256Digest
    evaluated_classifier_gates: tuple[ClassifierGateOutcome | str, ...] = Field(
        min_length=6, max_length=6
    )
    target_selection_sha256: Sha256Digest
    intended_test_id: str
    intended_case_id: str | None = None
    resolved_source_identities: dict[str, Any]
    failed_required_input_role: str | None = None
    presented_identity_evidence: dict[str, Any]
    inherited_evidence_class: EvidenceClass
    evidence_contract_version: SemanticVersion = "1.0"
    reason_parameters: dict[str, Any]
    rendered_reason: str = Field(min_length=1)
    evidence: tuple[ValidationSuspensionEvidence, ...] = Field(min_length=1)
    authority: ValidationSuspensionAuthority
    scenario_run_id: UUID | None = None
    validation_execution_id: UUID | None = None
    created_at: UtcMillisecondInstant
    finalised_at: UtcMillisecondInstant | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        if str(self.classifier_version) != "1.0" and any(
            isinstance(item, str) for item in self.evaluated_classifier_gates
        ):
            raise ValueError(
                "current classifier records require actual structured gate outcomes"
            )
        if (self.status is SuspensionRecordStatus.FINALISED) != (
            self.finalised_at is not None
        ):
            raise ValueError("finalised suspension requires finalised_at")
        if self.lifecycle_position is SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY:
            if self.scenario_run_id is not None or self.validation_execution_id is not None:
                raise ValueError("pre-entry suspension must not fabricate run/execution identity")
        elif self.scenario_run_id is None or self.validation_execution_id is None:
            raise ValueError("in-progress/finalisation suspension requires actual run and execution")
        return self


class EvidenceSnapshot(FrozenModel):
    evidence_snapshot_id: UUID
    validation_execution_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    catalogue_version: SemanticVersion = "1.0"
    catalogue_sha256: Sha256Digest | None = None
    test_definition_version: SemanticVersion | None = None
    test_definition_sha256: Sha256Digest | None = None
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    case_definition_version: SemanticVersion | None = None
    case_definition_sha256: Sha256Digest | None = None
    scenario_run_id: UUID
    scenario_mode: ScenarioMode
    evidence_class: EvidenceClass
    configuration_id: ConfigurationId
    configuration_version: SemanticVersion
    application_build_id: Sha256Digest
    state_revision: int = Field(ge=0)
    checkpoint_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    scenario_time: UtcMillisecondInstant
    captured_scenario_time: UtcMillisecondInstant
    content_categories: tuple[str, ...] = Field(min_length=1)
    source_record_references: tuple[str, ...]
    observed_values: dict[str, Any]
    canonical_payload: dict[str, Any]
    canonical_payload_sha256: Sha256Digest


class ValidationExecutionSummary(FrozenModel):
    execution: ValidationExecution
    evidence_snapshots: tuple[EvidenceSnapshot, ...]


class StartValidationExecutionRequest(FrozenModel):
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    scenario_run_id: UUID
    links: ValidationExecutionLinks = ValidationExecutionLinks()


class CaptureValidationCheckpointRequest(FrozenModel):
    checkpoint_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")


class FinaliseValidationExecutionRequest(FrozenModel):
    checkpoint_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")


class CompositeConstituentLink(FrozenModel):
    link_schema_version: SemanticVersion = "1.0"
    case_id: str = Field(pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    source_kind: CompositeConstituentSourceKind = (
        CompositeConstituentSourceKind.EXECUTION_RESULT
    )
    validation_execution_id: UUID | None = None
    executed_result_id: UUID | None = None
    suspension_record_id: UUID | None = None
    scenario_run_id: UUID | None = None
    case_definition_sha256: Sha256Digest | None
    unavailable_required_input_role: RequiredInputRole | None = None
    constituent_verdict: ValidationVerdict | None = None
    evidence_snapshot_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def validate_source_union(self) -> Self:
        executed = self.source_kind is CompositeConstituentSourceKind.EXECUTION_RESULT
        if executed != (self.validation_execution_id is not None):
            raise ValueError("execution source requires exactly one execution ID")
        if executed == (self.suspension_record_id is not None):
            raise ValueError("constituent source must be execution XOR suspension")
        if str(self.link_schema_version) == "1.1" and executed != (self.executed_result_id is not None):
            raise ValueError("execution source requires its immutable executed result ID")
        if executed and self.unavailable_required_input_role is not None:
            raise ValueError("executed result cannot declare unavailable target provenance")
        if not executed and self.executed_result_id is not None:
            raise ValueError("suspension source cannot carry executed result identity")
        if executed and self.constituent_verdict not in {
            None,
            ValidationVerdict.PASS,
            ValidationVerdict.FAIL,
        }:
            raise ValueError("execution constituent must be incomplete or PASS/FAIL")
        if not executed and self.constituent_verdict is not ValidationVerdict.BLOCKED_TEST:
            raise ValueError("suspension constituent result must be BLOCKED-TEST")
        return self


class CompositeCompleteness(FrozenModel):
    status: CompositeCompletenessStatus
    required_case_ids: tuple[str, ...]
    present_case_ids: tuple[str, ...]
    missing_case_ids: tuple[str, ...]
    duplicate_case_ids: tuple[str, ...]
    mismatched_case_ids: tuple[str, ...]
    reasons: tuple[str, ...]


class CompositeValidationResult(FrozenModel):
    composite_result_id: UUID
    test_id: str = Field(pattern=r"^VT-EXP-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    test_definition_version: SemanticVersion
    test_definition_sha256: Sha256Digest
    catalogue_version: SemanticVersion
    catalogue_sha256: Sha256Digest
    evidence_class: EvidenceClass = EvidenceClass.EXPLORATORY
    application_build_id: Sha256Digest
    configuration_id: ConfigurationId
    configuration_version: SemanticVersion
    required_case_ids: tuple[str, ...] = Field(min_length=1)
    constituent_links: tuple[CompositeConstituentLink, ...]
    completeness: CompositeCompleteness
    status: CompositeResultStatus
    determination: ValidationVerdict | None = None
    determination_reason: str = Field(min_length=1)
    source_record_references: tuple[str, ...]
    created_at: UtcMillisecondInstant
    finalised_at: UtcMillisecondInstant | None = None

    @model_validator(mode="after")
    def validate_composite_lifecycle(self) -> Self:
        finalised = self.status is CompositeResultStatus.FINALISED
        complete = self.completeness.status is CompositeCompletenessStatus.COMPLETE
        if finalised and not complete:
            raise ValueError("only a complete composite may be finalised")
        if finalised != (self.determination is not None and self.finalised_at is not None):
            raise ValueError("finalised composite requires determination and audit time")
        if self.determination not in {
            None,
            ValidationVerdict.PASS,
            ValidationVerdict.FAIL,
            ValidationVerdict.BLOCKED_TEST,
        }:
            raise ValueError("composite determination is outside the accepted rule")
        return self


class AssembleCompositeRequest(FrozenModel):
    test_id: str = Field(pattern=r"^VT-EXP-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    validation_execution_ids: tuple[UUID, ...] = ()
    validation_suspension_record_ids: tuple[UUID, ...] = ()
    created_at: UtcMillisecondInstant


class FinaliseCompositeRequest(FrozenModel):
    finalised_at: UtcMillisecondInstant
