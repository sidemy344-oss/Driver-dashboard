"""
Etsy Search Results Scraper
Scrapes Etsy search pages to extract listing data from top results.
"""

import time
import random
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from config import (
    get_random_headers,
    get_proxies,
    DELAY_BETWEEN_REQUESTS,
    JITTER_RANGE,
    MAX_RETRIES,
    TIMEOUT,
    BACKOFF_FACTOR,
    ETSY_SEARCH_URL,
)

logger = logging.getLogger(__name__)


def _build_search_url(query: str, page: int = 1) -> str:
    """Build Etsy search URL with query parameters."""
    encoded_query = quote_plus(query)
    return f"{ETSY_SEARCH_URL}?q={encoded_query}&ref=pagination&page={page}"


def _request_with_retry(url: str, session: requests.Session) -> Optional[requests.Response]:
    """Make HTTP request with exponential backoff retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            headers = get_random_headers()
            response = session.get(
                url,
                headers=headers,
                proxies=get_proxies(),
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                return response
            elif response.status_code in (403, 429):
                wait_time = BACKOFF_FACTOR ** (attempt + 1) + random.uniform(1, 3)
                logger.warning(
                    f"Rate limited (HTTP {response.status_code}). "
                    f"Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"HTTP {response.status_code} for URL: {url}")
                return None

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}/{MAX_RETRIES}")
            time.sleep(BACKOFF_FACTOR ** attempt)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_FACTOR ** attempt)
            else:
                return None

    logger.error(f"All {MAX_RETRIES} retries exhausted for: {url}")
    return None


def _parse_listing_card(card) -> Optional[Dict]:
    """Extract listing data from a single search result card."""
    try:
        listing = {}

        # Title
        title_el = card.select_one("h3.v2-listing-card__title, h3.wt-text-caption")
        if title_el:
            listing["title"] = title_el.get_text(strip=True)
        else:
            # Fallback: try any h3 within the card
            title_el = card.select_one("h3")
            listing["title"] = title_el.get_text(strip=True) if title_el else "N/A"

        # Price
        price_el = card.select_one("span.currency-value, span.lc-price span.currency-value")
        if price_el:
            price_text = price_el.get_text(strip=True).replace(",", "")
            try:
                listing["price"] = float(price_text)
            except ValueError:
                listing["price"] = 0.0
        else:
            # Fallback: look for price in any span with currency pattern
            price_el = card.select_one("p.lc-price, span.lc-price")
            if price_el:
                price_text = price_el.get_text(strip=True)
                # Extract numeric value
                import re
                match = re.search(r"[\d,]+\.?\d*", price_text)
                listing["price"] = float(match.group().replace(",", "")) if match else 0.0
            else:
                listing["price"] = 0.0

        # Shop name
        shop_el = card.select_one("p.wt-text-gray, span.v2-listing-card__shop")
        if shop_el:
            listing["shop_name"] = shop_el.get_text(strip=True)
        else:
            listing["shop_name"] = "N/A"

        # Review count
        review_el = card.select_one(
            "span.wt-text-slime, span.wt-text-gray span.wt-screen-reader-only"
        )
        if review_el:
            review_text = review_el.get_text(strip=True)
            import re
            match = re.search(r"([\d,]+)", review_text)
            listing["review_count"] = int(match.group().replace(",", "")) if match else 0
        else:
            listing["review_count"] = 0

        # Listing URL
        link_el = card.select_one("a.listing-link, a[href*='/listing/']")
        if link_el and link_el.get("href"):
            href = link_el["href"]
            listing["listing_url"] = href if href.startswith("http") else f"https://www.etsy.com{href}"
        else:
            listing["listing_url"] = "N/A"

        # Thumbnail
        img_el = card.select_one("img")
        if img_el:
            listing["thumbnail"] = img_el.get("src", "") or img_el.get("data-src", "")
        else:
            listing["thumbnail"] = ""

        # Only return if we got at least a title
        if listing.get("title") and listing["title"] != "N/A":
            return listing

    except Exception as e:
        logger.debug(f"Error parsing listing card: {e}")

    return None


def _parse_search_page(html: str) -> List[Dict]:
    """Parse all listing cards from a search results page."""
    soup = BeautifulSoup(html, "lxml")
    listings = []

    # Try multiple selectors for listing cards (Etsy changes their DOM frequently)
    selectors = [
        "div[data-search-results] li.wt-list-unstyled",
        "div.search-listings-group div.js-merch-stash-check-listing",
        "ol.tab-reorder-container li",
        "div[data-search-results] div[data-listing-id]",
        "div.v2-listing-card",
    ]

    cards = []
    for selector in selectors:
        cards = soup.select(selector)
        if cards:
            logger.debug(f"Found {len(cards)} cards with selector: {selector}")
            break

    if not cards:
        # Last resort: find all elements with data-listing-id
        cards = soup.find_all(attrs={"data-listing-id": True})
        logger.debug(f"Fallback: found {len(cards)} elements with data-listing-id")

    for card in cards:
        listing = _parse_listing_card(card)
        if listing:
            listings.append(listing)

    return listings


def search_etsy(query: str, pages: int = 3) -> List[Dict]:
    """
    Scrape Etsy search results for a given query.

    Args:
        query: Search term (e.g., "funny t-shirt")
        pages: Number of pages to scrape (48 results per page)

    Returns:
        List of dicts with listing data (title, price, shop_name, etc.)
    """
    all_listings = []
    session = requests.Session()

    logger.info(f"Searching Etsy for: '{query}' ({pages} pages)")

    for page in range(1, pages + 1):
        url = _build_search_url(query, page)
        logger.info(f"Scraping page {page}/{pages}: {url}")

        response = _request_with_retry(url, session)

        if response is None:
            logger.warning(f"Failed to fetch page {page}, skipping...")
            continue

        page_listings = _parse_search_page(response.text)
        all_listings.extend(page_listings)
        logger.info(f"Page {page}: extracted {len(page_listings)} listings")

        # Rate limiting between pages
        if page < pages:
            delay = DELAY_BETWEEN_REQUESTS + random.uniform(*JITTER_RANGE)
            logger.debug(f"Waiting {delay:.1f}s before next page...")
            time.sleep(delay)

    logger.info(f"Total listings scraped: {len(all_listings)}")
    return all_listings


def search_etsy_with_metadata(query: str, pages: int = 3) -> Dict:
    """
    Search Etsy and return results with metadata.

    Returns:
        Dict with 'query', 'total_results', 'pages_scraped', 'listings'
    """
    listings = search_etsy(query, pages)
    return {
        "query": query,
        "total_results": len(listings),
        "pages_scraped": pages,
        "listings": listings,
    }
