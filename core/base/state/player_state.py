"""
Player state for the RPG game.

This module provides the PlayerState class for managing player information.
"""

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from core.utils.logging_config import get_logger
from core.interaction.social_effects import StatusEffectData # Import StatusEffectData

# Get the module logger
logger = get_logger("PLAYER")

@dataclass
class PlayerState:
    """
    Player state information.

    This dataclass contains all persistent information about the player,
    including basic attributes, location, and derived stats.
    """
    # Basic player information
    name: str
    race: str = "Human"  # Default race
    path: str = "Wanderer"  # Default path/class
    background: str = "Commoner"  # Default background
    sex: str = "Male"  # Default sex/gender
    origin_id: Optional[str] = None # Added origin_id

    # Player attributes
    level: int = 1
    experience: int = 0

    # Stats manager ID - reference to the stats manager for this player
    stats_manager_id: Optional[str] = None

    # Location
    current_location: str = ""
    current_district: str = ""

    # Inventory (to be properly integrated later)
    inventory_id: Optional[str] = None
    equipped_items: Dict[str, str] = field(default_factory=dict)  # slot -> item_id

    # Active quests (to be properly integrated later)
    active_quests: List[str] = field(default_factory=list)  # quest_ids
    completed_quests: List[str] = field(default_factory=list)  # quest_ids

    # Dynamic state related to social/combat
    current_resolve: float = 0.0 # Current social 'health'
    active_social_effects: List[StatusEffectData] = field(default_factory=list)

    # Character appearance
    character_image: Optional[str] = None

    @property
    def experience_to_next_level(self) -> int:
        """
        Calculate the experience required to reach the next level.

        This is a simple formula: 100 * current level
        Can be adjusted for different game progression rates.

        Returns:
            The experience points needed to level up.
        """
        return 100 * self.level

    def to_dict(self) -> Dict[str, Any]:
        """Convert PlayerState to a dictionary for serialization."""
        return {
            "name": self.name,
            "race": self.race,
            "path": self.path,
            "background": self.background,
            "sex": self.sex,
            "origin_id": self.origin_id, # Added
            "level": self.level,
            "experience": self.experience,
            "stats_manager_id": self.stats_manager_id,
            "current_location": self.current_location,
            "current_district": self.current_district,
            "inventory_id": self.inventory_id,
            "equipped_items": self.equipped_items,
            "active_quests": self.active_quests,
            "completed_quests": self.completed_quests,
            "character_image": self.character_image,
            "current_resolve": self.current_resolve,
            "active_social_effects": [effect.to_dict() for effect in self.active_social_effects],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlayerState':
        """Create a PlayerState from a dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            race=data.get("race", "Human"),
            path=data.get("path", "Wanderer"),
            background=data.get("background", "Commoner"),
            sex=data.get("sex", "Male"),
            origin_id=data.get("origin_id"), # Added
            level=data.get("level", 1),
            experience=data.get("experience", 0),
            stats_manager_id=data.get("stats_manager_id"),
            current_location=data.get("current_location", ""),
            current_district=data.get("current_district", ""),
            inventory_id=data.get("inventory_id"),
            equipped_items=data.get("equipped_items", {}),
            active_quests=data.get("active_quests", []),
            completed_quests=data.get("completed_quests", []),
            character_image=data.get("character_image"),
            current_resolve=data.get("current_resolve", 0.0),
            active_social_effects=[
                StatusEffectData.from_dict(effect_data)
                for effect_data in data.get("active_social_effects", [])
            ]
        )