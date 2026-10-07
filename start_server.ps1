# PowerShell script to start the Lost & Found server
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found. Create .venv and install requirements first."
    exit 1
}

# Avoid collisions with a machine-level DEBUG environment variable.
$env:DEBUG = "true"
$env:PYTHONUTF8 = "1"

Write-Host "Starting Lost & Found at http://127.0.0.1:8000" -ForegroundColor Green
& $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
