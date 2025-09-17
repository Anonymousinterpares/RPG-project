#!/usr/bin/env python3
"""
Script for managing LLM settings via CLI.

This script serves as an entry point for the LLM settings CLI,
allowing users to manage LLM settings, API keys, and agent configurations.
"""

import sys
import os
from core.llm.settings_cli import main as settings_cli_main

if __name__ == "__main__":
    # Add the current directory to the path to ensure imports work
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Run the settings CLI
    settings_cli_main()