# DC-003 — Generic Active-Fault Isolation Boundary Derivation

Status: Applied / cross-document verified / accepted baseline  
Date raised: 2026-08-09  
Revision date: 2026-08-09  
Acceptance date: 2026-08-09  
Application and verification date: 2026-08-09  
Change class: Engineering design clarification  
Origin: DQ-001 identified before Step 9 Validation Plan

## 1. Purpose

Exploration Mode already requires the selected fault section, affected feeder, topology, outage, restoration assessment and action availability to be derived by the same generic engine used by the formal scenario. The accepted baseline does not yet state a sufficiently exact rule for deriving the isolation boundaries and applicable OPEN actions for an arbitrary selected section.

This accepted change closes that design gap without adding an electrical fault type, protection study, topology editor, canned per-section result or new restoration criterion.

## 2. Existing baseline retained

- The formal controlled validation scenario remains `SEC-A2` with `SW-A12` and `SW-A23` as its isolation boundaries.
- Exploration fault selection remains transient scenario state and does not alter persistent configuration.
- The selected network configuration, observed device states, source availability and active topology remain the inputs to topology processing.
- Fault status remains distinct from energisation status.
- Restoration remains unavailable until the active fault is topologically isolated from every available source.
- Restoration outcomes remain `PERMITTED`, `REJECTED` or `BLOCKED`; the absence of a candidate remains a valid derived result.
- All outage, customer and restoration consequences remain derived. They shall not be stored as eight canned scenario outcomes.

## 3. Accepted generic rule

For the active fault section, the demonstrator shall:

1. Query the selected immutable network configuration for every switchable device directly incident to the fault section.
2. Treat those incident switchable devices as the fault-section isolation boundaries. Depending on section position, a boundary may be a feeder source breaker, sectionalising switch or the normally-open tie switch.
3. Evaluate each incident boundary using the three controlled evidence/action conditions in Section 3.1.
4. Execute no more than one device command per accepted action, then recalculate boundary status, available isolation actions, active topology, source paths and the overall isolation proof before another action is selected.
5. Prove fault isolation only when every incident switchable boundary is proven `OPEN` with trustworthy/fresh telemetry **and** topology processing finds zero active paths from every available source to the fault section.
6. Derive isolation switching actions as OPEN operations only. A close operation on an active-fault boundary shall not be offered as an isolation action.
7. Permit more than one eligible OPEN action to be displayed when multiple boundaries are proven CLOSED and the existing workflow/command gates authorise them. A validation procedure may select a deterministic order, but interface availability shall not hard-code that order as the engineering rule.

### 3.1 Boundary Evidence and Action Conditions

| Condition | Controlled evidence | Boundary result | Action/result treatment |
|---|---|---|---|
| **A — trustworthy OPEN** | Quality `GOOD`; freshness `FRESH`; observed state `OPEN` | Boundary is **PROVEN OPEN** and its isolation evidence is **SATISFIED**. | No OPEN command is required or offered for that boundary. |
| **B — trustworthy CLOSED** | Quality `GOOD`; freshness `FRESH`; observed state `CLOSED` | Boundary is **PROVEN CLOSED**. | Expose an authorised OPEN isolation action, subject to the existing workflow and command gates. |
| **C — boundary state cannot be trusted** | `STALE`, `UNCERTAIN`, `BAD`, `INVALID_TIMESTAMP`, or missing required telemetry, regardless of the last-reported OPEN/CLOSED value | Boundary is **UNPROVEN**. | Fault isolation cannot be completed. Do not offer a redundant OPEN command merely because the boundary cannot be proven open. Present the telemetry/evidence deficiency and require the controlled evidence condition to be corrected or refreshed before conclusive evaluation. |

The last-reported value does not override its evidence condition. In particular, a last-reported `OPEN` with stale, uncertain, bad, invalid or missing telemetry is not proven open and does not satisfy an isolation boundary.

After a valid telemetry update or an accepted switching command, the demonstrator recalculates:

- boundary status;
- available isolation actions;
- active topology;
- source paths; and
- overall isolation proof.

These conditions apply generically to sectionalising switches, tie switches and source breakers. A source breaker opened by feeder protection satisfies its incident boundary only when its observed `OPEN` state is supported by `GOOD`, `FRESH` telemetry.

The rule is configuration-driven. It shall not use section-ID conditionals to return stored switch lists, customer counts, outage extents or restoration results.

## 4. Controlled v1.1 incidence answer key

This table is the expected result of applying the generic incidence query to the corrected v1.1 configuration. “Initially satisfied” refers to the normal device state before the selected feeder protection operation and subsequent state processing; the affected source breaker is also opened by the feeder-protection transition.

| Selected fault section | Incident switchable isolation boundaries | Boundary condition relevant to the standard scenario |
|---|---|---|
| `SEC-A1` | `BRK-A`, `SW-A12` | `BRK-A` is opened by affected-feeder protection; `SW-A12` is the remaining OPEN isolation action. |
| `SEC-A2` | `SW-A12`, `SW-A23` | Both sectionalising switches require OPEN actions in the formal sequence. |
| `SEC-A3` | `SW-A23`, `SW-A34` | Both sectionalising switches are derived from incidence. |
| `SEC-A4` | `SW-A34`, `TS-01` | `TS-01` is normally OPEN and is satisfied evidence if telemetry is trustworthy/fresh; `SW-A34` is the remaining OPEN isolation action. |
| `SEC-B1` | `BRK-B`, `SW-B12` | `BRK-B` is opened by affected-feeder protection; `SW-B12` is the remaining OPEN isolation action. |
| `SEC-B2` | `SW-B12`, `SW-B23` | Both sectionalising switches are derived from incidence. |
| `SEC-B3` | `SW-B23`, `SW-B34` | Both sectionalising switches are derived from incidence. |
| `SEC-B4` | `SW-B34`, `TS-01` | `TS-01` is normally OPEN and is satisfied evidence if telemetry is trustworthy/fresh; `SW-B34` is the remaining OPEN isolation action. |

