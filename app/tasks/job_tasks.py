import subprocess
import zipfile
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.job import Job, JobFile, JobStatus
from app.tasks.celery_app import celery_app
from datetime import datetime

def get_db_session():
    return SessionLocal()

@celery_app.task(bind=True, name="app.tasks.job_tasks.convert_file_task")
def convert_file_task(self, job_id: str, filename: str):
    db: Session = get_db_session()
    try:
        # Update status to IN_PROGRESS
        job_file = db.query(JobFile).filter(JobFile.job_id == job_id, JobFile.filename == filename).first()
        if not job_file:
            print(f"File record not found: {job_id} / {filename}")
            return # Should probably retry or log error
        
        job_file.status = JobStatus.IN_PROGRESS
        db.commit()

        input_path = Path(settings.PROCESSING_DIR) / job_id / filename
        output_dir = Path(settings.OUTPUT_DIR) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        # Run LibreOffice conversion
        cmd = [
            "soffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(input_path)
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            raise Exception(f"LibreOffice failed: {process.stderr}")

        # Verify output file exists
        base_name = Path(filename).stem
        expected_output = output_dir / f"{base_name}.pdf"
        
        if not expected_output.exists():
             raise Exception(f"Output PDF not found at {expected_output}")

        job_file.status = JobStatus.COMPLETED
        db.commit()
        return {"filename": filename, "status": "COMPLETED"}

    except Exception as e:
        print(f"Conversion failed: {e}")
        if job_file:
            job_file.status = JobStatus.FAILED
            job_file.error_message = str(e)
            db.commit()
        return {"filename": filename, "status": "FAILED", "error": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="app.tasks.job_tasks.finalize_job_task")
def finalize_job_task(self, results, job_id: str):
    db: Session = get_db_session()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        # Zip the outputs
        source_dir = Path(settings.OUTPUT_DIR) / job_id
        zip_path = Path(settings.OUTPUT_DIR) / f"{job_id}.zip"
        
        if source_dir.exists():
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for file_path in source_dir.rglob("*.pdf"):
                    zip_ref.write(file_path, arcname=file_path.name)
        
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        print(f"Finalization failed: {e}")
        if job:
            job.status = JobStatus.FAILED 
            db.commit()
    finally:
        db.close()
