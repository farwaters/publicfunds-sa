# Thusa — South African public spending, with receipts

Prototype design for the most comprehensive, honest taxpayer dashboard of SA government spending. It ingests public sources, shows **what it doesn't know**, flags exceptions with evidence, and puts benchmarks ("utilities on the glass") next to every number. It is built as a **Grok Bot-hosted app** (ADR-0001).

## Get the app
Thusa is a **Grok Bot app**. To use it, **import the PublicFunds Bot template via its Grok Bot link: `https://x.ai/bot/7Hr1hnJPXqOQbMmUZ7mTi`**
(a `grokbot://` bot-template share link). This is the power-user and reviewer version; the public website is below (ADR-0010).
- **The bot chat is the primary UI:** ask about coverage, municipalities and flags, and review flags in the chat.
- **The local review web app** (127.0.0.1:8765) is a secondary tool that the bot opens in its own box browser for you.
- On first run, the bot clones this repo, builds the data and creates your reviewer account. See
  `docs/bot/template.md`.

## Public dashboard (v0.3.0, CHG-2026-006)
Everybody else uses the **public website**: a no-login dashboard at **https://publicfunds.grokforum.site/** (static hosting, ADR-0011; Grok Build deferred). It reads the open data export in [`public-data/v1/`](public-data/v1/) (`manifest.json` first; money in cents, `null` = unknown, every figure with its source), which `pf publish-data` builds after each successful refresh. Only review-confirmed flags are published. Code: [`apps/public-dashboard/`](apps/public-dashboard/); served from `main` (redeploys on every push) (ADR-0010, ADR-0011; [`GROK_BUILD_PROMPT.md`](apps/public-dashboard/GROK_BUILD_PROMPT.md) kept for a later Grok Build copy). The bot template above stays the power-user and reviewer version. What changed in the data: `#/changes` and the JSON Feed `public-data/v1/feed.json`; known gaps per province: `#/unknowns`; to report suspected corruption, use the National Anti-Corruption Hotline (0800 701 701). Roadmap: [`docs/roadmap/improvements-2026-10.md`](docs/roadmap/improvements-2026-10.md).

## Contents
| Path | What |
|---|---|
| `sa_public_funds_landscape.md` (+ `.pdf`, `.docx`) | Landscape of ~48 SA tools, coverage matrix, gap analysis, source inventory, exception ideas (19 Oct 2026) |
| `docs/design/application-design.md` (+ `.pdf`) | **Application design**: vision, personas, requirements, architecture, data model, detectors, coverage model, API, UI, security/POPIA/PAIA, roadmap, testing, engineering practices, observability, ITIL summary, open decisions |
| `docs/adr/` | Decision log (ADR-0001…0011 + template) |
| `docs/research/discoveringai-reposts.md` | The @DiscoveringAI reposts on going beyond vibe coding, and the practices adopted |
| `itil/` | ITIL 4 practice map, service definition, SLA/SLO, change enablement, templates (change, incident, problem, release), registers (risk, CI, CSI, change, incident), knowledge (runbooks, KEDB) |
| `config/sources.yaml`, `config/detectors.yaml` | Machine-readable CIs: data sources and red-flag detectors |
| `sql/core_schema.sql` | Target logical schema (the implemented MVP schema is in `thusa/models/` + `thusa/staging.py`) |
| `thusa/` | **MVP pipeline (v0.1.0)**: connectors, parsers, staging, SQL models (curated, marts/coverage), detectors, DQ suite, report, CLI. **`thusa/review/`** (v0.2.0): review web app, review store, `pf` CLI. `thusa/publish.py`: public snapshot of confirmed flags |
| `docs/bot/template.md`, `docs/bot/review-skill.md` | PublicFunds Bot template (contents, instructions, first run) and the `thusa-review` skill (driving reviews from chat with `pf review …`) |
| `scripts/`, `deploy/` | `review-app.sh` (start/stop), `review_screenshots.py`, systemd user unit |
| `tests/` | pytest: unit, connectors with mock HTTP, end-to-end smoke on synthetic data, DQ suite on the real warehouse |
| `apps/public-dashboard/`, `public-data/v1/` | Public dashboard (single-file SPA + Grok Build prompt) and the public JSON data export it reads (v0.3.0) |
| `docs/releases/v0.1.0.md` … `v0.4.0.md` | Release notes (drafts) |
| `docs/roadmap/` | Prioritised improvement backlog (scored; mirrored in the CSI register) |
| `AGENTS.md`, `REVIEW.md`, `.github/` | AI-agent context, review rules, PR template, CODEOWNERS |

