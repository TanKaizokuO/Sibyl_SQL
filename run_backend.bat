@echo off
REM ==================================
REM Start Cognitive Database Agent - Backend API
REM ==================================

echo ================================
echo Starting Backend API Server
echo ================================
echo.
echo Backend will run at: http://localhost:8000
echo API docs will be at: http://localhost:8000/docs
echo.

REM Run from project root with PYTHONPATH set
set PYTHONPATH=%CD%

uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
