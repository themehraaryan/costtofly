from typing import Any
import pandas as pd
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from loggerconfig import setup_logger
from scrapers.utils import load_input, random_delay, build_flight_record

logger = setup_logger()

WAIT_TIMEOUT = 30
SCROLL_PAUSE = 3
MAX_STALE_SCROLLS = 5
FILTER_RESET_WAIT = 3


def _build_url(departure: str, arrival: str, date: str) -> str:
    return f"https://www.makemytrip.com/flight/search?itinerary={departure}-{arrival}-{date}&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E"


def _reset_all_filters(browser, wait) -> bool:
    logger.info("Detecting and resetting active filters...")
    filters_reset = 0
    
    try:
        clear_all = browser.find_element(By.CSS_SELECTOR, "span.clearFilter")
        if clear_all.is_displayed():
            browser.execute_script("arguments[0].click();", clear_all)
            filters_reset += 1
            logger.info("Clicked 'CLEAR ALL' button")
            time.sleep(2)
    except Exception:
        logger.debug("No CLEAR ALL button found")
    
    try:
        chip_close_buttons = browser.find_elements(By.CSS_SELECTOR, "span.filterCross, .appliedFilter span.overlayCrossIcon")
        for btn in chip_close_buttons:
            try:
                if btn.is_displayed():
                    browser.execute_script("arguments[0].click();", btn)
                    filters_reset += 1
                    logger.debug("Removed filter chip via X button")
                    time.sleep(0.5)
            except Exception:
                continue
    except Exception:
        pass
    
    try:
        nonstop_labels = browser.find_elements(By.XPATH, 
            "//label[contains(., 'Non Stop') or contains(., 'NON STOP')]")
        for label in nonstop_labels:
            try:
                checkbox = label.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                if checkbox.is_selected():
                    browser.execute_script("arguments[0].click();", label)
                    filters_reset += 1
                    logger.debug("Unchecked Non Stop checkbox")
                    time.sleep(0.5)
            except Exception:
                continue
    except Exception:
        pass
    
    if filters_reset > 0:
        logger.info(f"Reset {filters_reset} filters, waiting for DOM update...")
        time.sleep(FILTER_RESET_WAIT)
        try:
            wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.listingCard")) > 0)
        except Exception:
            pass
    
    logger.info(f"Filter reset complete. Total filters cleared: {filters_reset}")
    return filters_reset > 0


def _verify_no_active_filters(browser) -> bool:
    try:
        clear_all = browser.find_elements(By.CSS_SELECTOR, "span.clearFilter")
        for el in clear_all:
            if el.is_displayed():
                logger.debug("CLEAR ALL button still visible - filters active")
                return False
    except Exception:
        pass
    
    try:
        applied_chips = browser.find_elements(By.CSS_SELECTOR, ".appliedFilter li")
        for chip in applied_chips:
            if chip.is_displayed():
                logger.debug(f"Applied filter chip found: {chip.text}")
                return False
    except Exception:
        pass
    
    return True


def _scroll_until_loaded(browser, wait) -> None:
    stale_scroll_count = 0
    previous_count = 0

    logger.info("Starting adaptive scrolling...")

    while stale_scroll_count < MAX_STALE_SCROLLS:
        current_count = len(browser.find_elements(By.CSS_SELECTOR, "[data-test='component-clusterItem'] div.listingCard"))

        if current_count > previous_count:
            logger.debug(f"Flight cards increased: {previous_count} → {current_count}")
            previous_count = current_count
            stale_scroll_count = 0
        else:
            stale_scroll_count += 1
            logger.debug(f"No new cards loaded (attempt {stale_scroll_count}/{MAX_STALE_SCROLLS})")

        if stale_scroll_count >= MAX_STALE_SCROLLS:
            break

        browser.execute_script("window.scrollBy(0, 1000);")

        try:
            wait.until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "[data-test='component-clusterItem'] div.listingCard")) >= current_count,
                message="Timeout waiting for potential new cards"
            )
        except Exception:
            pass

    logger.info(f"Scrolling complete. Total flight cards: {previous_count}")


def run(browser) -> tuple[bool, Any]:
    wait = WebDriverWait(browser, WAIT_TIMEOUT)
    flights_list = []

    try:
        input_data = load_input()
        url = _build_url(input_data["departure"], input_data["arrival"], input_data["date"])

        browser.get(url)
        logger.info("MakeMyTrip page loaded, waiting for results...")

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.listingCard")))
        random_delay(4, 6)
        
        for filter_attempt in range(3):
            _reset_all_filters(browser, wait)
            random_delay(1.5, 2.5)
            if _verify_no_active_filters(browser):
                logger.info("All filters successfully cleared")
                break
            logger.warning(f"Filters still active after attempt {filter_attempt + 1}")
        random_delay(1.5, 2.5)

        _scroll_until_loaded(browser, wait)

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

                flights_list.append(build_flight_record(
                    source="MakeMyTrip",
                    airline=airline,
                    flight_code=code,
                    departure=dep_time,
                    arrival=arr_time,
                    duration=duration_text,
                    stops=stops_text,
                    price=price_int
                ))

            except Exception as e:
                logger.debug(f"Skipped card due to missing element: {e}")
                continue

        if not flights_list:
            logger.warning("No flights extracted")
            return (False, None)

        df = pd.DataFrame(flights_list)
        logger.info(f"MakeMyTrip scraping completed: {len(df)} flights in DataFrame")
        return (True, df)

    except Exception as e:
        logger.error(f"MakeMyTrip scraper failed: {e}", exc_info=True)
        return (False, None)
