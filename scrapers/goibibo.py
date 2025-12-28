import re
from typing import Any
import pandas as pd
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchWindowException
)

from loggerconfig import setup_logger
from scrapers.utils import (
    load_input,
    parse_price,
    deduplicate_flights,
    random_delay,
    build_flight_record
)

logger = setup_logger()

GOIBIBO_HOME = "https://www.goibibo.com/"
WAIT_TIMEOUT = 40
SHORT_WAIT = 5
SCROLL_PAUSE_MIN = 1.5
SCROLL_PAUSE_MAX = 3.0
MAX_STALE_SCROLLS = 5
MAX_SCROLL_ATTEMPTS = 25
MAX_EXPAND_ATTEMPTS = 5
MAX_EXPANSION_ROUNDS = 10
EXPAND_WAIT_AFTER_CLICK = 2


def _human_type(element, text: str) -> None:
    import random
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))


def _save_debug_info(browser, prefix: str) -> None:
    from pathlib import Path
    try:
        logs_dir = Path(__file__).parent.parent / "Logs"
        logs_dir.mkdir(exist_ok=True)
        ts = int(time.time())
        screenshot_path = logs_dir / f"{prefix}_{ts}.png"
        browser.save_screenshot(str(screenshot_path))
        logger.info(f"Screenshot saved: {screenshot_path}")
        page_source_path = logs_dir / f"{prefix}_{ts}.html"
        with open(page_source_path, "w", encoding="utf-8") as f:
            f.write(browser.page_source)
        logger.info(f"Page source saved: {page_source_path}")
    except Exception as e:
        logger.error(f"Failed to save debug info: {e}")


def _dismiss_login_modal(browser) -> None:
    login_close_selectors = [
        "span.logSprite.icClose",
        "span.icClose",
        "span[class*='icClose']",
        "div.logPopInner span[class*='close']"
    ]
    for selector in login_close_selectors:
        try:
            elements = browser.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed():
                    el.click()
                    logger.info(f"Dismissed login modal: {selector}")
                    random_delay(0.5, 1.0)
                    return
        except Exception:
            continue


def _dismiss_popups(browser) -> None:
    _dismiss_login_modal(browser)
    popup_selectors = [
        "span[class*='close']",
        "span[class*='Close']",
        "button[class*='close']",
        "[aria-label='Close']",
        "div.shCalender span",
    ]
    for selector in popup_selectors:
        try:
            elements = browser.find_elements(By.CSS_SELECTOR, selector)
            for el in elements[:3]:
                try:
                    if el.is_displayed() and el.is_enabled():
                        el.click()
                        logger.debug(f"Dismissed popup: {selector}")
                        random_delay(0.2, 0.4)
                except Exception:
                    continue
        except Exception:
            continue


def _dismiss_lock_prices_popup(browser) -> bool:
    try:
        actions = ActionChains(browser)
        actions.move_by_offset(500, 300).click().perform()
        actions.reset_actions()
        time.sleep(0.3)
    except Exception:
        pass
    
    try:
        browser.execute_script("document.body.click();")
        time.sleep(0.2)
    except Exception:
        pass
    
    popup_selectors = [
        "button.buttonSecondry",
        "button[class*='buttonSecondry']",
        "button[class*='buttonPrimary']",
        "//button[contains(text(),'OKAY, GOT IT')]",
        "//button[contains(text(),'GOT IT')]",
        "//button[contains(text(),'Got It')]",
        "//button[contains(text(),'got it')]",
        "//span[contains(text(),'OKAY, GOT IT')]",
        "//span[contains(text(),'GOT IT')]",
        "//span[contains(text(),'Got It')]",
    ]
    
    for selector in popup_selectors:
        try:
            if selector.startswith("//"):
                elements = browser.find_elements(By.XPATH, selector)
            else:
                elements = browser.find_elements(By.CSS_SELECTOR, selector)
            
            for el in elements:
                try:
                    if el.is_displayed():
                        el_text = el.text.lower() if el.text else ""
                        if "got it" in el_text or "okay" in el_text or selector.startswith("button."):
                            try:
                                browser.execute_script("arguments[0].click();", el)
                            except Exception:
                                el.click()
                            logger.info("Dismissed 'Got It' popup instantly")
                            time.sleep(0.3)
                            return True
                except (StaleElementReferenceException, Exception):
                    continue
        except Exception:
            continue
    return False


