---
Status: Showcase V1 Release Candidate — pending final independent review
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-13
Increment: I9 — Packaging / Review
---

# I9 Showcase Packaging Closeout

## 1. Authorisation and boundary

The Showcase V1 Release Convergence Sprint authorised I9 from clean reviewed main `e4a934c97c84bcbcf7be9d2b0539aa9c24c52191` after PR #16 and converged PR #12 were incorporated. A fresh branch, `agent/i9-showcase-release`, was created from that exact baseline; the stopped historical I9 branch was not reused.

I9 packages and proves the accepted V1 engineering implementation. It adds no network, topology, outage, restoration, telemetry-validity, DC-003, validation-verdict or configuration rule. It adds no real interface, production-control capability, AI or automation feature.

## 2. Delivered reviewer experience

- `scripts/showcase.sh` provides `setup`, `start`, `verify` and `reset` commands. Default invocation installs locked dependencies when required, builds the frontend and starts one loopback-only process.
- The production React bundle is served by the existing local FastAPI composition root; API and UI share `127.0.0.1` without an external service.
- The root README is an external-reviewer entry point covering intent, limits, setup, a five-part walkthrough, technology and engineering authority.
- Run setup presents four direct showcase paths: formal operation, seeded-defect investigation, corrected-v1.1 Exploration and the accepted stale-telemetry safety case.
- The safety walkthrough submits only existing public scenario commands at accepted controlled times. It creates no alternate engineering calculation: the existing telemetry/topology/isolation authorities derive `GOOD` + `STALE`, `UNPROVEN` boundaries and unavailable switching actions.
- A reviewer can return to run setup from any active run. Backend replacement preserves the accepted immutable history treatment.
- Engineering Basis now exposes current build/configuration/run identity, baseline counts, the authority chain, demonstrated capabilities and deliberate non-production boundaries.
- Secondary controls, responsive layout variables, theme metadata and a local favicon remove visible unfinished/default presentation.

## 3. Controlled identities preserved

- Validation Plan v1.5: `33d8f46dca170045a352e022cc1d9312a6f821d93c1113c4926d40a7a0286c9b`.
- Validation Catalogue v1.2: `3553ac28856cbe64056fda516ccdc05242960194e956444c01bd11eb7fbd3d1f`.
- Validation Catalogue manifest: `e1bba6567da17a1074536859a17ff553f3b969ae1c27eefd1265e20bafdbe07f`.
- Historical catalogue v1.0/v1.1 and Network Configuration v1.0/v1.1 packages remain byte-identical.
- Exact 24 tests / 124 requirements / 286 RTM relationships / 35 methods / 214 criteria / 15 operational-event types remain.

## 4. Verification

Fresh clone of the published I9 branch:

- `./scripts/showcase.sh setup`: PASS — locked backend and frontend installation, zero reported npm vulnerabilities, production build created.
- `./scripts/showcase.sh verify`: PASS — 205 backend tests, deterministic catalogue rebuild and 20 component tests; production build passed.
- Chromium: 4/4 PASS — formal N0–N5, seeded-defect investigation/correction, stale-evidence safety and SEC-B2 reverse-role Exploration/export.
- Single-process start: PASS — `/` served the production application and `/api/v1/workspace/bootstrap` returned corrected configuration v1.1, `VT-FML-N0-N5-001` and 24 definitions.
- Manual reviewer inspection: PASS — start page, operational one-line, persistent provenance, navigation and Engineering Basis were coherent; browser console contained no errors or warnings.
- Clean shutdown: PASS through `Ctrl+C` application shutdown.

Release-critical outcomes reconfirmed:

- Formal: N1 850 affected; N3 670; N4 1.50 MW / 5.70 MW / 95.0% / PERMITTED; N5 220 affected and 450 restored.
- Defect: immutable v1.0 400/FAIL → SW-A23 endpoint investigation → corrected v1.1 850/PASS repeat with preserved records.
- Exploration: SEC-B2 reverses feeder roles through configuration-derived processing and retains EXPLORATORY export classification.
- Safety: SW-A12/SW-A23 remain GOOD but are STALE at controlled T+71; isolation is UNPROVEN and switching is withheld with backend reasons.
- Evidence basis: build/configuration/run/test identities, investigation records, validation records, exported package identity and engineering authority remain visible and linked.

## 5. Known limitations and deferred work

- The complete controlled 24-test campaign has not been executed. Implementation tests are conformance evidence only; absent campaign evidence remains `NOT_EVALUATED` / `INCOMPLETE` and no PASS/FAIL is manufactured.
- The production JavaScript bundle is approximately 709 kB before gzip and emits Vite's non-blocking code-splitting advisory. It loads correctly in the local showcase; optimisation is post-outreach work.
- The final fresh-checkout environment used Node.js 24.14.1 with npm 11.11.0. The controlled project metadata records Node.js 24.19.0 and npm 11.17.0; no dependency or lock content changed, the supported major-version gate passed and the install/build passed. Exact patch-toolchain reproduction remains an assurance follow-up, not a showcase behaviour claim.
- Wider catalogue campaign execution, additional manual accessibility/browser review and V2 assurance automation remain post-outreach work.

## 6. Review gate

The branch is ready for the single final independent Showcase Release Candidate review. It must not be described as a completed production OT product or a completed 24-test campaign. Proposed release name: **Showcase V1 Release Candidate 1**; proposed tag after acceptance: `showcase-v1-rc1`.

**V2 Automation Candidate — release evidence assembly.** Repeating clean-checkout setup, workflow execution, hash checks and closeout collation is time-consuming and evidence-heavy. A future assurance assistant could orchestrate these existing checks and assemble the review pack without changing engineering outcomes or reviewer authority.
