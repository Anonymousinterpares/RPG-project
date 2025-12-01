from typing import Dict, List, Any, TYPE_CHECKING

from core.combat.combat_entity import EntityType
from core.inventory.item_serialization import item_to_dict
from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.combat.combat_manager import CombatManager
from core.utils.logging_config import get_logger

logger = get_logger(__name__)

def generate_combat_loot(manager: 'CombatManager', engine: 'GameEngine'):
    """Generate loot from defeated NPCs and make it available to the player."""
    from core.combat.enums import CombatState
    
    if manager.state != CombatState.PLAYER_VICTORY:
        return 
    
    try:
        state_manager = engine._state_manager if hasattr(engine, '_state_manager') else None
        if not state_manager or not state_manager.current_state:
            return
        
        game_state = state_manager.current_state
        available_loot = []
        loot_sources = []
        
        npc_system = state_manager.get_npc_system()
        
        npcs_modified = False # Track if we need to save

        for entity_id, entity in manager.entities.items():
            if entity.entity_type == EntityType.ENEMY and not entity.is_alive():
                # Get Persistent NPC
                npc = npc_system.get_npc_by_id(entity_id)
                
                if npc:
                    # Mark dead in persistent system immediately
                    npc.is_dead = True
                    # Ensure stats reflect death (0 HP)
                    if npc.stats_manager:
                        from core.stats.stats_base import DerivedStatType
                        npc.stats_manager.set_current_stat(DerivedStatType.HEALTH, 0)
                        
                    # Extract loot
                    npc_loot = _extract_npc_loot(npc, entity.combat_name)
                    if npc_loot:
                        available_loot.extend(npc_loot)
                        loot_sources.append(entity.combat_name)
                    
                    npcs_modified = True
                else:
                    # Logic for non-persistent/transient NPCs (template loot generation) could go here
                    pass
        
        # Save the updated state of NPCs (Dead + Empty Inventory)
        if npcs_modified:
            npc_system.save_all_npcs()
            logger.info("Saved NPC states (marked dead/looted) to disk.")

        if available_loot:
            if not hasattr(game_state, 'available_loot'):
                game_state.available_loot = []
            game_state.available_loot.extend(available_loot)
            
            loot_count = len(available_loot)
            source_names = ", ".join(loot_sources)
            loot_message = f"Victory! Found {loot_count} item(s) from defeated enemies: {source_names}. Use 'loot' to examine available items."
            
            loot_event = DisplayEvent(
                type=DisplayEventType.SYSTEM_MESSAGE,
                content=loot_message,
                target_display=DisplayTarget.COMBAT_LOG,
                gradual_visual_display=False
            )
            engine._combat_orchestrator.add_event_to_queue(loot_event)
            engine.request_ui_update()
            
    except Exception as e:
        logger.error(f"Error generating combat loot: {e}", exc_info=True)

def _extract_npc_loot(npc, combat_name: str) -> List[Dict[str, Any]]:
    """Extract equipment AND stored inventory from a defeated NPC as loot items."""
    loot_items = []
    
    try:
        # 1. Extract Equipped Items
        if hasattr(npc, 'equipment_manager') and npc.equipment_manager:
            equipped_items = npc.equipment_manager.equipment
            for slot, item in equipped_items.items():
                if item is not None:
                    # Serialize the item using item_to_dict
                    item_data = item_to_dict(item)
                    
                    loot_item = {
                        'item_data': item_data,
                        'source': combat_name,
                        'source_type': 'defeated_enemy_equipment',
                        'slot': slot.value if hasattr(slot, 'value') else str(slot)
                    }
                    loot_items.append(loot_item)
            
            # Clear equipment to prevent dupes
            npc.equipment_manager.unequip_all()

        # 2. Extract Stored Inventory (e.g. items surrendered by player previously)
        if hasattr(npc, 'inventory') and npc.inventory:
            for item_entry in npc.inventory:
                # item_entry in npc.inventory is typically a dict (serialized item) 
                # or possibly an Item object depending on how it was added.
                
                item_data = None
                if isinstance(item_entry, dict):
                    item_data = item_entry
                elif hasattr(item_entry, 'to_dict'):
                    item_data = item_to_dict(item_entry)
                
                if item_data:
                    loot_item = {
                        'item_data': item_data,
                        'source': combat_name,
                        'source_type': 'defeated_enemy_inventory',
                        'slot': 'inventory'
                    }
                    loot_items.append(loot_item)
            
            # Clear inventory so it's not looted twice if body persists
            npc.inventory = []
            
        if loot_items:
            logger.debug(f"Extracted {len(loot_items)} items from {combat_name}")

    except Exception as e:
        logger.error(f"Error extracting loot from NPC {combat_name}: {e}", exc_info=True)
    
    return loot_items