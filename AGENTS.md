# AGENTS.md — context for AI agents working on Thusa

**What this is:** an evidence-first dashboard of South African public spending. Design: `docs/design/application-design.md`. Research: `sa_public_funds_landscape.md`.

**Stack:** Python 3.13 (uv + lockfile), DuckDB with plain SQL models (ADR-0007; dbt deferred), httpx, pdfplumber, Jinja2 static dashboard + matplotlib PNGs, pytest. Later: FastAPI, HTMX + ECharts, Playwright. Runs on the Grok Bot computer; the public site is a static snapshot.

**Non-negotiables**
1. Every number carries provenance (`source_snapshot_id`, `source_locator`). No source means it isn't shown.
2. Missing = NULL plus a coverage reason. Never render missing as 0.
3. Money = integer cents (ZAR). Store timestamps in UTC; display in SAST (UTC+2).
4. Never publish SA ID numbers. Natural-person data follows design §10.
5. High-severity flags naming a supplier or person need human review before publishing (ADR-0005).
6. Parameterised SQL only. Validate input server-side. No secrets in code, repo, logs or chat.
7. Before adding a dependency, confirm the package exists on PyPI, is the intended one, and is actively maintained. Update the lockfile.

**How to verify your work (show the output, don't claim it):** `uv run pytest -q` · `uv run thusa build && uv run thusa report` (DQ gate: exit 0, `ops.dq_result` all pass) · the screenshots in `dist/` for UI changes. Docs-only changes need a link check.

**Goals:** honest coverage, explainable flags, fast mobile pages. **Non-goals:** verdicts of guilt, leaked data, login-walled features in the MVP.

**Change process:** small PRs; fill in Testing / Risk / How to revert; risk tier per `itil/change-enablement.md`; max 3 review rounds.
