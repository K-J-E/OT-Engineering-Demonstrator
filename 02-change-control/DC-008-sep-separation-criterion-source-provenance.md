# DC-008 — SEP Separation-Criterion Source Provenance Clarification

Status: **Proposed — pending independent engineering design review; no authoritative-document, catalogue or implementation authority granted**

Date raised: 2026-08-13

Proposal date: 2026-08-13

Change class: Validation-assurance source-provenance clarification

Origin: QA-053 semantic-executability stop at `SEP-01`

Accepted authoritative baseline: main `60f7431ac1e8aa271845fd79ddc81a00766098b8`

Stopped machine/application baseline: PR #12 published head `a2027d0fbd3edf38789af6e994a669eeddcf5520`

Supporting audit: `03-derived-reference/dc-008-sep-selector-provenance-audit.md`

## 1. Purpose and boundary

DC-008 proposes the minimum source-provenance correction needed to execute the accepted `VT-EXP-SEPARATION-001` meaning without manufacturing narrative observations.

QA-053 established that `ScenarioRunAdapter.formal_run` proves the actual run's mode, fault and evidence class, but does not by itself prove the causal assurance in `SEP-01` that the formal fault is fixed and another formal fault cannot be selected. Returning the accepted sentence from those run fields alone would overstate the declared source.

This is a **source-provenance correction, not an engineering-answer-key change**. The proposal preserves:

- the exact expected propositions and engineering meanings of `SEP-01`–`SEP-06`;
- all criterion-to-requirement mappings;
- the `PRESERVED_RECORD_SET` context and backend-derived aggregate result;
- FORMAL/EXPLORATORY separation;
- DC-004 composite and DC-005 suspension semantics; and
- every network, topology, outage, restoration and telemetry rule.

This proposal does not authorise authoritative DOCX edits, machine-catalogue rebuilding, application/source-adapter changes, QA-053 resumption, QA-054/055 changes, PR #12 changes or I9 work.

## 2. Existing backend authority confirmed

The required formal policy is already enforced by the application. DC-008 does not create a new policy:

1. `FORMAL_N0_N3_DEFINITION` is the existing frozen `FormalScenarioDefinition` and sets `fault_section_id = SEC-A2`.
2. `ScenarioCoordinator._validate_initialisation()` returns that controlled definition fault for FORMAL initialisation.
3. The same method raises `ScenarioBoundaryError` when a FORMAL request supplies any different fault section.
4. `ScenarioCoordinator.initialise()` and `initialise_replacement_run()` invoke that validation before inserting or closing a run; a rejected request therefore does not alter scenario history.
5. `ScenarioCoordinator.initialise_next_run()` delegates to those existing paths.
6. `POST /api/v1/runs` and `POST /api/v1/runs/start` expose the existing boundary outcome as HTTP 409.

The rejection response is currently ephemeral rather than a persisted validation source record. A later authorised application may capture the actual result as immutable validation evidence, but it must call the existing authority and must not create a second policy engine, policy table or validation-only rule.

## 3. Four-criterion provenance decision

| Criterion | Audit disposition | Proposed controlled treatment |
|---|---|---|
| `SEP-01` | Source-provenance gap | Extend the selector to include the actual FORMAL run, the existing formal definition and actual rejection outcomes for every other configured section. |
| `SEP-02` | Source-provenance gap | Extend the selector to include the exact immutable Network Configuration package bound to the exploratory run, so corrected status and transient run-state ownership are explicit. |
| `SEP-03` | Source-provenance gap | Extend the selector to include actual strict command/API boundary outcomes for attempted in-place mode and selected-fault mutation. |
| `SEP-05` | Representational translation only | Retain the selector; populate it from actual formal-only and mixed-campaign calls to the accepted formal-progress projection, with actual exploratory execution/evidence/composite membership. |

`SEP-04` and `SEP-06` remain unchanged and require no translator or selector correction.

## 4. Exact proposed selector contracts

### 4.1 SEP-01 — formal run and initialisation boundary

**Expected proposition retained exactly**

> FORMAL run is fixed to SEC-A2, uses FORMAL evidence class and cannot select another fault.

**Proposed selector**

`ScenarioRunAdapter.formal_run + FormalScenarioDefinition.fault_section_id + ScenarioInitialisationBoundaryAdapter.{configured_section_ids,alternate_formal_fault_rejections}`

