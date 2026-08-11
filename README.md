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

The accepted working baseline after DC-001, DC-002, DC-003 and authoritative design baselining of
DC-004 is preserved on reviewed `main`. This DC-005 design branch contains four explicitly proposed
authoritative revisions for independent review; it does not supersede the accepted baseline. Both
accepted and proposed identities are recorded in `CURRENT-BASELINE-MANIFEST.json`.

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
Its separate machine/application phase exists only on unchanged draft PR #10 and is stopped at the
QA-042 design-control boundary; it is not part of the accepted `main` baseline.

DC-005 — Controlled Validation Suspension and BLOCKED-TEST Determination — is proposed on this
branch and pending independent engineering review. It defines the exact five accepted suspension
condition identities, lifecycle/record/authority/evidence contracts, deterministic reason,
immutable history and DC-004 composite relationship. It introduces no machine implementation,
requirement, electrical, restoration, catalogue, RTM or event-type change. PR #10 remains
unchanged, QA-041 is not applied and I9 remains stopped.

The accepted detailed Design Brief and Network Model are revision 0.4; the Requirements
Specification remains revision 0.3 with 124 unique requirements. Accepted System Architecture and
Workflow Design remain revision 0.2; accepted Demonstrator Design is revision 0.3 and accepted
Validation Plan is revision 1.1. The DC-005 branch proposes System Architecture v0.3 Section 27,
Workflow Design v0.3 Section 28, Demonstrator Design v0.4 Section 37 and Validation Plan v1.2
Section 20. The accepted identities remain controlling until independent review and controlled
application. The documents remain working Draft engineering artefacts because further controlled
development may require revision before final client-facing packaging.

The Simplified Network Model v0.4 is complete through Section 18.7 and constitutes the Step 5
engineering answer key. Step 6 — System Architecture v0.2 is established through Section 26.5 and
defines the logical component, information-ownership, interface, scenario, restoration,
configuration and evidence boundaries for downstream design. Step 7 — Workflow Design v0.2 is
established through Section 27.4 and defines the controlled actor, command, processing, formal,
exploratory, restoration, defect-investigation, repeat-validation and evidence workflows.
Step 8 — Demonstrator Design v0.3 is established through Section 36.8 and defines the practical local
application, module and data-ownership boundaries, storage and identifier decisions, API and
transaction model, screen/navigation structure, exploration/evidence/investigation presentation,
technology stack, implementation increments, coding gate and accepted DC-004 multi-run
validation-assurance design. Step 9 — Validation Plan v1.1 is the
accepted current validation-design baseline through Section 19.9. It defines the 24-test
catalogue, deterministic scenario-time and telemetry-boundary rules, formal and exploratory
verification approach, evidence strategy and requirements-to-verification mapping for all 124
formal requirements. DC-003 was applied and cross-document verified before final Step 9
acceptance. Implementation proceeds only through separately authorised increments. I1–I8 are
accepted implementation baselines. I8 — Exploration and Export passed final independent
engineering/implementation review, including accepted QA-008 evidence export and independently
verified closure of QA-040. Its reviewed history is incorporated into `main`. DC-004 is accepted as
the authoritative design change. Its separate application branch/PR #10 remains draft and
unmerged; QA-041 remains pending there and QA-042 produced the accepted design-control stop now
addressed only by proposed DC-005. I9 cannot resume until DC-005 is independently dispositioned,
the separately authorised application work is corrected and accepted, and that reviewed baseline
is incorporated into `main`.

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
