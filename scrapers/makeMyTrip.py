import time
from datetime import datetime
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from loggerconfig import setup_logger

logger = setup_logger()

URL = "https://www.makemytrip.com/flight/search?itinerary=DEL-BLR-19/12/2025&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E"
WAIT_TIMEOUT = 30
SCROLL_COUNT = 6
SCROLL_SLEEP = 3


def run(browser) -> tuple[bool, Any]:
    wait = WebDriverWait(browser, WAIT_TIMEOUT)
    flights_list = []

    try:
        browser.get(URL)
        logger.info("MakeMyTrip page loaded, waiting for results...")

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.listingCard")))

        logger.info(f"Scrolling {SCROLL_COUNT} times to load flights...")
        for i in range(SCROLL_COUNT):
            browser.execute_script("window.scrollBy(0, 1000);")
            time.sleep(SCROLL_SLEEP)

        flight_cards = browser.find_elements(By.CSS_SELECTOR, "[data-test='component-clusterItem'] div.listingCard")
        logger.info(f"Found {len(flight_cards)} flight cards, extracting data...")

        for card in flight_cards:
            try:
                airline_el = card.find_element(By.CSS_SELECTOR, "p.airlineName")
                airline = airline_el.get_attribute("innerText").strip()

                code_el = card.find_element(By.CSS_SELECTOR, "p.fliCode")
                code = code_el.get_attribute("innerText").strip()

                dep_el = card.find_element(By.CSS_SELECTOR, "div.timeInfoLeft p.flightTimeInfo span")
                dep_time = dep_el.get_attribute("innerText").strip()

                arr_el = card.find_element(By.CSS_SELECTOR, "div.timeInfoRight p.flightTimeInfo span")
                arr_time = arr_el.get_attribute("innerText").strip()

                duration_el = card.find_element(By.CSS_SELECTOR, "div.stop-info p")
                duration_text = duration_el.get_attribute("innerText").strip()

                stops_el = card.find_element(By.CSS_SELECTOR, "p.flightsLayoverInfo")
                stops_text = stops_el.get_attribute("innerText").strip()

                price_el = card.find_element(By.CSS_SELECTOR, "div.clusterViewPrice")
                price_raw = price_el.get_attribute("innerText")

                price_clean = str(price_raw).replace("₹", "").replace(",", "").split("\n")[0].strip()
                price_int = int(price_clean) if price_clean.isdigit() else 0

                flight_data = {
                    "source": "MakeMyTrip",
                    "airline": airline,
                    "flight_code": code,
                    "departure": dep_time,
                    "arrival": arr_time,
                    "duration": duration_text,
                    "stops": stops_text,
                    "price": price_int,
                    "timestamp": datetime.now().isoformat()
                }

                flights_list.append(flight_data)

            except Exception as e:
                logger.debug(f"Skipped card due to missing element: {e}")
                continue

        logger.info(f"MakeMyTrip scraping completed: {len(flights_list)} flights extracted")
        return (True, flights_list)

    except Exception as e:
        logger.error(f"MakeMyTrip scraper failed: {e}", exc_info=True)
        return (False, None)
