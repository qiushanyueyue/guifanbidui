import re
import os
import json
import logging
import traceback
import google.generativeai as genai
from dotenv import load_dotenv
from typing import List, Optional
from app.models.schemas import StandardInfo

# Configure logging
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 配置 Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def extract_standards_from_text(text: str) -> List[StandardInfo]:
    """
    从文本中提取规范信息 (优先使用 Gemini，失败则降级为正则)
    """
    try:
        standards = []
        
        # 1. 尝试使用 Gemini 提取
        # 1. 尝试使用 Gemini 提取 (暂时禁用以防止网络卡顿，优先使用正则)
        # if GEMINI_API_KEY:
        #     try:
        #         model = genai.GenerativeModel('gemini-pro')
        #         prompt = f"""
        #         请分析以下设计说明文本，提取其中提到的所有建筑设计规范、标准。
        #         请返回一个 JSON 数组，每个元素包含：
        #         - code: 规范编号 (如 GB 50016-2014)，如果文中只有名称没编号，尝试补全或留空
        #         - name: 规范名称 (如 建筑设计防火规范)
        #         - year: 年号 (如 2014)，提取编号中的年份字段
        #
        #         文本内容：
        #         {text}
        #         
        #         仅返回 JSON 格式，不要包含 Markdown 标记。
        #         """
        #         # response = model.generate_content(prompt)
        #         # content = response.text.replace('```json', '').replace('```', '').strip()
        #         
        #         # data = json.loads(content)
        #         # for item in data:
        #         #     standards.append(StandardInfo(
        #         #         code=item.get('code', '').strip(), 
        #         #         name=item.get('name', '').strip(), 
        #         #         year=item.get('year', '')
        #         #     ))
        #         
        #         # logger.info("Gemini extraction successful")
        #         # return standards
        #         pass 
        #         
        #     except Exception as e:
        #         logger.error(f"Gemini extraction failed: {e}. Falling back to regex.")
    
        # 1. 尝试使用 DeepSeek 提取 (如果 Regex 失败或作为增强)
        # 策略：先 Regex。如果 Regex 没提取到任何内容，尝试 DeepSeek。
        
        # 2. 优先使用正则提取
        # 匹配模式 1: 《名称》(编号) 或 《名称》编号
    
        # 例如: 《建筑设计防火规范》(GB 50016-2014)
        # group 1: Name, group 2: Code
        # 匹配模式 1: 《名称》(编号) 或 《名称》编号 或 《名称》(编号)(版本)
        # 例如: 《建筑设计防火规范》(GB 50016-2014)
        # 例如: 《混凝土结构设计标准》(GB/T 50010-2010)(2024年版)
        # group 1: Name, group 2: Code, group 3 (optional): Version Suffix
        # Use [ \t]* instead of \s* to prevent matching across lines
        # 匹配模式 1: 《名称》(编号)
        # Modified to support "建标" and OCR errors (l for 1, O for 0)
        # Code part: ([A-Z/a-z0-9\u4e00-\u9fa5\s\.-]+) -> Allow Chinese chars and common OCR typos
        pattern_full = re.compile(r"《(.*?)》[ \t]*[(（]?([A-Za-z0-9\-\.\/ \t\u4e00-\u9fa5lO]+)[)）]?[ \t]*([(（].*?年版.*?[)）])?")
        
        # 匹配模式 2: 仅编号
        # Added support for "建标" explicitly and OCR typos in digits
        # \d+ -> [\dIOl]+ to capture 18 as l8 or 10 as IO
        # Reverted: Removed \u4e00-\u9fa5 from lookaround because codes often touch Chinese text (e.g. "2012天津")
        # Updated: Allow hyphens/dots in serial part (e.g. DB/T29-176-2016) -> [\dIOl]+(?:[.-][\dIOl]+)*
        # Updated: Removed boundary lookarounds entirely to allow codes touching text (e.g., "Item1JGJ")
        pattern_code_only = re.compile(
            r"((?:[A-Z]{2,}|建标)\/?\s*[T]?\s*[\dIOl]+(?:[.-][\dIOl]+)*-[\dIOl]{4})"
        )
    
        # Store results with their start position for sorting
        results_with_pos = []
    
        # 1. 先尝试匹配完整的 《名称》(编号)
        matches_full = pattern_full.finditer(text)
        found_codes = set()
        extracted_spans = []  # Track spans to prevent overlap duplications
    
        def is_overlapping(span_a, span_b):
            return max(span_a[0], span_b[0]) < min(span_a[1], span_b[1])
    
        for match in matches_full:
            extracted_spans.append(match.span())
    
            name = match.group(1).strip()
            code = match.group(2).strip()
            version_suffix = match.group(3)
    
            if version_suffix:
                name = f"{name}{version_suffix.strip()}"
            
            name = clean_name(name)
            code = clean_code(code)
            year = extract_year(code)
            
            std = StandardInfo(code=code, name=name, year=year)
            results_with_pos.append((match.start(), std))
            found_codes.add(code)
    
        # 2. 扫描剩余可能是编号的文本 (且未被 pattern 1 捕获的)
        matches_code = pattern_code_only.finditer(text)
        for match in matches_code:
            current_span = match.span()
            if any(is_overlapping(current_span, s) for s in extracted_spans):
                continue
            
            code = match.group(1).strip()
            code = clean_code(code)
            
            if code not in found_codes:
                extracted_spans.append(current_span)
                year = extract_year(code)
                std = StandardInfo(code=code, name=None, year=year)
                results_with_pos.append((match.start(), std))
                found_codes.add(code)
    
        # 3. 扫描仅包含名称的规范 (如 《公路工程基本建设项目设计文件编制办法》)
        pattern_name_only = re.compile(r"《(.*?)》")
        matches_name = pattern_name_only.finditer(text)
        
        for match in matches_name:
            current_span = match.span()
            if any(is_overlapping(current_span, s) for s in extracted_spans):
                continue
                
            name = match.group(1).strip()
            name = clean_name(name)
            
            extracted_spans.append(current_span)
            std = StandardInfo(code="", name=name, year=None)
            results_with_pos.append((match.start(), std))
    
        # 4. 如果通过正则未提取到任何内容，启用 DeepSeek 作为兜底
        if not results_with_pos:
            logger.info("Regex extraction returned empty. Attempting DeepSeek fallback...")
            deepseek_standards = extract_standards_deepseek(text)
            if deepseek_standards:
                 standards.extend(deepseek_standards)
                 return standards
        
        # Sort by start position
        results_with_pos.sort(key=lambda x: x[0])
        
        # Extract just the StandardInfo objects
        standards = [item[1] for item in results_with_pos]
                
        return standards
    except Exception as e:
        logger.error(f"Error in extract_standards_from_text: {e}")
        logger.error(traceback.format_exc())
        return []

