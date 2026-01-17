from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Any
import uuid
from pathlib import Path

from app.db.session import get_db
from app.db.models.job import Job, JobFile, JobStatus
from app.api.v1.schemas.job import JobCreateResponse, JobStatusResponse
from app.services.file_service import file_service
from app.core.config import settings
from app.tasks.celery_app import celery_app
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
    db.commit() 
    
    try:
        # 3. Save and Extract
        zip_path = file_service.save_upload_file(file, str(job_id))
        extracted_files = file_service.extract_zip(zip_path, str(job_id))
        
        if not extracted_files:
             raise HTTPException(status_code=400, detail="Zip file is empty or contains no valid files")

        # 4. Create File Records
        job_files = []
        for filename in extracted_files:
            jf = JobFile(job_id=job_id, filename=filename, status=JobStatus.PENDING)
            db.add(jf)
            job_files.append(jf)
        
        db.commit()
        
        # 5. Trigger Celery Workflow
        convert_tasks = [
            celery_app.signature("app.tasks.job_tasks.convert_file_task", args=[str(job_id), f.filename])
            for f in job_files
        ]
        
        workflow = chain(
            group(convert_tasks),
            celery_app.signature("app.tasks.job_tasks.finalize_job_task", args=[str(job_id)])
        )
        workflow.apply_async()

        return JobCreateResponse(job_id=job_id, file_count=len(job_files))

    except Exception as e:
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
        # Simple for assignment
        response.download_url = f"/api/v1/jobs/{job_id}/download"
        
    return response

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
