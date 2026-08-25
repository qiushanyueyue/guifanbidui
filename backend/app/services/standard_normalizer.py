"""Normalization of Chinese engineering-standard references.

The normalizer intentionally applies OCR corrections only inside numeric
segments.  Replacing every ``O`` in a string would corrupt identifiers such as
``ISO`` and is not acceptable for source reconciliation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


_PREFIX = (
    r"(?:GB(?:\s*/?\s*T)?|JGJ(?:\s*/?\s*T)?|CJJ(?:\s*/?\s*T)?|"
    r"CJ(?:\s*/?\s*T)?|DBJ(?:\s*/?\s*T)?|DB(?:\s*/?\s*T)?|\u5efa\u6807|"
    r"T\s*/\s*[A-Z]{2,12}|[A-Z]{1,8}(?:\s*/\s*[A-Z]{1,8})?)"
)
_CODE_WITH_YEAR_RE = re.compile(
    rf"(?P<prefix>{_PREFIX})\s*(?P<serial>[A-Z0-9IOl()/.]+(?:\s*[-.]\s*[A-Z0-9IOl()/.]+)*)\s*-\s*(?P<year>[0-9IOl]{{2}}(?:[0-9IOl]{{2}})?)",
    re.IGNORECASE,
)
_CODE_WITHOUT_YEAR_RE = re.compile(
    rf"(?P<prefix>{_PREFIX})\s*(?P<serial>[A-Z0-9IOl()/.]+(?:\s*[-.]\s*[A-Z0-9IOl()/.]+)*)",
    re.IGNORECASE,
)
_EDITION_RE = re.compile(
    r"[（(]\s*(?P<year>\d{4})\s*年?\s*版\s*[)）]|(?P<year2>\d{4})\s*年?\s*版"
)


@dataclass(frozen=True)
class ParsedStandardCode:
    raw: str
    normalized: str
    prefix: str
    serial: str
    year: str | None = None

    @property
    def base_code(self) -> str:
        return self.normalized


@dataclass(frozen=True)
class ParsedEdition:
    edition: str | None
    revision_year: str | None
    amendment: str | None


def _numeric_ocr_fix(value: str) -> str:
    """Fix common OCR glyphs only in a segment known to be numeric."""

    return value.translate(str.maketrans({"l": "1", "I": "1", "O": "0", "o": "0"}))


def _normalize_code_punctuation(value: str) -> str:
    return value.translate(
        str.maketrans({"／": "/", "－": "-", "–": "-", "—": "-", "﹣": "-", "　": " "})
    )


def _format_prefix(value: str) -> str:
    prefix = re.sub(r"\s+", "", value).upper()
    compact_recommendations = {
        "GBT": "GB/T",
        "JGJT": "JGJ/T",
        "CJJT": "CJJ/T",
        "CJT": "CJ/T",
        "DBT": "DB/T",
        "DBJT": "DBJ/T",
    }
    prefix = compact_recommendations.get(prefix, prefix)
    return prefix


def _build_match(match: re.Match[str]) -> ParsedStandardCode:
    prefix = _format_prefix(match.group("prefix"))
    serial = _numeric_ocr_fix(re.sub(r"\s+", "", match.group("serial"))).upper().lstrip("/")
    year = match.groupdict().get("year")
    if year:
        year = _numeric_ocr_fix(year)
    normalized = f"{prefix}{serial}" if prefix == "T/" else f"{prefix} {serial}"
    if year:
        normalized += f"-{year}"
    return ParsedStandardCode(
        raw=match.group(0),
        normalized=normalized,
        prefix=prefix,
        serial=serial,
        year=year,
    )


def parse_standard_code(value: str | None) -> ParsedStandardCode | None:
    """Parse one code from a string, returning ``None`` for non-standard text."""

    if not value:
        return None
    text = _normalize_code_punctuation(str(value)).strip().replace("（", "(").replace("）", ")")
    match = _CODE_WITH_YEAR_RE.search(text)
    if match:
        return _build_match(match)
    if re.fullmatch(r"T/[A-Z]+", text, re.IGNORECASE):
        return None
    match = _CODE_WITHOUT_YEAR_RE.search(text)
    if match:
        return _build_match(match)
    return None


def extract_standard_codes(text: str | None) -> list[ParsedStandardCode]:
    """Extract ordered, de-duplicated standard codes from arbitrary text."""

    if not text:
        return []
    text = _normalize_code_punctuation(str(text))
    found: list[ParsedStandardCode] = []
    occupied: list[tuple[int, int]] = []
    for match in _CODE_WITH_YEAR_RE.finditer(text):
        parsed = _build_match(match)
        if parsed.normalized not in {item.normalized for item in found}:
            found.append(parsed)
        occupied.append(match.span())
    for match in _CODE_WITHOUT_YEAR_RE.finditer(text):
        if any(start <= match.start() < end for start, end in occupied):
            continue
        parsed = _build_match(match)
        if parsed.normalized not in {item.normalized for item in found}:
            found.append(parsed)
    return found


def normalize_standard_code(code: str | None) -> str:
    """Return a canonical display code without global OCR substitutions."""

    parsed = parse_standard_code(code)
    if parsed:
        return parsed.normalized
    if not code:
        return ""
    # Non-Chinese identifiers (for example ISO 9001) are preserved apart from
    # harmless whitespace/case normalization; no O->0 conversion is applied.
    return re.sub(r"\s+", " ", str(code).strip()).upper()


def parse_edition(text: str | None) -> ParsedEdition:
    if not text:
        return ParsedEdition(None, None, None)
    match = _EDITION_RE.search(str(text))
    revision_year = (match.group("year") or match.group("year2")) if match else None
    edition = f"{revision_year}年版" if revision_year else None
    lower = str(text)
    amendment: str | None = None
    for marker in ("局部修订", "部分修订", "修改单", "修订版"):
        if marker in lower:
            amendment = marker
            break
    return ParsedEdition(edition, revision_year, amendment)


def split_standard_reference(text: str | None) -> tuple[str, ParsedStandardCode | None, ParsedEdition]:
    """Extract a best-effort name, code, and edition from one source cell."""

    raw = str(text or "").strip()
    parsed_codes = extract_standard_codes(raw)
    parsed = parsed_codes[0] if parsed_codes else None
    edition = parse_edition(raw)
    name_match = re.search(r"《(?P<name>[^》]{1,500})》", raw)
    if name_match:
        name = name_match.group("name")
    elif parsed:
        name = raw[: raw.find(parsed.raw)].strip(" ,，;；:-—")
    else:
        name = raw
    name = clean_standard_name(name)
    return name, parsed, edition


def clean_standard_name(name: str | None) -> str:
    if not name:
        return ""
    value = str(name)
    value = value.replace("《", "").replace("》", "")
    value = re.sub(r"[(（]\s*\d{4}\s*年?版\s*[)）]", "", value)
    value = re.sub(r"[(（]\s*[含附]条文说明\s*[)）]", "", value)
    value = re.sub(r"[(（].*?附.*?说明.*?[)）]", "", value)
    value = re.sub(r"[\[【].*?[\]】]", "", value)
    value = re.sub(r"[(（]共.*?[册分卷][)）]", "", value)
    for code in extract_standard_codes(value):
        value = value.replace(code.raw, "")
    return re.sub(r"\s+", " ", value).strip(" ,，;；")


def normalized_name(name: str | None) -> str:
    return re.sub(r"\s+", "", clean_standard_name(name)).casefold()


def codes_equal(left: str | None, right: str | None) -> bool:
    return normalize_standard_code(left) == normalize_standard_code(right)


def iter_reference_parts(text: str | None) -> Iterable[tuple[str, ParsedStandardCode, ParsedEdition]]:
    """Yield nearby quoted names for each code in a text block."""

    raw = str(text or "")
    for code in extract_standard_codes(raw):
        position = raw.find(code.raw)
        before = raw[max(0, position - 180) : position]
        name_match = list(re.finditer(r"《(?P<name>[^》]{1,500})》", before))
        name = clean_standard_name(name_match[-1].group("name")) if name_match else ""
        edition = parse_edition(raw[max(0, position - 40) : position + len(code.raw) + 80])
        yield name, code, edition
