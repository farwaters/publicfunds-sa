from datetime import date

import pytest

from thusa import normalise as n


@pytest.mark.parametrize("raw,cents", [
    (None, None), ("", None), ("N/A", None), ("-", None), (float("nan"), None),
    ("0", 0), (0, 0), (12.34, 1234), ("1234,50", 123450), ("1,234", 123400), ("1,234.56", 123456),
    ("R 1 234,50", 123450), ("(500)", -50000), (9108938273.0, 910893827300), ("1e3", 100000),
])
def test_to_cents(raw, cents):
    assert n.to_cents(raw) == cents


def test_to_cents_unit_multiplier_thousands():
    assert n.to_cents("1,5", unit_multiplier=1000) == 150000


def test_to_cents_rejects_garbage_and_bool():
    with pytest.raises(ValueError):
        n.to_cents("abc")
    with pytest.raises(TypeError):
        n.to_cents(True)


def test_ocds_zero_is_unknown_not_zero():
    assert n.ocds_value_cents(0) == (None, "zero_placeholder")
    assert n.ocds_value_cents(None) == (None, "missing")
    assert n.ocds_value_cents(10.0) == (1000, "implausible_low")
    assert n.ocds_value_cents(1500.5) == (150050, None)
    assert n.ocds_value_cents(370817849750.0)[1] == "implausible_high"


def test_norm_name_strips_legal_suffixes():
    assert n.norm_name("BADCO TRADING (PTY) LTD") == n.norm_name("Badco Trading") == "badco trading"
    assert n.norm_name("Smith & Sons CC") == "smith sons"
    assert n.norm_name(None) is None


def test_person_key_order_insensitive():
    assert n.person_key("DOE, JANE") == n.person_key("Jane Doe") == "doe jane"


def test_muni_key():
    assert n.muni_key("City of Cape Town Metropolitan Municipality") == n.muni_key("Cape Town")
    assert n.muni_key("OR Tambo District Municipality") == n.muni_key("O R Tambo")
    assert n.muni_key("Cape Winelands DM") == "cape winelands"


def test_classify_identifier():
    assert n.classify_identifier("2015/123456/07") == ("cipc_reg", "2015/123456/07")
    assert n.classify_identifier(" 8001015009087 ") == ("sa_id", "8001015009087")
    assert n.classify_identifier("123") == ("other", "123")
    assert n.classify_identifier("") == ("none", None)


def test_hmac_is_keyed_and_stable():
    a = n.hmac_id(b"k1", "8001015009087")
    assert a == n.hmac_id(b"k1", "8001015009087") != n.hmac_id(b"k2", "8001015009087")
    assert len(a) == 64 and "8001015009087" not in a


def test_fiscal_years():
    assert n.municipal_fy_label(2024) == "2023/24"
    assert n.national_fy_label(2025) == "2025/26"
    assert n.municipal_fye_for_date(date(2023, 7, 1)) == 2024
    assert n.municipal_fye_for_date(date(2024, 6, 30)) == 2024


def test_parse_date_sentinels():
    assert n.parse_date("0001-01-01T00:00:00Z") is None
    assert n.parse_date("2024-08-29T00:00:00Z") == date(2024, 8, 29)
    assert n.parse_date("garbage") is None
