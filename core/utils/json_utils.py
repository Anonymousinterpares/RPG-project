#!/usr/bin/env python3
"""
JSON utilities for the RPG game.

This module provides enhanced JSON encoding/decoding capabilities
for handling complex data types used throughout the application.
"""

import json
import uuid
import dataclasses
import datetime
import enum
from typing import Any, Dict, List, Set, Tuple, Union, Optional
import logging

# Get the module logger
logger = logging.getLogger(__name__)

class EnhancedJSONEncoder(json.JSONEncoder):
    """Enhanced JSON encoder to handle various Python types."""
    
    def default(self, obj: Any) -> Any:
        """Convert Python objects to JSON serializable types."""
        # Handle dataclasses
        if dataclasses.is_dataclass(obj):
            return {
                "_type": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                "_data": {f.name: getattr(obj, f.name) for f in dataclasses.fields(obj)}
            }
        
        # Handle enums
        if isinstance(obj, enum.Enum):
            return {
                "_type": "enum",
                "_class": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                "_name": obj.name,
                "_value": obj.value
            }
        
        # Handle datetime objects
        if isinstance(obj, datetime.datetime):
            return {
                "_type": "datetime",
                "_value": obj.isoformat()
            }
        
        # Handle date objects
        if isinstance(obj, datetime.date):
            return {
                "_type": "date",
                "_value": obj.isoformat()
            }
        
        # Handle time objects
        if isinstance(obj, datetime.time):
            return {
                "_type": "time",
                "_value": obj.isoformat()
            }
        
        # Handle UUID objects
        if isinstance(obj, uuid.UUID):
            return {
                "_type": "uuid",
                "_value": str(obj)
            }
        
        # Handle sets
        if isinstance(obj, set):
            return {
                "_type": "set",
                "_value": list(obj)
            }
        
        # Handle any object with a to_dict method
        if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
            result = obj.to_dict()
            result["_type"] = f"{obj.__class__.__module__}.{obj.__class__.__name__}"
            return result
        
        # Let the parent class handle the rest
        try:
            return super().default(obj)
        except TypeError as e:
            logger.warning(f"Could not JSON serialize {type(obj)}: {e}")
            return str(obj)  # Fallback to string representation


class EnhancedJSONDecoder(json.JSONDecoder):
    """Enhanced JSON decoder to reconstruct Python objects from JSON."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the decoder with custom object hook."""
        kwargs["object_hook"] = self._object_hook
        super().__init__(*args, **kwargs)
    
    def _object_hook(self, obj: Dict[str, Any]) -> Any:
        """Convert JSON objects back to Python objects."""
        # Check if this is a specially encoded object
        if "_type" not in obj:
            return obj
        
        obj_type = obj["_type"]
        
        # Handle enums
        if obj_type == "enum":
            try:
                module_name, class_name = obj["_class"].rsplit(".", 1)
                module = __import__(module_name, fromlist=[class_name])
                enum_class = getattr(module, class_name)
                return enum_class[obj["_name"]]
            except (ImportError, AttributeError, KeyError) as e:
                logger.warning(f"Could not decode enum: {e}")
                return obj
        
        # Handle datetime objects
        if obj_type == "datetime":
            return datetime.datetime.fromisoformat(obj["_value"])
        
        # Handle date objects
        if obj_type == "date":
            return datetime.date.fromisoformat(obj["_value"])
        
        # Handle time objects
        if obj_type == "time":
            return datetime.time.fromisoformat(obj["_value"])
        
        # Handle UUID objects
        if obj_type == "uuid":
            return uuid.UUID(obj["_value"])
        
        # Handle sets
        if obj_type == "set":
            return set(obj["_value"])
        
        # Handle dataclasses and other custom objects
        try:
            module_name, class_name = obj_type.rsplit(".", 1)
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            
            # If it's a dataclass
            if dataclasses.is_dataclass(cls):
                return cls(**obj["_data"])
            
            # If it has a from_dict method
            if hasattr(cls, "from_dict") and callable(getattr(cls, "from_dict")):
                # Remove the _type field first
                obj_copy = obj.copy()
                obj_copy.pop("_type")
                return cls.from_dict(obj_copy)
        except (ImportError, AttributeError, ValueError) as e:
            logger.warning(f"Could not decode custom object: {e}")
        
        # Return the original object if we couldn't decode it
        return obj


# Utility functions

def to_json(obj: Any, pretty: bool = False) -> str:
    """Convert an object to a JSON string."""
    indent = 4 if pretty else None
    try:
        return json.dumps(obj, cls=EnhancedJSONEncoder, indent=indent)
    except Exception as e:
        logger.error(f"Error serializing to JSON: {e}")
        raise


def from_json(json_str: str) -> Any:
    """Convert a JSON string back to Python objects."""
    try:
        return json.loads(json_str, cls=EnhancedJSONDecoder)
    except Exception as e:
        logger.error(f"Error deserializing from JSON: {e}")
        raise


def save_json(obj: Any, file_path: str, pretty: bool = True) -> None:
    """Save an object to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, cls=EnhancedJSONEncoder, indent=4 if pretty else None)
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        raise


def load_json(file_path: str) -> Any:
    """Load an object from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f, cls=EnhancedJSONDecoder)
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        raise


# Add alias functions for compatibility with save_manager.py
def enhanced_json_dumps(obj: Any, indent: Optional[int] = None) -> str:
    """Alias for to_json for compatibility with save_manager."""
    return to_json(obj, pretty=indent is not None)


def enhanced_json_loads(json_str: str) -> Any:
    """Alias for from_json for compatibility with save_manager."""
    return from_json(json_str)


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Example dataclass
    @dataclasses.dataclass
    class Person:
        name: str
        age: int
        created_at: datetime.datetime = dataclasses.field(
            default_factory=lambda: datetime.datetime.now()
        )
        id: uuid.UUID = dataclasses.field(
            default_factory=uuid.uuid4
        )
        tags: Set[str] = dataclasses.field(default_factory=set)
    
    # Example enum
    class Color(enum.Enum):
        RED = 1
        GREEN = 2
        BLUE = 3
    
    # Create test objects
    person = Person(name="Alice", age=30)
    person.tags.add("player")
    person.tags.add("admin")
    
    favorite_color = Color.BLUE
    
    # Test serialization
    data = {
        "person": person,
        "favorite_color": favorite_color,
        "current_time": datetime.datetime.now(),
        "settings": {
            "debug": True,
            "volume": 0.8
        }
    }
    
    # Serialize to JSON
    json_str = to_json(data, pretty=True)
    print("Serialized JSON:")
    print(json_str)
    
    # Deserialize from JSON
    restored_data = from_json(json_str)
    print("\nDeserialized data:")
    print(f"Person name: {restored_data['person'].name}")
    print(f"Person age: {restored_data['person'].age}")
    print(f"Person created at: {restored_data['person'].created_at}")
    print(f"Person ID: {restored_data['person'].id}")
    print(f"Person tags: {restored_data['person'].tags}")
    print(f"Favorite color: {restored_data['favorite_color']}")
    print(f"Current time: {restored_data['current_time']}")
    print(f"Settings: {restored_data['settings']}")