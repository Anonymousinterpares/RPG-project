#!/usr/bin/env python3
"""
GUI runner for the RPG game.
This script initializes and runs the GUI interface.
"""

import sys
import logging
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from core.base.engine import get_game_engine
from core.utils.logging_config import setup_logging
from gui.utils.init_settings import init_default_settings
from core.base.init_modules import init_modules

def run_gui():
    """Initialize and run the GUI application."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger("GUI")
    logger.info("Initializing GUI application")
    
    try:
        # Initialize all game modules
        init_modules()
        
        # Create Qt Application
        app = QApplication(sys.argv)
        app.setApplicationName("RPG Game")
        
        # Initialize default settings
        init_default_settings()
        
        # Initialize game engine
        engine = get_game_engine()
        
        # Create main window
        win = MainWindow()
        win.show()
        
        logger.info("GUI application started")
        
        # Run the application
        return app.exec()
    
    except Exception as e:
        logger.exception(f"Error initializing GUI: {e}")
        raise

if __name__ == "__main__":
    # Exit with the application return code
    sys.exit(run_gui())
