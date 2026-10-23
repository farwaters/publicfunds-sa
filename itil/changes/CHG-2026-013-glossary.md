# CHG-2026-013: Plain-language glossary and explainers page (#/glossary)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-23 12:48 |
| Type | **Normal**. Static explanatory text on the public dashboard; no data, detector or publication-policy change. Owner approves the merge |
| CIs affected | `apps/public-dashboard/index.html` (new `vGlossary` view, route, nav item, two in-context links), `scripts/dashboard_check.py` (page list), `tests/test_improvements.py` (one test) |
| Linked records | CSI-027 (roadmap item #2, Stage 1 item A), CHG-2026-008 (known unknowns), CHG-2026-009/010 (D13, D6, D16, D17 never published) |
| PR | branch `feat/glossary` (unmerged) |

## What
1. New `#/glossary` page ("Glossary" in the main navigation): UIFW (unauthorised, irregular, fruitless and wasteful
   expenditure, from PFMA s1 and MFMA s1), the PFMA and MFMA, AGSA audit outcomes (AGSA glossary and Audit 101),
   competitive-bidding limits (MFMA R750 000 metro / R300 000 local / R200 000 district, Gazette 49863 of
   14 Dec 2023; PFMA departments R1 000 000, SCM Instruction 02 of 2021/22), restricted suppliers, eTenders, each
   detector (D1, D3, D4, D5, D8, D13, D6, D16, D17) in plain words with the parameters from `config/detectors.yaml`,
   why only reviewed and confirmed flags are shown (`config/publication.yaml`), and that a blank means unknown.
2. Every fact links to its official source (National Treasury, AGSA, eTenders); no repository links.
3. In-context links to the glossary from the municipality UIFW note and the Flags page.

## Not changed
Data, exporter, detectors, thresholds, publication policy, other pages.

## Verification
- `pytest`: 202 passed. `scripts/dashboard_check.py`: no problems (14 pages × desktop and mobile, axe-core).
- Lighthouse 12 on `#/glossary` (local server): mobile and desktop 100/100/100/100.

## Back-out
Revert the merge commit.
