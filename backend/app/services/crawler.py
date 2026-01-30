import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import urllib.parse
import re

BASE_URL = "http://www.csres.com"
SEARCH_URL = "http://www.csres.com/s.jsp"

def search_csres(keyword: str) -> List[Dict[str, str]]:
    """
    搜索 csres.com 获取规范列表
    """
    try:
        # 构建查询参数: keyword 需 GBK 编码? 
        # csres usually accepts keyword in query param.
        # Ensure keyword is properly encoded for the URL
        
        # NOTE: csres pages are often GB2312/GBK encoded.
        # We might need to handle encoding carefully.
        
        params = {"keyword": keyword}
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        
        response = requests.get(SEARCH_URL, params=params, headers=headers, timeout=10)
        response.encoding = "gb2312" # CSRES uses gb2312 usually
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        
        # 解析搜索结果表格
        # The structure is usually a table with class or specific attributes
        # Searching for the main table that contains results
        
        # Check for "thead" generally implies the search result table
        tables = soup.find_all("table")
        target_table = None
        for table in tables:
            if table.find("thead"):
                target_table = table
                break
        
        if not target_table:
            # Fallback looking for specific headers header like "标准编号"
            for table in tables:
                if "标准编号" in table.text:
                    target_table = table
                    break
                    
        if target_table:
            # Try to identify column indices from header
            header_row = target_table.find("tr")
            status_idx = 2  # Default
            
            if header_row:
                header_cols = header_row.find_all(["th", "td"])
                for idx, col in enumerate(header_cols):
                    text = col.get_text(strip=True)
                    if "状态" in text:
                        status_idx = idx
                        break
            
            rows = target_table.find_all("tr")
            # Skip header row
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    # Column mapping (csres layout):
                    # 0: Standard Number (Code) - e.g. "GB 50016-2014"
                    # 1: Chinese Title - e.g. "建筑设计防火规范"
                    # Default 2: Status - e.g. "现行"
                    
                    link_tag = cols[0].find("a")
                    # Clean the code text (sometimes has &nbsp; or newlines)
                    code = cols[0].get_text(strip=True)
                    
                    # Fix for csres extra digits bug (e.g. "GB 50016-20142")
                    # If code ends with 5 digits and the 4th from last is a digit, it might be YYYY+Digit
                    # Better heuristic: Standard codes usually end with -YYYY. 
                    # If we see -YYYY\d, strip the last digit.
                    import re
                    match_year = re.search(r'-(\d{4})(\d+)$', code)
                    if match_year:
                         # Found -20142, take -2014
                         code = code[:-(len(match_year.group(2)))]

                    title = cols[1].get_text(strip=True)
                    
                    # Robust Status Extraction
                    status = ""
                    if len(cols) > status_idx:
                         status = cols[status_idx].get_text(strip=True)
                    
                    # Filter out invalid status strings like Department names
                    # Common invalid status text often contains "局" or "部" or is too long
                    invalid_keywords = ["局", "部", "委员会", "住房", "城乡", "建设"]
                    valid_statuses = ["现行", "废止", "即将实施", "作废", "被替", "现行有效"]
                    
                    is_valid_status = (
                        len(status) <= 10 
                        and not any(k in status for k in invalid_keywords)
                    )

                    if not is_valid_status:
                        # Reset status and try to find a valid one in other columns
                        status = ""
                        for col in cols:
                            txt = col.get_text(strip=True)
                            if any(s in txt for s in valid_statuses) and len(txt) < 10:
                                status = txt
                                break
                    
                    # Default to hyphen if still not found
                    if not status:
                        status = "-"

                    detail_url = ""
                    if link_tag and link_tag.has_attr("href"):
                         # Handle relative URLs correctly
                        if link_tag["href"].startswith("http"):
                            detail_url = link_tag["href"]
                        else:
                            detail_url = urllib.parse.urljoin(BASE_URL, link_tag["href"])
                    
                    # Ensure we returned valid data
                    # Filter out garbage rows where code is too long or contains non-code keywords
                    if code and title:
                        is_valid_code = len(code) < 40 and not any(k in code for k in ["共找到", "购书", "标准编号", "共有"])
                        
                        if is_valid_code:
                            results.append({
                                "code": code,
                                "name": title,
                                "status": status,
                                "url": detail_url
                            })
                    
        return results

    except Exception as e:
        print(f"Error searching csres: {e}")
        return []

