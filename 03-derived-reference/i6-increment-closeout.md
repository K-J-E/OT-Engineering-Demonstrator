---
Status: I6 assurance corrections implemented — pending independent re-review
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-10
Increment: I6 — Operational UI
---

# I6 Increment Closeout — Operational UI

## 1. Authorisation, branch and implementation boundary

The user explicitly authorised I6 only. Branch `agent/i6-operational-ui` was
created from the exact accepted I5 `main` baseline
`81e83e5000743e4709b40ea9862315ce16c376c6`.

The bounded implementation commit is
`b7993d9bc2ca224df8f5721e372c0d4e39d69366`. It implements the local
operational review workspace, backend projection assembly, fixed one-line,
configured/observed/derived inspection, telemetry/events, restoration and formal
validation presentation, plus component and browser assurance.

Independent review accepted I6 in substance and independently accepted QA-033's
JSON-transport correction. The targeted assurance-correction commit
`09622018d8bbd57adf8da818d3d0d5c253f49a0b` implements QA-034 and QA-035:
FORMAL-only validation progress and continuously visible full scenario-run
identity. It does not change engineering behaviour or add later-increment scope.

I1–I5 remain the engineering and transaction authorities. I6 composes and renders
their controlled outputs; it does not calculate topology, energisation, outage,
customer impact, isolation, restoration outcomes, N-state transitions or
validation determinations in the frontend.

No I7 investigation/correction workflow, I8 Exploration orchestration/export,
I9 packaging, real-control interface, automation/AI feature, new requirement,
engineering rule, expected result or authoritative document change was added.

## 2. Authoritative sources and requirements used

Before implementation, the complete mandatory I6 source set in Implementation
Control Plan Section 9 was read:

- Requirements Specification presentation paths for `REQ-NET-*`, `REQ-TOP-*`,
  `REQ-TEL-*`, `REQ-ALM-*`, `REQ-OUT-*`, `REQ-RST-*`, `REQ-EVT-*`,
  `REQ-VAL-*`, `REQ-NFR-001`, `REQ-NFR-005–007` and `REQ-NFR-009`;
- Network Model Sections 13–16;
- System Architecture Sections 13, 17–18, 20–21 and 26.3;
- Workflow Design Sections 9–14 and 18–21;
- Demonstrator Design Sections 13–19, 23–25 and 27–29; and
- Validation Plan Sections 6–10 and 13–15, including
  `VT-FML-N0-N5-001`, `VT-ALM-EVT-001`, the five telemetry
  boundary/quality cases, `VT-VAL-RECORD-001` and `VT-NFR-REVIEW-001`.

Accepted DC-001, DC-002 and DC-003, the I1–I5 contracts/services and current
derived controls were also inspected. Authoritative Word/PDF artefacts and change
records remained read-only and unchanged.

## 3. Files and modules produced or changed

- `app/backend/ot_demo/modules/workspace/`: immutable I6 read-model contracts
  that keep configured, observed, derived, fault and evidence information
  distinct.
- `app/backend/ot_demo/application/workspace_service.py`: backend-owned
  composition of I1–I5 records, formal workflow context, current allowed actions,
  validation progress and presentation-only positions.
- `app/backend/ot_demo/api/`: local runtime composition, workspace query
  endpoints and explicit JSON-transport-to-strict-domain conversion.
- `config/presentation/network-one-line.v1.json`: presentation coordinates only;
  no connectivity or engineering state.
- `app/frontend/src/features/` and `components/network/`: run setup, persistent
  context, operational view, fixed Cytoscape one-line, entity inspector,
  telemetry/events, restoration and validation/evidence views.
- `app/frontend/src/api/`: typed projection/action contracts and HTTP client.
- `app/frontend/playwright.config.ts` and `tests/e2e/`: isolated local runtime and
  real-browser formal N0–N5 workflow.
- component/integration tests, frontend scripts/configuration, pytest I6 marker,
  runtime-data ignore rule and derived closeout/source-map/register updates.

Dependency versions and lockfiles are unchanged.

## 4. Information ownership and interaction treatment

The browser receives complete owner-produced projections. Configuration fields,
observed telemetry value/quality/timestamp, derived energisation/source/outage,
fault status and immutable validation evidence are separate contracts and visual
groups. QA-003 is explicit: configured normal feeder load is shown beside, never
relabelled as, derived currently supplied load.

The one-line uses backend-provided fixed presentation coordinates with drag and
topology editing disabled. Cytoscape renders supplied nodes/edges; position cannot
create or change connectivity. A textual network-state table provides an
accessible alternative.

