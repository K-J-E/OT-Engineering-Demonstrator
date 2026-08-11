"""Typed I8 evidence-package identities and trusted request boundary."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from ...domain.base import FrozenModel
from ...domain.enums import EvidenceClass, ScenarioRunStatus
from ...domain.value_objects import (
    ConfigurationId,
    SemanticVersion,
    Sha256Digest,
)


class EvidencePackageRequest(FrozenModel):
    validation_execution_id: UUID


class EvidencePackage(FrozenModel):
    package_id: str = Field(pattern=r"^PKG-[0-9a-f]{12}$")
    validation_execution_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    test_definition_version: SemanticVersion
    test_definition_sha256: Sha256Digest
    source_catalogue_version: SemanticVersion = "1.0"
    source_catalogue_sha256: Sha256Digest | None = None
    evidence_class: EvidenceClass
    scenario_run_id: UUID
    configuration_id: ConfigurationId
    configuration_version: SemanticVersion
    application_build_id: Sha256Digest
    generation_application_build_id: Sha256Digest
    evidence_snapshot_ids: tuple[UUID, ...] = Field(min_length=1)
    manifest_sha256: Sha256Digest
    archive_sha256: Sha256Digest
    archive_path: str = Field(min_length=1)
    verification_status: Literal["VERIFIED"]
    source_record_references: tuple[str, ...] = Field(min_length=1)


class CompositeEvidencePackage(FrozenModel):
    package_id: str = Field(pattern=r"^CPKG-[0-9a-f]{12}$")
    composite_result_id: UUID
    test_id: str = Field(pattern=r"^VT-EXP-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    evidence_class: EvidenceClass = EvidenceClass.EXPLORATORY
    source_catalogue_version: SemanticVersion
    source_catalogue_sha256: Sha256Digest
    test_definition_version: SemanticVersion
    test_definition_sha256: Sha256Digest
    source_application_build_id: Sha256Digest
    generation_application_build_id: Sha256Digest
    constituent_execution_ids: tuple[UUID, ...] = ()
    constituent_suspension_record_ids: tuple[UUID, ...] = ()
    manifest_sha256: Sha256Digest
    archive_sha256: Sha256Digest
    archive_path: str = Field(min_length=1)
    verification_status: Literal["VERIFIED"]
    source_record_references: tuple[str, ...] = Field(min_length=1)


class SuspensionEvidencePackage(FrozenModel):
    package_id: str = Field(pattern=r"^SPKG-[0-9a-f]{12}$")
    suspension_record_id: UUID
    validation_attempt_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_id: str | None = None
    evidence_class: EvidenceClass
    source_catalogue_version: SemanticVersion | None = None
    source_catalogue_sha256: Sha256Digest | None = None
    source_test_definition_version: SemanticVersion | None = None
    source_test_definition_sha256: Sha256Digest | None = None
    source_case_definition_version: SemanticVersion | None = None
    source_case_definition_sha256: Sha256Digest | None = None
    source_configuration_id: ConfigurationId | None = None
    source_configuration_version: SemanticVersion | None = None
    source_application_build_id: Sha256Digest | None = None
    verifier_application_build_id: Sha256Digest
    generation_application_build_id: Sha256Digest
    validation_execution_id: UUID | None = None
    scenario_run_id: UUID | None = None
    evidence_snapshot_ids: tuple[UUID, ...] = ()
    manifest_sha256: Sha256Digest
    archive_sha256: Sha256Digest
    archive_path: str = Field(min_length=1)
    verification_status: Literal["VERIFIED"]
    source_record_references: tuple[str, ...] = Field(min_length=1)


class EvidenceExportCandidate(FrozenModel):
    validation_execution_id: UUID
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    evidence_class: EvidenceClass
    scenario_run_id: UUID
    source_run_status: ScenarioRunStatus
    export_available: bool
    reason_code: str = Field(min_length=1)
    reason: str = Field(min_length=1)
