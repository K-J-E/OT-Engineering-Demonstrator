---
Status: Accepted DC-006 design and authoritative-document application; machine/catalogue application pending separate authorisation; I9 stopped
Authority: Derived analysis only — authoritative meaning remains in the accepted detailed documents and change record
Baseline: Reviewed main 70781cad986f3700f8e2d94fd20aa8b01482f50b
Updated: 2026-08-11
---

# DC-006 Determination-Coverage Analysis

## 1. Purpose and investigation boundary

This analysis records the I9 validation-design stop and the accepted minimum controlled determination contract needed to execute the 24-test Validation Plan catalogue without turning implementation-conformance tests into catalogue verdict evidence. It is an assurance/navigation aid only. Validation Plan v1.3, Demonstrator Design v0.5, System Architecture v0.4 and Workflow Design v0.4 are now the accepted DC-006 authoritative-document baselines; Requirements Specification v0.4, Engineering Design Brief v0.4, Network Model v0.4 and the machine Validation Catalogue remain unchanged.

The investigation preserves:

- `ExecutedValidationResult` as a valid expected-versus-observed comparison carrying exactly `PASS` or `FAIL`;
- ordinary missing evidence as `INCOMPLETE`, not `FAIL` or `BLOCKED-TEST`;
- DC-004 exact constituent/composite semantics;
- DC-005 exact suspension classifier and `BLOCKED-TEST` semantics;
- FORMAL/EXPLORATORY separation;
- one `ScenarioRun` per validation execution wherever a test actually exercises one scenario run;
- historical catalogue/test/case-definition resolution;
- 24 catalogue tests, 124 unique requirement IDs, 286 exact RTM relationships and 15 operational-event types; and
- the distinction between implementation-conformance tests and catalogue validation evidence.

## 2. Baseline finding

The accepted active Validation Catalogue v1.1 contains 24 definitions. Its current identity is:

- catalogue: `VALIDATION-CATALOGUE-V1.1`;
- catalogue SHA-256: `28bfe69131c40857c08f175abba42be3eb36514924b6de416b4e72bbefe35865`;
- manifest SHA-256: `45cb015f58af1d453be0255cdbbb857c08901877c416e830f26bb2fe6ecf60a3`;
- 24 definitions, 124 unique requirements and 286 exact `(test_id, requirement_id)` relationships.

Three catalogue-level paths are already authorised:

1. `VT-TOP-DEF-001` uses the existing structured expected-versus-observed execution comparison. Defective Network Configuration v1.0 and corrected Network Configuration v1.1 are separate one-run executions with immutable failure/repeat linkage; each execution also retains its distinct source Validation Catalogue identity.
2. `VT-EXP-ALL-001` uses nine accepted DC-004 constituent cases, each bound to one exploratory run/execution, followed by one immutable composite determination.
3. `VT-EXP-ROLE-001` uses four accepted DC-004 constituent cases, each bound to one exploratory run/execution, followed by one immutable composite determination.

The remaining 21 definitions contain objectives, methods, procedures, expected-result statements, evidence obligations and verdict rules, but no authorised structured determination criteria. The current validation service correctly refuses to invent a verdict for them. Existing unit, integration, component and browser tests prove implementation conformance only and are not immutable campaign `ExecutedValidationResult` evidence.

## 3. Recommended common determination model

### 3.1 One criteria contract, four controlled context kinds

Every promoted **non-composite** catalogue test should own one versioned `DeterminationMethodDefinition` with an exact required criterion set and one controlled context kind. Each exact constituent case of `VT-EXP-ALL-001` and `VT-EXP-ROLE-001` should separately own one such method. Those two parent catalogue tests remain governed exclusively by their accepted DC-004 `CompositeValidationResult` and must not acquire a direct DC-006 parent method, fictional context, parent `ValidationExecution` or parent `ExecutedValidationResult`.

| Context kind | Controlled use | Scenario-run rule |
|---|---|---|
| `SCENARIO_EXECUTION` | One operational scenario with one or more named checkpoints. | Exactly one `ScenarioRun` is bound to the execution. Multiple checkpoints never become fictional tests or runs. |
| `CONTROLLED_FIXTURE_EXECUTION` | A lower-level telemetry, topology, capacity or rule-boundary vector authorised by Validation Plan VP-P07/Section 10.1. | No fictional scenario run is created. An immutable fixture definition/result and executing build are bound instead. |
| `PRESERVED_RECORD_SET` | Configuration comparison, investigation chain, cross-run separation, deterministic-repeat or package-integrity assessment over existing immutable records. | Every member identity, role and hash is fixed before comparison. A run is linked only where a member genuinely owns one. |
| `ENGINEERING_REVIEW` | Explicit inspection/judgement criteria such as clarity or conceptual-boundary review. | No fictional run is created. A controlled review record, reviewed build/package identities and evidence are bound. |

This is a validation-execution context distinction, not four verdict mechanisms. All four use the same criterion record, completeness rule and deterministic aggregate.

The proposed common model retains one immutable `ValidationExecution` per executed non-composite procedure or DC-004 constituent-case procedure. `scenario_run_id` is mandatory only for `SCENARIO_EXECUTION`; fixture, record-set and review executions bind their own exact immutable context instead of fabricating a run. DC-004 constituents and every actual operational scenario remain one-run/one-execution; the composite parent adds no execution.

### 3.2 Criterion definition

Each required criterion should contain:

- stable `criterion_id`, version and canonical definition hash;
- parent test/case identity and evidence class;
- criterion kind: `MACHINE_COMPARISON` or `ENGINEERING_REVIEW`;
- exact `requirement_ids` allocated from the parent test's accepted RTM relationship set;
- context/checkpoint/subject role;
- predetermined expected value or explicit review proposition;
- controlled observation-source type and selector;
- controlled comparison operator/normalisation rule where machine-comparable;
- required evidence categories and authoritative source references;
- units, rounding and set/order semantics where relevant; and
- reviewer authority profile where engineering judgement is required.

Criterion-to-requirement mapping is a controlled refinement below the accepted RTM. For a non-composite test, each criterion's `requirement_ids` must be a subset of that test's accepted Section 15 requirement set and the union across its exact criterion set must equal that complete parent set.

For `VT-EXP-ALL-001` and `VT-EXP-ROLE-001`, each exact required constituent case's criteria may map only the subset of the parent test RTM that the case's defined evidence actually supports. No single case must cover the full parent set. The static union over the exact required nine/four case criterion mappings must equal the complete parent test set. Catalogue validation must reject missing parent coverage, out-of-parent mappings, unknown cases and any requirement assigned only by a non-required case.

