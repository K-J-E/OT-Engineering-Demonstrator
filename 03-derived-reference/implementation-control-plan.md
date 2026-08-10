---
Status: Active implementation control plan — DC-004 design accepted; I8 implementation accepted; I9 stopped pending separate DC-004 application
Authority: Derived reference and delivery-control aid only
Owner: Project engineering and implementation review process
Updated: 2026-08-11
Applies to: Approved Step 8 implementation increments I1–I9
---

# Implementation Control Plan

## 1. Purpose and authority

This plan governs controlled delivery of the approved Step 8 increments I1–I9. It translates the accepted engineering, architecture, workflow, demonstrator-design and validation baselines into bounded implementation work packages. It does not override or replace the governing documents, authoritative Word documents, accepted design changes, exact requirement wording, Validation Plan expected outcomes or formal change control.

If this plan conflicts with an authoritative artefact, the authoritative artefact wins and implementation stops until the inconsistency is resolved. This plan does not authorise I1 or any later increment. An increment begins only after the user explicitly authorises that specific bounded increment.

The current baseline is:

- Network Model v0.4 through Section 18.7;
- System Architecture v0.2 through Section 26.5;
- Workflow Design v0.2 through Section 27.4;
- Demonstrator Design v0.3 through Section 36.8, including accepted DC-004;
- Validation Plan v1.1 through Section 19.9, accepted as the current validation-design baseline;
- 124 unchanged formal requirements; and
- DC-001, DC-002, DC-003 and DC-004 accepted and applied to their authoritative design artefacts.

Accepted DC-004 makes Demonstrator Design Section 36 and Validation Plan Section 19 authoritative. Its machine-readable catalogue, contract, persistence and application treatment remains a separate controlled application phase requiring its own branch (planned as `agent/dc-004-application` from the accepted design `main` baseline), tests, build identity, independent review and incorporation into `main`. The stopped `agent/i9-packaging-review` branch is not reused. I9 remains stopped until that application baseline is accepted.

The detailed source documents remain authoritative. Requirement ranges and catalogue-test references below are navigation and delivery controls, not substitutes for reading the exact rows and test definitions.

## 2. Increment order and authorisation state

The Step 8 ordering is preserved because each increment supplies an implementation dependency required by the next:

| Increment | Approved Step 8 name | Current authority state |
|---|---|---|
| I1 | Contracts and inputs | **Accepted implementation baseline** |
| I2 | Topology and outage core | **Accepted implementation baseline** |
| I3 | Scenario transactions | **Accepted implementation baseline** |
| I4 | Restoration | **Accepted implementation baseline** |
| I5 | Validation/evidence | **Accepted implementation baseline** |
| I6 | Operational UI | **Accepted implementation baseline** |
| I7 | Investigation/correction | **Accepted implementation baseline** |
| I8 | Exploration and export | **Accepted implementation baseline** |
| I9 | Packaging/review | **Authorised, then stopped before implementation — accepted DC-004 application not yet authorised or implemented** |

No later increment starts automatically after the current one completes. Completion closes only the authorised increment; the repository then remains stopped until the increment branch is independently reviewed and accepted, merged to `main`, and the user separately authorises the next increment. The next increment starts from that reviewed `main` baseline on its own branch.

## 3. Controls that apply to every increment

### 3.1 Mandatory source reading

Before editing implementation files, the implementing task shall:

1. read the Project Vision, Project Definition and Project Decisions;
2. read the exact Requirements Specification rows named for the increment, including their rationale and verification methods;
3. read the named Network Model, System Architecture, Workflow Design, Demonstrator Design and Validation Plan sections;
4. check all accepted design-change records and the current baseline manifest; and
5. consult the implementation source map only as a navigation aid.

The source references in Sections 4–12 are minimum reading, not permission to ignore a directly applicable authoritative section.

### 3.2 Per-increment delivery cycle

Each increment shall be:

1. explicitly authorised and bounded;
2. developed on its own branch created from the reviewed `main` baseline;
3. implemented only within that boundary;
4. tested against its named implementation tests and Validation Plan gates;
5. reviewed for requirement, design-decision and source-section traceability;
6. committed as a separate intentional Git commit;
7. pushed for independent review; and
8. merged to `main` only after that increment is independently accepted.

Each increment is therefore implemented, tested, committed and pushed separately on its own branch before review and merge.

The branch and commit shall identify the increment and shall not include unrelated work or work from a later increment. Test and evidence results shall identify the source commit/build where applicable. Acceptance and merge close only the current increment; the next branch is not created and the next increment does not begin until the user provides separate authorisation.

### 3.3 Progression and stop rules

Progression stops when any required test fails, required evidence is absent or corrupt, a baseline contradiction appears, a required input/version cannot be identified, or an engineering/design choice is unspecified. A failed test is never bypassed by changing its expected result, weakening the assertion, hard-coding an answer, suppressing evidence or moving the work into a later increment.

