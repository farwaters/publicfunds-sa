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
   | key present, status `pass`, no `warn` notes | `evidence_guard: pass` |
   | key present, one or more `warn` notes | `evidence_guard: warn (N note[s])` |
   | export refused (exit 3) and the `pf` error starts with `evidence guard` (a BLOCK, or the guard could not run) | `evidence_guard: BLOCKED (exit 3; nothing published, published files left as they are)` |
   | export refused (exit 3) for another reason (quality gate, safety scan, no warehouse) | `evidence_guard: not the cause (exit 3 came from the quality gate, the safety scan or another export refusal; see data/publish-data.log)` |
   | key missing, not an object, status not `pass`, `notes` not a list, file unreadable | `evidence_guard: UNKNOWN (...; treat as not checked)`: never shown as pass |

   After the line come up to 3 note lines (`evidence_guard:   <note>`; `warn` notes first, then `note:`/`allowed:` notes) and, if more, `evidence_guard:   ... and K more (data/publish-data.json, data/publish-data.log)`. The BLOCKED line is followed by the refusal reason. The exit-3 case is read from the log because on exit 3 `pf` writes no `evidence_guard` key (the export raised before it returned).
2. **It can never change what is published or the exit code.** The helper only reads two ignored files in `data/` and prints; it is called as `guard_report ... || true`, and it has a catch-all that prints UNKNOWN. The `uv run pf publish-data ... || { ...; exit 3; }` line keeps its exit 3; `exit 4`, the no-change exit 0 and the timestamp-only exit 0 are untouched. No new Python module: the logic is an inline `python3 -` heredoc in the script, so the tests run the real script.
3. **"BLOCKED" is printed only when the guard was the cause.** The first design would have called any exit 3 a guard block. The quality gate runs before the guard in `export()`, so a quality-gate exit 3 prints `not the cause`.
4. **Skill (repo copy only):** step 4 of `docs/bot/skills/publicfunds-refresh/SKILL.md` now says a non-`pass` `evidence_guard:` line and an exit 3 must be reported to the owner, and says what exit 3 means. The user's own skill and the routine's saved prompt are **not** touched by this change; wording for both is in the Appendix.

## Scope: what this change does not do
- No change to `thusa/*`, the guard, its thresholds, the allow list, the published files, any exit code, or the quality gate.
- No edit outside the repo: not the live skill, not the routine, not memory, not the template. The nightly does not show the new line until the skill step and the routine prompt are updated by the owner after a merge (Appendix).
- No change to RB-11 (it already says exit 3 = export refused; read the files).
- The pre-existing exit 3 / `tail` quirk below is noted and not changed.

## What the nightly does on exit 3 (verified from the repo and the box, with the limit stated)
- **In the script (`set -euo pipefail`):** the `pf publish-data` line is `uv run pf publish-data > data/publish-data.json 2> data/publish-data.log || { tail -n 5 data/publish-data.json data/publish-data.log >&2; log "export refused (see data/publish-data.*)"; exit 3; }`. So on a `pf` failure the script shows the last 5 lines of each file on stderr, prints `export refused`, and **exits 3 before any git step: nothing is staged, committed or pushed, and the files in `public-data/` are left as they are.** Checked on a scratch run (below): `git status` clean, no new commit, `public-data/` unchanged.
- **In `pf` (`thusa/review/cli.py`, `cmd_publish_data`):** `UnsafeExport` is turned into `CliError("public data not written: <reason>", 3)`; `main()` prints `{"error": "<message>", "exit_code": 3}` as JSON on stderr and returns 3. The same exit 3 is used for: no warehouse, the quality gate (`quality gate: the current build failed N data-quality check(s)`), the evidence guard (`evidence guard: BLOCK ...` or `evidence guard could not run ...`) and the safety scan. The quality gate runs before the guard.
- **Exit 4** is a different refusal (other staged files, wrong branch, main moved) and is already covered by the skill.
- **Documentation:** RB-11 says "Exit 3 = export refused (quality gate or safety scan: read data/publish-data.json / .log)". The repo copy of the skill covered only exit 4 (before this change). RB-12: `scripts/check_live.py` warns at 30 h of data age and breaches at 48 h, so a missing publish becomes a breach only after two nights.
- **Not visible, so not known: what the nightly routine does or reports when the script exits 3.** The live skill on the box (`/home/box/agent-data/workflows/publicfunds-refresh/SKILL.md`, read only, not changed) has steps 0 to 5 and **no publish step**: the publishing is done by the routine's own saved prompt, which cannot be read from the repo or the box (CHG-2026-025 records the same, and the routine's own data commits are in the reflog). It is therefore **not verified** whether the routine reports an exit 3 to the owner, retries, or stops. This replaces the earlier wording of CHG-2026-040 ("not verified: what the nightly routine does ... the routine and skill were not read"): the skill was read for this RFC (no publish step); the routine prompt still cannot be read. The Appendix wording is written so that it works whatever the routine does today.
- **Last real nightly (26 Oct 2026 03:10 SAST, `f3801f0`):** `data/publish-data.json` has `"evidence_guard": {"status": "pass", "notes": []}` and `data/publish-data.log` is empty. The guard has run in production once since it was merged and passed.
- **Pre-existing quirk, not changed:** inside the `||` block, if `tail` itself fails (for example `data/publish-data.log` was deleted after the redirect created it), `set -e` ends the script with exit 1 and not 3. Not reachable in normal running; recorded so nobody expects exit 3 from every failure.

