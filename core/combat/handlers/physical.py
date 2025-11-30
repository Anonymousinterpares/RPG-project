import random
from typing import Dict, Any, TYPE_CHECKING

from core.stats.combat_effects import StatusEffect, StatusEffectType
from core.stats.derived_stats import get_modifier_from_stat
from core.stats.stats_base import StatType, DerivedStatType
from core.stats.modifier import StatModifier, ModifierType, ModifierSource
from core.utils.dice import roll_dice_notation, check_success
from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_action import CombatAction
from core.combat.enums import CombatState, CombatStep
from core.base.config import get_config
from core.orchestration.events import DisplayEvent, DisplayEventType
from core.utils.logging_config import get_logger

from .resource_utils import apply_and_display_costs

if TYPE_CHECKING:
    from core.combat.combat_manager import CombatManager
    from core.stats.stats_manager import StatsManager
    from core.base.engine import GameEngine

logger = get_logger(__name__)

def handle_attack_action(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handle the mechanics of an attack action."""
    
    queued_events_this_handler = False
    handler_result_summary = {"success": False, "message": "Attack failed or target invalid."} 
    current_result_detail.update(handler_result_summary) 

    if not action.targets:
        current_result_detail["message"] = "No target specified for attack."
        return current_result_detail 

    target_id = action.targets[0]
    target = manager.entities.get(target_id)

    if not target:
        current_result_detail["message"] = f"Target {target_id} not found."
        return current_result_detail
    if not target.is_alive():
        current_result_detail["message"] = f"{target.combat_name} is already defeated."
        return current_result_detail

    target_stats_manager = manager._get_entity_stats_manager(target_id)
    if not target_stats_manager:
        current_result_detail["message"] = f"Internal Error: Stats missing for target {target.combat_name}."
        return current_result_detail

    attack_stat_type = StatType.STRENGTH 
    attack_bonus = 0
    attack_stat_modifier = 0
    try:
        attack_stat_value = performer_stats_manager.get_stat_value(attack_stat_type)
        attack_stat_modifier = get_modifier_from_stat(attack_stat_value)
        attack_bonus = attack_stat_modifier 
    except Exception as e: logger.warning(f"Could not get attack stat modifier for {performer.combat_name}: {e}")

    defense_value = target_stats_manager.get_stat_value(DerivedStatType.DEFENSE)

    # --- Passive Defense from Skill ---
    try:
        def_skill = target_stats_manager.get_skill_value("defensive_combat")
        if def_skill > 0:
            passive_def_bonus = def_skill * 0.5
            defense_value += passive_def_bonus
            target_stats_manager.award_skill_exp("defensive_combat", 5) 
    except Exception:
        pass 
    # ----------------------------------

    adv = performer.has_status_effect("Advantage")
    disadv = performer.has_status_effect("Disadvantage")
    roll1 = random.randint(1, 20)
    roll2 = random.randint(1, 20) if (adv or disadv) else roll1
    
    raw_d20_roll = roll1 
    roll_type_str = ""
    adv_rolls_str_display = f"[{roll1}]"
    if adv and not disadv: raw_d20_roll = max(roll1, roll2); roll_type_str = " (Adv)"; adv_rolls_str_display = f"Adv[{max(roll1,roll2)} from ({roll1},{roll2})]"
    elif disadv and not adv: raw_d20_roll = min(roll1, roll2); roll_type_str = " (Disadv)"; adv_rolls_str_display = f"Disadv[{min(roll1,roll2)} from ({roll1},{roll2})]"
    
    hit_roll_total_modified = raw_d20_roll + attack_bonus 

    _, is_critical, is_fumble = check_success(raw_d20_roll, int(defense_value), is_attack=True)
    
    if is_critical: 
        hit_success = True
    elif is_fumble: 
        hit_success = False
    else:
        hit_success = (hit_roll_total_modified >= defense_value)

    roll_msg_content = (f"{performer.combat_name} attacks {target.combat_name} with {action.name}: "
                        f"Roll {hit_roll_total_modified}{roll_type_str} (Dice:{adv_rolls_str_display} + Bonus:{attack_bonus}) vs Def {int(defense_value)}")
    
    manager._log_and_dispatch_event(roll_msg_content, DisplayEventType.SYSTEM_MESSAGE)
    queued_events_this_handler = True

    # Apply costs via helper
    apply_and_display_costs(manager, performer, performer_stats_manager, engine, current_result_detail)

    damage_type = "slashing"
    current_result_detail.update({
        "hit_roll_result": {"success": hit_success, "is_critical": is_critical, "is_fumble": is_fumble,
                            "roll_total": hit_roll_total_modified, "roll_dice": raw_d20_roll, "roll_bonus": attack_bonus,
                            "target_defense": defense_value},
        "damage": 0, "damage_type": damage_type,
        "target_hp_before": target.current_hp if hasattr(target, 'current_hp') else target_stats_manager.get_current_stat_value(DerivedStatType.HEALTH), 
        "target_hp_after": target.current_hp if hasattr(target, 'current_hp') else target_stats_manager.get_current_stat_value(DerivedStatType.HEALTH), 
        "target_max_hp": target.max_hp if hasattr(target, 'max_hp') else target_stats_manager.get_stat_value(DerivedStatType.MAX_HEALTH),
        "target_defeated": not target.is_alive(), "damage_rolls_desc": ""
    })

    if hit_success:
        current_result_detail["success"] = True 
        current_result_detail["message"] = "Attack landed." 
        try:
            damage_dice = action.dice_notation or "1d4"
            base_damage_roll_obj = roll_dice_notation(damage_dice)
            base_damage_from_dice = base_damage_roll_obj["total"]
            damage_rolls_str = base_damage_roll_obj['rolls_str']

            if is_critical:
                crit_damage_roll_obj = roll_dice_notation(damage_dice) 
                base_damage_from_dice += crit_damage_roll_obj["total"]
                damage_rolls_str += f" + {crit_damage_roll_obj['rolls_str']} (Crit!)"
                manager._log_and_dispatch_event("  Critical Hit!", DisplayEventType.SYSTEM_MESSAGE)
                queued_events_this_handler = True
            
            current_result_detail["damage_rolls_desc"] = damage_rolls_str
            damage_stat_mod_value = attack_stat_modifier 
            total_raw_damage = base_damage_from_dice + damage_stat_mod_value
            
            raw_damage_msg = f"  Raw Damage: {total_raw_damage:.0f} ({damage_rolls_str} + {damage_stat_mod_value} mod)"
            manager._log_and_dispatch_event(raw_damage_msg, DisplayEventType.SYSTEM_MESSAGE)
            queued_events_this_handler = True
            
            damage_reduction = target_stats_manager.get_stat_value(DerivedStatType.DAMAGE_REDUCTION)
            after_flat = max(0, total_raw_damage - damage_reduction)
            final_damage_dealt = round(after_flat)
            
            mitigation_msg = f"  Mitigation: DR {damage_reduction:.0f}. After DR: {after_flat:.0f}"
            manager._log_and_dispatch_event(mitigation_msg, DisplayEventType.SYSTEM_MESSAGE)
            queued_events_this_handler = True
            
            try:
                typed_resist = float(target_stats_manager.get_resistance_percent(damage_type))
            except Exception:
                typed_resist = 0.0
            if abs(typed_resist) > 0.0001:
                after_type = max(0, after_flat * (1 - typed_resist / 100.0))
                final_damage_dealt = round(after_type)
                type_msg = f"  Type Resistance ({damage_type}): {typed_resist:.0f}% -> Final Damage: {final_damage_dealt}"
                manager._log_and_dispatch_event(type_msg, DisplayEventType.SYSTEM_MESSAGE)
                queued_events_this_handler = True

            target_hp_before_actual_deduction = target_stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
            target_hp_after_damage_preview = max(0, target_hp_before_actual_deduction - final_damage_dealt)
            
            # Optional typed rider
            try:
                cfg = get_config()
                rider = cfg.get(f"combat.typed_riders.{damage_type}")
            except Exception:
                rider = None
            try:
                if rider and isinstance(rider, dict) and rider.get("status"):
                    ch = rider.get("chance", 0.0)
                    dur = rider.get("duration", 1)
                    if random.random() < float(ch) and final_damage_dealt > 0:
                        status_name = str(rider.get("status"))
                        target_stats_manager.add_status_effect(StatusEffect(name=status_name, description=f"From {action.name}", effect_type=StatusEffectType.SPECIAL, duration=int(dur)))
                        target.add_status_effect(status_name, duration=int(dur))
                        status_msg = f"  {target.combat_name} is now {status_name} due to {action.name}!"
                        manager._log_and_dispatch_event(status_msg, DisplayEventType.SYSTEM_MESSAGE)
                        queued_events_this_handler = True
            except Exception as rider_err:
                logger.debug(f"Typed rider application failed or skipped: {rider_err}")
            
            damage_taken_log_msg = f"  {target.combat_name} takes {final_damage_dealt:.0f} {current_result_detail['damage_type']} damage! (HP: {int(target_hp_after_damage_preview)}/{int(target.max_hp)})"
            manager._log_and_dispatch_event(damage_taken_log_msg, DisplayEventType.SYSTEM_MESSAGE, gradual=True)
            queued_events_this_handler = True

            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE,
                content={},
                metadata={"entity_id": target.id, "bar_type": "hp", "final_new_value": target_hp_after_damage_preview, "max_value": target.max_hp}
            )); queued_events_this_handler = True

            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={}, metadata={"entity_id": target.id, "bar_type": "hp", "old_value": target_hp_before_actual_deduction, "new_value_preview": target_hp_after_damage_preview, "max_value": target.max_hp})); queued_events_this_handler = True
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={}, metadata={"entity_id": target.id, "bar_type": "hp", "final_new_value": target_hp_after_damage_preview, "max_value": target.max_hp})); queued_events_this_handler = True

            current_result_detail.update({"damage": final_damage_dealt, "target_hp_after": target_hp_after_damage_preview})

            if target_hp_after_damage_preview <= 0:
                defeat_msg = f"{target.combat_name} is defeated!"
                manager._log_and_dispatch_event(defeat_msg, DisplayEventType.SYSTEM_MESSAGE)
                queued_events_this_handler = True
                current_result_detail["target_defeated"] = True

                try:
                    game_state = engine._state_manager.current_state
                    if game_state is not None:
                        from core.game_flow.event_log import record_enemy_defeated
                        template_id = getattr(target, 'name', None) or getattr(target, 'combat_name', None)
                        tags = {"combat_name": getattr(target, 'combat_name', None)}
                        record_enemy_defeated(game_state, entity_id=str(target.id), template_id=str(template_id) if template_id else None, tags=tags, location_id=None)
                except Exception as e_log:
                    logger.debug(f"Failed to record defeat event: {e_log}")

                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                    type=DisplayEventType.APPLY_ENTITY_STATE_UPDATE,
                    content={},
                    metadata={"entity_id": target.id, "is_active_in_combat": False}
                ))
                
                try:
                    if target.entity_type == EntityType.PLAYER:
                        manager.state = CombatState.PLAYER_DEFEAT
                        manager.current_step = CombatStep.ENDING_COMBAT
                        manager.waiting_for_display_completion = True
                    else:
                        remaining_enemies = [e for e in manager.entities.values() if e.entity_type == EntityType.ENEMY and e.is_active_in_combat and e.is_alive()]
                        if len(remaining_enemies) == 0:
                            manager.state = CombatState.PLAYER_VICTORY
                            manager.current_step = CombatStep.ENDING_COMBAT
                            manager.waiting_for_display_completion = True
                except Exception:
                    pass
        except Exception as dmg_err:
            logger.error(f"Error during damage calculation for {action.name}: {dmg_err}", exc_info=True)
            current_result_detail["message"] = "Hit landed, but error calculating damage."
            current_result_detail["error_detail"] = f"Damage calc error: {dmg_err}"

    else: 
        miss_log_msg = "  Fumble! Attack misses wildly." if is_fumble else "  Attack misses."
        manager._log_and_dispatch_event(miss_log_msg, DisplayEventType.SYSTEM_MESSAGE)
        queued_events_this_handler = True
        current_result_detail["success"] = False 
        current_result_detail["message"] = "Attack missed."
    
    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail

def handle_defend_action(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handle the mechanics of a defend action."""
    logger.info(f"{performer.combat_name} takes a defensive stance.")
    queued_events_this_handler = False
    
    base_bonus = 20
    skill_bonus = 0
    try:
        skill_val = performer_stats_manager.get_skill_value("defensive_combat")
        skill_bonus = int(skill_val) 
    except Exception:
        pass
        
    total_bonus = base_bonus + skill_bonus
    duration = 1 
    
    defend_effect = StatusEffect(
        name="Defending", 
        description=f"Defensive stance (+{total_bonus} Def).", 
        effect_type=StatusEffectType.BUFF, 
        duration=duration,
        tick_on_turn_start=True
    )
    performer_stats_manager.add_status_effect(defend_effect)
    performer.add_status_effect("Defending", duration=duration) 

    mod = StatModifier(
        stat=DerivedStatType.DEFENSE,
        value=total_bonus,
        source_type=ModifierSource.CONDITION,
        source_name="Defending",
        modifier_type=ModifierType.TEMPORARY,
        duration=duration
    )
    if hasattr(performer_stats_manager, 'modifier_manager'):
        performer_stats_manager.modifier_manager.add_modifier(mod)
    else:
        if hasattr(performer_stats_manager, 'add_modifier'):
            performer_stats_manager.add_modifier(mod)
        else:
            logger.error("Could not find method to add modifier in handle_defend_action")

    defend_msg = f"  {performer.combat_name} takes a defensive stance (+{total_bonus} Defense)."
    manager._log_and_dispatch_event(defend_msg, DisplayEventType.SYSTEM_MESSAGE)
    queued_events_this_handler = True
    
    current_result_detail.update({
        "success": True, 
        "message": "Took defensive stance.",
        "effects_applied": [{"type": "status", "name": "Defending", "duration": duration, "target": performer.combat_name}],
        "queued_events": queued_events_this_handler
    })
    return current_result_detail