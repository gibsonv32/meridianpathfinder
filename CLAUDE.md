# Centurion Acquisitor — Memory (Hot Cache)

## Identity
**Agent:** Centurion Acquisitor
**Platform:** FedProcure (Path C — product-first, platform-extractable)
**Domain:** Full-lifecycle federal acquisition automation for TSA/DHS
**Operator:** Vince Gibson
**Phase:** Research & Early Planning (March 2026)

## Fundamental Principles
1. **FedProcure Does Everything Except Inherently Governmental (FAR 7.503).**
   FedProcure produces, formats, populates, routes, and presents complete deliverables — PWS, IGCE, J&A, SSDD, evaluation worksheets, mod packages, closeout files — ready for the human decision-maker.
   The app provides/suggests/formats all data up to the point where government personnel make the independent decision.
   Deterministic controls own: thresholds, approvals, routing, required documents, date triggers, clause logic, record integrity.
   AI generates the actual deliverables with full provenance from the rules engine.
   Humans review, decide, approve, sign — the 9 hard stops below are the ONLY things FedProcure cannot do.
   **Caveat:** Actual coverage depends on source access, template availability, and agency-specific policy constraints.
2. **Propose / Redline / Explain / Accept.**
   Every AI output shows source provenance, confidence, and requires explicit human acceptance before entering the official record.
3. **Accept / Modify / Override.**
   Human always has final authority. Every output is "analysis," never a "decision."
4. **Honest CO Effort.**
   FedProcure targets 15–25% CO effort on a $20M procurement (vs 100% manual). Not "95/5." Time savings measured in hours, not percentages.

## Hard Stops (Tier 3 — AI Legally Prohibited)
| # | Function | Authority |
|---|----------|-----------|
| 1 | Contract signature/award | FAR 1.602-1 (warranted CO only) |
| 2 | Source selection decision | FAR 15.308, 7.503(b)(1) |
| 3 | Obligate government funds | Anti-Deficiency Act, 31 U.S.C. §1501(a) |
| 4 | CO Final Decision on claims | CDA, 41 U.S.C. §7103 |
| 5 | J&A approval | FAR 6.304 |
| 6 | D&F signature | Various FAR parts |
| 7 | Termination for default | FAR 49 |
| 8 | Ratification | HCA or designee |
| 9 | Define strategic requirements | FAR 7.503(b)(1) |
**ACTION:** If user requests any above → REFUSE → redirect to responsible official.

## Threshold Matrix (Oct 2025 — updates annually Oct 1)
**DESIGN: Thresholds MUST live in a policy-as-code rules service with effective dates, NOT in static prose or prompt logic.**
| Value | Docs | Competition | AP Required? |
|-------|------|-------------|-------------|
| ≤$15K micro | Minimal | Not required | No |
| $15K–$25K | Brief/standard | Reasonable effort | No |
| $25K–SAT ($350K) | Standard | Full & open, SAM.gov, SB default | No |
| SAT–$5.5M | Full file | Full & open, SB review | Recommended (but TSA MD 300.25 = Yes) |
| $5.5M–$50M | Full + D&F | Full & open, AP per 7.105 | Yes |
| $50M–$100M | Full + D&F | Full & open, SSAC encouraged | Yes |
| ≥$100M | Full + D&F | Full & open, SSAC required | Yes |

**J&A Approval Ladders (FAR 6.304):**
| ≤$800K → CO | $800K–$15.5M → Competition advocate | $15.5M–$100M → HCA or designee | >$100M → SPE |
**NOTE: At $20M, J&A approval = HCA or designee (NOT competition advocate).**

**Key breakpoints:** SAT $350K | Commercial SAP $9M | Cost data $2.5M | Subcon plan $900K | FAR 16.505 debriefing $7.5M | GAO protest (civilian task order) >$10M

