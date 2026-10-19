# Known error database (KEDB)
| ID | Symptom | Cause | Workaround | Linked |
|---|---|---|---|---|
| KE-001 | `ocds-api.etenders.gov.za/api/OCDSReleases` returns HTTP 500 or times out (19 Oct 2026) | Upstream API instability **[cause unverified]** | Use Treasury monthly bulk files; fallback OCP registry mirror; mark source stale if both fail | CSI-002, CSI-003 |
| KE-002 | `data.vulekamali.gov.za` CKAN returns 500/timeout (19 Oct 2026) | Upstream | Use treasury.gov.za ENE/EPRE/s32 Excel files | RSK-003 |
| KE-003 | Stats SA, some SIU/PP pages block or time out on scripted requests | WAF (Incapsula) / hosting | Manual drop folder; Bot browser download if terms allow (D-07) | CSI-005 |
| KE-004 | Instruction 10 PDF is image-only | Scanned "Print to PDF" | Render pages to PNG + read/OCR | — |
