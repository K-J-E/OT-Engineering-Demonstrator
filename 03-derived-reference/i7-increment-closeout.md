---
Status: I7 implementation complete — pending independent review
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-10
Increment: I7 — Investigation/Correction
---

# I7 Increment Closeout — Investigation/Correction

## 1. Authorisation, branch and boundary

The user explicitly authorised I7 only. Branch `agent/i7-investigation-correction`
was created from exact accepted I6 `main` commit
`3860c4c4a83bf9cec9ac04e2a229651b45f3070f`.

I7 implements the approved DEF-001 consequence-to-source investigation,
read-only configuration comparison, immutable defect/correction records,
same-build corrected direct repeat and corrected full-regression evidence. It
consumes the accepted I1 configuration/build, I2 topology/outage, I3
transaction/time/event, I4 restoration, I5 validation/evidence and I6
presentation authorities.

No I8 Exploration orchestration/export, I9 packaging/final campaign, arbitrary
fault investigation, configuration editing, external OT integration, AI,
autonomous correction, real switching/control, new operational-event type,
engineering rule or authoritative-document change was added.

Independent review accepted I7 in substance and accepted QA-036's bounded
cross-configuration replacement-run concept in principle. Correction commit
`ae645053af1cf6b464bf411166b328f0b6abc1d3` addresses the two targeted
assurance findings QA-037 and QA-038 without redesigning the increment.

## 2. Mandatory sources and requirements

Before implementation, the complete Implementation Control Plan Section 10
reading set was inspected:

- Requirements Specification `REQ-CFG-001–012`, `REQ-VAL-005`,
  `REQ-VAL-010–012` and applicable `REQ-TOP-*`/`REQ-OUT-*` rows;
- Network Model Section 16.5 and Sections 17–18.7;
- System Architecture Sections 19–20 and 26.4–26.5;
- Workflow Design Sections 15–17 and 19;
- Demonstrator Design Sections 19, 21–22, 27–28 and 35.4–35.5; and
- Validation Plan `VT-TOP-DEF-001`, `VT-CFG-INV-001`,
  `VT-DET-REPEAT-001`, `VT-FML-N0-N5-001` and Sections 11, 13–15.

Accepted DC-001–DC-003 and the I1–I6 implementation contracts were also
inspected. Authoritative engineering artefacts remained read-only and unchanged.

## 3. Produced modules and records

- `modules/investigation/` defines immutable comparison, investigation,
  DEF-001, COR-001, repeat-link, action and workspace read models.
- `InvestigationService` assembles evidence only from actual package contents
  and owner-produced scenario, topology, outage and validation records.
- `InvestigationRepository` plus SQLite migration 005 persist separate defect,
  correction and repeat-link records with database-level update/delete guards.
- The scenario coordinator adds a bounded replacement-run operation that closes
  and preserves the prior run, applies the accepted restoration-assessment
  invalidation treatment when required, and loads a separately identified
  existing package under the same backend-controlled application build.
- Typed local HTTP endpoints expose backend-owned investigation projections and
  commands; React renders them without calculating source attribution, outage
  arithmetic, package differences, root cause, correction acceptability or
  validation verdicts.
- The I7 workspace progressively reveals the controlled evidence sequence and
  does not expose the package difference until the preceding consequence,
  telemetry, source-path and OMS evidence has been reviewed.

## 4. Consequence-to-source evidence

The implementation executes the real accepted v1.0 package through the same
generic I2/I3/I5 authorities used for v1.1. It preserves the actual result rather
than intercepting it:

1. `VT-TOP-DEF-001` observes 400 affected customers and validation FAIL.
2. SEC-A1/A2 are de-energised while SEC-A3/A4 remain energised.
3. BRK-A is OPEN with trustworthy, fresh telemetry, so the observed protection
   state is not altered to explain the discrepancy.
