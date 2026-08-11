---
Status: QA-045–QA-047 corrected and verified; pending independent re-review
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-11
Change: DC-005 — Controlled Validation Suspension and BLOCKED-TEST Determination
---

# DC-005 Application Closeout

## Boundary and provenance

The accepted DC-005 authoritative baseline was reconciled from main commit `195e21ac0f2e0641f17c0307c0a095591623d7bd` into existing branch `agent/dc-004-application` without rewriting original reviewed DC-004 application commit `a22d428483b8afcbcbaa5309d327c2ac3709f7fa`. Requirements Specification v0.4, Validation Plan v1.2, Demonstrator Design v0.4, System Architecture v0.3 and Workflow Design v0.3 remain byte-identical to main. I8 remains the accepted implementation baseline; this application is pending independent re-review and I9 remains stopped.

## Applied contracts

- `ValidationTargetSelection` is a backend-resolved, canonical-hashed pre-entry anchor for test, case, catalogue, definition, configuration, evidence class, selection authority and target build.
- `ValidationAttempt` owns incomplete, active, suspended and executed lifecycle state. An `ExecutedValidationResult` is created only by the controlled expected-versus-observed comparison and permits PASS or FAIL only.
- Exactly VSC-001 through VSC-005 exist. The public boundary no longer accepts a caller-declared condition, failure code, evidence payload or backend actor identity. It accepts only an evaluation type and controlled reference for an authority to verify.
- VSC-003 is derived from trusted target identities; VSC-005 from actual registered artefact bytes/schema/canonical content; runtime/finalisation VSC-004 from the backend time verifier. Healthy inputs are rejected and backend proposer/reviewer identities are assigned internally.
- VSC-001/VSC-002 resolve exact OPEN DQ or UNRESOLVED conflict records and exact controlled source locations/hashes. Missing, closed, unrelated, mismatched and hash-invalid records are rejected; positive tests use test-only controlled records rather than inventing a production issue.
- VSC-003 target selection preserves intended/requested/resolved identities for APPLICATION_BUILD, CONFIGURATION, CATALOGUE, TEST_DEFINITION, CASE_DEFINITION and CONTROLLED_FIXTURE, permits exactly the resolver-proven failed role to remain unresolved, and records the independent assurance-verifier build. Composite suspension membership carries that exact unavailable role without backfilling the missing target value.
- Judgement evidence binds each source to whole-file hash, exact location, canonical assertion-text hash and assertion-record fingerprint. Pre-entry controlled-time review likewise binds the exact step reference, canonical step-text hash and step-record fingerprint; the backend verifies identity while the engineering reviewer retains the judgement.
- EXECUTION_RESULT composite membership explicitly resolves immutable `ExecutedValidationResult` identity and recomputable controlled result hash, validates attempt/execution/run/evidence/result links bidirectionally at assembly and finalisation, and persists `executed_result_id` directly on each execution constituent link.
- Finalised `ValidationSuspensionRecord` preserves schema/classifier versions, evaluated gates, target hash, intended/resolved/failed identities, target and verifier builds, evidence hashes, authority, lifecycle, generated reason and deterministic fingerprint.
- PRE_EXECUTION_ENTRY creates no scenario run, execution or result. EXECUTION_IN_PROGRESS and EVIDENCE_FINALISATION bind actual run/execution records; suspension prevents later evidence/result continuation. Ordinary missing evidence remains incomplete.
- Composite membership is an immutable union of EXECUTION_RESULT (PASS/FAIL only) and SUSPENSION_RESULT (genuine finalised BLOCKED-TEST only). Exact completeness and FAIL > BLOCKED-TEST > PASS precedence remain unchanged.
- Migration 008 creates target, attempt, executed-result, suspension/evidence and composite-source tables; migration 009 adds immutable explicit composite-to-executed-result identity. Database-level finalised-truth immutability remains enforced.
- Workspace review remains projection-only. EXPLORATORY suspensions do not affect FORMAL progress; future FORMAL BLOCKED-TEST progress can come only from genuine FORMAL suspension records, never an execution verdict.
- Composite evidence export includes preserved suspension, target and attempt records and keeps source-build/source-catalogue identities separate from generation build.

## QA-041 and controlled catalogue identity

QA-041 is independently accepted. Historical v1.0 catalogue/manifest hashes remain exactly `e4b1fb616fb4f0605c19129f18746bfae48278ed35fbb971aac4f690fd32bcc1` / `8bc2f16e6dd475a56a5c5dc3ed52ca46caafc77c08bd858de3f2d748c4dfe714`. The superseded first-application v1.1 hashes remain recorded as `354284d1…713f` / `dadb890a…e0d3`; corrected active v1.1 hashes are `28bfe69131c40857c08f175abba42be3eb36514924b6de416b4e72bbefe35865` / `45cb015f58af1d453be0255cdbbb857c08901877c416e830f26bb2fe6ecf60a3`.

## Verification

- backend: 134 passed, including focused QA-045 identity-role/composite, QA-046 fingerprint and QA-047 executed-result provenance negatives;
- focused QA-041/DC-005 actual service, persistence, composite and ZIP paths: passed;
- frontend components: 17 passed;
- Chromium formal, investigation and Exploration/export workflows: 3 passed;
- exact Node 24.19.0/npm 11.17.0 clean install and production build: passed;
- 24 definitions, 124 requirement IDs, exact 286 RTM relationships and 15 operational-event types: unchanged and covered by the full suite;
- canonical network v1.0/v1.1, schema, dependency-lock and authoritative DOCX hashes: unchanged;
- hard-coded answer, cross-run mixing, FORMAL/EXPLORATORY contamination, live-state reconstruction, real-control implication and I9 leakage scans: no unauthorised behaviour found.

## Gate

QA-041 and QA-043 are independently accepted. QA-045–QA-047 are corrected and verified but pending independent re-review; QA-044 remains pending until QA-046 closes and QA-042/DC-005 application therefore remains not accepted. Draft PR #10 must remain unmerged. I9 has not resumed and requires later separate authorisation only after the complete application is independently accepted and incorporated into reviewed main.

The separately reviewable machine-application commit is `708c9814fe307a849c7a011e5bfae65d52f5ceca` (`Apply QA-041 and DC-005 validation assurance`). The following derived closeout/status commit does not change implementation behaviour.

**V2 Automation Candidate — suspension assurance assembly.** Repeatedly resolving controlled identities, checking evidence contracts, generating fingerprints and assembling review/export records is evidence-heavy and error-prone; a future assurance assistant could automate candidate checks while leaving the VSC judgement and acceptance authority with engineers.
