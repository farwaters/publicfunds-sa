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
- Flags are bounded and checked before anything is fetched (exit code 2): `--wait` 0 to 3600 s, `--poll` 1 to 600 s (`run_checks` also never polls faster than 0.05 s, so poll 0 cannot busy-loop), `--max-age-hours` and `--warn-age-hours` positive and finite with warn below max, `--retries` 0 to 10, `--retry-delay` 0 to 60 s, `--sample-files` at least one name (an empty or all-comma value is refused with exit code 2: it would otherwise be a silent OK with no file checked; I chose to reject rather than WARN).
- Printed URLs have no userinfo and no query string or fragment; error messages never repeat a rejected URL or any part of it: an unparseable URL (a bad port, for example) gets one fixed message and not Python's own text, which would echo the port.

**Known limits (read before relying on it):**
- A checksum mismatch immediately after a publish can be a **false BREACH** while GitHub Pages is still deploying the new files (the manifest and a data file can come from different deploys). Mitigation: after a publish run `--expect-local <manifest> --wait <seconds>`, which waits for the site to serve the published build and then checks age and files against the manifest fetched after the wait. A BREACH that persists after the wait is real.
- The opener honours the `*_proxy` environment variables of the calling process (a proxy set there is used for every request). Response bodies and the total run time are **unbounded**: the timeout is per socket read, so a server that keeps sending slowly can hold a run open. Both are known limits: run the script under an overall timeout.
- A default run measures **the site**, not raw.githubusercontent.com, which SLO-PD-1 names as the measuring point. `--raw-url` adds that measurement (and the site/git-host comparison); without it the age check is the site's view, which can lag the git host.

`itil/knowledge/runbooks.md`: new **RB-12** (command, flags, exit codes, what to do on a BREACH: report it, do not re-publish blindly, SLO-PD-1 and RSK-024 links). `itil/sla-slo.md`: SLO-PD-1 measurement cell names the script. `itil/registers/csi-register.md`: CSI-036 status. Change-log row at the end.

## Proposed routine step (NOT applied; separate GO needed)
The nightly routine lives in the live skill file (`publicfunds-refresh`, outside git). Editing it needs the owner's separate GO and its own RFC (as CHG-2026-025 did); this RFC does not edit it and nothing in this PR can. Proposed text for that later step, after the push step:
> N. Check the live site: `python3 scripts/check_live.py --expect-local public-data/v1/manifest.json --raw-url <raw manifest URL from RB-11> --wait 600`. Put its `RESULT:` line and any `[BREACH]`/`[WARN]` lines in the report. A BREACH is reported as a breach, never as success. Do not re-run the publish to "fix" it; report and stop.

## Not changed
`thusa/`, `config/`, `public-data/` (no file written, no nightly run), `scripts/publish-public-data.sh`, the dashboard, the live skill file, the working data root outside git, CI files, dependencies. No external uptime service (D-08) is signed up for.

## Data identical before/after
Yes. No data file is touched.

## Tests
New `tests/test_check_live.py` (113 tests after the second review round; 100 at facc3f8; 21 in the first version) runs the script against a local HTTP server that serves fixture manifests (no network): healthy site, stale manifest, 30 to 48 hour warning, future timestamp, 404 manifest, invalid JSON, unreachable host, 500 with retry that then succeeds, `--expect-local` match, mismatch with `--wait 0`, a build that appears during the wait, raw/site differing, no `--raw-url`, and the exit codes through `main()`. Added after review: `main()` with no flags at 29 h (OK), 31 h (WARN) and 49 h (BREACH); strict boundaries at exactly 30 h (OK) and 48 h (WARN, not BREACH); the sha256 check and the byte-count check each proved necessary by its own test (same-length corrupt body; right sha256 with a wrong byte count); the exact SAST string for a manifest written in UTC, UTC-5 and UTC+2; `files` null, dict, string, number, list of junk and missing; a truncated body (manifest and data file, and that it is retried); other unparseable manifests; `file://`, `ftp://` and other schemes refused for `--site`, `--raw-url`, `run_checks`, `fetch` and a redirect; a followed http redirect; 23 nonsense flag values; poll 0 not busy-looping; the age and file checks re-run on the manifest fetched after `--wait` (the manifest and the data file served before and after the wait differ in age, length and sha256, so using the pre-wait manifest for either check fails the test); an `ftp://` redirect is refused without any connection (listening socket); a bad port or unparseable URL for `--site` and `--raw-url` gets a fixed message with no part of the URL; an empty or all-comma `--sample-files` exits 2 and fetches nothing, and a single sample file works; missing build ids on either side are not OK; no userinfo or query string is ever printed. Also run: `uv run pytest -q` with `THUSA_ROOT` unset and with a data copy; one real run against the production site (read-only, output kept with the review evidence, not in the repo). Results below.

