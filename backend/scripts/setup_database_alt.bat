@echo off
REM ==================================
REM Alternative Database Setup - Using Python
REM ==================================
REM This script sets up the database using Python instead of psql
REM Use this if PostgreSQL command-line tools are not in PATH
REM ==================================

echo ================================
echo Database Setup (Python Method)
echo ================================
echo.

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy .env.example to .env and configure it.
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo Warning: Virtual environment not found
    echo Make sure you have psycopg2 installed: pip install psycopg2-binary
)
echo.

REM Run Python setup script
echo Running Python database setup script...
echo.

python backend\scripts\setup_database_python.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ================================
    echo [OK] Database setup completed!
    echo ================================
) else (
    echo.
    echo [ERROR] Database setup failed
    echo Check the error messages above
)
echo.
pause
