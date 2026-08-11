"""DC-006 method, context, finding, review and deterministic-result gates."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from uuid import UUID
from zipfile import ZipFile
import json

import pytest

from ot_demo.application.scenario_coordinator import ScenarioCoordinator
from ot_demo.domain.enums import (
    CriterionFindingStatus,
    DeterminationCompletenessStatus,
    DeterminationContextKind,
    EvidenceClass,
    ScenarioCommandType,
    ScenarioMode,
    ValidationVerdict,
)
from ot_demo.infrastructure.build_identity import ApplicationBuildManifest, BuildIdentityPayload
from ot_demo.infrastructure.configuration_loader import JsonConfigurationLoader
from ot_demo.infrastructure.determination_repository import DeterminationRepository
from ot_demo.infrastructure.evidence_package_repository import EvidencePackageRepository
from ot_demo.infrastructure.hashing import canonical_json_bytes, sha256_bytes
from ot_demo.infrastructure.investigation_repository import InvestigationRepository
from ot_demo.infrastructure.scenario_repository import ScenarioRepository
from ot_demo.infrastructure.validation_repository import ValidationRepository
from ot_demo.modules.validation.catalogue import (
    ValidationCatalogueLoader,
    ValidationCatalogueResolver,
)
from ot_demo.modules.validation.determination import (
    DeterminationBoundaryError,
    DeterminationService,
)
from ot_demo.modules.validation.service import ValidationService
from ot_demo.modules.scenario.models import InitialiseRunRequest, ScenarioCommandRequest
from ot_demo.modules.evidence_export.service import EvidenceExportService


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
    )
    return catalogue, validation, determination, determination_repository


def scenario_services(tmp_path: Path):
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
    )
    return scenarios, catalogue, validation, determination


def prepare_record_context(
    tmp_path: Path,
    test_id: str,
    *,
    omit_selector: str | None = None,
):
    catalogue, validation, determination, repository = services(tmp_path)
    _, attempt = validation.create_target_selection(test_id, created_at=T0)
    method = catalogue.get_method(test_id)
    selector_values = {
        criterion.source_selector: criterion.expected_value
        for criterion in method.criteria
        if criterion.kind.value == "MACHINE_COMPARISON"
        and criterion.source_selector != omit_selector
    }
    source = determination.register_authoritative_source(
        source_type="PRESERVED_TEST_SOURCE_SET",
        owner_module="validation-assurance-test-authority",
        evidence_class=method.evidence_class,
        selector_values=selector_values,
        evidence_references=("controlled:test-source",),
        created_at=T0,
        configuration_id="network-configuration-v1.1",
        configuration_version="1.1",
    )
    context = determination.bind_context(
        validation_attempt_id=attempt.validation_attempt_id,
        role_source_record_ids={role: source.source_record_id for role in method.required_context_roles},
        frozen_at=T0 + timedelta(seconds=1),
    )
    return catalogue, validation, determination, repository, attempt, method, context


@pytest.mark.dc006
def test_preserved_record_method_derives_pass_without_client_verdict(tmp_path: Path) -> None:
    _, validation, determination, repository, attempt, method, context = prepare_record_context(
        tmp_path, "VT-CFG-BASE-001"
    )

    findings = determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    assert len(findings) == len(method.criteria) == 5
    assert {item.status for item in findings} == {CriterionFindingStatus.SATISFIED}
    assert determination.completeness(context.determination_context_id).status is DeterminationCompletenessStatus.COMPLETE

    result = determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=3)
    )
    assert result.verdict is ValidationVerdict.PASS
    assert result.validation_execution_id is None
    assert result.determination_context_id == context.determination_context_id
    assert len(result.criterion_finding_ids) == 5
    assert repository.get_result(result.executed_result_id) == result
    assert validation._repository.get_attempt(attempt.validation_attempt_id).status.value == "EXECUTED"


@pytest.mark.dc006
def test_missing_source_evidence_remains_incomplete_and_creates_no_result(tmp_path: Path) -> None:
    catalogue_selector = "ConfigurationComparisonResult.uncontrolled_differences"
    catalogue, _, determination, _, _, _, context = prepare_record_context(
        tmp_path,
        "VT-CFG-BASE-001",
        omit_selector=catalogue_selector,
    )
    assert catalogue_selector in {
        item.source_selector for item in catalogue.get_method("VT-CFG-BASE-001").criteria
    }
    determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    completeness = determination.completeness(context.determination_context_id)
    assert completeness.status is DeterminationCompletenessStatus.INCOMPLETE
    assert "CFG-05" in completeness.missing_criterion_ids
    with pytest.raises(DeterminationBoundaryError, match="incomplete criteria"):
        determination.finalise_result(
            context.determination_context_id, finalised_at=T0 + timedelta(seconds=3)
        )


@pytest.mark.dc006
def test_complete_authoritative_mismatch_derives_fail_without_caller_verdict(
    tmp_path: Path,
) -> None:
    selector = "ConfigurationComparisonResult.uncontrolled_differences"
    catalogue, validation, determination, repository = services(tmp_path)
    method = catalogue.get_method("VT-CFG-BASE-001")
    _, attempt = validation.create_target_selection("VT-CFG-BASE-001", created_at=T0)
    values = {
        criterion.source_selector: (
            "unexpected controlled mismatch"
            if criterion.source_selector == selector
            else criterion.expected_value
        )
        for criterion in method.criteria
        if criterion.kind.value == "MACHINE_COMPARISON"
    }
    source = determination.register_authoritative_source(
        source_type="PRESERVED_TEST_SOURCE_SET",
        owner_module="validation-assurance-test-authority",
        evidence_class=method.evidence_class,
        selector_values=values,
        evidence_references=("controlled:mismatch-source",),
        created_at=T0,
        configuration_id="network-configuration-v1.1",
        configuration_version="1.1",
    )
    context = determination.bind_context(
        validation_attempt_id=attempt.validation_attempt_id,
        role_source_record_ids={role: source.source_record_id for role in method.required_context_roles},
        frozen_at=T0 + timedelta(seconds=1),
    )
    findings = determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    assert next(item for item in findings if item.criterion_id == "CFG-05").status is (
        CriterionFindingStatus.NOT_SATISFIED
    )
    result = determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=3)
    )
    assert result.verdict is ValidationVerdict.FAIL
    assert repository.get_result(result.executed_result_id) == result


@pytest.mark.dc006
def test_fixture_method_binds_hash_identified_fixture_and_no_scenario_run(tmp_path: Path) -> None:
    catalogue, validation, determination, _, _, method, context = prepare_record_context(
        tmp_path, "VT-TEL-STALE-001"
    )
    assert method.context_kind is DeterminationContextKind.CONTROLLED_FIXTURE_EXECUTION
    assert method.controlled_fixture is not None
    assert method.controlled_fixture.fixture_id == "FIX-TEL-STALE-001"
    assert context.scenario_run_id is None
    assert context.validation_execution_id is None
    determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    assert determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=3)
    ).verdict is ValidationVerdict.PASS
    assert catalogue.get("VT-TEL-STALE-001").catalogue_version == "1.2"


@pytest.mark.dc006
def test_context_rejects_source_provenance_class_mismatch(tmp_path: Path) -> None:
    catalogue, validation, determination, _ = services(tmp_path)
    _, attempt = validation.create_target_selection("VT-CFG-BASE-001", created_at=T0)
    method = catalogue.get_method("VT-CFG-BASE-001")
    source = determination.register_authoritative_source(
        source_type="PRESERVED_TEST_SOURCE_SET",
        owner_module="validation-assurance-test-authority",
        evidence_class=EvidenceClass.EXPLORATORY,
        selector_values={
            criterion.source_selector: criterion.expected_value
            for criterion in method.criteria
            if criterion.kind.value == "MACHINE_COMPARISON"
        },
        evidence_references=("controlled:wrong-class",),
        created_at=T0,
    )
    with pytest.raises(DeterminationBoundaryError, match="evidence class mismatch"):
        determination.bind_context(
            validation_attempt_id=attempt.validation_attempt_id,
            role_source_record_ids={
                role: source.source_record_id for role in method.required_context_roles
            },
            frozen_at=T0 + timedelta(seconds=1),
        )


@pytest.mark.dc006
def test_scenario_context_binds_one_real_run_execution_and_preserved_evidence(
    tmp_path: Path,
) -> None:
    scenarios, catalogue, validation, determination = scenario_services(tmp_path)
    initial = scenarios.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=1),
            actor="Graduate Engineer",
            mode=ScenarioMode.FORMAL,
            configuration_version="1.1",
            scenario_time=T0,
        )
    )
    run_id = initial.snapshot.run.scenario_run_id
    execution = validation.start_execution("VT-TOP-NORMAL-001", run_id)
    evidence = validation.capture_checkpoint(
        execution.validation_execution_id, "CONTROLLED_RESULT"
    )
    method = catalogue.get_method("VT-TOP-NORMAL-001")
    source = determination.register_authoritative_source(
        source_type="SCENARIO_EXECUTION_SOURCE_SET",
        owner_module="scenario-topology-outage-authorities",
        evidence_class=EvidenceClass.FORMAL,
        selector_values={
            criterion.source_selector: criterion.expected_value
            for criterion in method.criteria
            if criterion.kind.value == "MACHINE_COMPARISON"
        },
        evidence_references=(f"evidence-snapshot:{evidence.evidence_snapshot_id}",),
        created_at=T0,
        configuration_id="network-configuration-v1.1",
        configuration_version="1.1",
        scenario_run_id=run_id,
        validation_execution_id=execution.validation_execution_id,
    )
    context = determination.bind_context(
        validation_attempt_id=execution.validation_attempt_id,
        role_source_record_ids={role: source.source_record_id for role in method.required_context_roles},
        frozen_at=T0,
        scenario_run_id=run_id,
        validation_execution_id=execution.validation_execution_id,
    )
    assert context.context_kind is DeterminationContextKind.SCENARIO_EXECUTION
    assert context.scenario_run_id == run_id
    determination.evaluate_machine_criteria(context.determination_context_id, evaluated_at=T0)
    result = determination.finalise_result(context.determination_context_id, finalised_at=T0)
    assert result.verdict is ValidationVerdict.PASS
    assert result.evidence_snapshot_ids == (evidence.evidence_snapshot_id,)

    later_identity = IDENTITY.model_copy(update={"git_commit": "9" * 40})
    later_build = ApplicationBuildManifest(
        application_build_id=sha256_bytes(
            canonical_json_bytes(later_identity.model_dump(mode="json"))
        ),
        identity=later_identity,
    )
    database = tmp_path / "validation.sqlite3"
    export = EvidenceExportService(
        EvidencePackageRepository(database, MIGRATIONS),
        ValidationRepository(database, MIGRATIONS),
        InvestigationRepository(database, MIGRATIONS),
        scenarios,
        JsonConfigurationLoader(ROOT / "config/network"),
        catalogue,
        determination._repository,
        application_build_manifest=later_build,
        output_directory=tmp_path / "evidence/exports",
    )
    package = export.generate(execution.validation_execution_id)
    assert package.application_build_id == BUILD.application_build_id
    assert package.generation_application_build_id == later_build.application_build_id
    with ZipFile(tmp_path / package.archive_path) as archive:
        names = set(archive.namelist())
        assert {
            "records/determination/context.json",
            "records/determination/executed-result.json",
            "records/determination/criterion-findings.json",
        } <= names
        exported_context = json.loads(
            archive.read("records/determination/context.json")
        )
        manifest = json.loads(archive.read("manifest.json"))
        assert exported_context["catalogue_version"] == "1.2"
        assert manifest["source_application_build_id"] == BUILD.application_build_id
        assert manifest["generation_application_build_id"] == later_build.application_build_id


@pytest.mark.dc006
def test_engineering_review_context_has_no_scenario_and_backend_derives_result(
    tmp_path: Path,
) -> None:
    catalogue, validation, determination, _ = services(tmp_path)
    _, attempt = validation.create_target_selection("VT-NFR-REVIEW-001", created_at=T0)
    method = catalogue.get_method("VT-NFR-REVIEW-001")
    source = determination.register_authoritative_source(
        source_type="CONTROLLED_ENGINEERING_REVIEW_SET",
        owner_module="review-assurance-authority",
        evidence_class=EvidenceClass.FORMAL,
        selector_values={
            criterion.source_selector: criterion.expected_value
            for criterion in method.criteria
            if criterion.kind.value == "MACHINE_COMPARISON"
        },
        evidence_references=("controlled:eight-surfaces", "controlled:45-record-set"),
        created_at=T0,
    )
    context = determination.bind_context(
        validation_attempt_id=attempt.validation_attempt_id,
        role_source_record_ids={role: source.source_record_id for role in method.required_context_roles},
        frozen_at=T0 + timedelta(seconds=1),
    )
    assert context.context_kind is DeterminationContextKind.ENGINEERING_REVIEW
    assert context.scenario_run_id is None and context.validation_execution_id is None
    determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    for index, criterion in enumerate(
        item for item in method.criteria if item.kind.value == "ENGINEERING_REVIEW"
    ):
        proposal = determination.propose_review_finding(
            context.determination_context_id,
            criterion.criterion_id,
            proposed_finding=CriterionFindingStatus.SATISFIED,
            proposer_actor_id="graduate-engineer",
            reason="Fixed proposition supported by the frozen review set.",
            proposed_at=T0 + timedelta(seconds=3 + index),
        )
        determination.finalise_review_finding(
            proposal.review_proposal_id,
            reviewer_actor_id="independent-reviewer",
            final_finding=CriterionFindingStatus.SATISFIED,
            reason="Independent criterion finding accepted.",
            finalised_at=T0 + timedelta(seconds=10 + index),
        )
    assert determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=20)
    ).verdict is ValidationVerdict.PASS


@pytest.mark.dc006
def test_final_v11_execution_resolves_and_exports_after_v12_promotion_while_old_active_is_read_only(
    tmp_path: Path,
) -> None:
    scenarios, catalogue, promoted, determination = scenario_services(tmp_path)
    database = tmp_path / "validation.sqlite3"
    historical = ValidationService(
        ValidationRepository(database, MIGRATIONS),
        ValidationCatalogueLoader(CATALOGUE.parent / "history/v1.1/catalogue.json"),
        scenarios,
        JsonConfigurationLoader(ROOT / "config/network"),
        application_build_manifest=BUILD,
    )
    first = scenarios.initialise(
        InitialiseRunRequest(
            command_id=UUID(int=101), actor="Graduate Engineer", mode=ScenarioMode.FORMAL,
            configuration_version="1.1", scenario_time=T0,
        )
    )
    final_execution = historical.start_execution(
        "VT-TOP-DEF-001", first.snapshot.run.scenario_run_id
    )
    scenarios.execute(
        first.snapshot.run.scenario_run_id,
        ScenarioCommandRequest(
            command_id=UUID(int=102), scenario_run_id=first.snapshot.run.scenario_run_id,
            actor="Graduate Engineer", expected_revision=0,
            command_type=ScenarioCommandType.INITIATE_FAULT,
            scenario_time=T0 + timedelta(seconds=10),
        ),
    )
    historical.capture_checkpoint(final_execution.validation_execution_id, "POST_TRIP")
    final_execution = historical.finalise_execution(
        final_execution.validation_execution_id, "POST_TRIP"
    )

    second = scenarios.initialise_next_run(
        InitialiseRunRequest(
            command_id=UUID(int=103), actor="Graduate Engineer", mode=ScenarioMode.FORMAL,
            configuration_version="1.1", scenario_time=T0,
        )
    )
    old_active = historical.start_execution(
        "VT-TOP-DEF-001", second.snapshot.run.scenario_run_id
    )
    assert promoted.get_execution(final_execution.validation_execution_id).execution == final_execution
    from ot_demo.modules.validation.service import ValidationBoundaryError
    with pytest.raises(ValidationBoundaryError, match="historical catalogue"):
        promoted.capture_checkpoint(old_active.validation_execution_id, "POST_TRIP")
    with pytest.raises(ValidationBoundaryError, match="historical catalogue"):
        promoted.finalise_execution(old_active.validation_execution_id, "POST_TRIP")

    later_identity = IDENTITY.model_copy(update={"git_commit": "8" * 40})
    later_build = ApplicationBuildManifest(
        application_build_id=sha256_bytes(
            canonical_json_bytes(later_identity.model_dump(mode="json"))
        ),
        identity=later_identity,
    )
    export = EvidenceExportService(
        EvidencePackageRepository(database, MIGRATIONS),
        ValidationRepository(database, MIGRATIONS),
        InvestigationRepository(database, MIGRATIONS),
        scenarios,
        JsonConfigurationLoader(ROOT / "config/network"),
        catalogue,
        determination._repository,
        application_build_manifest=later_build,
        output_directory=tmp_path / "evidence/exports",
    )
    package = export.generate(final_execution.validation_execution_id)
    assert str(package.source_catalogue_version) == "1.1"
    assert package.source_catalogue_sha256 == (
        "28bfe69131c40857c08f175abba42be3eb36514924b6de416b4e72bbefe35865"
    )
    assert package.application_build_id == BUILD.application_build_id
    assert package.generation_application_build_id == later_build.application_build_id
    with ZipFile(tmp_path / package.archive_path) as archive:
        definition = json.loads(archive.read("records/test-definition.json"))
        assert definition["catalogue_version"] == "1.1"
        assert definition["catalogue_sha256"] == package.source_catalogue_sha256


@pytest.mark.dc006
def test_reviewer_finding_requires_distinct_controlled_actors_and_backend_aggregate(tmp_path: Path) -> None:
    _, _, determination, _, _, method, context = prepare_record_context(
        tmp_path, "VT-CFG-INV-001"
    )
    determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )
    review = next(item for item in method.criteria if item.kind.value == "ENGINEERING_REVIEW")
    proposal = determination.propose_review_finding(
        context.determination_context_id,
        review.criterion_id,
        proposed_finding=CriterionFindingStatus.SATISFIED,
        proposer_actor_id="graduate-engineer",
        reason="The fixed proposition is supported by the preserved chain.",
        proposed_at=T0 + timedelta(seconds=3),
    )
    with pytest.raises(DeterminationBoundaryError, match="eligible reviewer"):
        determination.finalise_review_finding(
            proposal.review_proposal_id,
            reviewer_actor_id="graduate-engineer",
            final_finding=CriterionFindingStatus.SATISFIED,
            reason="not independent",
            finalised_at=T0 + timedelta(seconds=4),
        )
    finding = determination.finalise_review_finding(
        proposal.review_proposal_id,
        reviewer_actor_id="independent-reviewer",
        final_finding=CriterionFindingStatus.SATISFIED,
        reason="Independent criterion-level review accepted.",
        finalised_at=T0 + timedelta(seconds=4),
    )
    assert finding.status is CriterionFindingStatus.SATISFIED
    result = determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=5)
    )
    assert result.verdict is ValidationVerdict.PASS


@pytest.mark.dc006
def test_composite_parents_have_no_direct_method_but_all_exact_cases_do(tmp_path: Path) -> None:
    catalogue, *_ = services(tmp_path)
    for test_id, count in (("VT-EXP-ALL-001", 9), ("VT-EXP-ROLE-001", 4)):
        loaded = catalogue.get(test_id)
        assert loaded.definition.determination_method is None
        assert len(loaded.definition.constituent_cases) == count
        assert all(case.determination_method is not None for case in loaded.definition.constituent_cases)
        with pytest.raises(ValueError, match="does not own a direct"):
            catalogue.get_method(test_id)


@pytest.mark.dc006
def test_final_context_finding_result_and_membership_are_database_immutable(tmp_path: Path) -> None:
    _, _, determination, repository, _, _, context = prepare_record_context(
        tmp_path, "VT-CFG-BASE-001"
    )
    finding = determination.evaluate_machine_criteria(
        context.determination_context_id, evaluated_at=T0 + timedelta(seconds=2)
    )[0]
    result = determination.finalise_result(
        context.determination_context_id, finalised_at=T0 + timedelta(seconds=3)
    )
    with sqlite3.connect(repository.database_path) as connection:
        for statement, parameters in (
            (
                "UPDATE criterion_findings SET status='NOT_SATISFIED' WHERE criterion_finding_id=?",
                (str(finding.criterion_finding_id),),
            ),
            (
                "DELETE FROM determination_context_members WHERE determination_context_id=?",
                (str(context.determination_context_id),),
            ),
            (
                "DELETE FROM dc006_executed_validation_results WHERE executed_result_id=?",
                (str(result.executed_result_id),),
            ),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement, parameters)

        with pytest.raises(sqlite3.IntegrityError, match="cannot acquire findings"):
            connection.execute(
                "INSERT INTO criterion_findings "
                "(criterion_finding_id,determination_context_id,criterion_id,criterion_sha256,status,finding_sha256,finalised_at_ms,payload_json) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    "00000000-0000-0000-0000-000000000099",
                    str(context.determination_context_id),
                    "LATE-CRITERION",
                    "1" * 64,
                    "SATISFIED",
                    "2" * 64,
                    1,
                    "{}",
                ),
            )


@pytest.mark.dc006
def test_public_contract_never_accepts_observed_value_or_overall_verdict() -> None:
    from ot_demo.api.main import create_app

    schemas = create_app().openapi()["components"]["schemas"]
    assert set(schemas["FinaliseDeterminationPayload"]["properties"]) == {"finalised_at"}
    assert "verdict" not in schemas["ProposeCriterionFindingPayload"]["properties"]
    assert "evidence_references" not in schemas["ProposeCriterionFindingPayload"]["properties"]
    assert "observed_value" not in schemas["BindDeterminationContextPayload"]["properties"]
