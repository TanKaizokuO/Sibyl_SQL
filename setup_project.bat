@echo off
REM ==================================
REM Cognitive Database Agent - Complete Project Setup (Windows)
REM ==================================
REM This script sets up the entire project including:
REM - Python virtual environment with uv
REM - Python dependencies
REM - PostgreSQL database
REM - Knowledge base ingestion
REM ==================================

echo ========================================
echo Cognitive Database Agent - Project Setup
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env and add your:
    echo   - GOOGLE_API_KEY
    echo   - DB_PASSWORD
    echo.
    echo Press any key after editing .env...
    pause >nul
    echo.
)

REM Check if uv is installed
where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: uv is not installed!
    echo.
    echo Install uv with: pip install uv
    echo Or visit: https://github.com/astral-sh/uv
    pause
    exit /b 1
)

echo [OK] uv is installed
echo.

REM Create virtual environment with uv
echo Creating virtual environment with uv...
if not exist .venv (
    uv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo.

REM Install Python dependencies with uv
echo Installing Python dependencies with uv...
uv pip install -r requirements.txt
if %ERRORLEVEL% equ 0 (
    echo [OK] Python dependencies installed
) else (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo.

REM Setup database
echo Setting up PostgreSQL database...
call backend\scripts\setup_database.bat
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Database setup failed
    pause
    exit /b 1
)
echo.

REM Ingest knowledge base
echo.
echo Ingesting schema knowledge into RAG system...
python backend\scripts\ingest_knowledge.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Knowledge ingestion failed
    pause
    exit /b 1
)
echo.

REM Setup frontend
echo Setting up frontend...
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
    if %ERRORLEVEL% equ 0 (
        echo [OK] Frontend dependencies installed
    ) else (
        echo [ERROR] Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
) else (
    echo [OK] Frontend dependencies already installed
)
cd ..
echo.

echo ========================================
echo [OK] Project Setup Complete!
echo ========================================
echo.
echo You can now run the application:
echo.
echo Backend:
echo   1. Activate virtual environment: .venv\Scripts\activate.bat
echo   2. Run API server: python backend\main.py
echo   3. Or try CLI demo: python backend\cli_demo.py
echo.
echo Frontend:
echo   1. cd frontend
echo   2. npm run dev
echo.
echo API Documentation: http://localhost:8000/docs
echo Frontend: http://localhost:5173
echo.
pause
