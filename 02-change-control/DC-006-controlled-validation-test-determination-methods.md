# DC-006 — Controlled Validation Test Determination Methods

Status: **Proposed — architecture accepted in principle; bounded DR-01–DR-06 corrections applied pending final independent engineering re-review; not accepted, not applied**

Date raised: 2026-08-11

Proposal date: 2026-08-11

Change class: Validation-assurance determination design

Origin: Accepted I9 stop during final 24-test campaign preparation

Baseline: Reviewed main `70781cad986f3700f8e2d94fd20aa8b01482f50b`

Supporting analysis: `03-derived-reference/dc-006-determination-coverage-analysis.md`

## 1. Purpose and change boundary

The accepted Validation Plan defines 24 catalogue tests, their objectives, methods, procedures, expected engineering results, evidence obligations and verdict rules. Accepted implementation currently provides an authorised structured determination path for:

- `VT-TOP-DEF-001` direct Network Configuration v1.0/v1.1 execution comparison;
- `VT-EXP-ALL-001` through the exact nine DC-004 constituent executions and composite; and
- `VT-EXP-ROLE-001` through the exact four DC-004 constituent executions and composite.

The remaining 21 definitions cannot yet create an `ExecutedValidationResult` because the accepted baseline does not define a typed determination context, exact criterion set, authoritative observation source or engineering-review finding contract. I9 stopped rather than converting implementation-conformance test success into catalogue verdicts or using a false DC-005 suspension.

DC-006 proposes one common criteria-based determination method for all catalogue tests and constituents. It changes validation-assurance design only. It does not change any network configuration, electrical state, topology, outage, customer, telemetry, DC-003 isolation, restoration, event, defect/correction, DC-004 aggregate or DC-005 suspension outcome.

This proposal does not apply authoritative Word-document changes, alter the machine catalogue, create a schema/migration/API/frontend change, resume I9 or authorise implementation.

## 2. Existing authoritative meaning retained

The following remain controlling:

- `REQ-VAL-007` — a validly compared attempt creates an `ExecutedValidationResult` recording the observed result produced by the demonstrator.
- `REQ-VAL-008` — each `ExecutedValidationResult` has exactly one `PASS` or `FAIL` based on expected-versus-observed comparison.
- `REQ-VAL-009` — sufficient evidence must justify the observed result and determination.
- A missing criterion, checkpoint, source record, evidence item or reviewer finding leaves the attempt `INCOMPLETE` and non-finalisable.
- A genuine DC-005 condition may create `BLOCKED-TEST` only through the accepted target selection, classifier, authority, evidence and immutable suspension path. It creates no `ExecutedValidationResult`.
- An expected operational `BLOCKED`, `REJECTED` or `NO_CANDIDATE` is a criterion match and validation `PASS` when all required evidence agrees.
- One operational scenario run remains bound to one validation execution wherever the test actually exercises a scenario.
- FORMAL and EXPLORATORY evidence remain separated.
- DC-004 exact constituent membership, completeness and aggregate precedence remain unchanged.
- Completed historical executions resolve/export through their stored catalogue/test/case identities; unfinished old-catalogue work is historical/read-only after promotion.
- Unit, integration, component and browser tests remain implementation-conformance evidence and never become catalogue verdict evidence merely because they pass.

## 3. Proposed design decision

### 3.1 Common determination-method definition

Every promoted catalogue test or constituent case shall own one immutable, versioned and hash-controlled `DeterminationMethodDefinition` containing:

| Field | Controlled meaning |
|---|---|
| `determination_method_id` | Stable identity scoped to the test/case. |
| `version` / `definition_sha256` | Exact method identity preserved with the catalogue/test/case definition. |
| `test_id` / optional `case_id` | Parent controlled target. |
| `evidence_class` | Inherited FORMAL or EXPLORATORY; never caller-selected. |
| `context_kind` | One exact value from Section 3.2. |
| `required_context_roles` | Exact named runs, fixtures, packages, configurations or preserved-record members required before evaluation. |
| `required_checkpoint_ids` | Exact checkpoint set where the method is scenario/checkpoint based. |
| `criteria` | Exact required set of versioned `CriterionDefinition` records. |
| `requirement_coverage` | Derived union of criterion mappings; must equal the parent test's accepted RTM requirement set. |
| `aggregate_rule` | Fixed `ALL_SATISFIED_PASS_ANY_NOT_SATISFIED_FAIL`; incomplete has no verdict. |
| `source_references` | Authoritative document/section/answer-key basis. |

