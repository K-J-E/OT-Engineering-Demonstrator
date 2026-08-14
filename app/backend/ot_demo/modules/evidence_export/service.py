"""Assemble self-contained I8 ZIPs exclusively from preserved trusted records."""

from __future__ import annotations

import html
import json
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from ...application.scenario_coordinator import ScenarioCoordinator
from ...domain.enums import (
    CompositeConstituentSourceKind,
    CompositeResultStatus,
    EvidenceClass,
    RequiredInputRole,
    ScenarioMode,
    ScenarioRunStatus,
    ValidationExecutionStatus,
)
from ...infrastructure.build_identity import ApplicationBuildManifest
from ...infrastructure.configuration_loader import JsonConfigurationLoader
from ...infrastructure.evidence_package_repository import EvidencePackageRepository
from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from ...infrastructure.investigation_repository import InvestigationRepository
from ...infrastructure.validation_repository import ValidationRepository
from ...infrastructure.determination_repository import DeterminationRepository
from ...infrastructure.validation_repository import ValidationRecordNotFound
from ..validation.catalogue import (
    ValidationCatalogueError,
    ValidationCatalogueLoader,
    ValidationCatalogueResolver,
)
from ..validation.models import (
    ConstituentCaseDefinition,
    LoadedValidationDefinition,
    ValidationExecutionSummary,
)
from ..validation.suspension_provenance import (
    ResolvedSuspensionSource,
    SuspensionProvenanceError,
    resolve_suspension_source,
)
from .models import (
    CompositeEvidencePackage,
    EvidenceExportCandidate,
    EvidencePackage,
    SuspensionEvidencePackage,
)


class EvidenceExportBoundaryError(ValueError):
    """Raised when preserved records cannot support an approved I8 package."""


