"""Shared fixtures for the review-app tests: one synthetic warehouse per session, a fresh review DB per test."""
import re
from datetime import date

import pytest

from tests.synth import build_raw
from thusa.build import build
from thusa.settings import get_paths

SMALL = {"curated.gov_body": 3, "curated.muni_fin_line": 10, "curated.award": 100, "curated.restriction": 2,
         "marts.coverage_cell": 10}
PW = {"alice": "alice-password-123", "bob": "bob-password-4567", "root": "root-password-890"}


@pytest.fixture(scope="session")
def synth_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("review_wh")
    build_raw(root)
    s = build(get_paths(root), as_of=date(2026, 10, 19), fye_min=2023, fye_max=2026, min_rows=SMALL,
              secret=b"test-secret")
    assert s["dq"]["fail"] == [], s["dq"]["fail"]
    return root


@pytest.fixture
def paths(synth_root, tmp_path, monkeypatch):
    monkeypatch.setenv("THUSA_REVIEW_DB", str(tmp_path / "review.sqlite"))
    monkeypatch.setenv("THUSA_ROOT", str(synth_root))      # the `pf` CLI must never touch the real warehouse
    return get_paths(synth_root)


@pytest.fixture
def svc(paths):
    from thusa.review import security as sec
    from thusa.review.service import Service
    s = Service(paths)
    s.store.add_reviewer("alice", "Alice A", "reviewer", sec.hash_password(PW["alice"]), "test")
    s.store.add_reviewer("bob", "Bob B", "reviewer", sec.hash_password(PW["bob"]), "test")
    s.store.add_reviewer("root", "Root Admin", "admin", sec.hash_password(PW["root"]), "test")
    return s


@pytest.fixture
def app(paths, svc):
    from thusa.review.app import create_app
    return create_app(paths, allowed_hosts=["testserver"], secure_cookies=False)


def login(client, username, password=None):
    r = client.get("/login")
    tok = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    return client.post("/login", data={"username": username, "password": password or PW[username],
                                       "csrf_token": tok, "next": "/flags"}, follow_redirects=False)


def csrf_of(client, path="/flags"):
    return re.search(r'name="csrf_token" value="([^"]+)"', client.get(path).text).group(1)


def flag_of(svc, prefix):
    return next(f for f in svc.wh.flags() if f["detector_id"].startswith(prefix))
