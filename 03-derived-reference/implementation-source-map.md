# Implementation Source Map

This file is a navigation aid only. It is not a replacement for the detailed documents.

## Engineering basis
- Domain/research reasoning and engineering decisions: `Engineering Investigation and Research.docx`
- Proposed solution/design behaviour and assumptions: `OT Engineering Design Brief.docx`
- Formal testable behaviour: `OT Project Requirements Specification.docx`
- Concrete assets, topology, loads, customers, device IDs and network states: `OT Project Network Model.docx`

## Mandatory implementation discipline
When coding begins:
1. identify the requirement IDs being implemented;
2. read the associated detailed design rationale;
3. read the concrete Network Model values/state rules;
4. implement generic behaviour rather than canned scenario outputs where the design requires derivation;
5. add tests against the formal requirement;
6. do not invent missing engineering behaviour inside code.

If a required implementation choice is genuinely unspecified, raise it as a design question before coding it.
