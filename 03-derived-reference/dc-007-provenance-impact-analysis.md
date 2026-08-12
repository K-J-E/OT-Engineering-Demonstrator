# DC-007 Provenance and Impact Analysis

Status: **Derived analysis supporting accepted DC-007 technical design — application pending separate authorisation**

Authority: **Derived reference only; does not override authoritative engineering documents, accepted change records or controlled machine packages**

Owner: Project engineering review process

Updated: 2026-08-12

Related proposal: `02-change-control/DC-007-vt-top-def-current-run-criterion-provenance-clarification.md`

## 1. Investigation question

Can `DEF-02`, `DEF-03` and `DEF-04` be evaluated from their existing one-run source selectors without importing another run or manufacturing explanatory conclusions?

Finding: **No, not with their current full wording.** Each selector supplies the current run's facts, while the trailing clause of each expected value explains the result of a different configuration/run. The accepted architecture prohibits binding that other run into the direct `SCENARIO_EXECUTION` context.

The minimum correction changes the controlled expected-value wording to retain the current-run proposition and remove only the unsupported cross-configuration explanation. The underlying engineering answer key and expected v1.0/v1.1 outcomes do not change.

## 2. Selector-to-proposition provenance

| Criterion | Facts supplied by existing selector | Unsupported explanatory content | Minimum correction |
|---|---|---|---|
| `DEF-02` | Current configuration identity, current controlled input fingerprint and current BRK-A telemetry | Statement that applying the method to v1.0 leaves the criterion `NOT_SATISFIED` | Retain only the current corrected-v1.1 input/telemetry proposition |
| `DEF-03` | Current post-trip topology, outage and current expected/observed comparison | Separate v1.0 A3/A4/FDR-B/400 observation and its `FAIL`, plus explanatory v1.1 `PASS` clause | Retain only the current A1–A4/no-attribution/850 proposition |
| `DEF-04` | Current configuration-difference role and current source paths | Explanation that v1.0's ordinary source path does not satisfy the record | Retain only the current corrected endpoint/no-FDR-B-path proposition |

The removed clauses remain valid test-level rationale. They are not discarded from the project answer key; they are relocated conceptually to the level where both separate executions are reviewed.

### 2.1 DEF-04 source semantics

`configuration_difference_role` is **not** a generic configuration-role label or a pre-written proposition. It must be a backend-derived current-run configuration fact resolved from the immutable Network Configuration authority and must expose the actual controlled `SW-A23` endpoint relationship applicable to that run:

- Network Configuration v1.0 → `SW-A23` endpoint 1 = `SEC-B3`;
- Network Configuration v1.1 → `SW-A23` endpoint 1 = `SEC-A2`.

`source_paths` remains the current topology/source-attribution authority output. Under the retained selector `CurrentScenarioExecutionAdapter.{configuration_difference_role,source_paths}`, `DEF-04` may produce the corrected proposition only when the current run itself establishes both `SW-A23` endpoint = `SEC-A2` and no active FDR-B path through `SEC-B3`/`SW-A23` to A3/A4.

The v1.0 run must independently expose `SEC-B3` and the defective current source-path facts and therefore produce `NOT_SATISFIED`. No additional run or selector change is required or permitted.

The stopped PR #12 implementation's generic `CONTROLLED_PACKAGE_IDENTITY` placeholder does not establish this source provenance and is insufficient. A later authorised QA-053 implementation must replace it with the genuine source-derived current-configuration projection described above.

## 3. Rejected alternatives

### 3.1 Add the other run to the direct context

Rejected. This violates the accepted one-`ScenarioRun`/one-`ValidationExecution` `SCENARIO_EXECUTION` contract and would reverse DC006-AA-01.

### 3.2 Create one aggregate result over v1.0 and v1.1

Rejected. The accepted direct results remain separate `FAIL` and `PASS`; no meta-`PASS` exists.

### 3.3 Return the explanatory clause whenever the selector is invoked

Rejected. That would be an unconditional success string rather than a source-derived observation.

### 3.4 Retain prior hashes after changing wording

Rejected. Expected value is controlled criterion content; changing it necessarily changes criterion, method, test-definition, catalogue and manifest identities.

### 3.5 Create Validation Catalogue v1.3

Rejected at this stage. The current v1.2 package is an unaccepted candidate, so the corrected candidate should remain v1.2 with a new identity and the prior rejected identity preserved in change history.

## 4. Current-run outcome proof

### 4.1 Network Configuration v1.0 execution

The same method remains fixed to the corrected expected state. Its own current-run facts show:

- current configuration identity is v1.0 rather than corrected v1.1;
- BRK-A remains GOOD/FRESH/OPEN, confirming telemetry is not the defect;
- A3/A4 retain active FDR-B source attribution through the defective SW-A23 relationship; and
- affected-customer count is 400 rather than 850.

At least `DEF-02`, `DEF-03` and `DEF-04` are therefore `NOT_SATISFIED`. Once the full criterion set is complete, the backend deterministically derives the execution's immutable `FAIL`.

### 4.2 Corrected Network Configuration v1.1 execution

Its own current-run facts show:

- corrected v1.1 identity and the same controlled formal input;
- BRK-A GOOD/FRESH/OPEN;
- A1–A4 de-energised;
- no A3/A4 attribution to FDR-B;
- exactly 850 customers affected; and
- corrected SW-A23 endpoint/source paths.

