"""
Logging setup for the World Configurator Tool.
"""

import os
import logging
import datetime
from logging.handlers import RotatingFileHandler

def setup_logging(level=logging.INFO):
    """
    Set up logging for the World Configurator Tool.
    
    Args:
        level: The logging level to use.
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log filename with date
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(logs_dir, f"world_configurator_{date_str}.log")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    
    # Create file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5
    )
    file_handler.setLevel(level)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers to root logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Create world_configurator logger
    wc_logger = logging.getLogger("world_configurator")
    wc_logger.setLevel(level)
    
    return wc_logger