If resolution would change engineering behaviour, operational rules, network assumptions, workflow, requirement wording or accepted expected outcomes, implementation shall not decide the matter in code. The question is documented and resolved through the appropriate engineering review and controlled change before work resumes. A code-only correction may proceed within the same increment only when it restores conformance to an already explicit approved rule and the original failing evidence is retained.

### 3.4 Validation and evidence interpretation

Implementation-level tests may sit beneath a Validation Plan catalogue ID, but may not change its engineering result. Before I5 provides formal execution/evidence records, catalogue references in I1–I4 are conformance gates rather than claims that a formal validation execution has been completed. Formal and exploratory evidence remain separate, operational non-success may be an expected validation PASS, and operational events remain separate from test, defect, correction and engineering-review records.

### 3.5 Build identity, dependencies and immutable configuration

IMP-001 is resolved in I1. Exact Python, Node and package versions shall be pinned in lock files at that point and incorporated into the application build identity with the controlled source, dependency and toolchain hashes required by Demonstrator Design Sections 10.5, 26, 31 and 32. A later dependency change creates a new build identity and triggers affected regression; it is not silently absorbed.

I1 is also the first appropriate implementation baseline for the approved Network Configuration v1.0 and v1.1 definitions. It shall instantiate them as two separate schema-valid, immutable implementation packages, hash them, and prove that their only controlled topology difference is SW-A23 endpoint 1 (`SEC-B3` in v1.0 and `SEC-A2` in v1.1). This package baseline must be verified before any validation execution. Runtime logic shall load the packages independently and shall never create, rewrite or derive v1.1 from v1.0.

**V2 Automation Candidate — Increment assurance and evidence collation.** Rechecking source coverage, test status, build identity, traceability and commit evidence for every increment is repetitive and evidence-heavy; a future assurance tool could assemble a candidate completion pack while leaving technical acceptance and progression authority with the engineer.

## 4. I1 — Contracts and inputs

### Objective and engineering scope

Create the approved repository/application scaffold and the typed, versioned contracts on which later logic depends. Resolve IMP-001; establish typed enums, value objects and schemas; create initial database migrations; establish build identity; and instantiate the immutable v1.0/v1.1 configuration packages from the approved engineering definitions. Do not implement topology, outage, scenario, restoration or user-interface behaviour.

### Authoritative sources to read

- Requirements Specification: `REQ-NET-001–011`, `REQ-CFG-001–003`, `REQ-CFG-006`, `REQ-CFG-008–010`, `REQ-NFR-002`, `REQ-NFR-004` and `REQ-NFR-009`.
- Network Model: Sections 2–15, 17.1–17.4, 17.9–17.11 and 18.5–18.6.
- System Architecture: Sections 5, 14–15, 21 and 26.4–26.5.
- Workflow Design: Sections 5, 18, 22 and 27.4.
- Demonstrator Design: Sections 4–12, 26–27, 29–32 and 35.5–35.6.
- Validation Plan: Sections 2–5, catalogue/procedure row `VT-CFG-BASE-001`, Sections 10.1, 11, 14 and 15.

### Requirements addressed

Primary implementation coverage is `REQ-NET-001–011`; the configuration-definition and preservation foundations of `REQ-CFG-001–003`, `006` and `008–010`; and the stable-ID, fictional-data and consistent-entity controls in `REQ-NFR-002`, `004` and `009`. Later increments complete behavioural and presentation verification for these requirements.

### Applicable tests and gates

- `VT-CFG-BASE-001`: schema, identity, values, hashes and the single controlled difference.
- Configuration/package portions of `VT-TOP-DEF-001` and `VT-CFG-INV-001`; no defect workflow execution yet.
- Configuration and identifier review portions of `VT-NFR-REVIEW-001`.
- Validation Plan implementation entry criterion and Demonstrator Design Section 27.1 coding gate.

### Expected files/modules

- `app/backend/ot_demo/domain/` typed enums, entities and value objects.
- Initial `app/backend/ot_demo/modules/configuration/` contracts and `app/backend/ot_demo/infrastructure/` JSON loading, hashing and migration foundations.
- `app/backend/ot_demo/api/` and `app/frontend/` scaffolds only to the extent needed for a reproducible build; no later-increment behaviour.
- `config/network/v1.0/` and `config/network/v1.1/` immutable JSON and manifests.
- `config/presentation/` schema/boundary if needed, with no topology meaning.
- Dependency lock files, build-identity manifest logic and initial SQLite migrations.
- `tests/unit/` and `tests/integration/` coverage for contracts, schemas, manifests and configuration differences.

### Completion criteria and required evidence

- Clean environment setup and reproducible build use exact pinned dependencies; IMP-001 is closed in the QA register and the resolved versions appear in build identity.
- Both packages validate independently and match all approved IDs, assets, connectivity, normal states, loads, capacities and customer-zone mappings.
- A machine-verifiable comparison proves exactly one controlled topology difference: SW-A23 endpoint 1.
- Package hashes and version IDs are stable and captured before any execution path can use them.
- Database migrations apply cleanly from an empty local database.
- All I1 tests pass, source/requirement links are recorded, the increment is separately committed and pushed, and no I2 logic is present.

