"""CHG-2026-008 quick wins: data change log + JSON Feed, issue form, social cards, new dashboard pages."""
import hashlib
import json
import re

import yaml

from thusa import publish_data as pdx
from thusa.settings import REPO_ROOT

APP = REPO_ROOT / "apps" / "public-dashboard" / "index.html"


def _read(out, name):
    return json.loads((out / name).read_text())


def test_changelog_first_entry_feed_and_manifest(paths, tmp_path):
    out = tmp_path / "pd"
    pdx.export(paths, out)
    ch, feed, man = _read(out, "changes.json"), _read(out, "feed.json"), _read(out, "manifest.json")
    assert ch["schema"] == pdx.SCHEMA and ch["kind"] == "changes"
    assert len(ch["entries"]) == 1 and ch["entries"][0]["summary"] == ["First public release of this data."]
    assert ch["entries"][0]["build_id"] == man["build"]["id"]
    assert feed["version"] == "https://jsonfeed.org/version/1.1"
    assert {"title", "home_page_url", "feed_url", "items"} <= set(feed)
    assert all({"id", "url", "title", "content_text", "date_published"} <= set(i) for i in feed["items"])
    listed = {f["name"]: f["sha256"] for f in man["files"]}
    for n in ("changes.json", "feed.json"):
        assert listed[n] == hashlib.sha256((out / n).read_bytes()).hexdigest()


def test_unchanged_data_leaves_changelog_byte_identical(paths, tmp_path):
    """The nightly publish must not commit when only timestamps change (scripts/publish-public-data.sh)."""
    out = tmp_path / "pd"
    pdx.export(paths, out)
    before = {n: (out / n).read_bytes() for n in ("changes.json", "feed.json")}
    pdx.export(paths, out)
    assert {n: (out / n).read_bytes() for n in before} == before


def test_changed_data_adds_entry_with_deltas(paths, tmp_path):
    out = tmp_path / "pd"
    pdx.export(paths, out)
    # pretend the previous build had fewer award records and an older coverage figure
    man = _read(out, "manifest.json")
    man["counts"]["awards"] -= 5
    man["coverage"]["complete_pct"] = (man["coverage"]["complete_pct"] or 0) - 1
    man["files"] = [dict(f, sha256="0" * 64) if f["name"] == "flags.json" else f for f in man["files"]]
    (out / "manifest.json").write_text(json.dumps(man))
    ch = _read(out, "changes.json")
    ch["entries"][0]["data_hash"] = "stale"
    (out / "changes.json").write_text(json.dumps(ch))
    pdx.export(paths, out)
    ch = _read(out, "changes.json")
    assert len(ch["entries"]) == 2
    e = ch["entries"][0]
    assert e["count_changes"] == {"awards": 5}
    assert any("+5 tender award records" in s for s in e["summary"])
    assert any(s.startswith("Coverage of core municipal data rose") for s in e["summary"])
    assert e["files_changed"] == ["flags.json"]
    assert len(_read(out, "feed.json")["items"]) == 2


def test_changelog_is_capped(paths, tmp_path):
    out = tmp_path / "pd"
    pdx.export(paths, out)
    ch = _read(out, "changes.json")
    ch["entries"] = [dict(ch["entries"][0], data_hash=f"h{i}") for i in range(150)]
    (out / "changes.json").write_text(json.dumps(ch))
    pdx.export(paths, out)
    assert len(_read(out, "changes.json")["entries"]) == pdx.CHANGES_KEEP
    assert len(_read(out, "feed.json")["items"]) == 30


def test_issue_form_asks_for_no_personal_data():
    form = yaml.safe_load((REPO_ROOT / ".github/ISSUE_TEMPLATE/data-error.yml").read_text())
    ids = {b.get("id") for b in form["body"] if b.get("id")}
    assert "page" in ids                                      # prefilled by the app's "Report an error" link
    assert not ids & {"name", "email", "phone", "id_number", "address"}
    privacy = next(b for b in form["body"] if b.get("id") == "privacy")
    assert all(o["required"] for o in privacy["attributes"]["options"])
    yaml.safe_load((REPO_ROOT / ".github/ISSUE_TEMPLATE/config.yml").read_text())


def test_app_social_card_routes_and_report_link():
    html = APP.read_text()
    img = re.search(r'property="og:image" content="([^"]+)"', html).group(1)
    assert img.startswith("https://") and (APP.parent / img.rsplit("/", 1)[1]).is_file()
    for meta in ("og:title", "og:description", "og:url", "twitter:card"):
        assert f'"{meta}"' in html
    assert "#\\/unknowns$" in html and "#\\/changes$" in html
    assert "0800 701 701" in html                              # report link removed (CHG-2026-012); hotline kept
    assert not re.search(r"farwaters|github\.com|github\.io|githubusercontent", html, re.I)
    assert 'href="#/unknowns"' in html and 'href="#/changes"' in html
    root = (REPO_ROOT / "index.html").read_text()
    assert 'property="og:image"' in root and "apps/public-dashboard/" in root


def test_glossary_page_route_nav_and_cited_thresholds():
    """CHG-2026-013: plain-language glossary; limits must match config/detectors.yaml."""
    import yaml
    html = APP.read_text()
    assert "#\\/glossary$" in html and 'href="#/glossary"' in html
    th = yaml.safe_load((REPO_ROOT / "config" / "detectors.yaml").read_text())["procurement_thresholds"]
    shown = {"metro": "R750 000", "local": "R300 000", "district": "R200 000"}
    for k, v in th["mfma"]["rand"].items():
        assert shown[k] == "R" + f"{v:,}".replace(",", " ") and shown[k] in html
    assert "R" + f"{th['pfma']['rand']['department']:,}".replace(",", " ") in html
    for u in ("Municipal%20SCM%20Amendment%20Regulations.pdf", "PFM%20SCM%20Instruction%20No.%2002%20of%202021-22"):
        assert u in html
    for d in ("D1", "D3", "D4", "D5", "D8", "D13", "D6", "D16", "D17"):
        assert f'det("{d}"' in html
