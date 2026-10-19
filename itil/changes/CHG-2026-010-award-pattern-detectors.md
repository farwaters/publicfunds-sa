# CHG-2026-010: Award-pattern detectors that name suppliers (D16 repeat awards, D17 just below threshold, D6 splitting)

| Field | Value |
|---|---|
| Requested by / date (SAST) | Owner, 2026-10-20 00:35, item B; continued 00:46 |
| Type | **Normal-high**. Adds three detectors that name suppliers. Their flags are hidden leads only: they wait for the four-eyes review and are **never published**, even when confirmed (`config/publication.yaml` `never_publish`). Owner approves the merge |
| CIs affected | detectors (new D16, D17; D6 from placeholder to v0.1.0), `config/detectors.yaml` (new `procurement_thresholds`), publish policy (`never_publish`), public-data detector text |
| PR | branch `feat/supplier-detectors` (unmerged) |

## Thresholds (verified 2026-10-20 against the official documents)
| Regime | Buyer | Competitive bidding above (VAT incl.) | In force from | Source |
|---|---|---|---|---|
| MFMA | metro / local / district municipality | R750 000 / R300 000 / R200 000 | 14 Dec 2023 (on publication, reg 8) | Municipal SCM Regulations reg 12(1)(c)-(d), reg 19(b); GN 4198, GG 49863 (14 Dec 2023), https://mfma.treasury.gov.za/RegulationsandGazettes/Municipal%20SCM%20Amendment%20Regulations.pdf (sha256 abf57842…) |
| PFMA | national / provincial department (and Sch 3A/3C entities) | R1 000 000 | 1 Aug 2021 | PFMA SCM Instruction No. 02 of 2021/22 para 3.2-3.3, 4.1 (sha256 87f47236…) and its amendment, effective date (sha256 2cb4a856…), ocpo.treasury.gov.za Instruction Notes |

Both documents forbid *deliberately* splitting a requirement to avoid competitive bidding (MFMA reg 19(b); PFMA
instruction para 4.1). Awards dated before a regime's "from" date aren't assessed, because the older thresholds were
not verified for this change. Buyers not linked to a government body (no known regime) aren't assessed by D6/D17.

## What
- **D16 repeat awards:** at least 5 single-supplier, known-value awards from one buyer to one supplier within 365 days.
  Severity low.
- **D17 just below threshold:** at least 2 awards from one buyer to one supplier within 365 days, each between 90% and
  100% of that buyer's bidding threshold. Severity med at 3 or more.
- **D6 splitting:** 2 or more awards to one supplier starting within 30 days, each at or below the threshold but
  together above it. Severity med. The explanation says published awards cannot show whether they were one
  requirement.
- **Shared rules for all three:**
  - `names_supplier=True`, so flags are "pending human review" and need four-eyes.
  - Evidence lists each OCDS ocid and award id, with value, date and date basis.
  - Awards with a value note (implausible, placeholder) or more than one supplier are excluded.
- **Publication:**
  - `public_flags` skips `never_publish` detectors.
  - The public export counts them as hidden leads only.
  - These changes are the same lines as in CHG-2026-009 (PR #5).
- **First isolated build** (production raw data, 2026-10-20 00:48 SAST): D16 14 flags, D17 0, D6 0; DQ fail [].
  Few published awards fall under the thresholds (106 of 1 090 linked, known-value awards since 14 Dec 2023), as
  quotation-level procurement is mostly not on eTenders.

## Caveats
- 82% of award dates are the OCDS release date (a proxy), so windows are approximate. `date_basis` is shown in the
  evidence.
- Repeat awards and values near a limit are common and often legitimate (panels, framework contracts). These are leads
  for a reviewer, not findings.

## Not changed
- `scripts/publish-public-data.sh`, the nightly routine, other detectors, dependencies, the dashboard.

## Test / backout
- `tests/test_award_patterns.py` is new.
- Backout: revert the PR.
- Merge note: if PR #5 merges first, `config/publication.yaml` `never_publish` needs one hand-merged line (union of
  both lists), and `DETECTORS` in `thusa/detectors.py` keeps both sets of entries.