### Dependencies on later increments

I2 consumes the packages and domain contracts; I3 extends persistence and command contracts; I5 binds build/configuration identities into validation records; I7 presents the controlled comparison. I1 does not claim that any of those later behaviours are complete.

### Explicit stop conditions

Stop for any ambiguity in an asset, endpoint, value, identifier, schema ownership or v1.0/v1.1 difference; inability to pin compatible exact dependencies; an unapproved additional package difference; runtime mutation of a canonical package; or pressure to add topology/behavioural logic merely to make package tests pass.

## 5. I2 — Topology and outage core

### Objective and engineering scope

Implement the generic configuration-driven graph, active-edge calculation, source tracing, section energisation, radiality, active-fault boundary derivation/isolation proof, and OMS outage/customer mapping. Both v1.0 and v1.1 shall pass through the same normal logic. Do not add scenario-command orchestration, restoration assessment, validation records or UI state logic.

### Authoritative sources to read

- Requirements Specification: `REQ-TOP-001–009`, `REQ-OUT-001–007`, `REQ-CFG-002–005`, `REQ-NET-001–011`, `REQ-NFR-003` and `REQ-NFR-009`.
- Network Model: Sections 2–18.7, with particular attention to Sections 13–18.
- System Architecture: Sections 5, 7, 9, 14–16, 19 and 26.1–26.3.
- Workflow Design: Sections 8–10.3, 13, 15–17, 22 and 27.1–27.3.
- Demonstrator Design: Sections 5, 7–8.4, 11–12, 16, 22, 27–28 and 35.1–35.5.
- Validation Plan: Sections 6–8 rows `VT-TOP-NORMAL-001`, `VT-TOP-DEF-001`, `VT-RST-ISOLATION-001` and the domain portion of `VT-EXP-ALL-001`; Sections 11–12.1, 14 and 15.

### Requirements addressed

Primary coverage is `REQ-TOP-001–009` and `REQ-OUT-001–007`. This increment also supplies the normal-processing and propagated-impact behaviour for `REQ-CFG-002–005`, consumes the I1 network contracts for `REQ-NET-001–011`, and supports deterministic/consistent processing under `REQ-NFR-003` and `009`.

### Applicable tests and gates

- `VT-TOP-NORMAL-001` complete domain result.
- N0/N1 and outage portions of `VT-FML-N0-N5-001`.
- `VT-TOP-DEF-001` topology/outage result: v1.0 produces the 400-customer consequence and v1.1 the 850-customer expected result through identical algorithms.
- Isolation-domain portion of `VT-RST-ISOLATION-001`.
- All-eight-section incidence/boundary derivation portion of `VT-EXP-ALL-001`, including DC-003 A/B/C proof semantics at the pure-domain boundary.

### Expected files/modules

- `app/backend/ot_demo/modules/topology/`.
- `app/backend/ot_demo/modules/outage/`.
- Configuration graph adapters and pure domain types shared from I1.
- Read-model structures for configured and derived state, without UI rendering.
- Unit/integration fixtures for v1.0, v1.1, N0/N1 and all eight incident-boundary pairs.

### Completion criteria and required evidence

- Corrected v1.1 normal state energises all eight sections with the approved source attribution, load and no-loop/outage results.
- Formal BRK-A trip produces the approved v1.1 N1 topology and 850 affected customers.
- The same logic applied to v1.0 yields A3/A4 supplied from FDR-B and 400 affected customers; no defect-specific conditional or stored answer exists.
- Section energisation is derived only from configured connectivity, source availability and current device states; fault status remains separate.
- All eight DC-003 incident-boundary pairs and final isolation proof conditions are covered by domain tests.
- Configured load and derived supplied load remain distinct in models and tests.
- All I2 tests pass and the increment is separately committed and pushed.

### Dependencies on later increments

I3 supplies controlled state changes and observed evidence; I4 consumes the topology/outage results for restoration; I6 presents them; I7 exposes the investigation path; and I8 applies the same engine to arbitrary section selection.

### Explicit stop conditions

Stop if a topology or outage result requires a per-section answer table, fault-specific algorithm, UI-derived result, conflation of fault and energisation, canonical-package edit, unapproved handling of multiple sources/loops, or any boundary rule not explicit in the approved baseline.

## 6. I3 — Scenario transactions

### Objective and engineering scope

Implement run context, controlled scenario time, observed telemetry and alarms, command/revision/idempotency gates, atomic transaction ordering, operational events, reset semantics and the approved N0→N3 state-changing workflow. Do not implement restoration assessment/execution, formal validation execution records or UI workflows.

### Authoritative sources to read

