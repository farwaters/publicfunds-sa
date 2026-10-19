# Grok Build prompt: PublicFunds SA public dashboard

Paste everything below the line into Grok Build (grok.com, Build mode). It is self-contained.

---

Build and publish **PublicFunds SA**, a public website that helps South African taxpayers see where public money goes.
It must work for anyone with a browser: no login, no Grok account, no app install.

## Start from the existing code
- A complete working version already exists as one self-contained file:
  https://raw.githubusercontent.com/farwaters/publicfunds-sa/main/apps/public-dashboard/index.html
  (repo: https://github.com/farwaters/publicfunds-sa, folder `apps/public-dashboard/`).
- Use it as the starting point and keep its behaviour, texts and rules.
- You may restyle it, or split it into components, but don't drop features or safeguards.
- If you cannot fetch the URL, ask me to paste the file.

## Data (read-only, fetched in the browser)
- Base URL: `https://raw.githubusercontent.com/farwaters/publicfunds-sa/main/public-data/v1/`
  - Make the base URL configurable. The existing code reads `?data=<url>` or `window.PUBLICFUNDS_DATA_BASE`.
  - The files are static JSON, served with CORS by GitHub, and updated after each successful daily data refresh.
- No backend and no database are needed. Don't copy the data into the app; always fetch it live, so the site stays
  current.
- Schema `publicfunds.public-data/v1`. Start from `manifest.json`.

| File | What it holds |
|---|---|
| `manifest.json` | `generated_at_sast`; `build` (id, data-quality pass/warn/fail); `files` (name, bytes, sha256); `counts`; `coverage` (headline: `complete_pct`, `complete`, `applicable`, `entities`, `fye_min`, `fye_max`, `by_type`); `sources[]` (name, publisher, page, licence, `last_run_status`, `last_new_data_sast`, problem); `known_gaps[]` (plain-language text); `known_errors[]`; `population` (`status: unknown` + reason); `disclaimers[]`; `freshness_slo` |
| `coverage.json` | `years[]`, `fy_labels[]`, `data_types[]` (budget, actual_audited, uifw, audit_opinion, procurement), `states` (P present, p partial, m missing, - not applicable), `reasons[]`, `entities[]`. Each entity is `{id, c: {type: "PPPpm-…"}, r: {type: "0012…"}}`: one character per year; in `r`, 0 means no reason and n means `reasons[n-1]` |
| `municipalities.json` | `municipalities[]` with id, code, name, province (EC FS GT KZN LP MP NC NW WC), type (metro/local/district), category, profile (Municipal Money link). `years{fye: {budget, adjusted, audited: {rev, exp, basis, src}, uifw: {irregular, fruitless_wasteful, unauthorised, src}, audit: {code, report, src}}}`. Plus `audit_opinions` (code to label), `report_prefix` and `sources{src: {url, file, fetched_at_sast}}`. The financial year ends 30 June: fye 2025 is 2024/25 |
| `departments.json` | `departments[]` (id, name, vote). `years{fy: {main, adjusted, final, audited: {amount, lines, unknown_lines, approx_lines, src}}}`. The national financial year starts in April: 2025 is 2025/26 |
| `tenders-summary.json` | `all_years`; `buyers[]` (id, name, gov_body_id, `years{year or "all": {awards, valued, missing_value, implausible_value, missing_share, known_value, suppliers, top_supplier_share, hhi}}`); `award_files` |
| `awards-YYYY.json` | `columns` + `rows` of published eTenders award records: ocid, award_id, date, date_basis, buyer, supplier, value, value_note, reference, method, category, doc, src. A `doc` of the form `blob\|file` means `doc_prefix + blob + "&downloadedFileName=" + encodeURIComponent(file)` |
| `flags.json` | `confirmed[]`: only flags confirmed by human review, currently none. `hidden_leads` (counts by detector). `detectors` (plain-language descriptions). `policy`, `disclaimer` |
| `prices.json` | `fuel` (grades, rows `[year, month, grade, cents_per_litre, src]`, last_period); `cpi` (rows `[YYYY-MM, index, src]`, base, publisher, last_period) |

## Non-negotiable rules
1. **Money**
   - All money values are integer **cents**. Show them as rand: R1.2 bn, R350 m, R12 400.
   - `null` means **unknown**: show "unknown", never 0. Don't interpolate or fill gaps.
2. **Every figure links to its source**, using its `src` key and the file's `sources` map, or the record's link.
3. **Flags**
   - Show only `flags.json.confirmed`.
   - Explain that other leads are under review and hidden, and give the counts.
   - Always say that flags are indicators, not findings of wrongdoing.
   - Never compute or show your own "red flags", rankings of suspicious suppliers, or accusations.
4. **Tender awards** are public records shown as published. Label them "not flags or findings".
   - Supplier concentration is shown without supplier names.
   - "(name withheld)" stays withheld.
5. **Personal data:** don't add names of individuals, ID numbers, photos, or contact details of officials.
6. **Freshness:** show the data time (`generated_at_sast`, in SAST). Warn if it is older than 48 hours, or if a
   source's `last_new_data_sast` is older than its `freshness_slo_days`.
7. **Plain language** for taxpayers, in English.
   - Keep the disclaimer banner on every page.
   - Keep the "What we don't know" panel on the home page, from `known_gaps` and `population`.

## Pages
- **Home:**
  - headline numbers;
  - data freshness per source;
  - the "What we don't know" panel;
  - entry cards.
- **Data coverage:**
  - a heatmap of municipality × financial year for the selected data type;
  - filters: data type, province, municipality type, search;
  - a reason on hover or focus for each cell;
  - a summary table.
- **Municipalities:**
  - list and search;
  - a page for each municipality: KPIs, budget vs actual chart and table, irregular / fruitless & wasteful /
    unauthorised trend, audit opinion history with report links, tenders by year with award records (loaded on
    demand), coverage, and a link to compare.
- **National departments:** list, plus a page per department with its budget phases and spent vs final
  appropriation.
- **Tenders:** totals by year, a buyers table (search and sort) and award records.
- **Flags:** confirmed flags (an empty state explains why there are none) and hidden leads by type.
- **Tools:**
  - **Inflation adjuster:** rand amount and two months, using the CPI ratio. Show the index values, the source and
    the latest month.
  - **Fuel price checker:** date, grade and optional price paid. Use the official price for that month. Prices change
    on the first Wednesday, so earlier dates use the previous month. Show the difference in R and %. Note that diesel
    and paraffin are not regulated at the pump.
  - **Compare two municipalities:** side by side for a chosen year, with sources.
  - **Per resident:** show "unknown" with `population.reason` until population data exists.
- **Sources & method:** sources table, how it works, the checks, known errors, data files to reuse, disclaimers.
- **Download CSV** of every table view. The CSV contains rand values and source URLs, and cells starting with `= + - @`
  are neutralised.

## Quality bar
- **Mobile-first and fast:**
  - load `manifest.json` first;
  - load other files only on the pages that need them;
  - load the award files (about 2.3 MB in total) only when asked.
- **Accessible (WCAG 2.1 AA):**
  - semantic headings, skip link, visible focus, labelled form controls;
  - charts with a text or table equivalent;
  - colour never the only signal (cells also show ✓ ~ ✗ –);
  - respect `prefers-reduced-motion`; dark mode is OK.
- **Secure:**
  - render all data as text (no `innerHTML` with data);
  - allow only `http(s)` links, opened with `rel="noopener nofollow"`;
  - no third-party trackers or analytics without asking me;
  - no cookies.
- **Test before publishing:**
  - every page on a phone and a desktop viewport;
  - no console errors;
  - the fuel checker for 15 October 2026, Petrol 95 inland, shows the official October 2026 price;
  - the inflation adjuster works;
  - CSV downloads open in a spreadsheet.

## Publish
- Publish to a public URL (a grok.me address is fine). Title: "PublicFunds SA". Description: "Follow South Africa's
  public money: budgets, spending, audit results and tenders from official open data, with the gaps shown."
- Add a footer link to the repository and to `manifest.json`.
- **Custom domain later:** in the app's publish settings, add the domain (for example `publicfunds.example.org.za`),
  then create the DNS record Grok Build shows (usually a CNAME for a subdomain) at your DNS host. Wait for HTTPS to
  be issued, then check that the site loads on the new address.
  - The data URLs don't change; to serve the data from your own domain later, change only the data base URL.
- Optionally, export the finished app to GitHub at `apps/public-dashboard/` in the same repo as a pull request,
  so the code stays reviewable.
