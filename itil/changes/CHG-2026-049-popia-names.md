# CHG-2026-049: Remove agent and owner names from tracked files, and add a POPIA name guard

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-11-01 18:43, as reported to the author (PublicFunds) |
| Environment | Records, one test file and a new guard test. No pipeline, detector or data change |
| Type | Normal-high (POPIA). See "Tier" |
| CIs affected | 33 tracked files (see "Counts per file"), `.gitignore`, `tests/test_popia_names.py`, `tests/popia_names.sha256`, `tests/popia_allow.sha256`; this file |
| Linked records | CHG-2026-048 (file renamed), PR #45 (CHG-2026-046), PR #46 (CHG-2026-047) |
| Rollback | Close the PR. If the PR is merged, run `git revert -m 1 <merge commit>` |

## Decision

The owner's rule, word for word: "POPIA, personal information and doxxing. None of my githubs, agents, anything I have named or made for me should be public. grokforum github and grokforum.site are however pretty public-use, as is publicfunds. We'll figure this out one input or reply at a time".

## Tier

Normal-high. The change is POPIA work. It needs the owner and a second reviewer, or the owner and a 24 h cool-off. A bot approval never fills a human slot. No reviewer PASS in this record is owner approval.

## Change

1. Each agent name and the owner's personal name is replaced with a role word. The mapping is:
   - The first expert reviewer becomes "Reviewer A".
   - The shadow, drift and POPIA reviewer becomes "Reviewer B".
   - The independent copy reviewer becomes "Reviewer C".
   - The pre-merge reviewer from 31 Oct 2026 becomes "Reviewer D".
   - The agent that passed on owner words becomes "the orchestrator".
   - The owner's personal name becomes "the owner".
2. The letters keep the facts apart. A reader can still see which reviewer did which check. The letters are labels, not names.
3. The test helper `mutate_*_case` and two parametrize labels in `tests/test_unknowns_by_type_constant.py` are renamed. The test logic does not change.
4. The CHG-2026-048 RFC file is renamed with `git mv` to `itil/changes/CHG-2026-048-remove-relay-wording.md`. Its title and its old-text column now use role words. Its change-log row no longer gives the full branch name.
5. A new test, `tests/test_popia_names.py`, fails if a protected name occurs in a tracked file path or line. It reports the file and line, never the word.
6. The names are stored only as sha256 hashes of lowercased tokens in `tests/popia_names.sha256`.
7. An optional, gitignored file `.popia-names.local` adds plain names on the owner's computer. Use it for handles that must not be hashed in public.
8. `public-data/` is out of scope. It is source-agency data. It contains public place and supplier names that share words with the list.
9. Two-word public names are allowed by hash in `tests/popia_allow.sha256`.

### GO quotes with a bracketed role

The GO quote text is unchanged, except for the agent names inside it. This quote had two agent names. Each name became a bracketed role.

| File | Line | Change inside the quote |
|---|---|---|
| `itil/changes/CHG-2026-040-evidence-guard.md` | 108 | "accept [Reviewer A] and [Reviewer B] as the second reviewer" |
| `itil/changes/CHG-2026-042-merge-records-040-041.md` | 23 | same quote, same change |
| `itil/registers/change-log.md` | 58 | same quote, same change |

No other GO quote had a protected name.

### Kept on purpose (open questions for the owner)

- "Grok Build" (41 matches, 15 files). Each match names the xAI product used for hosting. No match uses it as a person or agent identity. The file names `GROK_BUILD_PROMPT.md` and ADR-0010 stay.
- "grokforum". Every match is the public domain `publicfunds.grokforum.site`. The owner allows it.
- "Grok Bot", "PublicFunds Bot" and "Thusa Ops Bot". These name the product and the app's bot role. The owner allows "publicfunds". Decide if "Thusa Ops Bot" must change.
- "farwaters" in URLs such as `https://farwaters.github.io/publicfunds-sa/` and the repo path. It is the GitHub account name. See "History and GitHub options".

## Counts per file

The count is the number of replacements in each file.