A criterion may support multiple applicable requirements and a requirement may be evidenced through multiple substantive criteria, but no criterion may claim an out-of-parent requirement. These rules preserve exactly 124 unique requirement IDs and 286 `(test_id, requirement_id)` relationships while retaining immutable criterion→requirement→evidence traceability.

Defined coverage is not achieved validation evidence. Criterion definitions retain their intended mappings regardless of execution outcome. PASS/FAIL evidence retains the complete executed criterion-finding chain; for a composite test, the complete accepted constituent set is the boundary for claiming parent coverage. A valid suspended constituent may produce composite `BLOCKED-TEST`, but any requirements dependent on that suspended evidence remain unverified and cannot be reported as successfully verified from their planned mappings alone.

Machine observations must be resolved from existing authoritative backend records through a versioned source-adapter and operator registry. Catalogue data supplies the expected value, source role, field selector and operator. Production logic must not contain a `test_id` outcome switch or a second expected-topology algorithm.

The exact primitive operator registry is `SCALAR_EQUAL`, `NUMERIC_EQUAL`, `BOOLEAN_EQUAL`, `CANONICAL_SET_EQUAL`, `ORDERED_SEQUENCE_EQUAL`, `PRESENT`, `ABSENT`, `IDENTITY_HASH_AGREEMENT`, `CANONICAL_RECORD_EQUAL` and `REVIEW_FINDING_EQUAL`. Every criterion uses exactly one primitive. Unit/rounding/order/exclusion/expected-finding profiles are separate definition-owned normalisation data; compound assertions are split into criteria or use deterministic derived selectors. Special engineering calculations remain owned by the existing topology/outage/restoration/telemetry authorities; the validator only reads their preserved outputs.

### 3.3 Criterion findings and reviewer control

A machine criterion produces a backend-controlled finding from the resolved source record and expected definition. A reviewer criterion permits only a criterion-level finding against a fixed proposition:

- `SATISFIED`; or
- `NOT_SATISFIED`.

Until the required evidence and authority are complete, the criterion remains `NOT_EVALUATED` and the test remains `INCOMPLETE`. Reviewer criteria require a controlled proposal record and finalisation by an eligible independent engineering-review actor distinct from the proposer. The final reviewer cannot change the criterion wording, expected proposition, evidence class, test identity or aggregate verdict. The criterion finding, reason, evidence membership, actors and hashes become immutable on finalisation.

### 3.4 Deterministic aggregate

For every non-composite test execution:

1. Resolve the exact bound catalogue/test/case and determination-method identities.
2. Resolve the exact required context and evidence.
3. Require the exact criterion set once each; reject duplicates, substitutions and wrong-scope evidence.
4. If any required criterion/evidence/finding is absent or unfinalised, the attempt remains `INCOMPLETE` with no `ExecutedValidationResult`.
5. If complete and any criterion is `NOT_SATISFIED`, create one immutable `ExecutedValidationResult = FAIL`.
6. If complete and every criterion is `SATISFIED`, create one immutable `ExecutedValidationResult = PASS`.

DC-005 remains separate. A genuine VSC-001–VSC-005 condition may terminally suspend the attempt as `BLOCKED-TEST` under the accepted classifier/evidence/authority contract; it does not create an `ExecutedValidationResult`. Missing criteria or ordinary missing evidence do not become a suspension.

DC-004 remains separate. Constituent `ExecutedValidationResult` or valid suspension sources continue to feed the exact composite completeness and aggregate precedence rules. The criterion model supplies constituent methods, findings and PASS/FAIL results only; it does not create a parent method/result or alter composite semantics.

## 4. Determination coverage summary — all 24 tests

| Test | Current path | Proposed context | Criterion mix | Campaign determination |
|---|---|---|---|---|
| `VT-CFG-BASE-001` | Gap | Preserved record set | Machine | Direct PASS/FAIL |
| `VT-TOP-NORMAL-001` | Gap | Scenario execution | Machine | Direct PASS/FAIL |
| `VT-FML-N0-N5-001` | Gap | One scenario execution, six checkpoints | Machine | One direct PASS/FAIL |
| `VT-TOP-DEF-001` | Supported | Scenario execution per Network Configuration v1.0/v1.1 run | Machine | Existing direct FAIL/PASS path retained |
| `VT-CFG-INV-001` | Gap | Preserved record set | Machine + reviewer | Direct PASS/FAIL |
| `VT-TEL-FRESH-001` | Gap | Controlled fixture execution | Machine | Direct PASS/FAIL |
| `VT-TEL-STALE-001` | Gap | Controlled fixture execution | Machine | Direct PASS/FAIL |
| `VT-TEL-UNCERTAIN-001` | Gap | Controlled fixture execution | Machine | Direct PASS/FAIL |
| `VT-TEL-BAD-001` | Gap | Controlled fixture execution | Machine | Direct PASS/FAIL |
| `VT-TEL-FUTURE-001` | Gap | Controlled fixture execution | Machine | Direct PASS/FAIL |
| `VT-RST-ISOLATION-001` | Gap | Scenario execution | Machine | Direct PASS/FAIL |
| `VT-RST-SOURCE-001` | Gap | Scenario execution | Machine | Direct PASS/FAIL |
| `VT-RST-RADIAL-001` | Gap | Controlled fixture execution | Machine | Direct PASS/FAIL |
| `VT-RST-CAP-EQUAL-001` | Gap | Controlled fixture execution | Machine | Direct PASS/FAIL |
| `VT-RST-CAP-OVER-001` | Gap | Controlled fixture execution | Machine | Direct PASS/FAIL |
| `VT-RST-BINDING-001` | Gap | Scenario execution | Machine | Direct PASS/FAIL |
| `VT-ALM-EVT-001` | Gap | Scenario execution | Machine | Direct PASS/FAIL |
| `VT-VAL-RECORD-001` | Gap | Preserved record set | Machine | Direct PASS/FAIL |
| `VT-EXP-ALL-001` | Supported | Nine scenario constituents | Machine | Existing DC-004 composite retained |
| `VT-EXP-ROLE-001` | Supported | Four scenario constituents | Machine | Existing DC-004 composite retained |
| `VT-EXP-SEPARATION-001` | Gap | Preserved record set | Machine | Direct PASS/FAIL |
| `VT-NFR-REVIEW-001` | Gap | Engineering review | Machine + reviewer | Direct PASS/FAIL |
| `VT-DET-REPEAT-001` | Gap | Preserved record set | Machine | Direct PASS/FAIL |
| `VT-PKG-EVIDENCE-001` | Gap | Preserved record set | Machine | Direct PASS/FAIL |

## 5. Already-supported determination paths

### 5.1 `VT-TOP-DEF-001`