## Risk
- **Touches the publishing script** (the reason for Normal-high). Mitigations: the helper is read-only, is always followed by `|| true`, prints to stdout only, and runs after `pf` has finished; tests assert no commit and no `public-data/` change in every case and that exit codes are unchanged, including a `pf` failure with another code (rc 7 gives exit 3 as before); the dry run below shows byte-identical output.
- **Extra stdout lines.** A caller that parses the script's stdout would see new lines starting `evidence_guard:`. The only known caller is the nightly routine (prompt not visible); the existing lines (`exported:`, `committed`, etc.) are unchanged and in the same order, with the new lines inserted after `exported:` (or before `export refused`).
- **A wrong label would mislead the owner.** "BLOCKED" needs the JSON error to start with `evidence guard`; anything unreadable is UNKNOWN, never pass. Tested.
- **The log format is a dependency.** The refused path reads the `{"error": ...}` JSON that `main()` prints. If that format changes the line falls back to `not the cause`, which is wrong for a BLOCK; a test replays the real `pf publish-data` output for a block, so a format change fails a test.
- **The line is only seen if the skill step and the routine prompt are updated** (Appendix). Until then nothing changes in the nightly report.
- **POPIA:** the line prints aggregate counts, data type names and years from the guard notes. No names, amounts, identifiers or suppliers.

## Tests (evidence)
- New `tests/test_publish_guard_line.py`: **15 tests** (11 functions; one parametrised over 5 missing/unusable-key cases). Each runs the **real script** in a scratch git repo with a stub `uv` that replays stdout, stderr and the exit code of `pf publish-data`, and asserts: no commit, no change in `public-data/`, and the exit code. Cases: pass (one line, exit 0); warn with 5 notes (the count, 3 notes, `... and 2 more`); one warn is singular and warns come before info notes; info notes only is still pass; **block** (exit 3, `BLOCKED`, the reason shown, exit stays 3); the guard "could not run" is also BLOCKED; a quality-gate exit 3 is `not the cause`; odd stderr with exit 3 still exits 3; **missing key**, `null`, not an object, bad status, `notes` not a list (UNKNOWN, exit 0, never pass); other exit codes unchanged; and one replay of real `pf_main(["publish-data", ...])` output on the synthetic warehouse for a first-run pass (with its note), a warn (previous file padded so the drop is over 10 %) and a block (output folder byte-identical).
- **Full suite** (`env -u THUSA_ROOT uv run --frozen pytest -q`): see the PR body for the counts at the head sha (main `f3801f0`: 699 passed, 61 skipped).
- **Dry run, 26 Oct 2026 (SAST), scratch copies only.** A copy of the nightly warehouse (`/workspace/publicfunds/data/thusa.duckdb`, built 03:10) in a scratch root, two scratch clones at `f3801f0` (one with the old script, one with the new), a `uv` shim that runs this branch's `pf publish-data` against the scratch warehouse and the clone's `public-data/v1`. The real checkout, warehouse and `public-data/` were not touched.
  - Old script: `exported: 4361785 bytes, 19 files`, `only timestamps changed; not committed`, exit 0. New script: the same plus `evidence_guard: pass`, exit 0. **`diff -r` of the two `public-data/` trees: identical; both identical to the committed `f3801f0` tree** (19 files, `git diff` empty).
  - Before the script's own timestamp-only restore, a direct `pf publish-data` into a copy of the committed folder differs from it in **one file, `manifest.json`, in one line (`generated_at_sast`)**; `coverage.json` and the other 17 files are byte-identical.
  - **Warn run** (scratch warehouse with 100 of the 247 opinion 2023 cells set missing): exit 0, `evidence_guard: warn (1 note)` and `evidence_guard:   warn: audit_opinion 2023: 247 -> 147 (40.5% fewer)`; the publish itself behaves as before (it commits in the scratch clone).
  - **Block run** (all 247 emptied): exit 3, `evidence_guard: BLOCKED (exit 3; nothing published, published files left as they are)` and the reason, `export refused`; `git status` clean apart from the script, no commit, `public-data/` unchanged.
  - A refusal that is not the guard (a scratch root with no warehouse) printed `evidence_guard: not the cause (...)`, exit 3.

