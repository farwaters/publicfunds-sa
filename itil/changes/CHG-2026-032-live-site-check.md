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
| `site.manifest` | `<site>/public-data/v1/manifest.json` answers 200 and parses as a JSON object | BREACH |
| `site.age` | `generated_at_sast` has a UTC offset and the age is at most `--max-age-hours` (default 48, SLO-PD-1) | BREACH; a timestamp more than 5 minutes in the future is also a BREACH (the clock or the file is wrong); WARN when over `--warn-age-hours` (default 30: one missed nightly shows before the SLO is breached) |
| `site.files` | 3 sample files named in the manifest (default `municipalities.json,departments.json,prices.json`) are served with the byte count and sha256 the manifest states | BREACH |
| `raw.manifest`, `raw.age` | only with `--raw-url`: the same manifest from the git host (the SLO's measuring point) is reachable, within the SLO age, and has the same `build.id` as the site | WARN if the build differs (site behind or ahead of git: Pages lag or a failed Pages build); BREACH if the raw manifest is unreachable or older than the SLO |
| `local.build` | only with `--expect-local <manifest.json>`: the site serves that file's `build.id`; polled every `--poll` seconds (default 30) for up to `--wait` seconds (default 0) so Pages has time to deploy | BREACH after the wait |

Each request is tried 3 times (`--retries`, 5 s apart) with a 20 s timeout before it counts as failed, so one network blip is not a breach. Output: one `[OK]`/`[WARN]`/`[BREACH]` line per check, then `RESULT: OK` / `RESULT: WARN (n)` / `RESULT: BREACH (n)`; `--json` prints the same as JSON; times are shown in SAST. Exit code 0 = OK or WARN only, 1 = at least one BREACH. The default site is the production host; every URL is an argument, so tests and previews use a local server.

`itil/knowledge/runbooks.md`: new **RB-12** (command, flags, exit codes, what to do on a BREACH: report it, do not re-publish blindly, SLO-PD-1 and RSK-024 links). `itil/sla-slo.md`: SLO-PD-1 measurement cell names the script. `itil/registers/csi-register.md`: CSI-036 status. Change-log row at the end.

## Proposed routine step (NOT applied; separate GO needed)
The nightly routine lives in the live skill file (`publicfunds-refresh`, outside git). Editing it needs the owner's separate GO and its own RFC (as CHG-2026-025 did); this RFC does not edit it and nothing in this PR can. Proposed text for that later step, after the push step:
> N. Check the live site: `python3 scripts/check_live.py --expect-local public-data/v1/manifest.json --raw-url <raw manifest URL from RB-11> --wait 600`. Put its `RESULT:` line and any `[BREACH]`/`[WARN]` lines in the report. A BREACH is reported as a breach, never as success. Do not re-run the publish to "fix" it; report and stop.

## Not changed
`thusa/`, `config/`, `public-data/` (no file written, no nightly run), `scripts/publish-public-data.sh`, the dashboard, the live skill file, `/workspace/publicfunds`, CI files, dependencies. No external uptime service (D-08) is signed up for.

## Data identical before/after
Yes. No data file is touched.

## Tests
New `tests/test_check_live.py` runs the script's functions against a local HTTP server that serves fixture manifests (no network): healthy site, stale manifest, 30 to 48 hour warning, future timestamp, 404 manifest, invalid JSON, unreachable host, 500 with retry that then succeeds, checksum mismatch, `--expect-local` match, mismatch with `--wait 0`, a build that appears during the wait, raw/site differing, no `--raw-url`, the SAST display, and the exit codes through `main()`. Also run: `uv run pytest -q` with `THUSA_ROOT` unset and with a data copy; one real run against the production site (read-only, output kept under `/workspace/previews/chg-2026-032/`). Results below.

## POPIA review
PASS (to be confirmed by popia-review). The script reads only public, non-personal files (home page, the data manifest and three public data files) from our own site and the git host, stores nothing, sends no credentials or cookies and no identifying header beyond a fixed User-Agent `publicfunds-check/1`. No personal information, IDs, contacts or accounts in code, tests or this record.

## Review
Four checks (expert, shadow, charter, drift) and popia-review by someone other than the author before any merge. Merge needs the owner's quoted GO for CHG-2026-032; using the script in the nightly needs a second, separate GO.

## Result (2026-10-24, SAST)
Built and tested in DEV only (fresh clone of origin/main 6abd695, own uv venv). The change has not been merged, nothing in PROD is changed, and nothing calls the script.
- `uv run pytest`: 217 passed, 61 skipped (main was 196 passed, 61 skipped; +21 new). With a data copy (ingest `dmpr_fuel`, `thusa build`): 277 passed, 1 skipped (main 256 passed, 1 skipped).
- Mutation check: loosening the SLO threshold in the script makes 4 of the new tests fail.
- One real read-only run against the production site (`/workspace/previews/chg-2026-032/healthy-live.txt`): all checks OK, data 8.4 h old (generated 2026-10-24 03:05 SAST), build `B20261024T010413Z` identical on the site, the git host and the local manifest; three sample files match their checksums. A forced-threshold run and an unreachable-host run (`breach-demo.txt`) show the BREACH lines and exit code 1.
- Nothing visible changes on the site, so there are no UI screenshots; the text output above is the evidence.

Awaiting review; no merge GO.