- **Accepted basis:** formal negative plus repeat; the same post-trip procedure on immutable Network Configuration v1.0 and Network Configuration v1.1 using the same build/inputs.
- **Existing path:** backend-derived post-trip topology, source attribution, energisation and customer impact are compared with predetermined structured values. Each execution remains bound to one run/Network Configuration and its source Validation Catalogue identity. Network Configuration v1.0 produces the preserved 400-customer `FAIL`; Network Configuration v1.1 produces the separately linked 850-customer `PASS`.
- **Evidence/provenance:** build, catalogue/test definition, configuration/package hash, run, evidence snapshot and comparison records.
- **DC-004/DC-005:** not composite; a genuine suspension remains possible only under DC-005. Ordinary missing evidence is incomplete.
- **DC-006 treatment:** express the existing structured fields as ordinary machine criteria in the promoted common schema without changing the engineering values, one-run provenance, failure preservation or repeat relationship.
- **Exact execution rule after AA-01:** the same common method is applied separately to the current post-trip run. The Network Configuration v1.0 ScenarioRun/ValidationExecution retains its own `FAIL`; a different corrected Network Configuration v1.1 ScenarioRun/ValidationExecution retains its own `PASS`. No criterion context contains both runs and no meta-PASS is derived. Current-record DEF-001/COR-001/repeat link fields remain immutable, while cross-run chain completeness is assessed by `VT-CFG-INV-001` and deterministic-repeat evidence.

### 5.2 `VT-EXP-ALL-001`

- **Accepted basis:** exact nine DC-004 constituent cases and one immutable composite.
- **Existing path:** each case has predetermined case-level structured values and one exploratory run/execution. The exact complete set determines the composite under DC-004.
- **Evidence/provenance:** corrected Network Configuration v1.1, common build/Validation Catalogue/test identity, case-definition identity, independent run/evidence links, EXPLORATORY class and composite membership.
- **DC-004/DC-005:** unchanged exact-set completeness and PASS/FAIL/BLOCKED-TEST precedence; suspension may occupy a case only through the accepted trusted target-selection path.
- **DC-006 treatment:** each exact required case owns its own method/criteria and maps only parent-test requirements supported by that case's evidence. No case must cover the entire parent RTM; the static union over all exact nine required case mappings must cover it. The parent owns no direct DC-006 method, context, execution or `ExecutedValidationResult`; map existing case fields to the common machine-criterion representation without changing case IDs, values, run count or the sole DC-004 composite determination.
- **Coverage/evidence rule:** catalogue validation rejects missing parent coverage, out-of-parent mappings and coverage supplied only by an unknown/non-required case. Planned mappings remain defined after PASS, FAIL or suspension, but achieved parent evidence is represented only by the complete DC-004 constituent chain. A suspended case may produce composite `BLOCKED-TEST`; requirements dependent on that evidence are not marked successfully verified.

### 5.3 `VT-EXP-ROLE-001`

- **Accepted basis:** exact four DC-004 constituent cases and one immutable composite.
- **Existing path:** each case has predetermined selected-fault, feeder-role, transfer/load/capacity and outcome values and one exploratory run/execution.
- **Evidence/provenance:** same controls as `VT-EXP-ALL-001`.
- **DC-004/DC-005:** unchanged.
- **DC-006 treatment:** each exact A2/B2/A1/A4 case owns its own method/criteria and maps only parent-test requirements supported by that case's evidence. No case must cover the entire parent RTM; the static union over the exact four required cases must cover it. The parent owns no direct DC-006 method, context, execution or `ExecutedValidationResult`; map existing fields to common machine criteria without changing the values or sole DC-004 composite determination.
- **Coverage/evidence rule:** apply the same missing/out-of-parent/non-required-case rejection and defined-versus-achieved evidence treatment as `VT-EXP-ALL-001`.

## 6. Detailed coverage for the remaining 21 tests

### 6.1 `VT-CFG-BASE-001` — Controlled configuration and network integrity

- **Accepted objective/method/procedure:** inspection plus functional loading of immutable Network Configuration v1.0/v1.1; verify identifiers, assets, connectivity, states, loads, capacities, customer zones and the single SW-A23 difference.
- **Expected engineering meaning:** both packages are schema-valid and hash-identified, match the Network Model, and differ only at SW-A23 endpoint 1 (`SEC-B3` versus `SEC-A2`).
- **Required criteria:** `CFG-01` both identities/manifests/hashes resolve; `CFG-02` both schemas validate; `CFG-03` canonical asset/connectivity/state/load/capacity/customer values equal the independent catalogue oracle; `CFG-04` the difference set contains exactly SW-A23 endpoint 1 with the accepted before/after values; `CFG-05` no other package difference exists.
- **Observed/evidence source:** configuration loader validation records, package manifests, canonical configuration records and configuration-comparison result. All are machine-comparable.
- **Context:** `PRESERVED_RECORD_SET`; no scenario run. Required roles are defective package, corrected package, schema and comparison.
- **Evidence/provenance:** build/tool identity, both configuration IDs/versions/hashes, schema hash, catalogue/test/method/criterion hashes and comparison payload hash.
- **Determination:** incomplete until exact roles/evidence exist; fail on any complete mismatch; pass only when all five criteria match.
- **DC-004/DC-005:** no composite interaction; a genuine package integrity failure may classify under DC-005 VSC-005, while an observed engineering/content mismatch with valid evidence is FAIL.
- **Artefact impact:** Validation Plan criteria table; System Architecture record-set context; Demonstrator Design configuration-source adapter. No Network Model change.

### 6.2 `VT-TOP-NORMAL-001` — Corrected normal topology and source attribution

- **Accepted objective/method/procedure:** functional/analysis run of corrected Network Configuration v1.1 at N0.
- **Expected engineering meaning:** eight energised sections; A1–A4 from FDR-A, B1–B4 from FDR-B; derived supplied loads 3,200/4,200 kW; radial, no outage.
- **Required criteria:** `TOP-N0-01` Network Configuration v1.1/normal switching/source conditions; `TOP-N0-02` exact energised section set; `TOP-N0-03` exact source attribution sets; `TOP-N0-04` derived feeder loads and complete attribution; `TOP-N0-05` radial/no unintended energised loop; `TOP-N0-06` empty de-energised set and zero affected customers.
- **Observed/evidence source:** backend ScenarioSnapshot/TopologyResult/OutageResult/feeder-load projection. All machine-comparable.
- **Context:** one FORMAL `SCENARIO_EXECUTION`, one `CONTROLLED_RESULT`/N0 checkpoint, one run using corrected Network Configuration v1.1.
- **Evidence/provenance:** build, configuration, run/revision/time, source paths, topology/outage records and criterion findings.
- **Determination:** standard incomplete/fail/pass aggregate.
- **DC-004/DC-005:** no composite; genuine suspension only under DC-005.
- **Artefact impact:** structured criteria/checkpoint in Validation Plan and promoted catalogue; generic scenario observation adapter.

