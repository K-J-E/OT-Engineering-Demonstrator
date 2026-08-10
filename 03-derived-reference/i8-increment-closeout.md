---
Status: Accepted I8 implementation baseline
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-10
Increment: I8 — Exploration and Export
---

# I8 Increment Closeout — Exploration and Export

## 1. Authorisation, branch and boundary

The user explicitly authorised I8 only. Branch
`agent/i8-exploration-export` was created from exact accepted I7 `main`
commit `b5cf733e2ebc30f7fd38e05b6e11377bc2ce540c` after verifying the clean,
synchronised I7 baseline.

Final independent engineering/implementation review accepted the complete I8
branch at reviewed tip `111df44a425731dc7f44c437c1d675e5dac85263`.
QA-008 is accepted as implemented under the I8 baseline and QA-040 is
independently verified closed. This acceptance update is administrative only;
it changes no engineering behaviour, implementation logic, controlled package,
authoritative artefact or dependency.

I8 implements corrected-v1.1 Exploration Mode and immutable evidence ZIP
export. It consumes the accepted I1 configuration/build identity, I2
topology/outage, I3 transaction/time/event, I4 restoration, I5
validation/evidence, I6 projection-only UI and I7 investigation/history
authorities.

No I9 packaging/final campaign, new electrical analysis, network editor,
configuration generator, alternate topology/restoration engine, client-side
engineering calculation, new operational-event type, dependency change,
authoritative-document change, AI feature or real switching/control was added.

## 2. Mandatory source review

Before implementation, the complete I8 source set named by Implementation
Control Plan Section 11 was read:

- Requirements Specification `REQ-EXP-001–007`, applicable `REQ-RST-*`,
  `REQ-VAL-009` and `REQ-NFR-008`;
- Network Model Sections 15.1, 17.12 and 18;
- System Architecture Sections 17.2–17.3, 20 and 26;
- Workflow Design Sections 13–14, 19 and 27.1–27.3;
- Demonstrator Design Sections 20–21, 27–29 and 35; and
- Validation Plan `VT-EXP-ALL-001`, `VT-EXP-ROLE-001`,
  `VT-EXP-SEPARATION-001`, `VT-PKG-EVIDENCE-001`, `VT-NFR-REVIEW-001`
  and Sections 12–15.

Accepted DC-003 and I1–I7 implementation/regression controls were also
inspected. No source contradiction or stop condition was found. The
authoritative engineering artefacts remain unchanged.

## 3. Part A — Exploration Mode

The run initialisation contract now accepts a selected fault section only as
transient EXPLORATION run input. The backend validates the selection against
the actual corrected v1.1 section set and fixes the run to configuration
`network-configuration-v1.1`, mode `EXPLORATION` and evidence class
`EXPLORATORY`. FORMAL remains the controlled SEC-A2 path. Starting another mode
closes and preserves the current run and creates a separately identified run;
neither mode is converted in place.

The scenario coordinator derives the selected section's feeder, source
breaker, incident boundaries, source paths, outage consequence, alternate
role, transfer group and restoration result through the existing I2–I4
authorities. Formal procedure ordering remains formal-only; exploration
evaluates each configuration-derived incident boundary independently for OPEN
eligibility. A `PROVEN_OPEN` boundary is satisfied without redundant action, a
`PROVEN_CLOSED` boundary remains individually eligible even if another incident
boundary is `UNPROVEN`, and the unproven boundary still prevents overall
isolation. Backend command acceptance uses the same per-boundary gate as the
allowed-action projection, followed by the existing full recalculation. A
generic prospective
topology check makes a normal-source reclose available only when it preserves
fault isolation and restores healthy load. If no safe normal reclose exists,
the isolated exploration topology may proceed to the existing restoration
assessment authority, which can legitimately return `NO_CANDIDATE`.

The browser obtains the selectable section set and every operational action
from backend projections. It continuously identifies EXPLORATION,
EXPLORATORY, corrected v1.1, selected section, full run ID, derived workflow
stage, state revision and assessment. It does not present exploration as
formal N0–N5 evidence or calculate feeder roles, boundaries, outage,
restoration candidates or outcomes in React.

The three accepted EXPLORATORY definitions use separate I5 executions and
immutable checkpoints. Their definitions, records and controls are presented
separately from the QA-034 FORMAL progress projection. Because the accepted
definitions have no authorised structured comparison, I8 preserves
`NOT DETERMINED` and does not invent PASS.

## 4. Exploration engineering results

