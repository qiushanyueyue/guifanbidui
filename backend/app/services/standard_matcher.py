"""Business decisions for comparing a cited reference with canonical metadata."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.standard_normalizer import normalize_standard_code, normalized_name
from app.services.business_conclusion import business_conclusion, revision_requirement


@dataclass(frozen=True)
class MatchDecision:
    match_type: str
    confidence: float
    recommended_citation: str
    message: str


def _citation(standard: object) -> str:
    name = str(getattr(standard, "name", "") or "").strip()
    code = str(getattr(standard, "normalized_code", "") or getattr(standard, "code", "") or "").strip()
    revision = revision_requirement(standard)
    suffix = f"（{revision}）" if revision else ""
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
        "conflict": ("source_conflict", "来源信息冲突，暂无法确认"),
    }
    citation = _citation(standard)
    if status in status_decisions:
        match_type, message = status_decisions[status]
        return MatchDecision(match_type, 0.0, citation, message)
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
    revision = revision_requirement(standard)
    if revision:
        reference = str(input_code or "")
        missing_parts = [part for part in revision.split("+") if part not in reference]
        if missing_parts:
            return MatchDecision("revision_missing", 0.95, citation, f"规范现行，但引用需采用{revision}")
    if not wanted_code and not wanted_name:
        return MatchDecision("unknown", 0.0, citation, "缺少可判定的编号或名称")
    if status == "unknown":
        return MatchDecision("exact", 1.0, citation, "引用与来源记录完全一致；规范状态暂无法确认")
    return MatchDecision("exact", 1.0, citation, f"引用一致；{business_conclusion(standard)}")
