# CHG-2026-048: Remove "relayed by Cavus" and close variants from the repo text

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-11-01 16:09, as reported to the author (PublicFunds) |
| Environment | Records only. No code, test or data change |
| Type | Standard. See "Tier" |
| CIs affected | `STATUS.md`, `changes/CAB-DECISION.md`, 18 RFCs in `itil/changes/`, `itil/registers/change-log.md`; this file |
| Linked records | CHG-2026-034, CHG-2026-036, CHG-2026-042, CHG-2026-043 |
| Rollback | Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>` |

## Decision
Remove "relayed by Cavus" and close variants from the repo text. Keep the facts. Use the words "as reported to the author (PublicFunds)". Never change GO quote text.

## Scope
The search was `git grep -i cavus` on origin/main 1108a54. It found 35 matches in 21 files. This change treats all of them as close variants: "relayed by Cavus", "as relayed by Cavus", "Cavus relayed", "Owner via Cavus", "Owner via Cavus backlog", "in Cavus's chat" and "requested by Cavus". After the change, `git grep -i cavus` finds only this record and the file name of this record in its change-log row.

## Rules applied
1. Each edit keeps the fact: who decided, when, and that the author got it second hand.
2. No text inside an owner GO quote changed. The GO quotes "Keep it as a standing approved change", "fix it", "GO on both" and the question "Merge both PublicFunds PRs to the live site?" are the same, byte for byte.
3. The reviewer note of Cassian (Build) is the same, word for word. Only its source line changed.
4. Three edits change a quote of record wording, not a GO quote (CHG-2026-034 lines 87 and 100, CHG-2026-036 line 31). They now point to this record.
5. Where "as reported to the author (PublicFunds)" was already present, the edit removes only "relayed by Cavus". This prevents a duplicate.

## Every edit
Line numbers are on origin/main 1108a54. The count is 1 for each line unless the row lists two lines.

| # | File | Line(s) | Old text | New text |
|---|---|---|---|---|
| 1 | `STATUS.md` | 10 | authorisation audit (requested by Cavus) | authorisation audit (request as reported to the author (PublicFunds)) |
| 2 | `STATUS.md` | 14 | ("fix it", in Cavus's chat) | ("fix it", as reported to the author (PublicFunds)) |
| 3 | `changes/CAB-DECISION.md` | 7 | Owner's words, relayed by Cavus: | Owner's words, as reported to the author (PublicFunds): |
| 4 | `changes/CAB-DECISION.md` | 28 | (15:30 SAST, relayed by Cavus) | (15:30 SAST, as reported to the author (PublicFunds)) |
| 5 | `changes/CAB-DECISION.md` | 59, 64 | (asked in Cavus's chat: | (as reported to the author (PublicFunds); question asked: |
| 6 | `itil/changes/CHG-2026-033-by-type-n-of-n.md` | 6 | chosen by delegation, relayed by Cavus (24 Oct 2026) | chosen by delegation, as reported to the author (PublicFunds) (24 Oct 2026) |
| 7 | `itil/changes/CHG-2026-034-option-a-headline-and-wording.md` | 6 | **Option A chosen by delegation, relayed by Cavus (24 Oct 2026); not a merge GO.** | **Option A chosen by delegation, as reported to the author (PublicFunds) (24 Oct 2026); not a merge GO.** |
| 8 | `itil/changes/CHG-2026-034-option-a-headline-and-wording.md` | 6 | Cavus relayed that as delegating | As reported to the author (PublicFunds), that answer delegated |
| 9 | `itil/changes/CHG-2026-034-option-a-headline-and-wording.md` | 11 | choice relayed by Cavus, 2026-10-24. | choice as reported to the author (PublicFunds), 2026-10-24. |
| 10 | `itil/changes/CHG-2026-034-option-a-headline-and-wording.md` | 87 | - The wording "relayed by Cavus" is kept as the owner's channel for the delegation; it is not changed here. | - The wording for the channel of the delegation is kept here. CHG-2026-048 later changed it to "as reported to the author (PublicFunds)". |
| 11 | `itil/changes/CHG-2026-034-option-a-headline-and-wording.md` | 92 | An independent review by Shipper, relayed by Cavus, was | An independent review by Shipper, as reported to the author (PublicFunds), was |
| 12 | `itil/changes/CHG-2026-034-option-a-headline-and-wording.md` | 100 | "chosen by delegation, relayed by Cavus (24 Oct 2026)"; that wording is unchanged. | "chosen by delegation, as reported to the author (PublicFunds) (24 Oct 2026)". CHG-2026-048 changed only the channel words. |
| 13 | `itil/changes/CHG-2026-036-cab-records.md` | 31 | the wording "relayed by Cavus" in CHG-2026-034; | the channel wording in CHG-2026-034 (reworded later by CHG-2026-048); |
| 14 | `itil/registers/change-log.md` | 52 | (chosen by delegation, relayed by Cavus; not a merge GO) | (chosen by delegation, as reported to the author (PublicFunds); not a merge GO) |
| 15 | `itil/changes/CHG-2026-018-cpi-update.md` | 5 | Owner via Cavus | Owner, as reported to the author (PublicFunds) |
| 16 | `itil/changes/CHG-2026-019-fuel-history-gaps.md` | 5 | Owner via Cavus | Owner, as reported to the author (PublicFunds) |
| 17 | `itil/changes/CHG-2026-020-fuel-lrp-label.md` | 5 | Owner via Cavus | Owner, as reported to the author (PublicFunds) |
| 18 | `itil/changes/CHG-2026-021-coast95-lrp-label.md` | 5 | Owner via Cavus | Owner, as reported to the author (PublicFunds) |
| 19 | `itil/changes/CHG-2026-023-inland95-ulp-label.md` | 5 | Owner via Cavus | Owner, as reported to the author (PublicFunds) |
| 20 | `itil/changes/CHG-2026-024-diesel-oct2022-note.md` | 5 | Owner via Cavus | Owner, as reported to the author (PublicFunds) |
| 21 | `itil/changes/CHG-2026-026-known-gaps-ke012.md` | 5 | Owner via Cavus backlog | Owner backlog, as reported to the author (PublicFunds) |
| 22 | `itil/changes/CHG-2026-027-fuel-2025-12-xlsx.md` | 5 | Owner via Cavus backlog | Owner backlog, as reported to the author (PublicFunds) |
| 23 | `itil/changes/CHG-2026-028-ke-jan2025-coast95.md` | 5 | Owner via Cavus backlog | Owner backlog, as reported to the author (PublicFunds) |
| 24 | `itil/changes/CHG-2026-029-wording-2025-12.md` | 5 | Owner via Cavus backlog | Owner backlog, as reported to the author (PublicFunds) |
| 25 | `itil/changes/CHG-2026-035-fuel-continuity.md` | 5 | Owner via Cavus backlog | Owner backlog, as reported to the author (PublicFunds) |
| 26 | `itil/changes/CHG-2026-040-evidence-guard.md` | 5 | Owner via Cavus backlog | Owner backlog, as reported to the author (PublicFunds) |
| 27 | `itil/changes/CHG-2026-041-guard-report.md` | 5 | Owner via Cavus backlog | Owner backlog, as reported to the author (PublicFunds) |
| 28 | `itil/changes/CHG-2026-042-merge-records-040-041.md` | 46 | Cassian (Build), relayed by Cavus, 31 Oct 2026 18:59 SAST, as reported to the author (PublicFunds) | Cassian (Build), 31 Oct 2026 18:59 SAST, as reported to the author (PublicFunds) |
| 29 | `itil/changes/CHG-2026-042-merge-records-040-041.md` | 50 | Cassian is now the pre-merge reviewer, as relayed by Cavus. | Cassian is now the pre-merge reviewer, as reported to the author (PublicFunds). |
| 30 | `itil/changes/CHG-2026-043-retro-review-042.md` | 17 | Cassian (Build), relayed by Cavus, 31 Oct 2026 18:59 SAST, as reported to the author (PublicFunds) | Cassian (Build), 31 Oct 2026 18:59 SAST, as reported to the author (PublicFunds) |
| 31 | `itil/changes/CHG-2026-043-retro-review-042.md` | 19 | Cassian is now the pre-merge reviewer, as relayed by Cavus. | Cassian is now the pre-merge reviewer, as reported to the author (PublicFunds). |
| 32 | `itil/registers/change-log.md` | 60 | Cassian (Build), relayed by Cavus, 31 Oct 2026 18:59 SAST, as reported to the author (PublicFunds) | Cassian (Build), 31 Oct 2026 18:59 SAST, as reported to the author (PublicFunds) |
| 33 | `itil/registers/change-log.md` | 60 | Cassian is now the pre-merge reviewer, as relayed by Cavus. | Cassian is now the pre-merge reviewer, as reported to the author (PublicFunds). |

## Tier
Standard. This change edits records and docs text only. It changes no code, test, detector, pipeline, data or page text.

## POPIA
No new personal data. The edits remove a name. They add none.

## Testing
- `uv run pytest` on this branch. Result is in the PR body.
- `git grep -i cavus` finds only this record and its change-log row.
- Quote check (author run): every double-quoted string that the diff removes is present again in the diff, except the three record-wording quotes in rule 4.
- Table pipes in `change-log.md` checked: each changed row keeps 6 cells.

## Risk
Low. Risk: a reader loses the channel of an old decision. The words "as reported to the author (PublicFunds)" keep that the source was second hand.

## How to revert
Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>`.
