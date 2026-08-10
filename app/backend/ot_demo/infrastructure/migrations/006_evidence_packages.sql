PRAGMA foreign_keys = ON;

CREATE TABLE evidence_packages (
    package_id TEXT PRIMARY KEY,
    validation_execution_id TEXT NOT NULL
        REFERENCES validation_executions(validation_execution_id),
    scenario_run_id TEXT NOT NULL,
    evidence_class TEXT NOT NULL CHECK (evidence_class IN ('FORMAL', 'EXPLORATORY')),
    application_build_id TEXT NOT NULL CHECK (length(application_build_id) = 64),
    manifest_sha256 TEXT NOT NULL CHECK (length(manifest_sha256) = 64),
    archive_sha256 TEXT NOT NULL CHECK (length(archive_sha256) = 64),
    archive_path TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL
);

CREATE INDEX evidence_packages_by_execution
ON evidence_packages (validation_execution_id, package_id);

CREATE TRIGGER evidence_packages_no_update
BEFORE UPDATE ON evidence_packages
BEGIN
    SELECT RAISE(ABORT, 'evidence package records are immutable');
END;

CREATE TRIGGER evidence_packages_no_delete
BEFORE DELETE ON evidence_packages
BEGIN
    SELECT RAISE(ABORT, 'evidence package records are immutable');
END;
