---
name: publicfunds-setup
description: Install or repair PublicFunds (Thusa) on this bot's computer with the idempotent bootstrap script - code, pinned dependencies, pipeline, tests, a local admin reviewer, and the localhost review app.
---
# PublicFunds setup

1. Run, and keep the output short in chat:
   `curl -fsSL https://publicfunds.grokforum.site/scripts/bootstrap.sh | bash`
   - Until the PRs merge to `main`, use `.../feat/review-app/scripts/bootstrap.sh` with `PF_BRANCH=feat/review-app`.
   - If `/workspace/publicfunds` already exists, run `/workspace/publicfunds/scripts/bootstrap.sh` instead. It is safe to re-run.
   - Settings are environment variables: `PF_BRANCH`, `PF_PORT` (default 8765), `PF_ADMIN_USER` (default `admin`), `PF_CONFIG_DIR` (default `~/.config/publicfunds`).
2. Success means the script ends with "done", and `curl -s http://127.0.0.1:8765/healthz` shows `"status":"ok"`.
3. Report to the user:
   - the coverage headline (`complete_pct` in `data/bootstrap-run.log`);
   - the test result line;
   - any source whose run status is not `ok` (KEDB: `itil/knowledge/known-errors.md`).
4. Tell the user that their admin password is in `~/.config/publicfunds/admin_credentials` (mode 600). **Never print or read that file into the chat.**
5. Add another reviewer (only when the user names them):
   `cd /workspace/publicfunds && uv run pf reviewer add <username> --display-name "<Name>" --credentials-file ~/.config/publicfunds/<username>_credentials`
   Hand over the file privately.
6. Failures:
   - Exit 2 from the pipeline means a data-quality check failed (runbook RB-01).
   - A source blocked by the publisher is recorded as a known error. Never work around access controls.
   - Never expose the review app beyond 127.0.0.1.
