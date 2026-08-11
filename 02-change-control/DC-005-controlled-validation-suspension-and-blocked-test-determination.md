# DC-005 — Controlled Validation Suspension and BLOCKED-TEST Determination

Status: Proposed / pending independent engineering review

Date raised: 2026-08-11

Proposal date: 2026-08-11

Change class: Validation-assurance lifecycle and record-model clarification

Origin: QA-042 design-control stop during independent DC-004 application review

## 1. Purpose and change boundary

Accepted Validation Plan v1.1 distinguishes an operational engineering result
`BLOCKED` from the validation verdict `BLOCKED-TEST` and names five permitted
validation suspension conditions. Accepted DC-004 permits a complete
multi-run exploratory composite to aggregate a genuine constituent
`BLOCKED-TEST`, but deliberately requires the named accepted condition and its
supporting evidence.

The accepted baseline does not yet define the machine identities, lifecycle
positions, authority, condition-specific evidence or immutable record needed
to establish that determination. QA-042 therefore stopped rather than allowing
a client to submit arbitrary prose and a verdict.

DC-005 proposes that missing contract. It changes validation assurance only.
It does not change network configuration, topology, outage, telemetry validity,
DC-003 isolation, restoration, scenario electrical behaviour or expected
engineering outcomes. It proposes a controlled terminology clarification to
`REQ-VAL-007`, `REQ-VAL-008` and `REQ-VAL-009` while retaining those IDs, the
124-requirement total, all 286 requirement-to-test relationships, the 24-test
catalogue and the 15 operational-event types.

This proposal does not implement QA-041 or QA-042, alter PR #10, resume I9 or
authorise application work.

## 2. Existing authoritative meaning retained

The following distinctions remain controlling:

- `PERMITTED`, `REJECTED`, operational `BLOCKED` and `NO_CANDIDATE` describe
  engineering/system outcomes. When a controlled negative test expects one of
  those outcomes and the evidence agrees, the validation verdict is `PASS`.
- A `ValidationAttempt` begins only after a trusted campaign/test-selection
  authority binds the intended controlled test or case and entry assurance
  starts. An attempt may remain incomplete, become active or terminate
  `SUSPENDED` with a valid `BLOCKED-TEST` assurance determination.
- An `ExecutedValidationResult` exists only after valid
  expected-versus-observed comparison. It records the observed result,
  sufficient supporting evidence and exactly one `PASS` or `FAIL`.
- `NOT RUN` means no valid attempt or accepted suspension determination exists;
  it draws no engineering or validation conclusion.
- `BLOCKED-TEST` means the validation procedure itself could not validly start,
  continue or reach determination because exactly one accepted entry/suspension
  condition was established with its required evidence.
- Ordinary missing evidence does not establish FAIL or suspension. It leaves
  the attempt non-finalisable/incomplete unless exactly one accepted condition
  is established. An unsupported condition is rejected. A missing or
  unexecuted DC-004 case remains `INCOMPLETE`; neither state can be relabelled
  `BLOCKED-TEST`.

## 3. Exact controlled condition identities

DC-005 adds no suspension category. The exact stable IDs and labels are:

| Condition ID | Accepted label | Authoritative meaning |
|---|---|---|
| `VSC-001` | Unspecified engineering behaviour | Integrity-valid trusted authoritative sources contain no controlling behaviour for the required field/step. |
| `VSC-002` | Inconsistent baseline | Two or more integrity-valid trusted authoritative sources provide incompatible controlling statements for the same field/step. |
| `VSC-003` | Unidentifiable input version | After integrity verification passes for presented artefacts, a required build, configuration, catalogue, test definition, case definition or fixture identity is missing, unknown or ambiguous. |
| `VSC-004` | Uncontrolled wall-clock dependency | One integrity-valid, unambiguous trusted definition/runtime actually relies on local current time, sleep/delay or another non-controlled time source. |
| `VSC-005` | Evidence corruption | A required trusted artefact/package fails its declared integrity, schema, hash or canonical-payload verification. |

