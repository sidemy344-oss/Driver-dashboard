"""
Etsy Trend Hunter - Configuration
User-editable settings for scraping, output, and behavior.
"""

import os
import random
from dotenv import load_dotenv

load_dotenv()

# --- User-Agent Rotation Pool ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def get_random_headers():
    """Return headers with a randomly selected User-Agent."""
    headers = HEADERS.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    return headers


# --- Request Settings ---
DELAY_BETWEEN_REQUESTS = 2  # seconds
JITTER_RANGE = (1, 3)  # random additional seconds
MAX_RETRIES = 3
TIMEOUT = 15
BACKOFF_FACTOR = 2  # exponential backoff multiplier

# --- Proxy Support ---
PROXY = os.getenv("PROXY", None)  # "http://user:pass@proxy:port"

def get_proxies():
    """Return proxy dict for requests library, or None."""
    if PROXY:
        return {"http": PROXY, "https": PROXY}
    return None

# --- Output Settings ---
DEFAULT_OUTPUT_DIR = "data"
DASHBOARD_TEMPLATE = "templates/dashboard.html"

# --- Etsy URLs ---
ETSY_BASE_URL = "https://www.etsy.com"
ETSY_SEARCH_URL = "https://www.etsy.com/search"
ETSY_AUTOCOMPLETE_URL = "https://www.etsy.com/search/suggestions"

# --- Analysis Settings ---
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "this", "that", "are", "was",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "not", "so", "no", "nor", "as", "if", "than", "too", "very", "just",
    "about", "above", "after", "again", "all", "also", "am", "any",
    "because", "been", "before", "being", "below", "between", "both",
    "each", "few", "further", "here", "how", "into", "its", "more",
    "most", "new", "now", "only", "other", "our", "out", "over", "own",
    "same", "she", "some", "such", "there", "these", "they", "those",
    "through", "under", "up", "us", "we", "what", "when", "where",
    "which", "while", "who", "whom", "why", "you", "your",
}
