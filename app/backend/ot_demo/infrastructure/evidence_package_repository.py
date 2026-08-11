"""SQLite persistence for immutable I8 EvidencePackage records."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..modules.evidence_export.models import (
    CompositeEvidencePackage,
    EvidencePackage,
    SuspensionEvidencePackage,
)
from .sqlite_migrations import apply_migrations


class EvidencePackageNotFound(LookupError):
    """Raised when a controlled export package record is absent."""


class EvidencePackageConflict(ValueError):
    """Raised when an immutable package identity would be reused."""


class EvidencePackageRepository:
    def __init__(self, database_path: Path, migration_directory: Path) -> None:
        self.database_path = database_path
        self.migration_directory = migration_directory
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            apply_migrations(connection, migration_directory)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def insert(self, package: EvidencePackage) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO evidence_packages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        package.package_id,
                        str(package.validation_execution_id),
                        str(package.scenario_run_id),
                        package.evidence_class.value,
                        package.application_build_id,
                        package.manifest_sha256,
                        package.archive_sha256,
                        package.archive_path,
                        package.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise EvidencePackageConflict(
                "evidence package identity/path already exists and cannot be replaced"
            ) from error

    def get(self, package_id: str) -> EvidencePackage:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM evidence_packages WHERE package_id = ?",
                (package_id,),
            ).fetchone()
        if row is None:
            raise EvidencePackageNotFound(f"evidence package not found: {package_id}")
        return EvidencePackage.model_validate_json(row["payload_json"], strict=True)

    def list(self) -> tuple[EvidencePackage, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM evidence_packages ORDER BY rowid"
            ).fetchall()
        return tuple(
            EvidencePackage.model_validate_json(row["payload_json"], strict=True)
            for row in rows
        )

    def insert_composite(self, package: CompositeEvidencePackage) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO composite_evidence_packages VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        package.package_id,
                        str(package.composite_result_id),
                        package.evidence_class.value,
                        package.source_application_build_id,
                        package.manifest_sha256,
                        package.archive_sha256,
                        package.archive_path,
                        package.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise EvidencePackageConflict(
                "composite evidence package identity/path already exists"
            ) from error

    def get_composite(self, package_id: str) -> CompositeEvidencePackage:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM composite_evidence_packages WHERE package_id = ?",
                (package_id,),
            ).fetchone()
        if row is None:
            raise EvidencePackageNotFound(
                f"composite evidence package not found: {package_id}"
            )
        return CompositeEvidencePackage.model_validate_json(
            row["payload_json"], strict=True
        )

    def list_composites(self) -> tuple[CompositeEvidencePackage, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM composite_evidence_packages ORDER BY rowid"
            ).fetchall()
        return tuple(
            CompositeEvidencePackage.model_validate_json(
                row["payload_json"], strict=True
            )
            for row in rows
        )

    def insert_suspension(self, package: SuspensionEvidencePackage) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO suspension_evidence_packages VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        package.package_id,
                        str(package.suspension_record_id),
                        package.evidence_class.value,
                        package.verifier_application_build_id,
                        package.generation_application_build_id,
                        package.manifest_sha256,
                        package.archive_sha256,
                        package.archive_path,
                        package.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise EvidencePackageConflict(
                "suspension evidence package identity/path already exists"
            ) from error

    def get_suspension(self, package_id: str) -> SuspensionEvidencePackage:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM suspension_evidence_packages WHERE package_id=?",
                (package_id,),
            ).fetchone()
        if row is None:
            raise EvidencePackageNotFound(
                f"suspension evidence package not found: {package_id}"
            )
        return SuspensionEvidencePackage.model_validate_json(
            row["payload_json"], strict=True
        )

    def list_suspensions(self) -> tuple[SuspensionEvidencePackage, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM suspension_evidence_packages ORDER BY rowid"
            ).fetchall()
        return tuple(
            SuspensionEvidencePackage.model_validate_json(row["payload_json"], strict=True)
            for row in rows
        )
