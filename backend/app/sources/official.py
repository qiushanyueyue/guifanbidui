"""Configurable official-source adapters.

Official portals differ by deployment and often change markup.  These
adapters provide the shared contract and safe HTTP behavior while requiring a
configured public metadata endpoint before attempting a fetch.  They never
invent a status when an endpoint is unavailable.
"""

from __future__ import annotations

import os

from app.sources.base import HttpSource, SourceRecord, SourceUnavailable


class ConfiguredOfficialSource(HttpSource):
    endpoint_env: str = ""

    def _endpoint(self) -> str:
        endpoint = os.getenv(self.endpoint_env, "").strip()
        if not endpoint:
            raise SourceUnavailable(
                f"{self.endpoint_env} is not configured for {self.name}", source=self.name
            )
        return endpoint

    def search(self, query: str) -> list[SourceRecord]:
        raise SourceUnavailable(
            f"{self.name} search parser is not configured; use the scheduled recent endpoint",
            source=self.name,
        )

    def fetch_detail(self, url: str) -> SourceRecord | None:
        raise SourceUnavailable(
            f"{self.name} detail parser is not configured", source=self.name, url=url
        )

    def fetch_recent(self, limit: int = 100) -> list[SourceRecord]:
        # Keep this explicit: a successful HTTP response still needs a source
        # specific parser before it may affect canonical status.
        endpoint = self._endpoint()
        raise SourceUnavailable(
            f"{self.name} endpoint is configured but parser is pending; no data was applied",
            source=self.name,
            url=endpoint,
        )


class SamrSource(ConfiguredOfficialSource):
    name = "samr"
    priority = 0
    endpoint_env = "SAMR_RECENT_URL"


class MohurdSource(ConfiguredOfficialSource):
    name = "mohurd"
    priority = 0
    endpoint_env = "MOHURD_RECENT_URL"


class OpenStdSource(ConfiguredOfficialSource):
    name = "openstd"
    priority = 1
    endpoint_env = "OPENSTD_RECENT_URL"
