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

# CHG-2026-041 (CSI-054): one clearly labelled stdout line (plus up to 3 note lines) about the evidence guard (CHG-2026-040), so the
# nightly report can show it. Read-only: it never touches a published file and never changes an exit code (`|| true` at each call).
#   evidence_guard: pass | pass (N notes) | warn (N notes) | BLOCKED (exit 3 ...) | not an evidence-guard refusal (...) | UNKNOWN (...)
# Only a bare `pass` is quiet. If the helper itself fails it prints UNKNOWN and returns 1; the callers swallow that with `|| true`.
guard_report() {  # $1 = ok (read the evidence_guard key of data/publish-data.json) | refused (read data/publish-data.log)
  python3 - "$1" <<'PY' || { echo "evidence_guard: UNKNOWN (report helper failed)"; return 1; }
import json, sys, unicodedata
MAX, CAP = 3, 300
def clean(n):  # one line, no control characters, so a note cannot forge a line or drive the terminal
    s = "".join(" " if c.isspace() else "" if unicodedata.category(c) in ("Cc", "Cf") else c for c in str(n))
    s = " ".join(s.split())
    return s if len(s) <= CAP else s[:CAP - 3] + "..."
def show(notes):
    for n in notes[:MAX]:
        print(f"evidence_guard:   {n}")
    if len(notes) > MAX:
        print(f"evidence_guard:   ... and {len(notes) - MAX} more (data/publish-data.json, data/publish-data.log)")
def count(n):
    return f"{n} note{'' if n == 1 else 's'}"
try:
    if sys.argv[1] == "refused":
        text = open("data/publish-data.log", encoding="utf-8", errors="replace").read()
        errs = []
        for l in text.splitlines():  # pf prints {"error": "public data not written: <reason>", "exit_code": 3} on stderr
            try:
                e = json.loads(l).get("error", "")
            except Exception:
                continue
            if isinstance(e, str) and e.startswith("public data not written:"):
                errs.append(clean(e.split(":", 1)[1]))
        if any(e.startswith("evidence guard") for e in errs):
            print("evidence_guard: BLOCKED (exit 3; nothing published, published files left as they are)")
            show([e for e in errs if e.startswith("evidence guard")])
        else:
            print("evidence_guard: not an evidence-guard refusal (no guard refusal found in the log; cause may be the quality gate, the safety scan, another refusal or a crash; read data/publish-data.log)")
    else:
        g = json.load(open("data/publish-data.json", encoding="utf-8")).get("evidence_guard")
        if not isinstance(g, dict) or g.get("status") != "pass" or not isinstance(g.get("notes", []), list):
            print("evidence_guard: UNKNOWN (no usable evidence_guard key in data/publish-data.json; treat as not checked)")
        else:
            notes = [clean(n) for n in g.get("notes", [])]
            warns = [n for n in notes if n.startswith("warn")]
            print(f"evidence_guard: warn ({count(len(warns))})" if warns else f"evidence_guard: pass ({count(len(notes))})" if notes else "evidence_guard: pass")
            show(warns + [n for n in notes if not n.startswith("warn")])
except Exception as e:  # never let the report change the publish
    print(f"evidence_guard: UNKNOWN ({type(e).__name__}; treat as not checked)")
PY
}

mkdir -p data
uv run pf publish-data > data/publish-data.json 2> data/publish-data.log || { tail -n 5 data/publish-data.json data/publish-data.log >&2; guard_report refused || true; log "export refused (see data/publish-data.*)"; exit 3; }
log "exported: $(python3 -c "import json;d=json.load(open('data/publish-data.json'));print(d['total_bytes'],'bytes,',len(d['files']),'files')")"
guard_report ok || true

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
