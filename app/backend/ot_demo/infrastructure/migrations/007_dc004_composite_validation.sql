PRAGMA foreign_keys = ON;

ALTER TABLE validation_executions
ADD COLUMN catalogue_version TEXT NOT NULL DEFAULT '1.0';

ALTER TABLE validation_executions
ADD COLUMN case_id TEXT;

ALTER TABLE validation_executions
ADD COLUMN case_definition_version TEXT;

ALTER TABLE validation_executions
ADD COLUMN case_definition_sha256 TEXT;

CREATE INDEX validation_executions_by_case
ON validation_executions (test_id, case_id, started_scenario_time_ms, validation_execution_id);

CREATE TRIGGER validation_execution_dc004_identity_no_update
BEFORE UPDATE ON validation_executions
WHEN NEW.catalogue_version != OLD.catalogue_version
  OR NEW.case_id IS NOT OLD.case_id
  OR NEW.case_definition_version IS NOT OLD.case_definition_version
  OR NEW.case_definition_sha256 IS NOT OLD.case_definition_sha256
BEGIN
    SELECT RAISE(ABORT, 'DC-004 validation execution identity is immutable');
END;

CREATE TABLE composite_validation_results (
    composite_result_id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL,
    test_definition_version TEXT NOT NULL,
    test_definition_sha256 TEXT NOT NULL CHECK (length(test_definition_sha256) = 64),
    catalogue_version TEXT NOT NULL,
    catalogue_sha256 TEXT NOT NULL CHECK (length(catalogue_sha256) = 64),
    evidence_class TEXT NOT NULL CHECK (evidence_class = 'EXPLORATORY'),
    application_build_id TEXT NOT NULL CHECK (length(application_build_id) = 64),
    configuration_id TEXT NOT NULL,
    configuration_version TEXT NOT NULL,
    completeness_status TEXT NOT NULL CHECK (completeness_status IN ('INCOMPLETE', 'COMPLETE')),
    status TEXT NOT NULL CHECK (status IN ('DRAFT', 'FINALISED')),
    determination TEXT,
    created_at_ms INTEGER NOT NULL,
    finalised_at_ms INTEGER,
    payload_json TEXT NOT NULL
);

CREATE INDEX composite_validation_results_by_test
ON composite_validation_results (test_id, created_at_ms, composite_result_id);

CREATE TABLE composite_validation_constituents (
    composite_result_id TEXT NOT NULL
        REFERENCES composite_validation_results(composite_result_id),
    case_id TEXT NOT NULL,
    validation_execution_id TEXT NOT NULL
        REFERENCES validation_executions(validation_execution_id),
    scenario_run_id TEXT NOT NULL,
    case_definition_sha256 TEXT NOT NULL CHECK (length(case_definition_sha256) = 64),
    constituent_verdict TEXT,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (composite_result_id, case_id),
    UNIQUE (composite_result_id, validation_execution_id)
);

CREATE TRIGGER composite_results_no_delete
BEFORE DELETE ON composite_validation_results
BEGIN
    SELECT RAISE(ABORT, 'composite validation results are immutable history');
END;

CREATE TRIGGER composite_finalised_no_update
BEFORE UPDATE ON composite_validation_results
WHEN OLD.status = 'FINALISED'
BEGIN
    SELECT RAISE(ABORT, 'finalised composite validation result is immutable');
END;

CREATE TRIGGER composite_identity_no_update
BEFORE UPDATE ON composite_validation_results
WHEN NEW.composite_result_id != OLD.composite_result_id
  OR NEW.test_id != OLD.test_id
  OR NEW.test_definition_version != OLD.test_definition_version
  OR NEW.test_definition_sha256 != OLD.test_definition_sha256
  OR NEW.catalogue_version != OLD.catalogue_version
  OR NEW.catalogue_sha256 != OLD.catalogue_sha256
  OR NEW.evidence_class != OLD.evidence_class
  OR NEW.application_build_id != OLD.application_build_id
  OR NEW.configuration_id != OLD.configuration_id
  OR NEW.configuration_version != OLD.configuration_version
  OR NEW.created_at_ms != OLD.created_at_ms
BEGIN
    SELECT RAISE(ABORT, 'composite validation provenance is immutable');
END;

CREATE TRIGGER composite_constituents_no_update
BEFORE UPDATE ON composite_validation_constituents
BEGIN
    SELECT RAISE(ABORT, 'composite constituent membership is immutable');
END;

CREATE TRIGGER composite_constituents_no_delete
BEFORE DELETE ON composite_validation_constituents
BEGIN
    SELECT RAISE(ABORT, 'composite constituent membership is immutable');
END;

CREATE TRIGGER composite_constituents_no_late_insert
BEFORE INSERT ON composite_validation_constituents
WHEN (
    SELECT status
    FROM composite_validation_results
    WHERE composite_result_id = NEW.composite_result_id
) = 'FINALISED'
BEGIN
    SELECT RAISE(ABORT, 'finalised composite cannot acquire constituents');
END;

CREATE TABLE composite_evidence_packages (
    package_id TEXT PRIMARY KEY,
    composite_result_id TEXT NOT NULL
        REFERENCES composite_validation_results(composite_result_id),
    evidence_class TEXT NOT NULL CHECK (evidence_class = 'EXPLORATORY'),
    source_application_build_id TEXT NOT NULL CHECK (length(source_application_build_id) = 64),
    manifest_sha256 TEXT NOT NULL CHECK (length(manifest_sha256) = 64),
    archive_sha256 TEXT NOT NULL CHECK (length(archive_sha256) = 64),
    archive_path TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL
);

CREATE INDEX composite_evidence_packages_by_result
ON composite_evidence_packages (composite_result_id, package_id);

CREATE TRIGGER composite_evidence_packages_no_update
BEFORE UPDATE ON composite_evidence_packages
BEGIN
    SELECT RAISE(ABORT, 'composite evidence package records are immutable');
END;

CREATE TRIGGER composite_evidence_packages_no_delete
BEFORE DELETE ON composite_evidence_packages
BEGIN
    SELECT RAISE(ABORT, 'composite evidence package records are immutable');
END;
