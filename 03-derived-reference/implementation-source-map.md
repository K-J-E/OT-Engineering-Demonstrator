# Implementation Source Map

This file is a navigation aid only. It is not a replacement for the detailed documents.

## Engineering basis
- Domain/research reasoning and engineering decisions: `Engineering Investigation and Research.docx`
- Proposed solution/design behaviour and assumptions: `OT Engineering Design Brief.docx`
- Formal testable behaviour: `OT Project Requirements Specification.docx`
- Concrete assets, topology, loads, customers, device IDs and network states: `OT Project Network Model.docx`
- Logical components, information ownership, interfaces, run-state boundaries and architecture decisions: `OT Project System Architecture.docx`
- Controlled actors, commands, gates, event types, formal/exploratory sequences, defect investigation and evidence workflow: `OT Project Workflow Design.docx`
- Practical application/module boundaries, data structures and ownership, persistence and IDs, API/transaction design, views/actions, evidence export, defect presentation, technology decisions and implementation increments: `OT Project Demonstrator Design.docx`
- Controlled test catalogue, deterministic scenario time, expected outcomes, negative-test interpretation, Exploration verification, evidence strategy and 124-requirement verification mapping: `OT Project Validation Plan.docx`
- Accepted generic active-fault isolation rule, A/B/C boundary evidence conditions, eight-section v1.1 incidence answer key, all-open plus zero-source-path proof and application verification: `DC-003-generic-active-fault-isolation-boundary-derivation.md` together with the applied sections in the six authoritative Word artefacts
- Accepted multi-run exploratory validation determination: `DC-004-multi-run-exploratory-validation-determination.md` together with authoritative Validation Plan v1.2 Section 19 and Demonstrator Design v0.4 Section 36. These define the immutable historical-catalogue/test-definition resolver, engineering-expectation versus provenance separation and constituent-owned scenario-time rule. Final independent review accepted the complete PR #10 application boundary at exact tip `eced7c06c27b959cdb29d3aaa9351ca11cb5e258`; QA-041 through QA-049 are closed for this boundary.
- Accepted validation-suspension assurance design and application: `DC-005-controlled-validation-suspension-and-blocked-test-determination.md` together with Requirements Specification v0.4 clarification at `REQ-VAL-007`–`REQ-VAL-009`, Validation Plan v1.2 Section 20, Demonstrator Design v0.4 Section 37, System Architecture v0.3 Section 27 and Workflow Design v0.3 Section 28. The independently accepted machine/application treatment is preserved in the reviewed PR #10 history; this acceptance does not authorise I9.

## Mandatory implementation discipline
When coding begins:
1. identify the requirement IDs being implemented;
2. read the associated detailed design rationale;
3. read the concrete Network Model values/state rules;
4. read the applicable System Architecture component, interface, information-class and architecture-decision sections;
5. read the applicable Workflow Design command, transaction, mode, evidence and decision sections;
6. read the applicable Demonstrator Design module, record, API, screen, interaction, technology and implementation-increment sections;
7. after Step 9 acceptance, read the applicable Validation Plan catalogue test, expected result, deterministic-time rule and evidence obligation;
8. implement generic behaviour rather than canned scenario outputs where the design requires derivation;
9. add tests against the formal requirement and its controlled catalogue mapping;
10. do not invent missing engineering behaviour inside code.

## Accepted DC-003 implementation reading path

For active-fault isolation work, read all of the following before coding:

1. Engineering Design Brief Section 23 and DD-22 for design intent and rationale;
2. Network Model Section 18 for the generic rule, A/B/C evidence conditions, corrected v1.1 answer key and proof criterion;
3. System Architecture Section 26 and AD-SA-013 for information ownership and processing boundaries;
4. Workflow Design Section 27 and AD-WF-017 for command/evidence/recalculation sequence;
5. Demonstrator Design Section 35 and AD-DD-023 for backend records, interaction and prohibited shortcuts; and
6. Validation Plan Sections 7–8, 12, 14–18 and AD-VP-012/015/018 for catalogue coverage, package lifecycle and acceptance gates.

