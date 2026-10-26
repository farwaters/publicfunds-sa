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
   - It prints one stdout line starting `evidence_guard:` (CHG-2026-040 guard; CHG-2026-041 line), then up to 3 note lines: `pass`, `pass (N notes)`, `warn (N notes)`, `BLOCKED (exit 3 ...)`, `not an evidence-guard refusal (...)` or `UNKNOWN (...)`.
     **Report that line to the owner in the nightly report whenever it is anything other than exactly `evidence_guard: pass`** (the bare `pass` is the only quiet value), with its note lines.
     Treat `UNKNOWN` as "guard not checked", never as pass. **If there is no `evidence_guard:` line at all, treat that as UNKNOWN too, not as pass.**
   - **If it exits 3, report it to the owner** (do not retry, do not edit data): the export was refused and **nothing was published**; the files in `public-data/` are left as they are and nothing was committed or pushed.
     Quote the `evidence_guard:` line (`BLOCKED` = the evidence guard refused; `not an evidence-guard refusal` = no guard refusal was found in the log, so the cause may be the quality gate, the safety scan, another refusal or a crash: read `data/publish-data.json` and `data/publish-data.log`).
     `scripts/check_live.py` warns at 30 h of data age and breaches at 48 h (RB-12), so a repeated exit 3 must reach the owner before then.
5. Check `curl -s http://127.0.0.1:8765/healthz`. If it is not ok, run `scripts/review-app.sh restart`. A broken audit chain is a security incident: stop and tell the user.
6. Never confirm or reject flags here. Reviews happen only in **publicfunds-review**, on the user's instruction.
