# CHG-YYYY-NNN — <short title>

| Field | Value |
|---|---|
| Requested by / date (SAST) | |
| Type | Standard / Normal-medium / Normal-high / Emergency |
| CIs affected | e.g. CI-010 (detector D1), CI-002 (etenders_ocds source) |
| Linked records | INC-…, PRB-…, CSI-…, ADR-… |
| PR / commit | |

## What and why
<!-- One paragraph. What user/value outcome does this change deliver? -->

## Risk assessment
- What could go wrong (data correctness, publication of a named entity, availability, privacy, cost)?
- Blast radius (pages/entities/sources affected):
- Does it change which suppliers or people are flagged publicly? Yes/No (If yes, type is Normal-high.)
- POPIA / licence impact:

## Testing (evidence, not claims)
- [ ] Unit / data tests: <command + result summary>
- [ ] Detector eval (if applicable): precision/recall before → after
- [ ] Reconciliation checks:
- [ ] Preview URL / screenshots:

## Implementation plan
1.
2.

## How to revert
<!-- Exact steps: git revert <sha>; redeploy snapshot REL-…; migration down-script; feature flag off -->

## Approval
| Role | Name | Commit approved | Date |
|---|---|---|---|
| Change authority | | | |
| Second reviewer (high-risk) | | | |

## Post-implementation review
- Outcome: Successful / Successful with issues / Failed (rolled back)
- Follow-ups (CSI/PRB):
