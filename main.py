import sys

from loggerconfig import setup_logger
from dataScraper import DataScraper
from dataAnalyser import DataAnalyser

logger = setup_logger()

if __name__ == "__main__":
    try:
        scraper = DataScraper()
        success, scraped_data = scraper.run()
        
        if success:
            logger.info("Data scraping completed successfully")
            logger.info(f"Scraped data: {scraped_data}")
            analyser = DataAnalyser()
            analyser.analyse(scraped_data)
        else:
            logger.error("Data scraping failed - no data collected")
            
    except Exception as e:
        logger.error(f"An error occurred in main: {e}", exc_info=True)
    finally:
        sys.exit()