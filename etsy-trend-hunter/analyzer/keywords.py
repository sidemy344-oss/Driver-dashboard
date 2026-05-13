"""
Keyword Frequency Analyzer
Analyzes listing data to extract trending keywords and calculate opportunity scores.
"""

import re
import logging
from typing import List, Dict, Optional
from collections import Counter
from itertools import combinations

import pandas as pd

from config import STOP_WORDS

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    """Lowercase, remove punctuation, normalize whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> List[str]:
    """Split text into words, removing stop words."""
    words = text.split()
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def _extract_ngrams(tokens: List[str], n: int) -> List[str]:
    """Extract n-grams from token list."""
    if len(tokens) < n:
        return []
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def analyze_keywords(listings_data: List[Dict], top_n: int = 50) -> pd.DataFrame:
    """
    Analyze keywords from listing data to find trending terms and opportunities.

    Args:
        listings_data: List of listing dicts (from search scraper)
        top_n: Number of top keywords to return

    Returns:
        DataFrame with columns: keyword, frequency, avg_price, avg_reviews,
        opportunity_score, listings_count
    """
    logger.info(f"Analyzing keywords from {len(listings_data)} listings")

    # Build corpus from titles and tags
    keyword_data = {}  # keyword -> {prices: [], reviews: [], count: 0}

    for listing in listings_data:
        title = listing.get("title", "")
        tags = listing.get("tags", [])
        price = listing.get("price", 0)
        reviews = listing.get("review_count", 0)

        # Combine title and tags into one text
        combined_text = _clean_text(title)
        if tags:
            if isinstance(tags, list):
                combined_text += " " + " ".join([_clean_text(t) for t in tags])
            else:
                combined_text += " " + _clean_text(str(tags))

        tokens = _tokenize(combined_text)

        # Extract 1-grams, 2-grams, and 3-grams
        all_ngrams = []
        all_ngrams.extend(_extract_ngrams(tokens, 1))
        all_ngrams.extend(_extract_ngrams(tokens, 2))
        all_ngrams.extend(_extract_ngrams(tokens, 3))

        # Track unique keywords per listing (avoid counting duplicates within same listing)
        seen_in_listing = set()
        for ngram in all_ngrams:
            if ngram not in seen_in_listing:
                seen_in_listing.add(ngram)
                if ngram not in keyword_data:
                    keyword_data[ngram] = {"prices": [], "reviews": [], "count": 0}
                keyword_data[ngram]["prices"].append(price)
                keyword_data[ngram]["reviews"].append(reviews)
                keyword_data[ngram]["count"] += 1

    # Convert to DataFrame
    rows = []
    for keyword, data in keyword_data.items():
        frequency = data["count"]
        if frequency < 2:  # Filter out very rare keywords
            continue

        avg_price = sum(data["prices"]) / len(data["prices"]) if data["prices"] else 0
        avg_reviews = sum(data["reviews"]) / len(data["reviews"]) if data["reviews"] else 0

        # Opportunity Score: (avg_price * avg_reviews) / (frequency ^ 1.5)
        # Higher = better opportunity (good revenue potential, less competition)
        if frequency > 0:
            opportunity_score = (avg_price * avg_reviews) / (frequency ** 1.5)
        else:
            opportunity_score = 0

        rows.append({
            "keyword": keyword,
            "frequency": frequency,
            "avg_price": round(avg_price, 2),
            "avg_reviews": round(avg_reviews, 1),
            "opportunity_score": round(opportunity_score, 2),
            "listings_count": len(listings_data),
        })

    df = pd.DataFrame(rows)

    if df.empty:
        logger.warning("No keywords found in listings data")
        return df

    # Sort by opportunity score descending
    df = df.sort_values("opportunity_score", ascending=False).reset_index(drop=True)

    logger.info(f"Extracted {len(df)} unique keywords, returning top {top_n}")
    return df.head(top_n)


def analyze_keywords_from_csv(csv_path: str, top_n: int = 50) -> pd.DataFrame:
    """
    Load listings from CSV and analyze keywords.

    Args:
        csv_path: Path to CSV file with listing data
        top_n: Number of top keywords to return

    Returns:
        DataFrame with keyword analysis
    """
    df = pd.read_csv(csv_path)
    listings = df.to_dict("records")
    return analyze_keywords(listings, top_n)


def find_price_gaps(listings_data: List[Dict]) -> List[Dict]:
    """
    Identify price gaps in the market — price ranges with few listings.

    Args:
        listings_data: List of listing dicts

    Returns:
        List of dicts with price_range, listing_count, gap_opportunity
    """
    prices = [l.get("price", 0) for l in listings_data if l.get("price", 0) > 0]

    if not prices:
        return []

    min_price = min(prices)
    max_price = max(prices)

    # Create price buckets
    bucket_size = max((max_price - min_price) / 10, 1)
    buckets = {}

    for price in prices:
        bucket = int((price - min_price) / bucket_size)
        bucket_key = f"${min_price + bucket * bucket_size:.0f}-${min_price + (bucket + 1) * bucket_size:.0f}"
        buckets[bucket_key] = buckets.get(bucket_key, 0) + 1

    # Identify gaps (buckets with fewer listings than average)
    if not buckets:
        return []

    avg_count = sum(buckets.values()) / len(buckets)
    gaps = []

    for price_range, count in sorted(buckets.items()):
        gap_opportunity = max(0, (avg_count - count) / avg_count) if avg_count > 0 else 0
        gaps.append({
            "price_range": price_range,
            "listing_count": count,
            "gap_opportunity": round(gap_opportunity, 3),
        })

    return sorted(gaps, key=lambda x: x["gap_opportunity"], reverse=True)


def get_keyword_summary(df: pd.DataFrame) -> Dict:
    """
    Generate a summary of keyword analysis results.

    Args:
        df: Keyword analysis DataFrame

    Returns:
        Dict with summary statistics
    """
    if df.empty:
        return {"total_keywords": 0}

    return {
        "total_keywords": len(df),
        "top_keyword": df.iloc[0]["keyword"] if len(df) > 0 else "N/A",
        "top_opportunity_score": df.iloc[0]["opportunity_score"] if len(df) > 0 else 0,
        "avg_price_all": round(df["avg_price"].mean(), 2),
        "avg_reviews_all": round(df["avg_reviews"].mean(), 1),
        "high_opportunity_count": len(df[df["opportunity_score"] > df["opportunity_score"].median()]),
    }