## Terms
| Term | Meaning |
|------|---------|
| **CO** | Contracting Officer (warranted, SF-1402) |
| **COR** | Contracting Officer's Representative |
| **SSA** | Source Selection Authority |
| **SSEB** | Source Selection Evaluation Board |
| **SSAC** | Source Selection Advisory Council (required ≥$100M) |
| **SAT** | Simplified Acquisition Threshold ($350K as of Oct 2025) |
| **AP** | Acquisition Plan |
| **PWS** | Performance Work Statement |
| **SOW** | Statement of Work |
| **SOO** | Statement of Objectives |
| **QASP** | Quality Assurance Surveillance Plan |
| **IGCE** | Independent Government Cost Estimate |
| **J&A** | Justification & Approval (sole source) |
| **LSJ** | Limited Sources Justification (GSA schedule) |
| **D&F** | Determination & Findings |
| **LPTA** | Lowest Price Technically Acceptable |
| **SSDD** | Source Selection Decision Document |
| **PBA** | Performance-Based Acquisition |
| **APFS** | Acquisition Planning & Forecast System (DHS) |
| **ITAR** | IT Acquisition Review (DHS/TSA) |
| **ARB** | Acquisition Review Board |
| **CPARS** | Contractor Performance Assessment Reporting System |
| **CUI** | Controlled Unclassified Information |
| **SSI** | Sensitive Security Information (TSA-specific) |
| **PRISM** | DHS contract writing system (Unison) |
| **J-L-M** | Section J / Section L / Section M traceability |
| **CO Effort** | Target 15–25% CO effort with FedProcure (not "95/5") |
→ Full glossary: memory/glossary.md

## Active Project
| Name | What |
|------|------|
| **FedProcure** | Full-lifecycle acquisition automation platform for TSA/DHS |
| **Smart SOW Builder** | Existing FastAPI/React/PostgreSQL app — Phase 1 foundation |
| **OpenClaw** | Agent runtime/OS layer concept (brainstorming, not committed) |
→ Details: memory/projects/

## Regulatory Stack (bottom to top)
FAR → HSAR (48 CFR Ch. 30) → HSAM → TSA MDs → TSA SOPs
**Rule:** More restrictive layer always wins.

## Key Legal Corrections (from CO Stress Test, Mar 2026)
- SAT = $350K (not $250K) as of Oct 2025
- FAR 6.302-1 follow-on = DoD/NASA/Coast Guard ONLY (not civilian bridge authority)
- FAR 6.302-2 urgency ≠ delayed recompete from poor planning
- J&A ≠ D&F — different instruments, different purposes
- DHS 150-day limit = disaster/terrorism rule ONLY
- CPARS has no public API (manual entry only)
- GAO sustain rate FY2025 = 14%
- Civilian task order GAO protest jurisdiction = >$10M (not $7.5M)

## Memory Tiers
| Tier | What | Where |
|------|------|-------|
| **T1** | Constitutional rules (always loaded) | memory/tier1/ |
| **T2** | Domain packs (loaded per task) | memory/tier2/ |
| **T3** | Reference index (RAG retrieval) | memory/tier3/ |
→ Playbook: Centurion_Acquisitor_Memory_Architecture_and_Playbook.md

## Three-Tier Automation Taxonomy
| Tier | What | Examples |
|------|------|---------|
| **1. Deterministic** (build first) | Rules, validation, routing, date math | Thresholds, approval chains, posting deadlines, clause insertion, completeness checks |
| **2. AI/LLM-Appropriate** (CO-reviewed) | Comparison, summarization, redlining, narrative drafting | SOW→PWS conversion, IGCE narrative, Section L/M alignment, evaluation summary |
| **3. Human-Only** (inherently governmental) | Decisions per FAR 7.503(b) | Award, source selection, fund obligation, J&A/D&F approval, termination |

## MVP Priority (Rules-First)
1. CO dashboard / work queues (blocked, expiring, pending decisions)
2. PR package completeness validator
3. Policy-as-code thresholds & routing engine
4. Controlled drafting workspace (PWS/IGCE/L-M with propose/redline/explain)
5. Evidence lineage ledger (requirement → CLIN → L → M → evaluator → SSDD → QASP → CPARS)
6. Secure evaluation workspace (role-based, immutable logs)
7. Post-award basics (option tracking, mod routing, CPARS alerts)

## Current Phase Capabilities
1. Regulatory cross-reference engine
2. Research validation (cross-check new findings vs synthesis)
3. TSA decision tree simulation (Q1–Q117)
4. Gap identification in synthesis
5. Document structure management (~2,810 lines, 36 sections)

