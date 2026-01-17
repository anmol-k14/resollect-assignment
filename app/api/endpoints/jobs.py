from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Any
import uuid
import os

from app.core.database import get_db
from app.models.job import Job, JobFile, JobStatus
from app.schemas.job import JobCreateResponse, JobStatusResponse
from app.services.file_service import file_service
from app.core.config import settings
from app.worker import celery_app
from celery import chain, group

router = APIRouter()

@router.post("/", response_model=JobCreateResponse, status_code=202)
def create_job(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> Any:
    # 1. Validation
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only zip files are allowed")

    # 2. Create Job Record
    job_id = uuid.uuid4()
    job = Job(id=job_id, status=JobStatus.PENDING)
    db.add(job)
    db.commit() # Commit via DB to get ID if we relied on DB gen (but we generated uuid)
    
    try:
        # 3. Save and Extract
        zip_path = file_service.save_upload_file(file, str(job_id))
        extracted_files = file_service.extract_zip(zip_path, str(job_id))
        
        if not extracted_files:
             raise HTTPException(status_code=400, detail="Zip file is empty or contains no valid files")

        # 4. Create File Records
        job_files = []
        for filename in extracted_files:
            # Filter for docx only? Requirement says "converts DOCX files". 
            # We should mark non-docx as ignored or failed immediately?
            # Or just let worker handle it. Let's let worker handle validation to keep API fast.
            # actually, better to fail fast if we can, but async is better.
            jf = JobFile(job_id=job_id, filename=filename, status=JobStatus.PENDING)
            db.add(jf)
            job_files.append(jf)
        
        db.commit()
        
        # 5. Trigger Celery Workflow
        # workflow: group(convert_file) -> finalize_job
        # We use signatures by name to avoid import circulars or issues if worker code isn't fully ready
        
        convert_tasks = [
            celery_app.signature("app.worker.convert_file_task", args=[str(job_id), f.filename])
            for f in job_files
        ]
        
        workflow = chain(
            group(convert_tasks),
            celery_app.signature("app.worker.finalize_job_task", args=[str(job_id)])
        )
        workflow.apply_async()

        return JobCreateResponse(job_id=job_id, file_count=len(job_files))

    except Exception as e:
        # Cleanup if something failed explicitly before async safely
        # db.rollback() # (handled by session manager usually but good to be safe)
        # settings job to FAILED?
        job.status = JobStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> Any:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    response = JobStatusResponse.model_validate(job)
    
    if job.status == JobStatus.COMPLETED:
        # Assuming simple running locally for now. In prod, this would be a real domain.
        # "http://localhost:8000/api/v1/jobs/{job_id}/download"
        # We can construct it from request base url if we had Request object, but hardcoding for simplicity of assignment
        response.download_url = f"/api/v1/jobs/{job_id}/download"
        
    return response

from fastapi.responses import FileResponse

@router.get("/{job_id}/download")
def download_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
         raise HTTPException(status_code=404, detail="Job not found")
         
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job is not completed yet")
        
    zip_path = Path(settings.OUTPUT_DIR) / f"{job_id}.zip"
    
    if not zip_path.exists():
         raise HTTPException(status_code=404, detail="Download file not found")
         
    return FileResponse(
        path=zip_path,
        filename=f"converted_{job_id}.zip",
        media_type="application/zip"
    )
