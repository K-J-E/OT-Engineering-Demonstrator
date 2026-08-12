"""Immutable I5 validation-definition, execution and evidence contracts."""

from __future__ import annotations

import hashlib
import json
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
    CriterionFindingStatus,
    CriterionKind,
    DeterminationCompletenessStatus,
    DeterminationContextKind,
    DeterminationContextStatus,
    DeterminationOperator,
    EngineeringReviewStatus,
    OperationalEventType,
    DeterminationSourceAdapterKind,
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


def _definition_sha256(model: FrozenModel, hash_field: str) -> str:
    payload = model.model_dump(mode="json", exclude={hash_field})
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ControlledFixtureDefinition(FrozenModel):
    fixture_id: str = Field(pattern=r"^FIX-[A-Z0-9-]+$")
    version: SemanticVersion
    fixture_sha256: Sha256Digest
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    method_id: str = Field(pattern=r"^DM-[A-Z0-9-]+$")
    network_configuration_id: ConfigurationId
    network_configuration_version: SemanticVersion
    controlled_inputs: tuple[str, ...] = Field(min_length=1)
    procedure_steps: tuple[str, ...] = Field(min_length=1)
    expected_result_statement: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if self.fixture_sha256 != _definition_sha256(self, "fixture_sha256"):
            raise ValueError("controlled fixture SHA-256 mismatch")
        return self


class ControlledSurfaceDefinition(FrozenModel):
    surface_id: str = Field(min_length=1)
    required_identity_profile: str = Field(min_length=1)


class ControlledDeterminationRegistries(FrozenModel):
    context_kinds: tuple[DeterminationContextKind, ...]
    operators: tuple[DeterminationOperator, ...]
    fixed_simulation_notice: str = Field(min_length=1)
    controlled_surface_set: tuple[ControlledSurfaceDefinition, ...]
    structural_record_set: dict[str, tuple[str, ...]]
    operational_event_type_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_exact_registries(self) -> Self:
        if (
            len(self.context_kinds) != len(DeterminationContextKind)
            or set(self.context_kinds) != set(DeterminationContextKind)
        ):
            raise ValueError("determination context-kind registry is not exact")
        if (
            len(self.operators) != len(DeterminationOperator)
            or set(self.operators) != set(DeterminationOperator)
        ):
            raise ValueError("determination operator registry is not exact")
        if len(self.controlled_surface_set) != 8 or len(
            {item.surface_id for item in self.controlled_surface_set}
        ) != 8:
            raise ValueError("NFR controlled-surface set must contain exactly eight views")
        records = [item for values in self.structural_record_set.values() for item in values]
        if len(records) != 45 or len(set(records)) != 45:
            raise ValueError("NFR structural record set must contain 45 unique records")
        if (
            len(self.operational_event_type_ids) != len(OperationalEventType)
            or set(self.operational_event_type_ids)
            != {item.value for item in OperationalEventType}
        ):
            raise ValueError("operational-event registry must contain exactly 15 IDs")
        return self


class CriterionDefinition(FrozenModel):
    criterion_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]+$")
    version: SemanticVersion
    criterion_sha256: Sha256Digest
    kind: CriterionKind
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    context_checkpoint: str = Field(min_length=1)
    expected_value: Any
    source_selector: str = Field(min_length=1)
    operator: DeterminationOperator
    normalisation: str = Field(min_length=1)
    required_evidence: str = Field(min_length=1)
    evidence_roles: tuple[str, ...] = Field(min_length=1)
    requirement_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        from .normalisation import SUPPORTED_NORMALISATION_PROFILES

        if self.criterion_sha256 != _definition_sha256(self, "criterion_sha256"):
            raise ValueError("criterion definition SHA-256 mismatch")
        if self.normalisation not in SUPPORTED_NORMALISATION_PROFILES:
            raise ValueError("criterion uses an unsupported normalisation profile")
        if len(set(self.requirement_ids)) != len(self.requirement_ids):
            raise ValueError("criterion requirement mapping contains duplicates")
        if self.kind is CriterionKind.ENGINEERING_REVIEW:
            if self.operator is not DeterminationOperator.REVIEW_FINDING_EQUAL:
                raise ValueError("review criterion must use REVIEW_FINDING_EQUAL")
        elif self.operator is DeterminationOperator.REVIEW_FINDING_EQUAL:
            raise ValueError("machine criterion cannot use REVIEW_FINDING_EQUAL")
        return self


