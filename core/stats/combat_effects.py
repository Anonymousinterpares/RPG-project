"""
System for managing combat-related stat modifiers and status effects.
"""

from enum import Enum, auto
from typing import Dict, List, Any, Optional, Union, Set
import logging
import uuid

from core.stats.stats_base import StatType, DerivedStatType
from core.stats.modifier import StatModifier, ModifierGroup, ModifierType, ModifierSource


logger = logging.getLogger(__name__)


class StatusEffectType(Enum):
    """Types of status effects that can affect a character."""
    BUFF = auto()        # Positive effect
    DEBUFF = auto()      # Negative effect
    CROWD_CONTROL = auto()  # Control effect (stun, slow, etc.)
    DAMAGE_OVER_TIME = auto()  # Damage over time (poison, bleeding, etc.)
    SPECIAL = auto()     # Special effect with unique mechanics


class StatusEffect:
    """
    A status effect that can be applied to a character.
    Includes common game effects like poison, stun, etc.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        effect_type: StatusEffectType,
        duration: int,
        modifier_group: Optional[ModifierGroup] = None,
        buff_is_visible: bool = True,
        custom_data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a status effect.
        
        Args:
            name: The display name of the effect
            description: A description of what the effect does
            effect_type: The type of effect
            duration: How many turns the effect lasts
            modifier_group: Optional group of stat modifiers for this effect
            buff_is_visible: Whether this effect should be visible to the player
            custom_data: Additional custom data for unique effects
        """
        self.name = name
        self.description = description
        self.effect_type = effect_type
        self.duration = duration
        self.modifier_group = modifier_group
        self.buff_is_visible = buff_is_visible
        self.custom_data = custom_data or {}
        self.id = str(uuid.uuid4())
    
    def update_duration(self) -> bool:
        """
        Update the duration of the effect.
        Returns True if the effect is still active, False if expired.
        """
        if self.duration <= 0:
            return False
        
        self.duration -= 1
        if self.modifier_group:
            self.modifier_group.update_duration()
        
        return self.duration > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "effect_type": self.effect_type.name,
            "duration": self.duration,
            "modifier_group": self.modifier_group.to_dict() if self.modifier_group else None,
            "buff_is_visible": self.buff_is_visible,
            "custom_data": self.custom_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusEffect':
        """Create a StatusEffect from a dictionary."""
        effect = cls(
            name=data["name"],
            description=data["description"],
            effect_type=StatusEffectType[data["effect_type"]],
            duration=data["duration"],
            modifier_group=ModifierGroup.from_dict(data["modifier_group"]) if data.get("modifier_group") else None,
            buff_is_visible=data.get("buff_is_visible", True),
            custom_data=data.get("custom_data", {})
        )
        effect.id = data.get("id", effect.id)
        return effect


