import requests

url = "http://www.csres.com/detail/209138.html"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
}
try:
    resp = requests.get(url, headers=headers, timeout=15)
    resp.encoding = 'gbk'
    with open("backend/debug_csres.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("Saved to backend/debug_csres.html")
except Exception as e:
    print(f"Error: {e}")
