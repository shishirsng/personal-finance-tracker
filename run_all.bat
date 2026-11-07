@echo off
title Launch Personal Finance Tracker (Backend + Frontend)
echo ========================================================
echo   Launching Personal Finance Tracker...
echo ========================================================
echo 1. Launching FastAPI Backend on port 8000...
start "Finance Backend (FastAPI)" cmd /k ""%~dp0run_backend.bat""
timeout /t 3 /nobreak >nul
echo 2. Launching Streamlit UI on port 8501...
start "Finance UI (Streamlit)" cmd /k ""%~dp0run_frontend.bat""
echo ========================================================
echo Both services started!
echo - Frontend: http://localhost:8501
echo - Backend:  http://localhost:8000/docs
echo ========================================================
