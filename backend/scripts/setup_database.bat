@echo off
REM ==================================
REM Cognitive Database Agent - Database Setup Script (Windows)
REM ==================================

echo ================================
echo Database Setup Script
echo ================================
echo.

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy .env.example to .env and configure it.
    pause
    exit /b 1
)

REM Load environment variables from .env
for /f "usebackq tokens=1,2 delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%b"=="" (
        set %%a=%%b
    )
)

REM Set default values if not found
if "%DB_NAME%"=="" set DB_NAME=cognitive_db_agent
if "%DB_USER%"=="" set DB_USER=postgres
if "%DB_HOST%"=="" set DB_HOST=localhost
if "%DB_PORT%"=="" set DB_PORT=5432

echo Database: %DB_NAME%
echo User: %DB_USER%
echo Host: %DB_HOST%:%DB_PORT%
echo.

REM Check if psql is available
where psql >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================
    echo ERROR: PostgreSQL tools not found!
    echo ========================================
    echo.
    echo PostgreSQL command-line tools are not in your PATH.
    echo.
    echo FIX THIS BY:
    echo.
    echo Option 1 - Add PostgreSQL to PATH:
    echo   1. Find your PostgreSQL installation directory
    echo      Common locations:
    echo      - C:\Program Files\PostgreSQL\14\bin
    echo      - C:\Program Files\PostgreSQL\15\bin
    echo      - C:\Program Files\PostgreSQL\16\bin
    echo.
    echo   2. Add it to System PATH:
    echo      - Right-click 'This PC' ^> Properties
    echo      - Advanced system settings
    echo      - Environment Variables
    echo      - Edit 'Path' under System variables
    echo      - Add the PostgreSQL bin directory
    echo      - Click OK and restart this terminal
    echo.
    echo Option 2 - Use SQL script directly:
    echo   1. Open pgAdmin 4 (comes with PostgreSQL)
    echo   2. Create database 'cognitive_db_agent'
    echo   3. Run the SQL scripts manually:
    echo      - database\01_setup_extensions.sql
    echo      - database\02_create_tables.sql
    echo      - database\03_insert_sample_data.sql
    echo      - database\04_create_rls_policies.sql
    echo      - database\05_test_security.sql
    echo.
    echo Option 3 - Run with full path:
    echo   Run this script again after adding to PATH, or
    echo   Edit this script and replace 'psql' with full path like:
    echo   "C:\Program Files\PostgreSQL\14\bin\psql.exe"
    echo.
    pause
    exit /b 1
)

echo [OK] PostgreSQL tools found
echo.

REM Set PGPASSWORD for authentication
set PGPASSWORD=%DB_PASSWORD%

REM Check if database exists
echo Checking database connection...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "SELECT 1" >nul 2>&1

if %ERRORLEVEL% neq 0 (
    echo Cannot connect to database: %DB_NAME%
    echo Creating database...
    createdb -h %DB_HOST% -p %DB_PORT% -U %DB_USER% %DB_NAME%

    if %ERRORLEVEL% equ 0 (
        echo [OK] Database created
    ) else (
        echo.
        echo ========================================
        echo ERROR: Failed to create database
        echo ========================================
        echo.
        echo This could be because:
        echo   1. PostgreSQL service is not running
        echo   2. Wrong password in .env file
        echo   3. User '%DB_USER%' doesn't have CREATE DATABASE privilege
        echo.
        echo TO FIX:
        echo   1. Check PostgreSQL is running (services.msc)
        echo   2. Verify DB_PASSWORD in .env file
        echo   3. Try creating database manually:
        echo.
        echo Using pgAdmin 4:
        echo   - Right-click 'Databases' ^> Create ^> Database
        echo   - Name: cognitive_db_agent
        echo   - Save
        echo.
        echo Using SQL:
        echo   - Open pgAdmin Query Tool
        echo   - Run: CREATE DATABASE cognitive_db_agent;
        echo.
        echo Then run this script again.
        echo.
        pause
        exit /b 1
    )
) else (
    echo [OK] Database connection successful
)
echo.

REM Run SQL scripts in order
echo Running: Setting up extensions (pgvector, uuid-ossp)...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f database\01_setup_extensions.sql
if %ERRORLEVEL% equ 0 (
    echo [OK] Extensions setup completed
) else (
    echo [ERROR] Extensions setup failed
    echo.
    echo If you see "pgvector extension not found":
    echo   1. Download pgvector for Windows from:
    echo      https://github.com/pgvector/pgvector/releases
    echo   2. Copy vector.dll to PostgreSQL lib directory
    echo      e.g., C:\Program Files\PostgreSQL\14\lib\
    echo   3. Restart PostgreSQL service
    echo   4. Run this script again
    echo.
    pause
    exit /b 1
)
echo.

echo Running: Creating tables...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f database\02_create_tables.sql
if %ERRORLEVEL% equ 0 (
    echo [OK] Tables creation completed
) else (
    echo [ERROR] Tables creation failed
    pause
    exit /b 1
)
echo.

echo Running: Inserting sample data...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f database\03_insert_sample_data.sql
if %ERRORLEVEL% equ 0 (
    echo [OK] Sample data insertion completed
) else (
    echo [ERROR] Sample data insertion failed
    pause
    exit /b 1
)
echo.

echo Running: Creating RLS policies...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f database\04_create_rls_policies.sql
if %ERRORLEVEL% equ 0 (
    echo [OK] RLS policies creation completed
) else (
    echo [ERROR] RLS policies creation failed
    pause
    exit /b 1
)
echo.

echo Running: Testing security policies...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f database\05_test_security.sql
if %ERRORLEVEL% equ 0 (
    echo [OK] Security testing completed
) else (
    echo [ERROR] Security testing failed
    pause
    exit /b 1
)
echo.

echo ================================
echo [OK] Database setup completed!
echo ================================
echo.
echo Next steps:
echo 1. Install Python dependencies: uv pip install -r requirements.txt
echo 2. Ingest schema knowledge: python backend\scripts\ingest_knowledge.py
echo 3. Start the API server: python backend\main.py
echo 4. Try the CLI demo: python backend\cli_demo.py
echo.
pause
