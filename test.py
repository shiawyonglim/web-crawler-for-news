import os
import json
import asyncio
import pandas as pd
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import tempfile
import threading
from urllib.parse import urljoin, urlparse
import re

app = Flask(__name__)
CORS(app)

# Global variables to store crawl results and status
crawl_results = []
crawl_status = {"is_running": False, "progress": 0, "total_pages": 0, "current_page": 0}
crawl_lock = threading.Lock()

# Cache directory for storing previous downloads
CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def extract_links_from_html(html_content, base_url, max_links=30):
    """Extract up to max_links from HTML content"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all links
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Convert relative URLs to absolute
            if href.startswith('/'):
                full_url = urljoin(base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                continue
            
            # Only include links from the same domain
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                links.append(full_url)
        
        # Remove duplicates and limit to max_links
        unique_links = list(dict.fromkeys(links))[:max_links]
        return unique_links
    except Exception as e:
        print(f"Error extracting links: {e}")
        return []

async def crawl_website(homepage_url, max_pages=30):
    """Main crawling function using Crawl4AI"""
    global crawl_results, crawl_status
    
    try:
        # Reset results and status
        crawl_results = []
        crawl_status = {
            "is_running": True, 
            "progress": 0, 
            "total_pages": max_pages, 
            "current_page": 0
        }
        
        # Configure the crawler
        browser_config = {
            "headless": True,
            "verbose": False
        }
        
        # Content filter for better quality extraction
        content_filter = PruningContentFilter(
            threshold=0.45,
            threshold_type="dynamic",
            min_word_threshold=10
        )
        
        # Markdown generator with content filtering
        markdown_generator = DefaultMarkdownGenerator(content_filter=content_filter)
        
        # Dispatcher for managing concurrent requests
        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=80.0,
            check_interval=1.0,
            max_session_permit=5
        )
        
        # First, crawl the homepage to extract links
        print(f"Starting crawl of homepage: {homepage_url}")
        
        async with AsyncWebCrawler() as crawler:
            # Crawl homepage first
            homepage_config = CrawlerRunConfig(
                cache_mode=CacheMode.ENABLED,
                markdown_generator=markdown_generator,
                screenshot=False,
                excluded_tags=["nav", "footer", "header", "aside"]
            )
            
            homepage_result = await crawler.arun(
                url=homepage_url,
                config=homepage_config
            )
            
            if not homepage_result.success:
                raise Exception(f"Failed to crawl homepage: {homepage_result.error_message}")
            
            # Extract links from homepage
            links = extract_links_from_html(homepage_result.html, homepage_url, max_pages)
            
            if not links:
                raise Exception("No links found on homepage")
            
            # Add homepage to results
            crawl_results.append({
                "url": homepage_url,
                "title": homepage_result.metadata.get("title", "Homepage"),
                "content": homepage_result.markdown.fit_markdown or homepage_result.markdown.raw_markdown,
                "word_count": len((homepage_result.markdown.fit_markdown or homepage_result.markdown.raw_markdown).split()),
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            })
            
            crawl_status["current_page"] = 1
            crawl_status["progress"] = (1 / (len(links) + 1)) * 100
            
            # Configure for sub-pages
            subpage_config = CrawlerRunConfig(
                cache_mode=CacheMode.ENABLED,
                markdown_generator=markdown_generator,
                screenshot=False,
                excluded_tags=["nav", "footer", "header", "aside"],
                word_count_threshold=50
            )
            
            # Crawl sub-pages
            print(f"Found {len(links)} links, starting sub-page crawl...")
            
            for i, link in enumerate(links):
                try:
                    print(f"Crawling {i+1}/{len(links)}: {link}")
                    
                    result = await crawler.arun(
                        url=link,
                        config=subpage_config
                    )
                    
                    if result.success:
                        crawl_results.append({
                            "url": link,
                            "title": result.metadata.get("title", f"Page {i+1}"),
                            "content": result.markdown.fit_markdown or result.markdown.raw_markdown,
                            "word_count": len((result.markdown.fit_markdown or result.markdown.raw_markdown).split()),
                            "timestamp": datetime.now().isoformat(),
                            "status": "success"
                        })
                    else:
                        crawl_results.append({
                            "url": link,
                            "title": "Error",
                            "content": f"Failed to crawl: {result.error_message}",
                            "word_count": 0,
                            "timestamp": datetime.now().isoformat(),
                            "status": "error"
                        })
                    
                    crawl_status["current_page"] = i + 2
                    crawl_status["progress"] = ((i + 2) / (len(links) + 1)) * 100
                    
                except Exception as e:
                    print(f"Error crawling {link}: {e}")
                    crawl_results.append({
                        "url": link,
                        "title": "Error",
                        "content": f"Exception: {str(e)}",
                        "word_count": 0,
                        "timestamp": datetime.now().isoformat(),
                        "status": "error"
                    })
            
            # Save results to cache
            save_to_cache(homepage_url, crawl_results)
            
            print(f"Crawl completed! Processed {len(crawl_results)} pages")
            
    except Exception as e:
        print(f"Crawl error: {e}")
        crawl_results.append({
            "url": homepage_url,
            "title": "Crawl Error",
            "content": f"Main crawl failed: {str(e)}",
            "word_count": 0,
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        })
    
    finally:
        crawl_status["is_running"] = False
        crawl_status["progress"] = 100

def save_to_cache(homepage_url, results):
    """Save crawl results to cache"""
    try:
        # Create a safe filename from the URL
        domain = urlparse(homepage_url).netloc
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_{timestamp}.json"
        filepath = os.path.join(CACHE_DIR, filename)
        
        # Save results
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "homepage_url": homepage_url,
                "crawl_timestamp": timestamp,
                "total_pages": len(results),
                "results": results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to cache: {filepath}")
        
    except Exception as e:
        print(f"Error saving to cache: {e}")

def load_from_cache(homepage_url):
    """Load previous crawl results from cache"""
    try:
        domain = urlparse(homepage_url).netloc
        
        # Find the most recent cache file for this domain
        cache_files = [f for f in os.listdir(CACHE_DIR) if f.startswith(domain)]
        
        if not cache_files:
            return None
        
        # Get the most recent file
        latest_file = max(cache_files, key=lambda x: os.path.getctime(os.path.join(CACHE_DIR, x)))
        filepath = os.path.join(CACHE_DIR, latest_file)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
        
        return cached_data
        
    except Exception as e:
        print(f"Error loading from cache: {e}")
        return None

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/crawl', methods=['POST'])
def start_crawl():
    """Start a new crawl"""
    global crawl_status
    
    if crawl_status["is_running"]:
        return jsonify({"error": "Crawl already in progress"}), 400
    
    data = request.get_json()
    homepage_url = data.get('homepage_url')
    max_pages = data.get('max_pages', 30)
    
    if not homepage_url:
        return jsonify({"error": "Homepage URL is required"}), 400
    
    # Check if we have cached results
    cached_results = load_from_cache(homepage_url)
    if cached_results:
        return jsonify({
            "message": "Found cached results",
            "cached_data": cached_results,
            "use_cache": True
        })
    
    # Start crawling in a separate thread
    def run_crawl():
        asyncio.run(crawl_website(homepage_url, max_pages))
    
    thread = threading.Thread(target=run_crawl)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "message": "Crawl started",
        "homepage_url": homepage_url,
        "max_pages": max_pages
    })

@app.route('/api/status')
def get_status():
    """Get current crawl status"""
    return jsonify(crawl_status)

@app.route('/api/results')
def get_results():
    """Get crawl results"""
    return jsonify({
        "results": crawl_results,
        "total_pages": len(crawl_results),
        "successful_pages": len([r for r in crawl_results if r["status"] == "success"]),
        "error_pages": len([r for r in crawl_results if r["status"] == "error"])
    })

@app.route('/api/download/csv')
def download_csv():
    """Download results as CSV"""
    if not crawl_results:
        return jsonify({"error": "No results to download"}), 400
    
    try:
        # Prepare data for CSV
        csv_data = []
        for result in crawl_results:
            csv_data.append({
                "URL": result["url"],
                "Title": result["title"],
                "Content": result["content"][:1000] + "..." if len(result["content"]) > 1000 else result["content"],
                "Word Count": result["word_count"],
                "Status": result["status"],
                "Timestamp": result["timestamp"]
            })
        
        # Create DataFrame and CSV
        df = pd.DataFrame(csv_data)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            df.to_csv(tmp.name, index=False, encoding='utf-8')
            tmp_path = tmp.name
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crawl_results_{timestamp}.csv"
        
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        return jsonify({"error": f"Error creating CSV: {str(e)}"}), 500

@app.route('/api/cache/list')
def list_cache():
    """List all cached crawl results"""
    try:
        cache_files = []
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(CACHE_DIR, filename)
                file_info = {
                    "filename": filename,
                    "size": os.path.getsize(filepath),
                    "created": datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
                    "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                }
                cache_files.append(file_info)
        
        # Sort by creation time (newest first)
        cache_files.sort(key=lambda x: x["created"], reverse=True)
        
        return jsonify({"cache_files": cache_files})
        
    except Exception as e:
        return jsonify({"error": f"Error listing cache: {str(e)}"}), 500

@app.route('/api/cache/load/<filename>')
def load_cache_file(filename):
    """Load a specific cache file"""
    try:
        filepath = os.path.join(CACHE_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "Cache file not found"}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
        
        return jsonify(cached_data)
        
    except Exception as e:
        return jsonify({"error": f"Error loading cache file: {str(e)}"}), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all cached results"""
    try:
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(CACHE_DIR, filename)
                os.remove(filepath)
        
        return jsonify({"message": "Cache cleared successfully"})
        
    except Exception as e:
        return jsonify({"error": f"Error clearing cache: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
