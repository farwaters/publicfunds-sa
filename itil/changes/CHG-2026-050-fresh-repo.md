# CHG-2026-050: Move PublicFunds to a fresh repo with clean history (DRAFT)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-11-01 18:57-18:58, as reported to the author (PublicFunds) |
| Status | **Draft.** Nothing in this RFC is done. No repo is created. No visibility is changed |
| Type | Normal-high (POPIA, hosting, CI of the live site) |
| Depends on | CHG-2026-049 (PR #48) merged |
| Linked records | CHG-2026-001, CHG-2026-004, CHG-2026-007, ADR-0011, CI-001, CI-105, CI-111 |
| Rollback | Per step, see "Rollback" |

## Decision

The owner's decision: move PublicFunds to a fresh repo, `grokforum/publicfunds-sa`, with clean history. The history has no owner names, agent names or personal account names. When the new repo is live, make `farwaters/publicfunds-sa` private. The git identity is now "Grok Bot (for the owner)".

## Tier

Normal-high. It needs the owner plus a second reviewer, or the owner plus a 24 h cool-off. A bot approval never fills a human slot.

## 1. Prerequisites (checked read-only, 1 Nov 2026 ~19:05 SAST)

| Check | Result |
|---|---|
| `gh auth status` | Logged in as the personal account (the current repo owner). Token scopes: `gist`, `read:org`, `repo`. No `admin:org`, no `workflow`, no `delete_repo` |
| `gh api orgs/grokforum` | **404. There is no organization named grokforum** |
| `gh api users/grokforum` | `{"login":"GrokForum","type":"User"}`. GrokForum is a **personal user account**, not an org |
| GrokForum public repos | `GrokForum/grokforum.site`, `GrokForum/GrokOS` |

**Blocker B1.** The gh token on the box belongs to a different account. It cannot create a repo under the GrokForum user account. Pick one option:

- **B1-a (recommended).** The owner signs in to gh on the box as GrokForum: `gh auth login` (scope `repo`, plus `workflow` if Actions come later). The repo is then `GrokForum/publicfunds-sa`.
- **B1-b.** The owner creates a GitHub organization (for example `grokforum-org`, because the name `grokforum` is taken by the user account) and adds an account with repo-create rights. A user account can also be converted to an org, but that is one-way. Do not convert without a separate decision.
- **B1-c.** The owner creates the empty repo `GrokForum/publicfunds-sa` in the web UI and adds the box account as a collaborator with Write. This leaks the personal account name in the collaborator list (private to admins) and in push events. Not recommended.

**Blocker B2.** The new owner account must be able to serve GitHub Pages with the custom domain. A custom domain can be on only one repo at a time.

## 2. Source tree

- Use the tree of `main` after PR #48 (CHG-2026-049) merges. Do not use #48's branch tree. Main can get nightly data commits after #48 merges.
- Freeze point: the sha of `origin/main` at the start of step S2. Record it here.
- Do not copy `.git`. Export the tree with `git archive <freeze sha> | tar -x -C /workspace/fresh-pf`.

## 3. The initial commit

1. `git init -b main` in `/workspace/fresh-pf`.
2. Commit once:
   `git -c user.name="Grok Bot (for the owner)" -c user.email=grokbot@localhost commit -m "PublicFunds SA: initial public release (clean history)"`.
3. Set both author and committer the same way. Use `GIT_AUTHOR_*` and `GIT_COMMITTER_*` env vars as well.
4. Do not copy tags. Create one annotated tag `snapshot-YYYY-MM-DD-HHMM` with the same identity, message "Initial snapshot (CHG-2026-050)".
5. The old snapshot tags and the old history exist only in the private old repo. Records that cite old shas stay true for that repo. Add one line to `README.md`: "Earlier history is kept in a private archive."

## 4. Guard check before the push

Run all of these in `/workspace/fresh-pf`. Stop on any failure.

1. `uv run pytest`. All pass, including `tests/test_popia_names.py`.
2. `git log --format='%an%n%ae%n%cn%n%ce%n%B' --all` piped into a scan with the same hash list as the guard (script: `python3 scripts/scan_meta.py`, to be added in the same tree, reusing `find_hits` from the test).
3. `git for-each-ref refs/tags --format='%(taggername) %(taggeremail) %(contents)'` through the same scan.
4. `git grep -i -n farwaters` must return 0 lines, except the two tests that assert the word is absent (`tests/test_improvements.py:94`, `tests/test_report_card.py:38`). Change those regexes to the hash check, or accept them as negative tests. Owner decides.
5. `git count-objects -v` shows one commit. `git rev-list --all --count` is 1.

## 5. Everything that points at the old account

| Item | Where | Exact change |
|---|---|---|
| Live site DNS | `publicfunds.grokforum.site` CNAME is `farwaters.github.io.` (TTL 3600, checked by DNS-over-HTTPS) | Change the CNAME to `grokforum.github.io.` at the DNS host of grokforum.site (A record 169.239.218.69; the registrar panel is not visible from the box). The owner does this |
| Pages source | Old repo Pages: legacy build, branch `main`, path `/`, cname `publicfunds.grokforum.site` | New repo: `gh api -X POST repos/GrokForum/publicfunds-sa/pages -f source[branch]=main -f source[path]=/`, then `gh api -X PUT repos/GrokForum/publicfunds-sa/pages -f cname=publicfunds.grokforum.site -F https_enforced=true`. First remove the domain from the old repo: `gh api -X PUT repos/farwaters/publicfunds-sa/pages -f cname=` |
| `CNAME` file | repo root, `publicfunds.grokforum.site` | No change |
| Bootstrap | `scripts/bootstrap.sh:16,27` default `PF_REPO_URL` | `https://github.com/GrokForum/publicfunds-sa` |
| Publish script | `scripts/publish-public-data.sh:89-91` pushes to `origin` | No text change. Change the remote: `git -C /workspace/publicfunds remote set-url origin https://github.com/GrokForum/publicfunds-sa.git` |
| check_live | `scripts/check_live.py` default site is the custom domain; `--raw-url` is passed by callers | No code change. Change the `--raw-url` value in `itil/knowledge/runbooks.md:126,132` to `https://raw.githubusercontent.com/GrokForum/publicfunds-sa/main/public-data/v1/manifest.json` |
| CI | No `.github/workflows/` exists. `.github/CODEOWNERS` has a placeholder | No change. Leave CODEOWNERS placeholder |
| Issue forms | `.github/ISSUE_TEMPLATE/config.yml` links only gov.za and the custom domain | No change |
| Webhooks | `gh api repos/farwaters/publicfunds-sa/hooks` returns `[]` | None to move |
| Actions secrets | None found | None to move |
| Forks | 0 forks at check time | None |
| Nightly refresh routine | Works in `/workspace/publicfunds`, remote `origin` = old repo | Pause the routine during S2-S5. After S5, `remote set-url` as above, then `git fetch origin && git reset --keep origin/main` only after the owner approves (the local history differs from the new single commit). Simplest: re-clone into `/workspace/publicfunds` after moving the old folder to `/workspace/publicfunds-old`, keeping `data/` (gitignored) by moving it across |
| Restore check routine (CHG-2026-044) | Backups live outside the repo (`publicfunds-backups/`) | No change. Check the path still resolves after a re-clone |
| Merge worktree | `/workspace/merge-run/pf` | Re-clone from the new repo for later work |
| Bot template | `README.md:6,86`, `docs/bot/template.md` give `https://x.ai/bot/7Hr1hnJPXqOQbMmUZ7mTi` and the repo URL | Update the repo URL in the template's install instructions and memory facts to the new repo. Re-export the template. The owner publishes it |
| Docs with old URLs | `docs/adr/0010:26`, `docs/adr/0011:20`, `docs/design/application-design.md:486,500`, `docs/roadmap/improvements-2026-10.md:76`, `itil/changes/CHG-2026-004:11,28`, `CHG-2026-005:9`, `CHG-2026-007:16,25`, `itil/registers/change-log.md:5,8,9,20`, `itil/registers/ci-register.md:7`, `CHG-2026-049` | Replace `farwaters/publicfunds-sa` with `GrokForum/publicfunds-sa`, and `farwaters.github.io/publicfunds-sa` with `publicfunds.grokforum.site`. Old PR links (`/pull/2` etc.) become "PR #2 (old repo, private)". Do this in the new tree before the initial commit, under this CHG |
| CHG-2026-049 text | Names the old account as an open question | Mark the question closed by CHG-2026-050 |

## 6. Order of steps, with a check after each

| Step | Action | Check |
|---|---|---|
| S0 | Owner GO plus second reviewer or 24 h. Fix B1. Pause the nightly routine | `gh auth status` shows the new account; routine shows paused |
| S1 | Create empty public repo `GrokForum/publicfunds-sa` (no README, no licence) | `gh repo view GrokForum/publicfunds-sa --json visibility,isEmpty` gives PUBLIC, true |
| S2 | Build the tree (section 2), make the edits (section 5), commit (section 3) | Section 4 checks all pass |
| S3 | `git push origin main` and `git push origin <new tag>` | `git ls-remote` shows only `main` and the one tag at the expected shas |
| S4 | Remove the custom domain from the old Pages. Enable Pages on the new repo with the custom domain. Owner changes the CNAME | DoH shows CNAME `grokforum.github.io.`; `gh api repos/GrokForum/publicfunds-sa/pages` shows status `built` and the cname |
| S5 | `python3 scripts/check_live.py --expect-local public-data/v1/manifest.json --wait 600 --raw-url https://raw.githubusercontent.com/GrokForum/publicfunds-sa/main/public-data/v1/manifest.json` | Exit 0; HTTPS certificate valid |
| S6 | Repoint `/workspace/publicfunds` (section 5), resume the nightly | Next nightly pushes to the new repo; check_live OK |
| S7 | Recreate #45 and #46 (section 8). Close the old PRs with a link-free note | New PRs open |
| S8 | Make the old repo private: `gh repo edit farwaters/publicfunds-sa --visibility private --accept-visibility-change-consequences` | `gh repo view farwaters/publicfunds-sa --json visibility` gives PRIVATE; `curl -sI https://github.com/farwaters/publicfunds-sa` gives 404 when signed out; live site still OK |

## 7. Rollback

| Step | Rollback |
|---|---|
| S1 | Delete the new empty repo (needs `delete_repo` scope and owner approval), or leave it empty |
| S2 | Delete `/workspace/fresh-pf`. Nothing is public |
| S3 | Make the new repo private. Do not force-push. Fix forward with a new commit |
| S4 | Remove the custom domain from the new repo. Put it back on the old repo (`-f cname=publicfunds.grokforum.site`). Owner sets the CNAME back to `farwaters.github.io.`. DNS TTL is 3600 s, so allow up to 1 h |
| S5 | If check_live fails after 30 min, do the S4 rollback |
| S6 | `git remote set-url origin` back to the old URL (or move `/workspace/publicfunds-old` back) |
| S7 | Close the new PRs. Reopen the old ones |
| S8 | `gh repo edit farwaters/publicfunds-sa --visibility public --accept-visibility-change-consequences`. Stars and watchers lost on private are not restored |

## 8. Open PRs #45 and #46

- Both are on the old repo and are based on the old history. They cannot be merged into the new repo.
- Recreate each one as a new branch from the new `main`. Apply its diff with `git diff <old merge-base>..<old head> | git apply -3`. Commit with the new identity.
- #45 (CHG-2026-046): also apply the changes CHG-2026-049 requires (role words in its change-log rows, new CHG-2026-048 file name).
- #46 (CHG-2026-047): no name changes needed. Update its change-log row base.
- Copy the PR bodies without agent names. Do not copy review comments. Record the old PR number as "old repo #45" only.
- Reviews and PASS lines restart on the new heads. The old PASS covers only the old head.
- Close the old PRs before S8.

## 9. Risks

- **Caches.** GitHub keeps `refs/pull/*`, cached raw URLs and old Pages builds for a while. Private does not delete them from clones.
- **Forks and clones.** Any clone made while the repo was public keeps the full history. A private switch does not reach it. The fork count was 0 at check time.
- **Search engines and archives.** Google, Bing and the Wayback Machine can hold old pages, commits and the `farwaters.github.io` URLs. Request removal only if the owner asks (outside the box).
- **Site downtime.** The custom domain moves between repos and DNS changes. Expect up to 1 h of downtime or a certificate error in S4.
- **Pages on a private repo.** On a free plan, making the old repo private disables its Pages. The site must already be on the new repo (S4 before S8).
- **Lost records.** Old shas in RFCs point at the private repo. Readers outside cannot check them.
- **Data freshness.** The nightly is paused during the move. SLO-PD-1 allows 48 h. Keep the move under 24 h.
- **The hash list.** It moves with the tree. The dictionary-attack risk in CHG-2026-049 still applies.

## Testing

- Section 4 checks before S3.
- check_live after S4 and S6.
- `uv run pytest` on the new tree and on each recreated PR.

## How to revert

There is no merge commit. Revert per step with section 7. This RFC file itself reverts with `git revert -m 1 <merge commit>`.
