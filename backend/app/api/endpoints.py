"""HTTP API backed by fresh cache with bounded query-time metadata refresh."""

from __future__ import annotations

import hmac
import io
import logging
import os
import urllib.parse
from datetime import datetime, timedelta, timezone

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
    DataHealthResponse,
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
from app.services.business_conclusion import business_conclusion
from app.services.live_verification import (
    attempt_outcome,
    FAILURE_OUTCOMES,
    LookupTrace,
    cache_is_fresh,
    discover_live,
    live_refresh_enabled,
    lookup_deadline,
    lookup_key,
    persist_discovered_standard,
    persist_live_verification,
    recent_attempt,
    record_attempt,
    verify_live,
)
from app.services.standard_normalizer import normalized_name, parse_standard_code
from app.sources.soujianzhu import canonical_soujianzhu_full_text_url

logger = logging.getLogger(__name__)
router = APIRouter()


def _source_info(source: StandardSourceModel) -> SourceInfo:
    source_url = (
        canonical_soujianzhu_full_text_url(source.source_url)
        if source.source_name == "soujianzhu"
        else source.source_url
    )
    return SourceInfo(
        name=source.source_name,
        url=source_url,
        code=source.source_code,
        name_text=source.source_name_text,
        status=normalize_status(source.source_status),
        raw_status=source.source_status,
        fetched_at=source.fetched_at,
        source_updated_at=source.source_updated_at,
        parse_status=source.parse_status,
    )


def _source_info_v2(source: StandardV2SourceModel) -> SourceInfo:
    source_url = (
        canonical_soujianzhu_full_text_url(source.source_url)
        if source.source_name == "soujianzhu"
        else source.source_url
    )
    return SourceInfo(
        name=source.source_name,
        url=source_url,
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
    # Sessions are request-scoped, so probe the V2 table once per request.
    if "use_v2" not in db.info:
        db.info["use_v2"] = StandardV2Repo.has_data(db)
    return db.info["use_v2"]


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
        business_conclusion=business_conclusion(standard),
        url=standard.canonical_url or standard.url,
        source=source,
        soujianzhu_url=canonical_soujianzhu_full_text_url(standard.soujianzhu_url),
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
    source_names = sorted({item.source_name for item in sources if item.source_name})
    target_codes = (
        db.query(StandardV2Model.base_code)
        .join(StandardV2RelationModel, StandardV2RelationModel.target_standard_id == StandardV2Model.id)
        .filter(StandardV2RelationModel.source_standard_id == standard.id)
        .filter(StandardV2RelationModel.relation_type == "replaced_by")
        .order_by(StandardV2RelationModel.id)
        .all()
    )
    replaced_by = "; ".join(code for (code,) in target_codes) or None
    resolved_status = normalize_status(standard.status)
    result = SearchResult(
        id=standard.id,
        code=standard.code,
        normalized_code=standard.normalized_code,
        name=standard.name,
        status=resolved_status,
        status_label=status_label(resolved_status),
        business_conclusion=business_conclusion(standard),
        url=source_map.get("csres") or source_map.get("soujianzhu"),
        source=source,
        soujianzhu_url=canonical_soujianzhu_full_text_url(source_map.get("soujianzhu")),
        edition=standard.edition,
        revision_year=standard.revision_year,
        amendment=standard.amendment,
        implement_date=standard.implement_date,
        publish_date=standard.publish_date,
        abolish_date=standard.abolish_date,
        replaced_by=replaced_by,
        mandatory_clause_status=standard.mandatory_clause_status,
        issuing_authority=standard.issuing_authority,
        canonical_source="+".join(source_names) or None,
        verification_level=VerificationLevel(standard.verification_level),
        source_conflict=standard.source_conflict,
        last_verified_at=standard.last_verified_at,
        sources=[_source_info_v2(item) for item in sources],
        data_quality_status=standard.data_quality_status,
        document_kind=standard.document_kind,
    )
    if replaced_by:
        result.business_conclusion = business_conclusion(result)
    return result


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
    sources = {name: "never" for name in ("samr", "mohurd", "openstd", "soujianzhu", "csres")}
    try:
        db.execute(text("SELECT 1"))
        database = "ok" if database_is_configured() else "warning"
        latest = _latest_sync(db)
        for source in sources:
            row = (db.query(SyncRunModel).filter(SyncRunModel.source == source)
                   .order_by(SyncRunModel.started_at.desc(), SyncRunModel.id.desc()).first())
            if row is not None:
                sources[source] = row.status
        # A partial batch with usable results is a successful data refresh;
        # zero-candidate runs must not hide stale evidence.
        successful = (db.query(SyncRunModel)
                      .filter(SyncRunModel.finished_at.isnot(None))
                      .filter(SyncRunModel.status.in_(["success", "partial"]))
                      .filter(SyncRunModel.found > SyncRunModel.failed)
                      .order_by(SyncRunModel.finished_at.desc(), SyncRunModel.id.desc()).first())
        counts = _repo(db).count_by_status(db)
    except Exception:
        db.rollback()
        return HealthResponse(
            status="degraded", database="error", sources=sources,
            data=DataHealthResponse(status="degraded", reasons=["database_unavailable"]),
        )
    total = sum(counts.values())
    unknown = counts[StandardStatus.UNKNOWN.value]
    unknown_rate = unknown / total if total else 0.0
    failure_rate = latest.failed / latest.found if latest and latest.found else None
    reasons = []
    if not total:
        reasons.append("empty_dataset")
    if unknown_rate > 0.05:
        reasons.append("high_unknown_rate")
    if counts[StandardStatus.CONFLICT.value]:
        reasons.append("conflicting_evidence")
    if successful is None:
        reasons.append("no_successful_sync")
    elif successful.finished_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc) - timedelta(days=3):
        reasons.append("stale_sync")
    if latest and (latest.status not in {"success", "partial"} or
                   (not latest.found and (latest.status != "success" or latest.failed)) or
                   (failure_rate is not None and failure_rate > 0.5)):
        reasons.append("unhealthy_latest_sync")
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        database=database,
        last_sync=latest.finished_at if latest else None,
        sources=sources,
        data=DataHealthResponse(
            status="degraded" if reasons else "ok", total=total, unknown=unknown,
            unknown_rate=round(unknown_rate, 4), reasons=reasons,
            last_successful_sync=successful.finished_at if successful else None,
            latest_sync_failure_rate=round(failure_rate, 4) if failure_rate is not None else None,
        ),
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
    if model is StandardV2Model:
        last_updated = db.query(func.max(StandardV2Model.published_at)).scalar()
        if last_updated is None:
            last_updated = db.query(func.max(StandardV2Model.last_verified_at)).scalar()
    else:
        last_updated = db.query(func.max(StandardModel.last_verified_at)).scalar()
    if last_updated is not None:
        last_updated = (
            last_updated.replace(tzinfo=timezone.utc)
            if last_updated.tzinfo is None
            else last_updated.astimezone(timezone.utc)
        )
    return StatsResponse(
        count=sum(counts.values()),
        last_updated=last_updated,
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
    # Public endpoint: raw error messages can carry source URLs or exception
    # details, so they stay in logs and the protected cron probe omits them too.
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
        }
    )


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    return _health_payload(db)


