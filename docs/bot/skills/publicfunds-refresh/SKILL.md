---
name: publicfunds-refresh
description: Daily data refresh for PublicFunds (Thusa) - ingest all sources, rebuild the warehouse, run the data-quality gate, refresh the public dashboard data and report what changed. Run it from a scheduled routine or on request.
---
# PublicFunds refresh

1. `cd /workspace/publicfunds && uv run thusa run > data/refresh-$(date +%F).log 2>&1; echo $?`
   - **0** means the build is releasable.
   - **2** means a data-quality check failed. Don't publish anything; summarise the failed checks and follow runbook RB-01.
2. Read the last `runs.jsonl` entries (`data/raw/runs.jsonl`) and report each source's status. For any source that is not `ok`:
   - if a known error already matches it (`itil/knowledge/known-errors.md`), name that KE;
   - otherwise, draft an incident with **publicfunds-itil**.
   Never bypass a block (403, login, WAF).
3. Report briefly:
   - the coverage headline;
   - flag counts by detector;
   - new flags and flags with "evidence changed" (`uv run pf review list --status stale`).
4. Public dashboard data (only if step 1 returned **0**): run `scripts/publish-public-data.sh`.
   - It runs `pf publish-data`, which refuses if the quality gate failed. It then commits **only** `public-data/`.
   - Add `--push` to push that commit to `origin/main`, where the public dashboard reads it. This push is
     pre-authorised **only** when you run it from the daily refresh routine the user approved. Otherwise, ask first.
   - Never push anything else. Never force-push.
   - If it exits 4 (other changes, wrong branch, main moved), stop and report.
5. Check `curl -s http://127.0.0.1:8765/healthz`. If it is not ok, run `scripts/review-app.sh restart`. A broken audit chain is a security incident: stop and tell the user.
6. Never confirm or reject flags here. Reviews happen only in **publicfunds-review**, on the user's instruction.
