# CHG-2026-040: Nightly evidence guard: a data type and financial year must not silently become fully empty (CSI-053)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus backlog, 2026-10-25 (CSI-053). **No GO to merge is given; no reviewer has been run** |
| Environment | The merge target is `main`, which is PROD (GitHub Pages serves `main`; the nightly build runs this code from `main`). The owner's GO must name `main` (PROD) and CHG-2026-040. Until then the work is on the branch `chg-2026-040-evidence-guard` (from origin/main `26b0b61`; PR open, not merged, nothing pushed to main) |
| Type | **Normal-high** (the "Normal — high" row of `itil/change-enablement.md`: "publishing pipeline"; unlike the fuel check of CHG-2026-035 this guard **can block the publish on purpose**) |
| CIs affected | `thusa/evidence_guard.py` (new, pure), `thusa/publish_data.py` (new `_evidence_guard`, one call in `export`, one extra key in the returned dict), `config/evidence-guard-allow.yaml` (new, empty), `tests/test_evidence_guard.py` (new), this record, `itil/registers/change-log.md` |
| Linked records | CSI-053; CHG-2026-033 (by-type N-of-N pins; `thusa/coverage_ceiling.py` already calls a year with no `P` cell for a type EMPTY); CHG-2026-035 (the warn-only fuel check, whose wiring this follows; this guard differs in blocking); `publish_data.UnsafeExport`, `scripts/publish-public-data.sh` |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback; no .bkp files). The guard stores nothing and writes nothing |

## Problem
The CHG-2026-033 review (X1) emptied 100 of 257 audit-opinion cells for 2022/23 in a scratch run: all tests passed. The pins in CHG-2026-033 are tests, and tests do not run in the nightly build, so a data hole that appears at night is published. Nothing compares tonight's candidate with what is already live.

## Design choices (stated plainly)
1. **Compare with the previously published file.** The candidate `coverage` document (built from the warehouse at export time) is compared with the `coverage.json` that is in `public-data/v1/` **before** the export overwrites it. That is the file on `main` as the nightly's checkout holds it. No warehouse history and no extra stored state are used.
2. **FAIL (block the publish, exit nonzero) only when** a data type and financial year that had **at least one fully present municipality** (a `P` cell) in the previous file has **none** in the candidate. "Fully present" is the `P` state of `coverage.json`; `p` (partial), `m`, `-` and `?` do not count. A data type or year missing from the candidate counts as zero.
3. **WARN only (never blocks) for a count drop.** When a pair's count of `P` falls by more than `WARN_DROP_SHARE` of the previous count, and the previous count is at least `WARN_MIN_PREVIOUS`, a `warn:` note is printed. Both are named constants in `thusa/evidence_guard.py`.
   - `WARN_DROP_SHARE = 0.10` (10 %). **Reasoning, and an honest limit:** no night-to-night history exists to measure on (`coverage.json` has been committed once, on 19 Oct 2026, all copies are byte-identical, and every build in `changes.json` shows the same 75.7 %). The proxy measured on the current file was the spread between adjacent years of the same type: 0 to 2.4 % for budget, actual and UIFW, and 9.0 % for one pair. So 10 % sits just above the largest normal spread and far below the X1 loss of 40.5 % (247 to 147). It is a starting value, to be re-set after the first 30 nightly runs (the CSI-053 acceptance counts false positives over those runs).
   - `WARN_MIN_PREVIOUS = 20`: a drop of one or two municipalities in a small pair (procurement has 1 and 3 `P` in 2019/20 and 2021/22) is not a signal.
4. **First run, or no previous file:** the guard passes with the note `no previous published coverage.json (first run): evidence guard skipped`, so a fresh clone or a new output folder can publish.
5. **Legitimately removed data:** a documented allow list, `config/evidence-guard-allow.yaml`, **empty by default** (`allow: []`, pinned by a test). An entry has `data_type`, `year`, `reason` and `date` (ISO `YYYY-MM-DD`), all required. An allowed pair no longer blocks; it is reported as `allowed:`. An entry whose pair has a fully present municipality again is a `warn:` ("remove it"). Adding an entry needs an RFC row and the owner's GO (it is a Normal-high change to a publish guard), and the test that pins the list empty is edited with it.
6. **Fail closed.** If the previous `coverage.json` cannot be read or parsed, if it is malformed (for example a cell string whose length differs from the number of years), if the allow file is missing, or if an allow entry is malformed (missing key, unknown type, non-integer year, empty reason, bad or impossible date, duplicate), the export raises `UnsafeExport` ("evidence guard could not run (nothing was written)") and **writes nothing**.
7. **Where it runs.** At the top of `publish_data.export`, right after the candidate documents are built and **before any file is written**. A block is an `UnsafeExport`, exactly like the existing quality gate, so: `pf publish-data` exits **3**, `scripts/publish-public-data.sh` exits 3 and commits nothing, and **the data already published stays live and untouched**. It is not a dq check: a dq failure would change the manifest's dq counts and would need the warehouse to know the published file; at export time the previous file is simply the one on disk. The guard's notes are also returned in the export result under `evidence_guard` (the CLI prints the result), and printed to stderr as `evidence guard: ...`. No connector is changed; no figure is changed.

