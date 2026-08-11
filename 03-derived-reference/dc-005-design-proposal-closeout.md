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
- Requirements Specification v0.3 `REQ-VAL-001–014`, especially unchanged `REQ-VAL-008`; and
- accepted DC-004 for one-execution/one-run provenance, composite exactness, aggregate precedence and historical catalogue resolution.

The review found required amendments in Validation Plan, Demonstrator Design, System Architecture and Workflow Design. It found no required change to the Requirements Specification, Engineering Design Brief or Network Model.

## 3. Proposed resolution

The proposal defines:

- exactly five stable conditions: `VSC-001` Unspecified engineering behaviour, `VSC-002` Inconsistent baseline, `VSC-003` Unidentifiable input version, `VSC-004` Uncontrolled wall-clock dependency and `VSC-005` Evidence corruption;
- lifecycle points `PRE_EXECUTION_ENTRY`, `EXECUTION_IN_PROGRESS` and `EVIDENCE_FINALISATION`;
- a separate immutable `ValidationSuspensionRecord`, with an optional mandatory link to the actual run/execution when one validly exists;
- condition-specific structured evidence and common provenance binding;
- independent-reviewer authority for judgement-based conditions and backend assurance for resolver/time/integrity facts;
- backend-generated deterministic reason code, rendered reason and canonical fingerprint;
- a controlled DC-004 constituent union of `EXECUTION_RESULT` for PASS/FAIL and `SUSPENSION_RESULT` for BLOCKED-TEST; and
- unchanged aggregate precedence, FORMAL/EXPLORATORY separation, historical resolution, 24 tests, 124 requirements, 286 RTM relationships and 15 operational-event types.

Operational `BLOCKED` remains an engineering/system outcome. It is not `BLOCKED-TEST` and may still yield validation PASS when it is the expected operational result.

## 4. Proposed authoritative revisions

| Artefact | Proposed section | Proposed identity | Accepted identity retained |
|---|---|---|---|
| Validation Plan v1.2 | Section 20.1–20.7 | SHA-256 `bc16880075cff637717e1a08742b2e5f7a101966a9a245c3aa1b248340bd28f6`; 846,655 bytes; 170 paragraphs; 31 tables | v1.1; SHA-256 `c6aa4edd824d6e084fd3335c22556b7dc9e86948fdce5628ae32fc05eccb2f9c` |
| Demonstrator Design v0.4 | Section 37.1–37.6 | SHA-256 `b8b3f3d9645649d86847939672f2df35224bfb1758d764768433c5feb2006683`; 851,456 bytes; 379 paragraphs; 35 tables | v0.3; SHA-256 `f2614e894dae64785ec01e0c6fbdc1e141f302608beeb3d7d07eebed3427bef5` |
| System Architecture v0.3 | Section 27.1–27.4 | SHA-256 `8ad9d834b4c90f35231844bcb793e4f18544040a0853644bfa9c8a1abe370613`; 547,971 bytes; 325 paragraphs; 13 tables | v0.2; SHA-256 `249e2370e0072cfc8324740a76a0b77647b1db2d93aef2364f4fa8b6a8a87a77` |
| Workflow Design v0.3 | Section 28.1–28.5 | SHA-256 `ac946735caecadcab49b6cf8748caa2e668e03f8b4afd19aed3131efd26ed3e5`; 622,490 bytes; 266 paragraphs; 34 tables | v0.2; SHA-256 `f09f7e983e208b6c9f9b9f19d41d35df1b347c195e9c78fe63032d0df30b1547` |

## 5. Verification performed

- all four proposed DOCX files reopen successfully through the document parser;
- all four packages render successfully: Validation Plan 49 pages, Demonstrator Design 47 pages, System Architecture 29 pages and Workflow Design 34 pages;
- every rendered page was reviewed in contact sheets, with proposed title pages and new sections inspected at readable page resolution;
- new table geometry was polished and re-rendered; no clipping, overflow, missing text or broken page was found;
- proposed/accepted versions and hashes are explicit in the change record, source map and current-baseline manifest;
- no requirement, machine catalogue, schema, application code, canonical network configuration, dependency or operational-event file is included in the proposal; and
- future implementation verification is defined in DC-005 Section 15 and Validation Plan Section 20.7.

## 6. Independent-review decision requested

Independent review should determine whether the proposed lifecycle location, evidence/authority contracts, execution/suspension union and deterministic reason are acceptable. Until that decision, accepted DC-004 design plus I8 implementation on reviewed `main` remains authoritative. No application work or I9 resumption is authorised by this package.

**V2 Automation Candidate — assurance-record preflight.** Condition-specific evidence binding, source/hash checks, reviewer separation and export completeness are repetitive and error-prone. A later V2 tool could preflight those facts while leaving engineering judgement and acceptance with the reviewer.
