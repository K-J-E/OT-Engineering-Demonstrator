"""Application build-identity foundation required by AD-DD-018 and Section 10.5."""

import json
import subprocess
import sys
from pathlib import Path

from pydantic import Field

from ..domain.base import FrozenModel
from ..domain.value_objects import Sha256Digest
from .hashing import canonical_json_bytes, sha256_bytes, sha256_file, sha256_tree


class BuildIdentityPayload(FrozenModel):
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    git_dirty: bool
    python_version: str
    node_version: str
    npm_version: str
    dependency_lock_sha256: dict[str, Sha256Digest]
    backend_source_sha256: Sha256Digest
    frontend_bundle_sha256: Sha256Digest | None


class ApplicationBuildManifest(FrozenModel):
    application_build_id: Sha256Digest
    identity: BuildIdentityPayload


def create_build_manifest(
    repository_root: Path,
    *,
    node_command: str = "node",
    npm_command: str = "npm",
) -> ApplicationBuildManifest:
    root = repository_root.resolve(strict=True)
    identity = BuildIdentityPayload(
        git_commit=_command(root, "git", "rev-parse", "HEAD"),
        git_dirty=bool(_command(root, "git", "status", "--porcelain")),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        node_version=_command(root, node_command, "--version").removeprefix("v"),
        npm_version=_command(root, npm_command, "--version"),
        dependency_lock_sha256={
            "requirements.lock": sha256_file(root / "requirements.lock"),
            "app/frontend/package-lock.json": sha256_file(
                root / "app/frontend/package-lock.json"
            ),
        },
        backend_source_sha256=sha256_tree(
            root / "app/backend/ot_demo", suffixes=(".py", ".sql")
        ),
        frontend_bundle_sha256=_optional_tree_hash(root / "app/frontend/dist"),
    )
    build_id = sha256_bytes(canonical_json_bytes(identity.model_dump(mode="json")))
    return ApplicationBuildManifest(application_build_id=build_id, identity=identity)


def create_deployment_build_manifest(
    repository_root: Path,
    *,
    git_commit: str,
    git_dirty: bool,
    node_version: str = "24.19.0",
    npm_version: str = "11.17.0",
) -> ApplicationBuildManifest:
    """Bind a packaged deployment without requiring Git or Node in the runtime image."""

    root = repository_root.resolve(strict=True)
    identity = BuildIdentityPayload(
        git_commit=git_commit,
        git_dirty=git_dirty,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        node_version=node_version,
        npm_version=npm_version,
        dependency_lock_sha256={
            "requirements.lock": sha256_file(root / "requirements.lock"),
            "app/frontend/package-lock.json": sha256_file(
                root / "app/frontend/package-lock.json"
            ),
        },
        backend_source_sha256=sha256_tree(
            root / "app/backend/ot_demo", suffixes=(".py", ".sql")
        ),
        frontend_bundle_sha256=_required_tree_hash(root / "app/frontend/dist"),
    )
    build_id = sha256_bytes(canonical_json_bytes(identity.model_dump(mode="json")))
    return ApplicationBuildManifest(application_build_id=build_id, identity=identity)


def write_build_manifest(
    repository_root: Path,
    output_path: Path,
    *,
    node_command: str = "node",
    npm_command: str = "npm",
) -> ApplicationBuildManifest:
    manifest = create_build_manifest(
        repository_root,
        node_command=node_command,
        npm_command=npm_command,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _optional_tree_hash(path: Path) -> str | None:
    if not path.is_dir() or not any(item.is_file() for item in path.rglob("*")):
        return None
    return sha256_tree(path)


def _required_tree_hash(path: Path) -> str:
    digest = _optional_tree_hash(path)
    if digest is None:
        raise RuntimeError("The packaged frontend bundle is missing or empty.")
    return digest


def _command(cwd: Path, *command: str) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()
