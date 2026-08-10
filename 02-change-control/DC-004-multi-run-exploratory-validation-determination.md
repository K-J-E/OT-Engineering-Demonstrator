# DC-004 — Multi-Run Exploratory Validation Determination

Status: Proposed / core architecture accepted in substance; bounded correction pending final independent review

Date raised: 2026-08-10

Proposal date: 2026-08-10

Change class: Validation-assurance design clarification

Origin: I9 explicit stop condition during pre-implementation source review

## 1. Purpose

The accepted catalogue contains two tests whose controlled evidence spans more
than one exploratory scenario run:

- `VT-EXP-ALL-001` verifies all eight selectable sections and a separate
  untrustworthy-last-reported-OPEN case; and
- `VT-EXP-ROLE-001` verifies four representative restoration outcomes and
  feeder-role arrangements.

The accepted I5 record model correctly binds one `ValidationExecution` to one
`ScenarioRun`. The accepted baseline did not define how separately preserved
constituent executions become one catalogue-level determination. I9 therefore
stopped before implementation or campaign execution rather than weakening
single-run provenance or inventing an aggregate verdict.

This proposed change defines stable constituent cases and a separate immutable
composite result. It does not create a multi-run `ValidationExecution` and does
not change any electrical, topology, outage, restoration or workflow outcome.

## 2. Existing baseline retained

- One `ValidationExecution` remains bound to exactly one `scenario_run_id`.
- Each constituent run is `EXPLORATION`, evidence class `EXPLORATORY`, uses the
  corrected immutable Network Configuration v1.1 and records the actual
  backend-controlled application build.
- Every constituent execution and evidence snapshot remains independently
  reviewable and immutable.
- Expected values are fixed by the accepted Validation Plan/Network Model
  oracle before execution and are never written into operational result data.
- Case comparison uses the generic expected-versus-observed validation
  mechanism, extended only to expose the approved structured fields required
  by the case definition.
- FORMAL validation progress excludes every constituent and composite record
  created under this change.
- The operational-event catalogue remains exactly 15 types. Constituent
  determinations and composite results are validation-assurance records, not
  operational events.
- I8 per-execution evidence ZIP behaviour remains unchanged.
- Every accepted validation catalogue revision is an immutable historical
  engineering input. A later accepted revision does not replace the package or
  identity needed to resolve an earlier execution.

## 3. Constituent-case definition and execution binding

A controlled multi-run test definition shall own an exact, versioned set of
`ConstituentCaseDefinition` records. Each record contains at minimum:

| Field | Controlled meaning |
|---|---|
| `case_id` | Stable ID unique within the catalogue test. |
| `test_id` | Parent catalogue test ID. |
| `case_title` | Human-readable controlled case name. |
| `selected_fault_section_id` | Transient run input fixed before initialisation. |
| `initial_conditions` | Controlled telemetry/topology conditions needed by the case. |
| `comparison_expected_values` | Case-specific structured oracle fixed before execution. |
| `checkpoint_obligations` | Evidence categories and named checkpoint(s) required before finalisation. |

Starting a constituent execution requires `test_id`, `case_id` and one
`scenario_run_id`. The validation authority verifies that the case belongs to
the named test and binds the immutable execution to the current case-definition
version/hash. The execution stores the case-specific expected values before
evidence capture. Its execution and evidence records identify `case_id`.

The same `(test_id, case_id)` may be executed again only as a new run and a new
execution. A repeat does not replace the earlier execution.

### 3.1 Engineering expectations versus provenance invariants

`comparison_expected_values` contains only predetermined engineering/case
expectations from the accepted oracle. Applicable fields include selected fault
section, affected/alternate feeder, protection breaker, canonical incident
boundary set, telemetry value/quality/freshness/proof/action state,
isolation result, restoration candidate/transfer sections, load, capacity,
loading percentage and operational outcome.

Dynamic identities are not ordinary expected-versus-observed engineering
fields. `application_build_id`, catalogue identity/hash, test-definition
identity/hash and case-definition identity/hash are separately validated
provenance/binding invariants. Scenario mode, evidence class and corrected v1.1
configuration identity/version are also execution preconditions/provenance
gates. The composite finalisation rule may require these identities to agree
across constituents, but their agreement is not an engineering comparison
result.

## 4. Exact `VT-EXP-ALL-001` constituent cases

The required case set contains exactly nine case IDs. Boundary ID sets are
compared canonically without relying on presentation or iteration order.

