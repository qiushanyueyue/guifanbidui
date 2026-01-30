from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.models.base import Base, engine
import logging

# Initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="规范对比工具 API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}
