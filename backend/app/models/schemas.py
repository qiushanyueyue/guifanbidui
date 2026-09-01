"""Pydantic contracts for the compatibility and v1 APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StandardStatus, VerificationLevel


class StandardInfo(BaseModel):
    code: str = ""
    name: Optional[str] = None
    year: Optional[str] = None
    base_code: Optional[str] = None
    normalized_code: Optional[str] = None
    edition: Optional[str] = None
    revision_year: Optional[str] = None
    amendment: Optional[str] = None


class ExtractionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)


class ExtractionResponse(BaseModel):
    standards: List[StandardInfo]


class ExportRequest(BaseModel):
    standards: List[StandardInfo] = Field(max_length=5000)


class SearchRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)


class SourceInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    url: Optional[str] = None
    code: Optional[str] = None
    name_text: Optional[str] = None
    status: StandardStatus = StandardStatus.UNKNOWN
    raw_status: Optional[str] = None
    fetched_at: Optional[datetime] = None
    source_updated_at: Optional[str] = None
    parse_status: str = "ok"


class SearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    code: str
    normalized_code: Optional[str] = None
    name: str = ""
    status: StandardStatus = StandardStatus.UNKNOWN
    status_label: Optional[str] = None
    business_conclusion: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = "db"
    soujianzhu_url: Optional[str] = None
    edition: Optional[str] = None
    revision_year: Optional[str] = None
    amendment: Optional[str] = None
    implement_date: Optional[str] = None
    publish_date: Optional[str] = None
    abolish_date: Optional[str] = None
    replaces: Optional[str] = None
    replaced_by: Optional[str] = None
    article_status: Optional[str] = None
    mandatory_clause_status: Optional[str] = None
    issuing_authority: Optional[str] = None
    canonical_source: Optional[str] = None
    verification_level: VerificationLevel = VerificationLevel.UNVERIFIED
    source_conflict: bool = False
    last_verified_at: Optional[datetime] = None
    sources: List[SourceInfo] = Field(default_factory=list)
    match_type: Optional[str] = None
    confidence: Optional[float] = None
    recommended_citation: Optional[str] = None
    message: Optional[str] = None
    data_quality_status: Optional[str] = None
    document_kind: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]


class DetailRequest(BaseModel):
    url: Optional[str] = None
    code: Optional[str] = None
    id: Optional[int] = None


class StandardDetail(SearchResult):
    department: Optional[str] = "-"
    release_date: Optional[str] = "-"
    implement_date: Optional[str] = "-"
    drafting_unit: Optional[str] = "-"
    technical_committee: Optional[str] = "-"
    ccs: Optional[str] = "-"
    englishName: Optional[str] = "-"
    ics: Optional[str] = "-"
    publisher: Optional[str] = "-"
    pages: Optional[str] = "-"
    obsolete_date: Optional[str] = "-"
    replaced_by_code: Optional[str] = None
    replaced_by_name: Optional[str] = None


class StatsResponse(BaseModel):
    count: int
    last_updated: Optional[datetime] = None
    current: int = 0
    upcoming: int = 0
    abolished: int = 0
    replaced: int = 0
    partially_amended: int = 0
    unknown: int = 0
    conflict: int = 0


class VerifyRequest(BaseModel):
    code: str = Field(default="", max_length=120)
    name: Optional[str] = Field(default=None, max_length=500)


class VerifyResponse(BaseModel):
    input_code: str
    canonical_code: Optional[str] = None
    name: str = ""
    status: StandardStatus = StandardStatus.UNKNOWN
    current_edition: Optional[str] = None
    replaced_by: Optional[str] = None
    publish_date: Optional[str] = None
    implement_date: Optional[str] = None
    verification_level: VerificationLevel = VerificationLevel.UNVERIFIED
    sources: List[SourceInfo] = Field(default_factory=list)
    last_verified_at: Optional[datetime] = None
    match_type: str = "unknown"
    confidence: float = 0.0
    recommended_citation: str = ""
    message: str = ""
    result: Optional[SearchResult] = None


class SyncStatusResponse(BaseModel):
    latest: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    database: str
    last_sync: Optional[datetime] = None
    sources: dict[str, str]
