#!/usr/bin/env python3
"""
Item effect definitions, such as dice roll effects.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class DiceRollEffect:
    """
    Represents a dice-roll based effect on an item.
    """
    effect_type: str  # e.g., "physical_damage", "fire_damage", "healing", "stat_buff"
    dice_notation: str # e.g., "1d6", "2d4+1"
    description: Optional[str] = None # e.g., "Deals fire damage on hit"
    # Future considerations: target_type (self, target_enemy, area), duration, application_trigger (on_hit, on_use)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "effect_type": self.effect_type,
            "dice_notation": self.dice_notation,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiceRollEffect':
        """Create a DiceRollEffect from a dictionary."""
        return cls(
            effect_type=data.get("effect_type", "unknown_effect"),
            dice_notation=data.get("dice_notation", "1d4"),
            description=data.get("description"),
        )