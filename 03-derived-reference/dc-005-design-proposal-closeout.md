---
Status: Proposed DC-005 design package — pending independent engineering review
Authority: Derived verification and handover record only
Owner: Project engineering review process
Updated: 2026-08-11
---

# DC-005 Design Proposal Closeout

## 1. Scope and gate

This record closes preparation of the design-only proposal for **DC-005 — Controlled Validation Suspension and BLOCKED-TEST Determination**. It does not accept or apply the change.

The branch was created from exact accepted `main` commit `e4f74611d9f750f4577f36c1c473f79506266347`. Read-only GitHub verification found draft PR #10 still OPEN at unchanged head `a22d428483b8afcbcbaa5309d327c2ac3709f7fa` on `agent/dc-004-application`. QA-041 has not been applied, QA-042 has not been implemented and I9 remains stopped.

## 2. Authoritative source review

The proposal was derived from the accepted hierarchy and the exact affected source locations:

- Validation Plan v1.1 Sections 4, 14 and 19: existing PASS/FAIL/NOT RUN/BLOCKED-TEST meanings, exact five suspension labels, execution entry/suspend rules and accepted DC-004 aggregation;
- Demonstrator Design v0.3 Sections 8.7, 9, 19–21 and 36: validation/evidence ownership, immutable persistence, presentation/export and composite assurance;
- System Architecture v0.2 Sections 10, 12 and 20: SA-CMP-08 validation/evidence authority and the existing execution-based PASS/FAIL record model;
- Workflow Design v0.2 Sections 5.2, 14 and 19: run/execution lifecycle, evidence finalisation and review workflow;
- Requirements Specification v0.3 `REQ-VAL-001–014`, especially the ambiguity between `REQ-VAL-007`–`REQ-VAL-009` and a suspended attempt; and
- accepted DC-004 for one-execution/one-run provenance, composite exactness, aggregate precedence and historical catalogue resolution.

The bounded re-review found that downstream interpretation alone was insufficient and therefore adds a controlled Requirements Specification v0.4 wording clarification to `REQ-VAL-007`–`REQ-VAL-009`. Their IDs, verification intent, total requirement count and RTM relationships remain unchanged. Engineering Design Brief and Network Model require no change.

## 3. Proposed resolution

The proposal defines:

- exactly five stable conditions: `VSC-001` Unspecified engineering behaviour, `VSC-002` Inconsistent baseline, `VSC-003` Unidentifiable input version, `VSC-004` Uncontrolled wall-clock dependency and `VSC-005` Evidence corruption;
- lifecycle points `PRE_EXECUTION_ENTRY`, `EXECUTION_IN_PROGRESS` and `EVIDENCE_FINALISATION`;
- a distinct `ValidationAttempt` lifecycle and PASS/FAIL-only `ExecutedValidationResult`, with ordinary missing evidence remaining non-finalisable/incomplete;
- a separate immutable `ValidationSuspensionRecord`, with an optional mandatory link to actual run/execution context when validly created;
- a trusted immutable `ValidationTargetSelection` anchor from campaign/test-selection authority, separated from resolved sources, failed-input evidence and assurance-verifier build;
- a versioned, deterministic and non-overlapping VSC classifier in which integrity failure is VSC-005 and integrity-valid missing/unknown/ambiguous identity is VSC-003;
- condition-specific structured evidence and common provenance binding;
- locally controlled actor/role and proposal/finalisation separation for judgement-based conditions, without claiming V1 cryptographically proves human independence, plus backend assurance for resolver/time/integrity facts;
- backend-generated deterministic reason code, rendered reason and canonical fingerprint;
- a controlled DC-004 constituent union of `EXECUTION_RESULT` for PASS/FAIL and `SUSPENSION_RESULT` for BLOCKED-TEST; and
- unchanged aggregate precedence, FORMAL/EXPLORATORY separation, historical resolution, 24 tests, 124 requirements, 286 RTM relationships and 15 operational-event types.

Operational `BLOCKED` remains an engineering/system outcome. It is not `BLOCKED-TEST` and may still yield validation PASS when it is the expected operational result.

