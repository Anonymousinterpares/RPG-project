# world_configurator/models/skill_manager.py
"""
Manager for skill data (skills.json).
"""

import os
import shutil
import datetime
from typing import Dict, Optional, Any

from models.base_models import WorldModelState
from utils.file_manager import load_json, save_json, get_project_root, get_config_dir
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.models.skill_manager")

class SkillManager:
    """
    Manager for skill data from skills.json.
    """
    def __init__(self):
        # The skills_data will store the direct content of the "skills" key in skills.json
        # e.g., {"melee_attack": {"name": "Melee Attack", ...}, ...}
        self.skills_data: Dict[str, Dict[str, Any]] = {}
        self.state = WorldModelState()
        self.file_path: Optional[str] = None
        self._ensure_default_file_path()

    def _ensure_default_file_path(self):
        """Ensures a default file path is set if not already loaded."""
        if not self.file_path:
            # Default path construction, assuming skills.json is in 'config/'
            project_r = get_project_root()
            self.file_path = os.path.join(project_r, "config", "skills.json")
            self.state.path = self.file_path # Also update state path

    def load_from_file(self, file_path: Optional[str] = None) -> bool:
        """
        Load skills from skills.json.

        Args:
            file_path: Path to the JSON file. If None, uses the default path.

        Returns:
            True if loading was successful, False otherwise.
        """
        load_path = file_path or self.file_path
        if not load_path:
            self._ensure_default_file_path()
            load_path = self.file_path
            if not load_path: # Still no path
                logger.error("SkillManager: No file path specified or determined for loading skills.")
                return False
        
        self.file_path = load_path # Update internal path

        try:
            data = load_json(load_path)
            if data and "skills" in data and isinstance(data["skills"], dict):
                self.skills_data = data["skills"]
                self.state.path = load_path
                self.state.modified = False
                logger.info(f"Loaded {len(self.skills_data)} skills from {load_path}")
                return True
            else:
                logger.warning(f"Invalid skills file format or 'skills' key missing in {load_path}. Initializing empty.")
                self.skills_data = {}
                # If the file exists but is invalid, we might want to mark as modified or handle differently
                if os.path.exists(load_path):
                     self.state.modified = True # Mark modified if we had to reset due to bad format
                return False # Indicate that loading wasn't fully successful if format was bad
        except Exception as e:
            logger.error(f"Error loading skills from {load_path}: {e}", exc_info=True)
            self.skills_data = {} # Reset on error
            return False

    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """
        Save skills to skills.json.

        Args:
            file_path: Path to the JSON file. If None, uses the path from state or default.

        Returns:
            True if saving was successful, False otherwise.
        """
        save_path = file_path or self.state.path or self.file_path
        if not save_path:
            self._ensure_default_file_path()
            save_path = self.file_path
            if not save_path: # Still no path
                logger.error("SkillManager: No file path specified or determined for saving skills.")
                return False

        data_to_save = {"skills": self.skills_data}
        try:
            if save_json(data_to_save, save_path):
                self.state.path = save_path
                self.file_path = save_path
                self.state.modified = False
                logger.info(f"Saved {len(self.skills_data)} skills to {save_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error saving skills to {save_path}: {e}", exc_info=True)
            return False

    def get_all_skills(self) -> Dict[str, Dict[str, Any]]:
        """Returns all loaded skill data."""
        return self.skills_data

    def update_skills(self, new_skills_data: Dict[str, Dict[str, Any]]):
        """
        Completely replaces the current skills data.
        Used by editor when it saves changes.
        """
        self.skills_data = new_skills_data
        self.state.mark_modified()
        logger.info(f"SkillManager data updated with {len(new_skills_data)} skills.")


    def export_to_game(self) -> bool:
        """
        Export skills to the game's configuration directory (config/skills.json).
        """
        try:
            target_dir = get_config_dir() # config/
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "skills.json")

            backup_dir = os.path.join(target_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)

            if os.path.exists(target_path):
                filename = os.path.basename(target_path)
                name, ext = os.path.splitext(filename)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{name}_skills_{timestamp}{ext}" # More specific backup name
                backup_path = os.path.join(backup_dir, backup_filename)
                try:
                    shutil.copy2(target_path, backup_path)
                    logger.info(f"Created backup of skills.json at {backup_path}")
                except Exception as backup_err:
                    logger.error(f"Failed to create skills.json backup: {backup_err}")

            return self.save_to_file(target_path)
        except Exception as e:
            logger.error(f"Error exporting skills to game: {e}", exc_info=True)
            return False