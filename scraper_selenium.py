import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

url = "https://www.makemytrip.com/flight/search?itinerary=DEL-BLR-11/12/2025&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E&lang=eng"

options = uc.ChromeOptions()
options.add_argument("--start-maximized")
driver = uc.Chrome(options=options)

driver.get(url)

try:
    el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "flightBody"))
    )

    # all HTML inside the div (without the outer <div> tag)
    inner_html = el.get_attribute("innerHTML")
    print("INNER HTML:\n", inner_html)

    # HTML including the <div> tag itself
    outer_html = el.get_attribute("outerHTML")
    print("\nOUTER HTML:\n", outer_html)

    # just visible text inside the div
    text_only = el.text
    print("\nTEXT:\n", text_only)

except Exception as e:
    print("not found:", e)
finally:
    driver.quit()
