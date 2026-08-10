"""Immutable I7 consequence-to-source investigation contracts."""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator
from typing_extensions import Self

from ...domain.base import FrozenModel
from ...domain.enums import RepeatRelationshipType, ValidationVerdict
from ...domain.value_objects import (
    ConfigurationId,
    EngineeringId,
    SemanticVersion,
    Sha256Digest,
    UtcMillisecondInstant,
)
from ..validation.models import ValidationExecutionSummary


class ConfigurationPackageIdentity(FrozenModel):
    configuration_id: ConfigurationId
    version: SemanticVersion
    package_sha256: Sha256Digest
    data_sha256: Sha256Digest
    schema_sha256: Sha256Digest


class ConfigurationDifferenceView(FrozenModel):
    path: str = Field(min_length=1)
    before: str
    after: str


class InvestigationFact(FrozenModel):
    label: str = Field(min_length=1)
    value: str = Field(min_length=1)


class InvestigationStep(FrozenModel):
    step_id: Literal[
        "INV-01", "INV-02", "INV-03", "INV-04", "INV-05", "INV-06", "INV-07"
    ]
    title: str = Field(min_length=1)
    facts: tuple[InvestigationFact, ...] = Field(min_length=1)
    source_record_references: tuple[str, ...] = Field(min_length=1)


class ConfigurationComparisonView(FrozenModel):
    defective: ConfigurationPackageIdentity
    corrected: ConfigurationPackageIdentity
    differences: tuple[ConfigurationDifferenceView, ...] = Field(min_length=1)
    unchanged_information_classes: tuple[str, ...] = Field(min_length=1)


class DefectRecord(FrozenModel):
    defect_record_id: UUID
    defect_id: EngineeringId
    original_failed_execution_id: UUID
    affected_configuration: ConfigurationPackageIdentity
    identified_difference: ConfigurationDifferenceView
    root_cause: str = Field(min_length=1)
    engineering_propagation: tuple[str, ...] = Field(min_length=1)
    supporting_evidence_references: tuple[str, ...] = Field(min_length=1)
    recorded_by: str = Field(min_length=1, max_length=120)
    recorded_scenario_time: UtcMillisecondInstant
    investigation_snapshot_sha256: Sha256Digest


class CorrectionRecord(FrozenModel):
    correction_record_id: UUID
    correction_id: EngineeringId
    defect_record_id: UUID
    defect_id: EngineeringId
    defective_configuration: ConfigurationPackageIdentity
    corrected_configuration: ConfigurationPackageIdentity
    approved_difference: ConfigurationDifferenceView
    engineering_effect: str = Field(min_length=1)
    verification_basis: tuple[str, ...] = Field(min_length=1)
    reviewed_by: str = Field(min_length=1, max_length=120)
    recorded_scenario_time: UtcMillisecondInstant


class RepeatLink(FrozenModel):
    repeat_link_id: UUID
    relationship_type: RepeatRelationshipType
    original_execution_id: UUID
    new_execution_id: UUID
    defect_record_id: UUID
    correction_record_id: UUID
    defect_id: EngineeringId
    correction_id: EngineeringId
    application_build_id: Sha256Digest

    @model_validator(mode="after")
    def distinct_executions(self) -> Self:
        if self.original_execution_id == self.new_execution_id:
            raise ValueError("repeat links require distinct validation executions")
        return self


class InvestigationAction(FrozenModel):
    action_type: Literal[
        "RECORD_DEFECT", "RECORD_CORRECTION", "RUN_DIRECT_REPEAT", "RUN_REGRESSION"
    ]
    available: bool
    reason_code: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class InvestigationWorkspace(FrozenModel):
    original_failure: ValidationExecutionSummary
    steps: tuple[InvestigationStep, ...]
    configuration_comparison: ConfigurationComparisonView
    defect_record: DefectRecord | None = None
    correction_record: CorrectionRecord | None = None
    direct_repeat: ValidationExecutionSummary | None = None
    regression: ValidationExecutionSummary | None = None
    repeat_links: tuple[RepeatLink, ...] = ()
    actions: tuple[InvestigationAction, ...]
    same_build_proven: bool
    conceptual_boundary_notice: str


class StartInvestigationRequest(FrozenModel):
    actor: str = Field(min_length=1, max_length=120)


class RecordDefectRequest(FrozenModel):
    reviewer: str = Field(min_length=1, max_length=120)
    reviewed_step_ids: tuple[str, ...]


class RecordCorrectionRequest(FrozenModel):
    reviewer: str = Field(min_length=1, max_length=120)


class RunLinkedValidationRequest(FrozenModel):
    actor: str = Field(min_length=1, max_length=120)
