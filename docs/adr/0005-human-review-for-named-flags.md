# ADR-0005: High-severity flags naming a supplier or person require human review before publication
- Status: Accepted
- Date: 2026-10-19
## Context
RSK-001 (defamation) and RSK-005 (entity-resolution errors). AGSA distinguishes irregular expenditure from theft.
## Decision
- Flag status flow: `open → reviewed → published`.
- Detector threshold changes are Normal-high changes.
- D9 (related parties) additionally needs legal review before its first publication.
## Consequences
Slower publication of flags; much lower harm risk. Review-time SLO to be added once volumes are known.
