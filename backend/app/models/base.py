from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

# Adapt for Vercel: Use /tmp for SQLite database if running in Vercel environment
# Vercel file system is read-only except for /tmp
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/standards.db"
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./standards.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
