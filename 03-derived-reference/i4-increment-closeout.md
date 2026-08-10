---
Status: Complete — pending independent review
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-10
Increment: I4 — Restoration
---

# I4 Increment Closeout — Restoration

## 1. Authorisation, branch and boundary

The user explicitly authorised I4 only. Work was created on
`agent/i4-restoration` from the accepted reviewed `main` baseline at
`32118765e435b12864a3bea7f1c3af8bacf8b161`.

The bounded implementation commit is
`55eb2c80ef734b5efc6e66dbd0da8a8c9a0ea708`. It adds generic restoration
candidate discovery, required-evidence capture, permissive evaluation, decision
precedence, immutable assessments, invalidation/current-binding controls and the
approved formal N3→N4→N5 assessment/execution path.

I2 remains authoritative for topology, energisation, source attribution,
radiality, isolation proof and outage/customer calculations. I3 remains
authoritative for controlled time, command identity, revisions, transactions,
events, reset and history. I4 consumes those results; it does not copy their
algorithms or store expected section/customer answers.

No I5 validation execution/evidence record, operational UI, defect-investigation
workflow, Exploration Mode orchestration, real control, manual override,
autonomous switching or new engineering behaviour was implemented.

## 2. Authoritative sources used

Before implementation, the mandatory I4 source set in Implementation Control Plan
Section 7 was read, including:

- Project Vision, Project Definition and Project Decisions;
- complete `REQ-RST-001–029` rows and directly applicable `REQ-TOP-*`,
  `REQ-TEL-*`, `REQ-OUT-*`, `REQ-EVT-*` and `REQ-NFR-006` rows, including
  rationale and verification methods;
- Engineering Design Brief restoration permissives, decision precedence,
  capacity calculations, simulated execution and validation treatment;
- Network Model Sections 6, 9–13, 15–16.15 and 18.3–18.5;
- System Architecture Sections 7–9, 11.2, 15–18 and 26.1–26.3;
- Workflow Design Sections 6.3, 8, 10.5–10.12, 11–13, 20–22 and 27;
- Demonstrator Design Sections 8.4–8.6, 11–12, 18, 23, 27–28 and 35.1–35.4;
- Validation Plan Sections 5–10, 12.3, 14 and 15, including the formal,
  telemetry, restoration and deterministic-repeat catalogue definitions;
- accepted DC-001, DC-002 and DC-003 and the current controlled baseline maps;
  and
- accepted I1–I3 contracts, services, persistence and closeout records.

## 3. Files and modules produced or changed

- `app/backend/ot_demo/modules/restoration/`: immutable candidate, evidence,
  permissive, calculation, assessment, invalidation and execution-binding models;
  configuration-driven candidate discovery; assessment precedence; capacity and
  binding hashes.
- `app/backend/ot_demo/application/scenario_coordinator.py`: N4 assessment,
  current-assessment checks, invalidation, permitted N5 execution, reset treatment
  and backend-derived action availability.
- `app/backend/ot_demo/infrastructure/migrations/003_restoration.sql` and
  `scenario_repository.py`: immutable assessment/invalidation persistence and
  assessment-linked append-only operational events.
- Domain/scenario/event contracts: approved N4/N5, restoration command and result
  types, snapshot history and assessment links.
- `tests/unit/test_restoration_service.py` and
  `tests/integration/test_restoration_transactions.py`: precedence, formal,
  negative, binding, rollback, idempotency and repeat gates.
- Migration packaging regression and the `i4` test marker. Dependency versions and
  lock files are unchanged.

## 4. Approved implementation treatment

### 4.1 Candidate discovery is not permission

Candidate discovery starts from configured connectivity, the active fault,
currently de-energised healthy sections, represented ties and an alternate feeder
path. It does not depend on the alternate breaker already being CLOSED. This
preserves the approved distinction in `REQ-RST-001–003`: the exact source-negative
case still identifies a candidate and is then `REJECTED` by the alternate-source
permissive. No section-, feeder-, configuration-version- or expected-result branch
manufactures the formal answer.

### 4.2 Evidence and decision precedence

