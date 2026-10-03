from pathlib import Path

import pytest

from app.sources import csres as csres_module
from app.sources.csres import parse_csres_detail_html, parse_csres_replacement_text, parse_csres_search_html
from app.sources.soujianzhu import parse_soujianzhu_recent_html
from app.sources.base import ParseError, RateLimited, SourceUnavailable
import requests


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


def test_real_csres_search_metadata_and_empty_page():
    record, = parse_csres_search_html((FIXTURES / "csres_search_live.html").read_text())
    assert (record.code, record.name, record.source_status) == ("GB 50009-2012", "建筑结构荷载规范", "现行")
    assert record.implement_date == "2012-10-01"
    assert record.issuing_authority == "住房和城乡建设部"
    assert record.source_url == "http://www.csres.com/detail/225280.html"
    assert parse_csres_search_html((FIXTURES / "csres_empty_live.html").read_text()) == []


def test_real_csres_detail_preserves_revision_and_old_standard_relation():
    record = parse_csres_detail_html((FIXTURES / "csres_detail_live.html").read_text(), url="http://www.csres.com/detail/212269.html")
    assert record.code == "GB/T 50010-2010"
    assert record.name == "混凝土结构设计标准（2024年版）"
    assert record.edition == "2024年版"
    assert record.source_status == "现行"
    assert record.replaces == "GB 50010-2002"
    assert record.replaced_by is None
    assert record.publish_date == "2010-08-18"


def test_csres_reordered_columns_and_direct_rows_are_not_positional():
    record, = parse_csres_search_html('''<table>
        <thead><tr><th>状态</th><th>标准名称</th><th>发布日期</th><th>标准编号</th><th>发布部门</th><th>实施日期</th></tr></thead>
        <tr><td>现行</td><td>测试规范</td><td>2020-01-01</td><td><a href="/detail/1.html">GB 1-2020</a></td><td>发布机构</td><td>2021-01-01</td></tr></table>''')
    assert record.code == "GB 1-2020"
    assert record.source_status == "现行"
    assert record.publish_date == "2020-01-01"
    assert record.implement_date == "2021-01-01"
    assert record.issuing_authority == "发布机构"


def test_csres_does_not_infer_status_or_authority_from_name_or_adjacent_cells():
    record, = parse_csres_search_html('''<table><tr><th>编号</th><th>中文名称</th></tr>
        <tr><td>GB 1-2020</td><td>现行建筑材料测试</td></tr></table>''')
    assert record.source_status is record.issuing_authority is record.implement_date is None
    record, = parse_csres_search_html((FIXTURES / "csres_search.html").read_text())[:1]
    assert record.issuing_authority is None


@pytest.mark.parametrize('html,error', [
    ('<title>安全验证</title><p>请输入验证码</p>', SourceUnavailable),
    ('<p>请求过于频繁，请稍后重试</p>', RateLimited),
    ('<html><p>没有结果表，但未确认零结果</p></html>', ParseError),
    ('<p>共找到1条相关标准</p><table><tr><th>标准编号</th><th>标准名称</th></tr></table>', ParseError),
    ('<title>错误页</title><p>共找到0条相关标准 抱歉，没有找到</p>', ParseError),
    ('<title>安全验证</title><p>共找到0条相关标准 抱歉，没有找到</p>', SourceUnavailable),
    ('<table><tr><th>标准编号</th><th>标准名称</th></tr><tr><td>乱码</td><td>名称</td></tr></table>', ParseError),
])
def test_csres_different_failures_do_not_become_empty_results(html, error):
    with pytest.raises(error):
        parse_csres_search_html(html)


def test_chinese_query_uses_csres_form_encoding(monkeypatch):
    adapter = csres_module.CsresSource()
    response = requests.Response()
    response.status_code = 200
    response.url = "http://www.csres.com/s.jsp"
    response._content = (FIXTURES / "csres_empty_live.html").read_text().encode('gb18030')
    response.headers['Content-Type'] = 'text/html;charset=gbk'
    prepared_urls = []
    def request(method, url, *, params):
        prepared_urls.append(requests.Request(method, url, params=params).prepare().url)
        return response
    monkeypatch.setattr(adapter, '_request', request)
    assert adapter.search('建标 143-2010') == []
    assert prepared_urls == ['http://www.csres.com/s.jsp?keyword=%BD%A8%B1%EA+143-2010']


def test_csres_diagnostics_include_response_shape_without_body(monkeypatch, caplog):
    adapter = csres_module.CsresSource()
    response = requests.Response()
    response.status_code = 200
    response.url = "http://www.csres.com/s.jsp"
    response._content = b'<html>private-body-marker</html>'
    response.headers['Content-Type'] = 'text/html;charset=gbk'
    monkeypatch.setattr(adapter, '_request', lambda *args, **kwargs: response)
    with pytest.raises(ParseError):
        adapter.search('GB 1-2020')
    assert 'HTTP_status=200' in caplog.text
    assert 'parse_result=parse_error' in caplog.text
    assert 'private-body-marker' not in caplog.text