The table is an engineering answer key for verifying the generic query against v1.1, not permission to implement a per-section lookup in production logic.

## 5. Requirements impact

No new formal requirement is proposed. The clarification supplies an implementable rule beneath existing requirements, principally:

- `REQ-NET-009` — switching devices represented in network connectivity;
- `REQ-TOP-007` — isolation state derived from switching states and topology; and
- `REQ-EXP-004` — selected fault location used by the generic topology, outage and restoration logic.

The formal requirement count remains **124**.

## 6. Controlled artefact application

The accepted change has been applied to the following detailed documents rather than left as an implementation-only interpretation:

- Engineering Design Brief — add the generic boundary-derivation decision and rationale;
- Simplified Network Model — add the incidence answer key and isolation-proof rule;
- System Architecture — allocate the configuration incidence query, topology proof and action-set ownership;
- Workflow Design — add the generic isolation-action derivation/recalculation sequence;
- Demonstrator Design — add the backend action-availability rule and prohibit per-section lookup logic; and
- Validation Plan — activate the DC-003-dependent Exploration isolation tests and accept the final Step 9 baseline.

The Requirements Specification needs no wording change unless review concludes that the existing requirements are insufficient.

## 7. Validation impact

Step 9 verifies through its accepted definitions and future controlled executions:

- the incident boundary pair for all eight selectable sections in corrected v1.1;
- trustworthy/fresh already-open boundaries are treated as satisfied evidence rather than redundant actions;
- a last-reported OPEN value with stale, uncertain, bad, invalid or missing telemetry remains UNPROVEN, blocks isolation proof and does not cause a redundant OPEN command to be offered;
- source breakers opened by protection are reflected in the subsequent isolation proof;
- applicable actions are recalculated after each accepted command;
- every incident boundary is proven OPEN and zero active source paths are required before isolation is proven; and
- no per-section stored outage/restoration answer is used.

## 8. Acceptance, application and implementation gate

Independent engineering re-review accepted revised DC-003 for controlled application on 2026-08-09. The change was then applied to all six affected authoritative artefacts and cross-document verified before final Step 9 acceptance. The obsolete increment-specific draft gate is withdrawn.

Current lifecycle disposition: **DC-003 applied and cross-document verified → Step 9 Validation Plan v1.0 accepted → implementation remains subject to separate explicit user authorisation.** This record and the Step 9 acceptance do not themselves authorise implementation.

## 9. Configuration-package administrative finding

Repository inspection confirmed that substantive implementation has not begun and that no immutable implementation configuration packages currently exist. The Simplified Network Model contains the approved engineering definitions of defective Network Configuration v1.0 and corrected Network Configuration v1.1. After implementation is explicitly authorised, the first implementation baseline shall instantiate both definitions as separate immutable schema-valid packages and record their SHA-256 hashes before validation execution.

The later running demonstrator shall select the already-instantiated v1.1 package for repeat validation; it shall not create, overwrite or silently correct v1.0 or v1.1 during the investigation workflow.

## 10. Application and verification record

| Authoritative artefact | Applied revision | Controlled application result |
|---|---:|---|
| Engineering Design Brief | 0.4 | Added DD-22 and the configuration-driven boundary/evidence/isolation-proof rationale. |
| Simplified Network Model | 0.4 | Added Section 18, the eight-section v1.1 incidence answer key, A/B/C conditions, final proof and package-lifecycle boundary. |
| System Architecture | 0.2 | Added AD-SA-013 and allocated configuration, observed evidence, derived proof, coordinator action-set and presentation ownership. |
| Workflow Design | 0.2 | Added AD-WF-017 and the generic one-action/recalculation workflow; replaced the obsolete before-I8 gate. |
| Demonstrator Design | 0.2 | Added AD-DD-023, backend records/action ownership, presentation rules and prohibited shortcuts. |
| Validation Plan | 1.0 — Accepted Validation Plan Baseline | Activated accepted DC-003 tests, corrected the implementation-package claim and recorded final Step 9 acceptance. |

Verification passed on 2026-08-09:

- the Requirements Specification file and its 124 unique formal requirements were unchanged;
- all six revised Word documents opened structurally, rendered successfully and were reviewed across all 237 pages;
- all six documents use the same A/B/C evidence conditions, all-open plus zero-source-path isolation proof and configuration-incidence rule;
- formal SEC-A2 remains separate from Exploration Mode and retains SW-A12/SW-A23 and the approved N0–N5 answer key;
- no per-section production lookup, new restoration criterion, new requirement or V1 AI/automation behaviour was introduced;
- the Validation Plan retains 24 catalogue tests and exactly 124 unique RTM rows; and
- the current-baseline manifest, design-change register, QA register, implementation source map and README were reconciled after application.

Final disposition: **Applied / cross-document verified / accepted baseline.**

## V2 Automation Candidate

**V2 Automation Candidate — configuration-driven isolation QA.** A future assurance tool could derive incident switchable boundaries from a supplied topology, compare them with expected isolation logic and flag incomplete or unsafe action sets; V1 shall perform the deterministic generic derivation and engineer-reviewed validation without AI.
