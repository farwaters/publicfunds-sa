"""Thusa review app: human review of automated flags (ADR-0005, ADR-0008).

- store.py     append-only, hash-chained SQLite review store (survives warehouse rebuilds)
- workflow.py  decision rules incl. the four-eyes rule for named-supplier flags
- security.py  password/token hashing, sessions, CSRF, login rate limiting
- warehouse.py read-only queries against the DuckDB build
- app.py       FastAPI + Jinja + HTMX web UI and JSON API
- cli.py       `pf` command line (reviewers, review list|show|decide, serve, publish)
"""