The method is controlled test-definition data. A client cannot alter its contexts, criteria, expected values, evidence requirements, reviewers or aggregate rule.

### 3.2 Exact execution-context kinds

| Context kind | Contract |
|---|---|
| `SCENARIO_EXECUTION` | Exactly one actual `ScenarioRun` is bound. The method may require multiple named evidence checkpoints from that same run. |
| `CONTROLLED_FIXTURE_EXECUTION` | Exactly one immutable controlled fixture definition and one immutable fixture result are bound. No fictional scenario run is created. |
| `PRESERVED_RECORD_SET` | An exact role-labelled set of existing immutable configuration, execution, investigation, comparison, package or assurance records is bound before evaluation. Every member resolves by identity/hash. |
| `ENGINEERING_REVIEW` | One immutable review execution is bound to the exact application build and controlled evidence set. No fictional scenario run is created. |

The context kind affects source binding only. It does not create a different verdict model.

Every valid procedure execution retains one immutable `ValidationExecution` and one exact context binding. `scenario_run_id` is mandatory for `SCENARIO_EXECUTION` and absent for the other three context kinds; those contexts instead bind their fixture, record-set or review identity. This is the proposed amendment to the current scenario-only execution contract and prevents fabrication of a run for inspection, fixture or review work. DC-004 constituents remain `SCENARIO_EXECUTION` records with exactly one run each.

### 3.3 Criterion definition

Each `CriterionDefinition` shall contain:

- stable `criterion_id`, version and canonical hash;
- kind `MACHINE_COMPARISON` or `ENGINEERING_REVIEW`;
- exact `requirement_ids` allocated from the parent test's accepted RTM relationship set;
- context role and optional checkpoint ID;
- predetermined expected value or exact review proposition;
- authoritative observation source type and controlled selector;
- comparison operator and normalisation/units/rounding/set/order rules where machine-comparable;
- exact evidence categories and source references; and
- reviewer authority profile where judgement is required.

The proposed machine operator registry is deliberately small and generic:

- `SCALAR_EQUAL`;
- `NUMERIC_EQUAL` with controlled unit/rounding rule;
- `BOOLEAN_EQUAL`;
- `CANONICAL_SET_EQUAL`;
- `ORDERED_SEQUENCE_EQUAL`;
- `PRESENT` / `ABSENT`;
- `IDENTITY_HASH_AGREEMENT`; and
- `CANONICAL_RECORD_EQUAL` with a fixed definition-owned exclusion profile for generated identities.

The validator shall not calculate topology, outage, restoration, telemetry validity or customer impact independently. It resolves the preserved output of the existing authoritative backend service and compares that output with the catalogue-owned expectation.

The validator shall not select expected values or return results through a `test_id`, section ID, configuration version or case-ID outcome lookup. Test-specific meaning exists only in the controlled definition data.

### 3.3.1 Requirement-to-criterion traceability

Each criterion shall identify only requirement IDs already related to its parent `test_id` by the accepted Section 15 RTM. For each test/case determination method:

1. every criterion `requirement_id` must be a member of the parent test's accepted requirement relationship set;
2. the union of all criterion `requirement_ids` must equal the parent test's complete accepted relationship set;
3. a criterion may map to more than one applicable requirement and a requirement may map to more than one substantive criterion;
4. criterion mapping cannot add, remove or transfer a `(test_id, requirement_id)` RTM relationship; and
5. catalogue loading/finalisation must reject out-of-parent, missing-union and unknown requirement IDs.

Criterion-level mapping refines traceability beneath the accepted RTM; it does not create a new RTM layer or change the exact 124 unique requirements / 286 `(test_id, requirement_id)` relationships. The immutable result/evidence package shall retain criterion→requirement→evidence links so coverage is justified by the actual criterion findings rather than by test-ID presence alone.

