"""
Logging configuration for the game.
"""

import os
import logging
import logging.handlers
import time
from typing import Dict, Optional

# Global configuration
DEFAULT_LEVEL = logging.DEBUG
LOGGERS: Dict[str, logging.Logger] = {}
LOGGER_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')

# Migration tracking - add to track fixed imports
LOG_MIGRATION_FIXES = True


def setup_logging(level: int = DEFAULT_LEVEL) -> None:
    """
    Set up the logging system for the application.
    
    Args:
        level: The log level to use.
    """
    return configure_logging(level)


def configure_logging(level: int = DEFAULT_LEVEL) -> None:
    """
    Configure the logging system.
    
    Args:
        level: The log level to use.
    """
    # Create log directory if it doesn't exist
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove all handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Set the format
    formatter = logging.Formatter(LOGGER_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(formatter)
    
    # Add the console handler to the root logger
    root_logger.addHandler(console_handler)
    
    # Create a file handler for all logs
    log_file = os.path.join(LOG_DIRECTORY, f'game_{time.strftime("%Y%m%d_%H%M%S")}.log')
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'  # Explicitly set encoding
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # Add the file handler to the root logger
    root_logger.addHandler(file_handler)
    
    # Create a file handler for errors only
    error_log_file = os.path.join(LOG_DIRECTORY, f'error_{time.strftime("%Y%m%d_%H%M%S")}.log')
    error_file_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=5,
        encoding='utf-8'  # Explicitly set encoding
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    
    # Add the error file handler to the root logger
    root_logger.addHandler(error_file_handler)
    
    # Log that logging is configured
    root_logger.info("Logging configured")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    If the logger doesn't exist, it will be created and configured.
    
    Args:
        name: The name of the logger.
    
    Returns:
        The logger.
    """
    # Check if the logger is already cached
    if name in LOGGERS:
        return LOGGERS[name]
    
    # Create a new logger
    logger = logging.getLogger(name)
    
    # Special per-logger file sink for TIME_AUDIT
    try:
        if name == "TIME_AUDIT":
            # Ensure log directory exists
            if not os.path.exists(LOG_DIRECTORY):
                os.makedirs(LOG_DIRECTORY)
            audit_log_file = os.path.join(LOG_DIRECTORY, 'time_audit.log')
            # Attach a rotating file handler specifically for audit lines
            audit_handler = logging.handlers.RotatingFileHandler(
                audit_log_file,
                maxBytes=5*1024*1024,  # 5 MB
                backupCount=3,
                encoding='utf-8'
            )
            audit_handler.setLevel(logging.INFO)
            audit_formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s', DATE_FORMAT)
            audit_handler.setFormatter(audit_formatter)
            # Avoid duplicate handlers if logger was created but not cached
            if not any(isinstance(h, logging.handlers.RotatingFileHandler) and getattr(h, 'baseFilename', '') == audit_log_file for h in logger.handlers):
                logger.addHandler(audit_handler)
            logger.setLevel(logging.INFO)
            # Let it also propagate to root if desired (kept True)
            logger.propagate = True
    except Exception:
        # Never fail logger creation due to audit setup
        pass
    
    # Cache the logger
    LOGGERS[name] = logger
    
    return logger


def log_migration_fix(module_name: str, old_import: str, new_import: str) -> None:
    """
    Log a migration fix for import paths.
    
    Args:
        module_name: The name of the module being fixed
        old_import: The old, incorrect import path
        new_import: The new, correct import path
    """
    if not LOG_MIGRATION_FIXES:
        return
        
    logger = get_logger("MIGRATION")
    logger.info(f"Fixed import in {module_name}: '{old_import}' -> '{new_import}'")