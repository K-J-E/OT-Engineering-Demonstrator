PRAGMA foreign_keys = ON;

CREATE TABLE determination_source_records (
    source_record_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    owner_module TEXT NOT NULL,
    application_build_id TEXT NOT NULL CHECK (length(application_build_id) = 64),
    evidence_class TEXT NOT NULL CHECK (evidence_class IN ('FORMAL','EXPLORATORY')),
    canonical_payload_sha256 TEXT NOT NULL CHECK (length(canonical_payload_sha256) = 64),
    created_at_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE determination_contexts (
    determination_context_id TEXT PRIMARY KEY,
    validation_attempt_id TEXT NOT NULL REFERENCES validation_attempts(validation_attempt_id),
    test_id TEXT NOT NULL,
    case_id TEXT,
    catalogue_version TEXT NOT NULL,
    catalogue_sha256 TEXT NOT NULL CHECK (length(catalogue_sha256) = 64),
    method_id TEXT NOT NULL,
    method_version TEXT NOT NULL,
    method_sha256 TEXT NOT NULL CHECK (length(method_sha256) = 64),
    context_kind TEXT NOT NULL CHECK (context_kind IN (
        'SCENARIO_EXECUTION','CONTROLLED_FIXTURE_EXECUTION',
        'PRESERVED_RECORD_SET','ENGINEERING_REVIEW'
    )),
    status TEXT NOT NULL CHECK (status IN ('DRAFT','FROZEN')),
    scenario_run_id TEXT,
    validation_execution_id TEXT,
    created_at_ms INTEGER NOT NULL,
    frozen_at_ms INTEGER,
    payload_json TEXT NOT NULL,
    CHECK (test_id NOT IN ('VT-EXP-ALL-001','VT-EXP-ROLE-001') OR case_id IS NOT NULL),
    CHECK (
        (context_kind = 'SCENARIO_EXECUTION' AND scenario_run_id IS NOT NULL AND validation_execution_id IS NOT NULL)
        OR
        (context_kind != 'SCENARIO_EXECUTION' AND scenario_run_id IS NULL AND validation_execution_id IS NULL)
    )
);

CREATE TABLE determination_context_members (
    determination_context_id TEXT NOT NULL REFERENCES determination_contexts(determination_context_id),
    role TEXT NOT NULL,
    source_record_id TEXT NOT NULL REFERENCES determination_source_records(source_record_id),
    source_record_sha256 TEXT NOT NULL CHECK (length(source_record_sha256) = 64),
    payload_json TEXT NOT NULL,
    PRIMARY KEY (determination_context_id, role)
);

CREATE TABLE criterion_findings (
    criterion_finding_id TEXT PRIMARY KEY,
    determination_context_id TEXT NOT NULL REFERENCES determination_contexts(determination_context_id),
    criterion_id TEXT NOT NULL,
    criterion_sha256 TEXT NOT NULL CHECK (length(criterion_sha256) = 64),
    status TEXT NOT NULL CHECK (status IN ('NOT_EVALUATED','SATISFIED','NOT_SATISFIED')),
    finding_sha256 TEXT NOT NULL CHECK (length(finding_sha256) = 64),
    finalised_at_ms INTEGER,
    payload_json TEXT NOT NULL,
    UNIQUE (determination_context_id, criterion_id),
    CHECK (
        (status = 'NOT_EVALUATED' AND finalised_at_ms IS NULL)
        OR (status != 'NOT_EVALUATED' AND finalised_at_ms IS NOT NULL)
    )
);

CREATE TABLE engineering_review_proposals (
    review_proposal_id TEXT PRIMARY KEY,
    determination_context_id TEXT NOT NULL REFERENCES determination_contexts(determination_context_id),
    criterion_id TEXT NOT NULL,
    proposer_actor_id TEXT NOT NULL,
    proposed_finding TEXT NOT NULL CHECK (proposed_finding IN ('SATISFIED','NOT_SATISFIED')),
    proposal_sha256 TEXT NOT NULL CHECK (length(proposal_sha256) = 64),
    proposed_at_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (determination_context_id, criterion_id)
);

CREATE TABLE engineering_review_finalisations (
    review_finalisation_id TEXT PRIMARY KEY,
    review_proposal_id TEXT NOT NULL UNIQUE REFERENCES engineering_review_proposals(review_proposal_id),
    determination_context_id TEXT NOT NULL REFERENCES determination_contexts(determination_context_id),
    criterion_id TEXT NOT NULL,
    reviewer_actor_id TEXT NOT NULL,
    final_finding TEXT NOT NULL CHECK (final_finding IN ('SATISFIED','NOT_SATISFIED')),
    finalisation_sha256 TEXT NOT NULL CHECK (length(finalisation_sha256) = 64),
    finalised_at_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (determination_context_id, criterion_id)
);

CREATE TABLE dc006_executed_validation_results (
    executed_result_id TEXT PRIMARY KEY,
    validation_attempt_id TEXT NOT NULL UNIQUE REFERENCES validation_attempts(validation_attempt_id),
    determination_context_id TEXT NOT NULL UNIQUE REFERENCES determination_contexts(determination_context_id),
    validation_execution_id TEXT,
    test_id TEXT NOT NULL,
    case_id TEXT,
    catalogue_version TEXT NOT NULL,
    catalogue_sha256 TEXT NOT NULL CHECK (length(catalogue_sha256) = 64),
    method_id TEXT NOT NULL,
    method_sha256 TEXT NOT NULL CHECK (length(method_sha256) = 64),
    verdict TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL')),
    result_sha256 TEXT NOT NULL CHECK (length(result_sha256) = 64),
    finalised_at_ms INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    CHECK (test_id NOT IN ('VT-EXP-ALL-001','VT-EXP-ROLE-001') OR case_id IS NOT NULL)
);

CREATE TRIGGER determination_source_no_update BEFORE UPDATE ON determination_source_records
BEGIN SELECT RAISE(ABORT, 'determination source records are immutable'); END;
CREATE TRIGGER determination_source_no_delete BEFORE DELETE ON determination_source_records
BEGIN SELECT RAISE(ABORT, 'determination source records are immutable'); END;
CREATE TRIGGER determination_context_no_delete BEFORE DELETE ON determination_contexts
BEGIN SELECT RAISE(ABORT, 'determination contexts are immutable history'); END;
CREATE TRIGGER determination_frozen_context_no_update BEFORE UPDATE ON determination_contexts
WHEN OLD.status = 'FROZEN'
BEGIN SELECT RAISE(ABORT, 'frozen determination context is immutable'); END;
CREATE TRIGGER determination_context_identity_no_update BEFORE UPDATE ON determination_contexts
WHEN NEW.determination_context_id != OLD.determination_context_id
 OR NEW.validation_attempt_id != OLD.validation_attempt_id
 OR NEW.test_id != OLD.test_id
 OR NEW.case_id IS NOT OLD.case_id
 OR NEW.catalogue_version != OLD.catalogue_version
 OR NEW.catalogue_sha256 != OLD.catalogue_sha256
 OR NEW.method_id != OLD.method_id
 OR NEW.method_version != OLD.method_version
 OR NEW.method_sha256 != OLD.method_sha256
 OR NEW.context_kind != OLD.context_kind
 OR NEW.scenario_run_id IS NOT OLD.scenario_run_id
 OR NEW.validation_execution_id IS NOT OLD.validation_execution_id
 OR NEW.created_at_ms != OLD.created_at_ms
BEGIN SELECT RAISE(ABORT, 'determination context identity is immutable'); END;
CREATE TRIGGER determination_member_no_update BEFORE UPDATE ON determination_context_members
BEGIN SELECT RAISE(ABORT, 'determination context membership is immutable'); END;
CREATE TRIGGER determination_member_no_delete BEFORE DELETE ON determination_context_members
BEGIN SELECT RAISE(ABORT, 'determination context membership is immutable'); END;
CREATE TRIGGER determination_member_no_late_insert BEFORE INSERT ON determination_context_members
WHEN (SELECT status FROM determination_contexts WHERE determination_context_id = NEW.determination_context_id) = 'FROZEN'
BEGIN SELECT RAISE(ABORT, 'frozen determination context cannot acquire members'); END;
CREATE TRIGGER criterion_finding_no_update BEFORE UPDATE ON criterion_findings
BEGIN SELECT RAISE(ABORT, 'criterion findings are immutable'); END;
CREATE TRIGGER criterion_finding_no_delete BEFORE DELETE ON criterion_findings
BEGIN SELECT RAISE(ABORT, 'criterion findings are immutable'); END;
CREATE TRIGGER criterion_finding_no_late_insert BEFORE INSERT ON criterion_findings
WHEN EXISTS (
    SELECT 1 FROM dc006_executed_validation_results
    WHERE determination_context_id = NEW.determination_context_id
)
BEGIN SELECT RAISE(ABORT, 'final determination cannot acquire findings'); END;
CREATE TRIGGER review_proposal_no_update BEFORE UPDATE ON engineering_review_proposals
BEGIN SELECT RAISE(ABORT, 'engineering-review proposals are immutable'); END;
CREATE TRIGGER review_proposal_no_delete BEFORE DELETE ON engineering_review_proposals
BEGIN SELECT RAISE(ABORT, 'engineering-review proposals are immutable'); END;
CREATE TRIGGER review_proposal_no_late_insert BEFORE INSERT ON engineering_review_proposals
WHEN EXISTS (
    SELECT 1 FROM dc006_executed_validation_results
    WHERE determination_context_id = NEW.determination_context_id
)
BEGIN SELECT RAISE(ABORT, 'final determination cannot acquire review proposals'); END;
CREATE TRIGGER review_finalisation_no_update BEFORE UPDATE ON engineering_review_finalisations
BEGIN SELECT RAISE(ABORT, 'engineering-review finalisations are immutable'); END;
CREATE TRIGGER review_finalisation_no_delete BEFORE DELETE ON engineering_review_finalisations
BEGIN SELECT RAISE(ABORT, 'engineering-review finalisations are immutable'); END;
CREATE TRIGGER dc006_result_no_update BEFORE UPDATE ON dc006_executed_validation_results
BEGIN SELECT RAISE(ABORT, 'DC-006 executed validation results are immutable'); END;
CREATE TRIGGER dc006_result_no_delete BEFORE DELETE ON dc006_executed_validation_results
BEGIN SELECT RAISE(ABORT, 'DC-006 executed validation results are immutable'); END;
