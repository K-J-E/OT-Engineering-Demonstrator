# OT Engineering Demonstrator

A local, engineering-first demonstration of how power-utility OT information can be separated, processed and reviewed across conceptual GIS, SCADA, ADMS and OMS responsibilities.

The engineering baseline came first. The software implements that approved baseline, and validation/investigation evidence remains traceable to controlled configuration and source records.

> **Fictional and simulated:** TasGrid East, its network and every operational record are fictional. This application has no connection to real SCADA, ADMS, OMS, GIS or field equipment and cannot issue real control commands.

## What the showcase demonstrates

- Configuration-driven network topology, source attribution, outage extent and customer impact.
- Reviewer-driven trials from normal operation through isolation and alternate-feeder restoration.
- Conservative restoration decisions: `PERMITTED`, `REJECTED`, `BLOCKED` and `NO_CANDIDATE` retain distinct engineering meanings.
- Telemetry as value + quality + timestamp, with freshness assessed independently.
- A seeded configuration defect that propagates through the normal topology/outage engine—there is no special wrong-answer code.
- Evidence-led investigation from consequence through SCADA, topology/source paths and OMS impact to the exact configuration difference.
- Trials for any configured distribution section using the same operating logic, without promising a restorable outcome.
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

## Suggested walkthrough

1. **Reviewer-driven trial:** select `SEC-A2` for a smooth first run through the operating sequence. The controlled results are `850` customers affected, `670` remaining after normal-supply recovery, a `PERMITTED` alternate-supply decision, and `220` remaining after staged restoration.
2. **Validation and defect investigation:** start with the seeded v1.0 GIS endpoint error. Follow the internally coherent assurance result and independent validation failure to the exact source difference, record the correction, then repeat the full sequence against immutable configuration v1.1.
3. **Stale-telemetry safety case:** follow the sequence until exact-boundary stale readings make isolation evidence `UNPROVEN`. Unsafe switching remains unavailable and the blocked result is preserved with its reasons.
4. **Evidence:** review the saved operating states, assurance, validation method, technical traceability and downloadable evidence package for the completed case.

## Engineering authority

The repository preserves the full lifecycle rather than replacing it with a software-only summary:

1. [`00-governance/`](00-governance/) — purpose, scope and locked project decisions.
2. [`01-engineering-source-documents/`](01-engineering-source-documents/) — authoritative detailed engineering documents.
3. [`02-change-control/`](02-change-control/) — accepted design changes DC-001 through DC-009.
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

The local runtime is intentionally one process serving a production frontend and API on loopback. SQLite files and generated evidence are local, ignored runtime outputs. The public package uses the same FastAPI application and built React frontend in one container, with SQLite and evidence placed in an explicitly bounded ephemeral runtime directory.

## Release and development model

- `main` is the stable branch intended for the Railway-deployed public showcase.
- The exact accepted public tree is identified by a release tag such as `public-showcase-v1`.
- Unfinished V2 automation belongs on separate `feature/v2-*` branches.
- V2 changes continue through requirements, change control and testing, and reach `main` only after review.

This preserves one canonical demonstrator while allowing further engineering work to proceed without changing the accepted public release in place.

## Public deployment on Railway

The repository includes a pinned multi-stage [`Dockerfile`](Dockerfile) and [`railway.toml`](railway.toml) for one Railway web service. The build uses Python `3.13.15`, Node.js `24.19.0`, npm `11.17.0`, `npm ci`, the frontend lockfile and `requirements.lock`. The final process serves the portfolio, `/demo`, API, health check and evidence downloads from one origin.

Deployment steps after the release branch has been reviewed and merged:

1. Connect the GitHub repository to Railway and select `main` as the deployment branch.
2. Deploy the repository root as one service; Railway detects the Dockerfile and checks `/healthz`.
3. Generate the Railway domain. No database service, persistent volume, custom domain or secret is required.
4. The neutral portfolio defaults to this public repository, the reviewed `public-showcase-v1` tag and the controlled engineering-source-document directory. The frontend build variables `VITE_PORTFOLIO_GITHUB_URL`, `VITE_PORTFOLIO_RELEASE_URL` and `VITE_PORTFOLIO_EVIDENCE_URL` can override those destinations for a later release or host.
5. Use Railway's deployment history to redeploy or roll back to a previously accepted image.

Railway supplies `PORT` and `RAILWAY_GIT_COMMIT_SHA`. The hosted build identity binds that triggering commit, a clean packaged-deployment state, the pinned Python/Node/npm versions, both dependency-lock hashes, the backend source hash and the built frontend-bundle hash. Local runs continue to derive identity directly from Git and installed tools.

### Shared transient workspace

The public service deliberately remains a single ephemeral SQLite workspace, not a multi-user system. Every full load or browser refresh of `/demo` resets generated runtime/evidence state before the workspace opens. Navigation within the loaded demonstrator retains the active run. A container restart or redeploy also starts with a clean runtime.

This supports sequential review and prevents an abandoned prior walkthrough from blocking the next visitor or a repeated review in the same browser. It does **not** provide concurrent session isolation: two simultaneous reviewers share one transient workspace, and the later page load can reset the earlier reviewer's run. Refreshing `/demo` also deliberately abandons the current run. No persistent evidence is promised by the public service; downloadable evidence should be saved during the active visit.

## Deliberate limits and future work

This is not a commercial ADMS, protection study, network editor, real-time platform or production control system. The electrical model is intentionally simplified and deterministic; fault type remains abstract; no real interfaces or autonomous/AI functions exist in V1.

The broader controlled 24-test campaign is not represented as complete merely because implementation regressions pass. Missing campaign evidence remains `NOT_EVALUATED` / `INCOMPLETE`. Future work includes wider campaign execution, additional accessibility/browser review and potential V2 automation of repetitive configuration QA, regression selection, evidence assembly and traceability checks.

## Repository status

**Public Showcase V1 is the release candidate described by this branch.** It packages the reviewed V1 engineering implementation and showcase workflows; it is not a production or real-OT-control system. The complete controlled 24-test campaign has not been executed, and implementation regressions remain conformance evidence rather than manufactured catalogue PASS/FAIL verdicts.