### 3.4 Controlled observation-source registry

The minimum source registry shall provide typed, identity-checked adapters for:

- application build manifest;
- immutable configuration package/manifest/schema;
- configuration comparison result;
- scenario checkpoint/evidence snapshot;
- topology/source-attribution/isolation result;
- outage/customer-impact result;
- telemetry validity result;
- restoration assessment/calculation/action projection;
- alarm/operational-event set;
- validation attempt/execution/result/evidence record set;
- investigation/defect/correction/repeat/regression chain;
- immutable controlled fixture definition/result;
- evidence-package verification result and archive manifest; and
- engineering-review record.

An adapter verifies source identity, ownership, configuration/build/run/definition binding, canonical payload hash and evidence class before exposing a controlled observed value. It may not reconstruct historical evidence from current mutable state.

### 3.5 Machine criterion finding

A machine finding records:

- criterion and determination-method identities/hashes;
- resolved source record identity/hash and context role/checkpoint;
- canonical expected and observed values;
- operator/normalisation version;
- `SATISFIED` or `NOT_SATISFIED`;
- deterministic reason code/parameters; and
- evaluating service/module and actual application build.

The caller supplies neither observed value nor finding. A source-integrity or identity failure is handled by the existing DC-005 classifier when its exact evidence contract is satisfied; a validly observed engineering mismatch is `NOT_SATISFIED` and ultimately `FAIL`.

### 3.6 Reviewer criterion finding

Engineering review is permitted only where the accepted method requires judgement rather than a backend field comparison. Each review criterion shall state an exact proposition and required evidence. V1 shall enforce:

1. a controlled local proposer actor/role records the candidate criterion finding and evidence references;
2. a different eligible Independent Engineering Reviewer actor finalises the finding;
3. the reviewer may choose only `SATISFIED` or `NOT_SATISFIED` for that fixed criterion;
4. the reviewer cannot alter expected meaning, evidence class, test/method identity, aggregate rule or overall verdict;
5. evidence membership, proposition, finding, actors, reason and hashes freeze atomically; and
6. optional notes remain subordinate and cannot change the finding or verdict.

This is bounded local role/actor control, not authentication of a real person or cryptographic proof of organisational independence. Independent engineering review remains responsible for confirming that the controlled identities represent distinct reviewers.

### 3.7 Completeness and deterministic PASS/FAIL

An attempt is finalisable only when:

- the active/historical catalogue, test/case and method resolve by exact stored identity;
- the context kind and exact required context roles resolve;
- every required checkpoint exists where applicable;
- the exact criterion set appears once each;
- every machine finding resolves its source and every review finding has final authority;
- every evidence/provenance link agrees; and
- no prior final result/suspension exists.

The determination is then fixed:

- any missing/unresolved/unfinalised required item → `INCOMPLETE`, no verdict and no `ExecutedValidationResult`;
- complete plus at least one `NOT_SATISFIED` → immutable `ExecutedValidationResult = FAIL`;
- complete plus every criterion `SATISFIED` → immutable `ExecutedValidationResult = PASS`.

The backend derives the overall result. No API or interface accepts an overall PASS/FAIL selection.

## 4. Exact treatment of the 24-test catalogue

The detailed criterion analysis in the supporting derived record is proposed as the normative drafting basis for the authoritative Validation Plan amendment. The controlled allocation is:

### 4.1 Existing supported paths retained

| Test | Treatment |
|---|---|
| `VT-TOP-DEF-001` | Existing Network Configuration v1.0/v1.1 structured comparison is expressed through machine criteria without changing 400/FAIL, 850/PASS, one-run provenance or immutable repeat links. Historical execution identity remains separately bound to its source Validation Catalogue revision. |
| `VT-EXP-ALL-001` | Existing exact nine cases are expressed through case machine criteria; DC-004 composite semantics remain unchanged. |
| `VT-EXP-ROLE-001` | Existing exact four cases are expressed through case machine criteria; DC-004 composite semantics remain unchanged. |

