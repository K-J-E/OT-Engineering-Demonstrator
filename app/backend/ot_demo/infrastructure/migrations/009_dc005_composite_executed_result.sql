PRAGMA foreign_keys = ON;

ALTER TABLE composite_validation_constituent_sources
ADD COLUMN executed_result_id TEXT REFERENCES executed_validation_results(executed_result_id);

CREATE TRIGGER composite_executed_result_identity_no_update
BEFORE UPDATE ON composite_validation_constituent_sources
WHEN NEW.executed_result_id IS NOT OLD.executed_result_id
BEGIN SELECT RAISE(ABORT, 'composite executed-result identity is immutable'); END;

CREATE TRIGGER composite_executed_result_required_on_insert
BEFORE INSERT ON composite_validation_constituent_sources
WHEN (NEW.source_kind = 'EXECUTION_RESULT' AND NEW.executed_result_id IS NULL)
  OR (NEW.source_kind = 'SUSPENSION_RESULT' AND NEW.executed_result_id IS NOT NULL)
BEGIN SELECT RAISE(ABORT, 'composite source has invalid executed-result identity'); END;
