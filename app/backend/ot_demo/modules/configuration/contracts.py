"""Repository-neutral contracts for loading immutable configurations."""

from typing import Protocol

from .models import LoadedConfiguration


class ConfigurationLoader(Protocol):
    def load(self, version: str) -> LoadedConfiguration:
        """Load and hash-verify one immutable configuration package."""

        ...