Every operational button comes from backend `allowed_actions`, including target,
availability, reason code, explanation, expected revision, proposed controlled
time and confirmation requirement. The frontend neither infers eligibility nor
encodes the N0–N5 transition sequence. Confirmation remains explicit for
simulated switching.

Telemetry exposes value, quality, timestamp, age, freshness, validity and reason
codes as text as well as styling. GOOD/UNCERTAIN/BAD and
FRESH/STALE/INVALID_TIMESTAMP remain independent. The approved 15 operational
event types and backend event ordering are unchanged and visually separate from
validation execution/evidence records.

Restoration presents NO_CANDIDATE, BLOCKED, REJECTED and PERMITTED as distinct
engineering outcomes with candidate, permissive, calculation, evidence and
binding detail. Missing attributable load produces no fabricated calculation.
Validation shows 24 accepted definitions separately from execution/PASS/FAIL
counts. The formal N0–N5 definition has no I5-authorised structured comparison,
so I6 correctly leaves its determination NOT DETERMINED and finalisation disabled
rather than inventing a verdict.

The UI continuously identifies the fictional, local, simulated and conceptual OT
boundary. It contains no implication of connection to real equipment.

## 5. Formal browser result and engineering checkpoints

The Playwright workflow starts corrected v1.1 through the public UI and uses only
backend-returned actions. It starts the formal validation execution, captures
N0–N5 evidence checkpoints and proves:

| Checkpoint | Browser-observed backend result |
|---|---|
| N0 | all eight sections energised; 0 affected customers |
| N1 | formal fault/protection result; 850 affected customers |
| N2 | both DC-003 incident boundaries operated and isolation proven |
| N3 | BRK-A normal-source restoration complete; 670 affected customers |
| N4 | revision 4; PERMITTED; 1.500 MW transfer; 5.700/6.000 MW; 95.0%; 450 proposed restored |
| N5 | radial alternate restoration; 450 restored; 220 remain affected |

The test reloads at N3 and proves the current run is re-queried from backend state
rather than reconstructed from browser memory. At N5 it proves FDR-B configured
normal load remains 4.200 MW while derived supplied load is 5.700 MW. It also
checks formal evidence remains NOT DETERMINED, the event chronology includes the
approved alarm acknowledgement/restoration assessment and exactly four switching
actions, and no false validation PASS appears.

These are I6 implementation-conformance gates, not a claim that the full Step 9
formal validation campaign has been executed.

## 6. QA finding and resolution

QA-033 records a genuine I6 integration finding. Strict domain request models
correctly reject raw JSON strings for UUID, enum and UTC-time values. The first API
assembly used those strict models directly as HTTP request bodies, which blocked
browser initialisation.

The correction adds explicit JSON transport payloads at the API boundary and
converts their parsed typed values into the unchanged strict domain contracts
before calling the I3/I5 services. It does not weaken domain validation or change
engineering behaviour. The passing full browser flow exercises initialisation,
scenario commands and validation checkpoint requests through the corrected
boundary. QA-033 is independently verified; final closure under the I6 baseline
awaits acceptance of the complete increment.

QA-003 was not reopened. Its I6 presentation treatment is implemented and awaits
review with the increment.

QA-034 records that the first progress aggregator counted all 24 definitions and
all executions while its UI was explicitly labelled FORMAL. The corrected read
model filters both definitions and executions by `evidence_class == FORMAL`.
Regression proves active/finalised exploratory executions with PASS, FAIL and
BLOCKED-TEST verdicts cannot affect any FORMAL total. The interface now states
that FORMAL scope contains 21 of 24 controlled catalogue definitions, preserving
the separate total-catalogue fact without presenting I8 exploratory records.

QA-035 records that the first context ribbon exposed the complete run UUID only
through hover and assistive text. The ribbon now visibly presents the short ID for
scanning and the complete UUID for provenance. Component and browser coverage
prove the full identity is visible without hover and remains unchanged from N0
through N5 while the persistent ribbon crosses workspace views.

## 7. Verification evidence

