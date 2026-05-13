#!/usr/bin/env python3
"""
Etsy Trend Hunter - CLI Entry Point
A Python-based CLI tool that scrapes Etsy search results to extract trending keywords,
best-selling t-shirt designs, competitor tags, and pricing data.
"""

import os
import sys
import json
import logging
from datetime import datetime

import click

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_OUTPUT_DIR


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose/debug logging")
def cli(verbose):
    """Etsy Trend Hunter - T-Shirt Design Intelligence Tool

    Scrape Etsy search results to find trending keywords, analyze competitors,
    and discover profitable niches for t-shirt designs.
    """
    setup_logging(verbose)


@cli.command()
@click.argument("query")
@click.option("--pages", "-p", default=3, help="Number of pages to scrape (48 results/page)")
@click.option("--output", "-o", default=None, help="Output CSV filename")
@click.option("--output-dir", "-d", default=None, help="Output directory")
def search(query, pages, output, output_dir):
    """Search Etsy and export results to CSV.

    Example: python main.py search "funny t-shirt" --pages 5
    """
    from scraper.etsy_search import search_etsy
    from reports.csv_exporter import export_search_results

    click.echo(f"Searching Etsy for: '{query}' ({pages} pages)...")
    click.echo("This may take a moment due to rate limiting...\n")

    listings = search_etsy(query, pages=pages)

    if not listings:
        click.echo("No listings found. Etsy may be blocking requests.", err=True)
        click.echo("Try reducing pages or using a proxy (see config.py).", err=True)
        sys.exit(1)

    click.echo(f"Found {len(listings)} listings!")

    # Export to CSV
    filepath = export_search_results(
        listings, filename=output, output_dir=output_dir, query=query
    )
    click.echo(f"Results saved to: {filepath}")

    # Quick stats
    prices = [l["price"] for l in listings if l.get("price", 0) > 0]
    if prices:
        click.echo(f"\nQuick Stats:")
        click.echo(f"  Price Range: ${min(prices):.2f} - ${max(prices):.2f}")
        click.echo(f"  Average Price: ${sum(prices)/len(prices):.2f}")
        avg_reviews = sum(l.get("review_count", 0) for l in listings) / len(listings)
        click.echo(f"  Average Reviews: {avg_reviews:.0f}")


