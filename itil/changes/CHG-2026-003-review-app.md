# CHG-2026-003: Review app (human review of flags, four-eyes, audit trail) and confirmed-only publication (v0.2.0)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner ("create the grok bot app that people can use to review data"), 2026-10-19 10:51 |
| Type | **Normal-high**: it changes the publication pipeline (what may be published about named parties) and adds authentication and secrets. Two approvals needed (E11) |
| CIs affected | CI-090, CI-091, CI-094, CI-095, CI-060, CI-070, CI-008 (gov_body province fix); new CI-096..101 |
| Linked records | ADR-0005 (amended), **ADR-0008**, **ADR-0009**; RSK-001 (updated), **RSK-017, RSK-018, RSK-019**; **KE-011**; **CSI-016..019**; RB-04 (updated), **RB-08, RB-09, RB-10**; REL-0.2.0 checklist |
| PR | branch `feat/review-app`, stacked on `feat/mvp-pipeline` (PR base = `feat/mvp-pipeline`; retarget to `main` after PR #1 merges). Not merged |

## Amendment (19 Oct 2026, 11:21 SAST): Grok Bot template distribution
The owner clarified that Thusa is a **Grok Bot app**, distributed through the **PublicFunds Bot** template link
(`<TEMPLATE_LINK>`), not a hosted website. Recorded as **ADR-0009**:
- **The bot chat is the primary UI.** The localhost review web app is a secondary tool that the bot opens in its own
  box browser.
- Public web hosting is dropped from the MVP; **D-03 and D-14 are superseded** in the decision log.
- Docs updated: README, docs/design, `docs/bot/template.md` (new), `docs/bot/review-skill.md`, RB-08.
- Registers updated: CI-009 retired, CI-102 added, RSK-018 updated, RSK-020 added; release checklist updated.
- No code behaviour changed: the app was already localhost-only.

## What and why
v0.1.0 produces 335 flags, but there was no way to review them. ADR-0005 blocks publishing named flags until a human
has reviewed them. This change adds:
- **Review web app** (`pf serve`, FastAPI + Jinja + HTMX, mobile-friendly):
  - flag queue (filter by detector, severity, status, naming, text);
  - flag detail with explanation, evidence links, raw-file lineage, matched records and match confidence;
  - decisions: confirm, reject, needs more info or escalate, with a mandatory reason;
  - decision history; audit trail page;
  - CSV/JSON export of reviewed flags;
  - coverage heatmap (filter by data type, province, municipality, year);
  - entity drill-down with lineage links.
- **Four-eyes rule:** named-supplier flags need two different reviewers confirming on the same evidence (ADR-0008).
- **Append-only, hash-chained review store** (`data/review/review.sqlite`). It is keyed on the deterministic flag id
  plus the evidence hash, so it survives rebuilds.
- **Identity:**
  - Admin-created reviewers (`pf reviewer add`) with scrypt-hashed passwords.
  - Per-reviewer bearer tokens (stored hashed) for the JSON API and CLI.
  - Sessions with CSRF, login rate limiting, and a localhost bind by default.
- **`pf` CLI** with JSON output, so the Grok Bot can drive reviews: `review list|show|decide|history|verify|export`.
  Skill draft: `docs/bot/review-skill.md`.
- **Public snapshot** `dist/public/`: only confirmed, non-stale flags. Others are excluded by default
  (`config/publication.yaml`). Named flags are never shown unconfirmed, and reviewer names and notes are never
  published. The local `dist/site` dashboard is now labelled INTERNAL.
- **Data fix KE-011:** province codes normalised (`KZ` → `KZN`, `LIM` → `LP`), so the province filter works, plus a
  DQ check. Flag counts and the coverage headline are unchanged (335 flags; 75.7%).

## Security controls (E3/E4/E5)
- Parameterised SQL everywhere. The only f-string SQL fragments are fixed `WHERE` choices and allow-listed column names.
- Server-side validation:
  - flag id `^[0-9a-f]{16}$`, sha `^[0-9a-f]{64}$`, gov_body id pattern;
  - enumerated filters; reason 10–2000 and notes ≤ 4000 characters; control characters rejected;
  - request body ≤ 64 KB.
- CSRF:
  - a synchroniser token on every POST form;
  - a double-submit cookie on login;
  - SameSite=Strict HttpOnly cookies (`__Host-` and Secure behind TLS).
- Security headers:
  - CSP `default-src 'none'; script-src 'self'; style-src 'self'` (no inline script or style; htmx eval disabled);
  - XFO DENY, nosniff, Referrer-Policy no-referrer, Permissions-Policy, COOP/CORP;
  - `Cache-Control: no-store`; HSTS when secure.
- TrustedHost allow-list (default `127.0.0.1,localhost`). No CORS. OpenAPI/docs disabled.
- Passwords: scrypt N=2^15, r=8, p=1. Tokens/sessions are 256-bit random, stored as SHA-256 only.
  Unknown users still incur a hash computation (timing).
- Login rate limit: 5 failures per user or 20 per IP in 15 minutes → 429 with Retry-After.
- Exports neutralise CSV formula injection. Evidence URLs are rendered only for `http(s)`.
- Secrets:
  - Never printed. The admin password was written only to `/home/box/.config/publicfunds/admin_credentials` (0600).
  - The review DB is 0600 inside a 0700 directory. Nothing secret is in the repo.
- Dependencies were checked on PyPI (official projects and current releases) and locked in `uv.lock`.
  htmx 2.0.11 is vendored with its sha256 recorded in CI-091.

## Testing
- `uv run pytest -q` → **156 passed**: the 99 existing tests plus 57 new ones.
  - `test_review_workflow.py`: four-eyes, rounds, evidence changes, escalation, validation.
  - `test_review_store.py`: append-only triggers, hash-chain tamper detection, SAST timestamps, survival across
    rebuilds, kept orphan decisions, province regression.
  - `test_review_app.py`:
    - auth, CSRF, rate limiting, disabled users, logout, open redirect;
    - headers, untrusted host, queue/HTMX partials, evidence page, four-eyes over the web, XSS escaping;
    - audit page and exports; coverage, entity and lineage pages; body limit;
    - API token auth and four-eyes.
  - `test_review_cli.py`: 0600 credential and token files, no secrets on stdout, the bot flow with exit codes
    0/3/4, a world-readable token refused, a revoked token, a refused public bind.
  - `test_publish.py`: nothing published before review; named flags only after two confirmations;
    label mode never shows named flags; stale confirmations not published.
- Real data:
  - `thusa build` → DQ 49 pass, 0 fail, 1 warn; `thusa report` → public snapshot 0 confirmed.
  - The app runs on 127.0.0.1:8765; `/healthz` is ok.
  - Playwright screenshots are in `dist/`. An HTMX filter was checked in Chrome under the CSP.

## Risk and impact
- Main risks: RSK-017 (reviewer misuse), RSK-018 (exposure of unreviewed allegations), RSK-019 (stale
  confirmation). See the risk register.
- Residual: anyone with shell access to the box can alter the review DB. The hash chain detects this but does not
  prevent it; anchor the head hash in release records.
- Until a second reviewer is onboarded (CSI-016), named-supplier flags can reach at most `awaiting second review`.
  That is intentional.
- No change to detector thresholds. Flag IDs and counts are unchanged.

## How to revert
- `scripts/review-app.sh stop`, then revert the PR. The pipeline (`thusa run`) keeps working.
- `thusa report` would then no longer build `dist/public/`; the public snapshot falls back to "not built".
- Keep `data/review/review.sqlite`: the decisions are records and must not be deleted.

## Post-implementation
- Onboard a second reviewer (CSI-016).
- Create and verify the PublicFunds Bot template link (D-15); remote access (D-14) is superseded by ADR-0009.
- Include `data/review/` in backups (D-05).
- After the first reviewed release, re-score RSK-001 and start the D3/D4 eval set (CSI-014) from real decisions.
