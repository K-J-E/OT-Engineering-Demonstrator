"""Single-service hosted entry point with a shared, ephemeral showcase workspace."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import Request
from fastapi.staticfiles import StaticFiles

from ..infrastructure.build_identity import (
    ApplicationBuildManifest,
    create_deployment_build_manifest,
)
from .runtime import create_local_app


PINNED_NODE_VERSION = "24.19.0"
PINNED_NPM_VERSION = "11.17.0"


def create_hosted_app(
    *,
    repository_root: Path | None = None,
    runtime_root: Path | None = None,
    git_commit: str | None = None,
    git_dirty: bool | None = None,
    application_build_manifest: ApplicationBuildManifest | None = None,
    mount_frontend: bool = True,
):
    root = (repository_root or Path(__file__).resolve().parents[4]).resolve(
        strict=True
    )
    workspace_root = (
        runtime_root
        or Path(os.environ.get("OT_DEMO_RUNTIME_ROOT", "/tmp/ot-showcase"))
    ).resolve()
    manifest = application_build_manifest
    if manifest is None:
        commit = (
            git_commit
            or os.environ.get("RAILWAY_GIT_COMMIT_SHA")
            or os.environ.get("OT_DEMO_GIT_COMMIT")
        )
        if commit is None:
            raise RuntimeError(
                "Hosted startup requires RAILWAY_GIT_COMMIT_SHA or OT_DEMO_GIT_COMMIT."
            )
        dirty = git_dirty if git_dirty is not None else _deployment_dirty(commit)
        manifest = create_deployment_build_manifest(
            root,
            git_commit=commit,
            git_dirty=dirty,
            node_version=PINNED_NODE_VERSION,
            npm_version=PINNED_NPM_VERSION,
        )
    app = create_local_app(
        data_directory=workspace_root / "data",
        evidence_output_directory=workspace_root / "evidence",
        application_build_manifest=manifest,
        reset_boundary=workspace_root,
        public_mode=True,
    )
    install_fresh_browser_boundary(app)

    frontend = root / "app/frontend/dist"
    if mount_frontend:
        if not frontend.is_dir():
            raise RuntimeError("Hosted startup requires the built frontend bundle.")
        app.mount(
            "/",
            StaticFiles(directory=frontend, html=True),
            name="showcase-frontend",
        )
    return app


def _deployment_dirty(commit: str) -> bool:
    value = os.environ.get("OT_DEMO_BUILD_DIRTY")
    if value is None:
        if os.environ.get("RAILWAY_GIT_COMMIT_SHA") == commit:
            return False
        raise RuntimeError("OT_DEMO_BUILD_DIRTY must be set for a non-Railway package run.")
    normalised = value.strip().lower()
    if normalised in {"0", "false", "no"}:
        return False
    if normalised in {"1", "true", "yes"}:
        return True
    raise RuntimeError("OT_DEMO_BUILD_DIRTY must be true or false.")


def install_fresh_browser_boundary(app) -> None:
    lock = asyncio.Lock()

    @app.middleware("http")
    async def fresh_browser_workspace(request: Request, call_next):
        if (
            request.method == "GET"
            and request.url.path == "/api/v1/workspace/bootstrap"
        ):
            async with lock:
                app.state.reset_showcase()
        return await call_next(request)
