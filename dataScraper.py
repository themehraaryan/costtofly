from typing import Any
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

from loggerconfig import setup_logger
from scrapers import makeMyTrip

logger = setup_logger()


class DataScraper:
    def __init__(self):
        self.scrapers = [
            ("MakeMyTrip", makeMyTrip),
            # ("Goibibo", goibibo),
            # ("Cleartrip", cleartrip),
            # ("EaseMyTrip", easeMyTrip)
        ]
        self.results = {}

    def _create_browser(self) -> uc.Chrome:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        return uc.Chrome(options=options)

    def _terminate_browser(self, browser: uc.Chrome) -> None:
        try:
            browser.quit()
        except OSError as e:
            logger.warning(f"OS error terminating browser: {e}")
        except Exception as e:
            logger.error(f"Error terminating browser: {e}")

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
