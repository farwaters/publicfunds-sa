"""CHG-2026-018 (CSI-031): IMF republication of Stats SA headline CPI (Dec 2024 = 100)."""
from datetime import date

import duckdb

from tests.conftest import SMALL
from tests.synth import build_raw
from thusa import parsers
from thusa.build import build
from thusa.settings import get_paths

IMF_XML = b"""<?xml version='1.0' encoding='UTF-8'?><message:StructureSpecificData
 xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"><message:DataSet>
<Series COUNTRY="ZAF" INDEX_TYPE="CPI" COICOP_1999="_T" TYPE_OF_TRANSFORMATION="IX" FREQUENCY="M"
 COMMON_REFERENCE_PERIOD="2024M12">
<Obs TIME_PERIOD="2024-M12" OBS_VALUE="100" REFERENCE_PERIOD="2024M12"/>
<Obs TIME_PERIOD="2025-M01" OBS_VALUE="100.3" REFERENCE_PERIOD="2024M12"/>
<Obs TIME_PERIOD="2025-M02" OBS_VALUE="" REFERENCE_PERIOD="2024M12"/>
</Series>
<Series COUNTRY="ZAF" INDEX_TYPE="CPI" COICOP_1999="CP01" TYPE_OF_TRANSFORMATION="IX" FREQUENCY="M">
<Obs TIME_PERIOD="2025-M01" OBS_VALUE="999" REFERENCE_PERIOD="2024M12"/>
</Series></message:DataSet></message:StructureSpecificData>"""


def test_imf_cpi_parser_keeps_headline_only_and_skips_blanks():
    rows = parsers.imf_cpi_rows(IMF_XML)
    assert [(r["year"], r["month"], r["index_value"]) for r in rows] == [(2024, 12, 100.0), (2025, 1, 100.3)]
    assert rows[0]["base_period"] == "Dec 2024" and rows[1]["source_locator"] == "Obs TIME_PERIOD=2025-M01"


def test_curated_cpi_prefers_imf_single_base_with_lineage(tmp_path):
    store = build_raw(tmp_path)
    store.save("imf_cpi", "imf_cpi_zaf_monthly.xml", IMF_XML, "https://example.org/imf.xml")
    p = get_paths(tmp_path)
    build(p, as_of=date(2026, 10, 19), fye_min=2023, fye_max=2026, min_rows=SMALL, secret=b"t")
    con = duckdb.connect(str(p.warehouse), read_only=True)
    rows = con.execute("SELECT year, month, index_value, base_period, source_id, source_url, source_sha256, "
                       "fetched_at_utc FROM curated.cpi ORDER BY year, month").fetchall()
    assert [(r[0], r[1], r[2]) for r in rows] == [(2024, 12, 100.0), (2025, 1, 100.3)]   # no OECD 2015-base rows mixed in
    assert all(r[3] == "Dec 2024" and r[4] == "imf_cpi" and r[5] and len(r[6]) == 64 and r[7] for r in rows)