The ID, not a label or narrative note, is the authoritative classification.
Labels may be presented for review but cannot create or change the result.

### 3.1 Deterministic non-overlapping classifier

The versioned classifier evaluates one semantic chain and stops at the first
applicable authoritative boundary:

1. a trusted target-selection anchor must exist before case-level evaluation;
2. integrity/schema/hash/canonical-payload failure is exclusively `VSC-005`;
3. only integrity-valid presented inputs proceed to identity resolution, where
   missing, unknown or ambiguous required identity is `VSC-003`;
4. among resolved trusted controlling sources, multiple incompatible
   assertions are `VSC-002`;
5. if those trusted sources contain no controlling behaviour, the result is
   `VSC-001`; and
6. only one unambiguous trusted definition/runtime that actually relies on a
   non-controlled time source is `VSC-004`.

Unsupported or simultaneous client claims are rejected; they do not select a
condition. Identical preserved facts and the same classifier version therefore
produce exactly one authoritative condition ID.

## 4. Lifecycle location of suspension

DC-005 defines three lifecycle points:

| Lifecycle point | Meaning |
|---|---|
| `PRE_EXECUTION_ENTRY` | The controlled test/case has been selected but a valid `ValidationExecution` and, where applicable, `ScenarioRun` cannot be created because an accepted entry condition fails. |
| `EXECUTION_IN_PROGRESS` | A valid execution already exists, but an accepted condition prevents the next controlled step or completion. Existing run, execution and evidence identities are preserved. |
| `EVIDENCE_FINALISATION` | The steps may have run, but verification of comparison inputs, provenance or evidence exposes an accepted condition that prevents a valid PASS/FAIL determination. |

The permitted locations are:

| Condition | Pre-execution | In execution | Evidence/finalisation | Rationale |
|---|---:|---:|---:|---|
| `VSC-001` | Yes | Yes | Yes | Missing engineering meaning may be found during source review, an attempted step or comparison review. |
| `VSC-002` | Yes | Yes | Yes | A source conflict may be visible before entry or discovered when a step/result is reconciled. |
| `VSC-003` | Yes | Yes | Yes | Entry normally catches identity failure; later resolution or historical review may expose a previously unavailable/mismatched identity. |
| `VSC-004` | Yes | Yes | Yes | A definition may prescribe wall time, a runtime step may use it, or evidence review may reveal it. |
| `VSC-005` | Yes | Yes | Yes | A required fixture may fail before entry, captured evidence may fail during the run, or stored evidence may fail final integrity review. |

This classification does not require every condition to occur at every point in
normal operation. It defines where a genuine occurrence is represented without
fabricating a run or discarding an existing one.

## 5. Lifecycle and determination model

### 5.1 Pre-execution suspension

Where a condition prevents valid entry, no `ScenarioRun` or
`ValidationExecution` is created merely to obtain a place to store a verdict.
Before evaluation, a trusted campaign/test-selection authority creates an
immutable `ValidationTargetSelection` that identifies the intended controlled
test/case, requested input identities, source campaign/catalogue authority and
canonical selection hash. Client-supplied `test_id` or `case_id` text is not a
target authority.

The assurance service creates a `ValidationAttempt` and a draft
`ValidationSuspensionRecord` against that anchor. It records only source
identities actually resolved, the failed required input role and presented
identity evidence, and the assurance-verifier application build separately
from the intended/unresolved target application build. Finalisation can make
the record authoritative at test/case level only when the target anchor proves
that exact test/case under the accepted active or historical source package.

The absence of run/execution identities is explicit as
`PRE_EXECUTION_ENTRY`; it is not a blank field that may be interpreted as a
missing linkage.

### 5.2 Suspension after execution starts

Where a valid execution/run context already exists, the suspension record must
link it exactly and preserve every checkpoint/evidence record. The
`ValidationAttempt` enters terminal status `SUSPENDED` and exposes
`BLOCKED-TEST` through the finalised suspension record. It does not create an
`ExecutedValidationResult`, because valid comparison was not reached. It
cannot later be reopened or converted to PASS/FAIL; a new valid attempt creates
new identities.

