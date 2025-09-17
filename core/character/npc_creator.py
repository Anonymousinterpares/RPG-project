#!/usr/bin/env python3
"""
NPC Creator module focused on creating and generating NPCs for various interactions.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from core.character.npc_base import NPC, NPCType, NPCRelationship, NPCInteractionType, NPCMemory
from core.character.npc_generator import NPCGenerator
from core.character.npc_manager import NPCManager

logger = logging.getLogger(__name__)


class NPCCreator:
    """
    Class for handling NPC creation operations.
    Contains methods for creating different types of NPCs and enhancing existing ones.
    """
    
    def __init__(self, npc_manager: NPCManager):
        """
        Initialize the NPC creator.
        
        Args:
            npc_manager: The NPCManager instance to use
        """
        self.npc_manager = npc_manager
        self.npc_generator = npc_manager.npc_generator
    
    def create_npc(self, 
                  interaction_type: NPCInteractionType,
                  name: Optional[str] = None,
                  npc_type: Optional[NPCType] = None,
                  npc_subtype: Optional[str] = None,
                  relationship: NPCRelationship = NPCRelationship.NEUTRAL,
                  location: Optional[str] = None,
                  description: Optional[str] = None,
                  occupation: Optional[str] = None,
                  is_persistent: bool = False) -> NPC:
        """
        Create a new NPC and add it to the manager.
        
        Args:
            interaction_type: The type of interaction this NPC is for
            name: Optional name for the NPC (generated if None)
            npc_type: Type of NPC (determined from interaction if None)
            relationship: Initial relationship with the player
            location: Where the NPC is located
            description: Optional description of the NPC
            occupation: Optional occupation
            is_persistent: Whether this NPC should be saved persistently
            
        Returns:
            The newly created NPC
        """
        # Check if NPC with this name already exists
        if name and self.npc_manager.get_npc_by_name(name):
            logger.warning(f"NPC with name '{name}' already exists, checking compatibility")
            existing_npc = self.npc_manager.get_npc_by_name(name)
            
            # If it exists but has minimal stats and we need more, enhance it
            if existing_npc and not existing_npc.has_stats():
                self.enhance_npc_for_interaction(existing_npc, interaction_type)
                return existing_npc
            
            # Otherwise, append a number to make the name unique
            i = 2
            while self.npc_manager.get_npc_by_name(f"{name} {i}"):
                i += 1
            name = f"{name} {i}"
        
        # Generate the NPC
        npc = self.npc_generator.generate_npc_for_interaction(
            interaction_type=interaction_type,
            name=name,
            npc_type=npc_type,
            npc_subtype=npc_subtype,
            relationship=relationship,
            location=location,
            description=description,
            occupation=occupation,
            is_persistent=is_persistent
        )
        
        # Add to manager
        self.npc_manager.add_npc(npc)
        
        return npc
    
    def create_enemy(self, 
                    name: Optional[str] = None,
                    enemy_type: str = "generic",
                    level: int = 1,
                    location: Optional[str] = None) -> NPC:
        """
        Create a new enemy NPC for combat and add it to the manager.
        
        Args:
            name: Optional name for the enemy
            enemy_type: Type of enemy (e.g., "bandit", "wolf", "guard")
            level: Level of the enemy, affects stats
            location: Where the enemy is located
            
        Returns:
            The newly created enemy NPC
        """
        # Generate the enemy
        npc = self.npc_generator.generate_enemy_npc(
            name=name,
            enemy_type=enemy_type,
            level=level,
            location=location
        )
        
        # Add to manager
        self.npc_manager.add_npc(npc)
        
        return npc
    
    def create_merchant(self,
                       name: Optional[str] = None,
                       shop_type: str = "general",
                       location: Optional[str] = None,
                       description: Optional[str] = None) -> NPC:
        """
        Create a merchant NPC specialized for commerce interactions.
        
        Args:
            name: Optional name for the merchant
            shop_type: Type of shop (e.g., "general", "weapons", "potions")
            location: Where the merchant is located
            description: Optional description of the merchant
            
        Returns:
            The newly created merchant NPC
        """
        # Generate a merchant-focused description if none provided
        if not description and name:
            description = f"{name} is a {shop_type} merchant offering goods for sale."
        elif not description:
            description = f"A {shop_type} merchant offering goods for sale."
        
        # Create the merchant NPC
        return self.create_npc(
            interaction_type=NPCInteractionType.COMMERCE,
            name=name,
            npc_type=NPCType.MERCHANT,
            relationship=NPCRelationship.NEUTRAL,
            location=location,
            description=description,
            occupation=f"{shop_type.capitalize()} Merchant",
            is_persistent=True  # Merchants are typically persistent
        )
    
    def create_quest_giver(self,
                          name: Optional[str] = None,
                          quest_type: str = "general",
                          location: Optional[str] = None,
                          description: Optional[str] = None) -> NPC:
        """
        Create a quest giver NPC specialized for quest interactions.
        
        Args:
            name: Optional name for the quest giver
            quest_type: Type of quest (e.g., "fetch", "kill", "escort")
            location: Where the quest giver is located
            description: Optional description of the quest giver
            
        Returns:
            The newly created quest giver NPC
        """
        # Generate a quest-focused description if none provided
        if not description and name:
            description = f"{name} is looking for someone to help with a {quest_type} task."
        elif not description:
            description = f"Someone looking for help with a {quest_type} task."
        
        # Create the quest giver NPC
        return self.create_npc(
            interaction_type=NPCInteractionType.QUEST,
            name=name,
            npc_type=NPCType.QUEST_GIVER,
            relationship=NPCRelationship.NEUTRAL,
            location=location,
            description=description,
            is_persistent=True  # Quest givers are typically persistent
        )
    
    def create_service_npc(self,
                          name: Optional[str] = None,
                          service_type: str = "innkeeper",
                          location: Optional[str] = None,
                          description: Optional[str] = None) -> NPC:
        """
        Create a service NPC specialized for service interactions.
        
        Args:
            name: Optional name for the service provider
            service_type: Type of service (e.g., "innkeeper", "blacksmith", "healer")
            location: Where the service provider is located
            description: Optional description of the service provider
            
        Returns:
            The newly created service NPC
        """
        # Generate a service-focused description if none provided
        if not description and name:
            description = f"{name} is a {service_type} offering services."
        elif not description:
            description = f"A {service_type} offering services."
        
        # Create the service NPC
        return self.create_npc(
            interaction_type=NPCInteractionType.SERVICE,
            name=name,
            npc_type=NPCType.SERVICE,
            relationship=NPCRelationship.NEUTRAL,
            location=location,
            description=description,
            occupation=service_type.capitalize(),
            is_persistent=True  # Service NPCs are typically persistent
        )
    
    def enhance_npc_for_interaction(self, npc: NPC, interaction_type: NPCInteractionType) -> None:
        """
        Enhance an existing NPC with additional details for a new type of interaction.
        This implements the just-in-time generation approach for NPC stats.
        
        Args:
            npc: The NPC to enhance
            interaction_type: The interaction type to prepare for
        """
        # No need to enhance if the NPC already has stats
        if npc.has_stats() and interaction_type == NPCInteractionType.MINIMAL:
            return
        
        # Generate stats if needed
        if not npc.has_stats():
            logger.info(f"Generating stats for NPC {npc.name} for {interaction_type.name} interaction")
            self.npc_generator.enhance_npc_for_new_interaction(npc, interaction_type)
            return
        
        # For existing NPCs with stats, enhance them for the new interaction
        self.npc_generator.enhance_npc_for_new_interaction(npc, interaction_type)
        
        # Record this enhancement in NPC's logs
        if not npc.known_information:
            npc.known_information = {}
        
        if "interaction_history" not in npc.known_information:
            npc.known_information["interaction_history"] = []
        
        npc.known_information["interaction_history"].append({
            "type": interaction_type.name,
            "timestamp": str(datetime.now())
        })
        
        logger.info(f"Enhanced NPC {npc.name} for {interaction_type.name} interaction")
    
    def get_or_create_npc(self,
                         name: str,
                         interaction_type: NPCInteractionType,
                         location: Optional[str] = None,
                         description: Optional[str] = None,
                         npc_type: Optional[NPCType] = None,
                         npc_subtype: Optional[str] = None) -> Tuple[NPC, bool]:
        """
        Get an existing NPC by name or create a new one if not found.
        This is the primary method for implementing just-in-time NPC generation.
        
        Args:
            name: Name of the NPC to get or create
            interaction_type: The interaction type needed
            location: Optional location for new NPCs
            description: Optional description for new NPCs
            npc_type: Optional NPC type for new NPCs
            npc_subtype: Optional subtype (e.g., 'boss_dragon', 'merchant')
            
        Returns:
            Tuple of (NPC, was_created) where was_created is True if a new NPC was created
        """
        # Check if the NPC already exists
        existing_npc = self.npc_manager.get_npc_by_name(name)
        
        if existing_npc:
            # Enhance the NPC if necessary for the current interaction
            self.enhance_npc_for_interaction(existing_npc, interaction_type)
            return existing_npc, False
        
        # Create a new NPC
        new_npc = self.create_npc(
            interaction_type=interaction_type,
            name=name,
            npc_type=npc_type,
            npc_subtype=npc_subtype,
            location=location,
            description=description
        )
        
        return new_npc, True
