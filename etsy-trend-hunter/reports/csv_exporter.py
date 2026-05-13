"""
CSV Report Exporter
Exports search results, keyword analysis, and competitor data to CSV files.
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

import pandas as pd

from config import DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)


def _ensure_output_dir(output_dir: str = None) -> str:
    """Ensure output directory exists, create if needed."""
    dir_path = output_dir or DEFAULT_OUTPUT_DIR
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def _generate_filename(base_name: str, extension: str = "csv") -> str:
    """Generate a timestamped filename."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    # Clean base name
    clean_name = base_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    clean_name = "".join(c for c in clean_name if c.isalnum() or c in "_-")
    return f"{clean_name}_{timestamp}.{extension}"


def export_search_results(
    data: List[Dict],
    filename: Optional[str] = None,
    output_dir: Optional[str] = None,
    query: str = "search",
) -> str:
    """
    Export search results to CSV.

    Args:
        data: List of listing dicts from search scraper
        filename: Custom filename (auto-generated if None)
        output_dir: Output directory path
        query: Search query used (for filename generation)

    Returns:
        Path to the created CSV file
    """
    dir_path = _ensure_output_dir(output_dir)

    if filename is None:
        filename = _generate_filename(query)

    filepath = os.path.join(dir_path, filename)

    df = pd.DataFrame(data)

    # Reorder columns for readability
    preferred_order = [
        "title", "price", "shop_name", "review_count",
        "listing_url", "thumbnail", "tags",
    ]
    existing_cols = [c for c in preferred_order if c in df.columns]
    remaining_cols = [c for c in df.columns if c not in existing_cols]
    df = df[existing_cols + remaining_cols]

    df.to_csv(filepath, index=False, encoding="utf-8")
    logger.info(f"Search results exported: {filepath} ({len(data)} rows)")

    return filepath


def export_keyword_analysis(
    df: pd.DataFrame,
    filename: Optional[str] = None,
    output_dir: Optional[str] = None,
    query: str = "keywords",
) -> str:
    """
    Export keyword analysis DataFrame to CSV.

    Args:
        df: Keyword analysis DataFrame
        filename: Custom filename
        output_dir: Output directory path
        query: Related query for filename

    Returns:
        Path to the created CSV file
    """
    dir_path = _ensure_output_dir(output_dir)

    if filename is None:
        filename = _generate_filename(f"{query}_keywords")

    filepath = os.path.join(dir_path, filename)
    df.to_csv(filepath, index=False, encoding="utf-8")
    logger.info(f"Keyword analysis exported: {filepath} ({len(df)} keywords)")

    return filepath


def export_competitor_report(
    data: Dict,
    filename: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> str:
    """
    Export competitor analysis to CSV.

    Args:
        data: Competitor analysis dict
        filename: Custom filename
        output_dir: Output directory path

    Returns:
        Path to the created CSV file
    """
    dir_path = _ensure_output_dir(output_dir)

    if filename is None:
        filename = _generate_filename("competitor_report")

    filepath = os.path.join(dir_path, filename)

    # Flatten competitor data for CSV
    rows = []

    # Target listing info
    target = data.get("target_listing", {})
    if target:
        row = {
            "type": "TARGET",
            "title": target.get("title", ""),
            "price": target.get("price", 0),
            "reviews": target.get("total_reviews", 0),
            "tags": ", ".join(target.get("tags", [])),
            "shop_name": target.get("shop_name", ""),
            "url": target.get("url", ""),
            "in_cart_count": target.get("in_cart_count", 0),
            "estimated_monthly_revenue": target.get("estimated_monthly_revenue", 0),
        }
        rows.append(row)

    # Similar listings
    for listing in data.get("similar_listings", []):
        row = {
            "type": "SIMILAR",
            "title": listing.get("title", ""),
            "price": listing.get("price", 0),
            "reviews": listing.get("review_count", 0),
            "tags": "",
            "shop_name": listing.get("shop_name", ""),
            "url": listing.get("listing_url", ""),
            "in_cart_count": 0,
            "estimated_monthly_revenue": 0,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False, encoding="utf-8")
    logger.info(f"Competitor report exported: {filepath}")

    return filepath


def export_trend_report(
    trend_data: Dict,
    filename: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> str:
    """
    Export trend analysis to CSV.

    Args:
        trend_data: Trend report dict from trends.detect_trends()
        filename: Custom filename
        output_dir: Output directory path

    Returns:
        Path to the created CSV file
    """
    dir_path = _ensure_output_dir(output_dir)

    if filename is None:
        filename = _generate_filename("trend_report")

    filepath = os.path.join(dir_path, filename)

    # Combine all keyword lists into one CSV with type column
    rows = []

    for kw in trend_data.get("high_opportunity_keywords", []):
        kw["category"] = "high_opportunity"
        rows.append(kw)

    for kw in trend_data.get("saturated_keywords", []):
        kw["category"] = "saturated"
        rows.append(kw)

    for kw in trend_data.get("niche_opportunities", []):
        kw["category"] = "niche"
        rows.append(kw)

    for kw in trend_data.get("rising_keywords", []):
        kw["category"] = "rising"
        rows.append(kw)

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False, encoding="utf-8")
        logger.info(f"Trend report exported: {filepath} ({len(rows)} entries)")
    else:
        # Write empty file with headers
        pd.DataFrame(columns=["keyword", "category", "frequency", "opportunity_score"]).to_csv(
            filepath, index=False
        )
        logger.warning(f"Trend report exported (empty): {filepath}")

    return filepath


def export_autocomplete_results(
    data: Dict[str, List[str]],
    filename: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> str:
    """
    Export autocomplete suggestions to CSV.

    Args:
        data: Dict mapping seed keywords to suggestion lists
        filename: Custom filename
        output_dir: Output directory path

    Returns:
        Path to the created CSV file
    """
    dir_path = _ensure_output_dir(output_dir)

    if filename is None:
        filename = _generate_filename("autocomplete")

    filepath = os.path.join(dir_path, filename)

    rows = []
    for seed, suggestions in data.items():
        for suggestion in suggestions:
            rows.append({"seed_keyword": seed, "suggestion": suggestion})

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False, encoding="utf-8")
    logger.info(f"Autocomplete results exported: {filepath} ({len(rows)} suggestions)")

    return filepath
