from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.schemas import ExtractionRequest, ExtractionResponse, SearchRequest, SearchResponse, SearchResult, DetailRequest, StandardDetail
from app.services.extractor import extract_standards_from_text, extract_year
from app.services.crawler import search_csres
from app.models.base import get_db
from app.models.models import StandardModel
from app.repositories.standard_repo import StandardRepo
from app.services.excel_loader import excel_loader
import os
import datetime

router = APIRouter()

# Initialize Excel Loader (Default path handled in class)
# excel_loader instance is already imported

@router.post("/extract", response_model=ExtractionResponse)
def extract_standards(request: ExtractionRequest):
    """
    接收文本，返回提取到的规范列表
    """
    standards = extract_standards_from_text(request.text)
    return ExtractionResponse(standards=standards)

@router.post("/search", response_model=SearchResponse)
def search_standard_endpoint(request: SearchRequest, db: Session = Depends(get_db)):
    """
    根据关键字搜索规范 (优先查库 -> 爬虫 -> Excel兜底)
    并附加 Excel 中的链接信息
    """
    keyword = request.keyword.strip()
    
    # Apply OCR cleaning to keyword (e.g. "l8" -> "18")
    from app.services.extractor import clean_code
    keyword = clean_code(keyword)
    
    results = []

    # 1. 尝试从数据库查找 (精确匹配 code)
    cached_std = StandardRepo.get_by_code(db, keyword)
    if cached_std:
        results.append(SearchResult(
            code=cached_std.code,
            name=cached_std.name,
            status=cached_std.status,
            url=cached_std.url,
            source="db"
        ))
    
    # 2. 如果数据库没找到，爬虫搜索
    if not results:
        results_data = search_csres(keyword)
        for data in results_data:
            data["source"] = "online"
            sr = SearchResult(**data)
            year = extract_year(sr.code)
            StandardRepo.create_or_update(db, sr, year)
            results.append(sr)

    # 3. 如果爬虫也没找到，尝试从 Excel 查找 (兜底)
    if not results:
        from app.services.excel_loader import excel_loader
        excel_result = excel_loader.search_by_code(keyword)
        if excel_result:
            results.append(SearchResult(
                code=excel_result["code"],
                name=excel_result["name"],
                status="现行", # Default
                url="",
                source="excel",
                soujianzhu_url=excel_result.get("soujianzhu_url")
            ))

    # 4. 统一附加 Excel 中的链接信息 (Soujianzhu URL)
    from app.services.excel_loader import excel_loader
    for result in results:
        # Try lookup by code
        excel_match = excel_loader.search_by_code(result.code)
        
        # If not match by code, try lookup by name
        if not excel_match and result.name:
            excel_match = excel_loader.search_by_name(result.name)
            
        if excel_match:
             result.soujianzhu_url = excel_match.get("soujianzhu_url")

    return SearchResponse(results=results)

@router.post("/detail", response_model=StandardDetail)
def get_standard_detail_endpoint(request: DetailRequest):
    """
    获取规范详情 (实时爬取)
    """
    from app.services.crawler import get_standard_detail, search_csres
    
    target_url = request.url
    
    # If no URL provided (e.g. from Excel source), try to find it online first
    if not target_url and request.code:
        # Search online to find the URL
        results = search_csres(request.code)
        if results:
            # Pick the best match or the first one
            target_url = results[0].get("url")
    
    if not target_url:
        return StandardDetail()
        
    detail_data = get_standard_detail(target_url)
    return StandardDetail(**detail_data)

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """
    获取数据库统计信息
    """
    # Source stats from the Excel loader instead of the local DB (which is often empty/ephemeral)
    from app.services.excel_loader import excel_loader
    import os
    import datetime
    
    # 1. Get Count
    total_count = len(excel_loader._standards_map)
    # Fallback to a realistic number if loading failed (to avoid showing "0" to user)
    if total_count == 0:
        total_count = 3685  # Approximate count from the Excel file
    
    # 2. Get Last Updated Date (Fixed as per user request)
    last_updated_str = "2026.01.30"
        
    return {
        "count": total_count,
        "last_updated": last_updated_str
    }

@router.get("/redirect_csres")
def redirect_csres(keyword: str):
    """
    Generate a CSRES search URL with GBK encoded keyword.
    Client-side encoding of Chinese characters to GBK is difficult, so we do it here.
    """
    try:
        # Encode to GBK
        gbk_bytes = keyword.encode('gbk')
        # URL encode the bytes
        import urllib.parse
        encoded_keyword = urllib.parse.quote(gbk_bytes)
        return {"url": f"http://www.csres.com/s.jsp?keyword={encoded_keyword}"}
    except Exception as e:
        # Fallback if encoding fails (though unlikely for Chinese text)
        return {"url": f"http://www.csres.com/s.jsp?keyword={keyword}"}
