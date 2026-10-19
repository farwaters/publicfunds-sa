---
name: publicfunds-itil
description: Keep PublicFunds (Thusa) ITIL records current - change records, incidents and known errors for failing sources, and the CI, risk and change registers - following the repo's change-enablement rules.
---
# PublicFunds ITIL records

All records live in `/workspace/publicfunds/itil/`. Copy the templates in `itil/templates/`. Use dates and times in SAST.

| Event | Record |
|---|---|
| A source fails or is blocked | Incident `itil/incidents/INC-YYYY-NNN.md` and a row in `registers/incident-log.md`. If it recurs or has a workaround, add or update a `knowledge/known-errors.md` KE |
| Code, config, detector, skill, routine or distribution change | Change `itil/changes/CHG-YYYY-NNN-<slug>.md` and a row in `registers/change-log.md` |
| A new or changed component | `registers/ci-register.md` (never record secret values, only where they are stored) |
| A new risk, or a change to an existing one | `registers/risk-register.md` (score = likelihood × impact; ≥ 15 is High) |
| An improvement idea | `registers/csi-register.md` |

Risk tier is set by the change, not by who made it (`itil/change-enablement.md`):
- **Standard:** docs, tests, a routine refresh that passes the data-quality gate.
- **Normal:** most code changes; 1 approval.
- **Normal-high:** detector thresholds, the publishing pipeline, `config/publication.yaml`, secrets/auth, distribution; 2 approvals.

Every change record states Testing, Risk and How to revert.

Rules:
- Number records sequentially: check the highest existing ID first.
- Never invent figures. Quote command output or files, and mark anything unverified **[unverified]**.
- Committing is fine. Pushing, opening PRs, merging and publishing need the user's explicit approval.
