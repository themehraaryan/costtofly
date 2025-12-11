# Flight Fare Scraper & Analyzer
## Project Design Document

---

## 1. Executive Summary

**Flight Fare Scraper & Analyzer** is a Python-based data pipeline tool that automates flight fare data collection from MakeMyTrip, performs statistical analysis using pandas and NumPy, and generates insightful visualizations using Matplotlib. The tool enables users to compare flight options across airlines, departure times, and pricing strategies in real-time.

**Purpose:** Extract, analyze, and visualize flight booking data to help users identify patterns in pricing, airline competition, and travel options.

**Tech Stack:** Python 3.8+, Selenium, BeautifulSoup4, Pandas, NumPy, Matplotlib, Requests

**Status:** In Development (Data Extraction Phase Complete)

---

## 2. Project Scope

### 2.1 Features

#### Core Features
- **User Input Interface** - CLI-based prompt for origin, destination, journey date, and optional cabin class
- **Web Scraping** - Selenium-based automation to fetch dynamic flight search results from MakeMyTrip
- **HTML Parsing** - BeautifulSoup4 to extract structured flight data from raw HTML
- **Data Cleaning & Transformation** - Pandas/NumPy to normalize, validate, and enrich extracted data
- **Statistical Analysis** - Compute key metrics: cheapest flights, fastest routes, airline comparisons, price trends
- **Data Visualization** - Matplotlib charts for price distribution, airline comparison, departure time analysis
- **Recommendation Engine** - Simple logic to rank flights by user-defined criteria (price, speed, stops)
- **CSV Export** - Save processed results to downloadable spreadsheet format
- **Error Handling** - Graceful failures for network issues, layout changes, no results scenarios

#### Advanced Features (Phase 2)
- Historical price tracking (database storage for trend analysis)
- Multi-city itinerary support
- Real-time price alerts
- Coupon/discount aggregation and recommendation
- API endpoint (Flask/FastAPI) for programmatic access

### 2.2 Out of Scope
- Mobile app (web-based only)
- Booking integration (view-only, no purchase transactions)
- ML-based price prediction (statistical analysis only)
- Multi-site scraping (MakeMyTrip only for MVP)
- Payment integration

---

## 3. Data Model

### 3.1 Flight Record Structure

Each extracted flight is represented as a dictionary/DataFrame row:

```python
{
    "flight_id": str,              # Unique identifier from website
    "airline": str,                # e.g., "IndiGo", "Air India"
    "flight_code": str,            # e.g., "6E 6622", "AI 3361"
    "departure_time": str,         # HH:MM format, e.g., "18:00"
    "departure_city": str,         # e.g., "New Delhi"
    "departure_airport": str,      # IATA code or full name
    "arrival_time": str,           # HH:MM format, e.g., "20:55"
    "arrival_city": str,           # e.g., "Bengaluru"
    "arrival_airport": str,        # IATA code or full name
    "duration_minutes": int,       # Total flight time in minutes (e.g., 175)
    "stops": int,                  # 0 for non-stop, 1 for 1 stop, etc.
    "stop_details": str,           # e.g., "Non stop" or "1 stop via Bhopal"
    "price_per_adult": int,        # Base fare in INR (e.g., 16058)
    "lock_price_from": float,      # Price-lock feature cost (e.g., 937)
    "cabin_class": str,            # "economy", "business" (if available)
    "offers": str,                 # Coupon/discount text
    "nearby_airport": bool,        # True if departure from nearby city (e.g., Ghaziabad for Delhi)
    "search_date": str,            # YYYY-MM-DD of search
    "journey_date": str,           # YYYY-MM-DD of requested flight date
}
```

### 3.2 Aggregated Metrics

```python
{
    "min_price": int,              # Cheapest fare across all results
    "max_price": int,              # Most expensive fare
    "avg_price": float,            # Mean fare
    "median_price": float,         # Median fare
    "price_range": str,            # e.g., "₹ 13,614 - ₹ 28,200" (from page filter)
    "cheapest_airline": str,       # Airline with lowest avg price
    "fastest_route": str,          # Route/airline with shortest duration
    "non_stop_count": int,         # Number of non-stop flights
    "one_stop_count": int,         # Number of flights with 1 stop
    "total_results": int,          # Total flights found
}
```

