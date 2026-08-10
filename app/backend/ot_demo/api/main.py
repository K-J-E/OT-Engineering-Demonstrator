"""Versioned local API foundation through the authorised I6 workspace."""

from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from ..application.scenario_coordinator import (
    ScenarioBoundaryError,
    ScenarioCommandConflict,
    ScenarioCoordinator,
    ScenarioRecordNotFound,
)
from ..application.investigation_service import (
    InvestigationBoundaryError,
    InvestigationService,
)
from ..application.workspace_service import WorkspaceProjectionError, WorkspaceService
from ..infrastructure.evidence_package_repository import EvidencePackageNotFound
from ..modules.events.models import OperationalEvent
from ..modules.scenario.models import (
    CommandResult,
    InitialiseRunRequest,
    ScenarioCommandRequest,
    ScenarioSnapshot,
)
from ..domain.enums import EvidenceClass, ScenarioCommandType, ScenarioMode, SwitchState
from ..infrastructure.validation_repository import ValidationRecordNotFound
from ..infrastructure.investigation_repository import InvestigationRecordNotFound
from ..modules.investigation.models import InvestigationWorkspace
from ..modules.evidence_export.models import (
    CompositeEvidencePackage,
    EvidenceExportCandidate,
    EvidencePackage,
)
from ..modules.evidence_export.service import (
    EvidenceExportBoundaryError,
    EvidenceExportService,
)
from ..modules.validation.models import (
    AssembleCompositeRequest,
    CaptureValidationCheckpointRequest,
    CompositeValidationResult,
    EvidenceSnapshot,
    FinaliseCompositeRequest,
    FinaliseValidationExecutionRequest,
    StartValidationExecutionRequest,
    ValidationExecutionLinks,
    ValidationExecution,
    ValidationExecutionSummary,
)
from ..modules.validation.service import ValidationBoundaryError, ValidationService
from ..modules.workspace.models import WorkspaceBootstrap, WorkspaceProjection


class _ApiRequest(BaseModel):
    """Permissive JSON transport model; converted to a strict domain contract."""

    model_config = ConfigDict(extra="forbid")


class InitialiseRunPayload(_ApiRequest):
    command_id: UUID
    actor: str = Field(min_length=1, max_length=120)
    expected_revision: int = Field(default=0, ge=0, le=0)
    mode: ScenarioMode
    configuration_version: str
    fault_section_id: str | None = None
    scenario_time: datetime

    def to_domain(self) -> InitialiseRunRequest:
        return InitialiseRunRequest.model_validate(self.model_dump())


class ScenarioCommandPayload(_ApiRequest):
    command_id: UUID
    scenario_run_id: UUID
    actor: str = Field(min_length=1, max_length=120)
    expected_revision: int = Field(ge=0)
    command_type: ScenarioCommandType
    scenario_time: datetime
    target_entity_id: str | None = None
    requested_state: SwitchState | None = None
    alarm_id: UUID | None = None
    assessment_id: UUID | None = None

    def to_domain(self) -> ScenarioCommandRequest:
        return ScenarioCommandRequest.model_validate(self.model_dump())


class ValidationExecutionLinksPayload(_ApiRequest):
    repeat_of_execution_id: UUID | None = None
    defect_id: str | None = None
    correction_id: str | None = None