| Case ID | Controlled run input | Required structured comparison |
|---|---|---|
| `EXP-ALL-A1` | Fault `SEC-A1` | affected `FDR-A`; protection breaker `BRK-A`; incident boundaries `{BRK-A, SW-A12}`. |
| `EXP-ALL-A2` | Fault `SEC-A2` | affected `FDR-A`; protection breaker `BRK-A`; incident boundaries `{SW-A12, SW-A23}`. |
| `EXP-ALL-A3` | Fault `SEC-A3` | affected `FDR-A`; protection breaker `BRK-A`; incident boundaries `{SW-A23, SW-A34}`. |
| `EXP-ALL-A4-FRESH` | Fault `SEC-A4`; `TS-01` last value `OPEN`, quality `GOOD`, age within 60,000 ms | affected `FDR-A`; protection breaker `BRK-A`; incident boundaries `{SW-A34, TS-01}`; `TS-01` freshness `FRESH`; proof `PROVEN_OPEN`; `open_action_eligible = false`; overall isolation remains false until every boundary and zero-source-path condition is satisfied. |
| `EXP-ALL-B1` | Fault `SEC-B1` | affected `FDR-B`; protection breaker `BRK-B`; incident boundaries `{BRK-B, SW-B12}`. |
| `EXP-ALL-B2` | Fault `SEC-B2` | affected `FDR-B`; protection breaker `BRK-B`; incident boundaries `{SW-B12, SW-B23}`. |
| `EXP-ALL-B3` | Fault `SEC-B3` | affected `FDR-B`; protection breaker `BRK-B`; incident boundaries `{SW-B23, SW-B34}`. |
| `EXP-ALL-B4` | Fault `SEC-B4` | affected `FDR-B`; protection breaker `BRK-B`; incident boundaries `{SW-B34, TS-01}`. |
| `EXP-ALL-A4-STALE-OPEN` | Separate `SEC-A4` run; `TS-01` last value `OPEN`, quality `GOOD`, age 60,001 ms | affected `FDR-A`; protection breaker `BRK-A`; incident boundaries `{SW-A34, TS-01}`; observed value `OPEN`; freshness `STALE`; proof `UNPROVEN`; `open_action_eligible = false`; overall isolation `false`; evidence-deficiency reason identifies stale telemetry. |

Every case also compares its predetermined `selected_fault_section_id`.
`scenario_mode = EXPLORATION`, `evidence_class = EXPLORATORY`, corrected
configuration identity/version 1.1, application build identity,
test-definition identity and case-definition identity are validated separately
as provenance/binding invariants under Section 3.1.

The stale case is deliberately one deterministic stale boundary: `GOOD` value
quality with age 60,001 ms. Other DC-003 untrustworthy states remain covered by
the existing lower-level telemetry/isolation regression suite; they are not
additional required composite constituents.

## 5. Exact `VT-EXP-ROLE-001` constituent cases

The required case set contains exactly four case IDs. Numerical quantities use
integer kW in canonical records and the accepted one-decimal percentage for
review presentation/comparison.

| Case ID | Controlled expected comparison |
|---|---|
| `EXP-ROLE-A2` | selected fault `SEC-A2`; affected `FDR-A`; alternate `FDR-B`; proposed sections `{SEC-A3, SEC-A4}`; transferable load 1,500 kW; resulting load 5,700 kW; capacity 6,000 kW; loading 95.0%; outcome `PERMITTED`. |
| `EXP-ROLE-B2` | selected fault `SEC-B2`; affected `FDR-B`; alternate `FDR-A`; proposed sections `{SEC-B3, SEC-B4}`; transferable load 1,900 kW; resulting load 5,100 kW; capacity 5,500 kW; loading 92.7%; outcome `PERMITTED`. |
| `EXP-ROLE-A1` | selected fault `SEC-A1`; affected `FDR-A`; alternate `FDR-B`; proposed sections `{SEC-A2, SEC-A3, SEC-A4}`; transferable load 2,450 kW; resulting load 6,650 kW; capacity 6,000 kW; loading 110.8%; outcome `REJECTED`. |
| `EXP-ROLE-A4` | selected fault `SEC-A4`; affected `FDR-A`; no restoration candidate; no transferable group/calculation; outcome `NO_CANDIDATE`. |

