"""Immutable I5 validation-definition, execution and evidence contracts."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field, model_validator
from typing_extensions import Self

from ...domain.base import FrozenModel
from ...domain.enums import (
    EvidenceClass,
    ScenarioMode,
    ValidationDefinitionStatus,
    ValidationExecutionStatus,
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
    catalogue_sha256: Sha256Digest


class ValidationExecutionLinks(FrozenModel):
    repeat_of_execution_id: UUID | None = None
    defect_id: EngineeringId | None = None
    correction_id: EngineeringId | None = None


class ValidationExecution(FrozenModel):
    validation_execution_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    test_definition_version: SemanticVersion
    test_definition_sha256: Sha256Digest
    catalogue_sha256: Sha256Digest
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

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
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
        return self


class EvidenceSnapshot(FrozenModel):
    evidence_snapshot_id: UUID
    validation_execution_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
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
    scenario_run_id: UUID
    links: ValidationExecutionLinks = ValidationExecutionLinks()


class CaptureValidationCheckpointRequest(FrozenModel):
    checkpoint_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")


class FinaliseValidationExecutionRequest(FrozenModel):
    checkpoint_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
