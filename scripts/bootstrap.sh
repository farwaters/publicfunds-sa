#!/usr/bin/env bash
# PublicFunds Bot (Thusa) one-command install for a fresh Grok Bot box. Idempotent: safe to re-run.
#
#   curl -fsSL https://publicfunds.grokforum.site/scripts/bootstrap.sh | bash
#   # or, from a checkout:  scripts/bootstrap.sh
#
# Steps:
#   1. clone or fast-forward the repo
#   2. install uv (pinned) and the locked dependencies
#   3. run the pipeline
#   4. run the tests
#   5. create the local admin reviewer (password in a 0600 file, never printed)
#   6. start the review app on localhost
#
# Settings (environment variables; defaults in brackets):
#   PF_REPO_URL     [https://github.com/farwaters/publicfunds-sa]
#   PF_BRANCH       [main]
#   PF_DIR          [/workspace/publicfunds]
#   PF_PORT         [8765]       review app port (127.0.0.1 only)
#   PF_CONFIG_DIR   [~/.config/publicfunds]   credentials + token files (0700 dir, 0600 files)
#   PF_ADMIN_USER   [admin]      username of the local admin reviewer
#   PF_ADMIN_NAME   [Administrator]
#   PF_SKIP_PIPELINE=1 / PF_SKIP_TESTS=1   skip steps 3 / 4 (e.g. offline re-runs)
#   THUSA_HMAC_KEY_FILE  [~/.config/thusa/hmac.key]   key for hashing SA ID numbers (created 0600 if missing)
set -euo pipefail

PF_REPO_URL="${PF_REPO_URL:-https://github.com/farwaters/publicfunds-sa}"
PF_BRANCH="${PF_BRANCH:-main}"
PF_DIR="${PF_DIR:-/workspace/publicfunds}"
export PF_PORT="${PF_PORT:-8765}"
PF_CONFIG_DIR="${PF_CONFIG_DIR:-$HOME/.config/publicfunds}"
PF_ADMIN_USER="${PF_ADMIN_USER:-admin}"
PF_ADMIN_NAME="${PF_ADMIN_NAME:-Administrator}"
UV_VERSION="0.13.1"

log() { printf '\n[bootstrap %s SAST] %s\n' "$(TZ=Africa/Johannesburg date +%H:%M:%S)" "$*"; }
die() { printf '[bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

for t in git curl; do command -v "$t" >/dev/null || die "$t is required"; done

# 1. code ------------------------------------------------------------------------------------------
if [[ -d "$PF_DIR/.git" ]]; then
  log "updating $PF_DIR ($PF_BRANCH)"
  cd "$PF_DIR"
  [[ -z "$(git status --porcelain --untracked-files=no)" ]] || die "$PF_DIR has uncommitted changes; commit or stash them first"
  git fetch --quiet origin "$PF_BRANCH"
  git checkout --quiet "$PF_BRANCH"
  git merge --ff-only --quiet "origin/$PF_BRANCH" || die "local $PF_BRANCH has diverged from origin; resolve manually"
else
  [[ ! -e "$PF_DIR" || -z "$(ls -A "$PF_DIR" 2>/dev/null)" ]] || die "$PF_DIR exists and is not a git checkout"
  log "cloning $PF_REPO_URL ($PF_BRANCH) into $PF_DIR"
  git clone --quiet --branch "$PF_BRANCH" "$PF_REPO_URL" "$PF_DIR"
  cd "$PF_DIR"
fi
log "code at $(git rev-parse --short HEAD)"
export THUSA_ROOT="$PF_DIR"
unset THUSA_REVIEW_DB

# 2. uv + locked dependencies ------------------------------------------------------------------------
if ! command -v uv >/dev/null; then
  if [[ -x "$HOME/.local/bin/uv" ]]; then
    export PATH="$HOME/.local/bin:$PATH"
  else
    log "installing uv $UV_VERSION"
    curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" | env UV_NO_MODIFY_PATH=1 sh
    export PATH="$HOME/.local/bin:$PATH"
  fi
fi
log "uv $(uv --version | awk '{print $2}'); installing locked dependencies"
uv sync --frozen --quiet
mkdir -p "$PF_DIR/data"

# 3. pipeline ----------------------------------------------------------------------------------------
if [[ "${PF_SKIP_PIPELINE:-0}" != "1" ]]; then
  log "running the pipeline (ingest -> build -> DQ -> report); first run takes several minutes"
  if ! uv run thusa run > "$PF_DIR/data/bootstrap-run.log" 2>&1; then
    tail -n 20 "$PF_DIR/data/bootstrap-run.log" >&2 || true
    die "pipeline failed (exit 2 = a data-quality check failed); see data/bootstrap-run.log and runbook RB-01"
  fi
  log "pipeline ok: $(grep -o '"complete_pct": [0-9.]*' "$PF_DIR/data/bootstrap-run.log" | head -1)"
else
  log "skipping pipeline (PF_SKIP_PIPELINE=1)"
fi

# 4. tests -------------------------------------------------------------------------------------------
if [[ "${PF_SKIP_TESTS:-0}" != "1" ]]; then
  log "running tests"
  if ! uv run pytest -q -p no:cacheprovider > "$PF_DIR/data/bootstrap-tests.log" 2>&1; then
    tail -n 30 "$PF_DIR/data/bootstrap-tests.log" >&2 || true
    die "tests failed; see data/bootstrap-tests.log"
  fi
  log "tests: $(tail -n 1 "$PF_DIR/data/bootstrap-tests.log")"
fi

# 5. local admin reviewer ----------------------------------------------------------------------------
mkdir -p "$PF_CONFIG_DIR" && chmod 700 "$PF_CONFIG_DIR"
CRED="$PF_CONFIG_DIR/admin_credentials"
if uv run pf reviewer list | grep -q "\"username\": \"$PF_ADMIN_USER\""; then
  log "reviewer $PF_ADMIN_USER already exists; leaving its password unchanged"
else
  [[ ! -e "$CRED" ]] || die "$CRED exists but reviewer $PF_ADMIN_USER is not in this install's review DB; move the file or set PF_CONFIG_DIR"
  uv run pf reviewer add "$PF_ADMIN_USER" --display-name "$PF_ADMIN_NAME" --admin \
    --credentials-file "$CRED" --actor "bootstrap" >/dev/null
  log "created admin reviewer $PF_ADMIN_USER; password is in $CRED (mode 600)"
fi
if [[ ! -e "$PF_CONFIG_DIR/review_token" ]]; then
  uv run pf reviewer token "$PF_ADMIN_USER" --out "$PF_CONFIG_DIR/review_token" --actor "bootstrap" >/dev/null
  log "issued chat/CLI token for $PF_ADMIN_USER in $PF_CONFIG_DIR/review_token (mode 600)"
fi

# 6. review app (localhost only) ---------------------------------------------------------------------
PORT="$PF_PORT" "$PF_DIR/scripts/review-app.sh" start
log "done. Review in chat with 'uv run pf review list --status open', or open http://127.0.0.1:$PF_PORT/ in the bot's browser"
