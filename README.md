# OT Graduate Demonstration Project — Authoritative Detailed Baseline

Baseline date: 2026-08-11
Status: CURRENT DRAFT ENGINEERING WORKING BASELINE

## Critical working rule

The detailed Word documents in `01-engineering-source-documents/` are the authoritative
engineering artefacts for ongoing design and later demonstrator implementation.

They are NOT summaries.

Future implementation must not infer a simpler design from a condensed reference document
when a more explicit decision, rationale, requirement, equation, state rule, identifier, diagram,
assumption, or verification method exists in these source documents.

## Authority hierarchy

1. `00-governance/` — governing project intent and locked decisions.
2. `01-engineering-source-documents/` — full-detail engineering baseline.
3. `02-change-control/` — accepted controlled amendments to the baseline.
4. `03-derived-reference/` — indexes/checklists only; never overrides source documents.
5. demonstrator implementation/code — must implement the approved engineering baseline.

## Authoritative detailed documents

- Engineering Investigation and Research.docx
- OT Engineering Design Brief.docx
- OT Project Requirements Specification.docx
- OT Project Network Model.docx
- OT Project System Architecture.docx
- OT Project Workflow Design.docx
- OT Project Demonstrator Design.docx
- OT Project Validation Plan.docx

The original uploaded pre-change files were copied byte-for-byte into the initial baseline. Their
historical hashes are preserved in `BASELINE-MANIFEST.json` and remain recoverable through Git
history.

The accepted working baseline after DC-001 through DC-006 is preserved from reviewed main. The
current dedicated branch contains the separately authorised DC-006 machine/catalogue application
for independent review. DC-006 promotes four reviewed authoritative revisions while
preserving their superseded, rejected first-application, independently reviewed technical-content
and administratively accepted identities in `CURRENT-BASELINE-MANIFEST.json`.

## Change status

DC-001 — Consistent Network Entity Modelling — is applied and accepted.

DC-002 — Selectable Fault Location in Exploration Mode — is applied, verified and accepted.

DC-003 — Generic Active-Fault Isolation Boundary Derivation — is applied, cross-document
verified and accepted. It defines configuration-driven incident isolation boundaries, the
trustworthy OPEN / trustworthy CLOSED / UNPROVEN evidence conditions, one-action recalculation
and the all-open plus zero-active-source-path isolation proof without adding requirements or new
restoration behaviour.

DC-004 — Multi-Run Exploratory Validation Determination — is accepted as the authoritative
validation/design treatment. It defines constituent cases, immutable composite determination,
historical catalogue/test-definition resolution and provenance boundaries without changing the
24-test catalogue, 124 requirements, 286 RTM relationships, 15 event types or electrical behaviour.
Its machine/application history is independently accepted at exact reviewed PR #10 tip
`eced7c06c27b959cdb29d3aaa9351ca11cb5e258` and incorporated into reviewed `main` without rewriting
the reviewed commits. Historical catalogue and first-application identities remain preserved. I9
remains stopped and requires separate user authorisation.

DC-005 — Controlled Validation Suspension and BLOCKED-TEST Determination — is accepted as the
authoritative validation-suspension design baseline. It defines the exact five accepted suspension
condition identities, a distinct attempt/result lifecycle, deterministic non-overlapping classifier,
trusted target/provenance anchor, bounded reviewer-authority control, immutable history and DC-004
composite relationship. Its machine application is independently accepted at reviewed PR #10 tip
`eced7c06c27b959cdb29d3aaa9351ca11cb5e258`; QA-041 through QA-049 are closed for this application
boundary. It introduces no electrical, restoration, RTM or event-type change. Requirements Specification v0.4 clarifies only
`REQ-VAL-007`–`REQ-VAL-009`, retaining their IDs, 124 total requirements and 286 mappings. Accepted
catalogue v1.1 changed only to machine-prove QA-041's exact 60,001 ms expectation and is now
preserved byte-for-byte as historical input on the DC-006 application branch. I9 remains stopped.

