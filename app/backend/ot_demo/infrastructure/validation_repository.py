"""SQLite persistence for immutable I5 execution and evidence records."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import UUID

from ..domain.enums import EvidenceClass
from ..modules.validation.models import (
    EvidenceSnapshot,
    ValidationExecution,
    ValidationExecutionSummary,
)
from ..modules.telemetry.service import instant_to_epoch_ms
from .sqlite_migrations import apply_migrations


class ValidationRecordNotFound(LookupError):
    """Raised when a controlled validation record is absent."""


class ValidationRecordConflict(ValueError):
    """Raised when an immutable identity/checkpoint would be replaced."""


class ValidationRepository:
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

    def insert_execution(self, execution: ValidationExecution) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO validation_executions (
                    validation_execution_id, test_id, test_definition_version,
                    test_definition_sha256, catalogue_sha256, scenario_run_id,
                    scenario_mode, evidence_class, configuration_id,
                    configuration_version, application_build_id, status,
                    started_scenario_time_ms, finalised_scenario_time_ms,
                    verdict, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(execution.validation_execution_id),
                    execution.test_id,
                    execution.test_definition_version,
                    execution.test_definition_sha256,
                    execution.catalogue_sha256,
                    str(execution.scenario_run_id),
                    execution.scenario_mode.value,
                    execution.evidence_class.value,
                    execution.configuration_id,
                    execution.configuration_version,
                    execution.application_build_id,
                    execution.status.value,
                    instant_to_epoch_ms(execution.started_scenario_time),
                    None,
                    None,
                    execution.model_dump_json(),
                ),
            )

    def finalise_execution(self, execution: ValidationExecution) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE validation_executions SET
                    status = ?, finalised_scenario_time_ms = ?, verdict = ?,
                    payload_json = ?
                WHERE validation_execution_id = ? AND status = 'ACTIVE'
                """,
                (
                    execution.status.value,
                    instant_to_epoch_ms(execution.finalised_scenario_time),
                    execution.verdict.value if execution.verdict is not None else None,
                    execution.model_dump_json(),
                    str(execution.validation_execution_id),
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise ValidationRecordNotFound(
                    "active validation execution not found for finalisation"
                )

    def insert_evidence(self, snapshot: EvidenceSnapshot) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO validation_evidence_snapshots (
                        evidence_snapshot_id, validation_execution_id,
                        checkpoint_id, scenario_run_id, scenario_time_ms,
                        state_revision, canonical_payload_sha256, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(snapshot.evidence_snapshot_id),
                        str(snapshot.validation_execution_id),
                        snapshot.checkpoint_id,
                        str(snapshot.scenario_run_id),
                        instant_to_epoch_ms(snapshot.scenario_time),
                        snapshot.state_revision,
                        snapshot.canonical_payload_sha256,
                        snapshot.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict(
                "validation checkpoint identity already exists and cannot be replaced"
            ) from error

    def get_execution(self, execution_id: UUID) -> ValidationExecution:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM validation_executions "
                "WHERE validation_execution_id = ?",
                (str(execution_id),),
            ).fetchone()
        if row is None:
            raise ValidationRecordNotFound(f"validation execution not found: {execution_id}")
        return ValidationExecution.model_validate_json(row["payload_json"], strict=True)

    def list_evidence(self, execution_id: UUID) -> tuple[EvidenceSnapshot, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM validation_evidence_snapshots "
                "WHERE validation_execution_id = ? ORDER BY scenario_time_ms, checkpoint_id",
                (str(execution_id),),
            ).fetchall()
        return tuple(
            EvidenceSnapshot.model_validate_json(row["payload_json"], strict=True)
            for row in rows
        )

    def get_evidence(self, execution_id: UUID, checkpoint_id: str) -> EvidenceSnapshot:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM validation_evidence_snapshots "
                "WHERE validation_execution_id = ? AND checkpoint_id = ?",
                (str(execution_id), checkpoint_id),
            ).fetchone()
        if row is None:
            raise ValidationRecordNotFound(
                f"evidence checkpoint not found: {execution_id}/{checkpoint_id}"
            )
        return EvidenceSnapshot.model_validate_json(row["payload_json"], strict=True)

    def summary(self, execution_id: UUID) -> ValidationExecutionSummary:
        return ValidationExecutionSummary(
            execution=self.get_execution(execution_id),
            evidence_snapshots=self.list_evidence(execution_id),
        )

    def list_summaries(
        self,
        *,
        test_id: str | None = None,
        evidence_class: EvidenceClass | None = None,
        scenario_run_id: UUID | None = None,
    ) -> tuple[ValidationExecutionSummary, ...]:
        clauses: list[str] = []
        values: list[str] = []
        if test_id is not None:
            clauses.append("test_id = ?")
            values.append(test_id)
        if evidence_class is not None:
            clauses.append("evidence_class = ?")
            values.append(evidence_class.value)
        if scenario_run_id is not None:
            clauses.append("scenario_run_id = ?")
            values.append(str(scenario_run_id))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT validation_execution_id FROM validation_executions"
                + where
                + " ORDER BY started_scenario_time_ms, validation_execution_id",
                values,
            ).fetchall()
        return tuple(self.summary(UUID(row["validation_execution_id"])) for row in rows)
