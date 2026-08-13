"""Single-process entry point for the local fictional OT engineering workspace."""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from .runtime import create_local_app


app = create_local_app()

_repository_root = Path(__file__).resolve().parents[4]
_frontend_dist = _repository_root / "app/frontend/dist"
if _frontend_dist.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=_frontend_dist, html=True),
        name="showcase-frontend",
    )
