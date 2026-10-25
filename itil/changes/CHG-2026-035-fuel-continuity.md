# CHG-2026-035: Read-only month-continuity check for the DMPR fuel price history (warn-only)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus backlog, 2026-10-24. No GO to merge is given |
| Environment | The merge target is `main`, which is PROD (GitHub Pages serves `main`; the nightly build runs this code from `main`). The owner's GO must name `main` (PROD) and CHG-2026-035. Until then the work is on the branch `chg-2026-035-fuel-continuity` (from origin/main `6abd695`, the pre-change commit; PR open, not merged, nothing pushed to main). **25 Oct 2026 (SAST):** main `d1ece5d` merged into the branch (merge commit, no rebase); only `itil/registers/change-log.md` conflicted and was resolved by the id-keyed resolver of CHG-2026-032 (38 rows, ids unique) |
| Type | **Normal-high** (the "Normal — high" row of `itil/change-enablement.md`: it touches the data-quality gate in `thusa/dq.py` that guards the publish, which is the safer literal fit for "publishing pipeline". Normal-medium is defensible by the CHG-2026-018 precedent, which added the warn-only DQ check `cpi_fresh_imf_info` to `thusa/dq.py` as Normal. The owner still decides the tier. This is a wording change of the label only; the code is unchanged. A gap is warn-only and cannot fail a build; if the check itself errors it reports `error: ...`, which the build counts as a failure like any broken check (exit 2, publish blocked), see Risk) |
| CIs affected | `thusa/dq.py` (new `FUEL_KNOWN_GAPS`, `month_gaps`, `fuel_continuity`, one extra result in `run()`), `scripts/fuel_continuity.py` (new), `tests/test_fuel_continuity.py` (new), this record, `itil/registers/change-log.md` |
| Linked records | KE-012 (fuel history), KE-014, KE-015, CHG-2026-019, -022, -027, -028; DQ checks `unique:fuel_price`, `fuel_price_plausible`, `cpi_fresh_imf_info` (the existing warn-only pattern) |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback; no .bkp files). Nothing is stored: the check writes only its row in `ops.dq_result`, rebuilt every night |

## Problem
A month that silently drops out of `curated.fuel_price` (a parser change, a PDF layout change, a 404 on a yearly file) is not caught by any check: `unique:fuel_price` and `fuel_price_plausible` look at rows that exist. 2025-12 was such a gap until CHG-2026-027; it was found by reading, not by a check.

## Facts the whitelist rests on (measured 2026-10-24 on a copy of the nightly warehouse; read-only)
- `curated.fuel_price`: 651 rows, 93 distinct months, 2019-01 to 2026-10, 7 rows in every month present. The only month missing in that range is **2025-12**. CHG-2026-027 (merged) reads it from the DMPR December 2025 workbook at the next nightly: 94 months x 7 grades = 658 rows.
- KE-012 (on main): "No fuel month is missing from 2019-01 to the latest month". History starts 2019-01 (2015 to 2018 are HTTP 404 at the DMPR path).
- CHG-2026-028: of the 84 monthly workbooks 2019-01 to 2025-12, 82 returned HTTP 200 and 2023-02 and 2023-06 returned HTTP 404. Those two are missing **workbooks**, not missing **months**: the series has both months (from the yearly history PDFs), so this check does not see them. They limit the PDF-versus-xlsx cross-check only.
- CHG-2026-028 and KE-014/KE-015: PDF-versus-xlsx **value** differences (2019-07, 2020-05, 2020-06, 2020-10, 2021-01, 2021-04, 2022-10, 2024-03, 2025-01). A value difference is not a missing month either; this check does not look at values.

## Whitelist of known gaps (exact content)
`thusa.dq.FUEL_KNOWN_GAPS = {}` : **empty.**

