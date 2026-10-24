# CHG-2026-032: Live site and data-age check script (CSI-036, script and runbook only)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-24 11:14 carte blanche, "go small, careful and verified" (11:26): one feature RFC from CSI-036 / CSI-020 / CSI-041 / CSI-044. **Owner GO: none. No merge GO is given** |
| Environment | DEV build and test; PROD effect after a merge GO is nil by itself (a script that nothing calls and a runbook entry); using it in the nightly is a later, separate step with its own GO (see "Proposed routine step") |
| Type | Normal, medium (new operational script; owner to confirm the tier). Not Normal-high: it publishes nothing, writes nothing, edits no workflow file, no pipeline code and no skill file |
| CIs affected | new `scripts/check_live.py`, new `tests/test_check_live.py`, `itil/knowledge/runbooks.md` (new RB-12), `itil/sla-slo.md` (SLO-PD-1 measurement cell), `itil/registers/csi-register.md` (CSI-036 row), `itil/registers/change-log.md` |
| Linked records | CSI-036, SLO-PD-1, RSK-024 (stale public data), RB-11, D-08 (external uptime check, not done) |
| Rollback | Close the PR unmerged. If merged: `git revert -m 1 <merge commit>`; nothing else depends on the script (git is the rollback; no .bkp files) |

