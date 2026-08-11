---
Status: Accepted DC-005 authoritative design baseline
Authority: Derived verification and handover record only
Owner: Project engineering review process
Updated: 2026-08-11
---

# DC-005 Design Acceptance Closeout

## 1. Scope and gate

This record closes administrative acceptance of **DC-005 — Controlled Validation Suspension and BLOCKED-TEST Determination** at independently reviewed design tip `974c39ac044b1af1342389f531f65281d93db114`. It promotes the reviewed design artefacts as the authoritative baseline but does not implement DC-005.

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

## 3. Accepted resolution

The accepted design defines:

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

## 4. Preserved proposal identities and accepted authoritative revisions

| Artefact | Accepted section | Independently reviewed proposal identity | Accepted authoritative identity | Superseded identity retained |
|---|---|---|---|---|
| Requirements Specification v0.4 | Controlled clarification at `REQ-VAL-007`–`REQ-VAL-009` | SHA-256 `11c8760aa3ed9b745853c6b6e9ab7363c0b6c1c64f7d26755e8ff57f465f352d`; 39,533 bytes | SHA-256 `ff4d2507e86178214d73c7f2ef19b5aaa9b9821ca1d5e04d8eeeec1ac896e3d4`; 39,488 bytes; 1,266 paragraphs; 1 table | v0.3; SHA-256 `7d5522e53dd99e505b9853d6b0b0255c8b4585964909f5659e1ab13d7d1eaeea` |
| Validation Plan v1.2 | Section 20.1–20.7 plus Section 13.1 consistency correction | SHA-256 `85dddab031aab7d2a5600fc844396474f042fa6dc2cbe5af243a23ebb504ca7d`; 847,644 bytes | SHA-256 `8cde791aae359a7a3d8f335bbb385aba24ef9e75a4fb9f019e14799f4c3db14b`; 847,666 bytes; 171 paragraphs; 31 tables | v1.1; SHA-256 `c6aa4edd824d6e084fd3335c22556b7dc9e86948fdce5628ae32fc05eccb2f9c` |
| Demonstrator Design v0.4 | Section 37.1–37.6 | SHA-256 `b30323b93fcbc23f0f6cd76feb9a1646314051d177a8f94c54b6aac0813771e8`; 851,645 bytes | SHA-256 `f3cbe66b1080096509796e35f62247b5c18f813c4facab68b38bdbeb70fb4c62`; 851,657 bytes; 379 paragraphs; 35 tables | v0.3; SHA-256 `f2614e894dae64785ec01e0c6fbdc1e141f302608beeb3d7d07eebed3427bef5` |
| System Architecture v0.3 | Section 27.1–27.4 | SHA-256 `83bb1b5f1e224943a76e0f91ea4cc37b4e71e95016b2fbae7e668c9068e17c21`; 548,273 bytes | SHA-256 `1e1ca4a2b8a054fcfa998bf33f809a6bcfdaf5e9647ffd285c9fe61a783aeb7d`; 548,281 bytes; 325 paragraphs; 13 tables | v0.2; SHA-256 `249e2370e0072cfc8324740a76a0b77647b1db2d93aef2364f4fa8b6a8a87a77` |
| Workflow Design v0.3 | Section 28.1–28.5 | SHA-256 `8c0ea11d595c1b1d719f927918894797ada3cccdad15c9a36764857c7642423e`; 622,805 bytes | SHA-256 `3b7250fa802f5cd4e0c8c224f17e51af10a1e6d0f1a323b28bbd19cedfedd2a8`; 622,810 bytes; 266 paragraphs; 34 tables | v0.2; SHA-256 `f09f7e983e208b6c9f9b9f19d41d35df1b347c195e9c78fe63032d0df30b1547` |

## 5. Verification performed

- all five accepted DOCX files reopen successfully through the document parser;
- all five packages render successfully: Requirements Specification 56 pages, Validation Plan 49 pages, Demonstrator Design 47 pages, System Architecture 29 pages and Workflow Design 34 pages;
- every rendered page was reviewed in contact sheets; accepted-status/gate pages Requirements 1 and 40–41, Validation Plan 1 and 44–49, Demonstrator Design 1 and 45–47, System Architecture 1 and 27–29, and Workflow Design 1 and 31–34 were inspected at readable full-page resolution;
- new table geometry was polished and re-rendered; no clipping, overflow, missing text or broken page was found;
- superseded, independently reviewed proposal and accepted versions/hashes are explicit in the change record and current-baseline manifest;
- the Requirements clarification retains the exact 124 IDs and 286 RTM relationships; no machine catalogue, schema, application code, canonical network configuration, dependency or operational-event file is included; and
- future implementation verification is defined in DC-005 Section 15 and Validation Plan Section 20.7.

## 6. Acceptance decision and next gate

Final independent engineering review accepted the complete design at tip `974c39ac044b1af1342389f531f65281d93db114`. Requirements Specification v0.4, Validation Plan v1.2, Demonstrator Design v0.4, System Architecture v0.3 and Workflow Design v0.3 are therefore the authoritative DC-005 design baseline. PR #10 remains unchanged. No machine application, QA-041/QA-042 correction or I9 resumption is authorised by this acceptance. The next separately controlled phase is PR #10 reconciliation followed by combined QA-041 + QA-042/DC-005 application and independent re-review.

**V2 Automation Candidate — assurance-record preflight.** Condition-specific evidence binding, source/hash checks, reviewer separation and export completeness are repetitive and error-prone. A later V2 tool could preflight those facts while leaving engineering judgement and acceptance with the reviewer.
