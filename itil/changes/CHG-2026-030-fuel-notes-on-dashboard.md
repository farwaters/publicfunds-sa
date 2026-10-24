# CHG-2026-030: Fuel price checker shows its "about" notes and the known errors they point to (CSI-051, rendering part)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-24 11:14 (carte blanche: "keep going", feature RFC from the roadmap, DEV only). **Owner GO: none. No merge GO is given** |
| Environment | DEV build and test; PROD release via the owner's merge GO |
| Type | Normal, medium (UI change, no flag; owner to confirm the tier). It changes `apps/public-dashboard/index.html` only; no exporter, no data, no workflow |
| CIs affected | `apps/public-dashboard/index.html` (`vTools`, fuel card), `scripts/dashboard_check.py`, new `tests/test_fuel_notes.py`, `itil/registers/csi-register.md` (CSI-051 row), `itil/registers/change-log.md` |
| Linked records | CSI-051 ("fuel.about is not rendered on the dashboard"), KE-012, KE-014, KE-015; CHG-2026-020/-021/-023 (grade labels), CHG-2026-029 (wording, stacked on `fuel.about`) |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>`; the page returns to the previous fuel card on the next Pages build (git is the rollback; no .bkp files) |

## Problem
`prices.json` already publishes `fuel.about` (six lines today: the pump-price regulation note, the three "Leaded Replacement Petrol / Unleaded" column notes, "diesel and paraffin are not regulated", and "only months published in the loaded DMPR history table are included (KE-012)"). The dashboard never shows them: the fuel checker in `#/tools` (`vTools`) reads `fuel.rows`, `fuel.grades` and `fuel.last_period` only. A reader who checks an invoice against "the official price" therefore sees no hint that
- the Coast 95 column and the 93 inland column sit under DMPR's "Leaded Replacement Petrol" heading;
- diesel and paraffin are not regulated at the pump;
- DMPR's own sources disagree in a few months (KE-014, KE-015) or a month is unknown (KE-012).

The known errors are published (`manifest.json` `known_errors`) and listed on `#/sources`, but nothing connects them to the fuel result. CSI-051 recorded the rendering as still open after the label changes.

## Change
One surgical edit in `vTools` (fuel card only):
1. **"Known issues with these prices"** (visible, under the checker result): the manifest `known_errors` entries that the fuel notes refer to, id in bold plus the published symptom text, and a link to `#/sources` ("all known errors"). Which entries? Data-driven, no hard-coded ids: every `KE-nnn` named in `fuel.about`, plus the ids named in the `known_gaps` entry of any of those ids (today `fuel.about` names KE-012 and the KE-012 gap text names KE-014 and KE-015). One hop only. If none are found the block is not drawn.
2. **"How to read these prices"** (a `details` element, collapsed, after the existing "All loaded official prices" details): the `fuel.about` lines as a list.

Text is inserted with `el()`/`textContent` only (no HTML injection, as elsewhere). No new request: `prices.json` and `manifest.json` are already loaded by `vTools`.

`scripts/dashboard_check.py`: records the new block's text in `checks` for both viewports and fails if the block is missing while `known_errors` contains a KE id named by `fuel.about` (so a future refactor cannot silently drop it).

## Not changed
`thusa/`, `config/`, `public-data/` (no file written, no nightly run), `itil/knowledge/known-errors.md`, CI workflows, the per-result text of the checker. The checker does not yet say "this month is affected by KE-014/015"; that needs structured month tags in the data and is a separate, Normal-high change (not done).