## Running the MVP pipeline
```bash
uv sync                                   # Python 3.13; pinned deps in uv.lock
uv run thusa run --as-of 2026-10-19       # ingest all sources -> build warehouse -> DQ gate -> dashboard
uv run thusa run --refresh                # refetch even if today's raw copies exist
uv run thusa ingest --only muni_api       # one source
uv run thusa build && uv run thusa report # rebuild from raw files only (offline)
uv run pytest -q                          # 162 tests
```
Outputs (git-ignored):
- `data/raw/<source>/<date>/…` (+ `.sha256`, `manifest.jsonl`, `runs.jsonl`)
- `data/thusa.duckdb`
- `dist/site/index.html` (dashboard), `dist/*.png` (charts and screenshots), `dist/summary.json`

Exit code 2 means a data-quality check failed and the build is not releasable.

**PPD manual drop:** put Power BI CSV exports in `data/drop/ppd/` (runbook RB-06).

**SA ID hashing key:** `THUSA_HMAC_KEY` (hex) or `~/.config/thusa/hmac.key`, created on first run with mode 0600. Never commit it.

## One-command install on a fresh bot box
```bash
curl -fsSL https://publicfunds.grokforum.site/scripts/bootstrap.sh | bash
# or, in a checkout: scripts/bootstrap.sh   (idempotent; env PF_BRANCH, PF_DIR, PF_PORT, PF_CONFIG_DIR, PF_ADMIN_USER)
```
It clones or pulls into `/workspace/publicfunds`, installs uv and the locked dependencies, runs the pipeline and tests, creates
a local admin reviewer (password in `~/.config/publicfunds/admin_credentials`, mode 600) and starts the review app on
localhost. Bot skills for the template are in `docs/bot/skills/` (see `docs/bot/template.md`).

## Review app (v0.2.0)
```bash
scripts/review-app.sh start               # http://127.0.0.1:8765 (localhost only); status | stop | restart
uv run pf reviewer add alice --display-name "Alice" --credentials-file ~/.config/publicfunds/alice_credentials
uv run pf reviewer token alice --out ~/.config/publicfunds/review_token   # API/CLI token (0600 file)
uv run pf review list --status open       # JSON; also: show, decide, history, verify, export
uv run pf publish                         # rebuild dist/public/ (confirmed flags only)
```
- Flags that name a supplier need **two different reviewers** to confirm on the same evidence (ADR-0008).
- Decisions are append-only and hash-chained in `data/review/review.sqlite`, and survive pipeline rebuilds.
- Passwords and tokens are never printed; they are written to 0600 files.
- The app is a local helper: it binds to localhost only, and the bot opens it in its own browser (ADR-0009).
- Start/stop, accounts and backup: runbooks RB-08, RB-09 and RB-10.
- Screenshots: `uv run --group screenshots python scripts/review_screenshots.py`.

## Not in git (by design)
- `src/` — raw research downloads from 19 Oct 2026 (~16 MB): eTenders OCDS full mirror `full.jsonl.gz` (11.7 MB, from https://data.open-contracting.org/en/publication/143/download?name=full.jsonl.gz), PPD user guide PDF, PFMA SCM Instruction 10 PDF + page renders. Re-download from the URLs in the landscape report.
- `data/` (incl. the review DB `data/review/`), `dist/`, `*.duckdb`: generated or raw data, backed up separately (D-05). Rebuild with `uv run thusa run`.

## Status
- MVP pipeline v0.1.0: branch `feat/mvp-pipeline` (CHG-2026-002, PR #1).
- Review app v0.2.0: branch `feat/review-app` (CHG-2026-003), stacked on it.
- Distributed as the PublicFunds Bot template (https://x.ai/bot/7Hr1hnJPXqOQbMmUZ7mTi). Public dashboard live at https://publicfunds.grokforum.site/ (CHG-2026-006, CHG-2026-007).
- Published flags: none confirmed yet (0 in `public-data/v1/flags.json`).
- All flags are unreviewed automated indicators.
- Supplier-naming flags are `pending human review`.

