@echo off
echo ===================================================
echo Starting Docx-to-PDF Service...
echo This will download and setup the Database, Redis, and App for you.
echo It might take a few minutes the first time.
echo ===================================================

docker-compose up --build

pause
