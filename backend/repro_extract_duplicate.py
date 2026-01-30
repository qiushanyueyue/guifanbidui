import sys
import os
sys.path.append(os.getcwd())

from app.services.extractor import extract_standards_from_text

text = """设计依据：
1. 《建筑设计防火规范》 GB 50016-2014
2. 《住宅设计规范》 GB 50096-2011
3. 《民用建筑设计统一标准》 GB 50352-2019"""

print("--- Extracting Standards ---")
results = extract_standards_from_text(text)
for r in results:
    print(f"Code: {repr(r.code)}, Name: {repr(r.name)}")
