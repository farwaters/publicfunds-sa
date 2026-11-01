# CHG-2026-045: Record the owner decision that the pin tests hard-fail after 1 Dec 2026

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-11-01 16:09, as reported to the author (PublicFunds) |
| Environment | Records only. No code, test or data change |
| Type | Standard. See "Tier" |
| CIs affected | Registers: change-log. This file |
| Linked records | CHG-2026-033 (owner decision 2, options a and b), CHG-2026-034 (prediction line) |
| Rollback | Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>` |

## Decision
The owner chose option (a) of CHG-2026-033 decision 2: hard fail. The pin tests must fail after 1 Dec 2026. Do not change them to xfail. Do not change them to a warning.

## Check of the current tests
The tests already hard-fail. So this change is records only.

- `tests/test_unknowns_by_type_constant.py` has `WINDOW = (2020, 2025)`.
- `test_empty_years_are_pinned_per_type` asserts that the headline window equals `WINDOW`. The assert is a plain `assert`. It has no `xfail`, no `skip` and no warning path.
- The failure message says: "expected on 2026-12-01 (FYE 2026 falls due)".
- The trigger is the data, not the clock. `100_coverage.sql` sets `all_core_due` when `as_of >= 1 Dec of the FYE`. `build.py` uses `fye_max=2026`. So the first build with `as_of` on or after 2026-12-01 puts FYE 2026 in the headline window.
- Proof on origin/main 1108a54 (author run, temp copy, not shipped): set `headline.fye_max` to 2026 in `coverage.json`. Result: 4 failed, 61 passed, 6 skipped in the pin file.

## What breaks on the first data update after 1 Dec 2026
The nightly refresh runs at 03:00 SAST. The first run on or after 2026-12-01 builds with FYE 2026 due. Then:

1. `headline.fye_max` becomes 2026 in `public-data/v1/coverage.json`.
2. `uv run pytest` goes red. `test_empty_years_are_pinned_per_type` fails on the window assert. In the temp proof, three more tests failed: `test_allowed_constant_is_pinned_to_window_and_exact_state_pattern`, `test_headline_context_edge_cases` and `test_headline_context_says_municipality_years_with_decimal_commas_and_why_the_prediction_falls`. Real data can change this count.
3. Tests marked `needs_baseline` skip. They do not fail.
4. `scripts/bootstrap.sh` fails at the test step. A fresh install or a repair stops. `PF_SKIP_TESTS=1` bypasses this. Use it only with a written reason.
5. The page is not blocked. The headline falls to about 64,9% (a prediction, CHG-2026-034). The prediction line stops. The tender caption "four years, not six" becomes stale.

## Fix path
Do these steps in one new CHG, with a PR:

1. Read the new `coverage.json`. Find the empty years for each data type.
2. Review the pins. Update `WINDOW` to the new window. Update `EXPECTED_EMPTY` and `ALLOWED_CONSTANT` to the real state.
3. Update the expected text in the tests for the headline context lines.
4. Review the tender caption ("four years, not six") and the notes on the page. Change them on purpose.
5. Update this record and CHG-2026-033 with a pointer to the new CHG.
6. Run `uv run pytest`. All tests must pass.

The tier of that fix is Normal-medium or higher. It changes page text.

## Tier
Standard. This change adds one record and one change-log row. It changes no code, test, detector, pipeline or data.

## POPIA
No personal data. No people, suppliers or IDs are named.

## Testing
- `uv run pytest` on this branch. Result is in the PR body.
- Table pipes in `change-log.md` checked: each row has 6 cells.

## Risk
Low. Records only. The risk of the decision itself: a fresh install fails until someone updates the pins. The owner accepts this cost.

## How to revert
Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>`.
