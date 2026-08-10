---
Status: I3 branch complete — pending independent review
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-10
Increment: I3 — Scenario Transactions
---

# I3 Increment Closeout — Scenario Transactions

## 1. Authorisation, branch and implementation boundary

The user explicitly authorised I3 only. Work was created on
`agent/i3-scenario-transactions` from the accepted reviewed `main` baseline at
`ef5426c5d083e0811a953cb31c3e9c6147aba6fe`.

The bounded implementation commit is
`359f594decb376d568785741afafd11870adc484`. It implements run context,
controlled scenario time, observed switching telemetry, quality/freshness
classification, feeder-trip alarm and acknowledgement, command/revision/idempotency
gates, atomic SQLite transactions, the approved operational-event catalogue,
reset/new-run history semantics and the formal N0→N3 state-changing workflow.

Topology, source attribution, energisation, fault isolation, radiality and outage
calculation remain owned by the accepted I2 services. I3 coordinates their use but
does not copy their algorithms or store expected topology/customer answers.

No restoration candidate discovery, restoration decision/execution, formal
validation execution/evidence record, operational UI, defect/correction workflow or
Exploration Mode orchestration was implemented. I4 has not started.

## 2. Authoritative sources used

Before implementation, the mandatory I3 source set in Implementation Control Plan
Section 6 was read, including:

- Project Vision, Project Definition and Project Decisions;
- exact Requirements Specification clauses `REQ-TEL-001–010`, `REQ-ALM-001–005`,
  `REQ-EVT-001–011`, `REQ-VAL-014`, `REQ-NFR-003` and transaction-facing
  `REQ-TOP-001–007`, with rationale and verification methods;
- Engineering Design Brief Sections 7, 9.1, 10.2, 10.6, 11.2–11.8, 14–14.1,
  15.3, 18–18.3 and the applicable design decisions;
- Network Model Sections 16.1–16.9 and 18.3–18.4;
- System Architecture Sections 6, 10–11, 14–18 and 26.2–26.3;
- Workflow Design Sections 5–10.8, 18, 20–22 and 27.1–27.3;
- Demonstrator Design Sections 8.2–8.6, 9–12, 15–17, 23, 25 and 27–28;
- Validation Plan Sections 3–5, 7–9, 14–15 and the exact I3 catalogue procedures;
- accepted DC-001, DC-002 and DC-003, the design-change register, current baseline
  manifest and implementation source map; and
- accepted I1/I2 implementation contracts, configuration packages, services and
  closeout records.

## 3. Files and modules produced or changed

- `app/backend/ot_demo/modules/telemetry/`: observed telemetry/alarm records and
  deterministic integer-millisecond validity classification.
- `app/backend/ot_demo/modules/events/`: typed operational-event record using only
  the approved 15 event types.
- `app/backend/ot_demo/modules/scenario/`: formal run, command, allowed-action and
  complete-snapshot contracts plus the approved formal N0→N3 procedure input.
- `app/backend/ot_demo/application/scenario_coordinator.py`: command handlers,
  transaction ordering, I2 service coordination, revision/idempotency gates,
  acknowledgement and reset semantics.
- `app/backend/ot_demo/infrastructure/scenario_repository.py`: explicit SQLite unit
  of work and typed persistence adapters.
- `app/backend/ot_demo/infrastructure/migrations/002_scenario_transactions.sql`:
  runs, current observations, alarms, derived snapshots, append-only events and
  immutable command-result records.
- `app/backend/ot_demo/api/main.py`: injected `/api/v1` run, command, snapshot and
  event foundations; no operational UI or later-increment endpoint.
- `tests/unit/test_telemetry_and_event_contracts.py` and
  `tests/integration/test_scenario_transactions.py`: I3 domain, transaction,
  persistence, chronology, rollback, repeat and API-boundary tests.
- `pyproject.toml` and the migration regression test: I3 marker and packaged second
  migration coverage. Dependency versions and lock files are unchanged.

## 4. Implementation decisions within the approved baseline

### 4.1 Controlled time and revisions

Scenario timestamps are timezone-aware UTC values validated and serialized with
exact millisecond precision. All age arithmetic uses integer milliseconds; no
wall-clock function or wait contributes to an engineering result. Acknowledgement
may advance controlled scenario time and append its event, but it does not increment
the electrical/topology `state_revision` or publish a false topology/outage change.

