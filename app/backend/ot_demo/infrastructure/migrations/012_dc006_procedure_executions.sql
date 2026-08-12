PRAGMA foreign_keys = ON;

-- DC-006 non-scenario procedures still own a real ValidationExecution, but they
-- must not fabricate a ScenarioRun or scenario clock.  Scenario executions
-- remain in validation_executions so the established evidence foreign keys and
-- historical records are unchanged.
CREATE TABLE procedure_validation_executions (
    validation_execution_id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL,
    test_definition_version TEXT NOT NULL,
    test_definition_sha256 TEXT NOT NULL CHECK (length(test_definition_sha256) = 64),
    catalogue_version TEXT NOT NULL,
    catalogue_sha256 TEXT NOT NULL CHECK (length(catalogue_sha256) = 64),
    case_id TEXT,
    case_definition_version TEXT,
    case_definition_sha256 TEXT,
    context_kind TEXT NOT NULL CHECK (context_kind IN (
        'CONTROLLED_FIXTURE_EXECUTION','PRESERVED_RECORD_SET','ENGINEERING_REVIEW'
    )),
    evidence_class TEXT NOT NULL CHECK (evidence_class IN ('FORMAL','EXPLORATORY')),
    configuration_id TEXT NOT NULL,
    configuration_version TEXT NOT NULL,
    application_build_id TEXT NOT NULL CHECK (length(application_build_id) = 64),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','FINALISED')),
    started_at_ms INTEGER NOT NULL,
    finalised_at_ms INTEGER,
    verdict TEXT,
    validation_attempt_id TEXT NOT NULL UNIQUE
        REFERENCES validation_attempts(validation_attempt_id),
    target_selection_id TEXT NOT NULL UNIQUE
        REFERENCES validation_target_selections(target_selection_id),
    executed_result_id TEXT,
    payload_json TEXT NOT NULL
);

CREATE INDEX procedure_validation_executions_by_test
ON procedure_validation_executions (test_id, started_at_ms, validation_execution_id);

ALTER TABLE determination_contexts
ADD COLUMN procedure_validation_execution_id TEXT
    REFERENCES procedure_validation_executions(validation_execution_id);

CREATE TRIGGER determination_context_execution_shape_insert
BEFORE INSERT ON determination_contexts
WHEN (
    (NEW.context_kind = 'SCENARIO_EXECUTION' AND NEW.procedure_validation_execution_id IS NOT NULL)
    OR
    (NEW.context_kind != 'SCENARIO_EXECUTION' AND (
        NEW.scenario_run_id IS NOT NULL
        OR NEW.validation_execution_id IS NOT NULL
        OR NEW.procedure_validation_execution_id IS NULL
    ))
)
BEGIN
    SELECT RAISE(ABORT, 'determination context execution shape is invalid');
END;

CREATE TRIGGER determination_context_procedure_identity_no_update
BEFORE UPDATE ON determination_contexts
WHEN NEW.procedure_validation_execution_id IS NOT OLD.procedure_validation_execution_id
BEGIN
    SELECT RAISE(ABORT, 'determination context execution identity is immutable');
END;

CREATE TRIGGER dc006_result_requires_validation_execution
BEFORE INSERT ON dc006_executed_validation_results
WHEN NEW.validation_execution_id IS NULL
BEGIN
    SELECT RAISE(ABORT, 'executed non-composite determination requires ValidationExecution');
END;

CREATE TRIGGER dc006_result_execution_matches_context
BEFORE INSERT ON dc006_executed_validation_results
WHEN NEW.validation_execution_id IS NOT (
    SELECT CASE
        WHEN context_kind = 'SCENARIO_EXECUTION' THEN validation_execution_id
        ELSE procedure_validation_execution_id
    END
    FROM determination_contexts
    WHERE determination_context_id = NEW.determination_context_id
)
BEGIN
    SELECT RAISE(ABORT, 'result execution does not match determination context');
END;

CREATE TRIGGER procedure_validation_executions_no_delete
BEFORE DELETE ON procedure_validation_executions
BEGIN
    SELECT RAISE(ABORT, 'validation executions are immutable history');
END;

CREATE TRIGGER procedure_validation_finalised_no_update
BEFORE UPDATE ON procedure_validation_executions
WHEN OLD.status = 'FINALISED'
BEGIN
    SELECT RAISE(ABORT, 'finalised validation executions are immutable');
END;

CREATE TRIGGER procedure_validation_identity_no_update
BEFORE UPDATE ON procedure_validation_executions
WHEN NEW.validation_execution_id != OLD.validation_execution_id
  OR NEW.test_id != OLD.test_id
  OR NEW.test_definition_version != OLD.test_definition_version
  OR NEW.test_definition_sha256 != OLD.test_definition_sha256
  OR NEW.catalogue_version != OLD.catalogue_version
  OR NEW.catalogue_sha256 != OLD.catalogue_sha256
  OR NEW.case_id IS NOT OLD.case_id
  OR NEW.case_definition_version IS NOT OLD.case_definition_version
  OR NEW.case_definition_sha256 IS NOT OLD.case_definition_sha256
  OR NEW.context_kind != OLD.context_kind
  OR NEW.evidence_class != OLD.evidence_class
  OR NEW.configuration_id != OLD.configuration_id
  OR NEW.configuration_version != OLD.configuration_version
  OR NEW.application_build_id != OLD.application_build_id
  OR NEW.started_at_ms != OLD.started_at_ms
  OR NEW.validation_attempt_id != OLD.validation_attempt_id
  OR NEW.target_selection_id != OLD.target_selection_id
BEGIN
    SELECT RAISE(ABORT, 'validation execution provenance is immutable');
END;
