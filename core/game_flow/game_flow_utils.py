#!/usr/bin/env python3
"""
Utility functions for game flow modules.
"""

import logging
from typing import Optional, Any

from core.base.state import GameState
from core.interaction.enums import InteractionMode
from core.character.npc_base import NPC # Moved from local import

# Get the module logger
logger = logging.getLogger("GAME_FLOW_UTILS")

def get_participant_by_id(game_state: 'GameState', entity_id: str, try_fuzzy_match: bool = True) -> Optional[Any]: # Use Any for broader compatibility
    """Helper to find a participant (player or NPC/CombatEntity) by ID.
    
    Args:
        game_state: The current game state
        entity_id: The ID or name of the entity to find
        try_fuzzy_match: If True, attempt fuzzy matching if exact match fails
    
    Returns:
        The found entity or None if not found
    """
    logger.debug(f"Attempting to find participant with ID: {entity_id}")

    # Check for special case 'player' id string
    if entity_id == 'player' and game_state.player:
        logger.debug(f"Found participant '{entity_id}' as player")
        return game_state.player

    # Check if it matches player's actual ID
    if game_state.player and getattr(game_state.player, 'id', None) == entity_id:
        logger.debug(f"Found participant '{entity_id}' matching player ID")
        return game_state.player
    
    # Check if it matches player's name (case insensitive)
    player_name = getattr(game_state.player, 'name', '')
    if player_name and player_name.lower() == entity_id.lower():
        logger.debug(f"Found participant '{entity_id}' matching player name")
        return game_state.player

    # Check combat manager entities first if in combat
    if game_state.current_mode == InteractionMode.COMBAT and game_state.combat_manager:
        try:
            # Try exact match first
            participant = game_state.combat_manager.get_entity_by_id(entity_id)
            if participant:
                logger.debug(f"Found entity {entity_id} in combat manager")
                return participant
            
            # Try to match by name if exact ID match failed
            for eid, entity in game_state.combat_manager.entities.items():
                entity_name = getattr(entity, 'name', '')
                if entity_name and entity_name.lower() == entity_id.lower():
                    logger.debug(f"Found entity with name '{entity_id}' in combat manager (ID: {eid})")
                    return entity
        except Exception as e:
            logger.error(f"Error getting entity from combat manager: {e}")
            # Continue to other lookup methods if this fails

    # Check current location for NPCs by ID
    current_location = None
    if hasattr(game_state, 'player') and hasattr(game_state.player, 'current_location'):
        current_location = game_state.player.current_location
    
    if current_location and hasattr(game_state, 'world') and hasattr(game_state.world, 'get_location'):
        try:
            location = game_state.world.get_location(current_location)
            if location and hasattr(location, 'npcs') and location.npcs:
                # Try exact match on ID first
                for npc in location.npcs:
                    if getattr(npc, 'id', '') == entity_id:
                        logger.debug(f"Found NPC '{entity_id}' in current location")
                        return npc
                    
                # Try name match
                for npc in location.npcs:
                    if getattr(npc, 'name', '').lower() == entity_id.lower():
                        logger.debug(f"Found NPC with name '{entity_id}' in current location")
                        return npc
        except Exception as e:
            logger.error(f"Error getting NPCs from current location: {e}")

    # Check current_combatants (used for social conflict)
    if hasattr(game_state, 'current_combatants') and entity_id in game_state.current_combatants:
         # Need a way to get the actual NPC/Player object from the ID
         if game_state.player and getattr(game_state.player, 'id', None) == entity_id:
             logger.debug(f"Found participant '{entity_id}' in current_combatants (matches player ID)")
             return game_state.player
         # Option 2: Check NPC manager/system
         if hasattr(game_state, 'npc_system') and game_state.npc_system:
             if hasattr(game_state.npc_system, 'get_npc_by_id'):
                 npc = game_state.npc_system.get_npc_by_id(entity_id)
                 if npc:
                     logger.debug(f"Found participant '{entity_id}' in current_combatants (via NPC system)")
                     return npc
             # Try to find by name if get_npc_by_id exists
             if hasattr(game_state.npc_system, 'get_npcs') and try_fuzzy_match:
                 try:
                     all_npcs = game_state.npc_system.get_npcs()
                     for npc in all_npcs:
                         if getattr(npc, 'name', '').lower() == entity_id.lower():
                             logger.debug(f"Found NPC with name '{entity_id}' via NPC system")
                             return npc
                 except Exception as e:
                     logger.error(f"Error getting NPCs from NPC system: {e}")
         # Option 3: Check entity manager (if it holds NPCs)
         if hasattr(game_state, 'entity_manager') and game_state.entity_manager and hasattr(game_state.entity_manager, 'get_entity_by_id'):
              entity = game_state.entity_manager.get_entity_by_id(entity_id)
              # Check if the entity is compatible (e.g., is an NPC or Player)
              if isinstance(entity, NPC) or hasattr(entity, 'entity_type'): # Or a common base class
                  logger.debug(f"Found participant '{entity_id}' in current_combatants (via entity manager)")
                  return entity

    # Fallback: Check world NPCs
    if game_state.world:
        # Check if get_npc_by_id method exists for exact ID match
        if hasattr(game_state.world, 'get_npc_by_id'):
            npc = game_state.world.get_npc_by_id(entity_id)
            if npc:
                logger.debug(f"Found participant '{entity_id}' in world NPCs")
                return npc
        
        # Try to match by name if we have access to all NPCs
        if try_fuzzy_match and hasattr(game_state.world, 'get_all_npcs'):
            try:
                all_npcs = game_state.world.get_all_npcs()
                for npc in all_npcs:
                    if getattr(npc, 'name', '').lower() == entity_id.lower():
                        logger.debug(f"Found NPC with name '{entity_id}' via world.get_all_npcs")
                        return npc
            except Exception as e:
                logger.error(f"Error accessing all NPCs: {e}")

    # If NPC system exists, try to get all NPCs and match by name
    if try_fuzzy_match and hasattr(game_state, 'npc_system') and game_state.npc_system:
        if hasattr(game_state.npc_system, 'get_npcs'):
            try:
                all_npcs = game_state.npc_system.get_npcs()
                for npc in all_npcs:
                    npc_name = getattr(npc, 'name', '')
                    if npc_name and npc_name.lower() == entity_id.lower():
                        logger.debug(f"Found NPC with name '{entity_id}' via npc_system.get_npcs")
                        return npc
            except Exception as e:
                logger.error(f"Error getting NPCs from NPC system: {e}")

    logger.warning(f"Could not find participant with ID or name: {entity_id} in current context.")
    return None