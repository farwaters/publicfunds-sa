# CHG-2026-016: Case referral pack (`pf case export`)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-23 15:12 |
| Environment | DEV only (branch `feat/case-pack` from origin/main; PR opened, not merged, nothing pushed to main) |
| Type | **Normal**. New local CLI command and module; no change to detectors, exporter, public-data, publication config or the public site |
| CIs affected | `thusa/review/casepack.py` (new), `thusa/review/cli.py` (new `case export` subcommand), `tests/test_case_pack.py` (new), this record, `itil/registers/change-log.md` |
| Linked records | CHG-2026-003 (review app), CHG-2026-013 (glossary wording reused) |

## What
`pf case export FLAG_ID [--out DIR] [--pdf]` writes one Markdown file `case-<flag_id>.md` for one hidden lead (default
`data/cases/`, already gitignored by `data/`). Purpose: the owner and a second person check it independently; cases that
hold up may be referred (Corruption Watch / SIU / AGSA / National Anti-Corruption Hotline). `--pdf` uses pandoc if
installed, otherwise reports "skipped". Exit codes follow `pf`: 2 unknown flag, 3 pack refused by the POPIA scan.

Contents: case ID, detector and glossary plain-language explanation, buyer entity, supplier name as in the official
record, amounts and dates, evidence rows with source lineage (locator, sha256, raw file, fetch time), direct official
links (eTenders OCDS release API `https://ocds-api.etenders.gov.za/api/OCDSReleases/release/<ocid>`, tender documents,
Treasury register, Municipal Finance API, AGSA report URLs where present), comparison baseline, innocent explanations,
checker checklist, "not a finding of wrongdoing" notice (top and bottom), how to refer. Links verified 2026-10-23:
Corruption Watch `https://www.corruptionwatch.org.za/report-corruption/` (HTTP 200), National Anti-Corruption Hotline
0800 701 701 (gov.za hotlines page, PSC), OCDS release endpoint (HTTP 200 for a sample ocid).

## POPIA controls
Columns whose names indicate personal data (contact, email, phone, fax, person key, ID/registration/CIPC number,
supplier_id, subject_id, address, is_person) are dropped. A supplier name is shown only if it carries a company or
organisation word or a number; otherwise (or if the register marks it `is_person`) it is replaced everywhere by
"[natural person, see official record link]". Fail closed: this over-redacts some company names (the checker reads the
name in the linked official record). The rendered text is scanned for emails, phone numbers (the hotline number is the
only allowed one) and 13-digit ID-like numbers; any hit refuses the pack (exit 3). No hotline email addresses are included.

## Tests and checks
- `.venv/bin/python -m pytest -q`: 212 passed (6 new in `tests/test_case_pack.py`: no emails/phones/person keys/ID or
  CIPC numbers/natural-person names; scanner catches leaks; sample pack renders every section; heuristic; output path
  gitignored and nothing under data/cases tracked; CLI writes the file / exit 2 for an unknown flag).
- Dry run over all 349 flags in the current DEV build: all render, 0 refused (after excluding tender reference numbers
  such as `X.012-345-6789/1F` from the phone pattern).

## POPIA review (popia-review release check)
Sample packs for a D3 (restricted supplier) and a D4 (supplier concentration) flag in `data/cases/` (not committed):
no emails, phones, ID, CIPC or person keys, no contact-point data, no natural-person names; suppliers are presented as
indicators from the official source with the "not a finding" notice. Diff contains synthetic test data only.
**Verdict: PASS.**

## Back-out
Do not merge the PR, or revert its merge commit (git history is the rollback). Generated packs are local files under
`data/cases/`; delete them when the referral is done (POPIA collect-the-minimum).

## Result
DEV build succeeded. Pending independent review (expert, shadow, charter, drift) and owner merge decision.