class StatusEffectManager:
    """
    Manages status effects for a character, including applying, updating,
    and removing effects.
    """
    
    def __init__(self, stats_manager=None):
        """
        Initialize the status effect manager.
        
        Args:
            stats_manager: Optional reference to the character's stats manager
        """
        self.stats_manager = stats_manager
        self.active_effects: Dict[str, StatusEffect] = {}
    
    def add_effect(self, effect: StatusEffect) -> None:
        """
        Add a status effect to the character.
        
        Args:
            effect: The effect to add
        """
        # Skip effects with duration <= 0
        if effect.duration <= 0:
            return
        
        # Stacking semantics
        stacking_rule = None
        try:
            stacking_rule = (effect.custom_data or {}).get("stacking_rule")
            if isinstance(stacking_rule, str):
                stacking_rule = stacking_rule.strip().lower()
        except Exception:
            stacking_rule = None
        
        # Check for an existing effect with the same name
        same_name_ids = [eid for eid, ex in self.active_effects.items() if ex.name == effect.name]
        if same_name_ids:
            if stacking_rule == "stack":
                # Allow multiple with same name; do not remove existing
                pass
            elif stacking_rule == "refresh":
                # Refresh duration of existing effects (use max between existing and new)
                for eid in same_name_ids:
                    ex = self.active_effects.get(eid)
                    if not ex:
                        continue
                    ex.duration = max(int(ex.duration), int(effect.duration))
                # Do not add a new instance for refresh semantics
                return
            else:
                # Replace existing: remove all same-name instances, then add new one
                for eid in same_name_ids:
                    self.remove_effect(eid)
        
        # Add the effect
        self.active_effects[effect.id] = effect
        
        # Apply the stat modifiers if we have a stats manager
        if self.stats_manager and effect.modifier_group:
            self.stats_manager.add_modifier_group(effect.modifier_group)
        # Wire typed resistances (percent and dice) from status custom_data if provided
        try:
            if self.stats_manager and isinstance(effect.custom_data, dict):
                src_id = f"status_{effect.id}"
                tr = effect.custom_data.get("typed_resistances")
                if isinstance(tr, dict) and hasattr(self.stats_manager, 'set_resistance_contribution'):
                    self.stats_manager.set_resistance_contribution(src_id, tr)
                trd = effect.custom_data.get("typed_resistances_dice")
                if isinstance(trd, dict) and hasattr(self.stats_manager, 'set_resistance_dice_contribution'):
                    self.stats_manager.set_resistance_dice_contribution(src_id, trd)
        except Exception:
            pass
        
        logger.debug(f"Added status effect: {effect.name} (Duration: {effect.duration})")
    
    def remove_effect(self, effect_id: str) -> bool:
        """
        Remove a status effect by ID.
        
        Args:
            effect_id: The ID of the effect to remove
            
        Returns:
            True if the effect was found and removed, False otherwise
        """
        if effect_id not in self.active_effects:
            return False
        
        effect = self.active_effects[effect_id]
        
        # Remove the stat modifiers if we have a stats manager
        if self.stats_manager and effect.modifier_group:
            self.stats_manager.remove_modifier_group(effect.modifier_group.id)
        # Remove any typed resistance contributions wired from this status
        try:
            if self.stats_manager:
                src_id = f"status_{effect.id}"
                if hasattr(self.stats_manager, 'remove_resistance_contribution'):
                    self.stats_manager.remove_resistance_contribution(src_id)
                if hasattr(self.stats_manager, 'remove_resistance_dice_contribution'):
                    self.stats_manager.remove_resistance_dice_contribution(src_id)
        except Exception:
            pass
        
        # Remove the effect
        del self.active_effects[effect_id]
        logger.debug(f"Removed status effect: {effect.name}")
        
        return True
    
    def remove_effects_by_name(self, name: str) -> int:
        """
        Remove all effects with a specific name.
        
        Args:
            name: The name of the effects to remove
            
        Returns:
            The number of effects removed
        """
        effect_ids = [e_id for e_id, effect in self.active_effects.items() if effect.name == name]
        for effect_id in effect_ids:
            self.remove_effect(effect_id)
        return len(effect_ids)
    
    def remove_effects_by_type(self, effect_type: StatusEffectType) -> int:
        """
        Remove all effects of a specific type.
        
        Args:
            effect_type: The type of effects to remove
            
        Returns:
            The number of effects removed
        """
        effect_ids = [e_id for e_id, effect in self.active_effects.items() if effect.effect_type == effect_type]
        for effect_id in effect_ids:
            self.remove_effect(effect_id)
        return len(effect_ids)
    
    def clear_all_effects(self) -> int:
        """
        Remove all active effects.
        
        Returns:
            The number of effects removed
        """
        count = len(self.active_effects)
        effect_ids = list(self.active_effects.keys())
        for effect_id in effect_ids:
            self.remove_effect(effect_id)
        return count
    
    def update_durations(self) -> Set[str]:
        """
        Update durations for all active effects.
        Removes expired effects.
        
        Returns:
            Set of IDs of expired effects that were removed
        """
        expired_ids = set()
        for effect_id, effect in list(self.active_effects.items()):
            if not effect.update_duration():
                self.remove_effect(effect_id)
                expired_ids.add(effect_id)
        
        if expired_ids:
            logger.debug(f"Removed {len(expired_ids)} expired status effects")
        
        return expired_ids
    
    def get_effect_by_id(self, effect_id: str) -> Optional[StatusEffect]:
        """
        Get a status effect by ID.
        
        Args:
            effect_id: The ID of the effect to get
            
        Returns:
            The effect if found, None otherwise
        """
        return self.active_effects.get(effect_id)
    
    def get_effects_by_name(self, name: str) -> List[StatusEffect]:
        """
        Get all effects with a specific name.
        
        Args:
            name: The name of the effects to get
            
        Returns:
            List of matching effects
        """
        return [effect for effect in self.active_effects.values() if effect.name == name]
    
    def get_effects_by_type(self, effect_type: StatusEffectType) -> List[StatusEffect]:
        """
        Get all effects of a specific type.
        
        Args:
            effect_type: The type of effects to get
            
        Returns:
            List of matching effects
        """
        return [effect for effect in self.active_effects.values() if effect.effect_type == effect_type]
    
    def has_effect(self, name: str) -> bool:
        """
        Check if the character has a specific effect.
        
        Args:
            name: The name of the effect to check for
            
        Returns:
            True if the effect is active, False otherwise
        """
        return any(effect.name == name for effect in self.active_effects.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "active_effects": {e_id: effect.to_dict() for e_id, effect in self.active_effects.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], stats_manager=None) -> 'StatusEffectManager':
        """Create a StatusEffectManager from a dictionary."""
        manager = cls(stats_manager)
        
        # Load active effects
        for effect_id, effect_data in data.get("active_effects", {}).items():
            effect = StatusEffect.from_dict(effect_data)
            manager.active_effects[effect_id] = effect
            
            # Apply the stat modifiers if we have a stats manager
            if stats_manager and effect.modifier_group:
                stats_manager.add_modifier_group(effect.modifier_group)
        
        return manager


