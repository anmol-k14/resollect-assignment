import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Docx to PDF Converter"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/docx_db")
    
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    STORAGE_DIR: str = "/app/storage"
    UPLOAD_DIR: str = f"{STORAGE_DIR}/uploads"
    PROCESSING_DIR: str = f"{STORAGE_DIR}/processing"
    OUTPUT_DIR: str = f"{STORAGE_DIR}/outputs"

    class Config:
        case_sensitive = True

settings = Settings()
