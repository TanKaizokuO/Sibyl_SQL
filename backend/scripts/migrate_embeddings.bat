@echo off
REM ==================================
REM Migrate Database to Local Embeddings
REM ==================================

echo ================================
echo Migrating to Local Embeddings
echo ================================
echo.
echo This will:
echo   1. Clear existing Gemini embeddings (768D)
echo   2. Update vector dimension to 384D
echo   3. Recreate vector index
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo Running migration script...
echo.

uv run python backend\scripts\setup_database_python.py --migration

if %ERRORLEVEL% equ 0 (
    echo.
    echo ================================
    echo [OK] Migration completed!
    echo ================================
    echo.
    echo Next steps:
    echo   1. Install sentence-transformers: uv pip install sentence-transformers
    echo   2. Run knowledge ingestion: uv run python backend\scripts\ingest_knowledge.py
) else (
    echo.
    echo [ERROR] Migration failed
)
echo.
pause