Every case additionally compares its selected fault and the case-specific
engineering fields in the table. `scenario_mode = EXPLORATION`,
`evidence_class = EXPLORATORY`, corrected v1.1 configuration identity, the
backend-controlled build identity and the bound test/case-definition identities
are separate provenance/binding invariants under Section 3.1.
`REJECTED` and `NO_CANDIDATE` are expected operational results and therefore
produce a case-level validation `PASS` when all expected fields and mandatory
evidence agree.

## 6. Immutable composite validation-assurance result

The catalogue-level result is a separate `CompositeValidationResult`; it is not
a `ValidationExecution`, scenario run, operational event or replacement for a
constituent record.

| Field | Minimum controlled content |
|---|---|
| Identity | `composite_result_id`; optional administrative `created_at`/`finalised_at` audit timestamps, explicitly not engineering scenario time. |
| Definition | `test_id`, test-definition version/hash and catalogue hash. |
| Classification | `evidence_class = EXPLORATORY`. |
| Provenance | One backend-controlled `application_build_id`; corrected configuration ID/version. |
| Required set | Exact ordered/canonical list of required `case_id` values from the bound definition. |
| Constituent links | For each case: `case_id`, `validation_execution_id`, `scenario_run_id`, case-definition hash and constituent verdict. |
| Completeness | Present/missing/duplicate/mismatched case diagnostics and `INCOMPLETE` or `COMPLETE`. |
| Determination | `PASS`, `FAIL` or `BLOCKED-TEST` only after finalisation. |
| Basis | Deterministic reason and immutable evidence/source-record references. |

An incomplete draft/assembly record may be queried for review, but it has no
validation verdict and does not count as an accepted catalogue execution.
The composite owns no authoritative scenario time. Each constituent retains
its own controlled scenario/run/checkpoint time through its execution and
evidence links. Any composite creation/finalisation timestamp is administrative
audit metadata only and shall not participate in the engineering comparison or
aggregate determination.

## 7. Aggregate determination rule

### 7.1 Finalisation preconditions

A composite is finalisable only when:

1. the constituent IDs equal the exact required case set;
2. every required case appears exactly once in the accepted constituent set;
3. every constituent execution is finalised;
4. every constituent retains the same parent test ID, test-definition
   version/hash and catalogue hash;
5. every constituent records the same backend-controlled final application
   build;
6. every constituent uses the same corrected configuration ID/version;
7. every run is `EXPLORATION` with `EXPLORATORY` evidence;
8. every execution/run/evidence/case link resolves and agrees in both
   directions; and
9. no constituent is already assigned to that composite under a different
   case ID.

For this rule, a finalised constituent may carry `PASS`, `FAIL` or
`BLOCKED-TEST`. A `BLOCKED-TEST` constituent is valid only when it records the
named accepted entry/suspension condition and its supporting evidence. A case
that has no finalised execution is missing/unexecuted, not blocked.

Missing, unexecuted, duplicate or mismatched cases keep the composite
`INCOMPLETE` with no verdict. They are not silently converted to
`BLOCKED-TEST`.

### 7.2 Verdict

- `PASS` iff the composite is complete and every constituent verdict is
  `PASS`.
- `FAIL` iff the composite is complete and at least one constituent verdict is
  `FAIL`, regardless of whether another constituent is `BLOCKED-TEST`.
- `BLOCKED-TEST` iff the composite is complete, no constituent is `FAIL`, at
  least one constituent is validly `BLOCKED-TEST`, every other constituent is
  `PASS`, and the named accepted entry/suspension condition and supporting
  evidence are preserved. It is not a substitute for a missing or unfinished
  case.

Finalisation derives the result once from preserved constituent records. It
never reconstructs a scenario from current mutable state.

## 8. Persistence, immutability and repeat treatment

- Constituent-case definitions are hash-controlled parts of the affected test
  definitions.
- Composite result, constituent membership and case links are inserted and
  finalised through controlled repository operations.
- Database-level guards reject update/delete of a finalised composite and
  insertion/deletion/replacement of its constituent links.
- A corrected or repeated campaign creates a new composite ID and new run,
  execution and evidence IDs. Earlier complete or incomplete records remain
  reviewable.
- Equivalent deterministic reruns may have different generated identities but
  must produce equivalent engineering results, comparisons and aggregate
  determination under the same controlled inputs.

## 9. Review presentation and export

The validation/evidence review model shall show, without collapsing provenance:

- parent test identity and aggregate determination;
- exact required/present/missing case IDs;
- each case ID, execution ID, run ID, case verdict and evidence link;
- common build/configuration/catalogue/test identities;
- FORMAL/EXPLORATORY classification; and
- completeness/finalisation reasons.

