"""I6 backend-owned workspace projection and formal browser-path gates."""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from ot_demo.application.scenario_coordinator import ScenarioCoordinator
from ot_demo.application.workspace_service import WorkspaceService
from ot_demo.domain.enums import (
    EvidenceClass,
    ScenarioCommandType,
    ScenarioMode,
    ValidationExecutionStatus,
    ValidationVerdict,
)
from ot_demo.infrastructure.build_identity import (
    ApplicationBuildManifest,
    BuildIdentityPayload,
)
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ot_demo.infrastructure.scenario_repository import ScenarioRepository
from ot_demo.infrastructure.validation_repository import ValidationRepository
from ot_demo.modules.scenario.models import InitialiseRunRequest, ScenarioCommandRequest
from ot_demo.modules.validation.catalogue import ValidationCatalogueLoader
from ot_demo.modules.validation.service import ValidationService


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "app/backend/ot_demo/infrastructure/migrations"
T0 = datetime(2030, 1, 1, tzinfo=timezone.utc)
IDENTITY = BuildIdentityPayload(
    git_commit="1" * 40,
    git_dirty=False,
    python_version="3.13.15",
    node_version="24.19.0",
    npm_version="11.17.0",
    dependency_lock_sha256={
        "requirements.lock": "2" * 64,
        "app/frontend/package-lock.json": "3" * 64,
    },
    backend_source_sha256="4" * 64,
    frontend_bundle_sha256="5" * 64,
)
MANIFEST = ApplicationBuildManifest(
    application_build_id=sha256_bytes(
        canonical_json_bytes(IDENTITY.model_dump(mode="json"))
    ),
    identity=IDENTITY,
)


def services(tmp_path: Path):
    loader = JsonConfigurationLoader(ROOT / "config/network")
    scenarios = ScenarioCoordinator(
        ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS),
        loader,
        application_build_manifest=MANIFEST,
    )
    catalogue = ValidationCatalogueLoader(
        ROOT / "validation/test-definitions/catalogue.json"
    )
    validation = ValidationService(
        ValidationRepository(tmp_path / "validation.sqlite3", MIGRATIONS),
        catalogue,
        scenarios,
        application_build_manifest=MANIFEST,
    )
    workspace = WorkspaceService(
        loader,
        scenarios,
        validation,
        catalogue,
        application_build_manifest=MANIFEST,
        presentation_path=ROOT / "config/presentation/network-one-line.v1.json",
    )
    return scenarios, validation, workspace


def initialise(scenarios: ScenarioCoordinator):
    return scenarios.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=1),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
        )
    )


def action(projection, command_type: ScenarioCommandType, target: str | None = None):
    return next(
        item
        for item in projection.allowed_actions
        if item.command_type is command_type
        and (target is None or item.target_entity_id == target)
        and item.available
    )


def execute_action(
    scenarios: ScenarioCoordinator,
    projection,
    command_type: ScenarioCommandType,
    command_number: int,
    target: str | None = None,
):
    item = action(projection, command_type, target)
    return scenarios.execute(
        projection.run.scenario_run_id,
        ScenarioCommandRequest(
            command_id=UUID(int=command_number),
            scenario_run_id=projection.run.scenario_run_id,
            actor="Graduate Engineer",
            expected_revision=item.expected_revision,
            command_type=item.command_type,
            scenario_time=item.proposed_scenario_time,
            target_entity_id=item.target_entity_id,
            requested_state=item.requested_state,
            alarm_id=item.alarm_id,
            assessment_id=item.assessment_id,
        ),
    )


