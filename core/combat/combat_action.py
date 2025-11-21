"""
Combat action class for representing actions in combat.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
import uuid


class ActionType(Enum):
    """Types of combat actions."""
    ATTACK = "attack"
    DEFEND = "defend"
    FLEE = "flee"
    SURRENDER = "surrender"  # New action type
    ITEM = "item"
    SPELL = "spell"
    WAIT = "wait"
    SKILL = "skill"
    OTHER = "other"


@dataclass
class CombatAction:
    """
    Represents an action taken during combat.
    
    Attributes:
        id: Unique identifier for the action
        name: Display name of the action
        action_type: Type of action
        performer_id: ID of the entity performing the action
        targets: List of target entity IDs
        cost_mp: Mana cost
        cost_stamina: Stamina cost
        dice_notation: Damage/effect formula (e.g., "2d6+3")
        description: Description of the action
        special_effects: Additional effects (dict of effect name to parameters)
    """
    id: str = ""
    name: str = ""
    action_type: ActionType = ActionType.OTHER
    performer_id: str = ""
    targets: List[str] = None
    cost_mp: float = 0
    cost_stamina: float = 0
    dice_notation: str = ""
    description: str = ""
    special_effects: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.targets is None:
            self.targets = []
        if self.special_effects is None:
            self.special_effects = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "action_type": self.action_type.name,
            "performer_id": self.performer_id,
            "targets": self.targets,
            "cost_mp": self.cost_mp,
            "cost_stamina": self.cost_stamina,
            "dice_notation": self.dice_notation,
            "description": self.description,
            "special_effects": self.special_effects
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CombatAction':
        """Create a CombatAction from a dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            action_type=ActionType[data["action_type"]],
            performer_id=data["performer_id"],
            targets=data.get("targets", []),
            cost_mp=data.get("cost_mp", 0),
            cost_stamina=data.get("cost_stamina", 0),
            dice_notation=data.get("dice_notation", ""),
            description=data.get("description", ""),
            special_effects=data.get("special_effects", {})
        )


@dataclass
class AttackAction(CombatAction):
    """Represents a basic attack action."""
    
    def __init__(
            self,
            performer_id: str,
            target_id: str,
            weapon_name: str = "unarmed",
            dice_notation: str = "1d4",
            **kwargs
        ):
            # Calculate the name based on weapon_name
            action_name = f"{weapon_name.capitalize()} Attack"
            
            # Remove 'name' from kwargs if it exists to prevent conflict
            kwargs.pop('name', None) 
            
            super().__init__(
                id=kwargs.get("id", str(uuid.uuid4())),
                name=action_name, # Pass the calculated name explicitly
                action_type=ActionType.ATTACK,
                performer_id=performer_id,
                targets=[target_id],
                dice_notation=dice_notation,
                description=f"Attack with {weapon_name}",
                **kwargs # Pass remaining kwargs
            )

@dataclass
class SpellAction(CombatAction):
    """Represents a spell casting action."""
    
    def __init__(
        self,
        performer_id: str,
        spell_name: str,
        target_ids: List[str],
        cost_mp: float,
        dice_notation: str = "",
        description: str = "",
        special_effects: Dict[str, Any] = None,
        **kwargs
    ):
        if special_effects is None:
            special_effects = {}
            
        super().__init__(
            id=kwargs.get("id", str(uuid.uuid4())),
            name=spell_name,
            action_type=ActionType.SPELL,
            performer_id=performer_id,
            targets=target_ids,
            cost_mp=cost_mp,
            dice_notation=dice_notation,
            description=description or f"Cast {spell_name}",
            special_effects=special_effects,
            **kwargs
        )


@dataclass
class DefendAction(CombatAction):
    """Represents a defensive action."""
    
    def __init__(self, performer_id: str, **kwargs):
        super().__init__(
            id=kwargs.get("id", str(uuid.uuid4())),
            name="Defend",
            action_type=ActionType.DEFEND,
            performer_id=performer_id,
            description="Take a defensive stance, reducing incoming damage",
            special_effects={"damage_reduction": 0.5},  # 50% damage reduction
            **kwargs
        )


@dataclass
class SurrenderAction(CombatAction):
    """Represents an attempt to surrender in combat."""
    
    def __init__(self, performer_id: str, **kwargs):
        super().__init__(
            id=kwargs.get("id", str(uuid.uuid4())),
            name="Surrender",
            action_type=ActionType.SURRENDER,
            performer_id=performer_id,
            description="Attempt to surrender to enemies",
            **kwargs
        )


@dataclass
class ItemAction(CombatAction):
    """Represents using an item in combat."""
    
    def __init__(
        self,
        performer_id: str,
        item_id: str,
        item_name: str,
        target_ids: List[str],
        dice_notation: str = "",
        description: str = "",
        special_effects: Dict[str, Any] = None,
        **kwargs
    ):
        if special_effects is None:
            special_effects = {"item_id": item_id}
        else:
            special_effects["item_id"] = item_id
            
        super().__init__(
            id=kwargs.get("id", str(uuid.uuid4())),
            name=f"Use {item_name}",
            action_type=ActionType.ITEM,
            performer_id=performer_id,
            targets=target_ids,
            dice_notation=dice_notation,
            description=description or f"Use {item_name}",
            special_effects=special_effects,
            **kwargs
        )


@dataclass
class FleeAction(CombatAction):
    """Represents an attempt to flee from combat."""
    
    def __init__(self, performer_id: str, **kwargs):
        super().__init__(
            id=kwargs.get("id", str(uuid.uuid4())),
            name="Flee",
            action_type=ActionType.FLEE,
            performer_id=performer_id,
            description="Attempt to escape from combat",
            **kwargs
        )
