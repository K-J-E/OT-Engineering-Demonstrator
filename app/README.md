# Application implementation through authorised I6

This directory contains the reproducible local application foundations and the
separately authorised I1–I5 backend increments plus the I6 operational review
workspace. I6 presents backend-owned topology/outage, telemetry, event,
restoration and validation records without moving engineering authority into the
browser. It does not contain the I7 defect-investigation presentation, I8
Exploration/export workflow or I9 packaging.

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

## I6 verification state

I6 is implemented at bounded commit
`b7993d9bc2ca224df8f5721e372c0d4e39d69366` and remains pending independent
review. Verification passed with 99 backend tests, 9 React/Cytoscape component
tests, one real-browser formal N0–N5 workflow, a clean exact-toolchain install and
the pinned TypeScript/Vite production build. The clean implementation build ID is
`2c5123bfab1359865ff4a27285bd14a2911b38dd1dfcc56442c7384d37e79d28`.

The canonical network packages, validation catalogue, dependency versions and
lockfiles are unchanged. I7 has not begun.
