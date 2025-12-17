from typing import Any

from loggerconfig import setup_logger

logger = setup_logger()


class DataAnalyser:
    def analyse(self, scraped_data: dict[str, Any]) -> None:
        logger.info("DataAnalyser: analysis not implemented yet")
        pass
