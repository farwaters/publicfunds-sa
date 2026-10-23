# CHG-2026-015: Municipality report card (#/m/<id>/card)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-23 15:00 |
| Environment | DEV only (branch `feat/report-card` from origin/main; not merged, nothing pushed to main) |
| Type | **Normal**. New read-only dashboard view over already-published public-data; no exporter, data or publication-config change |
| CIs affected | `apps/public-dashboard/index.html`, `scripts/dashboard_check.py` (new route), `tests/test_report_card.py` (new), this record, `itil/registers/change-log.md` |
| Linked records | Roadmap CSI-027/CSI-028 (closest items; the roadmap has no explicit report-card CSI), CHG-2026-008 (share cards), CHG-2026-011 (AGSA annexures, unpublished), CHG-2026-013 (glossary) |
| PR | branch `feat/report-card` |

## What
A plain-language card per municipality at `#/m/<id>/card`, linked from the municipality page. Indicators side by side;
**no grade or composite score** (the card says so).

| Indicator | public-data field |
|---|---|
| Latest audit opinion + year + source | `municipalities.json` `years[*].audit.code/src`, `audit_opinions` (already shown on the municipality page; National Treasury Municipal Money copy of the AGSA opinion) |
| AGSA annexure figures | Not shown: "not yet published" (checklist `docs/legal/agsa-wording-review-checklist.md` not signed off) |
| Irregular, fruitless & wasteful, unauthorised (latest year) | `municipalities.json` `years[*].uifw.*` ; null shown as "blank: not published (unknown, not zero)" |
| Data completeness | `coverage.json` `entities[].c/r`, `fy_labels`, `reasons` (present / partial / missing counts, missing list with reasons) |
| Confirmed published flags | `flags.json` `confirmed[]` filtered by `gov_body_id`, minus `never_publish` detectors. `hidden_leads` is never read |

Share-friendly: the card is a single bordered block (max 760 px, brand top border, site name in the footer line) with a
"Copy link to this card" button; the existing print rule hides chrome.

## Not changed
Exporter, public-data files, publication.yaml, detectors.yaml, other pages (except one link on the municipality page).

## Tests and checks
- `.venv/bin/python -m pytest -q`: 206 passed (4 new in `tests/test_report_card.py`: route order, never reads hidden/unpublished data
  or AGSA annexures, never_publish list equals publication.yaml, flag filter + completeness logic via node).
- `scripts/dashboard_check.py`: exit 0, no problems; new `report-card` page on desktop and mobile, axe clean.
- Lighthouse (local, `#/m/MUN:BUF/card`): accessibility 100, best practices 100, SEO 100, performance 75 (local unthrottled
  http.server, no compression; same app shell as the other pages).

## POPIA review (popia-review release check)
Scan of the diff, new test and screenshots: no ID, phone, email, address, account numbers, keys or officials' names. The card
shows municipality-level official figures only; no supplier names; flags are counts of confirmed flags only, framed as
"not a finding of wrongdoing". No GitHub references in served files. **Verdict: PASS.**

## Back-out
Do not merge the PR, or revert its merge commit (git history is the rollback). Copies of edited files before the change
were also kept outside the repo in `/workspace/bkp/` on the build box.

## Result
DEV build succeeded. Pending independent review (expert, shadow, charter, drift) and owner merge decision.
