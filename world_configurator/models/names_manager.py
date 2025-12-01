"""
NamesManager for handling config/npc/names.json within the World Configurator.
"""
import os
import shutil
import datetime
from typing import Optional, Dict, Any

from models.base_models import WorldModelState
from utils.file_manager import get_config_dir, save_json, load_json
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.models.names_manager")

class NamesManager:
    """Manager for culture-aware names configuration (config/npc/names.json)."""

    def __init__(self):
        self.data: Dict[str, Any] = {"cultures": {}}
        self.state = WorldModelState()

    def load_from_file(self, file_path: str) -> bool:
        """Load names.json from a file path."""
        try:
            raw = load_json(file_path)
            if not isinstance(raw, dict):
                logger.error(f"Invalid names file format (not an object): {file_path}")
                self.data = {"cultures": {}}
                return False
            if "cultures" not in raw or not isinstance(raw["cultures"], dict):
                logger.warning("names.json missing 'cultures' object; initializing empty.")
                raw["cultures"] = {}
            self.data = raw
            self.state.path = file_path
            self.state.modified = False
            logger.info(f"Loaded names from {file_path} (cultures: {len(self.data['cultures'])})")
            return True
        except Exception as e:
            logger.error(f"Error loading names from {file_path}: {e}")
            self.data = {"cultures": {}}
            return False

    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """Save names.json to the given file path or to the current state path."""
        try:
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving names.json")
                return False
            # Normalize structure
            data_to_save = dict(self.data) if isinstance(self.data, dict) else {"cultures": {}}
            if "cultures" not in data_to_save or not isinstance(data_to_save["cultures"], dict):
                data_to_save["cultures"] = {}
            ok = save_json(data_to_save, path)
            if ok:
                self.state.path = path
                self.state.modified = False
                logger.info(f"Saved names to {path} (cultures: {len(data_to_save['cultures'])})")
            return ok
        except Exception as e:
            logger.error(f"Error saving names.json: {e}")
            return False

    def export_to_game(self) -> bool:
        """Export the current names data to the game's config/npc/names.json with backups."""
        try:
            # Ensure we have data to save
            if not isinstance(self.data, dict):
                logger.error("No names data to export.")
                return False
            target_dir = os.path.join(get_config_dir(), "npc")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "names.json")

            # Backup if target exists
            backup_dir = os.path.join(target_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            if os.path.exists(target_path):
                name, ext = os.path.splitext(os.path.basename(target_path))
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(backup_dir, f"{name}_{timestamp}{ext}")
                try:
                    shutil.copy2(target_path, backup_path)
                    logger.info(f"Created backup of {target_path} at {backup_path}")
                except Exception as backup_err:
                    logger.error(f"Failed to create backup for names.json: {backup_err}")
            return self.save_to_file(target_path)
        except Exception as e:
            logger.error(f"Error exporting names to game: {e}")
            return False