---

## 4. Architecture & Components

### 4.1 System Architecture

```
User Input (CLI)
    ↓
Selenium Web Driver → MakeMyTrip Search
    ↓
Raw HTML Page
    ↓
BeautifulSoup Parser → Structured Data
    ↓
Pandas DataFrame (Cleaning & Transformation)
    ↓
NumPy Analysis (Statistics & Aggregation)
    ↓
Matplotlib Visualization
    ↓
CSV Export + Console Output
```

### 4.2 Module Breakdown

#### Module 1: `flight_scraper.py` (Web Scraping)
**Responsibility:** Fetch flight search results using Selenium

**Key Functions:**
- `initialize_selenium_driver()` - Launch Chrome/Firefox with MakeMyTrip
- `build_search_url(origin, destination, date, cabin_class)` - Construct search URL
- `fetch_flight_page(url)` - Navigate to URL, wait for dynamic content load
- `get_raw_html()` - Extract full page HTML after JavaScript render
- `close_driver()` - Cleanup and close browser

**Output:** Raw HTML string

---

#### Module 2: `parser.py` (HTML Parsing)
**Responsibility:** Extract structured data from raw HTML using BeautifulSoup

**Key Functions:**
- `parse_flight_cards(html_string)` - Identify all `div[data-test="component-clusterItem"]` card elements
- `extract_airline_info(card)` - Get airline name and flight code from card
- `extract_timing_info(card)` - Parse departure/arrival times and cities
- `extract_duration_stops(card)` - Parse flight duration and layover details
- `extract_price_info(card)` - Get base price and lock-price from price block
- `extract_offers(card)` - Capture coupon codes and discount text
- `build_flight_record(card)` - Combine all extracted fields into single dict
- `parse_page_metadata(html_string)` - Extract page-level filters (min/max price, coupons)

**Output:** List of flight dicts + metadata dict

---

#### Module 3: `processor.py` (Data Cleaning & Transformation)
**Responsibility:** Clean, validate, and enrich extracted data using Pandas/NumPy

**Key Functions:**
- `create_dataframe(flight_list)` - Convert list of dicts to Pandas DataFrame
- `clean_price_column(series)` - Remove `₹` and commas, convert to integer
- `parse_duration_to_minutes(series)` - Convert "02 h 55 m" to integer minutes
- `parse_time_to_datetime(series)` - Convert "18:00" strings to time objects
- `add_derived_columns(df)` - Create new columns:
  - `departure_hour` (0-23)
  - `departure_bucket` ("morning", "afternoon", "evening", "night")
  - `price_per_minute` (price divided by duration)
  - `is_non_stop` (boolean)
- `remove_duplicates(df)` - Drop duplicate flights by flight code + time
- `validate_data(df)` - Check for missing required fields, data type mismatches
- `sort_and_rank(df, sort_by)` - Sort by price, duration, stops, airline

**Output:** Cleaned Pandas DataFrame ready for analysis

---

#### Module 4: `analyzer.py` (Statistical Analysis)
**Responsibility:** Compute metrics and insights using NumPy and Pandas

**Key Functions:**
- `compute_price_stats(df)` - Return min, max, mean, median, std dev prices
- `cheapest_flights(df, top_n=5)` - Return N cheapest options
- `fastest_flights(df, top_n=5)` - Return N shortest duration options
- `compare_airlines(df)` - Average price, cheapest, fastest per airline
- `stops_analysis(df)` - Count and avg price per stop type
- `departure_time_analysis(df)` - Avg price per departure bucket (morning/afternoon/evening/night)
- `price_by_duration_correlation(df)` - Compute correlation between flight duration and price
- `best_value_flights(df)` - Rank flights by custom scoring (price + duration + stops)
- `generate_summary_report(df, metadata)` - Produce text summary with all key insights

**Output:** Dict of computed metrics and text report

---

