import shutil
import zipfile
import os
from fastapi import UploadFile
from pathlib import Path
from typing import List
from app.core.config import settings

class FileService:
    @staticmethod
    def save_upload_file(upload_file: UploadFile, job_id: str) -> Path:
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        destination = upload_dir / f"{job_id}.zip"
        
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        return destination

    @staticmethod
    def extract_zip(zip_path: Path, job_id: str) -> List[str]:
        processing_dir = Path(settings.PROCESSING_DIR) / str(job_id)
        processing_dir.mkdir(parents=True, exist_ok=True)
        
        extracted_files = []
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Filter for .docx files only? 
                # The requirement says "breakdown of the status of each individual file"
                # so we should probably try to process everything or filter here.
                # Let's extract everything but filter returned list for likely candidates if needed.
                # For now, just extract all.
                zip_ref.extractall(processing_dir)
                
                # Recursively find files (ignoring directories)
                for file in processing_dir.rglob("*"):
                    if file.is_file() and not file.name.startswith("._") and not file.name.startswith("__MACOSX"):
                         # Store relative path or just filename? 
                         # Requirement says "identified by its original filename". 
                         # Flattening might be risky if dupe names, but simpler for this assignment.
                         # Let's keep structure but return relative paths as identifiers.
                         rel_path = file.relative_to(processing_dir)
                         extracted_files.append(str(rel_path))
                         
        except zipfile.BadZipFile:
            raise ValueError("Invalid zip file")
            
        return extracted_files

file_service = FileService()
