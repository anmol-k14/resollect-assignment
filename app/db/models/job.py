import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    files = relationship("JobFile", back_populates="job")

class JobFile(Base):
    __tablename__ = "job_files"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    filename = Column(String)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    error_message = Column(String, nullable=True)

    job = relationship("Job", back_populates="files")
