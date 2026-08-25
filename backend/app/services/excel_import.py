"""One-time legacy Excel bootstrap; never used as production search fallback."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Iterator

import openpyxl
from sqlalchemy.orm import Session

from app.models.enums import StandardStatus, VerificationLevel
from app.models.models import StandardSourceModel
from app.repositories.standard_repo import StandardRepo
from app.services.standard_normalizer import split_standard_reference


def resolve_legacy_excel_path(path: str | Path | None = None) -> Path:
    if path:
        return Path(path).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "standards_data.xlsx"


def _date_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value).strip()
    text = re.sub(r"^(更新时间|实施时间|发布日期|发布日期：|实施日期)\s*[：:]?\s*", "", text)
    return text or None


def iter_legacy_records(path: str | Path | None = None) -> Iterator[dict[str, object]]:
    workbook_path = resolve_legacy_excel_path(path)
    if not workbook_path.exists():
        raise FileNotFoundError(workbook_path)
    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        for worksheet in workbook.worksheets:
            rows = worksheet.iter_rows(values_only=True)
            headers = next(rows, ())
            header_map = {str(value).strip(): index for index, value in enumerate(headers) if value is not None}
            name_index = header_map.get("名称", header_map.get("规范名称及编号"))
            url_index = header_map.get("网址")
            updated_index = header_map.get("更新时间")
            implement_index = header_map.get("实施时间")
            if name_index is None:
                continue
            for row in rows:
                if not row or name_index >= len(row) or not isinstance(row[name_index], str):
                    continue
                content = row[name_index].strip()
                name, code, edition = split_standard_reference(content)
                if code is None:
                    continue
                yield {
                    "code": code.normalized,
                    "name": name,
                    "edition": edition.edition,
                    "revision_year": edition.revision_year,
                    "amendment": edition.amendment,
                    "source_url": row[url_index] if url_index is not None and url_index < len(row) else None,
                    "source_updated_at": _date_text(row[updated_index]) if updated_index is not None and updated_index < len(row) else None,
                    "implement_date": _date_text(row[implement_index]) if implement_index is not None and implement_index < len(row) else None,
                    "sheet": worksheet.title,
                }
    finally:
        workbook.close()


def import_legacy_excel(db: Session, path: str | Path | None = None) -> dict[str, int]:
    counts = {"found": 0, "inserted": 0, "updated": 0, "unchanged": 0, "failed": 0}
    for item in iter_legacy_records(path):
        counts["found"] += 1
        try:
            standard, created = StandardRepo.upsert(
                db,
                code=str(item["code"]),
                name=str(item.get("name") or ""),
                edition=item.get("edition"),
                revision_year=item.get("revision_year"),
                amendment=item.get("amendment"),
                status=StandardStatus.UNKNOWN,
                implement_date=item.get("implement_date"),
                canonical_source="soujianzhu",
                canonical_url=item.get("source_url"),
                soujianzhu_url=item.get("source_url"),
                verification_level=VerificationLevel.UNVERIFIED,
                source_updated_at=item.get("source_updated_at"),
            )
            source_code = standard.normalized_code
            source_row = (
                db.query(StandardSourceModel)
                .filter(StandardSourceModel.standard_id == standard.id)
                .filter(StandardSourceModel.source_name == "soujianzhu")
                .filter(StandardSourceModel.source_code == source_code)
                .first()
            )
            if source_row is None:
                source_row = StandardSourceModel(
                    standard_id=standard.id,
                    source_name="soujianzhu",
                    source_code=source_code,
                    parse_status="ok",
                )
                db.add(source_row)
            source_row.source_url = item.get("source_url")
            source_row.source_name_text = item.get("name")
            source_row.source_status = StandardStatus.UNKNOWN.value
            source_row.implement_date = item.get("implement_date")
            source_row.source_updated_at = item.get("source_updated_at")
            source_row.fetched_at = None
            source_row.parse_status = "ok"
            counts["inserted" if created else "updated"] += 1
        except Exception:
            counts["failed"] += 1
    db.commit()
    return counts
