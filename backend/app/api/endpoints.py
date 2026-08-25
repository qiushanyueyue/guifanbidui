"""HTTP API; ordinary queries are database-only and never crawl third parties."""

from __future__ import annotations

import hmac
import io
import logging
import os
import urllib.parse

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.base import database_is_configured, get_db
from app.models.enums import StandardStatus, VerificationLevel, normalize_status, status_label
from app.models.models import (
    StandardHistoryModel,
    StandardModel,
    StandardSourceModel,
    StandardV2Model,
    StandardV2RelationModel,
    StandardV2SourceModel,
    SyncRunModel,
)
from app.models.schemas import (
    DetailRequest,
    ExtractionRequest,
    ExtractionResponse,
    ExportRequest,
    HealthResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SourceInfo,
    StandardDetail,
    StatsResponse,
    SyncStatusResponse,
    VerifyRequest,
    VerifyResponse,
)
from app.repositories.standard_repo import StandardRepo
from app.repositories.standard_v2_repo import StandardV2Repo
from app.services.extractor import extract_standards_from_text
from app.services.standard_matcher import assess_standard_match

logger = logging.getLogger(__name__)
router = APIRouter()


def _source_info(source: StandardSourceModel) -> SourceInfo:
    return SourceInfo(
        name=source.source_name,
        url=source.source_url,
        code=source.source_code,
        name_text=source.source_name_text,
        status=normalize_status(source.source_status),
        raw_status=source.source_status,
        fetched_at=source.fetched_at,
        source_updated_at=source.source_updated_at,
        parse_status=source.parse_status,
    )


def _source_info_v2(source: StandardV2SourceModel) -> SourceInfo:
    return SourceInfo(
        name=source.source_name,
        url=source.source_url,
        status=normalize_status(source.observed_status),
        raw_status=source.observed_status,
        fetched_at=source.fetched_at,
    )


def _use_v2(db: Session) -> bool:
    selected = os.getenv("STANDARDS_DATASET", "auto").strip().lower()
    if selected == "legacy":
        return False
    if selected == "v2":
        return True
    return StandardV2Repo.has_data(db)


def _result(db: Session, standard: StandardModel, *, source: str = "db") -> SearchResult:
    sources = StandardRepo.sources_for(db, standard.id)
    resolved_status = normalize_status(standard.status)
    return SearchResult(
        id=standard.id,
        code=standard.code,
        normalized_code=standard.normalized_code,
        name=standard.name or "",
        status=resolved_status,
        status_label=status_label(resolved_status),
        url=standard.canonical_url or standard.url,
        source=source,
        soujianzhu_url=standard.soujianzhu_url,
        edition=standard.edition,
        revision_year=standard.revision_year,
        amendment=standard.amendment,
        implement_date=standard.implement_date or standard.implementation_date,
        publish_date=standard.publish_date,
        abolish_date=standard.abolish_date,
        replaces=standard.replaces,
        replaced_by=standard.replaced_by,
        article_status=standard.article_status,
        mandatory_clause_status=standard.mandatory_clause_status,
        issuing_authority=standard.issuing_authority or standard.publishing_department,
        canonical_source=standard.canonical_source,
        verification_level=VerificationLevel(standard.verification_level or VerificationLevel.UNVERIFIED.value),
        source_conflict=bool(standard.source_conflict),
        last_verified_at=standard.last_verified_at,
        sources=[_source_info(item) for item in sources],
    )


