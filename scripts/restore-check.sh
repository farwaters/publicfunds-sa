#!/usr/bin/env bash
# CHG-2026-044. Runs `python -m thusa.backup restore-check`. Writes only outside the repo (PF_BACKUP_DIR, default /home/box/publicfunds-backups).
# Exit 0 on success. Any error gives a non-zero exit (fail closed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
umask 077
exec uv run --frozen python -m thusa.backup restore-check "$@"