The three source members have separate responsibilities:

- `ScenarioRunAdapter.formal_run` supplies actual run ID, mode, fault section, evidence class, configuration identity and build provenance.
- `FormalScenarioDefinition.fault_section_id` is a snapshot of the existing injected `FORMAL_N0_N3_DEFINITION`, including a canonical definition hash.
- `ScenarioInitialisationBoundaryAdapter` captures actual results from the existing initialisation authority for the complete configured section set. The candidate set is derived from the loaded configuration; it is not a hard-coded answer table. Every configured section other than the definition fault must have one rejected FORMAL initialisation outcome, and the current run must remain unchanged before/after the probes.

The adapter name denotes evidence capture over the existing boundary. It is not a new policy record or policy authority.

### 4.2 SEP-02 — exploratory run and immutable configuration package

**Expected proposition retained exactly**

> EXPLORATION run uses corrected Network Configuration v1.1, a transient selected section and EXPLORATORY evidence class.

**Proposed selector**

`ScenarioRunAdapter.exploration_run + NetworkConfigurationPackage.{manifest,catalog_entry,data}`

The run record supplies the actual mode, evidence class, selected section and bound configuration identity. The exact hash-verified package supplies configuration version/status and persistent configuration content. The observation may call the selection transient only when the selected fault is owned by the run record, the run and package identities agree, and the immutable package contains configuration rather than mutable scenario-selection state.

### 4.3 SEP-03 — immutable run fields and strict API boundary

**Expected proposition retained exactly**

> Run mode and selected fault are immutable after initialisation; in-place mode conversion is rejected.

**Proposed selector**

`ScenarioRunAdapter.mode_conversion_probe + ScenarioCommandApiBoundaryAdapter.{mode_mutation_rejection,fault_selection_mutation_rejection}`

The existing backend facts are:

- `RunContext` is a frozen domain record;
- `ScenarioCommandType` has no in-place mode/fault conversion command;
- strict API request models forbid unknown command types and extra mutation fields; and
- changing mode through the accepted workflow creates a new run and preserves/closes the prior run rather than modifying it.

The boundary adapter shall capture actual validation/API rejection outcomes and unchanged before/after run identity/hash. It shall not invent a conversion command or a second run-state algorithm.

### 4.4 SEP-05 — formal progress before/after

**Expected proposition and selector retained exactly**

`FormalProgressAdapter.before_after`

The source must contain:

- the actual FORMAL-only progress projection;
- the actual projection when the complete campaign execution/suspension records are supplied;
- actual exploratory execution/evidence identities; and
- actual finalised DC-004 composite identities.

The same accepted `WorkspaceService._validation_progress()` authority must produce both progress projections. The translator serialises whether the six controlled FORMAL totals are equal; it must not pre-populate equal dictionaries or infer a verdict.

## 5. Observation and failure semantics

For all affected criteria:

- complete matching source facts may be serialised into the existing canonical proposition;
- complete contradictory facts must be serialised truthfully and remain available to the primitive comparison as a mismatch;
- absent, incomplete, ambiguous or non-unique required authority must produce no proposition and leave the criterion `NOT_EVALUATED`/procedure `INCOMPLETE`;
- translation must not inspect `criterion.expected_value`;
- translation must not emit criterion or test verdicts;
- no test-, criterion-, case-, section- or configuration-version answer lookup is permitted; and
- all determination continues through accepted normalisation, primitive operator and aggregate logic.

## 6. Controlled identity consequences

The current unmerged MC-01-corrected Validation Catalogue v1.2 candidate remains unchanged by this proposal:

- catalogue: `f224a8826f4c02dd0c4bb5c22f3ab7351cd4eb17106b78541aeaf3b1c1d9cbe4`;
- manifest: `ef30f4e17a67dadefce5141edb3335544804bf512e4d76e85f351bc4fa0ee4c9`.

If the exact three selector strings above are later applied, with no other criterion change, the normal controlled increments and analytically reproduced identities are:

