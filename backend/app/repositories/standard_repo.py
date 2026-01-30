from sqlalchemy.orm import Session
from app.models.models import StandardModel
from app.models.schemas import SearchResult
from datetime import datetime

class StandardRepo:
    @staticmethod
    def get_by_code(db: Session, code: str):
        return db.query(StandardModel).filter(StandardModel.code == code).first()

    @staticmethod
    def create_or_update(db: Session, data: SearchResult, year: str = None):
        existing = StandardRepo.get_by_code(db, data.code)
        if existing:
            existing.name = data.name
            existing.status = data.status
            existing.url = data.url
            if year:
                existing.year = year
            existing.last_updated = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_std = StandardModel(
                code=data.code,
                name=data.name,
                status=data.status,
                url=data.url,
                year=year
            )
            db.add(new_std)
            db.commit()
            db.refresh(new_std)
            return new_std
