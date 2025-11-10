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

        # Conditionally activate startup tracer
        try:
            from PySide6.QtCore import QSettings
            settings = QSettings("RPGGame", "Settings")
            dev_mode = settings.value("dev/enabled", False, type=bool)
            trace_enabled = settings.value("dev/startup_trace_enabled", False, type=bool)
            if dev_mode and trace_enabled:
                import core.utils.startup_trace
                core.utils.startup_trace.activate()
                logger.info("Startup tracer activated.")
        except Exception as e:
            logger.error(f"Failed to check or activate startup tracer: {e}")
        
        # Apply stats_manager logging visibility based on settings
        try:
            from PySide6.QtCore import QSettings
            s = QSettings("RPGGame", "Settings")
            dev_enabled = bool(s.value("dev/enabled", False, type=bool))
            show_stats_logs = bool(s.value("dev/show_stats_manager_logs", False, type=bool))
            stats_logger = logging.getLogger("core.stats.stats_manager")
            if dev_enabled and show_stats_logs:
                stats_logger.setLevel(logging.DEBUG)
            else:
                stats_logger.setLevel(logging.WARNING)
        except Exception:
            # Never fail GUI startup due to settings/logging application
            pass
        
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
