"""工标网 CSRES adapter and fixture-testable parsers."""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
from typing import Any

from bs4 import BeautifulSoup

from app.services.standard_normalizer import extract_standard_codes, normalize_standard_code, parse_edition, parse_standard_code
from app.sources.base import HttpSource, ParseError, SourceRecord, SourceUnavailable

logger = logging.getLogger(__name__)

BASE_URL = "http://www.csres.com"
SEARCH_URL = f"{BASE_URL}/s.jsp"


def _status_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").strip("-：:")


def has_mandatory_clause_repeal(value: str | None) -> bool:
    raw = re.sub(r"\s+", "", str(value or ""))
    return "强制性" in raw and any(marker in raw for marker in ("废止", "废除", "不再适用"))


def _is_clause_level_notice(segment: str) -> bool:
    compact = re.sub(r"\s+", "", segment)
    return "强制性" in compact or (
        "局部修订" in compact and any(marker in compact for marker in ("条文", "条款", "第"))
    )


def parse_csres_replacement_text(value: str | None) -> tuple[list[str], list[str]]:
    """Split the old and new sides of CSRES compound replacement prose."""

    raw = str(value or "").strip()
    if not raw:
        return [], []
    # CSRES often appends notices such as "GB 550xx 实施后，相关强制性条文废止".
    # That is clause-level evidence, not a whole-standard replacement edge.
    raw = ";".join(
        segment
        for segment in re.split(r"[;；。]", raw)
        if not _is_clause_level_notice(segment)
    ).strip()
    if not raw:
        return [], []
    if "被" in raw:
        before, after = raw.split("被", 1)
        replaces = [item.normalized for item in extract_standard_codes(before)]
        replaced_by = [item.normalized for item in extract_standard_codes(after)]
        return replaces, replaced_by
    codes = [item.normalized for item in extract_standard_codes(raw)]
    return codes, []


def parse_csres_search_html(html: str, *, base_url: str = BASE_URL) -> list[SourceRecord]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    target = next((table for table in tables if "heng" in (table.get("class") or [])), None)
    if target is None:
        target = next((table for table in tables if table.find("thead")), None)
    if target is None:
        target = next((table for table in tables if "标准编号" in table.get_text(" ", strip=True)), None)
    if target is None:
        raise ParseError("CSRES search table was not found", source="csres")

    header = target.find("tr")
    status_idx = 2
    if header:
        for index, cell in enumerate(header.find_all(["th", "td"])):
            if "状态" in cell.get_text(" ", strip=True):
                status_idx = index
                break

    records: list[SourceRecord] = []
    rows = target.find_all("tr", recursive=False) or target.find_all("tr")
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        parsed_code = parse_standard_code(cells[0].get_text(" ", strip=True))
        code = parsed_code.normalized if parsed_code else ""
        name = cells[1].get_text(" ", strip=True)
        if not code or not name or len(code) > 120:
            continue
        status = _status_text(cells[status_idx].get_text(" ", strip=True)) if len(cells) > status_idx else ""
        if not status:
            status = next(
                (
                    _status_text(cell.get_text(" ", strip=True))
                    for cell in cells
                    if any(marker in cell.get_text(" ", strip=True) for marker in ("现行", "废止", "即将实施", "被替代"))
                ),
                "",
            )
        link = cells[0].find("a")
        href = link.get("href") if link else None
        url = urllib.parse.urljoin(base_url, href) if href else None
        edition = parse_edition(name)
        records.append(
            SourceRecord(
                source_name="csres",
                code=code,
                name=name,
                source_status=status or None,
                source_url=url,
                implement_date=cells[3].get_text(" ", strip=True) if len(cells) > 3 else None,
                issuing_authority=cells[2].get_text(" ", strip=True) if len(cells) > 2 else None,
                edition=edition.edition,
                revision_year=edition.revision_year,
                amendment=edition.amendment,
                raw_payload={"status": status, "row": row.get_text(" ", strip=True)},
            )
        )
    return records


