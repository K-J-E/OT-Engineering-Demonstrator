"""Hosted single-workspace boundaries for sequential public reviewers."""

import json
import socket
import threading
import time
from contextlib import contextmanager
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

import pytest
import uvicorn

from ot_demo.api.hosted import create_hosted_app
from ot_demo.api.runtime import create_local_app
from ot_demo.infrastructure.build_identity import (
    ApplicationBuildManifest,
    BuildIdentityPayload,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ApplicationBuildManifest(
    application_build_id="1" * 64,
    identity=BuildIdentityPayload(
        git_commit="1" * 40,
        git_dirty=False,
        python_version="3.13.15",
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


def hosted_app(tmp_path: Path):
    return create_hosted_app(
        repository_root=ROOT,
        runtime_root=tmp_path / "public-runtime",
        application_build_manifest=MANIFEST,
        mount_frontend=False,
    )


def start_payload(bootstrap: dict, mode: str, fault_section_id: str | None) -> dict:
    return {
        "command_id": "11111111-1111-4111-8111-111111111111",
        "actor": "Public reviewer",
        "expected_revision": 0,
        "mode": mode,
        "configuration_version": bootstrap["default_configuration_version"],
        "fault_section_id": fault_section_id,
        "scenario_time": bootstrap["default_scenario_time"],
    }


@contextmanager
def live_server(app):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            with urlopen(f"{base_url}/healthz", timeout=0.2) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.02)
    else:
        raise RuntimeError("Hosted test server did not start.")
    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=5)


class Browser:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(self, path: str, payload: dict | None = None) -> tuple[int, dict]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if payload is None else "POST",
        )
        try:
            with self.opener.open(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            payload = json.loads(error.read())
            return error.code, payload


def test_fresh_browser_resets_an_abandoned_defect_case_and_can_start_each_walkthrough(
    tmp_path: Path,
) -> None:
    app = hosted_app(tmp_path)
    with live_server(app) as base_url:
        abandoned = Browser(base_url)
        assert abandoned.request("/api/v1/workspace/bootstrap")[0] == 200
        assert abandoned.request(
            "/api/v1/investigations/start", {"actor": "First reviewer"}
        )[0] == 200

        defect_reviewer = Browser(base_url)
        assert defect_reviewer.request("/api/v1/workspace/bootstrap")[0] == 200
        assert defect_reviewer.request(
            "/api/v1/investigations/start", {"actor": "Second reviewer"}
        )[0] == 200

        trial_reviewer = Browser(base_url)
        _, trial_bootstrap = trial_reviewer.request("/api/v1/workspace/bootstrap")
        assert trial_reviewer.request(
            "/api/v1/runs/start",
            start_payload(trial_bootstrap, "EXPLORATION", "SEC-A2"),
        )[0] == 200

        safety_reviewer = Browser(base_url)
        _, safety_bootstrap = safety_reviewer.request("/api/v1/workspace/bootstrap")
        assert safety_reviewer.request(
            "/api/v1/runs/start",
            start_payload(safety_bootstrap, "FORMAL", None),
        )[0] == 200


def test_same_browser_refresh_resets_its_active_run(tmp_path: Path) -> None:
    with live_server(hosted_app(tmp_path)) as base_url:
        client = Browser(base_url)
        _, bootstrap = client.request("/api/v1/workspace/bootstrap")
        _, started = client.request(
            "/api/v1/runs/start",
            start_payload(bootstrap, "EXPLORATION", "SEC-A2"),
        )
        run_id = started["snapshot"]["run"]["scenario_run_id"]

        assert client.request("/api/v1/workspace/bootstrap")[0] == 200
        assert client.request(f"/api/v1/workspace/runs/{run_id}")[0] == 404
        assert client.request(
            "/api/v1/investigations/start", {"actor": "Same reviewer after refresh"}
        )[0] == 200


def test_public_mode_hides_api_docs_and_exposes_minimal_health(tmp_path: Path) -> None:
    with live_server(hosted_app(tmp_path)) as base_url:
        with urlopen(f"{base_url}/healthz") as response:
            assert json.loads(response.read()) == {"status": "ok"}
        for path in ("/docs", "/openapi.json"):
            with pytest.raises(HTTPError) as error:
                urlopen(f"{base_url}{path}")
            assert error.value.code == 404


def test_hosted_reset_rejects_paths_outside_the_controlled_boundary(
    tmp_path: Path,
) -> None:
    with pytest.raises(RuntimeError, match="outside the hosted reset boundary"):
        create_local_app(
            data_directory=tmp_path / "boundary/data",
            evidence_output_directory=tmp_path / "outside/evidence",
            application_build_manifest=MANIFEST,
            reset_boundary=tmp_path / "boundary",
            public_mode=True,
        )
