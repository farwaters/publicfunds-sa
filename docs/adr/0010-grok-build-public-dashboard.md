# ADR-0010: Public dashboard as a Grok Build app, reading a public JSON export from the repo
- Status: Accepted (PR #3 merged 19 Oct 2026 20:29 SAST); **host amended by ADR-0011**: GitHub Pages, Grok Build deferred
- Date: 2026-10-19
- Supersedes (in part): ADR-0009, only the parts "no public web hosting in the MVP" and "the bot chat is the only
  public UI". Also reopens D-03 (public hosting), now resolved as Grok Build.
- Keeps: ADR-0009 template distribution. The **PublicFunds Bot** template (https://x.ai/bot/7Hr1hnJPXqOQbMmUZ7mTi)
  stays as the power-user and reviewer version: chat, review app and pipeline.
- Related: ADR-0003 (static public snapshot), ADR-0004 (provenance, null semantics), ADR-0005/0008 (human review,
  four-eyes), CHG-2026-006

## Context
- Grok Bot has no GUI app primitive, and `x.ai/bot/…` template links need the Grok Bot app. So the general public
  can't use a bot template.
- The owner wants a user-friendly GUI with its own URL that needs no Grok Bot.
- Grok Build (grok.com, Build mode) can publish a web app to a public URL (grok.me). It also supports connectors,
  custom domains and export to GitHub.

## Decision
1. **The data engine stays on the bot box.** The `thusa` pipeline, warehouse, data-quality gate and review app are
   unchanged.
2. **`pf publish-data`** writes a versioned, compact, public-safe JSON export to `public-data/v1/`.
   - Schema `publicfunds.public-data/v1`, total under 5 MB, under 2 MB per file.
   - Money in cents; null means unknown; every figure carries a source.
   - Only confirmed flags, plus hidden-lead counts.
   - It refuses on a failed quality gate or a failed safety scan.
   - The export is committed to git and served from `raw.githubusercontent.com/farwaters/publicfunds-sa/main/public-data/v1/`.
3. **The public GUI is a static single-page app** (`apps/public-dashboard/index.html`).
   - The owner publishes it with Grok Build at a grok.me address, using `GROK_BUILD_PROMPT.md`.
   - It has no backend, no login, no cookies and no trackers. It fetches the export live.
4. **Refresh:**
   - After a successful daily refresh, the routine runs `scripts/publish-public-data.sh --push`. The script commits
     and pushes **only** `public-data/` to `main`.
   - That push is pre-authorised only through a routine the owner approves. Code changes still go through PRs.

## Consequences
- **Good:**
  - Anyone can use the site without an account.
  - Hosting is free and handled by Grok Build / GitHub.
  - The data is reusable (open JSON with checksums).
  - The public surface holds no secrets and no review data, so the attack surface is small.
- **Costs and risks:**
  - The site depends on GitHub raw hosting. Raw URLs only serve merged files and are cached for about 5 minutes.
  - The routine pushes data commits straight to `main`. This is mitigated: the script limits the commit to the path
    and allows only a fast-forward on `main`, and the export has its own quality and safety gates.
  - Public misreading of numbers (RSK-022), defamation through the public site (RSK-023) and stale data (RSK-024)
    are now live risks.
  - The Grok Build copy can drift from the repo code. Mitigation: re-export to GitHub as a PR, and treat
    `index.html` in the repo as the reference.
- **Rejected options:**
  - Hosting on the bot box (no public ingress, single point of failure).
  - Vercel or other hosts (the owner chose Grok Build).
  - Serving the warehouse through an API (it adds a backend and the export does the job).
