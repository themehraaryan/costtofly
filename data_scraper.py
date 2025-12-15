"""
MakeMyTrip Flight Scraper
- Uses undetected-chromedriver
- Uses precise DOM selectors (XPath/CSS) instead of Regex
- Extracts Airline, Code, Times, Duration, Stops, Price
"""

import time
from datetime import datetime
import undetected_chromedriver as uc
import pandas as pd
from tabulate import tabulate

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ---------------- CONFIG ---------------- #

URL = "https://www.makemytrip.com/flight/search?itinerary=DEL-BLR-17/12/2025&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E"
WAIT_TIMEOUT = 30
SCROLL_COUNT = 6
SCROLL_SLEEP = 3

# ---------------- SCRAPER ---------------- #

def main():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    print("\nStarting Scraper...")
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    
    flights_list = []

    try:
        driver.get(URL)
        print("Page loaded. Waiting for results...")

        # Wait for the main flight list container or first card
        # Using the specific listingCard class found in analysis
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.listingCard")))

        # --- SCROLLING LOGIC ---
        # Scroll the window to trigger lazy loading of more flights
        print(f"Scrolling {SCROLL_COUNT} times to load more flights...")
        for i in range(SCROLL_COUNT):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(SCROLL_SLEEP)
        
        # Scroll back up slightly to ensure elements are stable? (Optional, usually not needed if elements are present)
        # driver.execute_script("window.scrollTo(0, 0);")
        
        # --- COLLECT CARDS ---
        # Selector for the individual flight card container
        # Use [data-test='component-clusterItem'] to ensure we target the actual flight rows
        flight_cards = driver.find_elements(By.CSS_SELECTOR, "[data-test='component-clusterItem'] div.listingCard")
        
        print(f"\nFound {len(flight_cards)} flight cards. Extracting data...\n")

        for card in flight_cards:
            try:
                # --- EXTRACT DATA POINTS USING PRECISE SELECTORS ---
                
                # 1. Airline Name
                # Selector: p.airlineName
                airline_el = card.find_element(By.CSS_SELECTOR, "p.airlineName")
                airline = airline_el.get_attribute("innerText").strip()

                # 2. Flight Code
                # Selector: p.fliCode
                code_el = card.find_element(By.CSS_SELECTOR, "p.fliCode")
                code = code_el.get_attribute("innerText").strip()

                # 3. Departure Time
                # Selector: div.timeInfoLeft p.flightTimeInfo span (first-child mostly)
                dep_el = card.find_element(By.CSS_SELECTOR, "div.timeInfoLeft p.flightTimeInfo span")
                dep_time = dep_el.get_attribute("innerText").strip()

                # 4. Arrival Time
                # Selector: div.timeInfoRight p.flightTimeInfo span
                arr_el = card.find_element(By.CSS_SELECTOR, "div.timeInfoRight p.flightTimeInfo span")
                arr_time = arr_el.get_attribute("innerText").strip()

                # 5. Duration
                # Selector: div.stop-info p (e.g., "02 h 55 m")
                duration_el = card.find_element(By.CSS_SELECTOR, "div.stop-info p")
                duration_text = duration_el.get_attribute("innerText").strip()

                # 6. Stops
                # Selector: p.flightsLayoverInfo (e.g., "Non stop")
                stops_el = card.find_element(By.CSS_SELECTOR, "p.flightsLayoverInfo")
                stops_text = stops_el.get_attribute("innerText").strip()

                # 7. Price
                # Selector: div.clusterViewPrice (contains "₹ 12,689")
                price_el = card.find_element(By.CSS_SELECTOR, "div.clusterViewPrice")
                price_raw = price_el.get_attribute("innerText")
                
                # --- DATA CLEANING ---
                
                # Clean Price: Remove '₹', commas, and extra text like "/adult"
                price_clean = str(price_raw).replace("₹", "").replace(",", "").split("\n")[0].strip()
                price_int = int(price_clean) if price_clean.isdigit() else 0

                # Data Object
                flight_data = {
                    "Airline": airline,
                    "Flight Code": code,
                    "Departure": dep_time,
                    "Arrival": arr_time,
                    "Duration": duration_text,
                    "Stops": stops_text,
                    "Price": price_int,
                    "Raw Price" : f"₹ {price_int:,}" # Formatted for display
                }

                flights_list.append(flight_data)
                # print(f"Extracted: {airline} {code} - ₹{price_int}") # Debug print

            except Exception as e:
                # If a specific element is missing in a card (e.g. ad banners masquerading as cards), skip it
                # print(f"Skipping a card due to missing element: {e}")
                pass

    except Exception as e:
        print(f"Global Scraper Error: {e}")

    finally:
        print("Closing driver...")
        driver.quit()

    # --- OUTPUT ---
    if flights_list:
        df = pd.DataFrame(flights_list)
        
        # Sort by Price
        df = df.sort_values("Price")
        
        # Display
        print(f"\n{'='*80}")
        print(f"  FLIGHT SEARCH RESULTS - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  Total Flights Scraped: {len(flights_list)}")
        print(f"{'='*80}\n")
        
        # Columns to display
        cols = ["Airline", "Flight Code", "Departure", "Arrival", "Duration", "Stops", "Raw Price"]
        print(tabulate(df[cols], headers=cols, tablefmt="fancy_grid", showindex=False))
        
        print(f"\nCheapest Flight: {df.iloc[0]['Airline']} ({df.iloc[0]['Raw Price']})")

    else:
        print("No flights found.")

if __name__ == "__main__":
    main()
