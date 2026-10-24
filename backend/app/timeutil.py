"""Naive-UTC timestamps matching the existing DateTime columns."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Replacement for the deprecated ``datetime.utcnow()``."""

    return datetime.now(UTC).replace(tzinfo=None)