### 5.3 Evidence/finalisation suspension

Where an accepted condition is established while verifying evidence or
provenance, the same linked treatment applies. A comparison mismatch under
valid evidence creates `FAIL`; it cannot be converted to suspension. Ordinary
missing mandatory evidence alone creates neither FAIL nor BLOCKED-TEST: the
attempt remains non-finalisable/incomplete unless a genuine accepted condition
is established through the applicable classifier, authority and evidence
contract.

## 6. Immutable `ValidationSuspensionRecord`

The proposed minimum record is:

| Field group | Controlled fields and rules |
|---|---|
| Identity | `suspension_record_id` as UUID v4; review display `VSR-` plus first eight UUID characters; `record_schema_version`. |
| Classification | `classifier_version`; evaluated gate outcomes; exactly one `condition_id` from `VSC-001`–`VSC-005`; controlled label is resolved from the registry. |
| Intended target anchor | `target_selection_id`; trusted campaign/test-selection authority identity/version/hash; intended `test_id`/`case_id`; requested catalogue/test/case/configuration/fixture/application-build identities; canonical selection payload SHA-256. |
| Resolved source provenance | Only successfully verified catalogue/test/case-definition and input identities; historical resolver/package identity used. |
| Failed-input provenance | Exact `failed_required_input_role`; every presented ID/version/hash or explicit absence; controlled resolver evidence. |
| Build separation | `target_application_build_id` remains intended/resolved/unresolved as evidenced; `assurance_verifier_build_id` identifies the build making the suspension determination and never substitutes for the target. |
| Attempt and existing context | `validation_attempt_id`; `scenario_run_id` and `validation_execution_id` only when validly created; `executed_validation_result_id` is absent for suspension. |
| Lifecycle | One lifecycle point from Section 4; evidence class `FORMAL` or `EXPLORATORY` inherited from the bound definition/case. |
| Authority | `authority_kind`; backend verifier identity/build or controlled local reviewer `actor_id`/role; proposal/finalisation actor separation where reviewer judgement is required. |
| Evidence | Condition-specific evidence-contract version; ordered/canonical immutable evidence references; structured evidence payload hash; verifier result and provenance agreement result. |
| Reason | Backend-generated `controlled_reason_code`, controlled reason parameters, rendered deterministic reason and canonical reason fingerprint. |
| State | `DRAFT` or `FINALISED`; `BLOCKED-TEST` relationship exists only when `FINALISED`. |
| Audit | Administrative `created_at` and `finalised_at`, explicitly not engineering scenario time; optional human notes stored separately and excluded from reason/verdict derivation. |

A draft permits review and correction before finalisation but carries no
verdict. Finalisation is atomic with the evidence membership and, when an
execution exists, its terminal suspension relationship.

## 7. Common evidence binding rules

Every condition-specific evidence item uses a common immutable envelope:

- evidence-record ID and evidence type;
- owning `target_selection_id` and intended test/case;
- trusted campaign/test-selection authority identity and selection hash;
- resolved catalogue/test/case-definition identities only where verified;
- intended/resolved target application build and configuration/input identity
  where applicable;
- separate assurance-verifier application build;
- failed input role and presented identity evidence where applicable;
- run/execution identity when one exists;
- repository/source-record reference and canonical payload SHA-256;
- producer/verifier identity and verification result; and
- lifecycle point and evidence-class agreement.

The assurance service resolves these identities from controlled repositories.
A client cannot make unrelated evidence relevant by copying its ID. Evidence
from another test, case, definition, build, configuration, run or execution is
rejected whenever that identity is applicable. Historical records resolve
against their own accepted catalogue/definition package under DC-004 rather
than being relabelled under the active version. A copied test/case ID, even if
textually valid, cannot replace the trusted target selection.

## 8. Condition-specific evidence contracts

### 8.1 `VSC-001` — Unspecified engineering behaviour