The same criteria are `SATISFIED`. When all other direct criteria are complete and satisfied, the backend derives the separate immutable `PASS`.

No step requires either execution to read or aggregate the other.

## 5. Traceability audit

The accepted `VT-TOP-DEF-001` RTM set and direct criterion union are identical and contain 21 requirement IDs:

- `REQ-CFG-001`–`REQ-CFG-012`;
- `REQ-OUT-001`, `REQ-OUT-002`, `REQ-OUT-003`, `REQ-OUT-007`;
- `REQ-TOP-003`; and
- `REQ-VAL-005`, `REQ-VAL-010`, `REQ-VAL-011`, `REQ-VAL-012`.

The exact mappings of `DEF-02`, `DEF-03` and `DEF-04` remain unchanged. Their union with `DEF-01`, `DEF-05` and `DEF-06` still equals the parent RTM set exactly. No out-of-parent requirement is introduced and no accepted relationship is removed.

Defined criterion coverage must not be confused with achieved evidence. The v1.0 failed execution does not claim successful verification merely because the criterion definitions retain requirement mappings. Successful correction/repeat assurance still relies on the preserved v1.0 `FAIL`, separate v1.1 `PASS`, `DEF-06` links, `VT-CFG-INV-001` and `VT-DET-REPEAT-001`.

## 6. Authoritative-document inspection result

| Document | Accepted identity inspected | Finding | Proposed impact |
|---|---|---|---|
| Validation Plan v1.3 | `626514e30f85e83990816be142e7a90b7d108e3e1f8cdf5c56e83ca31598f8f0` | Section 21.3.4 contains the three unsupported explanatory clauses; Section 21.5 already states the correct one-run model | Minimum technical amendment to proposed v1.4 |
| System Architecture v0.4 | `76c768df708dac528d8be0c585975adcfb8ac4f1c43c402c463b4a343b6db47c` | Already states independent one-run v1.0 `FAIL` and v1.1 `PASS`, external links and no meta-`PASS` | No technical amendment |
| Workflow Design v0.4 | `aa5886103c57b182fd9868c6d0d2f27966640a73eb188979efd13813d1fda479` | Already requires separate executions and prohibits a two-run context/meta-result | No technical amendment |
| Demonstrator Design v0.5 | `f907d0393cba2b636349579bff281073814adbf0f952ef19eeae63517d47ede2` | Already presents separate one-run results and prohibits aggregate/meta-`PASS` presentation | No technical amendment |

The accepted document identities remain controlling; no DOCX has been modified by this analysis.

## 7. Candidate identity calculation basis

The proposed hashes in DC-007 were calculated in memory against the exact unaccepted Validation Catalogue v1.2 candidate present at PR #12 head `a214b78fb425ca9a40108745d660f10888565080` using the changed controlled expected-value wording while retaining the unchanged engineering answer key and expected v1.0/v1.1 outcomes, specifically:

- the three exact proposed expected values;
- criterion version increments 1.0 → 1.1;
- `DM-TOP-DEF-001` version increment 1.0 → 1.1;
- `VT-TOP-DEF-001` definition version increment 1.1 → 1.2;
- unchanged selectors, operators, normalisation, roles, criterion IDs and requirement mappings; and
- the existing controlled canonical JSON/hash algorithms and manifest format.

No catalogue, manifest, revision file or application source was written during the calculation.

## 8. Verification obligations for a later authorised application

A separately authorised DC-007 application should verify:

1. only the three Section 21.3.4 expected values change technically in the Validation Plan;
2. Validation Plan version/status/hash history is updated under controlled change;
3. `DEF-02`, `DEF-03` and `DEF-04` retain IDs, selectors, operators, normalisation and requirement mappings;
4. criterion, method, test-definition, catalogue and manifest hashes match the controlled rebuild;
5. the rejected/unaccepted prior v1.2 candidate identities are preserved;
6. exact 24/124/286/15 and 35/214 invariants remain;
7. direct `VT-TOP-DEF-001` criterion union still equals its exact parent RTM set;
8. v1.0 independently produces 400/`FAIL` and v1.1 independently produces 850/`PASS`;
9. no direct context contains two runs and no meta-`PASS` exists;
10. DC-004/DC-005, configuration, topology/outage/restoration and dependency identities remain unchanged; and
11. QA-053 resumes only after the authoritative and machine identities are separately accepted.

The later QA-053 application must additionally prove that `configuration_difference_role` is resolved from the immutable current-run Network Configuration authority, that `source_paths` is supplied by the existing topology/source-attribution authority, and that altering either controlling fact remains visible as `NOT_SATISFIED`. The generic `CONTROLLED_PACKAGE_IDENTITY` placeholder is not acceptable evidence for `DEF-04`.

## 9. Current gate

DC-007 technical design is independently accepted at exact reviewed tip `92d56720229c77f1760c55ade136f9a5e5ce8f08`; `DC007-DR-01` and `DC007-DR-02` are closed. Authoritative-document and machine application remain pending separate authorisation. PR #12 remains draft/unmerged, its local WIP remains preserved, QA-053 remains stopped and I9 remains stopped.
