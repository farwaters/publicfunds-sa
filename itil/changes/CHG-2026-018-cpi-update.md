# CHG-2026-018: CPI to the latest month (CSI-031) from the IMF republication of Stats SA P0141

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, as reported to the author (PublicFunds), 2026-10-23 ~16:00 ("GO" for the DEV build of CSI-031) |
| Environment | DEV only (branch `feat/cpi-update` from origin/main 142c0d4; PR open, not merged, nothing pushed to main) |
| Type | **Normal**. New ingest source `imf_cpi`, parser, staging, curated selection rule, publisher label |
| CIs affected | `thusa/connectors/prices.py`, `thusa/parsers.py`, `thusa/staging.py`, `thusa/cli.py`, `thusa/models/curated/090_price_benchmarks.sql`, `thusa/publish_data.py`, `thusa/dq.py`, `config/sources.yaml`, `config/public-data.yaml`, `apps/public-dashboard/index.html`, `tests/test_cpi_imf.py` (new), this record, `itil/registers/change-log.md` |
| Linked records | Roadmap CSI-031 (score 25), KE-003 (Stats SA WAF), KE-012 (OECD lag), CHG-2026-006 (price benchmarks) |
| Rollback | Close the PR unmerged. If ever merged: `git revert -m 1 <merge commit>`; the next nightly rebuild falls back to `oecd_cpi` (git history is the rollback; no .bkp files per owner amendment) |

## Source feasibility (2026-10-23, SAST)
| Candidate | Result |
|---|---|
| Stats SA P0141 PDF/Excel (statssa.gov.za) | robots.txt allows all, but every scripted request gets the Incapsula JS challenge (noindex page). Not worked around (KE-003). |
| SARB web indicators API (custom.resbank.co.za) | Responds, but returned no CPI series for the code tried; no documented CPI open-data endpoint found. Not used. |
| data.gov.za | No response (connection failed) from the box. Not used. |
| OECD SDMX (current source) | Still ends 2025-01. |
| **IMF CPI dataset, IMF.STA:CPI (api.imf.org SDMX 2.1)** | **Chosen.** Public, no login, `ACCESS_SHARING_LEVEL=PUBLIC_OPEN`. Series ZAF all-items index, Stats SA's own base Dec 2024 = 100, 2008-01 to 2026-07, one decimal as Stats SA publishes. IMF "Special Terms for Statistical Data": download, reuse and redistribute with attribution ("Source: International Monetary Fund, Consumer Price Index (CPI)"), no alteration. api.imf.org/robots.txt returned 502 (no rules published). One request per nightly run. |

