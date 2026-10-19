# ADR-0001: Build as a Grok Bot-hosted app (box pipeline + routines + Ops Bot + static public snapshot)
- Status: Accepted (prototype); revisit at public launch
- Date: 2026-10-19
- Deciders: L👀ty McFreely (owner), Grok Bot (proposer)

## Context
The user wants the prototype, and possibly the whole project, to be a "Grok Bot app". Grok Bot provides persistent Bots on a shared cloud computer with browser, filesystem and terminal, plus skills, scheduled/event routines, connectors/MCP and file storage (https://docs.x.ai/grok-bot/overview, https://docs.x.ai/grok-bot/skills-routines-and-automations). The docs don't describe a first-party way to publicly host a web app from the Bot's computer **[unverified that none exists]**. Grok Build (separate xAI product) publishes apps and dashboards with connectors and GitHub export (https://x.ai/news/grok-build-for-everyone). Community Grok Bot templates deploy via the Vercel connector (https://grokbotsdirectory.com/bots/website-builder-3Zzb23).

## Decision
- The **system of record** (pipeline, warehouse, API, internal UI) runs on the box.
- **Routines** run ingestion, DQ and release prep.
- A dedicated **Thusa Ops Bot** with skills is the operator and conversational front end.
- The **public dashboard is a static snapshot** deployed to an external host (Vercel or Grok Build; D-03), which keeps the box off the public internet.

## Consequences
- (+) No servers to run; box is private; public surface is static (small attack surface, cheap, fast).
- (+) Bot-native operation: routines, approvals and chat-based Q&A.
- (−) Single box: no HA (accepted; RTO/RPO in SLOs). Box credentials and files are shared across all of the user's Bots, so keep secrets minimal.
- (−) Public API (phase 2) needs a hosted runtime or a static JSON API.
- Follow-up: confirm whether Grok Bot later adds first-party app hosting or custom in-chat apps; if so, revisit.

## Alternatives
- Full Grok Build app: fast UI, but heavy ETL, PDF parsing and DuckDB pipelines fit poorly in a hosted app runtime **[unverified limits]**; it may still host the snapshot.
- Conventional cloud (VM + Postgres): more ops burden and cost for a prototype.
