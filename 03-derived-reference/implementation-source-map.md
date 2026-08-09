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

The repository currently holds the approved engineering definitions of Network Configuration v1.0 and v1.1; it does **not** yet hold immutable implementation configuration packages. After explicit implementation authorisation, the first implementation baseline must instantiate both definitions as separate schema-valid immutable packages, capture their hashes and verify the single controlled SW-A23 endpoint difference before validation execution.

Current gate: DC-003 is applied/cross-document verified and Validation Plan v1.0 is the accepted Step 9 baseline. **Implementation is still not authorised.** Begin only after the user explicitly authorises a bounded implementation increment, then resolve IMP-001 at I1.

If a required implementation choice is genuinely unspecified, raise it as a design question before coding it.