### Mutation tests
20 mutants of `scripts/publish-public-data.sh`, each applied alone and `tests/test_publish_guard_line.py` run with `-x`, the script restored after each. **The runner is a scratch script outside the repo (`/tmp/work/mut41.py`); it is not committed**, so this list is the record. **18 killed, 2 survive (both reasoned to be unreachable, not missing tests).**

| Mutants | Result |
|---|---|
| M01 BLOCKED label becomes pass; M02 guard-error detector never matches; M03 any error counts as a guard block; M20 refused mode reports a pass line | killed |
| M04 note cap 3 to 5; M10 no "more" line; M11 "more" count off by one; M09 info notes before warns | killed |
| M05 wrong warn prefix; M08 plural flipped; M06 unusable key accepted as pass; M19 status `fail` accepted | killed |
| M12 refused report call removed; M13 ok report call removed; M17 ok report moved after the no-change exit; M16 modes swapped; M15 JSON error prefix never matches | killed |
| M14 exit 3 becomes exit 1 | killed |
| M07 the catch-all prints `pass` instead of UNKNOWN | **survives** |
| M18 `|| true` removed from the ok call | **survives** |

M07 and M18 are defensive code with no input that reaches them: the preceding `exported:` line (which reads the same JSON) fails first, and the helper's own try/except swallows every error, so the catch-all and the `|| true` on the ok call cannot be triggered through the script. They are kept as a second guard. A test that tried to reach the catch-all by deleting the log failed for the pre-existing `tail` reason above (exit 1) and was removed.

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
**No review of this change exists yet.** Results may be added later only as reported to the author (PublicFunds), each for an exact commit. A reviewer PASS is not an owner GO.

Result: PR open, not merged; no owner GO; no review.

## Appendix: exact proposed wording (for the owner to apply after a merge; not applied by this change)

### A. Skill step (live `publicfunds-refresh` skill, publish step)
> **Publish.** (Only if the build returned 0.) Run `scripts/publish-public-data.sh --push`. It prints one line starting `evidence_guard:`.
> - Put that line, and the note lines under it, in the nightly report **whenever it is not `evidence_guard: pass`**. `warn (N notes)` means the guard published but saw a drop; `UNKNOWN` means the guard was not checked and is not a pass.
> - If the script exits **3**, the export was refused: **nothing was published**, the files in `public-data/` are left as they are, and nothing was committed or pushed. Do not retry and do not edit data. Report to the owner at once: the exit code, the `evidence_guard:` line (`BLOCKED` = the evidence guard refused; `not the cause` = the quality gate or the safety scan refused), and the last lines of `data/publish-data.json` and `data/publish-data.log`. `scripts/check_live.py` warns at 30 h of data age and breaches at 48 h, so the owner needs to hear before then.
> - If it exits 4, stop and report (other changes, wrong branch, main moved).

### B. Routine prompt (the nightly's saved prompt; add to the end of its report instructions)
> In the report, add a line "Evidence guard:" with the `evidence_guard:` line printed by `scripts/publish-public-data.sh` and up to three note lines under it. If the line is not `pass`, or the script exited 3 or 4, begin the report with `ACTION: publish needs attention`, say that nothing was published when the exit code was 3, and quote the `evidence_guard:` line. Never describe an `UNKNOWN` guard line as a pass.
