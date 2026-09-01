"""Enumerations and value normalization shared by the API and sync jobs."""

from __future__ import annotations

from enum import Enum


class StandardStatus(str, Enum):
    CURRENT = "current"
    UPCOMING = "upcoming"
    ABOLISHED = "abolished"
    REPLACED = "replaced"
    PARTIALLY_AMENDED = "partially_amended"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class VerificationLevel(str, Enum):
    OFFICIAL = "official"
    CROSS_VERIFIED = "cross_verified"
    SINGLE_SOURCE = "single_source"
    UNVERIFIED = "unverified"
    CONFLICT = "conflict"


class RelationType(str, Enum):
    REPLACES = "replaces"
    REPLACED_BY = "replaced_by"
    AMENDS = "amends"
    AMENDED_BY = "amended_by"
    PARTIALLY_REPLACES = "partially_replaces"


class ParseStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    NOT_FOUND = "not_found"


_STATUS_ALIASES = {
    "current": StandardStatus.CURRENT,
    "现行": StandardStatus.CURRENT,
    "现行有效": StandardStatus.CURRENT,
    "有效": StandardStatus.CURRENT,
    "upcoming": StandardStatus.UPCOMING,
    "即将实施": StandardStatus.UPCOMING,
    "待实施": StandardStatus.UPCOMING,
    "abolished": StandardStatus.ABOLISHED,
    "废止": StandardStatus.ABOLISHED,
    "作废": StandardStatus.ABOLISHED,
    "失效": StandardStatus.ABOLISHED,
    "replaced": StandardStatus.REPLACED,
    "被替代": StandardStatus.REPLACED,
    "已替代": StandardStatus.REPLACED,
    "partially_amended": StandardStatus.PARTIALLY_AMENDED,
    "局部修订": StandardStatus.PARTIALLY_AMENDED,
    "部分修订": StandardStatus.PARTIALLY_AMENDED,
    "修改单": StandardStatus.PARTIALLY_AMENDED,
    "unknown": StandardStatus.UNKNOWN,
    "待核验": StandardStatus.UNKNOWN,
    "": StandardStatus.UNKNOWN,
    "conflict": StandardStatus.CONFLICT,
    "来源冲突": StandardStatus.CONFLICT,
}


def normalize_status(value: object) -> StandardStatus:
    """Map source-specific status text to the finite internal vocabulary."""

    if isinstance(value, StandardStatus):
        return value
    text = str(value or "").strip().lower()
    if text in _STATUS_ALIASES:
        return _STATUS_ALIASES[text]
    # Sources often append a date or explanation to the status label.
    for marker, status in (
        ("即将实施", StandardStatus.UPCOMING),
        ("废止", StandardStatus.ABOLISHED),
        ("作废", StandardStatus.ABOLISHED),
        ("被替代", StandardStatus.REPLACED),
        ("局部修订", StandardStatus.PARTIALLY_AMENDED),
        ("部分修订", StandardStatus.PARTIALLY_AMENDED),
        ("现行", StandardStatus.CURRENT),
    ):
        if marker in text:
            return status
    return StandardStatus.UNKNOWN


STATUS_LABELS = {
    StandardStatus.CURRENT: "现行",
    StandardStatus.UPCOMING: "即将实施",
    StandardStatus.ABOLISHED: "废止",
    StandardStatus.REPLACED: "被替代",
    StandardStatus.PARTIALLY_AMENDED: "局部修订",
    StandardStatus.UNKNOWN: "暂无法确认",
    StandardStatus.CONFLICT: "暂无法确认",
}


def status_label(value: object) -> str:
    return STATUS_LABELS[normalize_status(value)]