I8 per-execution ZIP content/immutability semantics remain unchanged. Historical
catalogue resolution is extended as specified in Section 9.1 so an execution is
exported with its own original source catalogue/test definition rather than the
currently active definition. If a catalogue-level package is requested, it is
generated only from a finalised immutable composite and its preserved
constituent records/evidence. The package contains the composite record and
every linked constituent identity; it does not reconstruct live state. It is
labelled `EXPLORATORY` and cannot satisfy FORMAL progress.

### 9.1 Historical catalogue and test-definition resolution

Accepted validation catalogue revisions are immutable historical engineering
inputs. Before promoting the DC-004 catalogue revision, controlled application
shall preserve the exact accepted machine-readable catalogue v1.0 package and
its manifest/hash as independently resolvable historical input. The exact
filesystem or repository layout is deferred to bounded implementation design;
convenience shall not determine or weaken the identity invariant.

- New executions resolve and bind to the current accepted catalogue revision.
- Historical review/export resolves an execution-bound source catalogue and
  test definition using the identities stored on the execution, principally
  catalogue version/hash plus test-definition version/hash. It does not require
  equality with the currently active catalogue.
- A finalised historical execution remains readable, reviewable and exportable
  after catalogue promotion, including when its individual test definition did
  not change between catalogue revisions.
- An unfinished execution bound to an older catalogue/definition becomes
  historical read-only after promotion. It shall not capture further evidence
  or be continued/finalised against the newer definition; a new execution is
  required under the active accepted catalogue.
- An evidence package generated after promotion records the original source
  catalogue/test-definition identity separately from the generation
  application-build identity. It never relabels old evidence as originating
  from the new catalogue.
- Existing already-generated evidence ZIPs and immutable package records remain
  valid and unchanged.

## 10. Traceability and controlled identity impact

- Catalogue test count remains **24**.
- Formal requirement count remains **124**.
- The accepted RTM remains exactly **286** `(test_id, requirement_id)` pairs.
- Requirements Specification wording and verification methods do not change.
- Network Model, topology/outage/restoration behaviour, DC-003 and the
  immutable v1.0/v1.1 packages do not change.
- `VT-EXP-ALL-001` and `VT-EXP-ROLE-001` definition versions, the catalogue
  version/hash and manifest hash will change only after independent acceptance
  and controlled machine-readable application.
- Old and new definition/catalogue identities must be recorded explicitly;
  historical executions remain bound to their original identities.
- The accepted machine-readable catalogue v1.0 plus its manifest/hash remains
  preserved and independently resolvable after the DC-004 revision is promoted.
- Historical export records the execution-bound source catalogue/test
  definition separately from the later generation application build.

## 11. Authoritative artefact impact assessment

| Artefact | Proposed treatment | Behaviour impact |
|---|---|---|
| Validation Plan | Add stable case definitions, case comparisons, composite completeness/verdict rules, evidence/exit treatment and verification cases. | Validation-assurance clarification only. |
| Demonstrator Design | Add constituent/composite records, catalogue-revision resolver, ownership, persistence/immutability, review projection and optional composite export boundary. | Application/evidence design clarification only. |
| Requirements Specification | No change. Existing requirements remain allocated through unchanged RTM relationships. | None. |
| Network Model | No change. All case expectations already exist in Sections 12 and 18 or the accepted Validation Plan answer key. | None. |
| System Architecture / Workflow Design | No proposed wording change after impact review; existing validation/evidence ownership and deterministic workflow boundaries remain sufficient when read with the Demonstrator Design amendment. | None. |
| Machine catalogue/contracts/schema | Deferred until DC-004 is independently accepted. Controlled application must preserve accepted catalogue v1.0 and add identity-based historical definition resolution before promoting the new revision. | Future bounded implementation work. |
| Manifests/source map/baseline aids | Record proposed status now; update controlled identities only after acceptance/application. | Administrative only. |

## 12. Future implementation areas

After independent acceptance and separate implementation authorisation, the
bounded impact is expected in:

- validation catalogue schema/loader for case definitions and hashes;
- immutable accepted-catalogue revision preservation and an identity-based
  historical catalogue/test-definition resolver;
- validation execution start/finalise contracts for `case_id` and case-bound
  expected values;
- observed-value projection for the approved topology/isolation/restoration
  comparison fields;
- SQLite migrations/repository for composite records and immutable constituent
  links;
