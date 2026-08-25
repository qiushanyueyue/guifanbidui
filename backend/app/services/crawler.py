"""Compatibility facade for legacy callers.

New code uses ``app.sources`` and scheduled sync jobs.  These wrappers keep
old scripts/imports working without allowing ordinary API search to trigger a
network request.
"""

from __future__ import annotations

from app.sources.csres import CsresSource


def search_csres(keyword: str):
    return [
        {
            "code": item.code,
            "name": item.name,
            "status": item.source_status or "",
            "url": item.source_url or "",
            "source": "csres",
        }
        for item in CsresSource().search(keyword)
    ]


def get_standard_detail(url: str):
    record = CsresSource().fetch_detail(url)
    if record is None:
        return {"url": url}
    return {
        "url": record.source_url,
        "code": record.code,
        "name": record.name,
        "status": record.source_status or "",
        "department": record.issuing_authority or "-",
        "release_date": record.publish_date or "-",
        "implement_date": record.implement_date or "-",
        "obsolete_date": record.abolish_date or "-",
        "replaces": record.replaces or "-",
        "replaced_by": record.replaced_by or "-",
    }