Exhaustive configuration-driven tests cover every represented section and the
accepted DC-003 incident boundaries. Runtime code contains no eight-section
answer table or expected-outcome lookup.

- `SEC-A1`: BRK-A/SW-A12 boundaries; 2,450 kW transfer; FDR-B resulting
  6,650/6,000 kW (110.8%); `REJECTED`.
- `SEC-A2`: SW-A12/SW-A23 boundaries; 1,500 kW transfer; FDR-B resulting
  5,700/6,000 kW (95.0%); `PERMITTED`.
- `SEC-A3`: SW-A23/SW-A34 boundaries.
- `SEC-A4`: SW-A34/TS-01 boundaries; `NO_CANDIDATE` without a manufactured
  path.
- `SEC-B1`: BRK-B/SW-B12 boundaries.
- `SEC-B2`: SW-B12/SW-B23 boundaries; affected/alternate roles reverse to
  FDR-B/FDR-A; B3+B4 transfer 1,900 kW; FDR-A resulting 5,100/5,500 kW
  (92.7%); `PERMITTED`.
- `SEC-B3`: SW-B23/SW-B34 boundaries.
- `SEC-B4`: SW-B34/TS-01 boundaries.

The SEC-A4 assurance case proves trustworthy/fresh OPEN TS-01 satisfies its
boundary without a redundant OPEN command. The same last-reported OPEN with
stale evidence remains `UNPROVEN`, blocks isolation and still does not create
a meaningless OPEN action. Separate equivalent SEC-B2 runs use different run
and assessment identities while producing the same engineering result.

These values are test oracles from the accepted Network Model/Validation Plan;
they are not runtime conditions.

## 5. Part B — Evidence ZIP export

The new evidence-export module accepts only a preserved validation-execution
identity. The backend retrieves immutable execution, evidence, run,
configuration, catalogue and applicable I7 investigation records; the browser
cannot submit expected/observed values, verdicts, build/configuration identity,
hashes or engineering calculations.

Each request creates a new `PKG-<short-id>-<FORMAL|EXPLORATORY>.zip` under the
logical `evidence/exports/` area. Generated exports are ignored as runtime
output and cannot become source/configuration input. A database-backed
append-only package record preserves source and generation build IDs,
configuration, execution, run, evidence identities, archive path and hashes;
database triggers reject package update/delete.

Every ZIP contains:

- `report.html` with fictional/local/simulated notice, classification,
  provenance, expected/observed/determination and limitations;
- canonical JSON configuration, definition, execution, run, telemetry,
  topology, outage, restoration, operational-event, source-index and evidence
  snapshot records;
- applicable immutable DEF-001, COR-001 and repeat-link/history records;
- `figures/network-evidence.svg` generated from the preserved evidence
  snapshot rather than current live state;
- `README.txt`; and
- a non-self-referential `manifest.json` listing byte size and SHA-256 for
  every other package entry.

The service reopens each completed archive, verifies its exact entry set,
path safety, byte sizes, SHA-256 values and manifest bytes, then records the
archive SHA-256. Tests independently repeat that verification. Repeated
exports receive new identities/paths and preserve prior ZIPs.

FORMAL export requires a finalised execution with evidence. EXPLORATORY export
requires evidence and a closed EXPLORATION source run. Classification is
prominent in the report, README, manifest, immutable package record and UI.
The I7 chain export preserves the original v1.0 400/FAIL, DEF-001, COR-001,
same-build v1.1 850/PASS direct repeat and six-checkpoint corrected regression;
the regression remains ACTIVE / NOT DETERMINED.

## 6. Produced implementation areas

- `modules/evidence_export/`, `EvidencePackageRepository` and migration 006;
- evidence-package generate/list/candidate/download API boundaries and runtime
  composition;
- EXPLORATION run selection, validation and separate-run orchestration;
- generic exploration action/stage and exploratory validation projections;
- Exploration setup, context, validation and evidence-library UI treatment;
- generated-output ignore policy; and
- focused backend, component and Chromium coverage.

## 7. QA disposition

QA-008 is accepted as implemented under the I8 baseline.
QA-040 records that the first Exploration action projection reused a single
lexically ordered "next target" result, allowing an earlier `UNPROVEN` boundary
to suppress another independently `PROVEN_CLOSED` incident boundary. The
bounded correction leaves the FORMAL next-target procedure unchanged and gives
EXPLORATION a per-actual-boundary evidence gate shared by projection and command
acceptance. Both SEC-A2 asymmetric permutations prove order independence;
post-operation evidence proves the operated boundary becomes `PROVEN_OPEN`, the
other remains `UNPROVEN`, overall isolation remains false and full action/proof
recalculation occurs. Final independent review verified QA-040 closed under the
accepted I8 baseline.

