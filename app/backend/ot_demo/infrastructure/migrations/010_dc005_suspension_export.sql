PRAGMA foreign_keys = ON;

CREATE TABLE suspension_evidence_packages (
    package_id TEXT PRIMARY KEY,
    suspension_record_id TEXT NOT NULL
        REFERENCES validation_suspension_records(suspension_record_id),
    evidence_class TEXT NOT NULL CHECK (evidence_class IN ('FORMAL','EXPLORATORY')),
    verifier_application_build_id TEXT NOT NULL CHECK (length(verifier_application_build_id) = 64),
    generation_application_build_id TEXT NOT NULL CHECK (length(generation_application_build_id) = 64),
    manifest_sha256 TEXT NOT NULL CHECK (length(manifest_sha256) = 64),
    archive_sha256 TEXT NOT NULL CHECK (length(archive_sha256) = 64),
    archive_path TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL
);

CREATE INDEX suspension_evidence_packages_by_record
ON suspension_evidence_packages (suspension_record_id, package_id);

CREATE TRIGGER suspension_evidence_packages_no_update
BEFORE UPDATE ON suspension_evidence_packages
BEGIN SELECT RAISE(ABORT, 'suspension evidence package records are immutable'); END;

CREATE TRIGGER suspension_evidence_packages_no_delete
BEFORE DELETE ON suspension_evidence_packages
BEGIN SELECT RAISE(ABORT, 'suspension evidence package records are immutable'); END;

CREATE TRIGGER suspended_attempt_execution_no_update
BEFORE UPDATE ON validation_executions
WHEN EXISTS (
    SELECT 1 FROM validation_attempts
    WHERE validation_attempt_id = OLD.validation_attempt_id
      AND status = 'SUSPENDED'
)
BEGIN SELECT RAISE(ABORT, 'suspended validation execution is immutable'); END;

CREATE TRIGGER suspended_attempt_evidence_no_insert
BEFORE INSERT ON validation_evidence_snapshots
WHEN EXISTS (
    SELECT 1
    FROM validation_executions execution
    JOIN validation_attempts attempt
      ON attempt.validation_attempt_id = execution.validation_attempt_id
    WHERE execution.validation_execution_id = NEW.validation_execution_id
      AND attempt.status = 'SUSPENDED'
)
BEGIN SELECT RAISE(ABORT, 'suspended validation attempt cannot acquire evidence'); END;
