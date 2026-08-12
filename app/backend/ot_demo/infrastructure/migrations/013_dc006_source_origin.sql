PRAGMA foreign_keys = ON;

-- A validation attempt has exactly one backend-produced authority source for
-- each controlled context role. Context binding resolves these memberships;
-- callers cannot choose among competing same-role snapshots.
CREATE TABLE determination_source_origin_bindings (
    validation_attempt_id TEXT NOT NULL REFERENCES validation_attempts(validation_attempt_id),
    source_role TEXT NOT NULL,
    source_record_id TEXT NOT NULL UNIQUE
        REFERENCES determination_source_records(source_record_id),
    producer_kind TEXT NOT NULL CHECK (producer_kind IN (
        'CONFIGURATION_PACKAGE','SCENARIO_STATE','CONTROLLED_FIXTURE',
        'OPERATIONAL_EVENT_HISTORY','VALIDATION_INVESTIGATION_HISTORY',
        'DETERMINISTIC_REPEAT','EVIDENCE_PACKAGE','NFR_REVIEW'
    )),
    origin_identity TEXT NOT NULL,
    origin_identity_sha256 TEXT NOT NULL CHECK (length(origin_identity_sha256) = 64),
    created_at_ms INTEGER NOT NULL,
    PRIMARY KEY (validation_attempt_id, source_role)
);

CREATE TRIGGER determination_source_origin_no_update
BEFORE UPDATE ON determination_source_origin_bindings
BEGIN
    SELECT RAISE(ABORT, 'determination source origin bindings are immutable');
END;

CREATE TRIGGER determination_source_origin_no_delete
BEFORE DELETE ON determination_source_origin_bindings
BEGIN
    SELECT RAISE(ABORT, 'determination source origin bindings are immutable');
END;
