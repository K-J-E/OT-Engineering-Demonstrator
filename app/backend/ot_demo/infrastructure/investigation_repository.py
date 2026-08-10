"""SQLite persistence for immutable I7 defect, correction and repeat records."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import UUID

from ..modules.investigation.models import CorrectionRecord, DefectRecord, RepeatLink
from ..modules.telemetry.service import instant_to_epoch_ms
from .sqlite_migrations import apply_migrations


class InvestigationRecordNotFound(LookupError):
    """Raised when a controlled I7 record is absent."""


class InvestigationRecordConflict(ValueError):
    """Raised when immutable I7 identity would be replaced."""


class InvestigationRepository:
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

    def insert_defect(self, record: DefectRecord) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO investigation_defect_records VALUES (?, ?, ?, ?, ?)",
                    (
                        str(record.defect_record_id),
                        record.defect_id,
                        str(record.original_failed_execution_id),
                        instant_to_epoch_ms(record.recorded_scenario_time),
                        record.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise InvestigationRecordConflict(
                "the controlled defect record already exists and cannot be replaced"
            ) from error

    def insert_correction(self, record: CorrectionRecord) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO investigation_correction_records VALUES (?, ?, ?, ?, ?)",
                    (
                        str(record.correction_record_id),
                        record.correction_id,
                        str(record.defect_record_id),
                        instant_to_epoch_ms(record.recorded_scenario_time),
                        record.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise InvestigationRecordConflict(
                "the controlled correction record already exists and cannot be replaced"
            ) from error

    def insert_repeat_link(self, record: RepeatLink) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO investigation_repeat_links VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(record.repeat_link_id),
                        record.relationship_type.value,
                        str(record.original_execution_id),
                        str(record.new_execution_id),
                        str(record.defect_record_id),
                        str(record.correction_record_id),
                        record.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise InvestigationRecordConflict(
                "the controlled repeat/regression link already exists and cannot be replaced"
            ) from error

    def get_defect(self, defect_id: str = "DEF-001") -> DefectRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM investigation_defect_records WHERE defect_id = ?",
                (defect_id,),
            ).fetchone()
        return None if row is None else DefectRecord.model_validate_json(row[0], strict=True)

    def get_correction(self, correction_id: str = "COR-001") -> CorrectionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM investigation_correction_records WHERE correction_id = ?",
                (correction_id,),
            ).fetchone()
        return None if row is None else CorrectionRecord.model_validate_json(row[0], strict=True)

    def list_repeat_links(self, defect_record_id: UUID) -> tuple[RepeatLink, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM investigation_repeat_links "
                "WHERE defect_record_id = ? ORDER BY rowid",
                (str(defect_record_id),),
            ).fetchall()
        return tuple(RepeatLink.model_validate_json(row[0], strict=True) for row in rows)