### 4.2 Command identity and atomicity

Every state command carries the run ID, actor, expected revision, command ID, type,
target/payload where applicable and controlled request time. The command hash
includes the run identity. An identical duplicate returns its immutable original
result; different content or a different run under the same command ID is rejected.
SQLite `BEGIN IMMEDIATE` transactions contain the complete accepted mutation,
derived recalculation, events, snapshots and command result. Injected failure proves
that no partial run, telemetry, alarm, topology, outage, event or idempotency state
survives rollback.

### 4.3 Topology/outage and action authority

The coordinator constructs I2 inputs from selected immutable configuration, current
telemetry, source availability and active fault state. I2 returns topology, boundary
evaluations and isolation proof; OMS returns outage/customer consequences. Allowed
isolation actions are assembled only from the incident boundary IDs returned by the
I2 proof. The approved formal procedure order is applied to those derived boundaries
as workflow ordering, not used as a replacement incidence lookup.

### 4.4 Reset/history semantics

Reset appends `SCENARIO_RESET`, closes the prior run without deleting its telemetry,
snapshots, alarms, events or command results, and creates a new run ID at the same
controlled initial epoch with normal observed state and fresh derivations. It is not
an undo or in-place history rewrite.

## 5. Requirements and conformance-gate traceability

| Requirement / gate | I3 implementation evidence | I3 status |
|---|---|---|
| `REQ-TEL-001–010` | Typed value/quality/time/revision records; 0–60,000 ms FRESH, 60,001 ms STALE, negative age INVALID_TIMESTAMP; quality remains independent. | I3 telemetry/domain portion complete; I4 adds restoration outcomes. |
| `REQ-ALM-001–005` | CLOSED→OPEN protection transition generates one traceable feeder-trip alarm; acknowledgement records alarm/time/actor without topology revision. | Complete for formal N0→N3. |
| `REQ-EVT-001–011` | Exact 15-type enum, append-only per-run sequence, controlled timestamps, source/entity/prior/new/actor/command/alarm links and N0→N3 emissions. | I3 catalogue/chronology foundation complete; restoration event execution remains I4. |
| `REQ-VAL-014` | Reset closes/references the old run and creates a new clean N0 run while retaining old history and snapshots. | I3 reset mechanism complete; I5 adds validation-execution records. |
| `REQ-NFR-003` | No wall clock, stable sorting/sequence, repeat comparison and controlled identical times produce equal canonical engineering outputs. | I3 portion complete. |
| `REQ-TOP-001–007` | Every accepted device change calls I2 topology and outage services; isolation proof/action eligibility is consumed, not recalculated in scenario code. | Transaction-facing I3 portion complete. |
| `VT-TEL-FRESH-001` | 0, 59,999 and 60,000 ms positive classification; exact 60,000 ms isolation command gate passes. | I3 implementation conformance PASS only. |
| `VT-TEL-STALE-001` | 60,001 ms classifies STALE and blocks the isolation action without mutation. | I3 implementation conformance PASS only; restoration result remains I4. |
| `VT-TEL-UNCERTAIN-001`, `VT-TEL-BAD-001` | Fresh UNCERTAIN/BAD retain FRESH classification but remain invalid through their separate quality result. | I3 implementation conformance PASS only. |
| `VT-TEL-FUTURE-001` | −1 ms classifies INVALID_TIMESTAMP and is never clamped to fresh. | I3 implementation conformance PASS only. |
| `VT-ALM-EVT-001` | Alarm lifecycle, initiating-before-derived event order, exact catalogue and exclusion of validation/defect event types are asserted. | I3 implementation conformance PASS only. |
| `VT-FML-N0-N5-001` N0→N3 portion | N1 850, separate alarm acknowledgement, two isolation transactions/N2, BRK-A reclose/N3 670 with 180 restored. | I3 implementation conformance PASS only. |
| `VT-VAL-RECORD-001` reset clauses | Prior run remains CLOSED/readable; new run starts at N0 with a new ID and sequence; no history is overwritten. | I3 implementation conformance PASS only. |
| `VT-DET-REPEAT-001` controlled-clock/output portion | Reset repeat produces equal topology/outage and canonical event chronology; generated record IDs may differ. | I3 implementation conformance PASS only. |