### 6.3 `VT-FML-N0-N5-001` — Complete formal SEC-A2 sequence

- **Accepted objective/method/procedure:** execute the controlled formal sequence at the accepted times and capture N0, N1, N2, N3, N4 and N5.
- **Expected engineering meaning:** the exact Network Model state answer key, including 850/670/220 affected customers, 1,500 kW transfer, 5,700/6,000 kW, 95.0%, 450 restored and radial N5.
- **Required criteria:** `FML-TIME-01` exact controlled chronology T+0 N0 initial state → T+10 fault/protection trip to N1 → T+11 alarm acknowledgement → T+20 first isolation action → T+30 N2 after the second isolation action → T+40 N3 → T+50 N4 → T+55 N5; `FML-N0-01` normal corrected Network Configuration v1.1 topology/source/outage; `FML-N1-01` SEC-A2 fault, BRK-A OPEN, A1–A4 de-energised, B sections energised and 850 affected; `FML-N2-01` SW-A12/SW-A23 trustworthy OPEN, zero active source paths, isolation proven and 850 affected; `FML-N3-01` BRK-A CLOSED, A1 from FDR-A, A2/A3/A4 de-energised and 670 affected; `FML-N4-01` unchanged N3 switching plus A3/A4 candidate, 1,500 kW, 5,700/6,000 kW, 95.0%, 450 proposed restored and PERMITTED; `FML-N5-01` TS-01 CLOSED, A3/A4 from FDR-B, SEC-A2 faulted/de-energised, 450 restored, 220 affected and radial; `FML-EVT-01` required command/derived records retain accepted chronology, including the T+11 acknowledgement between trip and the first isolation action.
- **Observed/evidence source:** the six preserved backend scenario/evidence checkpoints, restoration assessment and operational event records. All criteria are machine-comparable.
- **Context:** exactly one FORMAL `SCENARIO_EXECUTION`, one `ScenarioRun` using corrected Network Configuration v1.1 under the future promoted DC-006 Validation Catalogue revision, and six named N0–N5 state checkpoints. The T+11 acknowledgement is chronology/alarm/event evidence, not a seventh state checkpoint. N0–N5 are not separate tests, executions or runs.
- **Evidence/provenance:** one run identity; per-checkpoint scenario time/revision and record hashes; build/config/catalogue/test/method/criterion identities; full source records.
- **Determination:** incomplete until every named checkpoint and criterion is present; one mismatch yields one final FAIL; all satisfied yields one final PASS.
- **DC-004/DC-005:** not a composite. A valid suspension closes the attempt under DC-005 without creating an N0–N5 `ExecutedValidationResult`.
- **Artefact impact:** Validation Plan must add the exact multi-checkpoint criterion matrix; Workflow/Demonstrator Design must define one-execution/multi-checkpoint finalisation.

### 6.4 `VT-CFG-INV-001` — Defect investigation, correction and evidence chain

- **Accepted objective/method/procedure:** inspect the consequence→SCADA→source trace→OMS→configuration comparison path and record DEF-001/correction/repeat/regression.
- **Expected engineering meaning:** correct telemetry; incorrect A3/A4 source path through SEC-B3/SW-A23; correct OMS result for the received topology; exact endpoint defect; algorithms unchanged; immutable linked failure/correction/repeat/regression.
- **Required criteria:** `INV-01` preserved Network Configuration v1.0 400/FAIL; `INV-02` initiating BRK-A evidence trustworthy and not causal; `INV-03` preserved A3/A4 path reaches FDR-B through SEC-B3/SW-A23; `INV-04` OMS arithmetic matches the derived de-energised set; `INV-05` exact one-difference comparison; `INV-06` immutable DEF-001/COR-001/direct-repeat/regression links; `INV-07` same backend build across failure/repeat/regression and correct Network Configuration v1.0/v1.1 roles, with each execution retaining its source Validation Catalogue identity; `INV-R01` independent reviewer confirms the recorded causal conclusion follows the required evidence sequence and does not claim an algorithm change.
- **Observed/evidence source:** investigation, validation, configuration-comparison, topology/outage and build records are machine-comparable for `INV-01`–`INV-07`; `INV-R01` uses an evidence-bound engineering review finding.
- **Context:** `PRESERVED_RECORD_SET` anchored to the original failed execution; no additional fictional run.
- **Evidence/provenance:** complete bidirectional chain, source record hashes, reviewed step IDs, reviewer actors/roles and criterion-definition hashes.
- **Determination:** incomplete until all machine criteria and the independently finalised review finding exist; any mismatch/NOT_SATISFIED yields FAIL.
- **DC-004/DC-005:** no composite; missing review is incomplete. VSC-001/002 applies only if its accepted facts genuinely exist, not because the review is pending.
- **Artefact impact:** Validation Plan reviewer criterion; architecture/workflow/design criteria-review contract.

### 6.5 `VT-TEL-FRESH-001` — Freshness arithmetic and inclusive boundary

- **Accepted objective/method/procedure:** evaluate controlled ages 0, 59,999 and 60,000 ms.
- **Expected engineering meaning:** integer non-negative ages are FRESH through the inclusive 60,000 ms boundary and evidence retains value/quality/timestamp/age separately.
- **Required criteria:** `TEL-FR-01/02/03` exact observed ages 0/59,999/60,000 ms; `TEL-FR-04/05/06` each classifies FRESH with GOOD quality and valid timestamp; `TEL-FR-07` the resulting validity permits continued assessment when other gates pass.
- **Observed/evidence source:** immutable outputs of the existing telemetry validity authority and associated assessment fixture. Machine-comparable.
- **Context:** one `CONTROLLED_FIXTURE_EXECUTION` owning the exact three-vector set; no wall-clock and no fictional run.
- **Evidence/provenance:** fixture definition/hash, controlled timestamps, executing build, telemetry results and criterion findings.
- **Determination:** standard aggregate across all three subcases.
- **DC-004/DC-005:** no composite; an actual uncontrolled-time dependency may invoke VSC-004, while an incorrect boundary value is FAIL.
- **Artefact impact:** Validation Plan exact fixture criteria; controlled-fixture context in architecture/design.

### 6.6 `VT-TEL-STALE-001` — Stale telemetry blocking

