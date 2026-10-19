# ADR-0006: Supplier entity resolution: registration number first, then normalised name, then probabilistic with review
- Status: Accepted (rules in MVP; Splink in phase 2)
- Date: 2026-10-19
## Context
CSD supplier numbers and directors are not public (landscape §3.2). OCDS, PPD and the RSR use inconsistent names; the RSR carries registration/ID numbers; PPD does not publish registration numbers **[verify on first CSV drop]**.
## Decision
Match in three tiers:
1. Exact CIPC registration number.
2. Normalised name (case, punctuation, legal suffixes such as (Pty) Ltd/CC/SOC, "t/a" splitting) plus province.
3. Splink probabilistic matching (phase 2) with a review queue.

D3 (barred) uses only tier 1 or tier 2 matches with confidence ≥ 0.9.
## Consequences
Under-matching rather than over-matching (TenderWatch reports matching 32 of 409 restricted entries for the same reason). Advocacy target: publish registration numbers (CSI-001).
