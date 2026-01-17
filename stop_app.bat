@echo off
echo ===================================================
echo Stopping Docx-to-PDF Service...
echo This will stop and remove the containers.
echo ===================================================

docker-compose down

echo ===================================================
echo Application stopped successfully.
echo ===================================================
pause
