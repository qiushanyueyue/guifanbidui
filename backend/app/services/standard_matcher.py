"""Business decisions for comparing a cited reference with canonical metadata."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.standard_normalizer import normalize_standard_code, normalized_name


@dataclass(frozen=True)
class MatchDecision:
    match_type: str
    confidence: float
    recommended_citation: str
    message: str


def _citation(standard: object) -> str:
    name = str(getattr(standard, "name", "") or "").strip()
    code = str(getattr(standard, "normalized_code", "") or getattr(standard, "code", "") or "").strip()
    edition = str(getattr(standard, "edition", "") or "").strip()
    suffix = f"（{edition}）" if edition else ""
    return f"《{name}》{code}{suffix}" if name else f"{code}{suffix}"


def _code_family(code: str) -> tuple[str, str, str | None]:
    canonical = normalize_standard_code(code)
    if not canonical:
        return "", "", None
    head, _, tail = canonical.partition(" ")
    number, sep, year = tail.rpartition("-")
    return head.replace("/T", ""), number if sep else tail, year if sep else None


def assess_standard_match(*, input_code: str | None, input_name: str | None, standard: object) -> MatchDecision:
    status = str(getattr(standard, "status", "unknown") or "unknown")
    status_decisions = {
        "abolished": ("obsolete", "该标准已废止"),
        "replaced": ("replaced", "该标准已被替代"),
        "conflict": ("source_conflict", "第三方来源信息冲突，需人工核验"),
    }
    citation = _citation(standard)
    if status in status_decisions:
        match_type, message = status_decisions[status]
        return MatchDecision(match_type, 0.0, citation, message)
    if status == "unknown":
        return MatchDecision("unknown", 0.0, citation, "来源未确认当前状态，需人工核验")

    wanted_code = normalize_standard_code(input_code)
    actual_code = normalize_standard_code(getattr(standard, "normalized_code", None) or getattr(standard, "code", None))
    wanted_name = normalized_name(input_name)
    actual_name = normalized_name(getattr(standard, "normalized_name", None) or getattr(standard, "name", None))

    if wanted_code and wanted_code != actual_code:
        if _code_family(wanted_code) == _code_family(actual_code):
            return MatchDecision("code_type_mismatch", 0.9, citation, "标准类型标识不一致，请采用推荐编号")
        return MatchDecision("code_mismatch", 0.0, citation, "标准编号不一致")
    if wanted_name and actual_name and wanted_name != actual_name:
        return MatchDecision("name_mismatch", 0.5, citation, "标准名称不一致")
    if getattr(standard, "edition", None) and str(getattr(standard, "edition")) not in str(input_code or ""):
        return MatchDecision("revision_missing", 0.95, citation, "引用缺少当前修订版信息")
    if not wanted_code and not wanted_name:
        return MatchDecision("unknown", 0.0, citation, "缺少可判定的编号或名称")
    return MatchDecision("exact", 1.0, citation, "引用与规范库记录一致")
