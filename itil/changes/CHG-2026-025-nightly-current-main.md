# CHG-2026-025: Nightly refresh runs current origin/main

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-24 08:17: "GO on CHG-2026-025" (covers this change only; not a GO to merge PR #22 or anything else to main) |
| Environment | DEV/ops on the box. Touches only the publicfunds-refresh skill text; no repo code, no data, nothing pushed to main |
| Type | Standard (one added guarded step in an owner-approved routine skill) |
| CIs affected | `/home/box/agent-data/workflows/publicfunds-refresh/SKILL.md` (same file as `/home/box/sand-data/workflows/publicfunds-refresh/SKILL.md`, same inode), this record, `itil/registers/change-log.md` |
| Linked records | RB-11 (`scripts/publish-public-data.sh`), CHG-2026-018 to 023, data commit 15c55e7 |
| Rollback | Remove step 0 (the line starting `0. ` and its two `   - ` sub-bullets) or restore the original block below. Original sha256 `97e3daa9bcf4db707ea91040cd995b0949ef131f37526e3466ba220592487efe`; verify with the sha256 check in the original-text section. Close the PR unmerged / `git revert -m 1 <merge>` for this record. No .bkp files |

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
Step 0 added to the skill, before the existing step 1 (steps 1-5 unchanged). Exact live text (copied from the file, not paraphrased):

````text
0. Update the checkout first (CHG-2026-025). Run exactly: `cd /workspace/publicfunds && [ "$(git branch --show-current)" = main ] && [ -z "$(git status --porcelain --untracked-files=no)" ] && git fetch -q origin && git merge --ff-only origin/main`
   - Any non-zero exit (not on `main`, tracked file modified, offline fetch, diverged, index.lock) means **stop and report**: skip steps 1 to 5 (including the healthz check and any publish), run nothing else, and do not push, reset or clean. In the routine's final SendToUser message give the error text, `git status --short`, and the local HEAD and `origin/main` SHAs (`git rev-parse --short HEAD origin/main`).
   - "Already up to date" is a pass (also when local `main` is ahead of origin with an unpushed data commit). Never `reset --hard`.
````

What the guard does, tested in a scratch repo (bare origin, clones; command with `cd` pointed at the clone):

| # | Case | Result | HEAD before -> after |
|---|---|---|---|
| 1 | main, clean, up to date | pass, rc 0 ("Already up to date.") | unchanged |
| 2 | main, clean, behind origin | pass, rc 0, fast-forward | moved to origin/main |
| 3 | feature branch, behind origin | **stop**, rc 1 (branch test) | unchanged |
| 4 | dirty tracked file, behind origin | **stop**, rc 1 (status test) | unchanged |
| 5 | diverged (local commit + origin commit) | **stop**, rc 128 (`merge --ff-only` refuses) | unchanged |
| 6 | offline / unreachable origin | **stop**, rc 128 (fetch fails) | unchanged |
| 7 | main ahead of origin (unpushed commit) | pass, rc 0 ("Already up to date."); run proceeds on that state | unchanged |
| 8 | detached HEAD | **stop**, rc 1 (branch test) | unchanged |
| 9 | untracked file only, behind | pass, rc 0, fast-forward (untracked files are ignored on purpose; a ff cannot overwrite them silently, git refuses if it would) | moved |

"Stop and report" is defined in the step: skip steps 1 to 5 (including the healthz check and any publish); run nothing else;
do not push, reset or clean; the routine's final SendToUser message carries the error text, `git status --short`, and the
local HEAD and `origin/main` SHAs. Only a divergence (or a dirty tree, other branch, offline fetch, index.lock) fails; being
on another branch is stopped by the explicit branch test, not by git, and the earlier claim that "another branch fails" is
withdrawn: a ff-only merge on another branch would succeed when behind, which is why the branch test is in the command.

### Notes
- If local `main` is ahead of origin/main (an unpushed data commit), `merge --ff-only` prints "Already up to date" and the run
  proceeds on that unpushed state. Accepted.
- A concurrent `thusa run` on the same warehouse is out of scope; git's `index.lock` makes a second fetch or merge fail,
  which is a stop-and-report.
- The venv `/workspace/publicfunds/.venv` was not restored after the 2026-10-24 box re-hydration, so `uv run` needs network
  access to rebuild it.
- The skill lives outside git (`/home/box/sand-data/workflows/publicfunds-refresh/SKILL.md`; `/home/box/agent-data` is a symlink to
  it) and a background library sync reverted it once on 2026-10-24 08:18; the live file must be re-checked after a sync.

Out of scope: the publish script and its guards, code, data, the routine's schedule, PR #22.

## Original skill text (pre-change; rollback copy)
sha256 `97e3daa9bcf4db707ea91040cd995b0949ef131f37526e3466ba220592487efe` (the live file with the three step-0 lines removed
hashes to exactly this value). Restore by writing this block back, with no trailing change.

````markdown
---
name: publicfunds-refresh
description: >-
  Use for the daily PublicFunds data refresh (from a scheduled routine or on
  request): ingest all sources, rebuild the warehouse, run the data-quality gate
  and report what changed.
---
# PublicFunds refresh

1. `cd /workspace/publicfunds && uv run thusa run > data/refresh-$(date +%F).log 2>&1; echo $?`
   - **0** means the build is releasable.
   - **2** means a data-quality check failed. Don't publish anything; summarise the failed checks and follow runbook RB-01.
2. Read the latest entries in `data/raw/runs.jsonl` and report each source's status. For any source that is not `ok`:
   - if a known error already matches it (`itil/knowledge/known-errors.md`), name it;
   - otherwise draft an incident with **publicfunds-itil**.
   Never bypass a block (403, login, WAF).
3. Report briefly: the coverage headline, flag counts by detector, and new flags or flags with "evidence changed" (`uv run pf review list --status stale`).
4. Check `curl -s http://127.0.0.1:8765/healthz`. If it is not ok, run `scripts/review-app.sh restart`. A broken audit chain is a security incident: stop and tell the user.
5. Never confirm or reject flags here. Reviews happen only in **publicfunds-review**, on the user's instruction.

````

## Tests (worktree of origin/main 15c55e7, fresh uv .venv)
- `pytest`: 166 passed, 60 skipped.
- Fingerprint (sha256 of json.dumps(sorted([(year, month, grade, cents_per_litre, source_locator)])), first 16 hex, basenames
  of data/raw/dmpr_fuel/*/*.pdf): `80bc13d78db54047`, 581 rows (unchanged).

## POPIA review
PASS. No personal information, IDs, contacts, accounts or credentials in the skill line or this record.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author. Merging this PR needs a separate owner GO.

Result: skill change applied; awaiting review.