- Requirements Specification: `REQ-TEL-001–010`, `REQ-ALM-001–005`, `REQ-EVT-001–011`, `REQ-VAL-014`, relevant `REQ-TOP-*`, and `REQ-NFR-003`.
- Network Model: Sections 16.1–16.9 and 18.3–18.4.
- System Architecture: Sections 6, 10–11, 14–18 and 26.2–26.3.
- Workflow Design: Sections 5–10.8, 18, 20–22 and 27.1–27.3.
- Demonstrator Design: Sections 8.2–8.6, 9–12, 15–17, 23, 25 and 27–28.
- Validation Plan: Sections 3–5, 7–9, 14 and 15, especially `VT-TEL-FRESH-001`, `VT-TEL-STALE-001`, `VT-TEL-UNCERTAIN-001`, `VT-TEL-BAD-001`, `VT-TEL-FUTURE-001`, `VT-ALM-EVT-001`, `VT-VAL-RECORD-001` reset clauses and `VT-DET-REPEAT-001`.

### Requirements addressed

Primary coverage is `REQ-TEL-001–010`, `REQ-ALM-001–005` and `REQ-EVT-001–011`, plus the reset mechanism for `REQ-VAL-014`, deterministic processing under `REQ-NFR-003`, and the transaction-facing portions of topology requirements.

### Applicable tests and gates

- Freshness arithmetic/classification gates in the five telemetry catalogue tests named in the source-reading list; restoration outcome assertions remain for I4.
- `VT-ALM-EVT-001` event types, ordering and acknowledgement behaviour.
- N0→N3 transaction portion of `VT-FML-N0-N5-001`.
- Reset/history portion of `VT-VAL-RECORD-001`.
- Controlled-clock and repeated-output portions of `VT-DET-REPEAT-001`.
- Additional implementation tests for stale revision, duplicate `command_id`, atomic rollback and invalid actions trace to these catalogue gates and the exact requirements.

### Expected files/modules

- `app/backend/ot_demo/modules/telemetry/`, `events/` and `scenario/`.
- `app/backend/ot_demo/application/` transaction coordinator, command handlers and allowed-action assembly foundations.
- SQLite repositories/migrations for runs, observations, alarms and operational events.
- `/api/v1` command/query contracts needed to exercise N0→N3 without a full UI.
- Unit/integration/API tests for time, evidence quality, revisions, idempotency, rollback, reset and chronology.

### Completion criteria and required evidence

- Scenario time is deterministic UTC millisecond time; wall clock is not an engineering input.
- 60,000 ms is inclusively FRESH, 60,001 ms is STALE, future timestamps are invalid, and quality remains independent from freshness.
- Accepted commands apply the approved transaction order atomically; a failure leaves no partial observed, derived or event state.
- Revision mismatch and invalid action leave engineering state unchanged; duplicate command IDs do not duplicate operations/events.
- The 15-type operational event catalogue and acknowledgement lifecycle match Step 7, with test/defect records excluded.
- N0→N3 transitions and reset/history behaviour pass their controlled tests.
- All I3 tests pass and the increment is separately committed and pushed.

### Dependencies on later increments

I4 extends the coordinator with assessment/execution binding; I5 adds validation/evidence records; I6 renders the projections; I8 creates exploratory runs using the same transaction engine.

### Explicit stop conditions

Stop for wall-clock dependence, partial commits, locally invented event types, operational events used for validation/defects, UI-owned action gates, ambiguous command ordering, telemetry quality/freshness conflation, or any N-state transition not defined by the workflow baseline.

## 7. I4 — Restoration

### Objective and engineering scope

Implement restoration candidate discovery, required evidence collection, decision precedence, `BLOCKED`/`REJECTED`/`PERMITTED` outcomes, exact capacity calculations, assessment invalidation and execution binding through formal N4/N5. Use topology, outage and observed state from earlier increments; do not add a manual override, guaranteed solution, real control or new electrical assumptions.

### Authoritative sources to read

- Requirements Specification: `REQ-RST-001–029` and directly applicable `REQ-TOP-*`, `REQ-TEL-*`, `REQ-OUT-*`, `REQ-EVT-*` and `REQ-NFR-006`.
- Network Model: Sections 6, 9–13, 15–16.15 and 18.3–18.5.
- System Architecture: Sections 7–9, 11.2, 15–18 and 26.1–26.3.
- Workflow Design: Sections 6.3, 8, 10.5–10.12, 11–13, 20–22 and 27.
- Demonstrator Design: Sections 8.4–8.6, 11–12, 18, 23, 27–28 and 35.1–35.4.
- Validation Plan: Sections 5–10, 12.3, 14 and 15, especially `VT-FML-N0-N5-001`, the five telemetry catalogue tests, the six restoration catalogue tests named below and `VT-DET-REPEAT-001`.

### Requirements addressed

Primary coverage is the complete `REQ-RST-001–029` group. The increment also exercises topology, telemetry, outage/customer and event requirements used as restoration inputs/outputs and the simulated-operation boundary in `REQ-NFR-006`.

### Applicable tests and gates