- **Accepted objective/method/procedure:** GOOD required telemetry at exact age 60,001 ms, then assessment.
- **Expected engineering meaning:** STALE/invalid-for-permissive evidence causes operational BLOCKED, names freshness cause and exposes no restoration execution.
- **Required criteria:** `TEL-ST-01` age exactly 60,001 ms; `TEL-ST-02` GOOD quality and STALE freshness remain distinct; `TEL-ST-03` overall validity false with stale reason; `TEL-ST-04` assessment BLOCKED rather than REJECTED; `TEL-ST-05` no restoration execution action.
- **Observed/evidence source:** telemetry authority, restoration assessment and backend action projection. Machine-comparable.
- **Context:** controlled fixture execution at the restoration-rule boundary.
- **Evidence/provenance:** exact timestamp arithmetic, fixture/build identities, assessment/action records.
- **Determination:** matching operational BLOCKED yields validation PASS; mismatch yields FAIL; missing evidence is incomplete.
- **DC-004/DC-005:** operational BLOCKED is not `BLOCKED-TEST`.
- **Artefact impact:** structured criteria only; no telemetry threshold change.

### 6.7 `VT-TEL-UNCERTAIN-001` — UNCERTAIN telemetry blocking

- **Accepted basis/meaning:** fresh required telemetry with quality UNCERTAIN must remain unusable and produce operational BLOCKED with the point/quality reason.
- **Required criteria:** `TEL-UN-01` exact quality UNCERTAIN and FRESH; `TEL-UN-02` overall validity false with quality reason; `TEL-UN-03` assessment BLOCKED; `TEL-UN-04` no execution action.
- **Observed source/context:** telemetry, assessment and action records from one controlled fixture execution; all machine-comparable.
- **Evidence/provenance/determination:** same typed fixture/build/test binding and incomplete/fail/pass rule as 6.6.
- **DC-004/DC-005:** operational BLOCKED remains expected PASS, not suspension.
- **Artefact impact:** Validation Plan/catalogue criteria only.

### 6.8 `VT-TEL-BAD-001` — BAD telemetry blocking

- **Accepted basis/meaning:** fresh BAD telemetry must remain unusable and produce operational BLOCKED with the point/quality reason.
- **Required criteria:** `TEL-BAD-01` exact quality BAD and FRESH; `TEL-BAD-02` overall validity false with quality reason; `TEL-BAD-03` assessment BLOCKED; `TEL-BAD-04` no execution action.
- **Observed source/context:** telemetry, assessment and action records from one controlled fixture execution; machine-comparable.
- **Evidence/provenance/determination:** same controls as 6.7.
- **DC-004/DC-005:** unchanged separation.
- **Artefact impact:** Validation Plan/catalogue criteria only.

### 6.9 `VT-TEL-FUTURE-001` — Future timestamp rejection

- **Accepted basis/meaning:** observation T+60.001 assessed at T+60.000 gives age −1 ms, `INVALID_TIMESTAMP`, operational BLOCKED and validation PASS.
- **Required criteria:** `TEL-FU-01` exact −1 ms age retained; `TEL-FU-02` INVALID_TIMESTAMP/not fresh/not clamped; `TEL-FU-03` invalid-time reason; `TEL-FU-04` assessment BLOCKED; `TEL-FU-05` no execution action.
- **Observed source/context:** telemetry, assessment and action records from one controlled fixture execution; machine-comparable.
- **Evidence/provenance/determination:** controlled timestamps and standard aggregate.
- **DC-004/DC-005:** an incorrect result is FAIL; actual uncontrolled time is separately VSC-004.
- **Artefact impact:** criteria only.

### 6.10 `VT-RST-ISOLATION-001` — Fault-isolation proof and workflow gate

- **Accepted basis/meaning:** before isolation the next gated restoration step is unavailable; each applicable boundary is operated/recalculated; isolation requires all incident boundaries trustworthy OPEN and zero active source paths; only BRK-A reclose becomes available at N2.
- **Required criteria:** `ISO-01` boundaries derive as `{SW-A12, SW-A23}`; `ISO-02` pre-isolation proof false and later workflow action unavailable; `ISO-03` one accepted boundary command is followed by recalculation before the next; `ISO-04` final boundary evidence GOOD/FRESH/OPEN; `ISO-05` zero active source paths; `ISO-06` isolation true; `ISO-07` BRK-A reclose available; `ISO-08` alternate restoration assessment remains unavailable until N3.
- **Observed/evidence source:** scenario snapshots, boundary evaluations, source paths, command/event chronology and allowed-action projection. Machine-comparable.
- **Context:** one FORMAL scenario execution through N2, with named pre/after-command/final-isolation checkpoints.
- **Evidence/provenance:** one run, exact revisions/times, command IDs, configuration/build/definition hashes.
- **Determination:** exact required checkpoint set, then standard aggregate.
- **DC-004/DC-005:** no composite; telemetry insufficiency during this test remains incomplete unless a genuine suspension is established.
- **Artefact impact:** Validation Plan checkpoint refinement; no DC-003 rule change.

### 6.11 `VT-RST-SOURCE-001` — Alternate-source breaker proven open

- **Accepted basis/meaning:** with all other evidence valid, ZS-01 AVAILABLE and trustworthy/fresh BRK-B OPEN leave a structural candidate but make alternate supply conclusively unavailable; outcome REJECTED, not BLOCKED/NO_CANDIDATE.
- **Required criteria:** `SRC-01` exact N3/pre-assessment state; `SRC-02` ZS-01 available; `SRC-03` BRK-B GOOD/FRESH/OPEN; `SRC-04` isolation/radiality/capacity evidence valid; `SRC-05` candidate retained; `SRC-06` source permissive fails with controlled reason; `SRC-07` outcome REJECTED; `SRC-08` close action unavailable.
- **Observed source/context:** one FORMAL scenario execution, current telemetry/topology/restoration/action records; machine-comparable.
- **Evidence/provenance/determination:** bound run/revision/assessment/build/config; standard aggregate.
- **DC-004/DC-005:** expected REJECTED produces PASS; untrustworthy source evidence would be an engineering BLOCKED result, not automatic test suspension.
- **Artefact impact:** criteria only.

### 6.12 `VT-RST-RADIAL-001` — Radial/no-loop permissive

- **Accepted basis/meaning:** a controlled proposed-topology fixture forming an unintended energised loop is rejected with loop/source-path evidence; canonical Network Configuration v1.1 remains unchanged.
- **Required criteria:** `RAD-01A` fixture definition identity/version/hash, executing build and configuration/hash provenance agree; `RAD-01B` fixture input/result proves the energised-loop/multiple-source condition; `RAD-02` complete trustworthy evidence; `RAD-03` radial permissive fails with offending path evidence; `RAD-04` outcome REJECTED; `RAD-05` close action unavailable; `RAD-06` canonical Network Configuration v1.1 bytes/hash unchanged.
- **Observed source/context:** one controlled fixture result from existing topology/restoration authorities plus pre/post configuration hash evidence; machine-comparable.
- **Evidence/provenance/determination:** fixture/build/config hashes and standard aggregate.
- **DC-004/DC-005:** expected REJECTED yields PASS; corrupted fixture may be VSC-005, but a calculated mismatch is FAIL.
- **Artefact impact:** controlled-fixture criteria; no topology rule or package change.

