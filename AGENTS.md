# AGENTS.md — context for AI agents working on Thusa

**What this is:** an evidence-first dashboard of South African public spending. Design: `docs/design/application-design.md`. Research: `sa_public_funds_landscape.md`.

**Stack:** Python 3.13 (uv + lockfile), DuckDB with plain SQL models (ADR-0007; dbt deferred), httpx, pdfplumber, Jinja2 static dashboard + matplotlib PNGs, pytest. Review app (ADR-0008): FastAPI + Jinja + vendored HTMX, SQLite review store, `pf` CLI; Playwright (group `screenshots`) for UI evidence. Later: ECharts. Runs on the Grok Bot computer and is distributed as the **PublicFunds Bot** Grok Bot template (`https://x.ai/bot/7Hr1hnJPXqOQbMmUZ7mTi`, ADR-0009). **The bot chat is the primary UI**; the localhost review app is a secondary tool the bot opens in its own browser. There is no public web hosting in the MVP; `dist/public/` is a confirmed-only file artefact. Templates must never carry `data/`, credentials or keys.

**Non-negotiables**
1. Every number carries provenance (`source_snapshot_id`, `source_locator`). No source means it isn't shown.
2. Missing = NULL plus a coverage reason. Never render missing as 0.
3. Money = integer cents (ZAR). Store timestamps in UTC; display in SAST (UTC+2).
4. Never publish SA ID numbers. Natural-person data follows design §10.
5. High-severity flags naming a supplier or person need human review before publishing (ADR-0005). Named flags need **two different reviewers** (four-eyes, ADR-0008). Only `confirmed` flags with unchanged evidence reach `dist/public/`. Never edit `data/review/review.sqlite` by hand: it is an append-only audit trail. Agents never record review decisions on their own judgement; they record only what a named human reviewer explicitly decided (`docs/bot/review-skill.md`).
6. Parameterised SQL only. Validate input server-side. No secrets in code, repo, logs or chat.
7. Before adding a dependency, confirm the package exists on PyPI, is the intended one, and is actively maintained. Update the lockfile.

**How to verify your work (show the output, don't claim it):** `uv run pytest -q` · `uv run thusa build && uv run thusa report` (DQ gate: exit 0, `ops.dq_result` all pass) · the screenshots in `dist/` for UI changes (`uv run --group screenshots python scripts/review_screenshots.py` for the review app). Docs-only changes need a link check.

**Goals:** honest coverage, explainable flags, fast mobile pages. **Non-goals:** verdicts of guilt, leaked data, login-walled features in the MVP.

**Change process:** small PRs; fill in Testing / Risk / How to revert; risk tier per `itil/change-enablement.md`; max 3 review rounds.
