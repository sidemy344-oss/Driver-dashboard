"""
Etsy Individual Listing Scraper
Extracts detailed data from a single Etsy listing page.
"""

import re
import time
import random
import logging
from typing import Dict, Optional, List

import requests
from bs4 import BeautifulSoup

from config import (
    get_random_headers,
    get_proxies,
    MAX_RETRIES,
    TIMEOUT,
    BACKOFF_FACTOR,
)

logger = logging.getLogger(__name__)


def _fetch_listing_page(url: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """Fetch a listing page with retry logic."""
    if session is None:
        session = requests.Session()

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
                return response.text
            elif response.status_code in (403, 429):
                wait_time = BACKOFF_FACTOR ** (attempt + 1) + random.uniform(1, 3)
                logger.warning(
                    f"Rate limited (HTTP {response.status_code}). "
                    f"Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"HTTP {response.status_code} for listing: {url}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for listing: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_FACTOR ** attempt)

    return None


def _extract_tags(soup: BeautifulSoup) -> List[str]:
    """Extract listing tags from the page."""
    tags = []

    # Method 1: Tag links in the listing page
    tag_links = soup.select("a[href*='/search?q='].wt-tag, a.tag-card")
    for link in tag_links:
        tag_text = link.get_text(strip=True)
        if tag_text:
            tags.append(tag_text.lower())

    # Method 2: Look in structured data / JSON-LD
    if not tags:
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and "keywords" in data:
                    keywords = data["keywords"]
                    if isinstance(keywords, str):
                        tags.extend([k.strip().lower() for k in keywords.split(",")])
                    elif isinstance(keywords, list):
                        tags.extend([k.lower() for k in keywords])
            except (json.JSONDecodeError, TypeError):
                continue

    # Method 3: Meta keywords
    if not tags:
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords and meta_keywords.get("content"):
            tags = [k.strip().lower() for k in meta_keywords["content"].split(",")]

    return list(set(tags))  # Deduplicate


def _extract_price(soup: BeautifulSoup) -> float:
    """Extract listing price."""
    # Try structured data first
    price_el = soup.select_one(
        "p[data-buy-box-listing-price] span.currency-value, "
        "div[data-appears-component-name='price'] span.currency-value"
    )
    if price_el:
        try:
            return float(price_el.get_text(strip=True).replace(",", ""))
        except ValueError:
            pass

    # Fallback: search for price patterns
    price_pattern = re.compile(r"\$\s*([\d,]+\.?\d*)")
    price_match = price_pattern.search(str(soup))
    if price_match:
        try:
            return float(price_match.group(1).replace(",", ""))
        except ValueError:
            pass

    return 0.0


def _extract_review_count(soup: BeautifulSoup) -> int:
    """Extract total review count."""
    # Look for review count in heading or stats
    review_patterns = [
        re.compile(r"([\d,]+)\s*reviews?", re.IGNORECASE),
        re.compile(r"reviews?\s*\(([\d,]+)\)", re.IGNORECASE),
    ]

    page_text = soup.get_text()
    for pattern in review_patterns:
        match = pattern.search(page_text)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                continue

    return 0


def _extract_in_cart_count(soup: BeautifulSoup) -> int:
    """Extract 'in X carts' count if visible."""
    cart_pattern = re.compile(r"in\s+([\d,]+)\s+carts?", re.IGNORECASE)
    page_text = soup.get_text()
    match = cart_pattern.search(page_text)
    if match:
        try:
            return int(match.group(1).replace(",", ""))
        except ValueError:
            pass
    return 0


def _extract_description(soup: BeautifulSoup) -> str:
    """Extract listing description (first 500 chars)."""
    desc_el = soup.select_one(
        "div[data-id='description-text'], "
        "p[data-product-details-description-text-content]"
    )
    if desc_el:
        text = desc_el.get_text(strip=True)
        return text[:500]

    # Fallback: meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        return meta_desc["content"][:500]

    return ""


def _extract_shipping_info(soup: BeautifulSoup) -> Dict:
    """Extract shipping cost and delivery estimate."""
    shipping_info = {"shipping_cost": "N/A", "estimated_delivery": "N/A"}

    # Shipping cost
    free_shipping = soup.find(string=re.compile(r"free\s+shipping", re.IGNORECASE))
    if free_shipping:
        shipping_info["shipping_cost"] = "Free"
    else:
        shipping_el = soup.select_one("span[data-shipping-cost]")
        if shipping_el:
            shipping_info["shipping_cost"] = shipping_el.get_text(strip=True)

    # Delivery estimate
    delivery_pattern = re.compile(r"(arrives?\s+by\s+\w+\s+\d+|[\w]+\s+\d+-\d+)", re.IGNORECASE)
    delivery_match = delivery_pattern.search(soup.get_text())
    if delivery_match:
        shipping_info["estimated_delivery"] = delivery_match.group(0)

    return shipping_info


def _extract_shop_info(soup: BeautifulSoup) -> Dict:
    """Extract shop name and other shop-level info."""
    shop_info = {"shop_name": "N/A", "shop_url": "N/A", "shop_sales": 0}

    # Shop name
    shop_el = soup.select_one(
        "a[href*='/shop/'], span[data-shop-name]"
    )
    if shop_el:
        shop_info["shop_name"] = shop_el.get_text(strip=True)
        if shop_el.get("href"):
            href = shop_el["href"]
            shop_info["shop_url"] = href if href.startswith("http") else f"https://www.etsy.com{href}"

    # Shop sales count
    sales_pattern = re.compile(r"([\d,]+)\s+sales?", re.IGNORECASE)
    page_text = soup.get_text()
    match = sales_pattern.search(page_text)
    if match:
        try:
            shop_info["shop_sales"] = int(match.group(1).replace(",", ""))
        except ValueError:
            pass

    return shop_info


def scrape_listing(url: str) -> Dict:
    """
    Scrape detailed information from a single Etsy listing.

    Args:
        url: Full Etsy listing URL

    Returns:
        Dict with: tags, description, total_reviews, in_cart_count,
        shipping_cost, estimated_delivery, shop_name, price, title
    """
    logger.info(f"Scraping listing: {url}")

    html = _fetch_listing_page(url)
    if html is None:
        logger.error(f"Failed to fetch listing: {url}")
        return {"error": "Failed to fetch listing", "url": url}

    soup = BeautifulSoup(html, "lxml")

    # Extract title
    title_el = soup.select_one("h1.wt-text-body-03, h1[data-buy-box-listing-title]")
    title = title_el.get_text(strip=True) if title_el else "N/A"

    # Build result
    shipping = _extract_shipping_info(soup)
    shop = _extract_shop_info(soup)

    result = {
        "url": url,
        "title": title,
        "price": _extract_price(soup),
        "tags": _extract_tags(soup),
        "description": _extract_description(soup),
        "total_reviews": _extract_review_count(soup),
        "in_cart_count": _extract_in_cart_count(soup),
        "shipping_cost": shipping["shipping_cost"],
        "estimated_delivery": shipping["estimated_delivery"],
        "shop_name": shop["shop_name"],
        "shop_url": shop["shop_url"],
        "shop_sales": shop["shop_sales"],
    }

    # Estimated monthly revenue (rough: reviews * price * factor)
    if result["total_reviews"] > 0 and result["price"] > 0:
        # Rough heuristic: ~1% of buyers leave reviews, estimate monthly fraction
        result["estimated_monthly_revenue"] = round(
            result["total_reviews"] * result["price"] * 0.05, 2
        )
    else:
        result["estimated_monthly_revenue"] = 0.0

    logger.info(f"Scraped: '{result['title']}' - ${result['price']} ({len(result['tags'])} tags)")
    return result


def scrape_multiple_listings(urls: List[str], delay: float = 3.0) -> List[Dict]:
    """
    Scrape multiple Etsy listings with delays between requests.

    Args:
        urls: List of Etsy listing URLs
        delay: Seconds to wait between requests

    Returns:
        List of listing detail dicts
    """
    results = []
    session = requests.Session()

    for i, url in enumerate(urls, 1):
        logger.info(f"Scraping listing {i}/{len(urls)}")
        html = _fetch_listing_page(url, session)

        if html:
            soup = BeautifulSoup(html, "lxml")
            title_el = soup.select_one("h1.wt-text-body-03, h1[data-buy-box-listing-title]")
            title = title_el.get_text(strip=True) if title_el else "N/A"
            shipping = _extract_shipping_info(soup)
            shop = _extract_shop_info(soup)

            result = {
                "url": url,
                "title": title,
                "price": _extract_price(soup),
                "tags": _extract_tags(soup),
                "description": _extract_description(soup),
                "total_reviews": _extract_review_count(soup),
                "in_cart_count": _extract_in_cart_count(soup),
                "shipping_cost": shipping["shipping_cost"],
                "estimated_delivery": shipping["estimated_delivery"],
                "shop_name": shop["shop_name"],
                "shop_url": shop["shop_url"],
                "shop_sales": shop["shop_sales"],
            }
            results.append(result)
        else:
            results.append({"error": "Failed to fetch", "url": url})

        if i < len(urls):
            wait = delay + random.uniform(1, 2)
            time.sleep(wait)

    return results