Each assessment captures the nine required monitored-device observations for the
formal candidate, including value, quality, timestamp, revision, exact age,
freshness and validity. Raw telemetry and source-availability hashes bind the
immutable record without using current wall time.

Decision precedence is explicit:

1. no candidate → `NO_CANDIDATE`;
2. a candidate with insufficient/unreliable required evidence → `BLOCKED`;
3. complete trustworthy evidence with any failed engineering criterion →
   `REJECTED`; and
4. all fault-isolation, alternate-source/path, radiality, telemetry and capacity
   criteria passing → `PERMITTED`.

### 4.3 Capacity and formal N4

Capacity uses integer kW inputs and decimal percentage presentation. Transferable
load is the sum of candidate-section configured loads; existing receiving-feeder
load is I2 derived currently supplied load; resulting load is their sum; and
passing uses exact `resulting_load <= capacity` comparison.

The formal N4 assessment at T+50 s produces:

- candidate sections `SEC-A3` and `SEC-A4` through `TS-01` from FDR-B;
- 1,500 kW transferable load and 450 proposed restored customers;
- FDR-B 4,200 kW existing, 5,700 kW resulting, 6,000 kW capacity and 95.0%;
- all five permissives PASS and overall `PERMITTED`; and
- unchanged electrical/topology revision 4 and unchanged N3 outage/topology
  snapshot. N4 is assessment only.

### 4.4 Binding, invalidation and formal N5

Execution requires the latest non-invalidated `PERMITTED` assessment for the same
run, configuration, state revision, candidate, raw telemetry snapshot and source
availability, with required evidence still trustworthy at current controlled time.
A time-only transition beyond the freshness limit makes the old assessment
non-executable without incrementing `state_revision`; the immutable assessment is
preserved and an append-only invalidation/event is recorded. Reset similarly
preserves then invalidates a current assessment before creating a new run.

At T+55 s the bound action changes only `TS-01` OPEN→CLOSED. The normal I2/I3
transaction path advances to revision 5/N5, derives A3/A4 from FDR-B, leaves
faulted SEC-A2 de-energised, remains radial, restores 450 customers and leaves 220
affected. No assessment can directly write section energisation or outage results.

## 5. Requirements and conformance-gate traceability

| Requirement / gate | I4 implementation evidence | I4 status |
|---|---|---|
| `REQ-RST-001–003` | Generic structural candidate discovery and typed source/tie/section/path/load record; candidate remains distinct from permission. | Implemented; pending review. |
| `REQ-RST-004–011` | I2 isolation proof, source/breaker/path, I2 radiality and all required quality/freshness states feed explicit permissives. | Implemented; pending review. |
| `REQ-RST-012–017` | Section-load sum, I2 current receiving load, exact resulting load/percentage and 6,000/6,001 kW fixtures. | Implemented; pending review. |
| `REQ-RST-018–022` | Explicit precedence, outcome/reason codes, evidence points and immutable assessment contents. | Implemented; pending review. |
| `REQ-RST-023–029` | Current permitted binding only; simulated tie close; I2 topology/outage recalculation; A3/A4 restored; A2 remains out; customers recalculate to 220. | Implemented; pending review. |
| Applicable topology/telemetry/outage/event requirements | Earlier services remain authoritative; exact approved 15-event catalogue is unchanged and restoration events link to assessment/command/run/revision. | I4 integration implemented; pending review. |
| `REQ-NFR-006` | Commands alter simulation state only; no external interface or control output exists. | Implemented; pending review. |
| `VT-FML-N0-N5-001` | Complete N0→N5 backend fixture proves the approved N4/N5 answer key. | Implementation conformance PASS only. |
| Five telemetry catalogue cases | Exact 60,000 ms permits; 60,001 ms, UNCERTAIN, BAD and future timestamp block. | Implementation conformance PASS only. |
| Six restoration catalogue cases | Isolation/source/radial negatives, exact capacity boundaries and stale binding are covered. | Implementation conformance PASS only. |
| `VT-DET-REPEAT-001` backend portion | Two controlled runs produce equal candidate/evidence/permissive/calculation/topology/outage engineering outputs. | Implementation conformance PASS only. |

