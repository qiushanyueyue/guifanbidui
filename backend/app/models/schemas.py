from pydantic import BaseModel
from typing import List, Optional

class StandardInfo(BaseModel):
    code: str  # 规范编号，如 GB 50016-2014
    name: Optional[str] = None  # 规范名称，如 建筑设计防火规范
    year: Optional[str] = None  # 年号，如 2014

class ExtractionRequest(BaseModel):
    text: str

class ExtractionResponse(BaseModel):
    standards: List[StandardInfo]

class SearchRequest(BaseModel):
    keyword: str

class SearchResult(BaseModel):
    code: str
    name: str
    status: str
    url: str
    source: Optional[str] = "online" # excel, db, online
    soujianzhu_url: Optional[str] = None # Link from the imported Excel file

class SearchResponse(BaseModel):
    results: List[SearchResult]

class DetailRequest(BaseModel):
    url: Optional[str] = None
    code: Optional[str] = None

class StandardDetail(BaseModel):
    department: Optional[str] = "-"
    release_date: Optional[str] = "-"
    implement_date: Optional[str] = "-"
    status: Optional[str] = "-"
    drafting_unit: Optional[str] = "-"
    replaced_by: Optional[str] = "-"
    replaces: Optional[str] = "-"
    technical_committee: Optional[str] = "-"
    ccs: Optional[str] = "-"
    englishName: Optional[str] = "-"
    ics: Optional[str] = "-"
    publisher: Optional[str] = "-"
    pages: Optional[str] = "-"
    obsolete_date: Optional[str] = "-"
    replaced_by_code: Optional[str] = None
    replaced_by_name: Optional[str] = None

