---
Status: I5 assurance corrections complete — pending independent re-review
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-10
Increment: I5 — Validation/evidence
---

# I5 Increment Closeout — Validation/Evidence

## 1. Authorisation, branch and boundary

The user explicitly authorised I5 only. Work was created on
`agent/i5-validation-evidence` from the exact accepted reviewed `main` baseline at
`0af4e8d6013e7699f73ae89448aa4b6c7424c45c`.

The bounded implementation commit is
`4a5c8e7916a6053a5e149150b032475fa6240a27`. It adds the accepted
24-definition machine catalogue, definition/hash loading, immutable validation
execution and evidence records, generic expected-versus-observed comparison,
backend-controlled provenance, reset/repeat preservation and the approved direct
DEF-001 v1.0/v1.1 comparison.

Independent review accepted I5 in substance and requested two bounded assurance
corrections. Commit `c8ac8db63ba275d24cdf8b92dcaa487bd2ee3170`
implements QA-031 and QA-032 without changing catalogue content, mappings,
expected results, engineering behaviour, configuration packages or dependencies.

I2 remains authoritative for topology, energisation, source attribution,
radiality, isolation and outage/customer results. I3 remains authoritative for
scenario runs, controlled time, revisions, commands, reset and the 15 operational
events. I4 remains authoritative for restoration candidates, permissives,
assessments and simulated execution. I5 captures and compares those owned results;
it does not copy or modify their algorithms.

No operational UI/dashboard, I7 investigation workflow, I8 Exploration
orchestration/export, I9 packaging, new engineering rule, new expected outcome,
real control, automation or AI feature was implemented.

## 2. Authoritative sources used

Before implementation, the complete mandatory I5 source set in Implementation
Control Plan Section 8 was read, including:

- `REQ-VAL-001–014`, `REQ-CFG-009–012`, `REQ-EVT-001–011`, `REQ-NFR-003`
  and `REQ-NFR-008`, including rationale and verification methods;
- Network Model Sections 16–18, including the N0–N5 answer key, DEF-001 exact
  v1.0/v1.1 difference, 400/850-customer consequence and repeat basis;
- System Architecture Sections 12, 17, 19–20 and 26.4–26.5;
- Workflow Design Sections 5.2–5.3, 14–19, 22 and 27.3–27.4;
- Demonstrator Design Sections 8.7, 9, 10.5, 12, 19, 21–22 and 27–28;
- Validation Plan Sections 3–15 and 17–18 in full, including every one of the
  24 catalogue rows, every controlled procedure row, all 124 RTM rows, the
  124/124 coverage audit and acceptance record;
- accepted DC-001, DC-002 and DC-003, current baseline metadata, QA register and
  implementation source map; and
- accepted I1–I4 implementation contracts, services, persistence and closeouts.

The authoritative Word/PDF engineering artefacts and accepted change records were
read only and were not modified.

## 3. Files and modules produced or changed

- `validation/test-definitions/catalogue.json`: exactly 24 controlled definitions
  preserving the accepted IDs, objectives, methods, controlled procedures,
  expected-result statements, requirement mappings, source references,
  checkpoint obligations, evidence requirements and verdict/reset rules.
- `validation/test-definitions/manifest.json`: catalogue version/count/file
  identity and repository-byte SHA-256.
- `app/backend/ot_demo/modules/validation/`: strict immutable definition,
  execution, checkpoint/evidence, link and query contracts; manifest/hash loader;
  backend-controlled execution/capture/comparison/query service.
- `app/backend/ot_demo/infrastructure/migrations/004_validation_evidence.sql`:
  execution/evidence persistence, provenance indexes and database triggers that
  reject finalised execution changes/deletes and all evidence changes/deletes.
- `app/backend/ot_demo/infrastructure/validation_repository.py`: execution,
  checkpoint, finalisation and class/test/run-filtered query persistence.
- `app/backend/ot_demo/api/main.py`: backend-only start, checkpoint, finalise and
  evidence-query endpoints; no presentation or later-increment workflow.
- domain enum, migration packaging and pytest marker updates.
- `tests/unit/test_validation_catalogue.py` and
  `tests/integration/test_validation_evidence.py`, plus API/migration regression
  updates.
- derived README, source-map, QA-register and this increment closeout updates.

Dependency definitions and locks are unchanged.

## 4. Controlled catalogue and traceability treatment

The machine catalogue contains exactly the accepted 24 test IDs. The objective,
method, controlled execution and expected-result statement for each definition are
the accepted Validation Plan Section 7/8 row contents, not shortened replacement
summaries. Definition records also carry:

- stable definition version `1.0`;
- FORMAL or EXPLORATORY evidence class as accepted by the relevant test family;
- every requirement ID mapped to that test by the exact Section 15 RTM;
- detailed source references;
- preconditions and controlled inputs;
- named checkpoint obligations and evidence content classes;
- the accepted PASS/FAIL/NOT RUN/BLOCKED-TEST interpretation; and
- reset/repeat preservation requirements.

The union of definition requirement mappings is exactly 124 unique IDs with the
accepted group counts: NET 11, TOP 9, TEL 10, ALM 5, OUT 7, RST 29, EXP 7,
EVT 11, VAL 14, CFG 12 and NFR 9. Loader tests reject a missing/extra definition,
duplicate ID, contradictory Exploration evidence class, invalid manifest identity
or byte-level catalogue tamper.

QA-032 adds an independent test-only oracle calculated directly from the accepted
Validation Plan Section 15 table. The authoritative table contains exactly 286
sorted `(test_id, requirement_id)` relationships and has canonical SHA-256
`53ecf30a7f59bb294410a1b5abbd0b9e014f02ea294f674d9a0ba22ddaf604c8`.
The machine catalogue matches it exactly. A mutation test moves one requirement to
the wrong test while retaining all 124 requirement IDs and all 286 relationships;
the exact oracle rejects it. No catalogue mapping required correction.

The catalogue byte hash is
`e4b1fb616fb4f0605c19129f18746bfae48278ed35fbb971aac4f690fd32bcc1`.
Each execution additionally stores the canonical SHA-256 of its individual
definition, so later catalogue change cannot be silently substituted for the
definition used by an existing record.

Instantiation of all 24 definitions does not claim that the full validation
campaign has run. I5 executes only its authorised record/comparison examples and
leaves the remaining catalogue procedures for their approved later boundary.

## 5. Execution, checkpoint and evidence model

The public start contract accepts only a controlled test ID, scenario-run ID and
optional linkage identities. It does not accept application build, configuration,
mode, evidence class, definition version/hash or scenario time from the caller.
Those values are obtained from the trusted backend build manifest, catalogue and
current scenario run. A run/build mismatch or FORMAL/EXPLORATORY mismatch is
rejected.

Checkpoint capture obtains the current complete backend scenario projection and
preserves it immediately as canonical JSON with:

- execution/test/definition/build/configuration/run/mode/evidence provenance;
- controlled scenario time, state revision and named checkpoint;
- actual telemetry, alarm, topology, energisation, source, outage/customer,
  restoration and operational-event content present at capture;
- source record references; and
- canonical payload SHA-256.

The evidence is not rebuilt later from mutable current state. Reset or subsequent
run changes do not alter the captured payload. A checkpoint identity is unique per
execution, so attempted replacement is rejected rather than overwritten.

Finalisation uses a generic expected-value comparison engine. The verdict path
reads the accepted structured expectation from the controlled definition and the
observed values from the captured checkpoint; it contains no section-, feeder-,
configuration-version- or expected-result-specific branch. If a definition lacks
an authorised automated comparison at the current increment boundary, I5 stops
with an explicit error rather than accepting caller-supplied expected/observed
content or inventing a verdict.

Final records preserve expected and observed results, calculations/comparison
rows, evidence IDs, verdict/reason, and all provenance/link fields. SQLite triggers
reject verdict rewrite, execution update/delete and evidence update/delete after
finalisation. QA-031 adds a database-level evidence-insert guard: once the parent
execution is `FINALISED`, an otherwise valid new checkpoint/evidence row is
rejected. The final immutable `evidence_snapshot_ids` is verified to equal the
persisted evidence rows exactly; active checkpoint capture remains unchanged.
Operational events remain in their original tables and exact
15-type enum; no PASS, FAIL, defect, correction or engineering-review record is
created as an operational event.

## 6. DEF-001, reset and repeat evidence

The direct `VT-TOP-DEF-001` fixture uses the accepted scenario coordinator and the
same I2 topology/outage algorithms for both immutable packages:

- v1.0 observed A1/A2 de-energised, A3/A4 supplied from FDR-B and 400 affected
  customers; generic comparison against the approved expected A1–A4/850 result
  produces a preserved `FAIL`;
- v1.1 observed A1–A4 de-energised and 850 affected customers; the same comparison
  produces a separate `PASS`; and
- both records carry the same backend application build, catalogue and definition
  identity, while their execution, run and evidence IDs remain different.

The corrected execution links to the failed execution with `DEF-001` and
`COR-001` linkage fields. These are record foundations only; no I7 investigation,
correction editor or configuration-generation workflow exists. The canonical
v1.0 failure remains queryable and immutable after the corrected pass.

Reset creates a new I3 scenario run while the completed validation execution and
its revision-1 evidence payload/hash remain unchanged. A deterministic repeat uses
a new run/execution/evidence identity, explicitly links to the prior finalised
execution and produces equal observed engineering output and comparison
calculations under the same build/definition/configuration.

## 7. Requirements and catalogue-gate traceability

| Requirement / gate | I5 implementation evidence | I5 status |
|---|---|---|
| `REQ-VAL-001–009` | Stable test/definition/execution identities; initial conditions from bound run; configuration/build/time; fixed expected; captured observed; generic comparison; evidence references. | Implementation complete — pending review. |
| `REQ-VAL-010–012` | Immutable v1.0 FAIL, linked same-build v1.1 PASS and separately preserved corrected result. | Implementation complete — pending review. |
| `REQ-VAL-013` | Definition/verdict model explicitly treats an expected operational BLOCKED/REJECTED outcome as validation PASS; no operational result is changed. | Definition and generic-engine gate complete. |
| `REQ-VAL-014` | Reset creates a new scenario run while old execution/evidence remains queryable and byte/hash stable. | Implementation complete — pending review. |
| `REQ-CFG-009–012` | Both immutable package identities are retained; defect/correction/repeat linkage foundations bind separate records. | I5 record/linkage portion complete. |
| `REQ-EVT-001–011` separation | Existing 15 operational event types are unchanged and separate from validation records/verdicts. | Regression PASS. |
| `REQ-NFR-003` | Separate repeats have equal canonical observed engineering output/calculations under identical controlled inputs. | Regression PASS. |
| `REQ-NFR-008` | Requirement → definition/version/hash → build/config/run/checkpoint/evidence → observed/comparison/verdict → repeat links are queryable. | I5 foundation complete. |
| `VT-VAL-RECORD-001` | Completeness, reset/history, provenance, separate evidence and immutability are exercised across the I5 integration suite. | I5 implementation conformance PASS. |
| `VT-TOP-DEF-001` | Same-build v1.0 400-customer FAIL and linked v1.1 850-customer PASS are separate immutable records. | I5 controlled direct execution PASS. |
| `VT-CFG-INV-001` | DEF-001/COR-001 failure/correction/repeat linkage fields exist without I7 workflow. | Authorised I5 record/linkage portion PASS. |
| `VT-DET-REPEAT-001` | New execution/run/evidence IDs, explicit repeat link and equal canonical observed/calculation content. | Authorised I5 portion PASS. |
| All 24 definitions / 124 RTM rows | Exact count/IDs, accepted row content, 124 unique mapped requirements, exact 286-pair Section 15 relationship and evidence/checkpoint obligations. | Machine-definition and exact-RTM gate PASS; not a claim of full campaign execution. |
| QA-031 evidence-set closure | Database insert guard rejects post-finalisation evidence; final evidence IDs exactly match returned rows. | Correction PASS — pending independent re-review. |
| QA-032 exact RTM oracle | Independent Section 15 fingerprint matches; wrong-test mutation fails despite unchanged 124-ID coverage. | Correction PASS — pending independent re-review. |

## 8. Verification results and controlled identities

