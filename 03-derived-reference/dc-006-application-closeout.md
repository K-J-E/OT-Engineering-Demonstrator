---
Status: Application complete — pending independent review
Authority: Derived implementation assurance record only
Owner: Project implementation review process
Updated: 2026-08-12
Change: DC-006 — Controlled Validation Test Determination Methods
---

# DC-006 Machine/Catalogue Application Closeout

## 1. Authorisation, provenance and boundary

The user separately authorised the DC-006 machine/catalogue application from exact accepted reviewed main `48b2ecab818e43ce587bb52593d99519ac01160a`. Branch `agent/dc-006-validation-determination-application` was created from that exact clean, synchronised baseline. Accepted DC-006 technical tip `c19451134c36d13d54f2185a3eaa0f20fcce95f0` and administrative acceptance tip `48b2ecab818e43ce587bb52593d99519ac01160a` were confirmed in history before work began.

The controlling DC-006 change record, Validation Plan v1.3 Section 21, System Architecture v0.4 Section 28, Workflow Design v0.4 Section 29, Demonstrator Design v0.5 Section 38 and referenced accepted DC-004/DC-005 design/application material were read in full. Their accepted document identities remain byte-identical.

This branch changes validation assurance only. It does not alter topology, source attribution, outage/customer calculation, telemetry validity, restoration, DC-003 isolation, Network Configuration content, operational-event meaning, dependencies or authoritative engineering documents. I9 has not resumed and no final catalogue campaign verdict was created.

## 2. Validation Catalogue promotion and preservation

- Active Validation Catalogue v1.2 catalogue SHA-256: `51c6079aeecdb04e11ad1fe9aa3b293e8517fbc7e961c2f1520864d7eada6de3`.
- Active Validation Catalogue v1.2 manifest SHA-256: `a9b7b91e903d1277433a049b99ec9a0324e0b32cd59a3bd8f24899ef86f49754`.
- Preserved historical v1.1 catalogue SHA-256: `28bfe69131c40857c08f175abba42be3eb36514924b6de416b4e72bbefe35865`.
- Preserved historical v1.1 manifest SHA-256: `45cb015f58af1d453be0255cdbbb857c08901877c416e830f26bb2fe6ecf60a3`.
- Preserved historical v1.0 catalogue/manifest SHA-256: `e4b1fb616fb4f0605c19129f18746bfae48278ed35fbb971aac4f690fd32bcc1` / `8bc2f16e6dd475a56a5c5dc3ed52ca46caafc77c08bd858de3f2d748c4dfe714`.

The promoted package retains exactly 24 test IDs, 124 unique requirement IDs, 286 accepted test-to-requirement relationships and 15 operational-event IDs. It contains exactly 35 determination methods: 22 non-composite methods and 13 exact DC-004 constituent-case methods. It contains exactly 214 criteria: 147 direct-test criteria and 67 constituent-case criteria. The two composite parent tests own no direct DC-006 method, context, execution or direct result.

Machine catalogue validation enforces the direct-test requirement unions, exact nine/four constituent sets, case-subset and static parent-union rules, globally unique criterion IDs, exact four-context and ten-operator registries, exact eight controlled surfaces, frozen 45-record ownership set, eight controlled fixtures and exact 15-event registry. The builder derives the promoted records from the accepted Validation Plan Section 21 while checking the accepted DOCX hash and preserving the v1.1 bytes before promotion.

## 3. Applied machine contracts

- Typed immutable contracts cover `DeterminationMethodDefinition`, `CriterionDefinition`, controlled fixtures and registries, source records, frozen role-labelled contexts, criterion findings, reviewer proposal/finalisation, completeness diagnostics and the existing `ExecutedValidationResult` extended with exact method/context/finding provenance.
- Only `SCENARIO_EXECUTION`, `CONTROLLED_FIXTURE_EXECUTION`, `PRESERVED_RECORD_SET` and `ENGINEERING_REVIEW` are permitted. Scenario contexts bind one real run/execution; non-scenario contexts reject fictional run identities.
- Frozen source membership resolves backend-controlled build, evidence-class and run/execution provenance before evaluation. Missing or ambiguous selector evidence produces `NOT_EVALUATED` and `INCOMPLETE`, with no result.
- The generic primitive evaluator creates only criterion-level `SATISFIED` or `NOT_SATISFIED` findings. Complete any-mismatch deterministically produces immutable `FAIL`; complete all-satisfied produces immutable `PASS`. Neither public API nor review UI contracts accept an overall verdict or caller-supplied observed value.
- Reviewer propositions retain fixed catalogue meaning. The backend derives their exact frozen evidence references; an eligible graduate-engineer proposal and a distinct eligible independent-reviewer finalisation are both immutable. The reviewer chooses only the criterion finding; the backend derives the overall result.
- Active v1.2 method/criterion resolution and historical v1.0/v1.1 definition resolution use stored version/hash identities. Completed older executions remain reviewable/exportable; unfinished older work is read-only after promotion.
- Existing DC-004 composite and DC-005 suspension services remain authoritative and unchanged. Missing ordinary evidence remains `INCOMPLETE`; only the accepted DC-005 classifier can produce `BLOCKED-TEST`.
- Evidence export adds exact determination context, result, criterion findings and frozen source records when the source execution owns a DC-006 result. Source-build and later generation-build identities remain separate.
- The frontend remains projection-only. It presents controlled method/criterion coverage distinctly from achieved evidence and does not calculate observations or verdicts. The formal workspace no longer describes the accepted DC-006 path as an undefined comparison; it prevents the legacy finalisation action from bypassing the criterion determination.