4. SEC-A3/A4 have actual source attribution to FDR-B.
5. The derived active source path reaches them through the configured
   SEC-B3/SW-A23 relationship.
6. OMS correctly sums CZ-A1/CZ-A2 as 180 + 220 = 400 for the topology it receives.
7. Read-only comparison of the loaded immutable packages discovers exactly one
   difference: SW-A23 endpoint 1 is SEC-B3 in v1.0 and SEC-A2 in v1.1.

The resulting engineering judgement is recorded in separate DEF-001 and COR-001
records. No topology, OMS or comparison function contains a configuration-version,
DEF-001, section-result or expected-customer conditional.

## 5. Correction, repeat and regression

COR-001 records selection of the already-instantiated immutable v1.1 package; it
does not edit or generate configuration. The original v1.0 run, failed execution
and evidence remain queryable.

The linked direct repeat creates a new v1.1 run/execution/evidence identity under
the same backend-controlled application build and same `VT-TOP-DEF-001`
definition identity/hash. Generic topology/outage processing produces 850 affected
customers and the I5 comparison authority produces PASS.

The subsequent v1.1 `VT-FML-N0-N5-001` regression creates another run and six
evidence checkpoints. It proves N1 = 850 affected, N3 = 670 affected, N4 revision
4 = PERMITTED with 1,500 kW transfer, 5,700/6,000 kW, 95.0% and 450 proposed
restored, and N5 = RADIAL with 450 restored and 220 affected.

The accepted machine definition has no structured expected-value comparison for
the full N0–N5 execution. I7 therefore preserves all six owner-produced evidence
snapshots while leaving that execution ACTIVE/NOT DETERMINED. It does not invent
a second verdict engine or claim a formal I9 campaign result.

## 6. QA finding

QA-036 records a genuine integration boundary: accepted I3 RESET intentionally
retains the current configuration, whereas the I7 correction workflow must start
a new run using a different already-approved package. The bounded replacement-run
operation preserves history, closes the previous mutable run, emits only the
existing operational-event types and loads v1.1 through the accepted
configuration authority under the same build. It changes neither reset semantics
nor package contents. Independent I7 review accepted this concept in principle;
final I7 acceptance remains pending.

QA-037 records that the first historical workspace read reused the current-build
mutation guard, which made a completed chain unreadable after the executable
advanced. Historical reads now validate the preserved execution on its own
identity, and same-build proof is calculated solely from linked stored execution
build IDs. All mutation boundaries separately require the current build to equal
the failure build; historical actions are explicitly
`HISTORICAL_BUILD_READ_ONLY`. Regression reopens a complete build-A chain under
build B and proves it remains reviewable, then proves an incomplete build-A chain
cannot be extended at any defect/correction/repeat/regression boundary under
build B. QA-037 is closed in implementation pending independent re-review.

QA-038 records that the first replacement-run path closed a prior run without the
accepted I4 reset invalidation treatment. Reset and replacement now share one
history-preserving close operation. A focused N4 regression proves a current
PERMITTED assessment and its original evidence remain preserved, an immutable
invalidation record is created, `RESTORATION_ASSESSMENT_INVALIDATED` precedes
`SCENARIO_RESET`, the prior run becomes CLOSED and the separately identified new
run starts at N0. The 15-type event catalogue is unchanged. QA-038 is closed in
implementation pending independent re-review.

## 7. Verification evidence

