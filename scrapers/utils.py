import json
import re
import time
import random
from pathlib import Path
from datetime import datetime

from selenium.webdriver.common.by import By

INPUT_PATH = Path(__file__).parent.parent / "input.json"

PRICE_MIN = 1000
PRICE_MAX = 100000


def load_input() -> dict:
    with open(INPUT_PATH, "r") as f:
        return json.load(f)


def parse_duration_minutes(duration_str: str) -> int:
    if not duration_str or (hasattr(duration_str, '__iter__') and not isinstance(duration_str, str)):
        return 9999
    
    duration_str = str(duration_str).lower().strip()
    if not duration_str:
        return 9999
    
    hours, minutes = 0, 0
    
    if 'h' in duration_str:
        parts = duration_str.split('h')
        hours = int(''.join(c for c in parts[0] if c.isdigit()) or 0)
        if len(parts) > 1 and 'm' in parts[1]:
            minutes = int(''.join(c for c in parts[1] if c.isdigit()) or 0)
    elif 'm' in duration_str:
        minutes = int(''.join(c for c in duration_str if c.isdigit()) or 0)
    
    total = hours * 60 + minutes
    return total if total > 0 else 9999


def parse_price(text: str) -> int:
    if not text:
        return 0
    
    all_prices = []
    price_matches = re.findall(r'₹\s*([\d,]+)', text)
    
    for match in price_matches:
        digits = match.replace(",", "").strip()
        if digits.isdigit():
            price_val = int(digits)
            if PRICE_MIN <= price_val <= PRICE_MAX:
                all_prices.append(price_val)
    
    return max(all_prices) if all_prices else 0


def deduplicate_flights(flights: list) -> list:
    if not flights:
        return []
    
    seen = set()
    unique = []
    
    for f in flights:
        key = (f.get("departure", ""), f.get("arrival", ""), f.get("price", 0))
        if key not in seen:
            seen.add(key)
            unique.append(f)
    
    return unique


def random_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def wait_for_skeleton_loaders(browser, timeout: float = 5.0) -> None:
    skeleton_selectors = [
        "[class*='skeleton']",
        "[class*='Skeleton']",
        "[class*='loading']",
        "[class*='shimmer']",
        "[class*='placeholder']",
    ]
    
    end_time = time.time() + timeout
    
    while time.time() < end_time:
        found = False
        for sel in skeleton_selectors:
            try:
                elements = browser.find_elements(By.CSS_SELECTOR, sel)
                for el in elements:
                    try:
                        if el.is_displayed() and el.size.get('height', 0) > 10:
                            found = True
                            break
                    except Exception:
                        continue
                if found:
                    break
            except Exception:
                continue
        
        if not found:
            break
        
        time.sleep(0.5)


def build_flight_record(
    source: str,
    airline: str,
    flight_code: str,
    departure: str,
    arrival: str,
    duration: str,
    stops: str,
    price: int
) -> dict:
    return {
        "source": source,
        "airline": airline or "Unknown",
        "flight_code": flight_code,
        "departure": departure,
        "arrival": arrival,
        "duration": duration,
        "stops": stops,
        "price": price,
        "timestamp": datetime.now().isoformat()
    }