## POPIA review
PASS by me (PublicFunds, the author), which is not an independent review. Scout (an independent reviewer, not the author) passed 9179fbc and the later head facc3f8 with no personal information found (reported to me): these are reviewer PASSes, not an owner GO, and they do not cover the delta in the commit that follows facc3f8 (the fixed bad-port message, the empty `--sample-files` rejection, tests and wording), which needs a re-check (requested). The script reads only public, non-personal files (home page, the data manifest and three public data files) from our own site and the git host, stores nothing, sends no credentials or cookies and no identifying header beyond a fixed User-Agent `publicfunds-check/1`. No personal information, IDs, contacts or accounts in code, tests or this record.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Validator and Scout passed 9179fbc with a small fix list (applied in facc3f8), then re-checked facc3f8: PASS on expert, charter, shadow and POPIA, with a second small list that the following commit applies. Re-check of that commit is requested; no PASS is claimed for it until both have re-checked. These are reviewer PASSes, not an owner GO. Merge needs the owner's quoted GO for CHG-2026-032; using the script in the nightly needs a second, separate GO.

## Result (2026-10-24, SAST)
Built and tested in DEV only (fresh clone of origin/main 6abd695, own uv venv). The change has not been merged, nothing in PROD is changed, and nothing calls the script.
- `uv run pytest`, `THUSA_ROOT` unset: **309 passed, 61 skipped** (main was 196 passed, 61 skipped; +113 new tests; 9179fbc had 217 passed, 61 skipped with 21 new tests, facc3f8 had 296 passed, 61 skipped with 100). With a data copy the first version had 277 passed, 1 skipped (main 256 passed, 1 skipped); that run was **not repeated** for this follow-up (no data-dependent code or test changed).
- Mutation check, all re-run on this head (113 tests in the file, after the changes). Each mutation was applied alone to a copy of `scripts/check_live.py`, then `pytest tests/test_check_live.py` was run and the file restored. Failing tests per mutation:

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
| post-wait manifest not used at all | 2 |
| pre-wait manifest used for the file checks | 1 |
| pre-wait manifest used for the age check | 1 |
| missing build id treated as the same build | 1 |
| printed URL not stripped | 1 |
| redirect scheme guard removed | 1 |
| redirect guard replaced by urllib's default opener | 1 |
| Python's parser message passed through in the URL error | 6 |
| empty `--sample-files` accepted | 5 |

  Every mutation is caught. The two "pre-wait manifest" mutations passed all 100 tests at facc3f8 (the old and new manifests listed identical files); the rewritten post-wait test now kills both, and the ftp-redirect, bad-port and empty `--sample-files` mutations are each caught by the tests added for them. The earlier text of this record said "loosening the SLO threshold makes 4 of the new tests fail": that was the threshold-times-10 mutation against the first 21 tests; with the current tests the same mutation fails 7.
- One real read-only run against the production site (output kept with the review evidence, not in the repo): all checks OK, data 8.4 h old (generated 2026-10-24 03:05 SAST), build `B20261024T010413Z` identical on the site, the git host and the local manifest; three sample files match their checksums. A forced-threshold run and an unreachable-host run (also kept with the review evidence) show the BREACH lines and exit code 1.
- Nothing visible changes on the site, so there are no UI screenshots; the text output above is the evidence.

Awaiting review; no merge GO.