class EvidenceExportService:
    def __init__(
        self,
        packages: EvidencePackageRepository,
        validation: ValidationRepository,
        investigations: InvestigationRepository,
        scenarios: ScenarioCoordinator,
        configurations: JsonConfigurationLoader,
        catalogue: ValidationCatalogueResolver | ValidationCatalogueLoader,
        determination: DeterminationRepository | None = None,
        *,
        application_build_manifest: ApplicationBuildManifest,
        output_directory: Path,
    ) -> None:
        self._packages = packages
        self._validation = validation
        self._investigations = investigations
        self._scenarios = scenarios
        self._configurations = configurations
        self._determination = determination
        if isinstance(catalogue, ValidationCatalogueResolver):
            self._catalogue = catalogue
        else:
            historical = tuple(
                sorted(
                    catalogue.catalogue_path.parent.glob("history/*/catalogue.json")
                )
            )
            self._catalogue = ValidationCatalogueResolver(
                catalogue.catalogue_path,
                historical,
            )
        self._application_build_manifest = application_build_manifest
        self._output_directory = output_directory.resolve()
        self._output_directory.mkdir(parents=True, exist_ok=True)

    def generate(self, execution_id: UUID) -> EvidencePackage:
        summary = self._validation.summary(execution_id)
        execution = summary.execution
        run = self._scenarios.run_context(execution.scenario_run_id)
        self._verify_export_boundary(summary, run.status)
        try:
            definition = self._catalogue.resolve(
                test_id=execution.test_id,
                catalogue_version=execution.catalogue_version,
                catalogue_sha256=execution.catalogue_sha256,
                test_definition_version=execution.test_definition_version,
                test_definition_sha256=execution.test_definition_sha256,
            )
        except ValidationCatalogueError as error:
            raise EvidenceExportBoundaryError(
                "execution-bound historical test definition did not resolve"
            ) from error
        loaded = self._configurations.load(f"v{execution.configuration_version}")
        if loaded.catalog_entry.configuration_id != execution.configuration_id:
            raise EvidenceExportBoundaryError(
                "execution configuration identity does not match the immutable package"
            )

        package_id = f"PKG-{uuid4().hex[:12]}"
        archive_name = f"{package_id}-{execution.evidence_class.value}.zip"
        archive_path = self._output_directory / archive_name
        if archive_path.exists():
            raise EvidenceExportBoundaryError(
                "new evidence package path unexpectedly already exists"
            )

        files, source_references = self._package_files(
            package_id, summary, definition.model_dump(mode="json"), loaded
        )
        manifest = self._manifest(
            package_id, summary, files, source_references
        )
        manifest_bytes = canonical_json_bytes(manifest)
        manifest_sha = sha256_bytes(manifest_bytes)
        self._write_archive(archive_path, files, manifest_bytes)
        try:
            self._verify_archive(archive_path, manifest)
            archive_sha = sha256_file(archive_path)
            relative_path = f"evidence/exports/{archive_name}"
            record = EvidencePackage(
                package_id=package_id,
                validation_execution_id=execution.validation_execution_id,
                test_id=execution.test_id,
                test_definition_version=execution.test_definition_version,
                test_definition_sha256=execution.test_definition_sha256,
                source_catalogue_version=execution.catalogue_version,
                source_catalogue_sha256=execution.catalogue_sha256,
                evidence_class=execution.evidence_class,
                scenario_run_id=execution.scenario_run_id,
                configuration_id=execution.configuration_id,
                configuration_version=execution.configuration_version,
                application_build_id=execution.application_build_id,
                generation_application_build_id=(
                    self._application_build_manifest.application_build_id
                ),
                evidence_snapshot_ids=tuple(
                    item.evidence_snapshot_id for item in summary.evidence_snapshots
                ),
                manifest_sha256=manifest_sha,
                archive_sha256=archive_sha,
                archive_path=relative_path,
                verification_status="VERIFIED",
                source_record_references=source_references,
            )
            self._packages.insert(record)
            return record
        except Exception:
            archive_path.unlink(missing_ok=True)
            raise

    def get(self, package_id: str) -> EvidencePackage:
        return self._packages.get(package_id)

    def generate_suspension(self, suspension_record_id: UUID) -> SuspensionEvidencePackage:
        suspension = self._validation.get_suspension(suspension_record_id)
        try:
            source = resolve_suspension_source(
                self._validation, self._scenarios, suspension
            )
        except SuspensionProvenanceError as error:
            raise EvidenceExportBoundaryError(str(error)) from error
        resolved_definition, resolved_case, source_resolution = (
            self._resolve_suspension_catalogue_source(source)
        )
        package_id = f"SPKG-{uuid4().hex[:12]}"
        archive_name = f"{package_id}-{suspension.inherited_evidence_class.value}.zip"
        archive_path = self._output_directory / archive_name
        if archive_path.exists():
            raise EvidenceExportBoundaryError(
                "new suspension evidence package path unexpectedly already exists"
            )
        records, source_references = self._suspension_record_set(
            source, prefix="records"
        )
        if source_resolution["catalogue"] == "RESOLVED":
            records["records/resolved-source-catalogue.json"] = {
                "catalogue_version": str(source.target.catalogue_version),
                "catalogue_sha256": source.target.catalogue_sha256,
                "resolution_authority": "ValidationCatalogueResolver",
            }
            source_references = tuple(sorted({
                *source_references,
                f"validation-catalogue:{source.target.catalogue_version}:{source.target.catalogue_sha256}",
            }))
        if resolved_definition is not None:
            records["records/resolved-source-test-definition.json"] = {
                "test_id": resolved_definition.definition.test_id,
                "test_definition_version": str(resolved_definition.definition.version),
                "test_definition_sha256": resolved_definition.definition_sha256,
                "definition": resolved_definition.definition.model_dump(mode="json"),
            }
            source_references = tuple(sorted({
                *source_references,
                f"test-definition:{resolved_definition.definition.test_id}:{resolved_definition.definition_sha256}",
            }))
        if resolved_case is not None:
            records["records/resolved-source-case-definition.json"] = {
                "case_id": resolved_case.case_id,
                "case_definition_version": str(resolved_case.version),
                "case_definition_sha256": sha256_bytes(
                    canonical_json_bytes(resolved_case.model_dump(mode="json"))
                ),
                "definition": resolved_case.model_dump(mode="json"),
            }
            source_references = tuple(sorted({
                *source_references,
                f"case-definition:{resolved_case.case_id}:{source.target.case_definition_sha256}",
            }))
        files = {path: canonical_json_bytes(value) for path, value in records.items()}
        files["README.txt"] = self._readme(suspension.inherited_evidence_class)
        source_build = (
            source.execution.application_build_id
            if source.execution is not None
            else source.target.target_application_build_id
        )
        manifest = {
            "package_id": package_id,
            "package_kind": "FINALISED_VALIDATION_SUSPENSION",
            "evidence_class": suspension.inherited_evidence_class.value,
            "evidence_notice": (
                "FORMAL VALIDATION ASSURANCE EVIDENCE — BLOCKED-TEST"
                if suspension.inherited_evidence_class is EvidenceClass.FORMAL
                else "NOT FORMAL VALIDATION EVIDENCE — BLOCKED-TEST"
            ),
            "source_suspension_record_id": str(suspension.suspension_record_id),
            "source_validation_attempt_id": str(suspension.validation_attempt_id),
            "source_validation_execution_id": (
                str(suspension.validation_execution_id)
                if suspension.validation_execution_id else None
            ),
            "source_scenario_run_id": (
                str(suspension.scenario_run_id) if suspension.scenario_run_id else None
            ),
            "source_application_build_id": source_build,
            "verifier_application_build_id": suspension.verifier_application_build_id,
            "generation_application_build_id": self._application_build_manifest.application_build_id,
            "source_catalogue_version": source.target.catalogue_version,
            "source_catalogue_sha256": source.target.catalogue_sha256,
            "test_id": source.target.test_id,
            "source_test_definition_version": source.target.test_definition_version,
            "source_test_definition_sha256": source.target.test_definition_sha256,
            "case_id": source.target.case_id,
            "source_case_definition_version": source.target.case_definition_version,
            "source_case_definition_sha256": source.target.case_definition_sha256,
            "source_configuration_id": source.target.configuration_id,
            "source_configuration_version": source.target.configuration_version,
            "source_resolution": source_resolution,
            "condition_id": suspension.condition_id.value,
            "classifier_version": suspension.classifier_version,
            "evidence_contract_version": suspension.evidence_contract_version,
            "source_record_references": list(source_references),
            "files": [
                {"path": path, "byte_size": len(content), "sha256": sha256_bytes(content)}
                for path, content in sorted(files.items())
            ],
        }
        manifest_bytes = canonical_json_bytes(manifest)
        manifest_sha = sha256_bytes(manifest_bytes)
        self._write_archive(archive_path, files, manifest_bytes)
        try:
            self._verify_archive(archive_path, manifest)
            package = SuspensionEvidencePackage(
                package_id=package_id,
                suspension_record_id=suspension.suspension_record_id,
                validation_attempt_id=suspension.validation_attempt_id,
                test_id=source.target.test_id,
                case_id=source.target.case_id,
                evidence_class=suspension.inherited_evidence_class,
                source_catalogue_version=source.target.catalogue_version,
                source_catalogue_sha256=source.target.catalogue_sha256,
                source_test_definition_version=source.target.test_definition_version,
                source_test_definition_sha256=source.target.test_definition_sha256,
                source_case_definition_version=source.target.case_definition_version,
                source_case_definition_sha256=source.target.case_definition_sha256,
                source_configuration_id=source.target.configuration_id,
                source_configuration_version=source.target.configuration_version,
                source_application_build_id=source_build,
                verifier_application_build_id=suspension.verifier_application_build_id,
                generation_application_build_id=self._application_build_manifest.application_build_id,
                validation_execution_id=suspension.validation_execution_id,
                scenario_run_id=suspension.scenario_run_id,
                evidence_snapshot_ids=tuple(
                    item.evidence_snapshot_id for item in source.evidence_snapshots
                ),
                source_resolution=source_resolution,
                manifest_sha256=manifest_sha,
                archive_sha256=sha256_file(archive_path),
                archive_path=f"evidence/exports/{archive_name}",
                verification_status="VERIFIED",
                source_record_references=source_references,
            )
            self._packages.insert_suspension(package)
            return package
        except Exception:
            archive_path.unlink(missing_ok=True)
            raise

    def generate_composite(self, composite_id: UUID) -> CompositeEvidencePackage:
        composite = self._validation.get_composite(composite_id)
        if (
            composite.status is not CompositeResultStatus.FINALISED
            or composite.evidence_class is not EvidenceClass.EXPLORATORY
            or composite.determination is None
        ):
            raise EvidenceExportBoundaryError(
                "composite export requires a finalised immutable EXPLORATORY result"
            )
        try:
            definition = self._catalogue.resolve(
                test_id=composite.test_id,
                catalogue_version=composite.catalogue_version,
                catalogue_sha256=composite.catalogue_sha256,
                test_definition_version=composite.test_definition_version,
                test_definition_sha256=composite.test_definition_sha256,
            )
        except ValidationCatalogueError as error:
            raise EvidenceExportBoundaryError(
                "composite-bound historical test definition did not resolve"
            ) from error
        summaries = tuple(
            self._validation.summary(item.validation_execution_id)
            for item in composite.constituent_links
            if item.source_kind is CompositeConstituentSourceKind.EXECUTION_RESULT
            and item.validation_execution_id is not None
        )
        suspensions = tuple(
            self._validation.get_suspension(item.suspension_record_id)
            for item in composite.constituent_links
            if item.source_kind is CompositeConstituentSourceKind.SUSPENSION_RESULT
            and item.suspension_record_id is not None
        )
        package_id = f"CPKG-{uuid4().hex[:12]}"
        archive_name = f"{package_id}-EXPLORATORY.zip"
        archive_path = self._output_directory / archive_name
        if archive_path.exists():
            raise EvidenceExportBoundaryError(
                "new composite evidence package path unexpectedly already exists"
            )
        records: dict[str, Any] = {
            "records/composite-validation-result.json": composite.model_dump(mode="json"),
            "records/test-definition.json": definition.model_dump(mode="json"),
        }
        for summary in summaries:
            execution_id = summary.execution.validation_execution_id
            if summary.execution.executed_result_id is None or summary.execution.validation_attempt_id is None:
                raise EvidenceExportBoundaryError(
                    "execution constituent is missing its immutable executed-result provenance"
                )
            executed_result = self._validation.get_executed_result(
                summary.execution.executed_result_id
            )
            records[
                f"records/constituents/{execution_id}/validation-execution.json"
            ] = summary.execution.model_dump(mode="json")
            records[
                f"records/constituents/{execution_id}/executed-validation-result.json"
            ] = executed_result.model_dump(mode="json")
            records[
                f"records/constituents/{execution_id}/validation-attempt.json"
            ] = self._validation.get_attempt(
                summary.execution.validation_attempt_id
            ).model_dump(mode="json")
            records[
                f"records/constituents/{execution_id}/scenario-run.json"
            ] = self._scenarios.run_context(
                summary.execution.scenario_run_id
            ).model_dump(mode="json")
            for evidence in summary.evidence_snapshots:
                records[
                    f"records/constituents/{execution_id}/evidence/{evidence.evidence_snapshot_id}.json"
                ] = evidence.model_dump(mode="json")
        for suspension in suspensions:
            suspension_id = suspension.suspension_record_id
            try:
                source = resolve_suspension_source(
                    self._validation, self._scenarios, suspension
                )
            except SuspensionProvenanceError as error:
                raise EvidenceExportBoundaryError(str(error)) from error
            link = next(
                item for item in composite.constituent_links
                if item.suspension_record_id == suspension_id
            )
            if (
                link.scenario_run_id != suspension.scenario_run_id
                or link.evidence_snapshot_ids != tuple(
                    item.evidence_snapshot_id for item in source.evidence_snapshots
                )
            ):
                raise EvidenceExportBoundaryError(
                    "composite suspension link differs from its preserved source set"
                )
            suspension_records, _ = self._suspension_record_set(
                source, prefix=f"records/constituents/{suspension_id}"
            )
            records.update(suspension_records)
        files = {path: canonical_json_bytes(value) for path, value in records.items()}
        files["README.txt"] = self._readme(EvidenceClass.EXPLORATORY)
        source_references = tuple(
            sorted(
                {
                    f"composite-validation-result:{composite.composite_result_id}",
                    *composite.source_record_references,
                }
            )
        )
        manifest = {
            "package_id": package_id,
            "evidence_class": EvidenceClass.EXPLORATORY.value,
            "evidence_notice": "NOT FORMAL VALIDATION EVIDENCE",
            "source_composite_result_id": str(composite.composite_result_id),
            "source_application_build_id": composite.application_build_id,
            "generation_application_build_id": (
                self._application_build_manifest.application_build_id
            ),
            "source_catalogue_version": composite.catalogue_version,
            "source_catalogue_sha256": composite.catalogue_sha256,
            "test_id": composite.test_id,
            "test_definition_version": composite.test_definition_version,
            "test_definition_sha256": composite.test_definition_sha256,
            "determination": composite.determination.value,
            "constituent_execution_ids": [
                str(item.execution.validation_execution_id) for item in summaries
            ],
            "constituent_suspension_record_ids": [
                str(item.suspension_record_id) for item in suspensions
            ],
            "source_record_references": list(source_references),
            "files": [
                {
                    "path": path,
                    "byte_size": len(content),
                    "sha256": sha256_bytes(content),
                }
                for path, content in sorted(files.items())
            ],
        }
        manifest_bytes = canonical_json_bytes(manifest)
        manifest_sha = sha256_bytes(manifest_bytes)
        self._write_archive(archive_path, files, manifest_bytes)
        try:
            self._verify_archive(archive_path, manifest)
            record = CompositeEvidencePackage(
                package_id=package_id,
                composite_result_id=composite.composite_result_id,
                test_id=composite.test_id,
                source_catalogue_version=composite.catalogue_version,
                source_catalogue_sha256=composite.catalogue_sha256,
                test_definition_version=composite.test_definition_version,
                test_definition_sha256=composite.test_definition_sha256,
                source_application_build_id=composite.application_build_id,
                generation_application_build_id=(
                    self._application_build_manifest.application_build_id
                ),
                constituent_execution_ids=tuple(
                    item.execution.validation_execution_id for item in summaries
                ),
                constituent_suspension_record_ids=tuple(
                    item.suspension_record_id for item in suspensions
                ),
                manifest_sha256=manifest_sha,
                archive_sha256=sha256_file(archive_path),
                archive_path=f"evidence/exports/{archive_name}",
                verification_status="VERIFIED",
                source_record_references=source_references,
            )
            self._packages.insert_composite(record)
            return record
        except Exception:
            archive_path.unlink(missing_ok=True)
            raise

    def get_composite_package(self, package_id: str) -> CompositeEvidencePackage:
        return self._packages.get_composite(package_id)

    def list_composite_packages(self) -> tuple[CompositeEvidencePackage, ...]:
        return self._packages.list_composites()

    def get_suspension_package(self, package_id: str) -> SuspensionEvidencePackage:
        return self._packages.get_suspension(package_id)

    def list_suspension_packages(self) -> tuple[SuspensionEvidencePackage, ...]:
        return self._packages.list_suspensions()

    def list(self) -> tuple[EvidencePackage, ...]:
        return self._packages.list()

    def candidates(self) -> tuple[EvidenceExportCandidate, ...]:
        candidates: list[EvidenceExportCandidate] = []
        for summary in self._validation.list_summaries():
            run = self._scenarios.run_context(summary.execution.scenario_run_id)
            try:
                self._verify_export_boundary(summary, run.status)
            except EvidenceExportBoundaryError as error:
                available = False
                reason_code = "EXPORT_SOURCE_NOT_READY"
                reason = str(error)
            else:
                available = True
                reason_code = "AVAILABLE"
                reason = (
                    "Preserved immutable records satisfy the evidence-package source gate."
                )
            candidates.append(
                EvidenceExportCandidate(
                    validation_execution_id=summary.execution.validation_execution_id,
                    test_id=summary.execution.test_id,
                    evidence_class=summary.execution.evidence_class,
                    scenario_run_id=summary.execution.scenario_run_id,
                    source_run_status=run.status,
                    export_available=available,
                    reason_code=reason_code,
                    reason=reason,
                )
            )
        return tuple(candidates)

    def archive_file(self, package_id: str) -> Path:
        package = self.get(package_id)
        candidate = (self._output_directory / Path(package.archive_path).name).resolve()
        if candidate.parent != self._output_directory or not candidate.is_file():
            raise EvidenceExportBoundaryError(
                "stored evidence package path is outside the controlled export directory"
            )
        if sha256_file(candidate) != package.archive_sha256:
            raise EvidenceExportBoundaryError(
                "stored evidence package archive hash no longer matches its record"
            )
        return candidate

    def composite_archive_file(self, package_id: str) -> Path:
        package = self.get_composite_package(package_id)
        candidate = (self._output_directory / Path(package.archive_path).name).resolve()
        if candidate.parent != self._output_directory or not candidate.is_file():
            raise EvidenceExportBoundaryError(
                "stored composite package path is outside the controlled export directory"
            )
        if sha256_file(candidate) != package.archive_sha256:
            raise EvidenceExportBoundaryError(
                "stored composite package archive hash no longer matches its record"
            )
        return candidate

    def suspension_archive_file(self, package_id: str) -> Path:
        package = self.get_suspension_package(package_id)
        candidate = (self._output_directory / Path(package.archive_path).name).resolve()
        if candidate.parent != self._output_directory or not candidate.is_file():
            raise EvidenceExportBoundaryError(
                "stored suspension package path is outside the controlled export directory"
            )
        if sha256_file(candidate) != package.archive_sha256:
            raise EvidenceExportBoundaryError(
                "stored suspension package archive hash no longer matches its record"
            )
        return candidate

    def _resolve_suspension_catalogue_source(
        self,
        source: ResolvedSuspensionSource,
    ) -> tuple[
        LoadedValidationDefinition | None,
        ConstituentCaseDefinition | None,
        dict[str, str],
    ]:
        target = source.target
        unavailable = target.unresolved_required_role
        resolution = {
            "catalogue": "PENDING",
            "test_definition": "PENDING",
            "case_definition": "PENDING",
        }
        try:
            catalogue_definitions: tuple[LoadedValidationDefinition, ...] | None
            if unavailable is RequiredInputRole.CATALOGUE:
                catalogue_definitions = None
                resolution["catalogue"] = "EXEMPT_UNAVAILABLE_VSC_003"
            else:
                if target.catalogue_version is None or target.catalogue_sha256 is None:
                    raise ValidationCatalogueError(
                        "available suspension catalogue identity is incomplete"
                    )
                catalogue_definitions = self._catalogue.resolve_catalogue(
                    catalogue_version=str(target.catalogue_version),
                    catalogue_sha256=target.catalogue_sha256,
                )
                resolution["catalogue"] = "RESOLVED"

            resolved_definition: LoadedValidationDefinition | None
            if unavailable is RequiredInputRole.TEST_DEFINITION:
                resolved_definition = None
                resolution["test_definition"] = "EXEMPT_UNAVAILABLE_VSC_003"
            else:
                if (
                    target.test_definition_version is None
                    or target.test_definition_sha256 is None
                ):
                    raise ValidationCatalogueError(
                        "available suspension test-definition identity is incomplete"
                    )
                if catalogue_definitions is None:
                    resolved_definition = self._catalogue.resolve_definition_identity(
                        test_id=target.test_id,
                        test_definition_version=str(target.test_definition_version),
                        test_definition_sha256=target.test_definition_sha256,
                    )
                else:
                    matches = tuple(
                        item for item in catalogue_definitions
                        if (
                            item.definition.test_id == target.test_id
                            and str(item.definition.version)
                            == str(target.test_definition_version)
                            and item.definition_sha256
                            == target.test_definition_sha256
                        )
                    )
                    if len(matches) != 1:
                        raise ValidationCatalogueError(
                            "suspension-bound test definition did not resolve uniquely in its source catalogue"
                        )
                    resolved_definition = matches[0]
                resolution["test_definition"] = "RESOLVED"

            resolved_case: ConstituentCaseDefinition | None = None
            if target.case_id is None:
                resolution["case_definition"] = "NOT_APPLICABLE"
            elif unavailable is RequiredInputRole.CASE_DEFINITION:
                resolution["case_definition"] = "EXEMPT_UNAVAILABLE_VSC_003"
            else:
                if (
                    target.case_definition_version is None
                    or target.case_definition_sha256 is None
                ):
                    raise ValidationCatalogueError(
                        "available suspension case-definition identity is incomplete"
                    )
                parent = resolved_definition
                if parent is None and catalogue_definitions is not None:
                    parents = tuple(
                        item for item in catalogue_definitions
                        if item.definition.test_id == target.test_id
                    )
                    if len(parents) != 1:
                        raise ValidationCatalogueError(
                            "case parent did not resolve uniquely in the source catalogue"
                        )
                    parent = parents[0]
                if parent is None:
                    raise ValidationCatalogueError(
                        "available case definition has no controlled catalogue parent"
                    )
                case_matches = tuple(
                    item for item in parent.definition.constituent_cases
                    if (
                        item.case_id == target.case_id
                        and str(item.version) == str(target.case_definition_version)
                        and sha256_bytes(canonical_json_bytes(item.model_dump(mode="json")))
                        == target.case_definition_sha256
                    )
                )
                if len(case_matches) != 1:
                    raise ValidationCatalogueError(
                        "suspension-bound case definition did not resolve uniquely"
                    )
                resolved_case = case_matches[0]
                resolution["case_definition"] = "RESOLVED"
        except ValidationCatalogueError as error:
            raise EvidenceExportBoundaryError(
                "suspension source catalogue/test/case identity did not resolve"
            ) from error
        return resolved_definition, resolved_case, resolution

    @staticmethod
    def _suspension_record_set(
        source: ResolvedSuspensionSource,
        *,
        prefix: str,
    ) -> tuple[dict[str, Any], tuple[str, ...]]:
        suspension = source.suspension
        records: dict[str, Any] = {
            f"{prefix}/validation-suspension.json": suspension.model_dump(mode="json"),
            f"{prefix}/validation-target-selection.json": source.target.model_dump(mode="json"),
            f"{prefix}/validation-attempt.json": source.attempt.model_dump(mode="json"),
            f"{prefix}/condition-definition.json": {
                "condition_id": suspension.condition_id.value,
                "record_schema_version": suspension.record_schema_version,
                "classifier_version": suspension.classifier_version,
                "evidence_contract_version": suspension.evidence_contract_version,
                "lifecycle_position": suspension.lifecycle_position.value,
                "reason_code": suspension.reason_code,
            },
        }
        references = {
            f"validation-suspension:{suspension.suspension_record_id}",
            f"validation-target-selection:{source.target.target_selection_id}",
            f"validation-attempt:{source.attempt.validation_attempt_id}",
            f"validation-condition:{suspension.condition_id.value}:{suspension.evidence_contract_version}",
        }
        for item in suspension.evidence:
            records[f"{prefix}/suspension-evidence/{item.evidence_id}.json"] = (
                item.model_dump(mode="json")
            )
            references.add(f"validation-suspension-evidence:{item.evidence_id}")
        if source.execution is not None and source.run is not None:
            records[f"{prefix}/validation-execution.json"] = source.execution.model_dump(mode="json")
            records[f"{prefix}/scenario-run.json"] = source.run.model_dump(mode="json")
            references.add(f"validation-execution:{source.execution.validation_execution_id}")
            references.add(f"scenario-run:{source.run.scenario_run_id}")
            for item in source.evidence_snapshots:
                records[f"{prefix}/evidence/{item.evidence_snapshot_id}.json"] = (
                    item.model_dump(mode="json")
                )
                references.add(f"evidence-snapshot:{item.evidence_snapshot_id}")
        return records, tuple(sorted(references))

    @staticmethod
    def _verify_export_boundary(
        summary: ValidationExecutionSummary,
        _run_status: ScenarioRunStatus,
    ) -> None:
        execution = summary.execution
        if not summary.evidence_snapshots:
            raise EvidenceExportBoundaryError(
                "evidence export requires at least one immutable checkpoint snapshot"
            )
        if execution.evidence_class is EvidenceClass.FORMAL:
            if execution.scenario_mode is not ScenarioMode.FORMAL:
                raise EvidenceExportBoundaryError(
                    "FORMAL evidence class requires a FORMAL scenario run"
                )
            if execution.status is not ValidationExecutionStatus.FINALISED:
                raise EvidenceExportBoundaryError(
                    "a FORMAL package requires a finalised validation execution"
                )
        else:
            if execution.scenario_mode is not ScenarioMode.EXPLORATION:
                raise EvidenceExportBoundaryError(
                    "EXPLORATORY evidence class requires an EXPLORATION scenario run"
                )
            if execution.status is not ValidationExecutionStatus.FINALISED:
                raise EvidenceExportBoundaryError(
                    "an EXPLORATORY package requires a finalised validation execution"
                )
        for evidence in summary.evidence_snapshots:
            identity = (
                evidence.validation_execution_id,
                evidence.scenario_run_id,
                evidence.scenario_mode,
                evidence.evidence_class,
                evidence.configuration_id,
                evidence.configuration_version,
                evidence.application_build_id,
            )
            expected = (
                execution.validation_execution_id,
                execution.scenario_run_id,
                execution.scenario_mode,
                execution.evidence_class,
                execution.configuration_id,
                execution.configuration_version,
                execution.application_build_id,
            )
            if identity != expected:
                raise EvidenceExportBoundaryError(
                    "evidence snapshot provenance differs from its execution"
                )

    def _package_files(
        self,
        package_id: str,
        summary: ValidationExecutionSummary,
        definition: dict[str, Any],
        loaded,
    ) -> tuple[dict[str, bytes], tuple[str, ...]]:
        execution = summary.execution
        latest = summary.evidence_snapshots[-1]
        captured = latest.canonical_payload.get("scenario_snapshot")
        if not isinstance(captured, dict):
            raise EvidenceExportBoundaryError(
                "preserved evidence does not contain its captured scenario snapshot"
            )
        source_references = tuple(
            sorted(
                {
                    f"validation-execution:{execution.validation_execution_id}",
                    f"test-definition:{execution.test_id}:{execution.test_definition_version}",
                    f"configuration:{execution.configuration_id}",
                    *(reference for item in summary.evidence_snapshots for reference in item.source_record_references),
                    *(f"evidence-snapshot:{item.evidence_snapshot_id}" for item in summary.evidence_snapshots),
                }
            )
        )
        records: dict[str, Any] = {
            "records/validation-execution.json": execution.model_dump(mode="json"),
            "records/test-definition.json": definition,
            "records/configuration.json": {
                "catalog_entry": loaded.catalog_entry.model_dump(mode="json"),
                "network": loaded.data.model_dump(mode="json"),
            },
            "records/scenario-run.json": captured.get("run"),
            "records/telemetry.json": captured.get("telemetry"),
            "records/topology.json": captured.get("topology"),
            "records/outage.json": captured.get("outage"),
            "records/restoration-assessments.json": captured.get(
                "restoration_assessments", []
            ),
            "records/operational-events.json": captured.get("events"),
            "records/source-index.json": {
                "source_record_references": source_references,
                "evidence_snapshot_ids": [
                    str(item.evidence_snapshot_id)
                    for item in summary.evidence_snapshots
                ],
            },
        }
        for evidence in summary.evidence_snapshots:
            records[
                f"records/evidence-snapshots/{evidence.evidence_snapshot_id}.json"
            ] = evidence.model_dump(mode="json")

        if self._determination is not None and execution.executed_result_id is not None:
            try:
                result = self._determination.get_result(execution.executed_result_id)
            except ValidationRecordNotFound:
                result = None
            if result is not None and result.determination_context_id is not None:
                context = self._determination.get_context(
                    result.determination_context_id
                )
                findings = self._determination.list_findings(
                    result.determination_context_id
                )
                records["records/determination/context.json"] = context.model_dump(
                    mode="json"
                )
                records["records/determination/executed-result.json"] = result.model_dump(
                    mode="json"
                )
                records["records/determination/criterion-findings.json"] = [
                    item.model_dump(mode="json") for item in findings
                ]
                for member in context.members:
                    source = self._determination.get_source(member.source_record_id)
                    records[
                        f"records/determination/sources/{member.role}.json"
                    ] = source.model_dump(mode="json")
                source_references = tuple(
                    sorted(
                        {
                            *source_references,
                            f"determination-context:{context.determination_context_id}",
                            f"determination-method:{context.method_id}:{context.method_sha256}",
                            *(
                                f"criterion-finding:{item.criterion_finding_id}"
                                for item in findings
                            ),
                        }
                    )
                )
                records["records/source-index.json"] = {
                    "source_record_references": source_references,
                    "evidence_snapshot_ids": [
                        str(item.evidence_snapshot_id)
                        for item in summary.evidence_snapshots
                    ],
                }

        chain = self._investigation_chain(execution.validation_execution_id)
        if chain is not None:
            records["records/investigation-chain.json"] = chain
            source_references = tuple(
                sorted(
                    {
                        *source_references,
                        "defect:DEF-001",
                        "correction:COR-001",
                        *(
                            f"repeat-link:{item['repeat_link_id']}"
                            for item in chain["repeat_links"]
                        ),
                    }
                )
            )
            records["records/source-index.json"] = {
                "source_record_references": source_references,
                "evidence_snapshot_ids": [
                    str(item.evidence_snapshot_id)
                    for item in summary.evidence_snapshots
                ],
            }

        files = {
            path: canonical_json_bytes(value) for path, value in records.items()
        }
        files["figures/network-evidence.svg"] = self._network_figure(
            package_id, execution.evidence_class, captured
        )
        files["report.html"] = self._report(
            package_id, summary, source_references, chain
        )
        files["README.txt"] = self._readme(execution.evidence_class)
        return files, source_references

    def _investigation_chain(self, execution_id: UUID) -> dict[str, Any] | None:
        defect = self._investigations.get_defect()
        correction = self._investigations.get_correction()
        if defect is None or correction is None:
            return None
        links = self._investigations.list_repeat_links(defect.defect_record_id)
        related_ids = {
            defect.original_failed_execution_id,
            *(item.new_execution_id for item in links),
        }
        if execution_id not in related_ids:
            return None
        return {
            "defect": defect.model_dump(mode="json"),
            "correction": correction.model_dump(mode="json"),
            "repeat_links": [item.model_dump(mode="json") for item in links],
            "executions": [
                self._validation.summary(item).model_dump(mode="json")
                for item in sorted(related_ids, key=str)
            ],
        }

    def _manifest(
        self,
        package_id: str,
        summary: ValidationExecutionSummary,
        files: dict[str, bytes],
        source_references: tuple[str, ...],
    ) -> dict[str, Any]:
        execution = summary.execution
        return {
            "package_id": package_id,
            "evidence_class": execution.evidence_class.value,
            "evidence_notice": (
                "FORMAL VALIDATION EVIDENCE"
                if execution.evidence_class is EvidenceClass.FORMAL
                else "NOT FORMAL VALIDATION EVIDENCE"
            ),
            "source_validation_execution_id": str(execution.validation_execution_id),
            "source_scenario_run_id": str(execution.scenario_run_id),
            "source_application_build_id": execution.application_build_id,
            "generation_application_build_id": (
                self._application_build_manifest.application_build_id
            ),
            "configuration_id": execution.configuration_id,
            "configuration_version": execution.configuration_version,
            "test_id": execution.test_id,
            "test_definition_version": execution.test_definition_version,
            "test_definition_sha256": execution.test_definition_sha256,
            "source_catalogue_version": execution.catalogue_version,
            "catalogue_sha256": execution.catalogue_sha256,
            "evidence_snapshots": [
                {
                    "evidence_snapshot_id": str(item.evidence_snapshot_id),
                    "canonical_payload_sha256": item.canonical_payload_sha256,
                }
                for item in summary.evidence_snapshots
            ],
            "source_record_references": list(source_references),
            "files": [
                {
                    "path": path,
                    "byte_size": len(content),
                    "sha256": sha256_bytes(content),
                }
                for path, content in sorted(files.items())
            ],
        }

    @staticmethod
    def _report(
        package_id: str,
        summary: ValidationExecutionSummary,
        source_references: tuple[str, ...],
        chain: dict[str, Any] | None,
    ) -> bytes:
        execution = summary.execution
        banner = (
            "FORMAL VALIDATION EVIDENCE"
            if execution.evidence_class is EvidenceClass.FORMAL
            else "NOT FORMAL VALIDATION EVIDENCE — EXPLORATORY"
        )
        observed = (
            "NOT DETERMINED"
            if execution.observed_result is None
            else json.dumps(execution.observed_result, indent=2, sort_keys=True)
        )
        verdict = execution.verdict.value if execution.verdict is not None else "NOT DETERMINED"
        chain_note = (
            "Linked DEF-001 / COR-001 / repeat records are included."
            if chain is not None
            else "No defect/correction chain is applicable to this execution."
        )
        links = "".join(
            f'<li><code>{html.escape(reference)}</code></li>'
            for reference in source_references
        )
        body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{package_id}</title>