def clean_name(name: str) -> str:
    """
    清洗规范名称，移除干扰性后缀或说明文字
    例如: "钢结构设计标准(附条文说明[另册])" -> "钢结构设计标准"
    """
    # 移除 (附条文说明...) 及其变体
    # 匹配模式：( 或 （ 开头，包含 "附" 和 "说明"， ) 或 ） 结尾
    name = re.sub(r"[(（].*?附.*?说明.*?[)）]", "", name)
    
    # 移除 [另册] 等方括号内容 (如果它单独存在)
    name = re.sub(r"[\[【].*?[\]】]", "", name)
    
    # 移除 (共X册) 
    name = re.sub(r"[(（]共.*?[册分卷][)）]", "", name)

    return name.strip()

def extract_standards_deepseek(text: str) -> List[StandardInfo]:
    """
    使用 DeepSeek API 提取规范信息
    """
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") 
    # Fallback to hardcoded key if env not set (User provided key)
    if not DEEPSEEK_API_KEY:
        logger.info("Detail: No DeepSeek API Key provided.")
        return []

    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        prompt = f"""
        请分析以下设计说明文本，提取其中提到的所有建筑设计规范、标准。
        请返回一个 JSON 数组，每个元素包含：
        - code: 规范编号 (如 GB 50016-2014)，如果文中只有名称没编号，尝试补全或留空
        - name: 规范名称 (如 建筑设计防火规范)
        - year: 年号 (如 2014)，提取编号中的年份字段

        文本内容：
        {text}
        
        仅返回 JSON 格式，不要包含 Markdown 标记 (如 ```json)。
        """
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that extracts standard codes and names from text."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        
        import requests
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        result_json = response.json()
        content = result_json['choices'][0]['message']['content']
        content = content.replace('```json', '').replace('```', '').strip()
        
        items = json.loads(content)
        standards = []
        for item in items:
             standards.append(StandardInfo(
                 code=item.get('code', '').strip(), 
                 name=item.get('name', '').strip(), 
                 year=item.get('year', '')
             ))
        return standards
            
    except Exception as e:
        logger.error(f"DeepSeek extraction failed: {e}")
        return []

def clean_code(code: str) -> str:
    """清理编号中的常见杂质及OCR错误"""
    # 替换中文括号等
    code = code.replace("（", "(").replace("）", ")")
    # 移除首尾标点
    code = code.strip(".,;。，；")
    
    # Fix OCR typos in the numeric part
    # Identify the Year part (last 4 chars usually) and the serial part
    # Simple heuristic: Replace 'l' with '1' and 'O' with '0' inside the string
    # BUT be careful not to replace 'l' in 'Cl' (Chlorine? Unlikely in standard code prefix)
    # Most prefixes are uppercase. 'l' usually means '1'.
    
    # Check if there are lowercase 'l' or uppercase 'O' mixed with digits
    # Since prefixes are usually uppercase letters, a 'l' is suspicious.
    if 'l' in code or 'O' in code:
         # Split prefix and number if possible. 
         # Assuming prefix is [A-Z]+. 
         # However, simplifying: just replace 'l' with '1' and 'O' with '0' 
         # because standard codes generally use uppercase letters (GB, JGJ). 
         # Lowercase 'l' is almost certainly 1.
         code = code.replace('l', '1')
         # Uppercase 'O' might be confusing with 'GB/T'. 'T' is fine. 
         # But 'O' is rare in prefixes. 'ISO' has O.
         # Be conservative with 'O'. Only replace if it looks like a year or number?
         # Most issues are l -> 1.
         pass

    # Force replace lowercase l -> 1
    code = code.replace('l', '1')
    
    return code

def extract_year(code: str) -> Optional[str]:
    """从编号中提取年份 (仅提取 -XXXX 部分)"""
    match = re.search(r"-(\d{4})", code)
    if match:
        return match.group(1)
    return None
