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
from collections import deque
from bs4 import BeautifulSoup

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
        
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            if href.startswith('/'):
                full_url = urljoin(base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                continue
            
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                links.append(full_url)
        
        unique_links = list(dict.fromkeys(links))
        return unique_links
    except Exception as e:
        print(f"Error extracting links: {e}")
        return []

async def crawl_website(homepage_url, max_pages=30):
    """Performs a two-level crawl: homepage + links found on homepage."""
    global crawl_results, crawl_status
    
    try:
        crawl_results = []
        crawl_status.update({
            "is_running": True, "progress": 0, "total_pages": 0, "current_page": 0
        })

        content_filter = PruningContentFilter(threshold=0.45, threshold_type="dynamic", min_word_threshold=10)
        markdown_generator = DefaultMarkdownGenerator(content_filter=content_filter)
        config = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED, markdown_generator=markdown_generator, screenshot=False,
            excluded_tags=["nav", "footer", "header", "aside"], word_count_threshold=50
        )
        
        # --- Stage 1: Crawl the homepage ---
        print(f"Crawling homepage: {homepage_url}")
        homepage_result = None
        links_to_crawl = []
        
        try:
            async with AsyncWebCrawler() as crawler:
                homepage_result = await crawler.arun(url=homepage_url, config=config)
            
            if homepage_result.success:
                crawl_results.append({
                    "url": homepage_url,
                    "title": homepage_result.metadata.get("title", "No Title"),
                    "content": homepage_result.markdown.fit_markdown or homepage_result.markdown.raw_markdown,
                    "full_html": homepage_result.html,
                    "word_count": len((homepage_result.markdown.fit_markdown or homepage_result.markdown.raw_markdown).split()),
                    "timestamp": datetime.now().isoformat(), "status": "success"
                })
                # Extract links for the next level, respecting max_pages
                links_to_crawl = extract_links_from_html(homepage_result.html, homepage_url)[:max_pages - 1]
            else:
                crawl_results.append({
                    "url": homepage_url, "title": "Error", "content": f"Failed to crawl: {homepage_result.error_message}",
                    "full_html": "", "word_count": 0, "timestamp": datetime.now().isoformat(), "status": "error"
                })
        except Exception as e:
            print(f"Critical error on homepage {homepage_url}: {e}")
            crawl_results.append({
                "url": homepage_url, "title": "Critical Error", "content": f"Exception: {str(e)}",
                "full_html": "", "word_count": 0, "timestamp": datetime.now().isoformat(), "status": "error"
            })
        
        # --- Stage 2: Crawl the extracted links ---
        total_pages_to_crawl = len(links_to_crawl) + 1
        crawl_status["total_pages"] = total_pages_to_crawl
        crawl_status["current_page"] = 1
        crawl_status["progress"] = (1 / total_pages_to_crawl) * 100

        for i, link in enumerate(links_to_crawl):
            print(f"Crawling sub-page {i + 1}/{len(links_to_crawl)}: {link}")
            crawl_status["current_page"] = i + 2
            crawl_status["progress"] = ((i + 2) / total_pages_to_crawl) * 100
            
            try:
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=link, config=config)
                
                if result.success:
                    crawl_results.append({
                        "url": link,
                        "title": result.metadata.get("title", "No Title"),
                        "content": result.markdown.fit_markdown or result.markdown.raw_markdown,
                        "full_html": result.html,
                        "word_count": len((result.markdown.fit_markdown or result.markdown.raw_markdown).split()),
                        "timestamp": datetime.now().isoformat(), "status": "success"
                    })
                else:
                    crawl_results.append({
                        "url": link, "title": "Error", "content": f"Failed to crawl: {result.error_message}",
                        "full_html": "", "word_count": 0, "timestamp": datetime.now().isoformat(), "status": "error"
                    })
            except Exception as e:
                print(f"Critical error crawling {link}: {e}")
                crawl_results.append({
                    "url": link, "title": "Critical Error", "content": f"Exception: {str(e)}",
                    "full_html": "", "word_count": 0, "timestamp": datetime.now().isoformat(), "status": "error"
                })

        save_to_cache(homepage_url, crawl_results)
        print(f"Two-level crawl completed! Processed {len(crawl_results)} pages.")
            
    except Exception as e:
        print(f"Crawl error: {e}")
        crawl_results.append({
            "url": homepage_url, "title": "Crawl Error", "content": f"Main crawl failed: {str(e)}",
            "full_html": "", "word_count": 0, "timestamp": datetime.now().isoformat(), "status": "error"
        })
    
    finally:
        crawl_status["is_running"] = False
        crawl_status["progress"] = 100


