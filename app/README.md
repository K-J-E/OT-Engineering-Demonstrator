# Demonstrator application

The application implements the approved engineering baseline as a local, simulated review workspace. The backend owns configuration loading, topology/outage derivation, telemetry validity, scenario transactions, restoration assessment, validation, investigation and evidence export. The React frontend is a projection and command-request surface; it does not reproduce engineering decisions.

Use the repository-level command:

```bash
./scripts/showcase.sh
```

It builds the frontend and starts the FastAPI application on loopback at `http://127.0.0.1:8000`. Runtime SQLite files live under `app/.runtime/`; generated evidence packages live under `evidence/exports/`. Both are ignored and can be cleared with `./scripts/showcase.sh reset` without changing controlled inputs.

The hosted public composition uses the same application behind `ot_demo.api.hosted:create_hosted_app`. It serves the built frontend and API from one origin, disables interactive API documentation, writes only inside its configured ephemeral runtime boundary, and gives each fresh sequential browser a clean shared showcase workspace. Local composition and loopback-only behaviour remain unchanged.

See the root [`README.md`](../README.md) for prerequisites, the recommended walkthrough, engineering authority and project limits.