### 4.2 Proposed context allocation for the 21 stopped tests

| Context | Tests |
|---|---|
| `SCENARIO_EXECUTION` | `VT-TOP-NORMAL-001`, `VT-FML-N0-N5-001`, `VT-RST-ISOLATION-001`, `VT-RST-SOURCE-001`, `VT-RST-BINDING-001`, `VT-ALM-EVT-001` |
| `CONTROLLED_FIXTURE_EXECUTION` | `VT-TEL-FRESH-001`, `VT-TEL-STALE-001`, `VT-TEL-UNCERTAIN-001`, `VT-TEL-BAD-001`, `VT-TEL-FUTURE-001`, `VT-RST-RADIAL-001`, `VT-RST-CAP-EQUAL-001`, `VT-RST-CAP-OVER-001` |
| `PRESERVED_RECORD_SET` | `VT-CFG-BASE-001`, `VT-CFG-INV-001`, `VT-VAL-RECORD-001`, `VT-EXP-SEPARATION-001`, `VT-DET-REPEAT-001`, `VT-PKG-EVIDENCE-001` |
| `ENGINEERING_REVIEW` | `VT-NFR-REVIEW-001` |

`VT-CFG-INV-001` uses the record-set context but contains one independently finalised reviewer criterion. `VT-NFR-REVIEW-001` contains both machine and reviewer criteria under one review execution.

### 4.3 Exact N0–N5 rule

`VT-FML-N0-N5-001` shall remain exactly one FORMAL validation execution bound to one `ScenarioRun` using corrected Network Configuration v1.1 under the future promoted DC-006 Validation Catalogue revision. It shall own the six accepted N0–N5 state checkpoints plus the accepted controlled-time/event-order criterion. The exact chronology is T+0 N0 initial state; T+10 fault/protection trip to N1; T+11 alarm acknowledgement; T+20 first isolation action; T+30 N2 after the second isolation action; T+40 N3; T+50 N4; and T+55 N5. T+11 acknowledgement is chronology/alarm/event evidence within the same execution, not a seventh N-state or checkpoint. The backend derives one overall result only after every required checkpoint criterion is complete.

It is prohibited to:

- create six fictional catalogue tests;
- create six unrelated validation executions;
- create separate runs merely to obtain a verdict per N-state;
- select only successful checkpoints; or
- substitute implementation test success for the preserved scenario/evidence records.

### 4.4 Exact fixture boundary

A `CONTROLLED_FIXTURE_EXECUTION` is permitted only for a fixture already authorised by the Validation Plan: exact telemetry ages/qualities/time authority, proposed energised-loop vector, capacity equality/overage or another explicitly accepted lower-level rule-boundary vector. It shall record the fixture definition/version/hash, executing build, input values/units, authoritative service output and canonical result hash. The deterministic alternate-source negative remains a scenario execution under Section 4.2.

It shall not mutate the canonical Network Configuration v1.0/v1.1 packages, create a free-form network/load editor or allow arbitrary validation values.

### 4.5 Exact deterministic-repeat member roles

To remove the current undefined word “selected,” the proposal fixes `VT-DET-REPEAT-001` to these three required repeat-pair roles:

- `DET-FORMAL`: two completed `VT-FML-N0-N5-001` executions under equal controlled inputs;
- `DET-NEGATIVE`: two completed `VT-TEL-STALE-001` controlled fixture executions under equal controlled inputs; and
- `DET-CORRECTED`: two completed `VT-TOP-DEF-001` executions using corrected Network Configuration v1.1 under the same future promoted DC-006 Validation Catalogue/test/method identities and equal controlled inputs.

Each pair must have distinct generated identities, explicit repeat linkage, equal build/configuration/test/method/fixture/clock inputs and canonically equal engineering outputs/checkpoints after excluding only definition-authorised generated identity fields.

Independent design review accepts these three deterministic-repeat roles subject to the explicit Network Configuration / Validation Catalogue namespace clarification above. They remain proposed, not authoritative, until DC-006 receives final design acceptance and later controlled application.

### 4.6 Exact evidence-package member roles