- `VT-FML-N0-N5-001` complete backend scenario.
- `VT-TEL-FRESH-001`, `VT-TEL-STALE-001`, `VT-TEL-UNCERTAIN-001`, `VT-TEL-BAD-001` and `VT-TEL-FUTURE-001` complete operational/validation-result logic.
- `VT-RST-ISOLATION-001`, `VT-RST-SOURCE-001`, `VT-RST-RADIAL-001`, `VT-RST-CAP-EQUAL-001`, `VT-RST-CAP-OVER-001` and `VT-RST-BINDING-001`.
- Deterministic backend-output portion of `VT-DET-REPEAT-001`.

### Expected files/modules

- `app/backend/ot_demo/modules/restoration/` models, candidate service, evidence evaluator and calculations.
- Application command/query handlers for assessment, invalidation and permitted execution.
- Persistence for immutable assessment records and revision bindings.
- Unit/integration/API fixtures for formal, telemetry-negative, alternate-source, radiality, capacity and stale-binding cases.

### Completion criteria and required evidence

- Formal N4 is `PERMITTED` with 1,500 kW transfer, 5,700 kW resulting FDR-B load and 95.0% loading; N5 restores 450 and leaves 220 affected while remaining radial.
- Insufficient/untrustworthy required evidence produces `BLOCKED`; complete trustworthy evidence with a failed criterion produces `REJECTED`; reason/evidence records are explicit.
- Equality at 6,000 kW passes and 6,001 kW rejects using controlled lower-level fixtures without mutating canonical packages.
- Only a current `PERMITTED` assessment bound to the matching revisions can authorise the simulated tie operation; relevant change invalidates availability and preserves the prior record.
- Isolation proof, alternate-source availability, radiality, telemetry and capacity all use generic approved rules.
- All I4 tests pass and the increment is separately committed and pushed.

### Dependencies on later increments

I5 records formal comparisons/evidence; I6 presents assessment and actions; I7 uses restoration consequences during investigation; I8 reuses the engine for non-guaranteed exploratory outcomes.

### Explicit stop conditions

Stop for a missing permissive/precedence rule, non-approved candidate selection, hard-coded 5.70 MW/95.0% output, silent action after invalidation, canonical fixture mutation, manual override, forced success, autonomous switching, or any attempt to turn a negative operational result into validation failure contrary to the accepted expected outcome.

## 8. I5 — Validation/evidence

### Objective and engineering scope

Implement the approved test-definition, execution, checkpoint, expected-versus-observed comparison, immutable evidence snapshot, reset-preservation and record-linkage model. Instantiate machine-readable definitions for all 24 accepted catalogue tests without altering their expected engineering results. Do not add the operational UI, investigation presentation, Exploration UI or evidence ZIP export.

### Authoritative sources to read

- Requirements Specification: `REQ-VAL-001–014`, `REQ-CFG-009–012`, `REQ-EVT-001–011`, `REQ-NFR-003` and `REQ-NFR-008`.
- Network Model: Sections 16–18.
- System Architecture: Sections 12, 17, 19–20 and 26.4–26.5.
- Workflow Design: Sections 5.2–5.3, 14–19, 22 and 27.3–27.4.
- Demonstrator Design: Sections 8.7, 9, 10.5, 12, 19, 21–22 and 27–28.
- Validation Plan: Sections 3–15 and 17–18 in full, including every catalogue/procedure row and the exact 124-row matrix.

### Requirements addressed

Primary coverage is `REQ-VAL-001–014`, with preservation/linkage foundations for `REQ-CFG-009–012`, separation from `REQ-EVT-001–011`, determinism under `REQ-NFR-003` and reviewable evidence under `REQ-NFR-008`.

### Applicable tests and gates

- `VT-VAL-RECORD-001` complete.
- `VT-TOP-DEF-001` v1.0 FAIL preservation and v1.1 PASS comparison using the same build.
- Record/linkage portions of `VT-CFG-INV-001`.
- `VT-DET-REPEAT-001` with immutable separate executions.
- Test-definition and checkpoint/evidence obligations of all 24 catalogue tests; this does not imply every end-to-end catalogue execution is complete.
- Validation Plan execution entry, suspension, regression and evidence-completeness criteria.

### Expected files/modules

- `app/backend/ot_demo/modules/validation/` and evidence-owned records/repositories.
- `validation/test-definitions/` containing all 24 controlled definitions and traceability metadata.
- Immutable execution, checkpoint, comparison, snapshot, defect/correction-link and reset-history persistence.
- Application/API services for controlled execution and evidence queries, without full presentation.
- Unit/integration/API tests for immutability, separation, linking, comparison and repeat behaviour.

### Completion criteria and required evidence

- Exactly 24 machine-readable test definitions match the accepted catalogue and carry requirement/source references; no expected result is weakened or invented.
- Executions identify build, configuration, test definition, controlled time, expected/observed results, calculations, evidence class and verdict.
- The v1.0 `VT-TOP-DEF-001` FAIL remains immutable while same-build v1.1 creates a separate linked PASS; reset creates a new run without deleting history.
- Formal, exploratory, operational-event, defect, correction and diagnostic records remain distinct and traceable.
- Overwrite/delete attempts on finalised controlled records are rejected and tested.
- All I5 tests pass and the increment is separately committed and pushed.

