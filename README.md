# CostToFly

CostToFly is a flight price comparison and analysis tool that collects data from multiple booking platforms, cleans and merges it, and presents clear price insights with visualizations.

The goal is not ticket booking, but understanding price behavior across sources and making trade-offs visible.

---

## What It Does

- Scrapes flight listings from:
  - MakeMyTrip
  - Goibibo
  - Cleartrip
- Deduplicates and normalizes inconsistent data
- Computes useful metrics:
  - Cheapest flight
  - Shortest duration
  - Best value (price vs duration)
  - Price range and distribution
- Generates visual insights:
  - Price distribution
  - Price vs departure time
  - Airline and source comparisons
- Serves results via a simple Flask web interface

---

## Project Structure

```
costtofly/
├── scrapers/
│   ├── makeMyTrip.py
│   ├── goibibo.py
│   └── cleartrip.py
├── dataScraper.py
├── dataAnalyser.py
├── visualizer.py
├── app.py
├── main.py
├── templates/
├── static/
├── Results/
├── input.json
└── README.md
```

---

## How It Works

### Input
User provides departure city, arrival city, and date.  
Saved in `input.json`.

### Scraping
Each platform is scraped independently using Selenium.  
Adaptive scrolling and stale-load detection ensure all results load.  
Popups and filters are handled defensively.

### Data Processing
Results from all sources are merged.  
Duplicate flights are removed.  
Prices and durations are normalized.

### Analysis
Key metrics are computed from the combined dataset.  
Results are saved as CSV and JSON.

### Visualization
Charts are generated using matplotlib.  
Charts are served as static images in the web UI.

---

## Running the Project

### Prerequisites

- Python 3.10+
- Google Chrome installed
- ChromeDriver handled via undetected-chromedriver

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Full Pipeline

```bash
python main.py
```

### Run Web App

```bash
python app.py
```

Open in browser:

```
http://localhost:5000
```

---

## Example Insights

- Cheapest flight across all platforms
- Platform-wise lowest prices
- Price distribution for a given route
- Impact of departure time on pricing

---

## Notes & Limitations

- Website DOMs may change and break scrapers
- Scraping speed depends on network and site behavior
- Intended for educational and analytical purposes

---

## Why This Project

Most projects stop at scraping or plotting.

This project focuses on building a reliable scraping pipeline, handling real-world UI instability, and turning noisy data into meaningful comparisons.

---

## Future Improvements

- Add caching to reduce repeated scrapes
- Support return and multi-city routes
- CSV export and API-only mode
- Interactive visualizations

---

## Disclaimer

This project is for learning and analysis only.  
It is not affiliated with or endorsed by any flight booking platform.
