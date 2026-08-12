# DC-007 — VT-TOP-DEF-001 Current-Run Criterion Provenance Clarification

Status: **Design accepted — authoritative-document and machine application pending separate authorisation**

Independent technical acceptance: exact reviewed tip `92d56720229c77f1760c55ade136f9a5e5ce8f08`

Design-review findings: `DC007-DR-01` and `DC007-DR-02` closed

Date raised: 2026-08-12

Proposal date: 2026-08-12

Change class: Validation-assurance criterion provenance clarification

Origin: QA-053 semantic-executability stop during DC-006 machine/application review

Authoritative baseline: Reviewed main `48b2ecab818e43ce587bb52593d99519ac01160a`

Stopped implementation baseline: PR #12 branch head `a214b78fb425ca9a40108745d660f10888565080`

Supporting analysis: `03-derived-reference/dc-007-provenance-impact-analysis.md`

## 1. Purpose and boundary

DC-007 proposes a bounded provenance correction to the controlled expected values of `DEF-02`, `DEF-03` and `DEF-04` within the `VT-TOP-DEF-001` determination method.

QA-053 established that each affected criterion currently combines:

- an engineering proposition established by the criterion's current-run selector; and
- explanatory conclusions about the separate Network Configuration v1.0 or v1.1 execution that are not supplied by that current-run-only selector.

This makes exact source-derived observation translation impossible without importing facts from another run or manufacturing explanatory text. Both treatments would contradict the accepted one-run `SCENARIO_EXECUTION` boundary.

DC-007 changes the controlled expected-value wording of `DEF-02`, `DEF-03` and `DEF-04` by removing only those cross-configuration explanatory clauses. Existing selectors, operators, normalisation and criterion-to-requirement mappings remain unchanged. The underlying engineering answer key and expected v1.0/v1.1 outcomes remain unchanged, as do the method structure, test procedure and evidence classes.

This proposal grants no authority to amend authoritative DOCX files, modify the machine Validation Catalogue, change application code or resume I9.

## 2. Accepted architecture retained

The following remain unchanged and controlling:

- one `ScenarioRun` per `VT-TOP-DEF-001` execution;
- one `ValidationExecution` per run;
- one fixed current-run determination method applied independently to each run;
- Network Configuration v1.0 produces its own immutable `FAIL`;
- corrected Network Configuration v1.1 produces its own separate immutable `PASS`;
- no direct context contains both runs;
- no aggregate or meta-`PASS` is created;
- `DEF-06` remains the direct-execution provenance/link-field boundary;
- `VT-CFG-INV-001` remains responsible for defect/correction and cross-run investigation-chain completeness;
- `VT-DET-REPEAT-001` remains responsible for the exact corrected repeat pair; and
- the test-level `VT-TOP-DEF-001` procedure and expected-result narrative may continue to describe the separate v1.0 `FAIL` and v1.1 `PASS`.

The rejected alternative is to add the other configuration or run to `DEF-02`, `DEF-03` or `DEF-04`. That would turn a one-run direct criterion into a cross-run context, conflict with accepted DC-006 AA-01, and recreate the prohibited meta-execution architecture.

## 3. Exact proposed criterion wording

### 3.1 DEF-02 — current input and telemetry provenance

**Proposed controlled expected value**

> The current post-trip run uses corrected Network Configuration v1.1 with BRK-A GOOD/FRESH/OPEN and the controlled formal fault/input fingerprint.

**Existing selector retained**

`CurrentScenarioExecutionAdapter.{configuration_identity,post_trip_input_fingerprint,telemetry[BRK-A]}`

**Existing operator and normalisation retained**

`CANONICAL_RECORD_EQUAL`; `exact canonical representation`.

The removed sentence explained the separate v1.0 criterion outcome. That explanation remains valid at test-procedure level but is not an observation produced by this current-run selector.

### 3.2 DEF-03 — current topology, source attribution and outage consequence

**Proposed controlled expected value**

> For the current run, A1–A4 are de-energised, no A3/A4 source attribution exists and exactly 850 customers are affected.

**Existing selector retained**

