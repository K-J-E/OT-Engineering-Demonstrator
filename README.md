# OT Graduate Demonstrator

A local, engineering-first demonstration of how power-utility OT information can be separated, processed and reviewed across conceptual GIS, SCADA, ADMS and OMS responsibilities.

The project was built as a graduate OT consulting work package: the engineering baseline came first, the software implements that approved baseline, and validation/investigation evidence remains traceable to controlled configuration and source records.

> **Fictional and simulated:** TasGrid East, its network and every operational record are fictional. This application has no connection to real SCADA, ADMS, OMS, GIS or field equipment and cannot issue real control commands.

## What the showcase demonstrates

- Configuration-driven network topology, source attribution, outage extent and customer impact.
- A formal SEC-A2 fault sequence from normal operation through isolation and alternate-feeder restoration.
- Conservative restoration decisions: `PERMITTED`, `REJECTED`, `BLOCKED` and `NO_CANDIDATE` retain distinct engineering meanings.
- Telemetry as value + quality + timestamp, with freshness assessed independently.
- A seeded configuration defect that propagates through the normal topology/outage engine—there is no special wrong-answer code.
- Evidence-led investigation from consequence through SCADA, topology/source paths and OMS impact to the exact configuration difference.
- Exploration of any configured distribution section using the same engineering algorithms, without promising a restorable outcome.
- Immutable validation, investigation and export provenance with separate `FORMAL` and `EXPLORATORY` evidence classes.

## Run locally

Prerequisites:

- Python 3.13
- Node.js 24
- npm 11
- Git

From a fresh checkout:

```bash
./scripts/showcase.sh
```

The command installs the locked dependencies when needed, builds the frontend and starts one loopback-only process at [http://127.0.0.1:8000](http://127.0.0.1:8000). Press `Ctrl+C` to stop it.

Useful lifecycle commands:

```bash
./scripts/showcase.sh setup   # install locked dependencies and build
./scripts/showcase.sh start   # build if needed, then start locally
./scripts/showcase.sh verify  # backend, catalogue, component and production-build checks
./scripts/showcase.sh reset   # clear local runtime/evidence output only
```

`reset` does not modify controlled configuration, validation definitions or engineering documents.

## Suggested 10-minute walkthrough

1. **Formal operation:** start the formal v1.1 run and follow the backend-authorised actions. The controlled results are N1 `850` affected, N3 `670` affected, N4 `1.50 MW` transfer / `5.70 MW` / `95.0%` / `PERMITTED`, and N5 `220` affected with `450` restored.
2. **Seeded defect:** return to setup, start the DEF-001 investigation, and follow the evidence chain from the v1.0 `400 affected / FAIL` result to the incorrect `SW-A23` endpoint, correction, v1.1 `850 / PASS` repeat and preserved regression evidence.
3. **Exploration:** start a corrected-v1.1 Exploration run for `SEC-B2` to see feeder roles reverse through configuration-derived topology. Other selections can legitimately be permitted, rejected or have no candidate.
4. **Safety case:** start the stale-evidence walkthrough. `SW-A12` and `SW-A23` remain `GOOD` but become `STALE`; isolation evidence becomes `UNPROVEN` and unsafe switching actions are withheld with explicit reasons.
5. **Engineering basis and evidence:** review the persistent run/configuration/build identities, Engineering Basis view, validation records and evidence export.

## Engineering authority

The repository preserves the full lifecycle rather than replacing it with a software-only summary:

1. [`00-governance/`](00-governance/) — purpose, scope and locked project decisions.
2. [`01-engineering-source-documents/`](01-engineering-source-documents/) — authoritative detailed engineering documents.
3. [`02-change-control/`](02-change-control/) — accepted design changes DC-001 through DC-008.
4. [`03-derived-reference/`](03-derived-reference/) — navigation, QA tracking and increment closeouts; derived only.
5. [`config/network/`](config/network/) — immutable defective v1.0 and corrected v1.1 implementation packages.
6. [`validation/test-definitions/`](validation/test-definitions/) — active and historical hash-protected validation catalogues.
7. [`app/`](app/) — the implementation of the approved baseline.

The current detailed baseline includes 124 stable requirement IDs, 24 validation tests, 286 requirement-to-test relationships, 35 determination methods, 214 criteria and 15 operational-event types. Exact authoritative identities are recorded in [`CURRENT-BASELINE-MANIFEST.json`](CURRENT-BASELINE-MANIFEST.json).

## Technology

- Python 3.13, FastAPI, Pydantic, NetworkX and SQLite
- React 19, TypeScript 6, Vite 8 and Cytoscape.js
- Pytest, Vitest and Playwright
- SHA-256 protected configuration, catalogue, build and evidence identities

The runtime is intentionally one local process serving a production frontend and API on loopback. SQLite files and generated evidence are local, ignored runtime outputs.

## Deliberate limits and future work

This is not a commercial ADMS, protection study, network editor, real-time platform or production control system. The electrical model is intentionally simplified and deterministic; fault type remains abstract; no real interfaces or autonomous/AI functions exist in V1.

The broader controlled 24-test campaign is not represented as complete merely because implementation regressions pass. Missing campaign evidence remains `NOT_EVALUATED` / `INCOMPLETE`. Post-outreach work includes wider campaign execution, additional accessibility/browser review and potential V2 automation of repetitive configuration QA, regression selection, evidence assembly and traceability checks.

## Repository status

**Showcase V1 is accepted for outreach.** The accepted release packages the reviewed V1 engineering implementation and showcase workflows; it is not a production or real-OT-control system. The complete controlled 24-test campaign has not been executed, and implementation regressions remain conformance evidence rather than manufactured catalogue PASS/FAIL verdicts.