### Dependencies on later increments

I6 presents formal validation progress; I7 adds the investigation/correction workspace; I8 presents exploratory evidence and creates ZIP exports; I9 executes and packages the full accepted validation set.

### Explicit stop conditions

Stop if any catalogue definition or expected result conflicts with Step 9, an execution cannot identify its build/configuration/test version, immutability or mode separation cannot be enforced, evidence is reconstructed from mutable current state, a reset removes history, or a missing validation decision would need to be guessed.

## 9. I6 — Operational UI

### Objective and engineering scope

Implement the approved local review interface: run setup, persistent context ribbon, fixed one-line network, configured/observed/derived inspector, telemetry/alarm/event views, backend-owned actions, restoration assessment and formal validation presentation. The frontend renders backend projections and allowed actions; it does not calculate topology, isolation, outage, restoration or N-state logic.

### Authoritative sources to read

- Requirements Specification: presentation paths for `REQ-NET-*`, `REQ-TOP-*`, `REQ-TEL-*`, `REQ-ALM-*`, `REQ-OUT-*`, `REQ-RST-*`, `REQ-EVT-*`, `REQ-VAL-*`, and `REQ-NFR-001`, `005–007` and `009`.
- Network Model: Sections 13–16 and the diagrams/labels needed for the one-line.
- System Architecture: Sections 13, 17–18, 20–21 and 26.3.
- Workflow Design: Sections 9–14 and 18–21.
- Demonstrator Design: Sections 13–19, 23–25 and 27–29.
- Validation Plan: Sections 6–10, 13–15, especially `VT-FML-N0-N5-001`, `VT-ALM-EVT-001`, the five telemetry boundary/quality cases, `VT-VAL-RECORD-001` and `VT-NFR-REVIEW-001`.

### Requirements addressed

This increment provides the approved presentation and interaction path for the operational requirement groups already implemented in I1–I5. Primary new acceptance emphasis is `REQ-NFR-001`, `005–007` and `009`; it does not redefine the backend ownership of any functional requirement.

### Applicable tests and gates

- Component tests for distinct configured/observed/derived/fault/evidence states, persistent context and backend-owned action availability.
- Playwright formal N0–N5 workflow under `VT-FML-N0-N5-001`.
- UI/chronology portions of `VT-ALM-EVT-001` and telemetry boundary/quality presentation under the five controlled telemetry tests.
- Formal record/progress presentation under `VT-VAL-RECORD-001`.
- Interface, scope and conceptual-boundary review under `VT-NFR-REVIEW-001`.

### Expected files/modules

- `app/frontend/src/features/` run setup, operational, telemetry/events, restoration and formal-validation features.
- `app/frontend/src/components/network/` fixed-coordinate Cytoscape one-line.
- Backend read-model assembly and `/api/v1` query/command endpoints required by these views.
- Presentation-only `config/presentation/` coordinates/labels where not completed in I1.
- Component and `tests/e2e/` formal-workflow coverage.

### Completion criteria and required evidence

- The complete N0–N5 browser workflow succeeds using only backend-returned projections/actions.
- Configured, observed and derived information, fault state, operational events and validation evidence are visibly distinct.
- The one-line is fixed for review; no drag/edit action changes engineering topology.
- The context ribbon continuously shows the approved Step 8 fields: mode, evidence class, short/full run identity, configuration version, active fault section, workflow stage, formal N-state where applicable, state revision and current assessment status.
- Controlled scenario time remains visible where the approved telemetry and workflow design requires it; it is not introduced as a new mandatory context-ribbon field.
- Warnings, reason codes, stale/quality states and rejected/blocked/permitted meanings remain reviewable and accessible.
- Simulated/local/conceptual boundaries are explicit and no real-control implication is introduced.
- All I6 tests pass and the increment is separately committed and pushed.

### Dependencies on later increments

I7 adds investigation/correction views; I8 adds exploration and export views; I9 completes accessibility, engineering-basis and walkthrough packaging.

### Explicit stop conditions

Stop if the frontend must infer an action/result, encode N-state transitions, hard-code section outcomes, alter topology via presentation data, hide evidence deficiencies, conflate configured and supplied load, or require a screen/workflow not approved in Step 8.

## 10. I7 — Investigation/correction

### Objective and engineering scope

Implement the approved consequence-to-source DEF-001 investigation workspace, configuration comparison and failure→defect→correction→repeat→regression links. Preserve the immutable v1.0 failure and select the already-instantiated immutable v1.1 package for repeat; do not rewrite configuration at runtime or change the shared algorithms.

### Authoritative sources to read

- Requirements Specification: `REQ-CFG-001–012`, `REQ-VAL-005`, `REQ-VAL-010–012`, and the topology/outage requirements used to show consequences.
- Network Model: Sections 17–18.7 and the applicable N1 answer key in Section 16.
- System Architecture: Sections 19–20 and 26.4–26.5.
- Workflow Design: Sections 15–17 and 19.
- Demonstrator Design: Sections 19, 21–22, 27–28 and 35.4–35.5.
- Validation Plan: catalogue/procedure rows `VT-TOP-DEF-001`, `VT-CFG-INV-001`, `VT-DET-REPEAT-001` and `VT-FML-N0-N5-001`; Sections 11, 13–15.

