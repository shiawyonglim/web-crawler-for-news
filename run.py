#!/usr/bin/env python3
"""
Startup script for the Crawl4AI Web Crawler Flask application.
This script handles setup verification and provides helpful error messages.
"""

import os
import sys
import subprocess
import importlib.util

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'flask', 'crawl4ai', 'pandas', 'requests', 
        'beautifulsoup4', 'lxml', 'flask_cors'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - Missing")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install them using:")
        print(f"pip install -r requirements.txt")
        return False
    
    return True

def check_crawl4ai_setup():
    """Check if Crawl4AI is properly set up"""
    try:
        # Try to import crawl4ai
        from crawl4ai import AsyncWebCrawler
        print("✅ Crawl4AI import successful")
        
        # Check if browser is installed
        try:
            result = subprocess.run(
                ['crawl4ai-doctor'], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            if result.returncode == 0:
                print("✅ Crawl4AI setup verified")
                return True
            else:
                print("⚠️  Crawl4AI setup may need attention")
                print("Run: crawl4ai-setup")
                return False
        except FileNotFoundError:
            print("⚠️  Crawl4AI CLI tools not found")
            print("Run: crawl4ai-setup")
            return False
            
    except ImportError as e:
        print(f"❌ Crawl4AI import failed: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['cache', 'templates']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"✅ Directory exists: {directory}")

def main():
    """Main startup function"""
    print("🚀🤖 Crawl4AI Web Crawler - Startup Check")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    print()
    
    # Check dependencies
    print("📦 Checking dependencies...")
    if not check_dependencies():
        print("\n❌ Please install missing dependencies and try again.")
        sys.exit(1)
    print()
    
    # Check Crawl4AI setup
    print("🔧 Checking Crawl4AI setup...")
    if not check_crawl4ai_setup():
        print("\n⚠️  Crawl4AI setup may need attention, but continuing...")
    print()
    
    # Create directories
    print("📁 Creating directories...")
    create_directories()
    print()
    
    # Start the application
    print("🌐 Starting Flask application...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the application")
    print("=" * 50)
    
    try:
        # Import and run the Flask app
        from app import app
        # ✨ MODIFIED LINE: Added use_reloader and exclude_patterns
        app.run(
            debug=True, 
            host='0.0.0.0', 
            port=5000, 
            use_reloader=True, 
            exclude_patterns=['cache/*']
        )
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        print("Please check the error message above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()