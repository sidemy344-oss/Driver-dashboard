# Etsy Trend Hunter

A Python-based CLI tool that scrapes Etsy search results to extract trending keywords, best-selling t-shirt designs, competitor tags, and pricing data — with zero API costs.

## Features

- **Keyword Trend Discovery** — Scrape autocomplete suggestions and rank keywords by frequency
- **Best-Seller Analysis** — Extract titles, prices, reviews, tags from top listings
- **Competitor Tag Spy** — Deep-dive any listing for tags, pricing, and estimated revenue
- **Trend Report Generator** — Identify rising keywords, price gaps, and under-served niches
- **HTML Dashboard** — Mobile-friendly visual report with charts and tables
- **CSV Export** — All data exportable for further analysis

## Installation

```bash
# Clone and enter the project
cd etsy-trend-hunter

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Install Playwright for dynamic page scraping
playwright install chromium
```

## Quick Start

```bash
# Search for trending t-shirts (scrapes 3 pages = ~144 results)
python main.py search "funny t-shirt" --pages 3

# Analyze keywords from the results
python main.py keywords --input data/funny_t-shirt_2026-05-13_120000.csv --top 30

# Deep-dive a competitor listing
python main.py analyze-listing "https://www.etsy.com/listing/1234567890"

# Get autocomplete keyword suggestions
python main.py autocomplete "dog mom shirt"

# Run the complete pipeline (search + analyze + report)
python main.py full-report "vintage band tee" --pages 5

# Generate HTML dashboard from existing data
python main.py dashboard --data-dir data/ --output my_report.html
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `search` | Scrape Etsy search results and export to CSV |
| `analyze-listing` | Deep-dive analysis of a single listing |
| `keywords` | Analyze keyword frequency and opportunity scores |
| `autocomplete` | Get Etsy autocomplete suggestions |
| `dashboard` | Generate HTML dashboard from data |
| `full-report` | Run the complete pipeline in one command |

### Global Options

```bash
python main.py --verbose COMMAND  # Enable debug logging
python main.py --help             # Show all commands
python main.py COMMAND --help     # Show command options
```

## Configuration

Edit `config.py` to customize:

- **User-Agent rotation** — 5 desktop UAs rotated randomly
- **Rate limiting** — 2s base delay + 1-3s jitter between requests
- **Retry logic** — 3 retries with exponential backoff
- **Proxy support** — Set `PROXY` env var or edit config
- **Output directory** — Default: `data/`

### Proxy Setup

```bash
# Option 1: Environment variable
export PROXY="http://user:pass@proxy:port"

# Option 2: .env file
cp .env.example .env
# Edit .env with your proxy
```

## Output Files

All outputs go to the `data/` directory by default:

| File Pattern | Content |
|-------------|---------|
| `{query}_{timestamp}.csv` | Raw search results |
| `{query}_keywords_{timestamp}.csv` | Keyword analysis with scores |
| `competitor_report_{timestamp}.csv` | Competitor intelligence |
| `trend_report_{timestamp}.csv` | Trend detection results |
| `dashboard_{timestamp}.html` | Visual HTML report |

## How It Works

### Opportunity Score Formula

```
opportunity_score = (avg_price * avg_reviews) / (frequency ^ 1.5)
```

- **Higher score** = Better opportunity (good revenue, less competition)
- **High frequency + low score** = Saturated market (avoid)
- **Low frequency + high price** = Niche opportunity

### Anti-Detection Measures

1. Random User-Agent rotation (5 desktop browsers)
2. Rate limiting with random jitter (2-5s between requests)
3. Exponential backoff on 403/429 errors
4. Session cookie persistence
5. Playwright fallback for blocked requests

## Project Structure

```
etsy-trend-hunter/
├── main.py                 # CLI entry point (click-based)
├── config.py               # User settings & constants
├── scraper/
│   ├── etsy_search.py      # Search result scraping
│   ├── etsy_listing.py     # Individual listing scraping
│   └── autocomplete.py     # Autocomplete keyword extraction
├── analyzer/
│   ├── keywords.py         # Keyword frequency & opportunity analysis
│   ├── competitors.py      # Competitor comparison logic
│   └── trends.py           # Trend detection algorithms
├── reports/
│   ├── csv_exporter.py     # CSV generation
│   └── html_dashboard.py   # HTML report generation
├── templates/
│   └── dashboard.html      # Jinja2 dashboard template
├── data/                   # Output folder (gitignored)
├── requirements.txt
├── .env.example
└── .gitignore
```

## Requirements

- Python 3.11+
- See `requirements.txt` for all dependencies

## Disclaimer

This tool is for educational and research purposes. Always respect Etsy's Terms of Service and robots.txt. Use responsibly with appropriate rate limiting.

## License

MIT
