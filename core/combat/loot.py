import logging
from typing import Dict, List, Any, TYPE_CHECKING

from core.combat.combat_entity import EntityType
from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.combat.combat_manager import CombatManager

logger = logging.getLogger(__name__)

def generate_combat_loot(manager: 'CombatManager', engine: 'GameEngine'):
    """Generate loot from defeated NPCs and make it available to the player."""
    from core.combat.enums import CombatState
    
    if manager.state != CombatState.PLAYER_VICTORY:
        return  # Only generate loot on player victory
    
    try:
        # Get state manager to access NPCs
        state_manager = engine._state_manager if hasattr(engine, '_state_manager') else None
        if not state_manager or not state_manager.current_state:
            logger.warning("Cannot generate loot: State manager unavailable")
            return
        
        game_state = state_manager.current_state
        available_loot = []
        loot_sources = []
        
        # Check each defeated enemy entity for loot
        for entity_id, entity in manager.entities.items():
            if entity.entity_type == EntityType.ENEMY and not entity.is_alive():
                # Try to get the NPC from the NPC system
                npc = None
                if hasattr(game_state, 'npc_system') and game_state.npc_system:
                    npc = game_state.npc_system.get_npc_by_id(entity_id)
                
                if npc and hasattr(npc, 'equipment_manager') and npc.equipment_manager:
                    # Extract equipment from defeated NPC
                    npc_loot = _extract_npc_equipment(npc, entity.combat_name)
                    if npc_loot:
                        available_loot.extend(npc_loot)
                        loot_sources.append(entity.combat_name)
        
        # Store loot in game state for player to collect
        if available_loot:
            if not hasattr(game_state, 'available_loot'):
                game_state.available_loot = []
            game_state.available_loot.extend(available_loot)
            
            # Generate loot message
            loot_count = len(available_loot)
            source_names = ", ".join(loot_sources)
            loot_message = f"Victory! Found {loot_count} item(s) from defeated enemies: {source_names}. Use 'loot' to examine available items."
            
            # Queue loot notification
            loot_event = DisplayEvent(
                type=DisplayEventType.SYSTEM_MESSAGE,
                content=loot_message,
                target_display=DisplayTarget.COMBAT_LOG,
                gradual_visual_display=False
            )
            engine._combat_orchestrator.add_event_to_queue(loot_event)
            
            logger.info(f"Generated {loot_count} loot items from {len(loot_sources)} defeated enemies")
        else:
            logger.debug("No loot generated from combat - no equipped items found on defeated enemies")
            
    except Exception as e:
        logger.error(f"Error generating combat loot: {e}", exc_info=True)

def _extract_npc_equipment(npc, combat_name: str) -> List[Dict[str, Any]]:
    """Extract equipment from a defeated NPC as loot items."""
    loot_items = []
    
    try:
        if not hasattr(npc, 'equipment_manager') or not npc.equipment_manager:
            return loot_items
        
        # Get all equipped items
        equipped_items = npc.equipment_manager.equipment
        for slot, item in equipped_items.items():
            if item is not None:
                # Create loot entry
                from core.inventory.item_serialization import item_to_dict
                loot_item = {
                    'item_data': item_to_dict(item),
                    'source': combat_name,
                    'source_type': 'defeated_enemy',
                    'slot': slot.value if hasattr(slot, 'value') else str(slot)
                }
                loot_items.append(loot_item)
                logger.debug(f"Added {item.name} to loot from {combat_name}")
        
        # Clear the NPC's equipment (they're defeated)
        if loot_items:
            npc.equipment_manager.unequip_all()
            
    except Exception as e:
        logger.error(f"Error extracting equipment from NPC {combat_name}: {e}", exc_info=True)
    
    return loot_items