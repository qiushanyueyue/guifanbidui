from pathlib import Path

import pytest

from app.sources.csres import parse_csres_detail_html, parse_csres_replacement_text, parse_csres_search_html
from app.sources.soujianzhu import parse_soujianzhu_recent_html
from app.sources.base import ParseError


FIXTURES = Path(__file__).parent / "fixtures"


def test_csres_fixture_parser():
    records = parse_csres_search_html((FIXTURES / "csres_search.html").read_text())
    assert [record.code for record in records] == ["GB 55001-2021", "GB/T 50010-2010"]
    assert records[0].source_status == "现行"
    assert records[1].source_status == "废止"


def test_csres_detail_fixture_parser():
    record = parse_csres_detail_html((FIXTURES / "csres_detail.html").read_text(), url="http://example/detail")
    assert record.code == "GB 55001-2021"
    assert record.name == "工程结构通用规范"
    assert record.source_status == "现行"
    assert record.implement_date == "2022-01-01"


def test_soujianzhu_fixture_parser():
    records = parse_soujianzhu_recent_html((FIXTURES / "soujianzhu_recent.html").read_text())
    assert records[0].normalized_code == "GB 55001-2021"
    assert records[1].edition == "2018年版"


def test_csres_structure_change_is_visible():
    with pytest.raises(ParseError):
        parse_csres_search_html("<html><body><p>changed</p></body></html>")


def test_csres_compound_replacement_text_is_split_by_direction():
    replaces, replaced_by = parse_csres_replacement_text(
        "GB 50157-1992 ;被 GB 50157-2013 代替并废止"
    )
    assert replaces == ["GB 50157-1992"]
    assert replaced_by == ["GB 50157-2013"]
