"""SQLite persistence for immutable I5 execution and evidence records."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import UUID

from ..domain.enums import EvidenceClass
from ..modules.validation.models import (
    CompositeValidationResult,
    EvidenceSnapshot,
    ValidationExecution,
    ValidationExecutionSummary,
    ValidationAttempt,
    ValidationTargetSelection,
    ExecutedValidationResult,
    ValidationSuspensionRecord,
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
                    test_definition_sha256, catalogue_version, catalogue_sha256,
                    case_id, case_definition_version, case_definition_sha256, scenario_run_id,
                    scenario_mode, evidence_class, configuration_id,
                    configuration_version, application_build_id, status,
                    started_scenario_time_ms, finalised_scenario_time_ms,
                    verdict, payload_json, validation_attempt_id,
                    target_selection_id, executed_result_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(execution.validation_execution_id),
                    execution.test_id,
                    execution.test_definition_version,
                    execution.test_definition_sha256,
                    execution.catalogue_version,
                    execution.catalogue_sha256,
                    execution.case_id,
                    execution.case_definition_version,
                    execution.case_definition_sha256,
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
                    str(execution.validation_attempt_id) if execution.validation_attempt_id else None,
                    str(execution.target_selection_id) if execution.target_selection_id else None,
                    str(execution.executed_result_id) if execution.executed_result_id else None,
                ),
            )

    def insert_target_and_attempt(
        self,
        target: ValidationTargetSelection,
        attempt: ValidationAttempt,
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO validation_target_selections "
                    "(target_selection_id,test_id,case_id,catalogue_sha256,test_definition_sha256,created_at_ms,payload_json) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        str(target.target_selection_id), target.test_id, target.case_id,
                        target.catalogue_sha256, target.test_definition_sha256,
                        instant_to_epoch_ms(target.created_at), target.model_dump_json(),
                    ),
                )
                connection.execute(
                    "INSERT INTO validation_attempts "
                    "(validation_attempt_id,target_selection_id,status,scenario_run_id,validation_execution_id,created_at_ms,updated_at_ms,payload_json) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        str(attempt.validation_attempt_id), str(attempt.target_selection_id),
                        attempt.status.value, None, None,
                        instant_to_epoch_ms(attempt.created_at),
                        instant_to_epoch_ms(attempt.updated_at), attempt.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("validation target/attempt identity conflicts") from error

    def bind_attempt_execution(
        self, attempt: ValidationAttempt, execution: ValidationExecution
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE validation_attempts SET status=?,scenario_run_id=?,validation_execution_id=?,updated_at_ms=?,payload_json=? "
                "WHERE validation_attempt_id=? AND status='NOT_STARTED'",
                (
                    attempt.status.value, str(attempt.scenario_run_id),
                    str(attempt.validation_execution_id), instant_to_epoch_ms(attempt.updated_at),
                    attempt.model_dump_json(), str(attempt.validation_attempt_id),
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise ValidationRecordConflict("validation attempt is not available for execution")
            connection.execute(
                "INSERT INTO validation_executions (validation_execution_id,test_id,test_definition_version,test_definition_sha256,catalogue_version,catalogue_sha256,case_id,case_definition_version,case_definition_sha256,scenario_run_id,scenario_mode,evidence_class,configuration_id,configuration_version,application_build_id,status,started_scenario_time_ms,finalised_scenario_time_ms,verdict,payload_json,validation_attempt_id,target_selection_id,executed_result_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(execution.validation_execution_id), execution.test_id,
                    execution.test_definition_version, execution.test_definition_sha256,
                    execution.catalogue_version, execution.catalogue_sha256, execution.case_id,
                    execution.case_definition_version, execution.case_definition_sha256,
                    str(execution.scenario_run_id), execution.scenario_mode.value,
                    execution.evidence_class.value, execution.configuration_id,
                    execution.configuration_version, execution.application_build_id,
                    execution.status.value, instant_to_epoch_ms(execution.started_scenario_time),
                    None, None, execution.model_dump_json(),
                    str(execution.validation_attempt_id), str(execution.target_selection_id), None,
                ),
            )

    def bind_attempt_run(self, attempt: ValidationAttempt) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE validation_attempts SET status=?,scenario_run_id=?,updated_at_ms=?,payload_json=? WHERE validation_attempt_id=? AND status='NOT_STARTED'",
                (attempt.status.value, str(attempt.scenario_run_id), instant_to_epoch_ms(attempt.updated_at), attempt.model_dump_json(), str(attempt.validation_attempt_id)),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise ValidationRecordConflict("validation attempt cannot enter the scenario")

    def insert_composite(self, composite: CompositeValidationResult) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO composite_validation_results (
                        composite_result_id, test_id, test_definition_version,
                        test_definition_sha256, catalogue_version, catalogue_sha256,
                        evidence_class, application_build_id, configuration_id,
                        configuration_version, completeness_status, status,
                        determination, created_at_ms, finalised_at_ms, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(composite.composite_result_id),
                        composite.test_id,
                        composite.test_definition_version,
                        composite.test_definition_sha256,
                        composite.catalogue_version,
                        composite.catalogue_sha256,
                        composite.evidence_class.value,
                        composite.application_build_id,
                        composite.configuration_id,
                        composite.configuration_version,
                        composite.completeness.status.value,
                        composite.status.value,
                        composite.determination.value if composite.determination else None,
                        instant_to_epoch_ms(composite.created_at),
                        (
                            instant_to_epoch_ms(composite.finalised_at)
                            if composite.finalised_at is not None
                            else None
                        ),
                        composite.model_dump_json(),
                    ),
                )
                for link in composite.constituent_links:
                    if link.validation_execution_id is not None:
                        connection.execute(
                            "INSERT INTO composite_validation_constituents (composite_result_id,case_id,validation_execution_id,scenario_run_id,case_definition_sha256,constituent_verdict,payload_json) VALUES (?,?,?,?,?,?,?)",
                            (str(composite.composite_result_id), link.case_id,
                             str(link.validation_execution_id), str(link.scenario_run_id),
                             link.case_definition_sha256,
                             link.constituent_verdict.value if link.constituent_verdict else None,
                             link.model_dump_json()),
                        )
                    connection.execute(
                        "INSERT INTO composite_validation_constituent_sources (composite_result_id,case_id,source_kind,validation_execution_id,suspension_record_id,constituent_verdict,payload_json) VALUES (?,?,?,?,?,?,?)",
                        (str(composite.composite_result_id), link.case_id,
                         link.source_kind.value,
                         str(link.validation_execution_id) if link.validation_execution_id else None,
                         str(link.suspension_record_id) if link.suspension_record_id else None,
                         link.constituent_verdict.value if link.constituent_verdict else None,
                         link.model_dump_json()),
                    )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict(
                "composite identity or constituent membership conflicts with immutable history"
            ) from error

    def finalise_composite(self, composite: CompositeValidationResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE composite_validation_results SET
                    completeness_status = ?, status = ?, determination = ?,
                    finalised_at_ms = ?, payload_json = ?
                WHERE composite_result_id = ? AND status = 'DRAFT'
                """,
                (
                    composite.completeness.status.value,
                    composite.status.value,
                    composite.determination.value if composite.determination else None,
                    instant_to_epoch_ms(composite.finalised_at),
                    composite.model_dump_json(),
                    str(composite.composite_result_id),
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise ValidationRecordNotFound(
                    "draft composite validation result not found for finalisation"
                )

    def get_composite(self, composite_id: UUID) -> CompositeValidationResult:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM composite_validation_results "
                "WHERE composite_result_id = ?",
                (str(composite_id),),
            ).fetchone()
        if row is None:
            raise ValidationRecordNotFound(
                f"composite validation result not found: {composite_id}"
            )
        return CompositeValidationResult.model_validate_json(
            row["payload_json"], strict=True
        )

    def list_composites(
        self, *, test_id: str | None = None
    ) -> tuple[CompositeValidationResult, ...]:
        where = " WHERE test_id = ?" if test_id is not None else ""
        values = (test_id,) if test_id is not None else ()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM composite_validation_results"
                + where
                + " ORDER BY created_at_ms, composite_result_id",
                values,
            ).fetchall()
        return tuple(
            CompositeValidationResult.model_validate_json(
                row["payload_json"], strict=True
            )
            for row in rows
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

    def finalise_execution_result(
        self,
        execution: ValidationExecution,
        attempt: ValidationAttempt,
        result: ExecutedValidationResult,
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE validation_executions SET status=?,finalised_scenario_time_ms=?,verdict=?,payload_json=?,executed_result_id=? "
                    "WHERE validation_execution_id=? AND status='ACTIVE'",
                    (
                        execution.status.value, instant_to_epoch_ms(execution.finalised_scenario_time),
                        execution.verdict.value, execution.model_dump_json(), str(result.executed_result_id),
                        str(execution.validation_execution_id),
                    ),
                )
                if connection.execute("SELECT changes()").fetchone()[0] != 1:
                    raise ValidationRecordConflict("active validation execution not found")
                connection.execute(
                    "UPDATE validation_attempts SET status=?,updated_at_ms=?,payload_json=? "
                    "WHERE validation_attempt_id=? AND status='ACTIVE'",
                    (attempt.status.value, instant_to_epoch_ms(attempt.updated_at), attempt.model_dump_json(), str(attempt.validation_attempt_id)),
                )
                if connection.execute("SELECT changes()").fetchone()[0] != 1:
                    raise ValidationRecordConflict("active validation attempt not found")
                connection.execute(
                    "INSERT INTO executed_validation_results (executed_result_id,validation_attempt_id,validation_execution_id,verdict,result_sha256,finalised_at_ms,payload_json) VALUES (?,?,?,?,?,?,?)",
                    (str(result.executed_result_id), str(result.validation_attempt_id), str(result.validation_execution_id), result.verdict.value, result.result_sha256, instant_to_epoch_ms(result.finalised_at), result.model_dump_json()),
                )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("executed validation result conflicts with immutable history") from error

    def insert_finalised_suspension(
        self,
        attempt: ValidationAttempt,
        record: ValidationSuspensionRecord,
    ) -> None:
        try:
            with self._connect() as connection:
                draft_payload = record.model_copy(update={"status": "DRAFT", "finalised_at": None}).model_dump_json()
                connection.execute(
                    "INSERT INTO validation_suspension_records (suspension_record_id,validation_attempt_id,target_selection_id,condition_id,lifecycle_position,status,reason_code,deterministic_fingerprint,scenario_run_id,validation_execution_id,finalised_at_ms,payload_json) VALUES (?,?,?,?,?,'DRAFT',?,?,?,?,?,?)",
                    (str(record.suspension_record_id), str(record.validation_attempt_id), str(record.target_selection_id), record.condition_id.value, record.lifecycle_position.value, record.reason_code, record.deterministic_fingerprint, str(record.scenario_run_id) if record.scenario_run_id else None, str(record.validation_execution_id) if record.validation_execution_id else None, instant_to_epoch_ms(record.finalised_at), draft_payload),
                )
                for evidence in record.evidence:
                    connection.execute(
                        "INSERT INTO validation_suspension_evidence (evidence_id,suspension_record_id,condition_id,evidence_type,failure_code,payload_sha256,payload_json) VALUES (?,?,?,?,?,?,?)",
                        (str(evidence.evidence_id), str(record.suspension_record_id), evidence.condition_id.value, evidence.evidence_type, evidence.failure_code, evidence.payload_sha256, evidence.model_dump_json()),
                    )
                connection.execute(
                    "UPDATE validation_suspension_records SET status='FINALISED',payload_json=? WHERE suspension_record_id=? AND status='DRAFT'",
                    (record.model_dump_json(), str(record.suspension_record_id)),
                )
                connection.execute(
                    "UPDATE validation_attempts SET status='SUSPENDED',updated_at_ms=?,payload_json=? WHERE validation_attempt_id=? AND status IN ('NOT_STARTED','ACTIVE','INCOMPLETE')",
                    (instant_to_epoch_ms(attempt.updated_at), attempt.model_dump_json(), str(attempt.validation_attempt_id)),
                )
                if connection.execute("SELECT changes()").fetchone()[0] != 1:
                    raise ValidationRecordConflict("validation attempt cannot be suspended")
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("suspension record conflicts with immutable history") from error

    def get_target(self, target_id: UUID) -> ValidationTargetSelection:
        return self._get_json("validation_target_selections", "target_selection_id", target_id, ValidationTargetSelection)

    def get_attempt(self, attempt_id: UUID) -> ValidationAttempt:
        return self._get_json("validation_attempts", "validation_attempt_id", attempt_id, ValidationAttempt)

    def get_suspension(self, record_id: UUID) -> ValidationSuspensionRecord:
        return self._get_json("validation_suspension_records", "suspension_record_id", record_id, ValidationSuspensionRecord)

    def list_suspensions(self) -> tuple[ValidationSuspensionRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload_json FROM validation_suspension_records WHERE status='FINALISED' ORDER BY finalised_at_ms,suspension_record_id").fetchall()
        return tuple(ValidationSuspensionRecord.model_validate_json(row["payload_json"], strict=True) for row in rows)

    def _get_json(self, table: str, key: str, identity: UUID, model):
        with self._connect() as connection:
            row = connection.execute(f"SELECT payload_json FROM {table} WHERE {key}=?", (str(identity),)).fetchone()
        if row is None:
            raise ValidationRecordNotFound(f"controlled validation record not found: {identity}")
        return model.model_validate_json(row["payload_json"], strict=True)

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
