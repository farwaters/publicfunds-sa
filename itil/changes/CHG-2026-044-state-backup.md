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
   - The script never opens a live database file. First it takes a snapshot. It copies the db file and the existing `-wal` (SQLite) or `.wal` (DuckDB) file into a private temp folder (mode 0700). It never copies `-shm`.
   - The script compares the size, mtime and inode of each source file before and after the copy. If a value changes, the script copies again. After 5 tries it stops with exit code 1.
   - SQLite: the script runs the online backup API (`Connection.backup`) from the snapshot. SQLite replays the copied WAL. Committed writes that are not checkpointed are in the backup. The script runs `PRAGMA integrity_check` on the copy.
   - DuckDB: the script opens the snapshot and runs `EXPORT DATABASE ... (FORMAT PARQUET)`.
   - The script deletes the snapshot before it writes the manifest.
   - The script refuses when a writer is active. A writer is a running `thusa ingest`, `thusa build` or `thusa run` process. A writer is also a `*.building.duckdb` file. A write lock on the DuckDB file also stops the backup. The script checks the lock with `fcntl(F_GETLK)` on a read-only file descriptor. This call writes nothing. A read-only connection (for example from `pf serve`) is not a writer and does not stop the backup.
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

## Method choice (review round 1)
Cassian (Build) failed head `8d2e6e92`, as reported to the author (PublicFunds). The read-only SQLite open created `review.sqlite-wal` and `review.sqlite-shm` in the live review folder. The fix weighed two methods:
- `immutable=1`. SQLite then does not create side files. But SQLite also ignores the `-wal` file and all locks. If `pf serve` writes, or if the WAL holds commits that are not checkpointed, the backup misses those commits. This method is not safe. The fix does not use it.
- Snapshot, then backup. The script copies the db file and the `-wal` file with plain file reads. Plain reads write nothing. The script checks that no source file changed during the copy. The online backup API then reads the private copy. The copy includes the WAL commits. This method is consistent and writes nothing to the source folder. The fix uses it.

`pf serve` can run during a backup. A write by `pf serve` during the copy changes the size or mtime of `review.sqlite` or `review.sqlite-wal`. The script then copies again. A torn copy that the check does not find fails `integrity_check`. The script then stops with exit code 1.

DuckDB: a read-only open did not create a `.wal` file in a test on 31 Oct 2026. The script does not depend on this result. It opens only the snapshot.

## Limits
- The earlier live run of head `8d2e6e92` (31 Oct 2026 19:17 SAST) created an empty `review.sqlite-wal` and a `review.sqlite-shm` in `data/review/`. The files are still there. This change does not delete them. They do not change the data.
- The size and mtime check finds most changes during the copy. It cannot find a write that keeps the size and the mtime. `integrity_check` is the second check.
- The backups are on the same box. They do not reduce RSK-006 (single box). The offsite target (CI-050) is still planned.
- The process check reads `ps` output. A writer with a different command line is not found by the process check. The DuckDB lock check and the `*.building.duckdb` check still apply.

## Testing
- `tests/test_backup_state.py`: 20 tests. The tests use temp fixtures only. They use no real data.
- The tests cover: manifest hashes and counts; file modes; restore PASS; FAIL on a changed file; FAIL on a changed count; FAIL with no backup; retention; a same-day rerun; refusal while `thusa run` runs; refusal while a build file exists; refusal while another process holds the DuckDB write lock; a missing source; source folders unchanged (file list, mode, size and sha256 of every file, before and after) for a normal db and for a WAL-mode db with no side files; a WAL-mode db with commits that are not checkpointed, held open by another process: the folders do not change and the backup has the 5 new rows; a DuckDB reader does not stop the backup; a snapshot of a file that keeps changing fails; the process pattern; CLI exit codes; `.gitignore`.
- Full suite: `uv run pytest`. The result is in the PR.
- Live proof, 31 Oct 2026 19:24 SAST, against `/workspace/publicfunds`. `pf serve` ran. No `thusa` writer ran. The backup went to a temp folder.
  - Before and after the backup and the restore check, the author recorded `ls -la --time-style=full-iso` of `data/` and `data/review/`. The author also recorded the sha256 of all 176 files under `data/`.
  - Both records were identical before and after (`cmp`). The file list, sizes, modes and mtimes did not change.
  - Backup: exit 0. Restore check: PASS.
  - The author deleted the temp backup after the check.

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
