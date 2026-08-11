"""I5 controlled execution, capture, comparison and evidence-query service."""

from __future__ import annotations

from typing import Any
from pathlib import Path
from uuid import UUID, uuid4

from ...application.scenario_coordinator import ScenarioCoordinator
from ...domain.enums import (
    CompositeConstituentSourceKind,
    CompositeCompletenessStatus,
    CompositeResultStatus,
    EvidenceClass,
    ScenarioCommandType,
    ScenarioMode,
    SwitchState,
    ValidationExecutionStatus,
    ValidationAttemptStatus,
    ValidationSuspensionCondition,
    SuspensionAuthorityKind,
    SuspensionLifecyclePosition,
    SuspensionRecordStatus,
    SuspensionEvaluationType,
    RequiredInputRole,
    ValidationVerdict,
)
from ...infrastructure.build_identity import ApplicationBuildManifest
from ...infrastructure.configuration_loader import JsonConfigurationLoader
from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ...infrastructure.validation_repository import (
    ValidationRecordConflict,
    ValidationRecordNotFound,
    ValidationRepository,
)
from ..scenario.models import ScenarioSnapshot
from .catalogue import (
    ValidationCatalogueError,
    ValidationCatalogueLoader,
    ValidationCatalogueResolver,
)
from .models import (
    CompositeCompleteness,
    CompositeConstituentLink,
    CompositeValidationResult,
    EvidenceSnapshot,
    ConstituentCaseDefinition,
    LoadedValidationDefinition,
    ValidationExecution,
    ValidationExecutionLinks,
    ValidationExecutionSummary,
    ValidationAttempt,
    ValidationTargetSelection,
    ExecutedValidationResult,
    ValidationSuspensionEvidence,
    ValidationSuspensionAuthority,
    ValidationSuspensionRecord,
)
from .assurance import (
    AssuranceAuthorityError,
    ControlledArtifact,
    ControlledEngineeringRegistry,
    IdentityResolutionAuthority,
    IntegrityVerificationAuthority,
    RuntimeTimeAuthority,
)


class ValidationBoundaryError(ValueError):
    """Raised when a request crosses the accepted I5 control boundary."""


