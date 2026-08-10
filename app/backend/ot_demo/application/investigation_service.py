"""I7 consequence-to-source workflow built from I1-I6 owner records."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from ..domain.enums import (
    RepeatRelationshipType,
    ScenarioCommandType,
    ScenarioMode,
    ValidationExecutionStatus,
    ValidationVerdict,
)
from ..infrastructure.build_identity import ApplicationBuildManifest
from ..infrastructure.configuration_comparison import compare_engineering_content
from ..infrastructure.configuration_loader import JsonConfigurationLoader
from ..infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ..infrastructure.investigation_repository import (
    InvestigationRecordConflict,
    InvestigationRepository,
)
from ..modules.configuration.models import LoadedConfiguration
from ..modules.investigation.models import (
    ConfigurationComparisonView,
    ConfigurationDifferenceView,
    ConfigurationPackageIdentity,
    CorrectionRecord,
    DefectRecord,
    InvestigationAction,
    InvestigationFact,
    InvestigationStep,
    InvestigationWorkspace,
    RepeatLink,
)
from ..modules.scenario.definition import formal_action_offset_seconds
from ..modules.scenario.models import (
    AllowedAction,
    InitialiseRunRequest,
    ScenarioCommandRequest,
    ScenarioSnapshot,
)
from ..modules.validation.models import ValidationExecutionLinks, ValidationExecutionSummary
from ..modules.validation.service import ValidationService
from .scenario_coordinator import ScenarioCoordinator


class InvestigationBoundaryError(ValueError):
    """Raised when a request crosses the approved I7 workflow boundary."""


class InvestigationService:
    DEFECT_ID = "DEF-001"
    CORRECTION_ID = "COR-001"
    DIRECT_TEST_ID = "VT-TOP-DEF-001"
    REGRESSION_TEST_ID = "VT-FML-N0-N5-001"
    REVIEW_STEP_IDS = tuple(f"INV-{number:02d}" for number in range(1, 8))
    FORMAL_EPOCH = datetime(2030, 1, 1, tzinfo=timezone.utc)
    NOTICE = (
        "Controlled fictional engineering investigation. Defect and correction "
        "judgements are separate from SCADA telemetry, operational events and "
        "validation verdicts; no configuration is editable here."
    )

    def __init__(
        self,
        repository: InvestigationRepository,
        configurations: JsonConfigurationLoader,
        scenarios: ScenarioCoordinator,
        validation: ValidationService,
        *,
        application_build_manifest: ApplicationBuildManifest,
    ) -> None:
        self._repository = repository
        self._configurations = configurations
        self._scenarios = scenarios
        self._validation = validation
        self._application_build_manifest = application_build_manifest

    def start_failure(self, actor: str) -> InvestigationWorkspace:
        initial = self._initialise_controlled_run("1.0", actor, self.FORMAL_EPOCH)
        execution = self._validation.start_execution(
            self.DIRECT_TEST_ID,
            initial.run.scenario_run_id,
            links=ValidationExecutionLinks(defect_id=self.DEFECT_ID),
        )
        self._execute_available(
            initial.run.scenario_run_id,
            actor,
            ScenarioCommandType.INITIATE_FAULT,
        )
        self._validation.capture_checkpoint(
            execution.validation_execution_id, "POST_TRIP"
        )
        finalised = self._validation.finalise_execution(
            execution.validation_execution_id, "POST_TRIP"
        )
        if finalised.verdict is not ValidationVerdict.FAIL:
            raise InvestigationBoundaryError(
                "the controlled v1.0 consequence did not produce the accepted failed execution"
            )
        return self.workspace(finalised.validation_execution_id)

    def workspace(self, failure_execution_id: UUID) -> InvestigationWorkspace:
        failure = self._failure(failure_execution_id)
        steps, comparison = self._investigation_projection(failure)
        defect = self._repository.get_defect(self.DEFECT_ID)
        if defect is not None and defect.original_failed_execution_id != failure_execution_id:
            raise InvestigationBoundaryError(
                "DEF-001 is already bound to a different preserved failed execution"
            )
        correction = self._repository.get_correction(self.CORRECTION_ID)
        links = (
            self._repository.list_repeat_links(defect.defect_record_id)
            if defect is not None
            else ()
        )
        direct_link = next(
            (item for item in links if item.relationship_type is RepeatRelationshipType.DIRECT_REPEAT),
            None,
        )
        regression_link = next(
            (item for item in links if item.relationship_type is RepeatRelationshipType.REGRESSION),
            None,
        )
        direct = (
            self._validation.get_execution(direct_link.new_execution_id)
            if direct_link is not None
            else None
        )
        regression = (
            self._validation.get_execution(regression_link.new_execution_id)
            if regression_link is not None
            else None
        )
        same_build = bool(
            direct is not None
            and direct.execution.application_build_id
            == failure.execution.application_build_id
            and (
                regression is None
                or regression.execution.application_build_id
                == failure.execution.application_build_id
            )
        )
        current_build = (
            failure.execution.application_build_id
            == self._application_build_manifest.application_build_id
        )
        return InvestigationWorkspace(
            original_failure=failure,
            steps=steps,
            configuration_comparison=comparison,
            defect_record=defect,
            correction_record=correction,
            direct_repeat=direct,
            regression=regression,
            repeat_links=links,
            actions=self._actions(
                defect,
                correction,
                direct,
                regression,
                current_build=current_build,
            ),
            same_build_proven=same_build,
            conceptual_boundary_notice=self.NOTICE,
        )

    def record_defect(
        self,
        failure_execution_id: UUID,
        reviewer: str,
        reviewed_step_ids: tuple[str, ...],
    ) -> InvestigationWorkspace:
        if tuple(reviewed_step_ids) != self.REVIEW_STEP_IDS:
            raise InvestigationBoundaryError(
                "all seven consequence-to-source steps must be reviewed in order before recording DEF-001"
            )
        failure = self._current_build_failure(failure_execution_id)
        steps, comparison = self._investigation_projection(failure)
        difference = comparison.differences[0]
        evidence = failure.evidence_snapshots[0]
        actual = failure.execution.observed_result or {}
        expected = failure.execution.expected_comparison_values or {}
        unexpected_sections = sorted(
            set(expected.get("de_energised_section_ids", ()))
            - set(actual.get("de_energised_section_ids", ()))
        )
        affected = int(actual.get("affected_customer_count", 0))
        expected_affected = int(expected.get("affected_customer_count", 0))
        record = DefectRecord(
            defect_record_id=uuid4(),
            defect_id=self.DEFECT_ID,
            original_failed_execution_id=failure_execution_id,
            affected_configuration=comparison.defective,
            identified_difference=difference,
            root_cause=(
                f"The configured value at {difference.path} is {difference.before}; "
                f"the approved corrected package establishes {difference.after}."
            ),
            engineering_propagation=(
                "The configured endpoint difference changes the active source path.",
                f"Unexpectedly energised sections: {', '.join(unexpected_sections)}.",
                "The derived outage extent therefore omits those customer zones.",
                f"Affected customers are understated by {expected_affected - affected}.",
            ),
            supporting_evidence_references=tuple(
                dict.fromkeys(
                    reference
                    for step in steps
                    for reference in step.source_record_references
                )
            ),
            recorded_by=reviewer,
            recorded_scenario_time=evidence.scenario_time,
            investigation_snapshot_sha256=sha256_bytes(
                canonical_json_bytes(
                    {
                        "steps": [item.model_dump(mode="json") for item in steps],
                        "configuration_comparison": comparison.model_dump(mode="json"),
                    }
                )
            ),
        )
        try:
            self._repository.insert_defect(record)
        except InvestigationRecordConflict as error:
            raise InvestigationBoundaryError(str(error)) from error
        return self.workspace(failure_execution_id)

    def record_correction(
        self, failure_execution_id: UUID, reviewer: str
    ) -> InvestigationWorkspace:
        failure = self._current_build_failure(failure_execution_id)
        defect = self._required_defect(failure_execution_id)
        _steps, comparison = self._investigation_projection(failure)
        record = CorrectionRecord(
            correction_record_id=uuid4(),
            correction_id=self.CORRECTION_ID,
            defect_record_id=defect.defect_record_id,
            defect_id=defect.defect_id,
            defective_configuration=comparison.defective,
            corrected_configuration=comparison.corrected,
            approved_difference=comparison.differences[0],
            engineering_effect=(
                "Select the existing corrected v1.1 package so the ordinary topology "
                "engine uses the intended endpoint relationship; no package or algorithm is modified."
            ),
            verification_basis=(
                self.DIRECT_TEST_ID,
                "VT-DET-REPEAT-001",
                self.REGRESSION_TEST_ID,
                "VT-CFG-BASE-001",
            ),
            reviewed_by=reviewer,
            recorded_scenario_time=failure.evidence_snapshots[0].scenario_time,
        )
        try:
            self._repository.insert_correction(record)
        except InvestigationRecordConflict as error:
            raise InvestigationBoundaryError(str(error)) from error
        return self.workspace(failure_execution_id)

    def run_direct_repeat(
        self, failure_execution_id: UUID, actor: str
    ) -> InvestigationWorkspace:
        failure = self._current_build_failure(failure_execution_id)
        defect = self._required_defect(failure_execution_id)
        correction = self._required_correction(defect)
        if self._link(defect, RepeatRelationshipType.DIRECT_REPEAT) is not None:
            raise InvestigationBoundaryError("the direct repeat is already preserved")
        initial_time = self._evidence_snapshot(failure).run.initial_scenario_time
        initial = self._initialise_controlled_run("1.1", actor, initial_time)
        execution = self._validation.start_execution(
            self.DIRECT_TEST_ID,
            initial.run.scenario_run_id,
            links=ValidationExecutionLinks(
                repeat_of_execution_id=failure_execution_id,
                defect_id=defect.defect_id,
                correction_id=correction.correction_id,
            ),
        )
        self._execute_available(
            initial.run.scenario_run_id, actor, ScenarioCommandType.INITIATE_FAULT
        )
        self._validation.capture_checkpoint(
            execution.validation_execution_id, "POST_TRIP"
        )
        passed = self._validation.finalise_execution(
            execution.validation_execution_id, "POST_TRIP"
        )
        if passed.verdict is not ValidationVerdict.PASS:
            raise InvestigationBoundaryError(
                "the same-build v1.1 direct repeat did not pass the accepted I5 comparison"
            )
        self._repository.insert_repeat_link(
            RepeatLink(
                repeat_link_id=uuid4(),
                relationship_type=RepeatRelationshipType.DIRECT_REPEAT,
                original_execution_id=failure_execution_id,
                new_execution_id=passed.validation_execution_id,
                defect_record_id=defect.defect_record_id,
                correction_record_id=correction.correction_record_id,
                defect_id=defect.defect_id,
                correction_id=correction.correction_id,
                application_build_id=passed.application_build_id,
            )
        )
        return self.workspace(failure_execution_id)

    def run_regression(
        self, failure_execution_id: UUID, actor: str
    ) -> InvestigationWorkspace:
        failure = self._current_build_failure(failure_execution_id)
        defect = self._required_defect(failure_execution_id)
        correction = self._required_correction(defect)
        direct_link = self._link(defect, RepeatRelationshipType.DIRECT_REPEAT)
        if direct_link is None:
            raise InvestigationBoundaryError(
                "the corrected full regression requires the preserved direct repeat PASS"
            )
        if self._link(defect, RepeatRelationshipType.REGRESSION) is not None:
            raise InvestigationBoundaryError("the corrected regression is already preserved")
        direct = self._validation.get_execution(direct_link.new_execution_id)
        if direct.execution.verdict is not ValidationVerdict.PASS:
            raise InvestigationBoundaryError("the linked direct repeat is not PASS")

        initial_time = self._evidence_snapshot(failure).run.initial_scenario_time
        initial = self._initialise_controlled_run("1.1", actor, initial_time)
        execution = self._validation.start_execution(
            self.REGRESSION_TEST_ID,
            initial.run.scenario_run_id,
            links=ValidationExecutionLinks(
                defect_id=defect.defect_id,
                correction_id=correction.correction_id,
            ),
        )
        self._validation.capture_checkpoint(execution.validation_execution_id, "N0")
        run_id = initial.run.scenario_run_id
        self._execute_available(run_id, actor, ScenarioCommandType.INITIATE_FAULT)
        self._validation.capture_checkpoint(execution.validation_execution_id, "N1")
        self._execute_available(run_id, actor, ScenarioCommandType.ACKNOWLEDGE_ALARM)
        while self._scenarios.snapshot(run_id).run.network_state_label.value != "N2":
            self._execute_available(
                run_id, actor, ScenarioCommandType.OPERATE_ISOLATION_DEVICE
            )
        self._validation.capture_checkpoint(execution.validation_execution_id, "N2")
        self._execute_available(run_id, actor, ScenarioCommandType.RESTORE_NORMAL_SOURCE)
        self._validation.capture_checkpoint(execution.validation_execution_id, "N3")
        self._execute_available(run_id, actor, ScenarioCommandType.ASSESS_RESTORATION)
        self._validation.capture_checkpoint(execution.validation_execution_id, "N4")
        self._execute_available(run_id, actor, ScenarioCommandType.EXECUTE_RESTORATION)
        self._validation.capture_checkpoint(execution.validation_execution_id, "N5")
        regression = self._validation.get_execution(execution.validation_execution_id)
        self._repository.insert_repeat_link(
            RepeatLink(
                repeat_link_id=uuid4(),
                relationship_type=RepeatRelationshipType.REGRESSION,
                original_execution_id=direct.execution.validation_execution_id,
                new_execution_id=regression.execution.validation_execution_id,
                defect_record_id=defect.defect_record_id,
                correction_record_id=correction.correction_record_id,
                defect_id=defect.defect_id,
                correction_id=correction.correction_id,
                application_build_id=regression.execution.application_build_id,
            )
        )
        return self.workspace(failure_execution_id)

    def _failure(self, execution_id: UUID) -> ValidationExecutionSummary:
        summary = self._validation.get_execution(execution_id)
        execution = summary.execution
        if (
            execution.test_id != self.DIRECT_TEST_ID
            or execution.status is not ValidationExecutionStatus.FINALISED
            or execution.verdict is not ValidationVerdict.FAIL
            or execution.configuration_version != "1.0"
            or len(summary.evidence_snapshots) != 1
        ):
            raise InvestigationBoundaryError(
                "investigation entry requires a preserved finalised v1.0 VT-TOP-DEF-001 FAIL"
            )
        return summary

    def _current_build_failure(
        self, execution_id: UUID
    ) -> ValidationExecutionSummary:
        failure = self._failure(execution_id)
        if (
            failure.execution.application_build_id
            != self._application_build_manifest.application_build_id
        ):
            raise InvestigationBoundaryError(
                "an investigation created by a different application build is historical and read-only"
            )
        return failure

    def _investigation_projection(
        self, failure: ValidationExecutionSummary
    ) -> tuple[tuple[InvestigationStep, ...], ConfigurationComparisonView]:
        snapshot = self._evidence_snapshot(failure)
        defective = self._configurations.load("v1.0")
        corrected = self._configurations.load("v1.1")
        raw_differences = compare_engineering_content(defective.data, corrected.data)
        if len(raw_differences) != 1:
            raise InvestigationBoundaryError(
                "controlled package comparison must contain exactly one engineering difference"
            )
        difference = ConfigurationDifferenceView(
            path=raw_differences[0].path,
            before=str(raw_differences[0].before),
            after=str(raw_differences[0].after),
        )
        comparison = ConfigurationComparisonView(
            defective=self._package_identity(defective),
            corrected=self._package_identity(corrected),
            differences=(difference,),
            unchanged_information_classes=(
                "assets and stable identifiers",
                "section loads and feeder capacities",
                "customer-zone mappings",
                "normal switching states",
                "schema and shared application algorithms",
            ),
        )
        execution = failure.execution
        expected = execution.expected_comparison_values or {}
        observed = execution.observed_result or {}
        expected_sections = set(expected.get("de_energised_section_ids", ()))
        observed_sections = set(observed.get("de_energised_section_ids", ()))
        unexpected = tuple(sorted(expected_sections - observed_sections))
        topology_sections = {item.section_id: item for item in snapshot.topology.sections}
        telemetry = {item.entity_id: item for item in snapshot.telemetry}
        validity = {item.point_id: item for item in snapshot.telemetry_validity}
        breaker = telemetry.get("BRK-A")
        if breaker is None:
            raise InvestigationBoundaryError("required BRK-A evidence is absent")
        breaker_validity = validity[breaker.point_id]
        source_facts: list[InvestigationFact] = []
        implicated_paths: list[str] = []
        difference_edge_id = difference.path.split(".")[1]
        for section_id in unexpected:
            section = topology_sections[section_id]
            for path in section.source_paths:
                trace = " → ".join(reversed(path.node_ids))
                source_facts.append(
                    InvestigationFact(
                        label=section_id,
                        value=f"ENERGISED from {path.source_feeder_id}: {trace}",
                    )
                )
                if difference_edge_id in path.edge_ids:
                    implicated_paths.append(trace)
        if not source_facts or not implicated_paths:
            raise InvestigationBoundaryError(
                "the preserved source paths do not traverse the single configured difference"
            )
        outage_terms = tuple(
            f"{item.customer_zone_id}/{item.section_id}={item.customer_count}"
            for item in snapshot.outage.affected_customer_zones
        )
        evidence = failure.evidence_snapshots[0]
        common_refs = (
            f"validation-execution:{execution.validation_execution_id}",
            f"evidence:{evidence.evidence_snapshot_id}",
        )
        steps = (
            InvestigationStep(
                step_id="INV-01",
                title="Preserved validation consequence",
                facts=(
                    InvestigationFact(label="Expected affected customers", value=str(expected.get("affected_customer_count"))),
                    InvestigationFact(label="Observed affected customers", value=str(observed.get("affected_customer_count"))),
                    InvestigationFact(label="Observed de-energised sections", value=", ".join(sorted(observed_sections))),
                    InvestigationFact(label="Validation verdict", value=execution.verdict.value),
                ),
                source_record_references=common_refs,
            ),
            InvestigationStep(
                step_id="INV-02",
                title="Initiating SCADA evidence",
                facts=(
                    InvestigationFact(label="BRK-A value", value=breaker.value.value),
                    InvestigationFact(label="Quality", value=breaker.quality.value),
                    InvestigationFact(label="Freshness", value=breaker_validity.freshness.value),
                    InvestigationFact(label="Evidence validity", value="VALID" if breaker_validity.overall_valid else "INVALID"),
                ),
                source_record_references=(*common_refs, f"telemetry:{breaker.point_id}"),
            ),
            InvestigationStep(
                step_id="INV-03",
                title="Section energisation and source attribution",
                facts=tuple(source_facts),
                source_record_references=(*common_refs, f"topology:{execution.scenario_run_id}:revision:{snapshot.run.state_revision}"),
            ),
            InvestigationStep(
                step_id="INV-04",
                title="OMS input and customer arithmetic",
                facts=(
                    InvestigationFact(label="Received outage extent", value=", ".join(snapshot.outage.de_energised_section_ids)),
                    InvestigationFact(label="Customer-zone arithmetic", value=" + ".join(outage_terms)),
                    InvestigationFact(label="OMS total", value=str(snapshot.outage.affected_customer_count)),
                ),
                source_record_references=(*common_refs, f"outage:{execution.scenario_run_id}:revision:{snapshot.run.state_revision}"),
            ),
            InvestigationStep(
                step_id="INV-05",
                title="Unexpected active source path",
                facts=tuple(
                    InvestigationFact(label=f"Path {index}", value=value)
                    for index, value in enumerate(implicated_paths, start=1)
                ),
                source_record_references=(*common_refs, f"configuration-edge:{difference_edge_id}"),
            ),
            InvestigationStep(
                step_id="INV-06",
                title="Immutable configuration comparison",
                facts=(
                    InvestigationFact(label="Changed field", value=difference.path),
                    InvestigationFact(label="v1.0", value=difference.before),
                    InvestigationFact(label="v1.1", value=difference.after),
                    InvestigationFact(label="Difference count", value="1"),
                ),
                source_record_references=(
                    f"configuration:{comparison.defective.configuration_id}:{comparison.defective.package_sha256}",
                    f"configuration:{comparison.corrected.configuration_id}:{comparison.corrected.package_sha256}",
                ),
            ),
            InvestigationStep(
                step_id="INV-07",
                title="Engineering root-cause record",
                facts=(
                    InvestigationFact(label="Configured cause", value=f"{difference.path}: {difference.before} instead of {difference.after}"),
                    InvestigationFact(label="Topology consequence", value=f"Unexpected source attribution for {', '.join(unexpected)}"),
                    InvestigationFact(label="Outage consequence", value=f"Observed {snapshot.outage.affected_customer_count} affected customers"),
                    InvestigationFact(label="Engineering disposition", value="Configuration correction; SCADA, topology and OMS algorithms remain unchanged"),
                ),
                source_record_references=(*common_refs, "engineering-defect:DEF-001"),
            ),
        )
        return steps, comparison

    @staticmethod
    def _package_identity(loaded: LoadedConfiguration) -> ConfigurationPackageIdentity:
        entry = loaded.catalog_entry
        return ConfigurationPackageIdentity(
            configuration_id=entry.configuration_id,
            version=entry.version,
            package_sha256=entry.package_sha256,
            data_sha256=entry.data_sha256,
            schema_sha256=entry.schema_sha256,
        )

    @staticmethod
    def _evidence_snapshot(summary: ValidationExecutionSummary) -> ScenarioSnapshot:
        payload = summary.evidence_snapshots[0].canonical_payload.get("scenario_snapshot")
        if not isinstance(payload, dict):
            raise InvestigationBoundaryError("preserved scenario snapshot is absent")
        return ScenarioSnapshot.model_validate_json(canonical_json_bytes(payload), strict=True)

    def _initialise_controlled_run(
        self, version: str, actor: str, scenario_time: datetime
    ) -> ScenarioSnapshot:
        request = InitialiseRunRequest(
            command_id=uuid4(),
            actor=actor,
            mode=ScenarioMode.FORMAL,
            configuration_version=version,
            scenario_time=scenario_time,
        )
        result = (
            self._scenarios.initialise_replacement_run(request)
            if self._scenarios.has_mutable_run()
            else self._scenarios.initialise(request)
        )
        return result.snapshot

    def _execute_available(
        self,
        run_id: UUID,
        actor: str,
        command_type: ScenarioCommandType,
    ) -> ScenarioSnapshot:
        snapshot = self._scenarios.snapshot(run_id)
        candidates = sorted(
            (
                item
                for item in snapshot.allowed_actions
                if item.command_type is command_type and item.available
            ),
            key=lambda item: item.target_entity_id or str(item.alarm_id or item.assessment_id or ""),
        )
        if not candidates:
            raise InvestigationBoundaryError(
                f"no backend-authorised {command_type.value} action is available"
            )
        action: AllowedAction = candidates[0]
        offset = formal_action_offset_seconds(command_type, action.target_entity_id)
        if offset is None:
            raise InvestigationBoundaryError(
                f"the controlled formal schedule has no time for {command_type.value}"
            )
        result = self._scenarios.execute(
            run_id,
            ScenarioCommandRequest(
                command_id=uuid4(),
                scenario_run_id=run_id,
                actor=actor,
                expected_revision=snapshot.run.state_revision,
                command_type=command_type,
                scenario_time=snapshot.run.initial_scenario_time + timedelta(seconds=offset),
                target_entity_id=action.target_entity_id,
                requested_state=action.requested_state,
                alarm_id=action.alarm_id,
                assessment_id=action.assessment_id,
            ),
        )
        if not result.accepted:
            raise InvestigationBoundaryError(result.reason)
        return result.snapshot

    def _required_defect(self, failure_execution_id: UUID) -> DefectRecord:
        defect = self._repository.get_defect(self.DEFECT_ID)
        if defect is None or defect.original_failed_execution_id != failure_execution_id:
            raise InvestigationBoundaryError("the preserved DEF-001 record is required")
        return defect

    def _required_correction(self, defect: DefectRecord) -> CorrectionRecord:
        correction = self._repository.get_correction(self.CORRECTION_ID)
        if correction is None or correction.defect_record_id != defect.defect_record_id:
            raise InvestigationBoundaryError("the preserved COR-001 record is required")
        return correction

    def _link(
        self, defect: DefectRecord, relationship: RepeatRelationshipType
    ) -> RepeatLink | None:
        return next(
            (
                item
                for item in self._repository.list_repeat_links(defect.defect_record_id)
                if item.relationship_type is relationship
            ),
            None,
        )

    @staticmethod
    def _actions(
        defect: DefectRecord | None,
        correction: CorrectionRecord | None,
        direct: ValidationExecutionSummary | None,
        regression: ValidationExecutionSummary | None,
        *,
        current_build: bool,
    ) -> tuple[InvestigationAction, ...]:
        if not current_build:
            return tuple(
                InvestigationAction(
                    action_type=action_type,
                    available=False,
                    reason_code="HISTORICAL_BUILD_READ_ONLY",
                    reason=(
                        "This investigation belongs to an earlier application build; "
                        "its preserved records are review-only."
                    ),
                )
                for action_type in (
                    "RECORD_DEFECT",
                    "RECORD_CORRECTION",
                    "RUN_DIRECT_REPEAT",
                    "RUN_REGRESSION",
                )
            )
        return (
            InvestigationAction(
                action_type="RECORD_DEFECT",
                available=defect is None,
                reason_code="AVAILABLE" if defect is None else "DEFECT_ALREADY_RECORDED",
                reason="Review all seven evidence steps and record DEF-001." if defect is None else "DEF-001 is preserved and immutable.",
            ),
            InvestigationAction(
                action_type="RECORD_CORRECTION",
                available=defect is not None and correction is None,
                reason_code="AVAILABLE" if defect is not None and correction is None else "REQUIRES_DEFECT" if defect is None else "CORRECTION_ALREADY_RECORDED",
                reason="Record selection of the existing immutable v1.1 package." if defect is not None and correction is None else "Record DEF-001 first." if defect is None else "COR-001 is preserved and immutable.",
            ),
            InvestigationAction(
                action_type="RUN_DIRECT_REPEAT",
                available=correction is not None and direct is None,
                reason_code="AVAILABLE" if correction is not None and direct is None else "REQUIRES_CORRECTION" if correction is None else "DIRECT_REPEAT_ALREADY_RECORDED",
                reason="Execute the same-build v1.1 direct repeat." if correction is not None and direct is None else "Record the correction first." if correction is None else "The direct repeat is preserved.",
            ),
            InvestigationAction(
                action_type="RUN_REGRESSION",
                available=direct is not None and direct.execution.verdict is ValidationVerdict.PASS and regression is None,
                reason_code="AVAILABLE" if direct is not None and direct.execution.verdict is ValidationVerdict.PASS and regression is None else "REQUIRES_DIRECT_REPEAT_PASS" if direct is None or direct.execution.verdict is not ValidationVerdict.PASS else "REGRESSION_ALREADY_RECORDED",
                reason="Execute and preserve the corrected N0-N5 evidence set." if direct is not None and direct.execution.verdict is ValidationVerdict.PASS and regression is None else "A direct repeat PASS is required first." if direct is None or direct.execution.verdict is not ValidationVerdict.PASS else "The corrected regression evidence is preserved.",
            ),
        )
