# CHG-2026-006: Public dashboard via Grok Build, with a public data export and price benchmarks

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-19 17:47 ("new direction, approved") |
| Type | **Normal-high**: the first public-facing surface; it publishes data and confirmed flags to the internet. Owner approval required; second reviewer parked (D-12) |
| CIs affected | New: CI-104 (public data export), CI-105 (public dashboard app), CI-106 (DMPR fuel source), CI-107 (OECD CPI source), CI-108 (curated price tables), CI-109 (`dashboard_check.py`), CI-110 (`publish-public-data.sh`). Changed: CI-070 (skills: publicfunds-refresh), CI-101 (publication policy, now also read by the export), CI-102 (template becomes the power-user/reviewer version) |
| Linked records | ADR-0010 (supersedes part of ADR-0009), D-03 (reopened and resolved: Grok Build), D-16, D-17, D-18, RSK-022 to RSK-024, SLO-PD-1, KE-003, KE-012, CSI-022 to CSI-025, RB-11 |
| PR | branch `feat/public-dashboard` (PR to `main`, unmerged) |

## What and why
The general public can't use a Grok Bot template. This change adds a no-login website that the owner publishes with
Grok Build, fed by a public JSON export from the pipeline:
1. **Price benchmarks:**
   - DMPR fuel prices (`dmpr_fuel`: the monthly adjustment ZIP containing the "History of Fuel Prices" DOCX table).
   - CPI (`oecd_cpi`: OECD SDMX, CC BY 4.0, used because Stats SA blocks scripted access, KE-003).
   - New tables `curated.fuel_price` and `curated.cpi`, with DQ checks.
2. **`pf publish-data`** writes `public-data/v1/*.json`: manifest, coverage, municipalities, departments, tenders
   summary, award records per year, flags (confirmed only) and prices.
   - Gates: a DQ fail blocks the export; a safety scan blocks it on forbidden keys, SA ID numbers, secrets-shaped
     values or restricted-person names; the size budget is enforced.
3. **`apps/public-dashboard/index.html`:** a single-file, mobile-first, accessible SPA.
   `GROK_BUILD_PROMPT.md` is the prompt the owner pastes into Grok Build.
4. **`scripts/publish-public-data.sh`**, plus a step in the `publicfunds-refresh` skill: commit and push only
   `public-data/` after a successful refresh. The push is pre-authorised only from a routine the owner approves.
   The routine is **not** created by this change.

## Risk and impact
- See RSK-022 to RSK-024.
- No change to the review app, the review DB or the audit trail.
- The main warehouse at `/workspace/publicfunds` was not rebuilt by this change. It picks up the price tables on its
  first `thusa run` after merge.

## Testing
- `pytest`: the full suite, plus `tests/test_publish_data.py`. It checks that no unconfirmed flag leaks (four-eyes),
  that there is no PII or review secret, that restricted-person names are withheld, the schema and checksums, that
  money is integer cents or null, the quality gate, the size budget, the price parsers, and that the committed
  `public-data/` matches its manifest.
- `scripts/dashboard_check.py`: headless Chrome against the real export. It visits 11 pages at desktop
  (1366×900) and mobile (390×844) sizes, with zero console errors, page errors or failed requests. It also
  exercises the fuel checker, the inflation adjuster, a CSV download and the mobile menu. Screenshots go to
  `dist/public-dashboard/`.

## Implementation plan
1. Review and merge the PR. The raw data URLs work only after the merge.
2. Paste `apps/public-dashboard/GROK_BUILD_PROMPT.md` into grok.com Build mode, check the preview, then publish to
   grok.me.
3. Record the URL in CI-105 and README (D-16).
4. Optionally, add a custom domain (D-17).
5. Optionally, approve a daily refresh routine that runs the `publicfunds-refresh` skill, including
   `publish-public-data.sh --push`.

## Back-out
- Unpublish the app in Grok Build.
- Revert the merge commit.
- If a bad export went out, revert the `public-data/` commit. GitHub raw caches for about 5 minutes.
- If personal data was published, follow RB-11 (§ "takedown"), and also handle it as a security incident (RSK-021).

## Approval
| Role | Name | Date (SAST) | Decision |
|---|---|---|---|
| Owner | | | |
