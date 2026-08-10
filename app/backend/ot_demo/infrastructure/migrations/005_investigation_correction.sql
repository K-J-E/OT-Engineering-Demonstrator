PRAGMA foreign_keys = ON;

CREATE TABLE investigation_defect_records (
    defect_record_id TEXT PRIMARY KEY,
    defect_id TEXT NOT NULL UNIQUE,
    original_failed_execution_id TEXT NOT NULL
        REFERENCES validation_executions(validation_execution_id),
    recorded_scenario_time_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE investigation_correction_records (
    correction_record_id TEXT PRIMARY KEY,
    correction_id TEXT NOT NULL UNIQUE,
    defect_record_id TEXT NOT NULL UNIQUE
        REFERENCES investigation_defect_records(defect_record_id),
    recorded_scenario_time_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE investigation_repeat_links (
    repeat_link_id TEXT PRIMARY KEY,
    relationship_type TEXT NOT NULL
        CHECK (relationship_type IN ('DIRECT_REPEAT', 'REGRESSION')),
    original_execution_id TEXT NOT NULL
        REFERENCES validation_executions(validation_execution_id),
    new_execution_id TEXT NOT NULL UNIQUE
        REFERENCES validation_executions(validation_execution_id),
    defect_record_id TEXT NOT NULL
        REFERENCES investigation_defect_records(defect_record_id),
    correction_record_id TEXT NOT NULL
        REFERENCES investigation_correction_records(correction_record_id),
    payload_json TEXT NOT NULL,
    UNIQUE (defect_record_id, relationship_type)
);

CREATE TRIGGER investigation_defects_no_update
BEFORE UPDATE ON investigation_defect_records
BEGIN
    SELECT RAISE(ABORT, 'defect records are immutable');
END;

CREATE TRIGGER investigation_defects_no_delete
BEFORE DELETE ON investigation_defect_records
BEGIN
    SELECT RAISE(ABORT, 'defect records are immutable');
END;

CREATE TRIGGER investigation_corrections_no_update
BEFORE UPDATE ON investigation_correction_records
BEGIN
    SELECT RAISE(ABORT, 'correction records are immutable');
END;

CREATE TRIGGER investigation_corrections_no_delete
BEFORE DELETE ON investigation_correction_records
BEGIN
    SELECT RAISE(ABORT, 'correction records are immutable');
END;

CREATE TRIGGER investigation_repeat_links_no_update
BEFORE UPDATE ON investigation_repeat_links
BEGIN
    SELECT RAISE(ABORT, 'repeat links are immutable');
END;

CREATE TRIGGER investigation_repeat_links_no_delete
BEFORE DELETE ON investigation_repeat_links
BEGIN
    SELECT RAISE(ABORT, 'repeat links are immutable');
END;