These are implementation conformance gates, not I5 formal validation executions or
PASS/FAIL evidence verdicts.

## 6. Verification results and identities

| Verification | Result |
|---|---|
| I4 marked backend suite | PASS — 16 tests |
| Complete backend unit/integration suite | PASS — 81 tests |
| I3 regression | PASS — 20 tests |
| I2 regression | PASS — 31 tests |
| I1 regression | PASS — 11 tests |
| Atomic rollback, duplicate-command and repeat controls | PASS |
| Pinned TypeScript/Vite production build | PASS with Node 24.19.0/npm 11.17.0 |
| Python dependency consistency | PASS — no broken requirements |
| Git whitespace check | PASS |
| Expected-answer/hard-coding scan | PASS — formal numeric/section answers occur only in controlled tests/documents, not restoration production logic |
| I5+ leakage scan | PASS — no validation record, UI, defect, exploration, override or real-control behaviour |
| Canonical v1.0/v1.1/schema bytes and hashes | PASS — all five accepted values unchanged |
| Dependency/lock files | PASS — dependency definitions and locks unchanged; only the pytest `i4` marker was added |
| Authoritative engineering artefacts | PASS — unchanged |

The clean application build identity captured at the I4 implementation commit is:

`c3643df6131d78efedbbb7d4ee8053e18e5c7882dbf2ac9f63b2d62978c82ff4`

Its identity records `git_dirty = false`, commit
`55eb2c80ef734b5efc6e66dbd0da8a8c9a0ea708`, Python 3.13.15, Node.js
24.19.0, npm 11.17.0, accepted dependency-lock hashes, backend source hash
`2e3ee53919e251b18c76c1ca30818e6170f60dd919386656bd3d54920f44476c`
and unchanged frontend bundle hash
`1e6d5ebc33a8e11a06fcb929603af00386a471b13e381e25f3cc3dfb9bde4305`.

The accepted canonical identities remain:

- v1.0 data `67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3`;
- v1.0 manifest `d0243fae46e6a5d403855953e14cdedbcdae9c71af7761a1aba49f88470bc12d`;
- v1.1 data `7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281`;
- v1.1 manifest `e0f16f3acdf2e85aa04cd23bb4b584a868626117b68f682d1219821a36857662`;
  and
- shared schema `ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c`.

The desktop shell initially exposed an older Node/npm pair. Assurance commands were
therefore run explicitly with the already installed, repository-pinned 24.19.0 /
11.17.0 toolchain. This was an execution-environment selection issue, not a
dependency or engineering change.

## 7. QA findings and controlled artefacts

No new engineering contradiction or implementation defect requiring a new QA item
was found. Existing QA-007, QA-014 and QA-017 implementation watches now have I4
conformance evidence but remain subject to independent increment review. No closed
item was reopened.

The configuration packages, dependency locks, governing documents, detailed
engineering DOCX/PDF artefacts, accepted design-change records, current baseline
manifest and requirement count/wording were not modified.

## 8. Stop conditions and later dependencies

No I4 stop condition remains open. No failed test was bypassed, expected result was
changed, candidate/outcome was hard-coded, canonical fixture was edited or action
was silently permitted after invalidation.

I5 must create formal validation definitions/executions/evidence separately from
operational events and immutable I4 assessments. I6 presents the backend projection
and allowed actions without inferring results. I7 consumes preserved consequences;
I8 reuses the same engine for non-guaranteed exploratory outcomes. None has begun.

**V2 Automation Candidate — restoration evidence and regression collation.**
Rechecking every assessment binding, evidence point, permissive calculation,
invalidation cause and post-switch consequence is repetitive and evidence-heavy. A
future assurance tool could assemble candidate comparison and traceability packs for
engineer review without changing V1 decisions or switching authority.

## 9. Review and progression gate

I4 is complete on `agent/i4-restoration` and is pending independent review. The
branch must be pushed and reviewed; it must not be merged until accepted. I5 has not
started and requires separate user authorisation after the reviewed I4 baseline is
incorporated into `main`.
