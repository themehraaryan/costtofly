# 🧪 TEST PLAN – Flight Price Tracker & Analytics System

## 1. Introduction / Objective

### Purpose

This Test Plan defines the testing scope, strategy, and criteria for validating the Flight Price Tracker & Analytics System, a web-based application that scrapes flight data from multiple third-party sources, processes and analyzes that data, and presents insights via a web UI and APIs.

### Primary Objectives

- Verify end-to-end functional correctness from user input to displayed results
- Ensure data accuracy, consistency, and integrity across scraping, aggregation, and analytics layers
- Validate system robustness when partial failures occur (one or more scrapers fail)
- Confirm correct generation of metrics and visualizations
- Ensure the UI and APIs present accurate, reliable information

---

## 2. Scope

### 2.1 In Scope

**User Interface (Flask Web App)**
- Search form validation (departure, arrival, date)
- Error handling and user feedback
- Results page rendering
- Metrics display
- Charts display
- Flight table rendering (top N rows)
- Navigation between search and results

**Backend Orchestration**
- Input persistence (input.json)
- Scraper execution orchestration
- Handling partial scraper success/failure
- End-to-end pipeline execution

**Scrapers**
- MakeMyTrip scraper
- Goibibo scraper
- Cleartrip scraper
- Scrolling, expansion, and lazy-load handling
- Filter reset logic
- Data extraction logic

**Data Processing & Analytics**
- Data merging and deduplication
- Sorting logic
- Metric calculations:
  - Cheapest overall
  - Shortest duration
  - Best value
  - Cheapest per airline
  - Cheapest per source
  - Price statistics
  - Stop analysis

**Visualization**
- Chart generation using matplotlib
- Correct chart values and labels
- File creation and storage
- Charts displayed correctly in UI

**APIs**
- /api/flights
- /api/metrics

**Error & Failure Handling**
- Scraper timeouts
- Empty results
- Partial data availability
- Invalid user input

### 2.2 Out of Scope

- Third-party website UI/DOM changes (treated as external risk)
- Performance / load testing
- Security testing
- Accessibility (WCAG) testing
- Mobile responsiveness
- Long-term scraper reliability or scheduling (cron jobs)
- Real-time price monitoring
- Payment or booking flows

---

## 3. Features to Be Tested

### 3.1 Search & Input Handling
- Mandatory field validation
- Airport code length validation
- Date format validation (DD/MM/YYYY)
- Error messages for invalid input

### 3.2 Scraper Execution
- Successful execution per scraper
- Handling scraper crashes or timeouts
- DataFrame creation correctness
- No duplicate browser instances
- Proper browser cleanup

### 3.3 Data Aggregation
- Combining multiple scraper outputs
- Deduplication logic correctness
- Sorting by price and departure time
- Schema enforcement

### 3.4 Metrics Computation
- Correctness of each metric
- Edge cases (single flight, same prices, missing durations)
- Numeric precision and rounding

### 3.5 Visualization
- Correct chart generation per run
- Charts reflect underlying data accurately
- No crashes when data is minimal
- Chart files saved correctly

### 3.6 Results Presentation
- Metrics displayed correctly
- Highlighted "best" values
- Flight table accuracy
- Total flight count correctness

### 3.7 APIs
- JSON structure correctness
- Empty data handling
- Consistency with UI data

---

## 4. Testing Types & Approach

### Testing Types
- Functional Testing (primary)
- Integration Testing
- End-to-End Testing
- Exploratory Testing
- Negative & Edge Case Testing
- Data Validation Testing

### Approach
- Risk-based testing prioritizing scrapers and data correctness
- Mostly manual testing supported by log inspection
- Selective automation possible for:
  - Input validation
  - Metrics computation (unit-level, optional)

---

## 5. Test Environments

### Application Environment
- OS: Windows / Linux
- Python 3.x
- Flask (local server)

### Browser
- Chrome (via undetected_chromedriver)

### External Dependencies
- Live MakeMyTrip, Goibibo, Cleartrip websites
- Internet connectivity required

### Data
- Live scraped data
- Local CSV and JSON outputs

---

## 6. Test Execution Strategy

### Execution Ownership
- Single tester / developer-led testing

### Execution Flow
1. Smoke test (app launch, basic search)
2. Scraper validation (per source)
3. Data aggregation & metrics validation
4. Visualization validation
5. UI and API validation
6. Failure scenario testing

### Defect Tracking
- Log-based (console + log files)
- Optional manual defect list (Markdown / Notion / Jira)

---

## 7. Test Deliverables

- Test Plan (this document)
- Manual Test Scenarios / Checklists
- Test Execution Notes
- Defect Logs
- Final Test Summary (Pass/Fail + known issues)

---

## 8. Entry Criteria

- Code builds successfully
- Flask app starts without error
- Internet connectivity available
- Required Python dependencies installed
- Third-party sites accessible

---

## 9. Exit Criteria

- All critical user flows tested
- No unresolved critical or high-severity defects
- Metrics and charts verified for correctness
- Application handles partial scraper failures gracefully
- Known limitations documented

---

## 10. Risks & Contingencies

### Key Risks
- Third-party DOM changes breaking scrapers
- Inconsistent or malformed scraped data
- Long scraper execution times
- Silent partial failures

### Mitigation
- Robust logging validation
- Partial success acceptance
- Manual sanity checks on output
- Clear documentation of known issues
