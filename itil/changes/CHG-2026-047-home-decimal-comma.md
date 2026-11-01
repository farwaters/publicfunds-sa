# CHG-2026-047: Use the en-ZA decimal comma for every decimal on the home page

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-11-01 16:09, as reported to the author (PublicFunds) |
| Environment | DEV for build. The merge to main is PROD (GitHub Pages) |
| Type | Normal-medium. See "Tier" |
| CIs affected | `apps/public-dashboard/index.html`, `scripts/dashboard_check.py`, new `tests/test_home_decimal_comma.py`; registers: change-log |
| Linked records | CHG-2026-033 and CHG-2026-034 (decimal comma in the note lines) |
| Rollback | Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>` |

## Decision
Use a comma as the decimal mark on the home page, every time (en-ZA, for example 12,5%). Do not change CSV or JSON data.

## Check of every number on the home page (`vHome`)
| Number | Source | Before | After |
|---|---|---|---|
| Headline percentage | `manifest.coverage.complete_pct` | `75.7%` (raw number, point) | `75,7%` (new `dec1()`) |
| n of N, municipality and department counts | manifest integers | integers | not changed |
| Tender award records | `toLocaleString("en-ZA")` | `12 345` | not changed |
| Flags and hidden leads | manifest integers | integers | not changed |
| Gap note and context lines | `coreGapLines()`, `headlineContextLines()` | comma already | not changed |
| Data date | `dateSast()`, en-ZA | date and time | not changed |
| Build checks (pass, warn, fail) | manifest integers | integers | not changed |
| Freshness targets | integers in days | integers | not changed |

Only the headline percentage used a point. This change fixes it.

## Not changed, and why
- Text that the page shows verbatim from `manifest.json` keeps its points. Examples: the source code "P0151.1" and the CPI known gap "about 0.1-0.2 index points". The text comes from `config/public-data.yaml` through `manifest.json`. The owner kept JSON unchanged, so this change does not edit it. "P0151.1" is a Stats SA code, not a decimal. A later CHG can change "0.1-0.2" to "0,1-0,2" in the config, if the owner wants that. That change would alter `manifest.json`.
- The coverage page sentence "Headline: 75.7% ..." is not on the home page. It is out of scope.
- CSV downloads and JSON files keep the decimal point.

## Change
1. New page function `dec1(x)`: one decimal with a comma.
2. The headline card uses `dec1(c.complete_pct) + "%"`.
3. `scripts/dashboard_check.py` expects `75,7%` on the headline card. It also fails on any `digit.digit` in the home text, after it cuts out the verbatim manifest text.
4. New `tests/test_home_decimal_comma.py` (5 tests): `dec1` in node, the headline uses `dec1`, `vHome` has no bare `toFixed` and only en-ZA `toLocaleString`, the note lines have no point decimals, and JSON keeps the number.

## Tier
Normal-medium. This change alters number text on the public page (PROD). It is not a detector, the publishing pipeline, POPIA handling or a CI workflow. It changes page code, so it is not Standard. It needs 1 owner approval. A bot approval does not fill that slot.

## POPIA
No personal data.

## Testing
- `uv run pytest`: 752 passed, 61 skipped (5 new tests).
- `uv run --group screenshots python scripts/dashboard_check.py`: `"problems": []`.
- Negative proof (author run, not shipped): with the old headline code, `dashboard_check` reported "the headline card no longer shows '75,7%'" and "decimal point on home" on desktop and mobile.

## Risk
Low. Risk: a script reads the headline from the page text and expects a point. No such script is known in the repo. The JSON value does not change.

## How to revert
Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>`.
