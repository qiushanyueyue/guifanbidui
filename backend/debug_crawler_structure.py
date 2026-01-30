import requests
from bs4 import BeautifulSoup
import re

url = "http://www.csres.com/detail/248465.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = 'gbk' # Force GBK
    
    print(f"Status Code: {resp.status_code}")
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    def debug_field(label_text):
        print(f"\n--- Debugging: {label_text} ---")
        label_tags = soup.find_all(string=re.compile(label_text))
        print(f"Found {len(label_tags)} matches.")
        
        for i, tag in enumerate(label_tags):
            print(f"Match {i+1}: '{tag}' (Parent: {tag.parent.name})")
            
            # Simulate logic
            parent_td = tag.find_parent('td') or tag.find_parent('th')
            if parent_td:
                print(f"  Found Parent TD: {parent_td}")
                next_td = parent_td.find_next_sibling('td')
                if next_td:
                    print(f"  Next Sibling TD: {next_td.get_text(strip=True)}")
                else:
                     print("  NO Next Sibling TD")
            else:
                print("  NO Parent TD found directly (might be further up)")

    debug_field("发布日期")
    debug_field("实施日期")
    debug_field("归口单位")
    debug_field("英文名称")

except Exception as e:
    print(f"Error: {e}")
