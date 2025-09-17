#!/usr/bin/env python3
"""
Main entry point for the RPG game.
This script handles initialization and startup of the game in GUI mode.
"""

import sys
import argparse
import logging
from dotenv import load_dotenv # Import load_dotenv

# Import module initializer
from core.base.init_modules import init_modules
# Use centralized logging config
from core.utils.logging_config import setup_logging as core_setup_logging

# Application version
VERSION = "0.1.0"

def setup_logging():
    """Set up logging using the centralized project configuration."""
    core_setup_logging()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="RPG Game")
    parser.add_argument("--version", action="version", version=f"RPG Game v{VERSION}")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser.parse_args()

def main():
    """Main entry point for the game."""
    load_dotenv() # Load environment variables from .env file
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    setup_logging()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Log startup information
    logging.info(f"Starting RPG Game v{VERSION}")
    
    # Initialize all game modules
    init_modules()
    
    # GUI mode
    logging.info("Running in GUI mode")
    try:
        # Import the GUI runner
        from run_gui import run_gui
        run_gui()
    except ImportError as e:
        logging.error(f"Failed to import GUI components: {e}")
        print("Error: Could not start GUI mode. See log for details.")
        sys.exit(1)
    except Exception as e:
        logging.exception(f"Error starting GUI: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()