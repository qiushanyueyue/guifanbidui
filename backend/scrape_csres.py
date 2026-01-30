import requests
from bs4 import BeautifulSoup
import sqlite3
import datetime
import time
import re

BASE_URL = "http://www.csres.com/sort/industry/002009_{}.html"
DB_PATH = "standards.db"
TOTAL_PAGES = 41

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def scrape_page(page_num):
    url = BASE_URL.format(page_num)
    print(f"Scraping page {page_num}: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # response.encoding = 'gb2312' 
        response.encoding = response.apparent_encoding # Let requests guess based on content
        if response.status_code != 200:
            print(f"Failed to retrieve page {page_num}, status code: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the table by looking for the header "标准编号"
        # Robust method: Find matching TD text
        header_td = None
        for td in soup.find_all('td'):
            if "标准编号" in td.get_text(strip=True):
                header_td = td
                break
        
        if not header_td:
            print(f"Could not find table header on page {page_num}")
            return []
            
        # The table is the parent of the parent of the tr containing the td
        # tr -> table or tbody -> table
        table = header_td.find_parent('table')
        if not table:
             print(f"Could not find table element on page {page_num}")
             return []

        standards = []
        # Skip the first row (header)
        rows = table.find_all('tr')[1:] 
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 5:
                continue
            
            try:
                code = cols[0].get_text(strip=True)
                name = cols[1].get_text(strip=True)
                dept = cols[2].get_text(strip=True)
                impl_date = cols[3].get_text(strip=True)
                status = cols[4].get_text(strip=True)
                
                # Extract year from code or date if possible, but for now we just store raw data
                # We can try to extract year from code (e.g. GB 50016-2014 -> 2014)
                year_match = re.search(r'-(\d{4})', code)
                year = year_match.group(1) if year_match else ""

                standards.append({
                    "code": code,
                    "name": name,
                    "department": dept,
                    "impl_date": impl_date,
                    "status": status,
                    "year": year
                })
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
                
        return standards

    except Exception as e:
        print(f"Error scraping page {page_num}: {e}")
        return []

def update_database(standards):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    count_new = 0
    count_updated = 0
    
    for std in standards:
        # Check if exists
        cursor.execute("SELECT id FROM standards WHERE code = ?", (std['code'],))
        existing = cursor.fetchone()
        
        now = datetime.datetime.utcnow()
        
        if existing:
            # Update
            cursor.execute("""
                UPDATE standards 
                SET name = ?, status = ?, publishing_department = ?, implementation_date = ?, year = ?, last_updated = ?
                WHERE code = ?
            """, (std['name'], std['status'], std['department'], std['impl_date'], std['year'], now, std['code']))
            count_updated += 1
        else:
            # Insert
            cursor.execute("""
                INSERT INTO standards (code, name, status, publishing_department, implementation_date, year, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (std['code'], std['name'], std['status'], std['department'], std['impl_date'], std['year'], now))
            count_new += 1
            
    conn.commit()
    conn.close()
    print(f"Batch result: {count_new} new, {count_updated} updated.")

def main():
    total_standards = 0
    for i in range(1, TOTAL_PAGES + 1):
        standards = scrape_page(i)
        if standards:
            update_database(standards)
            total_standards += len(standards)
        # Be polite to the server
        time.sleep(1)
        
    print(f"Scraping completed. Total standards processed: {total_standards}")

if __name__ == "__main__":
    main()
