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

## TSA C&P Review and Approval Thresholds (February 2026)
**Source:** TSA C&P Review and Approval Thresholds chart, February 2026 (2 pages)
**Legend:** R = Review, S = Sign, A = Approve, C = Receive Approved Copy
**Roles:** PM = Program Manager, CO = Contracting Officer, SB = Small Business, BC = Branch Chief, DD = Division Director, CA = Competition Advocate, APD = Acquisition Policy Division, DAA = Deputy Assistant Administrator, HCA = Head of Contracting Activity, DHS CPO = DHS Chief Procurement Officer, COCO = Chief of Contracting Office

### Acquisition Plans
| Value | Contract Type | PM | CO | SB | BC | DD | CA | DAA | HCA | DHS CPO |
|-------|--------------|----|----|----|----|----|----|-----|-----|---------|
| SAT–<$2.5M | OTFFP | S | S | | A | | | | | |
| $2.5M–<$10M | OTFFP | S | S | S | A | | | | | |
| $10M–<$15M | OTFFP | S | S | S | R | A | | | | |
| $15M–<$50M | OTFFP | S | S | S | R | R | R | A | | |
| $50M–<$500M | OTFFP | S | S | S | R | R | R | R | A | |
| $500M+ | FFP or OTFFP | S | S | S | R | R | R | R | R | A |
**CRITICAL: FFP acquisitions under $50M do NOT require a formal Acquisition Plan. Only OTFFP triggers AP below $50M.**

### Procurement Strategy Review & Solicitation Review (SR)
| Value | CO | BC | DD | APD | DAA | HCA |
|-------|----|----|----|----|-----|-----|
| Up to $SAT | A (SR only, comment disposition 1 level above CO) | | | | | |
| >$SAT–$10M | R | R | A | C | | |
| $10M–<$50M | R | R | R | R/C | A | |
| $50M+ | R | R | R | R/C | R | A |

### Business Clearance Memorandum (BCM)
| Value | CO | BC | DD | DAA | HCA |
|-------|----|----|----|----|-----|
| <$500K | A | | | | |
| $500K–<$5M | R | A | | | |
| $5M–<$20M | R | R | A | | |
| $20M–<$50M | R | R | R | A | |
| $50M+ | R | R | R | R | A |
**Rule: "All BCMs over $500,000 must be reviewed and approved at one level above the CO, at a minimum."**

### Source Selection Authority (SSA) Appointment
| Value | CO | BC | DD | DAA | HCA |
|-------|----|----|----|----|-----|
| <$2.5M | A | | | | |
| $2.5M–<$5M | | A | | | |
| $5M–<$20M | | | A | | |
| $20M–<$50M | | | | A | |
| $50M+ | | | | | A |

### J&A Approval (FAR Parts 6, 13) / LSJ (FAR Part 8) / Exclusion of Fair Opportunity (FAR Part 16)
| Value | CO | DD | CA | DAA | HCA | DHS CPO |
|-------|----|----|----|----|-----|---------|
| $2K–<$250K (construction) / $2.5K–<$250K (services) / $10K–<$250K (supplies) | A | | | | | |
| >$250K–$900K | R | R | A | | | |
| $900K–<$20M | R | R | R | R | A | |
| $20M+ | R | R | R | R | R | A |

### Determinations & Findings (D&F)
| Type | CO | BC | DD | CA | DAA | HCA | DHS CPO |
|------|----|----|----|----|-----|-----|---------|
| Contract Type Authority (T&M/LH for commercial, <3 yrs) | A | R | R | | | | |
| Contract Type Authority (T&M/LH, 3+ yrs) | S | R | R | R | R | A | |
| Incentive (including award fee) | S | R | R | S | R | R | A |
| Single Award IDIQ / Single Award BPA $150M+ | S | R | R | A | | | |
| Use of FAR 52.217-8 when evaluated at time of award | S | R | R | | | | |
| Unusual and Compelling Urgency | R | R | R | R | R | A | A |
| Public Interest | R | R | R | R | R | R | A |
| 8(a) Sole Source Set Aside > $/ 30M (See FAR 19.808-1) | S | R | R | R | R | R | A |
| Response to natural disaster / terrorism, POP >150 days and >$75M | R | R | | | R | R | A |
| Use of FAR 52.217-8 when NOT evaluated at time of award | R | R | R | | | | |

### Contract Award and Mod File Review/Approval
At a level above CO, using IPM "Contents of Contract Files …" checklists.

### Mandatory DHS Strategic Sourcing Contracts
- Memo authorizing exceptions to use of DHS strategic sourcing contracts: CO=R, BC=R, DD=R, DAA=A
- Waiver to the use of DHS strategic sourcing contracts: CO=R, BC=R, DD=R, DAA=R, HCA=A, DHS CPO=A

### Letter Contracts / Undefinitized Contract Actions
- $1M and below: CO=R, BC=R, DD=R, COCO=A
- >$1M: CO=R, BC=R, DD=R, COCO=R, HCA=A, Legal=A
- Pre-contract costs per FAR 31: CO=R, BC=R, DD=R, COCO=R, HCA=A, Legal=R, DHS CPO=A

## TSA Business Clearance Memorandum (BCM) — Template Structure
**Source:** 11 actual TSA BCMs (Streamlined, Pre-Competitive, Pre/Post Sole Source, OTA variants)

### BCM Types
1. **Streamlined Acquisition** — used for task orders under existing vehicles (OASIS, EAGLE, etc.)
2. **Pre-BCM Competitive Acquisition** — pre-negotiation clearance for full & open competitions
3. **Pre/Post Sole Source Acquisition** — combined pre-negotiation + post-negotiation for sole source
4. **Pre/Post Competitive Acquisition** — combined pre-negotiation + post-negotiation for competed awards
5. **OTA Streamlined** — Other Transaction Authority procurements

### Standard BCM Sections (A through H)
| Section | Title | Content |
|---------|-------|---------|
| A | Acquisition Information | Contract #, PRISM #, solicitation #, NAICS, PSC, contract type, period of performance, estimated value, obligated amount, contractor name, description of requirement |
| B | Business Clearance Information | Pre-Negotiation Objectives / Post-Negotiation Summary / Authority to Contract — includes evaluation summary, price analysis method, determination of fair & reasonable |
| C | Recommendation Summary | Unconditional Approval / Conditional Approval — the actual approval signatures |
| D | Review and Approvals | Signature chain (CS → CO → BC → DD → DAA → HCA as applicable per threshold) |
| E | Analysis | Key Highlights timeline (actual acquisition lifecycle milestones), attachments list |
| F | Proposal Summary | Evaluation factor ratings per offeror, strengths/weaknesses/deficiencies, price comparison |
| G | Pre/Post-Negotiation Compliance/Determinations | **27-item compliance checklist** with FAR/HSAM citations |
| H | Pre/Post-Negotiation Analysis | Detailed pricing analysis, CLIN-by-CLIN comparison, IGCE vs proposed, labor rate analysis |

### Section G — Compliance Checklist (27 Items)
Extracted from actual TSA BCMs. Each item is Yes/No/N-A with FAR/HSAM authority citation:
1. Inherently governmental analysis (FAR 7.503)
2. Acquisition Plan required/approved (FAR 7.102, HSAM 3007.1)
3. Market research conducted (FAR 10.001)
4. J&A required/approved (FAR 6.303/6.304)
5. Competition requirements met (FAR Part 6)
6. Small business review completed (FAR 19, DHS Form 700-22)
7. Subcontracting plan required/reviewed (FAR 19.702)
8. ITAR completed (HSAM 3039.1)
9. Service Contract Labor Standards applicable (FAR 22.10)
10. Wage determination obtained (FAR 22.10)
11. Non-personal services determination (FAR 37.104)
12. Performance-based requirements (FAR 37.102, HSAM 3037.1)
13. Section 508 accessibility compliance (FAR 39.2)
14. Cost/pricing data required (FAR 15.403)
15. Cost/pricing data exception applies (FAR 15.403-1)
16. Price analysis method documented (FAR 15.404)
17. IGCE prepared and compared (HSAM)
18. Organizational Conflict of Interest reviewed (FAR 9.5)
19. Responsibility determination made (FAR 9.1)
20. FAPIIS checked (FAR 9.104-6)
21. SAM.gov registration verified
22. Security requirements identified (HSAR 3052.204-71)
23. Government property addressed (FAR 45)
24. Option periods justified (FAR 17.207)
25. COR nomination received
26. QASP prepared
27. Debriefing requirements identified (FAR 15.506)

### Key Highlights Timeline (Acquisition Lifecycle from BCMs)
Standard milestones tracked in BCM Section E:
PSR → Inherently Governmental Analysis → PSR Finding Disposition → ITAR → SRB → SRB Finding Disposition → Solicitation Review (Chief Counsel) → Appendix G → Solicitation Release → Amendment(s) → Proposal Receipt → Oral Presentations (if applicable) → Technical/Price Evaluation → Chief Counsel Review → Award Recommendation Memo → SSA Decision Memo

### BCM Approval Chains (Confirmed from Actual Signatures)
| Value | Chain |
|-------|-------|
| <$500K | CS → CO approves |
| $500K–<$5M | CS → CO → BC approves |
| $5M–<$20M | CS → CO → BC → DD approves |
| $20M–<$50M | CS → CO → BC → DD → DAA approves |
| $50M+ | CS → CO → BC → DD → DAA → HCA approves |

### TSA PR Package Components (from SharePoint)
Required documents for a complete PR Package submission:
1. DHS Form 700-20 (Purchase Request)
2. TSA Form 5000 (Clearance Sheet)
3. Appendix G (Requirements Checklist)
4. Funding document
5. COR nomination letter
6. Market research report
7. IGCE
8. PWS/SOW/SOO
9. J&A (if sole source)
10. DHS Form 700-22 (Small Business Review)
11. ITAR documentation
12. Security requirements
13. Quality Assurance Surveillance Plan (QASP)
14. Past performance evaluation plan
15. Source selection plan (if applicable)

### TSA Solicitation Review (SR) Checklist Structure
**Source:** Actual signed SR Checklist (IPMSS PEO TORQ, Aug 2025), IGPM 0400.15
**Form type:** Internal C&P Use Only

| Section | Title | Content |
|---------|-------|---------|
| I | Review Process Information | CO, DD, PR#, solicitation#, value, contract type, SB set-aside, commercial, pre-solicitation synopsis date, estimated sol release date. **Division shall complete.** |
| II | Solicitation Review Elements | 7-item checklist: (1) PSR consistency, (2) Source Selection Plan approved, (3) SCA applicable, (4) PBA measures, (5) Past Performance as eval factor per FAR 15.304(c), (6) CO identified as POC per FAR 15.201(f)/15.303(c)(1), (7) Appendix G provisions/clauses included |
| III | APD Review/Comments | 9-item assessment: (1) PSR consistency, (2) PBA measures, (3) Provisions/clauses current, (4) SSP consistent with Section M, (5) Barriers to competition, (6) Due dates consistent in L, (7) Section L completeness for eval, (8) Other concerns, (9) Paper SR recommended? |
| IV | Board Results | Type of Board: Full or Paper. Attendees list. |
| V | DD Adjudication | "All comments have been adjudicated to my satisfaction." DD digital signature. **This serves as final approval at all DD-approval thresholds.** |
| VI | APD Verification | "All comments have been adjudicated and action items resolved." APD digital signature. |
| VII | Final C&P AA/DAA Approval | Unconditional Approval (no further action) OR Conditional (resubmit via APD after disposition). Checkboxes: HCA/AA or DAA. |

### BCM Waiver Process (from BCM May 2022 APD Guidance)
**Governing IGPM:** IGPM 0103.19 (Business Clearance Memorandum, Dec 2021)
**Pre-BCM purpose differs by competition type:**
- **Competitive:** Request authority to enter discussions. Provides history from PSR, requirement, evaluation criteria, solicitation, amendments, proposal receipt, evaluation, and need to conduct discussions. **You cannot award on initial offers with a Pre-BCM — that requires a Pre/Post.**
- **Sole Source:** Demonstrates CS/CO readiness to enter negotiations. Discusses requirement, contractor proposal, IGCE, pre-negotiation position, areas to negotiate.
**BCM Waiver process (competitive):**
1. Evaluate proposals/quotes. Are discussions required?
   - YES → Need Pre-BCM approved to enter discussions
   - NO → Can prepare Pre/Post BCM (no waiver required)
2. If discussions needed but no Pre was prepared: EITHER prepare a Pre to request approval OR prepare a Waiver to enter discussions and document in Pre/Post
**Waiver approval:** One level above normal BCM approval authority, up to HCA. IGPM 0103 governs.
**Key BCM best practices:**
- Plan BCM content during procurement planning stage (before soliciting)
- BCM should stand alone and tell the entire story — use tables, show math in attachments
- Do not submit entire contract file to HCA; at DD and below, submit supporting file for review
- Compliances matter — do the research, don't just click and forget
- For competitive: align BCM narrative to source selection steps and analysis results
- For sole source: negotiate — the vendor rarely gives the most fair and reasonable price initially

### J&A/LSJ Approval Authorities (TSA-Specific, from Competition June 2022)
**Note:** These TSA-specific thresholds differ from generic FAR 6.304. Feb 2026 C&P thresholds supersede for current use.
| Action Value | Reviewer | Approval |
|-------------|----------|----------|
| $1–$250K | Contract Specialist | CO (concurrence one level above) |
| >$250K–$750K | CO, BC, DD | DD |
| >$750K–$15M | CO, BC, DD | Competition Advocate |
| $15M–$75M | CO, BC, DD, Comp Advocate, Deputy HCA | HCA |
| >$75M | CO, BC, DD, Comp Advocate, Deputy HCA, HCA | DHS Chief Procurement Officer |
| Urgent & Compelling / Bridge | CO, BC, DD, Comp Advocate, Deputy HCA | HCA |
**HSAM 3004.7003:** All justifications >$500K reviewed for legal sufficiency (approval by legal not required).
**Types of Justifications:** LSJ (FAR Part 8 simplified/Part 13), Exception to Fair Opportunity (FAR Part 16.5 multiple award), J&A (FAR Part 6 above SAT), D&F for 8(a) direct <$25M (Appendix G)

