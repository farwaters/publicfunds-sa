# CHG-2026-011: Start AGSA annexure ingest (audit outcomes, UIF&W expenditure) with lineage; legal-review checklist

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-20 00:35, item C; continued 00:46 |
| Type | **Normal**. New source and warehouse tables only. **Nothing new is published:** no export, page or detector reads these tables. Owner approves the merge |
| CIs affected | new connector `thusa/connectors/agsa.py` (source `agsa_annexures`), parsers (stdlib xlsx reader), staging, new model `curated/055_agsa.sql`, build row counts, CLI source list, `config/sources.yaml`, KE-013 |
| Linked records | KE-006 (Municipal Finance API lacks 2024/25 audit data), KE-013, docs/legal/agsa-wording-review-checklist.md |
| PR | branch `feat/agsa-annexures` (unmerged) |

## What
1. **Connector:**
   - Fetches 4 official AGSA Excel files: MFMA 2023-24 Annexure 1 and 3 (mfma-2024.agsa.co.za) and PFMA 2023-24
     Annexure 1 and 3 (pfma-2023-24.agsa.co.za). URLs come from each site's own "Annexures to the report" links.
   - Each file is fetched **once**; afterwards the stored copy is reused, so the nightly run makes no further requests.
   - Checks the Excel signature. A failure is noted without failing the run.
2. **Parser:**
   - Uses a stdlib-only xlsx reader (no new dependency).
   - Keeps the audit group (financial, consolidated, small, dormant, private-firm), the outcome section, the auditee,
     category/type, province, and the year for each opinion.
   - Lineage: file name and sheet row (`#rowN`), plus the sha256 and URL via `ops.raw_file`.
3. **Tables:**
   - `curated.agsa_audit_outcome` (5 668 rows): opinions for 2019-20 to 2023-24.
   - `curated.agsa_uifw` (3 342 rows): 2023-24 unauthorised, irregular and fruitless & wasteful expenditure. Amounts
     are converted from R million to cents; blanks stay NULL (unknown), and a published 0 stays 0.
   - `curated.agsa_auditee_link`: municipalities are linked to `curated.gov_body` only when name key, province and
     type match exactly once. 238 of 260 municipal auditee names are linked; the rest are left unlinked (KE-013).
4. **Legal-review checklist** (draft): docs/legal/agsa-wording-review-checklist.md. It must be completed before any
   AGSA-sourced publication.

## Verification (isolated build, 2026-10-20 ~01:00 SAST; DQ fail [])
- MFMA 2023-24 municipalities (financial audits, category MUN): 41 clean, 99 unqualified with findings, 90 qualified,
  6 adverse, 11 disclaimer, 10 not finalised, 257 in total. This matches the AGSA site's "South Africa at a glance"
  exactly.
- Municipal UIF&W amounts vs the Municipal Finance API (2023-24, linked municipalities): 678 of 678 within R50 000.
- PFMA 2023-24 Annexure 1 irregular total is R55,50 bn across all audit groups, vs the general report's R49,53 bn
  headline. The general report's scope differs (audit groups and auditees counted), so annexure totals must not be
  presented as the AGSA headline (checklist item 1).

## Not done (owner decisions, KE-013)
- **Material irregularities:** not in any annexure. They're only in report chapters (PDF) and the MFMA site's
  per-municipality pages (served as JSON to that site). Not loaded.
- **2024-25:** the MFMA annexures are PDF only, and the PFMA Excel annexures are not linked from agsa.co.za. Not loaded.
- **Publication** of any AGSA data: needs the checklist first.

## Not changed
- `scripts/publish-public-data.sh` (but note: the nightly `thusa run` now includes `agsa_annexures`, which makes 4
  requests on its first run and none after), the public export and dashboard, detectors, dependencies.
- The public `sources.json` may list `agsa_annexures` and its run status once it has run, like every other source.

## Test / backout
- `tests/test_agsa_annexures.py` is new.
- Backout: revert. Raw files stay in `data/raw` (append-only).
