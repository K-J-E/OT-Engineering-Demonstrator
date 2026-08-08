# OT Graduate Demonstration Project — Authoritative Detailed Baseline

Baseline date: 2026-08-08
Status: PRE-DC-001 / PRE-DC-002

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

## Source documents preserved

- Engineering Investigation and Research.docx
- OT Engineering Design Brief.docx
- OT Project Requirements Specification.docx
- OT Project Network Model.docx

The uploaded files have been copied byte-for-byte into this baseline. Their hashes are recorded
in `BASELINE-MANIFEST.json`.

## Change status

DC-001 and DC-002 have been discussed but are not applied by this consolidation operation.
They must be applied separately through controlled change.

Note: the supplied Network Model already contains some text reflecting the recently discussed
consistency refinement (including symmetric sectionalising devices / NM-P06). During DC-001
we will formally reconcile that document with the Design Brief, Requirements and change
record rather than silently treating the cross-document change as complete.

## Future coding gate

Before coding a subsystem, use the relevant detailed design sections AND the corresponding
formal requirements. If implementation encounters an unresolved choice, do not guess:
record it as a design question/change and resolve it against the engineering baseline first.
