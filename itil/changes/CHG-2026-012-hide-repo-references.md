# CHG-2026-012: Serve the site from publicfunds.grokforum.site and stop disclosing the repository in served/shared files

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-23 10:33 |
| Type | **Normal**. Text, URL and config changes only; the repository stays public. Owner approves the merge |
| CIs affected | `apps/public-dashboard/index.html`, root `index.html`, new root `CNAME`, `config/public-data.yaml` (`base_url`, `site_url`), `thusa/publish_data.py` (docstring), `thusa/http.py` (User-Agent), `public-data/v1/manifest.json` + `feed.json`, README files, `GROK_BUILD_PROMPT.md`, `docs/bot/template.md`, `docs/bot/skills/publicfunds-setup/SKILL.md`, `scripts/bootstrap.sh` (usage comment only), `.github/ISSUE_TEMPLATE/*` (links only), one test |
| Linked records | CHG-2026-004 (repo public), CHG-2026-007 (Pages), CHG-2026-008 (report link, now removed) |
| PR | branch `chore/undisclose-repo` (unmerged) |

## What
1. Dashboard: canonical/og/twitter URLs use `https://publicfunds.grokforum.site/`; the footer repo link is replaced
   by a same-origin link to the open data; the data base is same-origin only (`../../public-data/v1/`), the
   raw.githubusercontent fallback is removed.
2. "Report an error" (GitHub issue form) link removed; the footer now gives the National Anti-Corruption Hotline
   (0800 701 701). A replacement channel is an owner decision.
3. Exporter config `base_url`/`site_url` point at the custom domain, so the nightly `pf publish-data` writes the new
   URLs into `manifest.json` and `feed.json`. The committed copies were updated to match (feed sha/bytes in the manifest).
4. `CNAME` file (`publicfunds.grokforum.site`) added so the Pages custom domain is set from `main` on merge.
5. Template, setup skill, README: the bootstrap is fetched from `https://publicfunds.grokforum.site/scripts/bootstrap.sh`.
   `bootstrap.sh` still clones `PF_REPO_URL` (default: the GitHub repo); see the PR report for options.

## Not changed
- Behaviour of `scripts/publish-public-data.sh` and of `bootstrap.sh`.
- Historical records (ADRs, ITIL records, design and roadmap docs) still name the repository; they are served by
  Pages because it publishes the whole `main` root (`.nojekyll`). Owner decision.

## Verification
- `pytest`: 142 passed, 59 skipped. `scripts/dashboard_check.py`: no problems.
- Local server + headless Chrome network log: 8 requests, all to 127.0.0.1; none to GitHub domains.

## Back-out
Revert the merge commit; delete `CNAME` (or clear the Pages custom domain).