- validation service for generic case comparison and composite completeness;
- workspace/evidence read models and review presentation;
- optional composite evidence-package assembly from preserved records;
- evidence export resolution that separates the execution-bound source
  catalogue/test-definition identity from the generation application build;
- historical read-only enforcement for unfinished old-catalogue executions;
- separate validation of engineering comparison fields and dynamic provenance
  identities; and
- focused unit, persistence, API, component and browser/campaign tests.

No topology, outage, restoration, event or scenario electrical algorithm is in
scope.

## 13. Proposed verification cases

Future implementation verification shall prove:

1. all nine `VT-EXP-ALL-001` cases are separately run, preserved and compared;
2. all four `VT-EXP-ROLE-001` cases are separately run, preserved and compared;
3. the exact complete passing set yields aggregate `PASS`;
4. one constituent `FAIL` in a complete set yields aggregate `FAIL`;
5. a missing or unexecuted case remains incomplete with no verdict;
6. a duplicate case is rejected/not finalisable;
7. wrong build, configuration, test-definition, catalogue, mode or evidence
   class is rejected/not finalisable;
8. constituent execution/run/evidence provenance remains independently
   reviewable;
9. exploratory composite records do not affect FORMAL progress;
10. finalised composite and membership records reject update/delete/late link
    insertion at database level;
11. a composite export retains every constituent link and verifies its hashes;
12. a deterministic rerun creates new identities but equivalent engineering,
    comparison and aggregate results; and
13. the catalogue remains 24 tests, the RTM remains 124 requirements and 286
    exact relationships, and the operational-event catalogue remains 15 types.
14. an execution created/finalised under catalogue v1.0 remains reviewable after
    promotion of the controlled DC-004 catalogue revision;
15. the historical resolver returns the exact original v1.0 catalogue and test
    definition by the identities stored on that execution;
16. a newly generated historical evidence package contains the original source
    catalogue/test-definition identity, preserves a separate generation build
    identity and does not relabel the evidence as v1.1;
17. a new execution after promotion binds to the new active catalogue identity;
18. an unfinished old-catalogue execution rejects further evidence capture and
    continuation/finalisation against the promoted definition and remains
    historical/read-only; and
19. engineering expected-value comparison excludes dynamic build/catalogue/
    test-definition/case-definition identities, while the separate provenance
    gates and composite agreement checks still enforce them.

## 14. Proposal and lifecycle gate

Current disposition: **Proposed / core architecture accepted in substance;
bounded correction pending final independent review.**

This branch contains design/change-control material only. It does not alter the
machine-readable catalogue, database contracts, implementation behaviour,
controlled configurations or accepted I8 runtime baseline. I9 remains stopped.

If independently accepted, DC-004 must then be applied to the machine-readable
validation definition/contracts and cross-document/identity impacts verified
before I9 resumes. Acceptance of this proposal does not itself authorise I9
implementation.

## 15. Proposal verification record

Initial proposal verification completed on 2026-08-10. The bounded review
correction was applied and verified on 2026-08-11. The corrected proposal
identities are:

- Validation Plan proposed v1.1: 842,561 bytes; SHA-256
  `9c9d248685c33bb08b14478acd4e46d8d15ba0793e0e5543fc60be6e353f6953`;
  44 rendered pages.
- Demonstrator Design proposed v0.3: 849,335 bytes; SHA-256
  `ebb9af6011be756491cea884712c40cc7f12121f31dcd79e0504e7202adb29ef`;
  44 rendered pages.
- Both DOCX packages passed ZIP/OOXML structural checks and all proposed pages
  were rendered and visually inspected, including repeated table headers and
  final-page layout.
- The unchanged machine catalogue still contains 24 definitions and exactly
  286 accepted requirement/test relationships across 124 requirements; the
  independent catalogue/RTM unit suite passed 7 tests.
- Catalogue, validation manifest, network configuration, network schema and
  dependency-lock hashes remain at the accepted I8 values.
- Git scope inspection confirms no Requirements Specification, Network Model,
  System Architecture, Workflow Design, implementation, schema, catalogue,
  configuration, migration, dependency or test file changed.
- The current-baseline manifest intentionally remains the accepted I8 manifest;
  proposed document identities are not promoted into it before independent
  acceptance/application.

## V2 Automation Candidate

**V2 Automation Candidate — composite validation evidence assembly.** Checking
that every required constituent exists once, shares controlled provenance and
has complete evidence is repetitive and evidence-heavy. A future assurance
tool could assemble and cross-check the proposed composite while preserving the
deterministic V1 rules and engineer-controlled final determination.
