#!/bin/bash

echo "🚀🤖 Crawl4AI Web Crawler - Unix Launcher"
echo "================================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo

# Check if requirements are installed
echo "📦 Checking dependencies..."
if ! python3 -c "import flask" &> /dev/null; then
    echo "⚠️  Dependencies not found. Installing..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies found"
fi

echo
echo "🌐 Starting Crawl4AI Web Crawler..."
echo "📱 Open your browser and go to: http://localhost:5000"
echo "⏹️  Press Ctrl+C to stop the application"
echo "================================================"
echo

# Run the startup script
python3 run.py