`CurrentScenarioExecutionAdapter.post_trip.{topology,outage,expected_observed_comparison}`

**Existing operator and normalisation retained**

`CANONICAL_RECORD_EQUAL`; `exact canonical representation`.

The removed sentence correctly described the separate v1.0 execution, but it was not established by the selected current-run record. The accepted 400-customer v1.0 result remains in the test-level answer key and its own preserved execution.

### 3.3 DEF-04 — current configuration-difference role and source paths

**Proposed controlled expected value**

> The current source-path/configuration evidence contains the corrected SW-A23 endpoint SEC-A2 and no active path from FDR-B through SEC-B3/SW-A23 to A3/A4.

**Existing selector retained**

`CurrentScenarioExecutionAdapter.{configuration_difference_role,source_paths}`

**Existing operator and normalisation retained**

`CANONICAL_RECORD_EQUAL`; `exact canonical representation`.

The removed sentence described why the separate v1.0 source-path record fails. The criterion itself remains fixed to the corrected current-run proposition, so v1.0 continues to produce `NOT_SATISFIED` from its own observed source paths.

`configuration_difference_role` is **not** a generic configuration-role label or a pre-written proposition. It must be a backend-derived current-run configuration fact resolved from the immutable Network Configuration authority and must expose the actual controlled `SW-A23` endpoint relationship applicable to that run:

- Network Configuration v1.0 → `SW-A23` endpoint 1 = `SEC-B3`;
- Network Configuration v1.1 → `SW-A23` endpoint 1 = `SEC-A2`.

`source_paths` remains the current topology/source-attribution authority output. `DEF-04` may produce the corrected proposition only when the current run itself establishes both:

- `SW-A23` endpoint = `SEC-A2`; and
- no active FDR-B path through `SEC-B3`/`SW-A23` to A3/A4.

The v1.0 run must independently expose `SEC-B3` and the defective current source-path facts and therefore produce `NOT_SATISFIED`. No other run is introduced and the selector remains unchanged.

The stopped PR #12 implementation's generic `CONTROLLED_PACKAGE_IDENTITY` placeholder is insufficient for this criterion. A later authorised QA-053 implementation must replace it with this genuine source-derived current-configuration projection; this proposal does not authorise or perform that implementation change.

## 4. Controlled wording changes; engineering answer key does not change

The controlled expected-value wording changes to narrow criterion provenance. The underlying engineering answer key and expected v1.0/v1.1 outcomes do not change, and no expected engineering state is altered.

| Controlled result | Before DC-007 | Proposed DC-007 | Change |
|---|---|---|---|
| Network Configuration v1.0 post-trip topology | A3/A4 supplied from FDR-B through the defective SW-A23 relationship | Unchanged | None |
| Network Configuration v1.0 affected customers | 400 | 400 | None |
| Network Configuration v1.0 direct determination | `FAIL` | `FAIL` | None |
| Network Configuration v1.1 post-trip topology | A1–A4 de-energised; no A3/A4 source attribution | Unchanged | None |
| Network Configuration v1.1 affected customers | 850 | 850 | None |
| Network Configuration v1.1 direct determination | `PASS` | `PASS` | None |
| Defect | SW-A23 endpoint 1 incorrectly connected to SEC-B3 in v1.0 | Unchanged | None |
| Correction | SW-A23 endpoint 1 connected to SEC-A2 in v1.1 | Unchanged | None |

The same fixed criteria continue to be applied independently:

- v1.0 does not satisfy `DEF-02` because its current configuration identity is not corrected v1.1;
- v1.0 does not satisfy `DEF-03` because its current topology/outage facts show A3/A4 supplied from FDR-B and 400 affected customers;
- v1.0 does not satisfy `DEF-04` because its current configuration/source-path facts contain the defective relationship and active FDR-B path;
- corrected v1.1 satisfies the same three criteria from its own current-run facts; and
- the standard complete-any-`NOT_SATISFIED` → `FAIL`, complete-all-`SATISFIED` → `PASS` rule remains unchanged.

## 5. Requirement and RTM traceability

