#!/usr/bin/env bash
# Refresh the public dashboard data after a successful pipeline run (CHG-2026-006, RB-11).
#
#   scripts/publish-public-data.sh            export + commit public-data/ only (no push)
#   scripts/publish-public-data.sh --push     ... and push that commit to origin/main
#
# --push is pre-authorised ONLY when run by the daily refresh routine the owner approved (publicfunds-refresh
# skill). Any other push needs the owner's explicit approval. The script refuses to:
#   - publish if the current build failed data quality (pf publish-data exits 3),
#   - commit anything outside public-data/,
#   - push from a branch other than main, or a non-fast-forward.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PUSH=0; [[ "${1:-}" == "--push" ]] && PUSH=1
log() { printf '[publish-data %s SAST] %s\n' "$(TZ=Africa/Johannesburg date +%H:%M:%S)" "$*"; }

mkdir -p data
uv run pf publish-data > data/publish-data.json 2> data/publish-data.log || { tail -n 5 data/publish-data.json data/publish-data.log >&2; log "export refused (see data/publish-data.*)"; exit 3; }
log "exported: $(python3 -c "import json;d=json.load(open('data/publish-data.json'));print(d['total_bytes'],'bytes,',len(d['files']),'files')")"

if git diff --quiet -- public-data/ && [[ -z "$(git ls-files --others --exclude-standard -- public-data/)" ]]; then
  log "no change in public-data/; nothing to commit"; exit 0
fi
# The manifest timestamp alone changing is not worth a commit.
if [[ "$(git diff --name-only -- public-data/ | sort)" == "public-data/v1/manifest.json" ]] \
   && [[ -z "$(git ls-files --others --exclude-standard -- public-data/)" ]] \
   && [[ "$(git diff -U0 -- public-data/v1/manifest.json | rg '^[+-] ' | rg -v 'generated_at_sast|"last_(run|checked)_sast"' | wc -l)" == "0" ]]; then
  git checkout -- public-data/v1/manifest.json; log "only timestamps changed; not committed"; exit 0
fi
git add -A -- public-data/
OTHER="$(git diff --cached --name-only | rg -v '^public-data/' || true)"
[[ -z "$OTHER" ]] || { log "refusing: other staged changes present: $OTHER"; exit 4; }
git commit -q -m "data: refresh public-data/v1 ($(python3 -c "import json;print(json.load(open('public-data/v1/manifest.json'))['build']['id'])"))" -- public-data/
log "committed $(git rev-parse --short HEAD)"
if [[ "$PUSH" == "1" ]]; then
  BR="$(git rev-parse --abbrev-ref HEAD)"
  [[ "$BR" == "main" ]] || { log "refusing to push from branch $BR (main only)"; exit 4; }
  git fetch -q origin main
  git merge-base --is-ancestor origin/main HEAD || { log "refusing: origin/main has moved; not a fast-forward"; exit 4; }
  git push -q origin HEAD:main
  log "pushed to origin/main"
fi