#### Module 5: `visualizer.py` (Matplotlib Charts)
**Responsibility:** Generate publication-ready charts

**Key Functions:**
- `plot_price_distribution(df)` - Histogram of prices across all flights
- `plot_price_by_airline(df)` - Bar chart: average price per airline
- `plot_price_by_departure_time(df)` - Scatter/line plot: departure time vs price
- `plot_duration_distribution(df)` - Histogram of flight durations
- `plot_stops_comparison(df)` - Bar chart: avg price for non-stop vs 1-stop
- `plot_price_per_minute(df)` - Scatter: flight duration vs price (efficiency metric)
- `create_dashboard(df, metadata)` - Multi-subplot figure with 4-6 key charts

**Output:** PNG/PDF files + display in Matplotlib window

---

#### Module 6: `exporter.py` (Data Export)
**Responsibility:** Save results to disk in multiple formats

**Key Functions:**
- `export_to_csv(df, filename)` - Save DataFrame to CSV
- `export_summary_json(metadata, report, filename)` - Save analysis results to JSON
- `generate_report_txt(report, filename)` - Save text summary to file
- `export_charts_to_pdf(charts, filename)` - Save all visualizations as PDF

**Output:** CSV, JSON, TXT, PDF files in `./output/` directory

---

#### Module 7: `main.py` (Orchestration & CLI)
**Responsibility:** User interface and workflow orchestration

**Key Functions:**
- `prompt_user_inputs()` - CLI prompts for origin, destination, date, class
- `validate_inputs(origin, destination, date)` - Check format and validity
- `run_full_pipeline()` - Execute all steps in sequence:
  1. Scrape
  2. Parse
  3. Clean
  4. Analyze
  5. Visualize
  6. Export
- `display_results(report, df_sample)` - Pretty-print summary and top flights to console
- `main()` - Entry point

**Output:** Console output + saved files

---

### 4.3 Data Flow Diagram

```
CLI Input (origin, dest, date, class)
    ↓
Selenium Scraper → MakeMyTrip → HTML
    ↓
BeautifulSoup Parser → List[Dict]
    ↓
Pandas DataFrame
    ↓
Cleaner → Validated DF
    ↓
Analyzer → Metrics Dict + Report
    ↓
Visualizer → PNG/PDF Charts
    ↓
Exporter → CSV + JSON + TXT
    ↓
Console Output + File Summary
```

---

## 5. Data Extraction Strategy

### 5.1 Target Selectors (BeautifulSoup)

**Flight Card Container:**
```python
cards = soup.select('div[data-test="component-clusterItem"]')
```

**Within Each Card:**
| Field | Selector | Example |
|-------|----------|---------|
| Airline | `p.airlineName` | "IndiGo" |
| Flight Code | `p.fliCode` | "6E 6622" |
| Dep Time | `.timeInfoLeft .flightTimeInfo span` | "18:00" |
| Dep City | `.timeInfoLeft .blackText` | "New Delhi" |
| Arr Time | `.timeInfoRight .flightTimeInfo span` | "20:55" |
| Arr City | `.timeInfoRight .blackText` | "Bengaluru" |
| Duration | `.stop-info > p` (first child) | "02 h 55 m" |
| Stops | `.flightsLayoverInfo` | "Non stop" or "1 stop via Bhopal" |
| Price | `.clusterViewPrice span.fontSize18` | "₹ 16,058" |
| Lock Price | `.lockPriceTrigger .fontSize12.boldFont.blueText` | "Lock this price starting from ₹ 937" |
| Offers | `.alertMsg span` | "FLAT ₹ 100 OFF using MMTSUPER…" |

### 5.2 Error Handling in Parsing

```python
def safe_extract(card, selector, default="N/A"):
    """Extract text from selector, return default if not found"""
    element = card.select_one(selector)
    return element.get_text(strip=True) if element else default
```

---

## 6. Algorithms & Analysis

### 6.1 Best Value Scoring

A flight's "value score" balances price, duration, and convenience:

```
score = (1 - (price / max_price)) * 40
       + (1 - (duration / max_duration)) * 30
       + (1 - (stops / max_stops)) * 30

Flights ranked by score (higher is better)
```

