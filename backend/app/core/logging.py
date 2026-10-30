import logging
import sys


def setup_logging(app_env: str = "development") -> logging.Logger:
    """Configure enterprise application logging format and thresholds."""
    is_prod = app_env.strip().lower() == "production"
    log_level = logging.INFO if is_prod else logging.DEBUG

    # Formatter for structured console output
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("sparehub")
    logger.setLevel(log_level)
    return logger


logger = logging.getLogger("sparehub")
