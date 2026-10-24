# SLA / SLO draft (v0.1)

No external SLA is offered while in beta. These are **internal SLOs** with error budgets; they become a published "service commitment" at public launch.

## Availability
| SLI | SLO | Window | Error budget | Measurement |
|---|---|---|---|---|
| Public snapshot HTTP 200 on home + 3 sample entity pages | **99.5%** | 30 days | ~3.6 h | External uptime check every 5 min (D-08) |
| Box API `/v1/meta/release` 200 | **99.0%** | 30 days | ~7.2 h | Routine health probe every 15 min |
| Box single point of failure | Accepted (no HA) | — | — | RTO/RPO below |

## Data freshness (per source; age = now − latest successful snapshot of a *published* upstream release)
| Source | SLO (age ≤) | Notes |
|---|---|---|
| eTenders OCDS | 2 days | API instability → bulk fallback |
| Municipal Finance API | 7 days after NT quarter load | |
| Procurement Payments Dashboard | 21 days after NT quarterly release | manual drop in MVP |
| Restricted Supplier Register | 8 days | |
| DMPR fuel prices | 5 days after adjustment | `dmpr_fuel`, monthly (first Wednesday); freshness check 35 days |
| Stats SA CPI | 10 days after release | manual drop; meanwhile OECD SDMX secondary series `oecd_cpi` (lags months, KE-012); freshness check 400 days |
| NT s32 monthly | 10 days | |
| AGSA reports | 30 days after tabling | |
| s71 non-compliance lists | 21 days | |
**Target: ≥ 95% of source-days within SLO per month.** A stale source is shown as stale in the UI (never silently).

## Public data and public dashboard (CHG-2026-006, ADR-0010)
| ID | SLI | SLO | Window | Measurement |
|---|---|---|---|---|
| **SLO-PD-1** | Age of the published export = now − `manifest.json` `generated_at_sast` at `raw.githubusercontent.com/…/main/public-data/v1/` | **≤ 48 h** on 95% of days | 30 days | Refresh routine reports the export time after each push; the app shows the age and warns above 48 h; `scripts/check_live.py` measures it from outside (`--raw-url` for the SLO's own measuring point) and reports a breach (RB-12, CHG-2026-032) |
| SLO-PD-2 | Unconfirmed leads, reviewer data or personal ID numbers in the public export | **0** (hard rule; export refuses) | always | `pf publish-data` safety scan + tests (RSK-023) |
| SLO-PD-3 | Public dashboard pages load without console errors on desktop and mobile | 100% of pages per release | per release | `scripts/dashboard_check.py` |
Availability of the Grok Build site itself is the host's; measure with the external uptime check once the URL exists (D-08, D-16).

## Correctness & review
| SLI | SLO |
|---|---|
| Time to correct a confirmed wrong published figure | **≤ 48 h** (P2 incident) |
| Time to triage a correction/objection request | ≤ 5 business days; resolve ≤ 30 days (POPIA-aligned) |
| High-severity named flags published without human review | **0** (hard rule) |
| Release DQ pass rate (blocking tests) | 100% (release blocked otherwise) |

## Performance
| SLI | SLO |
|---|---|
| Box entity page p95 | < 1.5 s |
| Public page LCP, mid-range Android, slow 4G | < 2.5 s (Lighthouse median of 3) |

## Recovery
| Item | Target |
|---|---|
| RPO (curated DB) | 24 h (nightly backup); raw snapshots are themselves the source of truth |
| RTO (public snapshot) | 1 h (redeploy previous snapshot) |
| RTO (box pipeline) | 1 business day (rebuild from git + raw backups) |
| Restore test | Monthly; result logged in CSI/incident log |

## Incident priority matrix
| Impact \ Urgency | High | Medium | Low |
|---|---|---|---|
| **Wrong/defamatory figure public, or personal data exposed** | P1 (respond 1 h, take down immediately) | P1 | P2 |
| **Bot/pipeline unavailable or data > 2× SLO stale** (no public site in the MVP, ADR-0009) | P2 (4 h) | P3 | P3 |
| **Single source stale / DQ fail blocks release** | P3 (1 business day) | P3 | P4 |
| **Cosmetic** | P4 | P4 | P4 |

## Error-budget policy
If any 30-day budget is > 50% burned: freeze non-urgent normal changes to the affected component until a problem record exists. If 100% burned: only fixes and standard changes until the budget recovers.
