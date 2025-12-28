import re
import time
from typing import Any
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from loggerconfig import setup_logger
from scrapers.utils import (
    load_input,
    parse_price,
    deduplicate_flights,
    wait_for_skeleton_loaders,
    build_flight_record
)

logger = setup_logger()

WAIT_TIMEOUT = 30
INITIAL_WAIT = 5
MAX_STALE_SCROLLS = 6
MAX_SCROLL_ATTEMPTS = 30
SCROLL_PAUSE_MIN = 1.5
SCROLL_PAUSE_MAX = 3.0
SKELETON_TIMEOUT = 5


def _build_url(departure: str, arrival: str, date: str) -> str:
    timestamp = int(time.time() * 1000)
    return (f"https://www.cleartrip.com/flights/results?"
            f"adults=1&childs=0&infants=0&class=Economy&"
            f"depart_date={date}&"
            f"from={departure}&to={arrival}&"
            f"intl=n&"
            f"origin={departure}%20-%20City&"
            f"destination={arrival}%20-%20City&"
            f"sft=&sd={timestamp}&"
            f"rnd_one=O&isCfw=false&isFF=false")


def _wait_for_results(browser, wait) -> bool:
    card_selectors = [
        "div[class*='sc-a15c1a81']",
        "div[class*='flight-card']",
        "div[class*='flightCard']",
        "[data-testid*='flight']",
        "div[class*='listing']"
    ]
    
    for selector in card_selectors:
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            logger.debug(f"Found results with selector: {selector}")
            return True
        except Exception:
            continue
    
    return False


def _find_flight_cards(browser) -> list:
    card_selectors = [
        "div[class*='sc-a15c1a81-0']",
        "div[class*='sc-'][class*='flex']",
        "[class*='flight-row']",
        "[class*='flightCard']"
    ]
    
    for selector in card_selectors:
        cards = browser.find_elements(By.CSS_SELECTOR, selector)
        if len(cards) > 0:
            valid_cards = []
            for card in cards:
                try:
                    text = card.text
                    if "₹" in text and any(c.isdigit() for c in text):
                        valid_cards.append(card)
                except Exception:
                    continue
            if valid_cards:
                logger.debug(f"Found {len(valid_cards)} valid cards with selector: {selector}")
                return valid_cards
    
    return []


def _count_flight_cards(browser) -> int:
    cards = _find_flight_cards(browser)
    return len(cards)


def _verify_no_active_filters(browser) -> bool:
    active_selectors = [
        "input[type='checkbox']:checked",
        "[class*='active'][class*='filter']",
        "[class*='selected'][class*='filter']",
        "[class*='appliedFilter']",
    ]
    for sel in active_selectors:
        try:
            elements = browser.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                try:
                    if el.is_displayed():
                        return False
                except Exception:
                    continue
        except Exception:
            continue
    return True


def _scroll_until_loaded(browser) -> int:
    stale_scroll_count = 0
    previous_count = 0
    scroll_attempts = 0
    
    logger.info("Starting adaptive scrolling for Cleartrip...")
    
    browser.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    while stale_scroll_count < MAX_STALE_SCROLLS and scroll_attempts < MAX_SCROLL_ATTEMPTS:
        scroll_attempts += 1
        
        wait_for_skeleton_loaders(browser, timeout=3)
        
        current_count = _count_flight_cards(browser)
        
        if current_count > previous_count:
            logger.debug(f"Flight cards increased: {previous_count} → {current_count}")
            previous_count = current_count
            stale_scroll_count = 0
        else:
            stale_scroll_count += 1
            logger.debug(f"No new cards loaded (attempt {stale_scroll_count}/{MAX_STALE_SCROLLS})")
        
        if stale_scroll_count >= MAX_STALE_SCROLLS:
            break
        
        scroll_amount = 800 + (scroll_attempts % 5) * 100
        browser.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
        scroll_pause = SCROLL_PAUSE_MIN + (SCROLL_PAUSE_MAX - SCROLL_PAUSE_MIN) * (scroll_attempts / MAX_SCROLL_ATTEMPTS)
        time.sleep(scroll_pause)
        
        try:
            WebDriverWait(browser, 2).until(
                lambda d: _count_flight_cards(d) >= current_count
            )
        except Exception:
            pass
    
    browser.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    final_count = _count_flight_cards(browser)
    logger.info(f"Scrolling complete. Total flight cards: {final_count}")
    return final_count


def _reset_filters(browser) -> bool:
    logger.info("Checking for active filters on Cleartrip...")
    filters_reset = 0
    
    try:
        active_filters = browser.find_elements(By.CSS_SELECTOR, 
            "input[type='checkbox']:checked, [class*='active'][class*='filter'], [class*='selected'][class*='filter']")
        
        for el in active_filters:
            try:
                if el.is_displayed():
                    el.click()
                    filters_reset += 1
                    time.sleep(0.5)
            except Exception:
                continue
    except Exception:
        pass
    
    try:
        clear_buttons = browser.find_elements(By.XPATH, 
            "//button[contains(text(),'Clear') or contains(text(),'Reset')] | //span[contains(text(),'Clear All')]")
        for btn in clear_buttons:
            try:
                if btn.is_displayed():
                    btn.click()
                    filters_reset += 1
                    time.sleep(1)
            except Exception:
                continue
    except Exception:
        pass
    
    if filters_reset > 0:
        logger.info(f"Reset {filters_reset} filters on Cleartrip")
        time.sleep(2)
    
    return filters_reset > 0


