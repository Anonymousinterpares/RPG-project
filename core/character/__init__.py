"""
Character-related modules for the RPG game.
"""

from typing import TYPE_CHECKING
from core.character.npc_base import NPC, NPCType, NPCRelationship, NPCInteractionType, NPCMemory

if TYPE_CHECKING:
    from core.character.npc_system import NPCSystem  # type: ignore

# Create alias for Character to NPC to fix import issues
Character = NPC

# Singleton instance for global access
_npc_system = None

def get_npc_system() -> 'NPCSystem':
    """
    Get the global NPC system instance.
    
    Returns:
        The global NPCSystem instance
    """
    global _npc_system
    if _npc_system is None:
        from core.character.npc_system import NPCSystem  # Local import to avoid circulars
        _npc_system = NPCSystem()
    return _npc_system
