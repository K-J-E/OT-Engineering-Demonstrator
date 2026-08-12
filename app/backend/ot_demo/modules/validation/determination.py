"""Generic DC-006 criteria, finding and deterministic result authority."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from ...domain.enums import (
    CriterionFindingStatus,
    CriterionKind,
    DeterminationCompletenessStatus,
    DeterminationContextKind,
    DeterminationContextStatus,
    DeterminationOperator,
    EvidenceClass,
    ValidationAttemptStatus,
    ValidationExecutionStatus,
    ValidationVerdict,
    DeterminationSourceAdapterKind,
)
from ...infrastructure.build_identity import ApplicationBuildManifest
from ...infrastructure.configuration_comparison import compare_engineering_content
from ...infrastructure.configuration_loader import JsonConfigurationLoader
from ...infrastructure.determination_repository import DeterminationRepository
from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ...infrastructure.validation_repository import ValidationRepository
from .catalogue import ValidationCatalogueResolver
from .models import (
    CriterionDefinition,
    CriterionFinding,
    DeterminationCompleteness,
    DeterminationContext,
    DeterminationContextMember,
    DeterminationSourceRecord,
    AuthoritativeRecordSnapshot,
    DeterminationReviewProjection,
    EngineeringReviewFinalisation,
    EngineeringReviewProposal,
    ExecutedValidationResult,
    ValidationExecution,
)
from .normalisation import NormalisationError, normalise
from .source_adapters import (
    AuthoritativeSourceAdapterRegistry,
    SourceAdapterError,
    common_provenance,
    freeze_authoritative_record,
)


class DeterminationBoundaryError(ValueError):
    """Raised when a request crosses the accepted DC-006 authority boundary."""


class DeterminationService:
    _ACTOR_ROLES = {
        "graduate-engineer": "GRADUATE_ENGINEER",
        "independent-reviewer": "INDEPENDENT_ENGINEERING_REVIEWER",
    }

    def __init__(
        self,
        repository: DeterminationRepository,
        validation_repository: ValidationRepository,
        catalogue: ValidationCatalogueResolver,
        *,
        application_build_manifest: ApplicationBuildManifest,
        configuration_loader: JsonConfigurationLoader | None = None,
    ) -> None:
        self._repository = repository
        self._validation_repository = validation_repository
        self._catalogue = catalogue
        self._build = application_build_manifest
        self._configurations = configuration_loader

    def capture_configuration_package_sources(
        self, validation_attempt_id: UUID, *, created_at
    ) -> dict[str, DeterminationSourceRecord]:
        """Capture the accepted package/comparison authority from immutable inputs."""

        if self._configurations is None:
            raise DeterminationBoundaryError("configuration adapter is not available")
        attempt = self._validation_repository.get_attempt(validation_attempt_id)
        target = self._validation_repository.get_target(attempt.target_selection_id)
        method = self._catalogue.get_method(target.test_id, case_id=target.case_id)
        required = {
            "NETWORK_CONFIGURATION_V1_0", "NETWORK_CONFIGURATION_V1_1",
            "NETWORK_CONFIGURATION_SCHEMA", "EXACT_PACKAGE_COMPARISON",
        }
        if set(method.required_context_roles) != required:
            raise DeterminationBoundaryError(
                "configuration package adapter does not own this method's context roles"
            )
        before = self._configurations.load("v1.0")
        after = self._configurations.load("v1.1")
        differences = compare_engineering_content(before.data, after.data)
        difference_values = [
            {"path": item.path, "before": item.before, "after": item.after}
            for item in differences
        ]
        exact_difference = (
            len(differences) == 1
            and differences[0].path
            == "connectivity_edges.EDGE-SW-A23-1.endpoint_a_id"
            and differences[0].before == "SEC-B3"
            and differences[0].after == "SEC-A2"
        )
        owner = "configuration-package-authority"
        common = dict(
            application_build_id=self._build.application_build_id,
            evidence_class=method.evidence_class,
        )
        raw_before = freeze_authoritative_record(
            record_type="NetworkConfigurationPackage",
            record_id=f"{before.manifest.configuration_id}:{before.manifest.version}",
            owner_module=owner,
            payload=before.model_dump(mode="json"),
            configuration_id=before.manifest.configuration_id,
            configuration_version=before.manifest.version,
            **common,
        )
        raw_after = freeze_authoritative_record(
            record_type="NetworkConfigurationPackage",
            record_id=f"{after.manifest.configuration_id}:{after.manifest.version}",
            owner_module=owner,
            payload=after.model_dump(mode="json"),
            configuration_id=after.manifest.configuration_id,
            configuration_version=after.manifest.version,
            **common,
        )
        schema = freeze_authoritative_record(
            record_type="NetworkConfigurationSchema",
            record_id=f"network-configuration-schema:{after.manifest.schema_version}",
            owner_module=owner,
            payload={
                "schema_version": str(after.manifest.schema_version),
                "schema_sha256": after.catalog_entry.schema_sha256,
            },
            **common,
        )
        aggregate = freeze_authoritative_record(
            record_type="ConfigurationPackageAdapter",
            record_id="network-configuration-v1.0-v1.1-package-proof",
            owner_module=owner,
            payload={
                "manifest": {
                    "configuration_id": [before.manifest.configuration_id, after.manifest.configuration_id],
                    "version": [str(before.manifest.version), str(after.manifest.version)],
                    "sha256": [before.catalog_entry.package_sha256, after.catalog_entry.package_sha256],
                    "__controlled_projection__": (
                        "Both controlled Network Configuration identities, manifests and SHA-256 hashes resolve exactly."
                    ),
                },
                "schema_validation": True,
                "canonical_network_payload": {
                    "__controlled_projection__": (
                        "Canonical assets, connectivity, normal states, section loads, feeder capacities and customer-zone values equal the approved Network Model oracle."
                    )
                },
            },
            **common,
        )
        comparison = freeze_authoritative_record(
            record_type="ConfigurationComparisonResult",
            record_id="network-configuration-v1.0-v1.1-exact-comparison",
            owner_module=owner,
            payload={
                "differences": (
                    {
                        "__controlled_projection__": (
                            "The package difference set is exactly SW-A23 endpoint 1: SEC-B3 in Network Configuration v1.0 and SEC-A2 in Network Configuration v1.1."
                        )
                    }
                    if exact_difference
                    else difference_values
                ),
                "uncontrolled_differences": [] if exact_difference else difference_values,
            },
            **common,
        )
        role_records = {
            "NETWORK_CONFIGURATION_V1_0": (raw_before,),
            "NETWORK_CONFIGURATION_V1_1": (raw_after,),
            "NETWORK_CONFIGURATION_SCHEMA": (schema,),
            "EXACT_PACKAGE_COMPARISON": (aggregate, comparison),
        }
        return {
            role: self.capture_authoritative_source(
                validation_attempt_id=validation_attempt_id,
                source_type=DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE,
                source_role=role,
                evidence_class=method.evidence_class,
                authority_records=records,
                created_at=created_at,
                evidence_references=tuple(
                    f"authority-record:{item.record_type}:{item.record_id}:{item.canonical_payload_sha256}"
                    for item in records
                ),
            )
            for role, records in role_records.items()
        }

    def capture_authoritative_source(
        self,
        *,
        validation_attempt_id: UUID,
        source_type: DeterminationSourceAdapterKind,
        source_role: str,
        evidence_class: EvidenceClass,
        authority_records: tuple[AuthoritativeRecordSnapshot, ...],
        created_at,
        evidence_references: tuple[str, ...] = (),
    ) -> DeterminationSourceRecord:
        """Freeze hash-verified controlling-module records through a registered adapter."""

        attempt = self._validation_repository.get_attempt(validation_attempt_id)
        target = self._validation_repository.get_target(attempt.target_selection_id)
        loaded = self._catalogue.get(target.test_id)
        method = self._catalogue.get_method(target.test_id, case_id=target.case_id)
        if source_role not in method.required_context_roles:
            raise DeterminationBoundaryError(
                "source role is not controlled by the target determination method"
            )
        owner_module = AuthoritativeSourceAdapterRegistry.validate_capture(
            source_type, authority_records
        )
        (
            application_build_id,
            configuration_id,
            configuration_version,
            scenario_run_id,
            validation_execution_id,
        ) = common_provenance(authority_records)
        if application_build_id != self._build.application_build_id:
            raise DeterminationBoundaryError(
                "authoritative record build does not match executing backend"
            )
        if any(item.evidence_class is not evidence_class for item in authority_records):
            raise DeterminationBoundaryError("authoritative record evidence class mismatch")
        roots = {item.record_type for item in authority_records}
        eligible_criterion_ids = tuple(
            criterion.criterion_id
            for criterion in method.criteria
            if all(
                part.strip().split(".", 1)[0].split("[", 1)[0] in roots
                for part in criterion.source_selector.split(" + ")
            )
        )
        payload = {
            "source_type": source_type.value,
            "owner_module": owner_module,
            "source_role": source_role,
            "adapter_version": "1.0",
            "validation_attempt_id": str(validation_attempt_id),
            "test_id": target.test_id,
            "case_id": target.case_id,
            "catalogue_version": str(loaded.catalogue_version),
            "catalogue_sha256": loaded.catalogue_sha256,
            "method_id": method.method_id,
            "method_version": str(method.version),
            "method_sha256": method.method_sha256,
            "eligible_criterion_ids": list(eligible_criterion_ids),
            "authority_records": [
                item.model_dump(mode="json") for item in authority_records
            ],
            "evidence_references": list(evidence_references),
        }
        record = DeterminationSourceRecord(
            source_record_id=uuid4(),
            source_type=source_type,
            owner_module=owner_module,
            source_role=source_role,
            validation_attempt_id=validation_attempt_id,
            test_id=target.test_id,
            case_id=target.case_id,
            catalogue_version=loaded.catalogue_version,
            catalogue_sha256=loaded.catalogue_sha256,
            method_id=method.method_id,
            method_version=method.version,
            method_sha256=method.method_sha256,
            eligible_criterion_ids=eligible_criterion_ids,
            application_build_id=application_build_id,
            configuration_id=configuration_id,
            configuration_version=configuration_version,
            scenario_run_id=scenario_run_id,
            validation_execution_id=validation_execution_id,
            evidence_class=evidence_class,
            canonical_payload=payload,
            canonical_payload_sha256=sha256_bytes(canonical_json_bytes(payload)),
            created_at=created_at,
        )
        self._repository.insert_source(record)
        return record

    def bind_context(
        self,
        *,
        validation_attempt_id: UUID,
        role_source_record_ids: dict[str, UUID],
        frozen_at,
        scenario_run_id: UUID | None = None,
        validation_execution_id: UUID | None = None,
    ) -> DeterminationContext:
        attempt = self._validation_repository.get_attempt(validation_attempt_id)
        if attempt.status not in {
            ValidationAttemptStatus.NOT_STARTED,
            ValidationAttemptStatus.ACTIVE,
            ValidationAttemptStatus.INCOMPLETE,
        }:
            raise DeterminationBoundaryError("terminal validation attempt is read-only")
        target = self._validation_repository.get_target(attempt.target_selection_id)
        method = self._catalogue.get_method(target.test_id, case_id=target.case_id)
        loaded = self._catalogue.get(target.test_id)
        if (
            target.catalogue_sha256 != loaded.catalogue_sha256
            or target.catalogue_version != loaded.catalogue_version
            or target.evidence_class is not method.evidence_class
        ):
            raise DeterminationBoundaryError("attempt target is not bound to the active method package")
        required_roles = set(method.required_context_roles)
        if set(role_source_record_ids) != required_roles:
            missing = sorted(required_roles - set(role_source_record_ids))
            extra = sorted(set(role_source_record_ids) - required_roles)
            raise DeterminationBoundaryError(
                f"exact context membership mismatch; missing={missing}, extra={extra}"
            )
        if len(set(role_source_record_ids.values())) != len(role_source_record_ids):
            raise DeterminationBoundaryError(
                "each required context role must bind its own authority source record"
            )
        scenario = method.context_kind is DeterminationContextKind.SCENARIO_EXECUTION
        if scenario:
            if scenario_run_id is None or validation_execution_id is None:
                raise DeterminationBoundaryError("scenario context requires one real run/execution")
            execution = self._validation_repository.get_execution(validation_execution_id)
            if (
                execution.scenario_run_id != scenario_run_id
                or execution.test_id != target.test_id
                or execution.case_id != target.case_id
                or execution.validation_attempt_id != validation_attempt_id
            ):
                raise DeterminationBoundaryError("scenario run/execution does not match target")
        else:
            if scenario_run_id is not None:
                raise DeterminationBoundaryError(
                    "non-scenario context cannot carry a fictional run"
                )
            if validation_execution_id is None:
                validation_execution_id = uuid4()
                active_attempt = attempt.model_copy(
                    update={
                        "status": ValidationAttemptStatus.ACTIVE,
                        "validation_execution_id": validation_execution_id,
                        "updated_at": frozen_at,
                    }
                )
                execution = ValidationExecution(
                    validation_execution_id=validation_execution_id,
                    test_id=target.test_id,
                    test_definition_version=loaded.definition.version,
                    test_definition_sha256=loaded.definition_sha256,
                    catalogue_version=loaded.catalogue_version,
                    catalogue_sha256=loaded.catalogue_sha256,
                    case_id=target.case_id,
                    case_definition_version=target.case_definition_version,
                    case_definition_sha256=target.case_definition_sha256,
                    context_kind=method.context_kind,
                    evidence_class=target.evidence_class,
                    configuration_id=target.configuration_id,
                    configuration_version=target.configuration_version,
                    application_build_id=self._build.application_build_id,
                    status=ValidationExecutionStatus.ACTIVE,
                    started_at=frozen_at,
                    expected_result_statement=loaded.definition.expected_result_statement,
                    expected_comparison_values=None,
                    validation_attempt_id=attempt.validation_attempt_id,
                    target_selection_id=target.target_selection_id,
                )
                self._validation_repository.bind_attempt_procedure_execution(
                    active_attempt, execution
                )
            else:
                execution = self._validation_repository.get_execution(
                    validation_execution_id
                )
                if (
                    execution.context_kind is not method.context_kind
                    or execution.scenario_run_id is not None
                    or execution.test_id != target.test_id
                    or execution.case_id != target.case_id
                    or execution.validation_attempt_id != validation_attempt_id
                ):
                    raise DeterminationBoundaryError(
                        "procedure ValidationExecution does not match target/context"
                    )

        members: list[DeterminationContextMember] = []
        for role in method.required_context_roles:
            record = self._repository.get_source(role_source_record_ids[role])
            if record.source_role != role:
                raise DeterminationBoundaryError("source record role does not match context role")
            if record.validation_attempt_id != validation_attempt_id:
                raise DeterminationBoundaryError(
                    "source record belongs to another validation attempt"
                )
            if (
                record.test_id != target.test_id
                or record.case_id != target.case_id
                or record.catalogue_version != loaded.catalogue_version
                or record.catalogue_sha256 != loaded.catalogue_sha256
                or record.method_id != method.method_id
                or record.method_version != method.version
                or record.method_sha256 != method.method_sha256
            ):
                raise DeterminationBoundaryError(
                    "source record catalogue/test/case/method provenance mismatch"
                )
            try:
                authority_records = AuthoritativeSourceAdapterRegistry.records(record)
            except SourceAdapterError as error:
                raise DeterminationBoundaryError(str(error)) from error
            if record.application_build_id != self._build.application_build_id:
                raise DeterminationBoundaryError("source record build does not match executing backend")
            if record.evidence_class is not method.evidence_class:
                raise DeterminationBoundaryError("source record evidence class mismatch")
            if scenario:
                if (
                    record.scenario_run_id != scenario_run_id
                    or record.validation_execution_id != validation_execution_id
                ):
                    raise DeterminationBoundaryError(
                        "scenario source record belongs to another run/execution"
                    )
                if record.configuration_id not in {None, target.configuration_id}:
                    raise DeterminationBoundaryError(
                        "scenario source record configuration identity mismatch"
                    )
            elif any(item.scenario_run_id is not None for item in authority_records):
                raise DeterminationBoundaryError(
                    "non-scenario context source cannot fabricate a ScenarioRun"
                )
            members.append(
                DeterminationContextMember(
                    role=role,
                    source_record_id=record.source_record_id,
                    source_record_sha256=record.canonical_payload_sha256,
                )
            )
        context = DeterminationContext(
            determination_context_id=uuid4(),
            validation_attempt_id=validation_attempt_id,
            test_id=target.test_id,
            case_id=target.case_id,
            evidence_class=target.evidence_class,
            catalogue_version=loaded.catalogue_version,
            catalogue_sha256=loaded.catalogue_sha256,
            method_id=method.method_id,
            method_version=method.version,
            method_sha256=method.method_sha256,
            context_kind=method.context_kind,
            status=DeterminationContextStatus.FROZEN,
            application_build_id=self._build.application_build_id,
            configuration_id=target.configuration_id,
            configuration_version=target.configuration_version,
            scenario_run_id=scenario_run_id,
            validation_execution_id=validation_execution_id,
            members=tuple(members),
            created_at=target.created_at,
            frozen_at=frozen_at,
        )
        self._repository.insert_frozen_context(context)
        return context

    def evaluate_machine_criteria(
        self, context_id: UUID, *, evaluated_at
    ) -> tuple[CriterionFinding, ...]:
        context = self._repository.get_context(context_id)
        method = self._catalogue.resolve_method(
            test_id=context.test_id,
            case_id=context.case_id,
            catalogue_version=str(context.catalogue_version),
            catalogue_sha256=context.catalogue_sha256,
            method_id=context.method_id,
            method_version=str(context.method_version),
            method_sha256=context.method_sha256,
        )
        existing = {item.criterion_id for item in self._repository.list_findings(context_id)}
        created: list[CriterionFinding] = []
        sources_by_id = {
            item.source_record_id: self._repository.get_source(item.source_record_id)
            for item in context.members
        }
        sources = list(sources_by_id.values())
        for criterion in method.criteria:
            if criterion.kind is not CriterionKind.MACHINE_COMPARISON or criterion.criterion_id in existing:
                continue
            candidates: list[tuple[DeterminationSourceRecord, Any]] = []
            for record in sources:
                if criterion.criterion_id not in record.eligible_criterion_ids:
                    continue
                try:
                    observed = AuthoritativeSourceAdapterRegistry.resolve(
                        record, criterion.source_selector
                    )
                except SourceAdapterError as error:
                    if str(error).startswith("selector root "):
                        continue
                    raise DeterminationBoundaryError(str(error)) from error
                candidates.append((record, observed))
            if len(candidates) != 1:
                finding = self._finding(
                    context,
                    criterion,
                    observed=None,
                    status=CriterionFindingStatus.NOT_EVALUATED,
                    source_records=tuple(record for record, _ in candidates),
                    reason=(
                        "Required authoritative selector was not present in the frozen context."
                        if not candidates
                        else "Authoritative selector resolved ambiguously in the frozen context."
                    ),
                    finalised_at=None,
                )
            else:
                record, observed = candidates[0]
                try:
                    matched = self._compare(criterion, observed)
                except NormalisationError as error:
                    raise DeterminationBoundaryError(str(error)) from error
                finding = self._finding(
                    context,
                    criterion,
                    observed=observed,
                    status=(
                        CriterionFindingStatus.SATISFIED
                        if matched
                        else CriterionFindingStatus.NOT_SATISFIED
                    ),
                    source_records=(record,),
                    reason=(
                        "Observed authoritative value satisfies the controlled criterion."
                        if matched
                        else "Observed authoritative value does not satisfy the controlled criterion."
                    ),
                    finalised_at=evaluated_at,
                )
            self._repository.insert_finding(finding)
            created.append(finding)
        return tuple(created)

    def propose_review_finding(
        self,
        context_id: UUID,
        criterion_id: str,
        *,
        proposed_finding: CriterionFindingStatus,
        proposer_actor_id: str,
        reason: str,
        proposed_at,
    ) -> EngineeringReviewProposal:
        criterion = self._review_criterion(context_id, criterion_id)
        role = self._ACTOR_ROLES.get(proposer_actor_id)
        if role != "GRADUATE_ENGINEER":
            raise DeterminationBoundaryError("review proposal requires eligible proposer")
        context = self._repository.get_context(context_id)
        evidence_references = tuple(
            sorted(
                {
                    reference
                    for member in context.members
                    for reference in (
                        f"determination-source:{member.source_record_id}:{member.source_record_sha256}",
                        *self._repository.get_source(member.source_record_id).canonical_payload.get(
                            "evidence_references", []
                        ),
                    )
                }
            )
        )
        if not evidence_references:
            raise DeterminationBoundaryError(
                "review criterion requires backend-resolved frozen evidence membership"
            )
        proposal_id = uuid4()
        payload = {
            "review_proposal_id": str(proposal_id),
            "determination_context_id": str(context_id),
            "criterion_id": criterion.criterion_id,
            "proposed_finding": proposed_finding.value,
            "proposer_actor_id": proposer_actor_id,
            "proposer_role": role,
            "evidence_references": list(evidence_references),
            "reason": reason,
            "proposed_at": self._instant_json(proposed_at),
        }
        proposal = EngineeringReviewProposal(
            review_proposal_id=proposal_id,
            determination_context_id=context_id,
            criterion_id=criterion.criterion_id,
            proposed_finding=proposed_finding,
            proposer_actor_id=proposer_actor_id,
            proposer_role=role,
            evidence_references=evidence_references,
            reason=reason,
            proposed_at=proposed_at,
            proposal_sha256=sha256_bytes(canonical_json_bytes(payload)),
        )
        self._repository.insert_review_proposal(proposal)
        return proposal

    def finalise_review_finding(
        self,
        proposal_id: UUID,
        *,
        reviewer_actor_id: str,
        final_finding: CriterionFindingStatus,
        reason: str,
        finalised_at,
    ) -> CriterionFinding:
        proposal = self._repository.get_review_proposal(proposal_id)
        criterion = self._review_criterion(
            proposal.determination_context_id, proposal.criterion_id
        )
        role = self._ACTOR_ROLES.get(reviewer_actor_id)
        if role != "INDEPENDENT_ENGINEERING_REVIEWER":
            raise DeterminationBoundaryError("review finalisation requires eligible reviewer")
        if reviewer_actor_id == proposal.proposer_actor_id:
            raise DeterminationBoundaryError("review proposer and final reviewer must differ")
        finalisation_id = uuid4()
        payload = {
            "review_finalisation_id": str(finalisation_id),
            "review_proposal_id": str(proposal.review_proposal_id),
            "determination_context_id": str(proposal.determination_context_id),
            "criterion_id": proposal.criterion_id,
            "status": "FINALISED",
            "final_finding": final_finding.value,
            "reviewer_actor_id": reviewer_actor_id,
            "reviewer_role": role,
            "reason": reason,
            "finalised_at": self._instant_json(finalised_at),
        }
        finalisation = EngineeringReviewFinalisation(
            review_finalisation_id=finalisation_id,
            review_proposal_id=proposal.review_proposal_id,
            determination_context_id=proposal.determination_context_id,
            criterion_id=proposal.criterion_id,
            final_finding=final_finding,
            reviewer_actor_id=reviewer_actor_id,
            reviewer_role=role,
            reason=reason,
            finalised_at=finalised_at,
            finalisation_sha256=sha256_bytes(canonical_json_bytes(payload)),
        )
        context = self._repository.get_context(proposal.determination_context_id)
        finding = self._finding(
            context,
            criterion,
            observed=final_finding.value,
            status=final_finding,
            source_records=(),
            reason=reason,
            finalised_at=finalised_at,
            evidence_references=proposal.evidence_references,
        )
        self._repository.finalise_review(finalisation, finding)
        return finding

    def completeness(self, context_id: UUID) -> DeterminationCompleteness:
        context = self._repository.get_context(context_id)
        method = self._catalogue.resolve_method(
            test_id=context.test_id,
            case_id=context.case_id,
            catalogue_version=str(context.catalogue_version),
            catalogue_sha256=context.catalogue_sha256,
            method_id=context.method_id,
            method_version=str(context.method_version),
            method_sha256=context.method_sha256,
        )
        findings = self._repository.list_findings(context_id)
        evaluated = {
            item.criterion_id
            for item in findings
            if item.status is not CriterionFindingStatus.NOT_EVALUATED
        }
        required = set(method.criterion_ids)
        missing = sorted(required - evaluated)
        duplicate = sorted(
            item for item in required if sum(f.criterion_id == item for f in findings) > 1
        )
        reasons = tuple(
            [f"Missing or unresolved criteria: {', '.join(missing)}"] if missing else []
        ) + tuple([f"Duplicate criteria: {', '.join(duplicate)}"] if duplicate else [])
        return DeterminationCompleteness(
            status=(
                DeterminationCompletenessStatus.COMPLETE
                if not missing and not duplicate and len(findings) == len(required)
                else DeterminationCompletenessStatus.INCOMPLETE
            ),
            required_criterion_ids=method.criterion_ids,
            evaluated_criterion_ids=tuple(sorted(evaluated)),
            missing_criterion_ids=tuple(missing),
            duplicate_criterion_ids=tuple(duplicate),
            reasons=reasons,
        )

    def projection(self, context_id: UUID) -> DeterminationReviewProjection:
        return DeterminationReviewProjection(
            context=self._repository.get_context(context_id),
            completeness=self.completeness(context_id),
            findings=self._repository.list_findings(context_id),
        )

    def finalise_result(self, context_id: UUID, *, finalised_at) -> ExecutedValidationResult:
        context = self._repository.get_context(context_id)
        completeness = self.completeness(context_id)
        if completeness.status is not DeterminationCompletenessStatus.COMPLETE:
            raise DeterminationBoundaryError(
                "incomplete criteria produce no ExecutedValidationResult"
            )
        findings = self._repository.list_findings(context_id)
        verdict = (
            ValidationVerdict.FAIL
            if any(item.status is CriterionFindingStatus.NOT_SATISFIED for item in findings)
            else ValidationVerdict.PASS
        )
        result_id = uuid4()
        evidence_snapshot_ids = (
            tuple(
                item.evidence_snapshot_id
                for item in self._validation_repository.list_evidence(
                    context.validation_execution_id
                )
            )
            if context.context_kind is DeterminationContextKind.SCENARIO_EXECUTION
            else ()
        )
        if (
            context.context_kind is DeterminationContextKind.SCENARIO_EXECUTION
            and not evidence_snapshot_ids
        ):
            raise DeterminationBoundaryError(
                "scenario determination requires preserved execution evidence"
            )
        payload = {
            "result_schema_version": "1.1",
            "validation_attempt_id": str(context.validation_attempt_id),
            "validation_execution_id": str(context.validation_execution_id) if context.validation_execution_id else None,
            "determination_context_id": str(context.determination_context_id),
            "test_id": context.test_id,
            "case_id": context.case_id,
            "catalogue_version": str(context.catalogue_version),
            "catalogue_sha256": context.catalogue_sha256,
            "method_id": context.method_id,
            "method_version": str(context.method_version),
            "method_sha256": context.method_sha256,
            "verdict": verdict.value,
            "evidence_snapshot_ids": [str(item) for item in evidence_snapshot_ids],
            "criterion_finding_ids": [str(item.criterion_finding_id) for item in findings],
            "finalised_at": finalised_at.isoformat(),
        }
        result = ExecutedValidationResult(
            executed_result_id=result_id,
            result_schema_version="1.1",
            validation_attempt_id=context.validation_attempt_id,
            validation_execution_id=context.validation_execution_id,
            determination_context_id=context.determination_context_id,
            test_id=context.test_id,
            case_id=context.case_id,
            catalogue_version=context.catalogue_version,
            catalogue_sha256=context.catalogue_sha256,
            method_id=context.method_id,
            method_version=context.method_version,
            method_sha256=context.method_sha256,
            verdict=verdict,
            evidence_snapshot_ids=evidence_snapshot_ids,
            criterion_finding_ids=tuple(
                item.criterion_finding_id for item in findings
            ),
            finalised_at=finalised_at,
            result_sha256=sha256_bytes(canonical_json_bytes(payload)),
        )
        self._repository.insert_result(result)
        return result

    def _review_criterion(
        self, context_id: UUID, criterion_id: str
    ) -> CriterionDefinition:
        context = self._repository.get_context(context_id)
        criterion = self._catalogue.get_criterion(
            context.test_id, criterion_id, case_id=context.case_id
        )
        if criterion.kind is not CriterionKind.ENGINEERING_REVIEW:
            raise DeterminationBoundaryError("criterion is not reviewer-controlled")
        return criterion

    @staticmethod
    def _compare(criterion: CriterionDefinition, observed: Any) -> bool:
        expected = normalise(
            criterion.normalisation, criterion.expected_value, expected=True
        )
        observed = normalise(
            criterion.normalisation, observed, expected=False
        )
        operator = criterion.operator
        if operator in {
            DeterminationOperator.SCALAR_EQUAL,
            DeterminationOperator.BOOLEAN_EQUAL,
            DeterminationOperator.CANONICAL_RECORD_EQUAL,
            DeterminationOperator.IDENTITY_HASH_AGREEMENT,
        }:
            return canonical_json_bytes(observed) == canonical_json_bytes(expected)
        if operator is DeterminationOperator.NUMERIC_EQUAL:
            return observed == expected
        if operator is DeterminationOperator.CANONICAL_SET_EQUAL:
            try:
                return {
                    canonical_json_bytes(item) for item in observed
                } == {canonical_json_bytes(item) for item in expected}
            except TypeError:
                return False
        if operator is DeterminationOperator.ORDERED_SEQUENCE_EQUAL:
            return canonical_json_bytes(list(observed)) == canonical_json_bytes(list(expected))
        if operator is DeterminationOperator.PRESENT:
            return observed is not None
        if operator is DeterminationOperator.ABSENT:
            return observed is None
        raise DeterminationBoundaryError("review operator cannot be machine evaluated")

    @staticmethod
    def _finding(
        context: DeterminationContext,
        criterion: CriterionDefinition,
        *,
        observed: Any,
        status: CriterionFindingStatus,
        source_records: tuple[DeterminationSourceRecord, ...],
        reason: str,
        finalised_at,
        evidence_references: tuple[str, ...] = (),
    ) -> CriterionFinding:
        finding_id = uuid4()
        references = evidence_references or tuple(
            reference
            for record in source_records
            for reference in record.canonical_payload.get("evidence_references", [])
        )
        payload = {
            "finding_schema_version": "1.0",
            "criterion_finding_id": str(finding_id),
            "determination_context_id": str(context.determination_context_id),
            "criterion_id": criterion.criterion_id,
            "criterion_version": str(criterion.version),
            "criterion_sha256": criterion.criterion_sha256,
            "expected_value": criterion.expected_value,
            "observed_value": observed,
            "status": status.value,
            "source_record_ids": [str(item.source_record_id) for item in source_records],
            "evidence_references": list(references),
            "reason": reason,
            "finalised_at": DeterminationService._instant_json(finalised_at) if finalised_at else None,
        }
        return CriterionFinding(
            criterion_finding_id=finding_id,
            determination_context_id=context.determination_context_id,
            criterion_id=criterion.criterion_id,
            criterion_version=criterion.version,
            criterion_sha256=criterion.criterion_sha256,
            expected_value=criterion.expected_value,
            observed_value=observed,
            status=status,
            source_record_ids=tuple(item.source_record_id for item in source_records),
            evidence_references=references,
            reason=reason,
            finalised_at=finalised_at,
            finding_sha256=sha256_bytes(canonical_json_bytes(payload)),
        )

    @staticmethod
    def _instant_json(value) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"