Authority: engineering/reviewer judgement; never asserted automatically merely
because a code path is absent.

Mandatory evidence:

1. a `ControlledSourceReviewEvidence` record naming every integrity-valid
   reviewed governing or detailed source by document identity, version,
   SHA-256 and section;
2. the exact test/case/step or comparison field for which controlling behaviour
   is absent;
3. a registered engineering-design-question reference in the controlled QA/DQ
   register that binds the same test/case and source-review record;
4. proposal actor and independent engineering-reviewer finalisation actor; and
5. run/execution/evidence links if the issue was discovered after entry.

Verification confirms the cited source files/hashes exist, the question record
is current and linked, the reviewer is authorised and no PASS/FAIL comparison
has already been finalised. Optional narrative explanation is not the
classification or verdict basis.

### 8.2 `VSC-002` — Inconsistent baseline

Authority: engineering/reviewer judgement.

Mandatory evidence:

1. a `BaselineConflictEvidence` record containing at least two distinct,
   integrity-valid trusted authoritative controlling assertions;
2. for each assertion: document identity/version/hash, section/row reference
   and canonical assertion-text hash;
3. the exact controlling field/step/result affected;
4. a controlled conflict-review item that records why the authority hierarchy
   did not already resolve the issue and remains open; and
5. proposal actor plus independent engineering-reviewer finalisation actor.

Verification proves that the sources are distinct, their hashes match the
controlled artefacts and all evidence binds to the same test/case. The backend
does not pretend to infer engineering contradiction from text; it validates the
record and reviewer authority.

### 8.3 `VSC-003` — Unidentifiable input version

Authority: backend assurance from the controlled identity resolver. A client or
reviewer may request evaluation but cannot override the resolver result.

Mandatory evidence is an `IdentityResolutionEvidence` record containing:

- one required input role from `APPLICATION_BUILD`, `CONFIGURATION`,
  `CATALOGUE`, `TEST_DEFINITION`, `CASE_DEFINITION` or `CONTROLLED_FIXTURE`;
- every presented ID/version/hash value, including explicit absence;
- one resolver failure code from `MISSING_IDENTITY`, `UNKNOWN_IDENTITY` or
  `AMBIGUOUS_IDENTITY` after integrity checks pass for every presented
  artefact;
- resolver service identity, backend build and canonical resolution-attempt
  payload/hash; and
- the test/case and any run/execution identity already established.

Finalisation re-runs or independently verifies the resolver failure. If the
input resolves uniquely, `VSC-003` is rejected. Configuration or definition
identity may be unavailable only when that exact input role is the proven
failure; all other available provenance remains mandatory.

`HASH_MISMATCH`, schema failure, unreadable bytes and canonical-payload
mismatch are exclusively `VSC-005`; they are never `VSC-003` identity outcomes.

### 8.4 `VSC-004` — Uncontrolled wall-clock dependency

Authority:

- pre-entry definition review: engineering reviewer; or
- runtime/evidence detection: backend assurance.

Pre-entry mandatory evidence is a `ControlledTimeDefinitionReviewEvidence`
record containing one integrity-valid, unambiguous trusted catalogue/test/case
definition identity, procedure step/checkpoint index, canonical step-text hash
and reviewer authority showing that the controlling step actually requires
local current time, sleep/delay or a non-controlled time source. Missing or
ambiguous controlling definitions classify earlier as `VSC-001`, `VSC-002` or
`VSC-003`, as applicable.

Runtime/finalisation mandatory evidence is a `TimeAuthorityEvidence` record
containing:

- affected command, step, checkpoint or comparison field;
- required authority `CONTROLLED_SCENARIO_CLOCK`;
- observed time authority/source identity;
- one failure code from `MISSING_CONTROLLED_TIME`,
  `WALL_CLOCK_SOURCE_DETECTED` or `NONDETERMINISTIC_DELAY_DEPENDENCY`;
- controlled scenario time if one validly exists, without substituting it for
  the offending time source; and