@cli.command("analyze-listing")
@click.argument("url")
@click.option("--output", "-o", default=None, help="Output CSV filename")
@click.option("--json-output", "-j", is_flag=True, help="Also save as JSON")
def analyze_listing(url, output, json_output):
    """Deep-dive analysis of a single Etsy listing.

    Example: python main.py analyze-listing "https://www.etsy.com/listing/12345"
    """
    from analyzer.competitors import analyze_competitor
    from reports.csv_exporter import export_competitor_report

    click.echo(f"Analyzing listing: {url}")
    click.echo("Fetching listing details and finding similar items...\n")

    analysis = analyze_competitor(url)

    if "error" in analysis:
        click.echo(f"Error: {analysis['error']}", err=True)
        sys.exit(1)

    # Display results
    target = analysis.get("target_listing", {})
    click.echo(f"Title: {target.get('title', 'N/A')}")
    click.echo(f"Price: ${target.get('price', 0):.2f}")
    click.echo(f"Reviews: {target.get('total_reviews', 0)}")
    click.echo(f"In Carts: {target.get('in_cart_count', 0)}")
    click.echo(f"Est. Monthly Revenue: ${target.get('estimated_monthly_revenue', 0):.2f}")

    # Tags
    tags = target.get("tags", [])
    click.echo(f"\nTags ({len(tags)}):")
    for tag in tags[:15]:
        click.echo(f"  - {tag}")

    # Tag analysis
    tag_analysis = analysis.get("tag_analysis", {})
    categories = tag_analysis.get("tag_categories", {})
    if categories:
        click.echo(f"\nTag Strategy:")
        for cat, cat_tags in categories.items():
            click.echo(f"  {cat.title()}: {', '.join(cat_tags[:5])}")

    # Price positioning
    pricing = analysis.get("price_positioning", {})
    click.echo(f"\nPrice Position: {pricing.get('position', 'N/A').upper()}")
    click.echo(f"  Market Avg: ${pricing.get('market_avg_price', 0):.2f}")
    click.echo(f"  Percentile: {pricing.get('price_percentile', 0):.0f}th")

    # Competitor summary
    summary = analysis.get("competitor_summary", {})
    strengths = summary.get("strengths", [])
    weaknesses = summary.get("weaknesses", [])
    if strengths:
        click.echo(f"\nStrengths:")
        for s in strengths:
            click.echo(f"  + {s}")
    if weaknesses:
        click.echo(f"\nWeaknesses:")
        for w in weaknesses:
            click.echo(f"  - {w}")

    # Export
    filepath = export_competitor_report(analysis, filename=output)
    click.echo(f"\nReport saved to: {filepath}")

    if json_output:
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        json_path = os.path.join(DEFAULT_OUTPUT_DIR, f"listing_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(json_path, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        click.echo(f"JSON saved to: {json_path}")


@cli.command()
@click.option("--input", "-i", "input_file", required=True, help="Input CSV file with search results")
@click.option("--top", "-t", default=50, help="Number of top keywords to return")
@click.option("--output", "-o", default=None, help="Output CSV filename")
def keywords(input_file, top, output):
    """Analyze keywords from search results CSV.

    Example: python main.py keywords --input data/results.csv --top 50
    """
    from analyzer.keywords import analyze_keywords_from_csv, get_keyword_summary
    from reports.csv_exporter import export_keyword_analysis

    if not os.path.exists(input_file):
        click.echo(f"Error: File not found: {input_file}", err=True)
        sys.exit(1)

    click.echo(f"Analyzing keywords from: {input_file}")

    df = analyze_keywords_from_csv(input_file, top_n=top)

    if df.empty:
        click.echo("No keywords found in the input data.", err=True)
        sys.exit(1)

    # Display top keywords
    click.echo(f"\nTop {min(top, len(df))} Keywords by Opportunity Score:\n")
    click.echo(f"{'#':<4} {'Keyword':<35} {'Freq':<6} {'Avg $':<8} {'Reviews':<9} {'Score':<8}")
    click.echo("-" * 72)

    for i, row in df.iterrows():
        click.echo(
            f"{i+1:<4} {row['keyword']:<35} {row['frequency']:<6} "
            f"${row['avg_price']:<7.2f} {row['avg_reviews']:<9.1f} {row['opportunity_score']:<8.2f}"
        )

    # Summary
    summary = get_keyword_summary(df)
    click.echo(f"\nSummary:")
    click.echo(f"  Total unique keywords: {summary['total_keywords']}")
    click.echo(f"  Top keyword: {summary['top_keyword']}")
    click.echo(f"  Avg price across all: ${summary['avg_price_all']:.2f}")
    click.echo(f"  High-opportunity keywords: {summary['high_opportunity_count']}")

    # Export
    filepath = export_keyword_analysis(df, filename=output)
    click.echo(f"\nKeyword analysis saved to: {filepath}")


@cli.command()
@click.option("--data-dir", "-d", default=DEFAULT_OUTPUT_DIR, help="Directory with data files")
@click.option("--output", "-o", default=None, help="Output HTML file path")
@click.option("--input", "-i", "input_file", default=None, help="Specific CSV to use")
def dashboard(data_dir, output, input_file):
    """Generate an HTML dashboard from analysis data.

    Example: python main.py dashboard --data-dir data/ --output report.html
    """
    import pandas as pd
    from analyzer.trends import detect_trends
    from reports.html_dashboard import generate_dashboard

    click.echo("Generating HTML dashboard...")

    # Load data from CSV files
    search_results = []

    if input_file and os.path.exists(input_file):
        df = pd.read_csv(input_file)
        search_results = df.to_dict("records")
    elif os.path.exists(data_dir):
        # Find most recent search results CSV
        csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv") and "keyword" not in f.lower()]
        if csv_files:
            csv_files.sort(reverse=True)
            latest = os.path.join(data_dir, csv_files[0])
            click.echo(f"Using: {latest}")
            df = pd.read_csv(latest)
            search_results = df.to_dict("records")

    if not search_results:
        click.echo("No data files found. Run a search first:", err=True)
        click.echo('  python main.py search "your query" --pages 3', err=True)
        sys.exit(1)

    # Generate trend analysis
    trend_data = detect_trends(search_results)

    # Generate dashboard
    output_path = generate_dashboard(
        trend_data=trend_data,
        search_results=search_results,
        output_path=output,
    )

    click.echo(f"Dashboard generated: {output_path}")
    click.echo("Open in your browser to view the report.")


@cli.command()
@click.argument("seed_keyword")
@click.option("--output", "-o", default=None, help="Output CSV filename")
def autocomplete(seed_keyword, output):
    """Get Etsy autocomplete suggestions for a keyword.

    Example: python main.py autocomplete "dog mom shirt"
    """
    from scraper.autocomplete import get_autocomplete_suggestions
    from reports.csv_exporter import export_autocomplete_results

    click.echo(f"Getting autocomplete suggestions for: '{seed_keyword}'")

    suggestions = get_autocomplete_suggestions(seed_keyword)

    if not suggestions:
        click.echo("No suggestions found. Etsy may be blocking or the keyword has no suggestions.")
        sys.exit(1)

    click.echo(f"\nFound {len(suggestions)} suggestions:\n")
    for i, suggestion in enumerate(suggestions, 1):
        click.echo(f"  {i:2d}. {suggestion}")

    # Export
    data = {seed_keyword: suggestions}
    filepath = export_autocomplete_results(data, filename=output)
    click.echo(f"\nSuggestions saved to: {filepath}")


@cli.command("full-report")
@click.argument("query")
@click.option("--pages", "-p", default=3, help="Number of pages to scrape")
@click.option("--output", "-o", default=None, help="Output HTML filename")
@click.option("--csv/--no-csv", default=True, help="Also export CSV files")
def full_report(query, pages, output, csv):
    """Run the complete pipeline: search, analyze, and generate report.

    Example: python main.py full-report "vintage t-shirt" --pages 3
    """
    from scraper.etsy_search import search_etsy
    from scraper.autocomplete import get_autocomplete_suggestions
    from analyzer.keywords import analyze_keywords
    from analyzer.trends import detect_trends
    from reports.csv_exporter import export_search_results, export_keyword_analysis, export_trend_report
    from reports.html_dashboard import generate_dashboard

    click.echo("=" * 60)
    click.echo("ETSY TREND HUNTER - FULL REPORT")
    click.echo(f"Query: '{query}' | Pages: {pages}")
    click.echo("=" * 60)

    # Step 1: Search
    click.echo(f"\n[1/5] Searching Etsy for '{query}'...")
    listings = search_etsy(query, pages=pages)

    if not listings:
        click.echo("No listings found. Aborting.", err=True)
        sys.exit(1)

    click.echo(f"      Found {len(listings)} listings")

    # Step 2: Autocomplete suggestions
    click.echo(f"\n[2/5] Getting autocomplete suggestions...")
    suggestions = get_autocomplete_suggestions(query)
    click.echo(f"      Found {len(suggestions)} suggestions")

    # Step 3: Keyword analysis
    click.echo(f"\n[3/5] Analyzing keywords...")
    keyword_df = analyze_keywords(listings, top_n=50)
    click.echo(f"      Extracted {len(keyword_df)} keywords")

    # Step 4: Trend detection
    click.echo(f"\n[4/5] Detecting trends...")
    trend_data = detect_trends(listings)
    opportunities = len(trend_data.get("high_opportunity_keywords", []))
    niches = len(trend_data.get("niche_opportunities", []))
    click.echo(f"      {opportunities} opportunities, {niches} niches found")

    # Step 5: Generate reports
    click.echo(f"\n[5/5] Generating reports...")

    if csv:
        csv_path = export_search_results(listings, query=query)
        click.echo(f"      CSV (search): {csv_path}")

        kw_path = export_keyword_analysis(keyword_df, query=query)
        click.echo(f"      CSV (keywords): {kw_path}")

        trend_path = export_trend_report(trend_data)
        click.echo(f"      CSV (trends): {trend_path}")

    # HTML Dashboard
    html_path = generate_dashboard(
        trend_data=trend_data,
        keyword_df=keyword_df,
        search_results=listings,
        output_path=output,
    )
    click.echo(f"      HTML Dashboard: {html_path}")

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("REPORT COMPLETE")
    click.echo("=" * 60)

    prices = [l["price"] for l in listings if l.get("price", 0) > 0]
    if prices:
        click.echo(f"\n  Listings Analyzed: {len(listings)}")
        click.echo(f"  Price Range: ${min(prices):.2f} - ${max(prices):.2f}")
        click.echo(f"  Average Price: ${sum(prices)/len(prices):.2f}")
        click.echo(f"  Keywords Found: {len(keyword_df)}")
        click.echo(f"  Opportunities: {opportunities}")
        click.echo(f"  Niche Ideas: {niches}")

    if not keyword_df.empty:
        click.echo(f"\n  Top 5 Opportunity Keywords:")
        for i, row in keyword_df.head(5).iterrows():
            click.echo(f"    {i+1}. {row['keyword']} (score: {row['opportunity_score']:.2f})")

    click.echo(f"\n  Open the dashboard: {html_path}")


if __name__ == "__main__":
    cli()
