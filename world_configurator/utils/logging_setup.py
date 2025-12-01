"""
Logging setup for the World Configurator Tool.
"""

import os
import logging
import datetime
from logging.handlers import RotatingFileHandler

# Global flag to track if logging has been initialized
_LOGGING_SETUP_DONE = False

def setup_logging(name_or_level="world_configurator", level=logging.INFO):
    """
    Set up logging for the World Configurator Tool.
    
    Args:
        name_or_level: The logger name (str) or logging level (int). 
                       Defaults to "world_configurator".
        level: The logging level to use (int), used if name_or_level is a string.
               Defaults to logging.INFO.

    Returns:
        logging.Logger: The requested logger.
    """
    global _LOGGING_SETUP_DONE
    
    target_name = "world_configurator"
    target_level = level

    # Handle overloaded arguments
    if isinstance(name_or_level, int):
        target_level = name_or_level
    elif isinstance(name_or_level, str):
        target_name = name_or_level

    # Only configure the root logger handlers once
    if not _LOGGING_SETUP_DONE:
        # Create logs directory if it doesn't exist
        # go up from utils/logging_setup.py to world_configurator root
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create log filename with date
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(logs_dir, f"world_configurator_{date_str}.log")
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(target_level)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(target_level)
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
        file_handler.setLevel(target_level)
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        
        # Add handlers to root logger
        if not root_logger.handlers:
            root_logger.addHandler(console_handler)
            root_logger.addHandler(file_handler)
        
        _LOGGING_SETUP_DONE = True
    
    # Get the requested logger
    logger = logging.getLogger(target_name)
    logger.setLevel(target_level)
    
    return logger