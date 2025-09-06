# 🚀🤖 Crawl4AI Multi-URL Web Crawler

A powerful Flask-based web application that uses Crawl4AI to crawl websites, extract content, and provide intelligent data management with caching and CSV export capabilities.

## ✨ Features

- **Multi-URL Crawling**: Automatically discovers and crawls up to 30 pages from a homepage
- **Intelligent Content Extraction**: Uses Crawl4AI's advanced content filtering and markdown generation
- **Real-time Progress Tracking**: Live progress updates with visual progress bars
- **Smart Caching System**: Automatically saves and retrieves previous crawl results
- **CSV Export**: Download all crawl results in CSV format for analysis
- **Modern Web Interface**: Beautiful, responsive UI with real-time updates
- **Memory Management**: Built-in memory monitoring and adaptive concurrency control
- **Error Handling**: Comprehensive error handling and status reporting

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Crawl4AI browser dependencies**:
   ```bash
   python -m playwright install --with-deps chromium
   ```

4. **Run the post-installation setup**:
   ```bash
   crawl4ai-setup
   ```

5. **Verify installation**:
   ```bash
   crawl4ai-doctor
   ```

## 🚀 Usage

### Starting the Application

1. **Run the Flask app**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

### Using the Web Interface

1. **Enter a Homepage URL**: 
   - Input the main website URL you want to crawl
   - Example: `https://example.com`

2. **Set Maximum Pages**:
   - Choose how many pages to crawl (default: 30)
   - Range: 1-100 pages

3. **Start Crawling**:
   - Click "Start Crawling" to begin the process
   - Monitor real-time progress in the progress bar

4. **View Results**:
   - See all crawled pages with titles, content previews, and word counts
   - Expand content to see full text
   - Check status (success/error) for each page

5. **Export Data**:
   - Download results as CSV for further analysis
   - Clear results to start fresh

6. **Manage Cache**:
   - View previously cached crawl results
   - Load cached results without re-crawling
   - Clear cache when needed

## 🔧 Configuration

### Crawl4AI Settings

The application uses optimized Crawl4AI configurations:

- **Content Filtering**: PruningContentFilter with dynamic threshold (0.45)
- **Markdown Generation**: DefaultMarkdownGenerator with content filtering
- **Memory Management**: MemoryAdaptiveDispatcher with 80% threshold
- **Concurrency**: Maximum 5 concurrent sessions
- **Caching**: Enabled for performance and reusability

### Customization

You can modify the crawling behavior by editing `app.py`:

```python
# Adjust content filtering threshold
content_filter = PruningContentFilter(
    threshold=0.45,           # Lower = more content, Higher = less content
    threshold_type="dynamic", # "fixed" or "dynamic"
    min_word_threshold=10     # Minimum words per content block
)

# Modify memory management
dispatcher = MemoryAdaptiveDispatcher(
    memory_threshold_percent=80.0,  # Pause if memory exceeds 80%
    max_session_permit=5            # Max concurrent requests
)
```

## 📁 Project Structure

```
web-crawler/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Web interface template
└── cache/                # Cached crawl results (auto-created)
    ├── domain1_timestamp.json
    └── domain2_timestamp.json
```

## 🌐 API Endpoints

### Core Endpoints

- `GET /` - Main web interface
- `POST /api/crawl` - Start a new crawl
- `GET /api/status` - Get current crawl status
- `GET /api/results` - Get crawl results
- `GET /api/download/csv` - Download results as CSV

### Cache Management

- `GET /api/cache/list` - List all cached results
- `GET /api/cache/load/<filename>` - Load specific cache file
- `POST /api/cache/clear` - Clear all cached results

## 📊 Data Format

### Crawl Results Structure

Each crawled page includes:

```json
{
  "url": "https://example.com/page",
  "title": "Page Title",
  "content": "Extracted markdown content",
  "word_count": 150,
  "timestamp": "2024-01-01T12:00:00",
  "status": "success"
}
```

### CSV Export Format

The CSV includes columns:
- URL
- Title
- Content (truncated to 1000 characters)
- Word Count
- Status
- Timestamp

## 🔍 How It Works

1. **Homepage Analysis**: Crawls the main URL to extract internal links
2. **Link Discovery**: Finds up to 30 internal links from the same domain
3. **Content Extraction**: Uses Crawl4AI to crawl each discovered page
4. **Smart Filtering**: Applies content filtering to remove noise and irrelevant content
5. **Progress Tracking**: Real-time updates on crawling progress
6. **Caching**: Automatically saves results for future use
7. **Export**: Provides CSV download for data analysis

## 🚨 Important Notes

### Rate Limiting
- Built-in rate limiting to respect website resources
- Random delays between requests (1-3 seconds)
- Exponential backoff for rate limit responses

### Memory Management
- Automatic memory monitoring
- Pauses crawling if memory usage exceeds 80%
- Configurable memory thresholds

### Ethical Crawling
- Respects robots.txt when possible
- Includes delays between requests
- Only crawls internal links from the same domain

## 🐛 Troubleshooting

### Common Issues

1. **Browser Installation Failed**:
   ```bash
   python -m playwright install --with-deps chromium
   ```

2. **Memory Issues**:
   - Reduce `max_session_permit` in the dispatcher
   - Lower `memory_threshold_percent`

3. **Crawl Failures**:
   - Check if the website allows crawling
   - Verify the URL is accessible
   - Check console logs for specific error messages

### Debug Mode

Run with debug enabled for detailed logging:
```bash
python app.py
```

## 🔒 Security Considerations

- Input validation for URLs
- Rate limiting to prevent abuse
- Error handling to prevent information disclosure
- CORS enabled for development

## 📈 Performance Tips

1. **Adjust concurrency**: Modify `max_session_permit` based on your system
2. **Memory optimization**: Lower `memory_threshold_percent` for limited systems
3. **Content filtering**: Adjust threshold values for better content quality
4. **Caching**: Use cached results when possible to avoid re-crawling

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve the project.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- Built with [Crawl4AI](https://github.com/unclecode/crawl4ai) - Open-source LLM Friendly Web Crawler
- Powered by Flask and modern web technologies
- Beautiful UI with Bootstrap and custom CSS

---

**Happy Crawling! 🕸️🚀**
