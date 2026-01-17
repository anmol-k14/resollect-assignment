from fastapi import FastAPI
from app.core.config import settings
from app.api.api import api_router
from app.core.database import engine, Base
# Import models to ensure they are registered with Base
from app.models import job

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to Docx to PDF Converter Service"}
