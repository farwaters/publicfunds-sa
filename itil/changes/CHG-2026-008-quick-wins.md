# CHG-2026-008: Public dashboard quick wins (social cards, What's new + feed, report-an-error, known unknowns, accessibility)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-19 21:41 ("over to you to come up with improvements and/or enhancements") |
| Type | **Normal**. The public site and the export gain additive features, with no change to what data or flags are published, and no new named-supplier flags. Owner approves the merge |
| CIs affected | CI-104 (export: new `changes.json`, `feed.json`), CI-105 (app), CI-109 (dashboard_check: axe scan, 2 new pages), new CI-112 (issue form `.github/ISSUE_TEMPLATE/`), new CI-113 (social card `apps/public-dashboard/og-card.png`) |
| Linked records | docs/roadmap/improvements-2026-10.md, CSI-026 to CSI-050, RSK-022 (misreading), RSK-023 (defamation), SLO-PD-3 |
| PR | branch `feat/improvements-2026-10` (unmerged) |

## What
1. **Social share cards:** Open Graph and Twitter meta tags, canonical URL and theme colour on the app and the root redirect
   page, plus a 1200×630 card image.
2. **What's new:**
   - `pf publish-data` keeps `changes.json`: one entry per build whose data changed, at most 100, newest first.
   - Each entry records count deltas, the coverage change and the files changed.
   - The export also writes `feed.json` (JSON Feed 1.1), and the app has a `#/changes` page.
   - Re-exporting identical data leaves both files byte-identical. **`scripts/publish-public-data.sh` is unchanged:** its
     timestamp-only check still skips the commit when only `manifest.json` timestamps change. The first nightly run after
     merge adds both files and makes one commit.
3. **Report an error:**
   - A GitHub issue form with no personal-data fields, a required privacy checkbox, and a pointer to the official
     anti-corruption hotline instead.
   - Linked from every page's footer and prefilled with the page address.
4. **Known unknowns (`#/unknowns`):** the share of municipality-years fully published, per province and data type, plus
   the most common reason for each gap. It is computed in the browser from `coverage.json`.
5. **Accessibility and performance:**
   - Contrast fixes: status pills, the active nav item, opinion chips and heatmap cells.
   - Scrolling tables are focusable regions with labels.
   - Reserved main height removes the layout shift (CLS 0.73 → 0.008 on mobile).
   - `dashboard_check.py` now runs axe-core when it's installed and fails on serious or critical violations.

## Risk
- Low.
- No new data categories, and flags are unchanged: confirmed flags only.
- The issue tracker is public. The form warns against including personal data. Triage removes any that slips in
  (RB-11 takedown).

## Testing
- `pytest`: 185 passed, including 6 new tests in `tests/test_improvements.py` and the 59 warehouse DQ tests, run
  read-only against the main warehouse.
- `dashboard_check.py`: 13 pages × desktop/mobile, 0 problems, 0 axe violations.
- Lighthouse 12, before → after (local, same data):
  - mobile 77/96/100/100 → 100/100/100/100;
  - desktop 76/96/100/100 → 100/100/100/100.
  The four numbers are performance/accessibility/best practices/SEO. Details: docs/roadmap/improvements-2026-10.md.

## Back-out
- Revert the merge commit.
- `changes.json` and `feed.json` disappear on the next export, which deletes files it no longer writes.

## Approval
| Role | Name | Date (SAST) | Decision |
|---|---|---|---|
| Owner | | | |
