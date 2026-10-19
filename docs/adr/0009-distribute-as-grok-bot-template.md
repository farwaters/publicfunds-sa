# ADR-0009: Distribute Thusa as the "PublicFunds Bot" Grok Bot template; the bot chat is the primary UI; no public web hosting in the MVP
- Status: Accepted (owner clarification, 19 Oct 2026 11:21 SAST); **partly superseded by ADR-0010** (19 Oct 2026 17:47 SAST): the public GUI is now a Grok Build app; the template remains the power-user/reviewer version
- Date: 2026-10-19
- Supersedes: decisions **D-03** (public hosting of snapshots) and **D-14** (remote access to the review app);
  ADR-0001 decision (d) "static public snapshot deployed to an external host"; and the "public site" part of ADR-0003
- Amends: ADR-0001 (the Ops Bot becomes the product's front end), ADR-0003 (the snapshot is a file artefact, not a site)

## Context
The owner clarified that this is a **Grok Bot app**: it is distributed and accessed through a Grok Bot template share
link (`grokbot://…`), not as a hosted website. Earlier designs assumed a public static site (Vercel or Grok Build,
D-03) and asked how remote reviewers would reach the review web app (D-14). Both assumptions no longer hold.

## Decision
1. **Distribution:** users import the **PublicFunds Bot** template via its Grok Bot link: `https://x.ai/bot/7Hr1hnJPXqOQbMmUZ7mTi` (the
   owner will fill this in). The template carries the bot's instructions and skills, plus a pointer to this
   repository. It carries **no data, review database, credentials or tokens**. Each importer's bot builds its own
   warehouse on its own box with `thusa run` and creates its own reviewer accounts.
   - How Grok Bot templates are packaged (which files and settings travel with a template) is **[unverified]**.
     `docs/bot/template.md` lists what we intend to include; check it against the platform when the link is created.
2. **Primary UI = the bot chat.** The bot answers coverage and flag questions from the warehouse, explains flags
   with their evidence, and records review decisions through the `pf` CLI (JSON). It does this only on the user's
   explicit instruction (skill `thusa-review`).
3. **Secondary UI = the local review web app** (`pf serve`, 127.0.0.1:8765). It is a local tool on the box that the
   bot can open in **its own box browser** for the user: heatmaps, a long queue, side-by-side evidence.
   - The user watches or takes over through the bot's desktop and signs in themselves. The bot never types or
     reveals a password.
   - It stays bound to localhost. Exposing it to the internet is **not an MVP requirement** (D-14 superseded).
4. **No public web hosting in the MVP** (D-03 superseded). `dist/public/` is still built, with confirmed flags only
   (ADR-0008). It is a file artefact the bot can attach in chat or export, not a website.
   Any later public hosting is a new Normal-high change with its own ADR.

## Consequences
- (+) No public attack surface, no hosting cost, no DNS/TLS operations. RSK-018 (exposure of unreviewed
  allegations) falls further.
- (+) It fits Grok Bot's model: routines, skills, chat and approvals live where the users already are.
- (−) Reach is limited to people who import the bot; there is no anonymous public audience. Accepted for the MVP.
- (−) Every importer runs the pipeline and holds their own review database, so reviews are not shared across
  importers. Shared reviewing (e.g. a newsroom) means people using the same bot/box, or a later sync design.
- (−) Template contents must be checked on every update so that no secrets or data ride along (RSK-020).
- Follow-ups:
  - Fill in `https://x.ai/bot/7Hr1hnJPXqOQbMmUZ7mTi` (README, docs/bot/template.md, CI-102).
  - Verify the template packaging.
  - Decide whether a later phase needs public hosting (new ADR).
