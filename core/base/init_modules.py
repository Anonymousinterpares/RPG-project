"""
Module initialization for the RPG game.

This module imports all necessary modules to ensure they are initialized properly.
"""

import logging
from core.utils.logging_config import get_logger

# Get the module logger
logger = get_logger("SYSTEM")

def init_modules():
    """Initialize all necessary modules."""
    logger.info("Initializing game modules...")
    
    # Import core modules
    try:
        # Import inventory
        import core.inventory
        logger.info("Inventory module initialized")
        
        # Import combat system
        import core.combat
        logger.info("Combat module initialized")
        
        # Add other modules as needed
        
        logger.info("All modules initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing modules: {e}", exc_info=True)
        return False