To remove the current undefined phrase “two executions,” the proposal fixes `VT-PKG-EVIDENCE-001` to:

- `PKG-FORMAL`: one finalised `VT-FML-N0-N5-001` PASS using corrected Network Configuration v1.1 under the future promoted DC-006 Validation Catalogue/test/method identity; and
- `PKG-HISTORICAL-DEFECT`: one preserved `VT-TOP-DEF-001` FAIL using defective Network Configuration v1.0, resolved/exported under the exact historical Validation Catalogue/test-definition identity stored on that failed execution.

The test verifies distinct non-overwriting package identities/paths, required content, canonical JSON and relative links, file/manifest/archive hashes, source/build/config/test provenance, source-build versus generation-build separation, historical resolution and immutability of the first package/source records after the second export.

Independent design review accepts these package roles subject to the explicit Network Configuration / Validation Catalogue namespace clarification above. They remain proposed, not authoritative, until DC-006 receives final design acceptance and later controlled application. Composite and suspension export controls remain separate regression requirements and are not silently substituted for these two package roles.

### 4.7 Exact operational-event registry criterion

`VT-ALM-EVT-001` shall contain separate machine criteria that:

1. prove the controlled operational-event registry is exactly the canonical set `{SCENARIO_INITIALISED, CONFIGURATION_SELECTED, FAULT_INITIATED, TELEMETRY_UPDATED, DEVICE_STATE_CHANGE, ALARM_GENERATED, ALARM_ACKNOWLEDGED, SWITCHING_ACTION, TOPOLOGY_RECALCULATED, OUTAGE_UPDATED, RESTORATION_CANDIDATE_IDENTIFIED, RESTORATION_NO_CANDIDATE, RESTORATION_ASSESSED, RESTORATION_ASSESSMENT_INVALIDATED, SCENARIO_RESET}` with no missing or additional ID;
2. prove every emitted operational event in the controlled execution is a member of that exact registry;
3. prove equal-time command/derived chronology through event sequence;
4. prove every simulated isolation/restoration switching action is represented; and
5. prove validation verdict, defect, correction, composite, suspension and evidence-package records are absent from the operational event stream.

Registry equality is distinct from emitted-event membership: a run need not emit every event type, but the controlled registry itself must remain exactly 15 IDs.

### 4.8 Exploration-separation evidence boundary

`VT-EXP-SEPARATION-001` shall use the actual campaign exploratory executions/evidence and DC-004 composite records to prove that EXPLORATORY activity cannot satisfy or alter FORMAL progress. It shall not create, insert or require an exploratory DC-005 suspension as a campaign member. If a legitimate exploratory suspension already exists through the independent accepted DC-005 path, it may be retained as additional evidence only.

Implementation-conformance regression shall continue to prove that exploratory suspension records cannot affect FORMAL progress, but such regression success is not catalogue campaign verdict evidence and cannot be substituted for the required campaign exploratory execution/evidence and composite records.

### 4.9 Machine/reviewer judgement boundary

For `VT-NFR-REVIEW-001`, machine criteria may prove only controlled facts such as label/notice presence, identity fields and resolvable links, structural separation, loopback-only configuration/no external operational endpoint, and use of common entity schemas. Machine comparison shall not determine whether a presentation is prominent, understandable, clear, engineering-first or not misleading.

Those subjective propositions shall be fixed, versioned, evidence-bound `ENGINEERING_REVIEW` criteria. An eligible independent reviewer records only `SATISFIED` or `NOT_SATISFIED` for each exact proposition; the backend retains sole authority to derive the overall PASS/FAIL result under Section 3.6.

## 5. DC-004 interaction

DC-004 remains controlling for `VT-EXP-ALL-001` and `VT-EXP-ROLE-001`:

- exact nine/four case sets;
- one run and one execution per constituent;
- constituent-owned controlled scenario time;
- exact completeness and provenance gates;
- incomplete/no-verdict treatment for missing, duplicate or mismatched cases;
- aggregate FAIL precedence; and
- immutable composite/history/export rules.

DC-006 supplies the common constituent criterion/finding representation and does not create a multi-run `ValidationExecution` or a second composite engine.

