from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.models.job import JobStatus

class JobFileSchema(BaseModel):
    filename: str
    status: JobStatus
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class JobCreateResponse(BaseModel):
    job_id: UUID
    file_count: int

class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    files: List[JobFileSchema]

    class Config:
        from_attributes = True