<style>body{{font:16px system-ui,sans-serif;max-width:1050px;margin:40px auto;padding:0 24px;color:#13263e}}header{{border-left:8px solid #1f5f8b;padding:18px;background:#eef4f8}}.banner{{font-weight:800;color:#8a1831}}dl{{display:grid;grid-template-columns:240px 1fr;gap:8px}}dt{{font-weight:700}}dd{{margin:0;overflow-wrap:anywhere}}pre{{white-space:pre-wrap;background:#f5f8fb;padding:16px}}code{{overflow-wrap:anywhere}}a{{color:#1f5f8b}}</style></head>
<body><header><p>OT Graduate Demonstrator · TasGrid East fictional utility</p><h1>Evidence package {package_id}</h1><p class="banner">{banner}</p><p>Simulated operation only — no real equipment control.</p></header>
<h2>Controlled provenance</h2><dl>
<dt>Validation execution</dt><dd>{execution.validation_execution_id}</dd>
<dt>Test</dt><dd>{html.escape(execution.test_id)} v{html.escape(str(execution.test_definition_version))}</dd>
<dt>Scenario run</dt><dd>{execution.scenario_run_id}</dd>
<dt>Evidence class</dt><dd>{execution.evidence_class.value}</dd>
<dt>Configuration</dt><dd>{html.escape(execution.configuration_id)} v{html.escape(str(execution.configuration_version))}</dd>
<dt>Source application build</dt><dd>{execution.application_build_id}</dd>
<dt>Test-definition hash</dt><dd>{execution.test_definition_sha256}</dd>
<dt>Execution status</dt><dd>{execution.status.value}</dd><dt>Determination</dt><dd>{verdict}</dd></dl>
<h2>Expected engineering result</h2><p>{html.escape(execution.expected_result_statement)}</p>
<h2>Preserved observed result</h2><pre>{html.escape(observed)}</pre>
<h2>Captured engineering figure</h2><p><a href="figures/network-evidence.svg">Open network evidence figure</a>. The figure is subordinate to canonical JSON.</p>
<h2>Record set</h2><p><a href="records/validation-execution.json">Validation execution</a> · <a href="records/test-definition.json">Test definition</a> · <a href="records/configuration.json">Configuration</a> · <a href="records/topology.json">Topology</a> · <a href="records/outage.json">Outage</a> · <a href="records/operational-events.json">Operational events</a></p>
<p>{html.escape(chain_note)}</p><h2>Stable source references</h2><ul>{links}</ul>
<p>Integrity is verified with <code>manifest.json</code>. The report and figure do not replace the source records.</p></body></html>"""
        return body.encode("utf-8")

    @staticmethod
    def _readme(evidence_class: EvidenceClass) -> bytes:
        notice = (
            "FORMAL VALIDATION EVIDENCE"
            if evidence_class is EvidenceClass.FORMAL
            else "NOT FORMAL VALIDATION EVIDENCE"
        )
        return (
            "OT Graduate Demonstrator evidence package\n"
            f"Classification: {evidence_class.value} — {notice}\n\n"
            "This package contains fictional local engineering evidence only.\n"
            "It represents simulated operation and has no real equipment-control authority.\n"
            "Open report.html in a browser. Verify every manifest.json file entry by\n"
            "computing SHA-256 over the exact packaged bytes. Canonical JSON records are\n"
            "the source evidence; report.html and figures are review aids only.\n"
        ).encode("utf-8")

    @staticmethod
    def _network_figure(
        package_id: str,
        evidence_class: EvidenceClass,
        captured: dict[str, Any],
    ) -> bytes:
        topology = captured.get("topology") or {}
        outage = captured.get("outage") or {}
        sections = topology.get("sections") or []
        rows: list[str] = []
        for index, section in enumerate(sorted(sections, key=lambda item: item["section_id"])):
            y = 105 + index * 44
            energised = bool(section.get("energised"))
            faulted = bool(section.get("faulted"))
            colour = "#b4233f" if faulted else "#0f766e" if energised else "#64748b"
            sources = ", ".join(section.get("source_feeder_ids") or []) or "none"
            rows.append(
                f'<rect x="40" y="{y}" width="210" height="30" rx="5" fill="{colour}"/>'
                f'<text x="52" y="{y + 20}" fill="white" font-weight="700">{html.escape(section["section_id"])}</text>'
                f'<text x="275" y="{y + 20}" fill="#13263e">Energised: {str(energised).upper()} · Faulted: {str(faulted).upper()} · Source: {html.escape(sources)}</text>'
            )
        height = 145 + max(len(sections), 1) * 44
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}">
<rect width="1000" height="{height}" fill="#f8fafc"/><text x="40" y="42" font-family="system-ui" font-size="24" font-weight="800" fill="#13263e">Captured network evidence</text>
<text x="40" y="70" font-family="system-ui" font-size="14" fill="#52667b">{package_id} · {evidence_class.value} · affected customers {outage.get("affected_customer_count", "unknown")}</text>
<g font-family="system-ui" font-size="14">{''.join(rows)}</g>
<text x="40" y="{height - 24}" font-family="system-ui" font-size="12" fill="#52667b">Review aid generated from the preserved evidence snapshot; canonical JSON remains authoritative.</text></svg>"""
        return svg.encode("utf-8")

    @staticmethod
    def _write_archive(
        path: Path,
        files: dict[str, bytes],
        manifest_bytes: bytes,
    ) -> None:
        with ZipFile(path, mode="x", compression=ZIP_DEFLATED) as archive:
            for name, content in (*sorted(files.items()), ("manifest.json", manifest_bytes)):
                info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, content)

    @staticmethod
    def _verify_archive(path: Path, manifest: dict[str, Any]) -> None:
        expected = {item["path"]: item for item in manifest["files"]}
        with ZipFile(path, mode="r") as archive:
            names = set(archive.namelist())
            if names != {*expected, "manifest.json"}:
                raise EvidenceExportBoundaryError(
                    "evidence ZIP contents differ from the approved manifest set"
                )
            for name, entry in expected.items():
                if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
                    raise EvidenceExportBoundaryError(
                        "evidence ZIP contains an unsafe package path"
                    )
                content = archive.read(name)
                if len(content) != entry["byte_size"]:
                    raise EvidenceExportBoundaryError(
                        f"evidence ZIP byte-size mismatch: {name}"
                    )
                if sha256_bytes(content) != entry["sha256"]:
                    raise EvidenceExportBoundaryError(
                        f"evidence ZIP SHA-256 mismatch: {name}"
                    )
            packaged_manifest = json.loads(archive.read("manifest.json"))
            if packaged_manifest != manifest:
                raise EvidenceExportBoundaryError(
                    "packaged manifest differs from the independently verified manifest"
                )
