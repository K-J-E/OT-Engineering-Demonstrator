"""Static controls for the one-service public deployment package."""

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_pins_toolchains_and_uses_locked_builds() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM node:24.19.0-bookworm-slim" in dockerfile
    assert "npm@11.17.0" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "FROM python:3.13.15-slim-bookworm" in dockerfile
    assert "--requirement requirements.lock" in dockerfile
    assert "ot_demo.api.hosted:create_hosted_app --factory" in dockerfile
    assert "--host 0.0.0.0" in dockerfile
    assert '${PORT:-8000}' in dockerfile


def test_railway_configuration_uses_health_and_bounded_restart_policy() -> None:
    with (ROOT / "railway.toml").open("rb") as source:
        railway = tomllib.load(source)

    assert railway["build"] == {
        "builder": "DOCKERFILE",
        "dockerfilePath": "Dockerfile",
    }
    assert railway["deploy"] == {
        "healthcheckPath": "/healthz",
        "healthcheckTimeout": 100,
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 3,
    }


def test_docker_context_excludes_local_runtime_and_development_outputs() -> None:
    ignored = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {
        ".git",
        ".venv",
        "app/frontend/node_modules",
        "app/frontend/dist",
        "app/.runtime",
        "evidence/exports",
        "app/frontend/test-results",
    }.issubset(ignored)
