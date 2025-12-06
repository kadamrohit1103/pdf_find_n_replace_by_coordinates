import logging
import sys

def setup_logger(verbose: bool = False) -> logging.Logger:
    """Sets up the logger with appropriate level and formatting."""
    logger = logging.getLogger("PDFTextReplacer")
    # Avoid adding multiple handlers if already setup
    if logger.hasHandlers():
        logger.handlers.clear()
        
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    return logger
