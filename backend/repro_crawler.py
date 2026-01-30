import sys
import os
sys.path.append(os.getcwd())

from app.services.crawler import search_csres, get_standard_detail

print("--- Searching GB 55001-2021 ---")
results = search_csres("GB 55001-2021")
for r in results:
    print(r)
    if "url" in r:
        print(f"Fetching details for {r['url']}...")
        detail = get_standard_detail(r['url'])
        print(f"Detail: {detail}")
