"""I5 controlled execution, capture, comparison and evidence-query service."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from ...application.scenario_coordinator import ScenarioCoordinator
from ...domain.enums import (
    EvidenceClass,
    ValidationExecutionStatus,
    ValidationVerdict,
)
from ...infrastructure.build_identity import ApplicationBuildManifest
from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ...infrastructure.validation_repository import (
    ValidationRecordConflict,
    ValidationRepository,
)
from ..scenario.models import ScenarioSnapshot
from .catalogue import ValidationCatalogueLoader
from .models import (
    EvidenceSnapshot,
    LoadedValidationDefinition,
    ValidationExecution,
    ValidationExecutionLinks,
    ValidationExecutionSummary,
)


class ValidationBoundaryError(ValueError):
    """Raised when a request crosses the accepted I5 control boundary."""


class ValidationService:
    def __init__(
        self,
        repository: ValidationRepository,
        catalogue: ValidationCatalogueLoader,
        scenarios: ScenarioCoordinator,
        *,
        application_build_manifest: ApplicationBuildManifest,
    ) -> None:
        self._repository = repository
        self._catalogue = catalogue
        self._scenarios = scenarios
        self._application_build_manifest = application_build_manifest

    def start_execution(
        self,
        test_id: str,
        scenario_run_id: UUID,
        *,
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
        self._verify_links(loaded_definition, links)
        execution = ValidationExecution(
            validation_execution_id=uuid4(),
            test_id=test_id,
            test_definition_version=loaded_definition.definition.version,
            test_definition_sha256=loaded_definition.definition_sha256,
            catalogue_sha256=loaded_definition.catalogue_sha256,
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
                loaded_definition.definition.comparison_expected_values
            ),
            links=links,
        )
        self._repository.insert_execution(execution)
        return execution

    def capture_checkpoint(
        self,
        execution_id: UUID,
        checkpoint_id: str,
    ) -> EvidenceSnapshot:
        execution = self._repository.get_execution(execution_id)
        if execution.status is not ValidationExecutionStatus.ACTIVE:
            raise ValidationBoundaryError("finalised execution evidence cannot be replaced")
        definition = self._bound_definition(execution)
        obligation = next(
            (
                item
                for item in definition.definition.checkpoint_obligations
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
        definition = self._bound_definition(execution)
        expected = definition.definition.comparison_expected_values
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
            for item in definition.definition.checkpoint_obligations
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
            }
        )
        self._repository.finalise_execution(finalised)
        return finalised

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

    def _bound_definition(
        self, execution: ValidationExecution
    ) -> LoadedValidationDefinition:
        loaded = self._catalogue.get(execution.test_id)
        if (
            loaded.definition.version != execution.test_definition_version
            or loaded.definition_sha256 != execution.test_definition_sha256
            or loaded.catalogue_sha256 != execution.catalogue_sha256
        ):
            raise ValidationBoundaryError(
                "current catalogue identity differs from the execution-bound definition"
            )
        return loaded

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

    @staticmethod
    def _observed_values(snapshot: ScenarioSnapshot) -> dict[str, Any]:
        return {
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
            comparisons.append(
                {
                    "field": ".".join(path),
                    "expected": expected_value,
                    "observed": observed_value,
                    "match": observed_value == expected_value,
                }
            )
        return comparisons

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