- backend verifier/build plus run/execution identity.

Equivalent controlled timestamps with different elapsed wall time never create
this condition. The 60,000 ms freshness rule and deterministic scenario clock
remain unchanged.

### 8.5 `VSC-005` — Evidence corruption

Authority: backend integrity/schema verifier. A reviewer cannot declare an
otherwise valid record corrupt through prose.

Mandatory evidence is an `IntegrityFailureEvidence` record containing:

- artefact/evidence type and controlled record/file identity;
- owning test/case/build/configuration/run/execution identities where
  applicable;
- expected SHA-256 and actual SHA-256, or explicit absence where the bytes are
  unreadable;
- one failure code from `HASH_MISMATCH`, `UNREADABLE`, `SCHEMA_INVALID` or
  `CANONICAL_PAYLOAD_MISMATCH`;
- verifier identity/build and schema/manifest identity used; and
- an immutable quarantine/source reference and hash for the bytes or failure
  report that was actually examined.

Finalisation repeats or verifies the integrity failure. A missing optional item
or ordinary absence of mandatory evidence is not corruption and does not create
`BLOCKED-TEST`.

## 9. Authority and interaction model

| Condition | May be proposed by | Final authority | Client boundary |
|---|---|---|---|
| `VSC-001` | Graduate Engineer | Independent Engineering Reviewer | Client may select the accepted ID and submit controlled source/question references; cannot submit verdict or reason. |
| `VSC-002` | Graduate Engineer | Independent Engineering Reviewer | Client may submit the accepted ID and exact conflict records; cannot assert machine-detected conflict or verdict. |
| `VSC-003` | Backend resolver or user request for evaluation | Backend Assurance | Client cannot choose resolver outcome, failure code, controlled reason or verdict. |
| `VSC-004` pre-entry | Graduate Engineer | Independent Engineering Reviewer | Client submits exact definition/step evidence; reviewer decision is required. |
| `VSC-004` runtime/finalisation | Backend time-authority verifier | Backend Assurance | Client cannot override the detected authority/source or verdict. |
| `VSC-005` | Backend integrity verifier | Backend Assurance | Client cannot supply the integrity result, hashes, failure code or verdict. |

Reviewer-authorised records require distinct proposal and finalisation audit
identities. V1 machine-enforces that both actor IDs exist in a controlled local
actor/role registry, the roles are eligible, the IDs differ, the audit links
agree and finalisation is immutable. The same actor ID may not both propose and
finalise the record. V1 does not authenticate a real person or cryptographically
prove organisational independence; independent engineering review asserts
that the controlled actor identities correspond to distinct reviewers.
Backend-authorised records identify the service/module and assurance-verifier
build and are reproducible from preserved controlled facts.

The public API accepts a suspension evaluation/request, not
`verdict = BLOCKED-TEST`. The backend resolves the condition registry, validates
the exact evidence contract and generates the result.

## 10. Deterministic controlled reason

Every finalised record contains:

- `controlled_reason_code` formatted
  `BLOCKED-TEST/<condition_id>/<lifecycle_point>`;
- condition-specific controlled parameters from verified evidence;
- a backend-rendered reason from the fixed template for that condition; and
- `reason_fingerprint = SHA-256(canonical JSON(classifier version, evaluated
  gate outcomes, selected condition ID, lifecycle point, target-selection
  identity/hash, resolved-source identities, failed-input evidence where
  applicable, evidence-contract version, sorted verified evidence
  identities/hashes and controlled parameters))`.

The fixed reason semantics are:

| Condition | Controlled template meaning |
|---|---|
| `VSC-001` | Required engineering behaviour is unspecified for the bound test/case/field; identifies the controlled design-question record. |
| `VSC-002` | Identified authoritative sources conflict for the bound test/case/field; identifies the controlled conflict-review record. |
| `VSC-003` | The named required input role failed controlled identity resolution with the verified resolver failure code. |
| `VSC-004` | The named step/checkpoint depends on the verified non-controlled time authority/failure code instead of the controlled scenario clock. |
| `VSC-005` | The named evidence/artefact failed the verified integrity/schema check with the controlled failure code. |