# Common status effect factory methods
def create_poison_effect(potency: int = 1, duration: int = 3) -> StatusEffect:
    """Create a poison effect."""
    modifier_group = ModifierGroup(
        name="Poison",
        source_type=ModifierSource.CONDITION,
        modifier_type=ModifierType.TEMPORARY,
        duration=duration,
        description=f"Poison dealing {potency} damage per turn"
    )
    
    # Poison reduces CON and deals damage over time
    modifier_group.add_modifier(
        stat=StatType.CONSTITUTION,
        value=-potency,
        is_percentage=False,
        description="Poison weakens your constitution"
    )
    
    return StatusEffect(
        name="Poison",
        description=f"Taking {potency} damage per turn and suffering reduced constitution",
        effect_type=StatusEffectType.DAMAGE_OVER_TIME,
        duration=duration,
        modifier_group=modifier_group,
        custom_data={"damage_per_turn": potency}
    )


def create_stun_effect(duration: int = 1) -> StatusEffect:
    """Create a stun effect."""
    modifier_group = ModifierGroup(
        name="Stunned",
        source_type=ModifierSource.CONDITION,
        modifier_type=ModifierType.TEMPORARY,
        duration=duration,
        description="Stunned and unable to act"
    )
    
    # Stunned characters have severely reduced stats
    modifier_group.add_modifier(
        stat=DerivedStatType.INITIATIVE,
        value=-100,
        is_percentage=False,
        description="Stunned characters cannot act"
    )
    
    return StatusEffect(
        name="Stunned",
        description="Unable to take actions",
        effect_type=StatusEffectType.CROWD_CONTROL,
        duration=duration,
        modifier_group=modifier_group,
        custom_data={"can_act": False}
    )


def create_berserk_effect(duration: int = 3) -> StatusEffect:
    """Create a berserk effect."""
    modifier_group = ModifierGroup(
        name="Berserk",
        source_type=ModifierSource.CONDITION,
        modifier_type=ModifierType.TEMPORARY,
        duration=duration,
        description="Increased damage but reduced defense"
    )
    
    # Berserk increases strength but reduces defense
    modifier_group.add_modifier(
        stat=StatType.STRENGTH,
        value=4,
        is_percentage=False,
        description="Increased strength from berserk rage"
    )
    
    modifier_group.add_modifier(
        stat=DerivedStatType.DEFENSE,
        value=-2,
        is_percentage=False,
        description="Reduced defense from reckless attacks"
    )
    
    return StatusEffect(
        name="Berserk",
        description="Increased damage but reduced defense",
        effect_type=StatusEffectType.BUFF,
        duration=duration,
        modifier_group=modifier_group
    )


def create_regeneration_effect(amount: int = 2, duration: int = 5) -> StatusEffect:
    """Create a regeneration effect."""
    modifier_group = ModifierGroup(
        name="Regeneration",
        source_type=ModifierSource.CONDITION,
        modifier_type=ModifierType.TEMPORARY,
        duration=duration,
        description=f"Regenerating {amount} health per turn"
    )
    
    # No stat modifiers for regeneration, it's handled by the custom data
    
    return StatusEffect(
        name="Regeneration",
        description=f"Regenerating {amount} health per turn",
        effect_type=StatusEffectType.BUFF,
        duration=duration,
        modifier_group=modifier_group,
        custom_data={"heal_per_turn": amount}
    )
