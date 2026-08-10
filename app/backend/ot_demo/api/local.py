"""Uvicorn entry point for the local fictional OT engineering workspace."""

from .runtime import create_local_app


app = create_local_app()
