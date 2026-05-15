import logging
import sys
from pathlib import Path

class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.INFO

def setup_logging():
    log_dir = Path(__file__).resolve().parent.parent.parent / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Prevent adding duplicate handlers on reload
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler for all levels
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Info file handler
    info_handler = logging.FileHandler(log_dir / "info.log", mode='w')
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(InfoFilter())
    info_handler.setFormatter(formatter)
    root_logger.addHandler(info_handler)

    # Error file handler for WARNING and above
    error_handler = logging.FileHandler(log_dir / "error.log", mode='w')
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    logging.info("Logging configured. INFO -> info.log, WARNING+ -> error.log")
