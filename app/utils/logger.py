import logging
import sys


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_LEVEL = logging.INFO


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    Each logger gets its own handler and no propagation to avoid duplicates.
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        # Create handler for this specific logger
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))

        logger.setLevel(LOG_LEVEL)
        logger.addHandler(handler)
        # Prevent propagation to parent loggers to avoid duplicates
        logger.propagate = False

    return logger


def configure_logging():
    """
    Configure application-wide logging to prevent duplicates.
    """
    # Disable uvicorn access logging to prevent duplicates
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.disabled = True

    # Configure uvicorn main logger
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.WARNING)  # Only show warnings and errors

    # Configure fastapi logger
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.setLevel(logging.WARNING)

    # Configure root logger to prevent duplicates
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)

    # Remove any existing handlers from root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
