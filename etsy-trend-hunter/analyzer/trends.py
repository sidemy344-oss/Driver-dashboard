"""
Trend Detection Module
Identifies rising keywords, under-served niches, and market opportunities.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

import pandas as pd

from analyzer.keywords import analyze_keywords, find_price_gaps

logger = logging.getLogger(__name__)


def detect_trends(search_results: List[Dict], historical_data: Optional[List[Dict]] = None) -> Dict:
    """
    Detect trending patterns from search results.

    Args:
        search_results: Current search results (list of listing dicts)
        historical_data: Previous search results for comparison (optional)

    Returns:
        Dict with trend analysis: rising_keywords, declining, stable, opportunities
    """
    logger.info(f"Detecting trends from {len(search_results)} listings")

    # Analyze current keywords
    current_keywords = analyze_keywords(search_results, top_n=100)

    trend_report = {
        "timestamp": datetime.now().isoformat(),
        "total_listings_analyzed": len(search_results),
        "rising_keywords": [],
        "high_opportunity_keywords": [],
        "saturated_keywords": [],
        "price_gaps": [],
        "niche_opportunities": [],
    }

    if current_keywords.empty:
        return trend_report

    # Identify high-opportunity keywords (high score, moderate frequency)
    median_freq = current_keywords["frequency"].median()
    median_score = current_keywords["opportunity_score"].median()

    high_opp = current_keywords[
        (current_keywords["opportunity_score"] > median_score) &
        (current_keywords["frequency"] <= median_freq * 2)
    ]
    trend_report["high_opportunity_keywords"] = high_opp.head(20).to_dict("records")

    # Identify saturated keywords (very high frequency, low opportunity)
    saturated = current_keywords[
        (current_keywords["frequency"] > median_freq * 3) &
        (current_keywords["opportunity_score"] < median_score * 0.5)
    ]
    trend_report["saturated_keywords"] = saturated.head(10).to_dict("records")

    # Compare with historical data if available
    if historical_data:
        historical_keywords = analyze_keywords(historical_data, top_n=100)
        rising = _find_rising_keywords(current_keywords, historical_keywords)
        trend_report["rising_keywords"] = rising

    # Price gap analysis
    trend_report["price_gaps"] = find_price_gaps(search_results)

    # Niche opportunities: keywords with high avg_price but low frequency
    niches = current_keywords[
        (current_keywords["avg_price"] > current_keywords["avg_price"].median() * 1.3) &
        (current_keywords["frequency"] < median_freq)
    ]
    trend_report["niche_opportunities"] = niches.head(10).to_dict("records")

    logger.info(
        f"Trends detected: {len(trend_report['high_opportunity_keywords'])} opportunities, "
        f"{len(trend_report['saturated_keywords'])} saturated, "
        f"{len(trend_report['niche_opportunities'])} niches"
    )

    return trend_report


def _find_rising_keywords(
    current: pd.DataFrame, historical: pd.DataFrame
) -> List[Dict]:
    """
    Find keywords that are rising in frequency compared to historical data.

    Returns:
        List of dicts with keyword, current_freq, historical_freq, growth_rate
    """
    rising = []

    current_dict = dict(zip(current["keyword"], current["frequency"]))
    historical_dict = dict(zip(historical["keyword"], historical["frequency"]))

    for keyword, curr_freq in current_dict.items():
        hist_freq = historical_dict.get(keyword, 0)

        if hist_freq == 0 and curr_freq >= 3:
            # New keyword appearing
            rising.append({
                "keyword": keyword,
                "current_frequency": curr_freq,
                "historical_frequency": 0,
                "growth_rate": float("inf"),
                "status": "new",
            })
        elif hist_freq > 0:
            growth_rate = (curr_freq - hist_freq) / hist_freq
            if growth_rate > 0.3:  # 30%+ growth
                rising.append({
                    "keyword": keyword,
                    "current_frequency": curr_freq,
                    "historical_frequency": hist_freq,
                    "growth_rate": round(growth_rate, 2),
                    "status": "rising",
                })

    # Sort by growth rate
    rising.sort(key=lambda x: x["growth_rate"] if x["growth_rate"] != float("inf") else 999, reverse=True)
    return rising[:20]


def generate_trend_summary(trend_report: Dict) -> str:
    """
    Generate a human-readable trend summary.

    Args:
        trend_report: Output from detect_trends()

    Returns:
        Formatted string summary
    """
    lines = []
    lines.append("=" * 60)
    lines.append("ETSY TREND REPORT")
    lines.append(f"Generated: {trend_report.get('timestamp', 'N/A')}")
    lines.append(f"Listings Analyzed: {trend_report.get('total_listings_analyzed', 0)}")
    lines.append("=" * 60)

    # High Opportunity Keywords
    opportunities = trend_report.get("high_opportunity_keywords", [])
    lines.append(f"\n{'='*40}")
    lines.append(f"TOP OPPORTUNITY KEYWORDS ({len(opportunities)})")
    lines.append(f"{'='*40}")
    for i, kw in enumerate(opportunities[:10], 1):
        lines.append(
            f"  {i:2d}. {kw['keyword']:<30} "
            f"Score: {kw['opportunity_score']:>8.2f} | "
            f"Freq: {kw['frequency']:>3d} | "
            f"Avg Price: ${kw['avg_price']:.2f}"
        )

    # Saturated Keywords (avoid these)
    saturated = trend_report.get("saturated_keywords", [])
    if saturated:
        lines.append(f"\n{'='*40}")
        lines.append(f"SATURATED KEYWORDS - AVOID ({len(saturated)})")
        lines.append(f"{'='*40}")
        for kw in saturated[:5]:
            lines.append(
                f"  - {kw['keyword']:<30} "
                f"Freq: {kw['frequency']:>3d} | "
                f"Low Score: {kw['opportunity_score']:.2f}"
            )

    # Niche Opportunities
    niches = trend_report.get("niche_opportunities", [])
    if niches:
        lines.append(f"\n{'='*40}")
        lines.append(f"NICHE OPPORTUNITIES ({len(niches)})")
        lines.append(f"{'='*40}")
        for kw in niches[:5]:
            lines.append(
                f"  - {kw['keyword']:<30} "
                f"Avg Price: ${kw['avg_price']:.2f} | "
                f"Freq: {kw['frequency']}"
            )

    # Price Gaps
    gaps = trend_report.get("price_gaps", [])
    if gaps:
        top_gaps = [g for g in gaps if g["gap_opportunity"] > 0.3][:5]
        if top_gaps:
            lines.append(f"\n{'='*40}")
            lines.append("PRICE GAPS (Under-served ranges)")
            lines.append(f"{'='*40}")
            for gap in top_gaps:
                lines.append(
                    f"  - {gap['price_range']:<20} "
                    f"Only {gap['listing_count']} listings | "
                    f"Opportunity: {gap['gap_opportunity']:.1%}"
                )

    # Rising Keywords
    rising = trend_report.get("rising_keywords", [])
    if rising:
        lines.append(f"\n{'='*40}")
        lines.append(f"RISING KEYWORDS ({len(rising)})")
        lines.append(f"{'='*40}")
        for kw in rising[:10]:
            growth = f"+{kw['growth_rate']:.0%}" if kw["growth_rate"] != float("inf") else "NEW"
            lines.append(
                f"  - {kw['keyword']:<30} {growth:>6} | "
                f"Current Freq: {kw['current_frequency']}"
            )

    lines.append(f"\n{'='*60}")
    return "\n".join(lines)


def combine_multiple_searches(search_results_list: List[Dict]) -> Dict:
    """
    Combine results from multiple search queries into one trend analysis.

    Args:
        search_results_list: List of search result dicts (each with 'query' and 'listings')

    Returns:
        Combined trend report
    """
    all_listings = []
    queries = []

    for result_set in search_results_list:
        if isinstance(result_set, dict):
            all_listings.extend(result_set.get("listings", []))
            queries.append(result_set.get("query", "unknown"))
        elif isinstance(result_set, list):
            all_listings.extend(result_set)

    trend_report = detect_trends(all_listings)
    trend_report["queries_combined"] = queries
    trend_report["total_listings_combined"] = len(all_listings)

    return trend_report