| Gate | Result |
|---|---|
| Complete backend unit/integration suite | PASS — 100 tests |
| I6 backend projection/integration tests | PASS — 3 tests |
| React/Cytoscape component assurance | PASS — 9 tests |
| Playwright formal v1.1 N0–N5 workflow | PASS — 1 test in Chromium |
| Exact-toolchain clean `npm ci` | PASS — 120 packages, 0 vulnerabilities |
| TypeScript/Vite production build | PASS — Node 24.19.0 / npm 11.17.0 |
| Python dependency consistency | PASS — no broken requirements |
| Git whitespace check | PASS |
| Fixed one-line/no-edit component gate | PASS |
| Configured/observed/derived/fault/evidence separation | PASS |
| Telemetry quality/freshness presentation | PASS |
| Backend-only action availability and reasons | PASS |
| NO_CANDIDATE/BLOCKED/REJECTED/PERMITTED presentation | PASS |
| 24 definitions not treated as execution/PASS | PASS |
| FORMAL progress isolation | PASS — 21 FORMAL of 24 total; exploratory ACTIVE/finalised/PASS/FAIL/BLOCKED-TEST records have zero effect |
| Complete persistent run UUID | PASS — visibly unchanged from N0 through N5 without hover |
| Exact 15 operational event types | PASS — unchanged |
| Frontend engineering-calculation/hard-coding scan | PASS |
| I7+ leakage scan | PASS |
| Canonical configuration/catalogue integrity | PASS — unchanged |
| Dependency definitions/locks | PASS — unchanged |
| Authoritative engineering/change-control artefacts | PASS — unchanged |

The production bundle warning for a single 673 kB minified Cytoscape/React chunk
is non-blocking for this local graduate demonstrator; no performance or delivery
criterion failed. Code splitting remains optional I9 packaging polish and does not
justify dependency or architecture change in I6.

## 8. Controlled identities

The clean build identity at bounded implementation commit
`b7993d9bc2ca224df8f5721e372c0d4e39d69366` is:

`2c5123bfab1359865ff4a27285bd14a2911b38dd1dfcc56442c7384d37e79d28`

The clean build identity after the QA-034/QA-035 implementation correction at
`09622018d8bbd57adf8da818d3d0d5c253f49a0b` is:

`c424327a404608c817ec34c749dbcbfce671044e99a195d6168a828d2c2c640c`

The corrected identity records `git_dirty = false`, Python 3.13.15, Node 24.19.0, npm 11.17.0,
requirements-lock hash
`0c68ce8fad5cbc3b877ade42f7a6d0400b50f0f2a52cee262734c7df10b41a64`,
frontend-lock hash
`b628f98c999bcf66ae3bbdf067e961ced6b56f3db03a7339f4ca54e20ada3177`,
backend-source hash
`df0584950c10868de31a771938336508cbf72249643400eabfbd8a640e3fc895`
and frontend-bundle hash
`ff464dc251efdb33b5ae2c50ea6f75efda56c4d4446324a5022f08a2dfc705b2`.

Accepted controlled input hashes remain:

- v1.0 data `67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3`;
- v1.0 manifest `d0243fae46e6a5d403855953e14cdedbcdae9c71af7761a1aba49f88470bc12d`;
- v1.1 data `7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281`;
- v1.1 manifest `e0f16f3acdf2e85aa04cd23bb4b584a868626117b68f682d1219821a36857662`;
- shared schema `ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c`;
- validation catalogue `e4b1fb616fb4f0605c19129f18746bfae48278ed35fbb971aac4f690fd32bcc1`;
  and
- validation manifest `8bc2f16e6dd475a56a5c5dc3ed52ca46caafc77c08bd858de3f2d748c4dfe714`.

## 9. Unresolved items, regression implications and stop conditions

No I6 stop condition remains open. No test was bypassed; no missing engineering
choice was guessed; no frontend engineering authority, editable topology,
unlabelled evidence deficiency, configured/derived-load conflation, real-control
implication or later-increment workflow was introduced.

Independent review should focus on projection ownership, information-class
separation, action availability/reasons, the JSON transport correction, formal
workflow checkpoint values, fixed one-line behaviour and the absence of I7/I8
scope. Later increments must preserve all I1–I6 regression gates.

**V2 Automation Candidate — evidence-led interface regression.** Comparing the
approved N-state answer key, API projection, one-line labels, tables and captured
browser evidence is repetitive and error-prone. A future assurance tool could
generate cross-view comparison reports and flag presentation drift for engineer
review without changing V1 calculations or verdict authority.

## 10. Review and progression gate

The I6 implementation commit and this derived closeout are to be pushed on
`agent/i6-operational-ui` for independent re-review. I6 remains unmerged and is
not the accepted implementation baseline until separately reviewed and accepted.

**I7 has not started. No later increment may begin automatically.**
