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
- `--retries` and `--retry-delay` with an enormous number (an integer of 309 or more digits, either sign) are a bad command line (exit 2, "at most" message), not an `OverflowError` traceback with exit 1.
- A manifest that starts with a UTF-8 byte-order mark is read normally (the site manifest and an `--expect-local` file): browsers drop the mark when the dashboard reads the file, so a BOM does not break readers and must not be reported as an outage. Any other leading garbage (a second BOM, a UTF-16 mark, a space before the mark) is still "not valid JSON", a BREACH.

**Known limits (read before relying on it):**
- A checksum mismatch immediately after a publish can be a **false BREACH** while GitHub Pages is still deploying the new files (the manifest and a data file can come from different deploys). Mitigation: after a publish run `--expect-local <manifest> --wait <seconds>`, which waits for the site to serve the published build and then checks age and files against the manifest fetched after the wait. A BREACH that persists after the wait is real.
- The opener honours the `*_proxy` environment variables of the calling process (requests go through a proxy set there, except for hosts exempted by `no_proxy`). Response bodies and the total run time are **unbounded**: the timeout is per socket read, so a server that keeps sending slowly can hold a run open. Both are known limits: run the script under an overall timeout.
- A default run measures **the site**, not raw.githubusercontent.com, which SLO-PD-1 names as the measuring point. `--raw-url` adds that measurement (and the site/git-host comparison); without it the age check is the site's view, which can lag the git host.

`itil/knowledge/runbooks.md`: new **RB-12** (command, flags, exit codes, what to do on a BREACH: report it, do not re-publish blindly, SLO-PD-1 and RSK-024 links). `itil/sla-slo.md`: SLO-PD-1 measurement cell names the script. `itil/registers/csi-register.md`: CSI-036 status. Change-log row at the end.

## Proposed routine step (NOT applied; separate GO needed)
The nightly routine lives in the live skill file (`publicfunds-refresh`, outside git). Editing it needs the owner's separate GO and its own RFC (as CHG-2026-025 did); this RFC does not edit it and nothing in this PR can. Proposed text for that later step, after the push step:
> N. Check the live site: `python3 scripts/check_live.py --expect-local public-data/v1/manifest.json --raw-url <raw manifest URL from RB-11> --wait 600`. Put its `RESULT:` line and any `[BREACH]`/`[WARN]` lines in the report. A BREACH is reported as a breach, never as success. Do not re-run the publish to "fix" it; report and stop.

## Merge notes (change-log conflicts with #29 and #30)
**Why it conflicts.** #29 (CHG-2026-030), #30 (CHG-2026-031) and #31 (CHG-2026-032) each edit `itil/registers/change-log.md` (new row at the end, and #30 also edits rows 019-029), so the second and third merge stop with a conflict in that one file. **The web merge button cannot do this: it needs local merge commits and a normal push** (after the owner's quoted GO for each change; a reviewer PASS is never a GO). Nothing below pushes anything.

**Any order gives the same result.** Resolving with the script below, all six orders of #29/#30/#31 end in an identical tree (checked with `git rev-parse HEAD^{tree}`, and the full suite run on the result). So the order is the owner's choice, and any subset (for example only #29 and #31) works the same way.

