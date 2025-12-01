#!/usr/bin/env python
"""
World Configurator Tool for the RPG Project.

This tool allows creating and editing world configuration for the RPG game.
"""

import os
import sys

# Add the project root to the Python path so we can use absolute imports
project_root = os.path.dirname(os.path.abspath(__file__))
# Add parent directory to allow importing world_configurator as a package
parent_dir = os.path.dirname(project_root)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from utils.logging_setup import setup_logging

def main():
    """
    Main entry point for the World Configurator Tool.
    """
    # Setup logging
    setup_logging()
    logger = setup_logging("world_configurator")
    logger.info("Starting World Configurator Tool")
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("World Configurator")
    app.setApplicationVersion("1.0.0")
    
    # Create main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
