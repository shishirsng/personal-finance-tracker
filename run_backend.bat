@echo off
title Personal Finance Tracker - FastAPI Backend
echo ========================================================
echo   Starting Personal Finance Tracker FastAPI Backend...
echo ========================================================
echo API Swagger Docs: http://localhost:8000/docs
echo Health Check:     http://localhost:8000/health/live
echo ========================================================
cd /d "%~dp0"
call .venv\Scripts\activate.bat
uvicorn app.main:app --port 8000 --reload
pause
