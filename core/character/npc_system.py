#!/usr/bin/env python3
"""
NPC System - Main integration module for the NPC subsystem.
Provides a unified interface for NPC management, creation, persistence, and memory.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from datetime import datetime

from core.character.npc_base import NPC, NPCType, NPCRelationship, NPCInteractionType, NPCMemory
from core.character.npc_manager import NPCManager
from core.character.npc_creator import NPCCreator
from core.character.npc_persistence import NPCPersistence
from core.character.npc_memory import NPCMemoryManager

logger = logging.getLogger(__name__)


class NPCSystem:
    """
    Main class for the NPC subsystem.
    Integrates NPC management, creation, persistence, and memory into a single interface.
    """
    
    def __init__(self, save_directory: str = "saves/npcs"):
        """
        Initialize the NPC system.
        
        Args:
            save_directory: Directory for saving NPC data
        """
        # Initialize storage for direct access fallbacks
        self.npcs: Dict[str, NPC] = {}
        self.npc_list: List[NPC] = []
        
        # Initialize all the component managers
        self.manager = NPCManager(save_directory)
        self.creator = NPCCreator(self.manager)
        self.persistence = NPCPersistence(self.manager)
        self.memory = NPCMemoryManager(self.manager)
        
        logger.info("NPC system initialized")
    
    def load_all_npcs(self) -> int:
        """
        Load all persisted NPCs.
        
        Returns:
            Number of NPCs loaded
        """
        return self.persistence.load_all_npcs()
    
    def save_all_npcs(self) -> Tuple[int, int]:
        """
        Save all persistent NPCs.
        
        Returns:
            Tuple of (success_count, total_count)
        """
        return self.persistence.save_all_persistent_npcs()
    
    def clear_all_npcs(self) -> None:
        """Clear all NPCs from the system."""
        self.manager.clear_all()
        self.npcs.clear()
        self.npc_list.clear()
    
    def get_npc(self, npc_id: str) -> Optional[NPC]:
        """
        Get an NPC by ID.
        
        Args:
            npc_id: ID of the NPC to get
            
        Returns:
            The NPC if found, None otherwise
        """
        return self.manager.get_npc_by_id(npc_id)
    
    def get_npc_by_name(self, name: str) -> Optional[NPC]:
        """
        Get an NPC by name.
        
        Args:
            name: Name of the NPC to get
            
        Returns:
            The NPC if found, None otherwise
        """
        return self.manager.get_npc_by_name(name)
    
    def get_or_create_npc(self, 
                         name: str, 
                         interaction_type: NPCInteractionType,
                         location: Optional[str] = None,
                         npc_subtype: Optional[str] = None) -> Tuple[NPC, bool]:
        """
        Get an existing NPC by name or create a new one.
        This is the primary method for just-in-time NPC generation.
        
        Args:
            name: Name of the NPC
            interaction_type: Type of interaction
            location: Where the NPC is located
            npc_subtype: Optional subtype (e.g., 'boss_dragon', 'merchant')
            
        Returns:
            Tuple of (npc, is_new) where is_new is True if a new NPC was created
        """
        npc, is_new = self.creator.get_or_create_npc(
            name=name,
            interaction_type=interaction_type,
            location=location,
            npc_subtype=npc_subtype
        )
        # Register in direct storage if newly created
        if npc and is_new:
            self.register_npc(npc)
        return npc, is_new
    
    def prepare_npc_for_interaction(self, 
                                   npc_or_name: Union[NPC, str],
                                   interaction_type: NPCInteractionType,
                                   npc_subtype: Optional[str] = None) -> Optional[NPC]:
        """
        Prepare an NPC for a specific interaction, enhancing it if necessary.
        Implements the just-in-time generation of NPC capabilities.
        
        Args:
            npc_or_name: NPC object or name of the NPC
            interaction_type: Type of interaction to prepare for
            npc_subtype: Optional subtype for new NPCs
            
        Returns:
            The prepared NPC if found or created, None on failure
        """
        # Get or create the NPC
        if isinstance(npc_or_name, str):
            npc, _ = self.get_or_create_npc(npc_or_name, interaction_type, npc_subtype=npc_subtype)
            if not npc:
                return None
        else:
            npc = npc_or_name
            
        # Enhance the NPC for this interaction if needed
        self.creator.enhance_npc_for_interaction(npc, interaction_type)
        
        return npc
    
    def record_interaction(self,
                          npc_or_name: Union[NPC, str],
                          interaction_type: NPCInteractionType,
                          description: str,
                          location: Optional[str] = None,
                          importance: int = 3,
                          npc_subtype: Optional[str] = None) -> Optional[NPCMemory]:
        """
        Record an interaction with an NPC.
        Creates the NPC if it doesn't exist.
        
        Args:
            npc_or_name: NPC object or name of the NPC
            interaction_type: Type of interaction
            description: Description of what happened
            location: Where it happened
            importance: How important this memory is (1-10)
            npc_subtype: Optional subtype for new NPCs
            
        Returns:
            The created memory if successful, None otherwise
        """
        # Get or create the NPC
        if isinstance(npc_or_name, str):
            npc, _ = self.get_or_create_npc(npc_or_name, interaction_type, location, npc_subtype=npc_subtype)
            if not npc:
                return None
        else:
            npc = npc_or_name
        
        # Record the interaction
        return self.memory.record_interaction(
            npc_id=npc.id,
            interaction_type=interaction_type,
            description=description,
            location=location,
            importance=importance
        )
    
    def get_context_for_interaction(self,
                                   npc_or_name: Union[NPC, str],
                                   interaction_type: NPCInteractionType,
                                   npc_subtype: Optional[str] = None) -> Dict[str, Any]:
        """
        Get context for an interaction with an NPC.
        Creates or enhances the NPC as needed.
        
        Args:
            npc_or_name: NPC object or name of the NPC
            interaction_type: Type of interaction
            npc_subtype: Optional subtype for new NPCs
            
        Returns:
            Dictionary with NPC information and relevant memories
        """
        # Prepare the NPC
        npc = self.prepare_npc_for_interaction(npc_or_name, interaction_type, npc_subtype)
        if not npc:
            return {"error": "NPC not found or could not be created"}
        
        # Get relevant memories
        memories = self.memory.get_relevant_context_for_interaction(npc.id, interaction_type)
        
        # Build the context
        context = {
            "npc": {
                "id": npc.id,
                "name": npc.name,
                "type": npc.npc_type.name,
                "relationship": npc.relationship.name,
                "description": npc.description,
                "occupation": npc.occupation,
                "location": npc.location,
                "personality": npc.personality
            },
            "stats": {},
            "memories": memories,
            "interaction_count": npc.interaction_count
        }
        
        # Add stats if available
        if npc.has_stats():
            # Only include stats relevant to this interaction type
            if interaction_type == NPCInteractionType.COMBAT:
                combat_stats = ["STR", "DEX", "CON", "MELEE_ATTACK", "RANGED_ATTACK", "DEFENSE"]
                for stat in combat_stats:
                    value = npc.get_stat(stat)
                    if value is not None:
                        context["stats"][stat] = value
            
            elif interaction_type == NPCInteractionType.SOCIAL:
                social_stats = ["CHA", "WIS"]
                for stat in social_stats:
                    value = npc.get_stat(stat)
                    if value is not None:
                        context["stats"][stat] = value
            
            elif interaction_type == NPCInteractionType.COMMERCE:
                commerce_stats = ["CHA", "INT"]
                for stat in commerce_stats:
                    value = npc.get_stat(stat)
                    if value is not None:
                        context["stats"][stat] = value
        
        return context
    
    def create_enemy_for_combat(self,
                               name: Optional[str] = None,
                               enemy_type: str = "bandit",
                               level: int = 1,
                               location: Optional[str] = None) -> NPC:
        """
        Create an enemy NPC ready for combat.
        
        Args:
            name: Optional name for the enemy
            enemy_type: Type of enemy
            level: Enemy level
            location: Where the enemy is located
            
        Returns:
            The created enemy NPC
        """
        npc = self.creator.create_enemy(
            name=name,
            enemy_type=enemy_type,
            level=level,
            location=location
        )
        # Register in direct storage for fallback access
        if npc:
            self.register_npc(npc)
        return npc
    
    def create_merchant(self,
                       name: str,
                       shop_type: str = "general",
                       location: Optional[str] = None) -> NPC:
        """
        Create a merchant NPC.
        
        Args:
            name: Name of the merchant
            shop_type: Type of shop
            location: Where the merchant is located
            
        Returns:
            The created merchant NPC
        """
        return self.creator.create_merchant(
            name=name,
            shop_type=shop_type,
            location=location
        )
    
    def update_npc_location(self, npc_id: str, new_location: str) -> bool:
        """
        Update an NPC's location.
        
        Args:
            npc_id: ID of the NPC
            new_location: New location
            
        Returns:
            True if successful, False otherwise
        """
        return self.manager.update_npc_location(npc_id, new_location)
    
    def update_npc_relationship(self, npc_id: str, new_relationship: NPCRelationship) -> bool:
        """
        Update an NPC's relationship with the player.
        
        Args:
            npc_id: ID of the NPC
            new_relationship: New relationship
            
        Returns:
            True if successful, False otherwise
        """
        return self.manager.update_npc_relationship(npc_id, new_relationship)
    
    def save_state(self) -> bool:
        """
        Save the entire NPC system state.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Save all persistent NPCs
            self.save_all_npcs()
            return True
        except Exception as e:
            logger.error(f"Error saving NPC system state: {e}")
            return False
    
    def load_state(self) -> bool:
        """
        Load the entire NPC system state.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear existing NPCs
            self.clear_all_npcs()
            
            # Load all NPCs
            self.load_all_npcs()
            return True
        except Exception as e:
            logger.error(f"Error loading NPC system state: {e}")
            return False

    def register_npc(self, npc: NPC) -> None:
        """Register an NPC in the direct storage for fallback access.
        
        Args:
            npc: The NPC to register
        """
        if npc and hasattr(npc, 'id') and npc.id:
            self.npcs[npc.id] = npc
            if npc not in self.npc_list:
                self.npc_list.append(npc)
            logger.debug(f"Registered NPC {npc.name} (ID: {npc.id}) in direct storage.")
    
    def get_npc_by_id(self, npc_id: str) -> Optional[NPC]:
        """Retrieves an NPC instance by its unique ID.

        Args:
            npc_id: The unique identifier of the NPC to retrieve.

        Returns:
            The NPC object if found, otherwise None.
        """
        # First try the main manager
        npc = self.manager.get_npc_by_id(npc_id)
        if npc:
            return npc
        
        # Fallback to direct storage
        if npc_id in self.npcs:
            return self.npcs[npc_id]
        
        # Fallback to list search
        for npc in self.npc_list:
            if getattr(npc, 'id', None) == npc_id:
                return npc
        
        logger.debug(f"NPC with ID {npc_id} not found in NPCSystem storage.")
        return None