from app.models.base import SessionLocal
from app.models.models import StandardModel

def add_screenshot_standard():
    db = SessionLocal()
    try:
        # Standard from screenshot
        code = "DB/T 29-176-2016"
        name = "天津市预防混凝土碱骨料反应技术规程"
        
        std = StandardModel(
            code=code,
            name=name,
            status="unknown",
            year="2016",
            publishing_department="天津市城乡建设委员会",
            implementation_date="2016-10-01",
            url="" # No URL provided in screenshot
        )
        
        # Check if exists
        existing = db.query(StandardModel).filter(StandardModel.code == code).first()
        if not existing:
            db.add(std)
            print(f"Added {code} - {name}")
        else:
            # Update fields if it exists
            existing.name = name
            existing.status = "unknown"
            existing.year = "2016"
            existing.publishing_department = "天津市城乡建设委员会"
            existing.implementation_date = "2016-10-01"
            print(f"Updated {code} - {name}")
            
        db.commit()
    except Exception as e:
        print(f"Error adding standard: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_screenshot_standard()
