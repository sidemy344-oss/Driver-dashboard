"""
HTML Dashboard Generator
Generates a mobile-friendly HTML report from trend analysis data.
"""

import os
import logging
from typing import Dict, Optional, List
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import DEFAULT_OUTPUT_DIR, DASHBOARD_TEMPLATE

logger = logging.getLogger(__name__)

# Base directory for templates (relative to project root)
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")


def generate_dashboard(
    trend_data: Dict,
    keyword_df=None,
    search_results: Optional[List[Dict]] = None,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate an HTML dashboard from analysis data.

    Args:
        trend_data: Trend report from trends.detect_trends()
        keyword_df: Keyword analysis DataFrame (optional)
        search_results: Raw search results for additional stats
        output_path: Output file path (default: data/report.html)

    Returns:
        Path to generated HTML file
    """
    if output_path is None:
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"dashboard_{timestamp}.html")

    # Prepare template data
    template_data = _prepare_template_data(trend_data, keyword_df, search_results)

    # Render template
    try:
        env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template("dashboard.html")
        html_content = template.render(**template_data)
    except Exception as e:
        logger.warning(f"Template rendering failed ({e}), using inline template")
        html_content = _render_inline_template(template_data)

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"Dashboard generated: {output_path}")
    return output_path


def _prepare_template_data(
    trend_data: Dict, keyword_df=None, search_results: Optional[List[Dict]] = None
) -> Dict:
    """Prepare all data for the template context."""
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_listings": trend_data.get("total_listings_analyzed", 0),
        "queries": trend_data.get("queries_combined", []),
    }

    # Top keywords
    opportunities = trend_data.get("high_opportunity_keywords", [])
    data["top_keywords"] = opportunities[:20]

    # Saturated keywords
    data["saturated_keywords"] = trend_data.get("saturated_keywords", [])[:10]

    # Niche opportunities
    data["niche_opportunities"] = trend_data.get("niche_opportunities", [])[:10]

    # Price gaps
    data["price_gaps"] = trend_data.get("price_gaps", [])[:10]

    # Rising keywords
    data["rising_keywords"] = trend_data.get("rising_keywords", [])[:10]

    # Price distribution for chart
    if search_results:
        prices = [r.get("price", 0) for r in search_results if r.get("price", 0) > 0]
        data["price_stats"] = {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
            "avg": round(sum(prices) / len(prices), 2) if prices else 0,
            "count": len(prices),
        }
        # Price buckets for chart
        data["price_distribution"] = _calculate_price_distribution(prices)
    else:
        data["price_stats"] = {"min": 0, "max": 0, "avg": 0, "count": 0}
        data["price_distribution"] = []

    # Keyword DataFrame stats
    if keyword_df is not None and not keyword_df.empty:
        data["keyword_count"] = len(keyword_df)
        data["keyword_table"] = keyword_df.head(20).to_dict("records")
    else:
        data["keyword_count"] = len(opportunities)
        data["keyword_table"] = opportunities[:20]

    return data


def _calculate_price_distribution(prices: List[float]) -> List[Dict]:
    """Calculate price distribution for chart rendering."""
    if not prices:
        return []

    min_p = min(prices)
    max_p = max(prices)
    bucket_count = min(10, len(set(prices)))

    if bucket_count <= 1 or max_p == min_p:
        return [{"range": f"${min_p:.0f}", "count": len(prices)}]

    bucket_size = (max_p - min_p) / bucket_count
    buckets = []

    for i in range(bucket_count):
        low = min_p + i * bucket_size
        high = low + bucket_size
        count = sum(1 for p in prices if low <= p < high or (i == bucket_count - 1 and p == high))
        buckets.append({
            "range": f"${low:.0f}-${high:.0f}",
            "count": count,
            "percentage": round(count / len(prices) * 100, 1) if prices else 0,
        })

    return buckets


def _render_inline_template(data: Dict) -> str:
    """Fallback: render dashboard with inline HTML template."""
    # Build keyword rows
    keyword_rows = ""
    for i, kw in enumerate(data.get("keyword_table", []), 1):
        keyword_rows += f"""
        <tr>
            <td>{i}</td>
            <td><strong>{kw.get('keyword', 'N/A')}</strong></td>
            <td>{kw.get('frequency', 0)}</td>
            <td>${kw.get('avg_price', 0):.2f}</td>
            <td>{kw.get('avg_reviews', 0):.1f}</td>
            <td><span class="score">{kw.get('opportunity_score', 0):.2f}</span></td>
        </tr>"""

    # Build price distribution bars
    price_bars = ""
    for bucket in data.get("price_distribution", []):
        price_bars += f"""
        <div class="bar-row">
            <span class="bar-label">{bucket['range']}</span>
            <div class="bar" style="width: {min(bucket['percentage'] * 3, 100)}%"></div>
            <span class="bar-value">{bucket['count']}</span>
        </div>"""

    # Build niche cards
    niche_cards = ""
    for niche in data.get("niche_opportunities", []):
        niche_cards += f"""
        <div class="card">
            <h4>{niche.get('keyword', 'N/A')}</h4>
            <p>Avg Price: ${niche.get('avg_price', 0):.2f} | Freq: {niche.get('frequency', 0)}</p>
        </div>"""

    queries_str = ", ".join(data.get("queries", [])) or "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Etsy Trend Hunter - Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        header {{ background: linear-gradient(135deg, #f76b1c, #e94e77); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; }}
        header h1 {{ font-size: 2em; margin-bottom: 8px; }}
        header p {{ opacity: 0.9; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }}
        .stat-card .number {{ font-size: 2em; font-weight: bold; color: #e94e77; }}
        .stat-card .label {{ color: #666; font-size: 0.9em; }}
        .section {{ background: white; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .section h2 {{ color: #333; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #f76b1c; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f9f9f9; font-weight: 600; color: #555; }}
        tr:hover {{ background: #fafafa; }}
        .score {{ background: #e94e77; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.85em; font-weight: bold; }}
        .bar-row {{ display: flex; align-items: center; margin: 8px 0; }}
        .bar-label {{ min-width: 100px; font-size: 0.85em; color: #666; }}
        .bar {{ height: 24px; background: linear-gradient(90deg, #f76b1c, #e94e77); border-radius: 4px; margin: 0 10px; transition: width 0.3s; }}
        .bar-value {{ font-size: 0.85em; font-weight: bold; color: #333; }}
        .cards-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }}
        .card {{ background: #f9f9f9; padding: 16px; border-radius: 8px; border-left: 4px solid #f76b1c; }}
        .card h4 {{ color: #333; margin-bottom: 4px; }}
        .card p {{ color: #666; font-size: 0.9em; }}
        footer {{ text-align: center; padding: 20px; color: #999; font-size: 0.85em; }}
        @media (max-width: 768px) {{
            .container {{ padding: 12px; }}
            header {{ padding: 20px; }}
            header h1 {{ font-size: 1.5em; }}
            table {{ font-size: 0.8em; }}
            th, td {{ padding: 6px 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Etsy Trend Hunter</h1>
            <p>Generated: {data['generated_at']} | Queries: {queries_str}</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="number">{data['total_listings']}</div>
                <div class="label">Listings Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="number">{data['keyword_count']}</div>
                <div class="label">Keywords Found</div>
            </div>
            <div class="stat-card">
                <div class="number">${data['price_stats']['avg']:.2f}</div>
                <div class="label">Avg Price</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(data.get('niche_opportunities', []))}</div>
                <div class="label">Niche Opportunities</div>
            </div>
        </div>

        <div class="section">
            <h2>Top 20 Trending Keywords</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Keyword</th>
                        <th>Frequency</th>
                        <th>Avg Price</th>
                        <th>Avg Reviews</th>
                        <th>Opportunity Score</th>
                    </tr>
                </thead>
                <tbody>
                    {keyword_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Price Distribution</h2>
            {price_bars if price_bars else '<p>No price data available.</p>'}
        </div>

        <div class="section">
            <h2>Niche Opportunities</h2>
            <div class="cards-grid">
                {niche_cards if niche_cards else '<p>No niche opportunities detected.</p>'}
            </div>
        </div>

        <footer>
            <p>Etsy Trend Hunter &mdash; T-Shirt Design Intelligence Tool</p>
        </footer>
    </div>
</body>
</html>"""

    return html