## Phase 2 Capabilities (commit 4180a9d, 2026-03-20)
- Protest risk scoring (10-factor GAO engine, mitigations, authority citations)
- Solicitation assembly (UCF section mapping, J-L-M traceability, FAR/HSAR clause selection)
- PIL pricing analysis (15 DHS PIL benchmark rates, fuzzy matching, variance detection)
- Protected evaluation workspace (RBAC: 5 roles, 7 phases, immutable audit log, Tier 3 hard stop at decision)
- DocumentService extracted from AuditService (propose/redline/explain model foundation)

## Policy-as-Code Engine (commit f266dd2, 2026-03-20)
- **PolicyService** orchestrator: single entry point replacing hardcoded if/else
- **Q-code DAG**: 17 nodes, 20 edges, real traversal with audit trace (not cosmetic)
- **Corrected D-code registry**: 17 codes (D102=PWS, D115=COR, D103=CLINs, D109=Special Reqs)
- **FAR 5.203 posting matrix**: 6 rules (micro/below-SAT/sole-source/competitive/combined/emergency)
- **Deterministic clause selection**: 14 rules (FAR Part 12, 37, HSAR, IT, cost data)
- **J&A approval ladder**: 4 tiers per FAR 6.304 with effective dates
- **12 threshold seeds**: micro, SAT, subcon, cost data, AP, commercial SAP, GAO protest, debriefing, SSAC encouraged, SSAC required, ESAR, CAS
- All rules carry effective_date/expiration_date for Oct 1 annual updates
- **124/125 tests passing** (87 protest/entity + 11 Q-code + 40 policy engine + 8 migration + 10 completeness validator + others — 1 pre-existing SAM.gov test unrelated)

## SAM.gov Data Pipeline (2026-03-20/21)
- **45,635 opportunities** ingested (historical backfill 2014–2026)
- **470 enriched** with full description text, POC, and attachment links
- **62 cross-matched** protests↔opportunities via solicitation_number JOIN
- **4 cross-reference endpoints**: by-solicitation, enrich-protests, analytics, protest-risk
- **Daily 6 AM cron** for SAM.gov + Tango incremental ingest
- **Description enrichment script** (enrich_descriptions.py): priority mode DHS→cross-matched→all

## PolicyService Migration (deployed, commit dea3f7a, 2026-03-21)
- **rules_migration.py**: schemas, singleton, conversion functions (to_enrichment, to_v2_response)
- **rules_router_patch.py**: replaces rules.py — V1 backward-compat + enrichment, V2 full PolicyService
- **test_rules_migration.py**: 8 integration tests (V1 compat, enrichment, V2 output, sole source, micro, commercial IT, thresholds)
- **deploy_policy_migration.sh**: automated deployment with backup, smoke tests, and rollback
- STATUS: **Deployed and verified** — 139/139 tests passing (0.89s)
- V1 `/api/v1/rules/evaluate` returns original fields + `policy_evaluation` enrichment
- V2 `/api/v1/rules/evaluate/v2` returns full PolicyService output (Q-code trace, clauses, thresholds, J&A ladder)

## Phase 3: CO Dashboard Frontend (commit 6d7fc11, 2026-03-21)
- **PolicyCard component**: expandable Q-code trace (17 nodes), 9 applicable clauses, posting requirements, J&A ladder, 12 thresholds with triggered/below indicators, D-code list, authority chain provenance
- **ProtestRiskCard component**: overall risk score bar, 10-factor breakdown with mitigations and GAO authorities, recommendations
- **CompletenessCard component**: progress bar, status counts (satisfied/pending/missing/blocking), expandable document list with filter bar (All/Blocking/Missing/Pending/Satisfied), responsible party + UCF section + FAR authority per doc, blocker badges
- **CreatePackageForm component**: intake form with live "Preview Policy" (hits V2 + protest-risk + completeness simultaneously before package creation), document preview chips with blocker highlighting
- **Enhanced PackageDetail**: tabbed view (Overview/Completeness/Policy/Risk/Documents), auto-fetches completeness on load, re-fetches on document status change
- **Enhanced WorkQueue**: status filter bar (All/Blocked/Action/Ready) with counts
- **App navigation**: 3-view layout (Work Queue / New Package / Analytics), header badges for blocked/action/ready, system status panel
- **api.js normalizer**: `normalizePolicyResponse()` maps V2 flat response → component-friendly shapes (qcode rename, posting/J&A object assembly, threshold dict→array with triggered flags)
- **CORS updated**: backend allows ports 3000–3002 + LAN IP
- **Frontend live**: Vite dev server on port 3002, production build passes (175 KB gzipped)
- **10 frontend files, ~1,600 lines total**
- STATUS: **Deployed and verified** — Vite build clean (183 KB / 55 KB gzipped), 124/125 backend tests passing

