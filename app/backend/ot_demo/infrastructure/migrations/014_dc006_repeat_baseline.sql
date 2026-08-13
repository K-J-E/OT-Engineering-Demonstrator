PRAGMA foreign_keys = ON;

-- Internal assurance persistence only: this freezes the original source-record
-- fingerprint immediately before a linked repeat execution is created.  It is
-- not a new engineering record or validation result.
CREATE TABLE dc006_repeat_source_baselines (
    repeat_execution_id TEXT PRIMARY KEY,
    source_execution_id TEXT NOT NULL UNIQUE,
    baseline_sha256 TEXT NOT NULL CHECK (length(baseline_sha256) = 64),
    captured_at_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TRIGGER dc006_repeat_baseline_no_update
BEFORE UPDATE ON dc006_repeat_source_baselines
BEGIN SELECT RAISE(ABORT, 'repeat source baselines are immutable'); END;

CREATE TRIGGER dc006_repeat_baseline_no_delete
BEFORE DELETE ON dc006_repeat_source_baselines
BEGIN SELECT RAISE(ABORT, 'repeat source baselines are immutable'); END;
