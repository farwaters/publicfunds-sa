# Improvement backlog, October 2026

Owner request 19 Oct 2026 21:41 SAST ("over to you to come up with improvements and/or enhancements"). North star: the most comprehensive
public-expenditure source for South African taxpayers that knows what it doesn't know, flags exceptions (e.g. diesel bought at R123/l when the
official price was about R24/l), tracks irregular / fruitless & wasteful expenditure and looting, with benchmarks "on the glass".

## Scoring

| Factor | Scale |
|---|---|
| **V**: taxpayer value | 1–5 (5 = a taxpayer learns something important they couldn't easily find) |
| **F**: north-star fit | 1–5 (comprehensiveness, honesty about gaps, exceptions, UIF&W/looting, benchmarks) |
| **E**: effort | 1–5 (1 = under a day, 5 = weeks) |
| **R**: risk | 1–5 (legal/POPIA/defamation, misreading, source access, operational) |

**Score = 2V + 2F + (6 − E) + (6 − R)**, range 6–30. Value and fit are weighted double so that cheap-but-minor work doesn't crowd out the north star.
Each item is also a CSI register entry (CSI ID in the first column).

Rules for every item:
- Source access must be legitimate: no bypassing WAFs or logins (KE-003). Use manual drops or other official or open republications, with the licence checked.
- No named-supplier flag goes public without four-eyes review (ADR-0005/0008).
- Unknown stays unknown.

## Ranked backlog

| # | CSI | Item | Area | V | F | E | R | Score | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | CSI-026 | Procurement Payments Dashboard (PPD) transaction CSVs via owner manual drop | Data source | 5 | 5 | 2 | 2 | **28** | KE-009 / RB-06 loader exists; the owner exports from the Power BI report by hand. Unlocks actual payments, unit prices and the R123/l-style exceptions. |
| 2 | CSI-027 | Plain-language explainers: glossary and 'what does irregular / fruitless & wasteful / unauthorised mean' cards inline on every page | Product | 4 | 4 | 1 | 1 | **26** | Static text, reviewed against the PFMA/MFMA definitions. |
| 3 | CSI-028 | Known unknowns v2: trend over time and a per-municipality ranking of missing data (v1 per-province scoreboard shipped in CHG-2026-008) | Product | 3 | 5 | 1 | 1 | **26** | Uses coverage.json only. |
| 4 | CSI-029 | Unit-price outlier detector vs on-the-glass benchmarks (fuel first: R/litre on awards/payments vs DMPR price for that month and zone) | Detector | 5 | 5 | 3 | 3 | **26** | Needs line items with quantity and unit (PPD payments, contract documents); fuel benchmark already loaded (CI-108). Leads stay hidden until confirmed (four-eyes). |
| 5 | CSI-030 | AGSA MFMA/PFMA per-entity annexures (audit outcomes, material irregularities, UIF&W per entity) | Data source | 5 | 5 | 4 | 2 | **26** | PDF/Excel annexures; PFMA brings national and provincial departments and SOEs into the audit view. |
| 6 | CSI-031 | CPI after Jan 2025 from a legitimate source: Stats SA P0141 (owner browser download as a manual drop), or a current official republication (e.g. SARB, IMF data portal), with the licence checked | Data source | 4 | 4 | 2 | 1 | **25** | KE-003 / KE-012; no bypassing the Stats SA WAF. |
| 7 | CSI-032 | Full fuel price history (DMPR archive documents before 2026, or SAPIA's published history), with zone/grade mapping | Data source | 3 | 5 | 2 | 1 | **25** | KE-012, CSI-022; makes the fuel checker and the unit-price detector work for past years. |
| 8 | CSI-033 | Awards just under procurement thresholds detector (value bunching below SCM thresholds per current NT instructions) | Detector | 4 | 5 | 2 | 3 | **25** | Threshold values must be verified from the current NT SCM instructions; aggregate pattern per buyer, no supplier named publicly. |
| 9 | CSI-034 | Repeat awards to the same supplier by the same buyer (frequency and share over time) | Detector | 4 | 5 | 2 | 3 | **25** | Builds on D4 concentration; named-supplier leads need four-eyes review before publication. |
| 10 | CSI-035 | Looting tracker: SIU proclamations and outcomes, AGSA material irregularities, Special Tribunal judgments, linked to entities (public records only) | Data source | 5 | 5 | 4 | 3 | **25** | Court/SIU records only; no allegations; legal review of wording (D-09). |
| 11 | CSI-036 | Uptime and freshness monitor: the nightly routine checks the live site and manifest age (SLO-PD-1) and reports breaches; optionally an external uptime check (D-08) | Operations | 3 | 4 | 1 | 1 | **24** | No workflow scope needed; runs from the bot routine. |
| 12 | CSI-037 | Population per municipality (Census 2022) from a published open table (e.g. Stats SA tables re-published on an open portal such as HDX or OpenUp/Wazimap; licence and provenance checked) | Data source | 4 | 4 | 2 | 2 | **24** | Unlocks per-resident figures (D-18, CSI-024). |
| 13 | CSI-038 | Tender splitting detector (several awards to one supplier, same buyer, short window, summing above a threshold) | Detector | 4 | 5 | 3 | 3 | **24** | Needs good entity resolution and dates; high false-positive risk, review required. |
| 14 | CSI-039 | Provincial treasuries: provincial department budgets and in-year spending (EPRE/IYM), via Vulekamali or provincial treasury publications | Data source | 5 | 4 | 4 | 2 | **24** | Extends coverage beyond national departments and municipalities. |
| 15 | CSI-040 | Year-end award spike detector (share of a buyer's awards in the last weeks of its financial year vs its own baseline) | Detector | 3 | 4 | 1 | 2 | **23** | Buyer-level indicator (no supplier named), so it can be published as an aggregate once reviewed. |
| 16 | CSI-041 | Static per-municipality pages (/m/CODE/) with their own title, description and social card, for search engines and sharing | Reach / SEO | 4 | 3 | 2 | 1 | **23** | Hash routes can't carry per-page meta; generate small static stubs in publish-data. |
| 17 | CSI-042 | Entity resolution v2: supplier name normalisation, registration-number matching where OCDS has it, and a public match-confidence note | Data quality | 4 | 4 | 3 | 2 | **23** | Underpins detectors D3/D4 and supplier pages. |
| 18 | CSI-043 | Lighthouse + axe gate in CI on every PR (scores recorded, a11y regressions fail) | Quality | 3 | 3 | 1 | 1 | **22** | Needs a GitHub token with `workflow` scope; until then dashboard_check.py runs axe locally (CHG-2026-008). |
| 19 | CSI-044 | Full data bundle download (zip of public-data with a README and licence) and a reuse/API page | Reuse | 3 | 3 | 1 | 1 | **22** | Static; helps journalists and researchers. |
| 20 | CSI-045 | Searchable supplier pages built only from public award records (no flags, natural persons withheld, right-of-reply link) | Product | 4 | 4 | 3 | 3 | **22** | POPIA: sole proprietors are natural persons, so the RSR person filter is not enough; needs a legal check (D-09). |
| 21 | CSI-046 | SOE annual reports: irregular and fruitless & wasteful expenditure and audit outcomes of the major SOEs | Data source | 4 | 4 | 4 | 2 | **22** | PDF tables; start with the largest SOEs. |
| 22 | CSI-047 | Split municipalities.json (1.5 MB) per province or per municipality for faster mobile loads | Performance | 3 | 2 | 2 | 1 | **19** | Schema v1.1 change; keep v1 for reusers. |
| 23 | CSI-048 | Site-wide search (municipalities, departments, buyers) from the header | Product | 3 | 2 | 2 | 1 | **19** | Client-side index from existing files. |
| 24 | CSI-049 | Translations (isiZulu, isiXhosa, Afrikaans, Sesotho) of the interface and explainers | Reach | 3 | 3 | 3 | 2 | **19** | Needs native-speaker review. |
| 25 | CSI-050 | Custom domain for the public site (D-17) | Reach | 2 | 2 | 1 | 1 | **18** | Owner owns DNS; Pages supports a CNAME. |

## Shipped as quick wins in CHG-2026-008 (v0.4.0)

| Item | Evidence |
|---|---|
| Social share cards and meta tags (Open Graph, Twitter) on the app and the root page; `og-card.png` (1200×630) | `tests/test_improvements.py::test_app_social_card_routes_and_report_link` |
| Data change log: `changes.json`, a `#/changes` "What's new" page, and a `feed.json` (JSON Feed 1.1). Re-exporting unchanged data leaves both files byte-identical, so the nightly routine still makes no commit | `test_unchanged_data_leaves_changelog_byte_identical`, `test_changed_data_adds_entry_with_deltas` |
| "Report an error": GitHub issue form `.github/ISSUE_TEMPLATE/data-error.yml`, with a required privacy checkbox and no personal-data fields, linked from every page and prefilled with the page address | `test_issue_form_asks_for_no_personal_data` |
| Known unknowns per province (`#/unknowns`) | dashboard_check (13 pages × desktop and mobile) |
| Accessibility and layout-shift fixes; axe-core in `dashboard_check.py` (serious or critical WCAG 2.1 A/AA violations fail the check) | See "Audit results" below |

## Audit results (19 Oct 2026, local server, same data; headless Chrome)

| Run | Performance | Accessibility | Best practices | SEO | CLS |
|---|---|---|---|---|---|
| before, mobile (Lighthouse 12) | 77 | 96 | 100 | 100 | 0.73 |
| before, desktop (Lighthouse 12) | 76 | 96 | 100 | 100 | 0.825 |
| after, mobile (Lighthouse 12) | 100 | 100 | 100 | 100 | 0.008 |
| after, desktop (Lighthouse 12) | 100 | 100 | 100 | 100 | 0.004 |

- **axe-core 4** (WCAG 2.0/2.1 A and AA) on the 11 existing pages × 2 viewports:
  - Before: serious violations on every page view (19 page-views): `color-contrast` (status pills, active nav item, audit-opinion chips) and `scrollable-region-focusable` (scrolling tables on mobile).
  - After: **0 violations** on all 13 pages × 2 viewports.
- The live site, before the change (https://farwaters.github.io/publicfunds-sa/apps/public-dashboard/, 21:43 SAST) scored mobile 77/96/100/100 and desktop 76/96/100/100.

## Biggest next bets (need the owner's decision)

1. **PPD payments via manual drop** (#1). This unlocks real payments and unit prices, so the R123/l-diesel-style exceptions and the unit-price detector (#4) become possible. Needs the owner to export the CSVs by hand on a regular schedule (KE-009).
2. **Detectors that name suppliers** (#8, #9 and the tender-splitting detector). They need named-supplier review capacity, and reviewers are parked (D-12). They also need a legal review before supplier pages (D-09). Decide whether to build them now as hidden leads only.
3. **AGSA per-entity annexures and a looting tracker** (#5, #10). This is a large data effort (PDF and Excel), and the public wording needs legal review. It is the heart of the UIF&W and looting mission.
