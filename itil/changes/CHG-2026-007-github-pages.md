# CHG-2026-007: Publish the public dashboard on GitHub Pages

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-19 20:30 ("Yes, publish the dashboard on GitHub Pages") |
| Type | **Normal-high**: the first live public website. Owner approval given. Second reviewer parked (D-12) |
| CIs affected | CI-105 (public dashboard app: host is now GitHub Pages), new CI-111 (GitHub Pages site config), CI-104 (export also served same-origin) |
| Linked records | ADR-0011 (amends ADR-0010), CHG-2026-006, D-16 (resolved: GitHub Pages URL), D-17, RSK-022 to RSK-024, SLO-PD-1 |

## What
- Pages is enabled from branch `main`, folder `/` (`.nojekyll`; root `index.html` redirects to `apps/public-dashboard/`).
  It redeploys on every push to `main`.
- A workflow-based deploy was preferred, but the push was rejected because the token lacks the `workflow` scope.
  Pages was first created with `build_type=workflow`, then switched to the branch build.
- The app now loads `./public-data/v1/` from its own site first, and falls back to the raw GitHub URL.
- README and `docs/bot/template.md` give the public URL: https://farwaters.github.io/publicfunds-sa/

## Testing
- **Before the push:** the local dashboard check against the export.
- **After deployment:** headless Chrome loads the live site on desktop and mobile, with live data and no console
  errors. Screenshots: `dist/public-dashboard/pages-home-{desktop,mobile}.png`.

## Back-out
Pick one:
- disable Pages: `gh api -X DELETE repos/farwaters/publicfunds-sa/pages`;
- or revert the commit that adds the root `index.html`.

## Approval
| Role | Name | Date (SAST) | Decision |
|---|---|---|---|
| Owner | | 2026-10-19 20:30 | Approved (chat) |