def _wait_for_homepage_ready(browser, wait) -> bool:
    logger.info("Waiting for GoIbibo homepage...")
    random_delay(3, 5)
    _dismiss_popups(browser)
    homepage_indicators = [
        "#fromCity",
        "#toCity",
        "input.react-autosuggest__input",
        "div[class*='fswFrom']"
    ]
    for indicator in homepage_indicators:
        try:
            WebDriverWait(browser, SHORT_WAIT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, indicator))
            )
            logger.info(f"Homepage ready - found: {indicator}")
            return True
        except TimeoutException:
            continue
    logger.warning("Homepage readiness check failed")
    return False


def _click_city_field(browser, field_id: str) -> bool:
    try:
        field = browser.find_element(By.CSS_SELECTOR, f"#{field_id}")
        field.click()
        random_delay(0.5, 1.0)
        return True
    except Exception as e:
        logger.debug(f"Could not click {field_id}: {e}")
        return False


def _enter_city(browser, wait, field_id: str, city_code: str, field_name: str) -> bool:
    logger.info(f"Entering {field_name}: {city_code}")
    if not _click_city_field(browser, field_id):
        try:
            field = browser.find_element(By.CSS_SELECTOR, f"span#{field_id}, p#{field_id}, div#{field_id}")
            browser.execute_script("arguments[0].click();", field)
            random_delay(0.5, 1.0)
        except Exception as e:
            logger.error(f"Cannot click {field_name} field: {e}")
            return False
    random_delay(0.5, 1.0)
    try:
        active_input = browser.switch_to.active_element
        input_field = None
        input_selectors = [
            "input.react-autosuggest__input",
            "input[placeholder*='From']",
            "input[placeholder*='To']",
            "input[type='text']"
        ]
        for sel in input_selectors:
            inputs = browser.find_elements(By.CSS_SELECTOR, sel)
            for inp in inputs:
                if inp.is_displayed():
                    input_field = inp
                    break
            if input_field:
                break
        if input_field:
            input_field.clear()
            _human_type(input_field, city_code)
        else:
            active_input.send_keys(Keys.CONTROL + "a")
            _human_type(active_input, city_code)
        random_delay(1.5, 2.5)
        suggestion_selectors = [
            "li.react-autosuggest__suggestion",
            "ul.react-autosuggest__suggestions-list li",
            f"li[data-suggestion*='{city_code}']",
            "div.react-autosuggest__suggestions-container li"
        ]
        for sug_sel in suggestion_selectors:
            try:
                suggestions = browser.find_elements(By.CSS_SELECTOR, sug_sel)
                for sug in suggestions:
                    if sug.is_displayed():
                        sug.click()
                        logger.info(f"Selected suggestion for {field_name}")
                        random_delay(0.5, 1.0)
                        return True
            except Exception:
                continue
        active_input = browser.switch_to.active_element
        active_input.send_keys(Keys.ARROW_DOWN)
        random_delay(0.2, 0.4)
        active_input.send_keys(Keys.ENTER)
        logger.info(f"Selected {field_name} via keyboard")
        random_delay(0.5, 1.0)
        return True
    except Exception as e:
        logger.error(f"Failed to enter {field_name}: {e}")
        return False