def _record_attempt_safely(db: Session, key: str | None, outcome: str) -> None:
    try:
        record_attempt(db, key, outcome)
    except Exception:
        db.rollback()
        logger.exception("could not record live lookup attempt key=%s", key)


# The matched record is a different standard or an unconfirmed version, so its
# status must not be presented as the cited standard's status.
_STATUS_NOT_TRANSFERABLE = frozenset({"code_mismatch", "version_unconfirmed"})


def _distinct_standards(rows) -> list:
    seen: dict[str, object] = {}
    for row in rows:
        seen.setdefault(getattr(row, "base_code", None) or row.normalized_code or row.code, row)
    return list(seen.values())


def _series(code: str | None) -> tuple[str, str] | None:
    parsed = parse_standard_code(code)
    return (parsed.prefix.replace("/T", ""), parsed.serial) if parsed is not None else None


def _resolve_local(db: Session, repo, request: VerifyRequest):
    """Return (standard, candidates); candidates are set only when the choice is ambiguous."""

    standard = repo.get_by_code(db, request.code) if request.code else None
    if standard is not None:
        return standard, []
    wanted_name = normalized_name(request.name)
    series = repo.code_candidates(db, request.code) if request.code else []
    if len(series) > 1:
        named = [row for row in series if wanted_name and normalized_name(row.name) == wanted_name]
        return (named[0], []) if len(named) == 1 else (None, series)
    if not request.name:
        return None, []
    matches = _distinct_standards(repo.search(db, request.name, limit=5))
    if len(matches) <= 1:
        return (matches[0] if matches else None), []
    wanted_series = _series(request.code)
    if wanted_series is not None:
        same_series = [row for row in matches if _series(row.normalized_code or row.code) == wanted_series]
        # With a code the matcher reports any identity difference, so the first
        # name hit stays acceptable when the series does not single one out.
        return (same_series[0] if len(same_series) == 1 else matches[0]), []
    return None, matches