@pytest.mark.i6
def test_workspace_bootstrap_and_n0_projection_preserve_authority_classes(
    tmp_path: Path,
) -> None:
    scenarios, _, workspace = services(tmp_path)
    bootstrap = workspace.bootstrap()
    initial = initialise(scenarios)
    projection = workspace.projection(initial.snapshot.run.scenario_run_id)

    assert bootstrap.definition_count == 24
    assert bootstrap.formal_test_id == "VT-FML-N0-N5-001"
    assert bootstrap.default_configuration_version == "1.1"
    assert bootstrap.default_scenario_time == T0
    assert "no real equipment control" in bootstrap.conceptual_boundary_notice.lower()

    assert len(projection.network_nodes) == 18
    assert len(projection.network_edges) == 18
    assert all(node.position.x >= 0 and node.position.y >= 0 for node in projection.network_nodes)
    assert all(node.derived.energised for node in projection.network_nodes if node.configured.entity_type == "SECTION")
    assert all(not node.fault_status == "FAULTED" for node in projection.network_nodes)
    assert projection.summary.affected_customer_count == 0
    assert projection.summary.current_assessment_status == "NOT_ASSESSED"

    feeders = {item.feeder_id: item for item in projection.feeders}
    assert feeders["FDR-A"].configured_normal_load_kw == 3200
    assert feeders["FDR-A"].derived_currently_supplied_load_kw == 3200
    assert feeders["FDR-B"].configured_normal_load_kw == 4200
    assert feeders["FDR-B"].derived_currently_supplied_load_kw == 4200

    initiate = action(projection, ScenarioCommandType.INITIATE_FAULT)
    assert initiate.proposed_scenario_time.isoformat() == "2030-01-01T00:00:10+00:00"
    assert initiate.expected_revision == 0
    assert projection.validation.progress.definition_count == 21
    assert projection.validation.progress.definitions_without_execution_count == 21
    assert projection.validation.progress.pass_count == 0
    assert projection.validation.actions[0].action_type == "START_EXECUTION"
    assert projection.validation.actions[0].available is True


@pytest.mark.i6
def test_formal_validation_progress_excludes_every_exploratory_record_state() -> None:
    definitions = ValidationCatalogueLoader(
        ROOT / "validation/test-definitions/catalogue.json"
    ).load()

    def execution(
        test_id: str,
        evidence_class: EvidenceClass,
        status: ValidationExecutionStatus,
        verdict: ValidationVerdict | None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            execution=SimpleNamespace(
                test_id=test_id,
                evidence_class=evidence_class,
                status=status,
                verdict=verdict,
            )
        )

    formal_active = execution(
        "VT-FML-N0-N5-001",
        EvidenceClass.FORMAL,
        ValidationExecutionStatus.ACTIVE,
        None,
    )
    exploratory_records = (
        execution(
            "VT-EXP-ALL-001",
            EvidenceClass.EXPLORATORY,
            ValidationExecutionStatus.ACTIVE,
            None,
        ),
        execution(
            "VT-EXP-ALL-001",
            EvidenceClass.EXPLORATORY,
            ValidationExecutionStatus.FINALISED,
            ValidationVerdict.PASS,
        ),
        execution(
            "VT-EXP-ROLE-001",
            EvidenceClass.EXPLORATORY,
            ValidationExecutionStatus.FINALISED,
            ValidationVerdict.FAIL,
        ),
        execution(
            "VT-EXP-SEPARATION-001",
            EvidenceClass.EXPLORATORY,
            ValidationExecutionStatus.FINALISED,
            ValidationVerdict.BLOCKED_TEST,
        ),
    )

    formal_only = WorkspaceService._validation_progress(
        definitions,
        (formal_active,),
    )
    with_exploratory = WorkspaceService._validation_progress(
        definitions,
        (formal_active, *exploratory_records),
    )

    assert len(definitions) == 24
    assert sum(
        item.definition.evidence_class is EvidenceClass.EXPLORATORY
        for item in definitions
    ) == 3
    assert with_exploratory == formal_only
    assert formal_only.model_dump() == {
        "definition_count": 21,
        "definitions_without_execution_count": 20,
        "execution_count": 1,
        "active_execution_count": 1,
        "finalised_execution_count": 0,
        "pass_count": 0,
        "fail_count": 0,
        "blocked_test_count": 0,
    }


