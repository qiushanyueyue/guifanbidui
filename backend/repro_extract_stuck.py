import sys
import os
import time

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.extractor import extract_standards_from_text

# Example text from InputSection.tsx
text = """设计依据：
(1)《民用建筑设计统一标准》GB 50352-2019
(2)《建筑设计防火规范》GB 50016-2014
(3)《无障碍设计规范》GB 50763-2012
(4)《汽车库、修车库、停车场设计防火规范》GB 50067-2014
(5)《办公建筑设计标准》JGJ 67-2019
(6)《地铁设计规范》（GB 50157-2003）
(7)《公路工程基本建设项目设计文件编制办法》"""

print("Starting extraction...")
start_time = time.time()

try:
    standards = extract_standards_from_text(text)
    print(f"Extraction complete in {time.time() - start_time:.4f} seconds.")
    print(f"Found {len(standards)} standards:")
    for std in standards:
        print(f"- {std.code} {std.name} ({std.year})")
except Exception as e:
    print(f"Extraction failed: {e}")
