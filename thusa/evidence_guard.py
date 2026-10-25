"""CHG-2026-040 (CSI-053): nightly evidence guard. Pure functions of two coverage.json documents; no I/O, no database.

DEFINITION. For a data type and a financial year, the evidence count is the number of municipalities whose cell is 'P' (fully
present) in coverage.json. The guard compares the candidate (about to be published) with the previously published file:

  FAIL (blocks the publish)  a data type + year whose previous count was >= 1 and whose candidate count is 0, unless the allow
                             list has an entry for it. Nothing else fails.
  WARN (never blocks)        the count fell by more than WARN_DROP_SHARE of the previous count (previous count >= WARN_MIN_PREVIOUS).
  NOTE                       no previous file (first run): the guard passes and says so.

It looks at counts only. It does not say why data is gone, and it never reads names, amounts or flags (POPIA: aggregate counts).
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import date

# WARN threshold: a fall of MORE than this share of the previous count of fully present municipalities is reported. Default 10%.
# Basis (25 Oct 2026): there is no night-to-night history to measure (coverage.json was committed once, on 19 Oct, and the eight
# later nightly exports left it unchanged; the six builds in changes.json all show 75.7%), so the nearest measure is the spread between neighbouring
# financial years of the published file, for counts of 20 or more: falls of 0% to 2.4% for budget, audited actuals and UIFW, and
# 9.0% for audit opinion (256 -> 233, 2019/20 to 2020/21, which then rises 9.4% the next year).
# 10% sits just above that spread (an expected change is not a warning) and well below the X1 scratch case (100 of 247 emptied = 40.5%).
WARN_DROP_SHARE = 0.10
# A small count moves in whole cells (tender awards 2019/20 has 1 fully present municipality, 2021/22 has 3), so a share of it means
# little: the drop warning is only for previous counts of at least this many municipalities.
WARN_MIN_PREVIOUS = 20

DATA_TYPES = ("budget", "actual_audited", "uifw", "audit_opinion", "procurement")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class EvidenceGuardError(ValueError):
    """The coverage document or the allow list is malformed. The caller must treat this as a block (fail closed)."""


def present_counts(cov: Mapping) -> dict[tuple[str, int], int]:
    """(data_type, year) -> number of entities whose cell is 'P'. Raises EvidenceGuardError on a malformed document."""
    try:
        years, types, ents = list(cov["years"]), list(cov["data_types"]), list(cov["entities"])
    except (KeyError, TypeError) as exc:
        raise EvidenceGuardError(f"coverage document lacks years, data_types or entities: {exc!r}") from exc
    counts = {(t, y): 0 for t in types for y in years}
    for e in ents:
        for t in types:
            cells = e["c"][t] if isinstance(e, Mapping) and isinstance(e.get("c"), Mapping) and t in e["c"] else None
            if not isinstance(cells, str) or len(cells) != len(years):
                raise EvidenceGuardError(f"entity {e.get('id') if isinstance(e, Mapping) else e!r}: cells for {t} do not match the years")
            for y, ch in zip(years, cells):
                counts[(t, y)] += ch == "P"
    return counts


def check_allow(allow: Iterable[Mapping] | None) -> dict[tuple[str, int], str]:
    """Validate the allow list: {(data_type, year): reason}. Every entry needs data_type, year, reason and an ISO date."""
    out: dict[tuple[str, int], str] = {}
    for i, a in enumerate(allow or []):
        if not isinstance(a, Mapping):
            raise EvidenceGuardError(f"allow entry {i} is not a mapping")
        t, y, reason, d = a.get("data_type"), a.get("year"), a.get("reason"), a.get("date")
        if t not in DATA_TYPES or not isinstance(y, int) or isinstance(y, bool):
            raise EvidenceGuardError(f"allow entry {i}: data_type must be one of {DATA_TYPES} and year an integer")
        if not isinstance(reason, str) or not reason.strip():
            raise EvidenceGuardError(f"allow entry {i} ({t} {y}): a reason is required")
        d = d.isoformat() if isinstance(d, date) else d          # YAML reads an unquoted 2026-11-02 as a date
        if not isinstance(d, str) or not _DATE.match(d):
            raise EvidenceGuardError(f"allow entry {i} ({t} {y}): date must be YYYY-MM-DD")
        try:
            date.fromisoformat(d)
        except ValueError as exc:
            raise EvidenceGuardError(f"allow entry {i} ({t} {y}): not a real date: {d}") from exc
        if (t, y) in out:
            raise EvidenceGuardError(f"allow entry {i}: {t} {y} is listed twice")
        out[(t, y)] = reason.strip()
    return out


def evidence_guard(previous: Mapping | None, candidate: Mapping, allow: Iterable[Mapping] | None = None,
                   warn_share: float = WARN_DROP_SHARE, min_previous: int = WARN_MIN_PREVIOUS) -> dict:
    """Compare the candidate coverage with the previously published one. Returns
    {"status": "pass"|"fail", "empty": [...], "allowed": [...], "stale_allow": [...], "drops": [...], "notes": [...]},
    each list item a dict of aggregate counts. status is "fail" only when `empty` is not empty."""
    allowed = check_allow(allow)
    cand = present_counts(candidate)
    if previous is None:
        return {"status": "pass", "empty": [], "allowed": [], "drops": [], "stale_allow": [],
                "notes": ["no previous published coverage.json (first run): evidence guard skipped"]}
    prev = present_counts(previous)
    empty, ok, drops = [], [], []
    for (t, y), before in sorted(prev.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        after = cand.get((t, y), 0)
        item = {"data_type": t, "year": y, "before": before, "after": after}
        if before >= 1 and after == 0:
            if (t, y) in allowed:
                ok.append(item | {"reason": allowed[(t, y)]})
            else:
                empty.append(item)
        elif before >= min_previous and (before - after) / before > warn_share:
            drops.append(item | {"share": round((before - after) / before, 3)})
    stale = [{"data_type": t, "year": y, "reason": r, "after": cand.get((t, y), 0)}
             for (t, y), r in sorted(allowed.items()) if cand.get((t, y), 0) >= 1]
    notes = [f"BLOCK: {d['data_type']} {d['year']}: {d['before']} fully present municipalities before, 0 now" for d in empty]
    notes += [f"allowed: {d['data_type']} {d['year']}: {d['before']} before, 0 now ({d['reason']})" for d in ok]
    notes += [f"warn: {d['data_type']} {d['year']}: {d['before']} -> {d['after']} ({d['share']:.1%} fewer)" for d in drops]
    notes += [f"warn: allow entry {d['data_type']} {d['year']} is no longer needed ({d['after']} present again): remove it" for d in stale]
    return {"status": "fail" if empty else "pass", "empty": empty, "allowed": ok, "drops": drops, "stale_allow": stale,
            "notes": notes}
