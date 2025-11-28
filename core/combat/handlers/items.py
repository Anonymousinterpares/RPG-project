import logging
from typing import Dict, Any, TYPE_CHECKING
from core.stats.combat_effects import StatusEffect, StatusEffectType
from core.stats.derived_stats import DerivedStatType
from core.combat.combat_entity import CombatEntity
from core.combat.combat_action import CombatAction
from core.orchestration.events import DisplayEvent, DisplayEventType

if TYPE_CHECKING:
    from core.combat.combat_manager import CombatManager
    from core.stats.stats_manager import StatsManager
    from core.base.engine import GameEngine

logger = logging.getLogger(__name__)

def handle_item_action(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handle using an item in combat."""
    
    item_id_from_action = action.special_effects.get("item_id", "unknown_item") 
    item_name_from_action = action.name.replace("Use ", "") 
    queued_events_this_handler = False

    current_result_detail.update({"targets_processed": [], "item_id": item_id_from_action, "item_name": item_name_from_action})
    at_least_one_effect_applied = False

    targets_for_item = action.targets if action.targets else [performer.id]

    for target_id in targets_for_item:
        target = manager.entities.get(target_id)
        target_processing_summary = {"target_id": target_id, "target_name": "Unknown", "effects_applied": [], "damage_done": 0, "healing_done": 0, "defeated": False}

        if not target:
            logger.warning(f"Target {target_id} not found for item {item_name_from_action}")
            target_processing_summary["error"] = "Target not found"
            current_result_detail["targets_processed"].append(target_processing_summary)
            continue
        
        target_processing_summary["target_name"] = target.combat_name

        if not target.is_alive() and "revive" not in action.special_effects: 
            logger.debug(f"Target {target.combat_name} already defeated, skipping item effect for {item_name_from_action}.")
            target_processing_summary["status"] = "Already defeated"
            current_result_detail["targets_processed"].append(target_processing_summary)
            continue

        target_stats_manager = manager._get_entity_stats_manager(target_id)
        if not target_stats_manager:
            logger.error(f"StatsManager for target {target_id} of item {item_name_from_action} not found.")
            target_processing_summary["error"] = "Target StatsManager not found"
            current_result_detail["targets_processed"].append(target_processing_summary)
            continue
            
        target_hp_before_item = target_stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
        item_effects = action.special_effects 
        
        if item_effects.get("effect_type") == "healing_potion": 
            at_least_one_effect_applied = True
            heal_amount = int(item_effects.get("heal_amount", 10)) 
            target_hp_preview = min(target_hp_before_item + heal_amount, target.max_hp)
            actual_healed = target_hp_preview - target_hp_before_item

            if actual_healed > 0:
                heal_msg = f"  {target.combat_name} is healed for {actual_healed:.0f} HP by {item_name_from_action}! (HP: {int(target_hp_preview)}/{int(target.max_hp)})"
                manager._log_and_dispatch_event(heal_msg, DisplayEventType.SYSTEM_MESSAGE, gradual=True)
                queued_events_this_handler = True
                
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                    type=DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE,
                    content={},
                    metadata={"entity_id": target.id, "bar_type": "hp", "final_new_value": target_hp_preview, "max_value": target.max_hp}
                )); queued_events_this_handler = True

                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={}, metadata={"entity_id": target.id, "bar_type": "hp", "old_value": target_hp_before_item, "new_value_preview": target_hp_preview, "max_value": target.max_hp})); queued_events_this_handler = True
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={}, metadata={"entity_id": target.id, "bar_type": "hp", "final_new_value": target_hp_preview, "max_value": target.max_hp})); queued_events_this_handler = True
                target_processing_summary["healing_done"] = actual_healed
            else:
                no_heal_msg = f"  {item_name_from_action} has no further healing effect on {target.combat_name} (already at/near full health)."
                manager._log_and_dispatch_event(no_heal_msg, DisplayEventType.SYSTEM_MESSAGE)
                queued_events_this_handler = True
        
        if item_effects.get("apply_status"):
            at_least_one_effect_applied = True
            status_to_apply = item_effects["apply_status"].get("name", "UnknownEffect")
            status_duration = item_effects["apply_status"].get("duration")
            
            target_stats_manager.add_status_effect(StatusEffect(name=status_to_apply, description=f"From item {item_name_from_action}", effect_type=StatusEffectType.SPECIAL, duration=status_duration))
            target.add_status_effect(status_to_apply, duration=status_duration)
            
            duration_text = f" for {status_duration} turns" if status_duration is not None else ""
            status_msg = f"  {target.combat_name} is now {status_to_apply}{duration_text} from {item_name_from_action}!"
            manager._log_and_dispatch_event(status_msg, DisplayEventType.SYSTEM_MESSAGE)
            queued_events_this_handler = True
            target_processing_summary["effects_applied"].append(status_to_apply)
            
        current_result_detail["targets_processed"].append(target_processing_summary)

    if at_least_one_effect_applied:
        current_result_detail["success"] = True 
        current_result_detail["message"] = f"{item_name_from_action} was used effectively."
    else: 
        current_result_detail["success"] = True 
        current_result_detail["message"] = f"{item_name_from_action} was used, but had no immediate combat effects."
        no_effect_msg = f"{performer.combat_name} uses {item_name_from_action}, but it seems to have no immediate effect."
        manager._log_and_dispatch_event(no_effect_msg, DisplayEventType.SYSTEM_MESSAGE)
        queued_events_this_handler = True
        
    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail