---
Status: Applied and verified; pending independent review
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-11
Change: DC-004 — Multi-Run Exploratory Validation Determination
---

# DC-004 Application Closeout

## 1. Authorisation, baseline and boundary

The user separately authorised the machine/application phase of accepted
DC-004. Branch `agent/dc-004-application` was created from exact reviewed
`main` commit `e4f74611d9f750f4577f36c1c473f79506266347` after confirming a clean,
synchronised repository and the accepted authoritative DC-004 identities.

This phase applies only the accepted validation-assurance design: immutable
catalogue revision history, controlled constituent cases, one execution per
scenario run, generic case comparison, immutable composite assurance,
historical resolution/review and evidence export. It does not change network
configuration, topology, outage, restoration, DC-003 isolation, transaction
semantics, the 15 operational-event types, dependency baselines or
authoritative engineering documents.

I8 remains the accepted implementation baseline. I9 remains stopped and was
not resumed on this branch. DC-004 application acceptance and incorporation
into reviewed `main` require separate independent review.

## 2. Authoritative source review

Implementation was checked against:

- accepted DC-004 change record and design-change register entry;
- Validation Plan v1.1 Section 19, SHA-256
  `c6aa4edd824d6e084fd3335c22556b7dc9e86948fdce5628ae32fc05eccb2f9c`;
- Demonstrator Design v0.3 Section 36, SHA-256
  `f2614e894dae64785ec01e0c6fbdc1e141f302608beeb3d7d07eebed3427bef5`;
- accepted Validation Plan Sections 12–15 and the controlled 24-test RTM;
- accepted I5 validation/evidence and I8 Exploration/export authorities; and
- the current implementation-control plan, source map and QA register.

No source contradiction or unresolved engineering choice was found. No
authoritative Word document was edited during application.

## 3. Controlled catalogue promotion and history

The exact pre-DC-004 machine catalogue is preserved as an immutable historical
input under `validation/test-definitions/history/v1.0/`:

- catalogue v1.0 bytes SHA-256
  `e4b1fb616fb4f0605c19129f18746bfae48278ed35fbb971aac4f690fd32bcc1`;
- manifest v1.0 bytes SHA-256
  `8bc2f16e6dd475a56a5c5dc3ed52ca46caafc77c08bd858de3f2d748c4dfe714`;
- historical `VT-EXP-ALL-001` definition v1.0 SHA-256
  `bd94a2a668c30eb4e54c111beab912fbd45503af159b15fd0c96a8628d778a47`;
  and
- historical `VT-EXP-ROLE-001` definition v1.0 SHA-256
  `29dc26956048db3b6db8a6d84b4a6de4428edeb3226f139a384b2022727fd802`.

The promoted active machine catalogue remains revision v1.1. Its first-application identity is preserved above; QA-041 legitimately corrects the active identity without changing the 24 definitions or 286 RTM relationships:

- superseded first-application catalogue v1.1 SHA-256
  `354284d1f119b76edd545eaf35330e4f3bf05379852f4c6676f4494d07fb713f`;
- superseded first-application manifest v1.1 SHA-256
  `dadb890ae2ddd9224d2b809b6cdffe1a523faecb40010a5a7b053d815a2be0d3`;
- corrected active catalogue v1.1 SHA-256
  `28bfe69131c40857c08f175abba42be3eb36514924b6de416b4e72bbefe35865`;
- corrected active manifest v1.1 SHA-256
  `45cb015f58af1d453be0255cdbbb857c08901877c416e830f26bb2fe6ecf60a3`;
- `VT-EXP-ALL-001` definition v1.1 SHA-256
  `869e020f010db68e973228d72c6f5dfe2500590f0ba94260dd7773ada6469c35`;
  and
- `VT-EXP-ROLE-001` definition v1.1 SHA-256
  `6e984acde3f9ce3e0203e486620291dbda6cf65e9f999c71ee2e466285609b2d`.

The active revision retains exactly 24 test definitions, 124 unique formal
requirements and the exact accepted 286 requirement-to-test relationships.
Only the two accepted multi-run definitions advance to v1.1 and receive their
controlled case definitions. The exact nine `VT-EXP-ALL-001` and four
`VT-EXP-ROLE-001` cases match accepted DC-004. Dynamic provenance is enforced
as binding evidence and is not misrepresented as a predetermined engineering
comparison value.

`ValidationCatalogueResolver` resolves a stored catalogue version/hash and
test-definition version/hash against the exact active or historical package.
Hash or identity mismatch is rejected; execution review does not silently
substitute the current catalogue for its bound source revision.

## 4. Constituent execution and comparison

Starting a controlled case execution binds one `ValidationExecution` to one
`ScenarioRun`, one `test_id` and one `case_id`. The backend verifies corrected
Network Configuration v1.1, EXPLORATION mode, EXPLORATORY evidence class,
selected fault section and the case's controlled identities. A constituent
execution cannot span or manufacture multiple runs.

Observed engineering values are projected only from accepted backend
authorities. They include selected fault, affected feeder and protection
breaker, canonical incident boundaries, boundary telemetry/proof/action
eligibility, isolation, alternate feeder, proposed transfer sections, loads,
capacity/loading and outcome where required by the accepted case. The generic
comparison canonicalises controlled set-like fields and makes no case-specific
runtime decision.

Tests execute and finalise all nine all-section cases and all four role/outcome
cases through actual scenario transactions. They also prove a genuine field
mismatch produces a constituent FAIL and that missing, unfinished, duplicate
or provenance-mismatched constituents cannot be treated as complete.

## 5. Composite validation assurance

A composite assurance record is separate from scenario runs, constituent
executions and operational events. It owns exact immutable membership and
records the source catalogue/test identities, constituent identities,
completeness diagnostics and aggregate result. It has no composite engineering
scenario time.

Finalisation requires the exact accepted case set, one eligible finalised
execution for every case and matching controlled provenance. Missing,
unexecuted, duplicate or mismatched membership remains `INCOMPLETE` without a
verdict. Complete membership applies the accepted precedence: any constituent
FAIL produces composite FAIL; otherwise any BLOCKED-TEST produces composite
BLOCKED-TEST; otherwise all PASS produces composite PASS.

SQLite migration 007 provides composite, membership and package persistence.
Database triggers enforce finalised-result and membership immutability rather
than relying on application checks alone.

## 6. Historical review and export

Finalised historical v1.0 executions remain resolvable, reviewable and
exportable after catalogue promotion using their stored source catalogue and
definition identities. An unfinished v1.0 execution remains visible but is
historical/read-only: checkpoint capture and finalisation under the promoted
catalogue are rejected. New executions bind to v1.1.

Existing per-execution export now resolves the execution's actual historical
definition. Composite export is created only from the finalised immutable
composite and its preserved constituent execution/evidence/run records. The
export distinguishes source catalogue/test-definition provenance from the
later export-generation build and retains FORMAL/EXPLORATORY classification.
ZIP entry, manifest, archive and database-register integrity controls remain
append-only and independently verifiable.

The workspace review projection lists preserved composite identity, status,
completeness, result and constituent provenance without inventing a single
composite run. FORMAL validation progress remains isolated from all
EXPLORATORY constituent and composite records.

## 7. Verification evidence

| Gate | Result |
|---|---|
| Complete backend unit/integration suite | PASS — 131 tests including QA-043/QA-044 corrections; application acceptance remains pending independent re-review |
| React/Cytoscape component suite | PASS — 17 tests |
| Chromium formal, investigation and Exploration/export workflows | PASS — 3 tests |
| Pinned TypeScript/Vite production build | PASS |
| Exact historical v1.0 catalogue/manifest bytes and hashes | PASS |
| Active/historical catalogue resolution and tamper rejection | PASS |
| Exact 9 + 4 controlled case definitions | PASS |
| Actual execution/finalisation of all 13 cases | PASS |
| Complete all-PASS composite determination | PASS |
| Constituent mismatch and aggregate FAIL treatment | PASS |
| Missing/unfinished/duplicate/mismatched completeness controls | PASS |
| BLOCKED-TEST / FAIL aggregate precedence | PASS |
| Composite persistence and database immutability | PASS |
| Historical finalised review/export after promotion | PASS |
| Historical unfinished read-only enforcement | PASS |
| Composite ZIP construction and independent SHA-256 verification | PASS |
| Exact 24 definitions / 124 requirements / 286 RTM relationships | PASS — unchanged |
| Exact operational-event types | PASS — 15, unchanged |
| FORMAL progress isolation | PASS — unchanged |
| Canonical network configuration/schema hashes | PASS — unchanged |
| Python/frontend dependency definitions and locks | PASS — unchanged |
| Runtime case/outcome hard-coding review | PASS |
| Cross-run/execution mixing review | PASS |
| Electrical authority and I9 leakage review | PASS — no leakage |

