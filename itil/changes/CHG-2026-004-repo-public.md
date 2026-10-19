# CHG-2026-004: Repository visibility changed to public

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner. Carried out by the owner on 2026-10-19 at ~11:21 SAST; recorded retrospectively at 11:25 SAST |
| Type | **Normal-high** (a visibility/permissions change). Implemented and approved by the owner; this is a retrospective record |
| CIs affected | CI-001 (repository), CI-102 (template: importers no longer need GitHub access) |
| Linked records | D-02 (resolved), D-15, ADR-0009, RSK-020, **RSK-021**, **CSI-020**, CHG-2026-001, CHG-2026-005 |

## What and why
https://github.com/farwaters/publicfunds-sa went from private to **public**. Anyone who imports the PublicFunds Bot
template can then clone the code anonymously with `scripts/bootstrap.sh`. No access grants and no mirror are needed.

## Pre-change control
The owner scanned the **full git history** for secrets before the change, and the result was **clean** (owner's
report). The scan tool and its output are not stored in the repo **[not independently re-verified by the bot]**.

By design, the repo never contains:
- `data/` (raw files, warehouse, review DB);
- `dist/`;
- credentials and tokens (`~/.config/publicfunds/`);
- the HMAC key (`~/.config/thusa/`).

These are git-ignored and live outside the repo.

## Verification (bot, 19 Oct 2026)
- Anonymous access works:
  `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_TERMINAL_PROMPT=0 git ls-remote https://github.com/farwaters/publicfunds-sa`
  listed the branches without credentials (`feat/review-app` = `4018999`).
- `scripts/bootstrap.sh` cloned the public URL anonymously into `/tmp/pf-bootstrap-test` (see CHG-2026-005).

## Risk
RSK-021: a future mistaken commit is published at once. Mitigations are in the register; the automated scan is
CSI-020.

## How to revert
GitHub, Settings, Danger zone, Change visibility, Private. Revert is instant, but forks and clones made while the
repo was public persist. If a secret is ever found in history, **rotate the secret first**, then rewrite history.
