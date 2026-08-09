# DC-001 — Consistent Network Entity Modelling

**Project:** Operational Technology Graduate Demonstration Project  
**Change ID:** DC-001  
**Title:** Consistent Network Entity Modelling  
**Status:** Applied / accepted baseline
**Date:** 2026-08-08

## 1. Change trigger

During detailed Network Model development, Feeder A contained sectionalising switches required for the formal fault-isolation scenario while Feeder B did not contain equivalent devices between its distribution sections.

Although the earlier arrangement was functionally sufficient for the fixed SEC-A2 validation scenario, the resulting asymmetry made the two primary feeders appear to have been modelled according to immediate demonstrator needs rather than as comparable engineering entities.

## 2. Engineering rationale

Equivalent entities should use a consistent modelling structure unless there is a documented engineering reason for them to differ.

The change does not require identical numerical values, operating roles or scenario behaviour. Feeder A and Feeder B may retain different capacities, loads, customer counts and scenario roles. The change concerns structural modelling consistency.

For this network, both primary feeders use the same basic radial pattern:

Source breaker → Section 1 → sectionalising switch → Section 2 → sectionalising switch → Section 3 → sectionalising switch → Section 4.

Only the devices necessary to the formal SEC-A2 validation scenario are actively operated during that scenario. The additional sectionalising devices remain legitimate network elements whose closed state contributes to topology tracing.

## 3. Approved change

1. Represent three sectionalising switches on each four-section feeder:
   - FDR-A: SW-A12, SW-A23, SW-A34
   - FDR-B: SW-B12, SW-B23, SW-B34
2. Retain TS-01 as the single normally-open tie between SEC-A4 and SEC-B4.
3. Represent equivalent sectionalising switches using a consistent information model, including stable identifier, configured endpoints, normal state, current state and telemetry information where monitored.
4. Introduce the broader rule: equivalent engineering entities use a consistent modelling structure and information set unless a documented engineering reason justifies a difference.
5. Do not require every represented switch to operate in the formal validation scenario.

## 4. Scope impact

No change to:
- project purpose;
- formal feeder-fault scenario;
- fault location (SEC-A2 at this baseline);
- selected intentional defect category;
- feeder loads/capacities;
- customer counts;
- restoration transfer load;
- simplified power-system-analysis boundary;
- conceptual SCADA/ADMS/OMS/GIS responsibilities.

The change is a detailed model-quality refinement and does not expand the project into additional operating scenarios.

## 5. Artefact impact

### Engineering Investigation & Research
No amendment required. Investigation A and C require sufficient sectionalising capability for credible isolation/restoration but did not prohibit additional equivalent devices.

### Engineering Design Brief
Modified Section 6.5 to:
- establish consistent sectional structure on both feeders;
- distinguish entity consistency from identical behaviour;
- retain the formal scenario's use of only the switches needed to isolate its fault;
- clarify that other switches still participate in topology/source-path determination.

Added:
- **DD-19 — Consistent Entity Modelling.**

### System Requirements Specification
Added:
- **REQ-NET-011 — Consistent Sectionalising Structure**
- **REQ-NFR-009 — Consistent Entity Modelling**

Requirement count updated from 114 to 116.

### Simplified Network Model
Reconciled the already-introduced symmetric feeder structure with the new formal requirements:
- NM-P05 polished;
- NM-P06 polished and linked to REQ-NET-011 / REQ-NFR-009;
- FDR-A contains SW-A12, SW-A23, SW-A34;
- FDR-B contains SW-B12, SW-B23, SW-B34;
- both feeders use equivalent four-section / three-sectionalising-switch radial structures.

A minor typographical error in Section 15 ("SEC-A2has") was corrected.

## 6. Requirements impact

New requirement REQ-NET-011 makes the exact network structural decision verifiable.

New supporting requirement REQ-NFR-009 generalises the modelling philosophy beyond the immediate switch arrangement so that later data modelling and implementation do not introduce arbitrary structural differences between equivalent assets.

No existing requirement is removed or weakened.

## 7. Validation impact

No existing formal validation outcome changes.

Future verification should include:
- inspection that both feeders contain sectionalising switches between every adjacent section pair;
- cross-model review that equivalent switch entities use the same core information structure.

Additional switches may naturally participate in topology-path validation but do not create new mandatory operating scenarios.

## 8. Configuration impact

The network configuration must contain these sectionalising devices and endpoints:

- SW-A12: SEC-A1 ↔ SEC-A2
- SW-A23: SEC-A2 ↔ SEC-A3
- SW-A34: SEC-A3 ↔ SEC-A4
- SW-B12: SEC-B1 ↔ SEC-B2
- SW-B23: SEC-B2 ↔ SEC-B3
- SW-B34: SEC-B3 ↔ SEC-B4

Normal state for all six: CLOSED.

## 9. Implementation implication

The later demonstrator should model sectionalising switches generically rather than creating feeder-specific switch object shapes.

Equivalent switch instances may have different IDs, endpoints, states and scenario roles, but the software/data structure used to represent them should be common.

## 10. Acceptance statement

DC-001 was implemented and accepted in the engineering baseline through the revised Engineering Design Brief, Requirements Specification and Network Model committed together.

DC-002 — Selectable Fault Location in Exploration Mode — remains a separate design change and is not included in DC-001.
