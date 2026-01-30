import pandas as pd
import re
from typing import Optional, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelLoader:
    _instance = None
    _standards_map: Dict[str, dict] = {} # Key: normalized code
    _name_map: Dict[str, dict] = {}      # Key: normalized name

    def __new__(cls, file_path: str = None):
        if cls._instance is None:
            cls._instance = super(ExcelLoader, cls).__new__(cls)
            # Default to the user's provided path if none specified
            # Use local copy if available, fallback to volume
            # When running from backend/, the file is in current dir
            local_path = "standards_data.xlsx" 
            volume_path = "/Volumes/yue/Download/规范目录库（含网址）.xlsx"
            
            import os
            # Check current directory
            if os.path.exists(local_path):
                path_to_load = local_path
            # Check backend directory (if running from root)
            elif os.path.exists(os.path.join("backend", local_path)):
                 path_to_load = os.path.join("backend", local_path)
            else:
                path_to_load = file_path if file_path else volume_path
            
            cls._instance.load_data(path_to_load)
        return cls._instance

    def load_data(self, file_path: str):
        try:
            logger.info(f"Loading standards from Excel: {file_path}")
            df = pd.read_excel(file_path)
            
            # Check for new format columns
            if '名称' in df.columns and '网址' in df.columns:
                self._load_new_format(df)
            elif '规范名称及编号' in df.columns:
                self._load_old_format(df)
            else:
                logger.error("Unknown Excel format: columns not found")
                
            logger.info(f"Loaded {len(self._standards_map)} codes and {len(self._name_map)} names from Excel.")
            
            # Inject manual overrides
            self._inject_manual_data()
            
        except Exception as e:
            logger.error(f"Failed to load Excel file: {e}")
        finally:
            # Inject manual overrides even if Excel fails
            self._inject_manual_data()

    def _load_new_format(self, df):
        for _, row in df.iterrows():
            content = row['名称']
            url = row['网址']
            
            if not isinstance(content, str):
                continue
            
            # Parse "《Name》Code" or "Prefix,《Name》Code"
            # Extract Name (inside 《》) and Code (after 》)
            name_match = re.search(r"《(.*?)》", content)
            
            if name_match:
                name = name_match.group(1).strip()
                # Code typically follows the closing bracket
                # But sometimes content is "Prefix,《Name》Code"
                # Let's try to extract code from the whole string or just the part after?
                # Usually code is at the end or after name.
                
                # Heuristic: Find pattern matching code in the whole string
                code_match = re.search(r"([A-Z/]{2,}\s*[A-Z]?\s*\d+(?:\.\d+)?-\d{4})", content)
                code = code_match.group(1).strip() if code_match else ""
                
                entry = {
                    "name": name,
                    "code": code,
                    "full_content": content,
                    "source": "excel",
                    "soujianzhu_url": url
                }
                
                if code:
                    norm_code = self._normalize_code(code)
                    self._standards_map[norm_code] = entry
                
                if name:
                    norm_name = self._normalize_name(name)
                    self._name_map[norm_name] = entry

    def _load_old_format(self, df):
        for _, row in df.iterrows():
            content = row['规范名称及编号']
            if not isinstance(content, str):
                continue
            
            match = re.search(r"《(.*?)》(.*)", content)
            if match:
                name = match.group(1).strip()
                code = match.group(2).strip()
                
                entry = {
                    "name": name,
                    "code": code,
                    "full_content": content,
                    "source": "excel",
                    "soujianzhu_url": None
                }
                
                normalized_code = self._normalize_code(code)
                self._standards_map[normalized_code] = entry
                norm_name = self._normalize_name(name)
                self._name_map[norm_name] = entry

    def _normalize_code(self, code: str) -> str:
        """Remove spaces and convert to uppercase for consistent lookups"""
        return re.sub(r"\s+", "", code).upper()

    def _normalize_name(self, name: str) -> str:
        """Remove spaces for consistent name lookups"""
        # First clean the name of artifacts like (共二册)
        clean = self._clean_name_text(name)
        return re.sub(r"\s+", "", clean).strip()

    def _clean_name_text(self, name: str) -> str:
        """Clean specific suffixes from name"""
        # Remove (共X册)
        name = re.sub(r"[(（]共.*?[册分卷][)）]", "", name)
        return name

    def search_by_code(self, code: str) -> Optional[dict]:
        """Search for a standard by its code"""
        normalized_query = self._normalize_code(code)
        return self._standards_map.get(normalized_query)
        
    def search_by_name(self, name: str) -> Optional[dict]:
        """Search for a standard by its name"""
        normalized_query = self._normalize_name(name)
        return self._name_map.get(normalized_query)

    def _inject_manual_data(self):
        """Inject manually provided standards that are missing from Excel"""
        manual_entries = [
            {
                "name": "地铁设计规范",
                "code": "GB 50157-2013",
                "full_content": "地铁设计规范 GB 50157-2013",
                "source": "manual",
                "soujianzhu_url": "https://www.soujianzhu.cn/NormAndRules/NormContent.aspx?id=2246"
            },
            {
                "name": "钢筋焊接及验收规程",
                "code": "JGJ 18-2012",
                "full_content": "钢筋焊接及验收规程 JGJ 18-2012",
                "source": "manual",
                "soujianzhu_url": "http://www.csres.com/detail/223722.html"
            }
        ]
        
        for entry in manual_entries:
            # Add to code map
            if entry["code"]:
                norm_code = self._normalize_code(entry["code"])
                self._standards_map[norm_code] = entry
            
            # Add to name map
            if entry["name"]:
                norm_name = self._normalize_name(entry["name"])
                self._name_map[norm_name] = entry
                
        logger.info(f"Injected {len(manual_entries)} manual standards.")

# Global instance
excel_loader = ExcelLoader()
