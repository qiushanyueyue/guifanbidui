import sys
import os
sys.path.append("/Users/qiushanyueyue/Documents/work/规范对比/backend")

from app.services.extractor import extract_standards
import json

text = "3) 《建筑设计防火规范》（GB50016-2014）（2018年版）；"

print(f"Input text: {text}")
standards = extract_standards(text)
print(f"Extracted {len(standards)} standards:")
for i, std in enumerate(standards):
    print(f"Standard {i+1}:")
    print(json.dumps(std, ensure_ascii=False, indent=2))
