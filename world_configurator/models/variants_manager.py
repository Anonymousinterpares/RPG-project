"""
VariantsManager for handling config/npc/variants.json within the World Configurator.
"""
import os
import json
import logging
import shutil
import datetime
from typing import Optional, Dict, Any, List

from models.base_models import WorldModelState
from utils.file_manager import get_config_dir, save_json, load_json

logger = logging.getLogger("world_configurator.models.variants_manager")

class VariantsManager:
    """Manager for NPC variants configuration (config/npc/variants.json)."""

    def __init__(self):
        # Stored structure: { "variants": {"variant_id": {...}}, "metadata": {...} }
        self.data: Dict[str, Any] = {"variants": {}, "metadata": {"version": "1.0.0"}}
        self.state = WorldModelState()

    def load_from_file(self, file_path: str) -> bool:
        """Load variants.json from a file path."""
        try:
            raw = load_json(file_path)
            if not isinstance(raw, dict):
                logger.error(f"Invalid variants file format (not an object): {file_path}")
                self.data = {"variants": {}, "metadata": {"version": "1.0.0"}}
                return False
            if "variants" not in raw or not isinstance(raw["variants"], dict):
                logger.warning("variants.json missing 'variants' object; initializing empty.")
                raw["variants"] = {}
            self.data = raw
            self.state.path = file_path
            self.state.modified = False
            logger.info(
                f"Loaded variants from {file_path} (variants: {len(self.data['variants'])})"
            )
            return True
        except Exception as e:
            logger.error(f"Error loading variants.json from {file_path}: {e}")
            self.data = {"variants": {}, "metadata": {"version": "1.0.0"}}
            return False

    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """Save variants.json to the given file path or to the current state path."""
        try:
            path = file_path or self.state.path
            if not path:
                logger.error("No file path specified for saving variants.json")
                return False
            # Normalize structure
            data_to_save = dict(self.data) if isinstance(self.data, dict) else {"variants": {}, "metadata": {"version": "1.0.0"}}
            if "variants" not in data_to_save or not isinstance(data_to_save["variants"], dict):
                data_to_save["variants"] = {}
            ok = save_json(data_to_save, path)
            if ok:
                self.state.path = path
                self.state.modified = False
                logger.info(
                    f"Saved variants to {path} (variants: {len(data_to_save['variants'])})"
                )
            return ok
        except Exception as e:
            logger.error(f"Error saving variants.json: {e}")
            return False

    def export_to_game(self) -> bool:
        """Export the current variants data to the game's config/npc/variants.json with backups."""
        try:
            if not isinstance(self.data, dict):
                logger.error("No variants data to export.")
                return False
            target_dir = os.path.join(get_config_dir(), "npc")
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "variants.json")

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
                    logger.error(f"Failed to create backup for variants.json: {backup_err}")
            return self.save_to_file(target_path)
        except Exception as e:
            logger.error(f"Error exporting variants.json to game: {e}")
            return False

    def get_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get a variant by ID."""
        return self.data.get("variants", {}).get(variant_id)

    def add_variant(self, variant_id: str, variant_data: Dict[str, Any]) -> None:
        """Add or update a variant."""
        if "variants" not in self.data:
            self.data["variants"] = {}
        self.data["variants"][variant_id] = variant_data
        self.state.modified = True
        logger.debug(f"Added/updated variant: {variant_id}")

    def remove_variant(self, variant_id: str) -> bool:
        """Remove a variant by ID."""
        if "variants" in self.data and variant_id in self.data["variants"]:
            del self.data["variants"][variant_id]
            self.state.modified = True
            logger.debug(f"Removed variant: {variant_id}")
            return True
        return False

    def get_variants_by_family(self, family_id: str) -> List[Dict[str, Any]]:
        """Get all variants that belong to a specific family."""
        variants = []
        for variant_id, variant_data in self.data.get("variants", {}).items():
            if variant_data.get("family_id") == family_id:
                variant_copy = dict(variant_data)
                variant_copy["id"] = variant_id  # Ensure ID is included
                variants.append(variant_copy)
        return variants

    def get_social_role_variants(self, role: str) -> List[Dict[str, Any]]:
        """Get all variants that have a specific social role tag."""
        role_tag = f"role:{role}"
        variants = []
        for variant_id, variant_data in self.data.get("variants", {}).items():
            tags_add = variant_data.get("tags_add", [])
            if role_tag in tags_add:
                variant_copy = dict(variant_data)
                variant_copy["id"] = variant_id
                variants.append(variant_copy)
        return variants

    def get_culture_variants(self, culture: str) -> List[Dict[str, Any]]:
        """Get all variants that belong to a specific culture family."""
        variants = []
        culture_pattern = f"{culture}_"  # e.g., "concordant_", "verdant_"
        for variant_id, variant_data in self.data.get("variants", {}).items():
            if variant_id.startswith(culture_pattern):
                variant_copy = dict(variant_data)
                variant_copy["id"] = variant_id
                variants.append(variant_copy)
        return variants

    def validate_variant(self, variant_data: Dict[str, Any]) -> List[str]:
        """Validate a variant data structure and return list of errors."""
        errors = []
        
        # Required fields
        required_fields = ["id", "family_id", "name", "description"]
        for field in required_fields:
            if field not in variant_data or not variant_data[field]:
                errors.append(f"Missing required field: {field}")

        # Validate stat_modifiers structure
        if "stat_modifiers" in variant_data:
            stat_mods = variant_data["stat_modifiers"]
            if not isinstance(stat_mods, dict):
                errors.append("stat_modifiers must be a dictionary")
            else:
                valid_stats = ["hp", "damage", "defense", "initiative"]
                for stat, mod in stat_mods.items():
                    if stat not in valid_stats:
                        errors.append(f"Unknown stat in stat_modifiers: {stat}")
                    if not isinstance(mod, dict):
                        errors.append(f"stat_modifiers.{stat} must be a dictionary")
                    else:
                        for op in mod:
                            if op not in ["add", "mul"]:
                                errors.append(f"Unknown operation in stat_modifiers.{stat}: {op}")

        # Validate list fields
        list_fields = ["roles_add", "abilities_add", "tags_add"]
        for field in list_fields:
            if field in variant_data and not isinstance(variant_data[field], list):
                errors.append(f"{field} must be a list")

        return errors

    def create_social_role_variant(self, 
                                 culture: str, 
                                 role: str, 
                                 family_id: str, 
                                 name: str, 
                                 description: str,
                                 stat_modifiers: Optional[Dict[str, Dict[str, float]]] = None,
                                 abilities: Optional[List[str]] = None,
                                 roles: Optional[List[str]] = None) -> str:
        """
        Create a new social role variant with appropriate defaults.
        
        Returns:
            The generated variant ID
        """
        variant_id = f"{culture}_{role}"
        
        # Default stat modifiers by role
        default_stat_mods = {
            "guard": {"hp": {"add": 5}, "defense": {"add": 2}},
            "official": {"hp": {"add": 3}},
            "scholar": {"defense": {"add": 1}, "damage": {"add": 1}}
        }
        
        # Default abilities by role
        default_abilities = {
            "guard": ["resonant_shield"],
            "official": ["rally_shout"],
            "scholar": ["chorus_of_clarity"]
        }
        
        # Default combat roles by social role
        default_roles = {
            "guard": ["tank", "controller"],
            "official": ["support"],
            "scholar": ["controller", "support"]
        }
        
        variant_data = {
            "id": variant_id,
            "family_id": family_id,
            "name": name,
            "description": description,
            "stat_modifiers": stat_modifiers or default_stat_mods.get(role, {}),
            "roles_add": roles or default_roles.get(role, []),
            "abilities_add": abilities or default_abilities.get(role, []),
            "tags_add": [f"role:{role}"]
        }
        
        # Add duty tag for guards
        if role == "guard":
            variant_data["tags_add"].append("duty:watch")
        
        self.add_variant(variant_id, variant_data)
        return variant_id