### 6.2 Price Correlation Analysis

Compute Pearson correlation between flight duration and price:
- Positive correlation: longer flights tend to be more expensive
- Negative correlation: longer flights are cheaper
- Near zero: duration and price independent

### 6.3 Outlier Detection (Optional)

Flag flights whose price is >2 standard deviations from mean (potential errors or premium services).

---

## 7. Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Scraping** | Selenium | 4.x | Browser automation for dynamic content |
| **Parsing** | BeautifulSoup4 | 4.11+ | HTML parsing and CSS selectors |
| **HTTP** | Requests | 2.28+ | Fallback for static requests |
| **Data** | Pandas | 1.5+ | DataFrame manipulation, cleaning |
| **Math** | NumPy | 1.23+ | Numerical operations, statistics |
| **Viz** | Matplotlib | 3.6+ | Charting and visualizations |
| **CLI** | argparse / Click | Built-in / 8.x | Command-line interface |
| **Testing** | unittest / pytest | Built-in / 7.x | Unit and integration tests |
| **Logging** | logging | Built-in | Error tracking and debugging |

---

## 8. Implementation Timeline

### Phase 1: MVP (Weeks 1-3)
- [x] Selenium scraper setup
- [x] HTML extraction (raw HTML saved)
- [ ] BeautifulSoup parser implementation
- [ ] Pandas cleaner + basic validation
- [ ] Basic NumPy statistics
- [ ] 3 key Matplotlib charts (price dist, airline comparison, time vs price)
- [ ] CSV export
- [ ] CLI interface
- [ ] Error handling & logging

### Phase 2: Polish (Weeks 4-5)
- [ ] Comprehensive unit tests
- [ ] README with examples
- [ ] Sample output screenshots
- [ ] Resume/portfolio documentation
- [ ] Optional: price history tracking (DB)

### Phase 3: Future (Optional)
- [ ] API endpoint (Flask)
- [ ] Multi-city support
- [ ] Real-time price alerts
- [ ] Coupon recommendation engine
- [ ] Web dashboard (Streamlit)

---

## 9. File Structure

```
flight-scraper/
├── README.md                    # Project overview and usage guide
├── requirements.txt             # Python dependencies
├── config.py                    # Configuration (URLs, selectors, headers)
├── main.py                      # Entry point and CLI orchestration
├── flight_scraper.py            # Selenium web scraper
├── parser.py                    # BeautifulSoup HTML parser
├── processor.py                 # Data cleaning and transformation
├── analyzer.py                  # Statistical analysis
├── visualizer.py                # Matplotlib charts
├── exporter.py                  # CSV/JSON/PDF export
├── utils.py                     # Helper functions (logging, validation)
├── tests/
│   ├── test_parser.py           # Unit tests for parser
│   ├── test_processor.py        # Unit tests for processor
│   ├── test_analyzer.py         # Unit tests for analyzer
│   └── sample_html.html         # Sample HTML for testing
├── output/                      # Generated files (CSV, charts, reports)
│   ├── flights_2025-12-11.csv
│   ├── analysis_report.json
│   ├── charts.pdf
│   └── summary.txt
├── logs/                        # Application logs
│   └── scraper.log
└── .gitignore                   # Git ignore file
```

---

## 10. Usage Example

### Command Line

```bash
# Basic search
python main.py --from DEL --to BOM --date 2025-12-20

# With cabin class
python main.py --from DEL --to BOM --date 2025-12-20 --class economy

# With export options
python main.py --from DEL --to BOM --date 2025-12-20 --save-csv --show-charts --format pdf

# Verbose logging
python main.py --from DEL --to BOM --date 2025-12-20 --debug
```

### Python API (Future)

```python
from flight_scraper import FlightScraper

scraper = FlightScraper()
results = scraper.search(
    origin="DEL",
    destination="BOM",
    date="2025-12-20",
    cabin_class="economy"
)

# Access DataFrame
print(results.flights_df)

# View analysis
print(results.analysis_report)

# Export
results.to_csv("flights.csv")
results.to_charts("output/charts.pdf")
```

