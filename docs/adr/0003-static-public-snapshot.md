# ADR-0003: Public site is a static snapshot per release; box API stays private in MVP
- Status: Accepted
- Date: 2026-10-19
## Context
Defamation/POPIA risk, single box, small team. Post P3 (@mardehaym) warns that zero-downtime deploys, rollbacks, CDN and security are all hard. A static site makes most of them trivial.
## Decision
Pre-render all public pages plus JSON/CSV/Parquet per release. Rollback = re-promote the previous snapshot.
## Consequences
(+) CDN-fast, secure, cheap, reproducible. (−) No live search beyond a client-side index; personalised alerts need phase-2 infrastructure.
