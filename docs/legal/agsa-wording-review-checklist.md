# Legal-review checklist: AGSA audit data on the public site (draft, CHG-2026-011)

**Status:** draft for the owner and a media/defamation lawyer. Nothing from the AGSA annexures is published yet.
This PR only loads the data into the warehouse. Before any page or export shows it, every item below needs a ✅ and the
reviewer's name and date, recorded in the CHG that turns publication on.

## 1. Attribution and fidelity
- [ ] Every figure is shown with "Source: Auditor-General of South Africa, *<report name>*, Annexure <n>", the year
      and a link to the official file. The stored sha256 and row reference stay in the evidence.
- [ ] Opinions use the AGSA's exact labels ("Unqualified with findings", "Disclaimer", "Audit not finalised at
      legislated date"). They are not reworded as "failed", "corrupt", "looted", "stole" or similar.
- [ ] Irregular, fruitless and wasteful, and unauthorised expenditure each have the legal definition shown next to
      them (PFMA s1 / MFMA s1). The page also says irregular expenditure means a process was not followed, **not** that
      money was lost or stolen. Fruitless and wasteful means spending that could have been avoided with reasonable
      care.
- [ ] Amounts are shown in rand as the AGSA reports them (R million). They are never summed across regimes or years
      in a way the AGSA does not.
- [ ] "Audit not finalised" and blank cells are shown as unknown or not finalised, never as zero or as a bad outcome.
- [ ] Consolidated, small, dormant and private-firm audit groups are labelled or kept apart, so an auditee is not
      double-counted.

## 2. No new allegations
- [ ] No wording on the site states or implies wrongdoing beyond what the AGSA itself states in the cited document.
- [ ] Opinion pieces or advocacy text are kept visibly apart from AGSA facts, with no "looting" language next to an
      auditee's results.
- [ ] Named individuals (municipal managers, CFOs, mayors) are **not** shown next to audit outcomes.
- [ ] Material irregularities, if added later, are quoted with the AGSA's status (e.g. "notified", "appropriate
      action taken", "resolved") and its date. The page says an MI is a suspected or identified matter, not a
      finding of guilt.

## 3. Accuracy and right of reply
- [ ] Spot checks against the official file are recorded before each publication (at least 10 auditees per regime,
      covering each opinion type).
- [ ] The "report an error" form is linked from each AGSA-sourced page, and corrections follow the CSI process.
- [ ] A dated note covers later changes, e.g. "Figures as at the AGSA report cut-off date; later re-audits or
      condonements are not reflected".

## 4. Legal basis and terms
- [ ] AGSA website terms of use / copyright checked for reuse of annexure data, and attribution wording agreed.
- [ ] POPIA: the annexures contain no personal information (auditee-level only). Confirm the same for any MI data
      before loading it.
- [ ] Defamation: lawyer confirms that factual, attributed republication with the definitions above is acceptable,
      and confirms the takedown and correction procedure.

## 5. Owner decisions recorded
- [ ] Publish AGSA facts at all? (Yes or no, and which pages.)
- [ ] Use the AGSA MFMA site's per-municipality pages for material irregularities (no file is published)?
- [ ] Parse the MFMA 2024-25 PDF annexures, or wait for Excel?
