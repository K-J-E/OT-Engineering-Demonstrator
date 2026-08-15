"""Ephemeral backend used only by the controlled I6 browser assurance run."""

from pathlib import Path
from tempfile import mkdtemp

from ot_demo.api.runtime import create_local_app
from ot_demo.api.hosted import install_fresh_browser_boundary
from ot_demo.infrastructure.build_identity import (
    ApplicationBuildManifest,
    BuildIdentityPayload,
)


TEST_BUILD_MANIFEST = ApplicationBuildManifest(
    application_build_id="1" * 64,
    identity=BuildIdentityPayload(
        git_commit="1" * 40,
        git_dirty=False,
        python_version="3.14.3",
        node_version="24.19.0",
        npm_version="11.17.0",
        dependency_lock_sha256={
            "requirements.lock": "2" * 64,
            "app/frontend/package-lock.json": "3" * 64,
        },
        backend_source_sha256="4" * 64,
        frontend_bundle_sha256="5" * 64,
    ),
)

TEST_DATA_DIRECTORY = Path(mkdtemp(prefix="ot-demo-i8-e2e-"))

app = create_local_app(
    data_directory=TEST_DATA_DIRECTORY,
    evidence_output_directory=TEST_DATA_DIRECTORY / "evidence/exports",
    application_build_manifest=TEST_BUILD_MANIFEST,
    reset_boundary=TEST_DATA_DIRECTORY,
    public_mode=True,
)
install_fresh_browser_boundary(app)