## What
- `imf_cpi` connector stores the SDMX-ML response unchanged in the raw store (URL, fetch time, sha256 via `ops.raw_file`).
- `parsers.imf_cpi_rows`: headline series only (`COICOP_1999=_T`, `IX`, `M`), blanks skipped never zeroed, values as published.
- `curated.cpi` uses one source and one base: `imf_cpi` when loaded, else `oecd_cpi` (fallback kept, unchanged). Lineage columns unchanged (source_url, source_sha256, fetched_at_utc, source_locator).
- Publisher text in `prices.json` labels the series "Stats SA headline CPI (all urban areas)", as republished by the IMF, with the IMF citation and dataset link (https://data.imf.org/en/datasets/IMF.STA:CPI); same label and link in `config/public-data.yaml`. Base label comes from the data ("Dec 2024 = 100").
- DQ check `cpi_fresh_imf_info` (severity warn, existing `thusa/dq.py` pattern): WARN if the latest CPI month is older than the 120-day freshness target or `curated.cpi` fell back to `oecd_cpi`. Never fails the build.
- SHADOW round 2 fixes: `prices.json` CPI block gets `back_series_note` (IMF source only): "Values from 2025-01 match Stats SA P0141. Earlier values are the IMF's linked back-series (OECD 2015-base series scaled) and can differ from Stats SA's rebased figures by about 0.1-0.2 index points." Dashboard shows it in plain small text under the inflation adjuster, only when the field exists. CPI `measure` is "Headline consumer price index, all items, all urban areas (Stats SA)" for IMF (OECD label unchanged). KE-003 text now says CPI comes from the IMF's republication of Stats SA headline CPI (all urban areas), OECD as fallback, with the back-series note; OECD-lag claim dropped.
- Added to `cli.SOURCES`, so the existing nightly `ingest` picks it up the same way as `oecd_cpi` (no routine change).

Effect: CPI goes from 2008-01..2025-01 (2015 = 100, OECD) to 2008-01..2026-07 (Dec 2024 = 100). 18 months added: 2025-02..2026-07.
The base changes for the whole series; the dashboard's inflation calculator uses ratios, so results are base-independent
(differences only from one-decimal rounding of the official index). Stats SA has published Aug and Sep 2026 (P0141 of
23 Sep and 21 Oct 2026); the IMF has not yet republished them. They arrive automatically when it does.

## Cross-check against the official Stats SA publication text
Scope of the claim: the loaded series matches Stats SA P0141 from 2025-01 onward. Values before 2025 are the IMF's linked
back-series (the OECD 2015-base series scaled), which can differ from Stats SA's rebased Table B1 by about 0.1-0.2 index points.
Source text: P0141 July 2026, Table B1 "CPI headline index numbers (Dec 2024=100)", and P0141 July 2025 / August 2025 Table A
(read as indexed public text; Stats SA site not scripted).
All 19 months 2025-01..2026-07 match exactly, e.g.:
| Month | IMF (loaded) | P0141 text | |
|---|---|---|---|
| 2025-01 | 100.3 | 100,3 (B1) | match |
| 2025-07 | 103.3 | 103,3 (B1; Jul 2025 Table A) | match |
| 2025-08 | 103.2 | 103,2 (B1; Aug 2025 Table A) | match |
| 2025-12 | 103.6 | 103,6 (B1) | match |
| 2026-04 | 106.0 | 106,0 (B1) | match |
| 2026-07 | 107.7 | 107,7 (B1) | match |
Also Dec 2024 = 100.0 on both. No values were typed in by hand; all come from the stored raw file.

## Not changed
`oecd_cpi` connector and data (kept as fallback), public-data files (regenerated by the standing nightly refresh only after merge), other sources.

## Tests and checks (2026-10-23, DEV)
- `.venv/bin/python -m pytest -q`: 219 passed with a built local warehouse; 159 passed and 60 skipped in a fresh checkout without one (3 new in tests/test_cpi_imf.py: parser keeps headline only and skips blanks; curated.cpi prefers IMF with no mixed base and full lineage; CPI freshness/OECD-fallback DQ check warns, never fails).
- Local DEV run: `thusa ingest --only imf_cpi` ok (1 request, 25.5 KB, sha256 3804ac4e…), `thusa build` DQ fail [] (cpi_fresh_imf_info pass: 2026-07 within 120 days) , export to a temp dir: prices.json cpi last_period 2026-07, 223 months, base "Dec 2024 = 100".
- SHADOW round 2: `pytest -q` 159 passed, 60 skipped (fresh worktree, no warehouse); `test_curated_cpi_prefers_imf_single_base_with_lineage` extended to assert `back_series_note` and the IMF measure label in `prices()` output.
- `scripts/dashboard_check.py` with axe-core (prices.json temporarily given the note locally, not committed): problems [], axe violations 0 on all 30 views (desktop + mobile, incl. tools).

## popia-review: PASS
Scan of the diff and the new raw file: no ID, passport, phone, email, address, account numbers, plates, locations, credentials or keys.
Content is national aggregate price statistics only; no people, suppliers or identity linking. Nothing removed.

## Four checks
Pending (author does not sign off; Law I). Outcome: pending review. Merge (main = PROD) needs the owner's quoted GO for this PR.
