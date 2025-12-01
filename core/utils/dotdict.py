#!/usr/bin/env python3
"""
DotDict utility for the RPG game.

This module provides a dictionary subclass that allows accessing keys
using dot notation (e.g., d.key instead of d['key']).
"""

from typing import Any, Dict
from core.utils.logging_config import get_logger

# Get the module logger
logger = get_logger("SYSTEM")

class DotDict(dict):
    """
    Dictionary that supports dot notation access to keys.
    
    This class extends the built-in dict to allow accessing keys
    using dot notation (e.g., d.key instead of d['key']). It also
    automatically converts nested dictionaries to DotDict objects.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize a DotDict.
        
        Args:
            *args: Arguments to pass to dict.__init__.
            **kwargs: Keyword arguments to pass to dict.__init__.
        """
        super().__init__(*args, **kwargs)
        # Convert nested dictionaries to DotDict objects
        self.__convert_nested_dicts()
    
    def __convert_nested_dicts(self):
        """Convert nested dictionaries to DotDict objects."""
        for key, value in self.items():
            if isinstance(value, dict) and not isinstance(value, DotDict):
                self[key] = DotDict(value)
            elif isinstance(value, list):
                self[key] = [
                    DotDict(item) if isinstance(item, dict) and not isinstance(item, DotDict) else item
                    for item in value
                ]
    
    def __getattr__(self, key: str) -> Any:
        """
        Get an attribute (key) from the dictionary.
        
        This method is called when an attribute is accessed that doesn't
        exist in the instance's __dict__. It looks up the key in the
        dictionary instead.
        
        Args:
            key: The attribute (key) to get.
        
        Returns:
            The value associated with the key.
        
        Raises:
            AttributeError: If the key is not in the dictionary.
        """
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'DotDict' object has no attribute '{key}'")
    
    def __setattr__(self, key: str, value: Any) -> None:
        """
        Set an attribute (key) in the dictionary.
        
        Args:
            key: The attribute (key) to set.
            value: The value to set.
        """
        self[key] = value
        
        # Convert to DotDict if it's a dict
        if isinstance(value, dict) and not isinstance(value, DotDict):
            self[key] = DotDict(value)
    
    def __delattr__(self, key: str) -> None:
        """
        Delete an attribute (key) from the dictionary.
        
        Args:
            key: The attribute (key) to delete.
        
        Raises:
            AttributeError: If the key is not in the dictionary.
        """
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'DotDict' object has no attribute '{key}'")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the dictionary with a default.
        
        Similar to dict.get, but supports dot notation for nested keys.
        
        Args:
            key: The key to get. Can be a dot-separated path (e.g., 'a.b.c').
            default: The default value to return if the key is not found.
        
        Returns:
            The value associated with the key, or the default if not found.
        """
        if "." not in key:
            return super().get(key, default)
        
        # Handle nested keys
        parts = key.split(".")
        current = self
        
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], (dict, DotDict)):
                return default
            current = current[part]
        
        return current.get(parts[-1], default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the dictionary.
        
        Supports dot notation for nested keys, creating intermediate
        dictionaries as needed.
        
        Args:
            key: The key to set. Can be a dot-separated path (e.g., 'a.b.c').
            value: The value to set.
        """
        if "." not in key:
            self[key] = value
            if isinstance(value, dict) and not isinstance(value, DotDict):
                self[key] = DotDict(value)
            return
        
        # Handle nested keys
        parts = key.split(".")
        current = self
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = DotDict()
            elif not isinstance(current[part], (dict, DotDict)):
                current[part] = DotDict()
            current = current[part]
        
        current[parts[-1]] = value
        if isinstance(value, dict) and not isinstance(value, DotDict):
            current[parts[-1]] = DotDict(value)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the DotDict to a regular dictionary.
        
        This method recursively converts all nested DotDict objects to
        regular dictionaries.
        
        Returns:
            A regular dictionary.
        """
        result = {}
        
        for key, value in self.items():
            if isinstance(value, DotDict):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [
                    item.to_dict() if isinstance(item, DotDict) else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'DotDict':
        """
        Create a DotDict from a regular dictionary.
        
        Args:
            d: The dictionary to convert.
        
        Returns:
            A DotDict with the same keys and values.
        """
        return cls(d)


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logger.basicConfig(level=logger.INFO)
    
    # Create a DotDict
    config = DotDict({
        "game": {
            "title": "RPG Game",
            "version": "0.1.0",
            "settings": {
                "difficulty": "normal",
                "sound": {
                    "volume": 0.8,
                    "music": True,
                    "effects": True
                }
            }
        },
        "player": {
            "name": "Test Player",
            "stats": {
                "health": 100,
                "mana": 50
            },
            "inventory": [
                {"name": "Sword", "damage": 10},
                {"name": "Potion", "healing": 25}
            ]
        }
    })
    
    # Access values using dot notation
    print(f"Game title: {config.game.title}")
    print(f"Game version: {config.game.version}")
    print(f"Sound volume: {config.game.settings.sound.volume}")
    print(f"Player name: {config.player.name}")
    print(f"Player health: {config.player.stats.health}")
    
    # Access nested list items (these remain list items, not DotDicts)
    print(f"First inventory item: {config.player.inventory[0].name}")
    
    # Set values using dot notation
    config.player.stats.health = 90
    print(f"Updated player health: {config.player.stats.health}")
    
    # Add new keys
    config.game.settings.graphics = DotDict({"quality": "high", "fullscreen": True})
    print(f"Graphics quality: {config.game.settings.graphics.quality}")
    
    # Use get with dot notation for nested keys
    fps = config.get("game.settings.graphics.fps", 60)
    print(f"FPS: {fps}")
    
    # Use set with dot notation for nested keys
    config.set("game.settings.graphics.fps", 120)
    print(f"Updated FPS: {config.game.settings.graphics.fps}")
    
    # Convert back to dict
    regular_dict = config.to_dict()
    print(f"Regular dict: {type(regular_dict)}")
    
    # Create from dict
    new_config = DotDict.from_dict({"test": {"value": 42}})
    print(f"New config test value: {new_config.test.value}")