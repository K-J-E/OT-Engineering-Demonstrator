---
Status: Accepted I1 implementation baseline — independently verified
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-10
Increment: I1 — Contracts and Inputs
---

# I1 Increment Closeout — Contracts and Inputs

## 1. Authorisation, branch and boundary

The user explicitly authorised I1 only. Work was created on
`agent/i1-contracts-and-inputs` from reviewed `main` commit
`f69b9138448430246637cd625b3a240743e3a9ee`.

Implemented scope is limited to repository/application scaffolding, strict typed
configuration-domain contracts, configuration loading and hashing, initial SQLite
migrations, exact dependency pinning, build-identity generation, immutable Network
Configuration v1.0/v1.1 packages, I1 tests and traceability.

No topology traversal, active-edge calculation, source tracing, section
energisation, outage/customer-impact processing, scenario orchestration,
restoration logic, formal validation execution or operational UI behaviour is
present. I2 has not started.

## 2. Authoritative sources used

The mandatory I1 source set in Implementation Control Plan Section 4 was read
before implementation:

- Project Vision, Project Definition and Project Decisions;
- accepted DC-001, DC-002 and DC-003, the current baseline manifest and the
  implementation source map;
- Requirements Specification rows `REQ-NET-001–011`, `REQ-CFG-001–003`,
  `REQ-CFG-006`, `REQ-CFG-008–010`, `REQ-NFR-002`, `REQ-NFR-004` and
  `REQ-NFR-009`, including rationale and verification methods;
- Network Model Sections 2–15, 17.1–17.4, 17.9–17.11 and 18.5–18.6;
- System Architecture Sections 5, 14–15, 21 and 26.4–26.5;
- Workflow Design Sections 5, 18, 22 and 27.4;
- Demonstrator Design Sections 4–12, 26–27, 29–32 and 35.5–35.6; and
- Validation Plan Sections 2–5, `VT-CFG-BASE-001`, Sections 10.1, 11, 14 and 15.

## 3. Produced implementation foundation

- `app/backend/ot_demo/domain/`: strict immutable enums, value objects and network
  configuration entities with referential/consistency validation only.
- `app/backend/ot_demo/modules/configuration/`: package metadata and loader
  contracts owned by the configuration module.
- `app/backend/ot_demo/infrastructure/`: canonical hashing, hash-verifying JSON
  loading, deterministic configuration comparison, build identity and migration
  foundations.
- `app/backend/ot_demo/api/` and `app/frontend/`: reproducible non-operational
  scaffolds only.
- `config/network/schema/v1/`: checked-in JSON Schema generated from the strict
  domain contract.
- `config/network/v1.0/` and `v1.1/`: separate canonical data and manifest files;
  neither is generated from the other at runtime.
- `.python-version`, `.nvmrc`, `pyproject.toml`, `requirements.lock`, frontend
  package/lock files and the build-manifest generator.
- repository `.gitattributes` enforcing deterministic LF text checkout bytes and
  explicit binary treatment for authoritative documents and common binary formats.
- initial SQLite schema for migration history, configuration catalogue records and
  application-build records.
- unit/integration tests for schema parity, immutability, unknown-field rejection,
  manifest ID/version consistency, package identity/hashes, tamper rejection,
  exact configuration difference, build-manifest assembly and input participation,
  approved values/IDs, packaged migration availability and empty-database migration.

Connectivity-edge IDs are deterministic implementation record identifiers required
by the approved Step 8 `ConnectivityEdge` contract; they do not replace or modify
the stable engineering asset IDs. Presentation data is not needed in I1 and has not
been invented.

## 4. Requirements and gate traceability

| Requirement / gate | I1 implementation and evidence | I1 coverage status |
|---|---|---|
| `REQ-NET-001–011` | Typed source, feeder, breaker, section, switch, connectivity, load, capacity and customer-zone records; both packages; schema and approved-value tests. | I1 contract/configuration foundation complete; later behavioural/presentation verification remains allocated. |
| `REQ-CFG-001–003` | v1.0 contains the approved SEC-B3↔SW-A23 error; both versions share one schema/loader/comparator; no defect-specific processing exists. | I1 configuration portion complete; normal topology processing is I2. |
| `REQ-CFG-006` | I1 stores no scenario telemetry and therefore introduces no false telemetry condition. | Configuration boundary confirmed; scenario evidence is I3/I5. |
| `REQ-CFG-008–010` | v1.1 contains the approved correction; v1.0 and v1.1 remain separately identifiable and hash verified. | I1 package-preservation foundation complete. |
| `REQ-NFR-002` | Approved stable asset IDs are retained across typed records, packages and tests. | I1 foundation complete. |
| `REQ-NFR-004` | Only the approved fictional TasGrid network/customer data is instantiated; the scaffold states simulated operation/no real control. | I1 configuration/review portion complete. |
| `REQ-NFR-009` | Equivalent feeders, sections, devices, edges and customer mappings use consistent structures and validation rules. | I1 model/configuration portion complete. |
| `VT-CFG-BASE-001` | Independent package loads, schema parity, values/IDs, SHA-256 verification, tamper rejection and machine-verifiable single-difference test. | I1 gate passed; no claim of a formal I5 execution record. |
| `VT-TOP-DEF-001`, `VT-CFG-INV-001` | Package-input and configuration-comparison portions only. | Later behavioural/workflow portions intentionally not started. |
| `VT-NFR-REVIEW-001` | Stable IDs, fictional boundary, consistent modelling, exact dependencies and scaffold-scope inspection. | I1 review portion passed; full review remains I9. |

