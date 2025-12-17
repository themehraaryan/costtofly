from typing import Any

from loggerconfig import setup_logger

logger = setup_logger()


def run(browser) -> tuple[bool, Any]:
    logger.warning("Cleartrip scraper not implemented yet")
    return (False, None)
