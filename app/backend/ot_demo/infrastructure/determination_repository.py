"""SQLite persistence for immutable DC-006 determination records."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import UUID

from ..domain.enums import (
    DeterminationContextStatus,
    ValidationAttemptStatus,
    ValidationExecutionStatus,
)
from ..modules.telemetry.service import instant_to_epoch_ms
from ..modules.validation.models import (
    CriterionFinding,
    DeterminationContext,
    DeterminationContextMember,
    DeterminationSourceRecord,
    EngineeringReviewFinalisation,
    EngineeringReviewProposal,
    ExecutedValidationResult,
    ValidationAttempt,
    ValidationExecution,
)
from .sqlite_migrations import apply_migrations
from .validation_repository import ValidationRecordConflict, ValidationRecordNotFound


class DeterminationRepository:
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

    def insert_produced_source(
        self,
        record: DeterminationSourceRecord,
        *,
        producer_kind: str,
        origin_identity: str,
        origin_identity_sha256: str,
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO determination_source_records "
                    "(source_record_id,source_type,owner_module,application_build_id,evidence_class,canonical_payload_sha256,created_at_ms,payload_json) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        str(record.source_record_id), record.source_type,
                        record.owner_module, record.application_build_id,
                        record.evidence_class.value, record.canonical_payload_sha256,
                        instant_to_epoch_ms(record.created_at), record.model_dump_json(),
                    ),
                )
                connection.execute(
                    "INSERT INTO determination_source_origin_bindings "
                    "(validation_attempt_id,source_role,source_record_id,producer_kind,"
                    "origin_identity,origin_identity_sha256,created_at_ms) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        str(record.validation_attempt_id), record.source_role,
                        str(record.source_record_id), producer_kind, origin_identity,
                        origin_identity_sha256, instant_to_epoch_ms(record.created_at),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict(
                "attempt/role already owns a backend-produced authority source"
            ) from error

    def source_ids_for_attempt(self, attempt_id: UUID) -> dict[str, UUID]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT source_role,source_record_id "
                "FROM determination_source_origin_bindings "
                "WHERE validation_attempt_id=? ORDER BY source_role",
                (str(attempt_id),),
            ).fetchall()
        return {row["source_role"]: UUID(row["source_record_id"]) for row in rows}

    def get_source(self, record_id: UUID) -> DeterminationSourceRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM determination_source_records WHERE source_record_id=?",
                (str(record_id),),
            ).fetchone()
        if row is None:
            raise ValidationRecordNotFound(f"determination source not found: {record_id}")
        return DeterminationSourceRecord.model_validate_json(row["payload_json"], strict=True)

    def insert_context(self, context: DeterminationContext) -> None:
        if context.status is not DeterminationContextStatus.DRAFT or context.members:
            raise ValidationRecordConflict("new determination context must be an empty draft")
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO determination_contexts "
                    "(determination_context_id,validation_attempt_id,test_id,case_id,catalogue_version,catalogue_sha256,method_id,method_version,method_sha256,context_kind,status,scenario_run_id,validation_execution_id,created_at_ms,frozen_at_ms,payload_json,procedure_validation_execution_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(context.determination_context_id), str(context.validation_attempt_id),
                        context.test_id, context.case_id, context.catalogue_version,
                        context.catalogue_sha256, context.method_id, context.method_version,
                        context.method_sha256, context.context_kind.value, DeterminationContextStatus.DRAFT.value,
                        str(context.scenario_run_id) if context.scenario_run_id else None,
                        (
                            str(context.validation_execution_id)
                            if context.context_kind.value == "SCENARIO_EXECUTION"
                            else None
                        ),
                        instant_to_epoch_ms(context.created_at), None, context.model_dump_json(),
                        (
                            str(context.validation_execution_id)
                            if context.context_kind.value != "SCENARIO_EXECUTION"
                            else None
                        ),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("determination context identity conflicts") from error

    def insert_frozen_context(self, context: DeterminationContext) -> None:
        if context.status is not DeterminationContextStatus.FROZEN:
            raise ValidationRecordConflict("controlled context must be frozen atomically")
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO determination_contexts "
                    "(determination_context_id,validation_attempt_id,test_id,case_id,catalogue_version,catalogue_sha256,method_id,method_version,method_sha256,context_kind,status,scenario_run_id,validation_execution_id,created_at_ms,frozen_at_ms,payload_json,procedure_validation_execution_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(context.determination_context_id), str(context.validation_attempt_id),
                        context.test_id, context.case_id, context.catalogue_version,
                        context.catalogue_sha256, context.method_id, context.method_version,
                        context.method_sha256, context.context_kind.value, DeterminationContextStatus.DRAFT.value,
                        str(context.scenario_run_id) if context.scenario_run_id else None,
                        (
                            str(context.validation_execution_id)
                            if context.context_kind.value == "SCENARIO_EXECUTION"
                            else None
                        ),
                        instant_to_epoch_ms(context.created_at), None,
                        context.model_dump_json(),
                        (
                            str(context.validation_execution_id)
                            if context.context_kind.value != "SCENARIO_EXECUTION"
                            else None
                        ),
                    ),
                )
                for member in context.members:
                    connection.execute(
                        "INSERT INTO determination_context_members "
                        "(determination_context_id,role,source_record_id,source_record_sha256,payload_json) VALUES (?,?,?,?,?)",
                        (
                            str(context.determination_context_id), member.role,
                            str(member.source_record_id), member.source_record_sha256,
                            member.model_dump_json(),
                        ),
                    )
                connection.execute(
                    "UPDATE determination_contexts SET status='FROZEN',frozen_at_ms=?,payload_json=? "
                    "WHERE determination_context_id=? AND status='DRAFT'",
                    (
                        instant_to_epoch_ms(context.frozen_at), context.model_dump_json(),
                        str(context.determination_context_id),
                    ),
                )
                if connection.execute("SELECT changes()").fetchone()[0] != 1:
                    raise ValidationRecordConflict("determination context freeze failed")
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("frozen determination context conflicts") from error

    def add_member(
        self, context_id: UUID, member: DeterminationContextMember
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO determination_context_members "
                    "(determination_context_id,role,source_record_id,source_record_sha256,payload_json) VALUES (?,?,?,?,?)",
                    (
                        str(context_id), member.role, str(member.source_record_id),
                        member.source_record_sha256, member.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("determination context member conflicts") from error

    def freeze_context(self, context: DeterminationContext) -> None:
        if context.status is not DeterminationContextStatus.FROZEN:
            raise ValidationRecordConflict("context finalisation requires FROZEN state")
        with self._connect() as connection:
            connection.execute(
                "UPDATE determination_contexts SET status='FROZEN',frozen_at_ms=?,payload_json=? "
                "WHERE determination_context_id=? AND status='DRAFT'",
                (
                    instant_to_epoch_ms(context.frozen_at), context.model_dump_json(),
                    str(context.determination_context_id),
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise ValidationRecordConflict("draft determination context is unavailable")

    def get_context(self, context_id: UUID) -> DeterminationContext:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM determination_contexts WHERE determination_context_id=?",
                (str(context_id),),
            ).fetchone()
        if row is None:
            raise ValidationRecordNotFound(f"determination context not found: {context_id}")
        return DeterminationContext.model_validate_json(row["payload_json"], strict=True)

    def insert_finding(self, finding: CriterionFinding) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO criterion_findings "
                    "(criterion_finding_id,determination_context_id,criterion_id,criterion_sha256,status,finding_sha256,finalised_at_ms,payload_json) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        str(finding.criterion_finding_id), str(finding.determination_context_id),
                        finding.criterion_id, finding.criterion_sha256, finding.status.value,
                        finding.finding_sha256,
                        instant_to_epoch_ms(finding.finalised_at) if finding.finalised_at else None,
                        finding.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("criterion finding identity conflicts") from error

    def list_findings(self, context_id: UUID) -> tuple[CriterionFinding, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM criterion_findings WHERE determination_context_id=? ORDER BY criterion_id",
                (str(context_id),),
            ).fetchall()
        return tuple(CriterionFinding.model_validate_json(row["payload_json"], strict=True) for row in rows)

    def insert_review_proposal(self, proposal: EngineeringReviewProposal) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO engineering_review_proposals "
                    "(review_proposal_id,determination_context_id,criterion_id,proposer_actor_id,proposed_finding,proposal_sha256,proposed_at_ms,payload_json) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        str(proposal.review_proposal_id), str(proposal.determination_context_id),
                        proposal.criterion_id, proposal.proposer_actor_id,
                        proposal.proposed_finding.value, proposal.proposal_sha256,
                        instant_to_epoch_ms(proposal.proposed_at), proposal.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("engineering-review proposal conflicts") from error

    def get_review_proposal(self, proposal_id: UUID) -> EngineeringReviewProposal:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM engineering_review_proposals WHERE review_proposal_id=?",
                (str(proposal_id),),
            ).fetchone()
        if row is None:
            raise ValidationRecordNotFound(f"review proposal not found: {proposal_id}")
        return EngineeringReviewProposal.model_validate_json(row["payload_json"], strict=True)

    def finalise_review(
        self,
        finalisation: EngineeringReviewFinalisation,
        finding: CriterionFinding,
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO engineering_review_finalisations "
                    "(review_finalisation_id,review_proposal_id,determination_context_id,criterion_id,reviewer_actor_id,final_finding,finalisation_sha256,finalised_at_ms,payload_json) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        str(finalisation.review_finalisation_id),
                        str(finalisation.review_proposal_id),
                        str(finalisation.determination_context_id), finalisation.criterion_id,
                        finalisation.reviewer_actor_id, finalisation.final_finding.value,
                        finalisation.finalisation_sha256,
                        instant_to_epoch_ms(finalisation.finalised_at),
                        finalisation.model_dump_json(),
                    ),
                )
                connection.execute(
                    "INSERT INTO criterion_findings "
                    "(criterion_finding_id,determination_context_id,criterion_id,criterion_sha256,status,finding_sha256,finalised_at_ms,payload_json) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        str(finding.criterion_finding_id), str(finding.determination_context_id),
                        finding.criterion_id, finding.criterion_sha256, finding.status.value,
                        finding.finding_sha256, instant_to_epoch_ms(finding.finalised_at),
                        finding.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("engineering-review finalisation conflicts") from error

    def insert_result(self, result: ExecutedValidationResult) -> None:
        if result.determination_context_id is None:
            raise ValidationRecordConflict("DC-006 result requires determination context")
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO dc006_executed_validation_results "
                    "(executed_result_id,validation_attempt_id,determination_context_id,validation_execution_id,test_id,case_id,catalogue_version,catalogue_sha256,method_id,method_sha256,verdict,result_sha256,finalised_at_ms,payload_json) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(result.executed_result_id), str(result.validation_attempt_id),
                        str(result.determination_context_id),
                        str(result.validation_execution_id) if result.validation_execution_id else None,
                        result.test_id, result.case_id, result.catalogue_version,
                        result.catalogue_sha256, result.method_id, result.method_sha256,
                        result.verdict.value, result.result_sha256,
                        instant_to_epoch_ms(result.finalised_at), result.model_dump_json(),
                    ),
                )
                if result.validation_execution_id is not None:
                    execution_row = connection.execute(
                        "SELECT payload_json FROM validation_executions WHERE validation_execution_id=?",
                        (str(result.validation_execution_id),),
                    ).fetchone()
                    procedure = execution_row is None
                    if procedure:
                        execution_row = connection.execute(
                            "SELECT payload_json FROM procedure_validation_executions WHERE validation_execution_id=?",
                            (str(result.validation_execution_id),),
                        ).fetchone()
                    if execution_row is None:
                        raise ValidationRecordConflict("bound validation execution not found")
                    execution = ValidationExecution.model_validate_json(
                        execution_row["payload_json"], strict=True
                    )
                    finalised_execution = execution.model_copy(
                        update={
                            "status": ValidationExecutionStatus.FINALISED,
                            (
                                "finalised_at"
                                if procedure
                                else "finalised_scenario_time"
                            ): result.finalised_at,
                            "observed_result": {
                                "determination_context_id": str(result.determination_context_id),
                                "criterion_finding_ids": [
                                    str(item) for item in result.criterion_finding_ids
                                ],
                            },
                            "calculations": {
                                "comparison_method": "DC006_CONTROLLED_CRITERION_AGGREGATE",
                                "criterion_count": len(result.criterion_finding_ids),
                            },
                            "evidence_snapshot_ids": result.evidence_snapshot_ids,
                            "verdict": result.verdict,
                            "verdict_reason": (
                                "Complete controlled criterion set contains at least one NOT_SATISFIED finding."
                                if result.verdict.value == "FAIL"
                                else "Complete controlled criterion set contains only SATISFIED findings."
                            ),
                            "executed_result_id": result.executed_result_id,
                        }
                    )
                    table = (
                        "procedure_validation_executions" if procedure else "validation_executions"
                    )
                    final_time_column = "finalised_at_ms" if procedure else "finalised_scenario_time_ms"
                    connection.execute(
                        f"UPDATE {table} SET status='FINALISED',{final_time_column}=?,verdict=?,payload_json=?,executed_result_id=? "
                        "WHERE validation_execution_id=? AND status='ACTIVE'",
                        (
                            instant_to_epoch_ms(result.finalised_at), result.verdict.value,
                            finalised_execution.model_dump_json(), str(result.executed_result_id),
                            str(result.validation_execution_id),
                        ),
                    )
                    if connection.execute("SELECT changes()").fetchone()[0] != 1:
                        raise ValidationRecordConflict("active validation execution unavailable")
                    if not procedure:
                        connection.execute(
                            "INSERT INTO executed_validation_results "
                            "(executed_result_id,validation_attempt_id,validation_execution_id,verdict,result_sha256,finalised_at_ms,payload_json) VALUES (?,?,?,?,?,?,?)",
                            (
                                str(result.executed_result_id), str(result.validation_attempt_id),
                                str(result.validation_execution_id), result.verdict.value,
                                result.result_sha256, instant_to_epoch_ms(result.finalised_at),
                                result.model_dump_json(),
                            ),
                        )
                attempt_row = connection.execute(
                    "SELECT payload_json FROM validation_attempts WHERE validation_attempt_id=?",
                    (str(result.validation_attempt_id),),
                ).fetchone()
                if attempt_row is None:
                    raise ValidationRecordConflict("validation attempt not found for result")
                attempt = ValidationAttempt.model_validate_json(
                    attempt_row["payload_json"], strict=True
                ).model_copy(
                    update={
                        "status": ValidationAttemptStatus.EXECUTED,
                        "updated_at": result.finalised_at,
                    }
                )
                connection.execute(
                    "UPDATE validation_attempts SET status=?,updated_at_ms=?,payload_json=? "
                    "WHERE validation_attempt_id=? AND status IN ('NOT_STARTED','ACTIVE','INCOMPLETE')",
                    (
                        ValidationAttemptStatus.EXECUTED.value,
                        instant_to_epoch_ms(result.finalised_at),
                        attempt.model_dump_json(),
                        str(result.validation_attempt_id),
                    ),
                )
                if connection.execute("SELECT changes()").fetchone()[0] != 1:
                    raise ValidationRecordConflict("validation attempt is not available for result")
        except sqlite3.IntegrityError as error:
            raise ValidationRecordConflict("DC-006 executed result conflicts") from error

    def get_result(self, result_id: UUID) -> ExecutedValidationResult:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM dc006_executed_validation_results WHERE executed_result_id=?",
                (str(result_id),),
            ).fetchone()
        if row is None:
            raise ValidationRecordNotFound(f"DC-006 executed result not found: {result_id}")
        return ExecutedValidationResult.model_validate_json(row["payload_json"], strict=True)
