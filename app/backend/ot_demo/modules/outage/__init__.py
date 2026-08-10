"""Outage and affected-customer derivation."""

from .models import OutageResult
from .service import OutageService

__all__ = ["OutageResult", "OutageService"]
