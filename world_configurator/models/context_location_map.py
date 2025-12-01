"""
Context Location Map manager for world_configurator.
Manages config/audio/context_location_map.json with by_id/by_name mapping.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
import os

from utils.file_manager import load_json, save_json, get_config_dir
from models.base_models import WorldModelState
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.models.context_location_map")


class ContextLocationMapManager:
    def __init__(self) -> None:
        self.data: Dict[str, Any] = {"by_id": {}, "by_name": {}}
        self.state = WorldModelState()  # reuse for path/modified flags

    # Basic accessors
    def get_entry(self, location_id: Optional[str] = None, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if location_id and isinstance(self.data.get("by_id"), dict):
            e = self.data["by_id"].get(location_id)
            if e:
                return dict(e)
        if name and isinstance(self.data.get("by_name"), dict):
            e = self.data["by_name"].get(name)
            if e:
                return dict(e)
        return None

    def set_entry(self, location_id: str, name: str, payload: Dict[str, Any]) -> None:
        """Set or update mapping for an id (and ensure by_name mirror)."""
        self.data.setdefault("by_id", {})[location_id] = dict(payload)
        if name:
            self.data.setdefault("by_name", {})[name] = dict(payload)
        self.state.modified = True

    def rebuild_by_name(self, id_to_name: Dict[str, str]) -> None:
        by_name: Dict[str, Any] = {}
        for _id, entry in (self.data.get("by_id") or {}).items():
            nm = id_to_name.get(_id)
            if nm:
                by_name[nm] = dict(entry)
        self.data["by_name"] = by_name
        self.state.modified = True

    # IO
    def load_from_file(self, file_path: str) -> bool:
        try:
            data = load_json(file_path) or {}
            if not isinstance(data, dict):
                data = {"by_id": {}, "by_name": {}}
            self.data = data
            self.state.path = file_path
            self.state.modified = False
            logger.info(f"Loaded context_location_map from {file_path}: ids={len((self.data.get('by_id') or {}))}")
            return True
        except Exception as e:
            logger.error(f"Error loading context_location_map: {e}")
            return False

    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        path = file_path or self.state.path
        if not path:
            # Default to game's config dir
            path = os.path.join(get_config_dir(), "audio", "context_location_map.json")
        ok = save_json(self.data, path)
        if ok:
            self.state.path = path
            self.state.modified = False
            logger.info(f"Saved context_location_map to {path}")
        else:
            logger.error(f"Failed to save context_location_map to {path}")
        return ok
