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
    parse_edition,
)

logger = logging.getLogger(__name__)


def extract_standards_from_text(text: str) -> List[StandardInfo]:
    """Extract references without sending the design document to a remote LLM.

    Remote extraction is an explicit opt-in for administrators and is never a
    required part of database synchronization.  The local parser handles
    quoted names, code-only references, editions, and common OCR glyphs.
    """

    if not text or not text.strip():
        return []

    standards: list[StandardInfo] = []
    seen: set[tuple[str, str, str | None]] = set()
    raw = str(text)
    quoted_names = list(re.finditer(r"《(?P<name>[^》]{1,500})》", raw))
    codes = extract_standard_codes(raw)

    for code in codes:
        position = raw.find(code.raw)
        name = ""
        if position >= 0:
            candidates = [item for item in quoted_names if item.end() <= position]
            if candidates and position - candidates[-1].end() <= 180:
                between = raw[candidates[-1].end() : position]
                if not extract_standard_codes(between):
                    name = clean_standard_name(candidates[-1].group("name"))
        # Edition suffixes are defined relative to the code and must not leak
        # from a preceding reference in the same paragraph.
        nearby = raw[position + len(code.raw) : position + len(code.raw) + 100]
        next_codes = extract_standard_codes(nearby)
        if next_codes:
            nearby = nearby[: nearby.find(next_codes[0].raw)]
        edition_info = parse_edition(nearby)
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

    # Preserve quoted, name-only references for the existing workflow.
    for match in quoted_names:
        name = clean_standard_name(match.group("name"))
        if not name:
            continue
        has_nearby_code = any(
            0 <= raw.find(code.raw) - match.end() <= 180 for code in codes
        )
        if has_nearby_code:
            continue
        key = ("", name, None)
        if key not in seen:
            seen.add(key)
            standards.append(StandardInfo(code="", name=name, year=None))

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
                "content": "Extract Chinese engineering standard code and name pairs as JSON.",
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
        return [
            StandardInfo(
                code=clean_code(item.get("code", "")),
                normalized_code=clean_code(item.get("code", "")),
                base_code=clean_code(item.get("code", "")),
                name=clean_name(item.get("name", "")) or None,
                year=item.get("year") or extract_year(item.get("code", "")),
            )
            for item in items
            if isinstance(item, dict)
        ]
    except Exception as exc:  # Remote extraction is optional and non-fatal.
        logger.warning("Remote extraction failed: %s", exc.__class__.__name__)
        return []
