"""
Etsy Autocomplete / Search Suggestions Extractor
Extracts keyword suggestions from Etsy's search autocomplete.
"""

import time
import random
import logging
from typing import List, Optional
from urllib.parse import quote_plus

import requests

from config import (
    get_random_headers,
    get_proxies,
    MAX_RETRIES,
    TIMEOUT,
    BACKOFF_FACTOR,
    DELAY_BETWEEN_REQUESTS,
    JITTER_RANGE,
    ETSY_AUTOCOMPLETE_URL,
)

logger = logging.getLogger(__name__)


def get_autocomplete_suggestions(seed_keyword: str) -> List[str]:
    """
    Get Etsy autocomplete suggestions for a seed keyword.

    Args:
        seed_keyword: Base keyword to get suggestions for

    Returns:
        List of suggested search terms
    """
    logger.info(f"Getting autocomplete suggestions for: '{seed_keyword}'")

    suggestions = []

    # Try the suggestions endpoint
    suggestions = _fetch_from_api(seed_keyword)

    if not suggestions:
        # Fallback: try partial queries (type-ahead simulation)
        suggestions = _simulate_typeahead(seed_keyword)

    logger.info(f"Found {len(suggestions)} suggestions for '{seed_keyword}'")
    return suggestions


def _fetch_from_api(keyword: str) -> List[str]:
    """Try to fetch suggestions from Etsy's suggestion API."""
    encoded = quote_plus(keyword)
    url = f"{ETSY_AUTOCOMPLETE_URL}?q={encoded}&type=listings"

    for attempt in range(MAX_RETRIES):
        try:
            headers = get_random_headers()
            headers["X-Requested-With"] = "XMLHttpRequest"
            headers["Accept"] = "application/json"

            response = requests.get(
                url,
                headers=headers,
                proxies=get_proxies(),
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                data = response.json()
                # Handle various response formats
                if isinstance(data, list):
                    return [item if isinstance(item, str) else item.get("query", "") for item in data]
                elif isinstance(data, dict):
                    if "results" in data:
                        return [r.get("query", r) if isinstance(r, dict) else r for r in data["results"]]
                    elif "suggestions" in data:
                        return data["suggestions"]
                return []

            elif response.status_code in (403, 429):
                wait_time = BACKOFF_FACTOR ** (attempt + 1)
                logger.debug(f"Rate limited on suggestions API, waiting {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.debug(f"Suggestions API returned {response.status_code}")
                break

        except requests.exceptions.RequestException as e:
            logger.debug(f"Suggestions API error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_FACTOR ** attempt)

    return []


def _simulate_typeahead(keyword: str) -> List[str]:
    """
    Simulate typeahead by making requests with partial keywords.
    Fetches suggestions for progressive characters of the keyword.
    """
    suggestions = set()
    words = keyword.split()

    # Try variations: base word, base + first letter of next, etc.
    prefixes = []
    if len(words) >= 1:
        prefixes.append(words[0])
    if len(words) >= 2:
        prefixes.append(f"{words[0]} {words[1][:1]}")
        prefixes.append(f"{words[0]} {words[1][:3]}")
        prefixes.append(f"{words[0]} {words[1]}")

    for prefix in prefixes[:3]:  # Limit to avoid too many requests
        result = _fetch_from_api(prefix)
        suggestions.update(result)
        time.sleep(random.uniform(0.5, 1.5))

    return list(suggestions)


def get_bulk_suggestions(seed_keywords: List[str]) -> dict:
    """
    Get autocomplete suggestions for multiple seed keywords.

    Args:
        seed_keywords: List of seed keywords

    Returns:
        Dict mapping each keyword to its suggestions
    """
    results = {}

    for i, keyword in enumerate(seed_keywords):
        logger.info(f"Processing keyword {i + 1}/{len(seed_keywords)}: '{keyword}'")
        suggestions = get_autocomplete_suggestions(keyword)
        results[keyword] = suggestions

        if i < len(seed_keywords) - 1:
            delay = DELAY_BETWEEN_REQUESTS + random.uniform(*JITTER_RANGE)
            time.sleep(delay)

    return results


def expand_keyword_tree(seed: str, depth: int = 2) -> dict:
    """
    Recursively expand a seed keyword into a tree of suggestions.

    Args:
        seed: Starting keyword
        depth: How many levels deep to expand (max 3 to avoid rate limiting)

    Returns:
        Nested dict: {keyword: {sub_keyword: {...}, ...}}
    """
    depth = min(depth, 3)  # Safety cap

    if depth <= 0:
        return {}

    suggestions = get_autocomplete_suggestions(seed)
    tree = {}

    for suggestion in suggestions[:5]:  # Limit breadth
        if suggestion != seed:
            tree[suggestion] = expand_keyword_tree(suggestion, depth - 1) if depth > 1 else {}
            time.sleep(random.uniform(1, 2))

    return tree


def get_related_searches_from_page(html: str) -> List[str]:
    """
    Extract related search suggestions from an Etsy search results page.

    Args:
        html: Raw HTML content of search page

    Returns:
        List of related search terms
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    related = []

    # Look for related searches section
    related_selectors = [
        "div.related-searches a",
        "a[href*='/search?q='].wt-action-group__item",
        "div[data-appears-component-name='related_searches'] a",
    ]

    for selector in related_selectors:
        elements = soup.select(selector)
        if elements:
            for el in elements:
                text = el.get_text(strip=True)
                if text and len(text) > 2:
                    related.append(text.lower())
            break

    return list(set(related))