| Gate | Result |
|---|---|
| Complete backend unit/integration suite | PASS — 106 tests |
| I7 backend chain/integrity tests | PASS — 6 tests |
| React/Cytoscape component suite | PASS — 10 tests |
| Chromium formal I6 and I7 investigation workflows | PASS — 2 tests |
| Exact-toolchain clean frontend install | PASS |
| Pinned TypeScript/Vite production build | PASS |
| Python dependency consistency | PASS |
| v1.0 400/FAIL preserved | PASS |
| Ordered consequence-to-source chain | PASS |
| Exact one-difference package comparison | PASS |
| Separate immutable DEF-001/COR-001/link records | PASS |
| Same-build v1.1 850/PASS direct repeat | PASS |
| Corrected six-checkpoint N0–N5 regression | PASS |
| Complete chain review under later build | PASS — stored build identities retain same-build proof |
| Incomplete old-build mutation boundary | PASS — historical read-only at every continuation step |
| N4 replacement assessment invalidation | PASS — assessment/event/invalidation preserved; new run N0 |
| Exact 15 operational-event types | PASS — unchanged |
| Exact 24 validation definitions and 286 RTM relationships | PASS — unchanged |
| Configuration/catalogue/hash integrity | PASS — unchanged |
| Dependency definitions/locks | PASS — unchanged |
| Hard-coded result/root-cause scan | PASS |
| I8+ leakage scan | PASS |
| Authoritative engineering/change-control artefacts | PASS — unchanged |

These are I7 implementation-conformance gates, not a claim that the I9 final
validation campaign has been executed.

## 8. Controlled identities

Accepted controlled hashes remain:

- v1.0 data `67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3`;
- v1.0 manifest `d0243fae46e6a5d403855953e14cdedbcdae9c71af7761a1aba49f88470bc12d`;
- v1.1 data `7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281`;
- v1.1 manifest `e0f16f3acdf2e85aa04cd23bb4b584a868626117b68f682d1219821a36857662`;
- network schema `ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c`;
- validation catalogue `e4b1fb616fb4f0605c19129f18746bfae48278ed35fbb971aac4f690fd32bcc1`;
- validation manifest `8bc2f16e6dd475a56a5c5dc3ed52ca46caafc77c08bd858de3f2d748c4dfe714`;
- backend lock `0c68ce8fad5cbc3b877ade42f7a6d0400b50f0f2a52cee262734c7df10b41a64`; and
- frontend lock `b628f98c999bcf66ae3bbdf067e961ced6b56f3db03a7339f4ca54e20ada3177`.

The bounded I7 implementation commit is
`785b2b21d77e66466ade3df1d69f75e9e241f9a7`. Its clean application build ID is:

`1d66e55323b5b80040e00ea2036d087da1e3a3aa5863ff1ac7635dbcacec561b`

The identity records `git_dirty = false`, Python 3.13.15, Node.js 24.19.0,
npm 11.17.0, backend-source hash
`a7e9502d096bbfcab5791ffb4d592fccd4fadf45f87acf8bdd00077790c54c99`
and frontend-bundle hash
`e92d6d2281c9a4417a3402086c19cb67d35cc2df4c7a9e7df01555fa1955c0c9`.

The clean QA-037/QA-038 correction commit is
`ae645053af1cf6b464bf411166b328f0b6abc1d3`. Its application build ID is:

`e90a18b6d3124e1cf169943b79d74343ecee35bf8fefdf2f8fa7b43dfda260ff`

The corrected identity records `git_dirty = false`, the same pinned toolchain and
lock hashes, backend-source hash
`480393276e42ceb2263722dbe7b5d52d34415ce017f1417fc3fd698471689194`
and unchanged frontend-bundle hash
`e92d6d2281c9a4417a3402086c19cb67d35cc2df4c7a9e7df01555fa1955c0c9`.

## 9. Review gate

I7 is complete on its dedicated branch and pending independent re-review. Draft
PR #7 remains open and must not be merged until accepted. I8 has not begun and
requires separate user authorisation after the reviewed I7 baseline is
incorporated into `main`.

## V2 Automation Candidate

**V2 Automation Candidate — evidence-chain assembly and assurance.** Gathering
SCADA, source-path, topology, OMS, package-difference, provenance and regression
records into a traceable investigation is manual and evidence-heavy. A future
assurance assistant could assemble and cross-check the chain while preserving
engineer ownership of root-cause judgement and correction approval.
