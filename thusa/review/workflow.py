"""Review decision rules (pure functions; no I/O). See ADR-0008.

Statuses
  unreviewed              initial status of a flag that does not name a supplier or person
  pending human review    initial status of a flag that names a supplier or person (ADR-0005)
  awaiting second review  named flag confirmed by ONE reviewer; a second, different reviewer must confirm
  confirmed               confirmed (named flags: by two different reviewers on the same evidence)
  rejected                false positive
  needs more info         reviewer could not decide from the evidence
  escalated               referred to an admin; only an admin may then confirm or reject

Four-eyes: confirmations only count within the current "round" (since the last non-confirm decision) and only
when they were made on the same evidence hash as the flag has now. A rebuild that changes the evidence therefore
restarts the count, and a confirmed flag whose evidence changed is shown as stale and is not published.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

DECISIONS = {
    "confirm": "confirmed",
    "reject": "rejected",
    "needs_info": "needs more info",
    "escalate": "escalated",
}
DECISION_LABELS = {"confirm": "Confirm", "reject": "Reject (false positive)", "needs_info": "Needs more info",
                   "escalate": "Escalate"}
INITIAL = {True: "pending human review", False: "unreviewed"}
AWAITING = "awaiting second review"
STATUSES = ["unreviewed", "pending human review", AWAITING, "confirmed", "rejected", "needs more info", "escalated"]
REASON_MIN, REASON_MAX, NOTES_MAX = 10, 2000, 4000
REQUIRED_CONFIRMATIONS_NAMED = 2


class ReviewError(Exception):
    """Invalid input (exit code 2 / HTTP 422)."""
    code = "invalid"


class FourEyesError(ReviewError):
    """The four-eyes rule (or another workflow rule) forbids this decision (exit code 3 / HTTP 409)."""
    code = "workflow"


def evidence_hash(flag: dict) -> str:
    """Fingerprint of what the reviewer saw. Changes when a rebuild changes the numbers or the evidence."""
    material = {k: flag.get(k) for k in ("flag_id", "detector_id", "detector_version", "severity", "score", "title",
                                         "explanation", "names_supplier")}
    ev = flag.get("evidence_json")
    material["evidence"] = json.loads(ev) if isinstance(ev, str) else ev
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class State:
    status: str
    round_confirmers: tuple[tuple[str, str], ...]   # (reviewer username, evidence hash) since last non-confirm
    last_evidence_hash: str | None
    n_decisions: int

    def confirmers_on(self, ev_hash: str) -> list[str]:
        return sorted({u for u, h in self.round_confirmers if h == ev_hash})


def replay(decisions: list[dict], names_supplier: bool) -> State:
    """Current state from the ordered decision log of one flag (stored new_status is authoritative)."""
    status, confirmers, last_hash = INITIAL[bool(names_supplier)], [], None
    for d in decisions:
        if d["decision"] == "confirm":
            confirmers.append((d["reviewer_username"], d["evidence_hash"]))
        else:
            confirmers = []
        status, last_hash = d["new_status"], d["evidence_hash"]
    return State(status, tuple(confirmers), last_hash, len(decisions))


def is_stale(state: State, current_hash: str | None) -> bool:
    """Decided on evidence that has since changed (or the flag no longer exists in the current build)."""
    return state.n_decisions > 0 and state.last_evidence_hash != current_hash


def validate_text(reason: str | None, notes: str | None) -> tuple[str, str | None]:
    reason = (reason or "").strip()
    notes = (notes or "").strip() or None
    if len(reason) < REASON_MIN:
        raise ReviewError(f"A reason is required (at least {REASON_MIN} characters).")
    if len(reason) > REASON_MAX:
        raise ReviewError(f"Reason is too long (max {REASON_MAX} characters).")
    if notes and len(notes) > NOTES_MAX:
        raise ReviewError(f"Notes are too long (max {NOTES_MAX} characters).")
    for t in (reason, notes or ""):
        if any(ord(c) < 32 and c not in "\n\r\t" for c in t):
            raise ReviewError("Control characters are not allowed.")
    return reason, notes


def next_status(state: State, decision: str, reviewer: str, role: str, names_supplier: bool,
                current_hash: str) -> str:
    """Validate a decision against the rules and return the status it produces. Raises ReviewError/FourEyesError."""
    if decision not in DECISIONS:
        raise ReviewError(f"Unknown decision {decision!r}; use one of {', '.join(DECISIONS)}.")
    stale = is_stale(state, current_hash)
    if state.status == "escalated" and decision in ("confirm", "reject") and role != "admin":
        raise FourEyesError("This flag is escalated: only an admin may confirm or reject it.")
    if decision != "confirm":
        return DECISIONS[decision]
    if state.status == "confirmed" and not stale:
        raise FourEyesError("This flag is already confirmed on the current evidence.")
    if not names_supplier:
        return "confirmed"
    prior = [u for u in state.confirmers_on(current_hash)]
    if reviewer in prior:
        raise FourEyesError("Four-eyes rule: you have already confirmed this flag. A second, different reviewer "
                            "must confirm it.")
    return "confirmed" if len(prior) + 1 >= REQUIRED_CONFIRMATIONS_NAMED else AWAITING