No requirement mapping changes are proposed.

The explanatory clauses being removed were not separately sourced evidence. Removing them therefore does not remove an evidence-bearing criterion or transfer requirement responsibility. The current-run propositions, independent application to each configuration, `DEF-06` provenance fields, `VT-CFG-INV-001` chain review and `VT-DET-REPEAT-001` repeat evidence retain the accepted verification allocation.

The exact affected criterion mappings remain:

- `DEF-02`: `REQ-VAL-011`, `REQ-VAL-012`, `REQ-CFG-006`, `REQ-CFG-008`, `REQ-CFG-009`, `REQ-CFG-010`, `REQ-CFG-012`;
- `DEF-03`: `REQ-TOP-003`, `REQ-OUT-001`, `REQ-OUT-002`, `REQ-OUT-003`, `REQ-OUT-007`, `REQ-CFG-004`, `REQ-CFG-005`, `REQ-CFG-012`; and
- `DEF-04`: `REQ-CFG-001`, `REQ-CFG-004`, `REQ-CFG-007`, `REQ-CFG-008`.

The complete direct criterion union for `VT-TOP-DEF-001` remains exactly its accepted 21-requirement RTM set:

`REQ-CFG-001`–`REQ-CFG-012`, `REQ-OUT-001`, `REQ-OUT-002`, `REQ-OUT-003`, `REQ-OUT-007`, `REQ-TOP-003`, `REQ-VAL-005`, `REQ-VAL-010`, `REQ-VAL-011`, `REQ-VAL-012`.

No `(test_id, requirement_id)` relationship is added, removed or transferred.

## 6. Controlled identity consequences

Because controlled expected values are part of criterion identity, the prior hashes cannot be silently retained.

The current unaccepted Validation Catalogue v1.2 candidate on PR #12 has these affected identities:

| Identity | Current unaccepted candidate |
|---|---|
| `DEF-02` | version 1.0; `40800209fb35090a5cc288e824af100abcc1a798541c49791d506d4116f068a1` |
| `DEF-03` | version 1.0; `f93c93a72f9f998fb4a8d7ea3784e71bbda68aa6649793d928823ad030e63913` |
| `DEF-04` | version 1.0; `5719a0e24be8ec82498d13561c43a5056e2fe42bb934e8c1ffba21e94a62eee8` |
| `DM-TOP-DEF-001` | version 1.0; `039de8b79d121cd5652cd185b787ef673c54e13fd8da7c15c6d551530abc8b40` |
| `VT-TOP-DEF-001` | version 1.1; definition SHA-256 `ae420cd20f30aee9bd6e3bd3a5845124580d163088489511feb90e06e09531cd` |
| Validation Catalogue v1.2 | file SHA-256 `51c6079aeecdb04e11ad1fe9aa3b293e8517fbc7e961c2f1520864d7eada6de3` |
| Validation Catalogue v1.2 manifest | file SHA-256 `a9b7b91e903d1277433a049b99ec9a0324e0b32cd59a3bd8f24899ef86f49754` |

If the exact DC-007 wording and normal controlled version increments are later applied to that candidate, the calculated consequential identities are:

| Identity | Proposed corrected candidate |
|---|---|
| `DEF-02` | version 1.1; `dc9bdda01270506b6871f053bddda03174289b0f550c64141da88d72dd26add1` |
| `DEF-03` | version 1.1; `e9977d8accc64dec128a92ace3be4bc48a94617ea90d72fbafa1a1221f12546c` |
| `DEF-04` | version 1.1; `484d08341dcb0df61755d9e80e0567f1e85f808838380f9cb9cc3cd04c774260` |
| `DM-TOP-DEF-001` | version 1.1; `f6a223f6155d53312190e7748d92428c03f39353f37b9c05b08c2e571363f166` |
| `VT-TOP-DEF-001` | version 1.2; definition SHA-256 `323c5db24e397ff5377d8210a684e547e3af85951b8dabc3394d91e36d9aa76a` |
| Validation Catalogue v1.2 | candidate file SHA-256 `2ebe3400a480fcd31c9317551316d20df4b1d828eb325cf131c73ee13ec970a1` |
| Validation Catalogue v1.2 manifest | candidate file SHA-256 `4e7bd40a7e44d97d6cd995011f18d1257ed58f8cc1be57329c04123aa04fed42` |

