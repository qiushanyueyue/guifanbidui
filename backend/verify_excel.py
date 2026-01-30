import sys
import os

# Add project root to path
sys.path.append("/Users/qiushanyueyue/Documents/work/规范对比/backend")

from app.services.excel_loader import excel_loader

EXCEL_PATH = "/Users/qiushanyueyue/Documents/work/规范对比/规范目录库20251011.xlsx"

print(f"Testing Excel load from: {EXCEL_PATH}")
if os.path.exists(EXCEL_PATH):
    print("File exists.")
    try:
        excel_loader.load_data(EXCEL_PATH)
        print("Load successful.")
        # Test a known standard if possible, or just checking count
        # print(f"Loaded {len(excel_loader._standards_map)} standards.") 
    except Exception as e:
        print(f"Error loading: {e}")
else:
    print("File DOES NOT exist.")
