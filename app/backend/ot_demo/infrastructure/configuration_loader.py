"""Hash-verifying loader for immutable v1.0/v1.1 configuration packages."""

import re
from pathlib import Path

from ..domain.configuration import NetworkConfigurationData
from ..modules.configuration.models import (
    ConfigurationCatalogEntry,
    ConfigurationManifest,
    LoadedConfiguration,
)
from .hashing import sha256_file


class ConfigurationIntegrityError(ValueError):
    """Raised when a controlled package identity or file hash is invalid."""


class JsonConfigurationLoader:
    _VERSION_DIRECTORY = re.compile(r"^v(?P<version>\d+\.\d+)$")

    def __init__(self, configuration_root: Path) -> None:
        self._root = configuration_root.resolve(strict=True)

    def load(self, version: str) -> LoadedConfiguration:
        match = self._VERSION_DIRECTORY.fullmatch(version)
        if match is None:
            raise ConfigurationIntegrityError(f"invalid configuration directory: {version}")

        package_directory = self._safe_resolve(self._root, version)
        manifest_path = self._safe_resolve(package_directory, "manifest.json")
        manifest_payload = manifest_path.read_bytes()
        manifest = ConfigurationManifest.model_validate_json(manifest_payload, strict=True)

        if manifest.version != match.group("version"):
            raise ConfigurationIntegrityError("manifest version does not match package directory")

        data_path = self._safe_resolve(package_directory, manifest.data_file.path)
        schema_path = self._safe_resolve(self._root, manifest.schema_file.path)
        data_sha256 = sha256_file(data_path)
        schema_sha256 = sha256_file(schema_path)
        if data_sha256 != manifest.data_file.sha256:
            raise ConfigurationIntegrityError("configuration data SHA-256 mismatch")
        if schema_sha256 != manifest.schema_file.sha256:
            raise ConfigurationIntegrityError("configuration schema SHA-256 mismatch")

        data = NetworkConfigurationData.model_validate_json(data_path.read_bytes(), strict=True)
        if data.schema_version != manifest.schema_version:
            raise ConfigurationIntegrityError("data and manifest schema versions differ")

        catalog_entry = ConfigurationCatalogEntry(
            configuration_id=manifest.configuration_id,
            version=manifest.version,
            status=manifest.status,
            package_path=package_directory.relative_to(self._root.parent.parent).as_posix(),
            schema_version=manifest.schema_version,
            package_sha256=sha256_file(manifest_path),
            data_sha256=data_sha256,
            schema_sha256=schema_sha256,
            source_references=manifest.source_references,
        )
        return LoadedConfiguration(
            catalog_entry=catalog_entry,
            manifest=manifest,
            data=data,
        )

    @staticmethod
    def _safe_resolve(root: Path, relative_path: str) -> Path:
        candidate = (root / relative_path).resolve(strict=True)
        if not candidate.is_relative_to(root):
            raise ConfigurationIntegrityError("configuration path escaped its controlled root")
        return candidate