These proposed hashes are an impact-analysis result only. They do not promote or modify the machine package.

The corrected package should remain **Validation Catalogue v1.2** because v1.2 is an unaccepted candidate and has never been promoted into the accepted main baseline. The rejected/unaccepted candidate hashes above shall be retained in change history. Creating v1.3 merely to avoid replacing an unaccepted candidate identity would incorrectly imply that v1.2 had been accepted.

Accepted historical Validation Catalogue v1.0/v1.1 packages and identities remain immutable and unchanged.

## 7. Authoritative-document impact

The minimum technical amendment is:

- **Validation Plan v1.3 → proposed v1.4:** replace only the `DEF-02`, `DEF-03` and `DEF-04` expected-value text in Section 21.3.4, record DC-007 provenance rationale, and retain the existing one-run rule in Section 21.5.

No technical amendment is required to:

- **System Architecture v0.4:** Section 28 already states that the common method is applied independently, with one-run v1.0 `FAIL`, separate one-run v1.1 `PASS`, and no cross-run result/meta-`PASS`;
- **Workflow Design v0.4:** Section 29 already requires separate common-method executions and prohibits a context containing both runs or a meta-result; or
- **Demonstrator Design v0.5:** Section 38 already presents v1.0 `FAIL` and v1.1 `PASS` as separate one-run executions and prohibits an aggregate/meta-`PASS` label.

Their accepted identities remain unchanged:

- System Architecture v0.4 — `76c768df708dac528d8be0c585975adcfb8ac4f1c43c402c463b4a343b6db47c`;
- Workflow Design v0.4 — `aa5886103c57b182fd9868c6d0d2f27966640a73eb188979efd13813d1fda479`; and
- Demonstrator Design v0.5 — `f907d0393cba2b636349579bff281073814adbf0f952ef19eeae63517d47ede2`.

The accepted Validation Plan v1.3 identity `626514e30f85e83990816be142e7a90b7d108e3e1f8cdf5c56e83ca31598f8f0` remains controlling until a separately authorised DC-007 document application is independently reviewed and accepted. A proposed v1.4 hash cannot be assigned until that exact DOCX application exists.

Requirements Specification v0.4, Engineering Design Brief v0.4 and Network Model v0.4 require no change.

## 8. Project-wide invariants

DC-007 preserves exactly:

- 24 catalogue tests;
- 124 unique requirements;
- 286 `(test_id, requirement_id)` relationships;
- 15 operational-event types;
- 35 determination methods;
- 214 criteria;
- criterion IDs `DEF-02`, `DEF-03` and `DEF-04`;
- DC-004 constituent/composite semantics;
- DC-005 suspension and `BLOCKED-TEST` semantics;
- Network Configuration v1.0/v1.1 content and hashes;
- topology, source-attribution, outage/customer, telemetry, DC-003 isolation and restoration behaviour; and
- dependency/toolchain identities.

## 9. Lifecycle and stop state

- DC-007 technical design is independently accepted at reviewed tip `92d56720229c77f1760c55ade136f9a5e5ce8f08`.
- `DC007-DR-01` and `DC007-DR-02` are closed.
- PR #12 remains draft and unmerged.
- Its uncommitted QA-054, QA-055 and partial QA-053 work remains WIP and shall not be committed or pushed before separately authorised DC-007 application and QA-053 resumption.
- QA-053 implementation remains stopped.
- No authoritative-document application is authorised by this design acceptance.
- No machine catalogue/application work is authorised by this design acceptance.
- I9 remains stopped.

The next gate is separately authorised DC-007 authoritative-document application. Candidate catalogue rebuild and resumption of QA-053 also require separate authorisation.

**V2 Automation Candidate:** a criterion-provenance linter could compare every expected proposition with its declared selector/source membership and flag unsupported cross-run clauses before catalogue publication.
