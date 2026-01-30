from app.models.base import SessionLocal
from app.repositories.standard_repo import StandardRepo
from app.models.models import StandardModel

def add_new_standards():
    db = SessionLocal()
    try:
        # 1. RFJ02-2009 (User specifically asked for this format, likely to match their input)
        # We previously added "RFJ 02-2009". Let's ensure both exist or alias work.
        # But for now, let's add the specific one they asked for if it doesn't exist.
        
        # User input: 轨道交通工程人民防空设计规范 RFJ02-2009
        # URL : http://www.csres.com/detail/199253.html
        
        std1 = StandardModel(
            code="RFJ02-2009", # User requested format
            name="轨道交通工程人民防空设计规范",
            status="现行",
            year="2009",
            url="http://www.csres.com/detail/199253.html"
        )
        
        # Check if exists
        curr1 = db.query(StandardModel).filter(StandardModel.code == "RFJ02-2009").first()
        if not curr1:
             db.add(std1)
             print("Added RFJ02-2009")
        else:
             curr1.url = "http://www.csres.com/detail/199253.html"
             print("Updated RFJ02-2009")

        # 2. http://www.csres.com/detail/248838.html
        # Need to know what this is. I'll infer or just add it if I can read the page?
        # Since I can't browse live easily without tool overhead, I'll assumne the user checked it.
        # Wait, I can use read_url_content!
        # But first let's create the script to fetch it or just assume I need to fetch it.
        # Let's write a script that fetches the title from the URL if possible, or I'll just use my knowledge base?
        # No, I should be precise. I will use 'requests' in this script to fetch the title.
        
        import requests
        import re
        
        url2 = "http://www.csres.com/detail/248838.html"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url2, headers=headers, timeout=10)
            resp.encoding = 'gbk' # CSRES is usually GBK
            html = resp.text
            
            # Simple regex to find title
            # <font color="#000080" face="黑体"><strong>DB11/ 995-2013</strong></font>
            # <font color="#000080" face="黑体"><strong>城市轨道交通工程设计规范</strong></font>
            
            # Let's try to extract.
            title_pat = re.compile(r'<font color="#000080" face="黑体"><strong>(.*?)</strong></font>')
            matches = title_pat.findall(html)
            
            if len(matches) >= 2:
                # usually code is first, then name
                code2 = matches[0].replace("&nbsp;", " ").strip()
                name2 = matches[1].replace("&nbsp;", " ").strip()
                
                print(f"Extracted from 248838: {code2} {name2}")
                
                std2 = StandardModel(
                    code=code2,
                    name=name2,
                    status="现行", # Assume active? Need to check status field.
                    # Status often in: <font color="green">现行</font>
                    url=url2
                )
                
                # Check status in HTML
                if "废止" in html or "作废" in html:
                    std2.status = "废止"
                elif "现行" in html:
                     std2.status = "现行"
                     
                year_match = re.search(r"-(\d{4})", code2)
                if year_match:
                    std2.year = year_match.group(1)

                curr2 = db.query(StandardModel).filter(StandardModel.code == code2).first()
                if not curr2:
                    db.add(std2)
                    print(f"Added {code2}")
                else:
                    curr2.url = url2
                    print(f"Updated {code2}")
            else:
                print("Could not extract details for 248838")
                
        except Exception as e:
            print(f"Failed to fetch 248838: {e}")

        db.commit()

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_new_standards()
