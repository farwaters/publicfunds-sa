# CHG-2026-017: Known unknowns v2 (CSI-028): trend over time and per-municipality ranking

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-23 15:45 ("pick the single highest-value remaining roadmap item") |
| Environment | DEV only (branch `feat/unknowns-v2` from origin/main e5d9c3a; PR open, not merged, nothing pushed to main) |
| Type | **Normal**. Read-only addition to the existing `#/unknowns` view over already-published `coverage.json`; no exporter, data or config change |
| CIs affected | `apps/public-dashboard/index.html` (vUnknowns only), `tests/test_unknowns_v2.py` (new), this record, `itil/registers/change-log.md` |
| Linked records | Roadmap CSI-028 (score 26), CHG-2026-008 (v1 per-province scoreboard) |
| Rollback | Close the PR unmerged. If ever merged: `git revert -m 1 <merge commit>` (git history is the rollback; no .bkp files per owner amendment) |

## Why this item
Remaining eligible items, highest score first: CSI-028 (26) needs only coverage.json. CSI-026 (28) needs the owner's manual
PPD export; CSI-029 (26) depends on PPD line items and leads stay hidden; CSI-030 (26) AGSA load done but not cleared.
Next two eligible: CSI-031 CPI (25, source access/licence still to be verified, Stats SA WAF) and CSI-032 fuel history (25, partly
done in CHG-2026-009; pre-2019 archive is multi-document work).

## What
Two tables added to `#/unknowns`, each with a CSV download, using the v1 counting rule (skip `-` and `?`, years fye_min..fye_max):
1. Trend over time: share of municipality data items fully published per financial year, all types and per data type.
2. Municipalities ranked lowest-published first (25 shown, CSV has all), with partial/missing counts and a link to the municipality page.

Lineage: every number is a count over `public-data/v1/coverage.json` `entities[].c`; no new figures.

## Not changed
Exporter, public-data files, other views, dashboard_check.py page list (`#/unknowns` already covered).

## Tests and checks (2026-10-23, DEV)
- `.venv/bin/python -m pytest -q`: 215 passed (3 new in tests/test_unknowns_v2.py; one reconciles the page's counting rule with the exporter's `headline.by_type`).
- `scripts/dashboard_check.py`: problems [] (all pages, desktop + mobile, axe 0 violations).
- Lighthouse 12 accessibility on `#/unknowns` (local): 100.

## popia-review: PASS
Scan of the diff: no ID, passport, phone, email, address, account numbers, plates, locations or keys. Only public bodies
(municipalities) and aggregate counts; no suppliers, no people, no flags, no AGSA annexure figures. Nothing removed.

## Four checks
Pending (author does not sign off; Law I). Outcome: pending review. PROD needs the owner's quoted GO for this PR.