## Problem
SLO-PD-1 says the published export is at most 48 hours old and RSK-024 lists "the export stops refreshing while the site still looks current". Today nothing measures either. The nightly reports that it pushed; it never looks at what the public site actually serves afterwards. Failure modes nobody would notice: the push succeeds but GitHub Pages does not rebuild (site stays on yesterday's data); the site is down or serves an error page; a data file on the site does not match the manifest's checksum; a missed nightly leaves the manifest older than 48 hours. The only existing check is a manual `curl` line in RB-11.

## What I checked first (nothing redone)
On origin/main 6abd695: no script, test or workflow checks the live site or manifest age (`rg` for SLO-PD-1: only the SLO text, the RB-11 manual `curl` line and the exporter's `freshness_slo` string). The dashboard shows a "older than our 48-hour target" pill to a human reader, but that is not a report. `.github/` has no workflow, and the token lacks `workflow` scope, so this is a script the routine can call, not a scheduled Action (CSI-043/CSI-020 CI parts stay blocked on that scope; D-08 external uptime stays open).

## Change
New `scripts/check_live.py` (Python standard library only, so no dependency or lockfile change; read-only GETs of public URLs; writes nothing; sends no cookies or credentials):

| Check | Passes when | Otherwise |
|---|---|---|
| `site.home` | `<site>/` answers HTTP 200 | BREACH |
| `site.app` | `<site>/apps/public-dashboard/` answers 200 and the page contains "PublicFunds" | BREACH |
| `site.manifest` | `<site>/public-data/v1/manifest.json` answers 200 (the body is read completely) and parses as a JSON object | BREACH (also for a truncated body, invalid JSON, a non-object) |
| `site.age` | `generated_at_sast` has a UTC offset and the age is at most `--max-age-hours` (default 48, SLO-PD-1) | BREACH; a timestamp more than 5 minutes in the future is also a BREACH (the clock or the file is wrong); WARN when over `--warn-age-hours` (default 30: one missed nightly shows before the SLO is breached) |
| `site.files` | 3 sample files named in the manifest (default `municipalities.json,departments.json,prices.json`) are served with the byte count and sha256 the manifest states; the manifest's `files` must be a list | BREACH, and the line says whether the byte count or the sha256 differs; a missing or non-list `files` is a BREACH on `site.files` |
| `raw.manifest`, `raw.age` | only with `--raw-url`: the same manifest from the git host (the SLO's measuring point) is reachable, within the SLO age, and has the same `build.id` as the site | WARN if the build differs (site behind or ahead of git: Pages lag or a failed Pages build) **or if either build id is missing** ("same build (None)" is not accepted as OK; I chose WARN rather than BREACH because freshness is judged separately by the age checks); BREACH if the raw manifest is unreachable or older than the SLO |
| `local.build` | only with `--expect-local <manifest.json>`: the site serves that file's `build.id`; polled every `--poll` seconds (default 30) for up to `--wait` seconds (default 0) so Pages has time to deploy. The age and sample-file checks then use the manifest fetched **after** the wait, not the one fetched before it | BREACH after the wait |

Each request is tried 3 times (`--retries`, 5 s apart) before it counts as failed, so one network blip is not a breach; network errors, 5xx and truncated bodies are retried, a 4xx is not. The 20 s timeout is **per socket read, not a total deadline** for a request (a slow server that keeps sending can take longer), so the worst case for one URL is about 3 x (timeout per read) plus the delays, and a run is not bounded in total. Output: one `[OK]`/`[WARN]`/`[BREACH]` line per check, then `RESULT: OK` / `RESULT: WARN (n)` / `RESULT: BREACH (n)`; `--json` prints the same as JSON; times are shown in SAST. Exit code 0 = OK or WARN only, 1 = at least one BREACH. The default site is the production host; every URL is an argument, so tests and previews use a local server.

**Hardening (added after review):**
- `--site` and `--raw-url` accept only `http` and `https` URLs with a host and no embedded credentials (`file://`, `ftp://` and the like are refused with exit code 2; `--site` also refuses a query string or fragment). **Redirects are followed** (urllib's limit of 10) but only to `http` or `https` URLs; a redirect to another scheme is refused before any connection is made and shows as a failed check (Python's own handler refuses `file://` but would follow `ftp://`, so the script's guard is what stops that; a test with a listening socket proves nothing connects).
- Anything that cannot be evaluated is a `[BREACH]` line for that check, a `RESULT:` line and exit 1, never a traceback: a manifest whose `files` is missing, null, a dict, a string or a list of junk; a truncated body (`IncompleteRead`); invalid JSON or non-UTF-8; an unexpected error inside a check.
- Flags are bounded and checked before anything is fetched (exit code 2): `--wait` 0 to 3600 s, `--poll` 1 to 600 s (`run_checks` also never polls faster than 0.05 s, so poll 0 cannot busy-loop), `--max-age-hours` and `--warn-age-hours` positive and finite with warn below max, `--retries` 0 to 10, `--retry-delay` 0 to 60 s, `--sample-files` at least one name (an empty or all-comma value is refused with exit code 2: it would otherwise be a silent OK with no file checked; I chose to reject rather than WARN). A value that is not a number, out of range, or a number too large to compare is an exit-2 message with no value in it.
- Printed URLs have no userinfo and no query string or fragment. **No rejected input is repeated in an error message.** Each URL rejection has one fixed text (`URL_ERRORS` in the script): an unparseable URL (a bad port, for example) gets a fixed message, not Python's own text, which would echo the port; a value with a colon but no scheme (`user:pw@host`, which Python reports as having the scheme "user") gets the fixed "only http and https URLs" message with no scheme named; a bad numeric value is just "not a number" or the allowed range; a flag that takes no value but is given one (`--json=X`, `--help=X`, `-h=X`) gets "this flag takes no value" instead of argparse's "ignored explicit argument 'X'"; stray arguments get a fixed "unrecognized arguments (not repeated here)".
- **What is guaranteed, exactly:** every exit-2 message the script prints is one of its own fixed texts (a regular expression of them, `_SAFE_ERROR`, is checked in `_Parser.error`), and anything else, including an argparse message nobody foresaw, is replaced by "invalid command line (details not shown: they could repeat what was typed)". So no part of a rejected URL, flag value, flag name or stray argument is printed back in an error. **Not covered:** the usage line and `--help` text (static); what is printed for *accepted* input (a URL without userinfo, query string or fragment, the `--sample-files` names that label the per-file lines, a `--expect-local` path in the "cannot read a build id from ..." BREACH line, and the host of an unreachable site); and failures outside the script's control (an interrupt, a Python crash).
- **Behaviour change: flag abbreviations are no longer accepted** (`allow_abbrev=False`): argparse by default lets `--sit` stand for `--site`, and its "ambiguous option" message repeats what was typed. `--sit` now gets the fixed "unrecognized arguments" error. Nothing in the repo uses an abbreviation (the runbook, the proposed routine step and the tests all use the full flag names); anyone typing one by hand has to spell the flag out.
- URLs must be plain ASCII (exit 2, fixed message that points to the punycode form `xn--...`; I chose rejecting over converting because it is the simpler rule and it is the user's own typed URL: Python's HTTP client cannot send a non-ASCII host or path, and before this change such a URL ended as a `[BREACH] the check itself failed (UnicodeEncodeError)` line and exit 1, which reads like an outage). A percent sign in the host (`http://h%20x/`, `%0a`, ...) is rejected the same way (exit 2): it is never a real host name here, and the lookup would also have been reported as an outage (I rejected every `%` in the host, not only encoded whitespace and control characters, because that is the simpler rule; an IPv6 zone id such as `[fe80::1%25eth0]` is refused too, which a public-site check does not need). A `%` in the path or query (`/a%20b`) is fine. A URL with whitespace or control characters is rejected (exit 2).
- Integer flags with an enormous number (an integer of 309 or more digits, either sign) are a bad command line (exit 2), not an `OverflowError` traceback with exit 1; one of more than 4300 digits (Python's own limit for reading an integer) now gets the same "at least ... and at most ..." message as any other out-of-range number, not "not a number" (it is a number). A digit separator (`1_0`, which Python's `int()` and `float()` accept) is refused as "not a number" for every numeric flag.
- A manifest that starts with a UTF-8 byte-order mark is read normally (the site manifest and an `--expect-local` file): browsers drop the mark when the dashboard reads the file, so a BOM does not break readers and must not be reported as an outage. Any other leading garbage (a second BOM, a UTF-16 mark, a space before the mark) is still "not valid JSON", a BREACH.

**Known limits (read before relying on it):**
- A checksum mismatch immediately after a publish can be a **false BREACH** while GitHub Pages is still deploying the new files (the manifest and a data file can come from different deploys). Mitigation: after a publish run `--expect-local <manifest> --wait <seconds>`, which waits for the site to serve the published build and then checks age and files against the manifest fetched after the wait. A BREACH that persists after the wait is real.
- The opener honours the `*_proxy` environment variables of the calling process (requests go through a proxy set there, except for hosts exempted by `no_proxy`). Response bodies and the total run time are **unbounded**: the timeout is per socket read, so a server that keeps sending slowly can hold a run open. Both are known limits: run the script under an overall timeout.
- A default run measures **the site**, not raw.githubusercontent.com, which SLO-PD-1 names as the measuring point. `--raw-url` adds that measurement (and the site/git-host comparison); without it the age check is the site's view, which can lag the git host.

`itil/knowledge/runbooks.md`: new **RB-12** (command, flags, exit codes, what to do on a BREACH: report it, do not re-publish blindly, SLO-PD-1 and RSK-024 links). `itil/sla-slo.md`: SLO-PD-1 measurement cell names the script. `itil/registers/csi-register.md`: CSI-036 status. Change-log row at the end.

## Proposed routine step (NOT applied; separate GO needed)
The nightly routine lives in the live skill file (`publicfunds-refresh`, outside git). Editing it needs the owner's separate GO and its own RFC (as CHG-2026-025 did); this RFC does not edit it and nothing in this PR can. Proposed text for that later step, after the push step:
> N. Check the live site: `python3 scripts/check_live.py --expect-local public-data/v1/manifest.json --raw-url <raw manifest URL from RB-11> --wait 600`. Put its `RESULT:` line and any `[BREACH]`/`[WARN]` lines in the report. A BREACH is reported as a breach, never as success. Do not re-run the publish to "fix" it; report and stop.

## Merge notes (change-log conflicts between #29, #31, #32, #33 and main)
**Why it conflicts.** Every change adds its own row at the end of `itil/registers/change-log.md`, and the RFC-records change (#30, merged as 6f1b992) also edited older rows, so the second and later merges stop with a conflict in that one file. **The web merge button cannot do this: it needs local merge commits and a normal push** (after the owner's quoted GO for each change; a reviewer PASS is never a GO). Nothing below pushes anything.

**Rule (no ids written into it).** Merge `change-log.md` row by row, keyed by the row's id, as a 3-way merge of the base (`:1:`), what you have (`:2:`) and what you are merging (`:3:`): a row only one side added or changed is kept (a new row goes into our file before the first larger id, else at the end); a row both sides have is taken from the side that changed it; rows nobody changed stay as they are. The script stops, and you resolve by hand, if both sides changed the same row, if either side changed any line that is not a table row, or if an id appears twice. It never counts rows and never names an id, so it works for any set of PRs, and it keeps rows that other PRs in the stack added. (A rule that drops the 030/031/032 rows, or picks a side by the number of merged rows, deletes the rows of any PR it does not name: that was the defect of the earlier text, found by review.)

```
export GIT_MERGE_AUTOEDIT=no                           # no editor: the merges run non-interactively
git fetch origin && git checkout -b merge-work origin/main    # one fresh merge-work per order; delete it afterwards
git merge --no-ff origin/<branch>                      # for each PR to merge, in any order (see the stack note below)
```
If a merge stops and `git diff --name-only --diff-filter=U` lists **only** `itil/registers/change-log.md`, run this, then `git add itil/registers/change-log.md && git commit --no-edit`. If any other file conflicts, stop and ask: nothing here covers it.
```
python3 - <<'PY'
import subprocess, sys
CL = "itil/registers/change-log.md"
def stage(n):
    return subprocess.run(["git", "show", f":{n}:{CL}"], capture_output=True, text=True, check=True).stdout.rstrip("\n").split("\n")
row = lambda l: l.startswith("| CHG-")
key = lambda l: l.split(" |")[0]
def parse(lines):
    rows = {key(l): l for l in lines if row(l)}
    assert len(rows) == sum(map(row, lines)), "duplicate id: resolve by hand"
    return rows, [l for l in lines if not row(l)]
(rb, nb), (ro, no), (rt, nt) = (parse(stage(n)) for n in (1, 2, 3))
if no != nt and nt != nb:
    sys.exit("they changed lines other than table rows: resolve by hand")
out = list(stage(2))  # start from our file, so the layout (and the prose between the rows) stays
for k in sorted(set(rt) - set(ro)):  # a row only they have goes before the first larger id, else after the last row
    rows_at = [i for i, l in enumerate(out) if row(l)]
    out.insert(next((i for i in rows_at if key(out[i]) > k), rows_at[-1] + 1), rt[k])
final = []
for l in out:
    if not row(l): final.append(l); continue
    k = key(l); b, o, t = rb.get(k), ro.get(k), rt.get(k)
    if o == t or t == b: v = o
    elif o == b: v = t
    else: sys.exit(f"both sides changed row {k}: resolve by hand")
    if v is not None: final.append(v)
open(CL, "w").write("\n".join(final) + "\n")
PY
```
**Stack note.** #33 (CHG-2026-034) was stacked on #32 (CHG-2026-033): merging #33 brought #32's commits with it, so #32 had to go first or together with it. Both have since been merged into main (917b8e8 and 75fbd63, 24 Oct 2026 17:41 and 17:42 SAST, while this text was being written); the text and checks below are the same for any set of branches, and what remains for this stack is #29 and #31 on main 75fbd63.

**Checks after each merge** (`CL=itil/registers/change-log.md`; list every branch you merged in the first line):
```
for r in origin/main origin/<each merged branch>; do git show $r:$CL; done | grep -o '^| CHG-2026-[0-9]*' | sort -u | diff - <(grep -o '^| CHG-2026-[0-9]*' $CL | sort)   # prints nothing: every id of every branch is there
grep -o '^| CHG-2026-[0-9]*' $CL | sort | uniq -d     # prints nothing (no duplicate id)
grep '^| CHG-' $CL | grep -v ' |$'                    # prints nothing (every row ends " |"; the |---| separator starts "|-", so "| CHG-" does not select it)
grep -n '^<<<<<<<\|^>>>>>>>\|^=======' $CL           # prints nothing (no conflict markers)
tail -c1 $CL | od -An -c                              # \n (the file ends with a newline)
env -u THUSA_ROOT uv run pytest -q                    # the expected counts are in the Result section of the RFC; run it after the last merge
```
**After merging, the status cells still say the PRs are open.** The change-log rows of the merged changes (for example 030, 031, 032) and the CSI register rows (CSI-036 for #31, CSI-051 for #29) keep reading "PR open" / "awaiting review" / "not merged"; the merge does not touch them. A follow-up status commit (its own PR and its own GO) sets them to merged, with the merge commit.

**What was verified** (details in the Result section): the trial merges in the Result section (every valid order of #29, #31, #32 and #33 on main 6f1b992); the resolver was run only on those combinations, not on any other, and not against a different main.

No helper script is added (nothing outside this PR's scope): the procedure is text, here and in the bodies of #29 and #31.

## Not changed
`thusa/`, `config/`, `public-data/` (no file written, no nightly run), `scripts/publish-public-data.sh`, the dashboard, the live skill file, the working data root outside git, CI files, dependencies. No external uptime service (D-08) is signed up for.

## Data identical before/after
Yes. No data file is touched.

## Tests
New `tests/test_check_live.py` (282 tests at this head; 232 at 53dffa4, the fourth review round; 155 at 8292fc8; 113 at 56f2f8d; 100 at facc3f8; 21 in the first version) runs the script against a local HTTP server that serves fixture manifests (no network): healthy site, stale manifest, 30 to 48 hour warning, future timestamp, 404 manifest, invalid JSON, unreachable host, 500 with retry that then succeeds, `--expect-local` match, mismatch with `--wait 0`, a build that appears during the wait, raw/site differing, no `--raw-url`, and the exit codes through `main()`. Added after review: `main()` with no flags at 29 h (OK), 31 h (WARN) and 49 h (BREACH); strict boundaries at exactly 30 h (OK) and 48 h (WARN, not BREACH); the sha256 check and the byte-count check each proved necessary by its own test (same-length corrupt body; right sha256 with a wrong byte count); the exact SAST string for a manifest written in UTC, UTC-5 and UTC+2; `files` null, dict, string, number, list of junk and missing; a truncated body (manifest and data file, and that it is retried); other unparseable manifests; `file://`, `ftp://` and other schemes refused for `--site`, `--raw-url`, `run_checks`, `fetch` and a redirect; a followed http redirect; 23 nonsense flag values; poll 0 not busy-looping; the age and file checks re-run on the manifest fetched after `--wait` (the manifest and the data file served before and after the wait differ in age, length and sha256, so using the pre-wait manifest for either check fails the test); an `ftp://` redirect is refused without any connection (listening socket); a bad port or unparseable URL for `--site` and `--raw-url` gets a fixed message with no part of the URL; an empty or all-comma `--sample-files` exits 2 and fetches nothing, and a single sample file works; a scheme-less `user:pw@host`, malformed and whitespace URLs, bad numeric values, stray and abbreviated arguments never repeat any part of the input (fixed marker string, for `--site`, `--raw-url`, `validate_url`, `fetch`, `run_checks` and `main`), plus a seeded fuzz of 1500 generated URLs; missing build ids on either side are not OK; no userinfo or query string is ever printed. Added in the fourth round (after the re-check of 8292fc8): a value given to a flag that takes none (`--json=X`, a second `--json=X`, `--help=X`, `-h=X`, empty values and combinations with other flags: 12 forms) is refused with "this flag takes no value" and never echoed, while a plain `--help` and `-h` still print the usage and exit 0 (and `-hX` answers with the same static help); every exit-2 message must be on the fixed list, and `_Parser.error` is called directly with messages the script never produces to prove they are replaced, not printed; every fixed URL message is reachable for both `--site` and `--raw-url`; `--retries` and `--retry-delay` with 308, 309, 400 and 5000 digits and the signs `-`, `+` and none (exit 2, no traceback); the `_num` converter itself raises only `ArgumentTypeError`; non-ASCII URLs (host, path) exit 2 and are not a BREACH, a punycode host is accepted, `%` in the host (`%20`, `%0a`, an IPv6 zone id) exits 2 and `%` in a path or query is fine; the printed site is the normalised safe form, not the typed string (an upper-case host is printed lower-case); a manifest with a UTF-8 BOM is read for the site and for `--expect-local`, and other leading garbage is still a BREACH; 11 abbreviated flags are refused and every documented flag is still accepted in full; the URL fuzz now also uses non-ASCII and percent forms, and a second seeded fuzz (600 generated command lines: all flags in many forms, `--x=MARK`, `-hMARK`, abbreviations, with a rejected value inserted so no fetch happens) must never print the marker, never show a traceback and exit 2 in more than 300 cases. Also run: `uv run pytest -q` with `THUSA_ROOT` unset and with a data copy; one real run against the production site (read-only, output kept with the review evidence, not in the repo). Added in the fifth round (after Scout's re-check of 53dffa4): a digit separator in any numeric flag (`1_0`, `1__0`, `_1`, `1_`, `1_0.5`, `1e1_0`, `0x1_0`, `+1_0`, for all 6 flags: 48 tests) is "not a number"; plain non-numbers (`abc`, `1.5.5`, `x1`, `1 2`) get the converter's own "not a number" text and not the generic fallback (this test is what lets the numeric-echo mutation be seen with the fallback on); the converter itself on `1_0`, on 4300, 4301 and 5000-digit integers (the "at most" message) and on a long run of digits ending in a letter ("not a number"); the 309/400/5000-digit test now requires the "at most" message and no "not a number". Results below.

## POPIA review
PASS by me (PublicFunds, the author), which is not an independent review. The independent popia-review is Scout's (an independent reviewer, not the author): Scout passed 56f2f8d and 8292fc8 with no personal information found (reported to me), and re-checked 53dffa4 (reported to me as a PASS; I have no statement that says which checks that covered, so I do not count it as a popia-review of 53dffa4). Each PASS covers only the head it names. No Validator popia-review is recorded here. These are reviewer PASSes, not an owner GO. They do not cover this head (the merge of main 6f1b992, the digit-separator and long-integer changes to the numeric flags, the merge procedure text, tests and wording): **an independent popia-review (Scout) of this head is requested, not done.** The new code prints no more than before (a rejected number gets the same fixed text) and reads no new input. The script reads only public, non-personal files (home page, the data manifest and three public data files) from our own site and the git host, stores nothing, sends no credentials or cookies and no identifying header beyond a fixed User-Agent `publicfunds-check/1`. No personal information, IDs, contacts or accounts in code, tests or this record.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Each PASS covers only the head it names. 9179fbc: reviewers passed with a small fix list (applied in facc3f8). facc3f8: Validator re-checked expert and charter (PASS, per Validator's report); Scout shadow/drift and the independent POPIA review (PASS). 56f2f8d: Validator passed expert and charter with should-fixes (per Validator's report); Scout passed shadow/drift and POPIA. 8292fc8: Validator passed expert and charter (per Validator's report) and Scout passed shadow/drift and the independent POPIA review, each with small remaining items. 53dffa4: Scout re-checked it (as reported to me) and gave corrected mutation counts, which are applied in the table below; no Validator re-check of 53dffa4 is recorded here. **This head has had no review**: Validator's expert and charter re-check and Scout's shadow/drift and independent POPIA re-check are requested, not done. These are reviewer PASSes, never an owner GO. Merge needs the owner's quoted GO for CHG-2026-032; using the script in the nightly needs a second, separate GO.

## Result (2026-10-24, SAST)
Built and tested in DEV only (fresh clone of origin/main 6abd695, own uv venv). The change has not been merged, nothing in PROD is changed, and nothing calls the script.
- `uv run pytest`, `THUSA_ROOT` unset: **549 passed, 61 skipped** on main 75fbd63 merged into this branch (main 75fbd63 is 267 passed, 61 skipped; +282 new tests; on the earlier main 6f1b992 it was 478 passed, 196 + 282; 53dffa4 had 428 passed with 232 new tests; 8292fc8 had 351 passed, 61 skipped with 155 new tests, 56f2f8d had 309 passed with 113, facc3f8 296 with 100, 9179fbc 217 with 21). With a data copy the first version had 277 passed, 1 skipped (main 256 passed, 1 skipped); that run was **not repeated** for the follow-ups (no data-dependent code or test changed).
- Mutation check, re-run on this head by me (282 tests in the file; **35 rows, 40 runs**: 33 rows and 38 runs in the earlier table, plus 2 new rows for this round, and 5 rows also run with the whitelist fallback off). Each mutation was applied alone to a copy of `scripts/check_live.py`, then `pytest tests/test_check_live.py` was run on a copy of the tree and the file restored; the rows were measured at 281 tests, and the two rows that the one test added afterwards can change were re-measured at 282. Several of the error-message defences are layered (the type converters, the fixed `ap.error`, and the `_Parser.error` whitelist behind them), so a mutation of an inner layer can be hidden by an outer one; those rows are also run with the whitelist fallback switched off, which is the only way to see that the inner layer is tested on its own. Failing tests per mutation (a parametrized test counts once per case):

| # | Mutation | Tests failing | Earlier table |
|---|---|---|---|
| 1 | max-age comparison `>` to `>=` | 2 |  |
| 2 | warn comparison `>` to `>=` | 1 |  |
| 3 | breach threshold multiplied by 10 | 7 |  |
| 4 | sha256 check removed | 1 |  |
| 5 | byte-count check removed | 1 |  |
| 6 | `file` added to the allowed schemes | 3 |  |
| 7 | manifest `files` list check removed | 4 |  |
| 8 | poll floor removed | 1 |  |
| 9 | post-wait manifest not used at all (the age and file checks use the pre-wait manifest) | 2 | was 1 |
| 10 | pre-wait manifest used for the file checks | 1 |  |
| 11 | pre-wait manifest used for the age check | 1 |  |
| 12 | missing build id treated as the same build | 1 |  |
| 13 | printed URL not stripped (`shown = site`) | 1 |  |
| 14 | redirect scheme guard removed | 1 |  |
| 15 | redirect guard replaced by urllib's default opener | 1 |  |
| 16 | Python's parser message passed through in the URL error | 10 |  |
| 17 | empty `--sample-files` accepted | 5 |  |
| 18 | scheme named in the scheme error | 6 (8 with fallback off) | was 7 (10) |
| 19 | bad numeric flag value echoed (both converter messages) | 49 (8 with fallback off) | was 3 (8); see note 3 |
| 20 | unrecognised arguments left to argparse | 11 (13 with fallback off) |  |
| 21 | flag abbreviations allowed again | 10 (13 with fallback off) |  |
| 22 | whitespace and control-character check removed | 11 |  |
| 23 | non-ASCII check removed | 11 |  |
| 24 | `%`-in-host check removed | 13 |  |
| 25 | `%` allowed in an IPv6 zone only (partial check) | 1 | was 2 |
| 26 | huge-integer guard removed (`math.isfinite` on an int) | 8 | was 7 |
| 27 | BOM not stripped (site manifest) | 1 |  |
| 28 | BOM not stripped (`--expect-local` file) | 1 |  |
| 29 | `_Parser` class removed (plain argparse) | 13 |  |
| 30 | "ignored explicit argument" message not replaced | 12 (14 with fallback off) |  |
| 31 | no-value message: the typed value appended to a fixed text (fallback off) | 11 | was 14; see note 4. The whole original message kept (fallback off) is the 14 in the row above |
| 32 | whitelist fallback switched off, alone | 1 |  |
| 33 | whitelist uses `search` instead of `fullmatch` | 1 |  |
| 34 | digit-separator (`_`) check removed (new row) | 23 |  |
| 35 | long-integer range branch removed (new row) | 4 |  |

  Every mutation is caught. Corrections to the earlier text (the first five are Scout's re-check of 53dffa4, which I re-ran rather than copied):
  1. Row 9 (post-wait manifest not used at all) was claimed as 1, measured 2. Row 18 (scheme echo) was claimed as 7 and 10 with the fallback off, measured 6 and 8. Row 25 (`%` allowed in an IPv6 zone only) was claimed as 2, measured 1. Row 26 (huge-integer guard) is 8 now, not 7 (I did not look into why).
  2. The earlier text said "38 mutations" in one place and "33 rows" in another; the count is rows and runs: 33 rows and 38 runs then, **35 rows and 40 runs** now.
  3. Row 19 (numeric echo): the earlier "3 (8 with fallback off)" cannot be reproduced for the reason below: most likely those 3 were the 5000-digit integer cases, which took the "not a number" path before this round and now take the range message (an inference: I could not re-run the old mutation). A bad number that is not an integer (`abc`) was not seen by any test with the fallback on, because the fallback hides a converter that echoes: a mutant on that path alone survived all 281 tests (8 failures only with the fallback off). The test of plain non-numbers added this round kills it (1 test with the fallback on, 8 with it off). The 49 is the sum of the two converter messages; 48 of those failures are the one parametrized digit-separator test.
  4. Row 31: the earlier 14 is only valid if the whole original argparse message is kept (the "whole message" mutant, fallback off, row 30 above). If only the typed value is appended to the fixed text, 11 tests fail. I now list both.
  5. The mutation definitions of the earlier table were written by me and are not kept (the runner was deleted), so these are reconstructed from the code and the old table's names, not a re-run of the same files; I cannot say why the earlier numbers 1, 7, 2 were wrong.
  6. (From an earlier round.) The printed-URL mutation (`shown = site`) **survived all 155 tests at 8292fc8**: `validate_url` already rejects userinfo, query and fragment for `--site`, so the rebuilt form differs from the typed one only in normalisation, and nothing tested the printed form. A test of the printed form (a host typed in upper case must print in lower case) kills it. An earlier run of the abbreviation mutation matched two places (a comment says the same words) and was repeated with the exact text.
- Trial merges of the change-log (24 Oct 2026, about 17:40 SAST), in a scratch worktree on main **6f1b992** (the base named in the brief; main has moved since, see below), `GIT_MERGE_AUTOEDIT=no`, a fresh merge-work for every order, with the resolver text above extracted from this file (not retyped): #29 at 135f2b8, #31 at 0c7095e, #32 at a4f99f4, #33 at bc35cd8 (the PR heads at that time; #32 and #33 are other people's branches, and these were the commits merged later). All 12 orders in which #33 comes after #32 (#33 contains #32's commits; #33 before #32 is not a valid order) ended in the same tree. In each order exactly one merge stopped, always only on `change-log.md`, and the resolver text fixed it (8 times at #31, 4 times at #33); the other merges had no conflict. In every order: no duplicate id, no row without the closing ` |`, no conflict markers, the file ends with a newline, every id of main and of the four branches is in the result, and every change-log row of each branch is in the result word for word. Full suite on the result of one order: **564 passed, 61 skipped** (main 196 + #29 15 + #31 282 + #32 and #33 71). In the same period #32 and #33 were merged into main as 75fbd63, so I merged main 75fbd63 into #29 (6a8594d, no conflict) and into #31 (the change-log conflicted, was resolved with the text above; only that file conflicted); full suites after those merges are in the PR bodies. **Not verified:** #34 (CHG-2026-035) and any other branch; a main other than 6f1b992 for the 12 orders (for 75fbd63 only #29 and #31 were tried, see the PR bodies); the orders with #33 before #32; that any owner GO covers more than the change it names; the visible site after a merge (nothing was published).
- One real read-only run against the production site (output kept with the review evidence, not in the repo): all checks OK, data 8.4 h old (generated 2026-10-24 03:05 SAST), build `B20261024T010413Z` identical on the site, the git host and the local manifest; three sample files match their checksums. A forced-threshold run and an unreachable-host run (also kept with the review evidence) show the BREACH lines and exit code 1.
- Nothing visible changes on the site, so there are no UI screenshots; the text output above is the evidence.

Awaiting review of this head; no merge GO.
