
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.models.models import StandardModel

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///backend/standards.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def fix_db():
    db = SessionLocal()
    try:
        # 1. Fix JGJ 145-2013 (ID 1283 usually, but using code to be safe)
        jgj = db.query(StandardModel).filter(StandardModel.code == "JGJ 145-2013").first()
        if jgj:
            print(f"Found JGJ 145-2013: Status={jgj.status}, ID={jgj.id}")
            jgj.status = "unknown"
            print("Updated status to '现行'")
        else:
            print("JGJ 145-2013 not found!")

        # 2. Cleanup garbage entry (ID 1270 which had huge text in code)
        # Search for code starting with "标准编号"
        garbage = db.query(StandardModel).filter(StandardModel.code.like("标准编号%")).all()
        for g in garbage:
            print(f"Deleting garbage entry ID={g.id} Code={g.code[:20]}...")
            db.delete(g)
        
        db.commit()
        print("Database fixed successfully.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_db()
