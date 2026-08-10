"""SQLite transaction and persistence adapters for I3 run-scoped records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from ..domain.enums import (
    AlarmAcknowledgementState,
    AlarmType,
    EvidenceClass,
    FaultType,
    NetworkStateLabel,
    OperationalEventSource,
    OperationalEventType,
    ScenarioMode,
    ScenarioRunStatus,
    SourceAvailability,
    SwitchState,
    TelemetryQuality,
    WorkflowStage,
)
from ..modules.events.models import OperationalEvent
from ..modules.outage.models import OutageResult
from ..modules.scenario.models import CommandResult, RunContext
from ..modules.telemetry.models import AlarmRecord, TelemetryPoint
from ..modules.telemetry.service import epoch_ms_to_instant, instant_to_epoch_ms
from ..modules.topology.models import TopologyResult
from .sqlite_migrations import apply_migrations


class ScenarioRecordNotFound(LookupError):
    """Raised when a requested run-scoped record is absent."""


class ScenarioRepository:
    """Open one explicit SQLite transaction for each coordinator operation."""

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

    @contextmanager
    def transaction(self) -> Iterator["ScenarioUnitOfWork"]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield ScenarioUnitOfWork(connection)
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()


class ScenarioUnitOfWork:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def has_mutable_run(self) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM scenario_runs WHERE status != 'CLOSED' LIMIT 1"
        ).fetchone()
        return row is not None

    def get_command_result(self, command_id: UUID) -> tuple[str, CommandResult] | None:
        row = self.connection.execute(
            "SELECT request_sha256, result_json FROM scenario_command_results "
            "WHERE command_id = ?",
            (str(command_id),),
        ).fetchone()
        if row is None:
            return None
        return row["request_sha256"], CommandResult.model_validate_json(
            row["result_json"], strict=True
        )

    def insert_command_result(
        self,
        *,
        command_id: UUID,
        scenario_run_id: UUID,
        request_sha256: str,
        result: CommandResult,
    ) -> None:
        self.connection.execute(
            "INSERT INTO scenario_command_results "
            "(command_id, scenario_run_id, request_sha256, result_json) "
            "VALUES (?, ?, ?, ?)",
            (
                str(command_id),
                str(scenario_run_id),
                request_sha256,
                result.model_dump_json(),
            ),
        )

    def insert_run(self, run: RunContext) -> None:
        self.connection.execute(
            """
            INSERT INTO scenario_runs (
                scenario_run_id, mode, configuration_id, configuration_version,
                fault_section_id, fault_type, initial_scenario_time_ms,
                scenario_time_ms, state_revision, workflow_stage,
                network_state_label, evidence_class, application_build_id,
                status, fault_active, source_availability_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._run_values(run),
        )

    def update_run(self, run: RunContext) -> None:
        values = self._run_values(run)
        self.connection.execute(
            """
            UPDATE scenario_runs SET
                mode = ?, configuration_id = ?, configuration_version = ?,
                fault_section_id = ?, fault_type = ?, initial_scenario_time_ms = ?,
                scenario_time_ms = ?, state_revision = ?, workflow_stage = ?,
                network_state_label = ?, evidence_class = ?, application_build_id = ?,
                status = ?, fault_active = ?, source_availability_json = ?
            WHERE scenario_run_id = ?
            """,
            (*values[1:], values[0]),
        )
        if self.connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise ScenarioRecordNotFound(f"run not found: {run.scenario_run_id}")

    @staticmethod
    def _run_values(run: RunContext) -> tuple[object, ...]:
        return (
            str(run.scenario_run_id),
            run.mode.value,
            run.configuration_id,
            run.configuration_version,
            run.fault_section_id,
            run.fault_type.value,
            instant_to_epoch_ms(run.initial_scenario_time),
            instant_to_epoch_ms(run.scenario_time),
            run.state_revision,
            run.workflow_stage.value,
            run.network_state_label.value,
            run.evidence_class.value,
            run.application_build_id,
            run.status.value,
            int(run.fault_active),
            json.dumps(
                {
                    key: value.value
                    for key, value in sorted(run.source_availability.items())
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        )

    def get_run(self, scenario_run_id: UUID) -> RunContext:
        row = self.connection.execute(
            "SELECT * FROM scenario_runs WHERE scenario_run_id = ?",
            (str(scenario_run_id),),
        ).fetchone()
        if row is None:
            raise ScenarioRecordNotFound(f"run not found: {scenario_run_id}")
        return RunContext(
            scenario_run_id=UUID(row["scenario_run_id"]),
            mode=ScenarioMode(row["mode"]),
            configuration_id=row["configuration_id"],
            configuration_version=row["configuration_version"],
            fault_section_id=row["fault_section_id"],
            fault_type=FaultType(row["fault_type"]),
            initial_scenario_time=epoch_ms_to_instant(row["initial_scenario_time_ms"]),
            scenario_time=epoch_ms_to_instant(row["scenario_time_ms"]),
            state_revision=row["state_revision"],
            workflow_stage=WorkflowStage(row["workflow_stage"]),
            network_state_label=NetworkStateLabel(row["network_state_label"]),
            evidence_class=EvidenceClass(row["evidence_class"]),
            application_build_id=row["application_build_id"],
            status=ScenarioRunStatus(row["status"]),
            fault_active=bool(row["fault_active"]),
            source_availability={
                key: SourceAvailability(value)
                for key, value in json.loads(row["source_availability_json"]).items()
            },
        )

    def put_telemetry(self, scenario_run_id: UUID, point: TelemetryPoint) -> None:
        self.connection.execute(
            """
            INSERT INTO scenario_telemetry_points (
                scenario_run_id, point_id, entity_id, value, quality,
                last_update_scenario_time_ms, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (scenario_run_id, point_id) DO UPDATE SET
                entity_id = excluded.entity_id,
                value = excluded.value,
                quality = excluded.quality,
                last_update_scenario_time_ms = excluded.last_update_scenario_time_ms,
                revision = excluded.revision
            """,
            (
                str(scenario_run_id),
                point.point_id,
                point.entity_id,
                point.value.value,
                point.quality.value,
                instant_to_epoch_ms(point.last_update_scenario_time),
                point.revision,
            ),
        )

    def list_telemetry(self, scenario_run_id: UUID) -> tuple[TelemetryPoint, ...]:
        rows = self.connection.execute(
            "SELECT * FROM scenario_telemetry_points WHERE scenario_run_id = ? "
            "ORDER BY point_id",
            (str(scenario_run_id),),
        ).fetchall()
        return tuple(
            TelemetryPoint(
                point_id=row["point_id"],
                entity_id=row["entity_id"],
                value=SwitchState(row["value"]),
                quality=TelemetryQuality(row["quality"]),
                last_update_scenario_time=epoch_ms_to_instant(
                    row["last_update_scenario_time_ms"]
                ),
                revision=row["revision"],
            )
            for row in rows
        )

    def insert_alarm(self, alarm: AlarmRecord) -> None:
        self.connection.execute(
            """
            INSERT INTO scenario_alarms (
                alarm_id, scenario_run_id, entity_id, alarm_type, active,
                acknowledgement_state, generated_scenario_time_ms,
                acknowledged_scenario_time_ms, acknowledged_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._alarm_values(alarm),
        )

    def update_alarm(self, alarm: AlarmRecord) -> None:
        values = self._alarm_values(alarm)
        self.connection.execute(
            """
            UPDATE scenario_alarms SET
                scenario_run_id = ?, entity_id = ?, alarm_type = ?, active = ?,
                acknowledgement_state = ?, generated_scenario_time_ms = ?,
                acknowledged_scenario_time_ms = ?, acknowledged_by = ?
            WHERE alarm_id = ?
            """,
            (*values[1:], values[0]),
        )
        if self.connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise ScenarioRecordNotFound(f"alarm not found: {alarm.alarm_id}")

    @staticmethod
    def _alarm_values(alarm: AlarmRecord) -> tuple[object, ...]:
        return (
            str(alarm.alarm_id),
            str(alarm.scenario_run_id),
            alarm.entity_id,
            alarm.alarm_type.value,
            int(alarm.active),
            alarm.acknowledgement_state.value,
            instant_to_epoch_ms(alarm.generated_scenario_time),
            (
                instant_to_epoch_ms(alarm.acknowledged_scenario_time)
                if alarm.acknowledged_scenario_time is not None
                else None
            ),
            alarm.acknowledged_by,
        )

    def list_alarms(self, scenario_run_id: UUID) -> tuple[AlarmRecord, ...]:
        rows = self.connection.execute(
            "SELECT * FROM scenario_alarms WHERE scenario_run_id = ? ORDER BY alarm_id",
            (str(scenario_run_id),),
        ).fetchall()
        return tuple(
            AlarmRecord(
                alarm_id=UUID(row["alarm_id"]),
                scenario_run_id=UUID(row["scenario_run_id"]),
                entity_id=row["entity_id"],
                alarm_type=AlarmType(row["alarm_type"]),
                active=bool(row["active"]),
                acknowledgement_state=AlarmAcknowledgementState(
                    row["acknowledgement_state"]
                ),
                generated_scenario_time=epoch_ms_to_instant(
                    row["generated_scenario_time_ms"]
                ),
                acknowledged_scenario_time=(
                    epoch_ms_to_instant(row["acknowledged_scenario_time_ms"])
                    if row["acknowledged_scenario_time_ms"] is not None
                    else None
                ),
                acknowledged_by=row["acknowledged_by"],
            )
            for row in rows
        )

    def next_event_sequence(self, scenario_run_id: UUID) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(event_sequence), 0) + 1 AS next_sequence "
            "FROM operational_events WHERE scenario_run_id = ?",
            (str(scenario_run_id),),
        ).fetchone()
        return row["next_sequence"]

    def insert_events(self, events: tuple[OperationalEvent, ...]) -> None:
        self.connection.executemany(
            """
            INSERT INTO operational_events (
                event_id, scenario_run_id, event_sequence, scenario_time_ms,
                state_revision, source, event_type, affected_entity_id,
                description, actor, previous_value, new_value, command_id, alarm_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(event.event_id),
                    str(event.scenario_run_id),
                    event.event_sequence,
                    instant_to_epoch_ms(event.scenario_time),
                    event.state_revision,
                    event.source.value,
                    event.event_type.value,
                    event.affected_entity_id,
                    event.description,
                    event.actor,
                    event.previous_value,
                    event.new_value,
                    str(event.command_id) if event.command_id is not None else None,
                    str(event.alarm_id) if event.alarm_id is not None else None,
                )
                for event in events
            ],
        )

    def list_events(self, scenario_run_id: UUID) -> tuple[OperationalEvent, ...]:
        rows = self.connection.execute(
            "SELECT * FROM operational_events WHERE scenario_run_id = ? "
            "ORDER BY event_sequence",
            (str(scenario_run_id),),
        ).fetchall()
        return tuple(
            OperationalEvent(
                event_id=UUID(row["event_id"]),
                scenario_run_id=UUID(row["scenario_run_id"]),
                event_sequence=row["event_sequence"],
                scenario_time=epoch_ms_to_instant(row["scenario_time_ms"]),
                state_revision=row["state_revision"],
                source=OperationalEventSource(row["source"]),
                event_type=OperationalEventType(row["event_type"]),
                affected_entity_id=row["affected_entity_id"],
                description=row["description"],
                actor=row["actor"],
                previous_value=row["previous_value"],
                new_value=row["new_value"],
                command_id=(UUID(row["command_id"]) if row["command_id"] else None),
                alarm_id=(UUID(row["alarm_id"]) if row["alarm_id"] else None),
            )
            for row in rows
        )

    def insert_derived_snapshots(
        self,
        scenario_run_id: UUID,
        state_revision: int,
        topology: TopologyResult,
        outage: OutageResult,
    ) -> None:
        self.connection.execute(
            "INSERT INTO topology_snapshots VALUES (?, ?, ?)",
            (str(scenario_run_id), state_revision, topology.model_dump_json()),
        )
        self.connection.execute(
            "INSERT INTO outage_snapshots VALUES (?, ?, ?)",
            (str(scenario_run_id), state_revision, outage.model_dump_json()),
        )

    def get_topology_snapshot(
        self, scenario_run_id: UUID, state_revision: int
    ) -> TopologyResult:
        row = self.connection.execute(
            "SELECT payload_json FROM topology_snapshots "
            "WHERE scenario_run_id = ? AND state_revision = ?",
            (str(scenario_run_id), state_revision),
        ).fetchone()
        if row is None:
            raise ScenarioRecordNotFound("topology snapshot not found")
        return TopologyResult.model_validate_json(row["payload_json"], strict=True)

    def get_outage_snapshot(
        self, scenario_run_id: UUID, state_revision: int
    ) -> OutageResult:
        row = self.connection.execute(
            "SELECT payload_json FROM outage_snapshots "
            "WHERE scenario_run_id = ? AND state_revision = ?",
            (str(scenario_run_id), state_revision),
        ).fetchone()
        if row is None:
            raise ScenarioRecordNotFound("outage snapshot not found")
        return OutageResult.model_validate_json(row["payload_json"], strict=True)