Accepted I1 instantiated the approved Network Configuration v1.0 and v1.1 definitions as separate schema-valid, hash-verified immutable implementation packages. Accepted I2–I4 consume those packages through common algorithms without modifying them. Authorised I5 binds validation executions and evidence to the selected package identity and preserves the same-build v1.0 failure / v1.1 corrected comparison.

## I5 validation/evidence implementation reading path

For controlled definition, execution, checkpoint, comparison and evidence work, read all of the following before coding:

1. Requirements Specification `REQ-VAL-001–014`, `REQ-CFG-009–012`, `REQ-EVT-001–011`, `REQ-NFR-003` and `REQ-NFR-008`;
2. Network Model Sections 16–18 for the approved answer key and DEF-001 basis;
3. System Architecture Sections 12, 17, 19–20 and 26.4–26.5 for record ownership, provenance and separation;
4. Workflow Design Sections 5.2–5.3, 14–19, 22 and 27.3–27.4 for lifecycle, checkpoint and evidence flow;
5. Demonstrator Design Sections 8.7, 9, 10.5, 12, 19, 21–22 and 27–28 for module, persistence and interface decisions; and
6. Validation Plan Sections 3–15 and 17–18 in full, including all 24 catalogue/procedure rows and the exact 124-row RTM.

## I6 operational UI implementation reading path

For the local review workspace and projection-only frontend, read all of the following before changing I6 behaviour:

1. Requirements Specification presentation paths for `REQ-NET-*`, `REQ-TOP-*`, `REQ-TEL-*`, `REQ-ALM-*`, `REQ-OUT-*`, `REQ-RST-*`, `REQ-EVT-*`, `REQ-VAL-*`, and `REQ-NFR-001`, `005–007`, `009`;
2. Network Model Sections 13–16 for the one-line entities and approved formal N0–N5 answer key;
3. System Architecture Sections 13, 17–18, 20–21 and 26.3 for information ownership and projection boundaries;
4. Workflow Design Sections 9–14 and 18–21 for action, chronology, evidence and review handling;
5. Demonstrator Design Sections 13–19, 23–25 and 27–29 for screens, interactions and implementation decisions; and
6. Validation Plan Sections 6–10 and 13–15, especially `VT-FML-N0-N5-001`, `VT-ALM-EVT-001`, telemetry presentation cases, `VT-VAL-RECORD-001` and `VT-NFR-REVIEW-001`.

## I7 investigation/correction implementation reading path

For the controlled DEF-001 consequence-to-source investigation and correction chain, read all of the following before changing I7 behaviour:

1. Requirements Specification `REQ-CFG-001–012`, `REQ-VAL-005`, `REQ-VAL-010–012` and the applicable `REQ-TOP-*`/`REQ-OUT-*` consequence requirements;
2. Network Model Section 16.5 and Sections 17–18.7 for the defective/corrected answer key, package difference and investigation basis;
3. System Architecture Sections 19–20 and 26.4–26.5 for defect, correction, evidence and configuration ownership;
4. Workflow Design Sections 15–17 and 19 for the ordered investigation, correction, repeat and regression workflow;
5. Demonstrator Design Sections 19, 21–22, 27–28 and 35.4–35.5 for records, persistence, read models, screens and increment boundary; and
6. Validation Plan definitions/procedures `VT-TOP-DEF-001`, `VT-CFG-INV-001`, `VT-DET-REPEAT-001`, `VT-FML-N0-N5-001` and Sections 11, 13–15.

## I8 exploration/export implementation reading path

For corrected-v1.1 Exploration Mode and immutable evidence-package export, read all of the following before changing I8 behaviour:

