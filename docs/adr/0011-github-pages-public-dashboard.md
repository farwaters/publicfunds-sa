# ADR-0011: Host the public dashboard on GitHub Pages (Grok Build deferred)
- Status: Accepted (owner, 19 Oct 2026 20:30 SAST: "Yes, publish the dashboard on GitHub Pages")
- Date: 2026-10-19
- Amends: ADR-0010 decision 3. The static SPA and the `public-data/v1` export are unchanged; only the host changes.
  Grok Build publishing is **deferred by the owner**. `GROK_BUILD_PROMPT.md` stays in the repo for later use.
- Related: CHG-2026-007, CI-105, D-16

## Context
The owner chose not to use Grok Build for now and wants the dashboard live straight away. The repository is public,
and the app is one static file reading static JSON.

## Decision
1. **Deploy:** GitHub Pages serves branch `main`, folder `/` (classic branch build, `.nojekyll`). A GitHub Actions
   workflow was preferred, but the push token lacks the `workflow` scope (push rejected 19 Oct 2026 ~20:40 SAST), so the
   branch build is used. It redeploys on every push to `main`, including the daily `public-data/` push.
2. **Site layout:** the site is the public repository itself. A root `index.html` redirects to `apps/public-dashboard/`.
   `data/`, the review DB and secrets are not in git, so they are not on the site.
3. **Data source:** the app loads its data from the same site (`../../public-data/v1/`) and falls back to the raw GitHub
   URL. `?data=` overrides both.
4. **Address:** https://farwaters.github.io/publicfunds-sa/

## Consequences
- **Data deploys:**
  - The daily `publish-public-data.sh --push` now also triggers a Pages deploy. It takes about a minute, and the
    site and data deploy together.
  - Loading data from the same site avoids CORS and the raw-URL cache.
- **Limits:**
  - GitHub Pages has soft limits of a 1 GB site and 100 GB/month bandwidth.
  - The public export is about 4.3 MB.
- **Custom domain:** can be added later in the repo Pages settings with a CNAME (D-17).
- **Single point of failure:** GitHub is now the single host for code, data and site.
