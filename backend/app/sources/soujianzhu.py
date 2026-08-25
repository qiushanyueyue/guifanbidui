"""搜建筑 change-detection adapter.

The adapter consumes only public metadata pages.  It intentionally requires
an endpoint configured by deployment rather than assuming an undocumented
page layout, so a site change becomes a visible sync failure.
"""

from __future__ import annotations

import logging
import os
import re
import time
import urllib.parse

from bs4 import BeautifulSoup

from app.services.standard_normalizer import normalize_standard_code, parse_edition, split_standard_reference
from app.sources.base import HttpSource, ParseError, SourceRecord, SourceUnavailable

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.soujianzhu.cn"


def parse_soujianzhu_recent_html(html: str, *, base_url: str = DEFAULT_BASE_URL) -> list[SourceRecord]:
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", href=True)
    records: list[SourceRecord] = []
    for link in links:
        href = urllib.parse.urljoin(base_url, link.get("href", ""))
        if "NormContent" not in href and "NormAndRules" not in href:
            continue
        text = re.sub(r"\s+", " ", link.get_text(" ", strip=True))
        if not text:
            continue
        name, code, edition = split_standard_reference(text)
        if code is None:
            # Some pages put the reference in a sibling or title attribute.
            context = " ".join(filter(None, [text, link.get("title", "")]))
            name, code, edition = split_standard_reference(context)
        if code is None:
            continue
        records.append(
            SourceRecord(
                source_name="soujianzhu",
                code=normalize_standard_code(code.normalized),
                name=name,
                source_url=href,
                edition=edition.edition,
                revision_year=edition.revision_year,
                amendment=edition.amendment,
                raw_payload={"text": text},
            )
        )
    if not records:
        # Detail pages frequently render the code in plain text rather than
        # as an anchor.  Parse the public metadata text as a fallback, while
        # still failing if no code can be found.
        page_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        name, code, edition = split_standard_reference(page_text)
        if code is not None:
            records.append(
                SourceRecord(
                    source_name="soujianzhu",
                    code=code.normalized,
                    name=name,
                    source_url=base_url,
                    edition=edition.edition,
                    revision_year=edition.revision_year,
                    amendment=edition.amendment,
                    raw_payload={"text": page_text[:2000]},
                )
            )
    if not records:
        raise ParseError("Soujianzhu page has no parseable standard records", source="soujianzhu")
    return records


class SoujianzhuSource(HttpSource):
    name = "soujianzhu"
    priority = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = os.getenv("SOUJIANZHU_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    def search(self, query: str) -> list[SourceRecord]:
        endpoint = os.getenv("SOUJIANZHU_SEARCH_URL", "").strip()
        if not endpoint:
            raise SourceUnavailable("SOUJIANZHU_SEARCH_URL is not configured", source=self.name)
        response = self._request("GET", endpoint, params={"q": query})
        records = parse_soujianzhu_recent_html(self.response_text(response), base_url=self.base_url)
        return [self.normalize(record) for record in records]

    def fetch_detail(self, url: str) -> SourceRecord | None:
        response = self._request("GET", url)
        records = parse_soujianzhu_recent_html(self.response_text(response), base_url=self.base_url)
        for record in records:
            if record.source_url == url:
                return self.normalize(record)
        return self.normalize(records[0]) if records else None

    def fetch_recent(self, limit: int = 100) -> list[SourceRecord]:
        endpoint = os.getenv("SOUJIANZHU_RECENT_URL", "").strip()
        if not endpoint:
            raise SourceUnavailable("SOUJIANZHU_RECENT_URL is not configured", source=self.name)
        started = time.monotonic()
        response = self._request("GET", endpoint, params={"limit": min(limit, 500)})
        try:
            records = parse_soujianzhu_recent_html(self.response_text(response), base_url=self.base_url)
        except ParseError as exc:
            self._log_parse_failure(url=endpoint, error=exc, elapsed=time.monotonic() - started)
            raise
        logger.info(
            "source=soujianzhu standard_code=%s URL=%s HTTP_status=%s parse_result=ok elapsed=%.3f retry_count=0",
            "",
            endpoint,
            response.status_code,
            time.monotonic() - started,
        )
        return [self.normalize(record) for record in records[:limit]]
