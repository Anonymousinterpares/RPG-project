"""
Classes for handling stat modifiers from various sources.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, List
import uuid

from core.stats.stats_base import StatType, DerivedStatType


class ModifierType(Enum):
    """Types of modifiers based on their duration."""
    PERMANENT = auto()       # Permanent bonus (race, class, etc.)
    SEMI_PERMANENT = auto()  # Long-term but not permanent (disease, training)
    TEMPORARY = auto()       # Short-term effect (spell, potion, etc.)


class ModifierSource(Enum):
    """Sources of stat modifiers."""
    RACIAL = auto()          # Inherent racial bonus
    CLASS = auto()           # Class feature
    BACKGROUND = auto()      # Character background
    EQUIPMENT = auto()       # From equipped items
    SPELL = auto()           # Magical effect
    POTION = auto()          # Consumable effect
    CONDITION = auto()       # Status effect (poisoned, blessed, etc.)
    ENVIRONMENT = auto()     # Location-based effect
    TRAINING = auto()        # Skill improvement
    LEVEL_UP = auto()        # Stat increase from leveling
    NARRATIVE = auto()       # Story-driven effect
    OTHER = auto()           # Miscellaneous source


@dataclass
class StatModifier:
    """
    A modifier that affects a character stat.
    
    Attributes:
        id: Unique identifier for the modifier
        stat: The stat being modified
        value: The value of the modification
        source_type: The type of source (equipment, spell, etc.)
        source_name: Specific name of the source
        modifier_type: Duration category (permanent, temporary, etc.)
        is_percentage: Whether the value is a percentage or flat bonus
        duration: Number of turns or time remaining (None for permanent)
        stacks: Whether this modifier stacks with others from same source
        description: Human-readable description of the effect
    """
    stat: Union[StatType, DerivedStatType, str]
    value: float
    source_type: ModifierSource
    source_name: str
    modifier_type: ModifierType
    is_percentage: bool = False
    duration: Optional[int] = None  # None means permanent
    stacks: bool = False
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __str__(self) -> str:
        """Human-readable representation."""
        prefix = "+" if self.value > 0 else ""
        suffix = "%" if self.is_percentage else ""
        duration_str = f" ({self.duration} turns)" if self.duration else ""
        return f"{self.source_name}: {prefix}{self.value}{suffix} to {self.stat}{duration_str}"
    
    def update_duration(self) -> bool:
        """
        Decrement the duration by 1 if it exists.
        Returns True if the modifier is still active, False if expired.
        """
        if self.duration is None:  # Permanent modifier
            return True
        
        if self.duration > 0:
            self.duration -= 1
            return True
        
        return False  # Expired
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "id": self.id,
            "stat": str(self.stat),
            "value": self.value,
            "source_type": self.source_type.name,
            "source_name": self.source_name,
            "modifier_type": self.modifier_type.name,
            "is_percentage": self.is_percentage,
            "duration": self.duration,
            "stacks": self.stacks,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatModifier':
        """Create a StatModifier from a dictionary."""
        try:
            # Try to convert stat to StatType
            stat = StatType.from_string(data["stat"])
        except ValueError:
            try:
                # Try to convert stat to DerivedStatType
                stat = DerivedStatType.from_string(data["stat"])
            except ValueError:
                # Just use the string name
                stat = data["stat"]
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            stat=stat,
            value=data["value"],
            source_type=ModifierSource[data["source_type"]],
            source_name=data["source_name"],
            modifier_type=ModifierType[data["modifier_type"]],
            is_percentage=data["is_percentage"],
            duration=data["duration"],
            stacks=data.get("stacks", False),
            description=data.get("description", "")
        )


@dataclass
class ModifierGroup:
    """
    A group of related modifiers that are applied together.
    For example, all modifiers from a single buff spell or equipment item.
    """
    name: str
    source_type: ModifierSource
    modifier_type: ModifierType
    duration: Optional[int] = None
    modifiers: List[StatModifier] = field(default_factory=list)
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def add_modifier(self, stat: Union[StatType, DerivedStatType, str], value: float, 
                    is_percentage: bool = False, stacks: bool = False, 
                    description: str = "") -> None:
        """Add a new modifier to this group."""
        modifier = StatModifier(
            stat=stat,
            value=value,
            source_type=self.source_type,
            source_name=self.name,
            modifier_type=self.modifier_type,
            is_percentage=is_percentage,
            duration=self.duration,
            stacks=stacks,
            description=description
        )
        self.modifiers.append(modifier)
    
    def update_duration(self) -> bool:
        """
        Update the duration of all modifiers in the group.
        Returns True if at least one modifier is still active.
        """
        if self.duration is None:  # Permanent group
            return True
        
        if self.duration > 0:
            self.duration -= 1
            # Update all modifiers' durations
            for mod in self.modifiers:
                mod.duration = self.duration
            return True
        
        return False  # All expired
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type.name,
            "modifier_type": self.modifier_type.name,
            "duration": self.duration,
            "modifiers": [mod.to_dict() for mod in self.modifiers],
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModifierGroup':
        """Create a ModifierGroup from a dictionary."""
        group = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            source_type=ModifierSource[data["source_type"]],
            modifier_type=ModifierType[data["modifier_type"]],
            duration=data["duration"],
            description=data.get("description", "")
        )
        
        # Add modifiers
        for mod_data in data.get("modifiers", []):
            group.modifiers.append(StatModifier.from_dict(mod_data))
        
        return group