class DeterminationMethodDefinition(FrozenModel):
    method_id: str = Field(pattern=r"^DM-[A-Z0-9-]+$")
    version: SemanticVersion
    method_sha256: Sha256Digest
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    evidence_class: EvidenceClass
    context_kind: DeterminationContextKind
    required_context_roles: tuple[str, ...] = Field(min_length=1)
    checkpoint_roles: tuple[str, ...] = Field(min_length=1)
    controlled_procedure: str | tuple[str, ...]
    aggregate_rule: str = Field(min_length=1)
    source_references: tuple[str, ...] = Field(min_length=1)
    criterion_ids: tuple[str, ...] = Field(min_length=1)
    criteria: tuple[CriterionDefinition, ...] = Field(min_length=1)
    controlled_fixture: ControlledFixtureDefinition | None = None

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if self.method_sha256 != _definition_sha256(self, "method_sha256"):
            raise ValueError("determination method SHA-256 mismatch")
        identifiers = tuple(item.criterion_id for item in self.criteria)
        if identifiers != self.criterion_ids or len(set(identifiers)) != len(identifiers):
            raise ValueError("method criterion identity list is not exact")
        if any(
            item.test_id != self.test_id or item.case_id != self.case_id
            for item in self.criteria
        ):
            raise ValueError("criterion parent identity does not match its method")
        fixture_context = (
            self.context_kind is DeterminationContextKind.CONTROLLED_FIXTURE_EXECUTION
        )
        if fixture_context != (self.controlled_fixture is not None):
            raise ValueError("fixture context requires exactly one controlled fixture definition")
        if self.controlled_fixture is not None and (
            self.controlled_fixture.test_id != self.test_id
            or self.controlled_fixture.method_id != self.method_id
        ):
            raise ValueError("controlled fixture parent identity mismatch")
        return self


