# DC-008 SEP Selector-to-Proposition Provenance Audit

Status: **Derived analysis supporting proposed DC-008 — pending independent design review**

Independent design review: **Accepted in principle at `98f15c6a953bd5a69d2a51f674f3bfcfa0ea4139`; `DC008-DR-01` diagnostic-rejection clarification pending final design acceptance**

Authority: **Derived reference only; does not override authoritative engineering documents, accepted change records or controlled machine packages**

Owner: Project engineering review process

Updated: 2026-08-13

Related proposal: `02-change-control/DC-008-sep-separation-criterion-source-provenance.md`

## 1. Investigation question

Can every proposition in `SEP-01`, `SEP-02`, `SEP-03` and `SEP-05` be translated truthfully from its currently declared source, without reading the expected value, manufacturing policy evidence or reproducing backend algorithms?

Finding: **Not all four.** `SEP-01`, `SEP-02` and `SEP-03` contain at least one assurance claim whose controlling authority is not explicit in the current selector. `SEP-05` is supportable through its current selector when that source is populated from actual formal-only and mixed-campaign progress calculations rather than duplicated/pre-filled values.

`SEP-04` and `SEP-06` already use structural empty-set comparisons and remain outside this correction.

## 2. Existing authority inventory

| Authority | Existing controlled behaviour/fact | Evidence availability |
|---|---|---|
| `FORMAL_N0_N3_DEFINITION` | Frozen formal definition sets `fault_section_id = SEC-A2`. | Direct backend model; canonical content can be hashed. |
| `ScenarioCoordinator._validate_initialisation()` | FORMAL request with no explicit fault resolves to the definition fault; a different explicit fault raises `ScenarioBoundaryError`. | Existing service outcome; not presently persisted as a validation source record. |
| `ScenarioCoordinator.initialise()` / `initialise_replacement_run()` | Calls initialisation validation before run insertion or prior-run closure. | Existing transaction path; rejected request leaves state unchanged. |
| `/api/v1/runs` and `/api/v1/runs/start` | Maps `ScenarioBoundaryError` to HTTP 409. | Existing API outcome; ephemeral unless later captured in validation evidence. |
| `RunContext` | Stores actual mode, evidence class, selected/controlled fault, configuration and run identity as a frozen record. | Persisted scenario authority. |
| `ConfigurationManifest` / `ConfigurationCatalogEntry` / `LoadedConfiguration` | Provides exact configuration ID/version/status/content and SHA-256 package identity. | Immutable configuration-package authority. |
| `ScenarioCommandType` and strict API request models | No mode/fault mutation command; unknown command types/extra mutation fields are rejected. | Existing enum/schema/API authority; exact negative outcome can be captured. |
| `initialise_next_run()` | Mode changes occur through a separately identified run while prior history is preserved. | Existing scenario transaction result/history. |
| `WorkspaceService._validation_progress()` | Filters definitions/executions/suspensions to FORMAL before calculating progress totals. | Existing backend projection authority. |
| DC-004 composite repository | Preserves actual exploratory composite identities/membership separately from direct FORMAL results. | Immutable validation-assurance records. |

No new engineering rule is required. The gaps concern which existing authority is explicitly bound into criterion evidence.

For `SEP-01` and `SEP-03`, rejection status alone is not evidence. The captured source must diagnose the intended rejected action and preserve the controlling boundary/reason. A generic or unrelated service/API failure is not substitutable merely because its HTTP class or exception type is also a rejection.

## 3. SEP-01 audit

**Expected proposition**

`FORMAL run is fixed to SEC-A2, uses FORMAL evidence class and cannot select another fault.`

**Current selector**

`ScenarioRunAdapter.formal_run`

| Proposition component | Current proving fact | Classification |
|---|---|---|
| A FORMAL run exists | `RunContext.mode` | Fully supported by current selector |
| Current run fault is `SEC-A2` | `RunContext.fault_section_id` | Fully supported by current selector |
| Evidence class is FORMAL | `RunContext.evidence_class` | Fully supported by current selector |
| `SEC-A2` is the controlled fixed FORMAL input | `FORMAL_N0_N3_DEFINITION.fault_section_id` | Source-provenance gap |
| Another FORMAL fault cannot be selected | Actual `ScenarioBoundaryError`/HTTP 409 outcomes for all other configured sections | Source-provenance gap |

The current run can show what was selected, but not that alternatives are prohibited. A truthful observation therefore requires the actual definition and actual boundary outcomes in addition to the run.

### 3.1 Exact existing enforcement path