## Evidence (DEV, 2026-10-24)
Built from origin/main 6abd695 (PRs #22-#28 merged). Live `public-data/v1` (published before the next nightly) and, for the post-nightly view, the export of a **copy** of the data (`cp -a` of the data root to a scratch location outside the repo; `thusa ingest --only dmpr_fuel` fetched the December 2025 workbook once into the copy; `thusa build` fail []; `pf publish-data` to a scratch folder; the working data root only read, `public-data/` not written, nightly not run).
- On the live data the block lists KE-012. On the post-nightly export the selection is KE-012, KE-014, KE-015 (the KE-012 known gap names KE-014 and KE-015), `fuel.about` has 6 lines, no console error on desktop or mobile.
- Bug found while testing and fixed before commit: my first version followed pointers transitively in gap order (KE-014's gap would have pulled in KE-015 only if listed later). It is now exactly one hop, independent of gap order; `tests/test_fuel_notes.py` has a case for both orders.
- Screenshots (not in the repo; kept with the review evidence): the live data run of `dashboard_check` (31 files) and the post-nightly export of the data copy (`fuel-card-before-*`, `fuel-card-after-*`, `fuel-card-after-about-open-*`, desktop and mobile; Jan 2025 coast 95 selected, which is a KE-015 month).

## Merge GO and PROD publish
Needs the owner's quoted merge GO for CHG-2026-030 only. The page is static: after the merge, GitHub Pages serves the new `index.html`. The block's content depends on the published manifest: on the live manifest of today (before the next nightly after PRs #22-#27) the "known issues" block lists KE-012 only; KE-014 and KE-015 appear when the nightly publishes them. No GO for any other PR is implied.

## Merge timing
Until the next nightly publishes the new known-error texts (PRs #22 to #27 are merged but not yet published), the live "Known issues with these prices" block would show KE-012 with the old text cut mid-sentence and no KE-014 or KE-015 (checked on the live manifest at 11:36 SAST on 24 Oct 2026: KE-012's symptom ends in an ellipsis and the manifest lists no KE-014/KE-015). Recommended: merge after the nightly of 25 Oct 2026, or the owner's GO explicitly accepts the interim state.

## Open follow-ups
(a) The public wording uses internal ids and jargon ("xlsx", "RON section, zone 1A", "c/l", "Others: CHG-2026-028", bare cent figures beside rand prices); a separate plain-language wording change is proposed.
(b) The block shows for every month, not only the affected months. Showing it only where it applies needs month tags in the published data: a separate Normal-high change.
(c) KE-015's "five months" covers only the 82 workbooks DMPR serves; nothing is known for 2023-02 and 2023-06 (HTTP 404).

## Data identical before/after
Yes. No file under `public-data/` or `data/` is touched; the diff is `index.html`, `scripts/dashboard_check.py`, one test file and records.

## Tests
Run: new `tests/test_fuel_notes.py` (static checks on `vTools`; the id-selection lines are cut out of the page verbatim and run in node against fixture cases and against `public-data/v1`, compared with a Python reference; skipped if node is missing); `uv run pytest -q` with `THUSA_ROOT` unset; the same with a data copy; `scripts/dashboard_check.py` with axe-core (15 pages x 2 viewports, `problems: []`); screenshots of the live data and of the post-nightly export of a data copy (kept with the review evidence, not in the repo).

## POPIA review
popia-review done by me (PublicFunds, the author), which is not an independent review: rendering of already-published, non-personal text (fuel notes and known-error descriptions). No personal information, IDs, contacts, accounts, credentials or supplier names; no new data collected; no third-party request; no cookies or storage. Independent popia-review: Scout (an independent reviewer, not the author) passed ee973ad and cb13b48 with no personal information found (cb13b48 as reported to the author); there is none at 3cb60d4. Each PASS covers only the head it names (ee973ad, cb13b48); Scout passed 6a8594d with the independent popia-review (as reported to me); the commit after 6a8594d (wording and counts only, no code change) has none (requested, not done). No Validator popia-review is recorded here. Reviewer PASSes are not an owner GO. This RFC does not claim an owner GO.

## Review
Four checks (expert, shadow, charter, drift) and the independent popia-review: Validator does expert and charter; Scout does shadow, drift and the independent popia-review. Validator (expert, charter) and Scout (shadow, drift) passed with should-fix items at 3cb60d4 (Validator's results per Validator's report). Re-checked PASS at ee973ad and cb13b48 (expert and charter per Validator's report; shadow and drift: Scout). A further small fix list at ee973ad (the reviewer who gave it is not recorded here) was applied in cb13b48 (RFC wording and records only; `index.html`, `scripts/dashboard_check.py` and the tests unchanged). At 6a8594d Scout passed all checks, including the independent popia-review, and Validator passed expert (PASS) and charter (PASS with should-fix items), as reported to me; I have not seen the reports. The should-fix items for this change are the wording and test counts in this file, applied in the commit after 6a8594d, which is not reviewed (re-check requested, not done); the commits between cb13b48 and 6a8594d have no named review beyond the 6a8594d report. Reviewer PASSes are never an owner GO and cover only the heads they name. Merge needs the owner's quoted GO for CHG-2026-030.

Result: DEV build and tests succeeded; Validator (expert, charter; per Validator's report) and Scout (shadow, drift) passed with should-fix items at 3cb60d4; Scout's independent popia-review passed at ee973ad and cb13b48 (none at 3cb60d4); 6a8594d passed by Scout (all checks, including popia-review) and Validator (expert PASS, charter PASS with should-fix), as reported to the author; the commit after it (wording and counts) is not reviewed (re-check requested); awaiting the owner's merge GO (none given).
- `uv run pytest -q`, `THUSA_ROOT` unset: **282 passed, 61 skipped** with main 75fbd63 merged into this branch (main 75fbd63: 267 passed, 61 skipped; +15 new tests in `tests/test_fuel_notes.py`). The earlier 211 passed, 61 skipped was on main 6abd695 (196 passed, 61 skipped; +15), before main moved.
- With the data copy (`THUSA_ROOT` pointing at the copy, December workbook ingested): **271 passed, 1 skipped** (main 6abd695: 256 passed, 1 skipped); not repeated on main 75fbd63.
- `scripts/dashboard_check.py` (axe-core 4.14.0 from a copy outside the repo, via `AXE_JS`; worktree first on `PYTHONPATH`): 15 pages x 2 viewports, axe on all 30, **0 violations, `problems: []`**, exit 0; `checks.*_fuel_known` records the block text.
- Not done: month-level flagging in the checker result (needs structured month tags in the data; separate Normal-high change); the CSI-051 row says "Rendering built in DEV (PR #29), not merged; needs the owner's merge GO" until the merge.
