"""Audit a user-supplied standards catalogue against the reviewed V2 seed.

The catalogue is a candidate list, not an authority for current/abolished
status.  This module keeps every physical Excel row in the result, records the
original row number, and only copies status/verification from an exact V2
match.  Excel-only candidates are deliberately reported as ``unknown`` and
``unverified`` so they cannot silently become current standards.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, ClassVar, Iterable

import openpyxl

from app.services.standard_normalizer import (
    ParsedEdition,
    clean_standard_name,
    normalized_name,
    parse_standard_code,
    split_standard_reference,
)


CATALOG_SOURCE_NAME = "excel_catalog_20251011"
_SUSPECT_PREFIXES = {"G", "SG", "T"}
_VERIFICATION_RANK = {
    "official": 4,
    "cross_verified": 3,
    "single_source": 2,
    "unverified": 1,
    "conflict": 0,
}


@dataclass(frozen=True)
class ExcelCatalogRow:
    """One auditable physical row from the supplied workbook."""

    excel_sheet: str
    excel_row: int
    raw_value: str
    name: str
    normalized_name: str
    normalized_code: str | None
    edition: str | None
    revision_year: str | None
    amendment: str | None
    classification: str
    verification_status: str
    verification_level: str
    matched_keys: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["matched_keys"] = list(self.matched_keys)
        value["notes"] = list(self.notes)
        return value


@dataclass(frozen=True)
class CatalogAuditReport:
    source_path: str
    seed_path: str
    total_rows: int
    rows: tuple[ExcelCatalogRow, ...]
    summary: dict[str, int]

    CLASSIFICATIONS: ClassVar[tuple[str, ...]] = (
        "existing",
        "missing",
        "version_conflict",
        "name_conflict",
        "unparseable",
    )

    @property
    def missing_rows(self) -> tuple[ExcelCatalogRow, ...]:
        return tuple(row for row in self.rows if row.classification == "missing")

    @property
    def candidate_rows(self) -> tuple[ExcelCatalogRow, ...]:
        """Rows eligible for an unknown seed candidate, after conflicts out."""

        return self.missing_rows

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "seed_path": self.seed_path,
            "total_rows": self.total_rows,
            "summary": dict(self.summary),
            "rows": [row.to_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class NormativeDocumentAuditRow:
    """Classification for one Excel row without a year-bearing standard code."""

    excel_sheet: str
    excel_row: int
    raw_value: str
    title: str
    normalized_name: str
    classification: str
    document_kind: str | None
    status: str
    verification_level: str
    existing_titles: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["existing_titles"] = list(self.existing_titles)
        value["notes"] = list(self.notes)
        return value


@dataclass(frozen=True)
class NormativeDocumentAuditReport:
    source_path: str
    seed_path: str
    total_rows: int
    rows: tuple[NormativeDocumentAuditRow, ...]
    summary: dict[str, int]
    staged_documents: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "seed_path": self.seed_path,
            "total_rows": self.total_rows,
            "summary": dict(self.summary),
            "staged_documents": [dict(item) for item in self.staged_documents],
            "rows": [row.to_dict() for row in self.rows],
        }


def _edition_key(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", "", str(value)).replace("（", "(").replace("）", ")")


def _load_seed(seed_path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 2:
        raise ValueError("unsupported V2 seed schema")
    standards = payload.get("standards")
    if not isinstance(standards, list):
        raise ValueError("V2 seed standards must be a list")
    return standards


def _seed_indexes(seed_rows: Iterable[dict[str, Any]]) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
    dict[tuple[str, str], list[dict[str, Any]]],
]:
    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in seed_rows:
        code = str(row.get("base_code") or row.get("normalized_code") or "").strip()
        if not code:
            continue
        by_code[code].append(row)
        parsed = parse_standard_code(code)
        if parsed is not None:
            by_family[(parsed.prefix, parsed.serial)].append(row)
        name = normalized_name(str(row.get("name") or ""))
        if name:
            by_name[name].append(row)
    return dict(by_code), dict(by_name), dict(by_family)


def _best_verification(rows: Iterable[dict[str, Any]]) -> str:
    values = [str(row.get("verification_level") or "unverified") for row in rows]
    return max(values or ["unverified"], key=lambda value: _VERIFICATION_RANK.get(value, -1))


def _normative_document_kind(name: str) -> str:
    """Route non-numbered catalogue entries without implying current status."""

    if any(marker in name for marker in ("图集", "构造详图")):
        return "standard"
    if any(marker in name for marker in ("通知", "意见")):
        return "notice"
    if any(marker in name for marker in ("办法", "实施细则", "管理办法")):
        return "method"
    if any(marker in name for marker in ("规定", "条例", "法律", "法")):
        return "regulation"
    if any(marker in name for marker in ("导则", "指南", "指引", "指导书", "手册", "案例集", "规划")):
        return "guideline"
    return "standard"


def _is_meaningful_document_title(title: str) -> bool:
    compact = re.sub(r"\s+", "", title or "")
    if len(compact) < 2:
        return False
    return not all(char in "-—_.。·/\\" for char in compact)


def classify_unparseable_documents(
    catalog_path: str | Path,
    *,
    seed_path: str | Path = Path("data/standards_v2_seed.json"),
) -> NormativeDocumentAuditReport:
    """Classify all non-numbered Excel rows without promoting them to standards."""

    catalog_report = audit_catalog(catalog_path, seed_path=seed_path)
    # Normative documents are kept in the top-level payload, so load that
    # part separately for this audit after validating the seed schema.
    payload = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    existing_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in payload.get("normative_documents", []):
        key = normalized_name(document.get("title") or document.get("normalized_name") or "")
        if key:
            existing_by_name[key].append(document)

    rows: list[NormativeDocumentAuditRow] = []
    staged_by_name: dict[str, dict[str, Any]] = {}
    for source_row in catalog_report.rows:
        if source_row.classification != "unparseable":
            continue
        title = clean_standard_name(source_row.name)
        name_key = normalized_name(title)
        notes: list[str] = []
        if not _is_meaningful_document_title(title):
            rows.append(
                NormativeDocumentAuditRow(
                    excel_sheet=source_row.excel_sheet,
                    excel_row=source_row.excel_row,
                    raw_value=source_row.raw_value,
                    title=title,
                    normalized_name=name_key,
                    classification="manual_review",
                    document_kind=None,
                    status="unknown",
                    verification_level="unverified",
                    notes=("空白或无意义文本，未入库",),
                )
            )
            continue

        existing = existing_by_name.get(name_key, [])
        if existing:
            rows.append(
                NormativeDocumentAuditRow(
                    excel_sheet=source_row.excel_sheet,
                    excel_row=source_row.excel_row,
                    raw_value=source_row.raw_value,
                    title=title,
                    normalized_name=name_key,
                    classification="existing_normative_document",
                    document_kind=str(existing[0].get("document_kind") or "unknown"),
                    status="unknown",
                    verification_level="unverified",
                    existing_titles=tuple(sorted({str(item.get("title") or "") for item in existing})),
                    notes=("名称已存在于 V2 normative_documents，未重复插入",),
                )
            )
            continue

        if "征求意见稿" in title:
            notes.append("征求意见稿，入库但保持 unknown")
        if any(marker in title for marker in ("图集", "G101", "G519", "SG115")):
            notes.append("图集或设计详图类资料，作为 normative_document 保存")
        document_kind = _normative_document_kind(title)
        rows.append(
            NormativeDocumentAuditRow(
                excel_sheet=source_row.excel_sheet,
                excel_row=source_row.excel_row,
                raw_value=source_row.raw_value,
                title=title,
                normalized_name=name_key,
                classification="staged_normative_document",
                document_kind=document_kind,
                status="unknown",
                verification_level="unverified",
                notes=tuple(notes),
            )
        )
        staged_by_name.setdefault(
            name_key,
            {
                "title": title,
                "normalized_name": name_key,
                "document_number": None,
                "document_kind": document_kind,
                "status": "unknown",
                "publish_date": None,
                "implement_date": None,
                "source_name": CATALOG_SOURCE_NAME,
                "source_url": None,
                "verification_level": "unverified",
            },
        )

    counts = Counter(row.classification for row in rows)
    summary = {
        "existing_normative_document": counts.get("existing_normative_document", 0),
        "staged_normative_document": counts.get("staged_normative_document", 0),
        "manual_review": counts.get("manual_review", 0),
    }
    return NormativeDocumentAuditReport(
        source_path=catalog_report.source_path,
        seed_path=catalog_report.seed_path,
        total_rows=len(rows),
        rows=tuple(rows),
        summary=summary,
        staged_documents=tuple(staged_by_name.values()),
    )


def _parse_catalog_value(raw_value: str) -> tuple[str, Any, ParsedEdition, tuple[str, ...]]:
    """Parse one catalogue value and flag known false-positive code shapes."""

    name, parsed, edition = split_standard_reference(raw_value)
    notes: list[str] = []
    if parsed is not None and parsed.year is None:
        notes.append("规范编号缺少四位年份，需人工核验")
        parsed = None
    if parsed is not None and parsed.prefix in _SUSPECT_PREFIXES:
        notes.append("generic drawing-code prefix requires manual review")
        parsed = None
    if parsed is None:
        notes.append("无法解析含年份的规范编号")
    return clean_standard_name(name), parsed, edition, tuple(notes)


def _classify(
    *,
    code: Any,
    name: str,
    edition: ParsedEdition,
    by_code: dict[str, list[dict[str, Any]]],
    by_name: dict[str, list[dict[str, Any]]],
    by_family: dict[tuple[str, str], list[dict[str, Any]]],
) -> tuple[str, str, str, tuple[str, ...], tuple[str, ...]]:
    if code is None:
        return "unparseable", "unknown", "unverified", (), ()

    code_value = code.normalized
    candidates = by_code.get(code_value, [])
    wanted_edition = _edition_key(edition.edition)
    exact = [row for row in candidates if _edition_key(row.get("edition")) == wanted_edition]
    wanted_name = normalized_name(name)
    exact_name = [row for row in exact if normalized_name(row.get("name")) == wanted_name]
    same_name_elsewhere = by_name.get(wanted_name, [])
    family = by_family.get((code.prefix, code.serial), [])
    notes: list[str] = []

    if exact_name:
        return (
            "existing",
            str(exact_name[0].get("status") or "unknown"),
            _best_verification(exact_name),
            tuple(str(row.get("key") or "") for row in exact_name),
            tuple(notes),
        )

    if exact and not exact_name:
        notes.append("规范名称与同编号同版本 V2 记录不一致")
        notes.append(
            "V2名称=" + "; ".join(sorted({str(row.get("name") or "") for row in exact}))
        )
        return (
            "name_conflict",
            "unknown",
            "unverified",
            tuple(str(row.get("key") or "") for row in exact),
            tuple(notes),
        )

    if candidates:
        notes.append("同一规范编号存在其他版本，需核查版次")
        notes.append(
            "V2版次=" + "; ".join(sorted({str(row.get("edition") or "原始") for row in candidates}))
        )
        return (
            "version_conflict",
            "unknown",
            "unverified",
            tuple(str(row.get("key") or "") for row in candidates),
            tuple(notes),
        )

    if family:
        family_name = [row for row in family if normalized_name(row.get("name")) == wanted_name]
        if family_name:
            notes.append("同一规范编号存在其他年份版本，需核查版次")
            notes.append(
                "V2版次=" + "; ".join(sorted({str(row.get("edition") or row.get("base_code") or "原始") for row in family}))
            )
            return (
                "version_conflict",
                "unknown",
                "unverified",
                tuple(str(row.get("key") or "") for row in family),
                tuple(notes),
            )
    if same_name_elsewhere:
        notes.append("规范名称已存在但编号不同，疑似编号录入错误")
        notes.append(
            "V2编号=" + "; ".join(sorted({str(row.get("base_code") or "") for row in same_name_elsewhere}))
        )
        return "name_conflict", "unknown", "unverified", (), tuple(notes)

    return "missing", "unknown", "unverified", (), ()


def audit_catalog(
    catalog_path: str | Path,
    *,
    seed_path: str | Path = Path("data/standards_v2_seed.json"),
) -> CatalogAuditReport:
    """Audit every non-header physical row in ``catalog_path``.

    Rows with no parseable year-bearing code remain in the output as
    ``unparseable``.  A missing row is a candidate only; its status remains
    ``unknown`` until an independent source verifies it.
    """

    catalog = Path(catalog_path).expanduser().resolve()
    seed = Path(seed_path).expanduser().resolve()
    if not catalog.exists():
        raise FileNotFoundError(catalog)
    if not seed.exists():
        raise FileNotFoundError(seed)
    by_code, by_name, by_family = _seed_indexes(_load_seed(seed))
    result: list[ExcelCatalogRow] = []
    workbook = openpyxl.load_workbook(catalog, read_only=True, data_only=True)
    try:
        for worksheet in workbook.worksheets:
            for excel_row, cells in enumerate(worksheet.iter_rows(values_only=True), start=1):
                if excel_row == 1:
                    continue
                raw = cells[0] if cells else None
                raw_value = "" if raw is None else str(raw).strip()
                name, parsed, edition, parse_notes = _parse_catalog_value(raw_value)
                classification, status, verification, matched_keys, notes = _classify(
                    code=parsed,
                    name=name,
                    edition=edition,
                    by_code=by_code,
                    by_name=by_name,
                    by_family=by_family,
                )
                result.append(
                    ExcelCatalogRow(
                        excel_sheet=worksheet.title,
                        excel_row=excel_row,
                        raw_value=raw_value,
                        name=name,
                        normalized_name=normalized_name(name),
                        normalized_code=parsed.normalized if parsed is not None else None,
                        edition=edition.edition,
                        revision_year=edition.revision_year,
                        amendment=edition.amendment,
                        classification=classification,
                        verification_status=status,
                        verification_level=verification,
                        matched_keys=matched_keys,
                        notes=tuple(parse_notes) + tuple(notes),
                    )
                )
    finally:
        workbook.close()
    counts = Counter(row.classification for row in result)
    summary = {key: counts.get(key, 0) for key in CatalogAuditReport.CLASSIFICATIONS}
    summary["total_rows"] = len(result)
    return CatalogAuditReport(
        source_path=str(catalog),
        seed_path=str(seed),
        total_rows=len(result),
        rows=tuple(result),
        summary=summary,
    )


def write_audit_report(
    report: CatalogAuditReport,
    output_path: str | Path,
    *,
    metadata: dict[str, Any] | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    if metadata:
        payload.update(metadata)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output