| Candidate | In the whitelist? | Why |
|---|---|---|
| Months before 2019-01 | No | Outside the range (first to last month present); KE-012 says history starts 2019-01, 2015-2018 HTTP 404 at the DMPR path |
| 2023-02, 2023-06 | No | The series has these months; only the DMPR monthly **workbook** is HTTP 404 (CHG-2026-028, checked 2026-10-24) |
| 2025-12 | No | Recovered by CHG-2026-027 (xlsx). Until the next nightly after that merge the live warehouse still lacks it, and the check **correctly reported it as a NEW gap** (24 Oct); after the 25 Oct nightly it is present and the check passes with the empty whitelist (see Tests) |
| The PDF-versus-xlsx value differences (KE-014, KE-015, CHG-2026-028) | No | Values, not months |

An entry would be `(year, month): "KE-nnn: reason"`. Adding one needs an RFC row naming the known error and its source, and an edit to `test_repository_allow_list_is_pinned_empty`. A whitelisted month that turns up present is reported as a stale entry (also a warning).

## What
- `thusa/dq.py`: pure `month_gaps(months, known)` (first and last month present, the months missing between them, split into `expected` (in `known`) and `new`, plus `stale_known`; a malformed month raises); `fuel_continuity(con, known=None)` (distinct `year, month` from `curated.fuel_price`; read-only SELECT); `run()` appends one result `fuel_month_continuity_info`, severity **warn**: `pass` when there is no new gap and no stale entry, else `warn` with `failures` = number of new gaps plus stale entries. It is outside `checks()`, like `raw_files_checksum_match`, because it needs Python. If it cannot run it reports `error: ...` and fails the build, as every other broken check does.
- `scripts/fuel_continuity.py [--warehouse PATH]`: opens the warehouse **read-only** and prints one report (`fuel months: 2019-01 to 2026-10, 93 present, 1 missing`, then `expected known gap: ...`, `NEW gap: ...`, `STALE allow-list entry ...`, and `fuel continuity: OK` or counts). Exit 1 on a new gap or stale entry, else 0. The same pattern as `scripts/fuel_xlsx_crosscheck.py` (a read-only script with an exit code).