def _trigger_search(browser, wait) -> bool:
    logger.info("Triggering flight search...")
    _dismiss_popups(browser)
    search_selectors = [
        "a.widgetSearchBtn",
        "button.widgetSearchBtn",
        "span.widgetSearchBtn",
        "a[data-cy='submit']",
        "button[data-cy='submit']"
    ]
    for selector in search_selectors:
        try:
            elements = browser.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed():
                    browser.execute_script("arguments[0].click();", el)
                    logger.info(f"Clicked search: {selector}")
                    return True
        except Exception:
            continue
    try:
        elements = browser.find_elements(By.XPATH, "//*[contains(text(),'SEARCH')]")
        for el in elements:
            if el.is_displayed():
                browser.execute_script("arguments[0].click();", el)
                logger.info("Clicked search by text")
                return True
    except Exception:
        pass
    logger.error("Failed to trigger search")
    return False


def _wait_for_results_page(browser, wait) -> bool:
    logger.info("Waiting for results page...")
    try:
        wait.until(lambda d: "flight/search" in d.current_url or "flights/air-" in d.current_url)
        logger.info(f"URL indicates results: {browser.current_url[:80]}...")
    except TimeoutException:
        logger.warning("URL did not change to results pattern")
    random_delay(5, 8)
    results_indicators = [
        "[class*='fltLstTubing']",
        "[class*='FlightCard']",
        "[class*='flightCard']",
        "[class*='srp-card']",
        "div[class*='sortingContainer']"
    ]
    for indicator in results_indicators:
        try:
            WebDriverWait(browser, SHORT_WAIT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, indicator))
            )
            logger.info(f"Results confirmed: {indicator}")
            return True
        except TimeoutException:
            continue
    logger.warning("Could not confirm results with known selectors - continuing anyway")
    return True


def _mutate_url_with_date(browser, target_date: str) -> bool:
    current_url = browser.current_url
    logger.info(f"Current URL: {current_url[:100]}...")
    day, month, year = target_date.split("/")
    new_date_str = f"{day}/{month}/{year}"
    date_pattern = re.compile(r'(\d{1,2}/\d{1,2}/\d{4})')
    match = date_pattern.search(current_url)
    if match:
        old_date = match.group(1)
        new_url = current_url.replace(old_date, new_date_str, 1)
        logger.info(f"Mutating date: {old_date} -> {new_date_str}")
        browser.get(new_url)
        return True
    date_pattern_alt = re.compile(r'(\d{8})')
    match_alt = date_pattern_alt.search(current_url)
    if match_alt:
        old_date = match_alt.group(1)
        new_date_clean = target_date.replace("/", "")
        new_url = current_url.replace(old_date, new_date_clean, 1)
        logger.info(f"Mutating date (alt): {old_date} -> {new_date_clean}")
        browser.get(new_url)
        return True
    logger.warning("Could not find date pattern in URL")
    return False


def _scroll_until_loaded(browser) -> int:
    import random
    stale_scroll_count = 0
    previous_count = 0
    scroll_attempts = 0
    logger.info("Scrolling to load all results...")
    while stale_scroll_count < MAX_STALE_SCROLLS and scroll_attempts < MAX_SCROLL_ATTEMPTS:
        scroll_attempts += 1
        cards = browser.find_elements(By.CSS_SELECTOR, 
            "[class*='FlightCard'], [class*='flightCard'], [class*='fltLstTubing'], [class*='srp-card']")
        current_count = len(cards)
        if current_count > previous_count:
            logger.debug(f"Cards: {previous_count} -> {current_count}")
            previous_count = current_count
            stale_scroll_count = 0
        else:
            stale_scroll_count += 1
        if stale_scroll_count >= MAX_STALE_SCROLLS:
            break
        scroll_amount = random.randint(800, 1200)
        browser.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(SCROLL_PAUSE_MIN, SCROLL_PAUSE_MAX))
    logger.info(f"Scroll complete. Cards: {previous_count}")
    return previous_count


