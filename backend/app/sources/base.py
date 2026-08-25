"""Common source adapter primitives and typed HTTP failures."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import requests

from app.models.enums import StandardStatus, normalize_status
from app.services.standard_normalizer import normalize_standard_code, parse_edition

logger = logging.getLogger(__name__)


class SourceError(RuntimeError):
    category = "source_error"

    def __init__(self, message: str, *, source: str = "unknown", url: str | None = None, status_code: int | None = None, retries: int = 0):
        super().__init__(message)
        self.source = source
        self.url = url
        self.status_code = status_code
        self.retries = retries


class NotFound(SourceError):
    category = "not_found"


class SourceUnavailable(SourceError):
    category = "source_unavailable"


class ParseError(SourceError):
    category = "parse_error"


class RateLimited(SourceError):
    category = "rate_limited"


class RequestTimeout(SourceError):
    category = "timeout"


@dataclass
class SourceRecord:
    source_name: str
    code: str
    name: str = ""
    source_status: str | StandardStatus | None = None
    source_url: str | None = None
    edition: str | None = None
    revision_year: str | None = None
    amendment: str | None = None
    publish_date: str | None = None
    implement_date: str | None = None
    abolish_date: str | None = None
    replaces: str | None = None
    replaced_by: str | None = None
    issuing_authority: str | None = None
    source_updated_at: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_code(self) -> str:
        return normalize_standard_code(self.code)

    @property
    def status(self) -> StandardStatus:
        return normalize_status(self.source_status)

    @property
    def content_hash(self) -> str:
        payload = {
            "code": self.normalized_code,
            "name": self.name,
            "status": self.status.value,
            "source_url": self.source_url,
            "edition": self.edition,
            "revision_year": self.revision_year,
            "amendment": self.amendment,
            "publish_date": self.publish_date,
            "implement_date": self.implement_date,
            "abolish_date": self.abolish_date,
            "replaces": self.replaces,
            "replaced_by": self.replaced_by,
            "source_updated_at": self.source_updated_at,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class StandardSource:
    """Adapter interface used by scheduled sync jobs, never ordinary search."""

    name = "base"
    priority = 99

    def search(self, query: str) -> list[SourceRecord]:
        raise NotImplementedError

    def fetch_detail(self, url: str) -> SourceRecord | None:
        raise NotImplementedError

    def fetch_recent(self, limit: int = 100) -> list[SourceRecord]:
        raise NotImplementedError

    def normalize(self, record: SourceRecord) -> SourceRecord:
        record.code = record.normalized_code
        edition = parse_edition(" ".join(filter(None, [record.edition, record.name])))
        if not record.edition:
            record.edition = edition.edition
        if not record.revision_year:
            record.revision_year = edition.revision_year
        if not record.amendment:
            record.amendment = edition.amendment
        return record


class HttpSource(StandardSource):
    """Requests session with bounded retries, rate limiting, and decoding."""

    user_agent = "GuifanBidui/2.0 (+public-standard-metadata; contact=repository-owner)"

    def __init__(self, *, session: requests.Session | None = None, timeout: float = 10.0, min_interval: float = 0.5):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent, "Accept": "text/html,application/json"})
        self.timeout = timeout
        self.min_interval = max(0.0, min_interval)
        self._last_request = 0.0

    def _request(self, method: str, url: str, *, params: dict[str, Any] | None = None, max_retries: int = 3, **kwargs) -> requests.Response:
        for attempt in range(max_retries + 1):
            wait = self.min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    timeout=kwargs.pop("timeout", self.timeout),
                    **kwargs,
                )
            except requests.Timeout as exc:
                if attempt >= max_retries:
                    raise RequestTimeout(
                        f"{self.name} request timed out", source=self.name, url=url, retries=attempt
                    ) from exc
                time.sleep(min(8.0, 0.5 * (2**attempt) + random.random() * 0.2))
                continue
            except requests.RequestException as exc:
                if attempt >= max_retries:
                    raise SourceUnavailable(
                        f"{self.name} request failed", source=self.name, url=url, retries=attempt
                    ) from exc
                time.sleep(min(8.0, 0.5 * (2**attempt) + random.random() * 0.2))
                continue

            if response.status_code == 429:
                if attempt >= max_retries:
                    raise RateLimited(
                        f"{self.name} rate limited", source=self.name, url=url, status_code=429, retries=attempt
                    )
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = min(30.0, float(retry_after)) if retry_after else 0.5 * (2**attempt)
                except ValueError:
                    delay = 0.5 * (2**attempt)
                time.sleep(delay)
                continue
            if response.status_code >= 500:
                if attempt >= max_retries:
                    raise SourceUnavailable(
                        f"{self.name} server error", source=self.name, url=url, status_code=response.status_code, retries=attempt
                    )
                time.sleep(min(8.0, 0.5 * (2**attempt) + random.random() * 0.2))
                continue
            if response.status_code == 404:
                raise NotFound(f"{self.name} page not found", source=self.name, url=url, status_code=404, retries=attempt)
            if response.status_code >= 400:
                raise SourceUnavailable(
                    f"{self.name} returned HTTP {response.status_code}",
                    source=self.name,
                    url=url,
                    status_code=response.status_code,
                    retries=attempt,
                )
            return response
        raise SourceUnavailable(f"{self.name} request exhausted retries", source=self.name, url=url, retries=max_retries)

    @staticmethod
    def response_text(response: requests.Response, fallback_encoding: str = "utf-8") -> str:
        # requests' apparent_encoding is derived from the payload and is more
        # reliable than hard-coding GBK for every page.
        encoding = response.apparent_encoding or response.encoding or fallback_encoding
        try:
            return response.content.decode(encoding, errors="replace")
        except (LookupError, UnicodeError):
            return response.content.decode(fallback_encoding, errors="replace")

    def _log_parse_failure(self, *, url: str, error: Exception, elapsed: float, retries: int = 0) -> None:
        logger.warning(
            "source=%s standard_code=%s URL=%s HTTP_status=%s parse_result=failed elapsed=%.3f retry_count=%s error=%s",
            self.name,
            "",
            url,
            "unknown",
            elapsed,
            retries,
            error.__class__.__name__,
        )
