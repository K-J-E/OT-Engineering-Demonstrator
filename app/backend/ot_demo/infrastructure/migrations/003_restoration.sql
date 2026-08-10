PRAGMA foreign_keys = ON;

ALTER TABLE operational_events ADD COLUMN assessment_id TEXT;

CREATE TABLE restoration_assessments (
    assessment_id TEXT PRIMARY KEY,
    scenario_run_id TEXT NOT NULL REFERENCES scenario_runs(scenario_run_id),
    assessment_sequence INTEGER NOT NULL CHECK (assessment_sequence >= 1),
    state_revision INTEGER NOT NULL CHECK (state_revision >= 0),
    scenario_time_ms INTEGER NOT NULL,
    configuration_id TEXT NOT NULL,
    candidate_id TEXT,
    outcome TEXT NOT NULL,
    telemetry_snapshot_sha256 TEXT NOT NULL CHECK (length(telemetry_snapshot_sha256) = 64),
    source_availability_sha256 TEXT NOT NULL CHECK (length(source_availability_sha256) = 64),
    payload_json TEXT NOT NULL,
    UNIQUE (scenario_run_id, assessment_sequence)
);

CREATE TABLE restoration_assessment_invalidations (
    invalidation_id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL REFERENCES restoration_assessments(assessment_id),
    scenario_run_id TEXT NOT NULL REFERENCES scenario_runs(scenario_run_id),
    superseding_state_revision INTEGER NOT NULL CHECK (superseding_state_revision >= 0),
    superseding_scenario_time_ms INTEGER NOT NULL,
    reason_code TEXT NOT NULL,
    event_id TEXT NOT NULL REFERENCES operational_events(event_id),
    UNIQUE (assessment_id)
);

CREATE TRIGGER restoration_assessments_no_update
BEFORE UPDATE ON restoration_assessments
BEGIN
    SELECT RAISE(ABORT, 'restoration assessments are immutable');
END;

CREATE TRIGGER restoration_assessments_no_delete
BEFORE DELETE ON restoration_assessments
BEGIN
    SELECT RAISE(ABORT, 'restoration assessments are immutable');
END;

CREATE TRIGGER restoration_invalidations_no_update
BEFORE UPDATE ON restoration_assessment_invalidations
BEGIN
    SELECT RAISE(ABORT, 'restoration invalidations are immutable');
END;

CREATE TRIGGER restoration_invalidations_no_delete
BEFORE DELETE ON restoration_assessment_invalidations
BEGIN
    SELECT RAISE(ABORT, 'restoration invalidations are immutable');
END;
