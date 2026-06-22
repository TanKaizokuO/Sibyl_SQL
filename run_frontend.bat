@echo off
REM ==================================
REM Run Frontend Development Server
REM ==================================

echo Starting Cognitive Database Agent Frontend...
echo.

cd frontend

REM Check if node_modules exists
if not exist node_modules (
    echo Error: node_modules not found!
    echo Please run: npm install
    pause
    exit /b 1
)

echo Starting Vite development server...
echo.
echo Frontend will be available at: http://localhost:5173
echo.
echo Press Ctrl+C to stop the server
echo.

call npm run dev

cd ..
pause
