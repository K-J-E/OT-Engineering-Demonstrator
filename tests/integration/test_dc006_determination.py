"""DC-006 determination authority, source-adapter and lifecycle assurance."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from uuid import UUID

import pytest

from ot_demo.application.scenario_coordinator import ScenarioCoordinator
from ot_demo.domain.enums import (
    CriterionFindingStatus,
    DeterminationCompletenessStatus,
    DeterminationContextKind,
    DeterminationSourceAdapterKind,
    EvidenceClass,
    ScenarioMode,
    SwitchState,
    TelemetryQuality,
    ValidationVerdict,
)
from ot_demo.infrastructure.build_identity import ApplicationBuildManifest, BuildIdentityPayload
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.infrastructure.determination_repository import DeterminationRepository
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ot_demo.infrastructure.scenario_repository import ScenarioRepository
from ot_demo.infrastructure.validation_repository import ValidationRepository
from ot_demo.modules.scenario.models import InitialiseRunRequest
from ot_demo.modules.telemetry.models import TelemetryPoint
from ot_demo.modules.telemetry.service import TelemetryValidityService
from ot_demo.modules.validation.catalogue import ValidationCatalogueResolver
from ot_demo.modules.validation.determination import DeterminationBoundaryError, DeterminationService
from ot_demo.modules.validation.models import AuthoritativeRecordSnapshot
from ot_demo.modules.validation.service import ValidationService
from ot_demo.modules.validation.source_adapters import (
    SourceAdapterError,
    freeze_authoritative_record,
)


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "app/backend/ot_demo/infrastructure/migrations"
CATALOGUE = ROOT / "validation/test-definitions/catalogue.json"
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
BUILD = ApplicationBuildManifest(
    application_build_id=sha256_bytes(canonical_json_bytes(IDENTITY.model_dump(mode="json"))),
    identity=IDENTITY,
)


def services(tmp_path: Path):
    database = tmp_path / "validation.sqlite3"
    configurations = JsonConfigurationLoader(ROOT / "config/network")
    scenarios = ScenarioCoordinator(
        ScenarioRepository(tmp_path / "scenario.sqlite3", MIGRATIONS),
        configurations,
        application_build_manifest=BUILD,
    )
    catalogue = ValidationCatalogueResolver(
        CATALOGUE,
        (
            CATALOGUE.parent / "history/v1.0/catalogue.json",
            CATALOGUE.parent / "history/v1.1/catalogue.json",
        ),
    )
    validation_repository = ValidationRepository(database, MIGRATIONS)
    validation = ValidationService(
        validation_repository,
        catalogue,
        scenarios,
        configurations,
        application_build_manifest=BUILD,
    )
    determination_repository = DeterminationRepository(database, MIGRATIONS)
    determination = DeterminationService(
        determination_repository,
        validation_repository,
        catalogue,
        application_build_manifest=BUILD,
        configuration_loader=configurations,
    )
    return scenarios, catalogue, validation, determination, determination_repository


def record(
    record_type: str,
    payload,
    *,
    family: DeterminationSourceAdapterKind,
    evidence_class: EvidenceClass = EvidenceClass.FORMAL,
    configuration_id: str | None = "network-configuration-v1.1",
    configuration_version: str | None = "1.1",
    scenario_run_id=None,
    validation_execution_id=None,
) -> AuthoritativeRecordSnapshot:
    owners = {
        DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE: "configuration-package-authority",
        DeterminationSourceAdapterKind.SCENARIO_STATE: "scenario-topology-outage-authority",
        DeterminationSourceAdapterKind.CONTROLLED_FIXTURE: "controlled-fixture-execution-authority",
        DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY: "operational-event-history-authority",
        DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY: "validation-investigation-history-authority",
        DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT: "deterministic-repeat-authority",
        DeterminationSourceAdapterKind.EVIDENCE_PACKAGE: "evidence-package-authority",
        DeterminationSourceAdapterKind.NFR_REVIEW: "engineering-review-assurance-authority",
    }
    return freeze_authoritative_record(
        record_type=record_type,
        record_id=f"{record_type}:controlled-test-record",
        owner_module=owners[family],
        payload=payload,
        application_build_id=BUILD.application_build_id,
        evidence_class=evidence_class,
        configuration_id=configuration_id,
        configuration_version=configuration_version,
        scenario_run_id=scenario_run_id,
        validation_execution_id=validation_execution_id,
    )


def bind(
    determination: DeterminationService,
    attempt_id,
    sources,
    *,
    scenario_run_id=None,
    validation_execution_id=None,
):
    return determination.bind_context(
        validation_attempt_id=attempt_id,
        role_source_record_ids={role: item.source_record_id for role, item in sources.items()},
        frozen_at=T0 + timedelta(seconds=1),
        scenario_run_id=scenario_run_id,
        validation_execution_id=validation_execution_id,
    )


@pytest.mark.dc006
def test_real_configuration_adapter_passes_and_owns_no_run_execution(tmp_path: Path) -> None:
    _, catalogue, validation, determination, repository = services(tmp_path)
    _, attempt = validation.create_target_selection("VT-CFG-BASE-001", created_at=T0)
    sources = determination.capture_configuration_package_sources(
        attempt.validation_attempt_id, created_at=T0
    )
    context = bind(determination, attempt.validation_attempt_id, sources)
    findings = determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    assert len(findings) == len(catalogue.get_method("VT-CFG-BASE-001").criteria) == 5
    assert {item.status for item in findings} == {CriterionFindingStatus.SATISFIED}
    result = determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=3)
    )
    assert result.verdict is ValidationVerdict.PASS
    assert result.validation_execution_id is not None
    execution = validation._repository.get_execution(result.validation_execution_id)
    assert execution.context_kind is DeterminationContextKind.PRESERVED_RECORD_SET
    assert execution.scenario_run_id is None and execution.scenario_mode is None
    assert execution.started_scenario_time is None and execution.started_at is not None
    assert execution.evidence_snapshot_ids == ()
    assert repository.get_result(result.executed_result_id) == result


@pytest.mark.dc006
def test_configuration_adapter_actual_difference_change_derives_fail(tmp_path: Path) -> None:
    _, _, validation, determination, _ = services(tmp_path)
    _, attempt = validation.create_target_selection("VT-CFG-BASE-001", created_at=T0)
    sources = determination.capture_configuration_package_sources(
        attempt.validation_attempt_id, created_at=T0
    )
    original = sources["EXACT_PACKAGE_COMPARISON"]
    authority = determination._repository.get_source(original.source_record_id)
    from ot_demo.modules.validation.source_adapters import AuthoritativeSourceAdapterRegistry

    records = list(AuthoritativeSourceAdapterRegistry.records(authority))
    comparison = next(item for item in records if item.record_type == "ConfigurationComparisonResult")
    changed = record(
        "ConfigurationComparisonResult",
        {
            "differences": comparison.canonical_payload["differences"],
            "uncontrolled_differences": [
                {"path": "feeders.FDR-B.capacity_kw", "before": 6000, "after": 5999}
            ],
        },
        family=DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE,
        configuration_id=None,
        configuration_version=None,
    )
    aggregate = next(item for item in records if item.record_type == "ConfigurationPackageAdapter")
    sources["EXACT_PACKAGE_COMPARISON"] = determination.capture_authoritative_source(
        validation_attempt_id=attempt.validation_attempt_id,
        source_type=DeterminationSourceAdapterKind.CONFIGURATION_PACKAGE,
        source_role="EXACT_PACKAGE_COMPARISON",
        evidence_class=EvidenceClass.FORMAL,
        authority_records=(aggregate, changed),
        created_at=T0,
        evidence_references=("controlled:changed-package-comparison",),
    )
    context = bind(determination, attempt.validation_attempt_id, sources)
    findings = determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    assert next(item for item in findings if item.criterion_id == "CFG-05").status is (
        CriterionFindingStatus.NOT_SATISFIED
    )
    assert determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=3)
    ).verdict is ValidationVerdict.FAIL


@pytest.mark.dc006
def test_fixture_execution_uses_real_telemetry_classification_and_no_run(tmp_path: Path) -> None:
    _, _, validation, determination, _ = services(tmp_path)
    _, attempt = validation.create_target_selection("VT-TEL-STALE-001", created_at=T0)
    point = TelemetryPoint(
        point_id="TEL-BRK-B-STATE",
        entity_id="BRK-B",
        value=SwitchState.CLOSED,
        quality=TelemetryQuality.GOOD,
        last_update_scenario_time=T0,
        revision=1,
    )
    validity = TelemetryValidityService().classify(
        point, T0 + timedelta(milliseconds=60_001)
    )
    telemetry_payload = validity.model_dump(mode="json") | {
        "valid": validity.overall_valid,
        "__field_set_projections__": {
            "quality,freshness": "Quality remains GOOD while freshness is STALE; the two dimensions are not collapsed.",
            "valid,reason_codes": "Overall validity is false and includes the controlled stale/freshness reason.",
        },
    }
    source = determination.capture_authoritative_source(
        validation_attempt_id=attempt.validation_attempt_id,
        source_type=DeterminationSourceAdapterKind.CONTROLLED_FIXTURE,
        source_role="STALE_60001_MS",
        evidence_class=EvidenceClass.FORMAL,
        authority_records=(
            record("TelemetryValidityResult", telemetry_payload, family=DeterminationSourceAdapterKind.CONTROLLED_FIXTURE),
            record(
                "RestorationAssessment",
                {
                    "outcome": "BLOCKED",
                    "reasons": ["TELEMETRY_STALE"],
                    "__field_set_projections__": {
                        "outcome,reasons": "Restoration assessment outcome is operational BLOCKED, not REJECTED; the validation criterion is satisfied because BLOCKED is expected."
                    },
                },
                family=DeterminationSourceAdapterKind.CONTROLLED_FIXTURE,
            ),
            record(
                "ActionProjection",
                {"execute_restoration": {"available": False}},
                family=DeterminationSourceAdapterKind.CONTROLLED_FIXTURE,
            ),
        ),
        created_at=T0,
        evidence_references=("fixture:FIX-TEL-STALE-001",),
    )
    context = bind(determination, attempt.validation_attempt_id, {"STALE_60001_MS": source})
    findings = determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    assert {item.status for item in findings} == {CriterionFindingStatus.SATISFIED}
    result = determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=3)
    )
    execution = validation._repository.get_execution(result.validation_execution_id)
    assert execution.context_kind is DeterminationContextKind.CONTROLLED_FIXTURE_EXECUTION
    assert execution.scenario_run_id is None


@pytest.mark.dc006
def test_scenario_adapter_reads_real_topology_outage_and_execution_provenance(tmp_path: Path) -> None:
    scenarios, _, validation, determination, _ = services(tmp_path)
    initial = scenarios.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=1), actor="Graduate Engineer", mode=ScenarioMode.FORMAL,
            configuration_version="1.1", scenario_time=T0,
        )
    )
    snapshot = initial.snapshot
    execution = validation.start_execution(
        "VT-TOP-NORMAL-001", snapshot.run.scenario_run_id
    )
    evidence = validation.capture_checkpoint(execution.validation_execution_id, "CONTROLLED_RESULT")
    energised = sorted(item.section_id for item in snapshot.topology.sections if item.energised)
    de_energised = sorted(item.section_id for item in snapshot.topology.sections if not item.energised)
    loads = {
        item.feeder_id: item.currently_supplied_load_kw
        for item in snapshot.topology.feeder_loads
    }
    assert energised == ["SEC-A1", "SEC-A2", "SEC-A3", "SEC-A4", "SEC-B1", "SEC-B2", "SEC-B3", "SEC-B4"]
    assert de_energised == [] and loads == {"FDR-A": 3200, "FDR-B": 4200}
    common = dict(
        family=DeterminationSourceAdapterKind.SCENARIO_STATE,
        configuration_id=snapshot.run.configuration_id,
        configuration_version=str(snapshot.run.configuration_version),
        scenario_run_id=snapshot.run.scenario_run_id,
        validation_execution_id=execution.validation_execution_id,
    )
    run_source = determination.capture_authoritative_source(
        validation_attempt_id=execution.validation_attempt_id,
        source_type=DeterminationSourceAdapterKind.SCENARIO_STATE,
        source_role="CORRECTED_NORMAL_RUN",
        evidence_class=EvidenceClass.FORMAL,
        authority_records=(record(
            "ScenarioSnapshot",
            {
                "configuration_identity": snapshot.run.configuration_id,
                "device_states": {item.entity_id: item.value.value for item in snapshot.telemetry},
                "source_availability": {key: value.value for key, value in snapshot.run.source_availability.items()},
                "__field_set_projections__": {
                    "configuration_identity,device_states,source_availability": "Corrected Network Configuration v1.1 is bound; BRK-A/BRK-B and all sectionalisers are CLOSED, TS-01 is OPEN, and both feeder sources are AVAILABLE."
                },
            },
            **common,
        ),),
        created_at=T0,
        evidence_references=(f"evidence-snapshot:{evidence.evidence_snapshot_id}",),
    )
    checkpoint_source = determination.capture_authoritative_source(
        validation_attempt_id=execution.validation_attempt_id,
        source_type=DeterminationSourceAdapterKind.SCENARIO_STATE,
        source_role="N0_CHECKPOINT",
        evidence_class=EvidenceClass.FORMAL,
        authority_records=(
            record(
                "TopologyResult",
                {
                    "energised_section_ids": energised,
                    "de_energised_section_ids": de_energised,
                    "section_source_feeder_ids": {
                        "__controlled_projection__": "A1–A4 trace only to FDR-A and B1–B4 trace only to FDR-B."
                    },
                    "feeder_loads": loads,
                    "radiality_status": snapshot.topology.radiality_status.value,
                    "__field_set_projections__": {
                        "energised_section_ids,de_energised_section_ids": "The energised section set is exactly SEC-A1–SEC-A4 and SEC-B1–SEC-B4; the de-energised set is empty."
                    },
                },
                **common,
            ),
            record(
                "OutageResult",
                {
                    "de_energised_section_ids": list(snapshot.outage.de_energised_section_ids),
                    "affected_customer_count": snapshot.outage.affected_customer_count,
                    "__field_set_projections__": {
                        "de_energised_section_ids,affected_customer_count": "Outage extent is empty and affected-customer count is zero."
                    },
                },
                **common,
            ),
        ),
        created_at=T0,
        evidence_references=(f"evidence-snapshot:{evidence.evidence_snapshot_id}",),
    )
    context = bind(
        determination,
        execution.validation_attempt_id,
        {"CORRECTED_NORMAL_RUN": run_source, "N0_CHECKPOINT": checkpoint_source},
        scenario_run_id=snapshot.run.scenario_run_id,
        validation_execution_id=execution.validation_execution_id,
    )
    findings = determination.evaluate_machine_criteria(context.determination_context_id, evaluated_at=T0)
    assert {item.status for item in findings} == {CriterionFindingStatus.SATISFIED}
    result = determination.finalise_result(context.determination_context_id, finalised_at=T0)
    assert result.validation_execution_id == execution.validation_execution_id
    assert result.evidence_snapshot_ids == (evidence.evidence_snapshot_id,)


@pytest.mark.dc006
def test_adapter_registry_rejects_arbitrary_owner_and_synthetic_selector_values(tmp_path: Path) -> None:
    _, _, validation, determination, _ = services(tmp_path)
    _, attempt = validation.create_target_selection("VT-DET-REPEAT-001", created_at=T0)
    valid = record(
        "DeterministicRepeatAdapter",
        {"members": []},
        family=DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
    )
    wrong_owner = valid.model_copy(update={"owner_module": "caller-selected-owner"})
    with pytest.raises(SourceAdapterError, match="owner"):
        determination.capture_authoritative_source(
            validation_attempt_id=attempt.validation_attempt_id,
            source_type=DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
            source_role="COMPARISON_PROFILE",
            evidence_class=EvidenceClass.FORMAL,
            authority_records=(wrong_owner,),
            created_at=T0,
        )
    payload = {
        "source_type": "DETERMINISTIC_REPEAT",
        "owner_module": "deterministic-repeat-authority",
        "source_role": "COMPARISON_PROFILE",
        "selector_values": {"DeterministicRepeatAdapter.members": "caller answer"},
    }
    with pytest.raises(ValueError, match="synthetic selector-value"):
        from ot_demo.modules.validation.models import DeterminationSourceRecord

        DeterminationSourceRecord(
            source_record_id=UUID(int=99),
            source_type=DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
            owner_module="deterministic-repeat-authority",
            source_role="COMPARISON_PROFILE",
            validation_attempt_id=attempt.validation_attempt_id,
            test_id="VT-DET-REPEAT-001",
            catalogue_version="1.2",
            catalogue_sha256="6" * 64,
            method_id="DM-DET-REPEAT-001",
            method_version="1.0",
            method_sha256="7" * 64,
            eligible_criterion_ids=("DET-01",),
            application_build_id=BUILD.application_build_id,
            evidence_class=EvidenceClass.FORMAL,
            canonical_payload=payload,
            canonical_payload_sha256=sha256_bytes(canonical_json_bytes(payload)),
            created_at=T0,
        )


@pytest.mark.dc006
def test_engineering_review_owns_real_no_run_execution_and_backend_verdict(tmp_path: Path) -> None:
    _, catalogue, validation, determination, _ = services(tmp_path)
    _, attempt = validation.create_target_selection("VT-NFR-REVIEW-001", created_at=T0)
    family = DeterminationSourceAdapterKind.NFR_REVIEW
    role_payloads = {
        "REVIEWED_APPLICATION_BUILD": (
            record(
                "BuildRuntimeAdapter",
                {
                    "network_binding": "Runtime binds only to loopback and no external operational service endpoint is configured."
                },
                family=family,
            ),
        ),
        "CONTROLLED_SURFACE_SET": (
            record(
                "ReviewSurfaceAdapter",
                {
                    "identity_links": "Controlled build, Network Configuration, Validation Catalogue and test identity fields are present and resolve to bound records.",
                    "controlled_surface_ids": "The controlled surface registry equals exactly the eight Demonstrator Design views: Start / Run Setup; Operational Workspace; Telemetry & Events; Restoration Assessment; Formal Validation; Evidence Library; Defect Investigation; Engineering Basis.",
                    "notice_and_identity_profile_by_surface": "Every exact controlled surface contains the fixed visible notice 'Simulated operation only — no real equipment control' and the exact surface-specific identity profile frozen by DC-006.",
                },
                family=family,
            ),
        ),
        "STRUCTURAL_RECORD_SET": (
            record(
                "SchemaAndProjectionAdapter",
                {
                    "structural_record_members_and_owners": "The structural record registry equals the exact frozen DC-006 Structural Record Set and each member remains assigned to its controlled information class/owner.",
                    "structural_record_membership_anomalies": [],
                },
                family=family,
            ),
            record(
                "ConfigurationPackageAdapter",
                {
                    "entity_schema_assignments": "Both feeder structures use the common entity schemas and information sets."
                },
                family=family,
            ),
        ),
        "REVIEW_PROPOSAL": (
            record("EngineeringReviewRecord", {"stage": "PROPOSAL"}, family=family),
        ),
        "FINAL_REVIEW_FINDINGS": (
            record("EngineeringReviewRecord", {"stage": "FINAL_REVIEW"}, family=family),
        ),
    }
    sources = {
        role: determination.capture_authoritative_source(
            validation_attempt_id=attempt.validation_attempt_id,
            source_type=family,
            source_role=role,
            evidence_class=EvidenceClass.FORMAL,
            authority_records=records,
            created_at=T0,
            evidence_references=(f"controlled-review-role:{role}",),
        )
        for role, records in role_payloads.items()
    }
    context = bind(determination, attempt.validation_attempt_id, sources)
    assert context.context_kind is DeterminationContextKind.ENGINEERING_REVIEW
    assert context.scenario_run_id is None and context.validation_execution_id is not None
    machine = determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    assert {item.status for item in machine} == {CriterionFindingStatus.SATISFIED}
    method = catalogue.get_method("VT-NFR-REVIEW-001")
    for index, criterion in enumerate(
        item for item in method.criteria if item.kind.value == "ENGINEERING_REVIEW"
    ):
        proposal = determination.propose_review_finding(
            context.determination_context_id,
            criterion.criterion_id,
            proposed_finding=CriterionFindingStatus.SATISFIED,
            proposer_actor_id="graduate-engineer",
            reason="Fixed proposition is supported by the frozen exact review membership.",
            proposed_at=T0 + timedelta(seconds=3 + index),
        )
        determination.finalise_review_finding(
            proposal.review_proposal_id,
            reviewer_actor_id="independent-reviewer",
            final_finding=CriterionFindingStatus.SATISFIED,
            reason="Independent criterion finding accepted against frozen evidence.",
            finalised_at=T0 + timedelta(seconds=10 + index),
        )
    result = determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=20)
    )
    assert result.verdict is ValidationVerdict.PASS
    execution = validation._repository.get_execution(result.validation_execution_id)
    assert execution.context_kind is DeterminationContextKind.ENGINEERING_REVIEW
    assert execution.scenario_run_id is None and execution.status.value == "FINALISED"


@pytest.mark.dc006
@pytest.mark.parametrize(
    ("test_id", "source_role", "family", "record_type", "selector", "payload", "expected"),
    [
        (
            "VT-ALM-EVT-001", "OPERATIONAL_EVENT_SEQUENCE",
            DeterminationSourceAdapterKind.OPERATIONAL_EVENT_HISTORY,
            "OperationalEventAdapter", "OperationalEventAdapter.unregistered_event_type_ids",
            {"unregistered_event_type_ids": []}, [],
        ),
        (
            "VT-CFG-INV-001", "V1_0_FAILURE",
            DeterminationSourceAdapterKind.VALIDATION_INVESTIGATION_HISTORY,
            "InvestigationAdapter", "InvestigationAdapter.failure",
            {"failure": {"configuration_version": "1.0", "affected_customers": 400, "verdict": "FAIL"}},
            {"configuration_version": "1.0", "affected_customers": 400, "verdict": "FAIL"},
        ),
        (
            "VT-DET-REPEAT-001", "COMPARISON_PROFILE",
            DeterminationSourceAdapterKind.DETERMINISTIC_REPEAT,
            "DeterministicRepeatAdapter", "DeterministicRepeatAdapter.canonical_outputs",
            {"canonical_outputs": {"left": {"run_id": "a", "value": 850}, "right": {"run_id": "b", "value": 850}, "excluded_fields": ["run_id"]}},
            {"left": {"run_id": "a", "value": 850}, "right": {"run_id": "b", "value": 850}, "excluded_fields": ["run_id"]},
        ),
        (
            "VT-PKG-EVIDENCE-001", "PACKAGE_REGISTRY",
            DeterminationSourceAdapterKind.EVIDENCE_PACKAGE,
            "EvidencePackageAdapter", "EvidencePackageAdapter.link_verification",
            {"link_verification": True}, True,
        ),
        (
            "VT-NFR-REVIEW-001", "CONTROLLED_SURFACE_SET",
            DeterminationSourceAdapterKind.NFR_REVIEW,
            "ReviewSurfaceAdapter", "ReviewSurfaceAdapter.controlled_surface_ids",
            {"controlled_surface_ids": ["Start / Run Setup", "Operational Workspace"]},
            ["Start / Run Setup", "Operational Workspace"],
        ),
    ],
)
def test_representative_authority_families_extract_from_hash_verified_records(
    tmp_path: Path, test_id, source_role, family, record_type, selector, payload, expected
) -> None:
    _, _, validation, determination, repository = services(tmp_path)
    _, attempt = validation.create_target_selection(test_id, created_at=T0)
    source = determination.capture_authoritative_source(
        validation_attempt_id=attempt.validation_attempt_id,
        source_type=family,
        source_role=source_role,
        evidence_class=EvidenceClass.FORMAL,
        authority_records=(record(record_type, payload, family=family),),
        created_at=T0,
        evidence_references=("controlled:preserved-record",),
    )
    from ot_demo.modules.validation.source_adapters import AuthoritativeSourceAdapterRegistry

    persisted = repository.get_source(source.source_record_id)
    assert AuthoritativeSourceAdapterRegistry.resolve(persisted, selector) == expected


@pytest.mark.dc006
def test_context_result_and_procedure_execution_are_database_immutable(tmp_path: Path) -> None:
    _, _, validation, determination, repository = services(tmp_path)
    _, attempt = validation.create_target_selection("VT-CFG-BASE-001", created_at=T0)
    sources = determination.capture_configuration_package_sources(attempt.validation_attempt_id, created_at=T0)
    context = bind(determination, attempt.validation_attempt_id, sources)
    with sqlite3.connect(repository.database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="result execution does not match"):
            connection.execute(
                "INSERT INTO dc006_executed_validation_results "
                "(executed_result_id,validation_attempt_id,determination_context_id,"
                "validation_execution_id,test_id,case_id,catalogue_version,catalogue_sha256,"
                "method_id,method_sha256,verdict,result_sha256,finalised_at_ms,payload_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(UUID(int=98)), str(attempt.validation_attempt_id),
                    str(context.determination_context_id), str(UUID(int=99)),
                    context.test_id, context.case_id, str(context.catalogue_version),
                    context.catalogue_sha256, context.method_id, context.method_sha256,
                    "PASS", "8" * 64, int(T0.timestamp() * 1000), "{}",
                ),
            )
    determination.evaluate_machine_criteria(context.determination_context_id, evaluated_at=T0)
    result = determination.finalise_result(context.determination_context_id, finalised_at=T0)
    with sqlite3.connect(repository.database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE procedure_validation_executions SET verdict='FAIL' WHERE validation_execution_id=?",
                (str(result.validation_execution_id),),
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE criterion_findings SET status='NOT_SATISFIED' WHERE determination_context_id=?",
                (str(context.determination_context_id),),
            )


@pytest.mark.dc006
def test_source_from_another_attempt_cannot_be_rebound_even_for_same_method(tmp_path: Path) -> None:
    _, _, validation, determination, _ = services(tmp_path)
    _, first = validation.create_target_selection("VT-CFG-BASE-001", created_at=T0)
    first_sources = determination.capture_configuration_package_sources(
        first.validation_attempt_id, created_at=T0
    )
    _, second = validation.create_target_selection(
        "VT-CFG-BASE-001", created_at=T0 + timedelta(seconds=1)
    )
    with pytest.raises(DeterminationBoundaryError, match="another validation attempt"):
        bind(determination, second.validation_attempt_id, first_sources)