### DHS Form 700-22 (Small Business Review) Details
**Required for:** All acquisitions over $100,000
**Must be completed:** Prior to synopsis or solicitation release
**23 items in 3 sections:**
- Items 1-8: Request (requisitioner, office, PR#, CS, CO, description, value, POP)
- Items 9-19: Strategy & Proposed Procurement Method
  - Item 13: First Consideration (socioeconomic set-aside: 8(a), HUBZone, SDVOSB, Total/Partial SB)
  - Item 14: Second Consideration (if set-aside ruled out → full & open)
  - Item 17: Substantial Bundling Review ($2M+ open market)
  - Items 18-19: Pre-existing contract vehicles ($2M+)
- Items 20-23: Submission and Review Signatures
  - (20) CO concurrence/non-concurrence
  - (21) SB Specialist concurrence/non-concurrence
  - (22) CO response to SBS non-concurrence
  - (23) SBA PCR concurrence ($2M+ unrestricted, including sole source to other than SB)
**Turnaround:** SBS = 2 business days, SBA PCR = 2 business days
**Completed form placed in solicitation file.**

### DHS Contract File Content Checklist (CG-4788, Preaward)
43-item preaward contract file checklist (filed consecutively, highest number on top):
1. PR + Amendments + Supporting Docs (IGCE, specs)
2. Acquisition Plan/Milestone Plan
3. A-E Board Report
4. SB Review Form (DHS 700-22) + 8(a) correspondence
5. Approved AIS Proposal (IT acquisitions)
6. Synopsis & Presolicitation Notices
7. AAP Submission
8. Source List/Planholder's List/Solicitation Requests
9. Justification for Other Than Full & Open Competition
10. Determinations/Approvals (a-g: Liquidated Damages, Nonpersonal Services, Options Justification, Options Exercise, Contract Type, Warranty, Other D&Fs)
11. SF 98 & DOL Wage Determination
12. Reserved
13. Solicitation, Amendments, & Reviews
14. Record of Pre-proposal/Pre-bid Conference
15. "No Proposal/Bid" Correspondence
16. Abstract
17. Bid Bond and Clearance
18. Record of Late Proposals/Bids
19. Technical Evaluation Memorandum (Evaluation of Proposals/Bids + Other Documents)
20. Competitive Range Determination
21. Unsuccessful Proposals/Bids + All Correspondence (segregated by contractor)
22. Successful Proposal/Bid
23. All Correspondence with Successful Offeror Prior to Execution
24. Successful Offeror's Price or Cost Data (a. In Proposal, b. Separate Papers)
25. Audit Reports (a. Price Analysis Staff, b. Field/DCAA)
26. Weighted Guidelines Profit/Fee Objective (DHS Form 700-17)
27. Certificate of Current Cost or Pricing Data (a. Separate Papers, b. Attached)
28. Final Technical Rating after Negotiations
29. Determination of Prospective Contractor Responsibility (DHS Form 700-12) (a. Pre-Award Survey, b. SBA Certificate of Competency, c. CO's Determination)
30. Post-Negotiation Memorandum/CO's Determination of Price Reasonableness
31. CO Revalidation of Requirement (if >1 year from PR date)
32. Security Requirements (a. Contract Security Classification Spec DD 254, b. Security Clearance Info)
33. Subcontracting Plan Approval Correspondence
34. Equal Opportunity Clearance
35. Protests before Award (a. To Agency, b. To GAO)
36. Reserved
37. Correspondence Relating to Execution
38. Notice to Unsuccessful Offerors/Bidders
39. Pre-Award Review and Approval of Award (Local + CGHQ/DOT reviews)
40. Contract Award Notification (DHS Form 2140-01)
41. Printout of Valid FPDS Record
42. Award Notice (Federal Business Opportunity/Fed Biz Ops)
43. Miscellaneous Documentation + COTR Delegations + Debriefings

### TSA Effective Policy Catalog (June 2023)
**Source:** C&P Acquisition Policy Division Effective Guidance List

#### Management Directives (MDs)
| MD | Title | Effective Date |
|----|-------|---------------|
| 300.2 | Ratification of Unauthorized Commitments | May 6, 2019 |
| 300.9 | Certification, Appointment, and Duties of CORs | April 1, 2019 |
| 300.14 | Small Business Program | December 8, 2022 |
| 300.16 | Interagency Agreements | September 2, 2020 |
| 300.17 | Acquisition of Employee Training | September 11, 2018 |
| 300.18 | Procurement Request Packages | September 14, 2022 |
| 300.22 | Approval of TSA Specific Contract Terms and Conditions | October 18, 2017 |
| 300.23 | Other Transaction Authority Agreements | May 8, 2019 |
| 300.24 | Emergency Lodging Procurement | April 28, 2022 |
| 300.25 | Acquisition Plans at TSA | May 19, 2020 |
| 300.26 | Procurement and Contract Administration During Appropriation Lapses | October 7, 2019 |

#### Internal Guidance and Procedure Memorandums (IGPMs)
| IGPM | Title | Effective Date |
|------|-------|---------------|
| 0102.11 | Contract Compliance Review Program | April 18, 2022 |
| **0103.19** | **Business Clearance Memorandum** | **December 6, 2021** |
| 0106.04 | Processing FOIA Requests | April 8, 2021 |
| 0300.05 | Safeguarding Procurement Integrity | June 1, 2021 |
| **0400.15** | **Solicitation Review and Approval Process** | **October 5, 2022** |
| 0401.09 | Procurement Instrument Identifier (Contract Numbering) and CLIN Numbering | April 20, 2022 |
| 0403.05 | Security Requirements for IT-related Contracts | July 15, 2022 |
| 0404.17 | Contract File Documentation | May 5, 2022 |
| 0405.07 | External Audit, Investigation and Data Call Compliance | January 22, 2021 |
| 0406.07 | Contract Award Distribution | May 11, 2022 |
| 0408.13 | Contract Closeout | December 13, 2022 |
| 0409.08 | Legal Reviews of Contract Actions | September 30, 2022 |
| 0410.0 | Special Contract Requirements and Instructions | October 28, 2020 |
| 0420.08 | Contract Specific Security Requirements | July 25, 2018 |
| **0701.17** | **Procurement Strategy Board** | **September 30, 2022** |
| 0717.09 | Acquisition Planning Forecast System | March 15, 2022 |
| 0900.07 | Organizational Conflicts of Interest Prevention and Mitigation | February 7, 2023 |
| 0901.07 | Suspension and Debarment | February 10, 2023 |
| **0902.08** | **Responsibility Determination** | **February 10, 2023** |
| 1600.07 | Undefinitized Contract Actions | March 29, 2022 |
| 1601.04 | TSA Incentive Contracting Procedures | May 20, 2021 |
| 1701.09 | Assisted Acquisition/Interagency Acquisition Execution and Administration | February 11, 2022 |
| 1800.12 | Contingency and Emergency Contracting | September 7, 2022 |
| 1900.11 | TSA Small Business Program | January 10, 2022 |
| 1901.04 | Small Business Set-Asides/Non-Manufacturer Rule | July 31, 2018 |
| 1902.06 | Subcontracting Plans | December 8, 2021 |
| 2400.04 | Privacy Act Requirements in Contracting | January 22, 2021 |
| 2500.09 | Foreign Acquisition at TSA | May 5, 2022 |
| 3201.05 | Severable Services | May 31, 2023 |
| **3300.09** | **Protests, Disputes and Appeals** | **December 9, 2021** |
| **4201.09** | **Contractor Past Performance Information Assessment and Use** | **February 10, 2023** |
| 4202.13 | Invoice and Payment Processing | October 27, 2021 |
| **4900.13** | **Contract Termination** | **February 10, 2023** |
| 5401.08 | C&P Annual Employee Awards | December 9, 2022 |
| 5410.03 | Section 504 Program for Contracting | December 2, 2021 |
| 5411.02 | Contract and Procurement Training Procedures | January 19, 2022 |
| 5412.01 | C&P 1102 Developmental Rotations Program | May 26, 2022 |

#### Policy Letters
| Number | Title | Effective Date |
|--------|-------|---------------|
| 2014-003 Rev.002 | TSA Contracting and Procurement Method of Issuing Policy and Guidance | July 10, 2018 |
| 2015-002 Rev.004 | Continual Appointment of TSA Competition Advocate | January 12, 2021 |
| 2015-006 Rev.002 | Delegation of Signatory Authority for TSA Document Review Process | July 10, 2018 |
| 2016-001 Rev.002 | Prohibition on Incremental Funding for Non-Severable Services | July 10, 2018 |
| 2016-005 Rev.007 | Bailment Agreements and Other Agreements Requiring CO Execution | March 9, 2022 |
| 2016-008 Rev.005 | Ordering Official Program | January 3, 2022 |
| 2017-003 Rev.002 | Class Approval of Contracts for Severable Services Crossing Fiscal Years | July 10, 2018 |
| **2017-004 Rev.004** | **Source Selection Authority Appointment and Business Process** | **August 23, 2022** |
| 2018-001 Rev.002 | Appointment of Alternate TSA Competition Advocate | January 13, 2021 |
| 2019-001 Rev.001 | TSA Contracting Warrant Policy and Process | November 2, 2021 |
| 2022-001 | Authority for Use of FPAS Ratings under TSA Contracts | February 25, 2022 |
| 2023-001 | Junior Contract Specialist Group (JCSG) Program | December 13, 2022 |
| 2023-002 | Interagency Acquisition Policy in TSA | March 30, 2023 |

#### Action Memos
- **Delegation of Authority — Appendix G Requirements** (March 22, 2023): Delegates to C&P Operational Division Directors for approval of HSAM 3004.470(d) Appendix G requirements
- **Delegation of Authority — Chief of Contracting Office (COCO)** (May 17, 2021): Delegates authority to Dina Thompson as COCO
- **Legal Review Threshold for Contract Solicitations and Awards** (September 14, 2022): Memorandum of Record between C&P and TSA Chief Counsel to increase legal review threshold

### Acquisition Plan (AP) Quick Start Rules (Dec 2024)
**Source:** APD Acquisition Plans Quick Start, December 2024
- **HSAM 3007.103(e):** No written AP required for FFP under $50M
- **OTFFP above SAT:** Written AP required (see threshold matrix)
- **HSAM 3007.1:** Requires acquisition **planning** (not necessarily a written AP) for all acquisitions above SAT — Appendix Z of HSAM for all APs
- **FITARA (HSAM 3007.103(j)):** TSA CIO must review and sign any AP that includes IT prior to C&P submission
- **TSA MD 300.25:** Governs process for drafting, processing, reviewing, and approving APs
- **APFS record ≠ written AP** — the requirement for a written AP does not satisfy the APFS record requirement
- **No solicitations shall be issued from C&P until the AP has been approved**
- If AP approved by DHS OCPO → submit HCA-approved AP to TSAProcurementPolicy@tsa.dhs.gov for upload to DHS RHCAST

### Competitive Standards by Acquisition Type (June 2022)
| Acquisition Type | FAR Competitive Standard | Documentation Required |
|-----------------|-------------------------|----------------------|
| Micro-Purchase | No competitive quotes required if price is reasonable per market research | Purchase Card program only |
| Simplified Acquisition (SAP) | Consider ≥3 sources, provide solicitation to all interested | Justification only if sole source (FAR 13.106-1(b)) |
| Federal Supply Schedules (Part 8) | Unrestricted consideration of all FSS holders | LSJ required if restricting to <3 holders |
| Multiple Award Contracts (Part 16.505) | Fair opportunity to all awardees is the standard | Exception to Fair Opportunity justification if restricting |
| 8(a) Set Aside (Part 19.8) | Competition required above competitive thresholds per FAR 19.805-1 | J&A for sole source above competitive threshold |
| Above SAT (Parts 6/13) | Full & open competition — all qualified sources per FAR Part 15 | J&A per FAR 6.302 if other than full & open |
| Brand Name Only | Inherently uncompetitive — CO must examine move to "brand name or equal" | FAR 11.105 rationale + appropriate justification for acquisition type |

### Best Value Decisions — TSA Policy (Aug 2023, APD Training Deck)
**Source:** Best Value Decisions Aug 2023.pptx (TSA Acquisition Policy Division)

**Best Value Continuum:**
- LPTA = endpoint where cost/price has maximum weight, all other factors Pass/Fail
- HTRLP (Highest Technically Rated Low Price) = can be anywhere on continuum
- Tradeoff Process = flexibility to award to other than lowest price or highest rated

**LPTA at TSA:**
- **Class D&F approved by HCA (Aug 11, 2022)**: Pre-authorizes LPTA for IT software and IT hardware — no individual D&F needed for those categories
- **HCA Delegation to Division Directors (Aug 25, 2023)**: DDs can approve LPTA use
- FedProcure implication: LPTA warning on $20M+ should note Class D&F exception for IT SW/HW

**Adequate Price Competition (Best Value):**
- Technically unacceptable offers do NOT count toward adequate price competition (FAR 15.403-1(c)(1))
- 2 offers received, 1 technically unacceptable = NO adequate price competition
- Cannot rely on FAR 15.404-1(b)(2)(i) for price reasonableness in that scenario
- FAR 15.4 applies to FAR 16.5 task orders, may apply to FAR 13, does NOT apply to FAR 8.4 (GSA Schedule)
- FAR 8.4 actions: fair & reasonable determined through other analysis, not based on price competition

**Tradeoff Documentation Standard (for SSDD):**
- SSA decision = independent assessment, NOT a "sign-off" of evaluation recommendation
- Must discuss S/W/D relative qualities, not just restate adjectival ratings
- Comparison must identify each area of significant difference between proposals
- As price differential increases, relative technical benefits must also increase proportionally
- No requirement to assign exact dollar value to technical benefits — qualitative analysis sufficient
- GAO case law: generalized or content-free statements = protest vulnerability
- If highest technically rated = lowest price → tradeoff analysis NOT required (state this in solicitation)

### Actual TSA BCM Examples in Database
| Contract | Value | Type | Contractor | Service |
|----------|-------|------|-----------|---------|
| FSSS $20M | $20M | Streamlined (OASIS-SB) | [Redacted] | Field support services |
| Leadership Institute | $10M | Pre-Competitive IDIQ | [Redacted] | Leadership training |
| 70T01023C7663N001 | $38.9M | Pre/Post Sole Source | Acuity International | Interim Medical Services |
| HazMat Mgmt | $55M | Streamlined (OASIS) | Leidos | Hazardous material management |
| 70T01025C7663N001 | $77.4M | Pre/Post Competitive | OptumServe Health Services | NNMS Medical Services |
| EWR CBIS | $26M | OTA Streamlined | [Redacted] | EWR Airport screening systems |

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

## Phase 9: Controlled Drafting Workspace — MVP #4 (2026-03-21)

### DraftingWorkspace Orchestrator
- **5 document types**: PWS, IGCE, Section L, Section M, QASP
- **Propose/Redline/Explain model**: every section has content + authority + confidence + rationale + source provenance
- Per-section accept/modify/override by CO
- Regeneration produces redlines against prior version automatically
- DiffEngine: section-by-section unified diff (added/modified/deleted)

### SectionLEngine (Instructions to Offerors)
- 6 standard sections (L.1–L.6) per FAR 15.204-5
- Page limits scale with acquisition value ($1M→25pp tech, $20M→40pp, $50M+→60pp)
- Past performance references scale (3–5 refs based on value)
- Commercial item flag adds L.7 (FAR Part 12 streamlined procedures)

### SectionMEngine (Evaluation Factors)
- **Tradeoff** template: 6 sections (basis for award, 4 factors, adjectival scale) per FAR 15.101-1
- **LPTA** template: 4 sections per FAR 15.101-2
- Auto-selects tradeoff vs LPTA based on value, complexity, and explicit override
- Tech weight language: "significantly more important" at $20M+, "approximately equal" below
- Custom evaluation factors injection support
- Warning raised for LPTA on $20M+ acquisitions

### QASPEngine
- Generates surveillance items mapped from PWS sections
- Extracts metrics (SLA times, percentages) from PWS content
- Auto-selects surveillance method (100% inspection, automated monitoring, random sampling, periodic assessment)
- Progressive remedy chain: CAR → Cure Notice → Default

### PWS Generation
- SOW→PWS conversion: detects will/shall, vague language, staffing specs, passive voice
- Template-based generation when no SOW provided
- Background, applicable documents, scope, service delivery, reporting, transition, QC sections

### IGCE Sections
- Methodology section with multi-source approach documentation
- Labor rate analysis table (benchmark + burdened rates)
- Comparable contract analysis framework (SAM.gov enrichment at runtime)

### API Endpoints
- `POST /api/v1/phase2/drafting/generate` — generate draft with propose/redline/explain
- `POST /api/v1/phase2/drafting/diff` — compute redline between two versions
- `GET /api/v1/phase2/drafting/doc-types` — list available document types

### Frontend: DraftingWorkspace.jsx
- Doc type selector (5 types with descriptions)
- Per-section cards: content display, accept/modify buttons, collapsible rationale
- Inline editing with save modification
- Accept All button, accepted section highlighting
- Redline view: color-coded change type badges, unified diff display
- Confidence bars (per-section and overall)
- Warnings panel, source provenance footer
- SOW text input for PWS conversion mode

### Test Coverage
- **35 dedicated tests** across 7 classes:
  - TestSectionLEngine (6): generation, sequential IDs, page limit scaling, commercial item, authority, rationale
  - TestSectionMEngine (6): tradeoff/LPTA selection, adjectival scale, tech weight, custom factors
  - TestQASPEngine (3): PWS mapping, purpose section, metric extraction
  - TestDiffEngine (5): modified/added/deleted detection, no-change, diff lines
  - TestDraftingWorkspace (10): all 5 doc types, SOW conversion, redlines on regen, provenance, warnings
  - TestTemplateCoverage (4): L/M template existence and authority validation
  - TestDraftDiffRequest (1): end-to-end diff via workspace
- STATUS: **Deployed and verified** — 35/35 drafting tests, 209/225 full suite (15 pre-existing DB errors, 1 SAM.gov)

## Phase 10: Evidence Lineage Ledger — MVP #5 (2026-03-21)

### EvidenceLineageLedger
- **13 node types**: requirement, clin, section_l_instruction, section_m_factor, evaluator_score, ssdd_finding, qasp_surveillance, cpars_rating, clause, dcode, qcode, document, audit_event
- **12 link types**: traces_to, evaluated_by, scored_in, decided_in, surveilled_by, rated_in, triggers, implements, contains, governed_by, supersedes, maps_to_clin
- **8-stage coverage model** per requirement chain: requirement → CLIN → Section L → Section M → evaluator score → SSDD finding → QASP surveillance → CPARS rating
- Idempotent node registry (type + reference_id dedup)
- Superseded link support for versioning
- Forward/backward BFS trace with cycle detection and configurable depth limiting

### Chain Building
- PWS sections anchor each chain as requirements
- Traces forward through available documents: L.3/L.4 (Technical/Management), M.2/M.3 (Technical/Management), QASP items
- Post-award stages (evaluator_score, ssdd_finding, cpars_rating) tracked as gaps until populated
- Per-chain coverage percentage and completeness flag

### Integration Points
- **Policy trace**: Q-code traversal → D-code trigger links imported from PolicyService
- **Document links**: Document → D-code IMPLEMENTS relationships
- **Clause governance**: FAR/HSAR clauses → document GOVERNED_BY links
- **Full ledger build**: orchestrates all layers from package documents

### API Endpoints
- `POST /api/v1/phase2/lineage/build` — build full package lineage with coverage analysis
- `POST /api/v1/phase2/lineage/trace-requirement` — trace single PWS requirement
- `POST /api/v1/phase2/lineage/add-policy-trace` — import Q-code → D-code links
- `GET /api/v1/phase2/lineage/stats` — ledger summary statistics

### Frontend: LineageLedger.jsx
- Chain cards with 8-stage coverage bars (green=covered, gray=gap)
- Filter bar: All / Fully Traced / Has Gaps with counts
- Expandable chain detail: traced nodes (color-coded by type), links with rationale, gap list
- Node detail slide-out panel with metadata, authority, timestamps
- Warnings panel for missing critical documents (PWS, L, M, QASP)
- Gap summary with deduplication

### Test Coverage
- **55 dedicated tests** across 9 classes:
  - TestSchemas (7): stages, enums, node/link creation, coverage math
  - TestNodeManagement (11): add/dedup/link/forward/backward/supersede
  - TestTraceRequirement (7): full docs, PWS only, package chains, post-award gaps, coverage
  - TestPolicyTraceIntegration (4): Q-code/D-code nodes and links
  - TestDocumentLinks (3): document→D-code implementation
  - TestClauseLinks (3): clause governance, multi-clause × multi-doc
  - TestBuildLedger (6): full build, no PWS, PWS only, document links, gaps, coverage
  - TestTracing (4): forward/backward BFS, max depth, empty
  - TestEdgeCases (6): empty docs, no sections, non-dict content, multi-package, retrieval
- STATUS: **Deployed and verified** — 55/55 tests passing, commit 9881aec

## Phase 11: Secure Evaluation Workspace — MVP #6 (2026-03-22)

### RBAC (5 Roles × 12 Permissions)
- **SSA**: Source Selection Authority — views consensus, generates SSDD, signs decision
- **SSEB_CHAIR**: manages evaluation, assigns factors, submits consensus scores
- **SSEB_MEMBER**: scores assigned factors only — **sees only own individual scores**
- **CO**: administers process, adds offerors, advances phases
- **ADVISOR**: read-only (legal, SB specialist) — consensus view only
- **12 permission actions**: create_workspace, add_offeror, define_factors, submit_individual_score, submit_consensus_score, advance_phase, exclude_offeror, view_all_scores, view_own_scores, view_consensus, generate_ssdd, make_award_decision

### Score Immutability
- Scores cannot be modified — only **superseded** with written rationale (min 10 chars)
- Only original evaluator can supersede their own score
- Double-supersession prevention (already-superseded scores blocked)
- Superseded scores excluded from consensus aggregation
- Original score preserved in audit trail (never deleted)

### Phase Gate Validation
- Setup → Individual Eval: requires offerors + factors registered
- Individual Eval → Consensus: requires active scores for ALL offeror/factor pairs
- Final Eval → Decision: requires consensus scores for ALL offeror/factor pairs
- Decision phase triggers prominent Tier 3 audit log entry

### Competitive Range Exclusion
- Requires written rationale per FAR 15.306(c) (min 10 chars)
- Excluded offerors blocked from new scoring
- Excluded offerors hidden from comparison matrix
- Exclusion metadata: rationale, excluded_by, excluded_at

### SSDD Draft Generation (Tier 2 — AI Assists)
- Per-offeror evaluation summary: factor ratings with S/W/D counts
- Rating rank (numerical) for each factor
- Excluded offeror documentation
- Explicit Tier 3 notice: "FedProcure does NOT recommend an awardee"
- Source provenance: evaluation_workspace, consensus_scores

### Tier 3 Hard Stop — Award Decision
- `make_award_decision()` **ALWAYS raises Tier3HardStopError**
- Cites FAR 15.308 and FAR 7.503(b)(1)
- Error type is Tier3HardStopError (distinct from PermissionError — this is a constitutional limit, not a role issue)

### Comparison Matrix (Enhanced)
- Active offerors only (excluded filtered out)
- Per-cell: rating + strength/weakness/deficiency counts
- Active consensus scores only (superseded filtered out)

### Frontend: EvaluationWorkspace.jsx
- 7-phase visual timeline with color-coded current/past/future states
- Tier 3 decision phase banner (purple, prominent)
- Tab bar: Comparison Matrix / SSDD Draft / Audit Log / Summary
- Comparison matrix table with color-coded rating cells and S/W/D counts
- SSDD panel with offeror summaries and Tier 3 notice
- Append-only audit log with expandable history

### Test Coverage
- **56 dedicated tests** across 12 classes:
  - TestSchemas (7): roles, ratings, ranking, phases, permissions, phase sets
  - TestWorkspaceCreation (4): CO create, chair create, permission denied, add offeror
  - TestRBAC (4): advisor blocked, member blocked, consensus blocked, SSDD blocked
  - TestScoreSubmission (5): submit, wrong phase, excluded offeror, unknown offeror/factor
  - TestScoreImmutability (5): supersede, rationale required, wrong evaluator, double-supersede, consensus exclusion
  - TestExclusion (3): exclude, rationale required, advisor blocked
  - TestPhaseAdvancement (7): setup→individual, gate blocks, scoring gates, decision gate, complete, tier3 logging
  - TestScoreVisibility (3): member own-only, chair sees all, advisor sees none
  - TestComparisonMatrix (3): full matrix, excluded filtered, S/W/D counts
  - TestSSDDGeneration (4): generate, excluded documented, factor ratings, no recommendation
  - TestTier3HardStop (3): always refuses, cites authority, distinct error type
  - TestAuditLog (2): append-only, records action/actor
  - TestWorkspaceSummary (3): basic, superseded tracking, completeness
  - TestEdgeCases (3): unknown workspace, consensus wrong phase, multiple evaluators
- STATUS: **Deployed and verified** — 56/56 tests passing, commit e703168

## Phase 12: Post-Award Management — MVP #7 (2026-03-22)

### Option Tracking (FAR 17.207)
- `register_options()`: registers option periods with auto-calculated deadlines
- **Decision deadline**: 60 days before option period start
- **Preliminary notice**: 90 days before start per FAR 17.207(c)
- `get_option_alerts()`: returns alerts by severity — expired (critical), decision_overdue (high), preliminary_notice_due (medium)
- `exercise_option()`: requires written rationale (min 10 chars), prevents double-exercise and expired exercise
- `decline_option()`: records rationale for declining
- Exercised/declined options excluded from future alerts

### Modification Routing (FAR 43)
- **5 mod types**: bilateral (FAR 43.103(a)), unilateral (FAR 43.103(b)), administrative (FAR 43.101), change_order (FAR 43.2), REA (FAR 43.204)
- **Sequential mod numbering**: P00001/P00002 for bilateral, A00001/A00002 for unilateral
- **Status workflow**: drafted → under_review → approved → executed (with rejected branch)
- **Scope change detection**: `outside_scope` triggers J&A requirement (D106)
- **Required documents**: D129 (Mod Request Package) always required
- Valid transition enforcement with rollback support (under_review → drafted, rejected → drafted)

### CPARS Tracking (FAR 42.15)
- `schedule_cpars()`: schedules interim/final evaluation periods
- **Default due date**: period_end + 60 days
- `get_cpars_alerts()`: overdue (high) and due_soon (medium, within 30 days) alerts
- `submit_cpars()`: records 5 rating areas (quality, schedule, cost, management, small business) + narrative
- Note: CPARS has no public API — FedProcure tracks locally only

### Performance Issues & Cure Notices (FAR 49.402-3)
- **Escalation chain**: none → verbal_warning → written_warning → cure_notice → show_cause
- **Cure notice**: configurable cure period (default 10 days per FAR 49.402-3(a)), auto-calculated deadline
- PWS and QASP cross-reference on each issue
- `resolve_issue()`: marks resolved with timestamp

### Tier 3 Hard Stops — Post-Award
- `terminate_for_default()` **ALWAYS raises Tier3PostAwardError** — cites FAR 49 and FAR 7.503(b)
- `ratify_unauthorized_commitment()` **ALWAYS raises Tier3PostAwardError** — cites FAR 1.602-3
- Tier3PostAwardError is distinct from Tier3HardStopError (evaluation) — both are constitutional limits

### Contract Closeout (FAR 4.804)
- **10-item checklist** per FAR 4.804-5: POP complete, final delivery, final invoice, ULO deobligation, property disposition, release of claims, final CPARS, subcontract closeout, patent rights, files archived
- Progressive status: not_started → in_progress → complete (auto-completes when all items checked)
- `get_closeout_status()`: progress report with blocking items and percentages

### Aggregated Alerts (CO Dashboard)
- `get_contract_alerts()`: combines option, CPARS, modification, issue, and closeout alerts
- Critical/high severity counts for dashboard badge display
- Supports `as_of` date parameter for point-in-time alert queries

### API Endpoints (router_post_award_patch.py)
- `POST /options/register`, `GET /options/alerts/{id}`, `POST /options/exercise`, `POST /options/decline`
- `POST /modifications/create`, `POST /modifications/advance`, `GET /modifications/pending/{id}`
- `POST /cpars/schedule`, `GET /cpars/alerts/{id}`, `POST /cpars/submit`
- `POST /issues/report`, `POST /issues/escalate`, `POST /issues/resolve`
- `POST /closeout/initiate`, `POST /closeout/update-item`, `GET /closeout/status/{id}`
- `GET /alerts/{id}` — aggregated contract alerts
- `POST /terminate-for-default`, `POST /ratify` — always return 403 (Tier 3)

### Frontend: PostAwardDashboard.jsx (~480 lines)
- Alert summary bar with severity badges and category counts
- 6-tab layout: Overview / Options / Modifications / CPARS / Issues / Closeout
- **OptionCard**: period details, alert highlighting, inline exercise/decline with rationale textarea
- **ModCard**: mod number, type badge, status workflow, scope change/J&A warning, value change display
- **CPARSCard**: period type, status badge, due date, alert integration, rating display
- **IssueCard**: severity badge, escalation action display, cure deadline warning, Tier 3 termination notice on show_cause
- **CloseoutPanel**: interactive 10-item checklist with progress bar, FAR 4.804 authority, completion date

### Test Coverage
- **45 dedicated tests** across 8 classes:
  - TestOptionTracking (11): register, deadlines, preliminary notice, exercise, decline, alerts (prelim/overdue/expired), exercised no alerts, rationale required, double-exercise blocked
  - TestModificationRouting (7): bilateral/unilateral create, scope change J&A, workflow advance, invalid transition, pending mods, sequential numbering
  - TestCPARSTracking (5): schedule, due date default, alert due soon/overdue, submit
  - TestPerformanceIssues (5): report, cure notice, show cause, resolve, custom cure period
  - TestTier3PostAward (4): terminate refuses, cites FAR 49, ratify refuses, cites FAR 1.602-3
  - TestCloseout (6): initiate, update item, complete all, status report, invalid item, FAR checklist coverage
  - TestAggregatedAlerts (2): full alerts, empty contract
  - TestEdgeCases (5): unknown option/mod/cpars/issue, no closeout record
- STATUS: **45/45 tests passing locally** — Spark SCP pending (VM network limitation)

## Phase 13: Post-Award Lineage Integration (2026-03-23)

### Lineage Integration Bridge (lineage_integration.py, 299 lines)
- `record_evaluator_score()`: creates evaluator_score node, links M→score (SCORED_IN)
- `record_ssdd_finding()`: creates ssdd_finding node, links consensus scores→SSDD (DECIDED_IN)
- `record_cpars_rating()`: creates cpars_rating node, links QASP→CPARS (RATED_IN)
- `update_chain_coverage()`: fills evaluator/ssdd/cpars stages in existing chains
- Best-effort hooks in router endpoints — never block primary operation on lineage failure
- **26 dedicated tests** across 6 classes
- STATUS: **Deployed and verified**

## Phase 14: Cross-Chain Impact Analysis (2026-03-23)

### trace_impact() method on EvidenceLineageLedger
- Forward BFS from any node with severity classification per node type
- **Severity levels**: critical (ssdd_finding, cpars_rating), high (evaluator_score, section_m_factor), medium (section_l_instruction, qasp_surveillance, clin), low (clause, dcode, document)
- Affected chain tracking — which requirement chains are impacted
- Context-aware recommended actions (e.g., "Re-evaluate Section M factor", "Update QASP surveillance items")
- Configurable max_depth for bounded traversal
- **9 dedicated tests** in TestTraceImpact class
- STATUS: **Deployed and verified**

## Phase 15: USAspending Award Data Pipeline (2026-03-23)

### USAspendingClient (usaspending_client.py)
- **Base URL**: `https://api.usaspending.gov/api/v2/`
- **No authentication required**, generous rate limits
- Provider adapter pattern (mirrors TangoClient structure)
- `search_awards()`: POST /search/spending_by_award/ with pagination
- `get_award_detail()`: GET /awards/{id}/ for full enrichment (solicitation_number, competition, set-aside, offers received)
- `health_check()`: connectivity test
- Retry with exponential backoff (3 attempts), rate limiting (5 req/s self-imposed)
- **16 search fields** requested (internal_id excluded — causes USAspending 500)

### Award Data Models (models.py)
- **ContractAward**: canonical award record (PIID, recipient, agency, NAICS, PSC, competition, set-aside, solicitation_number)
- **AwardCrossmatch**: links awards ↔ solicitations ↔ protests with confidence levels
- **AwardType**: BPA Call (A), Purchase Order (B), Delivery Order (C), Definitive (D)
- **CompetitionType**: full_and_open, not_competed, competed_under_sap, follow_on
- **SetAsideType**: 8(a), HUBZone, SDVOSB, WOSB, total/partial SB
- **CrossmatchConfidence**: exact (solicitation_number), piid (contract number), fuzzy, manual
- Federal FY auto-calculation from start_date (Oct 1 rule)

### Ingestion Service (ingestion.py)
- `AwardIngestionService.ingest()`: paginated search → normalize → store → optional detail enrichment
- `ingest_by_fiscal_year()`: convenience method with FY date range calculation
- `enrich_award()`: fetches full detail for solicitation_number, competition type, PSC/NAICS descriptions
- `AwardDataStore`: in-memory store with PIID and solicitation_number indexes, deduplication
- Normalization: award type mapping, competition type mapping, set-aside mapping, date parsing, solicitation number cleaning

### Cross-Match Service (crossmatch.py)
- **Primary**: solicitation_number exact match (awards ↔ SAM.gov opportunities)
- **Secondary**: solicitation_number exact match (awards ↔ protest cases)
- **Tertiary**: PIID match (award contract number appears in protest solicitation field)
- Deduplication index prevents duplicate matches
- `run_full_crossmatch()`: orchestrates all strategies, returns CrossmatchStats
- `get_protested_awards()`: the training data gold mine — awards linked to protests

### API Router (router_usaspending.py)
- `POST /api/v1/awards/ingest` — ingest with custom filters
- `POST /api/v1/awards/ingest/fiscal-year` — ingest by FY
- `POST /api/v1/awards/enrich` — fetch full detail for specific award
- `GET /api/v1/awards/store/summary` — store statistics
- `GET /api/v1/awards/store/by-piid/{piid}` — find by contract number
- `GET /api/v1/awards/store/by-solicitation/{sol}` — find by solicitation
- `POST /api/v1/awards/search` — filtered search with pagination
- `POST /api/v1/awards/crossmatch` — run cross-matching against DB
- `GET /api/v1/awards/analytics/protest-correlation` — protested vs unprotested analysis

### Database Tables
- **contract_awards**: 18 core columns + indexes on solicitation_number, piid, agency, fiscal_year, value
- **award_crossmatches**: match_type, confidence, match_key, linked IDs
- **award_ingestion_runs**: audit trail per ingest operation

### Data Load — Full DHS Coverage (2026-03-23)
- **27,686 DHS contract awards** ingested (FY2001–FY2027, peak FY2020–FY2026)
- FY2023–FY2026: 10K each (USAspending search API cap), sorted by value descending
- Total obligation value: **$217.8B** across all DHS components
- Top sub-agencies: USCG (8,184), OPO (5,326), FEMA (3,802), CBP (3,672), ICE (2,402), **TSA (1,739)**, USCIS (997), USSS (893), FLETC (552)
- TSA: 1,739 awards, $18.0B total obligation

### Award Detail Enrichment Pipeline
- **Scripts**: `enrich_awards.py` (v1), `enrich_awards_v2.py` (v2 — resilient/resumable)
- Calls `GET /api/v2/awards/{generated_unique_award_id}/` per un-enriched award
- Extracts: solicitation_identifier, extent_competed, set_aside, PSC, NAICS description, number_of_offers, UEI, parent_piid
- Maps competition codes and set-aside codes to canonical enums
- v2 improvements: exponential backoff (up to 60s), 30s cooldown every 100 awards, 50 consecutive error tolerance, batch DB updates every 25 records
- **In progress**: ~824 enriched, 351 with solicitation_number, ~26,862 remaining
- Rate: ~0.6–2.5 req/s depending on USAspending load

### Cross-Match Results (2026-03-23)
- **31 protested DHS awards** matched (29 exact solicitation_number + 2 PIID match)
- Award→SAM.gov Solicitation: **0 matches** (temporal mismatch — SAM.gov data is Sept 2025–Mar 2026, awards mostly FY2018–FY2022; will improve as enrichment continues on FY2023+ awards)
- Award→Protest: **31 matches** — GAO protest records use same solicitation format as USAspending

### Protest Correlation Analysis (Training Data)
- **Protest rate by value bracket**:
  - Under SAT ($350K): 0% — no protests
  - SAT–$5.5M: 0.01% — essentially zero
  - $5.5M–$50M: 0.03% — negligible
  - **$50M–$100M: 4.66%** — sharp inflection point
  - **$100M+: 10.26%** — 1 in 10 protested
- **All 31 protested awards = full-and-open competition** (100%)
- Protested avg obligation: **$210.9M** vs unprotested **$10.5M** (20× ratio)
- Protested median: **$105.7M** vs unprotested **$2.9M** (36× ratio)
- **6 TSA contracts protested**: IMPACT (b-414230, b-420441), credentialing (b-418642), Secure Flight (b-420470), screening services (b-417840), CT systems (b-417463)
- Top protested NAICS: 541512 (Computer Systems Design) = 9 protests, 541511 (Custom Programming) = 2
- Top protested agencies: USCIS (7), TSA (6), ICE (3), USCG (3), OPO (3)

### Test Coverage
- **48 dedicated tests** across 10 classes:
  - TestContractAward (3): FY calculation, defaults, enum values
  - TestAwardIngestionRun (4): complete success/partial/failed, summary
  - TestCrossmatchModel (1): creation
  - TestUSAspendingClient (8): config, filters (3 variants), parse search (2), parse detail (2)
  - TestNormalization (4): date parsing, solicitation cleaning, normalize record, enrich from detail
  - TestAwardDataStore (6): upsert new/update, PIID index, solicitation index, summary, with_solicitation count
  - TestAwardIngestionService (5): basic, pagination, dedup, API error, FY convenience
  - TestCrossmatchService (10): solicitation match, protest exact, protest PIID, no dupes, full crossmatch, protested awards, normalize helpers (2), summary
  - TestEdgeCases (6): empty store, no awards, no solicitations, no sol number, enrich preserves, nonexistent
  - TestIntegration (2): full pipeline, multi-FY ingest
- STATUS: **Deployed and verified** — 48/48 tests passing, 27,686 awards in DB

## Phase 16: GAO.gov DHS Protest Scrape + Multi-Source Cross-Match (2026-03-23)

### GAO.gov Web Scrape (OpenClaw browser automation)
- **1,451 DHS bid protest records** in `gao_protests` table (Phase 1 listing + Phase 2 detail enrichment)
- **Source URL**: `gao.gov/search?agency=DHS&ctype=Bid Protest`
- Phase 1 (listing data): complete — company, solicitation #, B-number, outcome, dates (all 1,451)
- Phase 2 (detail enrichment): **COMPLETE** — 1,004 detail pages scraped by OpenClaw, all 1,004 ingested (100% match rate)
- **Enrichment coverage** (post-Phase 2 ingest):
  - sub_agency: 959/1,451 (66.1%) — normalized to 11 canonical agencies
  - highlights: 573/1,451 (39.5%)
  - decision_summary: 573/1,451 (39.5%)
  - pdf_url: 458/1,451 (31.6%)
  - gao_contacts: 590/1,451 (40.7%)
  - evaluation_factors: 125/1,451 (8.6%)
  - filed_date: 861/1,451 (59.3%)
  - gao_attorney: 860/1,451 (59.3%)
  - pdf_downloaded: 422/1,451 (29.1%) — actual PDF files on disk
- **929/1,451 (64%)** have solicitation numbers
- Date range: 1990–2026 (bulk is 2018–2026)

### Outcome Distribution (DHS-specific, normalized, n=1,329)
- Denied: 566 (42.6%)
- Dismissed: 499 (37.5%)
- Withdrawn: 125 (9.4%)
- Sustained: 110 (8.3%)
- Denied in Part: 20 (1.5%)
- Granted: 9 (0.7%)
- **DHS sustain rate: 119/695 = 17.1%** (adjudicated only — Sustained+Granted vs Sustained+Granted+Denied)

### Sub-Agency Distribution (normalized, n=959)
- CBP: 143 | USCG: 141 | FEMA: 137 | ICE: 135 | TSA: 107
- DHS HQ: 103 | USCIS: 92 | USSS: 41 | FLETC: 29 | FPS: 26 | CISA: 5

### Phase 2 Ingestion Pipeline (ingest_gao_phase2.py, 2026-03-25)
- **Match strategy**: file_number exact → b_number array overlap → INSERT new
- **Sub-agency normalization**: 30+ raw variants → 11 canonical names (junk values like "for the agency", "U" → NULL)
- **Outcome normalization**: 122 raw variants → 6 canonical outcomes (Denied, Dismissed, Withdrawn, Sustained, Denied in Part, Granted)
- Long decision text mistakenly in outcome field → moved to decision_summary
- PDF manifest tracking: pdf_downloaded, pdf_local_filename, pdf_file_size columns added
- **Results**: 1,004 updated, 0 inserted, 0 errors

### Multi-Source Cross-Match Engine
- **`ingest_gao_scrape.py`**: ingests JSON + runs 4-way cross-match in 2.3s
- **Tables**: `gao_protests` (1,451 rows), `gao_crossmatches` (278 rows)
- **Normalized solicitation matching**: uppercase, strip dashes/spaces for fuzzy tolerance
- **B-number array support**: multi-B-number cases stored as `text[]` for GIN index
- **COFC fuzzy matching**: Jaccard similarity on company name tokens (threshold ≥0.4, ≥2 overlapping tokens)

### Cross-Match Results (347 total — up from 278 after enrichment v2 + Tango resync)
- **198 USAspending matches** (168 unique protests → contract awards by solicitation_number)
  - $1.4B Eastern Shipbuilding / USCG (Withdrawn)
  - $671M PAE Aviation / CBP air ops (multiple protests — Denied/Dismissed)
  - $263M HeiTech-PAE / ICE (Denied)
  - $211M CACI / TSA IMPACT (Sustained)
  - $162M Alpha Omega / DHS (Dismissed)
  - $94M Deloitte / TSA Secure Flight (Dismissed)
  - $70M Sterling Medical / ICE (multiple protests)
- **146 Tango matches** (141 unique protests → B-number exact join against 13,318 Tango cases)
- **3 COFC escalation matches** (GAO → Court of Federal Claims appeals by company name fuzzy match)
  - General Dynamics IT (B-420282, Denied at GAO → COFC appeal, sim=0.67)
  - Abacus Technology (B-416390, Denied at GAO → COFC appeal, sim=0.60)
- **0 SAM.gov matches** (temporal mismatch — SAM data is recent solicitations, protests on older awards)

### CourtListener COFC Ingest (complete)
- **Table**: `cofc_protests` — USCFC bid protest cases from free CourtListener/RECAP API
- 3 search queries: bid protest, injunctive relief, procurement/solicitation
- Bug fix: `pacer_case_id` string→int cast for asyncpg
- **38 unique dockets** stored (21 from 2026, 17 from 2025)
- Fields: docket_id, docket_number, case_name, dates, judge, parties (JSONB), attorneys, firms, recap_documents
- Top judges: Eleni M. Roumel (3), Edward Hulvey Meyers (3), Zachary N. Somers (2), Robin M. Meriweather (2)

### USAspending Enrichment v2 (complete)
- **12,021/12,184 enriched** (99%), **4,236 solicitation numbers** found, 163 errors
- Elapsed: 6.5h (389.9 min)
- Next: ~15,500 FY2023-2026 awards still need enrichment (rerun same script)

### Tango Full Re-Sync (2026-03-24)
- **13,318 total protest cases** (318 new + 13,000 updated)
- **707 DHS-related cases**
- 236 API calls in 34 min (primary key only, 1500/day limit)
- Top agencies: VA (1,931), DLA (1,090), Air Force (666+), Army (606+)
- Overall sustain rate: 246/12,838 = 1.9% (vs DHS 15.3%)
- FY range: FY2017-FY2026, peak FY2017-2018 (~1,450/yr)

## Phase 17: Contract Transaction/Modification History (2026-03-23)

### ingest_transactions.py
- **Endpoint**: `POST /api/v2/transactions/` (USAspending, free, no auth)
- Targets all awards cross-matched to GAO protests via `gao_crossmatches`
- Full pagination (checks `len(results) < PAGE_SIZE` — USAspending `hasNext` returns `None`)
- Paginated fetch with PAGE_SIZE=25, exponential backoff (4 attempts), 1.5s pacing
- Dedup on `(generated_unique_award_id, modification_number)`

### Results (v2 — full pagination, 2026-03-24)
- **1,666 transactions** stored across **77 unique awards**, 0 errors
- **77 base awards** + **1,589 modifications**
- **$5.87B total federal action obligation** across all transactions
- **Date range**: 2017-09-29 to 2026-03-20
- **Elapsed**: 3.1 minutes (110 API calls)
- v1→v2 delta: +575 records, +19 awards, +$1.39B obligation recovered from pagination fix

### Modification Type Distribution
| Type | Count | Obligation |
|------|-------|------------|
| Funding Only Action | 499 | $1,318M |
| Other Administrative Action | 383 | $346M |
| Supplemental Agreement (within scope) | 294 | $300M |
| Exercise an Option | 251 | $2,971M |
| Change Order | 133 | $62M |
| Close Out | 14 | -$10M |
| Terminate for Convenience | 7 | -$13M |
| Additional Work (new agreement) | 4 | $4M |
| Entity Address Change | 2 | $2M |
| UEI/Legal Name Change | 1 | N/A |

### Award-to-Protest Timing Analysis
- Pre-award protests observed (negative days = filed before award date)
- Hamilton Staffing: -36 days (pre-award protest, Dismissed)
- CentralCare: 42 days post-award (Dismissed)
- Loyal Source: 47 days to 772 days — serial protester (6 protests, all Denied/Dismissed)
- Sterling Medical: 41 days to 412 days — serial protester (3 protests, Dismissed/Withdrawn)
- Central Care: 477 days post-award (Denied)
- ICE medical services contract: 12+ protests from 5 different companies over 2+ years
- AT&T Corporation: 109 days post-award → Sustained

### Database Table
- **`contract_transactions`**: 26 columns + 5 indexes (award_id, piid, mod_number, action_date, solicitation)
- Full raw_payload JSONB preserved for all 1,666 records

### USAspending Enrichment v2 (complete, 2026-03-25)
- **Batch 1** (FY2001-2022): 12,021/12,184 enriched, 4,236 solicitation numbers, 163 errors, 6.5h
- **Batch 2** (FY2023-2026): 15,203/15,416 enriched, 5,706 NEW solicitation numbers, 213 errors, 8.4h
- **Combined**: 27,224/27,600 enriched (99%), **9,942 total solicitation numbers**, 376 errors
- Competition type, set-aside type, PSC/NAICS descriptions, UEI, parent PIID now populated

### Cross-Match Results (rebuilt 2026-03-25)
| Source | Matches | Method | Delta vs prior |
|--------|---------|--------|----------------|
| USAspending | **351** | solicitation_number exact | +153 (+77%) |
| Tango | **146** | B-number exact | — |
| COFC | **12** | company name Jaccard (>=0.4) | +9 (+300%) |
| SAM.gov | 0 | solicitation_number exact | — (temporal gap) |
| **Total** | **509 links, 437 unique protests** | | **+162 (+47%)** |
- Award-SAM.gov solicitation overlaps: 91 (not protest-related but useful for analytics)

### Data Pipeline Summary (as of 2026-03-25 08:30 UTC)
| Source | Records | Solicitation #s | Cross-Matched |
|--------|---------|-----------------|---------------|
| USAspending awards | 27,686 | 9,942 (enriched) | 351 -> GAO protests |
| USAspending transactions | 1,666 | — | 77 protested awards |
| Tango GAO protests | 13,318 | varies | 146 -> GAO scrape |
| GAO.gov scrape | 1,451 | 929 | 509 total matches |
| SAM.gov opportunities | 45,635 | 31,264 | 0 (temporal gap) |
| CourtListener COFC | 38 | — | 12 (fuzzy company match) |
| **Total protest records** | **~14,807** | | **509 cross-links** |

## Phase 18: Protest Risk Model v1 (2026-03-25)

### Model Training Pipeline (protest_risk_model.py)
- **Training data**: 27,686 DHS contract awards (162 protested, 27,524 not protested)
- **Labels**: 162 positive from 351 USAspending↔GAO cross-match links
- **Features** (10): log_value, value_bracket, competition_type, sub_agency, naics_2digit, psc_1char, award_type, extent_competed, has_solicitation, duration_days
- **3 models trained**: Logistic Regression, Random Forest, Gradient Boosting (5-fold stratified CV)

### Model Performance (5-fold cross-validation)
| Model | ROC AUC | Avg Precision |
|-------|---------|---------------|
| Logistic Regression | **0.9493** | 0.1053 |
| Random Forest | **0.9508** | 0.1246 |
| Gradient Boosting | 0.9399 | 0.0980 |

### Risk Tier Calibration (Gradient Boosting)
| Tier | Score Range | Awards | Protested | Actual Rate |
|------|-------------|--------|-----------|-------------|
| LOW | 0-2% | 26,728 | 80 | 0.3% |
| MODERATE | 2-5% | 521 | 32 | 6.1% |
| ELEVATED | 5-15% | 260 | 26 | 10.0% |
| HIGH | 15-30% | 98 | 12 | 12.2% |
| CRITICAL | 30%+ | 79 | 12 | 15.2% |

### Top Predictive Features
- **has_solicitation** (+3.47 LR coef, 0.316 RF importance) — strongest single predictor
- **log_value** (+1.11 LR, 0.151 RF) — protest risk scales with contract value
- **award_type_D** (definitive contract, +1.82 LR) — definitive contracts protested more than task orders
- **competition_type_not_competed** (-1.70 LR) — sole source = no protest standing
- **competition_type_full_and_open** (+1.41 LR) — all protests occur in competitive procurements
- **psc_1char_S** (services, +1.80 LR) — service contracts protested more than products
- **sub_agency USCIS** (3.21% rate) vs **USCG** (0.16% rate) — 20x differential

### Empirical Protest Rates (from 27,686 DHS awards)
- **By value**: under SAT 0.11% → SAT-5.5M 0.31% → 5.5M-50M 1.28% → 50M-100M **7.30%** → 100M+ **5.81%**
- **By competition**: full_and_open 0.85%, follow_on 0.28%, not_competed 0.00%
- **By sub-agency**: USCIS 3.21%, ICE 1.12%, OPO 0.79%, USSS 0.78%, TSA 0.75%, FLETC 0.54%, CBP 0.41%, FEMA 0.26%, USCG 0.16%
- **By NAICS**: telecom 517110 11.63%, temp staffing 561320 10.00%, custom programming 541511 2.62%, computer systems 541512 2.16%

### Scoring Function (protest_risk_scoring.py)
- Standalone function:  → risk_score (0-100), risk_tier, factors[], mitigations[]
- Weighted composite: value (40%), competition (20%), sub-agency (20%), NAICS (10%), base rate (10%)
- Test results:
  - M TSA IT (F&O): Score 48, Tier LOW, 0.94% risk
  - M USCIS IT (F&O): Score 69, Tier MODERATE, 2.50% risk
  - M USCG maintenance (sole source): Score 16, Tier LOW, 0.22% risk
  - M CBP security guards (F&O): Score 59, Tier LOW, 1.53% risk
  - K FEMA supplies (micro): Score 9, Tier LOW, 0.15% risk

### Outputs
-  — standalone scoring function with empirical rate tables
-  — full empirical protest rates by feature value
-  — model coefficients, importances, AUC scores
-  — serialized sklearn pipelines (LR, RF, GB)

## Phase 19: Empirical Protest Risk Integration (2026-03-25)

### Hybrid Scoring Engine (protest_scoring.py rewrite)
- **Layer 1 (Empirical)**: ML model trained on 27,686 DHS awards with 162 protested
  - Weighted geometric mean composite: value (40%), competition (20%), sub-agency (20%), NAICS (10%), base rate (10%)
  - Calibrated risk tiers: LOW (<2%), MODERATE (2-5%), ELEVATED (5-15%), HIGH (15-30%), CRITICAL (30%+)
  - Embedded PROTEST_RATES dict with empirical rates from cross-match analysis
- **Layer 2 (Heuristic)**: Qualitative overlay factors the ML model can't observe
  - HF01-HF09: J-L-M traceability, LPTA on high-value, incumbent recompete, OCI, discussions, debriefing, price analysis, small business, GAO jurisdiction
  - Each heuristic factor adds adjustment points to empirical base score (capped at 100)
- **5-tier risk system**: LOW/MODERATE/ELEVATED/HIGH/CRITICAL (replaces old 4-tier LOW/MEDIUM/HIGH/CRITICAL)
- **RiskLevel enum updated**: MEDIUM → MODERATE, added ELEVATED
- **Backward compatible**: Old-style calls (sole_source, j_l_m_traced, etc.) still work — competition_type inferred from sole_source flag

### Schema Updates (schemas_phase2.py)
- **ProtestRiskRequest**: 6 new optional fields (competition_type, sub_agency, naics_code, psc_code, award_type, extent_competed)
- **ProtestRiskResponse**: 4 new fields (risk_tier, risk_pct, empirical_rates[], training_data)
- **EmpiricalRateResponse**: feature, value, total_awards, protested, rate_pct
- **TrainingDataResponse**: total_awards, protested_awards, base_rate_pct, cross_match_links, model_version
- All original heuristic fields preserved for backward compatibility

### Router Updates (router_phase2.py)
- POST /phase2/protest-risk now passes all 18 fields (6 empirical + 12 heuristic)
- Response includes empirical_rates array and training_data provenance
- Source provenance now includes model version and training data summary

### Frontend Updates (FedProcure_v4_Dashboard.jsx)
- **RISK_LEVEL_CONFIG**: 6 entries (low, moderate, elevated, high, critical, medium for backward compat)
- **ProtestRiskCard v2**: risk tier badge with empirical probability percentage, expandable empirical rates panel (2-column grid showing rates from 27,686 awards), factor IDs shown (EF01-EF04 empirical, HF01-HF09 heuristic), model provenance footer with version and cross-match link count
- **API call updated**: passes competition_type, sub_agency (defaults to TSA), naics_code, psc_code, award_type, extent_competed

### Test Results
- 4/4 protest risk tests passing (updated for 5-tier enum)
- 167/167 standalone tests passing (0 regressions)
- 43 pre-existing DB connection errors (unrelated)
- Smoke test: M TSA IT → score 59, LOW, 0.93% | M USCIS sole source → score 86, LOW, 1.63% | K backward compat → score 34, LOW
- STATUS: **Deployed and verified** on Spark DGX

## Phase 20: Protest Outcome Prediction Model (2026-03-25)

### Model Training Pipeline (protest_outcome_model.py)
- **Training data**: 937 DHS protest outcomes (55 sustained, 296 denied, 462 dismissed, 124 withdrawn)
- **Binary classification**: sustained (1) vs not-sustained (0) — 5.9% sustain rate overall
- **DHS adjudicated sustain rate**: 15.7% (55/(55+296) — sustained vs denied only, excluding dismissed/withdrawn)
- **Two model tiers**: Basic (all 937, protest-level features), Enriched (adds cross-matched award data)
- **Cross-match coverage**: 286 unique protests linked to USAspending awards

### Model Performance (5-fold stratified CV)
| Tier | Model | ROC AUC | Avg Precision |
|------|-------|---------|---------------|
| Basic | Logistic Regression | 0.7661 | 0.1886 |
| Basic | Random Forest | 0.8086 | 0.2178 |
| Basic | **Gradient Boosting** | **0.8212** | **0.2494** |
| Enriched | Logistic Regression | 0.7595 | 0.1786 |
| Enriched | Random Forest | 0.7943 | 0.2271 |
| Enriched | **Gradient Boosting** | **0.8419** | **0.2663** |

### Top Predictive Features
- **company_protest_count** (RF 0.217) — repeat protesters have different outcome patterns
- **days_to_decision** (LR +0.623, RF 0.189) — sustained cases take ~74 days vs dismissed ~29 days
- **is_repeat_protester** (LR +0.617, RF 0.110) — repeat protesters sustain at 9.0% vs single 2.4%
- **is_decision_record** (LR +0.459, RF 0.104) — decision records (vs docket) correlate with adjudication
- **sub_agency_CBP** (LR -0.780) — CBP has 0% sustain rate (0/12 adjudicated)
- **value_bracket_5.5M_to_50M** (LR +0.647) — 20% sustain rate in this bracket
- **naics_2digit_56** (LR -0.672) — admin/support services protests rarely sustained

### Empirical Sustain Rates
- **By sub-agency**: DHS_HQ 29.4%, USCG 25.0%, FEMA 22.7%, TSA 15.8%, ICE 15.4%, CBP 0.0%
- **By value bracket**: .5M-M 20.0%, M+ 20.0%, M-M 10.0%, SAT-.5M 0.0%
- **By protester type**: serial (5+ protests) 10.6%, repeat (3-4) 9.0%, single 2.4%

### Scoring Function (protest_outcome_scoring.py)
- Standalone \ function
- Takes: sub_agency, estimated_value, j_l_m_traced, evaluation_type, has_discussions, is_repeat_protester
- Returns: sustain_score (0-100), sustain_pct, sustain_tier (VERY_LOW/LOW/MODERATE/HIGH/VERY_HIGH), factors[], mitigations[]
- 5-tier outcome system: VERY_LOW (<5%), LOW (5-15%), MODERATE (15-25%), HIGH (25-40%), VERY_HIGH (40%+)
- Process factor adjustments: J-L-M gap (+10), LPTA high-value (+5), discussions (+5)
- Smoke tests: TSA \M → 15.8%/MODERATE | USCIS \M no-JLM → 30.7%/HIGH | CBP \M → 0%/VERY_LOW | USCG \M LPTA → 30%/HIGH | DHS_HQ \M no-JLM → 39.4%/HIGH

### Outputs
- `protest_outcome_scoring.py` — standalone scoring function with embedded rate tables
- `protest_outcome_tables.json` — full empirical sustain rates by feature value
- `protest_outcome_metadata.json` — model coefficients, importances, AUC scores
- STATUS: **Trained and verified** — scoring function generated

## Phase 21: Protest Outcome API Integration (2026-03-25)

### API Endpoint
- `POST /api/v1/phase2/protest-outcome` — separate from `/protest-risk` (different question)
- **protest-risk**: "Will this procurement get protested?" (27,686 awards, 162 protested)
- **protest-outcome**: "If protested, will GAO sustain it?" (937 outcomes, 55 sustained)
- Sub-agency name normalization: full names (e.g. "Transportation Security Administration") → abbreviations (TSA) for scoring function compatibility
- Request fields: value, sub_agency, competition_type, evaluation_type, j_l_m_traced, has_discussions, is_repeat_protester, is_incumbent_rebid

### Schemas (schemas_phase2.py)
- `ProtestOutcomeRequest`: 8 fields (value + 7 optional qualitative)
- `ProtestOutcomeResponse`: sustain_score, sustain_pct, sustain_tier, factors[], mitigations[], outcome_rates{}, training_data, source_provenance
- `OutcomeFactorResponse`: factor_id, factor, weight, detail
- `OutcomeRateResponse`: feature, value, total_protests, sustained, sustain_rate_pct
- `OutcomeTrainingDataResponse`: full provenance (937 protests, 55 sustained, model_version)

### Frontend: ProtestOutcomeCard (FedProcure_v4_Dashboard.jsx)
- 5-tier sustain system: VERY_LOW / LOW / MODERATE / HIGH / VERY_HIGH with distinct colors
- Score gauge bar (0-100) with DHS adjudicated sustain rate reference
- Expandable empirical sustain rates panel (sub-agency, value bracket, overall)
- High-weight factors panel (red border, prominent)
- Mitigations panel (green border)
- Expandable all-factors list with weight badges
- Model provenance footer
- Loads via `outcomeCache` state alongside existing `protestCache`
- Renders below ProtestRiskCard in PackageDetailPanel

### Smoke Test Results
- TSA $20M: sustain_tier=MODERATE, sustain_pct=15.8%, score=15, 2 factors
- DHS_HQ $50M no-JLM/LPTA/discussions: sustain_tier=VERY_HIGH, sustain_pct=49.4%, 5 factors
- CBP $5M: sustain_tier=VERY_LOW, sustain_pct=0.0%
- protest-risk backward compat: risk_tier=LOW, risk_pct=0.91%

### Test Coverage
- **15 dedicated tests** across 3 classes:
  - TestScoreProtestOutcome (9): TSA/CBP/DHS_HQ scoring, JLM gap increases sustain, unknown agency, factors/mitigations, repeat protester, outcome rates, training data
  - TestOutcomeRates (3): all agencies present, value brackets present, overall stats
  - TestOutcomeTiers (3): coverage 0-100, tier names, no gaps
- STATUS: **Deployed and verified** — 15/15 outcome tests + 32/34 phase2 tests passing (2 pre-existing eval workspace gate failures)

## Phase 22: GAO Decision Text Extraction (2026-03-25)

### Layer 1: OCR Extraction (extract_gao_pdfs.py) — Superseded by Layer 2
- **422 PDFs processed** in 3.5 minutes (0 errors), all image-based (browser-captured screenshots of GAO.gov viewer)
- **OCR approach**: PyMuPDF (fitz) image extraction → Tesseract 4.1.1 OCR (PSM 3, fully automatic page segmentation)
- Each PDF = single page with 1 large image (~1933×1199px) containing first page of GAO decision
- Small images (icons, buttons <400px) automatically filtered out
- **Average 150 words per PDF** — captures DIGEST section + decision intro + start of BACKGROUND
- **Retained for**: ~160 records not covered by HTML extraction

### Layer 2: HTML Decision Text (ingest_html_decisions.py) — Primary Source
- **556 decision records** scraped from GAO.gov HTML decision pages by OpenClaw
- **Median 2,528 words per decision** (vs 150 from OCR — 17× improvement)
- Full decision text including BACKGROUND, DISCUSSION, detailed analysis, and conclusion
- **Source file**: `gao_decision_text_updates.json` (11MB, 556 records)

### Structured Field Parsing (from full HTML text)
- **DIGEST extraction**: 440/556 (79%) from OpenClaw + fallback regex
- **Decision outcome detection**: 358/556 (64%) — exact phrase extraction
  - "We deny the protest.": 275 | "We sustain the protest.": 40 | "We dismiss the protest.": 22 | Mixed: 21
- **Evaluation factor arrays**: 361/556 (65%) — technical (319), past performance (272), price (262), management (198), experience (137), key personnel (132), staffing (124), quality (102), cost (66), transition (47), oral presentation (42), small business (41)
- **Sustain grounds arrays**: 297/556 (53%) — failed to evaluate/consider (167), unequal treatment (109), competitive prejudice (98), unstated criteria (66), flawed evaluation (37), OCI (25), unreasonable evaluation (20)
- **Denial grounds arrays**: 360/556 (65%) — consistent with solicitation (240), reasonably evaluated (221), mere disagreement (177), untimely filing (134), within agency discretion (86), rational basis exists (84)
- **Deficiency mentions**: 308/556 (55%) — weakness, deficiency, adjectival rating language

### Combined Database State (after both layers)
- **716/1,451 protest records** have decision_text (556 HTML + ~160 OCR-only)
- **596 records** have parsed DIGEST text
- **429 records** have outcome phrase
- **432 records** have evaluation factor arrays
- **310 records** have sustain grounds, **445** have denial grounds
- **Avg word count**: 2,281 (HTML records) vs 150 (OCR-only records)
- **12 columns** on gao_protests: decision_text, digest, ocr_word_count, ocr_outcome_extracted, eval_factors_extracted[], sustain_grounds_extracted[], denial_grounds_extracted[], deficiency_mentions[], ocr_matter_of, ocr_agency, background_start, decision_text_source

### Outcome Distribution (records with decision text, n=716)
- Denied: 419 | Dismissed: 81 | Sustained: 78 | Withdrawn: 19 | Denied in Part: 18 | Granted: 8 | NULL: 93

### Outputs
- `gao_decision_text_updates.json` — OpenClaw HTML extraction (556 records, 11MB)
- `gao_pdf_extractions/` — OCR extraction artifacts (422 PDFs)
- `extract_gao_pdfs.py` — OCR extraction pipeline
- `ingest_html_decisions.py` — HTML text ingestion with NLP parsing (asyncpg, runs in Docker)
- `ingest_pdf_extractions.py` — OCR text ingestion (asyncpg, runs in Docker)

### Model v2 Features Now Available
- Full decision text → NLP feature extraction (TF-IDF, embeddings, topic modeling)
- 14 evaluation factor presence/absence binary features
- 9 sustain ground categorical features
- 11 denial ground categorical features
- Deficiency mention features (weakness, strength, adjectival ratings)
- Word count as proxy for decision complexity
- STATUS: **Deployed and verified** — 716 records with decision text, 0 errors

## Phase 23: Protest Model v2 — Decision Text Features (2026-03-25)

### Training Data Extraction (extract_model_v2_data.py)
- **Outcome data**: 1,329 protests with eval_factors[], sustain/denial grounds[], deficiency mentions, cross-match award data, company protest count
- **Risk data**: 27,686 awards with competition_type, set_aside_type, number_of_offers, mod_count, protest outcomes
- Outputs: `model_v2_outcome_data.json` (958KB), `model_v2_risk_data.json` (18MB)

### Model Training (train_models_v2.py)
- Computes empirical rates across all feature dimensions from extracted JSON
- Generates standalone scoring functions with embedded rate tables
- Key findings from decision text NLP:
  - **14 evaluation factor types** with sustain rate lift analysis
  - **9 sustain ground categories** with success rate per ground
  - Number of offers: **150× differential** (3.07% protest rate at 6+ offers vs 0.02% at 0-1)
  - USSS: **39.1% sustain rate** (highest sub-agency)
  - Oral presentation factor: **6.8% sustain rate** (0.39× lift — lowest)
  - "Inconsistent with solicitation" ground: **66.7% sustain rate** (highest ground)

### Protest Outcome Scoring v2 (protest_outcome_scoring_v2.py)
- **Training data**: 1,329 DHS protests, 705 adjudicated, 119 sustained (16.9% adjudicated sustain rate)
- **Layers**: agency base rate → value bracket adjustment → process quality (J-L-M, LPTA, discussions) → eval factor lift → deficiency count
- **New v2 features**:
  - `eval_factors` param: 14 factor types with lift-based adjustment (only high-lift factors >1.2 contribute: experience 1.27×, cost 1.21×)
  - `deficiency_count` param: 1-2 mentions → 20.4% sustain rate; 3+ → 16.4% (non-linear)
  - `sustain_grounds_argued` param: per-ground sustain rate lookup
  - `FACTOR_SUSTAIN_RATES` table: 14 factors with with_factor count, rate_with, rate_without, lift
  - `GROUND_SUSTAIN_RATES` table: 9 ground types with sustain probability
- **Bug fixes**: sustain_pct now uses composite score (not just agency_rate); AGENCY_ALIAS resolves abbreviations
- Smoke tests: TSA $20M → 8.3%/LOW | DHS HQ $50M no-JLM/LPTA → 33.2%/HIGH | CBP → 0%/VERY_LOW

### Protest Risk Scoring v2 (protest_risk_scoring_v2.py)
- **Training data**: 27,686 DHS awards, 162 protested (0.585% base rate)
- **6-factor weighted geometric mean**: value (35%), competition (20%), agency (15%), NAICS (10%), offers (10%), set-aside (10%)
- **New v2 features**:
  - `number_of_offers` param: 4 brackets (0-1, 2-3, 4-5, 6+) with 150× risk differential
  - `set_aside_type` param: none vs unknown (unknown = 8.43% protest rate)
  - `OFFERS_PROTEST_RATES` table: empirical protest rates by offer count
  - `SETASIDE_PROTEST_RATES` table: protest rates by set-aside type
- **Bug fixes**: log-scale score mapping (was `rate × 10000`, now `log1p` curve); AGENCY_ALIAS for USAspending→abbreviation resolution
- Smoke tests: TSA $20M → score=14, 0.88%/LOW | USCIS $100M 5 offers → score=24, 2.09%/MODERATE

### API Integration
- **Router updated**: `router_phase2.py` imports v2 `score_protest_risk()` (standalone function, replacing `ProtestRiskEngine` class) and v2 `score_protest_outcome()`
- **Schemas updated**: `ProtestRiskRequest` adds `number_of_offers`, `set_aside_type_v2`; `ProtestOutcomeRequest` adds `eval_factors[]`, `deficiency_count`, `sustain_grounds_argued[]`; `OutcomeFactorResponse.weight` changed to `Any` (numeric in v2)
- **Frontend updated**: `loadProtestRisk()` passes `number_of_offers`, `set_aside_type_v2`; `loadProtestOutcome()` passes `eval_factors`, `deficiency_count`, `sustain_grounds_argued`; sub_agency defaults to "TSA" abbreviation
- **Model version**: v2.0 (up from v1.0-dhs-27686 / v1.0-outcome-937)
- Source provenance updated with decision text NLP stats

### Test Coverage
- **29 dedicated tests** (inline execution due to VM filesystem constraints):
  - Outcome v2 (16): TSA/CBP/DHS_HQ tier/pct, JLM gap, eval factor lift (high/low), deficiency count, alias resolution, training data v2, low-lift no-change
  - Risk v2 (13): TSA/USCIS tier/pct/score, offers differential, JLM gap, alias resolution, training data v2, low-value LOW, sole source mitigation, LPTA factor, incumbent factor
- **Formal test files**: `phase2/test_protest_outcome.py` (18 tests across 3 classes), `phase2/test_protest_risk_v2.py` (16 tests across 3 classes)
- STATUS: **29/29 inline tests passing** — deploy to Spark pending

## Dashboard Walkthrough Verification (2026-03-26)
**File:** `FedProcure_CO_Workflow.html` (1,350 lines, self-contained interactive demo)
**Scenario:** TSA $20M IT Services Recompete — FFP, Full & Open, Best Value Tradeoff, NAICS 541512
**Cross-referenced against:** 10 TSA source documents (uploaded originals)

### Source Documents Verified Against
1. BCM May 2022 (APD training deck — BCM types, approval authorities, waiver process, best practices)
2. Competition June 2022 (J&A/LSJ purpose, approval authorities, competitive standards by acquisition type)
3. SR Checklist IPMSS PEO TORQ (Aug 2025 — actual signed SR with Sections I–VII, APD comments)
4. Effective Guidance List June 2023 (all MDs, IGPMs, Policy Letters, Action Memos)
5. IGPM 0102 Att 1 (Contract Review Checklist template)
6. IGPM 0102 Att 3 (Corrective Action Plan template — FAR 4.604(b), FAR 8.404(h)(3))
7. Acquisition Plans Quick Start Dec 2024 (HSAM 3007.103(e), FFP exemption, FITARA, APFS ≠ AP)
8. CG-4788 (DHS Preaward Contract File Checklist — 43 items)
9. DHS Form 700-22 / 31268 (Small Business Review Form + instructions — 23 items, $100K trigger)
10. Best Value Decisions Aug 2023 (LPTA Class D&F, adequate price competition, tradeoff standard)

### Phase 1 — Intake ✓
- SAT = $350K ✓ (Oct 2025 threshold)
- 24 required documents (18 D-codes + 6 TSA-specific) ✓
- BCM Approval = DAA at $20M–$50M ✓ (Feb 2026 C&P thresholds; BCM May 2022 calls this "Deputy HCA" = same role)
- SSA = Division Director at $5M–$20M ✓ (Feb 2026 C&P thresholds)
- AP Required = No (FFP under $50M) ✓ (AP Quick Start Dec 2024, HSAM 3007.103(e))
- Cost data threshold $2.5M ✓ (FAR 15.403)
- Q-code trace: 17 nodes (Q001–Q017) ✓
- FAR 5.203 posting: SAM.gov, 30-day response ✓

### Phase 2 — Requirements ✓
- Completeness 13% (3/24 satisfied) ✓
- TSA PR Package: 700-20 (Satisfied/PM), 5000 (Pending/CO), Pre-BCM (Missing/CO), 700-22 (Missing/SB Specialist), Appendix G (Missing/CO), ITAR (Missing/CO) ✓
- D120 (Security) BLOCKING — non-waivable gate ✓
- D-code responsible parties correct (CO, COR, Security Officer assignments match CLAUDE.md)
- DHS Form 700-22 required at $20M (threshold >$100K per form instructions) ✓

### Phase 3 — Solicitation Prep ✓
- 63% completeness (15/24) ✓
- 5 drafts: PWS, IGCE, Section L, Section M, QASP ✓
- Section L page limit: 40 pages at $20M (scales correctly from drafting engine) ✓
- Section M: Best value tradeoff, "non-price factors significantly more important than price" ✓ (FAR 15.101-1)
- Clause selection: 14 clauses including FAR 52.212-4, 52.217-9, 52.219-28, 52.222-41, HSAR 3052.204-71/72 ✓
- J-L-M traceability: 6 PWS → 6 Section L → 4 Section M → 6 QASP = 100% chain ✓
- TSA Lifecycle Gates: ITAR (IGPM 0403.05), Pre-BCM (CS→CO→BC→DD→DAA), SRB (DD review, APD copy, DAA approves), SSA (DD at $5M–$20M), Appendix G, Chief Counsel review ✓
- **IGPM citation note**: Dashboard cites "IGPM 0400" — should be "IGPM 0403.05" (Security Requirements for IT-related Contracts). Other applicable IGPMs present by function but not by number: IGPM 0103.19 (BCM), IGPM 0400.15 (SR), IGPM 0701.17 (PSB).

### Phase 4 — Solicitation ✓
- 83% completeness (20/24) ✓
- UCF format per FAR 15.204 ✓
- Sections A/B/C/I/J/K/L/M mapped to D-codes ✓
- SAM.gov 30-day posting ✓
- Gate: completeness ≥60% ✓

### Phase 5 — Evaluation ✓
- Tier 3 banner: FAR 7.503(b)(1), FAR 15.308 ✓
- 5 proposals, 4 factors (Tech, Mgmt, Past Performance, Price) ✓
- Adjectival ratings: Outstanding/Good/Acceptable/Marginal/Unacceptable ✓
- Competitive range exclusion per FAR 15.306(c) ✓
- SSDD: "FedProcure does NOT recommend an awardee" ✓ (Tier 3 hard stop)
- Score immutability: supersession with written rationale only ✓
- SSEB member visibility: own scores only ✓

### Phase 6 — Award ✓
- Post-BCM Competitive Acquisition ✓
- Approval chain: CS→CO→BC→DD→DAA ✓ (matches BCM May 2022 "$20M-<$50M" bracket; "Deputy HCA" = DAA)
- Section G: 27-item compliance checklist ✓
- Debriefing: **FAR 15.506** ✓ (corrected from FAR 16.505 — 16.505 is for task orders under IDIQs, this is standalone FFP)
- Protest Risk: score 14/LOW, 0.88% probability ✓ (v2 scoring with embedded empirical rates from 27,686 DHS awards)
- Sustain Probability: 8.3%/LOW ✓ (v2 scoring from 1,329 DHS protests)
- Comparable protests: B-414230 CACI/IMPACT (Sustained), B-420470 Deloitte/Secure Flight (Dismissed), B-418642 Credentialing (Denied), B-417840 Screening (Denied) ✓
- TSA sustain rate: 15.8% of adjudicated ✓
- **BCM May 2022 nuance**: Pre-BCM for competitive = request authority to enter discussions (not solicitation release). Dashboard says "required before solicitation release" which is timing-correct but purpose differs slightly. Pre-BCM establishes the procurement history from PSR through need for discussions. If awarding on initial offers → Pre/Post BCM (no waiver needed).

### Phase 7 — Post-Award ✓
- 3 alerts: Option Year 1 preliminary notice (MEDIUM), CPARS interim (MEDIUM), SLA breach (HIGH) ✓
- Option tracking: 4 years, 60-day decision deadlines, 90-day preliminary notice per FAR 17.207(c) ✓
- Modifications: P00001 (bilateral), A00001 (administrative) ✓
- Evidence lineage: 87.5% (7/8 stages — CPARS pending) ✓
- Performance issue escalation chain: Written Warning (step 2 of verbal→written→cure→show cause) ✓

### Phase 8 — Closeout ✓
- FAR 4.804-5 checklist: 10 items, 7 complete ✓
- Remaining: ULO de-obligation ($47,230), Release of claims (FAR 4.804-5(a)(15)), Final CPARS (FAR 42.1503) ✓
- Evidence lineage: 8/8 stages with closeout at 70% ✓
- FAR citations correct: 4.804-1, 46.5, 32.9, 45.6, 42.15, 27.3, 4.805 ✓

### Discrepancies Found (5 items — all minor)
| # | Location | Issue | Severity | Resolution |
|---|----------|-------|----------|------------|
| 1 | Phase 3 | IGPM 0400 shorthand — should be IGPM 0403.05 | Low | Cosmetic — correct IGPM number in next HTML update |
| 2 | Phase 3 | Missing explicit IGPM citations for 0103.19 (BCM), 0400.15 (SR), 0701.17 (PSB) | Low | Content is correct, only IGPM numbers not displayed |
| 3 | Phase 3/6 | Pre-BCM described as "required before solicitation release" — technically it's authority to enter discussions | Low | Timing is correct; purpose description could be more precise |
| 4 | Phase 6 | BCM May 2022 uses "Deputy HCA"; Feb 2026 thresholds use "DAA" — same role | None | Terminology difference only, no action needed |
| 5 | All | HSAM 3004.7003 legal sufficiency review (>$500K) not cited | Low | N/A for this F&O scenario but should be noted for sole source paths |

### Verification Result
**PASS** — All 8 phases verified against 10 TSA source documents. 0 material errors. 5 minor items (cosmetic IGPM citations, terminology, Pre-BCM purpose nuance). All thresholds, approval chains, FAR citations, D-code assignments, and Tier 3 boundaries are correct.

## Phase 23–28 Roadmap: Requirements Development & Document Generation (2026-04-03)

### Problem Statement
Most programs do not know how to write SOWs, which leads to them not getting the goods or services they want, and is a factor in protests because a bad SOW leads to bad evaluation factors. FedProcure automates the entire upstream pipeline — from market research through full document generation — so the CO receives a complete, protest-resistant package instead of a bad SOW to clean up.

### Phase 23a: Market Research Agent (Weeks 1–3)
- **Local-first + live API** architecture: PostgreSQL queries against existing tables (27,686 awards, 1,451 protests, 45,635 SAM.gov opps) as primary; live USAspending/SAM.gov/GSA APIs as secondary
- **Input contract**: NAICS, PSC, agency/sub-agency, estimated value, geographic scope, contract type, keywords, set-aside preference
- **Output**: FAR 10.002-compliant market research report with 6 sections:
  1. Comparable Awards Analysis (local DB: awards by NAICS/PSC, price benchmarks, PIL rates)
  2. Active Market Scan (SAM.gov opportunities, expiring contracts, recompete candidates)
  3. Small Business Availability (set-aside viability, SBA dynamic small business search)
  4. Commercial Availability Assessment (FAR Part 12 applicability, COTS/GOTS analysis)
  5. Pricing Intelligence (DHS PIL benchmark rates, labor category analysis, burdened rate ranges)
  6. Protest Risk Context (historical protest rates for similar acquisitions from protest model v2)
- **Data sources**: 14 total — 8 local tables + 6 live APIs (USAspending, SAM.gov entity, SAM.gov opps, GSA Advantage, GSA CALC, SBA)
- **Tier 2**: AI synthesizes findings, proposes narrative; CO accepts/modifies/overrides
- **Dependencies**: None (extends existing data pipeline)
- **Test target**: 25+ tests covering each report section, local vs live fallback, FAR 10.002 compliance

### Phase 23b: Evaluation Factor Derivation Engine (Weeks 3–5)
- **7-step derivation**: PWS section analysis → requirement classification → factor candidate generation → subfactor mapping → weight suggestion → adjectival definition drafting → protest-proofing check
- **Tier 2 boundary**: AI proposes candidate factors, subfactors, weights, and adjectival definitions; SSA accepts/modifies/overrides per FAR 15.304
- **Tier 3 boundary**: SSA makes final factor selection, relative importance determination, and adjectival scale approval — these are evaluation judgments per FAR 15.308
- **Protest-proofing checks** (6 automated validations):
  1. Every Section L instruction traces to at least one Section M factor
  2. Every Section M factor traces to at least one PWS requirement
  3. No unstated evaluation criteria (FAR 15.304 — all factors disclosed in solicitation)
  4. Adjectival definitions are specific enough to distinguish between ratings (GAO case law)
  5. Price/technical weight relationship consistent with stated importance (tradeoff analysis)
  6. Past performance questionnaire aligns with evaluation subfactors
- **Integration**: Feeds Section L engine (Phase 9), Section M engine (Phase 9), Evidence Lineage Ledger (Phase 10)
- **Dependencies**: Phase 23a (market research informs factor selection), Phase 9 (drafting workspace)
- **Test target**: 20+ tests covering derivation logic, J-L-M traceability, protest-proofing checks

### Phase 23c: Evaluator Assistance Model (Weeks 5–7)
- **Three-panel presentation** per evaluation factor per offeror:
  1. **Solicitation Requirements Panel**: Section L instruction, Section M factor/subfactor, adjectival definitions (what "Outstanding" means for this factor)
  2. **Offeror Submission Panel**: relevant proposal excerpts mapped to this factor (manual upload initially, future OCR/NLP extraction)
  3. **Preliminary Observations Panel** (Tier 2): flags potential strengths (proposal exceeds requirement), potential weaknesses (proposal partially addresses requirement), potential deficiencies (proposal fails to address requirement), questions for discussions
- **Tier 2 boundary**: AI presents structured information and flags potential S/W/D for evaluator consideration
- **Tier 3 boundary**: SSEB member makes independent evaluation judgment — assigns rating, determines S/W/D, writes narrative rationale per FAR 15.305
- **Integration**: Extends SecureEvalWorkspace (Phase 11) — adds structured panels alongside existing scoring interface
- **SSDD generation extension**: Phase 11 SSDD draft enhanced with factor-by-factor comparison narrative, tradeoff analysis template, price/technical relationship documentation
- **Dependencies**: Phase 23b (factor definitions), Phase 11 (evaluation workspace)
- **Test target**: 15+ tests covering panel generation, Tier 3 hard stop verification, SSDD enhancement

### Phase 24: Requirements Elicitation Agent (Weeks 8–10)
- **Guided intake wizard**: walks program office through structured Q&A to extract requirements
- **117 Q-code decision tree integration**: answers drive document requirements, approval chains, clause selection
- **Output**: structured requirements matrix (requirement → priority → verification method → acceptance criteria)
- **Two entry points**: greenfield (blank slate guided intake) and legacy (existing SOW analysis)
- **Dependencies**: Phase 23a (market research feeds requirement context)

### Phase 25: Legacy SOW Analyzer (Weeks 11–13)
- **SOW→PWS conversion**: detects passive voice, vague language, staffing specs, "will/shall" inconsistencies (extends Phase 9 PWS engine)
- **Gap analysis**: identifies missing FAR 37.102 PBA elements, missing QASP linkages, missing deliverable acceptance criteria
- **Protest vulnerability scan**: flags ambiguous evaluation language, unstated criteria, inconsistent L/M alignment
- **Dependencies**: Phase 24 (requirements matrix), Phase 9 (drafting workspace)

### Phase 26: Drafting Workspace Restructure (Weeks 14–16)
- **Refactors Phase 9** drafting engines into agent-callable services with standardized input/output contracts
- **Agent orchestration**: market research → requirements → factor derivation → PWS → IGCE → L → M → QASP → UCF assembly
- **Version control**: full diff history per document section with rollback capability
- **Dependencies**: Phases 23a–25 (all upstream agents)

### Phase 27: Full Document Chain Generation (Weeks 17–20)
- **15+ document types** from single intake: PWS, IGCE, Section L, Section M, QASP, J&A/LSJ, D&F, BCM (pre/post), Acquisition Plan, Source Selection Plan, Evaluation Worksheets, DHS 700-22, COR Nomination, Security Requirements, ITAR Documentation
- **UCF assembly**: Sections A through M populated and cross-referenced per FAR 15.204
- **Coexistence principle**: FedProcure generates/validates/assembles — PRISM or any contract writing system handles official entry
- **Dependencies**: Phase 26 (restructured drafting workspace)

### Phase 28: Lineage Extension — Full Traceability (Weeks 21–23)
- **Extends Phase 10** Evidence Lineage Ledger: requirement → market research finding → PWS section → CLIN → Section L → Section M → evaluator score → SSDD → QASP → CPARS
- **Modification impact analysis**: change to any node traces forward through entire chain, identifies all affected documents
- **Protest model v3**: decision text embeddings (TF-IDF / transformer features from 716 decision texts) as additional features
- **Dependencies**: Phase 27 (full document chain), Phase 14 (impact analysis)

## Phase 23a: Market Research Agent (2026-04-03) — COMPLETE

### MarketResearchAgent (backend/core/market_research_agent.py, ~520 lines)
- **6-section FAR 10.002 report**: Comparable Awards, Active Market Scan, Small Business Availability, Commercial Assessment, Pricing Intelligence, Protest Context
- **Input contract**: MarketResearchRequest (NAICS, PSC, agency, sub_agency, estimated_value, services, it_related)
- **PIL_RATES**: 15 DHS labor categories with min/max/avg benchmark rates
- **PROTEST_RATES_BY_VALUE**: 5 brackets (under_sat through 100m_plus)
- **PROTEST_RATES_BY_AGENCY**: 9 DHS sub-agencies
- **SetAsideRecommendation**: rule-of-two logic with priority ordering (total_sb > 8a > sdvosb > hubzone > wosb > full_and_open)
- **Commercial assessment**: FAR 12.101 applicability, SAP threshold ($9M for commercial IT)
- **FTE estimation**: estimated_value / (avg_rate × 1920 billable hours)
- **report_to_dict()**: full serialization for API response
- **40/40 tests** across 10 classes (0.06s)

## Phase 23b: Evaluation Factor Derivation Engine (2026-04-03) — COMPLETE

### EvalFactorDerivationEngine (backend/core/eval_factor_derivation.py, ~620 lines)
- **7-step pipeline**: PWS analysis → requirement classification → factor candidate generation → subfactor mapping → weight suggestion → adjectival definition drafting → protest-proofing check
- **Step 1-2**: parse_pws_requirements() with CATEGORY_KEYWORDS (7 categories, 100+ keywords), classify_requirement(), extract_keywords(), SLA extraction
- **Step 3**: generate_factor_candidates() maps to STANDARD_FACTORS (Technical Approach, Management Approach, Past Performance, Price/Cost per FAR 15.304)
- **Step 4**: map_subfactors() — Past Performance gets Relevance/Quality; Technical/Management get keyword-grouped subfactors; Price gets Total Evaluated Price
- **Step 5**: suggest_weights() — tradeoff weights scale with value ($20M+ → tech 40%, price 20%; $50M+ → tech 45%, price 15%); LPTA → price 60%, tech 20%
- **Step 6**: draft_adjectival_definitions() — 5-level scale (Outstanding through Unacceptable) with unique discriminators per adjacent pair; separate past performance template ("expectation" language)
- **Step 7**: run_protest_proofing() — 6 automated validations:
  - PP-01: L→M traceability (FAR 15.204-5)
  - PP-02: M→PWS traceability (FAR 15.304(c))
  - PP-03: No unstated criteria (FAR 15.304)
  - PP-04: Adjectival distinguishability (GAO case law)
  - PP-05: Price/technical weight consistency (FAR 15.101-1)
  - PP-06: Past performance questionnaire alignment (FAR 15.304(c)(2))
- **Tier 2**: SSA accepts/modifies/overrides all outputs
- **Tier 3**: SSA makes final factor selection, relative importance, adjectival approval per FAR 15.308
- **derivation_to_dict()**: full serialization
- **55/55 tests** across 10 classes (0.08s)

## Security Sub-Tree Expansion (2026-04-03) — COMPLETE

### security_subtree.py (backend/core/security_subtree.py, ~250 lines)
- Pattern 2: Expands D120 into 8 conditional sub-codes (D120.01–D120.08)
- D120.01 Personnel Security, D120.02 FISMA/SSP, D120.03 FedRAMP, D120.04 TWIC, D120.05 SSI, D120.06 Incident Response, D120.07 Data Classification, D120.08 Cyber Posture
- NON_WAIVABLE_SUBCODES: D120.01, D120.02, D120.04, D120.05 (blocking at Solicitation gate)
- D142 alias → D120.03 for backward compatibility
- OR conditions: D120.01 (on_site OR classified), D120.06 (is_it OR handles_pii), D120.07 (has_cui OR classified)
- D120.08 value threshold: > $5.5M
- Auto-inference: is_tsa from sub_agency, handles_security_info for TSA IT
- enrich_completeness_with_security(): post-processes completeness validator output
- **38/38 tests** across 7 classes (0.06s)

## Compliance Overlay Engine (2026-04-03) — COMPLETE

### compliance_overlay.py (backend/core/compliance_overlay.py, ~480 lines)
- Pattern 3: Per-section compliance checking against FAR/HSAR/TSA directives
- **20 compliance rules**: 5 PWS (PBA, metrics, AP reference, NIST 800-53, CUI/SSI), 4 Section L (structure, traceability, past perf refs, page limits), 5 Section M (factors, adjectival defs, SSA citation, LPTA rationale, price factor), 3 QASP (structure, PWS mapping, corrective action), 3 IGCE (methodology, comparables, cost data)
- **ComplianceLevel**: GREEN (100), YELLOW (70), RED (30), BLACK (0)
- **Source weights**: FAR 40%, HSAR 35%, TSA 25%
- Content analysis: _check_prescriptive(), _check_metrics(), _check_section_structure(), _check_keyword_present()
- Rule applicability: min_value, requires_services, requires_it filters
- ComplianceOverlayEngine.evaluate_document() and evaluate_all() methods
- Blocking classification: MAJOR and MISSING → blocking issues
- Recommended fix order: most blocking issues first
- **66/66 tests** across 8 classes (0.09s)

## Phase 23c: Evaluator Assistance Model (2026-04-03) — COMPLETE

### EvaluatorAssistanceEngine (backend/core/evaluator_assistance.py, ~620 lines)
- **Three-panel presentation** per evaluation factor per offeror:
  1. **Solicitation Requirements Panel**: Section L instruction, Section M factor/subfactor, adjectival definitions (what each rating means for this factor)
  2. **Offeror Submission Panel**: registered proposal excerpts mapped to factor, addressed/unaddressed subfactor tracking, page compliance check
  3. **Preliminary Observations Panel** (Tier 2): AI-flagged potential strengths, weaknesses, deficiencies, discussion questions, information gaps
- **Observation generation**: keyword-based pattern matching against registered excerpts
  - STRENGTH_INDICATORS: 10 patterns (exceeds, innovative, superior, proven track record, best practice, etc.)
  - WEAKNESS_INDICATORS: 10 patterns (limited detail, does not fully, unclear, insufficient, vague, etc.)
  - DEFICIENCY_INDICATORS: 7 patterns (fails to, does not address, missing required, non-compliant, etc.)
  - Discussion questions generated when no excerpts address a subfactor
  - Information gaps generated when no excerpts registered at all
  - Confidence scoring: 0.7 (strength/weakness), 0.8 (deficiency), 0.5 (discussion/gap)
- **All observations carry**: `requires_evaluator_judgment = True` — Tier 2 boundary enforced

### SSDD Enhancement (ssdd_enhancement)
- **Factor-by-factor comparison**: per-offeror rating with S/W/D counts, relative ranking
- **Discriminator identification**: _identify_discriminators() finds factors where offerors received different ratings
- **Tradeoff narrative**: _draft_tradeoff_narrative() per-factor comparison, _draft_overall_tradeoff() for full analysis
- **LPTA mode**: simplified narrative (lowest-priced technically acceptable, no tradeoff)
- **Price/technical relationship**: documents whether price differential justifies technical difference per GAO case law
- **Excluded offeror documentation**: rationale preserved in SSDD per FAR 15.306(c)
- **Tier 3 notice**: "FedProcure does NOT recommend an awardee" — always present

### Tier 3 Hard Stops — Evaluator Assistance
- `assign_rating()` **ALWAYS raises Tier3EvalAssistanceError** — cites FAR 15.305 and FAR 7.503(b)
- `determine_swd()` **ALWAYS raises Tier3EvalAssistanceError** — cites FAR 15.305(a)
- `recommend_awardee()` **ALWAYS raises Tier3EvalAssistanceError** — cites FAR 15.308 and FAR 7.503(b)(1)
- Tier3EvalAssistanceError is distinct from Tier3HardStopError (evaluation workspace) and Tier3PostAwardError

### Key Data Structures
- **PanelType**: SOLICITATION_REQUIREMENTS, OFFEROR_SUBMISSION, PRELIMINARY_OBSERVATIONS
- **ObservationType**: POTENTIAL_STRENGTH, POTENTIAL_WEAKNESS, POTENTIAL_DEFICIENCY, DISCUSSION_QUESTION, INFORMATION_GAP
- **SWDCategory**: STRENGTH, WEAKNESS, DEFICIENCY, SIGNIFICANT_STRENGTH, SIGNIFICANT_WEAKNESS
- **ComparisonDimension**: TECHNICAL_RATING, SWD_COUNT, PRICE, OVERALL
- **Serialization**: presentation_to_dict(), ssdd_to_dict() for API response and frontend consumption

### Integration Points
- Consumes Phase 23b EvalFactor, SubFactor, AdjectivalDefinition structures
- Extends Phase 11 SecureEvalWorkspace — adds structured panels alongside existing scoring interface
- SSDD generation extends Phase 11 draft with factor-by-factor comparison narrative
- Evidence Lineage (Phase 10): observations traceable as evaluator_score precursors

### Test Coverage
- **53 dedicated tests** across 12 classes:
  - TestTier3HardStops (3): assign_rating, determine_swd, recommend_awardee all raise Tier3EvalAssistanceError
  - TestRequirementsPanel (5): basic build, fields, subfactors, methodology, page_limit
  - TestExcerptRegistration (4): register, multiple, different offerors, uploaded_by
  - TestSubmissionPanel (5): basic, addressed/unaddressed subfactors, page compliance exceeded/ok, no excerpts
  - TestObservationGeneration (8): strengths, weaknesses, deficiencies, info gaps, discussion Qs, combined, empty, confidence
  - TestThreePanelPresentation (5): assembly, all panels, tier boundary, serialization, generated_at
  - TestSSDDEnhancement (8): basic gen, factor comparisons, discriminators, relative ranking, tradeoff narrative, LPTA mode, excluded offerors, tier3 notice
  - TestOverallTradeoff (3): tradeoff/LPTA/empty workspace narratives
  - TestPriceTechnical (2): relationship documentation, equal price case
  - TestRatingRank (3): Outstanding>Good>Acceptable ordering
  - TestSerialization (3): presentation_to_dict, ssdd_to_dict, round-trip
  - TestEdgeCases (4): no factors, single offeror, all excluded, unknown factor
- STATUS: **Deployed and verified** — 53/53 tests passing (0.07s)

## Phase 25: Legacy SOW Analyzer (2026-04-03) — COMPLETE

### LegacySOWAnalyzer (backend/core/legacy_sow_analyzer.py, ~750 lines)
- **3-layer analysis pipeline**: Language Quality → Gap Analysis → Protest Vulnerability Scan
- **Input**: Raw SOW text (string) or pre-parsed sections (list of dicts)
- **Output**: AnalysisReport with findings, extracted requirements/deliverables, PBA compliance, and scores

### Layer 1: Language Quality Analyzer
- **Passive voice detection**: 4 regex patterns (be+past participle), flags sections with 2+ instances
- **Vague term detection**: 25 unenforceable terms with specific fix suggestions (as needed, best practices, etc., and/or, may, should, timely, approximately, etc.)
- **Will/shall inconsistency**: detects mixed usage (binding vs predictive), flags sections using only "will" for contractor obligations
- **Prescriptive staffing**: 5 patterns detecting FTE counts, headcount specs — anti-PBA per FAR 37.102

### Layer 2: Gap Analyzer (FAR 37.102 PBA Compliance)
- **8 PBA elements** checked: performance_standards, measurable_outcomes, quality_assurance, performance_incentives, work_requirements, government_furnished, deliverables, period_of_performance
- **PBA score**: 0-100 based on element coverage
- **QASP linkage check**: flags missing QASP reference per FAR 46.4
- **Metrics gap**: flags sections >50 words with no detectable SLAs/KPIs/thresholds
- **Acceptance criteria gap**: flags deliverables without defined acceptance criteria
- **Security completeness**: checks for personnel security, incident response, data handling when security is referenced
- **Verification method gap**: flags when >30% of requirements lack verification method (inspection/analysis/demonstration/test)

### Layer 3: Protest Vulnerability Scanner
- **7 vulnerability patterns** (PV-01 through PV-07):
  - PV-01: Ambiguous evaluation language (CRITICAL — GAO B-414230)
  - PV-02: Unstated evaluation criteria embedded in SOW (CRITICAL — FAR 15.304)
  - PV-03: Cross-section inconsistencies (HIGH — Jaccard similarity detection)
  - PV-04: Missing deliverable acceptance criteria (MEDIUM — FAR 37.602)
  - PV-05: Brand-name/proprietary references (HIGH — FAR 11.105, detects Microsoft/Oracle/SAP/etc.)
  - PV-06: OCI risk — advisory + implementation combined (HIGH — FAR 9.5)
  - PV-07: Prescriptive staffing undermines competition (MEDIUM — FAR 37.102)
- **Cross-section inconsistency detection**: Jaccard word overlap (0.4-0.9) between shall-statements across different sections

### Requirement Extractor
- Extracts "shall" statements as binding requirements
- **5 category classifications**: technical, management, reporting, security, transition (keyword-based)
- **Priority inference**: critical/standard/desirable from requirement language
- **Verification method inference**: test, demonstration, analysis, inspection
- **Metric detection**: percentages, time SLAs, business day deadlines, uptime targets
- **Acceptance criteria extraction**: when explicitly stated in requirement text

### Deliverable Extractor
- Pattern-based extraction: submit/deliver/provide + name patterns, frequency patterns (daily through one-time)
- **Format detection**: PDF, Word, Excel, template references
- **Review period extraction**: "X business/calendar days for review"
- **Approval authority detection**: COR, CO references in context
- **Deduplication**: by normalized deliverable name

### Scoring Engine
- **Quality score** (0-100): starts at 100, deducts per language finding (CRITICAL -15, HIGH -8, MEDIUM -3, LOW -1)
- **Gap score** (0-100): 50% PBA element coverage + 50% gap finding penalty
- **Protest risk score** (0-100): sum of protest-relevant finding penalties (higher = more risk)
- **Overall score**: quality (30%) + gap (40%) + (100 - protest_risk) (30%)
- **Fix priority ordering**: CRITICAL → HIGH → MEDIUM → LOW

### Serialization
- `report.to_dict()`: full JSON-serializable output with sections, findings, requirements, deliverables, PBA elements, scores, severity counts, fix priority
- Section content truncated to 200 chars in serialization (full content preserved in object)

### Test Coverage
- **64 dedicated tests** across 13 classes:
  - TestSOWParser (9): parse canonical, section IDs, levels, word counts, metrics/security/deliverable tagging, empty, no headings
  - TestLanguageQuality (6): vague terms, will/shall inconsistency, only-will, staffing spec, etc severity, clean section
  - TestGapAnalysis (6): missing PBA elements, full PBA score, no QASP, no metrics, missing acceptance, incomplete security
  - TestProtestVulnerability (6): preference language, brand name, OCI risk, cross-section inconsistency, deliverables without acceptance, clean section
  - TestRequirementExtraction (7): shall statements, sequential IDs, technical/reporting classification, metric detection, verification inference, source tracking
  - TestDeliverableExtraction (4): canonical extraction, frequency detection, format detection, deduplication
  - TestScoring (5): perfect quality, quality degradation, protest risk scaling, severity counts, weighted overall
  - TestFullPipeline (8): canonical SOW, all layers present, deliverable extraction, PBA elements, empty/minimal/prescriptive SOW, section-based input
  - TestSerialization (5): dict structure, fix priority ordering, scores, PBA elements, finding fields
  - TestEdgeCases (5): no shall statements, single sentence, generated_at, requires_acceptance, source provenance
  - TestProtestRelevance (3): etc protest-relevant, preference language protest-relevant, clean SOW low risk
- STATUS: **Deployed and verified** — 64/64 tests passing (0.10s), 316/316 total across all new modules

## Phase 24: Requirements Elicitation Agent (2026-04-03) — COMPLETE

### RequirementsElicitationAgent (backend/core/requirements_elicitation.py, ~800 lines)
- **Two entry points**: greenfield (blank-slate guided intake) and legacy (Phase 25 SOW Analyzer import)
- **Output**: RequirementsPackage — structured requirements matrix with policy derivation, validation, and serialization

### IntakeEngine — 36 Staged Questions, 10 Groups
- **Groups**: BASIC_INFO (8), SCOPE_DEFINITION (5), TECHNICAL_REQUIREMENTS (4), MANAGEMENT_REQUIREMENTS (3), SECURITY_REQUIREMENTS (5), PERSONNEL_REQUIREMENTS (2), DELIVERABLES (2), PERFORMANCE_STANDARDS (2), TRANSITION (2), CONSTRAINTS (3)
- **Question types**: text, number, boolean, select, multi_select
- **Validation**: required check, type check (number/boolean/select), regex (NAICS 6-digit), unknown question detection
- **Completeness**: per-group and overall percentage based on required fields answered
- **FAR references**: 15 questions cite specific FAR/HSAR/TSA authorities
- **Q-code drivers**: 12 questions link to specific Q-code decision nodes

### ParameterDeriver — Answer→PolicyService Mapping
- Converts 36 intake answers to 20 PolicyService-compatible params
- Value, services, it_related, sole_source, commercial_item, vendor_on_site, classified, on_site
- NAICS, contract_type, competition_type, sub_agency (default TSA)
- has_options, has_oci_concern, has_key_personnel, has_gfe
- handles_ssi, has_cui, requires_fedramp, requires_badge

### RequirementsGenerator — Requirement & Deliverable Generation
- **Requirement generation**: technical outcomes (split on ;/newline), systems, integration, availability, key personnel, reporting, security (clearance/SSI/FISMA), SLAs, transition (in+out), QCP (auto for services), GFE
- **Sequential IDs**: REQ-001 through REQ-NNN
- **Category classification**: TECHNICAL, MANAGEMENT, REPORTING, SECURITY, TRANSITION, QUALITY, PERSONNEL, GENERAL
- **PWS section mapping**: 3.x (technical), 4.x (reporting), 5.x (management), 6.x (security), 7.x (transition), 8.x (general)
- **QASP method mapping**: automated_monitoring, periodic_assessment, 100_percent_inspection
- **Deliverable generation**: status reports (auto), QCP (auto), transition plan (if incumbent), custom from DL-01
- **Frequency inference**: daily/weekly/monthly/quarterly/annually/as_needed from deliverable name

### RequirementsValidator — 8 Validation Checks
1. Key personnel not specified for $20M+ (medium)
2. T&M/LH on high-value >$5.5M (high, cites FAR 16.601(d))
3. Services without SLAs (high, cites FAR 37.102)
4. Clearance without badge access (low)
5. IT without FISMA/FedRAMP (high, cites FISMA 2014)
6. No scope defined (critical)
7. Sole source >$250K without J&A (high, cites FAR 6.303/6.304)
8. No requirements generated (critical)
9. Deliverables without acceptance criteria (medium, cites FAR 46.2)
10. Recompete without transition planning (medium)

### LegacySOWImporter — Phase 25 Integration
- Imports LegacySOWAnalyzer.to_dict() output
- Maps categories (technical→TECHNICAL, etc.), priorities (critical→MUST, standard→SHOULD), verification methods
- Pre-populates answers from PBA elements (BI-03, SD-04, PS-01, SR-01) — never overwrites existing
- Security inference from section analysis
- SOW requirements get SOW-REQ-NNN IDs, deliverables get SOW-DLV-NNN IDs

### Approval Chain Derivation (TSA C&P Feb 2026)
- **BCM**: <$500K CO | $500K-$5M BC | $5M-$20M DD | $20M-$50M DAA | $50M+ HCA
- **SSA**: <$2.5M CO | $2.5M-$5M BC | $5M-$20M DD | $20M-$50M DAA | $50M+ HCA
- **Posting**: micro=none | sole source=award notice 30d | <SAT=reasonable | >SAT=30-day SAM.gov
- **Timeline**: <SAT 6-12wk | sole source 8-16wk | <$5.5M 4-6mo | <$50M 6-12mo | $50M+ 12-18mo

### Orchestrator — RequirementsElicitationAgent
- `get_intake_groups()`: 10 groups with metadata
- `get_questions(group)`: questions with serialized fields
- `get_next_group(completed)`: progressive disclosure
- `process_answers(answers)`: full pipeline (derive → generate → deliverables → policy → validate → completeness)
- `import_legacy_sow(report, existing_answers)`: legacy SOW → elicitation flow with dedup
- **Status logic**: COMPLETE if completeness ≥80% and no critical issues; IN_PROGRESS otherwise
- **Contract type notes**: T&M/LH → D&F warning; CPAF → award fee plan warning

### Test Coverage
- **100 dedicated tests** across 12 classes:
  - TestIntakeQuestions (6): count (36), groups covered, index complete, unique IDs, group order, group names
  - TestIntakeEngine (18): get questions, get groups, next group (none/some/all), validate (required/text/number/boolean/select/regex/unknown/optional), group completeness, overall completeness
  - TestParameterDeriver (6): canonical params, sole source flag, supplies, remote location, security flags, invalid value
  - TestRequirementsGenerator (12): canonical count, sequential IDs, outcome split, system support, integration, security clearance, transition, QCP for services, GFE, no QCP for supplies, reporting always, SLA split
  - TestDeliverableGeneration (5): canonical count, status report always, transition plan, custom parsed, frequency inference
  - TestRequirementsValidator (9): no critical on canonical, missing scope, key personnel $20M, T&M warning, no SLAs, no FISMA, sole source J&A, recompete transition, clearance without badge
  - TestApprovalChains (11): BCM chains (4 tiers), SSA (2 tiers), posting (3 scenarios), timeline (2 scenarios)
  - TestLegacySOWImporter (7): import requirements, import deliverables, pre-populate answers, no overwrite, metrics PS-01, category mapping, priority mapping
  - TestRequirementsElicitationAgent (14): canonical, minimal, title, policy, T&M notes, CPAF notes, legacy import, legacy with existing, dedup deliverables, groups, questions, next group, status complete, status in-progress
  - TestSerialization (5): dict structure, requirements, policy, status string, source provenance
  - TestEdgeCases (5): empty answers, zero value, requires_acceptance, generated_at, no clearance
- STATUS: **Deployed and verified** — 100/100 tests passing (0.12s), 416/416 total on Spark (0.29s)

## Phase 26: Drafting Workspace Restructure (2026-04-03) — COMPLETE

### Controlled Drafting Workspace (backend/phase2/drafting_workspace.py, ~945 lines)
- **Satisfies existing 35 Phase 9 tests** — backward-compatible reimplementation
- **5 document type engines**: PWS, IGCE, Section L, Section M, QASP
- **Propose/Redline/Explain model**: every section has content + authority + confidence + rationale + source provenance
- Per-section accept/modify/override by CO
- Regeneration produces redlines against prior version automatically
- DiffEngine: section-by-section unified diff (added/modified/deleted)

### SectionLEngine (Instructions to Offerors)
- 6 standard sections (L.1–L.6) per FAR 15.204-5
- Page limits scale with value ($1M→25pp, $20M→40pp, $50M+→60pp)
- Past performance references scale (3–5 refs based on value)
- Commercial item flag adds L.7 (FAR Part 12 streamlined procedures)

### SectionMEngine (Evaluation Factors)
- **Tradeoff** template: 6 sections per FAR 15.101-1
- **LPTA** template: 4 sections per FAR 15.101-2
- Auto-selects tradeoff vs LPTA based on value, complexity, and explicit override
- Tech weight language: "significantly more important" at $20M+
- Custom evaluation factors injection support
- Warning raised for LPTA on $20M+ acquisitions

### QASPEngine
- Generates surveillance items mapped from PWS sections
- Extracts metrics (SLA times, percentages) from PWS content
- Auto-selects surveillance method (100% inspection, automated monitoring, random sampling, periodic assessment)
- Progressive remedy chain: CAR → Cure Notice → Default

### PWSEngine
- SOW→PWS conversion: detects will/shall, vague language, staffing specs, passive voice
- Template-based generation when no SOW provided
- Background, applicable documents, scope, service delivery, reporting, transition, QC sections

### IGCEEngine
- DHS PIL benchmark rates (15 labor categories)
- Labor rate analysis table (benchmark + burdened rates)
- Comparable contract analysis framework
- Cost data section at $2.5M+ per FAR 15.403

### Drafting Orchestrator (backend/core/drafting_orchestrator.py, ~720 lines)
- **10-stage pipeline**: market_research → requirements → factor_derivation → pws → igce → section_l → section_m → qasp → compliance → ucf_assembly
- **PipelineStage enum**: 10 stages with ordering
- **UCFSection enum**: Sections A through M per FAR 15.204
- **EngineInput/EngineOutput**: standardized contracts for all engine adapters

### VersionStore (In-Memory Version Control)
- `save(package_id, stage, output, metadata)`: stores versioned output with auto-increment
- `get_latest(package_id, stage)`: retrieves most recent version
- `get_version(package_id, stage, version)`: retrieves specific version
- `get_history(package_id, stage)`: full version list with metadata
- `rollback(package_id, stage, version)`: restores prior version as new save
- `diff(package_id, stage, v1, v2)`: section-by-section diff between versions
- Separate version sequences per package × stage combination

### Engine Adapters (7 adapters)
- `run_market_research()`: MarketResearchAgent → EngineOutput (section_number→section_id, far_authority, dict content serialized, findings→rationale, confidence 0-1→0-100)
- `run_requirements()`: RequirementsElicitationAgent → EngineOutput (passthrough with canonical params)
- `run_factor_derivation()`: EvalFactorDerivationEngine → EngineOutput (7-step pipeline results)
- `run_pws()`: PWSEngine via DraftingWorkspace → EngineOutput
- `run_igce()`: IGCEEngine via DraftingWorkspace → EngineOutput
- `run_section_l()`: SectionLEngine via DraftingWorkspace → EngineOutput
- `run_section_m()`: SectionMEngine via DraftingWorkspace → EngineOutput (eval factors from factor_derivation injected)
- `run_qasp()`: QASPEngine via DraftingWorkspace → EngineOutput (PWS output from context injected)
- `run_compliance()`: ComplianceOverlayEngine → EngineOutput (post-generation validation)

### UCF Assembly
- `UCF_STAGE_MAP`: maps PipelineStage → (UCFSection, FAR authority)
  - pws → Section C (FAR 15.204-2), igce → Section B (FAR 15.204-2), section_l → Section L (FAR 15.204-5), section_m → Section M (FAR 15.204-5), qasp → Section J (FAR 15.204-2)
- `assemble_ucf()`: maps generated documents to UCF sections, sorted by section order
- Each UCF entry: section letter, title, FAR authority, generated_from stage, section count

### PipelineContext
- Accumulates outputs as pipeline progresses
- Inter-engine data flow: PWS feeds QASP, requirements feed downstream, eval factors feed Section M
- `get_output(stage)` for downstream engines to consume upstream results

### DraftingOrchestrator
- `run(params, stages=None)`: executes full or custom pipeline, stores versions, returns PipelineResult
- `run_stage(stage, params, context)`: execute individual stage
- Stage dispatch via `_STAGE_RUNNERS` dict
- Warning collection across all stages
- Source provenance deduplication
- `PipelineResult.to_dict()`: full serialization (documents, versions, UCF, warnings, provenance)

### Test Coverage
- **54 dedicated tests** across 9 classes:
  - TestVersionStore (14): save/retrieve, latest, specific version, history, rollback, diff (modified/added/deleted), version count, separate packages/stages, empty, metadata
  - TestEngineAdapters (10): run_pws, run_igce, run_section_l, run_section_m, run_qasp_with_pws, run_requirements passthrough/empty, tradeoff at $20M, page limits, cost data section
  - TestPipelineExecution (8): full pipeline, documents generated, custom stages, version store, serialization, warnings, provenance dedup, timestamp
  - TestInterEngineDataFlow (3): PWS feeds QASP, requirements feed downstream, eval factors feed Section M
  - TestUCFAssembly (5): mapping, ordering, authorities, stage map complete, serialization
  - TestComplianceIntegration (4): structure, stages defined, fallback on import error, compliance in pipeline
  - TestPipelineContext (2): initialization, accumulates
  - TestEdgeCases (8): empty stages, single stage, minimal params, multiple runs, version diff, default stages, unknown stage, nonexistent versions
- **35 existing Phase 9 tests**: all passing (backward-compatible reimplementation)
- STATUS: **Deployed and verified** — 54/54 orchestrator + 35/35 drafting workspace tests passing on Spark (0.08s combined)

## Phase 27: Full Document Chain Generation (2026-04-03) — COMPLETE

### Document Engines (backend/core/document_engines.py, ~1,100 lines)
- **10 new document engines** following Propose/Redline/Explain model
- **DraftSection dataclass**: section_id, heading, content, authority, rationale, confidence
- **DocumentDraft dataclass**: doc_type, sections, warnings, source_provenance, requires_acceptance, generated_at
- **Factory functions**: `generate_document(doc_type, params)` and `generate_full_chain(params)`

### 10 Engine Details
1. **JAEngine** (J&A — FAR 6.302/6.304): 8 sections, 7 FAR 6.302 authority types, approval ladder per TSA Feb 2026 thresholds, legal sufficiency note >$500K, cost analysis section >$2.5M
2. **BCMEngine** (Business Clearance Memorandum — IGPM 0103.19): Sections A–H, 27-item Section G compliance checklist with FAR/HSAM citations, 5 BCM types (streamlined/pre-competitive/pre-post-sole/pre-post-competitive/OTA), Key Highlights timeline, approval chains per value bracket
3. **DFEngine** (Determination & Findings): 4 sections, 6 D&F types (contract_type_authority, urgency, incentive, single_award_idiq, option_exercise, public_interest), type-specific approvers per Feb 2026 thresholds
4. **APEngine** (Acquisition Plan — HSAM Appendix Z / TSA MD 300.25): HSAM Appendix Z structure, FITARA/CIO review for IT, milestone timeline (competitive vs sole source), small business subcontracting plan >$900K, approval per value/contract type matrix
5. **SSPEngine** (Source Selection Plan — FAR 15.303): 6 sections, tradeoff vs LPTA methodology, SSA appointment per value bracket, adjectival rating scale, Tier 3 notice (SSA makes independent decision)
6. **SBReviewEngine** (DHS Form 700-22): 3 sections, 23 form items, $100K trigger, bundling review >$2M, SBA PCR >$2M unrestricted, set-aside recommendation logic
7. **CORNomEngine** (COR Nomination — TSA MD 300.9): 4 sections, 3 certification levels (I/II/III by value), 3 required signatures, Tier 3 COR limitations (cannot obligate funds, issue mods, etc.)
8. **EvalWorksheetEngine** (FAR 15.305): per-factor worksheets, tradeoff vs LPTA rating scales, S/W/D fields, summary/instructions sections
9. **AwardNoticeEngine** (FAR 5.301 / DHS 2140-01): competitive (3 sections: successful/unsuccessful/synopsis) vs sole source (2 sections), debriefing rights per FAR 15.506, SAM.gov posting >$25K
10. **SecurityReqEngine** (HSAR 3052.204-71/72): conditional sections for personnel security, IT security, SSI, CUI, incident response, HSAR clauses

### Constants & Helpers
- **BCM_APPROVAL_CHAINS**: 5 value brackets (<$500K through $50M+)
- **SSA_APPOINTMENT**: 5 value brackets (<$2.5M through $50M+)
- **JA_APPROVAL_LADDERS**: 4 tiers (<$250K through $20M+)
- **AP_APPROVAL**: 6 brackets with FFP exemption under $50M
- **FAR_6302_AUTHORITIES**: 7 other-than-full-and-open authorities
- **SECTION_G_CHECKLIST**: 27 items with FAR/HSAM citations
- **FORM_700_22_ITEMS**: 23 items in 3 sections
- **PIL_RATES**: 15 DHS labor categories with benchmark rates
- Helper functions: `_get_bcm_approval()`, `_get_ssa_appointment()`, `_get_ja_approval()`, `_get_ap_approval()`, `_format_value()`, `_estimate_fte()`

### generate_full_chain() Logic
- **Always generated**: BCM, SSP, eval_worksheet, award_notice, security_requirements
- **Conditional**: cor_nomination (services), sb_review (>$100K), ja (sole source), df (T&M/LH), ap (OTFFP above SAT or any above $50M)
- FFP under $50M → no AP (HSAM 3007.103(e))
- FFP → no D&F for contract type authority
- Competitive → no J&A

### Document Chain Orchestrator (backend/core/document_chain.py, ~240 lines)
- **Composition pattern**: wraps existing DraftingOrchestrator without modification (preserving 89 existing tests)
- **SUPPORT_DOC_UCF_MAP**: maps 10 doc types to UCF sections (bcm→G, ja→J, df→J, ap→J, ssp→J, sb_review→K, cor_nomination→G, eval_worksheet→J, award_notice→G, security_requirements→H)
- **ChainResult dataclass**: package_id, pipeline_result, supporting_docs, full_ucf_assembly, total_documents, total_sections, warnings, generated_at, approval_summary
- **DocumentChainOrchestrator.generate()**: runs base pipeline + supporting docs + combined UCF assembly + version store + approval summary
- **generate_single()**: generate individual supporting doc by type
- **_derive_approval_summary()**: BCM approver, SSA appointment, J&A approver (if sole source) from params
- **list_available_doc_types()**: returns all 10 doc types with descriptions
- **UCF assembly**: base pipeline UCF + supporting doc UCF entries, sorted by section order

### Test Coverage
- **110 dedicated tests** in test_document_engines.py across 15 classes:
  - TestHelpers (9): BCM approval (4 brackets), J&A approval, SSA appointment, AP approval, format_value, estimate_fte
  - TestJAEngine (11): 8 sections, approval at $20M (DHS CPO), FAR 6.302 authorities, cost analysis, legal sufficiency, market research, urgency type
  - TestBCMEngine (11): sections A–H, 27-item Section G, approval chain, timeline, sole source, streamlined, pre-competitive, pricing, AP/J&A applicability
  - TestDFEngine (7): 4 sections, all D&F types, approvers (urgency/public interest), T&M authority, option exercise, urgency warning
  - TestAPEngine (8): canonical sections, approval chain, FITARA/CIO, milestones, small business threshold, no FITARA non-IT
  - TestSSPEngine (8): 6 sections, tradeoff/LPTA methodology, SSA at $20M (DAA), rating methodology, custom factors, Tier 3 notice
  - TestSBReviewEngine (6): 3 sections, 23 form items, $100K trigger, bundling $2M, SBA PCR, sole source set-aside
  - TestCORNomEngine (6): 4 sections, certification levels I/II/III, 3 signatures, Tier 3 limitations
  - TestEvalWorksheetEngine (7): sections, tradeoff/LPTA ratings, instructions, summary, S/W/D fields, custom factors
  - TestAwardNoticeEngine (6): competitive 3 sections, debriefing rights, DHS 2140, SAM.gov posting, sole source no unsuccessful letter, under-SAT optional
  - TestSecurityReqEngine (8): multiple sections, personnel/IT/SSI/CUI/incident response, HSAR clauses, minimal security
  - TestDocumentDraft (2): generated_at, to_dict
  - TestGenerateDocument (5): all doc types, BCM/AP/JA/competitive warnings
  - TestGenerateFullChain (11): canonical chain, count, no AP FFP, no D&F FFP, no J&A competitive, sole source J&A, T&M D&F/AP, >$50M AP, micro minimal, all DocumentDraft
  - TestEdgeCases (5): all sections have authority, registry, missing params graceful, very high value, zero value
- **25 dedicated tests** in test_document_chain.py across 8 classes:
  - TestChainOrchestrator (9): generate supporting only, canonical docs, specific types, skip supporting, UCF assembly, UCF ordering, total counts, warnings, generated_at
  - TestApprovalSummary (2): canonical (BCM=DAA, SSA=DAA), sole source (J&A=DHS CPO)
  - TestSerialization (3): chain result, supporting docs, UCF assembly
  - TestSingleDocument (3): single BCM, single J&A (8 sections), unknown raises ValueError
  - TestListDocTypes (2): returns 10, each has description
  - TestUCFMapCoverage (2): all engines mapped, valid UCF sections
  - TestVersionStoreIntegration (1): supporting docs versioned
  - TestEdgeCases (3): invalid doc type warns, micro-purchase minimal chain, empty params
- STATUS: **Deployed and verified** — 135/135 tests passing on Spark (0.06s)

## Phase 28: Lineage Extension — Full Traceability (2026-04-03) — COMPLETE

### FullTraceabilityLedger (backend/core/lineage_extension.py, ~750 lines)
- **Composition pattern**: wraps EvidenceLineageLedger without modification (all Phase 10/13/14 tests untouched)
- **10-stage extended chain**: market_research → requirement → CLIN → Section L → Section M → evaluator_score → SSDD → QASP → CPARS → closeout (up from 8)
- **5 major capabilities**: market research integration, document chain registration, cross-document dependency graph, modification impact analysis, full build orchestration

### Extended Chain Stages (10, up from 8)
- NEW: `market_research` (first stage) — anchors chain to FAR 10.002 findings
- NEW: `closeout` (last stage) — closeout verification tracking
- All 8 original stages preserved in order

### Market Research Integration
- `register_market_research()`: creates DOCUMENT node + finding nodes per report section, linked via CONTAINS
- `link_market_research_to_requirements()`: links MR findings to PWS requirement nodes via TRACES_TO
- Finding nodes carry confidence scores, FAR authority, section IDs

### Document Chain Registration (Phase 27 Integration)
- `register_supporting_document()`: registers individual supporting doc with D-code IMPLEMENTS link + section CONTAINS links
- `register_document_chain()`: imports full ChainResult (supporting docs + pipeline docs) into lineage
- `SUPPORTING_DOC_DCODES`: 10 doc types → D-code mapping (ja→D106, bcm→D110, ap→D104, ssp→D114, etc.)
- Automatic cross-document dependency links created during registration

### Cross-Document Dependency Graph
- `DOCUMENT_DEPENDENCIES`: static map of 30+ dependency edges across 11 source documents
- **5 dependency types**: CONTENT_SOURCE, APPROVAL_GATE, CROSS_REFERENCE, COMPLIANCE_CHECK, EVALUATION_BASIS
- `build_dependency_graph()`: filters by acquisition params (sole source, services, value thresholds)
- `get_upstream_docs()` / `get_downstream_docs()`: directional graph queries
- PWS has most downstream dependencies (7 direct dependents)
- Blocking dependencies (APPROVAL_GATE): J&A → BCM, BCM → Award Notice

### Cross-Document Consistency Checking
- `check_consistency()`: 6 automated validation checks across document pairs
  1. PWS → Section L: requirements reflected in instructions
  2. Section L → Section M: J-L-M traceability (L.3↔M.2, L.4↔M.3)
  3. Section M → Eval Worksheet: factor alignment
  4. PWS → QASP: surveillance coverage ratio
  5. Security → COR Nomination: security oversight referenced
  6. AP → BCM: acquisition plan referenced in BCM
- `ConsistencyFinding` dataclass: finding_id, severity, source_doc, affected_doc, description, recommendation, authority
- Severity levels: critical (missing L→M link), high (missing coverage), medium (low ratio), low (missing reference)

### Modification Impact Analysis
- `analyze_modification_impact()`: BFS through dependency graph from changed document
- `ModificationImpact` dataclass: affected_documents, affected_chains, severity_summary, dependency_path, recommended_actions
- **requires_re_evaluation**: True if eval_worksheet or section_m affected
- **requires_re_solicitation**: True if pws, section_l, or section_m changed
- PWS change cascades to 5+ documents; leaf docs (award_notice) have zero downstream impact
- J-L-M re-verification action auto-generated when any J-L-M doc changes
- Blocking dependency actions highlighted prominently

### Extended Coverage Computation
- `compute_extended_coverage()`: 10-stage coverage per package
- Market research detected from either lineage nodes or document presence
- Base 8 stages computed from chain coverage ratios
- Closeout detected from closeout document nodes

### Full Build Orchestration
- `build_full_traceability()`: 7-step pipeline
  1. Register market research findings
  2. Build base lineage (Phase 10)
  3. Link market research → requirements
  4. Register document chain (Phase 27)
  5. Build dependency graph
  6. Check cross-document consistency
  7. Compute extended coverage
- `FullTraceabilityResult`: base_ledger, extended_coverage, document_chain stats, dependency_graph, consistency_findings, totals, warnings

### Test Coverage
- **71 dedicated tests** across 12 classes:
  - TestExtendedChainStages (5): 10 stages, market_research first, closeout last, base preserved, ordering
  - TestDocumentDependencyGraph (8): PWS most dependents, all types used, canonical build, sole source/competitive J&A, blocking deps, upstream/downstream queries
  - TestSupportingDocDcodes (2): 10 mapped, known mappings correct
  - TestMarketResearchIntegration (6): node creation (4 nodes), doc type, metadata, CONTAINS links, requirement links, empty report
  - TestDocumentChainRegistration (6): register supporting doc, D-code link, section nodes, chain registration, pipeline docs, dependency links
  - TestConsistencyChecking (9): consistent=no critical, missing L, missing M, L-M pair mismatch, QASP coverage, security-COR, BCM-AP reference, required fields, to_dict
  - TestModificationImpact (12): PWS cascades, re-solicitation, re-evaluation, IGCE limited, MR cascades, severity summary, actions, J&A blocking, J-L-M action, to_dict, leaf minimal, unknown empty
  - TestExtendedCoverage (4): empty, MR from nodes, MR from documents, base stages from chains
  - TestFullBuildOrchestration (10): returns result, with MR, with chain, has deps, has findings, has base ledger, generated_at, overall coverage, to_dict, minimal
  - TestDocumentDependencyDataclass (1): to_dict
  - TestModificationImpactDataclass (1): to_dict
  - TestEdgeCases (7): empty MR, no supporting, empty docs, multiple packages, idempotent, dep round-trip, full result structure
- STATUS: **Deployed and verified** — 71/71 tests passing on Spark (0.09s)

### Build Status Summary
| Phase | Name | Status | Effort |
|-------|------|--------|--------|
| 1–22 | Core Platform (Policy Engine, Dashboard, Evaluation, Post-Award, Data Pipeline, Protest Models) | **Complete** | — |
| — | Security Sub-Tree (Pattern 2) | **Complete** (38 tests) | 1 session |
| — | Compliance Overlay (Pattern 3) | **Complete** (66 tests) | 1 session |
| 23a | Market Research Agent | **Complete** (40 tests) | 1 session |
| 23b | Evaluation Factor Derivation Engine | **Complete** (55 tests) | 1 session |
| 23c | Evaluator Assistance Model | **Complete** (53 tests) | 1 session |
| 24 | Requirements Elicitation Agent | **Complete** (100 tests) | 1 session |
| 25 | Legacy SOW Analyzer | **Complete** (64 tests) | 1 session |
| 26 | Drafting Workspace Restructure | **Complete** (54+35 tests) | 1 session |
| 27 | Full Document Chain Generation | **Complete** (110+25 tests) | 1 session |
| 28 | Lineage Extension — Full Traceability | **Complete** (71 tests) | 1 session |

### Combined Test Count (new modules, updated 2026-04-03)
| Module | Tests | Time |
|--------|-------|------|
| security_subtree.py | 38 | 0.06s |
| market_research_agent.py | 40 | 0.06s |
| compliance_overlay.py | 66 | 0.09s |
| eval_factor_derivation.py | 55 | 0.08s |
| evaluator_assistance.py | 53 | 0.07s |
| legacy_sow_analyzer.py | 64 | 0.10s |
| requirements_elicitation.py | 100 | 0.12s |
| drafting_workspace.py | 35 | 0.04s |
| drafting_orchestrator.py | 54 | 0.04s |
| document_engines.py | 110 | 0.04s |
| document_chain.py | 25 | 0.02s |
| lineage_extension.py | 71 | 0.09s |
| **Total** | **711** | **0.52s** |

## NOT Yet Capable Of
- Re-run description enrichment for cross-matched protests (SAM.gov rate limit reset needed)
- Award/SAM.gov solicitation cross-matching for protests (temporal gap — SAM.gov data is Sept 2025+, protests on older solicitations; 91 non-protest overlaps exist)
- Frontend for USAspending award analytics / cross-match explorer / mod timeline
- Tango delta sync for page 135 (~100 missing records from 502 failures)
- Re-run cross-match with updated GAO data (new sub-agency + outcome data may improve matching)
- Interactive eval_factors / sustain_grounds input on frontend (currently hardcoded defaults)