def get_standard_detail(url: str) -> Dict[str, str]:
    """
    Scrape detailed information from a specific standard page on csres.com
    """
    if not url:
        return {}
        
    detail = {"url": url} # Initialize detail here for early return
    # Retry logic for stability
    max_retries = 3
    resp = None
    for attempt in range(max_retries):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                resp.encoding = 'gbk'
                break
        except Exception:
            if attempt == max_retries - 1:
                print(f"Error scraping detail {url} after {max_retries} attempts.")
                return detail
            import time
            time.sleep(1)
    
    if resp is None or resp.status_code != 200:
        return detail

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Helper to safely get text from a label row
        def get_field(label_text):
             # Find th/td with label, then get next td
             label_tag = soup.find(string=re.compile(label_text))
             if label_tag:
                 parent = label_tag.find_parent('td') or label_tag.find_parent('th')
                 if parent:
                     next_td = parent.find_next_sibling('td')
                     if next_td:
                         return next_td.get_text(strip=True)
             return "-"

        detail["englishName"] = get_field("英文名称")
        detail["ics"] = get_field("ICS分类")
        detail["publisher"] = get_field("出版社")
        detail["pages"] = get_field("页数")
        detail["department"] = get_field("发布部门")
        detail["release_date"] = get_field("发布日期")
        detail["implement_date"] = get_field("实施日期")
        detail["obsolete_date"] = get_field("废止日期")
        detail["replaces"] = get_field("替代情况")
        detail["technical_committee"] = get_field("归口单位")
        # CCS usually labeled as "中标分类"
        detail["ccs"] = get_field("中标分类")
        
        # New: Parse "被替代标准" (replaced_by)
        replaced_by_raw = get_field("被替代标准")
        detail["replaced_by"] = replaced_by_raw
        
        detail["replaced_by_code"] = None
        detail["replaced_by_name"] = None

        if replaced_by_raw and replaced_by_raw != "-":
            # Try to extract standard code from the raw text
            # Format usually: "OldCode;被NewCode代替" or just "被NewCode代替"
            # We want NewCode.
            
            target_segment = replaced_by_raw
            if "被" in replaced_by_raw:
                # Split and search in the part AFTER "被"
                parts = replaced_by_raw.split("被")
                if len(parts) > 1:
                    target_segment = parts[1]
            
            code_pattern = re.compile(r"([A-Z/]{2,}\s*\d+(?:\.\d+)?-\d{4})")
            match = code_pattern.search(target_segment)
            
            if match:
                replacing_code = match.group(1).strip()
                # Check if we accidentally extracted the same old code (unlikely with split, but possible)
                if replacing_code != detail.get('code'): # We don't have this.code here easily unless passed? We assume it's different.
                     detail["replaced_by_code"] = replacing_code
                
                # Now fetch the name for this code
                print(f"Found replacing code: {replacing_code}. Fetching name...")
                # Avoid infinite recursion or deep chains - just search once
                try:
                    search_results = search_csres(replacing_code)
                    if search_results:
                        # Find exact match if possible, or take the first
                        for res in search_results:
                            # Loose match to handle spaces
                            if res['code'].replace(' ', '') == replacing_code.replace(' ', ''):
                                detail["replaced_by_name"] = res['name']
                                break
                        if not detail["replaced_by_name"] and search_results:
                             detail["replaced_by_name"] = search_results[0]['name']
                except Exception as e:
                    print(f"Failed to fetch name for replacing code {replacing_code}: {e}")

        return detail

    except Exception as e:
        print(f"Error scraping detail {url}: {e}")
        return {}
