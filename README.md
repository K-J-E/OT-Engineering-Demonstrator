# OT Graduate Demonstration Project — Authoritative Detailed Baseline

Baseline date: 2026-08-10
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

The canonical files in `01-engineering-source-documents/` now contain the accepted working
baseline after DC-001, DC-002 and DC-003. Their current hashes and structural metadata are recorded in
`CURRENT-BASELINE-MANIFEST.json`.

## Change status

DC-001 — Consistent Network Entity Modelling — is applied and accepted.

DC-002 — Selectable Fault Location in Exploration Mode — is applied, verified and accepted.

DC-003 — Generic Active-Fault Isolation Boundary Derivation — is applied, cross-document
verified and accepted. It defines configuration-driven incident isolation boundaries, the
trustworthy OPEN / trustworthy CLOSED / UNPROVEN evidence conditions, one-action recalculation
and the all-open plus zero-active-source-path isolation proof without adding requirements or new
restoration behaviour.

The current detailed Design Brief and Network Model are revision 0.4; the Requirements
Specification remains revision 0.3 with 124 unique requirements. The System Architecture,
Workflow Design and Demonstrator Design are revision 0.2. They
remain working Draft engineering documents because subsequent controlled design development
may require further revision before final client-facing packaging.

The Simplified Network Model v0.4 is complete through Section 18.7 and constitutes the Step 5
engineering answer key. Step 6 — System Architecture v0.2 is established through Section 26.5 and
defines the logical component, information-ownership, interface, scenario, restoration,
configuration and evidence boundaries for downstream design. Step 7 — Workflow Design v0.2 is
established through Section 27.4 and defines the controlled actor, command, processing, formal,
exploratory, restoration, defect-investigation, repeat-validation and evidence workflows.
Step 8 — Demonstrator Design v0.2 is established through Section 35.6 and defines the practical local
application, module and data-ownership boundaries, storage and identifier decisions, API and
transaction model, screen/navigation structure, exploration/evidence/investigation presentation,
technology stack, implementation increments and coding gate. Step 9 — Validation Plan v1.0 is the
accepted current validation baseline through Section 18. It defines the 24-test
catalogue, deterministic scenario-time and telemetry-boundary rules, formal and exploratory
verification approach, evidence strategy and requirements-to-verification mapping for all 124
formal requirements. DC-003 was applied and cross-document verified before final Step 9
acceptance. Implementation proceeds only through separately authorised increments. I1–I6 are
accepted implementation baselines. I7 — Investigation/Correction has been implemented and
verified on its dedicated review branch and is pending independent review; it remains unmerged.
I8 has not begun and is not authorised.

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
