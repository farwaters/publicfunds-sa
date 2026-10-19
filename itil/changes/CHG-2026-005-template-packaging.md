# CHG-2026-005: PublicFunds Bot template packaging (skills, description, memory facts, bootstrap)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-19 11:25 |
| Type | **Normal-high**: a distribution change; the bootstrap creates an admin account and secrets on each importer's box. Two approvals needed (E11) |
| CIs affected | CI-070 (skills), CI-102 (template), new **CI-103** (bootstrap script), CI-060 (credential paths) |
| Linked records | ADR-0009, D-12 (**Parked**), D-15, CHG-2026-004, RSK-020, RSK-021, CSI-016 (Parked), **CSI-021**, RB-08 |
| PR | branch `feat/review-app`, [PR #2](https://github.com/farwaters/publicfunds-sa/pull/2) (unmerged) |

## What and why
This change makes the template importable and self-installing:
- **`scripts/bootstrap.sh`:** one idempotent command that installs on a fresh bot box from the public URL.
  1. Clone the repo, or fast-forward pull it (it refuses a dirty tree).
  2. Install uv 0.13.1 if it's missing, then the locked dependencies (`uv sync --frozen`).
  3. Run `thusa run`.
  4. Run `pytest`.
  5. Create a local admin reviewer: password in `$PF_CONFIG_DIR/admin_credentials` (mode 600, directory 700), and a
     chat token in `review_token`.
  6. Start the review app on `127.0.0.1:$PF_PORT`.

  Re-running it keeps the existing reviewer and credentials.
- **Skills** in `docs/bot/skills/<slug>/SKILL.md`: `getting-started`, `publicfunds-setup`, `publicfunds-refresh`,
  `publicfunds-review`, `publicfunds-itil`.
  - Each has `name` and `description` frontmatter.
  - They are generic, with no personal names.
  - They are kept short for the template size cap.
- **Template description and memory facts** in `docs/bot/template.md`.
- **Decision log:** D-12 (second reviewer) **Parked** by the owner. The skills ask about a second reviewer only once,
  during getting-started.

## Testing
**Real bootstrap from the public repo** (19 Oct 2026, SAST). The run was isolated from the live app (port 8765) and
the real credentials:
- clone: `PF_DIR=/tmp/pf-bootstrap-test`, `PF_BRANCH=feat/review-app`;
- port: `PF_PORT=8799`;
- config dir: `PF_CONFIG_DIR=/tmp/pf-bootstrap-test-config`;
- HMAC key: `THUSA_HMAC_KEY_FILE` inside that config dir;
- git: anonymous (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_TERMINAL_PROMPT=0`).

| Step | Result |
|---|---|
| Clone public URL anonymously | ok, 11:26:45 to 11:26:50; code at `4018999` |
| uv 0.13.1 + `uv sync --frozen` | ok (uv already on the box, so the installer path was not exercised; installer URL checked: 301 then 200) |
| `thusa run` | ok (exit 0), 11:26:50 to 11:29:09; `complete_pct` 75.7 |
| `pytest` | 156 passed |
| Admin reviewer | created; credentials file and token mode 600, config dir 700 |
| Review app | started on 127.0.0.1:8799; `/healthz` returned `status ok`, `audit_chain_ok true`, 0 decisions |
| Second run (idempotency, pipeline and tests skipped) | fast-forward pull ok; "reviewer admin already exists; leaving its password unchanged"; "already running"; exit 0 |
| Isolation | 8765 stayed healthy throughout (same build id); real credentials file unchanged (mtime 11:06:29) |
| Clean-up | test app stopped, port closed, both /tmp directories removed |

Caveat: the clone was the pushed `4018999`, which predates this commit. The script under test was the working copy
(`/workspace/publicfunds/scripts/bootstrap.sh`) run against that clone.

`uv run pytest -q` in the main checkout: 162 passed (includes the new `tests/test_bot_skills.py`).

## Risk
- An importer's bootstrap fails because a source is blocked. The script stops and reports it, and the skills record a
  known error.
- Template contents leak state (RSK-020).
- Skills drift from the CLI (the review skill is tested against `pf --help` output by hand).

## How to revert
Revert the commit(s) on `feat/review-app`. Remove the skills from the bot and update the template link. Boxes that
have already installed keep their own data.
