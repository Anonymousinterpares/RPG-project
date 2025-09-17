#!/usr/bin/env python3
"""
Configuration management for the RPG game.

This module provides a GameConfig class for loading, managing, and accessing
configuration data from JSON files.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import json

from core.utils.json_utils import load_json, save_json
from core.utils.logging_config import get_logger

# Get the module logger
logger = get_logger("SYSTEM")

class GameConfig:
    """
    Game configuration manager.

    This class handles loading configuration from JSON files,
    providing access to configuration values, and saving
    updated configurations.

    It supports dot notation for accessing nested configuration values
    (e.g., config.get("gui.window.width")).
    """

    # Singleton instance
    _instance = None

    # Default configuration directory relative to project root
    _CONFIG_DIR = "config"

    # Default configuration files, mapping domain to relative path within _CONFIG_DIR
    _DEFAULT_CONFIG_FILES = {
        "game": "game_config.json",
        "system": "system_config.json",
        "gui": "gui_config.json",
        "llm": "llm/base_config.json", # Added LLM config
        "classes": os.path.join("character", "classes.json"),
        "races": os.path.join("character", "races.json"),
        "origins": os.path.join("world", "scenarios", "origins.json"),
        "quests": os.path.join("world", "scenarios", "quests.json"),
        "locations": os.path.join("world", "locations", "locations.json")
    }

    # Configurations loaded from files
    _config_data: Dict[str, Dict[str, Any]] = {}

    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(GameConfig, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_dir: str = None):
        """Initialize the configuration."""
        # Prevent re-initialization
        if hasattr(self, '_initialized') and self._initialized:
            return

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._config_dir_abs = os.path.join(project_root, config_dir or self._CONFIG_DIR)

        self._config_data = {}

        os.makedirs(self._config_dir_abs, exist_ok=True)

        for domain in self._DEFAULT_CONFIG_FILES:
            self._config_data[domain] = {}

        # Load configurations
        self._load_all_configs()

        self._initialized = True

    def _load_all_configs(self):
        """Load all configuration files."""
        for domain, filename_rel in self._DEFAULT_CONFIG_FILES.items():
            self._load_config(domain, filename_rel)

    def _load_config(self, domain: str, filename_rel: str):
        """
        Load a configuration file for the specified domain.

        Args:
            domain: The configuration domain name (e.g., "game", "classes").
            filename_rel: The relative path of the file within the config directory
                          (e.g., "game_config.json", "character/classes.json").
        """
        # Construct the absolute file path
        file_path = os.path.join(self._config_dir_abs, filename_rel)

        # Log the attempt
        logger.info(f"Attempting to load configuration for domain '{domain}' from: {file_path}")

        # If the file doesn't exist, handle defaults or warnings
        if not os.path.exists(file_path):
            # Only create defaults for the original base configs
            if domain in ["game", "system", "gui", "llm"]: # Add llm here if it needs defaults
                logger.warning(f"Config file for '{domain}' not found. Creating default: {file_path}")
                self._create_default_config(domain, file_path) # Pass absolute path
            else:
                # For other configs like classes, races, origins just warn and set empty data
                logger.warning(f"Configuration file for domain '{domain}' not found at {file_path}. Skipping load.")
                self._config_data[domain] = {} # Ensure domain exists but is empty
            return # Stop processing if file doesn't exist (and wasn't created)

        try:
            loaded_data = load_json(file_path)
            if loaded_data is None: # Check if load_json returned None
                 logger.error(f"Failed to load or parse JSON for domain '{domain}' from {file_path}")
                 self._config_data[domain] = {} # Ensure domain exists but is empty
                 return

            # --- Specific Handling for files with top-level keys ---
            # Check if the domain is 'classes' and the loaded data has a top-level 'classes' key
            if domain == "classes" and isinstance(loaded_data, dict) and "classes" in loaded_data:
                self._config_data[domain] = loaded_data["classes"]
                logger.debug(f"Extracted 'classes' key content for domain '{domain}'.")
            # Check if the domain is 'races' and the loaded data has a top-level 'races' key
            elif domain == "races" and isinstance(loaded_data, dict) and "races" in loaded_data:
                self._config_data[domain] = loaded_data["races"]
                logger.debug(f"Extracted 'races' key content for domain '{domain}'.")
            # Check if the domain is 'origins' and the loaded data has a top-level 'origins' key
            elif domain == "origins" and isinstance(loaded_data, dict) and "origins" in loaded_data:
                 self._config_data[domain] = loaded_data["origins"]
                 logger.info(f"Extracted 'origins' key content for domain '{domain}'.")
                 # Add a check for the structure - expecting a dict of origins
                 if not isinstance(self._config_data[domain], dict):
                      logger.warning(f"Loaded 'origins' data for domain '{domain}' is not a dictionary. Check file structure.")
                      self._config_data[domain] = {} # Reset if structure is wrong
            # Check if the domain is 'quests' and the loaded data has a top-level 'quests' key
            elif domain == "quests" and isinstance(loaded_data, dict) and "quests" in loaded_data:
                 self._config_data[domain] = loaded_data["quests"]
                 logger.info(f"Extracted 'quests' key content for domain '{domain}'.")
                 if not isinstance(self._config_data[domain], dict):
                      logger.warning(f"Loaded 'quests' data for domain '{domain}' is not a dictionary. Check file structure.")
                      self._config_data[domain] = {}
            # Check if the domain is 'locations' and the loaded data has a top-level 'locations' key
            elif domain == "locations" and isinstance(loaded_data, dict) and "locations" in loaded_data:
                 self._config_data[domain] = loaded_data["locations"]
                 logger.debug(f"Extracted 'locations' key content for domain '{domain}'.")
                 if not isinstance(self._config_data[domain], dict):
                      logger.warning(f"Loaded 'locations' data for domain '{domain}' is not a dictionary. Check file structure.")
                      self._config_data[domain] = {}
            else:
                # Default behavior: store the entire loaded data
                self._config_data[domain] = loaded_data

            logger.info(f"Successfully loaded configuration for domain '{domain}'.")


        except Exception as e:
            logger.exception(f"Error loading configuration for domain '{domain}' from {file_path}: {e}")
            # Ensure domain exists even on error, maybe with empty data
            if domain not in self._config_data:
                self._config_data[domain] = {}

    def _create_default_config(self, domain: str, file_path: str):
        """
        Create a default configuration file for the specified domain.

        Args:
            domain: The configuration domain name.
            file_path: The absolute path where the file should be created.
        """
        # Define default configurations
        default_configs = {
            "game": {
                "version": "0.1.0",
                "title": "RPG Game",
                "default_save_slot": "auto",
                "auto_save_interval": 300,  # seconds
                "max_save_slots": 10,
            },
            "system": {
                "log_level": "INFO",
                "log_to_file": True,
                "log_to_console": True,
                "debug_mode": False,
                "save_dir": "saves", # Relative to project root
                "log_dir": "logs",   # Relative to project root
            },
            "gui": {
                "resolution": {
                    "width": 1280,
                    "height": 720,
                },
                "fullscreen": False,
                "theme": "default",
                "font_size": 12,
                "show_fps": False,
            },
            "llm": {
                 "default_provider_type": "GOOGLE", # Changed default
                 "default_temperature": 0.7,
                 "max_tokens": 1500, # Increased default
                 "timeout_seconds": 45, # Increased default
                 "retry_attempts": 2,
                 "retry_delay_seconds": 3,
                 "run_diagnostics_on_start": False,
                 "log_prompts": False, # Changed default
                 "log_completions": False, # Changed default
                 "cost_tracking_enabled": True,
                 "enabled": True # Explicitly add enabled flag
            }
            # No defaults needed for classes/races/origins here, as they should exist
        }

        default_config = default_configs.get(domain, {})
        if not default_config:
             logger.warning(f"No default configuration defined for domain '{domain}'")
             return # Don't create empty files for non-base domains

        self._config_data[domain] = default_config # Update in-memory config too

        try:
            # Create directory if it doesn't exist (handles nested paths)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Save default configuration
            save_json(default_config, file_path)
            logger.info(f"Created default configuration for {domain} at {file_path}")
        except Exception as e:
            logger.error(f"Error creating default configuration for {domain} at {file_path}: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key_path: The path to the configuration value (e.g., "gui.resolution.width", "origins.harmonia_initiate.description").
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default if not found.
        """
        # Split the key path into parts
        parts = key_path.split(".")

        # The first part is the domain (e.g., "gui", "origins")
        domain = parts[0]

        # If the domain doesn't exist in our loaded data, return the default
        if domain not in self._config_data:
            return default

        # Start with the domain's configuration data
        current = self._config_data[domain]

        # Traverse the configuration hierarchy using the remaining parts
        for part in parts[1:]:
            # Check if current level is a dictionary and the key exists
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    # Key not found at this level
                    return default
            # Check if current level is a list and the key is an integer index
            elif isinstance(current, list):
                 try:
                      index = int(part)
                      if 0 <= index < len(current):
                           current = current[index]
                      else:
                           # Index out of bounds
                           return default
                 except ValueError:
                      # Key is not a valid integer index for the list
                      return default
            else:
                 # Current level is not a dict or list, cannot traverse further
                 return default


        return current

    def set(self, key_path: str, value: Any) -> bool:
        """
        Set a configuration value using dot notation and save the corresponding file.

        Args:
            key_path: The path to the configuration value (e.g., "gui.resolution.width").
            value: The value to set.

        Returns:
            True if the value was set and saved successfully, False otherwise.
        """
        # Split the key path into parts
        parts = key_path.split(".")

        # The first part is the domain (e.g., "gui")
        domain = parts[0]

        # Check if the domain is known (has a default file mapping)
        if domain not in self._DEFAULT_CONFIG_FILES:
             logger.error(f"Cannot set configuration for unknown domain '{domain}'. Add it to _DEFAULT_CONFIG_FILES.")
             return False

        # If the domain doesn't exist in data, create it
        if domain not in self._config_data:
            logger.warning(f"Domain '{domain}' not found in configuration data, creating it.")
            self._config_data[domain] = {}

        # Start with the domain's configuration
        current = self._config_data[domain]

        # Traverse the configuration hierarchy, creating nodes as needed
        for part in parts[1:-1]:
            if part not in current or not isinstance(current[part], dict):
                 # If key doesn't exist or is not a dict, create/overwrite with a dict
                current[part] = {}
            current = current[part]

        # Set the final value
        final_key = parts[-1]
        # Ensure the final level is a dictionary before setting
        if not isinstance(current, dict):
             logger.error(f"Cannot set '{key_path}': Intermediate path does not lead to a dictionary.")
             return False

        current[final_key] = value
        logger.info(f"Set configuration '{key_path}' to: {value}")

        # --- Save the updated configuration file ---
        try:
            filename_rel = self._DEFAULT_CONFIG_FILES[domain]
            file_path = os.path.join(self._config_dir_abs, filename_rel)

            # Prepare data to save - handle potential top-level keys for specific domains
            data_to_save = self._config_data[domain]
            if domain == "classes":
                data_to_save = {"classes": self._config_data[domain]}
            elif domain == "races":
                 data_to_save = {"races": self._config_data[domain]}
            elif domain == "origins": # Added origins handler
                 data_to_save = {"origins": self._config_data[domain]}
            elif domain == "quests": # Added quests handler
                 data_to_save = {"quests": self._config_data[domain]}
            elif domain == "locations": # Added locations handler
                 data_to_save = {"locations": self._config_data[domain]}

            # Ensure the directory exists before saving
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            save_json(data_to_save, file_path)
            logger.info(f"Saved updated configuration for domain '{domain}' to {file_path}")
            return True
        except Exception as e:
            logger.exception(f"Error saving configuration for domain '{domain}' to {file_path}: {e}")
            return False

    def get_all(self, domain: str = None) -> Dict[str, Any]:
        """
        Get all configuration values for a domain, or all domains.

        Args:
            domain: The domain to get (e.g., "gui", "origins"). If None, return all domains.

        Returns:
            A dictionary of configuration values. Returns an empty dict if domain not found.
        """
        if domain is None:
            # Return a copy to prevent external modification
            return self._config_data.copy()

        if domain not in self._config_data:
            logger.warning(f"Domain '{domain}' not found in configuration")
            return {}

        # Return a copy
        return self._config_data[domain].copy()

    def reload(self, domain: str = None) -> bool:
        """
        Reload configuration from files.

        Args:
            domain: The domain to reload (e.g., "gui", "origins"). If None, reload all domains.

        Returns:
            True if the configuration was reloaded successfully, False otherwise.
        """
        logger.info(f"Reloading configuration for domain: {'ALL' if domain is None else domain}")
        try:
            if domain is None:
                self._load_all_configs()
                logger.info("Reloaded all configurations.")
                return True

            if domain not in self._DEFAULT_CONFIG_FILES:
                logger.warning(f"Cannot reload unknown domain '{domain}'.")
                return False

            filename_rel = self._DEFAULT_CONFIG_FILES[domain]
            self._load_config(domain, filename_rel)
            logger.info(f"Reloaded configuration for domain '{domain}'.")
            return True
        except Exception as e:
            logger.exception(f"Error reloading configuration: {e}")
            return False

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the configuration. (Basic validation for now)

        Returns:
            A tuple of (is_valid, error_messages).
        """
        is_valid = True
        errors = []

        # Updated required domains list
        required_domains = ["game", "system", "gui", "llm", "classes", "races", "origins"]
        for domain in required_domains:
            if domain not in self._config_data or not self._config_data[domain]:
                # Allow empty if the file genuinely didn't exist and wasn't required to have defaults
                filename_rel = self._DEFAULT_CONFIG_FILES.get(domain)
                if filename_rel:
                    file_path = os.path.join(self._config_dir_abs, filename_rel)
                    # Check if the file exists OR if it's a base config that should have defaults
                    if os.path.exists(file_path) or domain in ["game", "system", "gui", "llm"]:
                         is_valid = False
                         error = f"Configuration for domain '{domain}' is missing or empty."
                         errors.append(error)
                         logger.error(error)
                else: # Domain not even in default files - should not happen with current logic
                     is_valid = False
                     error = f"Configuration for domain '{domain}' is missing entirely."
                     errors.append(error)
                     logger.error(error)


        if is_valid:
            logger.info("Configuration validation passed.")
        else:
            logger.warning(f"Configuration validation failed: {errors}")

        return is_valid, errors


# Convenience functions

def get_config() -> GameConfig:
    """Get the game configuration singleton instance."""
    return GameConfig()


# Example usage
if __name__ == "__main__":
    # Set up basic logging for example run
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print("--- Initializing Config ---")
    config = get_config()
    print("\n--- Config Initialized ---")

    # Validate after load
    config.validate()

    # Get some values
    print("\n--- Getting Values ---")
    resolution_width = config.get("gui.resolution.width")
    print(f"GUI Resolution width: {resolution_width}")

    log_level = config.get("system.log_level", "DEBUG") # Example with default
    print(f"System Log Level: {log_level}")

    # Try getting a class description
    warrior_desc = config.get("classes.Warrior.description")
    if warrior_desc:
        print(f"Warrior Description: {warrior_desc}")
    else:
        print("Warrior class description not found (or classes.json missing/empty).")

    # Try getting an origin description
    harmonia_initiate_desc = config.get("origins.harmonia_initiate.description")
    if harmonia_initiate_desc:
         print(f"Harmonia Initiate Description: {harmonia_initiate_desc}")
    else:
         print("Harmonia Initiate origin not found (or origins.json missing/empty).")


    # Try getting a non-existent value
    non_existent = config.get("game.some_new_setting.value", "DefaultValue")
    print(f"Non-existent setting: {non_existent}")

    # Get all config for a domain
    print("\n--- Getting All GUI Config ---")
    gui_config = config.get_all("gui")
    print(json.dumps(gui_config, indent=2))

    print("\n--- Getting All Origins Config ---")
    origins_config = config.get_all("origins")
    if origins_config:
         print(f"Number of origins loaded: {len(origins_config)}")
         # print(json.dumps(origins_config, indent=2)) # Might be large
    else:
        print("No origins configuration loaded.")


    # Set a value (will save gui_config.json)
    print("\n--- Setting Value ---")
    success = config.set("gui.font_size", 14)
    print(f"Set gui.font_size success: {success}")
    print(f"New gui.font_size: {config.get('gui.font_size')}")

    # Reload config
    print("\n--- Reloading Config ---")
    config.reload("gui")
    print(f"Reloaded gui.font_size: {config.get('gui.font_size')}") # Should be 14 if save worked

    print("\n--- Example Finished ---")