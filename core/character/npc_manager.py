#!/usr/bin/env python3
"""
NPC Manager for tracking and persisting NPCs in the game world.
Implements the just-in-time generation of NPC stats based on context.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Union, Set
from datetime import datetime

from core.character.npc_base import NPC, NPCType, NPCRelationship, NPCInteractionType, NPCMemory
from core.character.npc_generator import NPCGenerator
from core.stats.stats_base import StatType, DerivedStatType
from core.utils.dotdict import DotDict

logger = logging.getLogger(__name__)


class NPCManager:
    """
    Manager for tracking and persisting NPCs in the game world.
    Implements just-in-time generation of NPC stats based on interaction context.
    """
    
    def __init__(self, save_directory: str = "saves/npcs"):
        """
        Initialize the NPC manager.
        
        Args:
            save_directory: Directory to save NPC data
        """
        self.save_directory = save_directory
        self.npcs: Dict[str, NPC] = {}  # Dictionary of NPCs by ID
        self.npcs_by_name: Dict[str, NPC] = {}  # Dictionary of NPCs by name (lowercase)
        self.npcs_by_location: Dict[str, List[NPC]] = {}  # Dictionary of NPCs by location
        self.npc_generator = NPCGenerator()
        
        # Ensure save directory exists
        os.makedirs(save_directory, exist_ok=True)
    
    def add_npc(self, npc: NPC) -> None:
        """
        Add an NPC to the manager.
        
        Args:
            npc: The NPC to add
        """
        # Add to ID index
        self.npcs[npc.id] = npc
        
        # Add to name index
        name_key = npc.name.lower()
        self.npcs_by_name[name_key] = npc
        
        # Add to location index if location is set
        if npc.location:
            location_key = npc.location.lower()
            if location_key not in self.npcs_by_location:
                self.npcs_by_location[location_key] = []
            
            # Avoid duplicates
            if npc not in self.npcs_by_location[location_key]:
                self.npcs_by_location[location_key].append(npc)
        
        logger.debug(f"Added NPC to manager: {npc.name} (ID: {npc.id})")
    
    def remove_npc(self, npc_id: str) -> bool:
        """
        Remove an NPC from the manager.
        
        Args:
            npc_id: ID of the NPC to remove
            
        Returns:
            True if the NPC was found and removed, False otherwise
        """
        if npc_id not in self.npcs:
            return False
        
        npc = self.npcs[npc_id]
        
        # Remove from ID index
        del self.npcs[npc_id]
        
        # Remove from name index
        name_key = npc.name.lower()
        if name_key in self.npcs_by_name and self.npcs_by_name[name_key].id == npc_id:
            del self.npcs_by_name[name_key]
        
        # Remove from location index
        if npc.location:
            location_key = npc.location.lower()
            if location_key in self.npcs_by_location:
                self.npcs_by_location[location_key] = [
                    n for n in self.npcs_by_location[location_key] if n.id != npc_id
                ]
                if not self.npcs_by_location[location_key]:
                    del self.npcs_by_location[location_key]
        
        logger.debug(f"Removed NPC from manager: {npc.name} (ID: {npc_id})")
        return True
    
    def get_npc_by_id(self, npc_id: str) -> Optional[NPC]:
        """
        Get an NPC by ID.
        
        Args:
            npc_id: ID of the NPC to get
            
        Returns:
            The NPC if found, None otherwise
        """
        return self.npcs.get(npc_id)
        
    def get_entity(self, entity_id: str) -> Optional[NPC]:
        """
        Get an entity (NPC) by ID.
        Alias for get_npc_by_id to maintain compatibility with EntityManager interface.
        
        Args:
            entity_id: ID of the entity to get
            
        Returns:
            The entity if found, None otherwise
        """
        return self.get_npc_by_id(entity_id)
    
    def get_npc_by_name(self, name: str) -> Optional[NPC]:
        """
        Get an NPC by name (case-insensitive).
        
        Args:
            name: Name of the NPC to get
            
        Returns:
            The NPC if found, None otherwise
        """
        return self.npcs_by_name.get(name.lower())
    
    def get_npcs_by_location(self, location: str) -> List[NPC]:
        """
        Get all NPCs at a specific location.
        
        Args:
            location: The location to check
            
        Returns:
            List of NPCs at the location (empty if none)
        """
        return self.npcs_by_location.get(location.lower(), [])
    
    def get_npcs_by_type(self, npc_type: NPCType) -> List[NPC]:
        """
        Get all NPCs of a specific type.
        
        Args:
            npc_type: The type of NPCs to get
            
        Returns:
            List of NPCs of the specified type
        """
        return [npc for npc in self.npcs.values() if npc.npc_type == npc_type]
    
    def get_npcs_by_relationship(self, relationship: NPCRelationship) -> List[NPC]:
        """
        Get all NPCs with a specific relationship to the player.
        
        Args:
            relationship: The relationship to filter by
            
        Returns:
            List of NPCs with the specified relationship
        """
        return [npc for npc in self.npcs.values() if npc.relationship == relationship]
    
    def update_npc_location(self, npc_id: str, new_location: str) -> bool:
        """
        Update an NPC's location.
        
        Args:
            npc_id: ID of the NPC to update
            new_location: New location for the NPC
            
        Returns:
            True if the NPC was found and updated, False otherwise
        """
        npc = self.get_npc_by_id(npc_id)
        if not npc:
            return False
        
        # Remove from old location index
        if npc.location:
            old_location_key = npc.location.lower()
            if old_location_key in self.npcs_by_location:
                self.npcs_by_location[old_location_key] = [
                    n for n in self.npcs_by_location[old_location_key] if n.id != npc_id
                ]
                if not self.npcs_by_location[old_location_key]:
                    del self.npcs_by_location[old_location_key]
        
        # Update NPC's location
        npc.location = new_location
        
        # Add to new location index
        if new_location:
            new_location_key = new_location.lower()
            if new_location_key not in self.npcs_by_location:
                self.npcs_by_location[new_location_key] = []
            self.npcs_by_location[new_location_key].append(npc)
        
        logger.debug(f"Updated location for NPC {npc.name} to {new_location}")
        return True
    
    def update_npc_relationship(self, npc_id: str, new_relationship: NPCRelationship) -> bool:
        """
        Update an NPC's relationship with the player.
        
        Args:
            npc_id: ID of the NPC to update
            new_relationship: New relationship for the NPC
            
        Returns:
            True if the NPC was found and updated, False otherwise
        """
        npc = self.get_npc_by_id(npc_id)
        if not npc:
            return False
        
        npc.update_relationship(new_relationship)
        return True
    
    def clear_all(self) -> None:
        """Clear all NPCs from the manager."""
        self.npcs.clear()
        self.npcs_by_name.clear()
        self.npcs_by_location.clear()
        logger.info("Cleared all NPCs from manager")


# Singleton instance for NPC manager
_npc_manager_instance = None

# Convenience function to get the NPC manager
def get_npc_manager() -> NPCManager:
    """Get the NPC manager instance."""
    global _npc_manager_instance
    if _npc_manager_instance is None:
        _npc_manager_instance = NPCManager()
    
    return _npc_manager_instance