def _expand_view_all_options(browser, clicked_cta_ids: set) -> int:
    import random
    expand_cta_selectors = [
        "//span[contains(text(),'View All')]",
        "//span[contains(text(),'View all')]",
        "//span[contains(text(),'view all')]",
        "//div[contains(text(),'View All')]",
        "//span[contains(text(),'Other')]",
        "//span[contains(text(),'other flight')]",
        "//span[contains(text(),'Other flight')]",
        "//span[contains(text(),'more flight')]",
        "//span[contains(text(),'More flight')]",
        "//button[contains(text(),'View All')]",
        "//a[contains(text(),'View All')]",
        "//*[contains(@class,'viewAll')]",
        "//*[contains(@class,'ViewAll')]",
        "//*[contains(@class,'otherFlights')]",
        "//*[contains(@class,'moreFlights')]"
    ]
    
    total_expanded = 0
    attempt = 0
    
    while attempt < MAX_EXPAND_ATTEMPTS:
        attempt += 1
        expanded_this_round = 0
        logger.debug(f"Expand attempt {attempt}/{MAX_EXPAND_ATTEMPTS}")
        
        browser.execute_script("window.scrollTo(0, 0);")
        random_delay(0.5, 1.0)
        
        page_height = browser.execute_script("return document.body.scrollHeight")
        scroll_position = 0
        scroll_step = 600
        
        while scroll_position < page_height:
            browser.execute_script(f"window.scrollTo(0, {scroll_position});")
            random_delay(0.3, 0.5)
            
            for xpath in expand_cta_selectors:
                try:
                    elements = browser.find_elements(By.XPATH, xpath)
                    for el in elements:
                        try:
                            if not el.is_displayed():
                                continue
                            
                            el_id = None
                            try:
                                el_loc = el.location
                                el_text_raw = el.text[:50] if el.text else ""
                                el_id = f"{el_loc.get('x',0)}_{el_loc.get('y',0)}_{el_text_raw}"
                            except Exception:
                                pass
                            
                            if el_id and el_id in clicked_cta_ids:
                                continue
                            
                            el_text = el.text.lower() if el.text else ""
                            if any(kw in el_text for kw in ['view all', 'other', 'more flight']):
                                try:
                                    el.click()
                                except ElementClickInterceptedException:
                                    browser.execute_script("arguments[0].click();", el)
                                
                                if el_id:
                                    clicked_cta_ids.add(el_id)
                                
                                expanded_this_round += 1
                                logger.debug(f"Clicked expand CTA: {el_text[:30]}")
                                random_delay(EXPAND_WAIT_AFTER_CLICK, EXPAND_WAIT_AFTER_CLICK + 1)
                                
                                page_height = browser.execute_script("return document.body.scrollHeight")
                                
                        except StaleElementReferenceException:
                            continue
                        except ElementNotInteractableException:
                            try:
                                browser.execute_script("arguments[0].click();", el)
                                expanded_this_round += 1
                                random_delay(EXPAND_WAIT_AFTER_CLICK, EXPAND_WAIT_AFTER_CLICK + 1)
                            except Exception:
                                continue
                        except Exception:
                            continue
                except Exception:
                    continue
            
            scroll_position += scroll_step
            page_height = browser.execute_script("return document.body.scrollHeight")
        
        total_expanded += expanded_this_round
        logger.debug(f"Expanded {expanded_this_round} CTAs in attempt {attempt}")
        
        if expanded_this_round == 0:
            break
    
    logger.info(f"Total expand CTAs clicked: {total_expanded}")
    return total_expanded