```
git fetch origin && git checkout -b merge-work origin/main
git merge --no-ff origin/chg-2026-030-fuel-notes      # #29; then the same for origin/chg-2026-031-rfc-records (#30) and origin/chg-2026-032-live-check (#31), in any order
```
If a merge stops and `git diff --name-only --diff-filter=U` lists **only** `itil/registers/change-log.md`, run this, then `git add itil/registers/change-log.md && git commit --no-edit`. (If any other file conflicts, stop and ask: nothing here covers it.) It reads the two sides from the index (`:2:` = what you have, `:3:` = what you are merging, so it does not matter which PR comes first), takes the side that carries #30's edited "Merged PR #..." rows as the base, drops the 030/031/032 rows from it and appends those three rows (taken from whichever side has them) in id order at the end:
```
python3 - <<'PY'
import subprocess
CL = "itil/registers/change-log.md"
def stage(n):
    return subprocess.run(["git", "show", f":{n}:{CL}"], capture_output=True, text=True, check=True).stdout.rstrip("\n").split("\n")
ours, theirs = stage(2), stage(3)
merged = lambda L: sum(l.startswith("| CHG-") and "| Merged PR #" in l for l in L)
base = theirs if merged(theirs) > merged(ours) else ours
mine = lambda l: l.startswith(("| CHG-2026-030 |", "| CHG-2026-031 |", "| CHG-2026-032 |"))
rows = {l[:15]: l for l in ours + theirs if mine(l)}
out = [l for l in base if not mine(l)] + [rows[k] for k in sorted(rows)]
open(CL, "w").write("\n".join(out) + "\n")
PY
```
**Checks after each merge** (`CL=itil/registers/change-log.md`):
```
grep -o '^| CHG-2026-[0-9]*' $CL | sort | uniq -d     # prints nothing (no duplicate id)
grep -o '^| CHG-2026-[0-9]*' $CL | tail -4            # ... 025, then 030, 031, 032 as far as they are merged, in id order
grep '^| CHG-' $CL | grep -v ' |$'                    # prints nothing (every row ends " |"; the |---| separator line starts "|-" so "| CHG-" does not select it)
grep -n '^<<<<<<<\|^>>>>>>>\|^=======' $CL           # prints nothing (no conflict markers)
tail -c1 $CL | od -An -c                              # \n (file ends with a newline)
```
After all three: `git diff --shortstat origin/main -- $CL` shows 9 insertions and 6 deletions, rows 019-029 equal #30's file (`diff <(grep -E '^\| CHG-2026-0(19|2[0-9]) ' $CL) <(git show origin/chg-2026-031-rfc-records:$CL | grep -E '^\| CHG-2026-0(19|2[0-9]) ')` prints nothing), and `env -u THUSA_ROOT uv run pytest -q` passes (443 passed, 61 skipped expected: main 196 + #29 15 + #31 232; #30 adds no tests). Only then, with the owner's quoted GO, push.

