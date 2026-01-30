import sys
import os
sys.path.append("/Users/qiushanyueyue/Documents/work/规范对比/backend")

from app.database import SessionLocal
from app.models.models import Standard
from sqlalchemy import select

def check_db_standard():
    db = SessionLocal()
    try:
        query = "GB 51348-2019"
        stmt = select(Standard).where(Standard.code.contains("51348"))
        results = db.execute(stmt).scalars().all()
        
        print(f"Checking DB for '51348': found {len(results)} results")
        for res in results:
            print(f"  - ID: {res.id}, Code: '{res.code}', Name: '{res.name}'")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_db_standard()
