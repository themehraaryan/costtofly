from typing import Any
import time
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from loggerconfig import setup_logger
from scrapers import makeMyTrip, goibibo, cleartrip

logger = setup_logger()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
GOOGLE_URL = "https://www.google.co.in"
GOOGLE_WAIT_TIMEOUT = 20

class DataScraper:
    def __init__(self):
        self.scrapers = [
            ("MakeMyTrip", makeMyTrip),
            ("Goibibo", goibibo),
            ("Cleartrip", cleartrip),
        ]
        self.results = {}

    def _create_browser(self) -> uc.Chrome:
        options = Options()
        
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.geolocation": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        chrome_args = [
            "--disable-blink-features=AutomationControlled",
            f"--user-agent={USER_AGENT}",
            "--window-size=1920,1080",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-extensions",
            "--disable-popup-blocking",
            "--disable-notifications",
            "--log-level=3",
            "--no-first-run",
        ]
        for arg in chrome_args:
            options.add_argument(arg)
        
        driver = uc.Chrome(options=options)
        
        time.sleep(2)
        
        try:
            logger.info(f"Navigating to {GOOGLE_URL} for browser initialization...")
            driver.get(GOOGLE_URL)
            
            time.sleep(3)
            
            wait = WebDriverWait(driver, GOOGLE_WAIT_TIMEOUT)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name='q'], input[name='q']")))
            
            logger.info("Google search bar detected, browser ready")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to initialize browser with Google: {e}", exc_info=True)
            try:
                driver.quit()
            except:
                pass
            raise

    def _terminate_browser(self, browser: uc.Chrome) -> None:
        if browser is None:
            return
        try:
            browser.quit()
            logger.info("Browser successfully terminated")
        except OSError:
            pass
        except Exception:
            pass

    def _execute_scraper(self, name: str, scraper_module: Any) -> tuple[bool, Any]:
        browser = None
        try:
            logger.info(f"Starting scraper: {name}")
            browser = self._create_browser()
            success, data = scraper_module.run(browser)
            
            if success:
                logger.info(f"{name} scraper completed successfully")
                return (True, data)
            else:
                logger.warning(f"{name} scraper returned failure")
                return (False, None)
                
        except Exception as e:
            logger.error(f"{name} scraper crashed: {e}", exc_info=True)
            return (False, None)
            
        finally:
            if browser:
                self._terminate_browser(browser)

    def run(self) -> tuple[bool, dict[str, Any]]:
        logger.info("DataScraper orchestration started")
        overall_success = False
        
        for name, scraper_module in self.scrapers:
            success, data = self._execute_scraper(name, scraper_module)
            
            if success:
                self.results[name] = data
                overall_success = True
            else:
                self.results[name] = None
        
        logger.info(f"DataScraper orchestration completed. Successful scrapers: {sum(1 for v in self.results.values() if v is not None)}/{len(self.scrapers)}")
        return (overall_success, self.results)
