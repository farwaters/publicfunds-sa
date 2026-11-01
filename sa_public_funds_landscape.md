# South African Public Funds Tracking: Landscape, Coverage & Gap Analysis

*Prepared for the owner, 19 October 2026 (SAST, UTC+2). Research by Grok Bot.*

**Method.** Live web research (WebSearch/WebFetch, X search, direct HTTP checks and a hands-on profile of the eTenders OCDS dataset) on 19 Oct 2026. Every factual claim carries a source URL. Items I could not confirm are marked **[unverified]**. "Liveness" = HTTP check from the research box on 19 Oct 2026. Some government sites (Stats SA, SIU, Public Protector, DMRE legacy site, Vulekamali datastore) blocked or timed out on automated requests. That is noted, but it does **not** mean they are offline for human users.

---

## 0. Executive summary

1. **The raw material is better than most people think, but it is scattered across islands.** SA has a strong budget-transparency base (Open Budget Survey 2023 transparency score 83/100, 4th of 125 countries; https://www.internationalbudget.org/open-budget-survey/country-results/2023/south-africa). It has open municipal finance data (18 years, 292 municipalities, ~85m facts, JSON API; https://municipaldata.treasury.gov.za/) and OCDS procurement data (https://data.etenders.gov.za/). Nobody joins budget, procurement, payments, audit findings, enforcement and ownership into one view.
2. **The biggest new development is Treasury's *Procurement Payments Dashboard* (Nov 2025, v2 Feb 2026).** It is the first public release of **transaction-derived payment data** for national and provincial departments from 1 April 2018. It includes supplier, commodity (UNSPSC/SCOA/MIIN) and, for LOGIS departments, **average price per unit**, plus a downloadable `Procurement_Spend_Transaction_List.csv`. The catch: it is aggregated per entity × supplier × item × year, delivered as Power BI, and excludes SOEs, municipalities, Defence, SAPS, SARS, SSA and provincial legislatures (https://data.etenders.gov.za/Home/DownloadFile/?fileName=Procurement+Payments+Dashboard+User+Guide+Feb+2026.pdf). PFMA SCM Instruction 10 of 2025/26 already requires **public entities** to submit monthly transaction-level payments through an OCPO API/Data Upload Tool (https://ocpo.treasury.gov.za/Legislation/Instruction%20Notes/PFMA%20SCM%20Instruction%20No.%2010%20of%202025-26%20Enhancing%20Procurement%20Information%20Transparency.pdf). That pipeline is the single most important lever for the north star.
3. **The legal path to invoice-level and beneficial-ownership disclosure has just been lost.** Section 31 of the Public Procurement Act 2024 required central, free, interoperable publication of bids, bidder identities, **beneficial ownership of winners**, contracts and **supplier invoices** (https://publicprocurementact.co.za/public-procurement-act/chapter-5/part-3/section-31/). On **17 Sep 2026 the Constitutional Court declared the whole Act invalid** for inadequate public participation, without suspending the order (https://www.citizen.co.za/news/south-africa/courts/concourt-public-procurement-act-parliament/). Treasury's draft regulations of 16 Apr 2026 (https://www.treasury.gov.za/public%20comments/ProcReg/GG%20No%2054528%20Notice%20Draft%20General%20Public%20Procurement%20Regulations,%202026.pdf) are therefore moot until a new Bill is passed.
4. **Beneficial ownership is closed.** The CIPC BO register (3m+ filings) is restricted to law enforcement and accountable institutions. The CIPC Commissioner publicly called for it to be opened in March 2026 (https://www.businessday.co.za/news/2026-03-05-cipc-head-calls-for-more-beneficial-ownership-transparency/). The Central Supplier Database (directors, bank verification, B-BBEE) is searchable only by organs of state (https://ocpo.treasury.gov.za/buyers_area/Supplier-Management/CSD_Supplier%20Search%20User%20Guide%20Master%202019-06-10.pdf).
5. **Procurement data is far from complete.**
   - **Municipalities and SOEs have no obligation to publish on eTenders** (https://data.etenders.gov.za/Home/LearnMore).
   - The 2024 MAPS assessment found only 12% of eTenders-registered organs uploaded procurement plans and 3% published contract notices (https://www.treasury.gov.za/comm_media/press/2024/MAPS%20Assessment%20South%20Africa.pdf).
   - My profile of the OCDS dataset as mirrored by the OCP Data Registry found the following:
     - 35,309 processes and **0 tender or award line items**, so OCDS cannot be used for unit prices.
     - Only 71% of awards (6,760 of 9,551) carry a value.
     - The Treasury portal itself headlines 70,873 awards, so the API-derived mirror looks incomplete (§5.1).
6. **Irregular expenditure is large, persistent and under-reported.** PFMA 2024-25: R42.58bn, with 33% of auditees qualified on IE completeness or still investigating it, and ~R32bn stuck in Treasury's IE "assessment" process (https://www.agsa.co.za/storage/app/media/reporting/pfma/PFMA-GR-2024-25-Interactive.pdf). MFMA 2024-25: R40.14bn, R145.21bn over four years, with 87% procurement-related (https://mfma-2025.agsa.co.za/report/mfma_report_2024_25.pdf).
7. **There are no known-unknowns dashboards.** Treasury publishes PDF lists of municipalities that failed to submit mSCOA/s71 data (https://mfma.treasury.gov.za/Publications%20and%20Media%20Releases/Section%2071%20Information%20(In-year%20Management,%20Monitoring%20and%20Reporting)/2024-25/4th%20Quarter/PDF/List%20of%20Non-Compliance%20to%20Section%2071%20of%20the%20MFMA%20-%2026%20September%202025.pdf). AGSA lists outstanding audits in its narrative. No tool turns these into a coverage layer.
8. **Unit-price benchmarking is technically feasible but nobody does it publicly.** Benchmarks exist:
   - monthly fuel prices (DMPR): https://www.dmpr.gov.za/Branches/Petroleum-Resources/Fuel-Prices
   - CPI **average prices** and 8-digit indices (Stats SA): https://www.statssa.gov.za/?page_id=1847
   - construction material indices (Stats SA): https://www.statssa.gov.za/publications/P01511/P01511June2026.pdf
   - medicine Single Exit Prices: https://www.health.gov.za/nhi-pee/
   - transversal contract price lists such as RT57 vehicles: https://www.etenders.gov.za/home/Download/?blobName=fb97139c-6af6-4c1d-a5bf-8b0325bae3e0.pdf&downloadedFileName=RT57+User+Manual.pdf

   Real cases show the value. North West Agriculture paid R26.26/l for diesel against a ~R21.33/l market price (https://www.vfplus.org.za/media-releases/north-wests-agricultural-department-pays-21-more-than-market-value-for-tender-diesel/).
9. **Civil-society tooling is thin but moving.**
   - **TenderWatch** (tenderwatch.org) is the closest analogue to the north star. It mirrors eTenders, AGSA annexures, Municipal Money and the restricted-supplier register, and it flags "barred and paid anyway" (2 matches) (https://tenderwatch.org/).
   - **Corruption Watch's Procurement Watch** is application-only (https://www.corruptionwatch.org.za/procurement-watch-a-corruption-watch-project/).
   - **OUTA** has demoed an AI tender-monitoring "firewall" with relationship graphs and price checks, but it is not public and lacks R1.5–2m/month in funding (https://mybroadband.co.za/news/government/663945-firewall-for-stopping-dodgy-tenders-in-south-africa.html).
   - **OpenUp** has funding to keep Municipal Money running until end-2028 (https://openup.org.za/blog/newly-tendered-municipal-money-dashboard).

---

## 1. Landscape table (South African tools)

Legend for **Gran.** (granularity): B = budget/appropriation; A = aggregated actuals; T = transaction-derived; C = contract/award; I = invoice; Au = audit findings; E = enforcement/investigation. **Status**: Active / Stale / Restricted / Demo.

### 1A. Government / official

| # | Tool | URL | Owner | Coverage (level, entities, years) | Gran. | Format / API / bulk | Cadence & status | Red-flag features | Known limitations |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Vulekamali** (budget portal) | https://vulekamali.gov.za/ | National Treasury + IMALI YETHU (https://vulekamali.gov.za/) | National & provincial budgets; ENE, EPRE, adjusted estimates, Appropriation Acts, budgeted vs actual national and provincial expenditure, conditional grants, public entities (https://vulekamali.gov.za/datasets) | B, A | CSV/XLSX datasets; CKAN datastore and OpenSpending-style API historically at data.vulekamali.gov.za (https://www.open.africa/dataset/budgeted-and-actual-national-expenditure) | Front page shows 2026-27 budgets (active). **CKAN datastore returned HTTP 500 / timed out on 19 Oct 2026.** OpenUp's role ended in 2023 and it is now NT + Imali Yethu (https://www.openup.org.za/projects/vulekamali) | None | Programme/economic-classification level only; no suppliers or transactions; datastore reliability uncertain |
| 2 | **National Treasury budget documents & s32 monthly statements** | https://www.treasury.gov.za/comm_media/press/monthly/monthly_2026.aspx | NT | National revenue, expenditure and borrowing monthly (PFMA s32), Tables 1–5 in Excel; latest Sep 2026 statement published 2 Oct 2026 | A | PDF + Excel | Monthly, active | None | Vote-level aggregates only |
| 3 | **Provincial in-year monitoring (IYM)** | https://www.treasury.gov.za/legislation/pfma/circulars/ (IYM circulars) | NT / provincial treasuries | Monthly IYM by national and provincial departments (circular on April 2025 IYM submission listed) | A | Mostly PDF media releases **[detail unverified]** | Quarterly public releases | None | Internal IYM detail not public |
| 4 | **Vulindlela** | https://www.vulindlela.gov.za/ | NT | BAS/PERSAL/LOGIS management information (https://www.cabri-sbo.org/uploads/files/Documents/FMIS-SA-INFORMATION-ARCHITECTURE_ENGLISH_Final.pdf) | T (internal) | Login; approved accounts only | Active, **Restricted** | Internal | Not public; the richest transaction source in government |
| 5 | **eTender Publication Portal** | https://www.etenders.gov.za/ | NT OCPO | Adverts, awards and documents from organs of state that share data; municipalities and SOEs voluntary (https://data.etenders.gov.za/Home/LearnMore) | C | Web + PDF attachments | Daily, active | None | Scanned PDFs; incomplete fields: 91% of a 2019/20 sample lacked bid value and 89% lacked points (https://www.opencitieslab.org/the-state-of-public-procurement-in-south-africa-is-not-transparent/) |
| 6 | **eTenders Transparency Portal / OCDS API** | https://data.etenders.gov.za/ ; API https://ocds-api.etenders.gov.za/swagger/ | NT OCPO | Planning, tender, award and contract stages; OCID prefix ocds-9t57fa; bulk from May 2021 (https://data.etenders.gov.za/Home/LearnMore) | C | OCDS JSON/CSV/XLSX monthly bulk; paginated release API (swagger.json live 19 Oct 2026). License shown as PDDL in the API spec but CC BY 4.0 on the portal home page (inconsistent) | Portal "last updated 18–19/10/2026" (active). **OCDS release endpoint returned HTTP 500 / timeouts on 19 Oct 2026** | Headline "largest contracts/suppliers" only | No line items, missing values, voluntary coverage (§5.1); "public beta, not guaranteed accurate" (https://data.open-contracting.org/en/publication/143) |
| 7 | **Procurement Payments Dashboard (BAS + LOGIS)** | via https://data.etenders.gov.za/ ; guide: https://data.etenders.gov.za/Home/DownloadFile/?fileName=Procurement+Payments+Dashboard+User+Guide+Feb+2026.pdf | NT OCPO | 180 of 193 national and provincial departments on BAS; 115 also on LOGIS; 1 Apr 2018 to date. **Excludes** SOEs, municipalities, Defence, SAPS, SARS, SSA and the 9 provincial legislatures | T (aggregated per entity × supplier × item × year) | Power BI (~1 GB .pbix); chart export to CSV/XLSX; `Procurement_Spend_Transaction_List.csv` download | v1 Nov 2025, v2 Feb 2026, quarterly updates planned (active) | "Spend Efficiencies and Anomalies" view; LOGIS average price per unit per MIIN group | Aggregation hides split orders; no contract link; no subcontractors; ownership from B-BBEE certificates, not BO |
| 8 | **PFMA SCM Instruction 10 of 2025/26 / OCPO Data Upload Tool** | https://ocpo.treasury.gov.za/Legislation/Instruction%20Notes/PFMA%20SCM%20Instruction%20No.%2010%20of%202025-26%20Enhancing%20Procurement%20Information%20Transparency.pdf | NT OCPO | Requires departments, constitutional institutions and **public entities** not on BAS/LOGIS to report transaction-level goods-and-services payments monthly (within 10 days) via API or Data Upload Tool (https://OCPOdst.treasury.gov.za); NT to publish quarterly | T | Upload tool (internal) | Issued Nov 2025 (first publication date 12 Nov 2025) | n/a | Publication of public-entity data not yet visible **[unverified whether included in dashboard yet]** |
| 9 | **Central Supplier Database (CSD)** | https://secure.csd.gov.za/ | NT OCPO | All registered suppliers; CIPC/SARS/bank/B-BBEE verification (https://secure.csd.gov.za/Home/Terms) | Registry | Search, bulk files and web services **for organs of state only** | Active, **Restricted** | Restriction checks | No public search of directors or ownership |
| 10 | **Register of Restricted Suppliers / Tender Defaulters** | https://secure.csd.gov.za/Home/RestrictedSuppliersReportNT ; PDF https://ocpo.treasury.gov.za/RestrictedSupplier/RestrictedSuppliersReport.pdf | NT OCPO | Restricted suppliers and individuals with ID/registration numbers, reason, period, authorising entity (entries dated up to Jul 2026 seen) | List | HTML report + PDF | Updated as entities report (active); TenderWatch counts 409 entries (https://tenderwatch.org/). Separate NT "Register for Tender Defaulters" PDF says "currently no tender defaulters" (https://www.treasury.gov.za/publications/other/Register%20for%20Tender%20Defaulters.pdf) | Can be cross-matched | PDF; depends on buyers reporting (e.g. delays listing Sodi-linked firms: https://tenderwatch.org/) |
| 11 | **Municipal Money / Municipal Finance Data API** | https://municipalmoney.gov.za/ ; https://municipaldata.treasury.gov.za/ | NT (built and maintained by OpenUp; DBSA-funded tender to end-2028) | 292 municipalities (8 metros, 44 districts, 240 locals incl. disestablished); FY2008-09 to 2025-26; 2026 Q2 loaded. Cubes: incexp(_v2), capital(_v2), cflow(_v2), bsheet, financial_position_v2, aged_creditor/debtor(_v2), grants_v2, conditional_grants, repmaint(_v2), **uifwexp**, **audit_opinions**, **officials**, demarcation_changes (API /api/cubes, 19 Oct 2026) | B, A, Au | JSON (Babbage-style cubes) API + bulk CSV/XLSX | Quarterly (active) | Scorecard indicators (cash coverage etc.) | Aggregates only; "·" or "Not Available" where not submitted (https://municipalmoney.gov.za/help); data "in the process of being verified" |
| 12 | **MFMA website: s71 in-year reports, budgets, AFS, s71 non-compliance lists** | https://mfma.treasury.gov.za/ | NT | Quarterly s71 summaries per province and municipality; conditional grants; **lists of municipalities not submitting mSCOA strings** | A, coverage | PDF + Excel | Quarterly (Q3 2025-26 released Jun 2026: https://www.treasury.gov.za/comm_media/press/2026/2026062301%2003.%20Media%20Statement%20-%203rd%20Q%20Section%2071%20-%2022%20June%202026.pdf) | Non-compliance lists = known-unknowns | PDF-heavy |
| 13 | **AGSA general reports (PFMA & MFMA) + MFMA 2024-25 microsite** | https://www.agsa.co.za/reports ; https://mfma-2025.agsa.co.za/ ; archive https://www.agsareports.co.za/ | AGSA | All national and provincial departments, entities, SOEs (PFMA); 257 municipalities (MFMA); auditee-level outcomes and IE annexures; MI summaries | Au | PDF + interactive microsite; auditee annexures (PDF/XLS **[format unverified]**) | Annual (PFMA ~Nov/Dec; MFMA 2024-25 tabled 24 Jun 2026: https://www.agsa.co.za/reports/mfma-reports) | Material irregularities (MI), IE/UIFW, consequence management findings | No downloadable auditee-level MI register (https://mfma-2025.agsa.co.za/pages/material-irregularities); entity reports scattered |
| 14 | **SIU proclamations & annual reports** | https://www.siu.org.za/proclamations/ ; https://www.siu.org.za/annual-reports/ | SIU | Proclamations by national, provincial, local and SOE; 2024/25: R1.31bn recovered, R5.61bn contracts set aside, 3,962 investigations closed (https://www.siu.org.za/wp-content/uploads/2025/11/SIU-2024-25-Annual-Report-Final-.pdf) | E | HTML lists + PDF | Annual / ad hoc (site timed out on automated check) | Case scope | No structured case or outcome dataset |
| 15 | **NPA Asset Forfeiture Unit / IDAC** | https://www.npa.gov.za/sites/default/files/uploads/NPA%202025%20Annual%20Report_2025_v14b.pdf | NPA | AFU 2024/25: R1.962bn recovered | E | PDF | Annual | None | Aggregates only |
| 16 | **Public Protector reports** | https://www.publicprotector.org/q-content/investigation-reports-categories/ | PP | Investigation reports by category and year; third-party dataset of 388 reports 2008–2022 (https://doi.org/10.17632/6y7r58g6pt) | E | PDF | Ad hoc (site timed out on automated check) | None | PDF only |
| 17 | **Parliament / PMG (SCOPA, portfolio committees, written replies, Members' Interests)** | https://pmg.org.za/committee/42/ ; API https://api.pmg.org.za/ (docs https://github.com/OpenUpSA/pmg-cms-2/blob/master/API.md) | PMG (NGO) | SCOPA meetings (latest listed 14 Oct 2026), questions and replies, Register of Members' Interests (Jun 2026: https://static.pmg.org.za/Register_of_members_interests_june_2026.pdf) | E, text | Read-only JSON API; PDFs | Daily (active) | None | Unstructured text |
| 18 | **State Capture (Zondo) reports + government implementation tracker** | https://www.statecapture.org.za/site/information/reports ; https://stateofthenation.gov.za/state-capture-commission-recommendations | Commission / Presidency | Final reports; 60-action plan; July 2025 progress: 29 complete or substantially complete, 14 on track, 17 delayed (https://www.thepresidency.gov.za/sites/default/files/2025-07/PROGRESS%20REPORT%20ON%20IMPLEMENTATION%20OF%20ACTIONS%20IN%20THE%20PRESIDENT%E2%80%99S%20RESPONSE%20TO%20THE%20RECOMMENDATIONS%20OF%20THE%20STATE%20CAPTURE%20COMMISSION.pdf) | E | PDF + web tracker | Periodic | None | No entity/supplier extraction |
| 19 | **Stats SA** (CPI incl. average prices; PPI; construction material price indices P0151.1; Financial Census of Municipalities P9114; quarterly municipal financial stats P9110.1) | https://www.statssa.gov.za/?page_id=1847 | Stats SA | CPI COICOP from 2008, 5/8-digit from 2017, average prices; P9114 latest confirmed edition 2023 (https://www.statssa.gov.za/publications/P9114/P91142023.pdf) | Benchmarks, A | Excel/ASCII time-series ZIPs | Monthly CPI/PPI; annual P9114 (newer P9114 editions blocked by WAF; **[unverified]**) | n/a (benchmark) | Automated access blocked by Incapsula WAF |
| 20 | **DMPR / CEF fuel prices** (formerly DMRE) | https://www.dmpr.gov.za/Branches/Petroleum-Resources/Fuel-Prices ; archive https://www.dmre.gov.za/energy-resources/energy-sources/pretoleum/petrol-price-archive | DMPR | Monthly fuel price schedules, breakdowns, history, diesel wholesale guidelines; Oct 2026 adjustment published | Benchmark | PDF/ZIP | Monthly (active); old DMRE archive timed out on automated check | n/a | PDF parsing needed; diesel wholesale prices are guidelines (deregulated) |
| 21 | **CIPC company register & BO register** | https://www.cipc.co.za/ | CIPC (dtic) | Companies; BO register since 2023, 3m+ filings | Registry | Paid company searches; BO **restricted to law enforcement / accountable institutions** (https://www.businessday.co.za/news/2026-03-05-cipc-head-calls-for-more-beneficial-ownership-transparency/) | Restricted | n/a | No open bulk data **[bulk-licensing terms unverified]** |
| 22 | **Provincial portals**: Gauteng e-Tenders / Open Tender (public observation of Bid Adjudication Committee), TendaSwift; Western Cape ePS + annual Procurement Disclosure Reports | https://e-tenders.gauteng.gov.za/pages/awarded-open-tenders.aspx ; https://iol.co.za/news/politics/2025-12-02-gauteng-finance-mec-launches-digital-tender-procurement-system-tendaswift-to-curb-tender-bid-related-corruption/ ; https://www.westerncape.gov.za/treasury/files/wcg-blob-files?file=2026-07%2FAnnual+Procurement+Disclosure+Report+PDR++2025+2026+Final.pdf&type=file | Provincial treasuries | Provincial awards; WC quotations up to R1m via ePS | C | HTML/PDF | Active | Gauteng public adjudication | Fragmented; other 7 provinces not reviewed in depth **[gap in this research]** |
| 23 | **Metro award registers** (City of Cape Town monthly awarded-tender registers 2016–2026; Joburg monthly award PDFs) | https://www.capetown.gov.za/work%20and%20business/doing-business-with-the-city/tenders-rfqs-and-supply/tenders-awarded ; https://joburg.org.za/work_/Pages/Work%20in%20Joburg/Tenders%20and%20Quotations/Links/List%20of%20awarded%20contracts/List-of-awarded-contracts.aspx | Metros | Awards with supplier, value, reasons | C | PDF/XLS; CoCT open data portal | Monthly | None | Each metro different; most municipalities publish little (https://dullahomarinstitute.org.za/multilevel-govt/publications/why-are-municipalities-not-publishing-procurement-information-on-their-websites-and-the-etender-portal_final.pdf) |
| 24 | **SOE procurement disclosures** (Eskom Tender Bulletin awards; Transnet eSupplier transparency) | https://www.eskom.co.za/tenders/ ; https://esupplierportal.transnet.net/portal/transparency | SOEs | SOE awards (Eskom is the largest buyer in the OCDS mirror: 2,095 processes) | C | Web/PDF | Active | None | SOEs only voluntarily on eTenders |
| 25 | **NT transversal contracts (RT57 vehicles, RT70 fuel, etc.)** | https://www.treasury.gov.za/divisions/ocpo/ostb/contracts/Amendment%2011%20-%20Revised%20Implementation%20Guide.pdf | NT OCPO | Contract price lists; RT70 fuel price lists monthly, Category A pegged to DoE prices | Benchmark | PDF/XLS | Active | Benchmark source | Scattered PDFs |
| 26 | **Medicine prices** (NDoH SEP database; Master Procurement Catalogue; medicineprices.org.za API) | https://www.health.gov.za/nhi-pee/ ; https://medicineprices.org.za/ (API per https://github.com/Code4SA/medicine-price-registry/) | NDoH / OpenUp legacy | SEP database dated 1 Oct 2026; MPC open copy from 2018 (https://www.open.africa/en/dataset/department-of-he) | Benchmark | XLS / JSON API | SEP active; MPC open copy stale | Benchmark | Public-sector tender prices not systematically open |
| 27 | **District Health Barometer** (Health Systems Trust) | https://www.hst.org.za/publications/Pages/HSTDistrictHealthBarometer.aspx | HST | District-hospital expenditure per patient-day equivalent (2022/23 national R3,783; districts R2,070–R9,991) (https://sahr.hst.org.za/article/122768-health-and-related-indicators-2023/attachment/242932.html) | A | PDF | Annual | Per-unit benchmark | Not facility-transaction level |
| 28 | **Schools: NNSSF allocations** | https://www.gov.za/documents/notices/south-african-schools-act-national-norms-and-standards-school-funding-nnssf-1 | DBE / provinces | Per-learner allocations by quintile; provincial lists with EMIS number and allocation (e.g. Northern Cape: http://www.ncpt.gov.za/LinkClick.aspx?fileticket=ellcl1VWDao%3D&mid=1429&portalid=0&tabid=347) | B | PDF | Annual | None | School AFS only by request under SASA s43 (https://beta.acts.co.za/south-african-schools-act-1996/43_audit_or_examination_of_financial_records_and_statements.php) |
| 29 | **Higher education: DHET reports, HEDA** | https://www.dhet.gov.za/SitePages/Reports.aspx ; https://www.heda.co.za/indicatordashboard/default.aspx | DHET / IDSC | Audit outcomes via PMG (e.g. 12 of 50 TVETs clean in 2024/25; SETA IE R175m: https://pmg.org.za/committee-meeting/41771/) | A, Au | PDF | Annual | None | University AFS scattered; no consolidated dataset |
| 30 | **CIDB Register of Contractors** | https://portal.cidb.org.za/RegisterOfContractors/ | CIDB | Contractor grading lookups | Registry | Web search, no API | Active | Grade vs contract-size checks | No bulk |

### 1B. Civil society, media, academic and commercial

| # | Tool / org | URL | Owner | What it covers | Gran. | Access | Status | Red-flag features | Limits |
|---|---|---|---|---|---|---|---|---|---|
| 31 | **TenderWatch** | https://tenderwatch.org/ | Operator not named on homepage **[unverified]** | Mirrors eTenders (166,605 tenders; 32,629 awards May 2021–Sep 2026), AGSA PFMA annexures (772 auditees, 7 years, R454.0bn IE), municipal UIFW (R290.6bn), restricted-supplier register, OpenSanctions PEP data; tracker of 14 commissions and cases | C, Au, E | Free web; method page | Active (data to Sep 2026) | **"Barred and paid anyway"** (409 restricted, 32 matched, 2 awarded while barred); plausibility exclusion rules; news linkage | Awards, not payments; matching limits stated |
| 32 | **Corruption Watch: Procurement Watch** | https://www.corruptionwatch.org.za/procurement-watch-a-corruption-watch-project/ ; report https://www.corruptionwatch.org.za/wp-content/uploads/2024/09/Corruption-Watch_Procurement-Watch-Report_Final_18Sept2024.pdf | Corruption Watch | Aggregates NT data on deviations, contract expansions, restricted suppliers; Procurement Risk Trends 2016–2024 | C | **Access by application** | Active (report Sep 2024); municipal corruption-risk toolkit Dec 2025 (https://www.corruptionwatch.org.za/wp-content/uploads/2025/12/Corruption-Risk-Assessment-Toolkit_Digital.pdf) | Deviations / expansions | Not open |
| 33 | **OUTA tender transparency "firewall"** | https://mybroadband.co.za/news/government/663945-firewall-for-stopping-dodgy-tenders-in-south-africa.html | OUTA + technical team | Claims to scrape all municipal and government portals; AI spec analysis; "spiderweb" relationship graph (e.g. one phone number linked to 15 companies, 48 tenders, R3.6bn); price-vs-average checks | C | **Demo only** (Aug 2026); not adopted by NT; needs ~R1.5–2m/month | Demo | Price benchmarking, network analysis | Not public; claims unverified |
| 34 | **OpenUp** (Municipal Money, PMG platform code, Wazimap, ex-Vulekamali) | https://openup.org.za/projects | OpenUp | Civic tech | various | Open source | Active | — | Wazimap current status not confirmed **[unverified]** |
| 35 | **IMALI YETHU** coalition | https://imaliyethu.org.za/ | Coalition (PSAM, Corruption Watch, Equal Education, SECTION27, SPII, My Vote Counts, LRC…) | Budget transparency partner of NT (Vulekamali) | B | Advocacy | Active | — | No dataset of its own |
| 36 | **PSAM** (Rhodes) | https://psam.org.za/monitoring-advocacy/ | PSAM | Expenditure tracking, budget analysis, social-accountability training (2025 manual) | B, A | PDF | Active | Methodology | Not a data platform |
| 37 | **Open Secrets** (Zondo Recommendations Tracker; Unaccountable series) | https://www.opensecrets.org.za/zondo-recommendations-tracker/ ; https://www.opensecrets.org.za/unaccountable/ | Open Secrets | Recommendation implementation scoring; private-sector enablers dossiers | E | Web | Active | — | Not a database |
| 38 | **amaBhungane, GroundUp** | https://amabhungane.org/ ; https://groundup.news/ | Media | Investigations (e.g. GroundUp lottery tender: https://groundup.news/article/committee-that-evaluated-the-multi-billion-rand-lotto-tender-had-no-experience-with-lotteries/); amaBhungane was a co-applicant in the PPA ConCourt case | E | Articles | Active | Case leads | Unstructured |
| 39 | **Budget Justice Coalition** | https://budgetjusticesa.org/ | Coalition | Budget advocacy (2026 submissions on fiscal framework, DoRB) | B | PDF | Active | — | Not data |
| 40 | **Dullah Omar Institute** (Local Government Bulletin) | https://dullahomarinstitute.org.za/ | UWC | Municipal finance and intervention analysis (Sep 2025 issue); research on why municipalities don't publish procurement info | Analysis | PDF | Active | — | — |
| 41 | **International Budget Partnership – OBS** | https://www.internationalbudget.org/open-budget-survey/country-results/2023/south-africa | IBP | OBS 2023: SA transparency 83 (2021: 86). OBS 2025 regional findings published (https://internationalbudget.org/2025-sub-saharan-africa/); SA 2025 country score not retrieved **[unverified]** | Index | Web/PDF | Biennial | — | Budget docs only |
| 42 | **Open Contracting Partnership – SA OCDS registry & Cardinal** | https://data.open-contracting.org/en/publication/143 ; https://cardinal.readthedocs.io/en/latest/cli/indicators/ | OCP | Monthly mirror of NT OCDS (JSONL/XLSX/CSV, 2017–2026) with quality checks; Cardinal computes 11 red flags (R003, R018, R024…) | C | Bulk download | Retrieved monthly (last 20 Sep 2026) | Red flags via Cardinal | Mirror appears incomplete vs portal (§5.1) |
| 43 | **openAFRICA (Code for Africa)** | https://www.open.africa/ | Code for Africa | Legacy SA datasets: budgeted vs actual, tender awards 2015–16 (https://open.africa/dataset/tender-awards-2015-2016), MPC, SEP | mixed | CKAN | Largely **Stale** | — | Old snapshots |
| 44 | **OpenSanctions (SA PEPs from PMG; FIC TFS list)** | https://www.opensanctions.org/datasets/za_pmg_legislators/ ; https://www.opensanctions.org/datasets/za_fic_sanctions/ | OpenSanctions | National and provincial legislators (PEPs), FIC sanctions; daily | Registry | API/bulk (CC BY-NC per TenderWatch) | Active | PEP matching | Legislators only (no municipal councillors or officials) |
| 45 | **Siyazana / Connected Africa** | https://connectedafrica.org/ ; https://github.com/ANCIR/Siyazana.co.za | ANCIR | 2015 influence-mapping (people, companies, government) | Network | GitHub data | **Stale** (2015) | Related parties | Outdated |
| 46 | **Ratings Afrika MFSI; GGA Governance Performance Index** | https://www.ratingsafrika.com/ ; https://gga.org/gpi/index.html | Private / NGO | MFSI 2025 covers 128 municipalities (https://www.ber.ac.za/Documents/Download/c15ce222-ac2f-42a3-a532-3a9e8dd94cb4); GPI March 2024 | Index | PDF / web | Annual / stale | Financial distress | Methodologies proprietary |
| 47 | **Commercial tender aggregators**: Leads 2 Business (R1,495.65/m ex VAT), OnlineTenders / Tender Bulletins (R850/m), TenderSearch SA, TENDERS-SA.ORG, EasyTenders, SimpleBid, Axel "Tender Finder", Apify eTenders scraper | https://www.l2b.co.za/Tenders/Tender-Pricing ; https://www.onlinetenders.co.za/pricing-and-plans.aspx ; https://x.com/blueitserver ; https://documents.easytenders.co.za/ ; https://www.simplebid.co.za/blog/etenders-ocds-guide-south-africa/ ; https://apify.com/publicmoney/etenders-south-africa-scraper/api/openapi | Private | Opportunity alerts; some award history (L2B award info; municipal adverts scraped) | C | Paid | Active | None (bidder-focused) | Paywalled; not accountability-oriented, but they do scrape municipal adverts the state does not centralise |
| 48 | **Academic / datasets**: Public Protector reports dataset (Mendeley); Zenodo study on municipal procurement transparency in Covid-19 | https://doi.org/10.17632/6y7r58g6pt ; https://doi.org/10.5281/zenodo.5733467 | Academics | — | — | Open | Static | — | One-off |

### 1C. International comparators worth borrowing from

| Tool | URL | What to borrow |
|---|---|---|
| **Prozorro + DOZORRO + BI Prozorro (Ukraine)** | https://dozorro.org/tools/public-bi ; https://www.open-contracting.org/2024/12/04/how-to-make-better-public-procurement-decisions-with-business-intelligence-insights-from-ukraine/ | Daily-updated open BI (49 dashboards incl. prices); ~35+ automated risk indicators; citizen feedback per tender; escalation workflow |
| **Brazil Portal da Transparência + CEIS + Painel de Preços + CGU ALICE** | https://portaldatransparencia.gov.br/download-de-dados/despesas ; https://api.portaldatransparencia.gov.br/ ; https://www.gov.br/compras/pt-br/sistemas/conheca-o-compras/pesquisa-de-precos ; https://www.gov.br/cgu/pt-br/assuntos/auditoria-e-fiscalizacao/alice/alice-para-estados-e-municipios | **Payment-level** data by stage (commitment, liquidation, payment) per payee tax number; sanctions register joinable by tax number; government **price panel** from homologated purchases; automated overpricing alerts |
| **USAspending.gov** | https://api.usaspending.gov/docs/endpoints | Transaction-level award API; ties awards to budget accounts (DATA Act); recipient profiles |
| **Mexico IMCO Índice de Riesgos de Corrupción** | https://imco.org.mx/indice-de-riesgos-de-corrupcion/ | Composite buyer-level risk index (direct awards, sanctioned suppliers, short timelines, concentration) on ~168k procedures |
| **Kenya PPIP OCDS** | https://data.open-contracting.org/en/publication/147 | Daily OCDS with API, mandatory publication |
| **OCP Red Flags guide (73 indicators) + Cardinal** | https://www.open-contracting.org/resources/red-flags-in-public-procurement-a-guide-to-using-data-to-detect-and-mitigate-risks/ | Off-the-shelf indicator definitions mapped to OCDS fields |
| **OpenSpending** | https://blog.okfn.org/2020/07/09/openspending-stewardship-moving-to-datopian/ | Cautionary tale: v2 shut in 2018; stewardship moved to Datopian in 2020. Don't depend on it. |

---

## 2. Coverage matrix

Legend: **●** covered, **◐** partial, **○** none. Columns:
- **VK** = Vulekamali / NT budget docs and s32
- **MM** = Municipal Money / API
- **S71** = MFMA s71 site
- **eT** = eTenders and OCDS
- **PPD** = Procurement Payments Dashboard
- **RSR** = Restricted Supplier Register
- **AG** = AGSA reports
- **ENF** = SIU / NPA-AFU / PP / Zondo trackers
- **PMG** = Parliament
- **SSA** = Stats SA
- **CIPC** = CIPC/CSD (public view)
- **TW** = TenderWatch
- **CW** = Procurement Watch
- **OSx** = OpenSanctions

| Category \ Tool | VK | MM | S71 | eT | PPD | RSR | AG | ENF | PMG | SSA | CIPC | TW | CW | OSx |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| National departments | ● | ○ | ○ | ◐ | ● | ◐ | ● | ◐ | ◐ | ◐ | ○ | ◐ | ◐ | ○ |
| Provincial departments | ● | ○ | ○ | ◐ | ● | ◐ | ● | ◐ | ◐ | ◐ | ○ | ◐ | ◐ | ○ |
| Municipalities (local/district) | ◐ (transfers) | ● | ● | ◐ (voluntary) | ○ | ◐ | ● | ◐ | ◐ | ● (P9114) | ○ | ● | ◐ | ○ |
| Metros | ◐ | ● | ● | ◐ | ○ | ◐ | ● | ◐ | ◐ | ● | ○ | ● | ◐ | ○ |
| SOEs (Eskom, Transnet, PRASA…) | ◐ (transfers) | ○ | ○ | ◐ (voluntary) | ○ | ◐ | ● | ◐ | ◐ | ○ | ○ | ◐ | ◐ | ○ |
| Public entities / SETAs | ◐ | ○ | ○ | ◐ | ○ (Instr. 10 pipeline) | ◐ | ● | ◐ | ◐ | ○ | ○ | ◐ | ◐ | ○ |
| TVET colleges / universities | ◐ (transfers) | ○ | ○ | ◐ | ○ | ○ | ◐ (TVET) | ○ | ◐ | ○ | ○ | ○ | ○ | ○ |
| Schools | ◐ (prov. votes) | ○ | ○ | ○ | ◐ (prov. education dept spend) | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| Health facilities | ◐ (prov. votes) | ○ | ○ | ○ | ◐ (prov. health dept spend) | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| Procurement awards | ○ | ○ | ○ | ◐ | ○ | ○ | ◐ (sampled) | ○ | ○ | ○ | ○ | ◐ | ◐ | ○ |
| Actual payments to suppliers | ○ | ○ | ○ | ○ | ◐ (aggregated; nat/prov only) | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ |
| Irregular / F&W / unauthorised exp. | ◐ | ● (uifwexp) | ○ | ○ | ○ | ○ | ● | ○ | ◐ | ○ | ○ | ● | ○ | ○ |
| Consequence management / recoveries | ○ | ○ | ○ | ○ | ○ | ◐ | ◐ | ◐ | ◐ | ○ | ○ | ◐ | ○ | ○ |
| Beneficial ownership / related parties | ○ | ○ | ○ | ○ | ◐ (B-BBEE ownership classes) | ○ | ◐ (AG reports awards to connected persons, aggregated) | ○ | ◐ (MPs' interests) | ○ | ○ (restricted) | ◐ (PEP) | ○ | ◐ (PEP) |

Sources for cell judgements: tool rows in §1. For AGSA awards to connected parties (R717.35m in municipalities 2024-25): https://mfma-2025.agsa.co.za/report/mfma_report_2024_25.pdf.

**Takeaway:** the bottom four rows are where the north star wins: payments, IE linked to transactions, consequences and ownership. They are almost entirely empty or partial.

---

## 3. Gap analysis vs the north star

### 3.1 What nobody does (publicly)

| North-star capability | Current state | Evidence |
|---|---|---|
| **Transaction-level payments for all spheres** | Only nat/prov departments on BAS, aggregated per supplier × item × year, in Power BI. Municipal payments are not published anywhere (aged-creditor aggregates only). SOEs not covered | PPD guide; MM cube notes "does not include individual creditors" (https://municipaldata.treasury.gov.za/api/cubes) |
| **Contract → payment → owner linkage** | No shared key published. OCDS has OCIDs but no payments (0 transactions in the registry); PPD has suppliers but no OCIDs; CSD has supplier numbers but isn't public; BO register closed | https://data.open-contracting.org/en/publication/143 ; PPD guide; Business Day |
| **Unit-price benchmarking** | Only inside the PPD LOGIS view (average price per MIIN group, lowest level 2). No item lines in OCDS. OUTA demo claims it but isn't public | PPD guide §7; OCDS profile (§5.1); MyBroadband |
| **Tender-splitting detection** | Impossible from aggregated payments; partially possible from OCDS (but RFQs under R1m, e.g. WC ePS, mostly unpublished) | WC ePS: https://www.westerncape.gov.za/treasury/tenders |
| **Deviations / expansions (Reg. 16A6.6 / MFMA s36)** | Collected by NT; visible only via Corruption Watch's application-only Procurement Watch | CW Procurement Watch page |
| **"Known unknowns" layer** | Scattered: s71 non-compliance PDFs, AGSA outstanding audits (e.g. Maluti-A-Phofung not submitting AFS for 2024-25), MM "Not Available", PPD exclusions, eTenders voluntary scope, 33% of PFMA auditees qualified on IE completeness. No tool scores coverage per entity × year × dataset | s71 list; https://mfma-2025.agsa.co.za/report/mfma_report_2024_25.pdf ; PFMA GR |
| **Alerting / watchlists** | Commercial aggregators alert bidders on opportunities; no accountability alerting (e.g. "restricted supplier paid", "IE spike", "award > CIDB grade") | §1B |
| **Consequence tracking per finding** | AGSA reports MI status in aggregate; SIU/AFU totals; no case-level open data linking finding → investigation → recovery | AG MI page; SIU AR; TenderWatch "what comes back" |
| **Per-capita / per-unit comparisons** | MM has some per-household indicators; DHB has cost per PDE; nobody does cross-sector per-capita spend with demographic denominators | DHB; MM |
| **Related-party detection** | AGSA finds R154.62m to employee-owned suppliers and R717.35m to suppliers linked to family/associates (2024-25 MFMA) but publishes only aggregates; CSD does the checks internally; PEP data limited to legislators | MFMA GR 2024-25; OpenSanctions |

### 3.2 Data that legally exists (is collected) but isn't published

1. **BAS/LOGIS transaction detail** (order and invoice lines, dates, quantities). It sits in Vulindlela (login only). The PPD exposes it only aggregated.
2. **Public-entity transaction payments** submitted monthly under Instruction 10 via the OCPO Data Upload Tool. Collected; publication of this tranche not yet evident **[unverified]**.
3. **CSD supplier master**: directors, B-BBEE, tax status and bank-verification flags. Shared with organs of state only.
4. **CIPC beneficial-ownership register.** Restricted. The PPA s31 route to publishing BO of winning bidders died with the ConCourt ruling of 17 Sep 2026.
5. **Deviation and contract-expansion registers.** Reported to NT/AGSA. Only Corruption Watch has access (application).
6. **Municipal mSCOA transaction strings.** Municipalities submit mSCOA data strings to NT's LGDRS. Only s71-level aggregates are published (MM help; s71 list). Line-level ledgers are unpublished **[inference]**.
7. **Municipal and departmental registers of irregular, fruitless and wasteful expenditure** (item-level, with condonation/recovery status). Only totals appear in AFS notes.
8. **AGSA material irregularity details per auditee.** These appear inside individual audit reports, but there is no consolidated register.
9. **School and SGB financial statements.** Available only for inspection on request (SASA s43).
10. **Contract documents and invoices**, which PPA s31(2)(a)(vi) would have required. Now void.

### 3.3 Access barriers

- **PDF-only / scanned** documents: eTenders award attachments, AGSA reports, SIU proclamations, DMPR fuel schedules, transversal price lists, metro award registers, Instruction 10 itself (image PDF).
- **Login walls**: Vulindlela, CSD search, CIPC BO register, Procurement Watch.
- **Voluntary publication**: municipalities and SOEs on eTenders. MFMA Circular 83 guidance is non-binding unless adopted by council (https://pmg.org.za/committee-question/29895/ as summarised; **[unverified direct quote]**).
- **API reliability**: the OCDS release endpoint returned HTTP 500 / timeouts and the Vulekamali CKAN datastore failed (HTTP 500) on 19 Oct 2026. Stats SA blocks automated requests (Incapsula WAF).
- **Licensing inconsistency**: eTenders states PDDL in the API spec but CC BY 4.0 on the portal. OpenSanctions is CC BY-NC (commercial use needs a licence).
- **PAIA**: everything else (deviation registers, IE registers, contracts) needs PAIA requests entity by entity, with statutory 30-day timelines and frequent non-response. **[Response rates not measured in this research.]**
- **Data-quality warnings**: Treasury labels OCDS data "public beta, derived from disparate sources" (https://data.open-contracting.org/en/publication/143). MM data is "in the process of being verified" (https://municipaldata.treasury.gov.za/).

---

## 4. Recommended data-source inventory (prioritised)

**MR** = machine-readable now? (Y / Partial / N)

| Priority | Source | Use in north star | MR | Access route |
|---|---|---|---|---|
| P0 | **Procurement Payments Dashboard + Transaction List CSV** (BAS/LOGIS) | Spine for actual payments (nat/prov); supplier × item × year; LOGIS unit prices | Partial (Power BI + CSV export) | data.etenders.gov.za; ask OCPO for a bulk/API feed under Instruction 10 |
| P0 | **eTenders OCDS** (bulk + API) | Awards, contracts, buyers, suppliers, procedure types; red flags via Cardinal | Y (unstable API) | data.etenders.gov.za, ocds-api.etenders.gov.za, OCP registry mirror |
| P0 | **Municipal Finance Data API** | All municipal budgets/actuals, UIFW, audit opinions, officials, grants, creditors | Y | municipaldata.treasury.gov.za/api |
| P0 | **AGSA PFMA & MFMA annexures + microsite** | Audit opinions, IE/UIFW per auditee, MIs, outstanding audits | Partial (PDF/XLS; microsite) | agsa.co.za, mfma-2025.agsa.co.za |
| P0 | **Restricted Supplier Register** | Debarment checks vs awards and payments | Partial (PDF/HTML) | ocpo.treasury.gov.za, secure.csd.gov.za |
| P0 | **Vulekamali / ENE / EPRE / s32 monthly** | Budget baseline, budget-vs-actual, per-capita | Y/Partial | vulekamali.gov.za, treasury.gov.za |
| P1 | **DMPR fuel prices** | Diesel/petrol benchmarks by month and zone | Partial (PDF/ZIP) | dmpr.gov.za |
| P1 | **Stats SA CPI (incl. average prices), PPI, P0151.1 CPAP, P9114** | Deflators, unit-price benchmarks, construction escalation | Y (Excel ZIPs) | statssa.gov.za (WAF: manual or whitelisted download) |
| P1 | **NT transversal contract price lists** (RT57 vehicles, RT70 fuel, etc.) | Government's own contracted prices as ceilings | Partial (PDF/XLS) | treasury.gov.za/divisions/ocpo/ostb/contracts |
| P1 | **NDoH SEP database + MPC** | Medicine price benchmarks | Y (XLS) | health.gov.za/nhi-pee |
| P1 | **s71 non-compliance lists; AGSA outstanding audits** | Known-unknowns layer | Partial (PDF) | mfma.treasury.gov.za |
| P1 | **OpenSanctions SA PEPs + PMG Register of Members' Interests** | Related-party matching (directors vs PEPs) | Y (API; PDF for RMI) | opensanctions.org, pmg.org.za |
| P1 | **SIU proclamations, AFU, PP reports, Zondo tracker** | Enforcement / consequence layer | N (PDF/HTML) | siu.org.za, npa.gov.za, publicprotector.org |
| P2 | **Metro and provincial award registers** (CoCT, Joburg, Gauteng, WC PDR) | Fill municipal/provincial award gaps | Partial | metro/province sites |
| P2 | **SOE disclosures** (Eskom bulletin, Transnet eSupplier) | SOE awards | Partial | SOE portals |
| P2 | **CIDB register** | Grade vs contract value checks | N (web lookup) | portal.cidb.org.za |
| P2 | **District Health Barometer; NNSSF school allocation lists; HEDA** | Sector unit-cost denominators | Partial (PDF) | hst.org.za, provincial gazettes |
| P2 | **PMG API** (SCOPA, written replies) | Text-mined disclosures (e.g. diesel price replies) | Y | api.pmg.org.za |
| P3 (blocked) | **CSD, CIPC BO, Vulindlela, deviation registers** | Ownership, directors, full transactions | N | Advocacy, partnership MoU, PAIA |

---

## 5. Exception-detection ideas (strongest, with feasibility)

### 5.1 Hands-on check: eTenders OCDS (OCP registry full mirror, downloaded 19 Oct 2026)

Source: https://data.open-contracting.org/en/publication/143/download?name=full.jsonl.gz

| Item | Result |
|---|---|
| Contracting processes | 35,309 (2017–2026; ~7,200–7,300 per year in 2022–2025) |
| Tender value present | 0 |
| Awards | 9,551, of which 6,760 (71%) have a value |
| Contracts | 1,691, of which 1,515 have a value |
| Tender / award items | 0 |
| Tenderers field present | 2,170 processes |
| Procurement method | open 34,875 · limited 214 · direct 166 · selective 54 |
| Distinct buyers | 732 (top buyers: Eskom 2,095; Public Works 1,262; ARC 1,258; City of Cape Town 904; PRASA 903; Transnet 841) |
| Distinct supplier names | 7,468 |

**Implications:**
- (a) Unit-price checks cannot come from OCDS.
- (b) Direct and limited procedures are almost certainly under-reported against AGSA's findings.
- (c) The portal claims 70,873 awards and TenderWatch mirrors 32,629 awards, so a builder should ingest Treasury's monthly bulk files directly, not just the API-derived registry copy.

### 5.2 Top exception detectors

| # | Detector | Logic | Data that makes it feasible | Feasibility now |
|---|---|---|---|---|
| 1 | **Fuel price benchmarking** (the R123/l vs R24/l case) | Paid price per litre vs DMPR monthly retail/wholesale guideline for the zone, plus RT70 transversal price. Flag > +20%. Real precedent: NW Agriculture R26.26 vs R21.33/l (https://www.vfplus.org.za/media-releases/north-wests-agricultural-department-pays-21-more-than-market-value-for-tender-diesel/) | **PPD LOGIS** average unit price for fuel MIIN groups (nat/prov); DMPR monthly schedules; RT70 price lists; PMG written replies | **Medium.** LOGIS view gives average unit price per MIIN group per supplier-year. Monthly granularity and municipalities missing |
| 2 | **Generic unit-price outliers** | Within-commodity robust z-score (median/IQR) of unit price across departments and suppliers; compare against CPI average prices, SEP (medicines), RT57 (vehicles), P0151.1 (construction escalation) | PPD LOGIS; Stats SA; NDoH SEP; RT57 | **Medium** for LOGIS departments; **Low** elsewhere |
| 3 | **Barred-and-paid / barred-and-awarded** | Restricted-supplier ID/registration number vs award and payment supplier during restriction period | RSR PDF; OCDS; PPD supplier names (no reg. numbers public → fuzzy match) | **High** for awards (TenderWatch already does it); **Medium** for payments |
| 4 | **Supplier concentration / repeat suppliers** | HHI per buyer × commodity; supplier share > X% over 3 years; same supplier across many departments | PPD (supplier × dept × item × year); OCDS | **High** |
| 5 | **Non-competitive procurement share** | Share of direct/limited/emergency per buyer; LOGIS "Non-Contract spending" share vs peers | OCDS procurementMethod; PPD LOGIS contract type | **High** (data under-reports) |
| 6 | **Tender splitting near thresholds** | Clusters of orders just under R1m (or old R500k/R30k thresholds) to the same supplier from the same buyer within short windows | Needs order-level transactions; PPD aggregation blocks it; OCDS RFQs sparse | **Low** until order-level data is published |
| 7 | **Budget–payment–audit triangulation** | Compare budgeted (ENE/EPRE), paid (PPD), and AGSA IE per entity; flag high payments + qualified IE completeness + MIs | Vulekamali, PPD, AGSA annexures | **High** (nat/prov) |
| 8 | **Municipal distress and coverage score ("known unknowns")** | Per municipality-year: submitted s71? AFS audited? audit outcome; UIFW trend; creditor ageing > 90 days; cash coverage | MM API (uifwexp, audit_opinions, aged_creditor_v2, cflow_v2); s71 non-compliance PDFs; AGSA outstanding list | **High.** All public; mostly API |
| 9 | **Related-party flags** | Supplier directors matched to PEPs (OpenSanctions), MPs' interests, municipal officials (MM `officials` cube) | Needs supplier directors (CSD/CIPC; restricted). PEP side is public | **Low–Medium** (blocked by director/BO access) |
| 10 | **Award vs contractor capacity** | Award value vs CIDB grade limit; newly registered companies winning large awards | OCDS + CIDB lookup + CIPC registration date (registration number encodes the year, e.g. 2024/007620/07) | **Medium** |
| 11 | **Contract-expansion / evergreen flags** | Month-to-month extensions and variations > 15/20% | Deviation/expansion registers (Procurement Watch only); OCDS amendments = 0 in mirror | **Low** |
| 12 | **Consequence-gap tracker** | Per auditee: IE incurred vs written off / recovered; MI status; SIU proclamation and outcome | AGSA, MM uifwexp, SIU lists | **Medium** (PDF extraction) |

---

## 6. Top recommended next steps (for building the north star)

1. **Ingest the "open now" spine in 4–6 weeks:**
   - Municipal Finance API (all cubes)
   - Treasury OCDS monthly bulk files (not just the API)
   - PPD Transaction List CSV
   - Restricted Supplier PDF
   - AGSA PFMA/MFMA annexures
   - Vulekamali ENE/EPRE

   Publish an entity × year × dataset **coverage matrix** from day one. That is the "knows what it doesn't know" feature, and nobody has it.
2. **Build the benchmark "utilities on the glass" layer.** Parse DMPR fuel schedules (monthly, by zone), Stats SA CPI average prices / PPI / P0151.1, NDoH SEP, and RT57/RT70 price lists into a price-reference service keyed to UNSPSC/MIIN. Then run detectors #1, #2 and #4 on PPD LOGIS data.
3. **Engage OCPO formally** for three things: (a) a bulk/API feed of the PPD at order/invoice level, (b) inclusion of the Instruction 10 public-entity submissions, and (c) supplier registration numbers in published data so suppliers can be joined deterministically to the RSR, OCDS and CIDB. Use the 2024 MAPS recommendations as leverage.
4. **Partner rather than duplicate:**
   - TenderWatch (method overlap; barred-and-paid)
   - Corruption Watch (Procurement Watch deviation data access)
   - OUTA (scraped municipal tenders and network graph)
   - OpenUp (MM maintainer)
   - OCP (Cardinal red flags, data-quality feedback to Treasury)
5. **Advocacy and legal track:** push for the re-enacted Procurement Bill to keep s31-style disclosure (invoices, BO of winners, deviations) and for an open CIPC BO register (the Commissioner already supports this). Meanwhile, run a PAIA programme for deviation registers and IE registers at the 20 largest-IE auditees: TenderWatch lists Transnet R73.0bn and Eskom R41.9bn over seven years (https://tenderwatch.org/).

---

## Appendix A: Key figures (with sources)

- PFMA 2024-25: IE R42.58bn (2023-24: R49.53bn); 252 auditees (60%) incurred IE; 203 MIs; ~R32.04bn IE under NT assessment, R20.72bn past timelines. https://www.agsa.co.za/storage/app/media/reporting/pfma/PFMA-GR-2024-25-Interactive.pdf
- MFMA 2024-25: 257 municipalities; 39 clean; IE R40.14bn; R145.21bn over 2021-22 to 2024-25; 10,830 awards audited worth R65.12bn; 216 municipalities (85%) non-compliant; R154.62m prohibited awards to employee-owned suppliers; R717.35m to connected suppliers; Maluti-A-Phofung did not submit 2024-25 AFS. https://mfma-2025.agsa.co.za/report/mfma_report_2024_25.pdf
- SIU 2024/25: R1.31bn recovered; R2.77bn losses prevented; R5.61bn contracts set aside. https://www.siu.org.za/wp-content/uploads/2025/11/SIU-2024-25-Annual-Report-Final-.pdf
- NPA AFU 2024/25: R1.962bn recovered. https://www.npa.gov.za/sites/default/files/uploads/NPA%202025%20Annual%20Report_2025_v14b.pdf
- OBS 2023 SA transparency 83/100. https://www.internationalbudget.org/open-budget-survey/country-results/2023/south-africa
- MAPS 2024: 12% of eTenders-registered organs uploaded plans; 3% published contract notices. https://www.treasury.gov.za/comm_media/press/2024/MAPS%20Assessment%20South%20Africa.pdf
- Public Procurement Act 28 of 2024 declared invalid, 17 Sep 2026. https://www.citizen.co.za/news/south-africa/courts/concourt-public-procurement-act-parliament/

## Appendix B: Liveness checks (box, 19 Oct 2026, ~08:15–08:25 SAST)

| Endpoint | Result |
|---|---|
| https://municipaldata.treasury.gov.za/api/cubes | 200 (21 cubes listed) |
| https://ocds-api.etenders.gov.za/swagger/v1/swagger.json | 200 |
| https://ocds-api.etenders.gov.za/api/OCDSReleases?... | 500 / timeout |
| https://data.vulekamali.gov.za/ (CKAN) | 500 / timeout |
| https://www.vulindlela.gov.za/ | 200 (login) |
| https://api.pmg.org.za/ | 200 |
| https://tenderwatch.org/ | 200 |
| https://esupplierportal.transnet.net/portal/transparency | 200 |
| https://e-tenders.gauteng.gov.za/ | 200 |
| https://medicineprices.org.za/ | 200 |
| https://www.health.gov.za/nhi-pee/ | 200 |
| https://www.dmpr.gov.za/Branches/Petroleum-Resources/Fuel-Prices | 200 (via fetch) |
| https://www.dmre.gov.za/... (legacy archive) | timeout |
| https://www.siu.org.za/proclamations/ | timeout |
| https://www.publicprotector.org/ | timeout |
| https://stateofthenation.gov.za/... | timeout |
| Stats SA PDFs | 403 (WAF) |

## Appendix C: Not verified / caveats

- TenderWatch operator identity; OUTA platform performance claims (demo reported by MyBroadband only).
- Whether Instruction 10 public-entity data has been published in the PPD yet.
- Wazimap current status; SA OBS 2025 country score; Stats SA P9114 editions after 2023.
- Exact format of AGSA auditee annexures (PDF vs Excel).
- Exact frequency and format of provincial IYM public releases.
- The Corruption Watch "opacity" research page timed out; the 91%/89% figures come from the Open Cities Lab write-up of the joint study.
- Seven provinces' own procurement portals were not individually reviewed.