1. Requirements Specification `REQ-EXP-001–007`, applicable `REQ-RST-*`, `REQ-VAL-009` and `REQ-NFR-008`;
2. Network Model Sections 15.1, 17.12 and 18 for transient selection, representative outcomes and generic DC-003 incidence;
3. System Architecture Sections 17.2–17.3, 20 and 26 for mode, evidence, configuration and ownership boundaries;
4. Workflow Design Sections 13–14, 19 and 27.1–27.3 for exploration actions, separation, export and evidence handling;
5. Demonstrator Design Sections 20–21, 27–29 and 35 for approved screen, run, module and evidence-package design; and
6. Validation Plan `VT-EXP-ALL-001`, `VT-EXP-ROLE-001`, `VT-EXP-SEPARATION-001`, `VT-PKG-EVIDENCE-001`, `VT-NFR-REVIEW-001` and Sections 12–15.

I8 consumes the accepted I2 topology/outage, I3 transaction/event, I4 restoration, I5 validation/evidence, I6 projection and I7 investigation authorities. Runtime engineering results must remain configuration-driven; answer-key section/boundary/outcome values belong only in tests. Evidence ZIPs are assembled from immutable preserved execution/evidence records and remain explicitly FORMAL or EXPLORATORY.

## Accepted DC-004 application reading path

Before the separately authorised DC-004 application phase on a fresh `agent/dc-004-application` branch from accepted `main`, read:

1. accepted DC-004 in full;
2. Validation Plan v1.1 Sections 3–4, 7–8, 12–15 and authoritative Section 19;
3. Demonstrator Design v0.3 Sections 8.7, 9, 19–21, 28 and authoritative Section 36;
4. accepted I5 validation/evidence and I8 exploration/export closeouts; and
5. the unchanged catalogue rows for `VT-EXP-ALL-001` and `VT-EXP-ROLE-001` as the pre-change identity, plus the accepted I8 export service's current-catalogue equality boundary that DC-004 must correct during later controlled application.

Current gate: I8 is accepted after final independent review of tip `111df44a425731dc7f44c437c1d675e5dac85263`. **DC-004 and DC-005 are accepted authoritative design and machine/application baselines. Final independent review accepted exact PR #10 tip `eced7c06c27b959cdb29d3aaa9351ca11cb5e258`; QA-041 through QA-049 are closed and the reviewed history is incorporated into `main`. I9 remains stopped and requires separate user authorisation from the resulting accepted-main baseline.**

Do not reuse the stopped `agent/i9-packaging-review` branch for DC-004 application work.

If a required implementation choice is genuinely unspecified, raise it as a design question before coding it.

## Accepted DC-005 application reading path

Before the separately authorised PR #10 reconciliation and combined QA-041 + QA-042/DC-005 application, read in order:

1. `02-change-control/DC-005-controlled-validation-suspension-and-blocked-test-determination.md` in full;
2. accepted Validation Plan v1.2 Sections 4, 14, 19 and 20;
3. accepted Demonstrator Design v0.4 Sections 8.7, 9, 19–21, 36 and 37;
4. accepted System Architecture v0.3 Sections 10, 12, 20 and 27;
5. accepted Workflow Design v0.3 Sections 5.2, 14, 19 and 28;
6. accepted Requirements Specification v0.4 `REQ-VAL-001–014`, especially the controlled clarification to `REQ-VAL-007`–`REQ-VAL-009`; and
7. accepted DC-004 Sections 5–13 for constituent identity, exact completeness, aggregation, historical resolution and export.

Application and re-review shall confirm exactly five condition IDs (`VSC-001`–`VSC-005`), the attempt/result lifecycle, non-overlapping classifier, trusted target/provenance anchor, condition-specific evidence and bounded authority, deterministic reason, immutable history, FORMAL/EXPLORATORY separation and the controlled DC-004 execution/suspension source union. It shall also confirm unchanged requirement IDs/count/RTM, Design Brief, Network Model and I9 behaviour, while retaining the historical catalogue and applying only the separately authorised machine changes.