def _result_v2(db: Session, standard: StandardV2Model, *, source: str = "db_v2") -> SearchResult:
    sources = StandardV2Repo.sources_for(db, standard.id)
    source_map = {item.source_name: item.source_url for item in sources if item.source_url}
    replaced_by_rows = (
        db.query(StandardV2RelationModel)
        .filter(StandardV2RelationModel.source_standard_id == standard.id)
        .filter(StandardV2RelationModel.relation_type == "replaced_by")
        .all()
    )
    targets = [db.get(StandardV2Model, item.target_standard_id) for item in replaced_by_rows]
    replaced_by = "; ".join(item.base_code for item in targets if item is not None) or None
    resolved_status = normalize_status(standard.status)
    return SearchResult(
        id=standard.id,
        code=standard.code,
        normalized_code=standard.normalized_code,
        name=standard.name,
        status=resolved_status,
        status_label=status_label(resolved_status),
        url=source_map.get("csres") or source_map.get("soujianzhu"),
        source=source,
        soujianzhu_url=source_map.get("soujianzhu"),
        edition=standard.edition,
        revision_year=standard.revision_year,
        amendment=standard.amendment,
        implement_date=standard.implement_date,
        publish_date=standard.publish_date,
        abolish_date=standard.abolish_date,
        replaced_by=replaced_by,
        mandatory_clause_status=standard.mandatory_clause_status,
        issuing_authority=standard.issuing_authority,
        canonical_source="soujianzhu+csres",
        verification_level=VerificationLevel(standard.verification_level),
        source_conflict=standard.source_conflict,
        last_verified_at=standard.last_verified_at,
        sources=[_source_info_v2(item) for item in sources],
        data_quality_status=standard.data_quality_status,
        document_kind=standard.document_kind,
    )


def _repo(db: Session):
    return StandardV2Repo if _use_v2(db) else StandardRepo


def _to_result(db: Session, standard) -> SearchResult:
    return _result_v2(db, standard) if isinstance(standard, StandardV2Model) else _result(db, standard)


def _detail(db: Session, standard: StandardModel) -> StandardDetail:
    result = _result(db, standard)
    payload = result.model_dump()
    payload.update(
        department=standard.issuing_authority or standard.publishing_department or "-",
        release_date=standard.publish_date or "-",
        implement_date=standard.implement_date or standard.implementation_date or "-",
        drafting_unit="-",
        technical_committee="-",
        ccs="-",
        englishName="-",
        ics="-",
        publisher="-",
        pages="-",
        obsolete_date=standard.abolish_date or "-",
    )
    return StandardDetail(**payload)


def _latest_sync(db: Session) -> SyncRunModel | None:
    return (
        db.query(SyncRunModel)
        .filter(SyncRunModel.finished_at.isnot(None))
        .order_by(SyncRunModel.finished_at.desc())
        .first()
    )


def _health_payload(db: Session) -> HealthResponse:
    database = "ok"
    try:
        db.execute(text("SELECT 1"))
        if not database_is_configured():
            database = "warning"
    except Exception:
        database = "error"
    latest = _latest_sync(db)
    sources: dict[str, str] = {name: "never" for name in ("samr", "mohurd", "openstd", "soujianzhu", "csres")}
    for row in db.query(SyncRunModel).order_by(SyncRunModel.finished_at.desc()).limit(20).all():
        if row.source not in sources or sources[row.source] != "never":
            continue
        sources[row.source] = row.status
    # A third-party outage is reported per-source and does not take the API
    # down when the database itself remains healthy.
    overall = "ok" if database == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        database=database,
        last_sync=latest.finished_at if latest else None,
        sources=sources,
    )


@router.post("/extract", response_model=ExtractionResponse)
def extract_standards(request: ExtractionRequest):
    return ExtractionResponse(standards=extract_standards_from_text(request.text))


def _search(db: Session, keyword: str, limit: int = 20) -> SearchResponse:
    keyword = keyword.strip()
    if not keyword:
        return SearchResponse(results=[])
    standards = _repo(db).search(db, keyword, limit=limit)
    return SearchResponse(results=[_to_result(db, standard) for standard in standards])


@router.post("/search", response_model=SearchResponse)
def search_standard_endpoint(request: SearchRequest, db: Session = Depends(get_db)):
    return _search(db, request.keyword)


