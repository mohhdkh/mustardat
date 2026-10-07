@echo off
REM Lost & Found - Docker Run Script for Windows

echo ========================================
echo Lost ^& Found - Docker Commands
echo ========================================
echo.

if "%1"=="" goto help
if "%1"=="build" goto build
if "%1"=="up" goto up
if "%1"=="dev" goto dev
if "%1"=="down" goto down
if "%1"=="logs" goto logs
if "%1"=="shell" goto shell
if "%1"=="clean" goto clean
if "%1"=="help" goto help
goto help

:build
echo Building Docker image...
docker-compose build
goto end

:up
echo Starting production server...
docker-compose up -d
echo.
echo Server running at http://localhost:8000
echo API docs at http://localhost:8000/docs
goto end

:dev
echo Starting development server with hot reload...
docker-compose --profile dev up api-dev
goto end

:down
echo Stopping containers...
docker-compose down
goto end

:logs
echo Showing logs...
docker-compose logs -f
goto end

:shell
echo Opening shell in container...
docker exec -it lostfound_api /bin/bash
goto end

:clean
echo Cleaning up Docker resources...
docker-compose down -v --rmi local
docker system prune -f
goto end

:help
echo Usage: docker-run.bat [command]
echo.
echo Commands:
echo   build   - Build Docker image
echo   up      - Start production server (detached)
echo   dev     - Start development server with hot reload
echo   down    - Stop all containers
echo   logs    - View container logs
echo   shell   - Open shell in running container
echo   clean   - Remove containers, volumes, and images
echo   help    - Show this help message
echo.
echo Examples:
echo   docker-run.bat build
echo   docker-run.bat up
echo   docker-run.bat dev
goto end

:end
