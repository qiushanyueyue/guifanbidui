from app.models.base import SessionLocal
from app.repositories.standard_repo import StandardRepo
from app.models.models import StandardModel

def fix_standards():
    db = SessionLocal()
    try:
        # Fix RFJ 02-2009
        # Find by the OCR'd code 'P REJ 02 — 2009' OR just insert the correct one if not found
        # Actually, let's just Upsert the CORRECT ones.
        
        # 1. RFJ 02-2009
        rfj = db.query(StandardModel).filter(StandardModel.code.like("%REJ%")).first()
        if rfj:
            print(f"Updating {rfj.code} -> RFJ 02-2009")
            db.delete(rfj)
            db.commit()
            
        new_rfj = StandardModel(
            code="RFJ 02-2009",
            name="轨道交通工程人民防空设计规范",
            status="现行",
            year="2009"
        )
        existing_rfj = db.query(StandardModel).filter_by(code="RFJ 02-2009").first()
        if not existing_rfj:
            db.add(new_rfj)
            
        # 2. DB13(J) 8330-2019
        # Update name to Chinese
        xiongan = db.query(StandardModel).filter(StandardModel.code == "DB13(J) 8330-2019").first()
        if xiongan:
            print("Updating Xiong'an standard name")
            xiongan.name = "雄安新区地下空间消防安全技术标准"
        else:
            new_xa = StandardModel(
                code="DB13(J) 8330-2019",
                name="雄安新区地下空间消防安全技术标准",
                status="现行",
                year="2019"
            )
            db.add(new_xa)
            
        db.commit()
        print("Corrections applied.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_standards()