## 4. Persistence and migration

Migration `011_dc006_determination.sql` adds:

- `determination_source_records`;
- `determination_contexts` and `determination_context_members`;
- `criterion_findings`;
- `engineering_review_proposals` and `engineering_review_finalisations`; and
- `dc006_executed_validation_results`.

Database checks preserve the four context shapes and reject direct composite-parent contexts/results. Triggers reject source mutation, frozen-context/member substitution, late findings or review proposals after final result, and update/deletion of findings, reviewer records or results. Scenario finalisation atomically binds the result to the existing execution/attempt/evidence history; non-scenario methods create no fictitious scenario record.

## 5. Verification result

- Focused DC-006 catalogue/determination/history/export tests: **19 passed**.
- Complete backend regression: **161 passed**.
- Frontend component tests: **18 passed**.
- Chromium workflows: **3 passed** — formal N0–N5, investigation/correction and Exploration/export.
- Pinned frontend production build: passed.
- Exact method/criterion counts, direct/composite requirement unions, independent 676 criterion-to-requirement assignment fingerprint, exact case sets, context/operator registries, fixtures, surfaces, structural records and event registry: passed.
- Incomplete/no-result, mismatch/FAIL, all-satisfied/PASS, source-class mismatch, four context kinds, zero-fictional-run fixture/review contexts, reviewer actor separation, backend aggregate and database immutability: passed.
- Historical v1.0 and v1.1 resolution after v1.2 promotion, final v1.1 review/export under a later generation build and unfinished-v1.1 read-only treatment: passed.
- Determination-aware evidence ZIP source/generation identity separation: passed.
- Existing DC-004, DC-005, FORMAL/EXPLORATORY, deterministic repeat, package-role and three browser workflows remain covered by the full regression.
- No production test/case/section/configuration-version outcome lookup was introduced. The only explicit composite-parent IDs in migration checks enforce the accepted prohibition on direct parent contexts/results.

These are implementation-conformance results only. They are not Validation Catalogue campaign PASS/FAIL evidence.

## 6. Protected identities

- Requirements Specification v0.4: `ff4d2507e86178214d73c7f2ef19b5aaa9b9821ca1d5e04d8eeeec1ac896e3d4`.
- Engineering Design Brief v0.4: `c65b0db3cf157a1ab1dc64f29cc86c49eda9f909952180abc0bbc20c52e9bfeb`.
- Network Model v0.4: `824a0a03d7bd2d58d7d1be1408bddce75b700aad7d5345bbf49b79e3d029b8c9`.
- Validation Plan/System Architecture/Workflow Design/Demonstrator Design: `626514e3…98f8f0` / `76c768df…db47c` / `aa588610…a479` / `f907d039…ede2` — unchanged accepted DC-006 identities.
- Network Configuration v1.0 manifest/network: `d0243fae…c12d` / `67cb237d…7ab3`.
- Network Configuration v1.1 manifest/network: `e0f16f3a…7662` / `7d65b7fb…3281`.
- Backend and frontend dependency locks: `0c68ce8f…1a64` / `b628f98c…3177`; package versions unchanged. `pyproject.toml` changes only by registering the `dc006` test marker.

## 7. Findings and review gate

No new engineering design question, QA correction ID, dependency request or authoritative-document change was required during application. Catalogue v1.2 did not collide with an existing controlled revision. The application is complete but **pending independent review**; it must not be described as accepted and must not be merged until that review is complete.

The branch tip, clean application build ID and draft PR number are recorded in the publication handoff after the final commit/push. I9 remains stopped and requires separate re-authorisation only after any accepted DC-006 application is incorporated into reviewed main.

**V2 Automation Candidate — criterion evidence assembly.** Creating exact role-labelled source sets, checking 214 criterion bindings and preparing immutable evidence/review records is repetitive and evidence-heavy. A future assurance assistant could propose bindings, detect omissions and assemble review packs while preserving fixed engineering expectations, independent reviewer authority and backend-derived verdicts.
