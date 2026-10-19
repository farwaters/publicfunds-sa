# REVIEW.md — what reviewers (human or AI) must check

**What failure looks like in this repo: "it lies."** A number that is wrong, unsourced, stale without saying so, or framed as wrongdoing without evidence.

Check, in this order, citing file:line as evidence:
1. **Provenance:** do new facts carry snapshot and locator? Do UI numbers link to their source?
2. **Missing vs zero:** could a NULL become 0 anywhere (SQL `COALESCE`, `sum` over empty, JS `|| 0`)?
3. **Money and time:** integer cents; fiscal-year boundaries (national Apr–Mar, municipal Jul–Jun); UTC storage.
4. **Privacy:** no ID numbers or personal contact details reach `marts`/public output.
5. **Flags:** detector changes come with eval results and an updated `config/detectors.yaml` version; named high-severity flags stay `open` until reviewed.
6. **Security:** parameterised SQL, no secrets, no new CORS wildcards, headers intact, new packages verified.
7. **Tests:** a regression test for every bug fixed.

Rules:
- Cap nits at 3.
- Skip `data/`, `dist/` and generated files.
- Start the summary with a count of findings, and say plainly when there's nothing to fix.
- Tag findings Important / Nit / Pre-existing.
