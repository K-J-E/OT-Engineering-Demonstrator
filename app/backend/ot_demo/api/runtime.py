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
from ..infrastructure.evidence_package_repository import EvidencePackageRepository
from ..infrastructure.scenario_repository import ScenarioRepository
from ..infrastructure.validation_repository import ValidationRepository
from ..infrastructure.determination_repository import DeterminationRepository
from ..modules.validation.catalogue import ValidationCatalogueResolver
from ..modules.validation.service import ValidationService
from ..modules.validation.determination import DeterminationService
from ..modules.validation.source_authority import (
    RegisteredSourceAuthority,
    SourceAuthorityDependencies,
)
from ..modules.evidence_export.service import EvidenceExportService
from .main import create_app


def create_local_app(
    *,
    data_directory: Path | None = None,
    evidence_output_directory: Path | None = None,
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
    catalogue = ValidationCatalogueResolver(
        repository_root / "validation/test-definitions/catalogue.json",
        (
            repository_root
            / "validation/test-definitions/history/v1.0/catalogue.json",
            repository_root
            / "validation/test-definitions/history/v1.1/catalogue.json",
        ),
    )
    validation_repository = ValidationRepository(
        runtime_data / "validation.sqlite3", migrations
    )
    investigation_repository = InvestigationRepository(
        runtime_data / "validation.sqlite3", migrations
    )
    evidence_package_repository = EvidencePackageRepository(
        runtime_data / "validation.sqlite3", migrations
    )
    validation_service = ValidationService(
        validation_repository,
        catalogue,
        coordinator,
        configuration_loader,
        application_build_manifest=build_manifest,
    )
    determination_repository = DeterminationRepository(
        runtime_data / "validation.sqlite3", migrations
    )
    investigation_service = InvestigationService(
        investigation_repository,
        configuration_loader,
        coordinator,
        validation_service,
        application_build_manifest=build_manifest,
    )
    determination_service = DeterminationService(
        determination_repository,
        validation_repository,
        catalogue,
        application_build_manifest=build_manifest,
        source_authority=RegisteredSourceAuthority(SourceAuthorityDependencies(
            repository_root=repository_root,
            build=build_manifest,
            configurations=configuration_loader,
            catalogue=catalogue,
            validation=validation_repository,
            scenarios=coordinator,
            investigation=investigation_repository,
            investigation_workflow=investigation_service,
            packages=evidence_package_repository,
            determination=determination_repository,
        )),
    )
    evidence_export_service = EvidenceExportService(
        evidence_package_repository,
        validation_repository,
        investigation_repository,
        coordinator,
        configuration_loader,
        catalogue,
        determination=determination_repository,
        application_build_manifest=build_manifest,
        output_directory=(
            evidence_output_directory
            or repository_root / "evidence/exports"
        ),
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
        evidence_export_service,
        determination_service,
    )
