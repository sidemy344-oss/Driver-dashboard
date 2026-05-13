"""
Competitor Analysis Module
Analyzes competitor listings to extract intelligence on pricing, tags, and positioning.
"""

import logging
from typing import Dict, List, Optional
from collections import Counter

from scraper.etsy_listing import scrape_listing, scrape_multiple_listings
from scraper.etsy_search import search_etsy

logger = logging.getLogger(__name__)


def analyze_competitor(listing_url: str) -> Dict:
    """
    Deep-dive analysis of a competitor listing.

    Args:
        listing_url: Full Etsy listing URL

    Returns:
        Dict with competitor intelligence: tags, pricing, strategy, similar listings
    """
    logger.info(f"Analyzing competitor: {listing_url}")

    # Scrape the target listing
    listing = scrape_listing(listing_url)

    if "error" in listing:
        return listing

    # Find similar listings by searching with the listing's top tags
    similar_listings = _find_similar_listings(listing)

    # Analyze positioning
    analysis = {
        "target_listing": listing,
        "tag_analysis": _analyze_tags(listing),
        "price_positioning": _analyze_price_position(listing, similar_listings),
        "similar_listings": similar_listings[:5],
        "competitor_summary": _build_competitor_summary(listing, similar_listings),
    }

    return analysis


def _find_similar_listings(listing: Dict) -> List[Dict]:
    """Find similar listings by searching with the target's keywords."""
    tags = listing.get("tags", [])
    title = listing.get("title", "")

    # Build search query from top tags or title words
    if tags:
        search_query = " ".join(tags[:3])
    else:
        # Use first few meaningful words from title
        words = title.split()[:4]
        search_query = " ".join(words)

    if not search_query.strip():
        return []

    logger.info(f"Searching for similar listings: '{search_query}'")
    similar = search_etsy(search_query, pages=1)

    # Filter out the target listing itself
    target_url = listing.get("url", "")
    similar = [s for s in similar if s.get("listing_url", "") != target_url]

    return similar


def _analyze_tags(listing: Dict) -> Dict:
    """Analyze the tag strategy of a listing."""
    tags = listing.get("tags", [])

    if not tags:
        return {"total_tags": 0, "tag_categories": {}}

    # Categorize tags
    categories = {
        "descriptive": [],  # What the product IS
        "style": [],  # Design style keywords
        "occasion": [],  # When/why to buy
        "audience": [],  # Who it's for
        "other": [],
    }

    style_words = {"vintage", "retro", "modern", "minimalist", "boho", "trendy", "classic", "funny", "cute"}
    occasion_words = {"gift", "birthday", "christmas", "wedding", "anniversary", "valentine", "mother", "father"}
    audience_words = {"men", "women", "kids", "mom", "dad", "her", "him", "boyfriend", "girlfriend", "wife", "husband"}

    for tag in tags:
        tag_lower = tag.lower()
        tag_words = set(tag_lower.split())

        if tag_words & style_words:
            categories["style"].append(tag)
        elif tag_words & occasion_words:
            categories["occasion"].append(tag)
        elif tag_words & audience_words:
            categories["audience"].append(tag)
        else:
            categories["descriptive"].append(tag)

    return {
        "total_tags": len(tags),
        "all_tags": tags,
        "tag_categories": {k: v for k, v in categories.items() if v},
        "tag_length_avg": round(sum(len(t) for t in tags) / len(tags), 1) if tags else 0,
    }


def _analyze_price_position(listing: Dict, similar_listings: List[Dict]) -> Dict:
    """Analyze how the listing is priced relative to competitors."""
    target_price = listing.get("price", 0)
    competitor_prices = [s.get("price", 0) for s in similar_listings if s.get("price", 0) > 0]

    if not competitor_prices or target_price == 0:
        return {
            "target_price": target_price,
            "position": "unknown",
            "competitor_count": len(competitor_prices),
        }

    avg_price = sum(competitor_prices) / len(competitor_prices)
    min_price = min(competitor_prices)
    max_price = max(competitor_prices)

    # Determine position
    if target_price < avg_price * 0.8:
        position = "budget"
    elif target_price > avg_price * 1.2:
        position = "premium"
    else:
        position = "mid-range"

    # Price percentile
    below_count = sum(1 for p in competitor_prices if p < target_price)
    percentile = (below_count / len(competitor_prices)) * 100 if competitor_prices else 50

    return {
        "target_price": target_price,
        "market_avg_price": round(avg_price, 2),
        "market_min_price": min_price,
        "market_max_price": max_price,
        "position": position,
        "price_percentile": round(percentile, 1),
        "competitor_count": len(competitor_prices),
        "price_difference_from_avg": round(target_price - avg_price, 2),
    }


def _build_competitor_summary(listing: Dict, similar_listings: List[Dict]) -> Dict:
    """Build a high-level competitor intelligence summary."""
    target_reviews = listing.get("total_reviews", 0)
    target_price = listing.get("price", 0)

    similar_reviews = [s.get("review_count", 0) for s in similar_listings]
    similar_prices = [s.get("price", 0) for s in similar_listings if s.get("price", 0) > 0]

    avg_reviews = sum(similar_reviews) / len(similar_reviews) if similar_reviews else 0
    avg_price = sum(similar_prices) / len(similar_prices) if similar_prices else 0

    # Strength assessment
    strengths = []
    weaknesses = []

    if target_reviews > avg_reviews * 1.5:
        strengths.append("Strong review count (social proof)")
    elif target_reviews < avg_reviews * 0.5:
        weaknesses.append("Low review count vs competitors")

    if target_price < avg_price * 0.9:
        strengths.append("Competitive pricing")
    elif target_price > avg_price * 1.3:
        weaknesses.append("Premium priced — needs strong differentiation")

    tags = listing.get("tags", [])
    if len(tags) >= 10:
        strengths.append("Good tag coverage")
    elif len(tags) < 5:
        weaknesses.append("Low tag count — missing discovery opportunities")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "market_size": len(similar_listings),
        "avg_competitor_reviews": round(avg_reviews, 1),
        "avg_competitor_price": round(avg_price, 2),
        "review_velocity_estimate": round(target_reviews * target_price * 0.05, 2) if target_reviews else 0,
    }


def compare_listings(urls: List[str]) -> Dict:
    """
    Compare multiple listings side by side.

    Args:
        urls: List of Etsy listing URLs to compare

    Returns:
        Dict with comparison data
    """
    listings = scrape_multiple_listings(urls)

    comparison = {
        "listings": [],
        "price_range": {"min": 0, "max": 0, "avg": 0},
        "tag_overlap": [],
        "unique_tags": {},
    }

    all_tags = []
    prices = []

    for listing in listings:
        if "error" not in listing:
            comparison["listings"].append({
                "title": listing.get("title", "N/A"),
                "price": listing.get("price", 0),
                "reviews": listing.get("total_reviews", 0),
                "tags_count": len(listing.get("tags", [])),
                "url": listing.get("url", ""),
            })
            all_tags.extend(listing.get("tags", []))
            if listing.get("price", 0) > 0:
                prices.append(listing["price"])

    # Price range
    if prices:
        comparison["price_range"] = {
            "min": min(prices),
            "max": max(prices),
            "avg": round(sum(prices) / len(prices), 2),
        }

    # Tag analysis
    tag_counts = Counter(all_tags)
    comparison["tag_overlap"] = [tag for tag, count in tag_counts.items() if count > 1]

    return comparison
