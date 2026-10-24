# CHG-2026-025: Nightly refresh runs current origin/main

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-24 08:17: "GO on CHG-2026-025" (covers this change only; not a GO to merge PR #22 or anything else to main) |
| Environment | DEV/ops on the box. Touches only the publicfunds-refresh skill text; no repo code, no data, nothing pushed to main |
| Type | Standard (one added instruction line in an owner-approved routine skill) |
| CIs affected | `/home/box/agent-data/workflows/publicfunds-refresh/SKILL.md` (same file as `/home/box/sand-data/workflows/publicfunds-refresh/SKILL.md`, same inode), this record, `itil/registers/change-log.md` |
| Linked records | RB-11 (`scripts/publish-public-data.sh`), CHG-2026-018 to 023, data commit 15c55e7 |
| Rollback | Delete the line starting `0. ` from the skill file. Original sha256 `97e3daa9bcf4db707ea91040cd995b0949ef131f37526e3466ba220592487efe`; verify with `grep -v '^0\. ' SKILL.md \| sha256sum`. Close the PR unmerged / `git revert -m 1 <merge>` for this record. No .bkp files |

## Problem
The skill's step 1 ran `uv run thusa run` in `/workspace/publicfunds` with no git update. On 2026-10-23 that checkout
was at 142c0d4, 32 commits behind origin/main (missing CHG-2026-018 to 023); the venv is an editable install pointing at
that checkout, so the run would have built from old code.

## Findings (read 2026-10-24 ~08:18 SAST, after `git fetch`)
- Local `main` HEAD = origin/main = `15c55e7`; tree clean; branch up to date. Nothing to fast-forward.
- Reflog: `142c0d4` -> `da29dbc` by `pull --ff-only origin main` (the 03:00 routine's own saved prompt pulled, so the
  run was already on da29dbc) -> `15c55e7` by the routine's data commit `data: refresh public-data/v1 (B20261024T010413Z)`
  (public-data/ only: changes, departments, feed, manifest, municipalities, prices .json).
- `data/refresh-2026-10-24.log`: every source row carries `git_commit: da29dbc`; run started 01:00 UTC = 03:00 SAST.
- Live `https://publicfunds.grokforum.site/public-data/v1/manifest.json`: build B20261024T010413Z, `code_commit` da29dbc,
  data quality 57 pass / 1 warn / 0 fail. `prices.json`: labels "Leaded Replacement Petrol (LRP) 93, inland",
  "Leaded Replacement Petrol (LRP) 95, coast", "Unleaded Petrol (ULP) 95, inland"; CPI to 2026-07 (223 rows, IMF
  republication of Stats SA); fuel months 2021-11, 2022-09, 2023-01/05/10/12 present. Live data came from current code.
- The routine's saved prompt is not readable from the box (no routine folder found); only the generic routines skill exists.
  The pull seen in the reflog is the evidence. The skill is the only readable instruction, so it is made consistent.
- The box workspace was re-hydrated at 08:18 SAST; `/workspace/publicfunds/.venv` (and with it the editable `.pth`) was not
  restored, so `uv run` will rebuild it on the next run (needs network). Not changed here.

## Change
Added step 0 to the skill, before the existing step 1 (steps 1-5 unchanged):

`0. cd /workspace/publicfunds && git fetch -q origin && git merge --ff-only origin/main` (checkout on `main`, tree clean).
Fast-forward only, never `reset --hard`. If it fails (dirty tree, other branch, not a fast-forward), stop and report instead of running.

Out of scope: the publish script and its guards, code, data, the routine's schedule, PR #22.

## Tests (worktree of origin/main 15c55e7, fresh uv .venv)
- `pytest`: 166 passed, 60 skipped.
- Fingerprint (sha256 of json.dumps(sorted([(year, month, grade, cents_per_litre, source_locator)])), first 16 hex, basenames
  of data/raw/dmpr_fuel/*/*.pdf): `80bc13d78db54047`, 581 rows (unchanged).

## POPIA review
PASS. No personal information, IDs, contacts, accounts or credentials in the skill line or this record.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author. Merging this PR needs a separate owner GO.

Result: skill change applied; awaiting review.