| Identity | Current candidate | Prospective DC-008 candidate |
|---|---|---|
| `SEP-01` | v1.0 / `78c862a7f2255aa0c3c4b14f0b5152fbbed929794279071c903e32f3dadc4231` | v1.1 / `fd51778a8aaa4e921b9e23512b434e44d40183dc92fa5dc399d6c93747ddf949` |
| `SEP-02` | v1.0 / `13a01b02a6dbb8c8749f27fe7cd823807041c567f7232f0c0a6519ea4b5e9edd` | v1.1 / `f955fc859a5de4ad3b2923502c363278f59f7fb156442ed71c765581b015e040` |
| `SEP-03` | v1.0 / `1e29eca7bca3393183a7b32760ab846f6646520e66fc9c56e3010232481caacc` | v1.1 / `2f5fdf89563fc89461540d37366940221670e9f8dc2dbd6cb13acf4004271065` |
| `DM-EXP-SEPARATION-001` | v1.0 / `197e4c1d4a79ffe1e48c1c8dae2b392ee2569bd793dc9d5fb92b6127c6188103` | v1.1 / `9504e4c102364205d255ed7ab631626e6299281ac1a3673a9104519bd78df6a0` |
| `VT-EXP-SEPARATION-001` | v1.1 / `cba4b606e7dd2d7a0ef3788756525abac096b40022755bb56f9e49a2e1f02921` | v1.2 / `4474172ab0023b56b8d54dd7e91635fd991ee6e152732b28cc0ba7279a27d27e` |

Using the prospective authority string `Accepted Validation Plan v1.5 Section 21 / DC-006 + DC-007 + DC-008`, the exact in-memory candidate calculation gives:

- prospective Validation Catalogue v1.2 SHA-256: `3553ac28856cbe64056fda516ccdc05242960194e956444c01bd11eb7fbd3d1f`;
- prospective manifest SHA-256: `e1bba6567da17a1074536859a17ff553f3b969ae1c27eefd1265e20bafdbe07f`.

These are analytical design identities only. A later authorised deterministic build must reproduce them against the independently accepted Validation Plan v1.5. If review changes any selector or authority string, the analytical hashes are invalid and must be recalculated.

Validation Catalogue remains **v1.2**, because the current v1.2 candidate is unmerged and unaccepted. A later application must preserve `f224a882...` / `ef30f4e...` as a superseded unaccepted candidate rather than inventing v1.3 to avoid candidate supersession. Historical accepted v1.0/v1.1 packages remain byte-identical.

## 7. Authoritative-document impact

The minimum authoritative amendment is:

- accepted Validation Plan v1.4 (`0cf0d383786a057b402d0a0f97597ecaafb2b86074a2ef93f238b688b21e4f5f`) → proposed v1.5;
- Section 21.3.19 only: retain all expected propositions, operators, normalisation, evidence roles and requirement mappings, but replace the `SEP-01`, `SEP-02` and `SEP-03` source-selector/provenance text with the accepted DC-008 contracts;
- add the minimum revision/change-history entry identifying a source-provenance correction with no answer-key change.

The Validation Plan v1.5 SHA-256 cannot exist until a separately authorised document application generates the file. Validation Plan v1.4 remains immutable and authoritative until then.

Inspection found no SEP criterion/selector text in System Architecture v0.4, Workflow Design v0.4 or Demonstrator Design v0.5. Their existing separation architecture is already consistent, so no technical amendment is proposed. Requirements Specification, Engineering Design Brief and Network Model remain unchanged.

## 8. Verification obligations for later authorised application

A later application must prove at minimum:

1. `SEP-01` matching, contradictory and missing-authority cases;
2. actual rejection of every configured alternate formal section by the existing coordinator/API authority;
3. rejection probes leave the current run/history byte-for-byte unchanged;
4. `SEP-02` matching, persistent/mismatched configuration and missing-package cases;
5. `SEP-03` matching, permissive/mutated boundary and missing-probe cases;
6. `SEP-05` matching, changed FORMAL total and missing campaign-membership cases;
7. `SEP-04` and `SEP-06` remain unchanged and executable;
8. no translator reads an expected value or produces a verdict;
9. exact 24 tests / 124 requirements / 286 RTM relationships / 15 event types / 35 methods / 214 criteria remain;
10. active and historical catalogue/configuration identities are preserved according to the accepted candidate history; and
11. PR #12/I9 remain stopped until the authoritative and machine applications receive separate independent acceptance.

## 9. Lifecycle gate

- DC-008 is proposed only.
- No authoritative-document application is authorised.
- No catalogue or application implementation is authorised.
- PR #12 remains draft/unmerged and unchanged at its published head.
- QA-053 remains stopped at `SEP-01`.
- QA-054/055 WIP remains preserved.
- I9 remains stopped.

