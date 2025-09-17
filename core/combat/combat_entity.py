"""
Combat entity class for representing combatants.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Union, Tuple
import logging

logger = logging.getLogger(__name__)

from core.stats.stats_base import StatType, DerivedStatType


class EntityType(Enum):
    """Types of combat entities."""
    PLAYER = auto()
    NPC = auto()
    ALLY = auto()
    ENEMY = auto()
    CREATURE = auto()


@dataclass
class CombatEntity:
    """
    Represents an entity in combat (player, enemy, ally, etc.).

    Attributes:
        id: Unique identifier for the entity
        name: Display name of the entity
        combat_name: Unique name used within this combat encounter (e.g., "Goblin 1") <--- ADDED
        entity_type: Type of entity (player, enemy, etc.)
        stats: Dictionary of stat values
        current_hp: Current hit points
        max_hp: Maximum hit points
        current_mp: Current mana points
        max_mp: Maximum mana points
        current_stamina: Current stamina
        max_stamina: Maximum stamina
        status_effects: Dict of active status effect names to optional durations
        initiative: Initiative value for turn order
        position: Position index in combat (0=front, higher=back)
        description: Flavor text description
        is_active_in_combat: Whether the entity is currently participating (not fled/removed)
    """
    id: str
    name: str
    combat_name: str # <--- ADDED
    entity_type: EntityType
    stats: Dict[Union[StatType, DerivedStatType, str], float]
    current_hp: float
    max_hp: float
    current_mp: float = 0
    max_mp: float = 0
    current_stamina: float = 0
    max_stamina: float = 0
    status_effects: Dict[str, Optional[int]] = field(default_factory=dict)
    initiative: float = 0
    position: int = 0
    description: str = ""
    is_active_in_combat: bool = True

    def is_alive(self) -> bool:
        """Check if the entity is alive."""
        return self.current_hp > 0

    def take_damage(self, amount: float) -> float:
        """
        Apply damage to the entity's current HP.

        Args:
            amount: Amount of damage to apply.

        Returns:
            The actual amount of damage dealt (after mitigation, etc.).
        """
        actual_damage = max(0, amount)
        previous_hp = self.current_hp
        self.current_hp = max(0, self.current_hp - actual_damage)
        damage_taken = previous_hp - self.current_hp
        return damage_taken

    def heal(self, amount: float) -> float:
        """
        Heal the entity's current HP.

        Args:
            amount: Amount of healing to apply.

        Returns:
            The actual amount healed.
        """
        if not self.is_alive():
            return 0

        amount_to_heal = max(0, amount)
        previous_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount_to_heal)
        amount_healed = self.current_hp - previous_hp
        return amount_healed

    def spend_mp(self, amount: float) -> bool:
        """
        Spend mana points directly on the entity.

        Args:
            amount: Amount of MP to spend.

        Returns:
            True if successful, False if not enough MP.
        """
        amount_to_spend = max(0, amount)
        if self.current_mp < amount_to_spend:
            return False

        self.current_mp -= amount_to_spend
        return True

    def spend_stamina(self, amount: float) -> bool:
        """
        Spend stamina directly on the entity.

        Args:
            amount: Amount of stamina to spend.

        Returns:
            True if successful, False if not enough stamina.
        """
        amount_to_spend = max(0, amount)
        if self.current_stamina < amount_to_spend:
            return False

        self.current_stamina -= amount_to_spend
        return True

    def restore_mp(self, amount: float) -> float:
        """
        Restore mana points directly on the entity.

        Args:
            amount: Amount of MP to restore.

        Returns:
            The actual amount restored.
        """
        amount_to_restore = max(0, amount)
        before = self.current_mp
        self.current_mp = min(self.max_mp, self.current_mp + amount_to_restore)
        amount_restored = self.current_mp - before
        return amount_restored

    def restore_stamina(self, amount: float) -> float:
        """
        Restore stamina directly on the entity.

        Args:
            amount: Amount of stamina to restore.

        Returns:
            The actual amount restored.
        """
        amount_to_restore = max(0, amount)
        before = self.current_stamina
        self.current_stamina = min(self.max_stamina, self.current_stamina + amount_to_restore)
        amount_restored = self.current_stamina - before
        return amount_restored

    def set_current_hp(self, value: float):
        """Sets the current HP, clamped between 0 and max_hp."""
        self.current_hp = max(0.0, min(value, self.max_hp))

    def set_current_stamina(self, value: float):
        """Sets the current Stamina, clamped between 0 and max_stamina."""
        self.current_stamina = max(0.0, min(value, self.max_stamina))

    def add_status_effect(self, effect: str, duration: Optional[int] = None) -> None:
        """
        Add a status effect to the entity.

        Args:
            effect: Name of the effect to add.
            duration: Number of turns the effect lasts, or None for permanent.
        """
        self.status_effects[effect] = duration
        logger.debug(f"Added status effect '{effect}' to {self.name} ({self.combat_name}) with duration: {duration}") # Added combat_name to log

    def remove_status_effect(self, effect: str) -> bool:
        """
        Remove a status effect from the entity.

        Args:
            effect: Name of the effect to remove.

        Returns:
            True if the effect was removed, False if it wasn't present.
        """
        if effect in self.status_effects:
            del self.status_effects[effect]
            logger.debug(f"Removed status effect '{effect}' from {self.name} ({self.combat_name})") # Added combat_name to log
            return True
        return False

    def has_status_effect(self, effect: str) -> bool:
        """
        Check if the entity has a specific status effect.

        Args:
            effect: Name of the effect to check.

        Returns:
            True if the entity has the effect, False otherwise.
        """
        return effect in self.status_effects

    def get_status_effect_duration(self, effect: str) -> Optional[int]:
        """
        Get the remaining duration of a status effect.

        Args:
            effect: Name of the effect to check.

        Returns:
            Remaining duration, None if permanent, or None if effect not present.
        """
        if effect in self.status_effects:
            return self.status_effects[effect]
        return None

    def decrement_status_effect_durations(self) -> List[str]:
        """
        Decrement durations of all timed status effects by 1.

        Returns:
            List of status effects that expired and were removed.
        """
        expired_effects = []

        for effect, duration in list(self.status_effects.items()):
            if duration is not None:
                new_duration = duration - 1
                if new_duration <= 0:
                    del self.status_effects[effect]
                    expired_effects.append(effect)
                    logger.debug(f"Status effect '{effect}' expired for {self.name} ({self.combat_name})") # Added combat_name
                else:
                    self.status_effects[effect] = new_duration
                    logger.debug(f"Status effect '{effect}' has {new_duration} turns remaining for {self.name} ({self.combat_name})") # Added combat_name

        return expired_effects

    def get_stat(self, stat: Union[StatType, DerivedStatType, str]) -> float:
        """
        Get the value of a stat.

        Args:
            stat: The stat to get.

        Returns:
            The stat value, or 0 if not found.
        """
        return self.stats.get(stat, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "combat_name": self.combat_name, # <--- ADDED
            "entity_type": self.entity_type.name,
            "stats": {str(k): v for k, v in self.stats.items()},
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "current_mp": self.current_mp,
            "max_mp": self.max_mp,
            "current_stamina": self.current_stamina,
            "max_stamina": self.max_stamina,
            "status_effects": {k: v for k, v in self.status_effects.items()},
            "initiative": self.initiative,
            "position": self.position,
            "is_active_in_combat": self.is_active_in_combat,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CombatEntity':
        """Create a CombatEntity from a dictionary."""
        stats = {}
        for k, v in data.get("stats", {}).items():
            try:
                stat_key = StatType.from_string(k)
            except ValueError:
                try:
                    stat_key = DerivedStatType.from_string(k)
                except ValueError:
                    stat_key = k
            stats[stat_key] = v

        # Handle potential missing combat_name during deserialization
        combat_name = data.get("combat_name", data.get("name", "Unknown")) # Fallback to name

        return cls(
            id=data["id"],
            name=data["name"],
            combat_name=combat_name, # <--- ADDED
            entity_type=EntityType[data["entity_type"]],
            stats=stats,
            current_hp=data["current_hp"],
            max_hp=data["max_hp"],
            current_mp=data.get("current_mp", 0),
            max_mp=data.get("max_mp", 0),
            current_stamina=data.get("current_stamina", 0),
            max_stamina=data.get("max_stamina", 0),
            status_effects=data.get("status_effects", {}) if isinstance(data.get("status_effects"), dict) else {effect: None for effect in data.get("status_effects", [])},
            initiative=data.get("initiative", 0),
            position=data.get("position", 0),
            description=data.get("description", ""),
            is_active_in_combat=data.get("is_active_in_combat", True) 
        )