@pytest.mark.i6
def test_workspace_actions_drive_exact_n0_n5_and_validation_progress_without_ui_logic(
    tmp_path: Path,
) -> None:
    scenarios, validation, workspace = services(tmp_path)
    initial = initialise(scenarios)
    run_id = initial.snapshot.run.scenario_run_id
    n0 = workspace.projection(run_id)
    execution = validation.start_execution("VT-FML-N0-N5-001", run_id)
    validation.capture_checkpoint(execution.validation_execution_id, "N0")

    execute_action(scenarios, n0, ScenarioCommandType.INITIATE_FAULT, 2)
    n1 = workspace.projection(run_id)
    assert n1.run.network_state_label.value == "N1"
    assert n1.summary.affected_customer_count == 850
    assert n1.summary.unacknowledged_alarm_count == 1
    validation.capture_checkpoint(execution.validation_execution_id, "N1")

    execute_action(scenarios, n1, ScenarioCommandType.ACKNOWLEDGE_ALARM, 3)
    acknowledged = workspace.projection(run_id)
    assert acknowledged.run.state_revision == 1
    assert acknowledged.summary.unacknowledged_alarm_count == 0

    execute_action(
        scenarios,
        acknowledged,
        ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
        4,
        "SW-A12",
    )
    isolation_one = workspace.projection(run_id)
    execute_action(
        scenarios,
        isolation_one,
        ScenarioCommandType.OPERATE_ISOLATION_DEVICE,
        5,
        "SW-A23",
    )
    n2 = workspace.projection(run_id)
    assert n2.run.network_state_label.value == "N2"
    assert n2.summary.affected_customer_count == 850
    assert n2.isolation_proof is not None and n2.isolation_proof.isolated
    validation.capture_checkpoint(execution.validation_execution_id, "N2")

    execute_action(
        scenarios,
        n2,
        ScenarioCommandType.RESTORE_NORMAL_SOURCE,
        6,
        "BRK-A",
    )
    n3 = workspace.projection(run_id)
    assert n3.run.network_state_label.value == "N3"
    assert n3.summary.affected_customer_count == 670
    assert n3.summary.restored_customer_delta == 180
    validation.capture_checkpoint(execution.validation_execution_id, "N3")

    execute_action(scenarios, n3, ScenarioCommandType.ASSESS_RESTORATION, 7)
    n4 = workspace.projection(run_id)
    assessment = n4.restoration_assessments[-1]
    assert n4.run.network_state_label.value == "N4"
    assert n4.summary.current_assessment_status == "PERMITTED"
    assert assessment.candidate is not None
    assert assessment.candidate.transferable_load_kw == 1500
    assert assessment.candidate.proposed_restored_customer_count == 450
    assert assessment.calculation is not None
    assert assessment.calculation.resulting_load_kw == 5700
    assert assessment.calculation.feeder_capacity_kw == 6000
    assert assessment.calculation.resulting_loading_percent == 95
    validation.capture_checkpoint(execution.validation_execution_id, "N4")

    execute_action(scenarios, n4, ScenarioCommandType.EXECUTE_RESTORATION, 8)
    n5 = workspace.projection(run_id)
    assert n5.run.network_state_label.value == "N5"
    assert n5.summary.affected_customer_count == 220
    assert n5.summary.restored_customer_delta == 450
    validation.capture_checkpoint(execution.validation_execution_id, "N5")
    final_projection = workspace.projection(run_id)

    feeders = {item.feeder_id: item for item in final_projection.feeders}
    assert feeders["FDR-B"].configured_normal_load_kw == 4200
    assert feeders["FDR-B"].derived_currently_supplied_load_kw == 5700
    assert [event.event_sequence for event in final_projection.events] == list(
        range(1, len(final_projection.events) + 1)
    )
    assert final_projection.validation.progress.execution_count == 1
    assert final_projection.validation.progress.active_execution_count == 1
    assert final_projection.validation.progress.pass_count == 0
    assert final_projection.validation.progress.definitions_without_execution_count == 20
    finalise = next(
        item
        for item in final_projection.validation.actions
        if item.action_type == "FINALISE_EXECUTION"
    )
    assert finalise.available is False
    assert finalise.reason_code == "CONTROLLED_COMPARISON_UNAVAILABLE"
    assert "does not invent a verdict" in finalise.reason
