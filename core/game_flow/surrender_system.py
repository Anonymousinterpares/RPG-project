import random
from typing import  TYPE_CHECKING

from core.character.npc_system import get_npc_system
from core.inventory import get_inventory_manager
from core.inventory.item_serialization import item_to_dict
from core.game_flow.lifecycle import save_game
from core.combat.combat_entity import EntityType
from core.utils.logging_config import get_logger

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.combat.combat_manager import CombatManager
    from core.combat.combat_entity import CombatEntity

logger = get_logger("SURRENDER_SYSTEM")

def process_surrender_consequences(engine: 'GameEngine', combat_manager: 'CombatManager', player_entity: 'CombatEntity') -> dict:
    """
    Handles the logic when a player successfully surrenders.
    1. Identifies living enemies.
    2. Strips player inventory (equipped + backpack).
    3. Transfers items to a selected enemy's persistent inventory.
    4. Marks that enemy as persistent and updates their location.
    5. Saves the global game state immediately (Auto-Save).
    """
    result_log = {"items_lost": 0, "recipient_npc_id": None, "recipient_name": None}
    
    # 1. Identify valid recipients (Living Enemies)
    enemies = [
        e for e in combat_manager.entities.values() 
        if e.entity_type == EntityType.ENEMY and e.is_alive() and getattr(e, 'is_active_in_combat', True)
    ]
    
    if not enemies:
        logger.warning("Surrender accepted but no enemies found to take loot.")
        return result_log

    # Pick a recipient (CombatEntity)
    recipient_entity = random.choice(enemies)
    
    # 2. Collect Player Items
    inv_mgr = get_inventory_manager()
    items_to_transfer = []
    
    # Backpack
    if hasattr(inv_mgr, 'items'):
        source_items = inv_mgr.items.values() if isinstance(inv_mgr.items, dict) else inv_mgr.items
        for item in source_items:
            items_to_transfer.append(item)
            
    # Equipped
    if hasattr(inv_mgr, 'equipment') and isinstance(inv_mgr.equipment, dict):
        for item in inv_mgr.equipment.values():
            if item:
                items_to_transfer.append(item)

    if not items_to_transfer:
        logger.info("Player surrendered but had no items to lose.")
        return result_log

    result_log["items_lost"] = len(items_to_transfer)

    # 3. Transfer to Persistent NPC
    # Prefer system from engine state to ensure same context
    npc_system = None
    if engine and hasattr(engine, 'state_manager'):
        npc_system = engine.state_manager.get_npc_system()
    
    if not npc_system:
        npc_system = get_npc_system()
    
    # Retrieve the actual NPC object (Persistence Shell)
    target_npc = npc_system.get_npc_by_id(recipient_entity.id)
    
    if not target_npc:
        logger.error(f"Could not find persistent NPC object for CombatEntity {recipient_entity.id} ({recipient_entity.name}).")
        # Check internal manager list
        if hasattr(npc_system, 'manager'):
            target_npc = npc_system.manager.get_npc_by_id(recipient_entity.id)

    if target_npc:
        # Initialize inventory if needed
        if not hasattr(target_npc, 'inventory') or target_npc.inventory is None:
            target_npc.inventory = []
            
        # Serialize and Transfer Inventory
        for item in items_to_transfer:
            item_data = item_to_dict(item, include_unknown=True)
            target_npc.inventory.append(item_data)
            
        logger.info(f"Transferred {len(items_to_transfer)} items to NPC {target_npc.name} ({target_npc.id})")
        
        # 4. Persistence & Stats Synchronization (CRITICAL FIX)
        target_npc.is_persistent = True
        
        # --- FIX START: Sync Combat Stats to Persistent NPC ---
        # Retrieve the active StatsManager from the CombatManager (which tracks current HP, etc.)
        active_stats_manager = combat_manager._get_entity_stats_manager(recipient_entity.id)
        
        if active_stats_manager:
            # Assign the active stats manager to the persistent NPC object
            # This ensures current HP, attributes, and level are saved to disk.
            target_npc.stats_manager = active_stats_manager
            target_npc.stats_generated = True
            
            # Explicitly sync derived stats like current HP
            from core.stats.stats_base import DerivedStatType
            target_npc.stats_manager.set_current_stat(DerivedStatType.HEALTH, recipient_entity.current_hp)
            
            logger.info(f"Synced stats for {target_npc.name}. HP: {recipient_entity.current_hp}")
        else:
            logger.warning(f"Could not find active StatsManager for {recipient_entity.name}. NPC saved without stats!")
        # --- FIX END ---

        # Update location to where the fight happened
        current_loc = getattr(player_entity, 'location', None)
        if not current_loc and engine.state_manager.current_state.player:
            current_loc = engine.state_manager.current_state.player.current_location
            
        if current_loc:
            target_npc.location = current_loc
            npc_system.update_npc_location(target_npc.id, current_loc)
            logger.info(f"NPC {target_npc.name} location updated to {current_loc}")

        # Save all NPCs to disk immediately
        npc_system.save_all_npcs()
        
        result_log["recipient_npc_id"] = target_npc.id
        result_log["recipient_name"] = target_npc.name
    else:
        logger.critical(f"FATAL: Loot lost! Could not locate NPC {recipient_entity.id} to transfer items to.")

    # 5. Wipe Player Inventory
    inv_mgr.clear()
    
    # 6. Trigger Auto-Save (Checkpoint)
    save_game(engine, auto_save=True)
    logger.info("Game Auto-Saved following Surrender.")

    return result_log