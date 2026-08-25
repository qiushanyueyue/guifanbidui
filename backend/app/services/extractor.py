"""Local-first extraction of standard references from design text."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import List, Optional

from app.models.schemas import StandardInfo
from app.services.standard_normalizer import (
    clean_standard_name,
    extract_standard_codes,
    normalize_standard_code,
    parse_standard_code,
    parse_edition,
)

logger = logging.getLogger(__name__)


_LOGICAL_ITEM_BOUNDARY_RE = re.compile(
    r"\r?\n|(?=[（(]\s*\d{1,3}\s*[)）])"
)
_INLINE_ANNOTATION_RE = re.compile(
    r"^\s*(?:[,，;；:：、]\s*)?[）)]?\s*"
    r"(?P<annotation>[（(][^）)]{0,120}[）)]|\d{4}\s*年?\s*版)"
)
_CODE_SEARCH_TRANSLATION = str.maketrans(
    {"／": "/", "－": "-", "–": "-", "—": "-", "﹣": "-", "　": " "}
)


def _iter_logical_segments(raw: str) -> list[str]:
    """Split references at lines and numbered list items, not editions."""

    boundaries = [0]
    for match in _LOGICAL_ITEM_BOUNDARY_RE.finditer(raw):
        boundary = match.end() if match.group(0) else match.start()
        if boundary > boundaries[-1]:
            boundaries.append(boundary)
    boundaries.append(len(raw))
    return [
        raw[start:end]
        for start, end in zip(boundaries, boundaries[1:])
        if raw[start:end].strip()
    ]


def _locate_segment_codes(segment: str) -> list[tuple[object, int]]:
    """Pair extracted codes with positions in the same logical segment."""

    searchable = segment.translate(_CODE_SEARCH_TRANSLATION)
    located: list[tuple[object, int]] = []
    search_from = 0
    for code in extract_standard_codes(segment):
        position = searchable.find(code.raw, search_from)
        if position < 0:
            position = searchable.find(code.raw)
        if position < 0:
            continue
        located.append((code, position))
        search_from = position + len(code.raw)
    located.sort(key=lambda item: item[1])
    return located


def _parse_inline_edition(text: str):
    match = _INLINE_ANNOTATION_RE.match(text)
    return parse_edition(match.group("annotation")) if match else parse_edition("")


def extract_standards_from_text(text: str) -> List[StandardInfo]:
    """Extract references without sending the design document to a remote LLM.

    Remote extraction is an explicit opt-in for administrators and is never a
    required part of database synchronization.  The local parser handles
    quoted names, code-only references, editions, and common OCR glyphs.
    """

    if not text or not text.strip():
        return []

    raw = str(text)
    standards: list[StandardInfo] = []
    seen: set[tuple[str, str, str | None]] = set()
    for segment in _iter_logical_segments(raw):
        quoted_names = list(re.finditer(r"《(?P<name>[^》]{1,500})》", segment))
        located_codes = _locate_segment_codes(segment)
        associated_quotes: set[int] = set()

        for index, (code, position) in enumerate(located_codes):
            name = ""
            candidates = [item for item in quoted_names if item.end() <= position]
            selected = candidates[-1] if candidates and position - candidates[-1].end() <= 180 else None
            if selected:
                between = segment[selected.end() : position]
                if not extract_standard_codes(between):
                    name = clean_standard_name(selected.group("name"))
                    associated_quotes.add(selected.start())

            next_position = (
                located_codes[index + 1][1] if index + 1 < len(located_codes) else len(segment)
            )
            edition_info = _parse_inline_edition(
                segment[position + len(code.raw) : next_position]
            )
            key = (code.normalized, name, edition_info.edition)
            if key in seen:
                continue
            seen.add(key)
            standards.append(
                StandardInfo(
                    code=code.normalized,
                    base_code=code.base_code,
                    normalized_code=code.normalized,
                    name=name or None,
                    year=code.year,
                    edition=edition_info.edition,
                    revision_year=edition_info.revision_year,
                    amendment=edition_info.amendment,
                )
            )

        # Preserve quoted, name-only references within this logical item.
        for match in quoted_names:
            if match.start() in associated_quotes:
                continue
            name = clean_standard_name(match.group("name"))
            if not name:
                continue
            edition_info = _parse_inline_edition(segment[match.end() :])
            key = ("", name, edition_info.edition)
            if key in seen:
                continue
            seen.add(key)
            standards.append(
                StandardInfo(
                    code="",
                    name=name,
                    year=None,
                    edition=edition_info.edition,
                    revision_year=edition_info.revision_year,
                    amendment=edition_info.amendment,
                )
            )

    # If a deployment explicitly opts in, use remote extraction only as an
    # enhancement after local extraction. The default remains privacy-safe.
    if not standards and os.getenv("ENABLE_REMOTE_EXTRACTION", "false").lower() == "true":
        standards.extend(extract_standards_deepseek(raw))
    return standards


def clean_name(name: str) -> str:
    return clean_standard_name(name)


def clean_code(code: str) -> str:
    """Backward-compatible alias for context-aware code normalization."""

    return normalize_standard_code(code)


def extract_year(code: str) -> Optional[str]:
    parsed = next(iter(extract_standard_codes(code)), None)
    return parsed.year if parsed else None


def _parse_remote_json_array(content: object) -> list[object]:
    """Recover a JSON array from a model response without trusting prose."""

    if not isinstance(content, str):
        return content if isinstance(content, list) else []

    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    decoder = json.JSONDecoder()
    candidates = [text]
    if text.startswith("[") is False:
        candidates.extend(text[index:] for index, char in enumerate(text) if char == "[")
    for candidate in candidates:
        try:
            value, _ = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            return value
    return []


_REMOTE_EMPTY_NAMES = frozenset(
    {"", "na", "n/a", "none", "null", "未知", "无法判断", "不确定", "未识别", "未找到", "暂无"}
)


def _normalize_remote_code(value: object) -> tuple[str, str | None]:
    """Keep only codes that have a structurally usable standard number."""

    if not isinstance(value, str):
        return "", None
    raw = value.strip()
    if not raw or re.search(r"[A-Z]\s+[A-Z]", raw):
        return "", None
    parsed = parse_standard_code(raw)
    if not parsed or not re.search(r"\d", parsed.serial):
        return "", None
    if parsed.prefix.isalpha() and len(parsed.prefix) < 2:
        return "", None
    return parsed.normalized, parsed.year


def _clean_remote_name(value: object) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = clean_name(value)
    if cleaned.casefold() in _REMOTE_EMPTY_NAMES:
        return ""
    return cleaned


def extract_standards_deepseek(text: str) -> List[StandardInfo]:
    """Optional, explicitly enabled remote extraction.

    This function is inert unless both the flag and a runtime secret are
    present. It never contains a fallback token.
    """

    if os.getenv("ENABLE_REMOTE_EXTRACTION", "false").lower() != "true":
        return []
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        logger.warning("Remote extraction enabled but DEEPSEEK_API_KEY is not configured")
        return []

    import requests

    payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是建筑工程规范引用识别器。仅根据输入文本提取明确出现的规范编号或规范名称，"
                    "不确定时不要臆造。只输出 JSON 数组，数组元素只能包含 \"code\" 和 \"name\" 两个字段，"
                    "格式如 [{\"code\":\"GB 50016-2014\",\"name\":\"建筑设计防火规范\"}]。"
                    "无法判断编号或名称时使用空字符串；无法确认任何规范时输出 []。"
                    "禁止输出 Markdown、解释文字或其它内容。"
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
    }
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=(3, 15),
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        items = _parse_remote_json_array(content)
        standards: list[StandardInfo] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            code, parsed_year = _normalize_remote_code(item.get("code"))
            name = _clean_remote_name(item.get("name"))
            if not code and not name:
                continue
            year = (item.get("year") or parsed_year) if code else None
            standards.append(
                StandardInfo(
                    code=code,
                    normalized_code=code,
                    base_code=code,
                    name=name or None,
                    year=year,
                )
            )
        return standards
    except Exception as exc:  # Remote extraction is optional and non-fatal.
        logger.warning("Remote extraction failed: %s", exc.__class__.__name__)
        return []
