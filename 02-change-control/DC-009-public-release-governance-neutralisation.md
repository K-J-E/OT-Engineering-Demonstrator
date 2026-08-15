# DC-009 — Public-Release Governance Neutralisation

Status: **Applied to the local public-release candidate; pending release review**

Date raised and applied: 2026-08-16

Change class: Governance presentation and public-release hygiene

## 1. Purpose and boundary

The original project vision, project definition and decisions record contained organisation-specific audience references that motivated the initial learning exercise. Those references are not required to explain, operate or validate the engineering artefact and are inappropriate in the neutral public repository.

DC-009 creates public-neutral revisions of those three governance records. It does not change:

- technical purpose or scope;
- requirements or accepted validation meanings;
- network configuration v1.0 or v1.1;
- topology, outage, telemetry, restoration or switching behaviour;
- validation catalogues, definitions, methods or evidence conclusions;
- defect, correction or repeat identities; or
- backend, frontend or database behaviour.

## 2. Controlled treatment

`BASELINE-MANIFEST.json` remains byte-identical and records the original historical baseline. The historical accepted source identities remain preserved in the untouched local accepted checkpoint `c8ebfe445affc915cc03c29840356da9d0917727` and its ancestry; those organisation-specific source revisions are intentionally absent from the public current tree.

`CURRENT-BASELINE-MANIFEST.json` binds the public-neutral current revisions:

| Artefact | Historical SHA-256 | Public-neutral SHA-256 |
|---|---|---|
| `00-governance/OT project vision.pdf` | `f0b24f1eff0f7f8f4fae65722cf44a54f7738bc085adb9adf8c2a5319baaac8e` | `4941bb198735e6bd26ab7f9cbea80e48b3ade56ebef89a78283c68e070c4d950` |
| `00-governance/OT demo project definition.pdf` | `b4ac9c24f1cb3692241aabdc958a895d9b06566ea5b9853ce4717910e395e572` | `bb0bc8fe60bdf0b2d2d06934fac8952e20fcbcda3201d8cb4a4c7cf09565b80d` |
| `00-governance/OT project decisions.md` | `dc2a1e7c2c1e8bd1321c718070b6afbc2cd10dd077699f88daccba4ee0a3d21d` | `6093daeeeb14a1200eb465a7c6c1d4dcfaf2784a82693e3e64009e43a4b3669a` |

The two PDFs retain their complete governing content. Only the organisation-specific introductory wording was replaced with neutral power-utility OT context. The decisions record changes only the target-audience line.

## 3. Verification requirements

Release review must confirm:

1. the three public-neutral files match `CURRENT-BASELINE-MANIFEST.json`;
2. `BASELINE-MANIFEST.json` remains unchanged from the accepted source checkpoint;
3. extracted PDF and DOCX text and all other tracked current-tree content contain no named employer;
4. all controlled application and validation tests remain unchanged and pass; and
5. the rendered PDF pages remain complete and readable.
