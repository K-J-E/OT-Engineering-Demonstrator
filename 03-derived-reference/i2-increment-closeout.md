---
Status: Accepted I2 implementation baseline — independently verified
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-10
Increment: I2 — Topology and Outage Core
---

# I2 Increment Closeout — Topology and Outage Core

## 1. Authorisation, branch and boundary

The user explicitly authorised I2 only. Work was created on
`agent/i2-topology-outage-core` from the accepted reviewed `main` baseline at
`828f3f9fe026fecb7561f14325b289d7c25ce3d0`.

The implementation commit is
`bb6a052ad04b3056681c6aa54c488ba5ab22a902`. Implemented scope is limited to
pure configuration-driven network graph/active-edge processing, feeder-source
tracing and attribution, section energisation, radiality, fault-state separation,
active-fault boundary incidence, DC-003 boundary evidence/proof, outage/customer
mapping, configured-versus-derived feeder load and their typed read models/tests.
The targeted independent-review assurance corrections are implemented at
`adf86fcfcf981fab62b20f8faed63f183c15b333` without redesigning I2.

No scenario command orchestration, mutable workflow transaction, controlled-clock
or alarm/event lifecycle, restoration assessment, formal validation execution or
evidence records, operational UI, defect-investigation workflow or Exploration
Mode orchestration was introduced. I3 has not started.

## 2. Authoritative sources used

The mandatory I2 source set in Implementation Control Plan Section 5 was read
before implementation:

- Project Vision, Project Definition and Project Decisions;
- accepted DC-001, DC-002 and DC-003, current baseline manifest and implementation
  source map;
- Requirements Specification rows `REQ-NET-001–011`, `REQ-TOP-001–009`,
  `REQ-OUT-001–007`, `REQ-CFG-002–005`, `REQ-NFR-003` and `REQ-NFR-009`, including
  their rationale and verification methods;
- Network Model Sections 2–18.7;
- System Architecture Sections 5, 7, 9, 14–16, 19 and 26.1–26.3;
- Workflow Design Sections 8–10.3, 13, 15–17, 22 and 27.1–27.3;
- Demonstrator Design Sections 5, 7–8.4, 11–12, 16, 22, 27–28 and 35.1–35.5;
- Validation Plan Sections 6–8 for the applicable catalogue rows, Sections
  11–12.1, 14 and 15; and
- Engineering Design Brief Section 23 as the accepted DC-003 active-fault source.

## 3. Files and modules produced

- `app/backend/ot_demo/modules/topology/`: immutable I2 inputs/read models and the
  generic topology service.
- `app/backend/ot_demo/modules/outage/`: immutable outage/customer-zone result and
  the OMS-style derivation service.
- `app/backend/ot_demo/domain/enums.py`: controlled boundary-evidence, proof,
  freshness/quality and radiality enum values needed at the pure-domain boundary.
- `tests/unit/test_topology_core.py`: active graph, source, radiality, fault,
  all-section incidence, A/B/C and isolation tests.
- `tests/integration/test_topology_outage_results.py`: v1.1 N0/N1, v1.0 defect,
  configured/derived load, source-path, customer-zone and restored-delta gates.
- `pyproject.toml`: registered the `i2` test marker only; dependency versions are
  unchanged.

## 4. Engineering implementation decisions within the approved baseline

`ZS-01` remains the common source-availability entity, while each feeder source
breaker is treated as its feeder's distinct injection boundary for source tracing.
Source-side edges remain configured and active-edge evidence, but distribution
traversal cannot cross through the common source entity. This implements Network
Model Sections 5, 6 and 13: with `TS-01` open there is no active feeder-to-feeder
path and each normal section has exactly one feeder attribution.

For an energised component, radiality requires an acyclic active distribution
component with no more than one active feeder-source injection. An energised graph
cycle or component with multiple active injections is reported as
`UNINTENDED_LOOP`. A physically closed cyclic component with zero active source
injections is de-energised and is not reported as an unintended energised loop.
Because the approved baseline defines no load-sharing calculation for an invalid
multiple-source component, I2 records its per-feeder currently supplied load as
unattributed rather than inventing an allocation; the source paths and affected
component remain reviewable.

Outage derivation consumes the same identity-bearing `LoadedConfiguration` contract
as topology processing and rejects a topology or previous outage state carrying a
different configuration identity. Restored-customer delta is the sum of customers
in previously affected section/customer-zone identities that are absent from the
new affected set; it is not a subtraction of aggregate outage totals.

Boundary evidence is accepted by I2 only as a preclassified pure-domain input.
I2 does not calculate timestamps or authorise commands. `OPEN_REQUIRED` records
Condition B's engineering need only; I3 must still apply actor, workflow, revision
and command gates before any action can be available.

## 5. Requirements and conformance-gate traceability

