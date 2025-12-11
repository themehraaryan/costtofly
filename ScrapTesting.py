import undetected_chromedriver as uc
from loggerconfig import setup_logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging = setup_logger()

# Optional: silence the destructor that raises during interpreter shutdown
# (safe because you explicitly quit the driver)
uc.Chrome.__del__ = lambda self: None

url = "https://www.makemytrip.com/flight/search?itinerary=DEL-BLR-12/12/2025&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E&lang=eng"

options = uc.ChromeOptions()
options.add_argument("--start-maximized")
# options.add_argument("--headless=new")

driver = uc.Chrome(options=options)

try:
    driver.get(url)

    el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "flightBody"))
    )

    logging.info("Element found!")
    inner_html = el.get_attribute("innerHTML")
    outer_html = el.get_attribute("outerHTML")
    text_only = el.text

except Exception as e:
    logging.exception("Error during scrape: %s", e)

finally:
    try:
        driver.quit()
    except Exception as e:
        # swallow WinError 6 and similar shutdown races — log and continue
        logging.exception("Ignored error while quitting driver: %s", e)