Optional human notes are stored separately, are excluded from the reason code,
fingerprint and verdict, and cannot relax an evidence rule. Equivalent verified
facts therefore retain equivalent controlled reason semantics even when record
UUIDs or narrative notes differ.

## 11. Exact `BLOCKED-TEST` transition

The assurance authority may finalise `BLOCKED-TEST` only when all of the
following are true:

1. a trusted `ValidationTargetSelection` proves the intended controlled
   test/case under its campaign/test-selection authority;
2. the versioned classifier evaluates the preserved facts and selects exactly
   one ID from `VSC-001`–`VSC-005`;
3. its lifecycle point is permitted;
4. the bound test/case and every available catalogue/definition/build/input
   identity resolve under the applicable active or historical package;
5. the target application-build role is distinct from the
   assurance-verifier-build role and neither substitutes for the other;
6. its condition-specific evidence contract is complete;
7. common evidence provenance agrees;
8. the required backend or reviewer control is satisfied;
9. no prior ExecutedValidationResult/final suspension exists for the attempt;
10. the backend generates the controlled reason/fingerprint; and
11. the record and evidence membership are atomically finalised and immutable.

Failure of any check rejects finalisation and leaves a reviewable draft or no
record. It never defaults to `BLOCKED-TEST`.

## 12. DC-004 composite interaction

DC-004 constituent membership is amended to a controlled union so pre-entry
suspension does not require a fictional run:

| Constituent source kind | Required source | Permitted verdict |
|---|---|---|
| `EXECUTION_RESULT` | One finalised `ExecutedValidationResult` and its actual `ValidationExecution`/`ScenarioRun`/evidence | `PASS` or `FAIL` only. |
| `SUSPENSION_RESULT` | One finalised `ValidationSuspensionRecord` whose trusted target-selection authority/hash resolves to the exact required case; linked execution/run required when validly created and explicitly absent only for `PRE_EXECUTION_ENTRY` | `BLOCKED-TEST` only. |

For an in-progress/finalisation suspension, the suspension source references
the terminal suspended attempt and actual execution/run context. For a
pre-entry suspension, the source contains its immutable target selection,
successfully resolved source identities, failed input role/presented identity
evidence, intended/unresolved target application build and separate
assurance-verifier build plus the verified reason entry failed.

Composite assembly independently resolves the source kind and verifies:

- exact required case appears once through exactly one source kind and, for a
  suspension, is proved by the trusted campaign/test-selection anchor rather
  than caller-supplied `case_id` text;
- test/case/definition/catalogue/build/configuration provenance agrees, except
  only the specific unavailable input proven by valid `VSC-003`;
- an `EXECUTION_RESULT` verdict is read from its immutable execution;
- a `SUSPENSION_RESULT` is finalised, condition-authorised and evidence-valid;
- any linked execution/run/evidence agrees bidirectionally; and
- the same execution or suspension record is not assigned inconsistently.

Aggregate precedence remains unchanged:

- complete and every constituent PASS → `PASS`;
- complete and any constituent FAIL → `FAIL`, including when another is a
  valid `BLOCKED-TEST`;
- complete, no FAIL, at least one valid `BLOCKED-TEST` and every other PASS →
  `BLOCKED-TEST`; and
- missing/unexecuted/invalid constituent → `INCOMPLETE` with no verdict.

A stored enum without its finalised suspension record and verified evidence is
never sufficient.

## 13. Immutability, history and export

Database-level controls shall reject update/delete of a finalised suspension,
condition replacement, evidence membership insertion/removal/replacement and
reclassification. A repeated or corrected attempt creates a new suspension,
run/execution where valid and composite identity. Historical records are never
rewritten.

Historical catalogue/build resolution follows accepted DC-004. A finalised
suspension and linked suspended execution remain reviewable/exportable under
their original source catalogue/test/case-definition identities after a later
catalogue or application build. An unfinished draft bound to an old catalogue
is historical/read-only and cannot be finalised under a new definition.

