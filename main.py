import sys

from loggerconfig import setup_logger
from dataScraper import DataScraper
from dataAnalyser import DataAnalyser
from visualizer import generate_visualizations

logger = setup_logger()

if __name__ == "__main__":
    exit_code = 1
    try:
        scraper = DataScraper()
        success, scraped_data = scraper.run()
        
        if success:
            logger.info("Data scraping completed successfully")
            
            analyser = DataAnalyser()
            master_df, metrics = analyser.analyse(scraped_data)
            
            if master_df is not None and not master_df.empty:
                chart_paths = generate_visualizations(master_df, metrics)
                logger.info(f"Generated {len(chart_paths)} visualizations")
            
            logger.info("Pipeline completed successfully")
            exit_code = 0
        else:
            logger.error("Data scraping failed - no data collected")
            
    except Exception as e:
        logger.error(f"An error occurred in main: {e}", exc_info=True)
    finally:
        sys.exit(exit_code)