@echo off
echo ========================================
echo    Equity Research Generator
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies if needed
echo Checking dependencies...
pip install -r backend\requirements.txt -q

REM Check for API key
if "%ANTHROPIC_API_KEY%"=="" (
    echo.
    echo WARNING: ANTHROPIC_API_KEY not set!
    echo AI analysis will use fallback mode.
    echo.
    echo To enable AI analysis, run:
    echo   set ANTHROPIC_API_KEY=your_key_here
    echo.
)

REM Create data directory
if not exist "data" mkdir data

echo.
echo Starting server on http://localhost:8000
echo API docs at http://localhost:8000/docs
echo.
echo Open frontend/index.html in your browser to use the app
echo Press Ctrl+C to stop the server
echo.

cd backend
python main.py
