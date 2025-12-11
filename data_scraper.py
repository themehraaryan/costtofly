import time
import subprocess
import sys

import undetected_chromedriver as uc

# Drop unused selenium imports if not needed
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options

from loggerconfig import setup_logger
logger = setup_logger()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

class DataScraper:
    def toggle_vpn(self, action: str) -> None:
        try:
            if action == "on":
                result = subprocess.run(["warp-cli", "connect"], capture_output=True, text=True)
            elif action == "off":
                result = subprocess.run(["warp-cli", "disconnect"], capture_output=True, text=True)
            else:
                raise ValueError(f"Unsupported VPN action: {action}")

            if result.stdout.strip() != "Success":
                logger.error("VPN toggle failed (%s): %s", action, result.stdout.strip())
                sys.exit(1)

            logger.info(result.stdout.strip())
            time.sleep(7)
        except Exception as e:
            logger.error(f"Error toggling VPN '{action}': {e}", exc_info=True)
            raise

    def create_driver(self):
        try:
            options = uc.ChromeOptions()
            chrome_args = [
                "--disable-blink-features=AutomationControlled",
                f"--user-agent={USER_AGENT}",
                "--window-size=1920,1080",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-popup-blocking",
                "--log-level=3",
                "--no-first-run",
                "--fast-start",
                "--start-maximized",
            ]
            for arg in chrome_args:
                options.add_argument(arg)

            logger.info("starting browser...")
            driver = uc.Chrome(options=options)
            logger.info("browser started")

            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'}
            )

            google_url = "https://www.google.com/search?hl=en&gl=IN&pws=0"
            driver.get(google_url)
            time.sleep(2)
            logger.info("Google homepage loaded successfully")
            return driver, True

        except Exception as e:
            logger.error(f"Error creating browser: {e}", exc_info=True)
            raise

    def run(self) -> bool:
        driver = None
        try:
            self.toggle_vpn("on")
            driver, success = self.create_driver()
            return bool(success)
        except Exception as e:
            logger.critical(f"Fatal Error in Main Execution: {e}", exc_info=True)
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.error(f"Error quitting driver: {e}", exc_info=True)
            try:
                self.toggle_vpn("off")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}", exc_info=True)