def parse_csres_detail_html(html: str, *, url: str) -> SourceRecord:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    def field(label: str) -> str | None:
        label_node = soup.find(string=re.compile(re.escape(label)))
        if not label_node:
            return None
        parent = label_node.find_parent(["td", "th", "li", "div"])
        if not parent:
            return None
        sibling = parent.find_next_sibling(["td", "th", "li", "div"])
        return sibling.get_text(" ", strip=True) if sibling else None

    code_match = re.search(r"标准编号\s*[:：]?\s*([A-Za-z/]+\s*[A-Za-z]?\s*[0-9IOl]+(?:[-.]\s*[0-9IOl]+)*\s*[-—]\s*[0-9IOl]{4})", page_text)
    code = normalize_standard_code(code_match.group(1)) if code_match else ""
    status_match = re.search(r"标准状态\s*[:：]?\s*(现行有效|现行|即将实施|已废止|废止|已作废|作废|被替代|局部修订)", page_text)
    name = field("中文名称") or field("标准名称") or ""
    title_text = soup.title.get_text(" ", strip=True) if soup.title else ""
    if code and title_text:
        title_without_code = re.sub(re.escape(code), "", title_text, count=1, flags=re.IGNORECASE)
        title_without_code = re.sub(
            r"\s+(?:国家标准|行业标准|地方标准|团体标准).*?工标网.*$",
            "",
            title_without_code,
        )
        title_without_code = re.sub(r"[-—]\s*工标网.*$", "", title_without_code).strip()
        if title_without_code:
            name = title_without_code
    if not code:
        # Some detail pages use the document title instead of a labelled row.
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        parsed_codes = extract_standard_codes(title)
        code = parsed_codes[0].normalized if parsed_codes else ""
    if not code:
        raise ParseError("CSRES detail page has no standard code", source="csres", url=url)
    edition = parse_edition(name)
    raw_replacement = field("替代情况") or field("被替代标准")
    replaces, replaced_by = parse_csres_replacement_text(raw_replacement)
    return SourceRecord(
        source_name="csres",
        code=code,
        name=name,
        source_status=(status_match.group(1) if status_match else field("标准状态")),
        source_url=url,
        edition=edition.edition,
        revision_year=edition.revision_year,
        amendment=edition.amendment,
        publish_date=field("发布日期"),
        implement_date=field("实施日期"),
        abolish_date=field("废止日期"),
        replaces="; ".join(replaces) or None,
        replaced_by="; ".join(replaced_by) or None,
        issuing_authority=field("发布部门"),
        raw_payload={"html_fields": True, "raw_replacement_text": raw_replacement},
    )


class CsresSource(HttpSource):
    name = "csres"
    priority = 3

    def search(self, query: str) -> list[SourceRecord]:
        started = time.monotonic()
        response = self._request("GET", SEARCH_URL, params={"keyword": query})
        html = self.response_text(response, fallback_encoding="gb18030")
        try:
            records = parse_csres_search_html(html)
        except ParseError as exc:
            self._log_parse_failure(url=response.url, error=exc, elapsed=time.monotonic() - started)
            raise
        logger.info(
            "source=csres standard_code=%s URL=%s HTTP_status=%s parse_result=ok elapsed=%.3f retry_count=0",
            query,
            response.url,
            response.status_code,
            time.monotonic() - started,
        )
        return [self.normalize(record) for record in records]

    def fetch_detail(self, url: str) -> SourceRecord | None:
        started = time.monotonic()
        response = self._request("GET", url)
        html = self.response_text(response, fallback_encoding="gb18030")
        try:
            record = parse_csres_detail_html(html, url=url)
        except ParseError as exc:
            self._log_parse_failure(url=url, error=exc, elapsed=time.monotonic() - started)
            raise
        logger.info(
            "source=csres standard_code=%s URL=%s HTTP_status=%s parse_result=ok elapsed=%.3f retry_count=0",
            record.normalized_code,
            url,
            response.status_code,
            time.monotonic() - started,
        )
        return self.normalize(record)

    def fetch_recent(self, limit: int = 100) -> list[SourceRecord]:
        endpoint = __import__("os").getenv("CSRES_RECENT_URL", "").strip()
        if not endpoint:
            raise SourceUnavailable(
                "CSRES recent endpoint is not configured; use search/detail or set CSRES_RECENT_URL",
                source=self.name,
            )
        response = self._request("GET", endpoint, params={"limit": min(limit, 500)})
        html = self.response_text(response, fallback_encoding="gb18030")
        records = parse_csres_search_html(html)
        return [self.normalize(record) for record in records[:limit]]
