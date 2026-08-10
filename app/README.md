# Application implementation through authorised I7

This directory contains the reproducible local application foundations and the
separately authorised I1–I7 increments. I6 presents backend-owned
topology/outage, telemetry, event, restoration and validation records without
moving engineering authority into the browser. I7 adds the controlled DEF-001
consequence-to-source investigation, immutable defect/correction records,
same-build corrected repeat and full corrected regression presentation. It does
not contain the I8 Exploration/export workflow or I9 packaging.

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

The accepted 24-test machine catalogue under `validation/test-definitions/` is a
hash-protected counterpart of Validation Plan v1.0. I5 binds each execution to the
backend-controlled build, configuration, definition version/hash, run, mode,
evidence class and controlled scenario time. Captured evidence is distinct from
the operational-event catalogue and finalised records are immutable.

## I7 verification state

I7 is implemented on its dedicated review branch and remains pending independent
review. Verification covers the real v1.0 400-customer failure, the ordered
seven-step investigation, the exact immutable package difference, separate
DEF-001/COR-001 records, the same-build v1.1 850-customer PASS and all six
corrected N0–N5 regression checkpoints. Backend, React/Cytoscape and Chromium
workflows, the clean exact-toolchain install and pinned TypeScript/Vite production
build pass. The latest assurance-correction commit and clean build identity are
recorded in the I7 increment closeout pending independent re-review.

The canonical network packages, validation catalogue, dependency versions and
lockfiles are unchanged. I8 has not begun.
