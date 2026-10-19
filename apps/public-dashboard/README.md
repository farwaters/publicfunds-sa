# PublicFunds SA public dashboard

This is the public, no-login website. It is published with **Grok Build** at a grok.me address
(see [ADR-0010](../../docs/adr/0010-grok-build-public-dashboard.md) and CHG-2026-006).

- `index.html` is one self-contained static page (plain JavaScript, no build step and no dependencies).
  - It reads the public data export `public-data/v1/` (`pf publish-data`).
  - By default the data comes from `https://raw.githubusercontent.com/farwaters/publicfunds-sa/main/public-data/v1/`.
    These URLs only work for files that are merged to `main`.
  - To use another data location, add `?data=<base url>` or set `window.PUBLICFUNDS_DATA_BASE`.
- `GROK_BUILD_PROMPT.md` is the prompt you paste into grok.com Build mode to publish the app.
  It also explains how to point a custom domain at it.

## Run locally
```bash
python3 -m http.server 8000      # run from the repo root
# open http://127.0.0.1:8000/apps/public-dashboard/index.html?data=http://127.0.0.1:8000/public-data/v1/
```

## Check it (headless Chrome, desktop + mobile)
```bash
uv run --group screenshots python scripts/dashboard_check.py   # screenshots in dist/public-dashboard/
```
The check:
- serves only `apps/public-dashboard/` and `public-data/`;
- runs axe-core (WCAG 2.1 A/AA) on every page when `axe-core` is installed (`AXE_JS=/path/axe.min.js`, or `npm i axe-core`); serious or critical violations fail;
- opens every page;
- fails on any console error, page error or failed request;
- exercises the fuel checker, the inflation adjuster, a CSV download and the mobile menu.

## Rules the app keeps
- Money is stored in cents and shown in rand.
- A blank (null) value is shown as "unknown", never as 0.
- Every figure links to its source.
- Only flags confirmed by review are shown, so there are no unreviewed leads; the app shows only how many are hidden.
- Tender awards are labelled as public records, not findings.
- Supplier names that match restricted natural persons stay withheld.
- Data is rendered as text only (no `innerHTML`), links are restricted to http(s), and there are no trackers or cookies.