The accepted QA-003, QA-007, QA-009, QA-014, QA-027, QA-031, QA-032 and
QA-034–QA-039 controls remain under passing regression. No authoritative
engineering change or new design decision was required.

The current-baseline manifest, README, implementation control plan, source map
and QA register were refreshed as derived navigation/control aids. Their update
records the accepted I8 status without altering authoritative engineering
meaning.

## 8. Verification evidence

| Gate | Result |
|---|---|
| Complete backend unit/integration suite | PASS — 120 tests |
| Focused I8 backend exploration/export suite | PASS — 14 tests |
| QA-040 asymmetric boundary eligibility | PASS — both lexical permutations; projection/command/recalculation agree |
| FORMAL controlled isolation ordering | PASS — unchanged |
| All-eight corrected-v1.1 section selection/incidence | PASS |
| SEC-A4 fresh OPEN / stale last-OPEN DC-003 case | PASS |
| Representative PERMITTED / REJECTED / NO_CANDIDATE results | PASS |
| Equivalent-run deterministic engineering result | PASS — new run/assessment identities |
| FORMAL/EXPLORATORY run, execution and progress separation | PASS |
| Evidence-package contents and independent SHA-256 verification | PASS |
| FORMAL, EXPLORATORY and I7 preserved-chain export | PASS |
| Non-overwrite and immutable package-register controls | PASS |
| React/Cytoscape component suite | PASS — 16 tests across 4 files |
| Focused I8 component coverage | PASS — 4 tests |
| Chromium formal, investigation and Exploration/export workflows | PASS — 3 tests |
| Exact-toolchain clean frontend install | PASS — Node 24.19.0 / npm 11.17.0 |
| Pinned TypeScript/Vite production build | PASS |
| Python dependency consistency | PASS |
| Exact 15 operational-event types | PASS — unchanged |
| Exact 24 definitions / 124 requirements / 286 RTM relationships | PASS — unchanged |
| Canonical configuration/schema/catalogue/manifest hashes | PASS — unchanged |
| Dependency definitions/locks | PASS — unchanged |
| Runtime section/outcome/boundary hard-coding scan | PASS — answer keys only in tests |
| Mutable-live-state export review | PASS — package sources are preserved evidence records |
| I9+ leakage scan | PASS |
| Authoritative engineering/change-control artefacts | PASS — unchanged |

These are I8 implementation-conformance gates, not a claim that the I9 final
validation campaign has been executed.

## 9. Controlled identity and integrity

The I8 implementation commit is
`aa2edc57fdf6d28777c183183f47fdb971529ac7`. Its clean application build ID is:

`202b4faf3e3fb4d41cd92dee4986a9e28a35c8c7b4bb9750b47497b3efc30979`

The identity records `git_dirty = false`, Python 3.13.15, Node.js 24.19.0,
npm 11.17.0, backend-source hash
`c1c4628d33afde45d091b88d1ea198e3c3308c65fb9a7e9c77ab6ef1c9b4cbc2`
and frontend-bundle hash
`c7a29657a65f831e41f70ac59950ebe4223c781cba6a916def2510d17bcec037`.

The bounded QA-040 correction commit is
`2f5701482e5e7d52ac098f0a89ab1ff939704ddd`. Its clean application build ID is:

`960ce33dcb707a4d7054bc78b15a4b24f1594f819ae810ab4a61f75e800408bb`

The corrected identity records `git_dirty = false`, the same pinned toolchain
and lock hashes, backend-source hash
`010ac950d435ef05c805acd11b23670988be78bf6c818de1e8be3d4c5fff12d5`
and unchanged frontend-bundle hash
`c7a29657a65f831e41f70ac59950ebe4223c781cba6a916def2510d17bcec037`.

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

## 10. Review gate

I8 is the accepted implementation baseline. The reviewed I8 history and this
administrative acceptance record are authorised for fast-forward incorporation
into `main`. I9 has not begun and remains separately unauthorised.

## V2 Automation Candidate

**V2 Automation Candidate — evidence-package completeness and integrity
assurance.** Selecting the correct preserved records, proving provenance,
checking every required entry and independently verifying hashes is repetitive
and evidence-heavy. A future assurance tool could preassemble and audit a
candidate package while preserving engineer control of scope, classification
and acceptance.