## 4. Proposed authoritative revisions

| Artefact | Proposed section | Proposed identity | Accepted identity retained |
|---|---|---|---|
| Requirements Specification v0.4 | Controlled clarification at `REQ-VAL-007`–`REQ-VAL-009` | SHA-256 `11c8760aa3ed9b745853c6b6e9ab7363c0b6c1c64f7d26755e8ff57f465f352d`; 39,533 bytes; 1,266 paragraphs; 1 table | v0.3; SHA-256 `7d5522e53dd99e505b9853d6b0b0255c8b4585964909f5659e1ab13d7d1eaeea` |
| Validation Plan v1.2 | Section 20.1–20.7 plus Section 13.1 consistency correction | SHA-256 `85dddab031aab7d2a5600fc844396474f042fa6dc2cbe5af243a23ebb504ca7d`; 847,644 bytes; 171 paragraphs; 31 tables | v1.1; SHA-256 `c6aa4edd824d6e084fd3335c22556b7dc9e86948fdce5628ae32fc05eccb2f9c` |
| Demonstrator Design v0.4 | Section 37.1–37.6 | SHA-256 `b30323b93fcbc23f0f6cd76feb9a1646314051d177a8f94c54b6aac0813771e8`; 851,645 bytes; 379 paragraphs; 35 tables | v0.3; SHA-256 `f2614e894dae64785ec01e0c6fbdc1e141f302608beeb3d7d07eebed3427bef5` |
| System Architecture v0.3 | Section 27.1–27.4 | SHA-256 `83bb1b5f1e224943a76e0f91ea4cc37b4e71e95016b2fbae7e668c9068e17c21`; 548,273 bytes; 325 paragraphs; 13 tables | v0.2; SHA-256 `249e2370e0072cfc8324740a76a0b77647b1db2d93aef2364f4fa8b6a8a87a77` |
| Workflow Design v0.3 | Section 28.1–28.5 | SHA-256 `8c0ea11d595c1b1d719f927918894797ada3cccdad15c9a36764857c7642423e`; 622,805 bytes; 266 paragraphs; 34 tables | v0.2; SHA-256 `f09f7e983e208b6c9f9b9f19d41d35df1b347c195e9c78fe63032d0df30b1547` |

## 5. Verification performed

- all five proposed DOCX files reopen successfully through the document parser;
- all five packages render successfully: Requirements Specification 56 pages, Validation Plan 49 pages, Demonstrator Design 47 pages, System Architecture 29 pages and Workflow Design 34 pages;
- every rendered page was reviewed in contact sheets; the changed Requirements pages 40–41, Validation Plan pages 20 and 45–49, Demonstrator Design pages 45–47, System Architecture pages 28–29 and Workflow Design pages 31–34 were inspected at readable full-page resolution;
- new table geometry was polished and re-rendered; no clipping, overflow, missing text or broken page was found;
- proposed/accepted versions and hashes are explicit in the change record, source map and current-baseline manifest;
- the Requirements clarification retains the exact 124 IDs and 286 RTM relationships; no machine catalogue, schema, application code, canonical network configuration, dependency or operational-event file is included; and
- future implementation verification is defined in DC-005 Section 15 and Validation Plan Section 20.7.

## 6. Independent-review decision requested

Final independent review should confirm that the three bounded corrections are closed: the requirements-level attempt/result clarification and non-finalisable missing-evidence treatment; deterministic non-overlapping VSC classification; and the trusted pre-entry target/provenance plus bounded reviewer-authority model. The already accepted-in-substance DC-005 core remains otherwise unchanged. Until final acceptance, DC-004 design plus I8 implementation on reviewed `main` remains authoritative. No application work or I9 resumption is authorised by this package.

**V2 Automation Candidate — assurance-record preflight.** Condition-specific evidence binding, source/hash checks, reviewer separation and export completeness are repetitive and error-prone. A later V2 tool could preflight those facts while leaving engineering judgement and acceptance with the reviewer.