async def crawl_website_list():
    """Crawls a predefined list of websites (shallow crawl)"""
    global crawl_results, crawl_status
    urls = read_website_list()
    if not urls:
        crawl_status['is_running'] = False
        return

    crawl_results = []
    crawl_status = {
        "is_running": True,
        "progress": 0,
        "total_pages": len(urls),
        "current_page": 0
    }

    for i, url in enumerate(urls):
        crawl_status["current_page"] = i + 1
        crawl_status["progress"] = ((i + 1) / len(urls)) * 100
        print(f"Crawling {i+1}/{len(urls)}: {url}")
        
        try:
            # Start a fresh crawler for each site for added stability
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.ENABLED,
                        excluded_tags=["nav", "footer", "header", "aside"],
                        word_count_threshold=50
                    )
                )
            
            if result.success:
                crawl_results.append({
                    "url": url,
                    "title": result.metadata.get("title", "No Title"),
                    "content": result.markdown.fit_markdown or result.markdown.raw_markdown,
                    "full_html": result.html,
                    "word_count": len((result.markdown.fit_markdown or result.markdown.raw_markdown).split()),
                    "timestamp": datetime.now().isoformat(),
                    "status": "success"
                })
            else:
                crawl_results.append({
                    "url": url, "title": "Error", "content": f"Failed to crawl: {result.error_message}",
                    "full_html": "", "word_count": 0, "timestamp": datetime.now().isoformat(), "status": "error"
                })
        except Exception as e:
            print(f"Critical error crawling {url}: {e}. This might be a browser crash.")
            crawl_results.append({
                "url": url, "title": "Critical Error", "content": f"Exception: {str(e)}",
                "full_html": "", "word_count": 0, "timestamp": datetime.now().isoformat(), "status": "error"
            })

    crawl_status["is_running"] = False
    crawl_status["progress"] = 100
    print("Batch crawl completed!")


def read_website_list():
    """Reads the list of websites from the text file"""
    try:
        with open("list_of_website.txt", "r") as f:
            lines = f.readlines()
        
        urls = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = re.search(r'https?://[^\s]+', line)
            if match:
                urls.append(match.group(0))
        
        return urls
    except FileNotFoundError:
        print("Error: list_of_website.txt not found!")
        return []
    except Exception as e:
        print(f"Error reading website list: {e}")
        return []


def save_to_cache(homepage_url, results):
    """Save crawl results to cache"""
    try:
        domain = urlparse(homepage_url).netloc
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{domain}_{timestamp}.json"
        filepath = os.path.join(CACHE_DIR, filename)
        
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
        
        cache_files = [f for f in os.listdir(CACHE_DIR) if f.startswith(domain)]
        
        if not cache_files:
            return None
        
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
    
    cached_results = load_from_cache(homepage_url)
    if cached_results:
        return jsonify({
            "message": "Found cached results",
            "cached_data": cached_results,
            "use_cache": True
        })
    
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

@app.route('/api/crawl/batch', methods=['POST'])
def start_batch_crawl():
    """Starts crawling all websites from the list"""
    global crawl_status
    if crawl_status["is_running"]:
        return jsonify({"error": "A crawl is already in progress"}), 400

    urls = read_website_list()
    if not urls:
        return jsonify({"error": "list_of_website.txt is empty or not found"}), 400

    thread = threading.Thread(target=lambda: asyncio.run(crawl_website_list()))
    thread.daemon = True
    thread.start()

    return jsonify({
        "message": "Batch crawl started",
        "total_websites": len(urls)
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

def clean_content_for_csv(html_content):
    """
    A robust function to clean text for CSV export by removing HTML,
    markdown, and extra whitespace.
    """
    if not html_content:
        return ""

    # 1. Use BeautifulSoup to get clean text and remove HTML tags
    # The separator=' ' ensures words don't get smashed together
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator=' ')

    # 2. Remove Markdown-like syntax
    # Remove links but keep the link text, e.g., [Google](...) -> Google
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove images, e.g., ![alt text](...)
    text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', text)
    # Remove markdown for bold, italics, headers, lists, etc.
    text = re.sub(r'(\*\*|__|\*|_|#+\s*|`|>|- )', '', text)

    # 3. Normalize whitespace
    # Replace multiple whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

@app.route('/api/download/csv')
def download_csv():
    """Download results as CSV"""
    if not crawl_results:
        return jsonify({"error": "No results to download"}), 400
    
    try:
        csv_data = []
        for result in crawl_results:
            # Use the new, powerful cleaning function here!
            clean_content = clean_content_for_csv(result.get("content", ""))

            csv_data.append({
                "URL": result["url"],
                "Title": result["title"],
                "Content": clean_content,  # Use the cleaned content
                "Word Count": result["word_count"],
                "Status": result["status"],
                "Timestamp": result["timestamp"]
            })
        
        df = pd.DataFrame(csv_data)
        
        # Create a temporary file to store the CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            df.to_csv(tmp.name, index=False, encoding='utf-8')
            tmp_path = tmp.name
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crawl_results_{timestamp}.csv"
        
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        print(f"Error creating CSV: {e}") # It's good practice to log the error
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