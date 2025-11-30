#!/usr/bin/env python3
"""
Base classes for NPC data structures and types.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
import uuid
from datetime import datetime

from core.inventory.equipment_manager import EquipmentManager
from core.stats.stats_base import StatType, DerivedStatType
from core.stats.stats_manager import StatsManager
from core.interaction.social_effects import StatusEffectData
from core.utils.logging_config import get_logger # Import StatusEffectData

logger = get_logger(__name__)


class NPCType(Enum):
    """Types of NPCs in the game world."""
    MERCHANT = auto()        # Shop owners, traders
    QUEST_GIVER = auto()     # NPCs who give quests
    ALLY = auto()            # Friendly NPCs who may aid the player
    ENEMY = auto()           # Hostile NPCs
    NEUTRAL = auto()         # NPCs with no particular alignment
    SERVICE = auto()         # Service providers (innkeepers, etc.)
    BACKGROUND = auto()      # Background NPCs with minimal interaction


class NPCRelationship(Enum):
    """Relationship states between NPCs and the player."""
    HOSTILE = auto()         # Attacks on sight
    UNFRIENDLY = auto()      # Dislikes player but won't attack
    NEUTRAL = auto()         # No particular feelings
    FRIENDLY = auto()        # Likes the player
    ALLY = auto()            # Will help the player
    FEAR = auto()            # Afraid of the player
    RESPECT = auto()         # Respects the player
    FAMILY = auto()          # Family relationship
    ROMANTIC = auto()        # Romantic interest
    UNKNOWN = auto()         # Relationship not yet established


class NPCInteractionType(Enum):
    """Types of interactions that require different NPC stats."""
    COMBAT = auto()          # Combat interactions (need full stats)
    SOCIAL = auto()          # Social interactions (focus on CHA, WIS)
    COMMERCE = auto()        # Trading interactions (focus on CHA)
    QUEST = auto()           # Quest-related interactions
    INFORMATION = auto()     # Information-gathering (focus on INT, WIS)
    SERVICE = auto()         # Service providing (focus on relevant skills)
    MINIMAL = auto()         # Minimal interaction (background characters)


@dataclass
class NPCMemory:
    """A memory of an interaction with an NPC."""
    npc_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    interaction_type: NPCInteractionType = NPCInteractionType.MINIMAL
    description: str = ""
    importance: int = 1  # 1-10 scale, higher is more important
    location: Optional[str] = None
    player_action: Optional[str] = None
    npc_reaction: Optional[str] = None
    relationship_change: Optional[NPCRelationship] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "npc_id": self.npc_id,
            "timestamp": self.timestamp.isoformat(),
            "interaction_type": self.interaction_type.name,
            "description": self.description,
            "importance": self.importance,
            "location": self.location,
            "player_action": self.player_action,
            "npc_reaction": self.npc_reaction,
            "relationship_change": self.relationship_change.name if self.relationship_change else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NPCMemory':
        """Create from dictionary after deserialization."""
        return cls(
            npc_id=data["npc_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            interaction_type=NPCInteractionType[data["interaction_type"]],
            description=data["description"],
            importance=data["importance"],
            location=data.get("location"),
            player_action=data.get("player_action"),
            npc_reaction=data.get("npc_reaction"),
            relationship_change=NPCRelationship[data["relationship_change"]] if data.get("relationship_change") else None
        )


@dataclass
class NPC:
    """Class representing an NPC in the game world."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Unknown NPC"
    npc_type: NPCType = NPCType.NEUTRAL
    relationship: NPCRelationship = NPCRelationship.NEUTRAL
    location: Optional[str] = None
    description: str = ""
    occupation: Optional[str] = None
    race: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    is_persistent: bool = False  # Should this NPC persist between sessions?
    last_interaction: Optional[datetime] = None
    interaction_count: int = 0
    stats_generated: bool = False
    stats_manager: Optional[StatsManager] = None
    equipment_manager: Optional['EquipmentManager'] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    goals: Optional[str] = None
    secrets: Optional[str] = None
    inventory: Optional[List[Dict[str, Any]]] = None
    known_information: Optional[Dict[str, Any]] = None
    dialog_history: List[Dict[str, Any]] = field(default_factory=list)
    memories: List[NPCMemory] = field(default_factory=list)
    current_resolve: float = 0.0 # Current social 'health'
    active_social_effects: List[StatusEffectData] = field(default_factory=list)

    def __post_init__(self):
        """Initialize any empty fields."""
        if self.inventory is None:
            self.inventory = []
        if self.known_information is None:
            self.known_information = {}

    def update_relationship(self, new_relationship: NPCRelationship) -> None:
        """Update the relationship between the NPC and the player."""
        old_relationship = self.relationship
        self.relationship = new_relationship
        logger.info(f"NPC {self.name}: Relationship changed from {old_relationship.name} to {new_relationship.name}")

    def record_interaction(self, memory: NPCMemory) -> None:
        """Record a new interaction with this NPC."""
        self.memories.append(memory)
        self.last_interaction = memory.timestamp
        self.interaction_count += 1
        logger.debug(f"Recorded interaction with NPC {self.name}: {memory.description}")

    def has_stats(self) -> bool:
        """Check if this NPC has stats generated."""
        return self.stats_generated and self.stats_manager is not None

    def get_stat(self, stat_type: Union[StatType, DerivedStatType, str]) -> Optional[float]:
        """Get a specific stat value if stats have been generated."""
        if not self.has_stats():
            return None

        try:
            return self.stats_manager.get_stat_value(stat_type)
        except ValueError:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "npc_type": self.npc_type.name,
            "relationship": self.relationship.name,
            "location": self.location,
            "description": self.description,
            "occupation": self.occupation,
            "race": self.race,
            "gender": self.gender,
            "age": self.age,
            "is_persistent": self.is_persistent,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "interaction_count": self.interaction_count,
            "stats_generated": self.stats_generated,
            "stats": self.stats_manager.to_dict() if self.has_stats() else None,
            "equipment": self.equipment_manager.to_dict() if hasattr(self, 'equipment_manager') and self.equipment_manager else None,
            "appearance": self.appearance,
            "personality": self.personality,
            "goals": self.goals,
            "secrets": self.secrets,
            "inventory": self.inventory,
            "known_information": self.known_information,
            "dialog_history": self.dialog_history,
            "memories": [memory.to_dict() for memory in self.memories],
            "current_resolve": self.current_resolve,
            "active_social_effects": [effect.to_dict() for effect in self.active_social_effects],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NPC':
        """Create from dictionary after deserialization."""
        npc = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Unknown NPC"),
            npc_type=NPCType[data.get("npc_type", "NEUTRAL")],
            relationship=NPCRelationship[data.get("relationship", "NEUTRAL")],
            location=data.get("location"),
            description=data.get("description", ""),
            occupation=data.get("occupation"),
            race=data.get("race"),
            gender=data.get("gender"),
            age=data.get("age"),
            is_persistent=data.get("is_persistent", False),
            interaction_count=data.get("interaction_count", 0),
            stats_generated=data.get("stats_generated", False),
            appearance=data.get("appearance"),
            personality=data.get("personality"),
            goals=data.get("goals"),
            secrets=data.get("secrets"),
            inventory=data.get("inventory", []),
            known_information=data.get("known_information", {}),
            dialog_history=data.get("dialog_history", [])
            # current_resolve and active_social_effects will be loaded below
        )

        # Load last_interaction
        if data.get("last_interaction"):
            npc.last_interaction = datetime.fromisoformat(data["last_interaction"])

        # Load stats if they exist
        if npc.stats_generated and data.get("stats"):
            npc.stats_manager = StatsManager.from_dict(data["stats"])

        # Load equipment if it exists
        if data.get("equipment"):
            from core.inventory.equipment_manager import EquipmentManager
            npc.equipment_manager = EquipmentManager.from_dict(data["equipment"])

        # Load memories
        if "memories" in data:
            npc.memories = [NPCMemory.from_dict(memory_data) for memory_data in data["memories"]]

        # Load current resolve and social effects
        npc.current_resolve = data.get("current_resolve", 0.0)
        if "active_social_effects" in data:
            npc.active_social_effects = [
                StatusEffectData.from_dict(effect_data)
                for effect_data in data["active_social_effects"]
            ]

        return npc
