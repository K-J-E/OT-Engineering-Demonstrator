"""Versioned local API foundation for exercising I3 without an operational UI."""

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


def create_app(coordinator: ScenarioCoordinator | None = None) -> FastAPI:
    app = FastAPI(
        title="OT Graduate Demonstrator",
        version="0.3.0",
        description=(
            "Fictional local engineering demonstrator — I3 scenario transaction API"
        ),
    )

    def service() -> ScenarioCoordinator:
        if coordinator is None:
            raise HTTPException(
                status_code=503,
                detail="Scenario coordinator is not configured for this process.",
            )
        return coordinator

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

    return app


app = create_app()
