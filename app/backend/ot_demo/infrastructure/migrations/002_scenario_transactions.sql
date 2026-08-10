PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS scenario_runs (
    scenario_run_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    configuration_id TEXT NOT NULL,
    configuration_version TEXT NOT NULL,
    fault_section_id TEXT NOT NULL,
    fault_type TEXT NOT NULL,
    initial_scenario_time_ms INTEGER NOT NULL,
    scenario_time_ms INTEGER NOT NULL,
    state_revision INTEGER NOT NULL CHECK (state_revision >= 0),
    workflow_stage TEXT NOT NULL,
    network_state_label TEXT NOT NULL,
    evidence_class TEXT NOT NULL,
    application_build_id TEXT NOT NULL CHECK (length(application_build_id) = 64),
    status TEXT NOT NULL,
    fault_active INTEGER NOT NULL CHECK (fault_active IN (0, 1)),
    source_availability_json TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS one_mutable_scenario_run
ON scenario_runs ((1))
WHERE status != 'CLOSED';

CREATE TABLE IF NOT EXISTS scenario_telemetry_points (
    scenario_run_id TEXT NOT NULL REFERENCES scenario_runs(scenario_run_id),
    point_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    value TEXT NOT NULL,
    quality TEXT NOT NULL,
    last_update_scenario_time_ms INTEGER NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 0),
    PRIMARY KEY (scenario_run_id, point_id)
);

CREATE TABLE IF NOT EXISTS scenario_alarms (
    alarm_id TEXT PRIMARY KEY,
    scenario_run_id TEXT NOT NULL REFERENCES scenario_runs(scenario_run_id),
    entity_id TEXT NOT NULL,
    alarm_type TEXT NOT NULL,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    acknowledgement_state TEXT NOT NULL,
    generated_scenario_time_ms INTEGER NOT NULL,
    acknowledged_scenario_time_ms INTEGER,
    acknowledged_by TEXT
);

CREATE TABLE IF NOT EXISTS topology_snapshots (
    scenario_run_id TEXT NOT NULL REFERENCES scenario_runs(scenario_run_id),
    state_revision INTEGER NOT NULL CHECK (state_revision >= 0),
    payload_json TEXT NOT NULL,
    PRIMARY KEY (scenario_run_id, state_revision)
);

CREATE TABLE IF NOT EXISTS outage_snapshots (
    scenario_run_id TEXT NOT NULL REFERENCES scenario_runs(scenario_run_id),
    state_revision INTEGER NOT NULL CHECK (state_revision >= 0),
    payload_json TEXT NOT NULL,
    PRIMARY KEY (scenario_run_id, state_revision)
);

CREATE TABLE IF NOT EXISTS operational_events (
    event_id TEXT PRIMARY KEY,
    scenario_run_id TEXT NOT NULL REFERENCES scenario_runs(scenario_run_id),
    event_sequence INTEGER NOT NULL CHECK (event_sequence >= 1),
    scenario_time_ms INTEGER NOT NULL,
    state_revision INTEGER NOT NULL CHECK (state_revision >= 0),
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    affected_entity_id TEXT,
    description TEXT NOT NULL,
    actor TEXT,
    previous_value TEXT,
    new_value TEXT,
    command_id TEXT,
    alarm_id TEXT,
    UNIQUE (scenario_run_id, event_sequence)
);

CREATE TABLE IF NOT EXISTS scenario_command_results (
    command_id TEXT PRIMARY KEY,
    scenario_run_id TEXT NOT NULL REFERENCES scenario_runs(scenario_run_id),
    request_sha256 TEXT NOT NULL CHECK (length(request_sha256) = 64),
    result_json TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS operational_events_no_update
BEFORE UPDATE ON operational_events
BEGIN
    SELECT RAISE(ABORT, 'operational events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS operational_events_no_delete
BEFORE DELETE ON operational_events
BEGIN
    SELECT RAISE(ABORT, 'operational events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS scenario_command_results_no_update
BEFORE UPDATE ON scenario_command_results
BEGIN
    SELECT RAISE(ABORT, 'command results are immutable');
END;

CREATE TRIGGER IF NOT EXISTS scenario_command_results_no_delete
BEFORE DELETE ON scenario_command_results
BEGIN
    SELECT RAISE(ABORT, 'command results are immutable');
END;