class ValidationService:
    _ACTOR_ROLES = {
        "graduate-engineer": "GRADUATE_ENGINEER",
        "independent-reviewer": "INDEPENDENT_ENGINEERING_REVIEWER",
        "backend-integrity-monitor": "BACKEND_ASSURANCE_PROPOSER",
        "backend-assurance-reviewer": "BACKEND_ASSURANCE_REVIEWER",
    }
    def __init__(
        self,
        repository: ValidationRepository,
        catalogue: ValidationCatalogueResolver | ValidationCatalogueLoader,
        scenarios: ScenarioCoordinator,
        configurations: JsonConfigurationLoader | None = None,
        *,
        application_build_manifest: ApplicationBuildManifest,
        engineering_registry: ControlledEngineeringRegistry | None = None,
        identity_authority: IdentityResolutionAuthority | None = None,
        integrity_authority: IntegrityVerificationAuthority | None = None,
        time_authority: RuntimeTimeAuthority | None = None,
    ) -> None:
        self._repository = repository
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
        self._scenarios = scenarios
        self._configurations = configurations or JsonConfigurationLoader(
            Path(__file__).resolve().parents[5] / "config/network"
        )
        self._application_build_manifest = application_build_manifest
        root = Path(__file__).resolve().parents[5]
        self._engineering_registry = engineering_registry or ControlledEngineeringRegistry.load(
            root / "validation/assurance/engineering-records.json", root
        )
        self._identity_authority = identity_authority or IdentityResolutionAuthority()
        if integrity_authority is None:
            active = self._catalogue.get("VT-EXP-ALL-001")
            integrity_authority = IntegrityVerificationAuthority((ControlledArtifact(
                artifact_reference="active-validation-catalogue",
                path=root / "validation/test-definitions/catalogue.json",
                expected_sha256=active.catalogue_sha256,
            ),))
        self._integrity_authority = integrity_authority
        self._time_authority = time_authority or RuntimeTimeAuthority()

    def start_execution(
        self,
        test_id: str,
        scenario_run_id: UUID,
        *,
        case_id: str | None = None,
        links: ValidationExecutionLinks = ValidationExecutionLinks(),
    ) -> ValidationExecution:
        loaded_definition = self._catalogue.get(test_id)
        snapshot = self._scenarios.snapshot(scenario_run_id)
        run = snapshot.run
        self._verify_backend_provenance(run.application_build_id)
        if run.evidence_class is not loaded_definition.definition.evidence_class:
            raise ValidationBoundaryError(
                "scenario evidence class does not match the controlled test definition"
            )
        case = self._select_case(loaded_definition, case_id)
        if case is not None:
            self._verify_case_run_boundary(case, snapshot)
            if self._repository.list_summaries(scenario_run_id=scenario_run_id):
                raise ValidationBoundaryError(
                    "a constituent scenario run may bind to only one validation execution"
                )
        self._verify_links(loaded_definition, links)
        target, attempt = self.create_target_selection(
            test_id,
            case_id=case_id,
            created_at=run.scenario_time,
            configuration_version=str(run.configuration_version),
        )
        execution_id = uuid4()
        active_attempt = attempt.model_copy(
            update={
                "status": ValidationAttemptStatus.ACTIVE,
                "scenario_run_id": scenario_run_id,
                "validation_execution_id": execution_id,
                "updated_at": run.scenario_time,
            }
        )
        execution = ValidationExecution(
            validation_execution_id=execution_id,
            test_id=test_id,
            test_definition_version=loaded_definition.definition.version,
            test_definition_sha256=loaded_definition.definition_sha256,
            catalogue_version=loaded_definition.catalogue_version,
            catalogue_sha256=loaded_definition.catalogue_sha256,
            case_id=case.case_id if case is not None else None,
            case_definition_version=case.version if case is not None else None,
            case_definition_sha256=(
                self._case_sha256(case) if case is not None else None
            ),
            scenario_run_id=scenario_run_id,
            scenario_mode=run.mode,
            evidence_class=run.evidence_class,
            configuration_id=run.configuration_id,
            configuration_version=run.configuration_version,
            application_build_id=self._application_build_manifest.application_build_id,
            status=ValidationExecutionStatus.ACTIVE,
            started_scenario_time=run.scenario_time,
            expected_result_statement=(
                loaded_definition.definition.expected_result_statement
            ),
            expected_comparison_values=(
                case.comparison_expected_values
                if case is not None
                else loaded_definition.definition.comparison_expected_values
            ),
            links=links,
            validation_attempt_id=attempt.validation_attempt_id,
            target_selection_id=target.target_selection_id,
        )
        self._repository.bind_attempt_execution(active_attempt, execution)
        return execution

    def create_target_selection(
        self,
        test_id: str,
        *,
        case_id: str | None = None,
        created_at,
        actor_id: str = "graduate-engineer",
        configuration_version: str = "1.1",
        requested_fixture_identity: str | None = "network-one-line.v1",
        required_input_role: RequiredInputRole | None = None,
        presented_identity_evidence: dict[str, Any] | None = None,
    ) -> tuple[ValidationTargetSelection, ValidationAttempt]:
        role = self._ACTOR_ROLES.get(actor_id)
        if role is None:
            raise ValidationBoundaryError("target selection actor is outside the local role registry")
        loaded = self._catalogue.get(test_id)
        case = self._select_case(loaded, case_id)
        configuration = self._configurations.load(f"v{configuration_version}").catalog_entry
        intended_identities = {
            RequiredInputRole.APPLICATION_BUILD.value: {
                "application_build_id": self._application_build_manifest.application_build_id,
            },
            RequiredInputRole.CONFIGURATION.value: {
                "configuration_id": configuration.configuration_id,
                "configuration_version": str(configuration.version),
            },
            RequiredInputRole.CATALOGUE.value: {
                "catalogue_version": str(loaded.catalogue_version),
                "catalogue_sha256": loaded.catalogue_sha256,
            },
            RequiredInputRole.TEST_DEFINITION.value: {
                "test_definition_version": str(loaded.definition.version),
                "test_definition_sha256": loaded.definition_sha256,
            },
            RequiredInputRole.CASE_DEFINITION.value: (
                {
                    "case_definition_version": str(case.version),
                    "case_definition_sha256": self._case_sha256(case),
                }
                if case else {"not_applicable": "true"}
            ),
            RequiredInputRole.CONTROLLED_FIXTURE.value: {
                "fixture_id": "network-one-line.v1",
            },
        }
        requested_identities = {
            key: dict(value) for key, value in intended_identities.items()
        }
        if required_input_role is RequiredInputRole.CASE_DEFINITION and case is None:
            raise ValidationBoundaryError("CASE_DEFINITION is not a required input for an unbound test")
        if requested_fixture_identity != "network-one-line.v1":
            required_input_role = RequiredInputRole.CONTROLLED_FIXTURE
            presented_identity_evidence = {"fixture_id": requested_fixture_identity}
        if required_input_role is not None:
            requested_identities[required_input_role.value] = dict(
                presented_identity_evidence or {}
            )
        unresolved_role = None
        if required_input_role is not None:
            resolution = self._identity_authority.evaluate_evidence(
                required_input_role,
                requested_identities[required_input_role.value],
                intended_identities[required_input_role.value],
            )
            if resolution is not None:
                unresolved_role = required_input_role
        resolved_identities = {
            key: dict(value)
            for key, value in intended_identities.items()
            if unresolved_role is None or key != unresolved_role.value
        }
        target_selection_id = uuid4()
        selection_payload = {
            "target_selection_id": str(target_selection_id),
            "test_id": test_id,
            "case_id": case.case_id if case else None,
            "requested_catalogue_version": requested_identities[RequiredInputRole.CATALOGUE.value].get("catalogue_version"),
            "requested_catalogue_sha256": requested_identities[RequiredInputRole.CATALOGUE.value].get("catalogue_sha256"),
            "requested_test_definition_version": requested_identities[RequiredInputRole.TEST_DEFINITION.value].get("test_definition_version"),
            "requested_test_definition_sha256": requested_identities[RequiredInputRole.TEST_DEFINITION.value].get("test_definition_sha256"),
            "requested_case_definition_sha256": requested_identities[RequiredInputRole.CASE_DEFINITION.value].get("case_definition_sha256"),
            "requested_configuration_id": requested_identities[RequiredInputRole.CONFIGURATION.value].get("configuration_id"),
            "requested_configuration_version": requested_identities[RequiredInputRole.CONFIGURATION.value].get("configuration_version"),
            "requested_application_build_id": requested_identities[RequiredInputRole.APPLICATION_BUILD.value].get("application_build_id"),
            "requested_fixture_identity": requested_identities[
                RequiredInputRole.CONTROLLED_FIXTURE.value
            ].get("fixture_id"),
            "required_input_role": required_input_role.value if required_input_role else None,
            "unresolved_required_role": unresolved_role.value if unresolved_role else None,
            "intended_identity_evidence": intended_identities,
            "requested_identity_evidence": requested_identities,
            "resolved_identity_evidence": resolved_identities,
            "assurance_verifier_application_build_id": self._application_build_manifest.application_build_id,
            "evidence_class": loaded.definition.evidence_class.value,
            "selection_authority_actor_id": actor_id,
            "selection_authority_role": role,
        }
        target = ValidationTargetSelection(
            target_selection_id=target_selection_id,
            test_id=test_id,
            case_id=case.case_id if case else None,
            test_definition_version=(None if unresolved_role is RequiredInputRole.TEST_DEFINITION else loaded.definition.version),
            test_definition_sha256=(None if unresolved_role is RequiredInputRole.TEST_DEFINITION else loaded.definition_sha256),
            catalogue_version=(None if unresolved_role is RequiredInputRole.CATALOGUE else loaded.catalogue_version),
            catalogue_sha256=(None if unresolved_role is RequiredInputRole.CATALOGUE else loaded.catalogue_sha256),
            case_definition_version=(None if unresolved_role is RequiredInputRole.CASE_DEFINITION else case.version if case else None),
            case_definition_sha256=(None if unresolved_role is RequiredInputRole.CASE_DEFINITION else self._case_sha256(case) if case else None),
            evidence_class=loaded.definition.evidence_class,
            configuration_id=(None if unresolved_role is RequiredInputRole.CONFIGURATION else configuration.configuration_id),
            configuration_version=(None if unresolved_role is RequiredInputRole.CONFIGURATION else configuration.version),
            target_application_build_id=(None if unresolved_role is RequiredInputRole.APPLICATION_BUILD else self._application_build_manifest.application_build_id),
            unresolved_required_role=unresolved_role,
            intended_identity_evidence=intended_identities,
            requested_identity_evidence=requested_identities,
            resolved_identity_evidence=resolved_identities,
            assurance_verifier_application_build_id=self._application_build_manifest.application_build_id,
            canonical_selection_payload=selection_payload,
            canonical_selection_sha256=sha256_bytes(canonical_json_bytes(selection_payload)),
            selected_by_actor_id=actor_id,
            selected_by_role=role,
            created_at=created_at,
        )
        attempt = ValidationAttempt(
            validation_attempt_id=uuid4(),
            target_selection_id=target.target_selection_id,
            status=ValidationAttemptStatus.NOT_STARTED,
            created_at=created_at,
            updated_at=created_at,
        )
        self._repository.insert_target_and_attempt(target, attempt)
        return target, attempt

    def capture_checkpoint(
        self,
        execution_id: UUID,
        checkpoint_id: str,
    ) -> EvidenceSnapshot:
        execution = self._repository.get_execution(execution_id)
        if execution.status is not ValidationExecutionStatus.ACTIVE:
            raise ValidationBoundaryError("finalised execution evidence cannot be replaced")
        if execution.validation_attempt_id is not None and self._repository.get_attempt(
            execution.validation_attempt_id
        ).status is not ValidationAttemptStatus.ACTIVE:
            raise ValidationBoundaryError("suspended/incomplete validation attempt cannot capture execution evidence")
        definition = self._bound_definition(execution)
        obligations = self._checkpoint_obligations(definition, execution.case_id)
        obligation = next(
            (
                item
                for item in obligations
                if item.checkpoint_id == checkpoint_id
            ),
            None,
        )
        if obligation is None:
            raise ValidationBoundaryError(
                f"checkpoint {checkpoint_id} is not defined for {execution.test_id}"
            )
        snapshot = self._scenarios.snapshot(execution.scenario_run_id)
        self._verify_snapshot_binding(execution, snapshot)
        observed_values = self._observed_values(snapshot)
        source_references = self._source_record_references(snapshot)
        payload = {
            "validation_execution_id": str(execution.validation_execution_id),
            "test_id": execution.test_id,
            "test_definition_version": execution.test_definition_version,
            "test_definition_sha256": execution.test_definition_sha256,
            "catalogue_version": execution.catalogue_version,
            "catalogue_sha256": execution.catalogue_sha256,
            "case_id": execution.case_id,
            "case_definition_version": execution.case_definition_version,
            "case_definition_sha256": execution.case_definition_sha256,
            "application_build_id": execution.application_build_id,
            "configuration_id": execution.configuration_id,
            "configuration_version": execution.configuration_version,
            "scenario_run_id": str(execution.scenario_run_id),
            "scenario_mode": execution.scenario_mode.value,
            "evidence_class": execution.evidence_class.value,
            "checkpoint_id": checkpoint_id,
            "scenario_snapshot": snapshot.model_dump(mode="json"),
            "observed_values": observed_values,
            "source_record_references": list(source_references),
        }
        evidence = EvidenceSnapshot(
            evidence_snapshot_id=uuid4(),
            validation_execution_id=execution.validation_execution_id,
            test_id=execution.test_id,
            catalogue_version=execution.catalogue_version,
            catalogue_sha256=execution.catalogue_sha256,
            test_definition_version=execution.test_definition_version,
            test_definition_sha256=execution.test_definition_sha256,
            case_id=execution.case_id,
            case_definition_version=execution.case_definition_version,
            case_definition_sha256=execution.case_definition_sha256,
            scenario_run_id=execution.scenario_run_id,
            scenario_mode=execution.scenario_mode,
            evidence_class=execution.evidence_class,
            configuration_id=execution.configuration_id,
            configuration_version=execution.configuration_version,
            application_build_id=execution.application_build_id,
            state_revision=snapshot.run.state_revision,
            checkpoint_id=checkpoint_id,
            scenario_time=snapshot.run.scenario_time,
            captured_scenario_time=snapshot.run.scenario_time,
            content_categories=obligation.required_content,
            source_record_references=source_references,
            observed_values=observed_values,
            canonical_payload=payload,
            canonical_payload_sha256=sha256_bytes(canonical_json_bytes(payload)),
        )
        try:
            self._repository.insert_evidence(evidence)
        except ValidationRecordConflict as error:
            raise ValidationBoundaryError(str(error)) from error
        return evidence

    def finalise_execution(
        self,
        execution_id: UUID,
        checkpoint_id: str,
    ) -> ValidationExecution:
        execution = self._repository.get_execution(execution_id)
        if execution.status is not ValidationExecutionStatus.ACTIVE:
            raise ValidationBoundaryError("validation execution is already finalised")
        if execution.validation_attempt_id is not None and self._repository.get_attempt(
            execution.validation_attempt_id
        ).status is not ValidationAttemptStatus.ACTIVE:
            raise ValidationBoundaryError("suspended/incomplete validation attempt cannot create an executed result")
        definition = self._bound_definition(execution)
        case = self._bound_case(definition, execution)
        expected = (
            case.comparison_expected_values
            if case is not None
            else definition.definition.comparison_expected_values
        )
        if expected is None:
            raise ValidationBoundaryError(
                "this controlled definition has no I5 automated comparison; "
                "do not invent a verdict"
            )
        evidence = self._repository.get_evidence(execution_id, checkpoint_id)
        all_evidence = self._repository.list_evidence(execution_id)
        captured_checkpoint_ids = {item.checkpoint_id for item in all_evidence}
        required_checkpoint_ids = {
            item.checkpoint_id
            for item in self._checkpoint_obligations(definition, execution.case_id)
        }
        missing = sorted(required_checkpoint_ids - captured_checkpoint_ids)
        if missing:
            raise ValidationBoundaryError(
                f"required evidence checkpoints are missing: {missing}"
            )
        comparisons = self._compare_expected(expected, evidence.observed_values)
        passed = all(item["match"] for item in comparisons)
        verdict = ValidationVerdict.PASS if passed else ValidationVerdict.FAIL
        calculations = {
            "comparison_method": "CONTROLLED_EXPECTED_VALUE_EQUALITY",
            "comparisons": comparisons,
        }
        result_id = uuid4()
        finalised = execution.model_copy(
            update={
                "status": ValidationExecutionStatus.FINALISED,
                "finalised_scenario_time": evidence.scenario_time,
                "observed_result": evidence.observed_values,
                "calculations": calculations,
                "evidence_snapshot_ids": tuple(
                    item.evidence_snapshot_id for item in all_evidence
                ),
                "verdict": verdict,
                "verdict_reason": (
                    "Preserved observed values agree with the controlled expected values."
                    if passed
                    else "Preserved observed values differ from the controlled expected values."
                ),
                "executed_result_id": result_id,
            }
        )
        if execution.validation_attempt_id is None:
            self._repository.finalise_execution(finalised)
            return finalised
        attempt = self._repository.get_attempt(execution.validation_attempt_id)
        executed_payload = {
            "validation_attempt_id": str(attempt.validation_attempt_id),
            "validation_execution_id": str(execution.validation_execution_id),
            "verdict": verdict.value,
            "evidence_snapshot_ids": [str(item.evidence_snapshot_id) for item in all_evidence],
            "finalised_at": evidence.scenario_time.isoformat(),
        }
        result = ExecutedValidationResult(
            executed_result_id=result_id,
            validation_attempt_id=attempt.validation_attempt_id,
            validation_execution_id=execution.validation_execution_id,
            verdict=verdict,
            evidence_snapshot_ids=tuple(item.evidence_snapshot_id for item in all_evidence),
            result_sha256=sha256_bytes(canonical_json_bytes(executed_payload)),
            finalised_at=evidence.scenario_time,
        )
        completed_attempt = attempt.model_copy(
            update={"status": ValidationAttemptStatus.EXECUTED, "updated_at": evidence.scenario_time}
        )
        self._repository.finalise_execution_result(finalised, completed_attempt, result)
        return finalised

    def evaluate_suspension(
        self,
        attempt_id: UUID,
        *,
        trusted_target_selection_id: UUID,
        evaluation_type: SuspensionEvaluationType,
        lifecycle_position: SuspensionLifecyclePosition,
        reference_id: str,
        field_id: str | None,
        source_assertion_ids: tuple[str, ...],
        proposer_actor_id: str | None,
        reviewer_actor_id: str | None,
        finalised_at,
        scenario_run_id: UUID | None = None,
        validation_execution_id: UUID | None = None,
    ) -> ValidationSuspensionRecord:
        attempt = self._repository.get_attempt(attempt_id)
        target = self._repository.get_target(attempt.target_selection_id)
        if trusted_target_selection_id != target.target_selection_id:
            raise ValidationBoundaryError("suspension evaluation is not bound to the trusted target selection")
        if attempt.status in {ValidationAttemptStatus.EXECUTED, ValidationAttemptStatus.SUSPENDED}:
            raise ValidationBoundaryError("completed validation attempt cannot be suspended")
        try:
            if evaluation_type is SuspensionEvaluationType.ENGINEERING_BEHAVIOUR:
                condition = ValidationSuspensionCondition.VSC_001
                failure_code = "UNSPECIFIED_ENGINEERING_BEHAVIOUR"
                evidence_payload = self._engineering_registry.verify_design_question(
                    target, reference_id, field_id or "", source_assertion_ids
                )
                authority_kind = SuspensionAuthorityKind.ENGINEERING_REVIEW
            elif evaluation_type is SuspensionEvaluationType.BASELINE_CONFLICT:
                condition = ValidationSuspensionCondition.VSC_002
                failure_code = "INCONSISTENT_BASELINE"
                evidence_payload = self._engineering_registry.verify_conflict(
                    target, reference_id, field_id or "", source_assertion_ids
                )
                authority_kind = SuspensionAuthorityKind.ENGINEERING_REVIEW
            elif evaluation_type is SuspensionEvaluationType.IDENTITY_RESOLUTION:
                condition = ValidationSuspensionCondition.VSC_003
                result = self._identity_authority.evaluate(target, reference_id)
                if result is None:
                    raise AssuranceAuthorityError("required identity resolves uniquely")
                failure_code, evidence_payload = result
                authority_kind = SuspensionAuthorityKind.BACKEND_ASSURANCE
            elif evaluation_type is SuspensionEvaluationType.INTEGRITY:
                condition = ValidationSuspensionCondition.VSC_005
                result = self._integrity_authority.evaluate(reference_id)
                if result is None:
                    raise AssuranceAuthorityError("controlled artefact passed integrity verification")
                failure_code, evidence_payload = result
                authority_kind = SuspensionAuthorityKind.BACKEND_ASSURANCE
            else:
                condition = ValidationSuspensionCondition.VSC_004
                failure_code = "UNCONTROLLED_WALL_CLOCK_DEPENDENCY"
                if lifecycle_position is SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY:
                    evidence_payload = self._engineering_registry.verify_preentry_time(
                        target, reference_id, field_id or "", source_assertion_ids
                    )
                    authority_kind = SuspensionAuthorityKind.ENGINEERING_REVIEW
                else:
                    result = self._time_authority.evaluate(
                        lifecycle_position, reference_id,
                        str(validation_execution_id) if validation_execution_id else None,
                    )
                    if result is None:
                        raise AssuranceAuthorityError("controlled runtime time verification passed")
                    failure_code, evidence_payload = result
                    authority_kind = SuspensionAuthorityKind.BACKEND_ASSURANCE
        except AssuranceAuthorityError as error:
            raise ValidationBoundaryError(str(error)) from error
        if authority_kind is SuspensionAuthorityKind.BACKEND_ASSURANCE:
            if proposer_actor_id is not None or reviewer_actor_id is not None:
                raise ValidationBoundaryError("caller cannot supply backend assurance actor identities")
            proposer_actor_id, reviewer_actor_id = "backend-integrity-monitor", "backend-assurance-reviewer"
        if proposer_actor_id is None or reviewer_actor_id is None:
            raise ValidationBoundaryError("engineering suspension requires proposer and reviewer identities")
        proposer_role = self._ACTOR_ROLES.get(proposer_actor_id)
        reviewer_role = self._ACTOR_ROLES.get(reviewer_actor_id)
        if proposer_actor_id == reviewer_actor_id or proposer_role is None or reviewer_role is None:
            raise ValidationBoundaryError("invalid suspension authority actors")
        if authority_kind is SuspensionAuthorityKind.ENGINEERING_REVIEW and (
            proposer_role != "GRADUATE_ENGINEER" or reviewer_role != "INDEPENDENT_ENGINEERING_REVIEWER"
        ):
            raise ValidationBoundaryError("engineering suspension requires independent reviewer authority")
        authority = ValidationSuspensionAuthority(
            authority_kind=authority_kind,
            proposer_actor_id=proposer_actor_id,
            proposer_role=proposer_role,
            reviewer_actor_id=reviewer_actor_id,
            reviewer_role=reviewer_role,
        )
        lifecycle = lifecycle_position
        if lifecycle is SuspensionLifecyclePosition.PRE_EXECUTION_ENTRY:
            scenario_run_id = None
            validation_execution_id = None
        else:
            if scenario_run_id != attempt.scenario_run_id:
                raise ValidationBoundaryError("suspension must bind the attempt's actual run")
            if validation_execution_id != attempt.validation_execution_id:
                raise ValidationBoundaryError("suspension must bind the attempt's actual execution")
        condition_evidence = evidence_payload
        evidence_payload = {
            "target_selection_id": str(target.target_selection_id),
            "condition_id": condition.value,
            "failure_code": failure_code,
            "evidence": condition_evidence,
        }
        evidence = ValidationSuspensionEvidence(
            evidence_id=uuid4(),
            condition_id=condition,
            evidence_type=f"{condition.value}_CONDITION_EVIDENCE",
            failure_code=failure_code,
            payload=evidence_payload,
            payload_sha256=sha256_bytes(canonical_json_bytes(evidence_payload)),
        )
        reason_code = f"BLOCKED-TEST/{condition.value}/{lifecycle.value}"
        evaluated_gates = (
            "TRUSTED_TARGET_SELECTION_PRESENT",
            "INTEGRITY_GATE_EVALUATED",
            "IDENTITY_RESOLUTION_GATE_EVALUATED",
            "BASELINE_CONFLICT_GATE_EVALUATED",
            "CONTROLLING_BEHAVIOUR_GATE_EVALUATED",
            "CONTROLLED_TIME_GATE_EVALUATED",
        )
        resolved_identities = {
            "catalogue_version": str(target.catalogue_version),
            "catalogue_sha256": target.catalogue_sha256,
            "test_definition_version": str(target.test_definition_version),
            "test_definition_sha256": target.test_definition_sha256,
            "case_definition_version": str(target.case_definition_version) if target.case_definition_version else None,
            "case_definition_sha256": target.case_definition_sha256,
            "configuration_id": target.configuration_id,
            "configuration_version": str(target.configuration_version),
        }
        failed_role = condition_evidence.get("input_name") if condition is ValidationSuspensionCondition.VSC_003 else None
        presented_identity = condition_evidence.get("presented_identity_evidence", {})
        reason_parameters = {
            "condition_id": condition.value,
            "failure_code": failure_code,
            "lifecycle_position": lifecycle.value,
            "failed_required_input_role": failed_role,
        }
        fingerprint_payload = {
            "target": target.model_dump(mode="json"),
            "classifier_version": "1.0",
            "evaluated_gates": list(evaluated_gates),
            "condition_id": condition.value,
            "lifecycle_position": lifecycle.value,
            "reason_code": reason_code,
            "evidence_sha256": evidence.payload_sha256,
            "evidence_ids": [str(evidence.evidence_id)],
            "evidence_contract_version": "1.0",
            "reason_parameters": reason_parameters,
            "authority": authority.model_dump(mode="json"),
            "verifier_application_build_id": self._application_build_manifest.application_build_id,
            "scenario_run_id": str(scenario_run_id) if scenario_run_id else None,
            "validation_execution_id": str(validation_execution_id) if validation_execution_id else None,
        }
        record = ValidationSuspensionRecord(
            suspension_record_id=uuid4(),
            validation_attempt_id=attempt.validation_attempt_id,
            target_selection_id=target.target_selection_id,
            condition_id=condition,
            lifecycle_position=lifecycle,
            status=SuspensionRecordStatus.FINALISED,
            reason_code=reason_code,
            deterministic_fingerprint=sha256_bytes(canonical_json_bytes(fingerprint_payload)),
            verifier_application_build_id=self._application_build_manifest.application_build_id,
            evaluated_classifier_gates=evaluated_gates,
            target_selection_sha256=target.canonical_selection_sha256,
            intended_test_id=target.test_id,
            intended_case_id=target.case_id,
            resolved_source_identities=resolved_identities,
            failed_required_input_role=failed_role,
            presented_identity_evidence=presented_identity,
            inherited_evidence_class=target.evidence_class,
            reason_parameters=reason_parameters,
            rendered_reason=(
                f"Validation attempt suspended under {condition.value} at {lifecycle.value}; "
                f"controlled failure code {failure_code}."
            ),
            evidence=(evidence,),
            authority=authority,
            scenario_run_id=scenario_run_id,
            validation_execution_id=validation_execution_id,
            created_at=attempt.created_at,
            finalised_at=finalised_at,
        )
        suspended = attempt.model_copy(
            update={"status": ValidationAttemptStatus.SUSPENDED, "updated_at": finalised_at}
        )
        try:
            self._repository.insert_finalised_suspension(suspended, record)
        except ValidationRecordConflict as error:
            raise ValidationBoundaryError(str(error)) from error
        return record

    def enter_attempt(
        self, attempt_id: UUID, scenario_run_id: UUID, *, entered_at
    ) -> ValidationAttempt:
        attempt = self._repository.get_attempt(attempt_id)
        target = self._repository.get_target(attempt.target_selection_id)
        run = self._scenarios.run_context(scenario_run_id)
        if (
            run.evidence_class is not target.evidence_class
            or run.configuration_id != target.configuration_id
            or run.configuration_version != target.configuration_version
            or run.application_build_id != target.target_application_build_id
            or (target.case_id is not None and run.fault_section_id != self._select_case(
                self._catalogue.get(target.test_id), target.case_id
            ).selected_fault_section_id)
        ):
            raise ValidationBoundaryError("scenario entry does not match the trusted target selection")
        entered = attempt.model_copy(
            update={
                "status": ValidationAttemptStatus.INCOMPLETE,
                "scenario_run_id": scenario_run_id,
                "updated_at": entered_at,
            }
        )
        self._repository.bind_attempt_run(entered)
        return entered

    def get_suspension(self, record_id: UUID) -> ValidationSuspensionRecord:
        return self._repository.get_suspension(record_id)

    def list_suspensions(self) -> tuple[ValidationSuspensionRecord, ...]:
        return self._repository.list_suspensions()

    def get_execution(self, execution_id: UUID) -> ValidationExecutionSummary:
        return self._repository.summary(execution_id)

    def list_executions(
        self,
        *,
        test_id: str | None = None,
        evidence_class: EvidenceClass | None = None,
        scenario_run_id: UUID | None = None,
    ) -> tuple[ValidationExecutionSummary, ...]:
        return self._repository.list_summaries(
            test_id=test_id,
            evidence_class=evidence_class,
            scenario_run_id=scenario_run_id,
        )

    def assemble_composite(
        self,
        test_id: str,
        execution_ids: tuple[UUID, ...],
        *,
        created_at,
        suspension_record_ids: tuple[UUID, ...] = (),
    ) -> CompositeValidationResult:
        if len(execution_ids) != len(set(execution_ids)):
            raise ValidationBoundaryError(
                "one constituent execution cannot be supplied more than once"
            )
        if len(suspension_record_ids) != len(set(suspension_record_ids)):
            raise ValidationBoundaryError(
                "one suspension result cannot be supplied more than once"
            )
        definition = self._catalogue.get(test_id)
        cases = definition.definition.constituent_cases
        if not cases:
            raise ValidationBoundaryError(
                "the controlled test definition has no composite constituent set"
            )
        if definition.definition.evidence_class is not EvidenceClass.EXPLORATORY:
            raise ValidationBoundaryError("DC-004 composites are EXPLORATORY only")

        required_case_ids = tuple(item.case_id for item in cases)
        case_by_id = {item.case_id: item for item in cases}
        summaries = tuple(self._repository.summary(item) for item in execution_ids)
        suspensions = tuple(
            self._repository.get_suspension(item) for item in suspension_record_ids
        )
        corrected = self._configurations.load("v1.1").catalog_entry
        suspension_targets = tuple(
            self._repository.get_target(item.target_selection_id) for item in suspensions
        )
        seen_case_ids = [item.execution.case_id for item in summaries] + [
            item.case_id for item in suspension_targets
        ]
        duplicates = tuple(
            sorted(
                case_id
                for case_id in set(seen_case_ids)
                if case_id is not None and seen_case_ids.count(case_id) > 1
            )
        )
        if duplicates:
            raise ValidationBoundaryError(
                f"duplicate constituent case membership is not permitted: {duplicates}"
            )

        links: list[CompositeConstituentLink] = []
        unfinished: list[str] = []
        mismatched: list[str] = []
        common_configuration_id = None
        common_configuration_version = None
        common_build_id = None
        for summary in summaries:
            execution = summary.execution
            case_id = execution.case_id
            if case_id is None or case_id not in case_by_id:
                raise ValidationBoundaryError(
                    f"execution is not bound to one required constituent case: {case_id}"
                )
            case = case_by_id[case_id]
            expected_case_sha = self._case_sha256(case)
            provenance = (
                execution.test_id == test_id
                and execution.test_definition_version == definition.definition.version
                and execution.test_definition_sha256 == definition.definition_sha256
                and execution.catalogue_version == definition.catalogue_version
                and execution.catalogue_sha256 == definition.catalogue_sha256
                and execution.case_definition_version == case.version
                and execution.case_definition_sha256 == expected_case_sha
                and execution.application_build_id
                == self._application_build_manifest.application_build_id
                and str(execution.configuration_version) == "1.1"
                and execution.configuration_id == corrected.configuration_id
                and execution.scenario_mode is ScenarioMode.EXPLORATION
                and execution.evidence_class is EvidenceClass.EXPLORATORY
            )
            if not provenance:
                raise ValidationBoundaryError(
                    f"constituent provenance does not satisfy DC-004: {case_id}"
                )
            if common_configuration_id is None:
                common_configuration_id = execution.configuration_id
                common_configuration_version = execution.configuration_version
                common_build_id = execution.application_build_id
            elif execution.configuration_id != common_configuration_id:
                raise ValidationBoundaryError(
                    "constituents do not share one corrected configuration identity"
                )
            run = self._scenarios.run_context(execution.scenario_run_id)
            if (
                run.scenario_run_id != execution.scenario_run_id
                or run.mode is not ScenarioMode.EXPLORATION
                or run.evidence_class is not EvidenceClass.EXPLORATORY
                or run.configuration_id != execution.configuration_id
                or run.configuration_version != execution.configuration_version
                or run.application_build_id != execution.application_build_id
                or run.fault_section_id != case.selected_fault_section_id
            ):
                raise ValidationBoundaryError(
                    f"constituent execution/run binding is inconsistent: {case_id}"
                )
            for evidence in summary.evidence_snapshots:
                if (
                    evidence.validation_execution_id
                    != execution.validation_execution_id
                    or evidence.scenario_run_id != execution.scenario_run_id
                    or evidence.case_id != case_id
                    or evidence.case_definition_sha256 != expected_case_sha
                ):
                    raise ValidationBoundaryError(
                        f"constituent evidence binding is inconsistent: {case_id}"
                    )
            if execution.status is not ValidationExecutionStatus.FINALISED:
                unfinished.append(case_id)
                continue
            elif execution.verdict not in {
                ValidationVerdict.PASS,
                ValidationVerdict.FAIL,
            }:
                raise ValidationBoundaryError(
                    f"constituent verdict is outside the aggregate rule: {case_id}"
                )
            result = self._verified_executed_result(execution, summary.evidence_snapshots)
            links.append(
                CompositeConstituentLink(
                    link_schema_version="1.1",
                    case_id=case_id,
                    source_kind=CompositeConstituentSourceKind.EXECUTION_RESULT,
                    validation_execution_id=execution.validation_execution_id,
                    executed_result_id=result.executed_result_id,
                    scenario_run_id=execution.scenario_run_id,
                    case_definition_sha256=expected_case_sha,
                    constituent_verdict=execution.verdict,
                    evidence_snapshot_ids=execution.evidence_snapshot_ids,
                )
            )

        for record, target in zip(suspensions, suspension_targets, strict=True):
            case_id = target.case_id
            if case_id is None or case_id not in case_by_id:
                raise ValidationBoundaryError(
                    f"suspension is not bound to one required constituent case: {case_id}"
                )
            case = case_by_id[case_id]
            expected_case_sha = self._case_sha256(case)
            attempt = self._repository.get_attempt(record.validation_attempt_id)
            unavailable_role = (
                target.unresolved_required_role
                if record.condition_id is ValidationSuspensionCondition.VSC_003
                and record.failed_required_input_role == (
                    target.unresolved_required_role.value
                    if target.unresolved_required_role else None
                )
                else None
            )
            if target.unresolved_required_role is not None and unavailable_role is None:
                raise ValidationBoundaryError("only a verified VSC-003 role may omit target provenance")
            intended = target.intended_identity_evidence
            intended_matches = (
                intended[RequiredInputRole.CATALOGUE.value]
                == {"catalogue_version": str(definition.catalogue_version), "catalogue_sha256": definition.catalogue_sha256}
                and intended[RequiredInputRole.TEST_DEFINITION.value]
                == {"test_definition_version": str(definition.definition.version), "test_definition_sha256": definition.definition_sha256}
                and intended[RequiredInputRole.CASE_DEFINITION.value]
                == {"case_definition_version": str(case.version), "case_definition_sha256": expected_case_sha}
                and intended[RequiredInputRole.CONFIGURATION.value]
                == {"configuration_id": corrected.configuration_id, "configuration_version": "1.1"}
                and intended[RequiredInputRole.APPLICATION_BUILD.value]
                == {"application_build_id": self._application_build_manifest.application_build_id}
            )
            if (
                record.status is not SuspensionRecordStatus.FINALISED
                or attempt.status is not ValidationAttemptStatus.SUSPENDED
                or record.target_selection_id != target.target_selection_id
                or target.test_id != test_id
                or not intended_matches
                or (unavailable_role is not RequiredInputRole.TEST_DEFINITION and (
                    target.test_definition_version != definition.definition.version
                    or target.test_definition_sha256 != definition.definition_sha256))
                or (unavailable_role is not RequiredInputRole.CATALOGUE and (
                    target.catalogue_version != definition.catalogue_version
                    or target.catalogue_sha256 != definition.catalogue_sha256))
                or (unavailable_role is not RequiredInputRole.CASE_DEFINITION and target.case_definition_sha256 != expected_case_sha)
                or target.evidence_class is not EvidenceClass.EXPLORATORY
                or (unavailable_role is not RequiredInputRole.CONFIGURATION and (
                    str(target.configuration_version) != "1.1"
                    or target.configuration_id != corrected.configuration_id))
                or (unavailable_role is not RequiredInputRole.APPLICATION_BUILD and target.target_application_build_id
                    != self._application_build_manifest.application_build_id)
                or target.assurance_verifier_application_build_id
                    != self._application_build_manifest.application_build_id
                or record.verifier_application_build_id
                != self._application_build_manifest.application_build_id
            ):
                raise ValidationBoundaryError(
                    f"suspension provenance does not satisfy DC-004/DC-005: {case_id}"
                )
            if target.configuration_id is not None:
                if common_configuration_id is None:
                    common_configuration_id = target.configuration_id
                    common_configuration_version = target.configuration_version
                elif target.configuration_id != common_configuration_id or target.configuration_version != common_configuration_version:
                    raise ValidationBoundaryError("constituent suspension configuration provenance differs")
            if target.target_application_build_id is not None:
                if common_build_id is None:
                    common_build_id = target.target_application_build_id
                elif target.target_application_build_id != common_build_id:
                    raise ValidationBoundaryError("constituent suspension build provenance differs")
            links.append(
                CompositeConstituentLink(
                    link_schema_version="1.1",
                    case_id=case_id,
                    source_kind=CompositeConstituentSourceKind.SUSPENSION_RESULT,
                    suspension_record_id=record.suspension_record_id,
                    scenario_run_id=record.scenario_run_id,
                    case_definition_sha256=(None if unavailable_role is RequiredInputRole.CASE_DEFINITION else expected_case_sha),
                    unavailable_required_input_role=unavailable_role,
                    constituent_verdict=ValidationVerdict.BLOCKED_TEST,
                    evidence_snapshot_ids=(),
                )
            )

        present_case_ids = tuple(sorted(item.case_id for item in links))
        missing_case_ids = tuple(
            item for item in required_case_ids if item not in present_case_ids
        )
        complete = not (missing_case_ids or unfinished or mismatched)
        reasons: list[str] = []
        if missing_case_ids:
            reasons.append(f"Missing required cases: {list(missing_case_ids)}")
        if unfinished:
            reasons.append(f"Unfinished constituent cases: {sorted(unfinished)}")
        if mismatched:
            reasons.append(f"Mismatched constituent cases: {sorted(mismatched)}")
        if complete:
            reasons.append("Exact required case set and constituent provenance are complete.")
        completeness = CompositeCompleteness(
            status=(
                CompositeCompletenessStatus.COMPLETE
                if complete
                else CompositeCompletenessStatus.INCOMPLETE
            ),
            required_case_ids=required_case_ids,
            present_case_ids=present_case_ids,
            missing_case_ids=missing_case_ids,
            duplicate_case_ids=duplicates,
            mismatched_case_ids=tuple(sorted(mismatched)),
            reasons=tuple(reasons),
        )
        if common_configuration_id is None or common_build_id is None:
            raise ValidationBoundaryError(
                "composite assembly requires at least one preserved constituent source"
            )
        composite = CompositeValidationResult(
            composite_result_id=uuid4(),
            test_id=test_id,
            test_definition_version=definition.definition.version,
            test_definition_sha256=definition.definition_sha256,
            catalogue_version=definition.catalogue_version,
            catalogue_sha256=definition.catalogue_sha256,
            application_build_id=common_build_id,
            configuration_id=common_configuration_id,
            configuration_version=common_configuration_version,
            required_case_ids=required_case_ids,
            constituent_links=tuple(sorted(links, key=lambda item: item.case_id)),
            completeness=completeness,
            status=CompositeResultStatus.DRAFT,
            determination_reason=(
                "Composite is complete and ready for deterministic finalisation."
                if complete
                else "; ".join(reasons)
            ),
            source_record_references=tuple(
                sorted(
                    {
                        *(f"validation-execution:{item.validation_execution_id}" for item in links if item.validation_execution_id),
                        *(f"executed-result:{item.executed_result_id}" for item in links if item.executed_result_id),
                        *(f"validation-suspension:{item.suspension_record_id}" for item in links if item.suspension_record_id),
                        *(f"scenario-run:{item.scenario_run_id}" for item in links if item.scenario_run_id),
                        *(f"evidence-snapshot:{evidence_id}" for item in links for evidence_id in item.evidence_snapshot_ids),
                    }
                )
            ),
            created_at=created_at,
        )
        try:
            self._repository.insert_composite(composite)
        except ValidationRecordConflict as error:
            raise ValidationBoundaryError(str(error)) from error
        return composite

    def finalise_composite(
        self, composite_id: UUID, *, finalised_at
    ) -> CompositeValidationResult:
        composite = self._repository.get_composite(composite_id)
        if composite.status is not CompositeResultStatus.DRAFT:
            raise ValidationBoundaryError("composite validation result is already finalised")
        if composite.completeness.status is not CompositeCompletenessStatus.COMPLETE:
            raise ValidationBoundaryError(
                "incomplete composite has no aggregate validation determination"
            )
        if composite.catalogue_sha256 != self._catalogue.raw_catalogue_sha256():
            raise ValidationBoundaryError(
                "unfinished composite belongs to a historical catalogue and is read-only"
            )
        verdicts: list[ValidationVerdict] = []
        for link in composite.constituent_links:
            if link.source_kind is CompositeConstituentSourceKind.EXECUTION_RESULT:
                assert link.validation_execution_id is not None
                execution = self._repository.get_execution(link.validation_execution_id)
                result = self._verified_executed_result(
                    execution, self._repository.list_evidence(execution.validation_execution_id)
                )
                if (
                    execution.status is not ValidationExecutionStatus.FINALISED
                    or execution.case_id != link.case_id
                    or execution.scenario_run_id != link.scenario_run_id
                    or execution.case_definition_sha256 != link.case_definition_sha256
                    or execution.verdict != link.constituent_verdict
                    or execution.evidence_snapshot_ids != link.evidence_snapshot_ids
                    or result.executed_result_id != link.executed_result_id
                    or result.verdict != link.constituent_verdict
                    or execution.verdict not in {ValidationVerdict.PASS, ValidationVerdict.FAIL}
                ):
                    raise ValidationBoundaryError(
                        f"execution constituent no longer resolves immutably: {link.case_id}"
                    )
                verdicts.append(execution.verdict)
            else:
                assert link.suspension_record_id is not None
                suspension = self._repository.get_suspension(link.suspension_record_id)
                target = self._repository.get_target(suspension.target_selection_id)
                if (
                    suspension.status is not SuspensionRecordStatus.FINALISED
                    or target.case_id != link.case_id
                    or target.unresolved_required_role != link.unavailable_required_input_role
                    or (
                        link.unavailable_required_input_role is not RequiredInputRole.CASE_DEFINITION
                        and target.case_definition_sha256 != link.case_definition_sha256
                    )
                    or (
                        suspension.condition_id is ValidationSuspensionCondition.VSC_003
                        and suspension.failed_required_input_role
                        != (link.unavailable_required_input_role.value if link.unavailable_required_input_role else None)
                    )
                    or link.constituent_verdict is not ValidationVerdict.BLOCKED_TEST
                ):
                    raise ValidationBoundaryError(
                        f"suspension constituent no longer resolves immutably: {link.case_id}"
                    )
                verdicts.append(ValidationVerdict.BLOCKED_TEST)
        determination, reason = self._aggregate_verdict(tuple(verdicts))
        finalised = composite.model_copy(
            update={
                "status": CompositeResultStatus.FINALISED,
                "determination": determination,
                "determination_reason": reason,
                "finalised_at": finalised_at,
            }
        )
        self._repository.finalise_composite(finalised)
        return finalised

    def _verified_executed_result(
        self,
        execution: ValidationExecution,
        evidence_snapshots: tuple[EvidenceSnapshot, ...],
    ) -> ExecutedValidationResult:
        if execution.executed_result_id is None or execution.validation_attempt_id is None:
            raise ValidationBoundaryError("finalised execution has no immutable ExecutedValidationResult")
        try:
            result = self._repository.get_executed_result(execution.executed_result_id)
            attempt = self._repository.get_attempt(execution.validation_attempt_id)
        except (ValidationRecordNotFound, ValueError) as error:
            raise ValidationBoundaryError("immutable ExecutedValidationResult cannot be resolved or verified") from error
        evidence_ids = tuple(item.evidence_snapshot_id for item in evidence_snapshots)
        if (
            result.executed_result_id != execution.executed_result_id
            or result.validation_attempt_id != execution.validation_attempt_id
            or result.validation_execution_id != execution.validation_execution_id
            or attempt.validation_attempt_id != result.validation_attempt_id
            or attempt.validation_execution_id != execution.validation_execution_id
            or attempt.scenario_run_id != execution.scenario_run_id
            or attempt.status is not ValidationAttemptStatus.EXECUTED
            or result.verdict not in {ValidationVerdict.PASS, ValidationVerdict.FAIL}
            or result.verdict != execution.verdict
            or result.evidence_snapshot_ids != execution.evidence_snapshot_ids
            or result.evidence_snapshot_ids != evidence_ids
            or any(item.validation_execution_id != execution.validation_execution_id for item in evidence_snapshots)
            or result.result_sha256 != result.recomputed_sha256()
        ):
            raise ValidationBoundaryError("ExecutedValidationResult provenance is inconsistent")
        return result

    def get_composite(self, composite_id: UUID) -> CompositeValidationResult:
        return self._repository.get_composite(composite_id)

    def list_composites(
        self, *, test_id: str | None = None
    ) -> tuple[CompositeValidationResult, ...]:
        return self._repository.list_composites(test_id=test_id)

    @staticmethod
    def _aggregate_verdict(
        verdicts: tuple[ValidationVerdict, ...],
    ) -> tuple[ValidationVerdict, str]:
        if not verdicts or any(
            item not in {
                ValidationVerdict.PASS,
                ValidationVerdict.FAIL,
                ValidationVerdict.BLOCKED_TEST,
            }
            for item in verdicts
        ):
            raise ValidationBoundaryError(
                "aggregate determination requires a complete accepted verdict set"
            )
        if ValidationVerdict.FAIL in verdicts:
            return (
                ValidationVerdict.FAIL,
                "Complete constituent set contains at least one FAIL.",
            )
        if ValidationVerdict.BLOCKED_TEST in verdicts:
            return (
                ValidationVerdict.BLOCKED_TEST,
                "Complete constituent set has no FAIL and contains at least one "
                "evidence-supported BLOCKED-TEST; every other constituent is PASS.",
            )
        return (
            ValidationVerdict.PASS,
            "Complete constituent set contains PASS for every required case.",
        )

    def _bound_definition(
        self, execution: ValidationExecution
    ) -> LoadedValidationDefinition:
        try:
            loaded = self._catalogue.resolve(
                test_id=execution.test_id,
                catalogue_version=execution.catalogue_version,
                catalogue_sha256=execution.catalogue_sha256,
                test_definition_version=execution.test_definition_version,
                test_definition_sha256=execution.test_definition_sha256,
            )
        except ValidationCatalogueError as error:
            raise ValidationBoundaryError(str(error)) from error
        if not self._catalogue.is_active(loaded):
            raise ValidationBoundaryError(
                "unfinished execution belongs to a historical catalogue and is read-only"
            )
        return loaded

    def resolve_historical_definition(
        self, execution: ValidationExecution
    ) -> LoadedValidationDefinition:
        try:
            return self._catalogue.resolve(
                test_id=execution.test_id,
                catalogue_version=execution.catalogue_version,
                catalogue_sha256=execution.catalogue_sha256,
                test_definition_version=execution.test_definition_version,
                test_definition_sha256=execution.test_definition_sha256,
            )
        except ValidationCatalogueError as error:
            raise ValidationBoundaryError(str(error)) from error

    @staticmethod
    def _case_sha256(case: ConstituentCaseDefinition) -> str:
        return sha256_bytes(canonical_json_bytes(case.model_dump(mode="json")))

    def _select_case(
        self,
        definition: LoadedValidationDefinition,
        case_id: str | None,
    ) -> ConstituentCaseDefinition | None:
        cases = definition.definition.constituent_cases
        if cases and case_id is None:
            raise ValidationBoundaryError("this multi-run test requires one controlled case ID")
        if not cases and case_id is not None:
            raise ValidationBoundaryError("this validation definition has no constituent cases")
        if case_id is None:
            return None
        try:
            return next(item for item in cases if item.case_id == case_id)
        except StopIteration as error:
            raise ValidationBoundaryError(
                f"case {case_id} does not belong to {definition.definition.test_id}"
            ) from error

    def _bound_case(
        self,
        definition: LoadedValidationDefinition,
        execution: ValidationExecution,
    ) -> ConstituentCaseDefinition | None:
        case = self._select_case(definition, execution.case_id)
        if case is None:
            return None
        if (
            case.version != execution.case_definition_version
            or self._case_sha256(case) != execution.case_definition_sha256
        ):
            raise ValidationBoundaryError("execution-bound case-definition identity differs")
        return case

    def _checkpoint_obligations(
        self,
        definition: LoadedValidationDefinition,
        case_id: str | None,
    ):
        if case_id is None:
            return definition.definition.checkpoint_obligations
        case = self._select_case(definition, case_id)
        assert case is not None
        return case.checkpoint_obligations

    @staticmethod
    def _verify_case_run_boundary(
        case: ConstituentCaseDefinition,
        snapshot: ScenarioSnapshot,
    ) -> None:
        run = snapshot.run
        if (
            run.mode is not ScenarioMode.EXPLORATION
            or run.evidence_class is not EvidenceClass.EXPLORATORY
            or str(run.configuration_version) != "1.1"
            or run.fault_section_id != case.selected_fault_section_id
        ):
            raise ValidationBoundaryError(
                "constituent case requires its selected fault on corrected v1.1 "
                "under EXPLORATION/EXPLORATORY classification"
            )

    def _verify_backend_provenance(self, run_build_id: str) -> None:
        controlled = self._application_build_manifest.application_build_id
        if run_build_id != controlled:
            raise ValidationBoundaryError(
                "scenario run build identity does not match the backend-controlled build"
            )

    def _verify_links(
        self,
        definition: LoadedValidationDefinition,
        links: ValidationExecutionLinks,
    ) -> None:
        if links.correction_id is not None and links.defect_id is None:
            raise ValidationBoundaryError("a correction link requires its defect identity")
        if links.repeat_of_execution_id is None:
            return
        prior = self._repository.get_execution(links.repeat_of_execution_id)
        if prior.status is not ValidationExecutionStatus.FINALISED:
            raise ValidationBoundaryError("repeat link must target a finalised execution")
        if prior.test_id != definition.definition.test_id:
            raise ValidationBoundaryError("repeat link must retain the controlled test ID")
        if (
            prior.test_definition_version != definition.definition.version
            or prior.test_definition_sha256 != definition.definition_sha256
        ):
            raise ValidationBoundaryError(
                "repeat link must retain the controlled test-definition identity"
            )
        if (
            prior.application_build_id
            != self._application_build_manifest.application_build_id
        ):
            raise ValidationBoundaryError("repeat link must retain the same application build")

    def _verify_snapshot_binding(
        self,
        execution: ValidationExecution,
        snapshot: ScenarioSnapshot,
    ) -> None:
        run = snapshot.run
        self._verify_backend_provenance(run.application_build_id)
        actual = (
            run.scenario_run_id,
            run.mode,
            run.evidence_class,
            run.configuration_id,
            run.configuration_version,
            run.application_build_id,
        )
        expected = (
            execution.scenario_run_id,
            execution.scenario_mode,
            execution.evidence_class,
            execution.configuration_id,
            execution.configuration_version,
            execution.application_build_id,
        )
        if actual != expected:
            raise ValidationBoundaryError(
                "current scenario snapshot no longer matches execution provenance"
            )

    def _observed_values(self, snapshot: ScenarioSnapshot) -> dict[str, Any]:
        loaded = self._configurations.load(f"v{snapshot.run.configuration_version}")
        sections = {item.entity_id: item for item in loaded.data.sections}
        feeders = {item.entity_id: item for item in loaded.data.feeders}
        affected_feeder_id = sections[snapshot.run.fault_section_id].feeder_id
        protection_breaker_id = feeders[affected_feeder_id].source_breaker_id
        proof = snapshot.topology.isolation_proof
        open_targets = {
            item.target_entity_id
            for item in snapshot.allowed_actions
            if item.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE
            and item.requested_state is SwitchState.OPEN
            and item.available
        }
        validity_by_point_id = {
            item.point_id: item for item in snapshot.telemetry_validity
        }
        telemetry_age_by_entity_id = {
            item.entity_id: validity_by_point_id[item.point_id].age_ms
            for item in snapshot.telemetry
            if item.point_id in validity_by_point_id
        }
        boundary_evidence = (
            {
                item.boundary_device_id: {
                    "observed_value": (
                        item.observed_state.value if item.observed_state is not None else None
                    ),
                    "quality": item.quality.value if item.quality is not None else None,
                    "freshness": (
                        item.freshness_status.value
                        if item.freshness_status is not None
                        else None
                    ),
                    "age_ms": telemetry_age_by_entity_id.get(
                        item.boundary_device_id
                    ),
                    "proof_status": item.proof_status.value,
                    "open_action_eligible": item.boundary_device_id in open_targets,
                    "reason_codes": list(item.reason_codes),
                }
                for item in sorted(
                    proof.boundary_evaluations,
                    key=lambda value: value.boundary_device_id,
                )
            }
            if proof is not None
            else {}
        )
        assessment = (
            snapshot.restoration_assessments[-1]
            if snapshot.restoration_assessments
            else None
        )
        candidate = assessment.candidate if assessment is not None else None
        calculation = assessment.calculation if assessment is not None else None
        return {
            "selected_fault_section_id": snapshot.run.fault_section_id,
            "affected_feeder_id": affected_feeder_id,
            "protection_breaker_id": protection_breaker_id,
            "incident_boundary_device_ids": (
                list(sorted(proof.incident_boundary_device_ids)) if proof else []
            ),
            "boundary_evidence": boundary_evidence,
            "isolated": proof.isolated if proof is not None else False,
            "alternate_feeder_id": (
                candidate.alternate_feeder_id if candidate is not None else None
            ),
            "proposed_section_ids": (
                list(sorted(candidate.proposed_section_ids)) if candidate else []
            ),
            "transferable_load_kw": (
                candidate.transferable_load_kw if candidate is not None else None
            ),
            "resulting_load_kw": (
                calculation.resulting_load_kw if calculation is not None else None
            ),
            "feeder_capacity_kw": (
                calculation.feeder_capacity_kw if calculation is not None else None
            ),
            "resulting_loading_percent": (
                str(calculation.resulting_loading_percent)
                if calculation is not None
                else None
            ),
            "de_energised_section_ids": list(
                snapshot.outage.de_energised_section_ids
            ),
            "affected_customer_count": snapshot.outage.affected_customer_count,
            "restored_customer_delta": snapshot.outage.restored_customer_delta,
            "radiality_status": snapshot.topology.radiality_status.value,
            "section_source_feeder_ids": {
                section.section_id: list(section.source_feeder_ids)
                for section in snapshot.topology.sections
            },
            "restoration_outcome": (
                snapshot.restoration_assessments[-1].outcome.value
                if snapshot.restoration_assessments
                else None
            ),
        }

    @staticmethod
    def _source_record_references(snapshot: ScenarioSnapshot) -> tuple[str, ...]:
        run_id = snapshot.run.scenario_run_id
        revision = snapshot.run.state_revision
        references = [
            f"scenario-run:{run_id}",
            f"topology:{run_id}:revision:{revision}",
            f"outage:{run_id}:revision:{revision}",
        ]
        references.extend(f"event:{item.event_id}" for item in snapshot.events)
        references.extend(f"alarm:{item.alarm_id}" for item in snapshot.alarms)
        references.extend(
            f"restoration-assessment:{item.assessment_id}"
            for item in snapshot.restoration_assessments
        )
        return tuple(references)

    @classmethod
    def _compare_expected(
        cls,
        expected: dict[str, Any],
        observed: dict[str, Any],
    ) -> list[dict[str, Any]]:
        comparisons: list[dict[str, Any]] = []
        for path, expected_value in cls._flatten(expected):
            observed_value = cls._lookup(observed, path)
            expected_value = cls._normalise_comparison_value(path, expected_value)
            observed_value = cls._normalise_comparison_value(path, observed_value)
            comparisons.append(
                {
                    "field": ".".join(path),
                    "expected": expected_value,
                    "observed": observed_value,
                    "match": observed_value == expected_value,
                }
            )
        return comparisons

    @staticmethod
    def _normalise_comparison_value(path: tuple[str, ...], value: Any) -> Any:
        if path[-1] in {"incident_boundary_device_ids", "proposed_section_ids"} and isinstance(value, list):
            return sorted(value)
        return value

    @classmethod
    def _flatten(
        cls,
        value: dict[str, Any],
        prefix: tuple[str, ...] = (),
    ) -> list[tuple[tuple[str, ...], Any]]:
        flattened: list[tuple[tuple[str, ...], Any]] = []
        for key in sorted(value):
            item = value[key]
            path = (*prefix, key)
            if isinstance(item, dict):
                flattened.extend(cls._flatten(item, path))
            else:
                flattened.append((path, item))
        return flattened

    @staticmethod
    def _lookup(value: dict[str, Any], path: tuple[str, ...]) -> Any:
        current: Any = value
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current