DC-006 — Controlled Validation Test Determination Methods — is accepted as the authoritative
validation-determination design and document baseline. Validation Plan v1.3 Section 21, System
Architecture v0.4 Section 28, Workflow Design v0.4 Section 29 and Demonstrator Design v0.5 Section
38 define the common criteria/finding model, four context kinds, direct and DC-004 constituent-case
coverage, reviewer boundary, deterministic PASS/FAIL aggregation and catalogue-history gate. The
corrected authoritative-document application was independently accepted at exact reviewed tip
`c19451134c36d13d54f2185a3eaa0f20fcce95f0`; DR-01–DR-07 and AA-01–AA-04 are closed. The machine
application now preserves catalogue v1.1 as immutable history and promotes active catalogue v1.2
with 35 determination methods and 214 criteria on its dedicated branch. That application remains
pending independent review and is not yet an accepted baseline. I9 remains stopped.

The accepted detailed Design Brief and Network Model are revision 0.4; accepted Requirements
Specification is revision 0.4 with 124 unique requirements. Accepted System Architecture and
Workflow Design are revision 0.4; accepted Demonstrator Design is revision 0.5 and accepted
Validation Plan is revision 1.3. DC-005 remains controlling through Requirements Specification
clarification at REQ-VAL-007–009, System Architecture Section 27, Workflow Design Section 28,
Demonstrator Design Section 37 and Validation Plan Section 20. DC-006 is controlling through the
four next sections identified above. The documents remain working Draft engineering artefacts
because further controlled development may require revision before final client-facing packaging.

The Simplified Network Model v0.4 is complete through Section 18.7 and constitutes the Step 5
engineering answer key. Step 6 — System Architecture v0.4 is established through Section 28.7 and
defines the logical component, information-ownership, interface, scenario, restoration,
configuration and evidence boundaries for downstream design. Step 7 — Workflow Design v0.4 is
established through Section 29.9 and defines the controlled actor, command, processing, formal,
exploratory, restoration, defect-investigation, repeat-validation and evidence workflows.
Step 8 — Demonstrator Design v0.5 is established through Section 38.8 and defines the practical local
application, module and data-ownership boundaries, storage and identifier decisions, API and
transaction model, screen/navigation structure, exploration/evidence/investigation presentation,
technology stack, implementation increments, coding gate and accepted DC-004/DC-005 validation-
assurance design plus the accepted DC-006 determination contract. Step 9 — Validation Plan v1.3 is
the accepted current validation-design baseline through Section 21.7. It defines the 24-test
catalogue, deterministic scenario-time and telemetry-boundary rules, formal and exploratory
verification approach, evidence strategy and requirements-to-verification mapping for all 124
formal requirements, together with the accepted 214-criterion DC-006 document identity. DC-003 was
applied and cross-document verified before final Step 9 acceptance. Implementation proceeds only
through separately authorised increments. I1–I8 are
accepted implementation baselines. I8 — Exploration and Export passed final independent
engineering/implementation review, including accepted QA-008 evidence export and independently
verified closure of QA-040. Its reviewed history is incorporated into `main`. DC-004 and DC-005 are
accepted authoritative design and machine/application baselines. Final independent review accepted
the complete PR #10 boundary at exact tip `eced7c06c27b959cdb29d3aaa9351ca11cb5e258`; QA-041 through
QA-049 are closed and the reviewed history is incorporated into `main`. The separately authorised
DC-006 machine/catalogue application is complete on its dedicated review branch, but remains
unaccepted pending independent review and incorporation. I9 remains stopped.

The approved Network Model contains the engineering definitions of defective Network
Configuration v1.0 and corrected v1.1. Accepted I1 instantiated both as separate immutable,
schema-valid and hash-verified implementation packages. I5 consumes them through the same approved
configuration loader and records their identities without modifying either package.

## Implementation gate

Before coding an authorised increment, use the relevant detailed design sections, System
Architecture, Workflow Design, Network Model answer key, accepted Validation Plan and corresponding
formal requirements. If
implementation encounters an unresolved choice, do not guess: record it as a design
question/change and resolve it against the engineering baseline first.
