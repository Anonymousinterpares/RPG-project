#!/usr/bin/env python3
"""
NPC Memory module for tracking interactions and NPC memory management.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta

from core.character.npc_base import NPC, NPCType, NPCRelationship, NPCInteractionType, NPCMemory
from core.character.npc_manager import NPCManager

logger = logging.getLogger(__name__)


class NPCMemoryManager:
    """
    Manager for tracking NPC memories and interactions.
    Handles recording, retrieving, and managing NPC memories.
    """
    
    def __init__(self, npc_manager: NPCManager):
        """
        Initialize the NPC memory manager.
        
        Args:
            npc_manager: The NPCManager instance to use
        """
        self.npc_manager = npc_manager
    
    def record_interaction(self, 
                          npc_id: str, 
                          interaction_type: NPCInteractionType,
                          description: str,
                          location: Optional[str] = None,
                          player_action: Optional[str] = None,
                          npc_reaction: Optional[str] = None,
                          relationship_change: Optional[NPCRelationship] = None,
                          importance: int = 1) -> Optional[NPCMemory]:
        """
        Record an interaction with an NPC.
        
        Args:
            npc_id: ID of the NPC
            interaction_type: Type of interaction
            description: Brief description of the interaction
            location: Where the interaction took place
            player_action: What the player did
            npc_reaction: How the NPC reacted
            relationship_change: Whether the relationship changed
            importance: Importance of the memory (1-10)
            
        Returns:
            The created memory if successful, None otherwise
        """
        npc = self.npc_manager.get_npc_by_id(npc_id)
        if not npc:
            logger.warning(f"Cannot record interaction: NPC with ID {npc_id} not found")
            return None
        
        # Create the memory
        memory = NPCMemory(
            npc_id=npc_id,
            timestamp=datetime.now(),
            interaction_type=interaction_type,
            description=description,
            location=location,
            player_action=player_action,
            npc_reaction=npc_reaction,
            relationship_change=relationship_change,
            importance=importance
        )
        
        # Add the memory to the NPC
        npc.record_interaction(memory)
        
        # Update NPC information based on the interaction
        if location and not npc.location:
            npc.location = location
        
        if relationship_change:
            npc.update_relationship(relationship_change)
        
        logger.debug(f"Recorded interaction with NPC {npc.name}: {description}")
        return memory
    
    def get_recent_memories(self, 
                           npc_id: str, 
                           count: int = 5, 
                           interaction_type: Optional[NPCInteractionType] = None) -> List[NPCMemory]:
        """
        Get the most recent memories for an NPC.
        
        Args:
            npc_id: ID of the NPC
            count: Maximum number of memories to return
            interaction_type: Optional filter by interaction type
            
        Returns:
            List of recent memories
        """
        npc = self.npc_manager.get_npc_by_id(npc_id)
        if not npc:
            logger.warning(f"Cannot get memories: NPC with ID {npc_id} not found")
            return []
        
        # Filter and sort memories
        if interaction_type:
            filtered_memories = [m for m in npc.memories if m.interaction_type == interaction_type]
        else:
            filtered_memories = npc.memories
        
        # Sort by timestamp (newest first)
        sorted_memories = sorted(filtered_memories, key=lambda m: m.timestamp, reverse=True)
        
        # Return the requested number of memories
        return sorted_memories[:count]
    
    def get_important_memories(self, 
                              npc_id: str, 
                              min_importance: int = 5) -> List[NPCMemory]:
        """
        Get important memories for an NPC.
        
        Args:
            npc_id: ID of the NPC
            min_importance: Minimum importance level (1-10)
            
        Returns:
            List of important memories
        """
        npc = self.npc_manager.get_npc_by_id(npc_id)
        if not npc:
            logger.warning(f"Cannot get memories: NPC with ID {npc_id} not found")
            return []
        
        # Filter by importance
        important_memories = [m for m in npc.memories if m.importance >= min_importance]
        
        # Sort by importance (highest first) and then by recency
        sorted_memories = sorted(
            important_memories, 
            key=lambda m: (m.importance, m.timestamp),
            reverse=True
        )
        
        return sorted_memories
    
    def get_memories_by_location(self, 
                                location: str,
                                max_count: int = 10) -> List[Tuple[NPC, NPCMemory]]:
        """
        Get memories that occurred at a specific location.
        
        Args:
            location: The location to check
            max_count: Maximum number of memories to return
            
        Returns:
            List of (NPC, memory) tuples
        """
        memories_at_location = []
        
        # Check all NPCs
        for npc in self.npc_manager.npcs.values():
            # Find memories at this location
            location_memories = [m for m in npc.memories if m.location and m.location.lower() == location.lower()]
            
            # Add them to the result list
            for memory in location_memories:
                memories_at_location.append((npc, memory))
        
        # Sort by timestamp (newest first)
        sorted_memories = sorted(memories_at_location, key=lambda nm: nm[1].timestamp, reverse=True)
        
        return sorted_memories[:max_count]
    
    def get_relationship_change_memories(self, 
                                        npc_id: str) -> List[NPCMemory]:
        """
        Get memories where the relationship with the player changed.
        
        Args:
            npc_id: ID of the NPC
            
        Returns:
            List of relationship change memories
        """
        npc = self.npc_manager.get_npc_by_id(npc_id)
        if not npc:
            logger.warning(f"Cannot get memories: NPC with ID {npc_id} not found")
            return []
        
        # Filter by relationship change
        return [m for m in npc.memories if m.relationship_change is not None]
    
    def summarize_npc_interactions(self, npc_id: str) -> Dict[str, Any]:
        """
        Create a summary of interactions with an NPC.
        
        Args:
            npc_id: ID of the NPC
            
        Returns:
            Dictionary with interaction summary
        """
        npc = self.npc_manager.get_npc_by_id(npc_id)
        if not npc:
            logger.warning(f"Cannot summarize interactions: NPC with ID {npc_id} not found")
            return {}
        
        # Count interactions by type
        interaction_counts = {}
        for memory in npc.memories:
            interaction_type = memory.interaction_type.name
            if interaction_type not in interaction_counts:
                interaction_counts[interaction_type] = 0
            interaction_counts[interaction_type] += 1
        
        # Find most recent interaction
        most_recent = None
        if npc.memories:
            most_recent = max(npc.memories, key=lambda m: m.timestamp)
        
        # Find most important memory
        most_important = None
        if npc.memories:
            most_important = max(npc.memories, key=lambda m: m.importance)
        
        # Create the summary
        summary = {
            "npc_name": npc.name,
            "npc_id": npc.id,
            "total_interactions": len(npc.memories),
            "interaction_counts": interaction_counts,
            "current_relationship": npc.relationship.name,
            "first_interaction": npc.memories[0].timestamp.isoformat() if npc.memories else None,
            "last_interaction": npc.last_interaction.isoformat() if npc.last_interaction else None,
            "most_recent_interaction": {
                "description": most_recent.description,
                "timestamp": most_recent.timestamp.isoformat(),
                "type": most_recent.interaction_type.name
            } if most_recent else None,
            "most_important_memory": {
                "description": most_important.description,
                "importance": most_important.importance,
                "type": most_important.interaction_type.name
            } if most_important else None
        }
        
        return summary
    
    def get_relevant_context_for_interaction(self, 
                                           npc_id: str, 
                                           interaction_type: NPCInteractionType,
                                           max_memories: int = 3) -> List[Dict[str, Any]]:
        """
        Get relevant memories as context for a new interaction.
        This is the primary method for integrating NPCs with the context system.
        
        Args:
            npc_id: ID of the NPC
            interaction_type: Type of the upcoming interaction
            max_memories: Maximum number of memories to include
            
        Returns:
            List of memory dictionaries formatted for context
        """
        npc = self.npc_manager.get_npc_by_id(npc_id)
        if not npc:
            logger.warning(f"Cannot get context: NPC with ID {npc_id} not found")
            return []
        
        # Start with basic NPC information
        context = []
        
        # First, get the most recent memory of the same interaction type
        same_type_memories = [m for m in npc.memories if m.interaction_type == interaction_type]
        if same_type_memories:
            most_recent_same_type = max(same_type_memories, key=lambda m: m.timestamp)
            context.append({
                "type": "recent_similar_interaction",
                "description": most_recent_same_type.description,
                "when": most_recent_same_type.timestamp.isoformat()
            })
        
        # Next, get the most recent interaction (if different from above)
        if npc.memories:
            most_recent = max(npc.memories, key=lambda m: m.timestamp)
            if not same_type_memories or most_recent.id != most_recent_same_type.id:
                context.append({
                    "type": "most_recent_interaction",
                    "description": most_recent.description,
                    "when": most_recent.timestamp.isoformat()
                })
        
        # Finally, get the most important memories
        important_memories = self.get_important_memories(npc_id, min_importance=7)
        for memory in important_memories[:max(0, max_memories - len(context))]:
            context.append({
                "type": "important_memory",
                "description": memory.description,
                "importance": memory.importance,
                "when": memory.timestamp.isoformat()
            })
        
        return context
    
    def prune_old_memories(self, 
                          npc_id: str, 
                          max_age_days: int = 90, 
                          keep_important: bool = True,
                          min_importance_to_keep: int = 5) -> int:
        """
        Remove old, less important memories to prevent memory bloat.
        
        Args:
            npc_id: ID of the NPC
            max_age_days: Maximum age of memories to keep
            keep_important: Whether to keep important memories regardless of age
            min_importance_to_keep: Minimum importance level to keep regardless of age
            
        Returns:
            Number of memories removed
        """
        npc = self.npc_manager.get_npc_by_id(npc_id)
        if not npc:
            logger.warning(f"Cannot prune memories: NPC with ID {npc_id} not found")
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        original_count = len(npc.memories)
        
        # Filter memories
        if keep_important:
            npc.memories = [
                m for m in npc.memories if 
                m.timestamp >= cutoff_date or m.importance >= min_importance_to_keep
            ]
        else:
            npc.memories = [m for m in npc.memories if m.timestamp >= cutoff_date]
        
        removed_count = original_count - len(npc.memories)
        logger.debug(f"Pruned {removed_count} old memories from NPC {npc.name}")
        
        return removed_count
