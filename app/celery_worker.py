from app.tasks.celery_app import celery_app
import app.tasks.job_tasks # Explicitly import tasks to register them

# This file is used as the entry point for the celery worker
# Command: celery -A app.celery_worker.celery_app worker ...
