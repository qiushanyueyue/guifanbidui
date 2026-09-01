from pathlib import Path

import pytest

from app.sources import csres as csres_module
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
    assert "/NormAndRules/NormContent.aspx?id=" in records[0].source_url


def test_soujianzhu_explicit_status_is_preserved_as_third_party_evidence():
    records = parse_soujianzhu_recent_html(
        """
        <table>
          <tr><td><a href="/NormAndRules/gfnr.aspx?id=1">《工程结构通用规范》GB 55001-2021</a></td><td>现行</td></tr>
          <tr><td><a href="/NormAndRules/gfnr.aspx?id=2">《旧规范》GB 50000-2001</a></td><td>已废止</td></tr>
        </table>
        """
    )
    assert [record.source_status for record in records] == ["现行", "已废止"]
    assert records[0].source_url == "https://www.soujianzhu.cn/NormAndRules/NormContent.aspx?id=1"


def test_csres_structure_change_is_visible():
    with pytest.raises(ParseError):
        parse_csres_search_html("<html><body><p>changed</p></body></html>")


def test_csres_compound_replacement_text_is_split_by_direction():
    replaces, replaced_by = parse_csres_replacement_text(
        "GB 50157-1992 ;被 GB 50157-2013 代替并废止"
    )
    assert replaces == ["GB 50157-1992"]
    assert replaced_by == ["GB 50157-2013"]


def test_mandatory_clause_repeal_is_not_parsed_as_whole_standard_replacement():
    text = "替代 GB 50157-2003 ;自《城市轨道交通工程项目规范》 GB 55033-2022 实施之日起，该标准相关强制性条文同时废止"
    replaces, replaced_by = parse_csres_replacement_text(text)
    assert replaces == ["GB 50157-2003"]
    assert replaced_by == []
    assert csres_module.has_mandatory_clause_repeal(text) is True


def test_numbered_mandatory_articles_are_also_clause_level_evidence():
    text = "替代 GB 50345-2004 ;自 GB 55030-2022 实施之日起，该标准相关强制性第3.0.5、4.5.1条同时废止"
    replaces, replaced_by = parse_csres_replacement_text(text)
    assert replaces == ["GB 50345-2004"]
    assert replaced_by == []
    assert csres_module.has_mandatory_clause_repeal(text) is True


def test_partial_revision_notice_is_not_a_whole_standard_replacement():
    text = "《城市综合管廊工程技术标准》（GB/T 50838-2015）局部修订的条文，自2025年4月1日起实施，本标准的第3.3节同时废止"
    assert parse_csres_replacement_text(text) == ([], [])
