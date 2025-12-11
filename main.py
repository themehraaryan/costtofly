import sys

from loggerconfig import setup_logger
from data_scraper import DataScraper

logger = setup_logger()

if __name__ == "__main__":
    try:

        scraper = DataScraper()
        status = scraper.run()
        if status:
            logger.info("Data scraping completed successfully.")
        else:
            logger.error("Data scraping failed.")
    except Exception as e:
        logger.error(f"An error occurred in main: {e}", exc_info=True)
    finally:
        sys.exit()