No helper script is added (nothing outside this PR's scope): the procedure is text, here and in the bodies of #29, #30 and #31.

## Not changed
`thusa/`, `config/`, `public-data/` (no file written, no nightly run), `scripts/publish-public-data.sh`, the dashboard, the live skill file, the working data root outside git, CI files, dependencies. No external uptime service (D-08) is signed up for.

## Data identical before/after
Yes. No data file is touched.

## Tests
New `tests/test_check_live.py` (232 tests after the fourth review round; 155 at 8292fc8; 113 at 56f2f8d; 100 at facc3f8; 21 in the first version) runs the script against a local HTTP server that serves fixture manifests (no network): healthy site, stale manifest, 30 to 48 hour warning, future timestamp, 404 manifest, invalid JSON, unreachable host, 500 with retry that then succeeds, `--expect-local` match, mismatch with `--wait 0`, a build that appears during the wait, raw/site differing, no `--raw-url`, and the exit codes through `main()`. Added after review: `main()` with no flags at 29 h (OK), 31 h (WARN) and 49 h (BREACH); strict boundaries at exactly 30 h (OK) and 48 h (WARN, not BREACH); the sha256 check and the byte-count check each proved necessary by its own test (same-length corrupt body; right sha256 with a wrong byte count); the exact SAST string for a manifest written in UTC, UTC-5 and UTC+2; `files` null, dict, string, number, list of junk and missing; a truncated body (manifest and data file, and that it is retried); other unparseable manifests; `file://`, `ftp://` and other schemes refused for `--site`, `--raw-url`, `run_checks`, `fetch` and a redirect; a followed http redirect; 23 nonsense flag values; poll 0 not busy-looping; the age and file checks re-run on the manifest fetched after `--wait` (the manifest and the data file served before and after the wait differ in age, length and sha256, so using the pre-wait manifest for either check fails the test); an `ftp://` redirect is refused without any connection (listening socket); a bad port or unparseable URL for `--site` and `--raw-url` gets a fixed message with no part of the URL; an empty or all-comma `--sample-files` exits 2 and fetches nothing, and a single sample file works; a scheme-less `user:pw@host`, malformed and whitespace URLs, bad numeric values, stray and abbreviated arguments never repeat any part of the input (fixed marker string, for `--site`, `--raw-url`, `validate_url`, `fetch`, `run_checks` and `main`), plus a seeded fuzz of 1500 generated URLs; missing build ids on either side are not OK; no userinfo or query string is ever printed. Added in the fourth round (after the re-check of 8292fc8): a value given to a flag that takes none (`--json=X`, a second `--json=X`, `--help=X`, `-h=X`, empty values and combinations with other flags: 12 forms) is refused with "this flag takes no value" and never echoed, while a plain `--help` and `-h` still print the usage and exit 0 (and `-hX` answers with the same static help); every exit-2 message must be on the fixed list, and `_Parser.error` is called directly with messages the script never produces to prove they are replaced, not printed; every fixed URL message is reachable for both `--site` and `--raw-url`; `--retries` and `--retry-delay` with 308, 309, 400 and 5000 digits and the signs `-`, `+` and none (exit 2, no traceback); the `_num` converter itself raises only `ArgumentTypeError`; non-ASCII URLs (host, path) exit 2 and are not a BREACH, a punycode host is accepted, `%` in the host (`%20`, `%0a`, an IPv6 zone id) exits 2 and `%` in a path or query is fine; the printed site is the normalised safe form, not the typed string (an upper-case host is printed lower-case); a manifest with a UTF-8 BOM is read for the site and for `--expect-local`, and other leading garbage is still a BREACH; 11 abbreviated flags are refused and every documented flag is still accepted in full; the URL fuzz now also uses non-ASCII and percent forms, and a second seeded fuzz (600 generated command lines: all flags in many forms, `--x=MARK`, `-hMARK`, abbreviations, with a rejected value inserted so no fetch happens) must never print the marker, never show a traceback and exit 2 in more than 300 cases. Also run: `uv run pytest -q` with `THUSA_ROOT` unset and with a data copy; one real run against the production site (read-only, output kept with the review evidence, not in the repo). Results below.

## POPIA review
PASS by me (PublicFunds, the author), which is not an independent review. The independent popia-review is Scout's (an independent reviewer, not the author): Scout passed the earlier heads, 56f2f8d and 8292fc8 with no personal information found (reported to me). Validator did not do a POPIA review. These are reviewer PASSes, not an owner GO, and they do not cover the delta in the commit that follows 8292fc8 (no echo of a value given to a flag that takes none, a generic fallback for any error message not on the fixed list, huge integers, non-ASCII and `%` hosts, BOM, tests, wording): **an independent popia-review (Scout) of the head after this commit is requested, not done.** The new code prints less than before (it replaces argparse messages that could repeat input) and reads no new input. The script reads only public, non-personal files (home page, the data manifest and three public data files) from our own site and the git host, stores nothing, sends no credentials or cookies and no identifying header beyond a fixed User-Agent `publicfunds-check/1`. No personal information, IDs, contacts or accounts in code, tests or this record.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Reviewers passed 9179fbc with a small fix list (applied in facc3f8). At facc3f8 Validator re-checked expert and charter (PASS) and Scout shadow/drift and the independent POPIA review (PASS); at 56f2f8d Validator passed expert and charter with should-fixes and Scout passed shadow/drift and POPIA. The commit after 56f2f8d applied those should-fixes; at 8292fc8 Validator passed expert and charter and Scout passed shadow/drift and the independent POPIA review, each with small remaining items (reported to me). The commit after 8292fc8 applies those items (flag-value echo, huge integers, non-ASCII and `%` hosts, BOM, the behaviour-change label, the merge procedure) and has had **no review**: Validator's expert and charter re-check and Scout's shadow/drift and independent POPIA re-check of it are requested, not done. These are reviewer PASSes, never an owner GO. Merge needs the owner's quoted GO for CHG-2026-032; using the script in the nightly needs a second, separate GO.

## Result (2026-10-24, SAST)
Built and tested in DEV only (fresh clone of origin/main 6abd695, own uv venv). The change has not been merged, nothing in PROD is changed, and nothing calls the script.
- `uv run pytest`, `THUSA_ROOT` unset: **428 passed, 61 skipped** (main was 196 passed, 61 skipped; +232 new tests; 8292fc8 had 351 passed, 61 skipped with 155 new tests, 56f2f8d had 309 passed with 113, facc3f8 296 with 100, 9179fbc 217 with 21). With a data copy the first version had 277 passed, 1 skipped (main 256 passed, 1 skipped); that run was **not repeated** for the follow-ups (no data-dependent code or test changed).
- Mutation check, all re-run on this head (232 tests in the file; 38 mutations). Each mutation was applied alone to a copy of `scripts/check_live.py`, then `pytest tests/test_check_live.py` was run and the file restored. Several of the error-message defences are layered (the type converters, the fixed `ap.error`, and the `_Parser.error` whitelist behind them), so a mutation of an inner layer can be hidden by an outer one; those rows are also run with the whitelist fallback switched off ("+ fallback off"), which is the only way to see that the inner layer is tested on its own. Failing tests per mutation:

| Mutation | Tests failing |
|---|---|
| max-age comparison `>` to `>=` | 2 |
| warn comparison `>` to `>=` | 1 |
| breach threshold multiplied by 10 | 7 |
| sha256 check removed | 1 |
| byte-count check removed | 1 |
| `file` added to the allowed schemes | 3 |
| manifest `files` list check removed | 4 |
| poll floor removed | 1 |
| post-wait manifest not used at all | 1 |
| pre-wait manifest used for the file checks | 1 |
| pre-wait manifest used for the age check | 1 |
| missing build id treated as the same build | 1 |
| printed URL not stripped (`shown = site`) | 1 (see below) |
| redirect scheme guard removed | 1 |
| redirect guard replaced by urllib's default opener | 1 |
| Python's parser message passed through in the URL error | 10 |
| empty `--sample-files` accepted | 5 |
| scheme named in the scheme error | 7 (10 with fallback off) |
| bad numeric flag value echoed | 3 (8 with fallback off) |
| unrecognised arguments left to argparse | 11 (13 with fallback off) |
| flag abbreviations allowed again | 10 (13 with fallback off) |
| whitespace and control-character check removed | 11 |
| non-ASCII check removed | 11 |
| `%`-in-host check removed | 13 |
| `%` allowed in an IPv6 zone only (partial check) | 2 |
| huge-integer guard removed (`math.isfinite` on an int) | 7 |
| BOM not stripped (site manifest) | 1 |
| BOM not stripped (`--expect-local` file) | 1 |
| `_Parser` class removed (plain argparse) | 13 |
| "ignored explicit argument" message not replaced | 12 (14 with fallback off) |
| no-value message keeps the typed value (fallback off) | 14 |
| whitelist fallback switched off, alone | 1 |
| whitelist uses `search` instead of `fullmatch` | 1 |

  Every mutation is caught. Two corrections to earlier text. (1) The printed-URL mutation (`shown = site`) **survived all 155 tests at 8292fc8** when re-run for this round: `validate_url` already rejects userinfo, query and fragment for `--site`, so the rebuilt form differs from the typed one only in normalisation, and nothing tested the printed form. The earlier table said 1 test failed; I could not reproduce that. A test of the printed form (a host typed in upper case must print in lower case) now kills it. (2) The rows for the numeric echo, unrecognised arguments and abbreviations are higher than before because the new tests and the fuzz of command lines also catch them; with the whitelist in place alone they are hidden, which is why the "fallback off" runs are listed. An earlier run of the abbreviation mutation matched two places (a comment now says the same words) and was repeated with the exact text.
- One real read-only run against the production site (output kept with the review evidence, not in the repo): all checks OK, data 8.4 h old (generated 2026-10-24 03:05 SAST), build `B20261024T010413Z` identical on the site, the git host and the local manifest; three sample files match their checksums. A forced-threshold run and an unreachable-host run (also kept with the review evidence) show the BREACH lines and exit code 1.
- Nothing visible changes on the site, so there are no UI screenshots; the text output above is the evidence.

Awaiting review of the head after 8292fc8; no merge GO.