## Phase 4: Q-Code Expansion + Completeness Validator (2026-03-21)

### Q-Code Decision Tree Expansion
- **47 Q-code nodes** (up from 17): Q001–Q047
- **57 edges** (up from 20)
- **28 D-code definitions** (up from 17): D101–D128
- New D-codes: D118 (Past Performance Eval Plan), D119 (OCI Mitigation), D120 (Security Requirements), D121 (Option Period Justification), D122 (Wage Determination), D123 (IDIQ Min/Max D&F), D124 (Fair Opportunity), D125 (Contractor Transition), D126 (Gov Property Inventory), D127 (Key Personnel), D128 (TSA Badge/Access)
- New Q-code categories: contract type selection (Q018–Q022), option periods (Q023–Q024), labor standards (Q025–Q027), security (Q028–Q031), past performance/evaluation (Q032–Q035), OCI (Q036–Q037), property/transition (Q038–Q040), COR/oversight (Q041–Q043), TSA-specific (Q044–Q047)
- Terminal node changed: Q017 → Q047
- Critical fix: `_should_trigger` and `_follow_edge` inject safe defaults before `eval()` to prevent NameError → fail-open

### PR Package Completeness Validator (MVP Priority #2)
- **Endpoint**: `POST /api/v1/phase2/completeness/validate`
- **Module**: `backend/phase2/completeness_validator.py`
- Takes acquisition params + list of documents in hand
- Runs PolicyService to determine required D-codes
- Returns gap analysis: missing/pending/satisfied per document
- `BLOCKING_DCODES` set: D101, D102, D103, D104, D106, D108, D115, D120, D131, D132, D136
- `RESPONSIBLE_PARTY` mapping for all 45 D-codes (CO, COR, Security Officer, etc.)
- Response includes: `package_ready` bool, `completeness_pct`, blocking/non-blocking classification, responsible parties, FAR authorities, UCF sections, actionable notes
- **10 dedicated tests** covering: standard acquisition, micro-purchase, sole source J&A, partial/full satisfaction, blocking classification, responsible party mapping, schema completeness, notes content
- STATUS: **Deployed and verified** — 124/125 tests passing (1 pre-existing SAM.gov test unrelated)

## Phase 5: Workflow Gate Engine (2026-03-21)

### WorkflowGateEngine (Tier 1 — Deterministic)
- **8 acquisition lifecycle phases**: Intake → Requirements → Solicitation Prep → Solicitation → Evaluation → Award → Post-Award → Closeout
- **Phase gate requirements**: per-phase D-code requirements with required status levels (pending/satisfied)
- **Completeness thresholds**: Solicitation Prep ≥15%, Solicitation ≥60%, Evaluation ≥75%, Award/Post-Award/Closeout = 100%
- **Non-waivable requirements**: D120 (Security) at Solicitation gate cannot be overridden
- **CO Override**: accept/modify/override pattern — CO can force-advance waivable gates with written rationale (logged)
- **Status hierarchy**: missing < pending/draft < satisfied — pending meets pending requirements
- **Phase ordering enforced**: no backward movement, no phase skipping
- **4 API endpoints**:
  - `POST /api/v1/phase2/workflow/check-gate` — check if package can advance
  - `POST /api/v1/phase2/workflow/advance` — advance phase (with optional override)
  - `GET /api/v1/phase2/workflow/roadmap/{package_id}` — full lifecycle roadmap with gate status
  - `GET /api/v1/phase2/workflow/phases` — list all phases in order

### PhaseRoadmap Frontend Component
- **Visual timeline**: 8-phase vertical roadmap with color-coded status dots (completed/current/ready/blocked/future)
- **Gate check display**: passed/failed requirements with D-code, authority, and status detail
- **Advance button**: one-click advance when gate is clear
- **CO Override UI**: expandable rationale textarea, submit/cancel, disabled when non-waivable
- **Live refresh**: re-fetches roadmap + gate check after document status changes or phase advancement
- **PackageDetail integration**: new Workflow tab (6 tabs total), overview shows roadmap + completeness side by side