## 6. DC-005 interaction

DC-005 remains the only route to `BLOCKED-TEST`:

- criterion mismatch with complete trustworthy evidence is `NOT_SATISFIED` and yields `FAIL`;
- missing ordinary evidence/finding/context is `INCOMPLETE`;
- expected operational BLOCKED/REJECTED/NO_CANDIDATE can satisfy a criterion and yield `PASS`;
- a genuine accepted VSC condition may suspend only under the existing trusted target, classifier precedence, condition evidence, authority, deterministic reason and immutable record; and
- a suspended attempt has no `ExecutedValidationResult`.

Criterion definitions and findings become additional bound source/evidence roles for DC-005 provenance checking; they do not add a sixth condition or change classifier precedence.

## 7. Persistence, immutability and history

Future controlled application shall separate and immutably store:

- determination-method definitions and criterion definitions in accepted catalogue packages;
- execution-context bindings and exact role-labelled membership;
- machine criterion findings;
- reviewer proposals/final findings/authority audit;
- aggregate completeness diagnostics; and
- `ExecutedValidationResult` with the exact criterion-finding/evidence membership used.

Database-level controls shall reject update/delete of final method-bound results and findings, criterion replacement, evidence/member insertion/removal/replacement after finalisation and overall-result override.

A repeat creates new attempt/context/finding/result identities. Historical resolution follows DC-004/DC-005 and never relabels an old result under a new criterion definition.

## 8. Catalogue revision and promotion gate

DC-006 requires a new controlled catalogue revision because context kinds, exact criteria, expected values/selectors, reviewer authority and member/checkpoint roles are test-definition meaning.

Before any later promotion:

1. preserve the exact accepted active Validation Catalogue v1.1 and manifest as immutable historical input:
   - catalogue SHA-256 `28bfe69131c40857c08f175abba42be3eb36514924b6de416b4e72bbefe35865`;
   - manifest SHA-256 `45cb015f58af1d453be0255cdbbb857c08901877c416e830f26bb2fe6ecf60a3`;
2. retain historical Validation Catalogue v1.0 byte-identically;
3. promote the criteria-based package as the next accepted revision only after authoritative document application and independent machine/application review;
4. bind new attempts to the promoted identity;
5. retain completed Validation Catalogue v1.0/v1.1 review/export through original identities while separately preserving each execution's Network Configuration identity; and
6. enforce historical/read-only treatment for unfinished older definitions.

The catalogue remains exactly 24 tests with the same 124 requirements and exact 286 RTM relationships unless independent review identifies a genuine contradiction. No such contradiction was found in this investigation.

## 9. Authoritative artefact impact

| Artefact | Proposed controlled amendment | Version if later applied |
|---|---|---|
| Requirements Specification | No amendment. Existing `REQ-VAL-003`, `REQ-VAL-006–009` are sufficient. Requirement count remains 124. | Remains v0.4. |
| Validation Plan | Add Section 21 defining the common method/context/criterion/finding/aggregate model; add exact criteria matrices for all 24 tests; fix N0–N5 as one execution/six checkpoints; accept the exact repeat/package roles; define catalogue-history gate. | Proposed v1.3. |
| System Architecture | Add Section 28 allocating method/criterion ownership, typed source adapters, context membership, machine evaluation, reviewer authority, deterministic aggregation and optional/non-fictional run relationships to Validation/Evidence. | Proposed v0.4. |
| Workflow Design | Add Section 29 for target/method resolution, context creation, checkpoint/fixture/record-set/review evidence, criterion finding, incomplete handling, independent review finalisation, aggregate result and DC-004/DC-005 branches. | Proposed v0.4. |
| Demonstrator Design | Add Section 38 for contracts, persistence/immutability, API/actions/read models, review screen treatment, generic selectors/operators, history/export and future implementation increments/gates. | Proposed v0.5. |
| Engineering Design Brief | No change. | Remains v0.4. |
| Network Model | No change. | Remains v0.4. |
| DC-004 / DC-005 | No change to accepted semantics; add cross-reference during later administrative application only if review requires it. | Existing records retained. |
| Derived control/source-map/manifests | Update only after accepted authoritative application and again after separately reviewed machine application. | Future controlled administration. |

