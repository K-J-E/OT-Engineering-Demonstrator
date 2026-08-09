# DC-002 — Selectable Fault Location in Exploration Mode

**Project:** Operational Technology Graduate Demonstration Project  
**Change ID:** DC-002  
**Title:** Selectable Fault Location in Exploration Mode  
**Status:** Applied / verified / accepted baseline
**Date:** 2026-08-08

## 1. Change trigger

The detailed network and topology design is deliberately model-driven: configured connectivity and current switching states determine energisation, outage extent, customer impact and restoration behaviour. During Network Model development, it was identified that allowing a reviewer to choose a fault location in a separate exploration mode would provide direct evidence that these outcomes are derived rather than hard-coded to the formal SEC-A2 validation scenario.

## 2. Engineering rationale

The formal engineering validation package requires a controlled, repeatable scenario with predetermined expected results, seeded-defect behaviour and repeat validation. That requirement is retained.

A reviewer-driven exploration mode serves a different purpose: it exercises the same network model with a different active fault-section input so that the reviewer can observe how operational consequences change with topology and network position. This strengthens the engineering demonstration without claiming that every exploration case has been formally validated.

The change deliberately applies to **fault location only**. Selectable electrical fault types are not introduced because credible differentiation between phase-to-ground, phase-to-phase, three-phase or high-impedance faults would require fault-current, protection and relay-behaviour scope that the project explicitly excludes.

## 3. Approved change

1. Preserve SEC-A2 as the fixed controlled fault location for the formal validation scenario.
2. Add a separate Exploration Mode in which the reviewer may select one represented distribution section (SEC-A1…SEC-A4 or SEC-B1…SEC-B4) as the active fault location.
3. Treat the exploration selection as a transient scenario input, not a persistent network-configuration change.
4. Determine the affected feeder from the selected section and apply the same generic protection-trip/topology/outage/customer/restoration logic used by the formal scenario.
5. Do not guarantee successful restoration for every exploration fault. No candidate, REJECTED and BLOCKED are legitimate derived outcomes.
6. Keep fault type fixed and abstract as a distribution-section fault resulting in operation of the relevant feeder protection.
7. Keep exploration outputs distinguishable from formal validation evidence unless an exploration case is separately defined and executed as a controlled validation test.

## 4. Scope impact

The change does not alter the core formal validation work package, seeded defect, detailed electrical-analysis boundary, conceptual OT responsibilities or real-equipment-control boundary. It adds a bounded demonstrator exploration capability using behaviour the engineering model already needs to support generically.

The project remains software-second: the additional interaction is justified because it exposes topology-derived engineering behaviour and produces meaningful non-success outcomes rather than adding unrelated interface functionality.

## 5. Artefact impact

### Engineering Investigation & Research
No retrospective amendment required. ED-C20 already establishes that fault location may be predefined **or otherwise provided as part of the validation scenario** and that no fault-location algorithm is developed. DC-002 uses the latter path for exploration mode while preserving the predefined formal baseline.

### Engineering Design Brief
Modified to:
- distinguish Formal Validation Mode from Exploration Mode;
- retain SEC-A2 as the controlled formal baseline;
- allow reviewer-selected section location in exploration;
- require generic model-driven behaviour after selection;
- explicitly exclude selectable electrical fault types;
- establish that unsuccessful restoration is a legitimate exploration outcome;
- clarify evidence classification.

Added:
- **DD-20 — Formal Validation / Exploration Separation**
- **DD-21 — Fixed Abstract Fault Type**

### System Requirements Specification
Generalised existing fault-isolation/restoration requirements from “predefined faulted section” to “active faulted section” where the behaviour is intended to be generic.

Added requirement group **REQ-EXP** with seven requirements covering:
- exploration-mode availability;
- section selection;
- fixed abstract fault type;
- generic derived behaviour;
- formal-baseline independence;
- non-guaranteed restoration;
- exploration-evidence classification.

Requirement count changes from 117 to 124.

### Simplified Network Model
Added **NM-P07 — Formal Validation and Exploration Separation** and Section **15.1 Exploration-Mode Applicability**. Existing SEC-A2/FDR-A scenario-role wording is clarified as applying specifically to formal validation.

No loads, capacities, customer counts, topology endpoints or normal switching states change.

## 6. Validation impact

The formal SEC-A2 validation baseline remains unchanged and continues to provide the controlled expected-result and seeded-defect path.

Exploration-mode functionality requires functional checks that:
- fault selection is available for represented sections;
- selections on both feeders invoke the same generic processing;
- outputs are derived from topology and network values;
- non-successful restoration outcomes are exposed rather than forced to success;
- exploration results remain separate from formal validation records.

These checks verify the exploration capability itself; they do not convert every selectable network contingency into a formal engineering validation case.

## 7. Configuration impact

No persistent network configuration values are changed by an exploration selection. The selected fault section belongs to transient scenario state.

Network Configuration v1.0 / v1.1 remain reserved for the seeded topology-defect baseline and corrected configuration developed against the formal SEC-A2 scenario.

## 8. Implementation implication

The later demonstrator should not implement a switch statement containing canned outcomes for SEC-A1, SEC-A2, etc. Fault selection should feed a common scenario engine whose results follow from section-to-feeder association, topology tracing, switching state, customer mapping, capacity and telemetry.

Formal Validation Mode should load the controlled SEC-A2 scenario explicitly. Exploration Mode should expose selection controls and identify itself clearly so reviewer experiments cannot be confused with formal validation evidence.


## 10. Verification correction

A post-generation top-to-bottom verification of DC-002 identified two administrative/wording issues and no loss of engineering content:

1. The Requirements Specification contained an inherited arithmetic error in the narrative requirement count. Counting unique formal requirement headings gives 115 requirements in the original uploaded baseline, 117 after DC-001, and 124 after the seven REQ-EXP requirements introduced by DC-002. Earlier prose counts of 114 / 116 / 123 were incorrect counts only; no requirement was missing. The DC-002 Requirements Specification and this change record have been corrected to 124.
2. The Design Brief retained one formal-scenario sentence stating that the second feeder would serve as the alternate source for the first. That wording was valid for the SEC-A2 formal baseline but ambiguous for Exploration Mode, where feeder roles may reverse. It has been clarified without changing the formal scenario.

The current detailed engineering documents remain revision 0.3. DC-001 should conceptually have advanced the documents from 0.1 to 0.2; the generated DC-001 files retained 0.1 in their headers due to an administrative edit omission. DC-002 correctly advances the current accepted working documents to 0.3. This note records that revision-history discrepancy so it is not mistaken for an engineering design change.

## 11. Acceptance statement

DC-002 was implemented, verified and accepted in the engineering baseline through the revised Engineering Design Brief, Requirements Specification and Network Model committed together as one controlled change.