### Test Coverage
- **14 dedicated tests**: gate pass, gate block, backward movement, phase skipping, override with/without rationale, non-waivable override, completeness threshold, status hierarchy (3 tests), roadmap generation, next phase lookup, unknown phase handling
- STATUS: **Deployed and verified** — 14/14 workflow tests + 117+ across other suites, Vite build clean (191 KB / 56 KB gzipped)

## Phase 6: Seed Data Migration + Interactive Document Status (2026-03-21)

### Seed Data Migration
- **Script**: `migrate_phases.py` (bulk UPDATE approach for async reliability)
- **Phase mapping**: PR Validation→Intake, CO Review→Requirements, Acquisition Planning→Solicitation Prep, Routing→Solicitation, Executive Review→Evaluation
- **7 demo packages migrated** — all now use valid 8-phase lifecycle names
- Roadmap, gate check, and advance endpoints confirmed working with migrated data
- **demo-004 advanced** Intake→Requirements successfully in end-to-end test

### Interactive Document Status Toggling
- **CompletenessCard v2**: accepts optional `onStatusChange` prop
- Click any status badge to cycle: missing → pending → satisfied
- Loading state per document (`updatingDcode`) prevents double-clicks
- Hint text shown when interactive mode active
- Falls back to read-only badges when `onStatusChange` not provided
- **PackageDetail v2**: passes `handleStatusChange` to both CompletenessCard (overview + completeness tabs) and DocumentList (documents tab)
- Extracted `buildParams()` and `buildDocsInHand()` helpers to reduce duplication
- Status change triggers automatic refresh of: completeness validator, phase roadmap, gate check
- **Vite build clean**: 191 KB / 57 KB gzipped
- STATUS: **Deployed and verified** — 138/139 tests passing (1 pre-existing SAM.gov test unrelated)

## Phase 7: Q-Code Tree Full Expansion (2026-03-21)

### Q-Code Decision Tree: 117 Nodes
- **117 Q-code nodes** (up from 47): Q001–Q117
- **129 edges** (up from 57)
- **45 D-code definitions** (up from 28): D101–D145
- **7 terminal nodes** for different lifecycle branches: Q047 (main), Q057 (mods), Q067 (award), Q087 (disputes), Q097 (special programs), Q107 (DHS/TSA), Q117 (closeout)
- **12 branch entry points**: Q001 (main), Q020, Q048 (mods), Q054 (option exercise), Q058 (award), Q068 (post-award), Q078 (protests), Q080/Q081 (protest venues), Q088 (special programs), Q098 (DHS/TSA), Q108 (closeout)

### New Q-Code Categories (Q048–Q117)
- **Contract Modifications** (Q048–Q057): bilateral/unilateral, scope changes, REA, change orders, option exercises
- **Award Phase** (Q058–Q067): pre-award survey, responsibility determination, cost/price analysis, negotiations, SSDD, award notification, debriefing, award synopsis
- **Post-Award Administration** (Q068–Q077): delivery monitoring, invoice review, CPARS interim, pending mods, option windows, COR reports, performance issues, cure notice, POP ending
- **Protest & Disputes** (Q078–Q087): GAO/agency/COFC protest venues, automatic stay, corrective action, ADR, CDA claims, claim certification
- **Special Acquisition Programs** (Q088–Q097): 8(a), HUBZone, SDVOSB, WOSB, AbilityOne, GSA Schedule, BPA, SBA review, LSJ
- **DHS/TSA Specific** (Q098–Q107): EAGLE II, FirstSource, PACTS III, deep ITAR review, ISSO, FedRAMP, HSAR flow-down, Category Management, FITARA
- **Contract Closeout** (Q108–Q117): POP completion, final delivery, final payment, property disposition, ULO de-obligation, release of claims, final CPARS, records retention, closeout checklist

