@echo off
echo Activating conda environment 'myenv'...
call conda activate myenv

echo Starting Lost & Found Backend Server...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
