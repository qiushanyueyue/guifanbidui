from app.services.extractor import extract_standards_from_text
import json

text = """
1、（1）《地铁设计规范》（GB50157-2013）
（2）《城市轨道交通工程设计规范》（北京市地方标准,DB11/995-2013）
（3）《北京地区建筑地基基础勘察设计规范》（北京市地方标准DBJ11-501-2009）
"""

try:
    results = extract_standards_from_text(text)
    print(f"Extracted {len(results)} standards:")
    for r in results:
        print(r)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
