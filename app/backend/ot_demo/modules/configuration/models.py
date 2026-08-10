"""Configuration package metadata owned by the configuration module."""

from pathlib import PurePosixPath
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from typing_extensions import Self

from ...domain.base import FrozenModel
from ...domain.configuration import NetworkConfigurationData
from ...domain.enums import ConfigurationStatus
from ...domain.value_objects import ConfigurationId, SemanticVersion, Sha256Digest


class HashedFile(FrozenModel):
    path: str = Field(min_length=1, max_length=240)
    sha256: Sha256Digest

    @field_validator("path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "." in path.parts:
            raise ValueError("artifact path must be a normalized relative POSIX path")
        return value


class ConfigurationManifest(FrozenModel):
    configuration_id: ConfigurationId
    version: SemanticVersion
    status: ConfigurationStatus
    schema_version: SemanticVersion
    data_file: HashedFile
    schema_file: HashedFile
    source_references: Annotated[tuple[str, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_controlled_identity_and_paths(self) -> Self:
        expected_configuration_id = f"network-configuration-v{self.version}"
        if self.configuration_id != expected_configuration_id:
            raise ValueError(
                "configuration_id must correspond to the declared version: "
                f"expected {expected_configuration_id}"
            )
        if self.data_file.path != "network.json":
            raise ValueError("configuration data file must be network.json")
        if self.schema_file.path != "schema/v1/network-configuration.schema.json":
            raise ValueError("configuration schema path is not the controlled v1 path")
        return self


class ConfigurationCatalogEntry(FrozenModel):
    configuration_id: ConfigurationId
    version: SemanticVersion
    status: ConfigurationStatus
    package_path: str
    schema_version: SemanticVersion
    package_sha256: Sha256Digest
    data_sha256: Sha256Digest
    schema_sha256: Sha256Digest
    source_references: tuple[str, ...]


class LoadedConfiguration(FrozenModel):
    catalog_entry: ConfigurationCatalogEntry
    manifest: ConfigurationManifest
    data: NetworkConfigurationData
