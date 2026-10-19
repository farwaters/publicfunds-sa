"""Review service: joins flags from the warehouse with review state from the review store.
Shared by the web app, the JSON API and the `pf` CLI so all three apply identical rules."""
from __future__ import annotations

import csv
import io
import json

from thusa.review import workflow as wf
from thusa.review.store import ReviewStore, sast_label
from thusa.review.warehouse import SEV_ORDER, Warehouse
from thusa.settings import Paths

EXPORT_COLS = ["flag_id", "detector_id", "detector_version", "severity", "score", "title", "gov_body_id", "body_name",
               "period_label", "names_supplier", "status", "evidence_changed", "in_current_build", "confirmed_by",
               "n_decisions", "last_decision", "last_reviewer", "last_reason", "last_decided_at_sast"]


class Service:
    def __init__(self, paths: Paths):
        self.paths = paths
        self.wh = Warehouse(paths.warehouse)
        self.store = ReviewStore(paths.review_db)

    # ------------------------------------------------------------------ flags with status
    def _annotate(self, flags: list[dict]) -> list[dict]:
        states = self.store.states({f["flag_id"]: bool(f["names_supplier"]) for f in flags})
        for f in flags:
            st = states[f["flag_id"]]
            cur = wf.evidence_hash(f)
            f["evidence_hash"] = cur
            f["status"] = st.status
            f["evidence_changed"] = wf.is_stale(st, cur)
            f["confirmed_by"] = st.confirmers_on(cur) if st.status in ("confirmed", wf.AWAITING) else []
            f["n_decisions"] = st.n_decisions
            f["publishable"] = st.status == "confirmed" and not f["evidence_changed"]
        return flags

    def list_flags(self, detector: str | None = None, severity: str | None = None, status: str | None = None,
                   q: str | None = None, named: str | None = None, gov_body_id: str | None = None) -> list[dict]:
        flags = self._annotate(self.wh.flags())
        if detector:
            flags = [f for f in flags if f["detector_id"] == detector or f["detector_id"].split("_")[0] == detector]
        if severity:
            flags = [f for f in flags if f["severity"] == severity]
        if status == "open":
            flags = [f for f in flags if f["status"] not in ("confirmed", "rejected") or f["evidence_changed"]]
        elif status == "stale":
            flags = [f for f in flags if f["evidence_changed"]]
        elif status:
            flags = [f for f in flags if f["status"] == status]
        if named in ("yes", "no"):
            flags = [f for f in flags if bool(f["names_supplier"]) == (named == "yes")]
        if gov_body_id:
            flags = [f for f in flags if f["gov_body_id"] == gov_body_id]
        if q:
            ql = q.lower()
            flags = [f for f in flags if ql in " ".join(str(f.get(k) or "") for k in
                                                         ("title", "body_name", "subject_name", "gov_body_id",
                                                          "flag_id")).lower()]
        return sorted(flags, key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["detector_id"], -(f["score"] or 0)))

    def get_flag(self, flag_id: str) -> dict | None:
        f = self.wh.flag(flag_id)
        if not f:
            return None
        f = self._annotate([f])[0]
        f["decisions"] = self.store.decisions(flag_id)
        for d in f["decisions"]:
            d["decided_label"] = sast_label(d["decided_at_utc"])
        f["matched"] = self.wh.matched_records(f)
        shas = [e.get("sha256") for e in f["evidence"]]
        for _, rows in f["matched"]["tables"]:
            shas += [r.get("source_sha256") for r in rows]
        f["raw_files"] = self.wh.raw_files(shas)
        return f

    def decide(self, flag_id: str, reviewer: dict, decision: str, reason: str, notes: str | None,
               channel: str) -> dict:
        f = self.wh.flag(flag_id)
        if not f:
            raise wf.ReviewError("Unknown flag (not in the current build).")
        return self.store.decide(f, reviewer, decision, reason, notes, channel, self.wh.build_id())

    # ------------------------------------------------------------------ export
    def reviewed(self, include_unreviewed: bool = False) -> list[dict]:
        flags = {f["flag_id"]: f for f in self._annotate(self.wh.flags())}
        decs: dict[str, list[dict]] = {}
        for d in self.store.decisions():
            decs.setdefault(d["flag_id"], []).append(d)
        out = []
        for fid in sorted(set(flags) | set(decs)):
            f, ds = flags.get(fid), decs.get(fid, [])
            if not ds and not include_unreviewed:
                continue
            if f is None:   # decided earlier; flag not produced by the current build
                snap = json.loads(ds[-1]["flag_snapshot"])
                st = wf.replay(ds, snap.get("names_supplier", True))
                f = {"flag_id": fid, **snap, "body_name": None, "status": st.status, "evidence_changed": True,
                     "confirmed_by": [], "n_decisions": len(ds)}
            last = ds[-1] if ds else {}
            out.append({**{k: f.get(k) for k in EXPORT_COLS}, "in_current_build": fid in flags,
                        "confirmed_by": ";".join(f.get("confirmed_by") or []),
                        "last_decision": last.get("decision"), "last_reviewer": last.get("reviewer_username"),
                        "last_reason": last.get("reason"), "last_decided_at_sast": last.get("decided_at_sast"),
                        "n_decisions": len(ds)})
        return out


def _csv_safe(v):
    """Neutralise spreadsheet formula injection (=, +, -, @, tab, CR at the start of a cell)."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return "" if v is None else v


def to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXPORT_COLS, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: _csv_safe(r.get(k)) for k in EXPORT_COLS})
    return buf.getvalue()