| File | Replacements |
|---|---|
| `changes/CAB-DECISION.md` | 49 |
| `docs/adr/0001-grok-bot-hosted-app.md` | 1 |
| `docs/design/application-design.md` | 2 |
| `itil/changes/CHG-2026-019-fuel-history-gaps.md` | 2 |
| `itil/changes/CHG-2026-020-fuel-lrp-label.md` | 3 |
| `itil/changes/CHG-2026-021-coast95-lrp-label.md` | 3 |
| `itil/changes/CHG-2026-022-fuel-split-row.md` | 2 |
| `itil/changes/CHG-2026-023-inland95-ulp-label.md` | 3 |
| `itil/changes/CHG-2026-024-diesel-oct2022-note.md` | 2 |
| `itil/changes/CHG-2026-026-known-gaps-ke012.md` | 2 |
| `itil/changes/CHG-2026-027-fuel-2025-12-xlsx.md` | 4 |
| `itil/changes/CHG-2026-028-ke-jan2025-coast95.md` | 17 |
| `itil/changes/CHG-2026-029-wording-2025-12.md` | 4 |
| `itil/changes/CHG-2026-030-fuel-notes-on-dashboard.md` | 23 |
| `itil/changes/CHG-2026-031-rfc-records-wording.md` | 28 |
| `itil/changes/CHG-2026-032-live-site-check.md` | 55 |
| `itil/changes/CHG-2026-034-option-a-headline-and-wording.md` | 5 |
| `itil/changes/CHG-2026-035-fuel-continuity.md` | 14 |
| `itil/changes/CHG-2026-036-cab-records.md` | 15 |
| `itil/changes/CHG-2026-037-status-records.md` | 13 |
| `itil/changes/CHG-2026-038-status-030.md` | 12 |
| `itil/changes/CHG-2026-039-rfc-wording-followup.md` | 40 |
| `itil/changes/CHG-2026-040-evidence-guard.md` | 10 |
| `itil/changes/CHG-2026-041-guard-report.md` | 2 |
| `itil/changes/CHG-2026-042-merge-records-040-041.md` | 8 |
| `itil/changes/CHG-2026-043-retro-review-042.md` | 2 |
| `itil/changes/CHG-2026-044-state-backup.md` | 1 |
| `itil/changes/CHG-2026-048-remove-relay-wording.md` | 63 |
| `itil/itil-practice-map.md` | 1 |
| `itil/registers/change-log.md` | 50 |
| `itil/service-definition.md` | 1 |
| `sa_public_funds_landscape.md` | 1 |
| `tests/test_unknowns_by_type_constant.py` | 10 |
| **Total** | **448** |

## History and GitHub options (not acted on)

This change edits only the current tree. The names stay in places that a tree change cannot reach. The scan found:

- **Commit messages.** 28 commits on all refs name agents (Reviewer B 21 matches, Reviewer A 22, Reviewer D 3, the orchestrator 4).
- **Commit authors.** 126 commits have the author "Grok Bot (for <owner's personal name>)". 27 commits have the GitHub account's display name, which is a personal name. One commit has "Grok Bot (for farwaters)".
- **Tag annotations.** 6 of 29 tags (snapshot-2026-10-23-1630, -1702, -1745, -1753, -1906, -1907) have the owner's personal name in the tagger line.
- **Old blobs.** Every earlier version of the edited files keeps the names.
- **Branch names.** The remote branch for PR #47 has the orchestrator's name in it.
- **GitHub.** PR titles, PR bodies, PR comments and review text can name agents. They are outside git.

Options:

1. **Leave it.** No risk to the repo. The names stay readable in `git log` and on GitHub. The guard stops new matches in tracked files.
2. **Rewrite the history.** Use `git filter-repo` with a message and mailmap callback, then force-push all branches and tags. This is destructive. It needs explicit owner approval. It changes every sha, so the snapshot tags, the RFC sha references and the live-site check records break. Forks and clones keep the old history. GitHub keeps old PR refs (`refs/pull/*`) until GitHub Support removes them.
3. **Move to a fresh repo under the grokforum org.** Push one squashed commit of the cleaned tree. Archive or make private the old repo. This keeps the old repo intact as a private record. The public URL changes from `farwaters.github.io` to the grokforum org or `publicfunds.grokforum.site` only. The Pages setup, the bot template link and `scripts/check_live.py` need updates.
4. **Delete the remote branch name.** Deleting the PR #47 branch on GitHub removes one name. That is a delete outside the box, so it needs the owner's approval.

The account name "farwaters" is the owner's GitHub account. Option 3 is the only option that removes it from the public URLs. Options 1 and 2 keep it.

## Effect on open PRs

- **PR #45 (CHG-2026-046, head d0cc443).** Its change-log rows for CHG-2026-045 and CHG-2026-048 contain two agent names ("... PASS, ... PASS"). It also links the old CHG-2026-048 file name and branch name. After this PR merges, #45 must merge main, take this PR's file name, and use "Reviewer D PASS, the orchestrator PASS" or bracketed roles. Otherwise the guard fails.
- **PR #46 (CHG-2026-047, head 222e622).** It adds no protected name. It is based on an older main, so it must merge main before it merges.

## Testing

- `uv run pytest`: see the PR body for the counts.
- The guard test has a self-test with a planted fake name and a planted allowed two-word name.
- `git grep -i -w` for each protected name, outside `public-data/`, finds 0 matches.

## Risk

- Low for the code. Only test names change.
- The hash list is public. A short or common name can be found again by a dictionary attack on the hashes. The hashes stop casual reading only. Put a sensitive handle in `.popia-names.local` instead.
- A new data word that matches a list name outside `public-data/` fails the suite. Add its two-word form to the allow list.

## How to revert

Run `git revert -m 1 <merge commit>`. That restores the names, so do it only with the owner's approval.
