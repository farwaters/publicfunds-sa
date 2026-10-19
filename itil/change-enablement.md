# Change enablement

**Scope:** anything that changes what the public sees or what the service depends on: code, dbt models, detector rules/thresholds, source registry, routines, Bot skills, hosting, secrets, DNS.

## Change types (risk tier set by *the change*, not the author — from @ClaudeDevs, P2)
| Type | Examples | Authority | Evidence required |
|---|---|---|---|
| **Standard** (pre-authorised, low risk) | Docs/copy; adding tests; routine re-run; scheduled data refresh that passes DQ; dependency patch with green CI; new approved digest send | Ops Bot / author after green CI + AI review | PR with template; CI green |
| **Normal — medium** | New parser; UI feature behind a flag; new dbt model; new non-MVP source | Owner (1 human approval) | CR record in PR description; tests; rollback note |
| **Normal — high** | Detector logic/thresholds; publishing pipeline; anything that changes which named entities are flagged; secrets/permissions; hosting/DNS; schema migrations on curated tables; CI workflow files; POPIA-relevant handling | Owner + explicit sign-off (second reviewer when available; else owner after 24 h cooling-off) | Full CR template; eval results for detectors; migration down-script tested |
| **Emergency** | Take down a wrong/defamatory figure; revoke a leaked secret; disable a broken routine | Owner or Ops Bot (take-down only), retro CR within 2 business days | Incident record linked |

## Rules
- An approval covers a specific commit; new commits after approval need re-approval.
- A bot approval never fills a human slot.
- Every PR states Testing, Risk, How to revert (`.github/pull_request_template.md`).
- AI code review + security review run on every PR; every finding fixed or resolved with a reason; max 3 review rounds, then rethink.
- Changes are small. Big changes are split.
- Change log: `registers/change-log.md` (one line per change; PR link).
