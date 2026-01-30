
import sys
import os
import requests

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.crawler import search_csres

def test_search():
    keyword = "JGJ 145-2013"
    print(f"Searching for: {keyword}")
    
    # Manually reproduce the request to save HTML
    params = {"keyword": keyword}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    resp = requests.get("http://www.csres.com/s.jsp", params=params, headers=headers)
    resp.encoding = "gb2312"
    with open("backend/debug_search_jgj.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved HTML to backend/debug_search_jgj.html")

    results = search_csres(keyword)
    
    for res in results:
        print(f"Code: {res['code']}")
        print(f"Name: {res['name']}")
        print(f"Status: {res['status']}")
        print("-" * 20)

if __name__ == "__main__":
    test_search()
