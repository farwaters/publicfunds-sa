# ADR-0008: Human review workflow, four-eyes rule and a separate append-only review store
- Status: Proposed (accept with the merge of CHG-2026-003)
- Date: 2026-10-19
- Amends: ADR-0005 (whose `open → reviewed → published` flow becomes the statuses below)

## Context
v0.1.0 produces 335 automated flags, 35 of which name a supplier (D3, D4). ADR-0005 forbids publishing those
before human review, but there was no way to record a review. Reviews must:
- survive the nightly warehouse rebuild, because `thusa build` recreates `data/thusa.duckdb` and swaps it in atomically;
- be attributable and tamper-evident (RSK-001 defamation, RSK-017 reviewer misuse);
- be writable by both the web app and the `pf` CLI that the Grok Bot drives. DuckDB allows only one writer process.

## Decision
1. **Separate review store:** SQLite at `data/review/review.sqlite` (WAL mode, file mode 0600, directory 0700),
   outside the rebuilt warehouse. It is keyed on the deterministic `flag_id`, which is
   sha256(detector | subject | body | period)[:16].
2. **Append-only audit trail:** every decision is a row in `decision`. Triggers refuse UPDATE and DELETE on
   `decision` and `reviewer_event`. Each row carries `prev_hash` and `record_hash` (a SHA-256 chain), so edits that
   bypass the triggers are detected by `pf review verify`, `/healthz` and `/audit`.
   Each row records the reviewer, the role, UTC and SAST timestamps, the previous and new status, a mandatory
   reason (10–2000 characters), optional notes, the channel (web/api/cli/bot), the build id, and the
   **evidence hash** of what the reviewer saw.
3. **Statuses:**
   - Initial: `unreviewed`, or `pending human review` when the flag names a supplier or person.
   - Decisions: confirm → `confirmed` (or `awaiting second review`); reject → `rejected`;
     needs_info → `needs more info`; escalate → `escalated`.
4. **Four-eyes:** a named-supplier flag becomes `confirmed` only when **two different reviewers** confirm it
   **on the same evidence hash** within the current round. A non-confirm decision restarts the round.
   The same person cannot confirm twice, and an admin counts as one reviewer.
   Once a flag is `escalated`, only an admin may confirm or reject it.
5. **Stale reviews:** if a rebuild changes a flag's evidence, earlier decisions stay in the log, but the flag shows
   `evidence changed`. Pending confirmations stop counting, and a confirmed flag is not published until it is
   re-confirmed.
6. **Publication:** `dist/public/` contains only flags that are `confirmed` with an unchanged evidence hash.
   - `config/publication.yaml` can switch other flags from `exclude` (the default) to `label` ("unreviewed lead").
   - Named-supplier flags are never shown unconfirmed, whatever the setting.
   - Reviewer names and notes are never published.
7. **Identity:**
   - Accounts are created only by an admin through `pf reviewer add` (local shell); there is no self sign-up.
   - Passwords use scrypt; tokens and sessions are stored as SHA-256 hashes only.
   - Web sessions are HttpOnly, SameSite=Strict cookies with CSRF tokens.
   - Bearer tokens are for the API and CLI.
   - Login is rate-limited (5 failures per user or 20 per IP in 15 minutes).

## Consequences
- (+) Reviews outlive rebuilds and detector re-runs. The trail is attributable and tamper-evident, and the public
  snapshot cannot leak unreviewed allegations.
- (−) It is a second datastore to back up. RB-04 and the backup plan D-05 must include `data/review/`.
- (−) Anyone with shell access to the box can bypass the app; the hash chain detects edits but does not prevent
  them. The chain head should be anchored in each release record (REL checklist).
- (−) Four-eyes needs at least two active reviewers before any named flag can be published.
- (−) A bot acting with a human's token acts as that human. The skill (docs/bot/review-skill.md) requires the human's
  explicit instruction for every decision, and the bot must never hold two humans' tokens to satisfy four-eyes alone.
