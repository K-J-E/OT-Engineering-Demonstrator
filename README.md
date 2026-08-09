# OT Graduate Demonstration Project — Authoritative Detailed Baseline

Baseline date: 2026-08-09
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

The original uploaded pre-change files were copied byte-for-byte into the initial baseline. Their
historical hashes are preserved in `BASELINE-MANIFEST.json` and remain recoverable through Git
history.

The canonical files in `01-engineering-source-documents/` now contain the accepted working
baseline after DC-001 and DC-002. Their current hashes and structural metadata are recorded in
`CURRENT-BASELINE-MANIFEST.json`.

## Change status

DC-001 — Consistent Network Entity Modelling — is applied and accepted.

DC-002 — Selectable Fault Location in Exploration Mode — is applied, verified and accepted.

The current detailed Design Brief, Requirements Specification and Network Model are revision
0.3. The System Architecture and Workflow Design are revision 0.1. They remain working Draft
engineering documents because subsequent controlled design development may require further
revision before final client-facing packaging.

The Simplified Network Model is complete through Section 17.13 and constitutes the Step 5
engineering answer key. Step 6 — System Architecture is established through Section 25 and
defines the logical component, information-ownership, interface, scenario, restoration,
configuration and evidence boundaries for downstream design. Step 7 — Workflow Design is
established through Section 26 and defines the controlled actor, command, processing, formal,
exploratory, restoration, defect-investigation, repeat-validation and evidence workflows. The
next lifecycle activity is Step 8 — Demonstrator Design.

## Future coding gate

Before coding a subsystem, use the relevant detailed design sections, System Architecture,
Workflow Design, Network Model answer key AND corresponding formal requirements. If
implementation encounters an unresolved choice, do not guess: record it as a design
question/change and resolve it against the engineering baseline first.
