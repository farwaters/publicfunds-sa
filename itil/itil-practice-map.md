# ITIL 4 mapping for Thusa

## Service value system (SVS)
| SVS element | Thusa instantiation |
|---|---|
| **Opportunity / demand** | Taxpayers, journalists, civil society, oversight bodies need one honest view of public spending (landscape report §0) |
| **Guiding principles** | *Focus on value* (taxpayer-first); *start where you are* (reuse Municipal Money, OCDS, PPD, TenderWatch method); *progress iteratively with feedback* (MVP → phases); *collaborate & promote visibility* (public methodology, corrections log); *think & work holistically* (data + legal + ops); *keep it simple & practical* (DuckDB on one box); *optimise & automate* (routines, CI) |
| **Governance** | Owner = the owner (service owner, change authority for high-risk changes, Information Officer under POPIA by default). Thusa Ops Bot = operator, never approves its own high-risk changes |
| **Service value chain** | See below |
| **Practices** | See table below |
| **Continual improvement** | CSI register reviewed monthly in the release cycle |
| **Value** | Faster, evidence-backed accountability; reduced cost to find irregularities; visible "known unknowns" that drive disclosure advocacy |

## Value chain
| Activity | What happens | Artefacts |
|---|---|---|
| Plan | Roadmap, quarterly priorities, risk review | design §11, risk register |
| Improve | Monthly CSI review; postmortem actions | CSI register, problem records |
| Engage | Persona research, partner outreach, corrections channel, right-of-reply | design §2, corrections log (phase 2) |
| Design & transition | ADRs, change requests, release checklist | docs/adr, templates |
| Obtain/build | Code, dbt models, parsers, tests | repo, CI |
| Deliver & support | Routines, ingestion, snapshot publishing, incident handling | sla-slo, runbooks |

## Practices in scope (14) and how they're applied
| Practice | Concrete application | Owner | Evidence |
|---|---|---|---|
| **Service catalogue management** | One catalogue entry per offered service: Public dashboard, Public API (phase 2), Alerts (phase 2), Data downloads | Owner | service-definition.md |
| **Service level management** | SLOs for freshness, availability, correction time, flag review time; monthly SLO report from routine | Owner | sla-slo.md |
| **Monitoring & event management** | Run ledger, DQ results, freshness ages, external uptime check; events classified *informational / warning / exception*; exceptions auto-open incidents | Ops Bot | design §14, ops schema |
| **Incident management** | Incident = user-facing degradation *or* wrong published figure. P1–P4 matrix; record template; "wrong number published" is always ≥ P2 | Ops Bot → Owner | templates/incident-record.md |
| **Problem management** | Recurring failures (e.g. OCDS API 500s, PDF layout changes) get problem records, workarounds become known errors (KEDB) | Owner | templates/problem-record.md, knowledge/known-errors.md |
| **Change enablement** | Standard / normal / emergency changes; risk tier from the change (P2 practice); change log | Owner | change-enablement.md, templates/change-request.md |
| **Release management** | Monthly data+code release `REL-YYYY.MM.N`; release notes = changelog; data release manifest (snapshot ids + commit) | Owner | templates/release-checklist.md |
| **Deployment management** | Box deploy via git tag + `make deploy`; public snapshot deploy to preview, then production after approval; rollback = previous snapshot | Ops Bot | release checklist §Deploy/Rollback |
| **Service configuration management** | CI register (sources, routines, Bots, hosts, repos, secrets *references*, detectors); `config/*.yaml` are machine-readable CIs; changes to CIs are changes | Owner | registers/ci-register.md, config/ |
| **Information security management** | POPIA controls, secret handling, least privilege, dependency & secret scanning, monthly access review | Owner | design §10, risk register |
| **Knowledge management** | Runbooks, methodology pages, KEDB, ADRs, AGENTS.md/REVIEW.md for AI agents | Owner + Ops Bot | itil/knowledge, docs/adr |
| **Continual improvement** | CSI register with value/effort scoring; each postmortem must add ≥1 CSI item or a test | Owner | registers/csi-register.md |
| **Risk management** | Risk register reviewed monthly; high risks block release | Owner | registers/risk-register.md |
| **Relationship / supplier management** | Data publishers (NT OCPO, AGSA, Stats SA, DMPR) treated as suppliers: feed requests, contact log, issue reporting (e.g. OCDS API 500s) | Owner | ci-register (supplier CIs), CSI items |

Not adopted yet (deliberately): service desk (corrections inbox covers it until public launch), capacity & performance as a separate practice (covered by SLOs), portfolio management, workforce & talent.
