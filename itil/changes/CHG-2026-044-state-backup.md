# CHG-2026-044: Nightly state backup and weekly restore check

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner's delegate (PublicFunds), 2026-10-31 |
| Environment | DEV for build. The merge to main is PROD. The merge adds code only. The code does not run until the owner approves the routine steps (appendices) |
| Type | Normal-high. See "Tier" |
| CIs affected | New CI-114 (`thusa/backup.py`, `scripts/backup-state.sh`, `scripts/restore-check.sh`, `tests/test_backup_state.py`); `.gitignore`; CI-098 (read only); registers: change-log, ci-register, csi-register (CSI-009) |
| Linked records | CSI-009 (restore test automation), RSK-006 (single box), CI-050 (offsite backup target, planned), CI-098 (review store) |
| Rollback | Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>`. Remove the routine steps first if the owner applied them |

## Problem
A restore test on 31 Oct 2026 found no backup of `data/thusa.duckdb`. It found no backup of `data/review/review.sqlite`. The pipeline can rebuild the warehouse from raw files. The review decisions are in the SQLite file only. If the file is lost, the review decisions are lost.

## Change
1. `thusa/backup.py backup` (wrapper `scripts/backup-state.sh`) makes one dated backup:
   - The folder is `/home/box/publicfunds-backups/YYYY-MM-DD/`. Set `PF_BACKUP_DIR` to change it. The folder is outside the repo.
   - SQLite: the script uses the online backup API (`Connection.backup`). The source is opened read-only. The script runs `PRAGMA integrity_check` on the copy.
   - DuckDB: the script opens the file read-only and runs `EXPORT DATABASE ... (FORMAT PARQUET)`. It never copies an open database file.
   - The script refuses when a writer is active. A writer is a running `thusa ingest`, `thusa build` or `thusa run` process. A writer is also a `*.building.duckdb` file. A lock that blocks the read-only open also stops the backup.
   - `manifest.json` records the sha256 of each backup file and the row count of each table.
   - The script writes into a temp folder first. It renames the folder only when all steps pass. A second run on the same day replaces that day's folder.
   - The script keeps 14 daily folders. Set `--keep` or `PF_BACKUP_KEEP` to change the number. It deletes the oldest folders.
   - Any error stops the script with exit code 1. The script writes no partial folder.
2. `thusa/backup.py restore-check` (wrapper `scripts/restore-check.sh`) checks the latest backup:
   - It compares each file with its sha256 in the manifest. It also compares the file list.
   - It imports the DuckDB export into a temp database. It compares the row counts with the manifest.
   - It copies the SQLite file into the temp folder. It runs `PRAGMA integrity_check` and compares the row counts.
   - It appends one line to `restore-check.log` in the backup folder. Set `PF_RESTORE_LOG` to change it. The line has a timestamp with an offset, then PASS or FAIL, then the backup day and any problems.
   - Exit code 0 means PASS. Exit code 1 means FAIL. Any error is a FAIL.
3. `.gitignore` gets `publicfunds-backups/`.

## Tier
Normal-high. `itil/change-enablement.md` puts "POPIA-relevant handling" in Normal-high. This change makes new copies of `review.sqlite`. That file holds reviewer decisions, reviewer accounts and sessions. New copies of that data are POPIA-relevant handling. The change does not touch detectors, the publishing pipeline or `public-data/`. Without the POPIA point, the tier would be Normal-medium. Normal-high needs owner sign-off and a second reviewer or a 24 h cooling-off. A bot approval does not fill a human slot.

## POPIA
- `review.sqlite` holds reviewer decisions. The backups contain the same data.
- The backups stay on this box only. Nobody commits them. Nobody publishes them.
- Folders use mode 0700. Files use mode 0600. The log uses mode 0600. The script sets `umask 077`.
- The default folder is outside the repo. `.gitignore` also covers `publicfunds-backups/`.
- The retention limit deletes copies older than 14 days.
- The restore check writes only to a temp folder. Python deletes the temp folder after the check.

## Limits
- The backups are on the same box. They do not reduce RSK-006 (single box). The offsite target (CI-050) is still planned.
- SQLite in WAL mode can create `review.sqlite-wal` and `review.sqlite-shm` next to the source on a read-only open. This is normal SQLite behaviour. The data does not change.
- The process check reads `ps` output. A writer with a different command line is not found by the process check. The DuckDB lock check and the `*.building.duckdb` check still apply.

## Testing
- `tests/test_backup_state.py`: 15 tests. The tests use temp fixtures only. They use no real data.
- The tests cover: manifest hashes and counts; file modes; restore PASS; FAIL on a changed file; FAIL on a changed count; FAIL with no backup; retention; a same-day rerun; refusal while `thusa run` runs; refusal while a build file exists; refusal while another process holds the DuckDB write lock; a missing source; the process pattern; CLI exit codes; `.gitignore`.
- Full suite: `uv run pytest`. The result is in the PR.
- A read-only run on the live files is described in the PR. It wrote only to a temp folder.

## Risk
Low for published output. The code does not run in any routine until the owner approves the appendices. The main risk is a disk that fills up. Each backup is about 21 MB on 31 Oct 2026. 14 copies use about 300 MB.

## How to revert
1. If the owner applied appendix A or B, remove those steps from the routines first.
2. Run `git revert -m 1 <merge commit of this PR>`.
3. Backups that exist stay in `/home/box/publicfunds-backups/`. The owner decides to keep or delete them.

## Appendix: proposed routine wording (outside the repo; needs the owner's separate approval after the merge)
These steps change bot config. This change does not apply them.

### A. Nightly refresh routine (add after a successful run)
> **Back up state.** Do this step only if the build and the publish step returned 0. Run `scripts/backup-state.sh`. If the exit code is 0, put the `backup: ok` line in the report. If the exit code is not 0, begin the report with `ACTION: backup failed`. Quote the `backup: FAILED` line. Do not retry. Do not delete any backup.

### B. New weekly routine (Sunday 04:00 SAST)
> **Restore check.** Run `scripts/restore-check.sh`. Report the PASS or FAIL line. If the result is FAIL, or the exit code is not 0, begin the report with `ACTION: restore check failed`. Quote the line. Do not delete any backup. Do not change any file in the repo.

Result: PR open, not merged; no owner GO.