### New D-Codes (D129–D145)
- D129 (Modification Request Package), D130 (Pre-Award Survey), D131 (Responsibility Determination), D132 (Cost/Price Analysis Report), D133 (Negotiation Memorandum), D134 (Award Notification Letters), D135 (Debriefing Documentation), D136 (SSDD), D137 (Protest Response Package), D138 (Corrective Action Plan), D139 (8(a) Offering Letter), D140 (GSA Schedule Order), D141 (BPA Documentation), D142 (FedRAMP Authorization), D143 (Closeout Checklist), D144 (Final CPARS Evaluation), D145 (Release of Claims)

### Updated Completeness Validator
- `RESPONSIBLE_PARTY` mapping expanded to all 45 D-codes
- `BLOCKING_DCODES` expanded: added D131 (Responsibility), D132 (Cost/Price Analysis), D136 (SSDD)
- $20M IT services traversal now triggers 20 required D-codes (up from ~12)

### Test Coverage
- **22 dedicated tests**: 8 structure (node/edge/dcode counts, reachability, terminal nodes, duplicates), 7 traversal paths (canonical $20M, micro, sole source, vendor on-site, IT, services, no-infinite-loop), 5 new D-code properties, 2 completeness integration
- STATUS: **Deployed and verified** — 159/160 tests passing (1 pre-existing SAM.gov test unrelated)

## Phase 8: Branch Wiring — Phase-to-Q-Code Mapping (2026-03-21)

### PHASE_BRANCH_MAP
- Maps each of the 8 acquisition lifecycle phases to Q-code branch entry points traversed IN ADDITION to main Q001 flow
- Early phases (Intake through Solicitation): no branches, main flow only
- Evaluation/Award: Q058 (award prep — pre-award survey, responsibility, cost/price)
- Post-Award: Q068 (post-award admin) + Q098 (DHS/TSA specific)
- Closeout: Q108 (closeout branch)

### CONDITIONAL_BRANCH_MAP
- Event-driven branches triggered by acquisition params, not phase:
  - `is_modification` → Q048 (contract modifications)
  - `is_option_exercise` → Q054 (option exercise)
  - `has_protest` → Q078 (protest handling)
  - `special_program` → Q088 (8(a), HUBZone, etc.)
  - `dhs_tsa` → Q098 (DHS/TSA-specific reviews)

### traverse_for_phase() Method
- Two-layer traversal: main Q001 tree runs first, then phase-specific branches
- Branch traversal **force-triggers ALL D-codes** on visited nodes (unlike main tree which checks conditions)
- Rationale: entering a branch implies the lifecycle event occurred — D-codes with `condition="False"` (e.g., D143 Closeout Checklist, D145 Release of Claims) must still fire
- `_traverse_from(start_code, params)` handles arbitrary entry point traversal with cycle detection

### Updated Signatures
- `PolicyService.evaluate(params, as_of=None, phase=None)` — accepts optional phase
- `ValidateCompletenessRequest.phase` — optional field for branch-aware D-code resolution
- `CompletenessValidator.validate()` forwards phase to PolicyService
- `_build_params_from_detail(detail)` helper in router for gate check re-evaluation

### Backward Compatibility
- `traverse_for_phase(params, phase=None)` returns identical results to `traverse(params)`
- All existing endpoints work without phase parameter
- Gate check re-evaluates required D-codes with phase awareness when available

### Test Coverage
- **29 dedicated tests** across 6 classes:
  - TestPhaseBranchMap (8): structure validation, all phases have entries, branch Q-codes exist in QCODE_NODES
  - TestTraverseForPhase (7): no-phase matches original, Intake matches original, Award/Post-Award/Closeout add correct D-codes, Award evaluates more nodes
  - TestConditionalBranches (3): modification/protest/option exercise flags enter correct branches
  - TestPolicyServicePhaseAware (4): evaluate with/without phase, Award/Closeout add correct D-codes, micro-purchase behavior
  - TestCompletenessPhaseAware (4): phase field accepted, backward compat, Closeout completeness, phase-aware has more docs
  - TestNoRegression (3): main tree terminal unchanged, micro-purchase unchanged, D-code count unchanged
- STATUS: **Deployed and verified** — 189/190 tests passing (1 pre-existing SAM.gov test unrelated, 0 regressions)

## NOT Yet Capable Of
- Document generation with full propose/redline/explain UI
- External system queries beyond SAM.gov (FPDS dead, CPARS no API)
- Re-run description enrichment for cross-matched protests (SAM.gov rate limit reset needed)
- Frontend component for V1↔V2 comparison toggle
