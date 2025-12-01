"""
LocationDefaultsManager for handling config/world/locations/defaults.json within the World Configurator.
"""
import os

import shutil
import datetime
from typing import Optional, Dict, Any

from models.base_models import WorldModelState
from utils.file_manager import get_world_config_dir, save_json, load_json
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.models.location_defaults_manager")

class LocationDefaultsManager:
    """Manager for world/locations/defaults.json which includes global culture_mix defaults."""

    def __init__(self):
        # Stored structure: { "culture_mix": {"culture_id": weight, ...}, "metadata": {...} }
        self.data: Dict[str, Any] = {"culture_mix": {}, "metadata": {"version": "1.0.0"}}
        self.state = WorldModelState()

    def load_from_file(self, file_path: str) -> bool:
        """Load defaults.json from a file path."""
        try:
            raw = load_json(file_path)
            if not isinstance(raw, dict):
                logger.error(f"Invalid defaults file format (not an object): {file_path}")
                self.data = {"culture_mix": {}, "metadata": {"version": "1.0.0"}}
                return False
            if "culture_mix" not in raw or not isinstance(raw["culture_mix"], dict):
                logger.warning("defaults.json missing 'culture_mix' object; initializing empty.")
                raw["culture_mix"] = {}
            self.data = raw
            self.state.path = file_path
            self.state.modified = False
            logger.info(
                f"Loaded culture mix defaults from {file_path} (entries: {len(self.data['culture_mix'])})"
            )
            return True
        except Exception as e:
            logger.error(f"Error loading defaults.json from {file_path}: {e}")
            self.data = {"culture_mix": {}, "metadata": {"version": "1.0.0"}}
            return False

    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """Save defaults.json to the given file path or to the current state path."""
        try:
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving defaults.json")
                return False
            # Normalize structure
            data_to_save = dict(self.data) if isinstance(self.data, dict) else {"culture_mix": {}, "metadata": {"version": "1.0.0"}}
            if "culture_mix" not in data_to_save or not isinstance(data_to_save["culture_mix"], dict):
                data_to_save["culture_mix"] = {}
            ok = save_json(data_to_save, path)
            if ok:
                self.state.path = path
                self.state.modified = False
                logger.info(
                    f"Saved culture mix defaults to {path} (entries: {len(data_to_save['culture_mix'])})"
                )
            return ok
        except Exception as e:
            logger.error(f"Error saving defaults.json: {e}")
            return False

    def export_to_game(self) -> bool:
        """Export the current defaults data to the game's config/world/locations/defaults.json with backups."""
        try:
            if not isinstance(self.data, dict):
                logger.error("No defaults data to export.")
                return False
            target_dir = os.path.join(get_world_config_dir(), "locations")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "defaults.json")

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
                    logger.error(f"Failed to create backup for defaults.json: {backup_err}")
            return self.save_to_file(target_path)
        except Exception as e:
            logger.error(f"Error exporting defaults.json to game: {e}")
            return False
