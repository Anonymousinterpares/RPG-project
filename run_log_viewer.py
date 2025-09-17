#!/usr/bin/env python3
"""
Entry point for the Log Viewer application.
"""
import sys
import os

# Add the project root to the Python path to allow imports from log_viewer_tool
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from log_viewer_tool.main_window import MainWindow
from core.utils.logging_config import setup_logging, configure_logging, LOG_DIRECTORY # Import configure_logging and LOG_DIRECTORY

# Define a specific log directory for the log viewer tool
LOG_VIEWER_TOOL_LOG_DIR = os.path.join(project_root, "log_viewer_tool", "logs")

if __name__ == "__main__":
    # Configure logging for the tool to use its own directory
    original_log_dir = LOG_DIRECTORY # Store original
    import core.utils.logging_config
    core.utils.logging_config.LOG_DIRECTORY = LOG_VIEWER_TOOL_LOG_DIR
    
    setup_logging() # Initialize logging for the tool itself using the new path

    core.utils.logging_config.LOG_DIRECTORY = original_log_dir

    app = QApplication(sys.argv)
    
    app.setStyle("Fusion")

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())