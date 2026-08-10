# I1 application scaffold

This directory contains the reproducible backend and frontend foundations created by
Implementation Increment I1. It does not contain topology, outage, scenario,
restoration, validation-execution or operational-UI behaviour.

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
