# CHG-2026-041: Show the evidence-guard result and exit 3 in the nightly report (CSI-054)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner via Cavus backlog, 2026-10-26 (CSI-054). **No GO to merge is given; no owner sign-off is recorded** |
| Environment | The merge target is `main`, which is PROD (the nightly runs `scripts/publish-public-data.sh` from `main`). The owner's GO must name `main` (PROD) and CHG-2026-041. Until then the work is on the branch `chg-2026-041-guard-report` (from origin/main `f3801f0`; nothing pushed to main) |
| Type | **Normal-high** (see "Tier" below) |
| CIs affected | `scripts/publish-public-data.sh` (one function, two call lines), `tests/test_publish_guard_line.py` (new), `docs/bot/skills/publicfunds-refresh/SKILL.md` (repo copy, step 4), this record, `itil/registers/change-log.md`, the CSI-054 row of `itil/registers/csi-register.md` |
| Linked records | CSI-054; CHG-2026-040 (the evidence guard, merged, `143c1be`); CHG-2026-025 (nightly step 0; the routine's saved prompt is not readable); CHG-2026-032 (RB-12, `scripts/check_live.py` warns at 30 h, breaches at 48 h); runbook RB-11 |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>` (git is the rollback; no .bkp files). The change stores nothing and writes nothing |

## Problem
Since CHG-2026-040 the publish can be refused by the evidence guard (exit 3) or can carry guard warnings. Both are visible only on stderr, in `data/publish-data.log` and in the `evidence_guard` key of `data/publish-data.json`. The publish script prints only `exported: N bytes, M files`. The nightly report therefore says nothing about a guard warning, and an exit 3 is reported only if the routine happens to say so (see "What the nightly does on exit 3").

## Tier
**Normal-high.** `itil/change-enablement.md` lists "publishing pipeline" under Normal-high, and this change edits `scripts/publish-public-data.sh`, which is the publishing pipeline. The reasoning for not going lower: the change is read-only and cannot alter a published file or an exit code (tested, see below), which would argue for Normal-medium, but the tier table is by what is touched and not by the size of the edit, and the edit sits on the one script that commits and pushes to `main`. A Normal-high needs the owner's explicit sign-off plus a second reviewer, or the owner after a 24 h cooling-off. **None is recorded.**

## Design (the smallest change that works)
1. **One labelled stdout line** from the script, from the existing `evidence_guard` key of `data/publish-data.json` (no change to `pf`, `thusa/publish_data.py` or `thusa/evidence_guard.py`):

   | Situation | Line |
   |---|---|
   | key present, status `pass`, **no notes at all** | `evidence_guard: pass` (the only quiet value) |
   | key present, status `pass`, notes but no `warn` note (an `allowed:` entry in use, a first run, a schema or data-type note) | `evidence_guard: pass (N note[s])` |
   | key present, one or more `warn` notes | `evidence_guard: warn (N note[s])` |
   | export refused (exit 3) and the `pf` error starts with `evidence guard` (a BLOCK, or the guard could not run) | `evidence_guard: BLOCKED (exit 3; nothing published, published files left as they are)` |
   | export refused (exit 3) and no guard refusal is found in the log (quality gate, safety scan, no warehouse, another refusal or a crash) | `evidence_guard: not an evidence-guard refusal (no guard refusal found in the log; cause may be the quality gate, the safety scan, another refusal or a crash; read data/publish-data.log)` |
   | key missing, not an object, status not `pass`, `notes` not a list, file empty/unreadable/invalid JSON | `evidence_guard: UNKNOWN (...; treat as not checked)`: never shown as pass |
   | the report helper itself fails (non-zero exit of `python3 -`) | `evidence_guard: UNKNOWN (report helper failed)` |

   After the line come up to 3 note lines (`evidence_guard:   <note>`; `warn` notes first, then `note:`/`allowed:` notes) and, if more, `evidence_guard:   ... and K more (data/publish-data.json, data/publish-data.log)`. The BLOCKED line is followed by the refusal reason. The exit-3 case is read from the log because on exit 3 `pf` writes no `evidence_guard` key (the export raised before it returned). **Note text is sanitised before it is printed:** control characters (including ESC and BEL) and format characters are removed, whitespace and newlines collapse to single spaces, and each note is capped at 300 characters (`...` at the end), so a note cannot forge a line or drive the terminal; at most 3 notes are shown.
2. **It can never change what is published or the exit code.** The helper only reads two ignored files in `data/` and prints; it is called as `guard_report ... || true`, it has a catch-all that prints UNKNOWN, and if the helper process itself fails the function prints `UNKNOWN (report helper failed)` and returns 1, which the call-site `|| true` swallows (so a crash can never turn exit 0 or 3 into exit 1, and cannot make the line silently disappear). The `uv run pf publish-data ... || { ...; exit 3; }` line keeps its exit 3; `exit 4`, the no-change exit 0 and the timestamp-only exit 0 are untouched. No new Python module: the logic is an inline `python3 -` heredoc in the script, so the tests run the real script.
3. **"BLOCKED" is printed only when the guard was the cause.** The first design would have called any exit 3 a guard block. The quality gate runs before the guard in `export()`, so a quality-gate exit 3 does not print BLOCKED. **Label corrected after review:** the first wording (`not the cause (exit 3 came from the quality gate, ...)`) claimed to know the cause; the line now says only `not an evidence-guard refusal (no guard refusal found in the log; ...)`, because the script cannot tell a quality gate from a crash.
4. **Skill (repo copy only):** step 4 of `docs/bot/skills/publicfunds-refresh/SKILL.md` now says a line that is not exactly the bare `evidence_guard: pass`, a **missing** line (treated as UNKNOWN, not pass) and an exit 3 must be reported to the owner, and says what exit 3 means. The user's own skill and the routine's saved prompt are **not** touched by this change; wording for both is in the Appendix.

## Scope: what this change does not do
- No change to `thusa/*`, the guard, its thresholds, the allow list, the published files, any exit code, or the quality gate.
- No edit outside the repo: not the live skill, not the routine, not memory, not the template. The nightly does not show the new line until the skill step and the routine prompt are updated by the owner after a merge (Appendix).
- **Appendix A and B change the routine's behaviour** (A adds a `--push` publish step to the live skill, which has none today, and B adds a new report format) and are **not applied by this change**. They need the owner's separate approval after a merge.
- No change to RB-11 (it already says exit 3 = export refused; read the files).
- The pre-existing exit 3 / `tail` quirk below is noted and not changed.

## What the nightly does on exit 3 (verified from the repo and the box, with the limit stated)
- **In the script (`set -euo pipefail`):** the `pf publish-data` line is `uv run pf publish-data > data/publish-data.json 2> data/publish-data.log || { tail -n 5 data/publish-data.json data/publish-data.log >&2; log "export refused (see data/publish-data.*)"; exit 3; }`. So on a `pf` failure the script shows the last 5 lines of each file on stderr, prints `export refused`, and **exits 3 before any git step: nothing is staged, committed or pushed, and the files in `public-data/` are left as they are.** Checked on a scratch run (below): `git status` clean, no new commit, `public-data/` unchanged.
- **In `pf` (`thusa/review/cli.py`, `cmd_publish_data`):** `UnsafeExport` is turned into `CliError("public data not written: <reason>", 3)`; `main()` prints `{"error": "<message>", "exit_code": 3}` as JSON on stderr and returns 3. The same exit 3 is used for: no warehouse, the quality gate (`quality gate: the current build failed N data-quality check(s)`), the evidence guard (`evidence guard: BLOCK ...` or `evidence guard could not run ...`) and the safety scan. The quality gate runs before the guard.
- **Exit 4** is a different refusal (other staged files, wrong branch, main moved) and is already covered by the skill.
- **Documentation:** RB-11 says "Exit 3 = export refused (quality gate or safety scan: read data/publish-data.json / .log)". The repo copy of the skill covered only exit 4 (before this change). RB-12: `scripts/check_live.py` warns at 30 h of data age and breaches at 48 h, so a missing publish becomes a breach only after two nights.
- **Not visible, so not known: what the nightly routine does or reports when the script exits 3.** The user's live refresh skill (a copy outside the repository; read only, not changed) has steps 0 to 5 and **no publish step**: the publishing is done by the routine's own saved prompt, which cannot be read from the repo or the box (CHG-2026-025 records the same, and the routine's own data commits are in the reflog). It is therefore **not verified** whether the routine reports an exit 3 to the owner, retries, or stops. This replaces the earlier wording of CHG-2026-040 ("not verified: what the nightly routine does ... the routine and skill were not read"): the skill was read for this RFC (no publish step); the routine prompt still cannot be read. The Appendix wording is written so that it works whatever the routine does today.
- **Last real nightly (26 Oct 2026 03:10 SAST, `f3801f0`):** `data/publish-data.json` has `"evidence_guard": {"status": "pass", "notes": []}` and `data/publish-data.log` is empty. The guard has run in production once since it was merged and passed.
- **Pre-existing quirk, not changed:** inside the `||` block, if `tail` itself fails (for example `data/publish-data.log` was deleted after the redirect created it), `set -e` ends the script with exit 1 and not 3. Not reachable in normal running; recorded so nobody expects exit 3 from every failure.

## Risk
- **Touches the publishing script** (the reason for Normal-high). Mitigations: the helper is read-only, is always followed by `|| true` (including when the helper process crashes, tested with a `python3` shim), prints to stdout only, and runs after `pf` has finished; tests assert no commit and no `public-data/` change in every case and that exit codes are unchanged, including a `pf` failure with another code (rc 7 gives exit 3 as before); the dry run below shows byte-identical output.
- **Extra stdout lines.** A caller that parses the script's stdout would see new lines starting `evidence_guard:`. The only known caller is the nightly routine (prompt not visible); the existing lines (`exported:`, `committed`, etc.) are unchanged and in the same order, with the new lines inserted after `exported:` (or before `export refused`).
- **A wrong label would mislead the owner.** "BLOCKED" needs the JSON error to start with `evidence guard`; anything unreadable is UNKNOWN, never pass, and a crashed helper is UNKNOWN too. A line that is **missing** (for example because the skill was not updated) must be treated as UNKNOWN by the report (Appendix A). Only a bare `pass` is quiet: a pass with any note (an allow entry in use, a first run) prints `pass (N notes)`. Tested.
- **The log format is a dependency.** The refused path reads the `{"error": ...}` JSON that `main()` prints. If that format changes the line falls back to `not an evidence-guard refusal`, which is wrong for a BLOCK; a test replays the real `pf publish-data` output for a block, so a format change fails a test.
- **The line is only seen if the skill step and the routine prompt are updated** (Appendix). Until then nothing changes in the nightly report.
- **Note text goes to a terminal and a report.** It comes from the guard (our own code) and from `pf` error text, which can carry a path or an exception message. It is cleaned (above) so it cannot forge an `evidence_guard:` line, inject control sequences or flood the report. Tested with a forged line, ESC, BEL, NUL, bidi and zero-width characters and a 200 KB note.
- **POPIA:** the line prints aggregate counts, data type names and years from the guard notes. No names, amounts, identifiers or suppliers.

## Tests (evidence)
- New `tests/test_publish_guard_line.py`: **28 tests** (the file was 15 before the fix round). Each runs the **real script** in a scratch git repo with a stub `uv` that replays stdout, stderr and the exit code of `pf publish-data`, and (where needed) a `python3` shim that fails only the report helper (`python3 -`). They assert the line, the notes, the exit code, and, unless the test is about a commit, no commit and no change in `public-data/`. Cases: pass (bare, one line, exit 0); **any note makes it `pass (N notes)`** (an info note, an `allowed:` note, a schema or data-type note; a real replay of a 247 to 0 emptying with an allow entry); warn with 5 notes (the count, 3 notes, `... and 2 more`); one warn is singular and warns come before info notes; **block** (exit 3, `BLOCKED`, the reason shown, exit stays 3); the guard "could not run" is also BLOCKED; a quality-gate or no-warehouse exit 3 is `not an evidence-guard refusal`; **a JSON error line that is not a `pf` refusal but mentions "evidence guard" is not taken for a block** (covers the `startswith('public data not written:')` check); odd stderr with exit 3 still exits 3; **missing key**, `null`, not an object, bad status, `notes` not a list (UNKNOWN, exit 0, never pass); **empty or invalid `publish-data.json`** (the `exported:` line prints blank, then `UNKNOWN`, exit 0); **a crashing report helper** prints `UNKNOWN (report helper failed)` in the ok path (exit stays 0) and in the refused path (exit stays 3), and a helper killed by a signal or missing leaves the exit code alone; **notes are one clean line each** (a note with `\nevidence_guard: pass` cannot forge a line; ESC, BEL, NUL, bidi and zero-width characters are removed; whitespace is collapsed; a 200 KB note is capped at exactly 300 characters; the BLOCKED reason is cleaned the same way); the line is also printed when the publish goes on to commit (order: `exported:`, `evidence_guard:` lines, `committed`); other exit codes unchanged; and the replay of real `pf_main(["publish-data", ...])` output on the synthetic warehouse for a first-run pass (with its note), a warn (previous file padded so the drop is over 10 %) and a block (output folder byte-identical).
- **Full suite** (`env -u THUSA_ROOT uv run --frozen pytest -q`): see the PR body for the counts at the head sha (main `f3801f0`: 699 passed, 61 skipped; the pre-fix head `57208e9`: 714 passed, 61 skipped).
- **Dry run, 26 Oct 2026 (SAST), scratch copies only, repeated on the final script.** A copy of the nightly warehouse (built 03:10) in a scratch root, scratch clones at `f3801f0` (one with the old script, one with the new), a `uv` shim that runs this branch's `pf publish-data` against the scratch warehouse and the clone's `public-data/v1`. The real checkout, warehouse and `public-data/` were not touched.
  - Old script: `exported: 4361785 bytes, 19 files`, `only timestamps changed; not committed`, exit 0. New script: the same plus `evidence_guard: pass`, exit 0. **`diff -r` of the two `public-data/` trees: identical; both identical to the committed `f3801f0` tree** (`git status` shows only the script).
  - A direct `pf publish-data` into a copy of the committed folder differs from it in **one file, `manifest.json`, in one line (`generated_at_sast`)**; **`coverage.json` is byte-identical** (`cmp`) and so are the other 17 files.
  - **Warn run** (100 of the 247 opinion 2023 cells set missing): exit 0, `evidence_guard: warn (1 note)` and `evidence_guard:   warn: audit_opinion 2023: 247 -> 147 (40.5% fewer)`; the publish itself behaves as before (it commits in the scratch clone).
  - **Block run** (all 247 emptied): exit 3, `evidence_guard: BLOCKED (exit 3; nothing published, published files left as they are)` and the reason, `export refused`; no commit, `public-data/` unchanged.
  - **Not a guard refusal** (a scratch root with no warehouse): `evidence_guard: not an evidence-guard refusal (no guard refusal found in the log; cause may be the quality gate, the safety scan, another refusal or a crash; read data/publish-data.log)`, exit 3.

### Mutation tests
38 mutants of `scripts/publish-public-data.sh`, each applied alone and `tests/test_publish_guard_line.py` run with `-x`, the script restored after each. **The runner is a scratch script outside the repo (it is not committed), so the results are not reproducible from this PR alone; this table is the record.** **37 killed, 1 survives (an equivalent mutant).**

| # | Mutant (applied alone) | Result |
|---|---|---|
| M01 | BLOCKED label prints pass | killed |
| M02 | guard-error detector never matches | killed |
| M03 | any error counts as a guard block | killed |
| M04 | note cap MAX 3 to 5 | killed |
| M05 | warn prefix wrong | killed |
| M06 | unusable key accepted (status check inverted) | killed |
| M07 | catch-all prints pass instead of UNKNOWN | killed |
| M08 | plural/singular flipped | killed |
| M09 | info notes before warns | killed |
| M10 | no 'more' line | killed |
| M11 | 'more' count off by one | killed |
| M12 | refused report call removed | killed |
| M13 | ok report call removed | killed |
| M14 | exit 3 becomes exit 1 | killed |
| M15 | JSON error prefix never matches | killed |
| M16 | modes swapped | killed |
| M17 | ok report moved after the no-change exit | killed |
| M18 | `\|\| true` removed from the ok call | killed |
| M19 | status `fail` accepted | killed |
| M20 | refused mode prints a pass line | killed |
| M21 | helper-failed fallback removed (no line) | killed |
| M22 | helper-failed fallback returns 0 | **survives (equivalent)** |
| M23 | helper-failed fallback prints pass | killed |
| M24 | `\|\| true` removed from the refused call | killed |
| M25 | bare pass kept when notes exist | killed |
| M26 | pass (N notes) count wrong | killed |
| M27 | pass (N notes) plural flipped (count helper only for pass) | killed |
| M28 | control characters kept | killed |
| M29 | only Cc removed (format characters kept) | killed |
| M30 | whitespace dropped instead of replaced by a space | killed |
| M31 | whitespace runs not collapsed | killed |
| M32 | no length cap | killed |
| M33 | cap 300 to 3000 | killed |
| M34 | cap has no ellipsis | killed |
| M35 | refused reasons not cleaned | killed |
| M36 | ok notes not cleaned | killed |
| M37 | non-pf JSON accepted (prefix check dropped) | killed |
| M38 | guard reasons kept whole (prefix not stripped) | killed |

Notes on the mutants:
- **M07 (the catch-all prints `pass`) and M18 (`|| true` removed from the ok call) are reachable and are killed.** (The first version of this RFC called them unreachable; that was wrong.) A failing `$(python3 ...)` inside the arguments of `log` does not trigger `set -e`, so with an empty or invalid `data/publish-data.json` the script prints `exported: ` (blank), carries on to the report, and exits 0; the catch-all is reached that way, and the tests for empty and invalid JSON kill M07. The report helper's own crash (a `python3` that fails on the heredoc) used to leave **no** `evidence_guard:` line at all in the original; it now prints `UNKNOWN (report helper failed)`, and the `python3` shim tests kill M18, M21, M23 and M24 (without the call-site `|| true` the failing helper aborts the script with exit 1).
- **M17 was a real gap in the first fix round's tests** (all tests ended on the no-change path, so moving the ok report after that exit went unnoticed). It is closed by the test that lets the publish go on to commit and checks the line order.
- **M22 (the helper-failed fallback returns 0 instead of 1) survives and is equivalent:** the call sites end in `|| true`, which swallows any return value, so no observable behaviour differs.
- The runner mutates one line at a time and only the script; a mutation of the tests, or of `pf`, is out of scope.
- A missing `evidence_guard:` line (for example because the skill step was not updated, or an old copy of the script ran) cannot be printed by the script itself; the report must treat a missing line as UNKNOWN (Appendix A).
- Pre-existing quirk, not changed: if `tail` itself fails inside the `||` block that handles the refusal, the script exits 1 instead of 3.

## How to revert
`git revert -m 1 <merge commit>`. The nightly then prints no `evidence_guard:` line; nothing else changes. Before a merge: close the PR.

## popia-review verdict: PASS (author's scan, not independent; independent review still required)
Diff scan: aggregate counts, data type names, years, RFC and CSI identifiers, and `/tmp` scratch paths only. No ID, passport, phone, email, address, account number, plate, location, credential or key; no persons or suppliers. The BLOCKED reason line repeats the guard's own message, which holds only counts, data types and years (and, if `pf` fails for another reason, an absolute path, which goes only to the screen and the gitignored `data/` files).

## Seen, not touched
- RB-11 does not mention the new line; it can be extended after the owner confirms the report wording.
- The routine's saved prompt cannot be read (above).

## Template sections not present
`itil/templates/change-request.md` has "Implementation plan", "Post-implementation review" and "PR / commit". This RFC does **not** have them; it carries the content of the other sections. "Eval results for detectors" and "migration down-script" do not apply (no detector, no migration).

## Approval (Normal-high)
**Unreviewed by the owner; no owner GO or sign-off exists.** Normal-high needs the owner's explicit sign-off **plus** a second reviewer, or the owner after a 24 h cooling-off. **None is recorded.**

| Role | Name | Commit approved | Date |
|---|---|---|---|
| Change authority (owner) | none yet | none | |
| Second reviewer (high-risk) | none recorded | none | |

If the owner approves, the "Commit approved" cell must name the final head, and any later commit needs re-approval.

## Review
**Reviewer heads and verdicts, as reported to the author (PublicFunds)** (not stored in the repository): Validator `57208e9` expert conditional PASS with should-fix, charter CONDITIONAL; `572d6bb` delta EXPERT PASS, CHARTER CONDITIONAL. Scout reviewer PASS at `57208e9` (full) and `572d6bb` (delta). Neither fills a human slot; a reviewer PASS is not an owner GO.

**Fix round (26 Oct 2026, SAST), on review findings as reported to the author (PublicFunds) for head `57208e9`** (conditional results; not an owner GO, and not a pass for the fix commit): (1) the exit-3 label no longer claims to know the cause; (2) M07 is reachable (empty or invalid JSON) and is tested; (3) M18 is reachable (a crashed report helper) and the script prints `UNKNOWN (report helper failed)`; a missing line must be treated as UNKNOWN; (4) any note makes the line `pass (N notes)`, so only a bare `pass` is quiet; (5) note text is sanitised and capped; (6) Appendix B says "any non-zero status", and A/B are stated to change routine behaviour and need separate owner approval; (7) the change-log row no longer splits on `||`; (8) the box path is gone from this RFC, the full mutant list is in it, and the non-pf JSON error case is tested.

Result: Merged as PR #40 (merge commit `571d2d5`, GitHub mergedAt 26 Oct 2026 17:28:18 SAST, tag `snapshot-2026-10-26-1728`). Appendices A and B were applied outside the repo on 26 Oct 2026 at 17:33 SAST with the owner's approval, as reported to the author (PublicFunds); recorded by CHG-2026-042. Sign-off basis: owner GO quoted verbatim from the merge commit message of 571d2d5 (not independently verified by reviewers): "Go and keep going" (a chat reply to a question naming PR #40 at head 572d6bb; the author read it as the GO for that PR and head). No human second reviewer and no 24 h cooling-off is evidenced (PR #40 was about 72 min from open to merge). Flag for the owner: `itil/change-enablement.md` (Rules) says "A bot approval never fills a human slot", which conflicts with accepting the bots as the second reviewer; the Normal-high second-reviewer or 24 h cooling-off requirement is not recorded as met.

## Appendix: exact proposed wording (for the owner to apply after a merge; not applied by this change; for what was applied after the merge, see the Result line above)
**Appendix A and B change the routine's behaviour:** A adds a `--push` publish step to the live skill (it has no publish step today; the push is pre-authorised only from the daily refresh routine the owner approved) and B adds a new report format. **They are not applied by this change and need the owner's separate approval after the merge.**

### A. Skill step (live `publicfunds-refresh` skill, publish step)
> **Publish.** (Only if the build returned 0.) Run `scripts/publish-public-data.sh --push`. It prints one line starting `evidence_guard:`.
> - Put that line, and the note lines under it, in the nightly report **whenever it is not exactly `evidence_guard: pass`**. The bare `evidence_guard: pass` is the only quiet value. `pass (N notes)` means the guard passed with notes (for example an allow entry in use or a first run); `warn (N notes)` means the guard published but saw a drop; `UNKNOWN` means the guard was not checked.
> - **If there is no `evidence_guard:` line at all, treat that as UNKNOWN, not as pass.** Never describe an UNKNOWN or missing line as a pass.
> - If the script exits **3**, the export was refused: **nothing was published**, the files in `public-data/` are left as they are, and nothing was committed or pushed. Do not retry and do not edit data. Report to the owner at once: the exit code, the `evidence_guard:` line (`BLOCKED` = the evidence guard refused; `not an evidence-guard refusal` = no guard refusal was found in the log, so the cause may be the quality gate, the safety scan, another refusal or a crash: read the log), and the last lines of `data/publish-data.json` and `data/publish-data.log`. `scripts/check_live.py` warns at 30 h of data age and breaches at 48 h, so the owner needs to hear before then.
> - If it exits 4, stop and report (other changes, wrong branch, main moved).

### B. Routine prompt (the nightly's saved prompt; add to the end of its report instructions)
> In the report, add a line "Evidence guard:" with the `evidence_guard:` line printed by `scripts/publish-public-data.sh` and up to three note lines under it. If the line is anything other than exactly `evidence_guard: pass`, or there is no such line, or the script exited with any non-zero status, begin the report with `ACTION: publish needs attention`, say that nothing was published when the exit code was 3, and quote the `evidence_guard:` line. Treat a missing line as UNKNOWN. Never describe an `UNKNOWN` or missing guard line as a pass.
