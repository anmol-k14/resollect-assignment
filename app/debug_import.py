import sys
import os
sys.path.append('/app')
try:
    print("Attempting to import app.tasks.job_tasks...")
    import app.tasks.job_tasks
    print("Import successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Import failed: {e}")