def _load_all_cards(browser) -> int:
    logger.info("Loading all cards (scroll + expand loop)...")
    clicked_cta_ids = set()
    previous_card_count = 0
    stale_rounds = 0
    
    for round_num in range(MAX_EXPANSION_ROUNDS):
        logger.debug(f"Load cards round {round_num + 1}/{MAX_EXPANSION_ROUNDS}")
        
        _scroll_until_loaded(browser)
        random_delay(1, 2)
        
        expanded = _expand_view_all_options(browser, clicked_cta_ids)
        random_delay(1, 2)
        
        cards = browser.find_elements(By.CSS_SELECTOR, 
            "[class*='FlightCard'], [class*='flightCard'], [class*='fltLstTubing'], [class*='srp-card']")
        current_card_count = len(cards)
        
        logger.debug(f"Round {round_num + 1}: {current_card_count} cards, {expanded} expansions")
        
        if current_card_count == previous_card_count and expanded == 0:
            stale_rounds += 1
            if stale_rounds >= 2:
                break
        else:
            stale_rounds = 0
        
        previous_card_count = current_card_count
    
    final_count = _scroll_until_loaded(browser)
    logger.info(f"All cards loaded. Final count: {final_count}")
    return final_count


def _find_flight_cards(browser) -> list:
    card_selectors = [
        "div.listingCard",
        "div[class*='listingCard']",
        "div[class*='fltLstTubing']",
        "div[class*='FlightCard']",
        "div[class*='flightCard']",
        "div[class*='srp-card']"
    ]
    for selector in card_selectors:
        cards = browser.find_elements(By.CSS_SELECTOR, selector)
        if cards:
            valid = []
            for c in cards:
                try:
                    text = c.text
                    if text and len(text) > 20 and "₹" in text:
                        if "Get Flat" not in text and "Lock this price" not in text and "COMPARE" not in text:
                            valid.append(c)
                except Exception:
                    continue
            if valid:
                logger.info(f"Found {len(valid)} valid cards using selector: {selector}")
                return valid
    
    logger.warning("Standard selectors failed, trying fallback with all divs...")
    divs = browser.find_elements(By.CSS_SELECTOR, "div")
    potential = []
    for div in divs:
        try:
            text = div.text
            if text and 40 < len(text) < 1000 and "₹" in text:
                if any(x in text for x in [":", "h", "min", "Stop", "Non", "stop"]):
                    if "Get Flat" not in text and "Lock this price" not in text:
                        potential.append(div)
        except Exception:
            continue
    logger.info(f"Fallback found {len(potential)} cards (no limit applied)")
    return potential


def _parse_card_text(card_text: str) -> dict:
    lines = [l.strip() for l in card_text.split("\n") if l.strip()]
    result = {
        "airline": "",
        "flight_code": "",
        "departure": "",
        "arrival": "",
        "duration": "",
        "stops": "Non stop",
        "price": parse_price(card_text)
    }
    
    time_pattern = re.compile(r'^\d{1,2}:\d{2}$')
    duration_pattern = re.compile(r'^\d+\s*h\s*\d*\s*m?$', re.IGNORECASE)
    code_pattern = re.compile(r'^[A-Z]{1,2}\s*-?\s*\d{2,5}$')
    
    for line in lines:
        if "₹" in line:
            continue
            
        line_lower = line.lower()
        if any(x in line_lower for x in ["stop", "via", "layover", "non-stop", "nonstop"]):
            result["stops"] = line
            continue
        if duration_pattern.match(line.replace(" ", "")):
            result["duration"] = line
            continue
        if time_pattern.match(line):
            if not result["departure"]:
                result["departure"] = line
            elif not result["arrival"]:
                result["arrival"] = line
            continue
        if code_pattern.match(line.upper().replace(" ", "")):
            if not result["flight_code"]:
                result["flight_code"] = line
            continue
        if not result["airline"] and len(line) > 3 and line[0].isupper():
            has_digit = any(c.isdigit() for c in line)
            if "free" in line_lower or "meal" in line_lower or "|" in line:
                continue
            if not has_digit or len(line) > 12:
                result["airline"] = line
    return result


