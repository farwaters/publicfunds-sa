# Risk register

Scoring: Likelihood (L) and Impact (I) 1–5; Score = L×I. **High ≥ 15**, Medium 8–14, Low ≤ 7. Reviewed monthly at release.

| ID | Risk | Category | L | I | Score | Mitigation / controls | Owner | Status |
|---|---|---|---|---|---|---|---|---|
| RSK-001 | Publishing a wrong or misleading flag that names a supplier/person (defamation, harm, credibility) | Legal / reputational | 3 | 5 | **15** | Human review for named high-severity flags; evidence + caveats on every card; right of reply; legal review before public launch (D-09); take-down = emergency change | Owner | Open |
| RSK-002 | Exposure of personal information (SA ID numbers in RSR PDF; sole proprietors) | POPIA / security | 3 | 5 | **15** | HMAC IDs; automated scan of public marts; POPIA impact assessment; Information Officer named | Owner | Open |
| RSK-003 | Upstream API/portal instability or format change (OCDS API 500s and Vulekamali CKAN 500 observed 19 Oct 2026) | Supplier / operational | 5 | 3 | **15** | Bulk-file fallback; OCP mirror; schema-drift contract tests; stale banners; problem records + publisher contact | Owner | Open |
| RSK-004 | Misinterpretation: irregular expenditure read as theft; aggregated LOGIS averages read as exact unit prices | Product / reputational | 4 | 3 | 12 | Plain-language caveats; methodology; "patterns not verdicts" copy rules; REVIEW.md "it lies" rule | Owner | Open |
| RSK-005 | Entity-resolution errors merge two different suppliers (false barred-and-paid) | Data quality | 3 | 4 | 12 | Reg-no-first matching; confidence threshold ≥0.9 for D3; review queue; eval set | Owner | Open |
| RSK-006 | Single box = single point of failure; data loss | Operational | 2 | 4 | 8 | Nightly backups offsite (D-05); monthly restore test; git remote; raw snapshots reproducible | Ops Bot | Open |
| RSK-007 | Shared Grok Bot computer: other Bots can read files/credentials | Security | 3 | 3 | 9 | No long-lived secrets on disk; Grok Bot secrets; least-privilege tokens; separate API keys per purpose; monthly access review | Owner | Open |
| RSK-008 | Licence breach (OpenSanctions CC BY-NC; site terms; PPD scraping) | Legal | 2 | 3 | 6 | Licence field per source; manual drop for PPD/Stats SA; attribution page | Owner | Open |
| RSK-009 | AI-introduced defects or malicious/non-existent packages (slopsquatting) | Engineering / security | 3 | 4 | 12 | Lockfile; verify packages; pip-audit; AI + security review; risk tiers; human approval on high-risk | Owner | Open |
| RSK-010 | Prompt injection via source text into "Ask Thusa" | Security | 3 | 3 | 9 | Read-only tools; source text treated as data; citations required; no send/write tools on that path | Owner | Open |
| RSK-011 | Runaway routine/agent cost | Financial | 2 | 3 | 6 | Routine caps; usage alerts; schedule ≥ 5 min apart (platform limit); weekly usage check | Owner | Open |
| RSK-012 | Political/legal pressure or takedown demands | External | 2 | 4 | 8 | Sourced-only policy; corrections process; partner with established CSOs; legal contact | Owner | Open |
| RSK-013 | Key-person risk (bus factor 1) | Organisational | 4 | 3 | 12 | ADRs, runbooks, README < 1 h setup, AGENTS.md; repo in owner's name; second maintainer (CSI-008) | Owner | Open |
| RSK-014 | Legal basis for disclosure shrinks (PPA 2024 invalidated 17 Sep 2026; no s31 publication duty) | Regulatory | 4 | 3 | 12 | Rely on existing PFMA Instruction 10 data; advocacy; PAIA programme | Owner | Open |
| RSK-015 | Source data errors read as wrongdoing (e.g. a municipal AUDA total 10× its budget; R370bn award values) | Data quality / reputational | 4 | 4 | **16** | Possible-data-error class in D1 (> 200%); implausible award-value bounds; caveats in every flag explanation; human review before publication | Owner | Open |
| RSK-016 | D3 name-only matches (eTenders publishes no registration numbers) produce false "restricted supplier awarded" flags | Data quality / legal | 3 | 5 | **15** | Confidence ≥ 0.90 and ≥ 2-token names; `pending human review`; never published unreviewed (DQ gate); eval set CSI-014; ask OCPO to publish CSD/CIPC numbers (CSI-001) | Owner | Open |