No authoritative Word document is amended by this proposal.

## 10. Future application boundary — not authorised

If DC-006 is independently accepted and later applied to the authoritative artefacts, a separate application phase would be expected to change only validation assurance:

- preserve Validation Catalogue v1.1 catalogue/manifest as historical input;
- promote the accepted criteria-based catalogue revision;
- add criterion/method/context contracts and resolver validation;
- add controlled fixture/record-set/review context records;
- add generic source adapters/operator registry;
- add machine and reviewer finding persistence/immutability;
- add deterministic aggregate and incomplete diagnostics;
- extend validation/evidence review and export; and
- run focused/history/full-regression verification before independent review.

It must not change topology, outage, restoration, telemetry, DC-003, network packages, operational events or I9 packaging behaviour. I9 remains stopped until both authoritative application and machine/application review are separately accepted into main.

## 11. Proposed verification obligations

Future design/application verification shall prove at minimum:

1. exact criterion sets and definition hashes are loaded from controlled catalogue data;
2. no production `test_id`/section/outcome lookup manufactures observations or verdicts;
3. each context kind binds only its exact permitted source roles;
4. scenario contexts bind exactly one run and `VT-FML-N0-N5-001` finalises once from all six checkpoints;
5. fixture contexts create no fictional run and cannot mutate canonical packages;
6. record-set contexts reject missing, duplicate, wrong-role, wrong-build, wrong-definition and cross-run/source mixing;
7. machine observations come from authoritative preserved backend records;
8. reviewer criteria use fixed propositions, evidence and distinct eligible actors, while the backend derives the overall result;
9. incomplete evidence/finding/context produces no verdict/result;
10. complete any-mismatch produces FAIL and complete all-satisfied produces PASS;
11. expected operational negative outcomes produce PASS when criteria agree;
12. DC-005 remains the exclusive `BLOCKED-TEST` route and ordinary missing evidence remains incomplete;
13. DC-004 exact 9/4 cases/composites and FORMAL isolation remain unchanged;
14. historical Validation Catalogue v1.0/v1.1 definitions/results remain resolvable/exportable after promotion with their separate Network Configuration identities unchanged;
15. unfinished older executions are read-only;
16. final findings/membership/results are database-immutable;
17. deterministic repeat uses the exact accepted member roles and equality profile;
18. package integrity uses the exact accepted package roles and verifies source/generation provenance;
19. each criterion's requirement mapping is a subset of its parent test mapping and each test's criterion union exactly covers that mapping;
20. Exploration separation uses actual campaign exploratory execution/evidence and DC-004 composite records without manufacturing a suspension;
21. machine criteria do not decide subjective NFR review qualities;
22. the operational-event registry equals the exact 15 IDs and emitted events are separately checked for registry membership;
23. implementation-conformance test success cannot be imported as a catalogue verdict; and
24. 24 tests, 124 requirements, 286 RTM relationships and 15 operational-event types remain exact.

## 12. Proposal gate

Current disposition: **Architecture accepted in principle; DR-01–DR-06 corrected; proposed pending final independent engineering design re-review.**

Independent review has accepted, in principle, the four-context/common-criteria architecture, deterministic backend aggregate, DC-004/DC-005 boundaries, historical catalogue treatment, authoritative artefact impact and the exact deterministic-repeat/evidence-package roles subject to version-namespace clarification. Final design re-review is requested only to confirm the bounded corrections recorded in Sections 3.3.1 and 4.3–4.9 and the corresponding supporting coverage analysis.

No acceptance, document application, catalogue promotion, code/schema/migration/UI change, I9 resumption or merge is authorised by this proposal.

## V2 Automation Candidate

**V2 Automation Candidate — evidence-to-criterion binding and review preparation.** The controlled source adapters and criteria make evidence completeness mechanically checkable; a future assurance assistant could propose candidate bindings and highlight gaps while V1 retains fixed expectations, immutable evidence, independent reviewer findings and backend-derived verdicts.