## What is NOT included
- No change to any figure, parser, source, raw file or `public-data/`. No edit of the refresh skill or the routine: wiring `scripts/fuel_continuity.py` into the refresh report or routine would need its own RFC and the owner's GO.
- Not an error-severity check: promoting it to `error` (a new silent gap fails the build and so blocks the nightly publish) is the owner's decision after a few nights of running warn-only.
- No check of the number of grades in a month (a month with 6 of 7 grades is not reported), of values, of a missing OLDEST month (it silently shrinks the range: the range starts at the first month present), or of months after the last present (a missing newest month cannot be seen by looking at the data only; the live data-age check of PR #31 (CHG-2026-032, merged), is meant for data age).
- No `pf` subcommand (the `pf` CLI is the review tool).
- The build's printed summary shows only the number of warnings, not their names; naming them is a follow-up. The CLI above gives the detail.

## Risk
- Build gate (checked again 25 Oct 2026 against `thusa/build.py`, `thusa/cli.py`, `thusa/publish_data.py`): the extra result is warn-only; the build's `fail` list takes only statuses other than `pass` and `warn`, so a gap cannot fail a build. The only way it fails a build is if the check itself errors (table missing or unreadable), the same rule as every check. `dq.run` catches the exception, so a crash in the check does not abort the build process, but the status `error: ...` is not `pass` or `warn`, so the build's `fail` list takes it, the CLI returns exit 2 and `publish_data` refuses to publish (`UnsafeExport`). A gap: not in the `fail` list (measured on an in-memory warehouse, 25 Oct). A missing table: in the `fail` list. `curated.fuel_price` always exists in a build.
- Malformed month data also fails closed, deliberately: a NULL month raises `TypeError` and a month outside 1 to 12 (for example 13) raises `ValueError`; `dq.run` catches either, the status is `error: ...`, it lands in the `fail` list and blocks the publish, the same as a missing or unreadable table (`test_dq_run_malformed_months_become_error_status`). Bad input (a NULL or invalid month) therefore blocks the nightly publish **by design (fail-closed)**; making the check warn-only for bad input as well is an option left to the owner. Known low-risk follow-up, not changed now: `month_gaps` does not cap the span between the first and last month (a stray year such as 1,000,000 would walk about 12 million entries); no cap is added in this change. An empty `curated.fuel_price` is not caught by this check: 0 months passes silently (`test_dq_run_empty_fuel_table_passes_silently`), and only the existing min-rows checks guard an empty table.
- Blocked publish, tested: `test_a_crash_in_the_check_lands_in_the_build_fail_list_and_blocks_the_publish` makes the new check raise in a real synthetic build, asserts its entry is the only item in `summary['dq']['fail']` and that `publish_data.export` raises `UnsafeExport` with "quality gate". Mutation: `thusa/build.py` line 90 changed to `r["status"] == "fail"` makes this test fail (the other 31 pass); reverted with `git checkout`, no leftover.
- Public effect: the published manifest `build.data_quality` counts (pass, warn, fail) include this result: **pass +1 if there is no gap, warn +1 if there is** (25 Oct 2026, SAST: `manifest.json` `build.data_quality` on main is pass 57, warn 1, fail 0; with no gap, the first nightly after a merge shows **pass 58**, warn 1, fail 0. The dashboard prints the counts from the manifest, `apps/public-dashboard/index.html` around lines 246 and 827, so its text reads 58 passed. No figure changes; no test pins the number; every other public file is byte-identical at `d1983f3`, as reported by Scout.) Nothing else in `public-data/` changes. `public-data/` is not edited by hand.
- False alarms: a real DMPR skipped month would warn until an RFC whitelists it with a source. Intended.
- POPIA / licence: national fuel prices only, month numbers only. No personal information, identifiers or suppliers.

## Tests (evidence)
- New `tests/test_fuel_continuity.py`: 32 tests (29 at d1983f3 plus the 3 added after Validator's conditional pass, listed in Risk; the 29 are: pure function: no gap, one gap, year boundary, January and December gaps, expected vs new, allow-list is the argument and not a constant, stale entry, known month outside range, range ends are the data, empty and single month, duplicates, invalid month raises; the repository whitelist is pinned empty; warehouse read; `run()` severity warn and status warn/pass/error; not part of `checks()`; synthetic build includes it and does not fail; CLI report, exit codes, expected-versus-new split, read-only open).
- **25 Oct 2026 (SAST), after merging main `d1ece5d`: main is 585 passed, 61 skipped; this branch at `d1983f3` was 614 passed, 61 skipped (+29 new tests, +0 skipped); with the 3 new tests (32 in the file) the full suite on this branch is **617 passed, 61 skipped** (main `d1ece5d` 585 + 32, +0 skipped), `THUSA_ROOT` unset, 25 Oct 2026 SAST.** The 225 / 196 figures below are history (the earlier base `6abd695`, 24 Oct 2026).
- **Live data, 25 Oct 2026 (SAST)**, `scripts/fuel_continuity.py --warehouse` on a copy of the nightly warehouse built 03:12 that day (empty whitelist): `fuel months: 2019-01 to 2026-10, 94 present, 0 missing` / `fuel continuity: OK` / exit 0 (658 rows, 7 in 2025-12). The 24 Oct result below (`NEW gap: 2025-12`) is history: 2025-12 has since been recovered.
- History (24 Oct 2026, base `6abd695`; superseded by the 617 / 585 figures above): full suite, this worktree first on PYTHONPATH, `THUSA_ROOT` unset: **main 6abd695: 196 passed, 61 skipped; branch: 225 passed, 61 skipped** (+29 new, +0 skipped; the 61 skipped are the warehouse tests, no warehouse is built in a worktree).
- Run on a copy of the live-nightly warehouse (read-only CLI, then `dq.run` on the copy): `fuel months: 2019-01 to 2026-10, 93 present, 1 missing` / `NEW gap: 2025-12` / exit 1; `dq.run` result `fuel_month_continuity_info warn failures 1`. That is the expected live state before the 25 Oct nightly.

### Mutation tests (each change applied alone, test file re-run, file restored by `git checkout`)
| Mutation | Result |
|---|---|
| gap logic removed (`if False:`) | killed (`test_one_missing_month_is_found_and_is_new`) |
| allow-list hard-coded in `expected` / in `new` / in `fuel_continuity` | killed (3 mutations; `test_one_missing_...`, `test_fuel_continuity_uses_the_module_allow_list`) |
| year rollover broken (December) | killed |
| severity `warn` to `error`; status `warn` to `fail` | killed (`test_dq_run_warns_on_a_new_gap_and_never_fails`) |
| stale-entry detection removed; DQ ignores stale | killed |
| whitelist made non-empty | killed (`test_repository_allow_list_is_pinned_empty`) |
| month validation removed | killed |
| DQ counts expected gaps as failures | killed |
| check not appended in `run()` | killed |
| CLI always exits 0; CLI opens read-write; CLI prints NEW as expected | killed (3 mutations) |
| `SELECT DISTINCT` dropped | **survives, equivalent mutant**: `month_gaps` already de-duplicates with a set, so the result cannot differ |

## How to revert
`git revert -m 1 <merge commit>`; the next nightly rebuild then has no such result. Revert order if several are to be undone: #34 first, then #37, #36, #29 (Scout measured it clean at every step, as reported to PublicFunds). Before a merge: close the PR.

## popia-review verdict: PASS
Scan of the diff: month numbers, KE/CHG identifiers and national fuel prices only; no ID, passport, phone, email, address, account number, plate, location, credential or key; no persons or suppliers; no identity linking. Nothing removed. (Author's scan; independent review still required.)

## Seen, not touched
- `itil/changes/CHG-2026-019-...md` and `-028-...md` quote different skipped counts ("60 skipped") from today's main (61); history, left alone.
- The 84-URL and "81 of 83" sweep counts in CHG-2026-028 are not reproduced here; this check does not need them.

## Approval (Normal-high)
The Normal-high row of `itil/change-enablement.md` asks for the owner's explicit sign-off (a second reviewer when available, else the owner after a 24 h cooling-off) and the full CR template. Status, factually: no owner sign-off has been given; no second-reviewer approval and no cooling-off is recorded; this RFC does not follow the section order of `itil/templates/change-request.md` but carries its content (what and why, risk, testing, revert, popia-review); the template's "eval results for detectors" and "migration down-script" do not apply (no detector and no migration; the check writes only a row in `ops.dq_result`, rebuilt every night).

| Role | Name | Commit approved | Date |
|---|---|---|---|
| Change authority (owner) | none yet | none | |
| Second reviewer (high-risk) | none recorded | none | |

If the owner approves, the "Commit approved" cell must name the final head, and any later commit needs re-approval.

**Published effect on merge:** manifest and dashboard data-quality pass count 57 -> 58 (shown after the first nightly following the merge); no figures change.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. The change-log conflict with the other PRs is resolved: #29 to #33 and #36, #37 are merged; main is `d1ece5d`, merged into this branch with the id-keyed resolver of CHG-2026-032 (only `change-log.md` conflicted). Another merge into main before this one would again cause a trivial append conflict in that file.

Scout reviewed `d1983f3` (shadow/drift, POPIA, data-sense: PASS) and `cb4aafb` (shadow/drift, POPIA: PASS, delta wording only); Validator reviewed `d1983f3` (conditional pass) and `cb4aafb` (expert PASS, charter PASS). All as reported to PublicFunds by those reviewers; this repo holds no independent record. A reviewer PASS is not an owner GO, and no second-reviewer sign-off or cooling-off for Normal-high is recorded. Validator's conditional-pass fixes (tier, Risk, Environment, tests) were re-checked at `cb4aafb`, as reported.

Result: Open PR (not marked draft), awaiting the owner's GO; reviewer passes at `cb4aafb` as reported (Validator expert and charter PASS, Scout shadow/drift and POPIA PASS); no owner GO.