For a FORMAL request, the coordinator checks an explicitly supplied fault against `self._definition.fault_section_id`. Any difference raises `ScenarioBoundaryError("formal mode remains fixed to the controlled SEC-A2 fault input")`. Validation occurs before any run is inserted or replaced. The public endpoints convert that same boundary error to HTTP 409.

The future evidence capture must derive the alternate candidate set from the loaded configuration's section entities, submit each candidate to the same backend authority and preserve the actual rejection details plus unchanged before/after run identity. It must not hard-code seven expected rejection rows or infer success from the criterion ID.

When a mutable run already exists, each probe must use `initialise_next_run()` / the replacement-run boundary (equivalently `POST /api/v1/runs/start`). That path validates the proposed FORMAL input before closing the prior run. Evidence must preserve the exact diagnostic detail `formal mode remains fixed to the controlled SEC-A2 fault input`, or a controlled reason/code proven to originate from that same `_validate_initialisation()` branch.

The rejection `a mutable run already exists` does not reach or diagnose the alternate-fault boundary and is therefore invalid `SEP-01` evidence. The same exclusion applies to configuration-resolution, build-identity, transaction, revision and other unrelated failures. The before/after run and history identities must demonstrate that every diagnostic rejection left the existing run unchanged.

## 4. SEP-02 audit

**Expected proposition**

`EXPLORATION run uses corrected Network Configuration v1.1, a transient selected section and EXPLORATORY evidence class.`

**Current selector**

`ScenarioRunAdapter.exploration_run`

| Proposition component | Current proving fact | Classification |
|---|---|---|
| Run mode is EXPLORATION | `RunContext.mode` | Fully supported by current selector |
| Bound configuration identity/version is v1.1 | `RunContext.configuration_id/version` | Fully supported by current selector |
| Configuration is the corrected controlled package | `ConfigurationManifest.status` plus `ConfigurationCatalogEntry.package_sha256` | Source-provenance gap |
| A section is selected | `RunContext.fault_section_id` | Fully supported by current selector |
| Selection is transient run state, not persistent configuration | Ownership of `fault_section_id` by `RunContext`, combined with the exact immutable configuration data/schema/package identity | Source-provenance gap |
| Evidence class is EXPLORATORY | `RunContext.evidence_class` | Fully supported by current selector |

The proposed explicit package source prevents `v1.1` from being treated as synonymous with “corrected” merely because of its version label and proves that the selected scenario fault is not a configuration mutation.

## 5. SEP-03 audit

**Expected proposition**

`Run mode and selected fault are immutable after initialisation; in-place mode conversion is rejected.`

**Current selector**

`ScenarioRunAdapter.mode_conversion_probe`

| Proposition component | Current proving fact | Classification |
|---|---|---|
| Persisted run mode does not change | Before/after `RunContext` identity/hash | Representationally supportable by current probe |
| Persisted selected fault does not change | Before/after `RunContext` identity/hash | Representationally supportable by current probe |
| Domain run record is immutable | Frozen `RunContext` model | Representationally supportable by current probe |
| No accepted command mutates mode/fault in place | Exact `ScenarioCommandType`/API schema | Source-provenance gap if not explicit |
| Attempted in-place conversion is rejected | Actual strict request-model/API rejection outcome | Source-provenance gap |
| Accepted mode switching creates a separate run | `initialise_next_run()` result and preserved prior-run history | Representationally supportable by current probe |

The current selector name anticipates a probe, but a run record alone cannot prove the API rejection. DC-008 therefore makes the existing API boundary explicit rather than allowing the run adapter to claim an unobserved rejection.

`mode_mutation_rejection` and `fault_selection_mutation_rejection` must each preserve the submitted mutation shape and the actual strict request-model/API diagnostic that rejects that specific field/action. An unrelated `4xx`/`409`, an unrelated required-field failure, an unrelated revision conflict or any other generic validation failure does not prove that in-place mode/fault mutation is prohibited and must not satisfy the observation.

## 6. SEP-05 audit

**Expected proposition**

`Actual campaign exploratory executions/evidence and DC-004 composites do not change FORMAL definition-without-execution, execution, finalised, PASS, FAIL or BLOCKED-TEST totals.`

**Current selector**

`FormalProgressAdapter.before_after`