## How an owner can override
- **The documented way:** merge an allow-list entry (RFC row + owner GO). It takes effect at the next nightly after the merge, so a false-positive block costs one night of staleness. This is slow on purpose: it leaves a reason and a date in git.
- **Emergency, on the nightly's own checkout:** the owner (or the person running the nightly) can add the entry locally without committing, or remove `public-data/v1/coverage.json` (the guard then takes the "first run" path and passes with a note). Both are bypasses of the guard: they must be recorded in the run notes and followed by the proper commit.
- **Not included:** a one-shot command-line flag (for example `--skip-evidence-guard`). It would be a quiet way to defeat the guard and the owner has not asked for one. Listed as an open question.

## What is NOT included
- No change to any figure, connector, parser, source, raw file or to `public-data/` (not edited by hand; the first nightly after a merge writes the same files).
- No edit of the refresh skill, the refresh routine or the publish script: WARN notes are visible only in the `pf publish-data` result (`data/publish-data.json`, `data/publish-data.log` where the routine writes them) and on stderr. Surfacing them in the nightly report needs its own RFC.
- No check of values or amounts, of `p` (partial) cells, of the headline percentage, or of a partial load that keeps one `P` (a pair going from 247 to 1 passes the FAIL rule; the WARN covers it, which is the fragility CHG-2026-033 describes).
- No FAIL for a count drop (the owner's instruction: WARN only). See the X1 finding below.

## X1 finding (read this before approving)
The CSI-053 acceptance text says the X1 scratch run, emptying 100 opinion cells for 2022/23, "fails the guard". Under the rule above it **does not fail**: 147 of 247 municipalities still have a fully present opinion for 2022/23, so the pair is not "fully empty". It gives a **WARN** (`warn: audit_opinion 2023: 247 -> 147 (40.5% fewer)`). **Only emptying all 247 fails.** The X1 test in `tests/test_evidence_guard.py` states exactly this, on the real file. Options for the owner: (A) keep the rule and reword the CSI-053 acceptance to "X1 produces a warning; emptying the whole type and year blocks"; (B) add a second, separate FAIL threshold for count drops (a new constant, for example a 30 % drop on a previous count of at least 20; it would have blocked X1). B was **not** built because the instruction was "WARN only" and B raises the false-positive risk of blocking the nightly.

## Risk
- **False-positive block of the nightly (the main risk).** A legitimate removal of a whole type and year, or a source outage that empties one pair, blocks the publish. Mitigations: the block leaves the existing live data exactly as it is (tested: the output folder is byte-identical after a block); the message names the pair and the counts; the allow list is the documented way out. Exposure today: 28 data type and year pairs have a `P` in the live file and are guarded; the smallest are procurement 2019/20 (1 `P`) and 2021/22 (3 `P`), which an ordinary loss of one or two municipalities would empty. Whether procurement belongs in the guarded set is an open question; it is guarded because the owner's rule says "a data type".
- **Fail closed** also means a corrupt `public-data/v1/coverage.json` or a bad allow file blocks the nightly until fixed (restore the file with `git checkout public-data/v1/coverage.json`).
- **Ordering caveat.** The guard compares with the nightly's local `public-data/`. If that folder is behind or ahead of `main` (for example an unmerged earlier publish), "previous" is that local file. The live dry run below used a copy of it.
- **The WARN threshold is a guess backed by a proxy**, not by history (see design choice 3). Too low gives noise that is easily ignored, too high misses a real drop.
- **A block is only seen if somebody looks.** The routine and the refresh skill are not edited. Exit code 3 and the stderr text already exist as the signal of a refused publish.
- **Published output:** none. The return dict of `export` gains the key `evidence_guard`; no published file reads it. The manifest's dq counts are unchanged because the guard is not a dq check.
- **POPIA:** the guard reads and prints aggregate counts of municipalities per data type and year, data type names and years. No names, amounts, identifiers or suppliers are read or written.

## Tests (evidence)
- New `tests/test_evidence_guard.py`: **52 tests**: pure function (unchanged data passes, first run passes with a note, emptied pair fails, one left passes, already-empty is not a new block, `p` is not counted, a missing year or type counts as empty, several pairs are all listed); allow list (allowed, stale, 13 malformed forms, duplicates, YAML date, repository list pinned empty); drop warning (exact boundary, rises, small counts, constants pinned, a drop to zero is a block and not also a warn); malformed coverage documents; the real `public-data/v1/coverage.json` (passes against itself; each of its guarded pairs blocks when emptied; **the X1 scratch test**: 100 of the 247 `P` opinion cells for 2022/23 emptied gives a warn and no block, emptying all 247 fails); **real synthetic builds** (the `synth_root` fixture and `publish_data.export`): a normal run passes (first-run note, then a second run with no notes and unchanged files), a **block path** (the opinion 2023 cells of a copy of the warehouse set to missing: `UnsafeExport`, the output folder byte-identical, CLI `pf publish-data` exit 3, a normal run exit 0), an allow entry lets it through, a bad allow entry blocks, unreadable previous files and a missing allow file block and write nothing, a drop warning is printed without blocking.
- **Full suite** (`env -u THUSA_ROOT uv run --frozen pytest -q`, 25 Oct 2026 SAST): **669 passed, 61 skipped** (main `26b0b61` 617 + 52, +0 skipped).
- **Live dry run, 25 Oct 2026 (SAST)**, on copies only (a copy of the nightly warehouse built 03:12 and a copy of `public-data/v1`): the guard passes with no notes, and the `coverage.json` it writes is byte-identical to the published one. On the same copies: X1 (100 opinion 2022/23 cells set to missing) exports with the WARN `audit_opinion 2023: 247 -> 147 (40.5% fewer)`; then emptying the rest blocks (`BLOCK: audit_opinion 2023: 147 fully present municipalities before, 0 now` — 147 because the copy already held the X1 output) and the output folder is untouched. The real warehouse and the real `public-data/` were not touched.

### Mutation tests (36 mutants, each applied alone, the guard/wiring tests re-run, file restored by `git checkout`)
| Mutation group | Result |
|---|---|
| Guard fails open: status always `pass`; `after == 0` changed to `after < 0` or `after <= 1`; `before >= 1` changed to `>= 2` or `>= 0`; missing year or type defaults to present; `p` counted as present (M01 to M05, M19, M20) | killed |
| Allow list ignored (membership forced False, list not read), applies to every pair, keyed by type only, keyed by year only (M06 to M10) | killed (M08 to M10 killed by a crash of the test run, M06 and M07 by test assertions) |
| Threshold sign flipped, `>` changed to `>=` or `<`, `WARN_DROP_SHARE` 0.10 to 0.5, `WARN_MIN_PREVIOUS` 20 to 0, `>=` changed to `>` or `<=` on the minimum (M11 to M17) | killed (M15 by a crash) |
| Stale-entry threshold `>= 1` changed to `> 1` (M18) | **survived at first** (nothing tested a stale entry with exactly one municipality back); **killed** by the added test `test_allow_entry_is_stale_as_soon_as_one_municipality_is_present_again` |
| Allow-entry validation removed one check at a time: reason, date format, real date, data type, duplicate, bool accepted as year, cell-length check (M22 to M28) | killed |
| First run not special-cased (M21) | killed |
| Wiring: guard call replaced by `pass`, fail does not raise, previous always treated as missing, allow list not passed, wrong previous file name, errors swallowed instead of blocking, notes not printed, result not returned (M29 to M36) | killed |

**Survivors after the added test: none** (an equivalent mutant was not found; the 36 mutants are the runner's list, kept outside the repo).

## How to revert
`git revert -m 1 <merge commit>`. The next nightly then has no guard; nothing else changes. Before a merge: close the PR.

## popia-review verdict: PASS (author's scan; independent review still required)
Diff scan: aggregate counts, data type names, years, RFC and CSI identifiers only. No ID, passport, phone, email, address, account number, plate, location, credential or key; no persons or suppliers.

## Seen, not touched
- The CSI-053 row in `itil/registers/csi-register.md` is not edited: its acceptance text ("fails the guard") needs the owner's answer on X1 first (option A would reword it).
- The change-log row of CHG-2026-039 lives on the branch of PR #38 and is not on `main`; this change adds only its own row, so a trivial append conflict with #38 is possible whichever merges second.
- Older change-log status cells (002, 003, 005, 008, 014) are stale; out of scope.

## Approval (Normal-high)
**Unreviewed, no owner GO.** The Normal-high row asks for the owner's explicit sign-off (a second reviewer when available, else the owner after a 24 h cooling-off) and the full CR template. No sign-off, second-reviewer approval or cooling-off is recorded. This RFC does not follow the section order of `itil/templates/change-request.md` but carries its content; "eval results for detectors" and "migration down-script" do not apply.

| Role | Name | Commit approved | Date |
|---|---|---|---|
| Change authority (owner) | none yet | none | |
| Second reviewer (high-risk) | none recorded | none | |

If the owner approves, the "Commit approved" cell must name the final head, and any later commit needs re-approval.

## Review
None run. Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author are needed before any merge.

Result: Open PR, not merged; no reviewers run; no owner GO.
