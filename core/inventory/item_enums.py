#!/usr/bin/env python3
"""
Enums for the inventory system.

This module defines the enumerations used throughout the item system,
including item types, rarities, and equipment slots.
"""

from enum import Enum, auto


class ItemType(str, Enum):
    """Types of items in the game."""
    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    QUEST = "quest"
    MATERIAL = "material"
    CONTAINER = "container"
    KEY = "key"
    DOCUMENT = "document"
    TOOL = "tool"
    TREASURE = "treasure"
    MISCELLANEOUS = "miscellaneous"
    
    def __str__(self) -> str:
        """Return a display-friendly string representation."""
        return self.value.capitalize()


class ItemRarity(str, Enum):
    """Rarity levels for items."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    ARTIFACT = "artifact"
    UNIQUE = "unique"
    
    def __str__(self) -> str:
        """Return a display-friendly string representation."""
        return self.value.capitalize()
    
    @property
    def color(self) -> str:
        """Get a color code for this rarity (for UI display)."""
        colors = {
            "common": "#c0c0c0",      # Silver
            "uncommon": "#00ff00",    # Green
            "rare": "#0070dd",        # Blue
            "epic": "#a335ee",        # Purple
            "legendary": "#ff8000",   # Orange
            "artifact": "#e6cc80",    # Gold
            "unique": "#ff0000"       # Red
        }
        return colors.get(self.value, "#ffffff")


class EquipmentSlot(str, Enum):
    """Equipment slots for wearable items."""
    HEAD = "head"
    NECK = "neck"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    CHEST = "chest"
    BACK = "back"
    WRISTS = "wrists"
    HANDS = "hands"
    WAIST = "waist"
    LEGS = "legs"
    FEET = "feet"
    FINGER_1 = "finger_1"
    FINGER_2 = "finger_2"
    FINGER_3 = "finger_3"
    FINGER_4 = "finger_4"
    FINGER_5 = "finger_5"
    FINGER_6 = "finger_6"
    FINGER_7 = "finger_7"
    FINGER_8 = "finger_8"
    FINGER_9 = "finger_9"
    FINGER_10 = "finger_10"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    TWO_HAND = "two_hand"
    RANGED = "ranged"
    AMMUNITION = "ammunition"
    TRINKET_1 = "trinket_1"
    TRINKET_2 = "trinket_2"
    
    def __str__(self) -> str:
        """Return a display-friendly string representation."""
        return self.value.replace('_', ' ').title()
    
    @property
    def is_finger(self) -> bool:
        """Check if this is a finger slot."""
        return self.value.startswith("finger_")
    
    @property
    def is_hand(self) -> bool:
        """Check if this is a hand slot."""
        return self.value in ["main_hand", "off_hand", "two_hand"]