Evidence export includes the suspension record, condition-registry definition,
structured evidence payloads, authority audit, controlled reason/fingerprint
and linked execution/run/evidence where they exist. Source application/catalogue
identity remains separate from generation build. Export never reconstructs the
condition from current mutable state.

## 14. FORMAL and EXPLORATORY treatment

The record inherits evidence class from its controlled test/case; the client
does not select it.

- A finalised FORMAL suspension may contribute to the FORMAL
  `BLOCKED-TEST` determination count for its test. It contributes to execution
  counts only when a real execution exists and is linked.
- An EXPLORATORY suspension never changes FORMAL definition, execution, PASS,
  FAIL or `BLOCKED-TEST` progress totals.
- Every DC-004 case suspension and composite remains `EXPLORATORY`.
- Presentation labels pre-entry suspension without implying that a run was
  executed, and shows actual run/execution IDs only where they exist.

QA-034 remains controlling.

## 15. Future implementation verification matrix

Future controlled application shall prove at minimum:

1. the condition registry recognises exactly `VSC-001`–`VSC-005` and rejects an
   unsupported ID;
2. every condition-specific mandatory evidence contract is enforced;
3. unrelated or wrong-test/case/run/build/configuration/catalogue/definition
   evidence is rejected whenever applicable;
4. reviewer-authorised conditions require distinct authorised proposal and
   finalisation actors;
5. backend-authorised conditions derive their verifier facts, failure code,
   reason and verdict without client override;
6. the versioned classifier gives exactly one deterministic non-overlapping
   VSC result, including HASH_MISMATCH exclusively as VSC-005;
7. valid finalised suspension produces `BLOCKED-TEST`; missing evidence,
   unsupported condition and unexecuted test do not;
8. pre-entry suspension requires a trusted target anchor and creates no
   fictional run/execution/result;
9. target application and assurance-verifier builds remain distinct;
10. post-entry suspension preserves and terminally links the actual execution,
   run and captured evidence;
11. valid comparison creates `ExecutedValidationResult` PASS/FAIL; ordinary
    missing evidence remains incomplete;
12. operational restoration `BLOCKED` remains distinct and produces validation
   PASS when it matches the negative-test oracle;
13. complete DC-004 membership with one valid suspension and remaining PASS
    finalises `BLOCKED-TEST`;
14. one genuine FAIL plus one genuine suspension finalises FAIL;
15. missing/unanchored/invalid membership remains INCOMPLETE;
16. finalised suspension/evidence/composite membership is database-immutable;
17. historical review/export preserves target/source/verifier provenance;
18. FORMAL/EXPLORATORY progress remains separated;
19. exactly 24 tests, 124 requirements, 286 RTM relationships and 15 event types
    remain unchanged; and
20. canonical network/configuration/schema and dependency identities remain
    unchanged.

## 16. Authoritative artefact impact assessment

| Artefact | Proposed impact | Basis |
|---|---|---|
| Validation Plan v1.1 | Proposed v1.2 Section 20 | Makes the existing five-condition suspension/BLOCKED-TEST meaning executable and testable. |
| Demonstrator Design v0.3 | Proposed v0.4 Section 37 | Defines record/API/persistence/review/export implementation boundary without applying it. |
| System Architecture v0.2 | Proposed v0.3 Section 27 | SA-CMP-08 currently describes execution-based PASS/FAIL only and needs the separate suspension assurance record plus optional execution relationship. |
| Workflow Design v0.2 | Proposed v0.3 Section 28 | Existing completion flow records PASS/FAIL only and needs pre-entry, post-entry and finalisation suspension sequences and authority roles. |
| Requirements Specification v0.3 | Proposed v0.4 controlled wording clarification to `REQ-VAL-007`–`REQ-VAL-009` | Defines ValidationAttempt versus ExecutedValidationResult in the requirements themselves. IDs, verification intent, 124 total and exact 286 RTM relationships remain unchanged. |
| Engineering Design Brief | No change | The change clarifies validation assurance, not operational engineering behaviour. |
| Network Model | No change | No electrical state, value, topology or validation answer key changes. |
| DC-004 | Bounded relationship clarification | Composite membership accepts a verified suspension source for `BLOCKED-TEST` without weakening one-execution/one-run provenance for actual executions. |