### 6.13 `VT-RST-CAP-EQUAL-001` — Capacity equality boundary

- **Accepted basis/meaning:** 4,500 + 1,500 = 6,000 kW; `6,000 ≤ 6,000`; capacity permissive passes and controlled display rounding is correct without canonical package mutation.
- **Required criteria:** `CAP-EQ-01/02/03` exact existing/transfer/capacity inputs; `CAP-EQ-04` resulting 6,000 kW; `CAP-EQ-05` capacity comparison true; `CAP-EQ-06` accepted unit/percentage presentation; `CAP-EQ-07` canonical configuration/load hashes unchanged.
- **Observed source/context:** controlled capacity fixture and restoration calculation result; machine-comparable.
- **Evidence/provenance/determination:** fixture/build/formula version, integer-kW values and standard aggregate.
- **DC-004/DC-005:** no interaction beyond general suspension rules.
- **Artefact impact:** criteria only.

### 6.14 `VT-RST-CAP-OVER-001` — Capacity exceedance boundary

- **Accepted basis/meaning:** 4,501 + 1,500 = 6,001 kW; capacity criterion fails and outcome is REJECTED without package mutation.
- **Required criteria:** `CAP-OV-01/02/03` exact inputs; `CAP-OV-04` resulting 6,001 kW; `CAP-OV-05` capacity permissive FAIL; `CAP-OV-06` outcome REJECTED with capacity reason; `CAP-OV-07` canonical hashes unchanged.
- **Observed source/context:** controlled capacity fixture/restoration result; machine-comparable.
- **Evidence/provenance/determination:** same controls as 6.13.
- **DC-004/DC-005:** expected REJECTED yields PASS.
- **Artefact impact:** criteria only.

### 6.15 `VT-RST-BINDING-001` — Assessment binding and invalidation

- **Accepted basis/meaning:** an N4 assessment is bound to current revisions; after relevant state/evidence change it cannot authorise execution, is immutably invalidated and a new assessment binds current revisions.
- **Required criteria:** `BIND-01` initial assessment identity/revision/current status; `BIND-02` controlled relevant revision change; `BIND-03` stale execution rejected; `BIND-04` exactly one linked invalidation record/event returned by the command result; `BIND-05` old assessment unchanged; `BIND-06` new assessment has a new identity/current revisions; `BIND-07` idempotent replay creates no duplicate.
- **Observed source/context:** one scenario run with assessment, command result, invalidation/event and replacement assessment records. Machine-comparable.
- **Evidence/provenance/determination:** run/revision/command/assessment/event/build/config links; standard aggregate.
- **DC-004/DC-005:** no composite; rejected stale execution is expected system behaviour and validation PASS.
- **Artefact impact:** criteria only.

### 6.16 `VT-ALM-EVT-001` — Alarm acknowledgement and operational chronology

- **Accepted basis/meaning:** formal workflow creates the approved alarm lifecycle and exact 15-type operational-event catalogue; commands precede derived records at equal time; validation/defect records remain separate.
- **Required criteria:** `EVT-01` fault creates the expected active/unacknowledged alarm; `EVT-02` acknowledgement records actor/time and preserves electrical revision behaviour; `EVT-03` the controlled operational-event registry equals exactly `{SCENARIO_INITIALISED, CONFIGURATION_SELECTED, FAULT_INITIATED, TELEMETRY_UPDATED, DEVICE_STATE_CHANGE, ALARM_GENERATED, ALARM_ACKNOWLEDGED, SWITCHING_ACTION, TOPOLOGY_RECALCULATED, OUTAGE_UPDATED, RESTORATION_CANDIDATE_IDENTIFIED, RESTORATION_NO_CANDIDATE, RESTORATION_ASSESSED, RESTORATION_ASSESSMENT_INVALIDATED, SCENARIO_RESET}` with no missing or additional ID; `EVT-04` every emitted operational event is a valid member of that exact registry; `EVT-05` equal-time command/derived ordering follows event sequence; `EVT-06` every simulated isolation/restoration switching action is represented; `EVT-07` validation, defect, correction, composite, suspension and package records are absent from operational events.
- **Observed source/context:** one formal scenario execution/event set, alarm and command records; machine-comparable.
- **Evidence/provenance/determination:** event/command/alarm/run/build/config identities and standard aggregate.
- **DC-004/DC-005:** confirms their records do not become event types; counts remain 15.
- **Artefact impact:** criteria only.

### 6.17 `VT-VAL-RECORD-001` — Validation records, reset and immutability

- **Accepted basis/meaning:** formal and negative executions retain complete definition/build/config/run/evidence/result links; reset/repeat creates new identities; final records/evidence are immutable.
- **Required criteria:** `VAL-REC-01` exact test/definition/catalogue/build/config identities; `VAL-REC-02` expected, observed, calculations, evidence class and evidence links complete; `VAL-REC-03` reset closes/preserves prior run and creates a new run; `VAL-REC-04` repeat creates a separate attempt/execution/result; `VAL-REC-05` final evidence membership equals stored evidence rows; `VAL-REC-06` controlled update/delete/late-insert attempts are rejected; `VAL-REC-07` operational events remain separate.
- **Observed source/context:** preserved validation/run/evidence repository records plus immutable persistence-assurance results. Machine-comparable.
- **Evidence/provenance/determination:** `PRESERVED_RECORD_SET` with exact member roles and hashes; standard aggregate.
- **DC-004/DC-005:** composite/suspension records may be included only to prove separation/immutability, not substituted for required PASS/FAIL members.
- **Artefact impact:** record-set and persistence-assurance criteria.

### 6.18 `VT-EXP-SEPARATION-001` — Formal/Exploration separation

