PRAGMA foreign_keys = ON;

ALTER TABLE validation_executions ADD COLUMN validation_attempt_id TEXT;
ALTER TABLE validation_executions ADD COLUMN target_selection_id TEXT;
ALTER TABLE validation_executions ADD COLUMN executed_result_id TEXT;

CREATE TABLE validation_target_selections (
    target_selection_id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL,
    case_id TEXT,
    catalogue_sha256 TEXT NOT NULL CHECK (length(catalogue_sha256) = 64),
    test_definition_sha256 TEXT NOT NULL CHECK (length(test_definition_sha256) = 64),
    created_at_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE validation_attempts (
    validation_attempt_id TEXT PRIMARY KEY,
    target_selection_id TEXT NOT NULL REFERENCES validation_target_selections(target_selection_id),
    status TEXT NOT NULL CHECK (status IN ('NOT_STARTED','ACTIVE','INCOMPLETE','SUSPENDED','EXECUTED')),
    scenario_run_id TEXT,
    validation_execution_id TEXT,
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE executed_validation_results (
    executed_result_id TEXT PRIMARY KEY,
    validation_attempt_id TEXT NOT NULL UNIQUE REFERENCES validation_attempts(validation_attempt_id),
    validation_execution_id TEXT NOT NULL UNIQUE REFERENCES validation_executions(validation_execution_id),
    verdict TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL')),
    result_sha256 TEXT NOT NULL CHECK (length(result_sha256) = 64),
    finalised_at_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE validation_suspension_records (
    suspension_record_id TEXT PRIMARY KEY,
    validation_attempt_id TEXT NOT NULL UNIQUE REFERENCES validation_attempts(validation_attempt_id),
    target_selection_id TEXT NOT NULL REFERENCES validation_target_selections(target_selection_id),
    condition_id TEXT NOT NULL CHECK (condition_id IN ('VSC-001','VSC-002','VSC-003','VSC-004','VSC-005')),
    lifecycle_position TEXT NOT NULL CHECK (lifecycle_position IN ('PRE_EXECUTION_ENTRY','EXECUTION_IN_PROGRESS','EVIDENCE_FINALISATION')),
    status TEXT NOT NULL CHECK (status IN ('DRAFT','FINALISED')),
    reason_code TEXT NOT NULL,
    deterministic_fingerprint TEXT NOT NULL CHECK (length(deterministic_fingerprint) = 64),
    scenario_run_id TEXT,
    validation_execution_id TEXT,
    finalised_at_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE validation_suspension_evidence (
    evidence_id TEXT PRIMARY KEY,
    suspension_record_id TEXT NOT NULL REFERENCES validation_suspension_records(suspension_record_id),
    condition_id TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    failure_code TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
    payload_json TEXT NOT NULL
);

CREATE TABLE composite_validation_constituent_sources (
    composite_result_id TEXT NOT NULL REFERENCES composite_validation_results(composite_result_id),
    case_id TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('EXECUTION_RESULT','SUSPENSION_RESULT')),
    validation_execution_id TEXT REFERENCES validation_executions(validation_execution_id),
    suspension_record_id TEXT REFERENCES validation_suspension_records(suspension_record_id),
    constituent_verdict TEXT CHECK (constituent_verdict IN ('PASS','FAIL','BLOCKED-TEST')),
    payload_json TEXT NOT NULL,
    PRIMARY KEY (composite_result_id, case_id),
    CHECK (
      (source_kind = 'EXECUTION_RESULT' AND validation_execution_id IS NOT NULL AND suspension_record_id IS NULL AND (constituent_verdict IS NULL OR constituent_verdict IN ('PASS','FAIL')))
      OR
      (source_kind = 'SUSPENSION_RESULT' AND validation_execution_id IS NULL AND suspension_record_id IS NOT NULL AND constituent_verdict = 'BLOCKED-TEST')
    )
);

CREATE TRIGGER validation_targets_no_update BEFORE UPDATE ON validation_target_selections
BEGIN SELECT RAISE(ABORT, 'validation target selections are immutable'); END;
CREATE TRIGGER validation_targets_no_delete BEFORE DELETE ON validation_target_selections
BEGIN SELECT RAISE(ABORT, 'validation target selections are immutable'); END;
CREATE TRIGGER executed_results_no_update BEFORE UPDATE ON executed_validation_results
BEGIN SELECT RAISE(ABORT, 'executed validation results are immutable'); END;
CREATE TRIGGER executed_results_no_delete BEFORE DELETE ON executed_validation_results
BEGIN SELECT RAISE(ABORT, 'executed validation results are immutable'); END;
CREATE TRIGGER suspension_records_no_update BEFORE UPDATE ON validation_suspension_records
WHEN OLD.status = 'FINALISED'
BEGIN SELECT RAISE(ABORT, 'finalised validation suspension records are immutable'); END;
CREATE TRIGGER suspension_records_no_delete BEFORE DELETE ON validation_suspension_records
BEGIN SELECT RAISE(ABORT, 'finalised validation suspension records are immutable'); END;
CREATE TRIGGER suspension_evidence_no_update BEFORE UPDATE ON validation_suspension_evidence
BEGIN SELECT RAISE(ABORT, 'validation suspension evidence is immutable'); END;
CREATE TRIGGER suspension_evidence_no_delete BEFORE DELETE ON validation_suspension_evidence
BEGIN SELECT RAISE(ABORT, 'validation suspension evidence is immutable'); END;
CREATE TRIGGER suspension_evidence_no_late_insert BEFORE INSERT ON validation_suspension_evidence
WHEN (SELECT status FROM validation_suspension_records WHERE suspension_record_id = NEW.suspension_record_id) = 'FINALISED'
BEGIN SELECT RAISE(ABORT, 'finalised suspension cannot acquire evidence'); END;
CREATE TRIGGER composite_sources_no_update BEFORE UPDATE ON composite_validation_constituent_sources
BEGIN SELECT RAISE(ABORT, 'composite constituent source is immutable'); END;
CREATE TRIGGER composite_sources_no_delete BEFORE DELETE ON composite_validation_constituent_sources
BEGIN SELECT RAISE(ABORT, 'composite constituent source is immutable'); END;
CREATE TRIGGER composite_sources_no_late_insert BEFORE INSERT ON composite_validation_constituent_sources
WHEN (SELECT status FROM composite_validation_results WHERE composite_result_id = NEW.composite_result_id) = 'FINALISED'
BEGIN SELECT RAISE(ABORT, 'finalised composite cannot acquire constituent sources'); END;

CREATE TRIGGER validation_execution_dc005_identity_no_update
BEFORE UPDATE ON validation_executions
WHEN NEW.validation_attempt_id IS NOT OLD.validation_attempt_id
  OR NEW.target_selection_id IS NOT OLD.target_selection_id
BEGIN SELECT RAISE(ABORT, 'DC-005 attempt/target execution binding is immutable'); END;
