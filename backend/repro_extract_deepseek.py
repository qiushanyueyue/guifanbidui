import sys
import os
import time

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.extractor import extract_standards_from_text

# Text that should fail regex and trigger DeepSeek
text = "请严格按照相关建筑防火和结构设计规范进行设计，特别是关于抗震等级的要求。"

print("Starting extraction (expecting DeepSeek fallback)...")
start_time = time.time()

try:
    standards = extract_standards_from_text(text)
    print(f"Extraction complete in {time.time() - start_time:.4f} seconds.")
    print(f"Found {len(standards)} standards:")
    for std in standards:
        print(f"- {std.code} {std.name} ({std.year})")
except Exception as e:
    print(f"Extraction failed: {e}")
