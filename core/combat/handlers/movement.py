import logging
from typing import Dict, Any, TYPE_CHECKING
from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_action import CombatAction
from core.orchestration.events import DisplayEvent, DisplayEventType
from core.stats.stats_base import StatType
from core.game_flow.mode_transitions import _determine_flee_parameters

if TYPE_CHECKING:
    from core.combat.combat_manager import CombatManager
    from core.stats.stats_manager import StatsManager
    from core.base.engine import GameEngine

logger = logging.getLogger(__name__)

def handle_flee_action_mechanics(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handles the mechanics of a flee action attempt."""
    
    current_result_detail.update({
        "performer_name": performer.combat_name,
        "action_name": "Flee",
        "action_type": action.action_type,  
        "target_name": "N/A",  
        "target_defeated": False, 
        "damage": 0
    })

    queued_events_this_handler = False

    if performer.has_status_effect("Immobilized"):
        immobilized_msg = f"  {performer.combat_name} cannot flee, they are immobilized!"
        manager._log_and_dispatch_event(immobilized_msg, DisplayEventType.SYSTEM_MESSAGE)
        queued_events_this_handler = True
        current_result_detail["message"] = "Cannot flee while immobilized."
        current_result_detail["success"] = False
        current_result_detail["fled"] = False
        current_result_detail["queued_events"] = queued_events_this_handler
        return current_result_detail 

    enemy_entities = [e for e in manager.entities.values() if e.entity_type == EntityType.ENEMY and e.is_alive() and getattr(e, 'is_active_in_combat', True)]
    if not enemy_entities:
        no_enemies_msg = f"{performer.combat_name} looks around... there are no active enemies to flee from. Combat ends."
        manager._log_and_dispatch_event(no_enemies_msg, DisplayEventType.SYSTEM_MESSAGE)
        queued_events_this_handler = True
        current_result_detail.update({"success": True, "fled": False, "message": "No enemies to flee from."})
        current_result_detail["queued_events"] = queued_events_this_handler
        return current_result_detail

    try:
        flee_dc, situational_modifier, modifier_reasons = _determine_flee_parameters(engine._state_manager.current_state, performer)

        skill_to_use = "acrobatics"
        stat_for_skill = StatType.DEXTERITY
        
        try:
            acrobatics_rank = performer_stats_manager.get_skill_value("acrobatics")
            athletics_rank = performer_stats_manager.get_skill_value("athletics")
            
            if athletics_rank > acrobatics_rank:
                skill_to_use = "athletics"
                stat_for_skill = StatType.STRENGTH
        except Exception:
            pass

        check_result = performer_stats_manager.perform_skill_check(
            stat_type=stat_for_skill, 
            difficulty=flee_dc,
            situational_modifier=situational_modifier,
            skill_name=skill_to_use
        )
        
        modifier_str_display = f"{check_result.modifier} (stat)"
        
        if check_result.situational_modifier != 0:
            modifier_str_display += f" {check_result.situational_modifier:+}"
            reasons_display = []
            if modifier_reasons:
                reasons_display.extend(modifier_reasons)
            
            if check_result.skill_exists:
                 reasons_display.append(f"{check_result.skill_name or skill_to_use}")
            else:
                 reasons_display.append("situational")

            if reasons_display:
                 modifier_str_display += f" ({', '.join(reasons_display)})"

        check_roll_msg = (
            f"{performer.combat_name} attempts to flee ({check_result.skill_name or skill_to_use} check DC {flee_dc}): "
            f"Roll {check_result.roll} + {modifier_str_display} "
            f"= {check_result.total} -> {check_result.outcome_desc}"
            f"{' (Crit!)' if check_result.critical else ''}"
        )
        manager._log_and_dispatch_event(check_roll_msg, DisplayEventType.SYSTEM_MESSAGE)
        queued_events_this_handler = True

        flee_succeeded_mechanically = check_result.success
        current_result_detail["roll_details"] = check_result.to_dict()
        
        if flee_succeeded_mechanically:
            current_result_detail.update({"success": True, "fled": True, "message": "Escape successful!"})
            performer.is_active_in_combat = False 
            
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.APPLY_ENTITY_STATE_UPDATE,
                content={},
                metadata={"entity_id": performer.id, "is_active_in_combat": False}
            ))
        else:
            current_result_detail.update({"success": False, "fled": False, "message": "Escape attempt failed."})
            
    except Exception as e:
        logger.exception(f"Error during flee check mechanics for {performer.combat_name}: {e}")
        err_msg = f"System Error performing flee check: {e}"
        manager._log_and_dispatch_event(err_msg, DisplayEventType.SYSTEM_MESSAGE)
        queued_events_this_handler = True
        current_result_detail["message"] = err_msg
        
    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail

def handle_surrender_action_mechanics(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handles the mechanics of a surrender attempt."""
    
    current_result_detail.update({
        "performer_name": performer.combat_name,
        "action_name": "Surrender",
        "action_type": action.action_type,
        "target_name": "Enemies", 
        "target_defeated": False, 
        "damage": 0
    })
    
    queued_events_this_handler = False

    surrender_dc = 12 
    enemies = [e for e in manager.entities.values() if e.entity_type == EntityType.ENEMY and e.is_alive() and getattr(e, 'is_active_in_combat', True)]
    
    if not enemies:
        no_enemies_msg = f"{performer.combat_name} lays down arms... but there is no one to surrender to. Combat ends."
        manager._log_and_dispatch_event(no_enemies_msg, DisplayEventType.SYSTEM_MESSAGE)
        current_result_detail.update({"success": True, "surrendered": True, "message": "No enemies to surrender to."})
        current_result_detail["queued_events"] = True
        return current_result_detail

    highest_level = 1
    aggro_mod = 0
    for enemy in enemies:
        lvl = getattr(enemy, 'level', 1)
        if lvl > highest_level: highest_level = lvl
        if "Undead" in enemy.name: aggro_mod += 5 
        
    surrender_dc = max(10, 10 + highest_level + aggro_mod)
    
    skill_to_use = "persuasion"
    stat_for_skill = StatType.CHARISMA
    
    check_result = performer_stats_manager.perform_skill_check(
        stat_type=stat_for_skill,
        difficulty=surrender_dc,
        skill_name=skill_to_use
    )
    
    modifier_str_display = f"{check_result.modifier} (stat)"
    if check_result.skill_exists:
         modifier_str_display += f" ({check_result.skill_name or skill_to_use})"

    check_roll_msg = (
        f"{performer.combat_name} attempts to surrender ({skill_to_use.title()} check DC {surrender_dc}): "
        f"Roll {check_result.roll} + {modifier_str_display} "
        f"= {check_result.total} -> {check_result.outcome_desc}"
    )
    manager._log_and_dispatch_event(check_roll_msg, DisplayEventType.SYSTEM_MESSAGE)
    queued_events_this_handler = True
    
    current_result_detail["roll_details"] = check_result.to_dict()

    if check_result.success:
        current_result_detail["intent_clarification"] = (
            "The player's surrender was ACCEPTED by the enemies. "
            "The player lays down their arms and submits. "
            "The enemies DO NOT surrender; they have won by forcing the player to submit. "
            "The player is stripped of all equipment as a consequence."
        )
        
        try:
            from core.inventory import get_inventory_manager
            import random
            inv_mgr = get_inventory_manager()
            
            items_to_transfer = []
            if hasattr(inv_mgr, 'items'):
                if isinstance(inv_mgr.items, dict):
                    items_to_transfer.extend(list(inv_mgr.items.values()))
                elif isinstance(inv_mgr.items, list):
                    items_to_transfer.extend(inv_mgr.items)
            
            if hasattr(inv_mgr, 'equipment') and isinstance(inv_mgr.equipment, dict):
                for item in inv_mgr.equipment.values():
                    if item: items_to_transfer.append(item)
            
            if items_to_transfer and enemies:
                npc_system = engine.state_manager.get_npc_system()
                for item in items_to_transfer:
                    recipient_entity = random.choice(enemies)
                    if npc_system:
                        npc_obj = npc_system.get_npc_by_id(recipient_entity.id)
                        if npc_obj:
                            if not hasattr(npc_obj, 'inventory'):
                                npc_obj.inventory = []
                            npc_obj.inventory.append(item.to_dict() if hasattr(item, 'to_dict') else str(item))

                if hasattr(inv_mgr, 'clear'):
                    inv_mgr.clear()
                else:
                    logger.error("InventoryManager does not have a clear() method. Equipment stripping failed.")
                
                loss_msg = f"You have been stripped of your belongings! ({len(items_to_transfer)} items lost)"
                manager._log_and_dispatch_event(loss_msg, DisplayEventType.SYSTEM_MESSAGE)
                current_result_detail["consequences"] = f"Player lost {len(items_to_transfer)} items to enemies."

        except Exception as e:
            logger.error(f"Error stripping player equipment: {e}", exc_info=True)
            current_result_detail["consequences_error"] = f"Error handling equipment loss: {e}"

        current_result_detail.update({"success": True, "fled": True, "surrendered": True, "message": "Surrender accepted!"})
        performer.is_active_in_combat = False 
        
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
            type=DisplayEventType.APPLY_ENTITY_STATE_UPDATE,
            content={},
            metadata={"entity_id": performer.id, "is_active_in_combat": False}
        ))
        
        engine.request_ui_update()
    else:
        current_result_detail["intent_clarification"] = "The player attempted to surrender, but the enemies REFUSED. The enemies continue to attack."
        current_result_detail.update({"success": False, "surrendered": False, "message": "Surrender rejected."})

    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail