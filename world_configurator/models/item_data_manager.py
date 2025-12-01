# world_configurator/models/item_data_manager.py
"""
Manager for all item data files (origin_items.json, base_weapons.json, etc.).
"""

import os
import shutil
import datetime
from typing import Dict, List, Optional, Any

from models.base_models import WorldModelState
from utils.file_manager import load_json, save_json, get_project_root, get_config_dir
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.models.item_data_manager")

# This mapping should ideally match ItemEditorPanel.ITEM_CATEGORIES keys to file paths
# It defines which item files this manager is responsible for.
# Paths are relative to the project root.
MANAGED_ITEM_FILES = {
    "items_origin": "config/items/origin_items.json",
    "items_weapons": "config/items/base_weapons.json",
    "items_armor": "config/items/base_armor.json",
    "items_consumables": "config/items/consumables.json",
    "items_misc": "config/items/miscellaneous.json"
    # Add more if new item categories are introduced
}

class ItemDataManager:
    """
    Manages loading, saving, and exporting for all item-related JSON files.
    """
    def __init__(self):
        # Stores data for each managed item file, e.g., {"items_origin": [list of items], ...}
        self.all_item_data: Dict[str, List[Dict[str, Any]]] = {}
        # Tracks modification state per file key
        self.file_states: Dict[str, WorldModelState] = {}
        self.project_root_path = get_project_root()

        for key, _ in MANAGED_ITEM_FILES.items():
            self.file_states[key] = WorldModelState()
            self.all_item_data[key] = []


    def load_item_file(self, file_key: str) -> bool:
        """
        Load a specific item file based on its key.

        Args:
            file_key: The key identifying the item file (e.g., "items_origin").

        Returns:
            True if loading was successful, False otherwise.
        """
        relative_path = MANAGED_ITEM_FILES.get(file_key)
        if not relative_path:
            logger.error(f"ItemDataManager: Unknown item file key '{file_key}'. Cannot load.")
            return False

        full_path = os.path.join(self.project_root_path, relative_path)
        
        try:
            data = load_json(full_path)
            if isinstance(data, list): # Item files are expected to be lists of items
                self.all_item_data[file_key] = data
                self.file_states[file_key].path = full_path
                self.file_states[file_key].modified = False
                logger.info(f"Loaded {len(data)} items for '{file_key}' from {full_path}")
                return True
            else:
                logger.warning(f"Invalid item file format for '{file_key}' (expected list) in {full_path}. Initializing empty.")
                self.all_item_data[file_key] = []
                if os.path.exists(full_path):
                    self.file_states[file_key].modified = True
                return False
        except Exception as e:
            logger.error(f"Error loading item file '{file_key}' from {full_path}: {e}", exc_info=True)
            self.all_item_data[file_key] = []
            return False

    def save_item_file(self, file_key: str, project_dir_override: Optional[str] = None) -> bool:
        """
        Save a specific item file.

        Args:
            file_key: The key identifying the item file.
            project_dir_override: If provided, save relative to this directory instead of original.

        Returns:
            True if saving was successful, False otherwise.
        """
        relative_path = MANAGED_ITEM_FILES.get(file_key)
        if not relative_path:
            logger.error(f"ItemDataManager: Unknown item file key '{file_key}'. Cannot save.")
            return False

        data_to_save = self.all_item_data.get(file_key, [])
        
        save_path: str
        if project_dir_override:
            # Construct path relative to the project_dir_override
            # MANAGED_ITEM_FILES paths are like "config/items/origin_items.json"
            # We need to join project_dir_override with the parts after "config/"
            # This assumes project_dir_override is the "config" directory itself or its parent.
            # For WorldConfigManager.save_project, target_dir is the *project's* root,
            # so we need to create "config/items" subdirectories within it.
            path_parts = relative_path.split(os.sep) # e.g. ['config', 'items', 'origin_items.json']
            # We need to ensure the 'items' subdirectory exists within 'project_dir_override/config/'
            save_dir = os.path.join(project_dir_override, *path_parts[:-1]) # e.g. project_dir/config/items
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, path_parts[-1])

        else: # Saving to original loaded path or default
            save_path = self.file_states[file_key].path or os.path.join(self.project_root_path, relative_path)


        try:
            if save_json(data_to_save, save_path):
                self.file_states[file_key].path = save_path # Update path if it changed
                self.file_states[file_key].modified = False
                logger.info(f"Saved {len(data_to_save)} items for '{file_key}' to {save_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error saving item file '{file_key}' to {save_path}: {e}", exc_info=True)
            return False

    def get_item_data_for_key(self, file_key: str) -> Optional[List[Dict[str, Any]]]:
        """Returns the item data list for a given file key."""
        return self.all_item_data.get(file_key)

    def update_item_data_for_key(self, file_key: str, new_data: List[Dict[str, Any]]):
        """Updates the item data for a given file key."""
        if file_key in self.all_item_data:
            self.all_item_data[file_key] = new_data
            self.file_states[file_key].mark_modified()
            logger.info(f"Item data for '{file_key}' updated in manager.")
        else:
            logger.warning(f"ItemDataManager: Attempted to update data for unknown file key '{file_key}'.")

    def load_all_managed_files(self, project_dir: Optional[str] = None):
        """Loads all item files defined in MANAGED_ITEM_FILES."""
        logger.info("ItemDataManager: Loading all managed item files.")
        for file_key in MANAGED_ITEM_FILES.keys():
            file_path_to_load = None
            if project_dir: # Loading from a specific project directory
                relative_path = MANAGED_ITEM_FILES[file_key]
                file_path_to_load = os.path.join(project_dir, relative_path)
                if not os.path.exists(file_path_to_load):
                    logger.debug(f"Item file {file_path_to_load} not found in project. Will use default if available or create new.")
                    # Reset specific file state if not found in project, it will try default path or create new
                    self.all_item_data[file_key] = []
                    self.file_states[file_key] = WorldModelState() # Reset state
                    # Try default load for this file
                    self.load_item_file(file_key) # This will use default path if project one DNE
                    continue # Move to next file key
            
            # If no project_dir or file not in project_dir, load_item_file handles default path logic.
            if not self.load_item_file(file_key) and not project_dir: # Only log error if not project specific and default fails
                 logger.warning(f"Failed to load default item file for '{file_key}'.")


    def save_all_managed_files(self, project_dir: Optional[str] = None) -> bool:
        """Saves all modified item files."""
        all_successful = True
        for file_key in MANAGED_ITEM_FILES.keys():
            # Save if modified OR if a project_dir_override is given (forcing save to new location)
            if self.file_states[file_key].modified or project_dir:
                if not self.save_item_file(file_key, project_dir_override=project_dir):
                    all_successful = False
        return all_successful

    def export_item_file_to_game(self, file_key: str) -> bool:
        """Exports a specific item file to the game's config directory."""
        relative_path_from_config_root = MANAGED_ITEM_FILES.get(file_key)
        if not relative_path_from_config_root:
            logger.error(f"Cannot export unknown item file key: {file_key}")
            return False
        
        # MANAGED_ITEM_FILES paths are like "config/items/origin_items.json"
        # We need path relative to "config" dir for export target construction.
        # e.g., "items/origin_items.json"
        if not relative_path_from_config_root.startswith("config/"):
            logger.error(f"Invalid path format for item file key '{file_key}': {relative_path_from_config_root}")
            return False
        
        path_in_config_dir = os.path.relpath(relative_path_from_config_root, "config")

        game_config_dir = get_config_dir() # This is .../RPG-Text-Game/config
        target_path = os.path.join(game_config_dir, path_in_config_dir)
        
        # Ensure target subdirectory (e.g., 'items') exists
        target_subdir = os.path.dirname(target_path)
        os.makedirs(target_subdir, exist_ok=True)

        # Backup existing game file
        backup_dir = os.path.join(target_subdir, "backup")
        os.makedirs(backup_dir, exist_ok=True)
        if os.path.exists(target_path):
            filename = os.path.basename(target_path)
            name, ext = os.path.splitext(filename)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{name}_{file_key}_{timestamp}{ext}" # More specific backup
            backup_file_path = os.path.join(backup_dir, backup_filename)
            try:
                shutil.copy2(target_path, backup_file_path)
                logger.info(f"Created backup of game's {filename} at {backup_file_path}")
            except Exception as e_backup:
                logger.error(f"Failed to backup game's {filename}: {e_backup}")
        
        # Load freshest data from source file on disk to avoid stale in-memory state
        source_full_path = os.path.join(get_project_root(), MANAGED_ITEM_FILES[file_key])
        latest = load_json(source_full_path)
        data_to_export = latest if isinstance(latest, list) else self.all_item_data.get(file_key, [])
        if save_json(data_to_export, target_path):
            logger.info(f"Successfully exported '{file_key}' to {target_path}")
            return True
        else:
            logger.error(f"Failed to export '{file_key}' to {target_path}")
            return False

    def is_any_file_modified(self) -> bool:
        """Checks if any managed item file has been modified."""
        return any(state.modified for state in self.file_states.values())