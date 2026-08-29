import logging
from pathlib import Path

LOG_DIR = Path("logs")
logger = logging.getLogger("executor")

def setup_logging(test_case_name):
    """
    Configure logging for a test case.
    Logs are written to logs/{test_case_name}.log and displayed in the console.
    """
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{test_case_name}.log"

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove existing handlers
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    # File handler
    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
    )

    # Console handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter(
            "%(levelname)s - %(message)s"
        )
    )

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
