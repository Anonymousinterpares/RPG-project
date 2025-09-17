"""
Data validation utilities for the World Configurator Tool.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple

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