def _unresolved_response(request: VerifyRequest, match_type: str, message: str, candidates=()) -> VerifyResponse:
    return VerifyResponse(
        input_code=request.code,
        status=StandardStatus.UNKNOWN,
        match_type=match_type,
        message=message,
        candidates=list(candidates),
    )


def _live_lookup(db: Session, key: str | None, run, trace: LookupTrace | None = None) -> str | None:
    """Run one bounded live lookup unless a recent attempt still applies; return its outcome."""

    cached = recent_attempt(db, key)
    if cached is not None:
        return cached
    trace = trace if trace is not None else LookupTrace()
    try:
        outcome = run(trace)
    except Exception:
        # Internal failures (e.g. persistence) are neither a source failure nor
        # a miss; nothing is cached so the next request retries.
        db.rollback()
        logger.exception("query-time live lookup failed for key=%s", key)
        return None
    if outcome is not None:
        _record_attempt_safely(db, key, outcome)
        if trace.failures:
            logger.warning("query-time live lookup key=%s outcome=%s failures=%s", key, outcome, trace.failures)
    return outcome


@router.post("/v1/verify", response_model=VerifyResponse)
def verify_standard(request: VerifyRequest, db: Session = Depends(get_db)):
    repo = _repo(db)
    standard, candidates = _resolve_local(db, repo, request)
    if candidates:
        listing = "、".join(f"{row.code}（{status_label(normalize_status(row.status))}）" for row in candidates)
        return _unresolved_response(
            request, "ambiguous", f"库中有多个可能的规范：{listing}，请补充完整编号确认",
            [_to_result(db, row) for row in candidates],
        )
    # One request-wide budget keeps discovery and refresh inside the platform
    # timeout; the attempt table stops unresolved codes re-querying sources.
    deadline = lookup_deadline()
    discovery_outcome = None
    discovery_trace = LookupTrace()
    if standard is None and live_refresh_enabled():
        discovered_holder: list = []

        def discover(trace: LookupTrace) -> str | None:
            discovered = discover_live(code=request.code, name=request.name, deadline=deadline, trace=trace)
            if discovered is None:
                return attempt_outcome(None, deadline, trace)
            persisted = persist_discovered_standard(db, discovered, use_v2=repo is StandardV2Repo)
            if persisted is None:
                return None
            discovered_holder.append(persisted)
            return attempt_outcome(discovered, deadline, trace)

        discovery_outcome = _live_lookup(
            db, lookup_key(code=request.code, name=request.name), discover, discovery_trace,
        )
        standard = discovered_holder[0] if discovered_holder else None
    if standard is None:
        if discovery_outcome == "ambiguous":
            listing = "、".join(discovery_trace.ambiguous) or "多个年份版本"
            return _unresolved_response(
                request, "ambiguous", f"来源中有多个可能的规范：{listing}，请补充完整编号确认",
            )
        if discovery_outcome in FAILURE_OUTCOMES:
            return _unresolved_response(
                request, "source_unavailable", "来源暂时不可用或查询超时，未能确认该规范是否存在，请稍后重试",
            )
        return _unresolved_response(request, "not_found", "本地规范库未找到匹配记录")
    if live_refresh_enabled() and not cache_is_fresh(standard):
        source_urls = {
            source.source_name: source.source_url
            for source in repo.sources_for(db, standard.id)
            if source.source_url
        }

        def refresh(trace: LookupTrace) -> str | None:
            refreshed = verify_live(standard, source_urls=source_urls, deadline=deadline, trace=trace)
            if refreshed is not None:
                persist_live_verification(db, standard, refreshed)
            return attempt_outcome(refreshed, deadline, trace)

        _live_lookup(db, lookup_key(code=standard.normalized_code or standard.code), refresh)
    result = _to_result(db, standard)
    decision = assess_standard_match(
        input_code=request.code, input_name=request.name, standard=standard, replaced_by=result.replaced_by,
    )
    result.match_type = decision.match_type
    result.confidence = decision.confidence
    result.recommended_citation = decision.recommended_citation
    result.message = decision.message
    return VerifyResponse(
        input_code=request.code,
        canonical_code=result.normalized_code or result.code,
        name=result.name,
        status=StandardStatus.UNKNOWN if decision.match_type in _STATUS_NOT_TRANSFERABLE else result.status,
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
            values = [item.name or "", item.code, "", "", "", "暂无法确认", "not_found", "", "", "", "", "", ""]
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