| Proposition component | Current proving fact | Classification |
|---|---|---|
| Actual exploratory executions/evidence exist | Exact repository execution/evidence IDs and counts | Fully supportable by current selector |
| Actual DC-004 composites exist | Exact finalised composite IDs/membership | Fully supportable by current selector |
| FORMAL definition-without-execution total unchanged | Formal-only vs mixed-campaign calls to accepted progress projection | Representational translation only |
| FORMAL execution/finalised/PASS/FAIL/BLOCKED-TEST totals unchanged | Same two actual projection results | Representational translation only |

The producer must call the accepted progress authority twice with different actual record sets. Supplying the same pre-filled dictionary under two labels would not establish this proposition. At least one actual exploratory execution/evidence chain and both required DC-004 composites must be present; otherwise the criterion remains incomplete.

No source-selector change is proposed for `SEP-05`.

## 7. Matching, mismatch and missing-evidence obligations

| Criterion | Matching facts | Truthful mismatch example | Missing/incomplete example |
|---|---|---|---|
| `SEP-01` | Run/definition both identify the same fixed formal section; every other configured section receives the diagnostic FORMAL fixed-fault rejection from the intended boundary; run unchanged | One configured alternate is accepted, rejected only by an unrelated boundary, definition differs from run, or evidence class is not FORMAL | Definition unresolved, candidate set incomplete, diagnostic boundary/reason missing or non-unique, or before/after run proof absent |
| `SEP-02` | EXPLORATION/EXPLORATORY run binds the exact corrected package; selection is run-owned and package unchanged | Package status is defective, run/package identities differ, or selected state appears as persistent configuration mutation | Run, package, manifest, catalog entry, data or identity/hash relationship absent |
| `SEP-03` | Actual mutation attempts receive mutation-specific strict-schema/API rejections and run identity/hash remains unchanged; accepted switch creates separate run | Boundary accepts a mutation, rejection diagnoses an unrelated failure, or existing run fields change | Either diagnostic mutation/rejection outcome or before/after run evidence absent |
| `SEP-05` | Actual mixed campaign leaves all six FORMAL totals equal to formal-only projection | Any one FORMAL total differs | Actual exploratory execution/evidence/composite membership or either projection absent |

The translator serialises these observed facts into canonical language. It never assigns `SATISFIED`, `NOT_SATISFIED`, `PASS`, `FAIL` or `BLOCKED`.

## 8. Identity analysis method

The prospective hashes in DC-008 were calculated entirely in memory from exact active candidate files at PR #12 head `a2027d0fbd3edf38789af6e994a669eeddcf5520`:

- catalogue `f224a8826f4c02dd0c4bb5c22f3ab7351cd4eb17106b78541aeaf3b1c1d9cbe4`;
- manifest `ef30f4e17a67dadefce5141edb3335544804bf512e4d76e85f351bc4fa0ee4c9`.

Only the following analytical mutations were applied:

1. replace the selectors of `SEP-01`, `SEP-02` and `SEP-03` with the exact proposed strings;
2. increment those criterion versions from 1.0 to 1.1 and recalculate their hashes;
3. increment `DM-EXP-SEPARATION-001` from 1.0 to 1.1 and recalculate its hash;
4. increment `VT-EXP-SEPARATION-001` from 1.1 to 1.2 and recalculate its definition hash; and
5. set the prospective authority string to `Accepted Validation Plan v1.5 Section 21 / DC-006 + DC-007 + DC-008` before calculating catalogue/manifest identities.

No expected value, operator, normalisation, evidence role, requirement mapping, catalogue count or application file was changed. The resulting model was validated against the current strict `ValidationCatalogue` contract. Nothing was written to the machine catalogue.

## 9. Authoritative impact inspection

Accepted Validation Plan v1.4 Section 21.3.19 contains the exact four current selector/proposition pairs audited above. A later accepted DC-008 application therefore requires Validation Plan v1.5 with only the three selector/provenance changes and normal revision metadata.

Text inspection of System Architecture v0.4, Workflow Design v0.4 and Demonstrator Design v0.5 found no SEP criterion IDs or machine selector definitions. Their existing FORMAL/EXPLORATORY separation contracts do not conflict with DC-008, so no amendment is proposed.

## 10. Gate and V2 note

DC-008 is proposed and grants no application authority. PR #12 remains draft/unmerged; QA-053 remains stopped; QA-054/055 WIP remains preserved; I9 remains stopped.

**V2 Automation Candidate** — the selector-to-proposition provenance audit and cascading criterion/method/test/catalogue identity calculation are repetitive, evidence-heavy assurance tasks. A future tool could trace each proposition clause to source fields and flag unsupported narrative claims before catalogue promotion, while leaving engineering judgement and change acceptance with the reviewer.
