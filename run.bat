@echo off
echo 🚀🤖 Crawl4AI Web Crawler - Windows Launcher
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Check if requirements are installed
echo 📦 Checking dependencies...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Dependencies not found. Installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
    echo ✅ Dependencies installed
) else (
    echo ✅ Dependencies found
)

echo.
echo 🌐 Starting Crawl4AI Web Crawler...
echo 📱 Open your browser and go to: http://localhost:5000
echo ⏹️  Press Ctrl+C to stop the application
echo ================================================
echo.

REM Run the startup script
python run.py

pause