---

## 11. Quality Assurance

### 11.1 Testing Strategy

- **Unit Tests** - Parser extracts correct fields, cleaner handles edge cases, analyzer computes correct metrics
- **Integration Tests** - Full pipeline runs end-to-end without errors
- **Data Validation** - Check for:
  - Missing required fields
  - Type consistency (prices are integers, times are valid HH:MM)
  - Price ranges are reasonable (₹10k-₹50k for domestic India flights)
  - No duplicate flight codes

### 11.2 Error Scenarios

| Scenario | Handling |
|----------|----------|
| No flights found | Display "No results" message, suggest date change |
| Website layout changed | Log error, print helpful message, suggest manual verification |
| Network timeout | Retry up to 3 times with exponential backoff |
| Invalid date format | Validate input, re-prompt user |
| Missing fields in card | Use default values ("N/A"), log warning |
| Selenium driver crash | Graceful shutdown, cleanup resources |

---

## 12. Performance & Scalability

### 12.1 Performance Targets

- **Scrape time:** ~5-10 seconds (depends on page load, network)
- **Parse time:** <1 second (100-200 flights)
- **Process/analyze time:** <2 seconds
- **Chart generation:** <3 seconds
- **Total end-to-end:** ~15-20 seconds for a typical search

### 12.2 Future Scalability

For multi-flight scraping or larger datasets:
- Implement threading in scraper (fetch multiple routes in parallel)
- Cache results in SQLite DB to avoid repeated scrapes
- Use async/await for network I/O
- Offload chart generation to background task

---

## 13. Known Limitations & Future Improvements

### 13.1 Current Limitations

1. **Single Site Only** - MakeMyTrip only (can extend to Goibibo, ixigo)
2. **Static Date Snapshot** - One search per run (no historical tracking yet)
3. **One-way Flights Only** - Round-trip requires separate search
4. **No Seat Availability** - Fare data only, no seat counts
5. **No Booking Integration** - View-only, no actual purchase
6. **Basic Recommendation** - Simple scoring, not ML-based

### 13.2 Future Improvements

1. **Multi-site Aggregation** - Scrape and compare Goibibo, ixigo, Cleartrip simultaneously
2. **Price History Tracking** - Store results over time, detect trends, predict best booking windows
3. **Real-time Alerts** - Notify user when price drops below threshold
4. **Advanced Analytics** - ML-based price prediction, demand forecasting
5. **Mobile App** - React Native or Flutter mobile version
6. **Coupon Optimization** - Recommend best coupon code for each flight
7. **Integration with Payment Gateways** - One-click booking with real payment

---

## 14. Resume & Portfolio Highlights

### Technical Skills Demonstrated

✅ **Web Scraping:** Selenium automation, dynamic content handling, JavaScript rendering  
✅ **Data Processing:** Pandas DataFrames, cleaning, validation, transformation  
✅ **Numerical Computing:** NumPy statistics, aggregation, correlation analysis  
✅ **Data Visualization:** Matplotlib charts, multi-subplot dashboards, publication-ready output  
✅ **Software Engineering:** Modular design, error handling, logging, unit testing  
✅ **APIs & Parsing:** BeautifulSoup CSS selectors, HTML DOM traversal  
✅ **CLI Design:** argparse, user input validation, formatted console output  
✅ **Problem Solving:** Real-world data extraction, edge case handling, robustness  

### Portfolio Artifacts

- **GitHub Repository** - Complete codebase with README, tests, documentation
- **Sample Output** - CSV files, charts, summary reports showing actual results
- **Project Documentation** - Design document, architecture diagrams, algorithm explanations
- **Test Suite** - Comprehensive unit and integration tests with >80% code coverage

---

## 15. Contact & Support

**Author:** [Your Name]  
**Email:** [Your Email]  
**GitHub:** [Repository Link]  
**Last Updated:** December 2025

---

## Appendix A: Selector Reference

Complete list of CSS selectors used for parsing MakeMyTrip flight cards:

