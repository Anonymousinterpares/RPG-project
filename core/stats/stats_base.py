"""
Base classes and enums for the stats system.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union


class StatCategory(Enum):
    """Categories of statistics."""
    PRIMARY = auto()
    DERIVED = auto()
    COMBAT = auto()
    SKILL = auto()
    RESISTANCE = auto()
    MISC = auto()


class StatType(Enum):
    """Primary character statistics."""
    # Primary attributes
    STRENGTH = "STR"        # Physical power
    DEXTERITY = "DEX"       # Agility and reflexes
    CONSTITUTION = "CON"    # Physical resilience
    INTELLIGENCE = "INT"    # Mental acuity
    WISDOM = "WIS"          # Intuition and perception
    CHARISMA = "CHA"        # Social influence
    WILLPOWER = "WIL"       # Mental fortitude, resistance to influence
    INSIGHT = "INS"         # Understanding situations and people

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, stat_name: str) -> 'StatType':
        """Convert a string to a StatType enum."""
        stat_name_lower = stat_name.lower()
        for stat in cls:
            # Check both value (e.g., "STR") and name (e.g., "STRENGTH")
            if stat.value.lower() == stat_name_lower or stat.name.lower() == stat_name_lower:
                return stat
        raise ValueError(f"Unknown stat type: {stat_name}")


class DerivedStatType(Enum):
    """Derived character statistics."""
    # Health and resources
    HEALTH = "Health Points"           # Hit points
    MAX_HEALTH = "Max Health Points"   # Maximum hit points
    MANA = "Mana Points"               # Current magic resource
    MAX_MANA = "Max Mana Points"       # Maximum magic resource 
    STAMINA = "Stamina"                # Current physical resource
    MAX_STAMINA = "Max Stamina"        # Maximum physical resource 
    MAX_AP = "Max Action Points"       # Maximum action points
    AP_REGENERATION = "AP Regeneration"  # AP recovery per turn
    RESOLVE = "Resolve"                # Social/Mental composure 'health'
    MAX_RESOLVE = "Max Resolve"        # Maximum social/mental composure
    
    # Combat stats
    MELEE_ATTACK = "Melee Attack"      # Melee attack bonus
    RANGED_ATTACK = "Ranged Attack"    # Ranged attack bonus
    MAGIC_ATTACK = "Magic Attack"      # Magic attack bonus
    DEFENSE = "Defense"                # Physical defense
    MAGIC_DEFENSE = "Magic Defense"    # Magic defense
    DAMAGE_REDUCTION = "Damage Reduction" # Flat damage reduction 

    # Utility stats
    INITIATIVE = "Initiative"          # Combat turn order
    CARRY_CAPACITY = "Carry Capacity"  # Weight limit
    MOVEMENT = "Movement"              # Movement speed

    def __str__(self) -> str:
        # Return the user-friendly value (e.g., "Health Points")
        return self.value

    @classmethod
    def from_string(cls, stat_name: str) -> 'DerivedStatType':
        """Convert a string to a DerivedStatType enum."""
        stat_name_lower = stat_name.lower().replace(" ", "_") 
        for stat in cls:
            enum_name_lower = stat.name.lower()
            enum_value_normalized = stat.value.lower().replace(" ", "_")
            if enum_name_lower == stat_name_lower or enum_value_normalized == stat_name_lower:
                return stat
        raise ValueError(f"Unknown derived stat type: {stat_name}")


class Skill(Enum):
    """Character skills."""
    # Social Skills
    PERSUASION = ("Persuasion", StatType.CHARISMA)      # Influencing others through diplomacy, negotiation
    INTIMIDATION = ("Intimidation", StatType.STRENGTH)  # Influencing others through threats, coercion (could also be CHA or WIL depending on flavor)
    DECEPTION = ("Deception", StatType.CHARISMA)       # Influencing others through lies, misdirection
    EMPATHY = ("Empathy", StatType.INSIGHT)           # Understanding others' feelings and intentions (could also be WIS)
    BARTER = ("Barter", StatType.CHARISMA)           # Influencing prices during trade

    # Combat Skills
    MELEE_ATTACK = ("Melee Attack", StatType.STRENGTH)   # Physical close-range combat attacks
    RANGED_ATTACK = ("Ranged Attack", StatType.DEXTERITY) # Physical ranged combat attacks
    SPELL_ATTACK = ("Spell Attack", StatType.INTELLIGENCE) # Magical attacks
    DEFENSE = ("Defense", StatType.DEXTERITY)       # Avoiding physical attacks
    DODGE = ("Dodge", StatType.DEXTERITY)         # Evading physical attacks

    # Add other skill types as needed (e.g., Crafting, Knowledge)

    def __init__(self, display_name: str, primary_stat: StatType):
        self._display_name = display_name
        self._primary_stat = primary_stat

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def primary_stat(self) -> StatType:
        return self._primary_stat

# REMOVED: Simple StatModifier dataclass definition

@dataclass
class Stat:
    """A character statistic with base value.""" # Updated docstring
    name: Union[StatType, DerivedStatType, str]
    base_value: float
    category: StatCategory
    description: str = ""
    exp: float = 0.0
    exp_to_next: float = 100.0

    # RESTORED: value property, simplified to return base_value
    @property
    def value(self) -> float:
        """Returns the base value of the stat.
        Note: This does NOT include modifiers managed by ModifierManager.
        Use StatsManager.get_stat_value() for the final calculated value.
        """
        return self.base_value

    # REMOVED: def add_modifier(self, modifier: StatModifier) -> None:
    # REMOVED: def remove_modifier(self, source: str) -> None:
    # REMOVED: def clear_modifiers(self) -> None:

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            # Use the Enum *name* (e.g., STRENGTH) for serialization consistency
            "name": self.name.name if isinstance(self.name, (StatType, DerivedStatType)) else str(self.name),
            "base_value": self.base_value,
            "category": self.category.name,
            "description": self.description,
            "exp": self.exp,
            "exp_to_next": self.exp_to_next
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Stat':
        """Create a Stat from a dictionary."""
        stat_name_str = data["name"]
        try:
            # Try to convert name string (e.g., "STRENGTH") back to StatType Enum
            name = StatType[stat_name_str]
        except KeyError:
            try:
                 # Try to convert name string (e.g., "MAX_HEALTH") back to DerivedStatType Enum
                name = DerivedStatType[stat_name_str]
            except KeyError:
                # If it's neither, keep it as a string (e.g., for custom stats)
                name = stat_name_str

        category = StatCategory[data["category"]]

        stat = cls(
            name=name,
            base_value=data["base_value"],
            category=category,
            description=data.get("description", ""),
            exp=data.get("exp", 0.0),
            exp_to_next=data.get("exp_to_next", 100.0)
        )
        # REMOVED: Loading modifiers from data here

        return stat