| Verification | Result |
|---|---|
| I5-marked backend suite | PASS — 15 tests |
| Complete backend unit/integration suite | PASS — 97 tests |
| I1 regression | PASS — 11 tests |
| I2 regression | PASS — 31 tests |
| I3 regression | PASS — 20 tests |
| I4 regression | PASS — 17 tests |
| Same-build v1.0 FAIL / v1.1 PASS | PASS — 400 versus 850 exact accepted consequences |
| Reset, repeat, provenance, class separation and immutable-trigger gates | PASS |
| Catalogue exact-count/ID/124-row coverage, exact 286-pair RTM and tamper tests | PASS |
| Pinned TypeScript/Vite production build | PASS — Node 24.19.0 / npm 11.17.0 |
| Python dependency consistency | PASS — no broken requirements |
| Git whitespace check | PASS |
| Hard-coding scan | PASS — controlled expected values live in definitions/tests, not topology/outage/restoration/verdict branches |
| I6+ leakage scan | PASS — no UI/dashboard, investigation workflow, Exploration orchestration, export or packaging implementation |
| Canonical v1.0/v1.1/schema bytes and hashes | PASS — all five accepted values unchanged |
| Dependencies/locks | PASS — unchanged |
| Authoritative engineering/change-control artefacts | PASS — unchanged |

The clean application build identity captured at QA-031/QA-032 correction commit
`c8ac8db63ba275d24cdf8b92dcaa487bd2ee3170` is:

`a22d49f926180e1a5d4ae6bc08e5001c0f43c1f21268b3a2082d6687a913ad3a`

Its identity records `git_dirty = false`, Python 3.13.15, Node.js 24.19.0,
npm 11.17.0, accepted dependency-lock hashes, backend source hash
`77af439e7940edc427004883deb0f5663c1d3956d773ac70d69c39d16bb680c3`
and unchanged frontend bundle hash
`1e6d5ebc33a8e11a06fcb929603af00386a471b13e381e25f3cc3dfb9bde4305`.

The accepted canonical configuration identities remain:

- v1.0 data `67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3`;
- v1.0 manifest `d0243fae46e6a5d403855953e14cdedbcdae9c71af7761a1aba49f88470bc12d`;
- v1.1 data `7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281`;
- v1.1 manifest `e0f16f3acdf2e85aa04cd23bb4b584a868626117b68f682d1219821a36857662`;
  and
- shared schema `ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c`.

## 9. QA findings and V2 candidate

Independent review raised QA-031 because the existing database controls did not
close the evidence set against a new insert after execution finalisation. The new
insert trigger and regression close the implementation gap pending independent
re-review.

Independent review raised QA-032 because the initial assurance test proved the
124-ID union and group totals but not every exact Section 15 relationship. The
independent 286-pair fingerprint and mapping-mutation negative close that assurance
gap pending independent re-review. The independent comparison found no actual
catalogue mismatch. No previously closed item was reopened.

**V2 Automation Candidate — validation evidence completeness and RTM impact.**
Capturing/checking checkpoint content, recomputing definition and evidence hashes,
finding affected requirement/test links and comparing repeat evidence is repetitive
and assurance-heavy. A future V2 tool could assemble completeness and impact
reports for engineer approval without changing V1 expectations or verdict authority.

## 10. Stop conditions and later dependencies

No I5 stop condition remains open. No failed test was bypassed, catalogue row or
expected result changed, caller-supplied provenance trusted, evidence reconstructed
from later mutable state, history overwritten, canonical package edited or verdict
invented where the accepted definition lacks an I5 comparison.

I6 may present these backend records only after I5 is independently accepted and
merged. I7 may add the approved investigation/correction workspace around the
existing linkage fields; I8 may create Exploration runs and evidence ZIP exports;
I9 may execute/package the full accepted campaign. None has begun.

## 11. Review and progression gate

The QA-031/QA-032 corrections are complete on
`agent/i5-validation-evidence` and are being pushed for independent re-review. I5
is not merged and is not yet the accepted implementation baseline. The accepted
baseline remains reviewed `main` through I4.

**I6 has not started. No later increment may begin automatically.**