def _extract_by_selectors(element, selectors: list) -> str:
    for selector in selectors:
        try:
            el = element.find_element(By.CSS_SELECTOR, selector)
            text = el.get_attribute("innerText").strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def _parse_card_text(card_text: str) -> dict:
    lines = [l.strip() for l in card_text.split("\n") if l.strip()]
    
    result = {
        "airline": "",
        "flight_code": "",
        "departure": "",
        "arrival": "",
        "duration": "",
        "stops": "Non-stop",
        "price": parse_price(card_text)
    }
    
    for i, line in enumerate(lines):
        if "₹" in line:
            continue
        
        if any(x in line.lower() for x in ["stop", "via", "layover", "non-stop", "nonstop"]):
            result["stops"] = line
            continue
            
        if "h" in line.lower() and "m" in line.lower() and len(line) < 15:
            result["duration"] = line
            continue
        
        time_pattern_count = sum(1 for c in line if c == ":")
        if time_pattern_count == 1 and len(line) <= 8:
            if not result["departure"]:
                result["departure"] = line
            elif not result["arrival"]:
                result["arrival"] = line
            continue
        
        if len(line) >= 2 and len(line) <= 10 and any(c.isdigit() for c in line) and any(c.isalpha() for c in line):
            if not result["flight_code"]:
                result["flight_code"] = line
            continue
        
        if not result["airline"] and len(line) > 3 and line[0].isupper():
            result["airline"] = line
    
    return result


def run(browser) -> tuple[bool, Any]:
    wait = WebDriverWait(browser, WAIT_TIMEOUT)
    flights_list = []

    try:
        input_data = load_input()
        url = _build_url(input_data["departure"], input_data["arrival"], input_data["date"])

        browser.get(url)
        logger.info("Cleartrip page loaded, waiting for results...")

        time.sleep(INITIAL_WAIT)
        
        if not _wait_for_results(browser, wait):
            logger.warning("Could not detect flight results on Cleartrip")
            return (False, None)

        time.sleep(2)
        
        _reset_filters(browser)
        
        for filter_attempt in range(3):
            if _verify_no_active_filters(browser):
                logger.info("All filters verified as cleared")
                break
            _reset_filters(browser)
            time.sleep(1)
        
        _scroll_until_loaded(browser)

        flight_cards = _find_flight_cards(browser)
        
        if not flight_cards:
            all_divs = browser.find_elements(By.CSS_SELECTOR, "div")
            for div in all_divs:
                try:
                    text = div.text
                    classes = div.get_attribute("class") or ""
                    if "₹" in text and len(text) < 500 and len(text) > 50:
                        if "sc-" in classes:
                            flight_cards.append(div)
                            if len(flight_cards) >= 50:
                                break
                except Exception:
                    continue

        logger.info(f"Found {len(flight_cards)} flight cards, extracting data...")

        for card in flight_cards:
            try:
                card_text = card.text
                
                if not card_text or "₹" not in card_text:
                    continue
                
                parsed = _parse_card_text(card_text)
                
                if not parsed["departure"] or not parsed["arrival"] or parsed["price"] == 0:
                    continue
                
                airline = _extract_by_selectors(card, [
                    ".eJFhSz + div p:first-child",
                    "p[class*='airline']",
                    "span[class*='airline']"
                ])
                if airline:
                    parsed["airline"] = airline
                
                flight_code = _extract_by_selectors(card, [
                    ".eJFhSz + div p:last-child",
                    "p[class*='code']",
                    "span[class*='code']"
                ])
                if flight_code:
                    parsed["flight_code"] = flight_code

                flights_list.append(build_flight_record(
                    source="Cleartrip",
                    airline=parsed["airline"],
                    flight_code=parsed["flight_code"],
                    departure=parsed["departure"],
                    arrival=parsed["arrival"],
                    duration=parsed["duration"],
                    stops=parsed["stops"],
                    price=parsed["price"]
                ))

            except Exception as e:
                logger.debug(f"Skipped card due to error: {e}")
                continue

        if not flights_list:
            logger.warning("No flights extracted from Cleartrip")
            return (False, None)

        unique_flights = deduplicate_flights(flights_list)
        df = pd.DataFrame(unique_flights)
        logger.info(f"Cleartrip scraping completed: {len(df)} flights in DataFrame")
        return (True, df)

    except Exception as e:
        logger.error(f"Cleartrip scraper failed: {e}", exc_info=True)
        return (False, None)