These results are implementation conformance gates. No I5 formal validation execution
or evidence verdict is created or claimed.

## 6. Verification results and identities

| Verification | Result |
|---|---|
| I3 marked backend suite | PASS — 18 tests |
| Complete backend unit/integration suite | PASS — 63 tests |
| I2 marked regression | PASS — 31 tests |
| I1 marked regression | PASS — 11 tests |
| Frontend scaffold regression | PASS — 1 test |
| Pinned TypeScript/Vite production build | PASS |
| Python dependency consistency | PASS — no broken requirements |
| Git whitespace check | PASS |
| Wall-clock dependency scan | PASS — no current-time/wait input in production code |
| I4+ scope scan | PASS — no restoration decision/execution, validation, UI, defect or exploration orchestration |
| Expected-answer/hard-coding scan | PASS — production scenario logic contains no customer-count or topology-result literals; formal IDs exist only in the controlled procedure definition |
| Canonical v1.0/v1.1/schema bytes and hashes | PASS — all five accepted SHA-256 values unchanged |
| Dependency/lock files | PASS — unchanged |
| Authoritative engineering artefacts | PASS — unchanged |

The clean application build identity captured at implementation commit
`359f594decb376d568785741afafd11870adc484` is:

`a409ce7aeb0512cd2528d654b6f7a3a56ac2bb780754a2d3c2846c10a39b04d8`

Its identity records `git_dirty = false`, Python 3.13.15, Node.js 24.19.0,
npm 11.17.0, the accepted dependency-lock hashes, backend source hash
`c8717bdee9ac0d426602d07ebb1eb531a5b01a17927e4cf38a73d9bb4cd0287b`
and the unchanged frontend bundle hash.

The accepted canonical configuration identities remain:

- v1.0 data `67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3`;
- v1.0 manifest `d0243fae46e6a5d403855953e14cdedbcdae9c71af7761a1aba49f88470bc12d`;
- v1.1 data `7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281`;
- v1.1 manifest `e0f16f3acdf2e85aa04cd23bb4b584a868626117b68f682d1219821a36857662`;
- shared schema `ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c`.

## 7. Implementation-assurance findings

- QA-024 records that default datetime JSON omitted `.000` for whole-second values.
  The controlled timestamp type now always emits exact UTC millisecond precision,
  and focused serialization/boundary tests pass.
- QA-025 records that the first command-contract draft relied on the API path for
  run identity. The final envelope carries `scenario_run_id`, includes it in the
  command hash and rejects path/envelope or cross-run command-ID mismatch.
- QA-026 records that the first action-assembly draft iterated the formal procedure
  sequence directly. The final implementation takes the actual boundary set only
  from I2 isolation proof and uses the procedure definition solely to order derived
  formal actions.

All three findings are corrected and verified on the I3 branch but remain pending
independent review before closure under an accepted I3 baseline.

## 8. Stop conditions, dependencies and regression implications

No I3 stop condition remains open. No failed test was bypassed, no requirement or
expected result was changed, and no authoritative engineering choice was invented in
code.

I4 must extend the coordinator with restoration candidate, assessment, invalidation
and execution binding without changing the I3 clock, command identity, revision,
rollback, event-order or reset contracts. I5 must create formal validation/evidence
records separately from operational events. I6 must consume backend allowed actions
and projections rather than toggle state directly. I7/I8 must not rewrite preserved
run history or convert exploratory records into formal evidence.

**V2 Automation Candidate — transaction/evidence conformance.** Rechecking command,
revision, telemetry, topology, outage, alarm and event consistency after every
success/rollback is repetitive and evidence-heavy. A future assurance tool could
flag incomplete or inconsistent linked records for engineer review while leaving V1
transaction behaviour and judgement unchanged.

## 9. Review and progression gate

The completed branch `agent/i3-scenario-transactions` is pushed for independent
review with its implementation and administrative closeout history preserved. I3
shall not be merged until accepted. I4 has not begun and requires separate user
authorisation from reviewed `main` after I3 acceptance and merge.
