"""Versioned local API foundation through I5 without an operational UI."""

from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from ..application.scenario_coordinator import (
    ScenarioBoundaryError,
    ScenarioCommandConflict,
    ScenarioCoordinator,
    ScenarioRecordNotFound,
)
from ..modules.events.models import OperationalEvent
from ..modules.scenario.models import (
    CommandResult,
    InitialiseRunRequest,
    ScenarioCommandRequest,
    ScenarioSnapshot,
)
from ..domain.enums import EvidenceClass
from ..infrastructure.validation_repository import ValidationRecordNotFound
from ..modules.validation.models import (
    CaptureValidationCheckpointRequest,
    EvidenceSnapshot,
    FinaliseValidationExecutionRequest,
    StartValidationExecutionRequest,
    ValidationExecution,
    ValidationExecutionSummary,
)
from ..modules.validation.service import ValidationBoundaryError, ValidationService


def create_app(
    coordinator: ScenarioCoordinator | None = None,
    validation_service: ValidationService | None = None,
) -> FastAPI:
    app = FastAPI(
        title="OT Graduate Demonstrator",
        version="0.5.0",
        description=(
            "Fictional local engineering demonstrator — scenario and I5 evidence API"
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

    @app.post("/api/v1/runs", response_model=CommandResult)
    def initialise_run(request: InitialiseRunRequest) -> CommandResult:
        try:
            return service().initialise(request)
        except (ScenarioBoundaryError, ScenarioCommandConflict) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post(
        "/api/v1/runs/{scenario_run_id}/commands",
        response_model=CommandResult,
    )
    def execute_command(
        scenario_run_id: UUID,
        request: ScenarioCommandRequest,
    ) -> CommandResult | JSONResponse:
        try:
            result = service().execute(scenario_run_id, request)
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
        request: StartValidationExecutionRequest,
    ) -> ValidationExecution:
        try:
            return validation().start_execution(
                request.test_id,
                request.scenario_run_id,
                links=request.links,
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

    return app


app = create_app()
