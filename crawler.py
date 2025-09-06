import requests
from bs4 import BeautifulSoup


def background_crawler(urls):
    """
    A simple crawler that fetches each URL and returns a list of dictionaries
    containing the URL, status, word count, title, and content.
    """
    results = []

    for url in urls:
        try:
            r = requests.get(url, timeout=5)
            status = f"HTTP {r.status_code}"
        except Exception as e:
            status = f"Exception during request: {e}"
            r = None

        if r is not None and r.status_code == 200:
            # Extract title
            soup = BeautifulSoup(r.text, "html.parser")
            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag else ""

            # Extract body content
            body_tag = soup.find("body")
            content = body_tag.get_text(separator=" ") if body_tag else ""

            # Word count
            word_count = len(content.split())
        else:
            title = None
            content = None
            word_count = 0

        results.append(
            {
                "url": url,
                "status": status,
                "title": title,
                "content": content,
                "word_count": word_count,
            }
        )

    return results
