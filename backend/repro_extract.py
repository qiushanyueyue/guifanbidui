import re

text = """
(2) 《建筑结构荷载规范》 (GB50009-2012)
    (3) 《混凝土结构设计标准》 (GB/T 50010-2010) (2024年版)
"""

# Current Regex from extractor.py (Patched)
pattern_full = re.compile(r"《(.*?)》[ \t]*[(（]?([A-Z/a-z0-9\s\.-]+)[)）]?[ \t]*([(（].*?年版.*?[)）])?")

print("--- Matches ---")
for match in pattern_full.finditer(text):
    print(f"Full: {match.group(0)!r}")
    print(f"Name: {match.group(1)!r}")
    print(f"Code: {match.group(2)!r}")
    print(f"Ver : {match.group(3)!r}")
    print("-" * 20)
