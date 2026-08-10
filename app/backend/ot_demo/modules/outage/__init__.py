"""Outage and affected-customer derivation."""

from .models import OutageResult
from .service import OutageConfigurationMismatch, OutageService

__all__ = ["OutageConfigurationMismatch", "OutageResult", "OutageService"]
