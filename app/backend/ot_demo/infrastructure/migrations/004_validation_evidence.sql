PRAGMA foreign_keys = ON;

CREATE TABLE validation_executions (
    validation_execution_id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL,
    test_definition_version TEXT NOT NULL,
    test_definition_sha256 TEXT NOT NULL CHECK (length(test_definition_sha256) = 64),
    catalogue_sha256 TEXT NOT NULL CHECK (length(catalogue_sha256) = 64),
    scenario_run_id TEXT NOT NULL,
    scenario_mode TEXT NOT NULL,
    evidence_class TEXT NOT NULL,
    configuration_id TEXT NOT NULL,
    configuration_version TEXT NOT NULL,
    application_build_id TEXT NOT NULL CHECK (length(application_build_id) = 64),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'FINALISED')),
    started_scenario_time_ms INTEGER NOT NULL,
    finalised_scenario_time_ms INTEGER,
    verdict TEXT,
    payload_json TEXT NOT NULL
);

CREATE INDEX validation_executions_by_test
ON validation_executions (test_id, started_scenario_time_ms, validation_execution_id);

CREATE INDEX validation_executions_by_run
ON validation_executions (scenario_run_id, started_scenario_time_ms, validation_execution_id);

CREATE TABLE validation_evidence_snapshots (
    evidence_snapshot_id TEXT PRIMARY KEY,
    validation_execution_id TEXT NOT NULL
        REFERENCES validation_executions(validation_execution_id),
    checkpoint_id TEXT NOT NULL,
    scenario_run_id TEXT NOT NULL,
    scenario_time_ms INTEGER NOT NULL,
    state_revision INTEGER NOT NULL CHECK (state_revision >= 0),
    canonical_payload_sha256 TEXT NOT NULL CHECK (length(canonical_payload_sha256) = 64),
    payload_json TEXT NOT NULL,
    UNIQUE (validation_execution_id, checkpoint_id)
);

CREATE TRIGGER validation_executions_no_delete
BEFORE DELETE ON validation_executions
BEGIN
    SELECT RAISE(ABORT, 'validation executions are immutable history');
END;

CREATE TRIGGER validation_finalised_executions_no_update
BEFORE UPDATE ON validation_executions
WHEN OLD.status = 'FINALISED'
BEGIN
    SELECT RAISE(ABORT, 'finalised validation executions are immutable');
END;

CREATE TRIGGER validation_execution_identity_no_update
BEFORE UPDATE ON validation_executions
WHEN NEW.validation_execution_id != OLD.validation_execution_id
  OR NEW.test_id != OLD.test_id
  OR NEW.test_definition_version != OLD.test_definition_version
  OR NEW.test_definition_sha256 != OLD.test_definition_sha256
  OR NEW.catalogue_sha256 != OLD.catalogue_sha256
  OR NEW.scenario_run_id != OLD.scenario_run_id
  OR NEW.scenario_mode != OLD.scenario_mode
  OR NEW.evidence_class != OLD.evidence_class
  OR NEW.configuration_id != OLD.configuration_id
  OR NEW.configuration_version != OLD.configuration_version
  OR NEW.application_build_id != OLD.application_build_id
  OR NEW.started_scenario_time_ms != OLD.started_scenario_time_ms
BEGIN
    SELECT RAISE(ABORT, 'validation execution provenance is immutable');
END;

CREATE TRIGGER validation_evidence_no_update
BEFORE UPDATE ON validation_evidence_snapshots
BEGIN
    SELECT RAISE(ABORT, 'validation evidence snapshots are immutable');
END;

CREATE TRIGGER validation_evidence_parent_must_be_active
BEFORE INSERT ON validation_evidence_snapshots
WHEN (
    SELECT status
    FROM validation_executions
    WHERE validation_execution_id = NEW.validation_execution_id
) = 'FINALISED'
BEGIN
    SELECT RAISE(
        ABORT,
        'finalised validation execution cannot acquire additional evidence'
    );
END;

CREATE TRIGGER validation_evidence_no_delete
BEFORE DELETE ON validation_evidence_snapshots
BEGIN
    SELECT RAISE(ABORT, 'validation evidence snapshots are immutable');
END;