```python
SELECTORS = {
    "flight_card": 'div[data-test="component-clusterItem"]',
    "airline_name": 'p.airlineName',
    "flight_code": 'p.fliCode',
    "departure_time": '.timeInfoLeft .flightTimeInfo span',
    "departure_city": '.timeInfoLeft .blackText',
    "arrival_time": '.timeInfoRight .flightTimeInfo span',
    "arrival_city": '.timeInfoRight .blackText',
    "duration": '.stop-info > p:first-child',
    "stops": '.flightsLayoverInfo',
    "price": '.clusterViewPrice span.fontSize18',
    "lock_price": '.lockPriceTrigger .fontSize12.boldFont.blueText',
    "offers": '.alertMsg span',
    "min_price_page": '[data-test="component-minLegendVal"]',
    "max_price_page": '[data-test="component-maxLegendVal"]',
}
```

---

## Appendix B: Sample Data Output

**Sample Flight Record (JSON):**
```json
{
    "flight_id": "RKEY:8512aa41-c695-48e9-8ea3-23025d558cc4:55_0",
    "airline": "IndiGo",
    "flight_code": "6E 6622",
    "departure_time": "18:00",
    "departure_city": "New Delhi",
    "departure_airport": "DEL",
    "arrival_time": "20:55",
    "arrival_city": "Bengaluru",
    "arrival_airport": "BLR",
    "duration_minutes": 175,
    "stops": 0,
    "stop_details": "Non stop",
    "price_per_adult": 16058,
    "lock_price_from": 937.0,
    "cabin_class": "economy",
    "offers": "FLAT ₹ 100 OFF using MMTSUPER | FLAT 10% OFF on SBI Debit cards",
    "nearby_airport": false,
    "search_date": "2025-12-11",
    "journey_date": "2025-12-20"
}
```

**Sample Analysis Report (TXT):**
```
===============================================
FLIGHT SEARCH ANALYSIS REPORT
===============================================

Search Parameters:
  Origin: New Delhi (DEL)
  Destination: Bengaluru (BLR)
  Journey Date: 2025-12-20
  Cabin Class: Economy

Results Summary:
  Total Flights Found: 25
  Non-Stop: 8
  1 Stop: 17

Price Analysis:
  Minimum Fare: ₹ 16,058 (IndiGo 6E 6622)
  Maximum Fare: ₹ 18,500 (Air India AI 3361)
  Average Fare: ₹ 16,752
  Median Fare: ₹ 16,650
  Price Range: ₹ 13,614 - ₹ 28,200 (page filter)

Top 3 Cheapest Options:
  1. IndiGo 6E 6622 | 18:00-20:55 | 2h55m | Non-stop | ₹ 16,058
  2. IndiGo 6E 173 | 10:30-13:25 | 2h55m | Non-stop | ₹ 16,475
  3. IndiGo 6E 6602 | 06:20-11:30 | 5h10m | 1 stop via Bhopal | ₹ 16,650

Airline Comparison:
  IndiGo: Avg ₹ 16,450 | Min ₹ 16,058 | 12 flights
  Air India: Avg ₹ 16,500 | Min ₹ 16,475 | 8 flights
  Spicejet: Avg ₹ 16,800 | Min ₹ 16,700 | 5 flights

Departure Time Analysis:
  Early Morning (6 AM - 12 PM): Avg ₹ 16,600
  Afternoon (12 PM - 6 PM): Avg ₹ 16,450
  Evening (6 PM onwards): Avg ₹ 16,550

Best Value Flights (Price + Duration + Stops):
  1. IndiGo 6E 6622 | Score: 9.2/10
  2. IndiGo 6E 173 | Score: 8.9/10
  3. Air India AI 3361 | Score: 8.5/10

Recommendations:
  - Non-stop flights are only ₹ 200-300 cheaper on average than 1-stop
  - Afternoon departures offer best value
  - IndiGo dominates with 48% of results and lowest avg fares
  - Apply coupon MMTSUPER for ₹ 100 instant discount
  - Lock Price feature (₹ 937 for IndiGo) recommended if unsure

Report Generated: 2025-12-11 19:45:23
===============================================
```

---

**End of Design Document**