@router.get("/standards/search", response_model=SearchResponse)
def search_standards(q: str = Query(min_length=1, max_length=200), limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    return _search(db, q, limit=limit)


@router.get("/standards/code/{code:path}", response_model=StandardDetail)
def get_standard_by_code(code: str, db: Session = Depends(get_db)):
    standard = _repo(db).get_by_code(db, code)
    if standard is None:
        raise HTTPException(status_code=404, detail="standard not found")
    return StandardDetail(**_to_result(db, standard).model_dump()) if _use_v2(db) else _detail(db, standard)


@router.get("/standards/{standard_id}", response_model=StandardDetail)
def get_standard_by_id(standard_id: int, db: Session = Depends(get_db)):
    standard = _repo(db).get_by_id(db, standard_id)
    if standard is None:
        raise HTTPException(status_code=404, detail="standard not found")
    return StandardDetail(**_to_result(db, standard).model_dump()) if _use_v2(db) else _detail(db, standard)


@router.get("/standards/{standard_id}/sources", response_model=list[SourceInfo])
def get_standard_sources(standard_id: int, db: Session = Depends(get_db)):
    repo = _repo(db)
    if repo.get_by_id(db, standard_id) is None:
        raise HTTPException(status_code=404, detail="standard not found")
    sources = repo.sources_for(db, standard_id)
    return [(_source_info_v2(source) if _use_v2(db) else _source_info(source)) for source in sources]


@router.get("/standards/{standard_id}/history")
def get_standard_history(standard_id: int, db: Session = Depends(get_db)):
    if _repo(db).get_by_id(db, standard_id) is None:
        raise HTTPException(status_code=404, detail="standard not found")
    if _use_v2(db):
        return []
    return [
        {
            "id": item.id,
            "changed_at": item.changed_at,
            "field": item.field_name,
            "old": item.old_value,
            "new": item.new_value,
            "source": item.source,
        }
        for item in db.query(StandardHistoryModel)
        .filter(StandardHistoryModel.standard_id == standard_id)
        .order_by(StandardHistoryModel.changed_at.desc())
        .all()
    ]


@router.post("/detail", response_model=StandardDetail)
def get_standard_detail_endpoint(request: DetailRequest, db: Session = Depends(get_db)):
    repo = _repo(db)
    standard = repo.get_by_id(db, request.id) if request.id else None
    if standard is None and request.code:
        standard = repo.get_by_code(db, request.code)
    if standard is None and request.url:
        standard = repo.get_by_source_url(db, request.url)
    if standard is None:
        # Keep the legacy modal contract without claiming a missing result is
        # current or performing a live third-party request.
        return StandardDetail(code=request.code or "", name="", status=StandardStatus.UNKNOWN)
    return StandardDetail(**_to_result(db, standard).model_dump()) if _use_v2(db) else _detail(db, standard)


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    repo = _repo(db)
    counts = repo.count_by_status(db)
    model = StandardV2Model if _use_v2(db) else StandardModel
    last_verified = db.query(func.max(model.last_verified_at)).scalar()
    return StatsResponse(
        count=sum(counts.values()),
        last_updated=last_verified,
        current=counts[StandardStatus.CURRENT.value],
        upcoming=counts[StandardStatus.UPCOMING.value],
        abolished=counts[StandardStatus.ABOLISHED.value],
        replaced=counts[StandardStatus.REPLACED.value],
        partially_amended=counts[StandardStatus.PARTIALLY_AMENDED.value],
        unknown=counts[StandardStatus.UNKNOWN.value],
        conflict=counts[StandardStatus.CONFLICT.value],
    )


@router.get("/sync/status", response_model=SyncStatusResponse)
def get_sync_status(db: Session = Depends(get_db)):
    latest = _latest_sync(db)
    if latest is None:
        return SyncStatusResponse(latest=None)
    return SyncStatusResponse(
        latest={
            "id": latest.id,
            "source": latest.source,
            "started_at": latest.started_at,
            "finished_at": latest.finished_at,
            "status": latest.status,
            "found": latest.found,
            "inserted": latest.inserted,
            "updated": latest.updated,
            "unchanged": latest.unchanged,
            "failed": latest.failed,
            "error_message": latest.error_message,
        }
    )


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    return _health_payload(db)


@router.post("/v1/verify", response_model=VerifyResponse)
def verify_standard(request: VerifyRequest, db: Session = Depends(get_db)):
    repo = _repo(db)
    standard = repo.get_by_code(db, request.code)
    if standard is None and request.name:
        matches = repo.search(db, request.name, limit=1)
        standard = matches[0] if matches else None
    if standard is None:
        return VerifyResponse(
            input_code=request.code,
            status=StandardStatus.UNKNOWN,
            match_type="not_found",
            message="本地规范库未找到匹配记录",
        )
    result = _to_result(db, standard)
    decision = assess_standard_match(input_code=request.code, input_name=request.name, standard=standard)
    result.match_type = decision.match_type
    result.confidence = decision.confidence
    result.recommended_citation = decision.recommended_citation
    result.message = decision.message
    return VerifyResponse(
        input_code=request.code,
        canonical_code=result.normalized_code or result.code,
        name=result.name,
        status=result.status,
        current_edition=result.edition,
        replaced_by=result.replaced_by,
        publish_date=result.publish_date,
        implement_date=result.implement_date,
        verification_level=result.verification_level,
        sources=result.sources,
        last_verified_at=result.last_verified_at,
        match_type=decision.match_type,
        confidence=decision.confidence,
        recommended_citation=decision.recommended_citation,
        message=decision.message,
        result=result,
    )


@router.post("/export")
def export_standards(request: ExportRequest, db: Session = Depends(get_db)):
    """Export review results as an Excel workbook using database-only lookups."""

    import xlsxwriter

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    sheet = workbook.add_worksheet("规范查新结果")
    headers = [
        "原规范名称", "原规范编号", "匹配规范名称", "匹配规范编号", "当前修订版", "状态",
        "问题类型", "建议修改为", "实施日期", "替代标准", "搜建筑链接", "工标网链接", "最近核验时间",
    ]
    for column, header in enumerate(headers):
        sheet.write(0, column, header)
    repo = _repo(db)
    for row_number, item in enumerate(request.standards, start=1):
        standard = repo.get_by_code(db, item.code) if item.code else None
        if standard is None and item.name:
            matches = repo.search(db, item.name, limit=1)
            standard = matches[0] if matches else None
        if standard is None:
            values = [item.name or "", item.code, "", "", "", "待核验", "not_found", "", "", "", "", "", ""]
        else:
            result = _to_result(db, standard)
            decision = assess_standard_match(input_code=item.code, input_name=item.name, standard=standard)
            source_urls = {source.name: source.url for source in result.sources}
            values = [
                item.name or "", item.code, result.name, result.code, result.edition or result.revision_year or "",
                result.status_label or status_label(result.status), decision.match_type, decision.recommended_citation,
                result.implement_date or "", result.replaced_by or "", result.soujianzhu_url or "",
                source_urls.get("csres") or "", result.last_verified_at.isoformat() if result.last_verified_at else "",
            ]
        for column, value in enumerate(values):
            sheet.write(row_number, column, value)
    sheet.autofilter(0, 0, max(1, len(request.standards)), len(headers) - 1)
    sheet.freeze_panes(1, 0)
    sheet.set_column(0, 3, 24)
    sheet.set_column(7, 12, 30)
    workbook.close()
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=standards-review.xlsx"},
    )


