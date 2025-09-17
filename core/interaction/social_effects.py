"""
Defines status effects specific to social interactions.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class StatusEffectData:
    """Holds data for an active status effect."""
    effect_type: Enum  # Could be SocialStatusEffect or CombatStatusEffect etc.
    duration: Optional[int] = None  # Turns or time units, None for permanent
    intensity: Optional[float] = None # Magnitude of the effect (e.g., penalty amount)
    source: Optional[str] = None # Origin of the effect (e.g., ability name, character ID)

    def __str__(self) -> str:
        details = []
        if self.duration is not None:
            details.append(f"duration={self.duration}")
        if self.intensity is not None:
            details.append(f"intensity={self.intensity}")
        if self.source:
            details.append(f"source='{self.source}'")
        details_str = f" ({', '.join(details)})" if details else ""
        return f"{self.effect_type.name}{details_str}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert StatusEffectData to a dictionary for serialization."""
        return {
            "effect_type_name": self.effect_type.name, # Store enum name
            "duration": self.duration,
            "intensity": self.intensity,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusEffectData':
        """Create a StatusEffectData from a dictionary."""
        effect_type_name = data.get("effect_type_name")
        effect_type = None
        if effect_type_name:
            try:
                # Assuming SocialStatusEffect for now, might need adjustment if other types exist
                effect_type = SocialStatusEffect[effect_type_name]
            except KeyError:
                # Handle cases where the effect type name is invalid or from a different enum
                print(f"Warning: Unknown status effect type '{effect_type_name}' found in data.") # Or use logger

        return cls(
            effect_type=effect_type, # Store the actual enum member or None
            duration=data.get("duration"),
            intensity=data.get("intensity"),
            source=data.get("source"),
        )


class SocialStatusEffect(Enum):
    """Status effects resulting from social interactions."""
    # Positive/Neutral
    CHARMED = auto()        # Highly positive disposition, susceptible to requests.
    CONVINCED = auto()      # Believes a specific argument or piece of information.
    TRUSTING = auto()       # Generally believes what the source says.
    FRIENDLY = auto()       # Positive disposition towards the source.

    # Negative
    INTIMIDATED = auto()    # Fearful, less likely to oppose, may comply reluctantly.
    ANGERED = auto()        # Hostile disposition, likely to refuse or argue.
    SUSPICIOUS = auto()     # Distrustful, likely to question motives or statements.
    UNFRIENDLY = auto()     # Negative disposition towards the source.
    DECEIVED = auto()       # Believes a falsehood presented by the source.

    # Could add more nuanced effects like:
    # INSPIRED, DEMORALIZED, CONFUSED, OBLIGATED, GRATEFUL, RESENTFUL

    def __str__(self) -> str:
        return self.name