### Requirements addressed

Primary coverage is `REQ-CFG-001–012` and the failed/corrected record requirements `REQ-VAL-005` and `REQ-VAL-010–012`, supported by the established topology, outage and evidence requirements.

### Applicable tests and gates

- `VT-TOP-DEF-001` same-build v1.0 FAIL → v1.1 PASS.
- `VT-CFG-INV-001` complete eight-step investigation/correction chain.
- `VT-DET-REPEAT-001` direct controlled repeat.
- `VT-FML-N0-N5-001` full corrected regression after the direct repeat.
- Configuration/package integrity recheck under `VT-CFG-BASE-001`.

### Expected files/modules

- Investigation/correction services and repositories within their Step 8 ownership boundaries.
- `app/frontend/src/features/investigation/` consequence, SCADA, source-path, OMS, compare, correction and repeat panels.
- Configuration comparison read models showing the exact endpoint difference without making canonical inputs editable.
- End-to-end fixtures for preserved failure, linked correction, same-build pass and full regression.

### Completion criteria and required evidence

- The reviewer can trace 400 affected customers to A1/A2 de-energisation, confirm correct BRK-A telemetry, trace A3/A4 to FDR-B via SEC-B3/SW-A23, verify OMS arithmetic and identify the single endpoint cause.
- v1.0 and v1.1 packages and hashes remain unchanged; the running application selects v1.1 rather than generating it.
- Algorithms and build identity are identical across the direct FAIL/PASS comparison.
- Original failure, defect, correction, repeat PASS and N0–N5 regression are separate immutable linked records.
- All I7 tests pass and the increment is separately committed and pushed.

### Dependencies on later increments

I8 exports these preserved records; I9 includes the chain in the final regression and walkthrough fixtures.

### Explicit stop conditions

Stop if the observed consequence differs from the approved answer key, more than one package difference appears, investigation requires defect-specific result code, the application edits/generates v1.1, a record is overwritten, or a correction would change engineering behaviour rather than restore the approved configuration.

## 11. I8 — Exploration and export

### Objective and engineering scope

Implement Exploration Mode for selection of any of the eight distribution sections using corrected v1.1 and the same generic engine, with derived feeder roles, DC-003 boundary evidence, non-guaranteed outcomes and strict EXPLORATORY evidence classification. Implement the approved self-contained evidence ZIP export for formal and exploratory records without mixing their evidentiary status.

### Authoritative sources to read

- Requirements Specification: `REQ-EXP-001–007`, applicable `REQ-RST-*`, `REQ-VAL-009`, and `REQ-NFR-008`.
- Network Model: Sections 15.1, 17.12 and 18.
- System Architecture: Sections 17.2–17.3, 20 and 26.
- Workflow Design: Sections 13–14, 19 and 27.1–27.3.
- Demonstrator Design: Sections 20–21, 27–29 and 35.
- Validation Plan: `VT-EXP-ALL-001`, `VT-EXP-ROLE-001`, `VT-EXP-SEPARATION-001`, `VT-PKG-EVIDENCE-001`, `VT-NFR-REVIEW-001`; Sections 12–15.

### Requirements addressed

Primary coverage is `REQ-EXP-001–007`, with export/evidence coverage for `REQ-VAL-009` and `REQ-NFR-008`, plus reuse of restoration requirements where exploratory runs legitimately produce a candidate and outcome.

### Applicable tests and gates

- `VT-EXP-ALL-001` all eight selections and the SEC-A4 trustworthy-OPEN versus untrustworthy-last-OPEN subcase.
- `VT-EXP-ROLE-001` role reversal and representative `PERMITTED`, `REJECTED` or `NO CANDIDATE` outcomes.
- `VT-EXP-SEPARATION-001` mode, input, run and evidence separation.
- `VT-PKG-EVIDENCE-001` ZIP content, links, canonical JSON, figures and SHA-256 manifest.
- Exploration/export review portions of `VT-NFR-REVIEW-001` and repeatability where applicable under `VT-DET-REPEAT-001`.

### Expected files/modules

- Exploration run setup/workspace features under `app/frontend/src/features/` and corresponding backend scenario/read-model services.
- Generic fault-selection handling that stores selection only as transient run state.
- Evidence-library and export features/adapters.
- `evidence/exports/` output handling, excluded from mutable application inputs.
- End-to-end tests for eight-section selection, role reversal, non-guaranteed outcomes, separation and package manifests.

### Completion criteria and required evidence

