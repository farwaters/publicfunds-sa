# CHG-2026-014: Change-log correction for CHG-2026-012 status

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-23 14:43 |
| Type | **Standard**. Documentation-only correction to the change log; no code, data or publication change |
| CIs affected | `itil/registers/change-log.md` (CHG-2026-012 status cell; new CHG-2026-014 row) |
| Linked records | CHG-2026-012, PR #8 |
| PR | branch `docs/chg-2026-014` (unmerged) |

## What
1. CHG-2026-012 status changed from "Pending owner merge" to "Merged PR #8 (2026-10-23, owner approved)".
   Verified with `gh pr view 8`: state MERGED, merged 2026-10-23 08:44 UTC (10:44 SAST).

## Not changed
Any other row or file.

## Back-out
Revert the merge commit.
