from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.models.base import Base

class StandardModel(Base):
    __tablename__ = "standards"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # distinct code, e.g. GB 50016-2014
    name = Column(String)
    status = Column(String)
    url = Column(String)
    year = Column(String, nullable=True)
    publishing_department = Column(String, nullable=True) # New column
    implementation_date = Column(String, nullable=True)   # New column
    last_updated = Column(DateTime, default=datetime.utcnow)