- **Accepted basis/meaning:** formal remains fixed to SEC-A2; Exploration uses corrected Network Configuration v1.1 and transient selection; modes cannot be converted; actual campaign exploratory records do not satisfy or contaminate formal progress.
- **Required criteria:** `SEP-01` formal run fixed SEC-A2 with FORMAL class; `SEP-02` exploratory run uses corrected Network Configuration v1.1, selected section and EXPLORATORY class; `SEP-03` run mode/fault selection immutable and mode conversion rejected; `SEP-04` distinct run/execution/evidence identities; `SEP-05` the actual campaign exploratory executions/evidence and DC-004 composite records leave all FORMAL definition-without-execution, execution, finalised, PASS, FAIL and BLOCKED-TEST progress totals unchanged; `SEP-06` no exploratory evidence or DC-004 composite membership is linked as satisfying a formal result.
- **Observed source/context:** preserved formal records, actual campaign exploratory runs/executions/evidence, DC-004 composite records and progress-projection snapshots. Machine-comparable. A legitimate exploratory DC-005 suspension, if one happens to exist independently, may be retained as additional evidence but is not a required campaign member and shall not be manufactured for this test.
- **Evidence/provenance/determination:** `PRESERVED_RECORD_SET`; exact before/after progress snapshots and record links.
- **DC-004/DC-005:** DC-004 composite records are required evidence for the accepted campaign separation. DC-005 suspension/progress separation remains independently covered by implementation-conformance regression; the catalogue campaign does not create or require an exploratory suspension.
- **Artefact impact:** record-set criteria only.

### 6.19 `VT-NFR-REVIEW-001` — Scope, clarity, conceptual boundaries and reviewability

- **Accepted basis/meaning:** structured engineering review of labels, basis links, simulated-operation notices, conceptual module wording, topology diagrams and information separation; understandable, fictional, local, engineering-led and no production/real-control claim.
- **Required machine criteria:** `NFR-M01` runtime binding is loopback-only and no external operational service endpoint is configured; `NFR-M02` controlled build, Network Configuration, Validation Catalogue and test identity fields are present and resolve; `NFR-M03` the controlled surface registry equals the exact eight Section 14 views; `NFR-M04` the exact frozen Structural Record Set and owner mapping resolves; `NFR-M05` both feeders use common schemas; `NFR-M06` every exact surface contains the fixed visible notice `Simulated operation only — no real equipment control` and its frozen identity profile; `NFR-M07` no structural record is omitted, duplicated across owners or implementation-selected. These criteria establish presence, identity, linkage, configuration and structural facts only; they do not decide prominence, understandability, clarity, engineering-first character or whether presentation is misleading.
- **Required reviewer criteria:** `NFR-R01` engineering meaning and workflow are understandable; `NFR-R02` OT module wording is clearly conceptual rather than a production-product claim; `NFR-R03` interface remains engineering-first rather than a generic dashboard; `NFR-R04` engineering-basis and evidence paths allow a reviewer to trace requirement→design→result→evidence; `NFR-R05` the required fictional/simulated/no-real-control treatment is sufficiently prominent and clear and is not misleading.
- **Observed/evidence source:** runtime/build/network/presentation metadata for machine criteria; a versioned evidence-bound engineering review checklist with screenshots/record links for reviewer criteria.
- **Context:** one `ENGINEERING_REVIEW` bound to the exact build/package identities; no fictional scenario run.
- **Evidence/provenance:** criterion definitions, reviewed surfaces/records and hashes, proposer/final reviewer actor identities and immutable findings.
- **Determination:** pending/unfinalised criterion means incomplete; any machine mismatch or reviewer `NOT_SATISFIED` yields FAIL; all satisfied yields PASS. The reviewer never supplies overall verdict.
- **DC-004/DC-005:** no composite; missing review is incomplete, not VSC-001. A genuine accepted source conflict/absence may invoke DC-005 only when its evidence contract is actually satisfied.
- **Artefact impact:** Validation Plan exact checklist; architecture/workflow/design reviewer-finding model and review presentation.

### 6.20 `VT-DET-REPEAT-001` — Deterministic repeatability

- **Accepted basis/meaning:** repeat selected formal, negative and corrected cases under equal controlled inputs; canonical engineering results/checkpoints equal while generated identities remain distinct and linked.
- **Minimum controlled member roles:** `DET-FORMAL` = two completed `VT-FML-N0-N5-001` executions using corrected Network Configuration v1.1 under the future promoted DC-006 Validation Catalogue identities; `DET-NEGATIVE` = two completed `VT-TEL-STALE-001` fixture executions under the same promoted Validation Catalogue method identity; `DET-CORRECTED` = two completed `VT-TOP-DEF-001` executions using corrected Network Configuration v1.1 under the same future promoted DC-006 Validation Catalogue/test/method identities. Independent review accepts these roles subject to this version-namespace distinction; they are authoritative in the accepted document baseline and await separately authorised machine/catalogue application.
- **Required criteria:** `DET-01` exact member roles and distinct identities; `DET-02` same build/configuration/test/method/fixture/clock inputs within each pair; `DET-03` canonical engineering outputs/checkpoints equal after excluding only controlled generated-identity fields; `DET-04` explicit repeat links; `DET-05` original records unchanged.
- **Observed source/context:** immutable execution/fixture/evidence records and generic canonical-record comparator. Machine-comparable.
- **Context:** `PRESERVED_RECORD_SET`; no new scenario run is invented by the repeatability test itself.
- **Evidence/provenance/determination:** exact pair roles, exclusion profile/version/hash and standard aggregate.
- **DC-004/DC-005:** no composite unless an accepted DC-004 result is later selected through controlled change; suspended/incomplete source records cannot satisfy a repeat pair.
- **Artefact impact:** Validation Plan must accept the exact three member roles and canonical comparison profile.

### 6.21 `VT-PKG-EVIDENCE-001` — Self-contained evidence-package integrity

- **Accepted basis/meaning:** separately export two executions; verify required files, relative links, canonical JSON, figures, README and SHA-256 manifest; source provenance remains traceable and earlier package/execution unchanged.
- **Minimum controlled package roles:** `PKG-FORMAL` = one finalised `VT-FML-N0-N5-001` PASS using corrected Network Configuration v1.1 under the future promoted DC-006 Validation Catalogue/test/method identity; `PKG-HISTORICAL-DEFECT` = one preserved `VT-TOP-DEF-001` FAIL using defective Network Configuration v1.0 and exported through its original historical Validation Catalogue/test-definition identity. These roles satisfy the accepted two-package procedure and I9 historical-evidence gate without inventing a free selection. Independent review accepts them subject to this version-namespace distinction; they are authoritative in the accepted document baseline and await separately authorised machine/catalogue application.
- **Required criteria:** `PKG-01` two distinct non-overwriting package IDs/paths; `PKG-02` exact required file set; `PKG-03` every manifest entry exists and hashes; `PKG-04` canonical records/relative links/figures/README resolve; `PKG-05` source execution/build/config/catalogue/test identities match preserved records; `PKG-06` generation build remains separate from source build; `PKG-07` historical definition resolves by original identity; `PKG-08` generating/verifying the second package leaves the first package and both source executions unchanged.
- **Observed source/context:** evidence-package registry/archive verifier, historical catalogue resolver and preserved source records. Machine-comparable.
- **Context:** `PRESERVED_RECORD_SET`; no new scenario run.
- **Evidence/provenance/determination:** archive/package/source/generation-build hashes and standard aggregate.
- **DC-004/DC-005:** composite and suspension package regressions remain separate required regression gates; they do not replace the two controlled execution-package roles unless the Validation Plan is later amended.
- **Artefact impact:** Validation Plan must accept exact package roles; Demonstrator Design must bind generic package-verification observations.

