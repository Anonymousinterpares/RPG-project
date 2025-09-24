"""
World configuration manager for the World Configurator Tool.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple

from models.base_models import WorldModelState
from models.world_data import CultureManager, WorldHistoryManager, WorldRulesManager, RaceManager, ClassManager, MagicSystemManager
from models.names_manager import NamesManager
from models.location_data import LocationManager
from models.location_defaults_manager import LocationDefaultsManager
from models.origin_data import OriginManager, QuestManager
from utils.file_manager import get_config_dir, get_project_root, get_world_config_dir, load_json, save_json

logger = logging.getLogger("world_configurator.models.world_config")

# Define expected filenames for each component relative to the main 'config' directory
COMPONENT_FILES = {
    "cultures": ("world/base", "cultures.json"),
    "races": ("character", "races.json"),
    "classes": ("character", "classes.json"),
    "locations": ("world/locations", "locations.json"), # Corrected path
    "history": ("world/base", "world_history.json"),
    "rules": ("world/base", "fundamental_rules.json"),
    "origins": ("world/scenarios", "origins.json"),
    "quests": ("world/scenarios", "quests.json"),
    "magic_systems": ("world/base", "magic_systems.json")
}

class WorldConfigManager:
    """Manages loading, saving, and accessing all world configuration components."""
    def __init__(self):
        self.state = WorldModelState()
        self.project_name: str = "Untitled Project"

        # Initialize managers
        self.culture_manager = CultureManager()
        self.race_manager = RaceManager()
        self.class_manager = ClassManager()
        self.location_manager = LocationManager()
        self.history_manager = WorldHistoryManager()
        self.rules_manager = WorldRulesManager()
        self.origin_manager = OriginManager()
        self.quest_manager = QuestManager()
        self.magic_system_manager = MagicSystemManager()
        
        # NEW Managers
        from .skill_manager import SkillManager # Local import
        self.skill_manager = SkillManager()
        
        # Names manager (npc/names.json)
        self.names_manager = NamesManager()
        
        # Location defaults (world/locations/defaults.json)
        self.location_defaults_manager = LocationDefaultsManager()

        from .item_data_manager import ItemDataManager, MANAGED_ITEM_FILES as ITEM_FILE_KEYS_MAP # Local import
        self.item_data_manager = ItemDataManager()
        self.ITEM_FILE_KEYS_MAP = ITEM_FILE_KEYS_MAP # Store for convenience

        # Map component names to managers for easier iteration
        self.managers = {
            "cultures": self.culture_manager,
            "races": self.race_manager,
            "classes": self.class_manager,
            "skills": self.skill_manager, # NEW
            # Individual item categories will be handled by ItemDataManager
            "locations": self.location_manager,
            "history": self.history_manager,
            "rules": self.rules_manager,
            "origins": self.origin_manager,
            "quests": self.quest_manager,
            "magic_systems": self.magic_system_manager,
            "names": self.names_manager,
            "location_defaults": self.location_defaults_manager
        }
        # Add item file keys to managers for load/save/export logic continuity if needed,
        # or handle item_data_manager specially. For now, ItemDataManager handles its own files.

    def new_project(self, name: str):
        """Start a new, empty project."""
        self.project_name = name
        self.state = WorldModelState() # Reset state
        for manager in self.managers.values():
            manager.__init__() # Reinitialize each manager
        logger.info(f"Started new project: {name}")
    
    def load_project(self, project_dir: str) -> bool:
        """
        Load a project from a specified directory.
        Assumes each component is saved as a separate JSON file within the directory.
        """
        if not os.path.isdir(project_dir):
            logger.error(f"Project directory not found: {project_dir}")
            return False

        self.project_name = os.path.basename(project_dir)
        all_loaded = True
        loaded_components = []

        # Define expected filenames for each component relative to the project_dir
        # Note: item files are handled separately by ItemDataManager
        project_component_files = {
            "cultures": "cultures.json",
            "races": "races.json",
            "classes": "classes.json",
            "skills": "skills.json", # Assuming skills.json is at the root of project_dir
            "locations": "locations.json",
            "history": "world_history.json",
            "rules": "fundamental_rules.json",
            "origins": "origins.json",
            "quests": "quests.json",
            "magic_systems": "magic_systems.json",
            "names": "names.json",
            "location_defaults": "location_defaults.json"
        }

        for component, filename in project_component_files.items():
            file_path = os.path.join(project_dir, filename) # Files expected at root of project_dir
            manager = self.managers.get(component)
            if manager:
                if os.path.exists(file_path):
                    if manager.load_from_file(file_path):
                        loaded_components.append(component)
                    else:
                        logger.warning(f"Failed to load component '{component}' from {file_path}")
                else:
                    logger.debug(f"Component file not found in project, skipping: {file_path}")
                    manager.__init__() # Reset manager
            else:
                 logger.warning(f"No manager found for component '{component}'")
        
        # Load all item files via ItemDataManager, relative to project_dir
        # ItemDataManager's load_all_managed_files needs to accept project_dir
        # and construct full paths like project_dir/config/items/file.json
        # This implies the project structure should mirror the game's config structure
        # e.g. MyProject/config/items/origin_items.json
        self.item_data_manager.load_all_managed_files(project_dir=project_dir)
        # We can assume items are "loaded" if the manager tried, success is per-file.
        loaded_components.append("items (all categories)")


        self.state.path = project_dir
        self.state.modified = False 
        logger.info(f"Project '{self.project_name}' loaded from {project_dir}. Components loaded: {', '.join(loaded_components)}")
        return True
    
    def save_project(self, project_dir: Optional[str] = None) -> bool:
        """
        Save the current project to a directory.
        If project_dir is None, saves to the current project path.
        """
        target_dir = project_dir or self.state.path
        if not target_dir:
            logger.error("Cannot save project: No directory specified or loaded.")
            return False

        os.makedirs(target_dir, exist_ok=True)
        all_saved = True

        # Define expected filenames for each component relative to the target_dir
        project_component_files = {
            "cultures": "cultures.json",
            "races": "races.json",
            "classes": "classes.json",
            "skills": "skills.json",
            "locations": "locations.json",
            "history": "world_history.json",
            "rules": "fundamental_rules.json",
            "origins": "origins.json",
            "quests": "quests.json",
            "magic_systems": "magic_systems.json",
            "names": "names.json",
            "location_defaults": "location_defaults.json"
        }

        for component, filename in project_component_files.items():
            manager = self.managers.get(component)
            if manager:
                file_path = os.path.join(target_dir, filename)
                if not manager.save_to_file(file_path):
                    logger.error(f"Failed to save component '{component}' to {file_path}")
                    all_saved = False
            else:
                logger.warning(f"No manager found for component '{component}', cannot save.")
        
        # Save all item files via ItemDataManager
        # It needs to save to project_dir/config/items/filename.json
        if not self.item_data_manager.save_all_managed_files(project_dir=target_dir):
            logger.error(f"Failed to save one or more item files for project '{self.project_name}'")
            all_saved = False


        if all_saved:
            self.state.path = target_dir 
            self.state.modified = False 
            logger.info(f"Project '{self.project_name}' saved to {target_dir}")
        else:
            logger.error(f"Project '{self.project_name}' saved to {target_dir} with errors.")

        return all_saved
    
    def export_to_game(self, export_options: Dict[str, bool]) -> Tuple[bool, List[str]]:
        """
        Export selected components to the game's config directory.

        Args:
            export_options: A dictionary where keys are component names
                            and values are booleans indicating if they should be exported.
                            Item categories will have keys like "items_origin", "items_weapons", etc.
        Returns:
            A tuple (bool, List[str]) indicating overall success and a list of errors.
        """
        all_success = True
        errors = []
        exported_count = 0

        # Standard components
        for component_key, should_export in export_options.items():
            if not should_export:
                continue

            # Handle item categories separately
            if component_key.startswith("items_"):
                item_file_key_to_export = component_key # e.g., "items_origin"
                if self.item_data_manager:
                    logger.debug(f"Attempting to export item category: {item_file_key_to_export}")
                    if self.item_data_manager.export_item_file_to_game(item_file_key_to_export):
                        logger.info(f"Successfully exported {item_file_key_to_export}")
                        exported_count +=1
                    else:
                        all_success = False
                        error_msg = f"Failed to export item category {item_file_key_to_export}."
                        errors.append(error_msg)
                        logger.error(error_msg)
                else:
                    error_msg = f"ItemDataManager not found, cannot export {item_file_key_to_export}."
                    errors.append(error_msg)
                    logger.warning(error_msg)
                continue # Move to next export option

            # Handle other standard managers
            manager = self.managers.get(component_key)
            if manager:
                logger.debug(f"Attempting to export component: {component_key}")
                if hasattr(manager, 'export_to_game') and callable(manager.export_to_game):
                    if manager.export_to_game():
                        logger.info(f"Successfully exported {component_key}")
                        exported_count += 1
                    else:
                        all_success = False
                        error_msg = f"Failed to export {component_key}."
                        errors.append(error_msg)
                        logger.error(error_msg)
                else:
                     logger.warning(f"Manager for '{component_key}' does not have a callable export_to_game method.")
            # If component_key is not for items and not in self.managers, it's an unknown option.
            # This case should ideally not happen if ExportDialog keys are consistent.
            elif not component_key.startswith("items_"):
                 error_msg = f"No manager found for component '{component_key}', cannot export."
                 errors.append(error_msg)
                 logger.warning(error_msg)


        if exported_count > 0 and all_success:
            logger.info(f"Successfully exported {exported_count} components/item files.")
        elif exported_count > 0:
            logger.warning(f"Export completed with errors. Successfully exported {exported_count} components/item files.")
        elif not errors: # No items selected for export
            logger.info("No components selected for export.")
            # This is not an error, so return True
        else: # No export count but errors exist (e.g. trying to export non-existent component)
             logger.error("Export failed. No components were exported successfully.")


        return all_success, errors
    
    def synchronize_with_game(self) -> bool:
        """Load all components directly from the game's config directory."""
        # game_config_dir is the root `config` directory of the game project.
        game_config_dir = get_config_dir()
        self.project_name = "Game Configuration" # Default name for this mode
        all_loaded = True
        loaded_components = []

        # This map defines how component keys map to subdirectories and filenames
        # *within the game's `config` directory*.
        game_files_structure = {
            "cultures": ("world/base", "cultures.json"),
            "races": ("character", "races.json"),
            "classes": ("character", "classes.json"),
            "skills": ("", "skills.json"), # skills.json is directly in config/
            "locations": ("world/locations", "locations.json"),
            "history": ("world/base", "world_history.json"),
            "rules": ("world/base", "fundamental_rules.json"),
            "origins": ("world/scenarios", "origins.json"),
            "quests": ("world/scenarios", "quests.json"),
            "magic_systems": ("world/base", "magic_systems.json"),
            "names": ("npc", "names.json"),
            "location_defaults": ("world/locations", "defaults.json")
            # Item files are handled by ItemDataManager below
        }

        for component, (subdir, filename) in game_files_structure.items():
            # Construct full path: game_config_dir / subdir / filename
            file_path = os.path.join(game_config_dir, subdir, filename) if subdir else os.path.join(game_config_dir, filename)
            
            manager = self.managers.get(component)
            if manager:
                if os.path.exists(file_path):
                    if manager.load_from_file(file_path):
                        loaded_components.append(component)
                    else:
                        logger.warning(f"Failed to sync component '{component}' from {file_path}")
                        all_loaded = False
                else:
                    logger.warning(f"Game config file not found for component '{component}', resetting: {file_path}")
                    manager.__init__() # Reset manager
            else:
                 logger.warning(f"No manager found for component '{component}' during sync.")

        # Synchronize all item files using ItemDataManager
        # ItemDataManager.load_all_managed_files() internally knows the "config/items/..." paths
        # relative to project root. For sync, project root IS the game's root.
        self.item_data_manager.load_all_managed_files(project_dir=get_project_root())
        # Assuming item data manager tries to load all its files, mark as "attempted"
        loaded_components.append("items (all categories)")


        self.state.path = None 
        self.state.modified = False 
        logger.info(f"Synchronized with game config. Components loaded/attempted: {', '.join(loaded_components)}")
        return all_loaded
    
    def is_modified(self) -> bool:
        """
        Check if any part of the world configuration has been modified.
        
        Returns:
            True if any manager has modified data, False otherwise.
        """
        if self.state.modified: return True # Project level modification (e.g. save as)

        for manager_name, manager_instance in self.managers.items():
            if hasattr(manager_instance, 'state') and manager_instance.state.modified:
                logger.debug(f"Modification detected in manager: {manager_name}")
                return True
        
        if hasattr(self, 'item_data_manager') and self.item_data_manager.is_any_file_modified():
            logger.debug("Modification detected in ItemDataManager.")
            return True
            
        return False