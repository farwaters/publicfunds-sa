# @DiscoveringAI: recent reposts on going beyond vibe coding

Retrieved via the X API on 19 Oct 2026 (~09:05 SAST). Account: @DiscoveringAI ("Tales From Ancient AI", user id 1695786676797210624). Its recent "reposts" are **quote-posts** with the body ". <link>". No plain retweets appeared in the latest 25 posts. The three most recent quote-reposts on strengthening AI-built software beyond vibe coding are listed below, newest first, with one further related quote-repost.

## P1 — @ghumare64, 17 Oct 2026 07:46 SAST
- Original: https://x.com/ghumare64/status/2111332908657148356
- Repost: https://x.com/DiscoveringAI/status/2111775575069086138 (18 Oct 2026 13:05 SAST)
- Content: "Who's gonna tell vibe coders about…", a 198-item list of engineering concepts:
  - **security:** SQLi, XSS, CSRF, CORS, SSRF, IDOR, path traversal, CSP, security headers, input validation, server-side authorisation, RLS, least privilege, RBAC, secrets management, `.env` in `.gitignore`, key rotation, secret scanning, hashing, salting, bcrypt/Argon2, JWT expiry, MFA, brute-force protection, dependency vulnerabilities, supply-chain attacks, threat modelling
  - **data:** indexes, EXPLAIN ANALYZE, N+1, connection pooling, migrations and down migrations, transactions/ACID, constraints, soft deletes, cursor pagination, backups, *testing your restores*, PITR, CDC, outbox
  - **distributed systems:** CAP, consistency, idempotency-adjacent topics, retries/jitter, backpressure, DLQs
  - **operations:** health checks, graceful shutdown, DR, RTO/RPO, SLAs/SLOs/error budgets, incident response, on-call, runbooks, postmortems, structured logging, tracing/OpenTelemetry, correlation IDs, alert fatigue
  - **delivery:** IaC, GitOps, blue-green/canary, rollbacks, feature flags, environment parity, staging, 12-factor, image scanning, semantic versioning, lockfiles, reproducible builds, branch protection

## P2 — @ClaudeDevs, 16 Oct 2026 20:54 SAST
- Original: https://x.com/ClaudeDevs/status/2111168901723906176
- Repost: https://x.com/DiscoveringAI/status/2111317158814777408 (17 Oct 2026 06:43 SAST)
- Linked article: "How the Claude Code team does code review" (Addy Osmani, Morgan Westlee Lunt, Qing Wang; published 15 Oct 2026) — https://claude.dev/blog/solving-code-review-at-anthropic/
- Claim: merged PRs more than doubled June→September while the reverted share fell by more than 40%.
- Practices:
  - Verify before review: give the agent runnable checks and make it show output; fresh-context subagent review.
  - Short `CLAUDE.md` (stack, conventions, goals, non-goals) and `REVIEW.md` ("what failure looks like here", cap nits, file+line evidence).
  - AI review on every PR; findings verified by multiple agents; each finding fixed or resolved with a reason.
  - Separate blocking security review.
  - CI checks; PR template with Testing / Risk / How to revert.
  - **Risk tiers set by the change, not the author** (low = no human; medium = 1; high = 2); trusted-author lists; a bot approval never replaces a human one; approval is per commit.
  - Merge queue, feature flags, internal use first, staged releases, fast rollback, on-call.
  - **Incidents and reverts as an eval set** run daily; measure reviewer noise.
  - **Cap review rounds at 3**, diff-only re-review, flag the class of bug.
  - Humans keep decisions about direction, risky code, architecture, reading evidence and ownership. "You land it, you own it."

## P3 — @mardehaym, 15 Oct 2026 14:12 SAST
- Original: https://x.com/mardehaym/status/2110705357492203564
- Repost: https://x.com/DiscoveringAI/status/2110961073717215702 (16 Oct 2026 07:08 SAST)
- Content: a long "before it touches a paying customer" checklist. Highlights:
  - **data model and money:** a designed schema; money as integers; timezones stored right
  - **auth:** sessions, MFA recovery, RBAC, IDOR checks, tenant isolation, rate limits
  - **migrations and backups:** migrations forward and back without locking tables; indexes; pooling; nightly backups with **tested restores**; PITR; soft deletes
  - **input safety:** server-side validation; apostrophes, emoji and RTL text in every field
  - **secrets and dependencies:** secrets out of code, repo **and AI chat history**; rotate keys the AI pasted; **confirm every package the AI installed exists**; dependency scanning
  - **web security:** OWASP; CORS; security headers; encryption; least privilege incl. for the AI agent; audit logs without secrets
  - **delivery:** environments that match, IaC, CI tests before deploy, one-click rollbacks, feature flags
  - **jobs and cost:** background jobs, retries with backoff, DLQs, cost alerts for runaway agent loops
  - **operations:** structured logs, error tracking, external uptime checks, tuned alerts, runbooks, postmortems that change something, status page
  - **testing:** unit/integration/E2E/load/regression tests
  - **AI-specific:** prompt-injection protection, evals for model updates, model fallback, human approval for irreversible AI actions
  - **people and process:** readable code, code review, branching strategy, monthly dependency upgrades, ADRs, a README that gets someone running in < 1 h, accounts/repos in the company's name, bus factor > 1
  - plus the human roles still needed

## Related (fourth) — @Voxyz_ai, 13 Oct 2026 21:00 SAST
- Original: https://x.com/Voxyz_ai/status/2110083153930920113
- Repost: https://x.com/DiscoveringAI/status/2111323433279635484 (17 Oct 2026 07:08 SAST)
- Content: before shipping a vibe-coded site, dispatch 4 read-only subagents to check 20 performance items:
  - assets: WebP/AVIF images, lazy loading, fonts, third-party scripts
  - frontend: bundle analysis, dynamic imports, server-fetch the homepage, skeletons
  - database: index filtered columns, fix N+1, paginate, cache public responses only, background jobs
  - network: co-locate functions with the DB, static/ISR, parallelise calls, test on a low-end Android on slow 4G
  - measure Lighthouse ×3 median before and after; ask before removing dependencies or changing infrastructure
- It is about performance hardening rather than engineering discipline overall, so it is listed as related rather than one of the three.

**Judgement call:** "3 recent reposts" is read as P1–P3, the three most recent quote-reposts that are explicitly about hardening AI/vibe-coded projects. P4 also fits and is included for completeness. How these map into Thusa is in design §13.
