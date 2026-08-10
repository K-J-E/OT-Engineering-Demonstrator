"""Composition root for the local fictional OT engineering workspace."""

from __future__ import annotations

import os
from pathlib import Path

from ..application.scenario_coordinator import ScenarioCoordinator
from ..application.investigation_service import InvestigationService
from ..application.workspace_service import WorkspaceService
from ..infrastructure.build_identity import (
    ApplicationBuildManifest,
    create_build_manifest,
)
from ..infrastructure.configuration_loader import JsonConfigurationLoader
from ..infrastructure.investigation_repository import InvestigationRepository
from ..infrastructure.scenario_repository import ScenarioRepository
from ..infrastructure.validation_repository import ValidationRepository
from ..modules.validation.catalogue import ValidationCatalogueLoader
from ..modules.validation.service import ValidationService
from .main import create_app


def create_local_app(
    *,
    data_directory: Path | None = None,
    application_build_manifest: ApplicationBuildManifest | None = None,
):
    """Assemble one local process with no external OT or utility interfaces."""

    repository_root = Path(__file__).resolve().parents[4]
    migrations = repository_root / "app/backend/ot_demo/infrastructure/migrations"
    runtime_data = data_directory or repository_root / "app/.runtime"
    runtime_data.mkdir(parents=True, exist_ok=True)
    build_manifest = application_build_manifest or create_build_manifest(
        repository_root,
        node_command=os.environ.get("OT_DEMO_NODE_COMMAND", "node"),
        npm_command=os.environ.get("OT_DEMO_NPM_COMMAND", "npm"),
    )
    configuration_loader = JsonConfigurationLoader(
        repository_root / "config/network"
    )
    coordinator = ScenarioCoordinator(
        ScenarioRepository(runtime_data / "scenario.sqlite3", migrations),
        configuration_loader,
        application_build_manifest=build_manifest,
    )
    catalogue = ValidationCatalogueLoader(
        repository_root / "validation/test-definitions/catalogue.json"
    )
    validation_service = ValidationService(
        ValidationRepository(runtime_data / "validation.sqlite3", migrations),
        catalogue,
        coordinator,
        application_build_manifest=build_manifest,
    )
    investigation_service = InvestigationService(
        InvestigationRepository(runtime_data / "validation.sqlite3", migrations),
        configuration_loader,
        coordinator,
        validation_service,
        application_build_manifest=build_manifest,
    )
    workspace_service = WorkspaceService(
        configuration_loader,
        coordinator,
        validation_service,
        catalogue,
        application_build_manifest=build_manifest,
        presentation_path=(
            repository_root / "config/presentation/network-one-line.v1.json"
        ),
    )
    return create_app(
        coordinator,
        validation_service,
        workspace_service,
        investigation_service,
    )
