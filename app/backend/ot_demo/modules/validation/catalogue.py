"""Hash-identified active and historical validation-catalogue resolution."""

import json
from pathlib import Path

from pydantic import ValidationError

from ...infrastructure.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from .models import (
    CriterionDefinition,
    DeterminationMethodDefinition,
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
        methods = [
            method
            for definition in catalogue.definitions
            for method in (
                (definition.determination_method,)
                if definition.determination_method is not None
                else tuple(
                    case.determination_method
                    for case in definition.constituent_cases
                    if case.determination_method is not None
                )
            )
        ]
        if manifest.method_count != len(methods) or manifest.criterion_count != sum(
            len(method.criteria) for method in methods
        ):
            raise ValidationCatalogueError(
                "controlled catalogue method/criterion counts do not match its payload"
            )
        return tuple(
            LoadedValidationDefinition(
                definition=definition,
                definition_sha256=sha256_bytes(
                    canonical_json_bytes(definition.model_dump(mode="json"))
                ),
                catalogue_id=catalogue.catalogue_id,
                catalogue_version=catalogue.catalogue_version,
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

    def get_method(
        self, test_id: str, *, case_id: str | None = None
    ) -> DeterminationMethodDefinition:
        loaded = self.get(test_id)
        if case_id is None:
            method = loaded.definition.determination_method
        else:
            matches = [
                case.determination_method
                for case in loaded.definition.constituent_cases
                if case.case_id == case_id
            ]
            method = matches[0] if len(matches) == 1 else None
        if method is None:
            raise ValidationCatalogueError(
                "target does not own a direct DC-006 determination method"
            )
        return method

    def get_criterion(
        self, test_id: str, criterion_id: str, *, case_id: str | None = None
    ) -> CriterionDefinition:
        method = self.get_method(test_id, case_id=case_id)
        matches = [item for item in method.criteria if item.criterion_id == criterion_id]
        if len(matches) != 1:
            raise ValidationCatalogueError("criterion identity did not resolve uniquely")
        return matches[0]

    def identity(self) -> tuple[str, str, str]:
        definitions = self.load()
        first = definitions[0]
        return (
            first.catalogue_id,
            str(first.catalogue_version),
            first.catalogue_sha256,
        )


class ValidationCatalogueResolver:
    """Resolve a definition by stored controlled identities, never by name alone."""

    def __init__(
        self,
        active_catalogue_path: Path,
        historical_catalogue_paths: tuple[Path, ...] = (),
    ) -> None:
        self.active_loader = ValidationCatalogueLoader(active_catalogue_path)
        self._loaders = (
            self.active_loader,
            *(ValidationCatalogueLoader(path) for path in historical_catalogue_paths),
        )
        identities = [loader.identity() for loader in self._loaders]
        if len(identities) != len(set(identities)):
            raise ValidationCatalogueError("catalogue revision identities must be unique")

    def load(self) -> tuple[LoadedValidationDefinition, ...]:
        return self.active_loader.load()

    def get(self, test_id: str) -> LoadedValidationDefinition:
        return self.active_loader.get(test_id)

    def raw_catalogue_sha256(self) -> str:
        return self.active_loader.raw_catalogue_sha256()

    def get_method(
        self, test_id: str, *, case_id: str | None = None
    ) -> DeterminationMethodDefinition:
        return self.active_loader.get_method(test_id, case_id=case_id)

    def get_criterion(
        self, test_id: str, criterion_id: str, *, case_id: str | None = None
    ) -> CriterionDefinition:
        return self.active_loader.get_criterion(
            test_id, criterion_id, case_id=case_id
        )

    def resolve_method(
        self,
        *,
        test_id: str,
        case_id: str | None,
        catalogue_version: str,
        catalogue_sha256: str,
        method_id: str,
        method_version: str,
        method_sha256: str,
    ) -> DeterminationMethodDefinition:
        loaded = self.resolve_catalogue(
            catalogue_version=catalogue_version,
            catalogue_sha256=catalogue_sha256,
        )
        definitions = [item for item in loaded if item.definition.test_id == test_id]
        if len(definitions) != 1:
            raise ValidationCatalogueError("method parent test did not resolve uniquely")
        definition = definitions[0].definition
        candidates = (
            (definition.determination_method,)
            if case_id is None
            else tuple(
                case.determination_method
                for case in definition.constituent_cases
                if case.case_id == case_id
            )
        )
        matches = [
            item
            for item in candidates
            if item is not None
            and item.method_id == method_id
            and str(item.version) == str(method_version)
            and item.method_sha256 == method_sha256
        ]
        if len(matches) != 1:
            raise ValidationCatalogueError(
                "historical determination method identity did not resolve uniquely"
            )
        return matches[0]

    def resolve_catalogue(
        self,
        *,
        catalogue_version: str,
        catalogue_sha256: str,
    ) -> tuple[LoadedValidationDefinition, ...]:
        matches: list[tuple[LoadedValidationDefinition, ...]] = []
        for loader in self._loaders:
            loaded = loader.load()
            if (
                str(loaded[0].catalogue_version) == str(catalogue_version)
                and loaded[0].catalogue_sha256 == catalogue_sha256
            ):
                matches.append(loaded)
        if len(matches) != 1:
            raise ValidationCatalogueError(
                "catalogue revision identity did not resolve uniquely"
            )
        return matches[0]

    def resolve_definition_identity(
        self,
        *,
        test_id: str,
        test_definition_version: str,
        test_definition_sha256: str,
    ) -> LoadedValidationDefinition:
        matches = [
            loaded
            for loader in self._loaders
            for loaded in loader.load()
            if (
                loaded.definition.test_id == test_id
                and str(loaded.definition.version) == str(test_definition_version)
                and loaded.definition_sha256 == test_definition_sha256
            )
        ]
        if len(matches) != 1:
            raise ValidationCatalogueError(
                "test-definition identity did not resolve uniquely across controlled revisions"
            )
        return matches[0]

    def resolve(
        self,
        *,
        test_id: str,
        catalogue_version: str,
        catalogue_sha256: str,
        test_definition_version: str,
        test_definition_sha256: str,
    ) -> LoadedValidationDefinition:
        matches: list[LoadedValidationDefinition] = []
        for loader in self._loaders:
            for loaded in loader.load():
                if (
                    loaded.definition.test_id == test_id
                    and str(loaded.catalogue_version) == str(catalogue_version)
                    and loaded.catalogue_sha256 == catalogue_sha256
                    and str(loaded.definition.version) == str(test_definition_version)
                    and loaded.definition_sha256 == test_definition_sha256
                ):
                    matches.append(loaded)
        if len(matches) != 1:
            raise ValidationCatalogueError(
                "execution-bound catalogue/test-definition identity did not resolve uniquely"
            )
        return matches[0]

    def is_active(self, loaded: LoadedValidationDefinition) -> bool:
        return loaded.catalogue_sha256 == self.raw_catalogue_sha256()