- Every represented section can be selected in v1.1; affected feeder/breaker and incident boundaries come from configuration incidence, not a lookup table.
- A trustworthy OPEN boundary is satisfied with no redundant command; an untrustworthy last-reported OPEN is UNPROVEN, blocks isolation and also offers no redundant OPEN command.
- Feeder A/B roles can reverse and the engine does not guarantee candidate discovery or successful restoration.
- Formal remains fixed to SEC-A2; exploratory runs cannot be converted in place or automatically satisfy formal validation.
- Each ZIP is new, self-contained and hash-verifiable, contains the approved files, preserves source-record/build/config/test links, and does not overwrite prior packages.
- All I8 tests pass and the increment is separately committed and pushed.

### Dependencies on later increments

I9 performs the complete regression, clean-build/package review and final walkthrough-fixture assembly. Client-facing portfolio/video packaging remains a later delivery activity outside I1–I9.

### Explicit stop conditions

Stop for hard-coded per-section outcomes/boundaries, mutation of v1.1, a forced restoration path, formal/exploratory evidence mixing, runtime topology editing, export assembled from mutable live state instead of preserved records, missing/hash-invalid package entries, or any new Exploration engineering rule.

## 12. I9 — Packaging/review

### Objective and engineering scope

Complete the one-command local build/start path, engineering-basis view, accessibility and review polish, clean build manifest, controlled walkthrough fixtures and full regression. This increment packages and proves the approved V1 implementation; it does not expand V1 scope, add hosting, add production OT claims, add automation/AI or perform final client-facing portfolio/video packaging unless separately authorised later.

### Authoritative sources to read

- All 124 Requirements Specification rows and the verification methods attached to them.
- Network Model v0.4 Sections 1–18.7.
- System Architecture v0.2 Sections 1–26.5.
- Workflow Design v0.2 Sections 1–27.4.
- Demonstrator Design v0.3 Sections 1–36.8, especially Sections 24, 26–30 and accepted DC-004 Section 36.
- Validation Plan v1.1 Sections 1–19.9, including all 24 procedures, the exact RTM, entry/exit/suspension/regression criteria and accepted DC-004 Section 19.
- All accepted design changes, current manifests, QA register and implementation source map.

### Requirements addressed

Final implementation and validation coverage is all 124 requirements. Primary packaging/review emphasis is `REQ-NFR-001–009`; every other requirement must retain accepted evidence through the full catalogue and RTM audit.

### Applicable tests and gates

- Full 24-test Validation Plan catalogue at the appropriate test level and the 124/124 requirements-to-verification audit.
- Full unit, transaction, persistence, API, component and Playwright regression.
- `VT-NFR-REVIEW-001`, `VT-DET-REPEAT-001` and `VT-PKG-EVIDENCE-001` in their final-build context.
- Complete corrected N0–N5 regression and preserved v1.0 FAIL → v1.1 PASS chain.
- Validation Plan V1 execution exit criteria and Demonstrator Design Step 8 completion/coding-gate conformance review.

### Expected files/modules

- `scripts/` one-command local build/start, validation checks and build-manifest generation.
- Engineering Basis view and final accessibility/review refinements within the approved frontend structure.
- Clean-build manifest and reproducible walkthrough fixtures.
- Final implementation test/evidence indexes and the generated evidence packages used for review.
- Local operator/reviewer instructions that preserve fictional, simulated and conceptual boundaries.

### Completion criteria and required evidence

- A clean checkout builds and starts locally through the approved one-command path with exact locked dependencies and loopback-only runtime behaviour.
- Build identity, immutable package hashes and source commit are traceable through executions and exports.
- All required tests pass; expected negative operational outcomes carry correct validation PASS semantics; no failure is hidden or waived without controlled disposition.
- The RTM audit confirms 124/124 substantive coverage and the 24-test catalogue has accepted evidence/verdicts required for V1 exit.
- Review checklist confirms engineering clarity, accessibility, stable IDs, fictional data, conceptual OT roles, simulated control only, deterministic behaviour, consistent modelling and no V2 features in V1.
- The final I9 commit contains only I9 work, is pushed separately, and the repository is left at a stable review boundary.

### Dependencies on later increments

There is no later implementation increment. Final client-facing packaging, portfolio narrative, video/walkthrough production, hosting or a Future V2 Extension require separate planning and authorisation and must use the accepted V1 evidence rather than alter its engineering baseline.

### Explicit stop conditions

Stop for any catalogue or regression failure, uncovered requirement, untraceable build/configuration/test identity, manifest/hash mismatch, non-reproducible clean build, accessibility or review blocker, production/real-control implication, external runtime dependency, scope expansion, or unresolved engineering/design question. I9 is not complete until the issue is resolved and affected tests are rerun.

## 13. Increment closeout record

For each authorised increment, the completion report shall record:

- increment ID and explicitly authorised scope;
- source sections and requirement IDs actually used;
- files/modules added or changed;
- tests run, catalogue IDs/gates and results;
- evidence/build/configuration identifiers created;
- unresolved items and regression implications;
- commit hash and pushed branch; and
- explicit statement that the next increment has not started.

An increment with an open stop condition is not complete and shall not be committed/pushed as an accepted increment closeout. Diagnostic work and failing evidence may be preserved in a clearly identified non-acceptance commit only when the user explicitly authorises that exception.