## 7. Catalogue revision and history decision

A new controlled catalogue revision is required. The determination method, exact criterion set, context kind, observation selectors, reviewer authority requirements and checkpoint/member roles are test-definition meaning. Adding them changes the affected definition hashes and catalogue/manifest hashes even though the engineering answer key, test IDs and RTM do not change.

Before any later promotion:

1. preserve active Validation Catalogue v1.1 and manifest byte-for-byte as a new immutable historical package;
2. keep existing historical Validation Catalogue v1.0 unchanged;
3. add the promoted criteria-based Validation Catalogue as the next controlled revision (proposed Validation Catalogue v1.2; final version assigned during controlled application);
4. bind new attempts/executions to the promoted identity;
5. resolve/review/export completed Validation Catalogue v1.0/v1.1 records through their stored identities while preserving each execution's separate Network Configuration version and hash;
6. make unfinished old-catalogue attempts/executions historical/read-only under the existing DC-004/DC-005 rule; and
7. preserve all existing evidence packages and application-build identities.

The three already-supported tests retain their accepted results and semantics. Their promoted definitions may express existing fields through the common criterion schema, but historical records remain resolved against the exact older Validation Catalogue definitions under which they were executed and are never substituted based on Network Configuration version.

## 8. Authoritative artefact impact conclusion

| Artefact | Accepted DC-006 impact | Reason |
|---|---|---|
| Requirements Specification v0.4 | No wording or ID change. | `REQ-VAL-003`, `006`, `007`, `008` and `009` already require a defined objective/expected result and evidence-supported expected-versus-observed PASS/FAIL. |
| Validation Plan v1.3 | Accepted Section 21 plus exact determination matrices. | Authorises context kinds; exact criteria for the 22 non-composite tests; constituent-case criteria and static parent-coverage rules for the two DC-004 composite tests; reviewer findings; aggregate rule; multi-checkpoint N0–N5 treatment; fixture/record-set roles; and catalogue history gate. |
| System Architecture v0.4 | Accepted Section 28. | Allocates criteria definitions, source adapters, context binding, reviewer authority, deterministic aggregation and optional/non-fictional run relationships. |
| Workflow Design v0.4 | Accepted Section 29. | Defines preparation, evidence capture, criterion evaluation/review, incomplete handling, PASS/FAIL finalisation and DC-004/DC-005 interaction. |
| Demonstrator Design v0.5 | Accepted Section 38. | Defines contracts, persistence/immutability, API/read models, review actions, historical resolution and implementation boundary. |
| Engineering Design Brief / Network Model | No change. | No electrical, topology, outage, restoration, telemetry or engineering answer-key change. |
| DC-004 / DC-005 | No semantic change; cross-reference only. | Composite and suspension semantics remain controlling. |
| Machine catalogue/application/schema | Future separately authorised application only. | Not modified by this investigation/proposal. |

## 9. Investigation conclusion

The gap is not 21 missing engineering answers. The accepted plan already states those answers. The gap is a controlled way to bind varied but legitimate procedure contexts to exact criteria, evidence and authority, then deterministically create one PASS/FAIL result.

One common criteria model can close the gap without 21 test-specific verdict engines. It requires a controlled design change and catalogue revision because execution context, criterion definitions, reviewer authority and aggregation are validation meaning, not packaging implementation detail.

Independent review accepts this architecture, the deterministic-repeat and evidence-package member roles, DR-01–DR-07 and the corrected authoritative-document application at exact reviewed technical tip `c19451134c36d13d54f2185a3eaa0f20fcce95f0`. Validation Catalogue promotion, application/machine change and I9 resumption remain separately unauthorised.

## 10. Authoritative-document application review corrections

The DC-006 design and DR-01–DR-07 remain accepted. The first authoritative application at `6dc44046408593af3fb2c3a19d5412bf9a81fc23` was not accepted. Independent re-review accepted the bounded AA-01–AA-04 corrections at exact reviewed technical tip `c19451134c36d13d54f2185a3eaa0f20fcce95f0`; AA-01–AA-04 are closed:

- **AA-01:** `VT-TOP-DEF-001` now uses one common six-criterion method independently per current run. Network Configuration v1.0 retains a separate one-run `FAIL`; corrected Network Configuration v1.1 retains a separate one-run `PASS`. There is no cross-run scenario context or aggregate meta-result. The criterion union still exactly covers the parent test's accepted RTM set.
- **AA-02:** all eight controlled fixture methods bind exact fixture definition/version/hash, fixture input/result, executing build and applicable immutable Network Configuration/hash provenance. No fixture method contains `SCENARIO_RUN_AND_REVISION` or any fictional run evidence role.
- **AA-03:** all criteria use one accepted primitive operator. `EVT-04` compares the derived unregistered-event set with empty using `CANONICAL_SET_EQUAL`; `RAD-01A` and `RAD-01B` separately use `IDENTITY_HASH_AGREEMENT` and `BOOLEAN_EQUAL`; `SEP-04` compares cross-class identity collisions with empty using `CANONICAL_SET_EQUAL`.
- **AA-04:** `CONTROLLED_SURFACE_SET` is frozen to Start / Run Setup, Operational Workspace, Telemetry & Events, Restoration Assessment, Formal Validation, Evidence Library, Defect Investigation and Engineering Basis. Every member must show the fixed simulated/no-control notice and its definition-owned identity profile. `STRUCTURAL_RECORD_SET` is frozen to the concrete Section 8 plus DC-004/DC-005/DC-006 record membership and one controlling owner recorded in the accepted amendments.

The accepted document application contains **214 criteria**: 147 criteria across 22 non-composite tests and 67 across the exact nine/four DC-004 constituent cases. This count is a reviewed identity of the accepted document application, not a permanent project invariant. The controlled invariants remain exactly 24 tests, 124 unique requirements, 286 `(test_id, requirement_id)` relationships and 15 operational-event types. No machine catalogue, code/schema/migration, dependency or I9 authority is granted by this acceptance.

**V2 Automation Candidate — criteria and evidence assembly.** Mapping repeated source records to fixed criteria, checking completeness and preparing reviewer evidence is assurance-heavy and error-prone. A future tool could propose/bind evidence and highlight missing criteria while V1 retains fixed definitions, deterministic aggregation and independent engineering authority.
