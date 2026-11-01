# CHG-2026-046: Show the yearly projection line on the home page, labelled as a projection

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-11-01 16:09, as reported to the author (PublicFunds) |
| Environment | DEV for build. The merge to main is PROD (GitHub Pages) |
| Type | Normal-medium. See "Tier" |
| CIs affected | `apps/public-dashboard/index.html`, `thusa/coverage_ceiling.py`, `scripts/dashboard_check.py`, `tests/test_unknowns_by_type_constant.py`; registers: change-log |
| Linked records | CHG-2026-034 (the prediction line), CHG-2026-045 (pin decision) |
| Rollback | Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>` |

## Decision
Show the yearly prediction line on the dashboard. Label it clearly as a projection, not data.

## Existing logic
CHG-2026-034 added the line. `headlineContextLines()` in the page makes it. `headline_context_lines()` in `thusa/coverage_ceiling.py` is the Python copy. A node test keeps the two equal. The line shows under the home headline while the next year is not yet counted (`all_core_due` false). The line is already shown on home today. Its old label was "Prediction, not a result:".

## Change
1. The label is now "Projection, not data:". The rest of the line is the same. Page and Python change together.
2. The page marks the line with `data-kind="projection"`.
3. `scripts/dashboard_check.py` now checks that home shows exactly the projection lines that `headline_context_lines()` gives, with that mark. The coverage page and the report card must show none.
4. The test literals change to the new label.

Not changed: the computation, the headline, the window, the data, CSV and JSON. The line stops by itself on the first data update on or after 1 Dec 2026 (see CHG-2026-045).

## Tier
Normal-medium. This change alters text and markup on the public page (PROD). It is not a detector, the publishing pipeline, POPIA handling or a CI workflow. So it is not Normal-high. It changes page code, so it is not Standard. It needs 1 owner approval. A bot approval does not fill that slot.

## POPIA
No personal data. The line holds counts and percentages only.

## Testing
- `uv run pytest`: 747 passed, 61 skipped. This includes the node parity test of the page block against the Python model.
- `uv run --group screenshots python scripts/dashboard_check.py`: `"problems": []`, desktop and mobile.

## Risk
Low. Risk: the page text and the Python text differ. The node parity test and `dashboard_check` catch this. Risk: a reader thinks the projection is data. The label and the word "if" reduce this.

## How to revert
Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>`.