class ConstituentCaseDefinition(FrozenModel):
    case_id: str = Field(pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    test_id: str = Field(pattern=r"^VT-EXP-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_title: str = Field(min_length=1)
    version: SemanticVersion
    selected_fault_section_id: EngineeringId
    initial_conditions: dict[str, Any]
    comparison_expected_values: dict[str, Any]
    checkpoint_obligations: tuple[CheckpointObligation, ...] = Field(min_length=1)
    determination_method: DeterminationMethodDefinition | None = None


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
    determination_method: DeterminationMethodDefinition | None = None

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
        if self.determination_method is not None and self.determination_method.test_id != self.test_id:
            raise ValueError("direct method parent identity mismatch")
        return self


class ValidationCatalogue(FrozenModel):
    catalogue_id: str = Field(pattern=r"^VALIDATION-CATALOGUE-V\d+\.\d+$")
    catalogue_version: SemanticVersion
    authority: str = Field(min_length=1)
    definition_count: int = Field(ge=1)
    definitions: tuple[ValidationTestDefinition, ...]
    controlled_registries: ControlledDeterminationRegistries | None = None

    @model_validator(mode="after")
    def validate_exact_catalogue(self) -> Self:
        if self.definition_count != 24 or len(self.definitions) != 24:
            raise ValueError("the accepted Step 9 catalogue must contain exactly 24 tests")
        identifiers = [item.test_id for item in self.definitions]
        if len(set(identifiers)) != 24:
            raise ValueError("catalogue test IDs must be unique")
        methods = [
            method
            for definition in self.definitions
            for method in (
                (definition.determination_method,)
                if definition.determination_method is not None
                else tuple(
                    case.determination_method
                    for case in definition.constituent_cases
                    if case.determination_method is not None
                )
            )
        ]
        if str(self.catalogue_version) != "1.2":
            if methods or self.controlled_registries is not None:
                raise ValueError("historical pre-DC-006 catalogue cannot contain methods")
            return self
        if self.controlled_registries is None:
            raise ValueError("DC-006 catalogue requires controlled registries")
        exact_composite_cases = {
            "VT-EXP-ALL-001": {
                "EXP-ALL-A1",
                "EXP-ALL-A2",
                "EXP-ALL-A3",
                "EXP-ALL-A4-FRESH",
                "EXP-ALL-B1",
                "EXP-ALL-B2",
                "EXP-ALL-B3",
                "EXP-ALL-B4",
                "EXP-ALL-A4-STALE-OPEN",
            },
            "VT-EXP-ROLE-001": {
                "EXP-ROLE-A2",
                "EXP-ROLE-B2",
                "EXP-ROLE-A1",
                "EXP-ROLE-A4",
            },
        }
        for definition in self.definitions:
            is_composite = definition.test_id in {"VT-EXP-ALL-001", "VT-EXP-ROLE-001"}
            if is_composite:
                if definition.determination_method is not None or any(
                    case.determination_method is None for case in definition.constituent_cases
                ):
                    raise ValueError("DC-004 parent owns case methods only")
                if {case.case_id for case in definition.constituent_cases} != exact_composite_cases[
                    definition.test_id
                ]:
                    raise ValueError("DC-004 required constituent-case set is not exact")
            elif definition.determination_method is None:
                raise ValueError("non-composite test requires one determination method")
        criteria = [criterion for method in methods for criterion in method.criteria]
        if len(methods) != 35 or len(criteria) != 214:
            raise ValueError("accepted DC-006 catalogue requires exactly 35 methods and 214 criteria")
        if len({item.criterion_id for item in criteria}) != 214:
            raise ValueError("DC-006 criterion IDs must be globally unique")
        if sum(method.controlled_fixture is not None for method in methods) != 8:
            raise ValueError("DC-006 catalogue requires exactly eight controlled fixtures")
        for definition in self.definitions:
            accepted = set(definition.requirement_ids)
            if definition.determination_method is not None:
                union = {
                    requirement_id
                    for criterion in definition.determination_method.criteria
                    for requirement_id in criterion.requirement_ids
                }
            else:
                union = set()
                for case in definition.constituent_cases:
                    assert case.determination_method is not None
                    case_union = {
                        requirement_id
                        for criterion in case.determination_method.criteria
                        for requirement_id in criterion.requirement_ids
                    }
                    if not case_union <= accepted:
                        raise ValueError("constituent criterion claims out-of-parent requirement")
                    union |= case_union
            if union != accepted:
                raise ValueError("criterion requirement union does not equal accepted RTM mapping")
        return self


class ValidationCatalogueManifest(FrozenModel):
    catalogue_id: str = Field(pattern=r"^VALIDATION-CATALOGUE-V\d+\.\d+$")
    catalogue_version: SemanticVersion
    definition_count: int = Field(ge=1)
    method_count: int = Field(default=0, ge=0)
    criterion_count: int = Field(default=0, ge=0)
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
    context_kind: DeterminationContextKind = DeterminationContextKind.SCENARIO_EXECUTION
    scenario_run_id: UUID | None = None
    scenario_mode: ScenarioMode | None = None
    evidence_class: EvidenceClass
    configuration_id: ConfigurationId
    configuration_version: SemanticVersion
    application_build_id: Sha256Digest
    status: ValidationExecutionStatus
    started_scenario_time: UtcMillisecondInstant | None = None
    started_at: UtcMillisecondInstant | None = None
    finalised_scenario_time: UtcMillisecondInstant | None = None
    finalised_at: UtcMillisecondInstant | None = None
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
        scenario = self.context_kind is DeterminationContextKind.SCENARIO_EXECUTION
        if scenario:
            if (
                self.scenario_run_id is None
                or self.scenario_mode is None
                or self.started_scenario_time is None
                or self.started_at is not None
            ):
                raise ValueError(
                    "scenario execution requires one run, mode and controlled scenario start time"
                )
        elif (
            self.scenario_run_id is not None
            or self.scenario_mode is not None
            or self.started_scenario_time is not None
            or self.started_at is None
        ):
            raise ValueError(
                "non-scenario execution requires an execution time and cannot fabricate scenario identity/time"
            )
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
                self.finalised_scenario_time if scenario else self.finalised_at,
                self.observed_result,
                self.calculations,
                self.verdict,
                self.verdict_reason,
            )
        ) and (bool(self.evidence_snapshot_ids) if scenario else True)
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
    result_schema_version: SemanticVersion = "1.0"
    executed_result_id: UUID
    validation_attempt_id: UUID
    validation_execution_id: UUID | None = None
    determination_context_id: UUID | None = None
    test_id: str | None = Field(default=None, pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    catalogue_version: SemanticVersion | None = None
    catalogue_sha256: Sha256Digest | None = None
    method_id: str | None = Field(default=None, pattern=r"^DM-[A-Z0-9-]+$")
    method_version: SemanticVersion | None = None
    method_sha256: Sha256Digest | None = None
    verdict: ValidationVerdict
    evidence_snapshot_ids: tuple[UUID, ...] = ()
    criterion_finding_ids: tuple[UUID, ...] = ()
    result_sha256: Sha256Digest
    finalised_at: UtcMillisecondInstant

    @model_validator(mode="after")
    def validate_pass_fail_only(self) -> Self:
        if self.verdict not in {ValidationVerdict.PASS, ValidationVerdict.FAIL}:
            raise ValueError("ExecutedValidationResult permits PASS or FAIL only")
        if str(self.result_schema_version) == "1.0":
            if self.validation_execution_id is None or not self.evidence_snapshot_ids:
                raise ValueError("legacy executed result requires execution and evidence")
        else:
            required = (
                self.validation_execution_id,
                self.determination_context_id,
                self.test_id,
                self.catalogue_version,
                self.catalogue_sha256,
                self.method_id,
                self.method_version,
                self.method_sha256,
            )
            if not all(item is not None for item in required) or not self.criterion_finding_ids:
                raise ValueError("DC-006 result requires complete method/context/finding provenance")
        if self.result_sha256 != self.recomputed_sha256():
            raise ValueError("ExecutedValidationResult controlled payload hash is invalid")
        return self

    def controlled_payload(self) -> dict[str, Any]:
        if str(self.result_schema_version) != "1.0":
            return {
                "result_schema_version": str(self.result_schema_version),
                "validation_attempt_id": str(self.validation_attempt_id),
                "validation_execution_id": (
                    str(self.validation_execution_id)
                    if self.validation_execution_id is not None
                    else None
                ),
                "determination_context_id": str(self.determination_context_id),
                "test_id": self.test_id,
                "case_id": self.case_id,
                "catalogue_version": str(self.catalogue_version),
                "catalogue_sha256": self.catalogue_sha256,
                "method_id": self.method_id,
                "method_version": str(self.method_version),
                "method_sha256": self.method_sha256,
                "verdict": self.verdict.value,
                "evidence_snapshot_ids": [str(item) for item in self.evidence_snapshot_ids],
                "criterion_finding_ids": [str(item) for item in self.criterion_finding_ids],
                "finalised_at": self.finalised_at.isoformat(),
            }
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


class AuthoritativeRecordSnapshot(FrozenModel):
    record_type: str = Field(pattern=r"^[A-Z][A-Za-z0-9]+(?:[A-Za-z0-9]|Result|Adapter|Snapshot|Record)$")
    record_id: str = Field(min_length=1)
    record_version: SemanticVersion
    owner_module: str = Field(min_length=1)
    application_build_id: Sha256Digest
    configuration_id: ConfigurationId | None = None
    configuration_version: SemanticVersion | None = None
    scenario_run_id: UUID | None = None
    validation_execution_id: UUID | None = None
    evidence_class: EvidenceClass
    canonical_payload: Any
    canonical_payload_sha256: Sha256Digest

    @model_validator(mode="after")
    def validate_authority_hash(self) -> Self:
        encoded = json.dumps(
            self.canonical_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        if self.canonical_payload_sha256 != hashlib.sha256(encoded).hexdigest():
            raise ValueError("authoritative source-record SHA-256 mismatch")
        return self


class DeterminationSourceRecord(FrozenModel):
    source_record_id: UUID
    source_type: DeterminationSourceAdapterKind
    owner_module: str = Field(min_length=1)
    source_role: str = Field(min_length=1)
    adapter_version: SemanticVersion = "1.0"
    validation_attempt_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    catalogue_version: SemanticVersion
    catalogue_sha256: Sha256Digest
    method_id: str = Field(pattern=r"^DM-[A-Z0-9-]+$")
    method_version: SemanticVersion
    method_sha256: Sha256Digest
    eligible_criterion_ids: tuple[str, ...]
    application_build_id: Sha256Digest
    configuration_id: ConfigurationId | None = None
    configuration_version: SemanticVersion | None = None
    scenario_run_id: UUID | None = None
    validation_execution_id: UUID | None = None
    evidence_class: EvidenceClass
    canonical_payload: dict[str, Any]
    canonical_payload_sha256: Sha256Digest
    created_at: UtcMillisecondInstant

    @model_validator(mode="after")
    def validate_payload_hash(self) -> Self:
        if "selector_values" in self.canonical_payload:
            raise ValueError("synthetic selector-value source authority is prohibited")
        encoded = json.dumps(
            self.canonical_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        if self.canonical_payload_sha256 != hashlib.sha256(encoded).hexdigest():
            raise ValueError("determination source-record SHA-256 mismatch")
        return self


class DeterminationContextMember(FrozenModel):
    role: str = Field(min_length=1)
    source_record_id: UUID
    source_record_sha256: Sha256Digest


class DeterminationContext(FrozenModel):
    context_schema_version: SemanticVersion = "1.0"
    determination_context_id: UUID
    validation_attempt_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    evidence_class: EvidenceClass
    catalogue_version: SemanticVersion
    catalogue_sha256: Sha256Digest
    method_id: str = Field(pattern=r"^DM-[A-Z0-9-]+$")
    method_version: SemanticVersion
    method_sha256: Sha256Digest
    context_kind: DeterminationContextKind
    status: DeterminationContextStatus
    application_build_id: Sha256Digest
    configuration_id: ConfigurationId | None = None
    configuration_version: SemanticVersion | None = None
    scenario_run_id: UUID | None = None
    validation_execution_id: UUID | None = None
    members: tuple[DeterminationContextMember, ...]
    created_at: UtcMillisecondInstant
    frozen_at: UtcMillisecondInstant | None = None

    @model_validator(mode="after")
    def validate_context_shape(self) -> Self:
        scenario = self.context_kind is DeterminationContextKind.SCENARIO_EXECUTION
        if self.validation_execution_id is None:
            raise ValueError("every executed determination context requires one ValidationExecution")
        if scenario != (self.scenario_run_id is not None):
            raise ValueError(
                "scenario context requires one run; non-scenario context must not fabricate one"
            )
        if self.status is DeterminationContextStatus.FROZEN:
            if self.frozen_at is None or not self.members:
                raise ValueError("frozen context requires time and exact membership")
        elif self.frozen_at is not None:
            raise ValueError("draft context cannot have frozen time")
        roles = [item.role for item in self.members]
        if len(roles) != len(set(roles)):
            raise ValueError("determination context role membership must be unique")
        return self


class CriterionFinding(FrozenModel):
    finding_schema_version: SemanticVersion = "1.0"
    criterion_finding_id: UUID
    determination_context_id: UUID
    criterion_id: str
    criterion_version: SemanticVersion
    criterion_sha256: Sha256Digest
    expected_value: Any
    observed_value: Any | None = None
    status: CriterionFindingStatus
    source_record_ids: tuple[UUID, ...]
    evidence_references: tuple[str, ...]
    reason: str = Field(min_length=1)
    finding_sha256: Sha256Digest
    finalised_at: UtcMillisecondInstant | None = None

    @model_validator(mode="after")
    def validate_finding_hash(self) -> Self:
        final = self.status is not CriterionFindingStatus.NOT_EVALUATED
        if final != (self.finalised_at is not None):
            raise ValueError("only evaluated findings carry finalisation time")
        if self.finding_sha256 != _definition_sha256(self, "finding_sha256"):
            raise ValueError("criterion finding SHA-256 mismatch")
        return self


class EngineeringReviewProposal(FrozenModel):
    review_proposal_id: UUID
    determination_context_id: UUID
    criterion_id: str
    proposed_finding: CriterionFindingStatus
    proposer_actor_id: str = Field(min_length=1)
    proposer_role: str = Field(min_length=1)
    evidence_references: tuple[str, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)
    proposal_sha256: Sha256Digest
    proposed_at: UtcMillisecondInstant

    @model_validator(mode="after")
    def validate_proposal(self) -> Self:
        if self.proposed_finding is CriterionFindingStatus.NOT_EVALUATED:
            raise ValueError("review proposal must choose a criterion finding")
        if self.proposal_sha256 != _definition_sha256(self, "proposal_sha256"):
            raise ValueError("engineering-review proposal SHA-256 mismatch")
        return self


class EngineeringReviewFinalisation(FrozenModel):
    review_finalisation_id: UUID
    review_proposal_id: UUID
    determination_context_id: UUID
    criterion_id: str
    status: EngineeringReviewStatus = EngineeringReviewStatus.FINALISED
    final_finding: CriterionFindingStatus
    reviewer_actor_id: str = Field(min_length=1)
    reviewer_role: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    finalisation_sha256: Sha256Digest
    finalised_at: UtcMillisecondInstant

    @model_validator(mode="after")
    def validate_finalisation(self) -> Self:
        if self.final_finding is CriterionFindingStatus.NOT_EVALUATED:
            raise ValueError("review finalisation must choose a criterion finding")
        if self.finalisation_sha256 != _definition_sha256(
            self, "finalisation_sha256"
        ):
            raise ValueError("engineering-review finalisation SHA-256 mismatch")
        return self


class DeterminationCompleteness(FrozenModel):
    status: DeterminationCompletenessStatus
    required_criterion_ids: tuple[str, ...]
    evaluated_criterion_ids: tuple[str, ...]
    missing_criterion_ids: tuple[str, ...]
    duplicate_criterion_ids: tuple[str, ...]
    reasons: tuple[str, ...]


class DeterminationReviewProjection(FrozenModel):
    context: DeterminationContext
    completeness: DeterminationCompleteness
    findings: tuple[CriterionFinding, ...]


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
