"""I1 build identity foundation: AD-DD-018 and Demonstrator Design Section 10.5."""

import sys
from pathlib import Path

from ot_demo.domain.value_objects import Sha256Digest
from ot_demo.infrastructure import build_identity
from ot_demo.infrastructure.hashing import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    sha256_tree,
)


def test_canonical_build_identity_hash_is_deterministic() -> None:
    first = {"python": "3.13.15", "locks": {"b": "2", "a": "1"}}
    second = {"locks": {"a": "1", "b": "2"}, "python": "3.13.15"}

    digest = sha256_bytes(canonical_json_bytes(first))
    assert digest == sha256_bytes(canonical_json_bytes(second))
    assert len(digest) == 64


def test_sha256_value_object_schema_is_available() -> None:
    assert Sha256Digest is not None


def test_create_build_manifest_assembles_every_controlled_identity_input(
    tmp_path: Path,
    monkeypatch,
) -> None:
    backend = tmp_path / "app/backend/ot_demo"
    frontend = tmp_path / "app/frontend"
    bundle = frontend / "dist"
    backend.mkdir(parents=True)
    bundle.mkdir(parents=True)
    (tmp_path / "requirements.lock").write_text("backend==1.0\n", encoding="utf-8")
    (frontend / "package-lock.json").write_text(
        '{"lockfileVersion":3}\n',
        encoding="utf-8",
    )
    (backend / "domain.py").write_text("VALUE = 1\n", encoding="utf-8")
    (backend / "migration.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (bundle / "app.js").write_text("export const value = 1;\n", encoding="utf-8")

    command_results = {
        ("git", "rev-parse", "HEAD"): "a" * 40,
        ("git", "status", "--porcelain"): "",
        ("node", "--version"): "v24.19.0",
        ("npm", "--version"): "11.17.0",
    }

    def fake_command(_cwd: Path, *command: str) -> str:
        return command_results[command]

    monkeypatch.setattr(build_identity, "_command", fake_command)
    manifest = build_identity.create_build_manifest(tmp_path)
    identity = manifest.identity

    assert identity.git_commit == "a" * 40
    assert identity.git_dirty is False
    assert identity.python_version == (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    assert identity.node_version == "24.19.0"
    assert identity.npm_version == "11.17.0"
    assert identity.dependency_lock_sha256 == {
        "requirements.lock": sha256_file(tmp_path / "requirements.lock"),
        "app/frontend/package-lock.json": sha256_file(frontend / "package-lock.json"),
    }
    assert identity.backend_source_sha256 == sha256_tree(
        backend,
        suffixes=(".py", ".sql"),
    )
    assert identity.frontend_bundle_sha256 == sha256_tree(bundle)
    assert manifest.application_build_id == sha256_bytes(
        canonical_json_bytes(identity.model_dump(mode="json"))
    )

    baseline_id = manifest.application_build_id

    for command, changed_value in (
        (("git", "rev-parse", "HEAD"), "b" * 40),
        (("git", "status", "--porcelain"), " M controlled-file"),
        (("node", "--version"), "v24.19.1"),
        (("npm", "--version"), "11.17.1"),
    ):
        original = command_results[command]
        command_results[command] = changed_value
        assert (
            build_identity.create_build_manifest(tmp_path).application_build_id
            != baseline_id
        )
        command_results[command] = original

    for path, changed_content in (
        (tmp_path / "requirements.lock", "backend==1.1\n"),
        (frontend / "package-lock.json", '{"lockfileVersion":4}\n'),
        (backend / "domain.py", "VALUE = 2\n"),
        (bundle / "app.js", "export const value = 2;\n"),
    ):
        original = path.read_text(encoding="utf-8")
        path.write_text(changed_content, encoding="utf-8")
        assert (
            build_identity.create_build_manifest(tmp_path).application_build_id
            != baseline_id
        )
        path.write_text(original, encoding="utf-8")
