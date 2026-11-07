@echo off
title Personal Finance Tracker - Streamlit Frontend
echo ========================================================
echo   Starting Personal Finance Tracker Streamlit UI...
echo ========================================================
echo Streamlit App URL: http://localhost:8501
echo ========================================================
cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run frontend.py
pause