### 16.1 Accepted and proposed authoritative identities

The accepted identities below remain authoritative while DC-005 is under
independent review. The proposed identities are the exact working files on
`agent/dc-005-validation-suspension`; they do not supersede the accepted files
unless DC-005 is separately accepted and applied.

| Artefact | Accepted identity | Proposed DC-005 identity |
|---|---|---|
| Requirements Specification | v0.3; SHA-256 `7d5522e53dd99e505b9853d6b0b0255c8b4585964909f5659e1ab13d7d1eaeea`; 38,838 bytes; 1,261 paragraphs; 1 table; 124 requirements | v0.4 proposed clarification; SHA-256 `11c8760aa3ed9b745853c6b6e9ab7363c0b6c1c64f7d26755e8ff57f465f352d`; 39,533 bytes; 1,266 paragraphs; 1 table; 124 requirements |
| Validation Plan | v1.1; SHA-256 `c6aa4edd824d6e084fd3335c22556b7dc9e86948fdce5628ae32fc05eccb2f9c`; 842,611 bytes; 145 paragraphs; 27 tables; through Section 19.9 | v1.2 proposed; SHA-256 `85dddab031aab7d2a5600fc844396474f042fa6dc2cbe5af243a23ebb504ca7d`; 847,644 bytes; 171 paragraphs; 31 tables; through Section 20.7 |
| Demonstrator Design | v0.3; SHA-256 `f2614e894dae64785ec01e0c6fbdc1e141f302608beeb3d7d07eebed3427bef5`; 849,329 bytes; 360 paragraphs; 33 tables; through Section 36.8 | v0.4 proposed; SHA-256 `b30323b93fcbc23f0f6cd76feb9a1646314051d177a8f94c54b6aac0813771e8`; 851,645 bytes; 379 paragraphs; 35 tables; through Section 37.6 |
| System Architecture | v0.2; SHA-256 `249e2370e0072cfc8324740a76a0b77647b1db2d93aef2364f4fa8b6a8a87a77`; 546,251 bytes; 311 paragraphs; 12 tables; through Section 26.5 | v0.3 proposed; SHA-256 `83bb1b5f1e224943a76e0f91ea4cc37b4e71e95016b2fbae7e668c9068e17c21`; 548,273 bytes; 325 paragraphs; 13 tables; through Section 27.4 |
| Workflow Design | v0.2; SHA-256 `f09f7e983e208b6c9f9b9f19d41d35df1b347c195e9c78fe63032d0df30b1547`; 620,162 bytes; 252 paragraphs; 31 tables; through Section 27.4 | v0.3 proposed; SHA-256 `8c0ea11d595c1b1d719f927918894797ada3cccdad15c9a36764857c7642423e`; 622,805 bytes; 266 paragraphs; 34 tables; through Section 28.5 |

## 17. Proposed design gate

DC-005 and all associated authoritative revisions remain proposed until
independent engineering review accepts them. This proposal authorises no
machine catalogue, contract, schema, database, API, frontend or test change.

If accepted, DC-005 must be applied to the five affected authoritative
artefacts, cross-document verified and incorporated into reviewed `main` before
QA-042 application resumes. QA-041 remains pending on the unchanged DC-004
application branch. PR #10 remains draft/unmerged, and I9 remains stopped until
the corrected DC-004 application is independently accepted and incorporated.

**V2 Automation Candidate — suspension evidence assessment.** Condition-specific
binding, source/hash verification, authority checks and evidence-package
assembly are repetitive and assurance-heavy. A future tool could pre-validate
the record and flag contradictions while leaving reviewer judgement and final
acceptance under engineering control.