| Requirement / gate | I2 implementation evidence | I2 status |
|---|---|---|
| `REQ-TOP-001–005` | Configuration edges plus complete device/source inputs produce deterministic active edges, source paths and recalculated section states. | Complete at I2 domain boundary. |
| `REQ-TOP-006` | `faulted` and `energised` are independent fields; an energised active-fault test proves no conflation. | Complete at I2 domain boundary. |
| `REQ-TOP-007` / DC-003 | Incident boundaries come from configuration; A/B/C evidence and all-open plus zero-source-path conjunction are tested. | Complete at I2 domain boundary; I3 action gates remain later. |
| `REQ-TOP-008–009` | Generic alternate source attribution and energised multiple-source/cycle detection use the common engine; a de-energised cyclic component is not misclassified as an energised loop. | Complete at I2 domain boundary; restoration assessment remains I4. |
| `REQ-OUT-001–007` | OMS consumes a matching identity-bearing configuration and de-energised section states, maps zones, sums customers and derives restored identities without reading fault labels. | Complete at I2 domain boundary. |
| `REQ-CFG-002–005` | The same service processes both packages; v1.0 propagates the configured endpoint defect to A3/A4 source attribution and 400 customers. | Complete at I2 topology/outage boundary. |
| `REQ-NET-001–011` | Accepted I1 typed configuration is consumed without modification; all configured entities/edges/mappings are handled consistently. | I2 consumption confirmed. |
| `REQ-NFR-003`, `REQ-NFR-009` | Stable sorting, immutable models, repeat tests and identifier-free production algorithms provide deterministic, consistent processing. | I2 portion complete. |
| `VT-TOP-NORMAL-001` | v1.1: all eight energised, A sections from FDR-A, B sections from FDR-B, 3.20/4.20 MW, radial and zero outage. | I2 implementation conformance PASS; not an I5 formal execution. |
| `VT-FML-N0-N5-001` N0/N1 portion | BRK-A trip produces A1–A4 de-energised and 850 affected customers. | I2 implementation conformance PASS only. |
| `VT-TOP-DEF-001` topology/outage portion | Same engine: v1.0 retains A3/A4 from FDR-B and reports A1/A2 = 400; v1.1 reports 850. | I2 implementation conformance PASS only. |
| `VT-RST-ISOLATION-001` domain portion | Every incident boundary proven OPEN and zero active paths are both required. | I2 implementation conformance PASS only. |
| `VT-EXP-ALL-001` domain portion | All eight v1.1 incidence pairs and Conditions A/B/C are derived/tested without section lookup data. | I2 implementation conformance PASS only. |

## 6. Verification results

| Verification | Result |
|---|---|
| I2 marked backend suite | PASS — 31 tests |
| Complete backend unit/integration regression | PASS — 45 tests |
| Relevant I1 marked regression | PASS — 11 tests |
| Energised versus de-energised cyclic-component distinction | PASS — energised cycle invalid; zero-injection cycle not reported as an energised loop |
| OMS current/previous configuration mismatch negatives | PASS — both rejected before customer derivation |
| Identity-based restored-customer composition change | PASS — 180 restored while affected total changes 400 → 480 |
| Frontend I1 scaffold regression | PASS — 1 test |
| Frontend TypeScript/Vite production build | PASS |
| Python module import/compile through the executed suite | PASS |
| v1.0/v1.1 load/hash/tamper/single-difference regression in complete suite | PASS |
| Canonical configuration/schema byte comparison against starting main | PASS — no changes |
| Canonical data/manifest/schema SHA-256 comparison with accepted I1 closeout | PASS — all five hashes unchanged |
| Forbidden-result/identifier scan of production topology/outage modules | PASS — no section, feeder, breaker, switch, version, 400 or 850 literals |
| Later-increment scope scan | PASS — no I3 transactions, I4 restoration, I5 evidence, I6 UI, I7 investigation or I8 orchestration |
| Git whitespace check | PASS |

The canonical SHA-256 identities remain:

- v1.0 data `67cb237df5084919b568f5620c523cb868db03eaba71e7f16c2f2671242f7ab3`;
- v1.0 manifest `d0243fae46e6a5d403855953e14cdedbcdae9c71af7761a1aba49f88470bc12d`;
- v1.1 data `7d65b7fb2e3e7b5cb3f0fc698554c3848935222fe56aee727d25cfc324e93281`;
- v1.1 manifest `e0f16f3acdf2e85aa04cd23bb4b584a868626117b68f682d1219821a36857662`;
- shared schema `ee6d42cb36be3470870028ab9983eba3a6ce33529ead73dfebc584b04b89c60c`.

## 7. Findings, stop conditions and regression implications

QA-021 records the implementation-assurance risk that a naive graph could traverse
through the shared zone-substation source and manufacture a feeder-to-feeder path.
The I2 representation and tests close that risk and were accepted in substance by
independent review.

QA-022 records the initial over-broad radiality classification of a cyclic active-
device component with no active source injection. The revised generic predicate
evaluates cyclicity only for energised components while retaining multiple-active-
source rejection and the established both-source/tie-closed negative.

QA-023 records the initial OMS provenance gap and aggregate subtraction for restored
customers. Outage calculation now rejects mismatched current/previous configuration
identities and calculates restored customers from previously affected section/zone
identities. A composition-change test proves that 180 customers are restored even
when the aggregate affected total increases from 400 to 480.

No authoritative engineering artefact, requirement, controlled package, dependency
or expected answer was changed by these assurance corrections.

No I2 stop condition remains open. I3 must consume these services without moving
workflow authority into topology models. I4 must reject/block through its approved
precedence rather than changing source/radiality results. I5 must execute formal
catalogue validation separately; the tests above are conformance gates, not formal
execution evidence. I6/I7/I8 must project the returned derivations without
recalculating or inserting expected answers.

**V2 Automation Candidate — topology/outage regression assurance.** Repeating
expected-versus-observed source-path, outage, customer arithmetic, configuration
difference and requirement-impact checks is manual and evidence-heavy. A future
assurance workflow could collate and flag discrepancies for engineer review while
leaving V1 algorithms and engineering judgement unchanged.

## 8. Review and progression gate

Independent engineering/implementation review accepted the revised I2 branch at
`e2aa7c0742a4df0867fc7624a59a4d104dd8dba0`. QA-003's I2 treatment is accepted,
and QA-021, QA-022 and QA-023 are independently verified closed under the accepted
I2 baseline. The reviewed I2 history and this administrative acceptance record are
incorporated into `main` as the accepted implementation baseline.

I3 has not begun and requires separate user authorisation from reviewed `main`.
