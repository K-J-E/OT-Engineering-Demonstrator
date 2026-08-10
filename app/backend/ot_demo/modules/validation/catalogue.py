"""Hash-identified loader for the accepted 24-test machine catalogue."""

import json
from pathlib import Path

from pydantic import ValidationError

from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from .models import (
    LoadedValidationDefinition,
    ValidationCatalogue,
    ValidationCatalogueManifest,
)


class ValidationCatalogueError(ValueError):
    """Raised when the controlled catalogue cannot be trusted."""


class ValidationCatalogueLoader:
    def __init__(self, catalogue_path: Path) -> None:
        self.catalogue_path = catalogue_path
        self.manifest_path = catalogue_path.with_name("manifest.json")

    def load(self) -> tuple[LoadedValidationDefinition, ...]:
        try:
            manifest = ValidationCatalogueManifest.model_validate_json(
                self.manifest_path.read_text(encoding="utf-8"),
                strict=True,
            )
            catalogue = ValidationCatalogue.model_validate_json(
                self.catalogue_path.read_text(encoding="utf-8"),
                strict=True,
            )
        except (OSError, ValidationError) as error:
            raise ValidationCatalogueError(str(error)) from error
        catalogue_sha256 = sha256_file(self.catalogue_path)
        if manifest.catalogue_sha256 != catalogue_sha256:
            raise ValidationCatalogueError("controlled catalogue SHA-256 mismatch")
        if (
            manifest.catalogue_id != catalogue.catalogue_id
            or manifest.catalogue_version != catalogue.catalogue_version
            or manifest.definition_count != catalogue.definition_count
            or manifest.catalogue_file != self.catalogue_path.name
        ):
            raise ValidationCatalogueError(
                "controlled catalogue manifest identity does not match its payload"
            )
        return tuple(
            LoadedValidationDefinition(
                definition=definition,
                definition_sha256=sha256_bytes(
                    canonical_json_bytes(definition.model_dump(mode="json"))
                ),
                catalogue_sha256=catalogue_sha256,
            )
            for definition in catalogue.definitions
        )

    def get(self, test_id: str) -> LoadedValidationDefinition:
        definitions = {item.definition.test_id: item for item in self.load()}
        try:
            return definitions[test_id]
        except KeyError as error:
            raise ValidationCatalogueError(f"unknown controlled test ID: {test_id}") from error

    def raw_catalogue_sha256(self) -> str:
        return sha256_file(self.catalogue_path)
