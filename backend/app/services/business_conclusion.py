"""User-facing business conclusions derived from canonical status and revisions."""

from __future__ import annotations

from app.models.enums import StandardStatus, normalize_status


def revision_requirement(standard: object) -> str | None:
    edition = str(getattr(standard, "edition", "") or "").strip()
    amendment = str(getattr(standard, "amendment", "") or "").strip()
    parts = [part for part in (edition, amendment) if part]
    return "+".join(parts) or None


def business_conclusion(standard: object) -> str:
    """Return the decisive conclusion shown to designers, not an audit label."""

    status = normalize_status(getattr(standard, "status", None))
    revision = revision_requirement(standard)
    if status in {StandardStatus.CURRENT, StandardStatus.PARTIALLY_AMENDED}:
        if revision:
            return f"现行，需采用{revision}"
        if status == StandardStatus.PARTIALLY_AMENDED:
            return "现行，但需采用最新局部修订"
        return "现行"
    if status == StandardStatus.ABOLISHED:
        return "已废止"
    if status == StandardStatus.REPLACED:
        replacement = str(getattr(standard, "replaced_by", "") or "").strip()
        return f"已被替代，建议采用{replacement}" if replacement else "已被替代"
    if status == StandardStatus.UPCOMING:
        return "即将实施"
    return "暂无法确认"
