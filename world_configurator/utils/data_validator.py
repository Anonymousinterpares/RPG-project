"""
Data validation utilities for the World Configurator Tool.
"""

import re
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional, Union, Tuple

try:
    import jsonschema
    from jsonschema.validators import validator_for
except Exception:  # jsonschema may be missing in some environments
    jsonschema = None
    validator_for = None

logger = logging.getLogger("world_configurator.data_validator")

class ValidationError:
    """
    Represents a validation error in configuration data.
    """
    def __init__(self, field: str, message: str, severity: str = "error"):
        """
        Initialize a ValidationError.
        
        Args:
            field: The field path that has the error.
            message: The error message.
            severity: The severity level ("error", "warning", or "info").
        """
        self.field = field
        self.message = message
        self.severity = severity
    
    def __str__(self) -> str:
        """String representation of the error."""
        return f"{self.severity.upper()} in {self.field}: {self.message}"

class DataValidator:
    """
    Validator for configuration data structures.
    """
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the DataValidator.
        
        Args:
            schema_path: Optional path to a JSON schema file.
        """
        self.schema = None
        if schema_path:
            self.load_schema(schema_path)
    
    def load_schema(self, schema_path: str) -> bool:
        """
        Load a JSON schema from a file.
        
        Args:
            schema_path: Path to the JSON schema file.
        
        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                self.schema = json.load(f)
            logger.debug(f"Loaded schema from {schema_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading schema from {schema_path}: {e}")
            self.schema = None
            return False
    
    def validate_cultures(self, data: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate cultures data.
        
        Args:
            data: The cultures data to validate.
        
        Returns:
            A list of validation errors, or an empty list if validation passed.
        """
        errors = []
        
        # Check for required top-level structure
        if not isinstance(data, dict):
            errors.append(ValidationError("root", "Must be a dictionary"))
            return errors
        
        if "cultures" not in data:
            errors.append(ValidationError("root", "Missing 'cultures' key"))
            return errors
        
        if not isinstance(data["cultures"], dict):
            errors.append(ValidationError("cultures", "Must be a dictionary"))
            return errors
        
        # Check each culture
        for culture_id, culture in data["cultures"].items():
            # Basic field checks
            if not isinstance(culture, dict):
                errors.append(ValidationError(f"cultures.{culture_id}", "Must be a dictionary"))
                continue
            
            # Check for required fields
            required_fields = ["name", "description", "values", "traditions"]
            for field in required_fields:
                if field not in culture:
                    errors.append(ValidationError(
                        f"cultures.{culture_id}", f"Missing required field: {field}"
                    ))
            
            # Check values
            if "values" in culture and isinstance(culture["values"], list):
                if len(culture["values"]) == 0:
                    errors.append(ValidationError(
                        f"cultures.{culture_id}.values", "Should have at least one value"
                    ))
            
            # Check traditions
            if "traditions" in culture and isinstance(culture["traditions"], list):
                if len(culture["traditions"]) == 0:
                    errors.append(ValidationError(
                        f"cultures.{culture_id}.traditions", "Should have at least one tradition"
                    ))
        
        return errors
    
    def validate_locations(self, data: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate locations data.
        
        Args:
            data: The locations data to validate.
        
        Returns:
            A list of validation errors, or an empty list if validation passed.
        """
        errors = []
        
        # Check for required top-level structure
        if not isinstance(data, dict):
            errors.append(ValidationError("root", "Must be a dictionary"))
            return errors
        
        if "locations" not in data:
            errors.append(ValidationError("root", "Missing 'locations' key"))
            return errors
        
        if not isinstance(data["locations"], dict):
            errors.append(ValidationError("locations", "Must be a dictionary"))
            return errors
        
        # Check each location
        for location_id, location in data["locations"].items():
            # Basic field checks
            if not isinstance(location, dict):
                errors.append(ValidationError(f"locations.{location_id}", "Must be a dictionary"))
                continue
            
            # Check for required fields
            required_fields = ["name", "description", "type"]
            for field in required_fields:
                if field not in location:
                    errors.append(ValidationError(
                        f"locations.{location_id}", f"Missing required field: {field}"
                    ))
            
            # Check connections
            if "connections" in location:
                if not isinstance(location["connections"], list):
                    errors.append(ValidationError(
                        f"locations.{location_id}.connections", "Must be a list"
                    ))
                else:
                    for i, conn in enumerate(location["connections"]):
                        if not isinstance(conn, dict):
                            errors.append(ValidationError(
                                f"locations.{location_id}.connections[{i}]", "Must be a dictionary"
                            ))
                            continue
                        
                        # Check for required connection fields
                        if "target" not in conn:
                            errors.append(ValidationError(
                                f"locations.{location_id}.connections[{i}]", 
                                "Missing required field: target"
                            ))
        
        return errors
    
    def validate_world_history(self, data: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate world history data.
        
        Args:
            data: The world history data to validate.
        
        Returns:
            A list of validation errors, or an empty list if validation passed.
        """
        errors = []
        
        # Check for required top-level structure
        if not isinstance(data, dict):
            errors.append(ValidationError("root", "Must be a dictionary"))
            return errors
        
        required_fields = ["name", "description", "eras"]
        for field in required_fields:
            if field not in data:
                errors.append(ValidationError("root", f"Missing required field: {field}"))
        
        # Check eras
        if "eras" in data:
            if not isinstance(data["eras"], list):
                errors.append(ValidationError("eras", "Must be a list"))
            else:
                if len(data["eras"]) == 0:
                    errors.append(ValidationError(
                        "eras", "Should have at least one era", "warning"
                    ))
                
                for i, era in enumerate(data["eras"]):
                    if not isinstance(era, dict):
                        errors.append(ValidationError(f"eras[{i}]", "Must be a dictionary"))
                        continue
                    
                    # Check for required era fields
                    era_required = ["name", "start_year", "end_year", "description", "events"]
                    for field in era_required:
                        if field not in era:
                            errors.append(ValidationError(
                                f"eras[{i}]", f"Missing required field: {field}"
                            ))
                    
                    # Check events
                    if "events" in era:
                        if not isinstance(era["events"], list):
                            errors.append(ValidationError(f"eras[{i}].events", "Must be a list"))
                        else:
                            for j, event in enumerate(era["events"]):
                                if not isinstance(event, dict):
                                    errors.append(ValidationError(
                                        f"eras[{i}].events[{j}]", "Must be a dictionary"
                                    ))
                                    continue
                                
                                # Check for required event fields
                                event_required = ["year", "title", "description"]
                                for field in event_required:
                                    if field not in event:
                                        errors.append(ValidationError(
                                            f"eras[{i}].events[{j}]", 
                                            f"Missing required field: {field}"
                                        ))
        
        return errors

    def validate_effect_atoms_magic_systems(self, magic_systems: Dict[str, Any], project_root: Optional[str] = None) -> List[ValidationError]:
        """
        Validate all effect_atoms across all magic systems and spells against the JSON schema.
        Also checks damage_type values against canonical list.

        Args:
            magic_systems: Dict of id -> MagicalSystem (or dict-like) objects.
            project_root: Optional override for the project root to resolve schema path.

        Returns:
            A list of ValidationError entries; empty list means validation passed.
        """
        errors: List[ValidationError] = []
        # Ensure jsonschema is available
        if jsonschema is None or validator_for is None:
            py = sys.executable or "python"
            msg = (
                "jsonschema is not available in the Python runtime used by the editor.\n"
                f"Interpreter: {py}\n"
                f"Install into this environment: \"{py}\" -m pip install jsonschema\n"
                "Then restart the editor and retry export."
            )
            errors.append(ValidationError("effect_atoms", msg))
            return errors

        try:
            root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # world_configurator/utils -> project root is one level up from repo root? Use known structure
            # Prefer walking up to repo root by finding 'config' directory
            repo_root = root
            # Heuristic: if 'config' not directly under root, go one level up
            if not os.path.exists(os.path.join(repo_root, 'config')):
                repo_root = os.path.dirname(repo_root)
            schema_path = os.path.join(repo_root, 'config', 'gameplay', 'effect_atoms.schema.json')
            canonical_path = os.path.join(repo_root, 'config', 'gameplay', 'canonical_lists.json')
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            canonical_damage_types: List[str] = []
            try:
                with open(canonical_path, 'r', encoding='utf-8') as cf:
                    canon = json.load(cf)
                    if isinstance(canon, dict) and isinstance(canon.get('damage_types'), list):
                        canonical_damage_types = [str(x).strip() for x in canon['damage_types'] if isinstance(x, str)]
            except Exception:
                # Not fatal; we'll skip canonical type enforcement if missing
                canonical_damage_types = []

            validator_cls = validator_for(schema)
            # Ensure schema is valid for this validator
            try:
                validator_cls.check_schema(schema)
            except Exception:
                pass
            validator = validator_cls(schema)

            def _pretty_path(p: List[Union[str, int]]) -> str:
                out = []
                for part in p:
                    if isinstance(part, int):
                        out.append(f"[{part}]")
                    else:
                        out.append(str(part))
                return ".".join(out)

            # Iterate systems and spells
            for sys_id, system in (magic_systems or {}).items():
                try:
                    sys_name = getattr(system, 'name', None) or (system.get('name') if isinstance(system, dict) else sys_id)
                    spells = getattr(system, 'spells', None) or (system.get('spells') if isinstance(system, dict) else {})
                except Exception:
                    sys_name = sys_id
                    spells = {}
                if hasattr(spells, 'items'):
                    it = spells.items()
                elif isinstance(spells, list):
                    it = [(str(i), s) for i, s in enumerate(spells)]
                else:
                    it = []

                for spell_key, spell in it:
                    try:
                        spell_name = getattr(spell, 'name', None) or (spell.get('name') if isinstance(spell, dict) else str(spell_key))
                        atoms = getattr(spell, 'effect_atoms', None) or (spell.get('effect_atoms') if isinstance(spell, dict) else None)
                    except Exception:
                        spell_name = str(spell_key)
                        atoms = None

                    if not atoms:
                        continue

                    # Validate the sequence against schema
                    try:
                        validator.validate(atoms)
                    except jsonschema.ValidationError as ve:
                        # Provide a human-friendly error with suggestions
                        loc = _pretty_path(list(ve.path))
                        msg = ve.message
                        suggestion = None
                        # Common suggestions
                        if 'is a required property' in msg:
                            if 'damage_type' in msg:
                                suggestion = "For 'damage' atoms, set Damage type (e.g., slashing, fire)."
                            elif 'magnitude' in msg:
                                suggestion = "Add Amount: set a flat value, dice (e.g., 2d6+3), or stat-based magnitude."
                            elif 'status' in msg:
                                suggestion = "For 'status apply', set Status name (e.g., Burning)."
                            elif 'duration' in msg:
                                suggestion = "Set Duration (unit and value). Default is 1 turn for statuses/shields."
                            elif 'resource' in msg:
                                suggestion = "For 'resource change', choose Resource (HEALTH/MANA/STAMINA/RESOLVE)."
                        elif 'does not match' in msg and 'dice' in loc:
                            suggestion = "Use dice format NdS±M, e.g., 2d6+3."
                        elif 'is not one of' in msg and 'stacking_rule' in loc:
                            suggestion = "Choose stacking: none, stack, refresh, or replace."
                        err_text = f"Magic Systems › {sys_name} › {spell_name} › {loc or 'effect_atoms'}: {msg}"
                        if suggestion:
                            err_text += f"\n  Suggestion: {suggestion}"
                        errors.append(ValidationError("magic_systems.effect_atoms", err_text))
                        # Continue collecting errors; do not abort on first

                    # Additional canonical checks per atom
                    for idx, atom in enumerate(atoms):
                        try:
                            if not isinstance(atom, dict):
                                continue
                            a_type = str(atom.get('type', '')).strip()
                            if a_type == 'damage':
                                dt = str(atom.get('damage_type', '')).strip()
                                if not dt:
                                    errors.append(ValidationError(
                                        "magic_systems.effect_atoms",
                                        f"Magic Systems › {sys_name} › {spell_name} › atoms[{idx}]: Damage type is required for damage atoms.\n  Suggestion: Choose one of the canonical types."
                                    ))
                                elif canonical_damage_types and dt not in canonical_damage_types:
                                    errors.append(ValidationError(
                                        "magic_systems.effect_atoms",
                                        f"Magic Systems › {sys_name} › {spell_name} › atoms[{idx}]: Unknown damage type '{dt}'.\n  Suggestion: Use one of: {', '.join(canonical_damage_types)}."
                                    ))
                            if a_type == 'status_apply':
                                # If periodic tags present, ensure magnitude exists and duration present
                                tags = [t for t in (atom.get('tags') or []) if isinstance(t, str)]
                                if any(t in ("damage_over_time", "healing_over_time", "regeneration") for t in tags):
                                    if 'magnitude' not in atom:
                                        errors.append(ValidationError(
                                            "magic_systems.effect_atoms",
                                            f"Magic Systems › {sys_name} › {spell_name} › atoms[{idx}]: Periodic status missing Amount per turn.\n  Suggestion: Set Amount per turn (magnitude)."
                                        ))
                                if 'duration' not in atom:
                                    errors.append(ValidationError(
                                        "magic_systems.effect_atoms",
                                        f"Magic Systems › {sys_name} › {spell_name} › atoms[{idx}]: Status apply is missing Duration.\n  Suggestion: Set Duration (e.g., 1 turn)."
                                    ))
                            if a_type == 'shield':
                                if 'magnitude' not in atom:
                                    errors.append(ValidationError(
                                        "magic_systems.effect_atoms",
                                        f"Magic Systems › {sys_name} › {spell_name} › atoms[{idx}]: Shield is missing Amount.\n  Suggestion: Set shield Amount (magnitude)."
                                    ))
                        except Exception:
                            # Skip malformed entries gracefully
                            continue
        except Exception as e:
            errors.append(ValidationError("magic_systems.effect_atoms", f"Validator error: {e}"))

        return errors
    
    def validate_scenario(self, data: Dict[str, Any]) -> List[ValidationError]:
        """
        Validate a scenario definition.
        
        Args:
            data: The scenario data to validate.
        
        Returns:
            A list of validation errors, or an empty list if validation passed.
        """
        errors = []
        
        # Check for required top-level structure
        if not isinstance(data, dict):
            errors.append(ValidationError("root", "Must be a dictionary"))
            return errors
        
        required_fields = ["id", "name", "description", "starting_location", "quests"]
        for field in required_fields:
            if field not in data:
                errors.append(ValidationError("root", f"Missing required field: {field}"))
        
        # Check quests
        if "quests" in data:
            if not isinstance(data["quests"], list):
                errors.append(ValidationError("quests", "Must be a list"))
            else:
                for i, quest in enumerate(data["quests"]):
                    if not isinstance(quest, dict):
                        errors.append(ValidationError(f"quests[{i}]", "Must be a dictionary"))
                        continue
                    
                    # Check for required quest fields
                    quest_required = ["id", "title", "description", "objectives"]
                    for field in quest_required:
                        if field not in quest:
                            errors.append(ValidationError(
                                f"quests[{i}]", f"Missing required field: {field}"
                            ))
                    
                    # Check objectives
                    if "objectives" in quest:
                        if not isinstance(quest["objectives"], list):
                            errors.append(ValidationError(
                                f"quests[{i}].objectives", "Must be a list"
                            ))
                        else:
                            for j, objective in enumerate(quest["objectives"]):
                                if not isinstance(objective, dict):
                                    errors.append(ValidationError(
                                        f"quests[{i}].objectives[{j}]", "Must be a dictionary"
                                    ))
                                    continue
                                
                                # Check for required objective fields
                                obj_required = ["id", "description", "type"]
                                for field in obj_required:
                                    if field not in objective:
                                        errors.append(ValidationError(
                                            f"quests[{i}].objectives[{j}]", 
                                            f"Missing required field: {field}"
                                        ))
        
        return errors
    
    def get_validator_for_type(self, data_type: str):
        """
        Get the appropriate validator function for a data type.
        
        Args:
            data_type: The type of data to validate.
        
        Returns:
            A validation function for the specified data type.
        """
        validators = {
            "cultures": self.validate_cultures,
            "locations": self.validate_locations,
            "world_history": self.validate_world_history,
            "scenario": self.validate_scenario,
        }
        
        return validators.get(data_type, lambda x: [])
