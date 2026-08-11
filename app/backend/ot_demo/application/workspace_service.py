"""Assemble the approved I6 projection without taking engineering authority."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from ..domain.enums import (
    AlarmAcknowledgementState,
    EvidenceClass,
    NetworkStateLabel,
    ScenarioCommandType,
    ScenarioMode,
    ScenarioRunStatus,
    ValidationExecutionStatus,
    ValidationVerdict,
)
from ..infrastructure.build_identity import ApplicationBuildManifest
from ..infrastructure.configuration_loader import JsonConfigurationLoader
from ..modules.configuration.models import LoadedConfiguration
from ..modules.scenario.models import AllowedAction, ScenarioSnapshot
from ..modules.scenario.definition import formal_action_offset_seconds
from ..modules.validation.catalogue import ValidationCatalogueResolver
from ..modules.validation.models import (
    LoadedValidationDefinition,
    ValidationExecutionSummary,
    ValidationSuspensionRecord,
)
from ..modules.validation.service import ValidationService
from ..modules.workspace.models import (
    ConfiguredEntityView,
    DerivedEntityView,
    ObservedEntityView,
    PresentationPosition,
    TelemetryWorkspaceRow,
    ValidationProgress,
    ValidationWorkspaceAction,
    ValidationWorkspaceView,
    WorkspaceAction,
    WorkspaceBootstrap,
    WorkspaceFeederView,
    WorkspaceNetworkEdge,
    WorkspaceNetworkNode,
    WorkspaceProjection,
    WorkspaceSummary,
)
from .scenario_coordinator import ScenarioCoordinator


class WorkspaceProjectionError(ValueError):
    """Raised when controlled presentation inputs cannot produce a projection."""


class WorkspaceService:
    """Compose owner-produced records into a read-only engineering workspace."""

    FORMAL_TEST_ID = "VT-FML-N0-N5-001"
    FORMAL_EPOCH = "2030-01-01T00:00:00.000Z"
    CONCEPTUAL_NOTICE = (
        "Fictional local engineering demonstrator — conceptual SCADA, ADMS and OMS "
        "functions only. All switching is simulated; no real equipment control."
    )

    def __init__(
        self,
        configuration_loader: JsonConfigurationLoader,
        scenarios: ScenarioCoordinator,
        validation: ValidationService,
        catalogue: ValidationCatalogueResolver,
        *,
        application_build_manifest: ApplicationBuildManifest,
        presentation_path: Path,
    ) -> None:
        self._configuration_loader = configuration_loader
        self._scenarios = scenarios
        self._validation = validation
        self._catalogue = catalogue
        self._application_build_manifest = application_build_manifest
        self._presentation_path = presentation_path

    def bootstrap(self) -> WorkspaceBootstrap:
        from datetime import datetime

        loaded = self._configuration_loader.load("v1.1")
        definitions = self._catalogue.load()
        formal = self._definition(definitions, self.FORMAL_TEST_ID)
        return WorkspaceBootstrap(
            application_build_id=self._application_build_manifest.application_build_id,
            default_actor="Graduate Engineer",
            default_mode=ScenarioMode.FORMAL,
            default_evidence_class=formal.definition.evidence_class,
            default_configuration_id=loaded.catalog_entry.configuration_id,
            default_configuration_version=loaded.catalog_entry.version,
            default_scenario_time=datetime.fromisoformat(
                self.FORMAL_EPOCH.replace("Z", "+00:00")
            ),
            formal_test_id=self.FORMAL_TEST_ID,
            formal_definition=formal,
            exploration_section_ids=tuple(
                sorted(section.entity_id for section in loaded.data.sections)
            ),
            definition_count=len(definitions),
            conceptual_boundary_notice=self.CONCEPTUAL_NOTICE,
        )

    def projection(self, scenario_run_id: UUID) -> WorkspaceProjection:
        snapshot = self._scenarios.snapshot(scenario_run_id)
        loaded = self._configuration_loader.load(
            f"v{snapshot.run.configuration_version}"
        )
        if loaded.catalog_entry.configuration_id != snapshot.run.configuration_id:
            raise WorkspaceProjectionError(
                "run and controlled configuration identity do not match"
            )
        positions = self._positions(loaded)
        telemetry = self._telemetry_rows(snapshot)
        telemetry_by_entity = {item.entity_id: item for item in telemetry}
        section_by_id = {item.section_id: item for item in snapshot.topology.sections}
        customer_by_section = {
            item.section_id: item for item in loaded.data.customer_zone_mappings
        }
        nodes: list[WorkspaceNetworkNode] = []

        for source in loaded.data.sources:
            nodes.append(
                WorkspaceNetworkNode(
                    entity_id=source.entity_id,
                    position=positions[source.entity_id],
                    configured=ConfiguredEntityView(
                        entity_id=source.entity_id,
                        entity_type="SOURCE",
                        name=source.name,
                        normal_source_availability=source.normal_source_availability,
                    ),
                    derived=DerivedEntityView(
                        current_source_availability=snapshot.run.source_availability[
                            source.entity_id
                        ]
                    ),
                    fault_status="NOT_APPLICABLE",
                )
            )
        for device in loaded.data.switching_devices:
            row = telemetry_by_entity.get(device.entity_id)
            nodes.append(
                WorkspaceNetworkNode(
                    entity_id=device.entity_id,
                    position=positions[device.entity_id],
                    configured=ConfiguredEntityView(
                        entity_id=device.entity_id,
                        entity_type="SWITCHING_DEVICE",
                        name=device.name,
                        feeder_id=device.feeder_id,
                        device_type=device.device_type.value,
                        normal_state=device.normal_state,
                    ),
                    observed=(
                        ObservedEntityView(
                            point_id=row.point_id,
                            value=row.value,
                            quality=row.quality,
                            timestamp=row.timestamp,
                            age_ms=row.age_ms,
                            freshness=row.freshness,
                            overall_valid=row.overall_valid,
                            reason_codes=row.reason_codes,
                        )
                        if row is not None
                        else None
                    ),
                    derived=DerivedEntityView(),
                    fault_status="NOT_APPLICABLE",
                )
            )
        for section in loaded.data.sections:
            state = section_by_id[section.entity_id]
            mapping = customer_by_section[section.entity_id]
            nodes.append(
                WorkspaceNetworkNode(
                    entity_id=section.entity_id,
                    position=positions[section.entity_id],
                    configured=ConfiguredEntityView(
                        entity_id=section.entity_id,
                        entity_type="SECTION",
                        name=section.name,
                        feeder_id=section.feeder_id,
                        configured_load_kw=section.load_kw,
                        customer_zone_id=mapping.customer_zone_id,
                        customer_count=mapping.customer_count,
                    ),
                    derived=DerivedEntityView(
                        energised=state.energised,
                        source_feeder_ids=state.source_feeder_ids,
                        source_path_node_ids=tuple(
                            path.node_ids for path in state.source_paths
                        ),
                    ),
                    fault_status="FAULTED" if state.faulted else "NOT_FAULTED",
                )
            )

        active_edges = set(snapshot.topology.active_edge_ids)
        edges = tuple(
            WorkspaceNetworkEdge(
                edge_id=edge.edge_id,
                endpoint_a_id=edge.endpoint_a_id,
                endpoint_b_id=edge.endpoint_b_id,
                semantics=edge.semantics.value,
                active=edge.edge_id in active_edges,
            )
            for edge in sorted(loaded.data.connectivity_edges, key=lambda item: item.edge_id)
        )
        feeder_load_by_id = {
            item.feeder_id: item for item in snapshot.topology.feeder_loads
        }
        feeders = tuple(
            WorkspaceFeederView(
                feeder_id=feeder.entity_id,
                name=feeder.name,
                source_id=feeder.source_id,
                source_breaker_id=feeder.source_breaker_id,
                section_ids=feeder.section_ids,
                configured_capacity_kw=feeder.capacity_kw,
                configured_normal_load_kw=feeder.normal_connected_load_kw,
                derived_currently_supplied_load_kw=feeder_load_by_id[
                    feeder.entity_id
                ].currently_supplied_load_kw,
                derived_load_attribution_complete=feeder_load_by_id[
                    feeder.entity_id
                ].load_attribution_complete,
                derived_supplied_section_ids=feeder_load_by_id[
                    feeder.entity_id
                ].supplied_section_ids,
            )
            for feeder in sorted(loaded.data.feeders, key=lambda item: item.entity_id)
        )
        invalidated_ids = {
            item.assessment_id for item in snapshot.restoration_invalidations
        }
        current_assessment = (
            snapshot.restoration_assessments[-1]
            if snapshot.restoration_assessments
            else None
        )
        current_invalidated = bool(
            current_assessment
            and current_assessment.assessment_id in invalidated_ids
        )
        active_alarms = tuple(item for item in snapshot.alarms if item.active)
        summary = WorkspaceSummary(
            de_energised_section_ids=snapshot.outage.de_energised_section_ids,
            affected_customer_count=snapshot.outage.affected_customer_count,
            restored_customer_delta=snapshot.outage.restored_customer_delta,
            active_alarm_count=len(active_alarms),
            unacknowledged_alarm_count=sum(
                item.acknowledgement_state
                is AlarmAcknowledgementState.UNACKNOWLEDGED
                for item in active_alarms
            ),
            current_assessment_status=(
                "NOT_ASSESSED"
                if current_assessment is None
                else "INVALIDATED"
                if current_invalidated
                else current_assessment.outcome.value
            ),
            current_assessment_id=(
                current_assessment.assessment_id if current_assessment else None
            ),
            current_assessment_invalidated=current_invalidated,
            radiality_status=snapshot.topology.radiality_status,
        )
        definitions = self._catalogue.load()
        all_executions = self._validation.list_executions()
        run_executions = self._validation.list_executions(
            scenario_run_id=scenario_run_id
        )
        validation_view = ValidationWorkspaceView(
            definitions=definitions,
            run_executions=run_executions,
            library_executions=all_executions,
            composites=self._validation.list_composites(),
            suspensions=self._validation.list_suspensions(),
            progress=self._validation_progress(
                definitions, all_executions, self._validation.list_suspensions()
            ),
            actions=self._validation_actions(snapshot, definitions, run_executions),
        )
        return WorkspaceProjection(
            application_build_id=self._application_build_manifest.application_build_id,
            run=snapshot.run,
            configuration_status=loaded.catalog_entry.status,
            summary=summary,
            network_nodes=tuple(sorted(nodes, key=lambda item: item.entity_id)),
            network_edges=edges,
            feeders=feeders,
            telemetry=telemetry,
            alarms=snapshot.alarms,
            events=snapshot.events,
            isolation_proof=snapshot.topology.isolation_proof,
            restoration_assessments=snapshot.restoration_assessments,
            restoration_invalidations=snapshot.restoration_invalidations,
            allowed_actions=tuple(
                self._workspace_action(snapshot, item)
                for item in snapshot.allowed_actions
            ),
            validation=validation_view,
            conceptual_boundary_notice=self.CONCEPTUAL_NOTICE,
        )

    @staticmethod
    def _definition(
        definitions: tuple[LoadedValidationDefinition, ...], test_id: str
    ) -> LoadedValidationDefinition:
        try:
            return next(item for item in definitions if item.definition.test_id == test_id)
        except StopIteration as error:
            raise WorkspaceProjectionError(
                f"controlled validation definition is unavailable: {test_id}"
            ) from error

    def _positions(
        self, loaded: LoadedConfiguration
    ) -> dict[str, PresentationPosition]:
        try:
            raw: dict[str, Any] = json.loads(
                self._presentation_path.read_text(encoding="utf-8")
            )
            positions = {
                entity_id: PresentationPosition.model_validate(value, strict=True)
                for entity_id, value in raw["positions"].items()
            }
        except (OSError, KeyError, TypeError, ValueError) as error:
            raise WorkspaceProjectionError(
                "presentation-only one-line metadata is invalid"
            ) from error
        required = {
            *(item.entity_id for item in loaded.data.sources),
            *(item.entity_id for item in loaded.data.sections),
            *(item.entity_id for item in loaded.data.switching_devices),
        }
        if set(positions) != required:
            raise WorkspaceProjectionError(
                "presentation positions must exactly cover configured one-line entities"
            )
        return positions

    @staticmethod
    def _telemetry_rows(
        snapshot: ScenarioSnapshot,
    ) -> tuple[TelemetryWorkspaceRow, ...]:
        validity_by_point = {
            item.point_id: item for item in snapshot.telemetry_validity
        }
        return tuple(
            TelemetryWorkspaceRow(
                point_id=point.point_id,
                entity_id=point.entity_id,
                value=point.value,
                quality=point.quality,
                timestamp=point.last_update_scenario_time,
                age_ms=validity_by_point[point.point_id].age_ms,
                freshness=validity_by_point[point.point_id].freshness,
                quality_valid=validity_by_point[point.point_id].quality_valid,
                timestamp_valid=validity_by_point[point.point_id].timestamp_valid,
                overall_valid=validity_by_point[point.point_id].overall_valid,
                reason_codes=validity_by_point[point.point_id].reason_codes,
            )
            for point in snapshot.telemetry
        )

    @staticmethod
    def _validation_progress(
        definitions: tuple[LoadedValidationDefinition, ...],
        executions: tuple[ValidationExecutionSummary, ...],
        suspensions: tuple[ValidationSuspensionRecord, ...] = (),
    ) -> ValidationProgress:
        formal_definitions = tuple(
            item
            for item in definitions
            if item.definition.evidence_class is EvidenceClass.FORMAL
        )
        formal_test_ids = {
            item.definition.test_id for item in formal_definitions
        }
        formal_executions = tuple(
            item
            for item in executions
            if item.execution.evidence_class is EvidenceClass.FORMAL
        )
        finalised = tuple(
            item
            for item in formal_executions
            if item.execution.status is ValidationExecutionStatus.FINALISED
        )
        executed_test_ids = {
            item.execution.test_id
            for item in formal_executions
            if item.execution.test_id in formal_test_ids
        }
        return ValidationProgress(
            definition_count=len(formal_definitions),
            definitions_without_execution_count=len(formal_definitions)
            - len(executed_test_ids),
            execution_count=len(formal_executions),
            active_execution_count=sum(
                item.execution.status is ValidationExecutionStatus.ACTIVE
                for item in formal_executions
            ),
            finalised_execution_count=len(finalised),
            pass_count=sum(
                item.execution.verdict is ValidationVerdict.PASS for item in finalised
            ),
            fail_count=sum(
                item.execution.verdict is ValidationVerdict.FAIL for item in finalised
            ),
            blocked_test_count=sum(
                item.inherited_evidence_class is EvidenceClass.FORMAL
                and item.intended_test_id in formal_test_ids
                for item in suspensions
            ),
        )

    def _validation_actions(
        self,
        snapshot: ScenarioSnapshot,
        definitions: tuple[LoadedValidationDefinition, ...],
        run_executions: tuple[ValidationExecutionSummary, ...],
    ) -> tuple[ValidationWorkspaceAction, ...]:
        if snapshot.run.mode is ScenarioMode.EXPLORATION:
            return self._exploration_validation_actions(
                snapshot, definitions, run_executions
            )
        definition = self._definition(definitions, self.FORMAL_TEST_ID)
        matching = tuple(
            item
            for item in run_executions
            if item.execution.test_id == self.FORMAL_TEST_ID
        )
        if not matching:
            available = (
                snapshot.run.mode is ScenarioMode.FORMAL
                and snapshot.run.network_state_label is NetworkStateLabel.N0
            )
            return (
                ValidationWorkspaceAction(
                    action_type="START_EXECUTION",
                    available=available,
                    reason_code=("AVAILABLE" if available else "REQUIRES_FORMAL_N0"),
                    reason=(
                        "Start the controlled formal execution before the first scenario action."
                        if available
                        else "The controlled formal execution may start only against FORMAL N0."
                    ),
                    test_id=self.FORMAL_TEST_ID,
                ),
            )
        current = matching[-1]
        execution = current.execution
        captured = {item.checkpoint_id for item in current.evidence_snapshots}
        required = {
            item.checkpoint_id for item in definition.definition.checkpoint_obligations
        }
        checkpoint_id = snapshot.run.network_state_label.value
        checkpoint_defined = checkpoint_id in required
        capture_available = (
            execution.status is ValidationExecutionStatus.ACTIVE
            and checkpoint_defined
            and checkpoint_id not in captured
        )
        all_captured = required <= captured
        comparison_available = (
            definition.definition.comparison_expected_values is not None
        )
        criterion_method_available = definition.definition.determination_method is not None
        finalise_available = (
            execution.status is ValidationExecutionStatus.ACTIVE
            and all_captured
            and comparison_available
        )
        return (
            ValidationWorkspaceAction(
                action_type="CAPTURE_CHECKPOINT",
                available=capture_available,
                reason_code=(
                    "AVAILABLE"
                    if capture_available
                    else "CHECKPOINT_ALREADY_CAPTURED"
                    if checkpoint_id in captured
                    else "CURRENT_N_STATE_HAS_NO_CHECKPOINT"
                    if not checkpoint_defined
                    else "EXECUTION_FINALISED"
                ),
                reason=(
                    f"Capture immutable {checkpoint_id} evidence from the current backend projection."
                    if capture_available
                    else f"Checkpoint {checkpoint_id} is already preserved."
                    if checkpoint_id in captured
                    else "The current backend N-state is not a defined checkpoint for this test."
                    if not checkpoint_defined
                    else "The validation execution is already finalised."
                ),
                test_id=self.FORMAL_TEST_ID,
                validation_execution_id=execution.validation_execution_id,
                checkpoint_id=checkpoint_id if checkpoint_defined else None,
            ),
            ValidationWorkspaceAction(
                action_type="FINALISE_EXECUTION",
                available=finalise_available,
                reason_code=(
                    "AVAILABLE"
                    if finalise_available
                    else "DC006_CRITERION_DETERMINATION_REQUIRED"
                    if all_captured and criterion_method_available
                    else "CONTROLLED_COMPARISON_UNAVAILABLE"
                    if all_captured and not comparison_available
                    else "REQUIRED_CHECKPOINTS_MISSING"
                    if not all_captured
                    else "EXECUTION_FINALISED"
                ),
                reason=(
                    "All required checkpoints and the accepted comparison are available."
                    if finalise_available
                    else "All six checkpoints are preserved. Bind their backend-owned source records to the accepted DC-006 method and complete its criteria; the legacy I5 finalisation action cannot bypass that determination."
                    if all_captured and criterion_method_available
                    else "The accepted I5 definition has no automated comparison; I6 does not invent a verdict."
                    if all_captured and not comparison_available
                    else "All defined evidence checkpoints must be captured before finalisation."
                    if not all_captured
                    else "The validation execution is already finalised."
                ),
                test_id=self.FORMAL_TEST_ID,
                validation_execution_id=execution.validation_execution_id,
                checkpoint_id=checkpoint_id if checkpoint_defined else None,
            ),
        )

    def _exploration_validation_actions(
        self,
        snapshot: ScenarioSnapshot,
        definitions: tuple[LoadedValidationDefinition, ...],
        run_executions: tuple[ValidationExecutionSummary, ...],
    ) -> tuple[ValidationWorkspaceAction, ...]:
        actions: list[ValidationWorkspaceAction] = []
        for definition in definitions:
            if definition.definition.evidence_class is not EvidenceClass.EXPLORATORY:
                continue
            test_id = definition.definition.test_id
            cases = tuple(
                item
                for item in definition.definition.constituent_cases
                if item.selected_fault_section_id == snapshot.run.fault_section_id
            )
            action_cases = cases if definition.definition.constituent_cases else (None,)
            for case in action_cases:
                case_id = case.case_id if case is not None else None
                matching = tuple(
                    item
                    for item in run_executions
                    if item.execution.test_id == test_id
                    and item.execution.case_id == case_id
                )
                if not matching:
                    run_already_bound = bool(run_executions) and case is not None
                    available = (
                        snapshot.run.network_state_label is NetworkStateLabel.N0
                        and snapshot.run.status is not ScenarioRunStatus.CLOSED
                        and not run_already_bound
                    )
                    actions.append(
                        ValidationWorkspaceAction(
                            action_type="START_EXECUTION",
                            available=available,
                            reason_code=(
                                "AVAILABLE"
                                if available
                                else "RUN_ALREADY_BOUND"
                                if run_already_bound
                                else "REQUIRES_EXPLORATION_N0"
                            ),
                            reason=(
                                "Start this controlled constituent before scenario actions."
                                if available and case is not None
                                else "Start a separate EXPLORATORY execution before scenario actions."
                                if available
                                else "A constituent requires its own clean scenario run."
                                if run_already_bound
                                else "An exploratory execution may start only at the clean run boundary."
                            ),
                            test_id=test_id,
                            case_id=case_id,
                        )
                    )
                    continue

                current = matching[-1]
                execution = current.execution
                checkpoint_id = "CONTROLLED_RESULT"
                captured = {
                    item.checkpoint_id for item in current.evidence_snapshots
                }
                capture_available = (
                    execution.status is ValidationExecutionStatus.ACTIVE
                    and snapshot.run.fault_active
                    and checkpoint_id not in captured
                )
                comparison_available = (
                    case is not None
                    or definition.definition.comparison_expected_values is not None
                )
                finalise_available = (
                    execution.status is ValidationExecutionStatus.ACTIVE
                    and checkpoint_id in captured
                    and comparison_available
                )
                actions.append(
                    ValidationWorkspaceAction(
                        action_type="CAPTURE_CHECKPOINT",
                        available=capture_available,
                        reason_code=(
                            "AVAILABLE"
                            if capture_available
                            else "CHECKPOINT_ALREADY_CAPTURED"
                            if checkpoint_id in captured
                            else "EXPLORATION_RESULT_NOT_READY"
                        ),
                        reason=(
                            "Capture the current generic engineering result as EXPLORATORY evidence."
                            if capture_available
                            else "The controlled exploratory checkpoint is already preserved."
                            if checkpoint_id in captured
                            else "Initiate the selected fault before capturing exploratory evidence."
                        ),
                        test_id=test_id,
                        case_id=case_id,
                        validation_execution_id=execution.validation_execution_id,
                        checkpoint_id=checkpoint_id,
                    )
                )
                actions.append(
                    ValidationWorkspaceAction(
                        action_type="FINALISE_EXECUTION",
                        available=finalise_available,
                        reason_code=(
                            "AVAILABLE"
                            if finalise_available
                            else "REQUIRED_CHECKPOINTS_MISSING"
                            if checkpoint_id not in captured
                            else "CONTROLLED_COMPARISON_UNAVAILABLE"
                            if not comparison_available
                            else "EXECUTION_FINALISED"
                        ),
                        reason=(
                            "Compare preserved evidence with the controlled case oracle."
                            if finalise_available
                            else "Capture the controlled result before finalisation."
                            if checkpoint_id not in captured
                            else "This exploratory definition has no authorised automated comparison."
                            if not comparison_available
                            else "The validation execution is already finalised."
                        ),
                        test_id=test_id,
                        case_id=case_id,
                        validation_execution_id=execution.validation_execution_id,
                        checkpoint_id=(
                            checkpoint_id if checkpoint_id in captured else None
                        ),
                    )
                )
        return tuple(actions)

    @staticmethod
    def _workspace_action(
        snapshot: ScenarioSnapshot, action: AllowedAction
    ) -> WorkspaceAction:
        if snapshot.run.mode is ScenarioMode.EXPLORATION:
            offset_seconds = {
                ScenarioCommandType.INITIATE_FAULT: 10,
                ScenarioCommandType.ACKNOWLEDGE_ALARM: 11,
                ScenarioCommandType.RESTORE_NORMAL_SOURCE: 40,
                ScenarioCommandType.ASSESS_RESTORATION: 50,
                ScenarioCommandType.EXECUTE_RESTORATION: 55,
            }.get(action.command_type)
            if action.command_type is ScenarioCommandType.OPERATE_ISOLATION_DEVICE:
                offset_seconds = 20 + 10 * max(
                    0, snapshot.run.state_revision - 1
                )
        else:
            offset_seconds = formal_action_offset_seconds(
                action.command_type, action.target_entity_id
            )
        proposed = (
            max(
                snapshot.run.scenario_time,
                snapshot.run.initial_scenario_time
                + timedelta(seconds=offset_seconds),
            )
            if offset_seconds is not None
            else snapshot.run.scenario_time
        )
        target = action.target_entity_id or action.alarm_id or action.assessment_id
        action_id = f"{action.command_type.value}:{target or 'RUN'}"
        confirmation_required = action.command_type in {
            ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
            ScenarioCommandType.RESTORE_NORMAL_SOURCE,
            ScenarioCommandType.EXECUTE_RESTORATION,
            ScenarioCommandType.RESET_RUN,
        }
        confirmation_text = None
        if confirmation_required:
            if action.command_type is ScenarioCommandType.RESET_RUN:
                confirmation_text = (
                    "Create a new clean run and preserve the current run history. Reset is not undo."
                )
            else:
                confirmation_text = (
                    f"Simulated operation only — no real equipment control. Confirm "
                    f"{action.command_type.value} for {target}."
                )
        return WorkspaceAction(
            action_id=action_id,
            command_type=action.command_type,
            target_entity_id=action.target_entity_id,
            requested_state=action.requested_state,
            alarm_id=action.alarm_id,
            assessment_id=action.assessment_id,
            available=action.available,
            reason_code=action.reason_code,
            reason=action.reason,
            expected_revision=snapshot.run.state_revision,
            proposed_scenario_time=proposed,
            confirmation_required=confirmation_required,
            confirmation_text=confirmation_text,
        )
