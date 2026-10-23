"""CHG-2026-016: case referral pack (pf case export)."""
import re
import subprocess
from pathlib import Path

from thusa.review import casepack as cp

ROOT = Path(__file__).resolve().parents[1]


def _flag(**kw):
    f = {
        "flag_id": "abc123", "detector_id": "D3_restricted_supplier_awarded", "detector_version": "0.1.0",
        "severity": "high", "score": 0.92, "review_status": "pending human review", "body_name": "Sample DM",
        "gov_body_id": "MUN:DC0", "period_label": "2023-03-25", "names_supplier": True,
        "subject_name": "ACME CONSTRUCTION", "evidence_hash": "0" * 64,
        "explanation": "Award to ACME CONSTRUCTION and to JOHN DOE. Pending human review; not a finding.",
        "evidence": [{"label": "eTenders OCDS record", "ocid": "ocds-9t57fa-1", "url": "https://example.org/pub",
                      "sha256": "a" * 64, "contactPoint_email": "x@y.co.za", "supplier_person_key": "PK-1"}],
        "matched": {"match": {"confidence": 0.92, "basis": "name", "award_supplier": "ACME CONSTRUCTION",
                              "register_name": "Acme Construction Pty Ltd"},
                    "tables": [("Award(s) on eTenders", [
                        {"ocid": "ocds-9t57fa-1", "supplier_name": "ACME CONSTRUCTION", "supplier_id": "8001015009087",
                         "value_cents": 400000000, "award_date": "2023-03-25", "contact_name": "Jane Roe",
                         "contact_email": "jane@buyer.gov.za", "contact_phone": "021 555 1234",
                         "supplier_person_key": "PK-9"},
                        {"ocid": "ocds-9t57fa-2", "supplier_name": "JOHN DOE", "value_cents": None}]),
                        ("Restricted Supplier register entry", [
                            {"name": "Acme Construction Pty Ltd", "is_person": 0, "cipc_reg_no": "2001/000001/07",
                             "period_from": "2021-01-01", "period_to": "2031-01-01",
                             "source_url": "https://ocpo.treasury.gov.za/RestrictedSupplier/RestrictedSuppliersReport.pdf"},
                            {"name": "Mary Major", "is_person": 1, "period_from": "2020-01-01"}])]},
        "raw_files": {},
    }
    f.update(kw)
    return f


def test_pack_has_no_emails_phones_or_person_keys():
    text = cp.render(_flag())
    assert not re.search(r"[\w.+-]+@[\w-]+\.\w", text)
    assert "021 555 1234" not in text and "person_key" not in text and "PK-" not in text
    assert "8001015009087" not in text and "2001/000001/07" not in text
    assert "Jane Roe" not in text and "Mary Major" not in text and "JOHN DOE" not in text
    assert cp.NATURAL_PERSON in text
    assert cp.scan(text) == []


def test_scan_catches_leaks():
    assert cp.scan("call 082 123 4567 or a@b.co.za id 8001015009087 supplier_person_key")
    assert cp.scan(f"hotline {cp.HOTLINE}") == []


def test_sample_pack_renders_required_sections():
    text = cp.render(_flag())
    for s in ("# Case referral pack: abc123", "not a finding of wrongdoing", "Restricted supplier",
              "## Comparison baseline", "## Evidence (with source lineage)", "## Official source records",
              "https://ocds-api.etenders.gov.za/api/OCDSReleases/release/ocds-9t57fa-1",
              "## Possible innocent explanations", "## Checklist for the independent checker",
              "## How to refer", cp.CW_REPORT, "0800 701 701", "ACME CONSTRUCTION", "R4,000,000", "Sample DM"):
        assert s in text, s


def test_natural_person_heuristic():
    assert cp.looks_like_natural_person("JOHN DOE")
    assert cp.looks_like_natural_person("Acme Ltd", is_person=1)
    assert not cp.looks_like_natural_person("NEXTEC ADVISORY")
    assert not cp.looks_like_natural_person("CALANDRIA 159")


def test_default_output_path_is_gitignored():
    r = subprocess.run(["git", "check-ignore", "-q", "data/cases/case-abc123.md"], cwd=ROOT)
    assert r.returncode == 0
    r = subprocess.run(["git", "ls-files", "data/cases"], cwd=ROOT, capture_output=True, text=True)
    assert r.stdout.strip() == ""


def test_cli_export_writes_file(tmp_path, monkeypatch):
    from thusa.review import cli

    class Svc:
        def get_flag(self, fid):
            return _flag() if fid == "abc123" else None
    monkeypatch.setattr(cli, "_svc", lambda: Svc())
    assert cli.main(["case", "export", "abc123", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "case-abc123.md").read_text().startswith("# Case referral pack")
    assert cli.main(["case", "export", "nope", "--out", str(tmp_path)]) == 2