These are DC-004 application-conformance results. They are not I9 campaign
execution or final project acceptance evidence.

## 8. Controlled unchanged identities

- Network Configuration v1.0 data:
  `67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3`.
- Network Configuration v1.1 data:
  `7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281`.
- Network configuration schema:
  `ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c`.
- Python dependency lock:
  `0c68ce8fad5cbc3b877ade42f7a6d0400b50f0f2a52cee262734c7df10b41a64`.
- Frontend dependency lock:
  `b628f98c999bcf66ae3bbdf067e961ced6b56f3db03a7339f4ca54e20ada3177`.
- Python project/dependency definition:
  `fbd7dd0fc100807bff1d97ddcd3bb5454a911c58940e1e4ecb02c70d8c0e08f1`.

The clean branch-tip application build identity is generated after the
implementation commit and recorded in the draft review PR and handoff report.
Keeping that post-commit value outside tracked application files avoids a
self-changing build-identity record.

## 9. QA and gate disposition

DQ-002 remains resolved by accepted DC-004. IMP-002 records the separately
authorised application phase as implemented and verified, pending independent
review. No additional implementation finding required a new engineering rule
or authoritative change.

The DC-004 change record, design-change register, QA register, implementation
control/source navigation, baseline manifest and README are updated only as
derived/change-control status aids. They do not declare DC-004 application or
I9 accepted before independent review.

**V2 Automation Candidate — composite campaign assembly and assurance.**
Selecting exact constituent executions, checking completeness/provenance,
assembling traceable evidence and independently verifying packages is
repetitive and evidence-heavy. A future assurance assistant could automate
candidate assembly and discrepancy detection while leaving final engineering
acceptance to the reviewer.

## 10. Stop statement

DC-004 machine/application work stops at the pushed draft-review boundary.
The branch must remain unmerged until independent engineering/implementation
review accepts it. I9 remains stopped and separately unauthorised.

## 11. Reconciled QA-041/DC-005 application addendum

Accepted main `195e21ac0f2e0641f17c0307c0a095591623d7bd` is an ancestor of this branch and original reviewed DC-004 application commit `a22d428483b8afcbcbaa5309d327c2ac3709f7fa` remains in history. Reconciliation itself changed no application behaviour and the five accepted DC-005 DOCX packages remain byte-identical to main.

QA-041 now captures and compares TS-01 `age_ms = 60001` at controlled time `T0 + 60,001 ms`. Actual case executions prove exactly 60,001 ms PASSes the accepted STALE expectation, 61,000 ms FAILs the exact field while retaining STALE categorical evidence, and 60,000 ms remains FRESH.

Accepted DC-005 is applied through migration 008 and the validation module: hashed trusted target selection, ValidationAttempt, PASS/FAIL-only ExecutedValidationResult, exactly VSC-001–005 with accepted failure-code/evidence contracts, bounded local authority separation, immutable deterministic suspension records, PRE_EXECUTION_ENTRY / EXECUTION_IN_PROGRESS / EVIDENCE_FINALISATION positions, and the DC-004 EXECUTION_RESULT / SUSPENSION_RESULT union. Suspension-source ZIPs are assembled from preserved records and retain source versus generation-build provenance. No authoritative engineering document, network package, dependency or I9 behaviour changed.

## 12. QA-043/QA-044 assurance correction

Independent re-review accepted QA-041 but held QA-042 application acceptance pending stronger condition authority. The corrected public boundary no longer accepts caller-declared failure codes, evidence payloads or backend actor identities. Backend identity, integrity and runtime-time verifiers establish VSC-003/VSC-005/runtime VSC-004 facts from trusted state, while a deterministic controlled-record mirror resolves VSC-001/VSC-002 DQ/conflict/source identities and actual hashes. The corrections are verified but remain pending independent re-review; PR #10 stays draft/unmerged and I9 remains stopped.