## 5. Controlled configuration identities

| Item | v1.0 | v1.1 |
|---|---|---|
| Configuration ID | `network-configuration-v1.0` | `network-configuration-v1.1` |
| Status | `DEFECTIVE_TEST_INPUT` | `CORRECTED_BASELINE` |
| Data SHA-256 | `67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3` | `7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281` |
| Manifest/package SHA-256 | `d0243fae46e6a5d403855953e14cdedbcdae9c71af7761a1aba49f88470bc12d` | `e0f16f3acdf2e85aa04cd23bb4b584a868626117b68f682d1219821a36857662` |
| Shared schema SHA-256 | `ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c` | `ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c` |

The machine comparison returns exactly:

`connectivity_edges.EDGE-SW-A23-1.endpoint_a_id: SEC-B3 → SEC-A2`

No second engineering-content difference exists.

## 6. IMP-001 and build identity

The verified toolchain is Python 3.13.15, Node.js 24.19.0 and npm 11.17.0.
Setuptools 84.0.0 and every runtime/test dependency are exact-pinned in the
controlled project and lock files. The frontend clean lock installation reports
zero vulnerabilities.

The initial clean I1 branch-tip build was
`6170691daf62e986acec83a6841cce768cdc75f57368e04e88669040f2b6d1d6` at commit
`6a70663294bb722a0a3d4b415d9846bb7f84fd02`. The independently accepted
assurance-corrected branch-tip build was
`758ae3a7d62b56b9e5cc907b8646426b9522d2226e1933153bc9ea4ff6aba7ae` at reviewed
implementation commit `ed8ba219caaf23ff5d32dd07893ddcc5ab0163e7`. The clean
post-merge `main` identity is generated after the administrative acceptance commit
and reported in the acceptance handoff without modifying tracked files.

## 7. Verification results

| Verification | Result |
|---|---|
| Fresh Python 3.13.15 environment installed from `requirements.lock` | PASS |
| Normal wheel build/install, backend import and packaged migration access | PASS |
| Python dependency consistency check | PASS |
| Backend unit/integration suite | PASS — 14 tests |
| Empty SQLite migration and repeat application | PASS |
| Fresh `npm ci` using Node 24.19.0/npm 11.17.0 | PASS |
| Frontend Vitest scaffold suite | PASS — 1 test |
| Frontend TypeScript/Vite production build | PASS |
| npm high-severity audit | PASS — 0 vulnerabilities |
| Independent package load/hash/tamper checks | PASS |
| Raw and typed v1.0/v1.1 single-difference checks | PASS |
| Git renormalization and controlled LF/binary-attribute inspection | PASS — only `.gitattributes` changed; controlled hashes unchanged |
| Mismatched manifest configuration ID/version negative test | PASS |
| Build-manifest assembly and controlled-input participation test | PASS |
| I2/later-module and behavioural-logic scope scan | PASS — absent |

## 8. Findings, stop conditions and regression implications

IMP-001 dependency evaluation exposed two tooling compatibility issues, recorded as
QA-018. Both were resolved within the permitted I1 dependency/setup scope and all
affected tests were repeated. No engineering rule, requirement, network value,
workflow or expected result changed.

Independent review identified deterministic-checkout and manifest-internal-
identity assurance gaps, recorded as QA-019 and QA-020. Both were corrected,
reverified and independently accepted as closed under the I1 baseline. The
recommended build-identity assurance improvement was also applied: the test now
verifies Git commit/dirty state, Python/Node/npm identity, both dependency-lock
hashes, backend source hash and frontend-bundle hash in the assembled controlled
identity.

No I1 stop condition remains open. Future increments must treat the two canonical
configuration packages and lock files as controlled inputs. Any dependency,
schema, package or manifest change creates a new build/configuration identity and
requires affected regression review.

**V2 Automation Candidate — dependency and increment evidence assurance.** Repeating
clean installs, dependency compatibility checks, package hash comparison,
traceability reconciliation and closeout collation is time-consuming and
evidence-heavy; a future assurance workflow could assemble and flag this material
for engineer acceptance without changing V1 behaviour.

## 9. Acceptance and progression gate

Independent engineering/implementation review accepted I1 at implementation commit
`ed8ba219caaf23ff5d32dd07893ddcc5ab0163e7`. QA-019 and QA-020 are independently
verified closed, and IMP-001 is closed by this accepted baseline. The subsequent
administrative acceptance commit changes only this closeout and the derived QA
register; its hash and the reviewed `main` state are recorded in the final task
handoff and Git history.

I1 is the accepted implementation baseline. I2 has not started and remains
unauthorised; it requires separate user authorisation from the reviewed merged
`main` baseline.
