# Application implementation through accepted I8

This directory contains the reproducible local application foundations and the
independently accepted I1–I8 increments. I6 presents backend-owned
topology/outage, telemetry, event, restoration and validation records without
moving engineering authority into the browser. I7 adds the controlled DEF-001
investigation/correction chain and I8 adds corrected-v1.1 Exploration plus
immutable evidence export. The separately reviewed DC-004 application branch
adds the accepted multi-run exploratory validation-assurance treatment; it is
pending independent review and is not an accepted implementation baseline.
I9 remains stopped.

## Pinned local toolchain

- Python 3.13.15
- Node.js 24.19.0
- npm 11.17.0

Backend dependencies are pinned in `pyproject.toml` and `requirements.lock`.
Frontend dependencies are pinned in `app/frontend/package.json` and
`app/frontend/package-lock.json`.

Use a normal wheel installation for the Python package. Python 3.13.15 skips the
hidden `.pth` file currently produced by setuptools 84.0.0 for editable installs,
so an editable install is not part of this controlled toolchain.

The canonical Network Configuration v1.0 and v1.1 packages under `config/network/`
are read-only runtime inputs. The application loader verifies their manifests and
SHA-256 hashes before returning typed configuration records.

The controlled 24-test machine catalogue under
`validation/test-definitions/` is a hash-protected counterpart of the accepted
Validation Plan. DC-004 preserves exact catalogue v1.0 as historical input and
promotes active catalogue v1.1 with the accepted 9/4 constituent case sets while
retaining 124 requirements and 286 RTM relationships. I5/DC-004 bind each
execution to backend-controlled build, configuration, catalogue/definition,
case where applicable, run, mode, evidence class and controlled scenario time.
Captured evidence remains distinct from the 15 operational-event types and
finalised execution/composite records are immutable.

## Current verification state

I8 is the accepted implementation baseline. Its reviewed Exploration and
evidence-export treatment remains unchanged. The DC-004 application phase is
implemented and verification-passed on `agent/dc-004-application`, including
historical catalogue resolution, exact constituent execution, immutable
composite assurance, review projection and preserved-record export. Backend,
React/Cytoscape and Chromium workflows, the clean exact-toolchain install and
pinned TypeScript/Vite production build pass.

The canonical network packages, electrical authorities, dependency versions
and lockfiles are unchanged. The DC-004 application requires independent review
and incorporation into `main` before I9 can be separately resumed.
