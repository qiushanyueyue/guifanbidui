import requests
import re
from app.models.base import SessionLocal
from app.models.models import StandardModel

def add_csres_standards():
    urls = [
        "http://www.csres.com/detail/209138.html",
        "http://www.csres.com/detail/223722.html",
        "http://www.csres.com/detail/233535.html",
        "http://www.csres.com/detail/199253.html"
    ]
    
    db = SessionLocal()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }

    try:
        for url in urls:
            print(f"Processing {url}...")
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.encoding = 'gbk'
                html = resp.text
                
                # Extract Code
                # <td width="50%" height="30">标准编号：<font size=3><strong>JGJ/T 178-2009</strong><font></td>
                code_match = re.search(r'标准编号：<font size=3><strong>(.*?)</strong>', html)
                code = code_match.group(1).strip() if code_match else None
                
                # Extract Name
                # <h3>补偿收缩混凝土应用技术规程 <a name="1"></a></h3>
                name_match = re.search(r'<h3>(.*?) <a', html)
                name = name_match.group(1).strip() if name_match else None
                
                if not code or not name:
                    # Fallback for Name if regex failed
                    # <title>JGJ/T 178-2009 补偿收缩混凝土应用技术规程 建筑工业行业标准(JG)-工标网</title>
                    title_match = re.search(r'<title>(.*?) 建筑工业行业标准', html)
                    if title_match:
                         full_title = title_match.group(1)
                         parts = full_title.split(' ', 1)
                         if len(parts) == 2:
                             if not code: code = parts[0]
                             if not name: name = parts[1]
                
                if code and name:
                    # Extract Status
                    # 标准状态：<a ...><font size=3><strong>现行</strong></font></a>
                    status = "unknown"
                    if "现行" in html:
                        status = "unknown"
                    if "废止" in html or "作废" in html:
                         status = "abolished"

                    # Extract Year
                    year_match = re.search(r"-(\d{4})", code)
                    year = year_match.group(1) if year_match else None
                    
                    # Extract Publishing Department
                    # <span class="sh14"><strong>发布部门：</strong></span></td><td class='ny_bg' >&nbsp;<span class="sh14">中华人民共和国住房和城乡建设部</span></td>
                    # Using a broader regex to capture the content in the next cell
                    dept_match = re.search(r'发布部门：</strong></span></td>\s*<td[^>]*>&nbsp;<span class="sh14">(.*?)</span>', html)
                    dept = dept_match.group(1).strip() if dept_match else None
                    
                    # Extract Implementation Date
                    # <span class="sh14"><strong>实施日期：</strong></span></td><td class='ny_bg' >&nbsp;<span class="sh14">2009-12-01\n\t\t\t\t\t</span></td>
                    impl_match = re.search(r'实施日期：</strong></span></td>\s*<td[^>]*>&nbsp;<span class="sh14">(.*?)(?:<|\n)', html)
                    impl_date = impl_match.group(1).strip() if impl_match else None

                    print(f"  Extracted: {code} | {name} | {status}")
                    
                    # DB Operations
                    existing = db.query(StandardModel).filter(StandardModel.code == code).first()
                    if not existing:
                        std = StandardModel(
                            code=code,
                            name=name,
                            status=status,
                            year=year,
                            url=url,
                            publishing_department=dept,
                            implementation_date=impl_date
                        )
                        db.add(std)
                        print(f"  -> Added to DB")
                    else:
                        existing.name = name
                        existing.status = status
                        existing.year = year
                        existing.url = url
                        existing.publishing_department = dept
                        existing.implementation_date = impl_date
                        print(f"  -> Updated in DB")
                else:
                    print(f"  FAILED to extract code/name. Code: {code}, Name: {name}")

            except Exception as e:
                print(f"  Error fetching/parsing {url}: {e}")
        
        db.commit()
        print("All Done.")

    except Exception as e:
        print(f"Global Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_csres_standards()
