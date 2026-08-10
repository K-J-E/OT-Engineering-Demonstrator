# Controlled Network Configuration Packages

`v1.0/` and `v1.1/` are separately identifiable immutable implementation inputs instantiated from the approved Network Model. The application may load and hash-verify them; it shall not create, overwrite, silently correct or derive one package from the other at runtime.

The engineering payloads differ only at `connectivity_edges.EDGE-SW-A23-1.endpoint_a_id`:

- v1.0: `SEC-B3` — defective input;
- v1.1: `SEC-A2` — corrected baseline.

Package manifests carry version/status identity and the controlled file hashes. They are metadata differences, not additional engineering-content differences.