@router.get("/redirect_csres")
def redirect_csres(keyword: str = Query(max_length=200)):
    try:
        encoded_keyword = urllib.parse.quote(keyword.encode("gbk"))
    except UnicodeEncodeError:
        encoded_keyword = urllib.parse.quote(keyword)
    return {"url": f"https://www.csres.com/s.jsp?keyword={encoded_keyword}"}


def _require_cron_secret(authorization: str | None) -> None:
    configured = os.getenv("CRON_SECRET", "").strip()
    if not configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="CRON_SECRET is not configured")
    expected = f"Bearer {configured}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@router.get("/cron/health", response_model=HealthResponse)
def cron_health(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_cron_secret(authorization)
    return _health_payload(db)


@router.get("/cron/status", response_model=SyncStatusResponse)
def cron_status(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Protected lightweight status probe; heavy crawling remains in Actions."""
    _require_cron_secret(authorization)
    latest = _latest_sync(db)
    if latest is None:
        return SyncStatusResponse(latest=None)
    return SyncStatusResponse(
        latest={
            "id": latest.id,
            "source": latest.source,
            "finished_at": latest.finished_at,
            "status": latest.status,
            "found": latest.found,
            "inserted": latest.inserted,
            "updated": latest.updated,
            "unchanged": latest.unchanged,
            "failed": latest.failed,
        }
    )