class StartValidationExecutionPayload(_ApiRequest):
    test_id: str = Field(pattern=r"^VT-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    case_id: str | None = Field(default=None, pattern=r"^EXP-(?:ALL|ROLE)-[A-Z0-9-]+$")
    scenario_run_id: UUID
    links: ValidationExecutionLinksPayload = ValidationExecutionLinksPayload()

    def to_domain(self) -> StartValidationExecutionRequest:
        return StartValidationExecutionRequest(
            test_id=self.test_id,
            case_id=self.case_id,
            scenario_run_id=self.scenario_run_id,
            links=ValidationExecutionLinks.model_validate(self.links.model_dump()),
        )


class StartInvestigationPayload(_ApiRequest):
    actor: str = Field(min_length=1, max_length=120)


class RecordDefectPayload(_ApiRequest):
    reviewer: str = Field(min_length=1, max_length=120)
    reviewed_step_ids: tuple[str, ...]


class RecordCorrectionPayload(_ApiRequest):
    reviewer: str = Field(min_length=1, max_length=120)


class RunLinkedValidationPayload(_ApiRequest):
    actor: str = Field(min_length=1, max_length=120)


class GenerateEvidencePackagePayload(_ApiRequest):
    validation_execution_id: UUID


class GenerateCompositeEvidencePackagePayload(_ApiRequest):
    composite_result_id: UUID


class AssembleCompositePayload(_ApiRequest):
    test_id: str = Field(pattern=r"^VT-EXP-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
    validation_execution_ids: tuple[UUID, ...] = Field(min_length=1)
    created_at: datetime

    def to_domain(self) -> AssembleCompositeRequest:
        return AssembleCompositeRequest.model_validate(self.model_dump())


class FinaliseCompositePayload(_ApiRequest):
    finalised_at: datetime

    def to_domain(self) -> FinaliseCompositeRequest:
        return FinaliseCompositeRequest.model_validate(self.model_dump())


def create_app(
    coordinator: ScenarioCoordinator | None = None,
    validation_service: ValidationService | None = None,
    workspace_service: WorkspaceService | None = None,
    investigation_service: InvestigationService | None = None,
    evidence_export_service: EvidenceExportService | None = None,
) -> FastAPI:
    app = FastAPI(
        title="OT Graduate Demonstrator",
        version="0.8.0",
        description=(
            "Fictional local engineering demonstrator — scenario, validation, investigation, exploration and evidence-export API"
        ),
    )

    def service() -> ScenarioCoordinator:
        if coordinator is None:
            raise HTTPException(
                status_code=503,
                detail="Scenario coordinator is not configured for this process.",
            )
        return coordinator

    def validation() -> ValidationService:
        if validation_service is None:
            raise HTTPException(
                status_code=503,
                detail="Validation service is not configured for this process.",
            )
        return validation_service

    def workspace() -> WorkspaceService:
        if workspace_service is None:
            raise HTTPException(
                status_code=503,
                detail="Operational workspace service is not configured for this process.",
            )
        return workspace_service

    def investigation() -> InvestigationService:
        if investigation_service is None:
            raise HTTPException(
                status_code=503,
                detail="Investigation service is not configured for this process.",
            )
        return investigation_service

    def evidence_export() -> EvidenceExportService:
        if evidence_export_service is None:
            raise HTTPException(
                status_code=503,
                detail="Evidence export service is not configured for this process.",
            )
        return evidence_export_service

    @app.post("/api/v1/evidence-packages", response_model=EvidencePackage)
    def generate_evidence_package(
        request: GenerateEvidencePackagePayload,
    ) -> EvidencePackage:
        try:
            return evidence_export().generate(request.validation_execution_id)
        except (ValidationRecordNotFound, EvidencePackageNotFound) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except EvidenceExportBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/v1/evidence-packages", response_model=tuple[EvidencePackage, ...])
    def list_evidence_packages() -> tuple[EvidencePackage, ...]:
        return evidence_export().list()

    @app.get(
        "/api/v1/evidence-packages/candidates",
        response_model=tuple[EvidenceExportCandidate, ...],
    )
    def list_evidence_export_candidates() -> tuple[EvidenceExportCandidate, ...]:
        return evidence_export().candidates()

    @app.get(
        "/api/v1/evidence-packages/{package_id}/download",
        response_class=FileResponse,
    )
    def download_evidence_package(package_id: str) -> FileResponse:
        try:
            path = evidence_export().archive_file(package_id)
        except EvidencePackageNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except EvidenceExportBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return FileResponse(
            path,
            media_type="application/zip",
            filename=path.name,
        )

    @app.post(
        "/api/v1/composite-evidence-packages",
        response_model=CompositeEvidencePackage,
    )
    def generate_composite_evidence_package(
        request: GenerateCompositeEvidencePackagePayload,
    ) -> CompositeEvidencePackage:
        try:
            return evidence_export().generate_composite(request.composite_result_id)
        except (ValidationRecordNotFound, EvidencePackageNotFound) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except EvidenceExportBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/api/v1/composite-evidence-packages",
        response_model=tuple[CompositeEvidencePackage, ...],
    )
    def list_composite_evidence_packages() -> tuple[CompositeEvidencePackage, ...]:
        return evidence_export().list_composite_packages()

    @app.get(
        "/api/v1/composite-evidence-packages/{package_id}/download",
        response_class=FileResponse,
    )
    def download_composite_evidence_package(package_id: str) -> FileResponse:
        try:
            path = evidence_export().composite_archive_file(package_id)
        except EvidencePackageNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except EvidenceExportBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return FileResponse(path, media_type="application/zip", filename=path.name)

    @app.post(
        "/api/v1/investigations/start",
        response_model=InvestigationWorkspace,
    )
    def start_investigation(request: StartInvestigationPayload) -> InvestigationWorkspace:
        try:
            return investigation().start_failure(request.actor)
        except (InvestigationBoundaryError, ScenarioBoundaryError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/api/v1/investigations/{failure_execution_id}",
        response_model=InvestigationWorkspace,
    )
    def get_investigation(failure_execution_id: UUID) -> InvestigationWorkspace:
        try:
            return investigation().workspace(failure_execution_id)
        except (ValidationRecordNotFound, InvestigationRecordNotFound) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except InvestigationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/api/v1/investigations/{failure_execution_id}/defect",
        response_model=InvestigationWorkspace,
    )
    def record_defect(
        failure_execution_id: UUID, request: RecordDefectPayload
    ) -> InvestigationWorkspace:
        try:
            return investigation().record_defect(
                failure_execution_id,
                request.reviewer,
                request.reviewed_step_ids,
            )
        except InvestigationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/api/v1/investigations/{failure_execution_id}/correction",
        response_model=InvestigationWorkspace,
    )
    def record_correction(
        failure_execution_id: UUID, request: RecordCorrectionPayload
    ) -> InvestigationWorkspace:
        try:
            return investigation().record_correction(
                failure_execution_id, request.reviewer
            )
        except InvestigationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/api/v1/investigations/{failure_execution_id}/direct-repeat",
        response_model=InvestigationWorkspace,
    )
    def run_direct_repeat(
        failure_execution_id: UUID, request: RunLinkedValidationPayload
    ) -> InvestigationWorkspace:
        try:
            return investigation().run_direct_repeat(
                failure_execution_id, request.actor
            )
        except InvestigationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/api/v1/investigations/{failure_execution_id}/regression",
        response_model=InvestigationWorkspace,
    )
    def run_regression(
        failure_execution_id: UUID, request: RunLinkedValidationPayload
    ) -> InvestigationWorkspace:
        try:
            return investigation().run_regression(
                failure_execution_id, request.actor
            )
        except InvestigationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/v1/workspace/bootstrap", response_model=WorkspaceBootstrap)
    def get_workspace_bootstrap() -> WorkspaceBootstrap:
        try:
            return workspace().bootstrap()
        except WorkspaceProjectionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/api/v1/workspace/runs/{scenario_run_id}",
        response_model=WorkspaceProjection,
    )
    def get_workspace_projection(scenario_run_id: UUID) -> WorkspaceProjection:
        try:
            return workspace().projection(scenario_run_id)
        except ScenarioRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except WorkspaceProjectionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/v1/runs", response_model=CommandResult)
    def initialise_run(request: InitialiseRunPayload) -> CommandResult:
        try:
            return service().initialise(request.to_domain())
        except (ScenarioBoundaryError, ScenarioCommandConflict) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/v1/runs/start", response_model=CommandResult)
    def initialise_next_run(request: InitialiseRunPayload) -> CommandResult:
        try:
            return service().initialise_next_run(request.to_domain())
        except (ScenarioBoundaryError, ScenarioCommandConflict) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/api/v1/runs/{scenario_run_id}/commands",
        response_model=CommandResult,
    )
    def execute_command(
        scenario_run_id: UUID,
        request: ScenarioCommandPayload,
    ) -> CommandResult | JSONResponse:
        try:
            result = service().execute(scenario_run_id, request.to_domain())
        except ScenarioRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (ScenarioBoundaryError, ScenarioCommandConflict) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if not result.accepted:
            return JSONResponse(
                status_code=409,
                content=result.model_dump(mode="json"),
            )
        return result

    @app.get(
        "/api/v1/runs/{scenario_run_id}/snapshot",
        response_model=ScenarioSnapshot,
    )
    def get_snapshot(scenario_run_id: UUID) -> ScenarioSnapshot:
        try:
            return service().snapshot(scenario_run_id)
        except ScenarioRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get(
        "/api/v1/runs/{scenario_run_id}/events",
        response_model=tuple[OperationalEvent, ...],
    )
    def get_events(scenario_run_id: UUID) -> tuple[OperationalEvent, ...]:
        try:
            return service().events(scenario_run_id)
        except ScenarioRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post(
        "/api/v1/validation/executions",
        response_model=ValidationExecution,
    )
    def start_validation_execution(
        request: StartValidationExecutionPayload,
    ) -> ValidationExecution:
        try:
            domain_request = request.to_domain()
            return validation().start_execution(
                domain_request.test_id,
                domain_request.scenario_run_id,
                case_id=domain_request.case_id,
                links=domain_request.links,
            )
        except ValidationRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValidationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/api/v1/validation/executions/{execution_id}/checkpoints",
        response_model=EvidenceSnapshot,
    )
    def capture_validation_checkpoint(
        execution_id: UUID,
        request: CaptureValidationCheckpointRequest,
    ) -> EvidenceSnapshot:
        try:
            return validation().capture_checkpoint(
                execution_id,
                request.checkpoint_id,
            )
        except ValidationRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValidationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/api/v1/validation/executions/{execution_id}/finalise",
        response_model=ValidationExecution,
    )
    def finalise_validation_execution(
        execution_id: UUID,
        request: FinaliseValidationExecutionRequest,
    ) -> ValidationExecution:
        try:
            return validation().finalise_execution(
                execution_id,
                request.checkpoint_id,
            )
        except ValidationRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValidationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/api/v1/validation/executions/{execution_id}",
        response_model=ValidationExecutionSummary,
    )
    def get_validation_execution(execution_id: UUID) -> ValidationExecutionSummary:
        try:
            return validation().get_execution(execution_id)
        except ValidationRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get(
        "/api/v1/validation/executions",
        response_model=tuple[ValidationExecutionSummary, ...],
    )
    def list_validation_executions(
        test_id: str | None = None,
        evidence_class: EvidenceClass | None = None,
        scenario_run_id: UUID | None = None,
    ) -> tuple[ValidationExecutionSummary, ...]:
        return validation().list_executions(
            test_id=test_id,
            evidence_class=evidence_class,
            scenario_run_id=scenario_run_id,
        )

    @app.post(
        "/api/v1/validation/composites",
        response_model=CompositeValidationResult,
    )
    def assemble_validation_composite(
        request: AssembleCompositePayload,
    ) -> CompositeValidationResult:
        try:
            domain_request = request.to_domain()
            return validation().assemble_composite(
                domain_request.test_id,
                domain_request.validation_execution_ids,
                created_at=domain_request.created_at,
            )
        except ValidationRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValidationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/api/v1/validation/composites/{composite_id}/finalise",
        response_model=CompositeValidationResult,
    )
    def finalise_validation_composite(
        composite_id: UUID,
        request: FinaliseCompositePayload,
    ) -> CompositeValidationResult:
        try:
            domain_request = request.to_domain()
            return validation().finalise_composite(
                composite_id, finalised_at=domain_request.finalised_at
            )
        except ValidationRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValidationBoundaryError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(
        "/api/v1/validation/composites/{composite_id}",
        response_model=CompositeValidationResult,
    )
    def get_validation_composite(composite_id: UUID) -> CompositeValidationResult:
        try:
            return validation().get_composite(composite_id)
        except ValidationRecordNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get(
        "/api/v1/validation/composites",
        response_model=tuple[CompositeValidationResult, ...],
    )
    def list_validation_composites(
        test_id: str | None = None,
    ) -> tuple[CompositeValidationResult, ...]:
        return validation().list_composites(test_id=test_id)

    return app


app = create_app()