def run(browser) -> tuple[bool, Any]:
    wait = WebDriverWait(browser, WAIT_TIMEOUT)
    flights_list = []
    try:
        input_data = load_input()
        departure = input_data["departure"]
        arrival = input_data["arrival"]
        target_date = input_data["date"]
        logger.info("=" * 80)
        logger.info("GoIbibo Scraper - Homepage Flow + URL Mutation")
        logger.info(f"Route: {departure} -> {arrival}, Date: {target_date}")
        logger.info("=" * 80)

        logger.info("Step 1: Navigate to GoIbibo homepage")
        browser.get(GOIBIBO_HOME)
        random_delay(4, 6)
        _dismiss_popups(browser)
        if not _wait_for_homepage_ready(browser, wait):
            _save_debug_info(browser, "goibibo_homepage_fail")
            return (False, None)
        _dismiss_popups(browser)

        logger.info("Step 2: Enter departure city")
        if not _enter_city(browser, wait, "fromCity", departure, "departure"):
            _save_debug_info(browser, "goibibo_departure_fail")
            return (False, None)
        _dismiss_popups(browser)
        random_delay(0.5, 1.0)

        logger.info("Step 3: Enter arrival city")
        if not _enter_city(browser, wait, "toCity", arrival, "arrival"):
            _save_debug_info(browser, "goibibo_arrival_fail")
            return (False, None)
        _dismiss_popups(browser)
        random_delay(1, 2)

        logger.info("Step 4: Trigger search (skip date picker)")
        _dismiss_popups(browser)
        if not _trigger_search(browser, wait):
            _save_debug_info(browser, "goibibo_search_fail")
            return (False, None)

        logger.info("Step 5: Wait for initial results")
        if not _wait_for_results_page(browser, wait):
            _save_debug_info(browser, "goibibo_results_fail")
        
        logger.info("Step 5b: Dismiss Lock Prices popup instantly")
        _dismiss_lock_prices_popup(browser)

        logger.info("Step 6: Mutate URL with target date")
        random_delay(1, 2)
        if not _mutate_url_with_date(browser, target_date):
            logger.warning("URL mutation failed - using current results")
        random_delay(3, 5)
        _dismiss_popups(browser)

        logger.info("Step 7: Handle post-mutation popups instantly")
        _dismiss_lock_prices_popup(browser)

        logger.info("Step 8: Load all cards (scroll + expand loop)")
        _load_all_cards(browser)
        random_delay(1, 2)

        logger.info("Step 9: Extract flight data")
        flight_cards = _find_flight_cards(browser)
        if not flight_cards:
            logger.error("No flight cards found")
            _save_debug_info(browser, "goibibo_no_cards")
            return (False, None)
        logger.info(f"Processing {len(flight_cards)} cards...")
        for idx, card in enumerate(flight_cards, 1):
            try:
                card_text = card.text
                if not card_text or "₹" not in card_text:
                    continue
                parsed = _parse_card_text(card_text)
                if not parsed["departure"] or not parsed["arrival"] or parsed["price"] == 0:
                    continue
                flights_list.append(build_flight_record(
                    source="Goibibo",
                    airline=parsed["airline"],
                    flight_code=parsed["flight_code"],
                    departure=parsed["departure"],
                    arrival=parsed["arrival"],
                    duration=parsed["duration"],
                    stops=parsed["stops"],
                    price=parsed["price"]
                ))
            except StaleElementReferenceException:
                continue
            except Exception as e:
                logger.debug(f"Card {idx} error: {e}")
                continue
        if not flights_list:
            logger.error("No valid flights extracted")
            _save_debug_info(browser, "goibibo_no_data")
            return (False, None)

        unique = deduplicate_flights(flights_list)
        df = pd.DataFrame(unique)
        logger.info("=" * 80)
        logger.info(f"SUCCESS: {len(df)} unique flights from GoIbibo")
        logger.info("=" * 80)
        return (True, df)

    except NoSuchWindowException:
        logger.error("Browser window closed unexpectedly during scraping")
        return (False, None)
    except Exception as e:
        logger.error(f"GoIbibo scraper failed: {e}", exc_info=True)
        try:
            _save_debug_info(browser, "goibibo_error")
        except Exception:
            pass
        return (False, None)
