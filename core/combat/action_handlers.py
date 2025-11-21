import random
import logging
from typing import Dict, List, Tuple, Any, Optional, TYPE_CHECKING

from core.stats.combat_effects import StatusEffect, StatusEffectType
from core.stats.derived_stats import get_modifier_from_stat
from core.stats.stats_base import StatType, DerivedStatType
from core.utils.dice import roll_dice_notation, check_success
from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_action import CombatAction 
from core.base.config import get_config
from core.combat.enums import CombatState, CombatStep

if TYPE_CHECKING:
    from .combat_manager import CombatManager 
    from core.stats.stats_manager import StatsManager
    from core.base.engine import GameEngine

logger = logging.getLogger(__name__)

def _handle_attack_action(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handle the mechanics of an attack action. Queues DisplayEvents. Updates current_result_detail."""
    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
    
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
    event_roll_msg = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=roll_msg_content, target_display=DisplayTarget.COMBAT_LOG)
    engine._combat_orchestrator.add_event_to_queue(event_roll_msg)
    manager._add_to_log(roll_msg_content) 
    queued_events_this_handler = True

    # Apply and display resource costs (stamina/mana) after roll line
    try:
        stamina_spent = current_result_detail.get("stamina_spent", 0)
        mana_spent = current_result_detail.get("mana_spent", 0)
        if stamina_spent and stamina_spent > 0:
            prev_stam = performer_stats_manager.get_current_stat_value(DerivedStatType.STAMINA)
            new_stam = max(0, prev_stam - stamina_spent)
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={},
                metadata={"entity_id": performer.id, "bar_type": "stamina", "old_value": prev_stam, "new_value_preview": new_stam, "max_value": performer.max_stamina}
            ))
            performer_stats_manager.set_current_stat(DerivedStatType.STAMINA, new_stam)
            performer.set_current_stamina(new_stam)
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={},
                metadata={"entity_id": performer.id, "bar_type": "stamina", "final_new_value": new_stam, "max_value": performer.max_stamina}
            ))
            manager._add_to_log(f"{performer.combat_name} spent {stamina_spent:.1f} stamina. Rem: {new_stam:.1f}")
        if mana_spent and mana_spent > 0:
            prev_mp = performer_stats_manager.get_current_stat_value(DerivedStatType.MANA)
            new_mp = max(0, prev_mp - mana_spent)
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={},
                metadata={"entity_id": performer.id, "bar_type": "mana", "old_value": prev_mp, "new_value_preview": new_mp, "max_value": performer.max_mp}
            ))
            performer_stats_manager.set_current_stat(DerivedStatType.MANA, new_mp)
            performer.current_mp = new_mp
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={},
                metadata={"entity_id": performer.id, "bar_type": "mana", "final_new_value": new_mp, "max_value": performer.max_mp}
            ))
            manager._add_to_log(f"{performer.combat_name} spent {mana_spent:.1f} mana. Rem: {new_mp:.1f}")
    except Exception as e_cost:
        logger.warning(f"Failed to apply/display resource costs after roll: {e_cost}")

    # Determine typed damage type for melee attacks (default to slashing)
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
            damage_rolls_str = ""
            base_damage_from_dice = 0
            
            base_damage_roll_obj = roll_dice_notation(damage_dice)
            base_damage_from_dice = base_damage_roll_obj["total"]
            damage_rolls_str = base_damage_roll_obj['rolls_str']

            if is_critical:
                crit_damage_roll_obj = roll_dice_notation(damage_dice) 
                base_damage_from_dice += crit_damage_roll_obj["total"]
                damage_rolls_str += f" + {crit_damage_roll_obj['rolls_str']} (Crit!)"
                crit_msg_event = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content="  Critical Hit!", target_display=DisplayTarget.COMBAT_LOG)
                engine._combat_orchestrator.add_event_to_queue(crit_msg_event); manager._add_to_log("  Critical Hit!")
                queued_events_this_handler = True
            
            current_result_detail["damage_rolls_desc"] = damage_rolls_str
            damage_stat_mod_value = attack_stat_modifier 
            total_raw_damage = base_damage_from_dice + damage_stat_mod_value
            
            raw_damage_msg = f"  Raw Damage: {total_raw_damage:.0f} ({damage_rolls_str} + {damage_stat_mod_value} mod)"
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=raw_damage_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(raw_damage_msg)
            queued_events_this_handler = True
            
            damage_reduction = target_stats_manager.get_stat_value(DerivedStatType.DAMAGE_REDUCTION)
            after_flat = max(0, total_raw_damage - damage_reduction)
            final_damage_dealt = round(after_flat)
            
            mitigation_msg = f"  Mitigation: DR {damage_reduction:.0f}. After DR: {after_flat:.0f}"
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=mitigation_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(mitigation_msg)
            queued_events_this_handler = True
            
            # Apply typed resistance
            try:
                typed_resist = float(target_stats_manager.get_resistance_percent(damage_type))
            except Exception:
                typed_resist = 0.0
            if abs(typed_resist) > 0.0001:
                after_type = max(0, after_flat * (1 - typed_resist / 100.0))
                final_damage_dealt = round(after_type)
                type_msg = f"  Type Resistance ({damage_type}): {typed_resist:.0f}% -> Final Damage: {final_damage_dealt}"
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=type_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(type_msg)
                queued_events_this_handler = True

            target_hp_before_actual_deduction = target_stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
            target_hp_after_damage_preview = max(0, target_hp_before_actual_deduction - final_damage_dealt)
            
            # Optional typed rider application (low chance) before announcing damage line
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
                        # Apply to stats manager and entity registry for consistency
                        target_stats_manager.add_status_effect(StatusEffect(name=status_name, description=f"From {action.name}", effect_type=StatusEffectType.SPECIAL, duration=int(dur)))
                        target.add_status_effect(status_name, duration=int(dur))
                        status_msg = f"  {target.combat_name} is now {status_name} due to {action.name}!"
                        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=status_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(status_msg)
                        queued_events_this_handler = True
            except Exception as rider_err:
                logger.debug(f"Typed rider application failed or skipped: {rider_err}")
            
            # STRICT ORDER: announce damage before any bar change
            damage_taken_log_msg = f"  {target.combat_name} takes {final_damage_dealt:.0f} {current_result_detail['damage_type']} damage! (HP: {int(target_hp_after_damage_preview)}/{int(target.max_hp)})"
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=damage_taken_log_msg, target_display=DisplayTarget.COMBAT_LOG, gradual_visual_display=True)); manager._add_to_log(damage_taken_log_msg)
            queued_events_this_handler = True

            # Apply model update AFTER the outcome text is displayed, then animate
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE,
                content={},
                metadata={"entity_id": target.id, "bar_type": "hp", "final_new_value": target_hp_after_damage_preview, "max_value": target.max_hp}
            )); queued_events_this_handler = True

            # Phase 1 preview, then finalize
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={}, metadata={"entity_id": target.id, "bar_type": "hp", "old_value": target_hp_before_actual_deduction, "new_value_preview": target_hp_after_damage_preview, "max_value": target.max_hp})); queued_events_this_handler = True
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={}, metadata={"entity_id": target.id, "bar_type": "hp", "final_new_value": target_hp_after_damage_preview, "max_value": target.max_hp})); queued_events_this_handler = True

            current_result_detail.update({"damage": final_damage_dealt, "target_hp_after": target_hp_after_damage_preview})

            if target_hp_after_damage_preview <= 0:
                defeat_msg = f"{target.combat_name} is defeated!"
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=defeat_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(defeat_msg)
                queued_events_this_handler = True
                current_result_detail["target_defeated"] = True

                # Record defeat event for quest evaluation (Phase 1)
                try:
                    game_state = engine._state_manager.current_state
                    if game_state is not None:
                        from core.game_flow.event_log import record_enemy_defeated
                        # Use target.name as template_id fallback; include combat_name as tag hint
                        template_id = getattr(target, 'name', None) or getattr(target, 'combat_name', None)
                        tags = {"combat_name": getattr(target, 'combat_name', None)}
                        record_enemy_defeated(game_state, entity_id=str(target.id), template_id=str(template_id) if template_id else None, tags=tags, location_id=None)
                except Exception as e_log:
                    logger.debug(f"Failed to record defeat event: {e_log}")

                # Delay removing the entity from active combat until after defeat text using an orchestrated state update
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                    type=DisplayEventType.APPLY_ENTITY_STATE_UPDATE,
                    content={},
                    metadata={"entity_id": target.id, "is_active_in_combat": False}
                ))
                # If defeat ends combat (player down or all enemies down), schedule a 3000ms pause and finalize
                try:
                    from core.combat.combat_entity import EntityType
                    if target.entity_type == EntityType.PLAYER:
                        # Mark immediate end state to prevent any further CM steps
                        manager.state = CombatState.PLAYER_DEFEAT
                        manager.current_step = CombatStep.ENDING_COMBAT
                        manager.waiting_for_display_completion = True
# Removed pause/finalize events; CM will end via state/step change
                    else:
                        remaining_enemies = [e for e in manager.entities.values() if e.entity_type == EntityType.ENEMY and e.is_active_in_combat and e.is_alive()]
                        if len(remaining_enemies) == 0:
                            # Mark immediate end state to prevent any further CM steps
                            manager.state = CombatState.PLAYER_VICTORY
                            manager.current_step = CombatStep.ENDING_COMBAT
                            manager.waiting_for_display_completion = True
# Removed pause/finalize events; CM will end via state/step change
                except Exception:
                    pass
        except Exception as dmg_err:
            logger.error(f"Error during damage calculation for {action.name}: {dmg_err}", exc_info=True)
            current_result_detail["message"] = "Hit landed, but error calculating damage."
            current_result_detail["error_detail"] = f"Damage calc error: {dmg_err}"

    else: 
        miss_log_msg = "  Fumble! Attack misses wildly." if is_fumble else "  Attack misses."
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=miss_log_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(miss_log_msg)
        queued_events_this_handler = True
        current_result_detail["success"] = False 
        current_result_detail["message"] = "Attack missed."
    
    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail

def _handle_spell_action(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handle a spell casting action, including damage and effects. Queues DisplayEvents.
    
    Prioritizes effect_atoms from the spell catalog over legacy dice_notation.
    """
    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
    
    queued_events_this_handler = False
    handler_result_summary = {"success": False, "message": "Spell casting failed or target invalid."} 
    current_result_detail.update(handler_result_summary) 

    if "targets_processed" not in current_result_detail:
        current_result_detail["targets_processed"] = []

    # Try to get spell from catalog and use effects engine if it has effect_atoms
    spell_obj = None
    effect_atoms = []
    try:
        from core.magic.spell_catalog import get_spell_catalog
        catalog = get_spell_catalog()
        # SpellAction stores canonical spell id in the name field for traceability
        spell_obj = catalog.get_spell_by_id(action.name)
        if spell_obj:
            effect_atoms = spell_obj.effect_atoms
    except Exception as e:
        logger.debug(f"Could not load spell from catalog for action {action.name}: {e}")

    # If no targets were provided, attempt to auto-resolve based on spell combat_role
    if (not action.targets) and spell_obj is not None:
        try:
            role = getattr(spell_obj, 'combat_role', 'offensive') or 'offensive'
        except Exception:
            role = 'offensive'
        try:
            from core.combat.combat_entity import EntityType
            import random
            if role == 'defensive':
                action.targets = [performer.id]
                current_result_detail["target_name"] = performer.combat_name
            elif role == 'offensive':
                alive_enemies = [e for e in manager.entities.values() if getattr(e, 'entity_type', None) == EntityType.ENEMY and getattr(e, 'is_active_in_combat', True) and e.is_alive()]
                if len(alive_enemies) == 1:
                    action.targets = [alive_enemies[0].id]
                    current_result_detail["target_name"] = alive_enemies[0].combat_name
                elif len(alive_enemies) > 1:
                    picked = random.choice(alive_enemies)
                    action.targets = [picked.id]
                    current_result_detail["target_name"] = picked.combat_name
                else:
                    # No enemies to target
                    current_result_detail["message"] = "No valid enemy targets available for offensive spell."
                    return current_result_detail
            else:
                current_result_detail["message"] = "This spell requires a specific target or can only be used out of combat."
                return current_result_detail
        except Exception as e_auto:
            logger.debug(f"Auto-targeting failed for spell {action.name}: {e_auto}")
            current_result_detail["message"] = "No target specified for spell and auto-targeting failed."
            return current_result_detail

    # If still missing targets, fail explicitly
    if not action.targets:
        current_result_detail["message"] = "No target specified for spell."
        return current_result_detail
    
    # Play magic SFX before resolving mechanics
    try:
        if hasattr(engine, '_sfx_manager') and engine._sfx_manager:
            system_id = getattr(spell_obj, 'system_id', None) if spell_obj else None
            role_tok = getattr(spell_obj, 'combat_role', None) if spell_obj else None
            engine._sfx_manager.play_magic_cast(system_id, role_tok, getattr(spell_obj, 'id', action.name), failed=False)
    except Exception:
        pass
    # Use effects engine if we have effect_atoms, otherwise fallback to legacy handling
    if effect_atoms and spell_obj:
        return _handle_spell_with_effects_engine(manager, action, performer, performer_stats_manager, engine, current_result_detail, spell_obj, effect_atoms)
    else:
        return _handle_spell_legacy_dice(manager, action, performer, performer_stats_manager, engine, current_result_detail)


def _handle_spell_with_effects_engine(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict, spell_obj, effect_atoms: List) -> Dict[str, Any]:
    """Handle spell using the new effects engine."""
    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
    from core.effects.effects_engine import apply_effects, TargetContext
    
    queued_events_this_handler = False
    
    # Apply and display resource costs first
    try:
        stamina_spent = current_result_detail.get("stamina_spent", 0)
        mana_spent = current_result_detail.get("mana_spent", 0)
        if stamina_spent and stamina_spent > 0:
            prev_stam = performer_stats_manager.get_current_stat_value(DerivedStatType.STAMINA)
            new_stam = max(0, prev_stam - stamina_spent)
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={},
                metadata={"entity_id": performer.id, "bar_type": "stamina", "old_value": prev_stam, "new_value_preview": new_stam, "max_value": performer.max_stamina}
            ))
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE,
                content={},
                metadata={"entity_id": performer.id, "bar_type": "stamina", "final_new_value": new_stam, "max_value": performer.max_stamina}
            ))
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={},
                metadata={"entity_id": performer.id, "bar_type": "stamina", "final_new_value": new_stam, "max_value": performer.max_stamina}
            ))
            manager._add_to_log(f"{performer.combat_name} spent {stamina_spent:.1f} stamina. Rem: {new_stam:.1f}")
        if mana_spent and mana_spent > 0:
            prev_mp = performer_stats_manager.get_current_stat_value(DerivedStatType.MANA)
            new_mp = max(0, prev_mp - mana_spent)
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={},
                metadata={"entity_id": performer.id, "bar_type": "mana", "old_value": prev_mp, "new_value_preview": new_mp, "max_value": performer.max_mp}
            ))
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE,
                content={},
                metadata={"entity_id": performer.id, "bar_type": "mana", "final_new_value": new_mp, "max_value": performer.max_mp}
            ))
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={},
                metadata={"entity_id": performer.id, "bar_type": "mana", "final_new_value": new_mp, "max_value": performer.max_mp}
            ))
            manager._add_to_log(f"{performer.combat_name} spent {mana_spent:.1f} mana. Rem: {new_mp:.1f}")
    except Exception as e_cost:
        logger.warning(f"Failed to apply/display resource costs after spell cast: {e_cost}")
    
    # Build caster and target contexts
    caster_ctx = TargetContext(
        id=performer.id,
        name=performer.combat_name,
        stats_manager=performer_stats_manager
    )
    
    targets = []
    # Track per-target HP before to drive UI updates and defeat checks later
    target_hp_before: Dict[str, float] = {}
    target_hp_max: Dict[str, float] = {}
    for target_id in action.targets:
        target_entity = manager.entities.get(target_id)
        if target_entity and target_entity.is_alive():
            target_sm = manager._get_entity_stats_manager(target_id)
            if target_sm:
                targets.append(TargetContext(
                    id=target_entity.id,
                    name=target_entity.combat_name,
                    stats_manager=target_sm
                ))
                try:
                    hp_before = float(target_sm.get_current_stat_value(DerivedStatType.HEALTH))
                except Exception:
                    hp_before = float(getattr(target_entity, 'current_hp', 0))
                target_hp_before[target_entity.id] = hp_before
                target_hp_max[target_entity.id] = float(getattr(target_entity, 'max_hp', 1) or 1)
    
    if not targets:
        current_result_detail.update({"success": False, "message": "No valid targets for spell.", "queued_events": queued_events_this_handler})
        return current_result_detail
    
    # Apply effects using the effects engine
    try:
        effect_result = apply_effects(atoms=effect_atoms, caster=caster_ctx, targets=targets)
        
        # Queue effect messages
        spell_name = getattr(spell_obj, 'name', action.name)
        cast_msg = f"{performer.combat_name} casts {spell_name}!"
        engine._combat_orchestrator.add_event_to_queue(
            DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=cast_msg, target_display=DisplayTarget.COMBAT_LOG)
        )
        manager._add_to_log(cast_msg)
        queued_events_this_handler = True
        
        # Display effect results (summarize per atom)
        id_to_name = {t.id: t.name for t in targets}
        for applied in effect_result.applied:
            try:
                atom_type = getattr(applied, 'atom_type', 'effect')
                amount = getattr(applied, 'amount', None)
                target_names = [id_to_name.get(tid, tid) for tid in getattr(applied, 'target_ids', [])]
                tn = ", ".join(target_names) if target_names else "target"
                if atom_type == 'damage' and amount is not None:
                    msg = f"  {tn} takes {abs(amount):.0f} damage."
                elif atom_type == 'heal' and amount is not None:
                    msg = f"  {tn} is healed for {abs(amount):.0f}."
                elif atom_type in ('buff','debuff'):
                    msg = f"  {atom_type.capitalize()} applied to {tn}."
                elif atom_type in ('status_apply','cleanse','status_remove'):
                    name = getattr(applied, 'status_name', None) or atom_type
                    msg = f"  {tn}: {name} applied."
                else:
                    msg = f"  {atom_type.capitalize()} applied to {tn}."
                engine._combat_orchestrator.add_event_to_queue(
                    DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=msg, target_display=DisplayTarget.COMBAT_LOG)
                )
                manager._add_to_log(msg)
                queued_events_this_handler = True
            except Exception:
                pass
        
        # After effects are applied, synchronize HP for each affected target and perform defeat checks
        killed_ids: List[str] = []
        target_summaries: List[Dict[str, Any]] = []
        primary_summary: Optional[Dict[str, Any]] = None
        for idx, target_ctx in enumerate(targets):
            try:
                old_hp = float(target_hp_before.get(target_ctx.id, 0.0))
                new_hp = float(target_ctx.stats_manager.get_current_stat_value(DerivedStatType.HEALTH))
                max_hp_val = float(target_hp_max.get(target_ctx.id, 1.0) or 1.0)
            except Exception:
                # Fallback: read from entity if needed
                entity_fallback = manager.entities.get(target_ctx.id)
                old_hp = float(target_hp_before.get(target_ctx.id, getattr(entity_fallback, 'current_hp', 0.0)))
                new_hp = float(getattr(entity_fallback, 'current_hp', 0.0))
                max_hp_val = float(getattr(entity_fallback, 'max_hp', 1.0) or 1.0)
            
            # Determine per-target deltas
            damage_dealt = max(0.0, old_hp - new_hp)
            defeated_now = new_hp <= 0
            
            # If HP changed, drive UI/model updates
            if abs(new_hp - old_hp) > 1e-6:
                # Apply model sync first so CombatEntity mirrors StatsManager
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                    type=DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE,
                    content={},
                    metadata={"entity_id": target_ctx.id, "bar_type": "hp", "final_new_value": new_hp, "max_value": max_hp_val}
                ))
                # Phase 1 preview and Phase 2 finalize
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                    type=DisplayEventType.UI_BAR_UPDATE_PHASE1,
                    content={},
                    metadata={"entity_id": target_ctx.id, "bar_type": "hp", "old_value": old_hp, "new_value_preview": new_hp, "max_value": max_hp_val}
                ))
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                    type=DisplayEventType.UI_BAR_UPDATE_PHASE2,
                    content={},
                    metadata={"entity_id": target_ctx.id, "bar_type": "hp", "final_new_value": new_hp, "max_value": max_hp_val}
                ))
                queued_events_this_handler = True
            
            # Summarize this target for narrative fallback and debugging
            summary_entry = {
                "target_id": target_ctx.id,
                "target_name": target_ctx.name,
                "hp_before": old_hp,
                "hp_after": new_hp,
                "damage_done": damage_dealt,
                "defeated": defeated_now,
            }
            target_summaries.append(summary_entry)
            if idx == 0:
                primary_summary = summary_entry
            
            # Defeat check using the post-effect HP value (independent of CombatEntity.is_alive())
            if defeated_now:
                killed_ids.append(target_ctx.id)
                target_entity = manager.entities.get(target_ctx.id)
                target_name = getattr(target_entity, 'combat_name', target_ctx.name or 'Target') if target_entity else (target_ctx.name or 'Target')
                defeat_msg = f"{target_name} is defeated by {getattr(spell_obj, 'name', action.name)}!"
                engine._combat_orchestrator.add_event_to_queue(
                    DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=defeat_msg, target_display=DisplayTarget.COMBAT_LOG)
                )
                manager._add_to_log(defeat_msg)
                # Mark inactive in combat
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                    type=DisplayEventType.APPLY_ENTITY_STATE_UPDATE,
                    content={},
                    metadata={"entity_id": target_ctx.id, "is_active_in_combat": False}
                ))
                queued_events_this_handler = True
        
        # Populate current_result_detail for narrator fallback consistency
        try:
            if primary_summary is not None:
                current_result_detail["damage"] = int(round(primary_summary.get("damage_done", 0)))
                current_result_detail["target_hp_before"] = primary_summary.get("hp_before")
                current_result_detail["target_hp_after"] = primary_summary.get("hp_after")
                current_result_detail["target_defeated"] = bool(primary_summary.get("defeated", False))
                # Ensure target_name aligns with the resolved context (if not already set)
                if not current_result_detail.get("target_name"):
                    current_result_detail["target_name"] = primary_summary.get("target_name")
            # Provide a richer list for potential future uses
            current_result_detail["targets_processed"] = target_summaries
        except Exception:
            pass
        
        # Handle combat end conditions based on killed_ids snapshot
        try:
            from core.combat.combat_entity import EntityType
            # If any player got killed -> defeat
            for kid in killed_ids:
                ent = manager.entities.get(kid)
                if ent and ent.entity_type == EntityType.PLAYER:
                    manager.state = CombatState.PLAYER_DEFEAT
                    manager.current_step = CombatStep.ENDING_COMBAT
                    manager.waiting_for_display_completion = True
                    break
            else:
                # Victory if no enemies remain alive after this resolution
                remaining_enemies = [e for e in manager.entities.values()
                                     if e.entity_type == EntityType.ENEMY and e.is_active_in_combat and (e.id not in killed_ids and e.is_alive())]
                if len(remaining_enemies) == 0 and killed_ids:
                    manager.state = CombatState.PLAYER_VICTORY
                    manager.current_step = CombatStep.ENDING_COMBAT
                    manager.waiting_for_display_completion = True
        except Exception:
            pass
        
        if effect_result.success:
            current_result_detail.update({
                "success": True,
                "message": f"{spell_name} was cast successfully.",
                "effects_applied": len(effect_result.applied),
                "queued_events": queued_events_this_handler
            })
        else:
            error_details = "; ".join(effect_result.errors) if effect_result.errors else "Unknown error"
            current_result_detail.update({
                "success": False,
                "message": f"{spell_name} had errors: {error_details}",
                "queued_events": queued_events_this_handler
            })
    except Exception as e:
        logger.error(f"Effects engine error for spell {action.name}: {e}", exc_info=True)
        current_result_detail.update({
            "success": False,
            "message": f"System error casting {action.name}: {e}",
            "queued_events": queued_events_this_handler
        })
    
    return current_result_detail


def _handle_spell_legacy_dice(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handle spells using legacy dice notation approach (fallback)."""
    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
    
    queued_events_this_handler = False
    at_least_one_target_processed = False
    
    # Add targets_processed tracking for legacy compatibility
    if "targets_processed" not in current_result_detail:
        current_result_detail["targets_processed"] = []
        
    for target_id in action.targets:
        target = manager.entities.get(target_id)
        target_processing_summary = {"target_id": target_id, "target_name": "Unknown", "effects_applied": [], "damage_done": 0, "healing_done": 0, "defeated": False}

        if not target:
            logger.warning(f"Target {target_id} not found for spell {action.name}")
            target_processing_summary["error"] = "Target not found"
            current_result_detail["targets_processed"].append(target_processing_summary)
            continue
        
        target_processing_summary["target_name"] = target.combat_name

        if not target.is_alive():
            logger.debug(f"Target {target.combat_name} already defeated, skipping spell effect.")
            target_processing_summary["status"] = "Already defeated"
            current_result_detail["targets_processed"].append(target_processing_summary)
            continue

        target_stats_manager = manager._get_entity_stats_manager(target_id)
        if not target_stats_manager:
            logger.error(f"Could not find StatsManager for target {target_id} of spell {action.name}. Skipping target.")
            target_processing_summary["error"] = "Target StatsManager not found"
            current_result_detail["targets_processed"].append(target_processing_summary)
            continue
            
        target_hp_before_spell = target_stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
        
        if action.dice_notation: 
            at_least_one_target_processed = True 
            base_damage_result = roll_dice_notation(action.dice_notation)

            # Apply and display resource costs (stamina/mana) after spell attempt/roll text
            try:
                stamina_spent = current_result_detail.get("stamina_spent", 0)
                mana_spent = current_result_detail.get("mana_spent", 0)
                if stamina_spent and stamina_spent > 0:
                    prev_stam = performer_stats_manager.get_current_stat_value(DerivedStatType.STAMINA)
                    new_stam = max(0, prev_stam - stamina_spent)
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                        type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={},
                        metadata={"entity_id": performer.id, "bar_type": "stamina", "old_value": prev_stam, "new_value_preview": new_stam, "max_value": performer.max_stamina}
                    ))
                    # Apply model update as a separate orchestrated event
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                        type=DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE,
                        content={},
                        metadata={"entity_id": performer.id, "bar_type": "stamina", "final_new_value": new_stam, "max_value": performer.max_stamina}
                    ))
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                        type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={},
                        metadata={"entity_id": performer.id, "bar_type": "stamina", "final_new_value": new_stam, "max_value": performer.max_stamina}
                    ))
                    manager._add_to_log(f"{performer.combat_name} spent {stamina_spent:.1f} stamina. Rem: {new_stam:.1f}")
                if mana_spent and mana_spent > 0:
                    prev_mp = performer_stats_manager.get_current_stat_value(DerivedStatType.MANA)
                    new_mp = max(0, prev_mp - mana_spent)
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                        type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={},
                        metadata={"entity_id": performer.id, "bar_type": "mana", "old_value": prev_mp, "new_value_preview": new_mp, "max_value": performer.max_mp}
                    ))
                    # Apply model update as a separate orchestrated event
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                        type=DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE,
                        content={},
                        metadata={"entity_id": performer.id, "bar_type": "mana", "final_new_value": new_mp, "max_value": performer.max_mp}
                    ))
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                        type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={},
                        metadata={"entity_id": performer.id, "bar_type": "mana", "final_new_value": new_mp, "max_value": performer.max_mp}
                    ))
                    manager._add_to_log(f"{performer.combat_name} spent {mana_spent:.1f} mana. Rem: {new_mp:.1f}")
            except Exception as e_cost:
                logger.warning(f"Failed to apply/display resource costs after spell roll: {e_cost}")
            base_damage = base_damage_result["total"]
            damage_rolls_str = base_damage_result['rolls_str']
            
            spell_stat_type_str = getattr(action, 'spell_stat_override', 'INTELLIGENCE') 
            spell_stat_type = StatType.from_string(spell_stat_type_str)
            spell_stat_modifier = get_modifier_from_stat(performer_stats_manager.get_stat_value(spell_stat_type))

            total_raw_damage = base_damage + spell_stat_modifier
            raw_dmg_msg = f"  {action.name} raw damage on {target.combat_name}: {total_raw_damage:.0f} ({damage_rolls_str} + {spell_stat_modifier} mod)"
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=raw_dmg_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(raw_dmg_msg)
            queued_events_this_handler = True

            magic_defense_val = target_stats_manager.get_stat_value(DerivedStatType.MAGIC_DEFENSE)
            after_flat = max(0, total_raw_damage - magic_defense_val)
            final_damage = round(after_flat)
            
            mitigation_msg = f"  {target.combat_name} resists ({magic_defense_val:.0f} M.Def). After M.Def: {after_flat:.0f}"
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=mitigation_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(mitigation_msg)
            queued_events_this_handler = True
            
            # Determine damage type for spell (default arcane)
            dmg_type = "arcane"
            try:
                if isinstance(action.special_effects, dict):
                    cand = action.special_effects.get("damage_type")
                    if isinstance(cand, str) and cand.strip():
                        dmg_type = cand.strip().lower()
            except Exception:
                pass
            
            # Apply typed resistance if defined
            try:
                typed_resist = float(target_stats_manager.get_resistance_percent(dmg_type))
            except Exception:
                typed_resist = 0.0
            if abs(typed_resist) > 0.0001:
                after_type = max(0, after_flat * (1 - typed_resist / 100.0))
                final_damage = round(after_type)
                type_msg = f"  Type Resistance ({dmg_type}): {typed_resist:.0f}% -> Final Damage: {final_damage}"
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=type_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(type_msg)
                queued_events_this_handler = True

            if final_damage > 0:
                target_hp_preview = max(0, target_hp_before_spell - final_damage)

                # Optional typed rider for spells
                try:
                    cfg = get_config()
                    rider = cfg.get(f"combat.typed_riders.{dmg_type}")
                except Exception:
                    rider = None
                try:
                    if rider and isinstance(rider, dict) and rider.get("status"):
                        ch = rider.get("chance", 0.0)
                        dur = rider.get("duration", 1)
                        if random.random() < float(ch) and final_damage > 0:
                            status_name = str(rider.get("status"))
                            target_stats_manager.add_status_effect(StatusEffect(name=status_name, description=f"From {action.name}", effect_type=StatusEffectType.SPECIAL, duration=int(dur)))
                            target.add_status_effect(status_name, duration=int(dur))
                            status_msg = f"  {target.combat_name} is now {status_name} due to {action.name}!"
                            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=status_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(status_msg)
                            queued_events_this_handler = True
                except Exception as rider_err:
                    logger.debug(f"Typed rider (spell) failed or skipped: {rider_err}")
                
                # STRICT ORDER: announce damage before bar changes
                damage_taken_msg = f"  {target.combat_name} takes {final_damage:.0f} {dmg_type} damage from {action.name}! (HP: {int(target_hp_preview)}/{int(target.max_hp)})"
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=damage_taken_msg, target_display=DisplayTarget.COMBAT_LOG, gradual_visual_display=True)); manager._add_to_log(damage_taken_msg)
                queued_events_this_handler = True

                # Apply model update AFTER the outcome text is displayed, then animate
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                    type=DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE,
                    content={},
                    metadata={"entity_id": target.id, "bar_type": "hp", "final_new_value": target_hp_preview, "max_value": target.max_hp}
                )); queued_events_this_handler = True

                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={}, metadata={"entity_id": target.id, "bar_type": "hp", "old_value": target_hp_before_spell, "new_value_preview": target_hp_preview, "max_value": target.max_hp})); queued_events_this_handler = True
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={}, metadata={"entity_id": target.id, "bar_type": "hp", "final_new_value": target_hp_preview, "max_value": target.max_hp})); queued_events_this_handler = True
                target_processing_summary["damage_done"] = final_damage

                if target_hp_preview <= 0:
                    defeat_msg = f"{target.combat_name} is defeated by {action.name}!"
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=defeat_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(defeat_msg)
                    queued_events_this_handler = True
                    target_processing_summary["defeated"] = True
                    # Delay removing the entity from active combat until after defeat text
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                        type=DisplayEventType.APPLY_ENTITY_STATE_UPDATE,
                        content={},
                        metadata={"entity_id": target.id, "is_active_in_combat": False}
                    ))
                    # If defeat ends combat (all enemies down or player down), pause and finalize
                    try:
                        from core.combat.combat_entity import EntityType
                        if target.entity_type == EntityType.PLAYER:
                            # Player defeat -> mark end-state and pause then finalize
                            manager.state = CombatState.PLAYER_DEFEAT
                            manager.current_step = CombatStep.ENDING_COMBAT
                            manager.waiting_for_display_completion = True
# Removed pause/finalize events; CM will end via state/step change
                        else:
                            remaining_enemies = [e for e in manager.entities.values() if e.entity_type == EntityType.ENEMY and e.is_active_in_combat and e.is_alive()]
                            if len(remaining_enemies) == 0:
                                manager.state = CombatState.PLAYER_VICTORY
                                manager.current_step = CombatStep.ENDING_COMBAT
                                manager.waiting_for_display_completion = True
# Removed pause/finalize events; CM will end via state/step change
                    except Exception:
                        pass

        for effect_name_key, effect_params in action.special_effects.items():
            at_least_one_target_processed = True
            if effect_name_key == "apply_status": 
                status_to_apply = effect_params.get("name", "UnknownEffect")
                status_duration = effect_params.get("duration") 
                
                target_stats_manager.add_status_effect(StatusEffect(name=status_to_apply, description=f"From {action.name}", effect_type=StatusEffectType.SPECIAL, duration=status_duration))
                target.add_status_effect(status_to_apply, duration=status_duration)
                
                duration_text = f" for {status_duration} turns" if status_duration is not None else ""
                status_msg = f"  {target.combat_name} is now {status_to_apply}{duration_text} due to {action.name}!"
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=status_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(status_msg)
                queued_events_this_handler = True
                target_processing_summary["effects_applied"].append(status_to_apply)
        
        current_result_detail["targets_processed"].append(target_processing_summary)

    if at_least_one_target_processed :
        current_result_detail["success"] = True
        current_result_detail["message"] = f"{action.name} was cast."
    else: 
        current_result_detail["success"] = False
        current_result_detail["message"] = f"{action.name} had no effect or no valid targets."
        no_effect_msg = f"{action.name} is cast by {performer.combat_name}, but has no discernible effect."
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=no_effect_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(no_effect_msg)
        queued_events_this_handler = True


    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail

def _handle_defend_action(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handle the mechanics of a defend action. Queues DisplayEvents."""
    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
    logger.info(f"{performer.combat_name} takes a defensive stance.")
    queued_events_this_handler = False
    
    duration = 1 
    performer_stats_manager.add_status_effect(StatusEffect(name="Defending", description="Taking a defensive stance, improving defense.", effect_type=StatusEffectType.BUFF, duration=duration))
    performer.add_status_effect("Defending", duration=duration) 

    defend_msg = f"  {performer.combat_name} is now Defending."
    # This message is usually covered by the NARRATIVE_IMPACT from CombatNarrator for defend action.
    # If CombatNarrator doesn't provide one, or if a system message is always desired:
    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=defend_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(defend_msg)
    queued_events_this_handler = True
    
    current_result_detail.update({
        "success": True, 
        "message": "Took defensive stance.",
        "effects_applied": [{"type": "status", "name": "Defending", "duration": duration, "target": performer.combat_name}],
        "queued_events": queued_events_this_handler
    })
    return current_result_detail

def _handle_item_action(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handle using an item in combat. Queues DisplayEvents."""
    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
    
    item_id_from_action = action.special_effects.get("item_id", "unknown_item") 
    item_name_from_action = action.name.replace("Use ", "") 
    queued_events_this_handler = False

    item_used_msg = f"{performer.combat_name} uses {item_name_from_action}!"
    # After the item usage line (if used), apply costs if any were recorded

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
                # STRICT ORDER: announce heal before bar changes
                heal_msg = f"  {target.combat_name} is healed for {actual_healed:.0f} HP by {item_name_from_action}! (HP: {int(target_hp_preview)}/{int(target.max_hp)})"
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=heal_msg, target_display=DisplayTarget.COMBAT_LOG, gradual_visual_display=True)); manager._add_to_log(heal_msg)
                queued_events_this_handler = True
                
                # Apply model update AFTER heal message is displayed
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
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=no_heal_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(no_heal_msg)
                queued_events_this_handler = True
        
        if item_effects.get("apply_status"):
            at_least_one_effect_applied = True
            status_to_apply = item_effects["apply_status"].get("name", "UnknownEffect")
            status_duration = item_effects["apply_status"].get("duration")
            
            target_stats_manager.add_status_effect(StatusEffect(name=status_to_apply, description=f"From item {item_name_from_action}", effect_type=StatusEffectType.SPECIAL, duration=status_duration))
            target.add_status_effect(status_to_apply, duration=status_duration)
            
            duration_text = f" for {status_duration} turns" if status_duration is not None else ""
            status_msg = f"  {target.combat_name} is now {status_to_apply}{duration_text} from {item_name_from_action}!"
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=status_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(status_msg)
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
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=no_effect_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(no_effect_msg)
        queued_events_this_handler = True
        
    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail

def _handle_flee_action_mechanics(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handles the mechanics of a flee action attempt. Queues DisplayEvents."""
    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
    from core.game_flow.mode_transitions import _determine_flee_parameters 

    # Populate standard result fields for the bridge/narrator
    current_result_detail.update({
        "performer_name": performer.combat_name,
        "action_name": "Flee",
        "action_type": action.action_type,  # Ensure this matches ActionType.FLEE enum
        "target_name": "N/A",  # Fleeing has no specific target usually
        "target_defeated": False, # Required by bridge logic
        "damage": 0
    })

    if performer.has_status_effect("Immobilized"):
        immobilized_msg = f"  {performer.combat_name} cannot flee, they are immobilized!"
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=immobilized_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(immobilized_msg)
        queued_events_this_handler = True
        current_result_detail["message"] = "Cannot flee while immobilized."
        current_result_detail["success"] = False
        current_result_detail["fled"] = False
        current_result_detail["queued_events"] = queued_events_this_handler
        return current_result_detail # Return immediately

    enemy_entities = [e for e in manager.entities.values() if e.entity_type == EntityType.ENEMY and e.is_alive() and getattr(e, 'is_active_in_combat', True)]
    if not enemy_entities:
        no_enemies_msg = f"{performer.combat_name} looks around... there are no active enemies to flee from. Combat ends."
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=no_enemies_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(no_enemies_msg)
        queued_events_this_handler = True
        # This signals success, but not "fled from danger".
        # CombatManager's main loop (_advance_turn -> _check_combat_state) will set player victory.
        current_result_detail.update({"success": True, "fled": False, "message": "No enemies to flee from."})
        current_result_detail["queued_events"] = queued_events_this_handler
        return current_result_detail

    try:
        # Pass the actual GameState rather than CombatManager to parameter determination
        flee_dc, situational_modifier, modifier_reasons = _determine_flee_parameters(engine._state_manager.current_state, performer)

        # Determine best skill for fleeing (Acrobatics vs Athletics)
        # Default to acrobatics as it's the primary flee skill, but allow athletics if better
        skill_to_use = "acrobatics"
        stat_for_skill = StatType.DEXTERITY
        
        try:
            acrobatics_rank = performer_stats_manager.get_skill_value("acrobatics")
            athletics_rank = performer_stats_manager.get_skill_value("athletics")
            
            if athletics_rank > acrobatics_rank:
                skill_to_use = "athletics"
                stat_for_skill = StatType.STRENGTH
        except Exception:
            # Fallback if get_skill_value fails
            pass

        check_result = performer_stats_manager.perform_skill_check(
            stat_type=stat_for_skill, 
            difficulty=flee_dc,
            situational_modifier=situational_modifier,
            skill_name=skill_to_use
        )
        
        # Construct display string
        modifier_str_display = f"{check_result.modifier} (stat)"
        
        if check_result.situational_modifier != 0:
            modifier_str_display += f" {check_result.situational_modifier:+}"
            reasons_display = []
            if modifier_reasons:
                reasons_display.extend(modifier_reasons)
            
            # Add skill note
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
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=check_roll_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(check_roll_msg)
        queued_events_this_handler = True

        flee_succeeded_mechanically = check_result.success
        current_result_detail["roll_details"] = check_result.to_dict()
        
        if flee_succeeded_mechanically:
            # The "fled" flag in current_result_detail signals to _step_advancing_turn
            # to end combat for the fleeing entity.
            current_result_detail.update({"success": True, "fled": True, "message": "Escape successful!"})
            performer.is_active_in_combat = False # Mark as no longer active
            
            # Delay removing the entity from active combat until after text
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.APPLY_ENTITY_STATE_UPDATE,
                content={},
                metadata={"entity_id": performer.id, "is_active_in_combat": False}
            ))
            
            # Logic to handle combat end if player fled is in CM's _step_narrating_action_outcome / _compute_regular_outcome_next_step
            # But we need to signal that the *actor* has fled.
        else:
            current_result_detail.update({"success": False, "fled": False, "message": "Escape attempt failed."})
            
    except ImportError as ie:
        logger.error(f"ImportError during flee check for {performer.combat_name}: {ie}.")
        err_msg = "System Error performing flee check: Module loading issue."
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=err_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(err_msg)
        queued_events_this_handler = True
        current_result_detail["message"] = err_msg
    except Exception as e:
        logger.exception(f"Error during flee check mechanics for {performer.combat_name}: {e}")
        err_msg = f"System Error performing flee check: {e}"
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=err_msg, target_display=DisplayTarget.COMBAT_LOG)); manager._add_to_log(err_msg)
        queued_events_this_handler = True
        current_result_detail["message"] = err_msg
        
    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail

def _handle_surrender_action_mechanics(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """Handles the mechanics of a surrender attempt. Queues DisplayEvents."""
    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
    from core.stats.stats_base import StatType
    
    # Populate standard result fields for the bridge/narrator
    current_result_detail.update({
        "performer_name": performer.combat_name,
        "action_name": "Surrender",
        "action_type": action.action_type,
        "target_name": "Enemies", 
        "target_defeated": False, 
        "damage": 0
    })
    
    queued_events_this_handler = False

    # Calculate Surrender DC based on enemy strength/will
    surrender_dc = 12 # Base DC
    enemies = [e for e in manager.entities.values() if e.entity_type == EntityType.ENEMY and e.is_alive() and getattr(e, 'is_active_in_combat', True)]
    
    if not enemies:
        no_enemies_msg = f"{performer.combat_name} lays down arms... but there is no one to surrender to. Combat ends."
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=no_enemies_msg, target_display=DisplayTarget.COMBAT_LOG))
        manager._add_to_log(no_enemies_msg)
        current_result_detail.update({"success": True, "surrendered": True, "message": "No enemies to surrender to."})
        current_result_detail["queued_events"] = True
        return current_result_detail

    # Adjust DC based on enemy "ferocity" or level (simplified heuristic)
    # E.g. if any enemy is much higher level or has "Aggressive" trait
    highest_level = 1
    aggro_mod = 0
    for enemy in enemies:
        lvl = getattr(enemy, 'level', 1)
        if lvl > highest_level: highest_level = lvl
        # Placeholder for traits
        if "Undead" in enemy.name: aggro_mod += 5 # Harder to reason with undead
        
    surrender_dc = max(10, 10 + highest_level + aggro_mod)
    
    # Perform Skill Check (Persuasion / Charisma)
    skill_to_use = "persuasion"
    stat_for_skill = StatType.CHARISMA
    
    check_result = performer_stats_manager.perform_skill_check(
        stat_type=stat_for_skill,
        difficulty=surrender_dc,
        skill_name=skill_to_use
    )
    
    # Construct display string
    modifier_str_display = f"{check_result.modifier} (stat)"
    if check_result.skill_exists:
         modifier_str_display += f" ({check_result.skill_name or skill_to_use})"

    check_roll_msg = (
        f"{performer.combat_name} attempts to surrender ({skill_to_use.title()} check DC {surrender_dc}): "
        f"Roll {check_result.roll} + {modifier_str_display} "
        f"= {check_result.total} -> {check_result.outcome_desc}"
    )
    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=check_roll_msg, target_display=DisplayTarget.COMBAT_LOG))
    manager._add_to_log(check_roll_msg)
    queued_events_this_handler = True
    
    current_result_detail["roll_details"] = check_result.to_dict()

    if check_result.success:
        # Explicit clarification for the LLM to avoid "Enemies Surrender" hallucination
        current_result_detail["intent_clarification"] = (
            "The player's surrender was ACCEPTED by the enemies. "
            "The player lays down their arms and submits. "
            "The enemies DO NOT surrender; they have won by forcing the player to submit. "
            "The player is stripped of all equipment as a consequence."
        )
        
        # --- Equipment Stripping Logic ---
        try:
            from core.inventory import get_inventory_manager
            import random
            inv_mgr = get_inventory_manager()
            
            # Collect all items
            items_to_transfer = []
            if hasattr(inv_mgr, 'items'):
                # items can be list or dict depending on version, handle both
                if isinstance(inv_mgr.items, dict):
                    items_to_transfer.extend(list(inv_mgr.items.values()))
                elif isinstance(inv_mgr.items, list):
                    items_to_transfer.extend(inv_mgr.items)
            
            if hasattr(inv_mgr, 'equipment') and isinstance(inv_mgr.equipment, dict):
                for item in inv_mgr.equipment.values():
                    if item: items_to_transfer.append(item)
            
            distribution_log = []
            if items_to_transfer and enemies:
                npc_system = engine.state_manager.get_npc_system()
                for item in items_to_transfer:
                    recipient_entity = random.choice(enemies)
                    # Update persistent NPC data if possible
                    if npc_system:
                        npc_obj = npc_system.get_npc_by_id(recipient_entity.id)
                        if npc_obj:
                            # Assume NPC has 'inventory' list or similar. 
                            # If not, we might need to add it or just log it for now.
                            if not hasattr(npc_obj, 'inventory'):
                                npc_obj.inventory = []
                            # Store item data (simplified)
                            npc_obj.inventory.append(item.to_dict() if hasattr(item, 'to_dict') else str(item))
                            distribution_log.append(f"{item.name} -> {recipient_entity.combat_name}")
                    else:
                        distribution_log.append(f"{item.name} -> {recipient_entity.combat_name}")

                # Clear Player Inventory
                # We can use specific methods if available, or brute force clear for this prototype
                if hasattr(inv_mgr, 'clear_inventory'):
                    inv_mgr.clear_inventory()
                else:
                    # Fallback clear
                    if isinstance(inv_mgr.items, dict): inv_mgr.items.clear()
                    elif isinstance(inv_mgr.items, list): inv_mgr.items.clear()
                
                if hasattr(inv_mgr, 'clear_equipment'):
                    inv_mgr.clear_equipment()
                else:
                    if hasattr(inv_mgr, 'equipment'): inv_mgr.equipment.clear()
                
                # Queue system message about loss
                loss_msg = f"You have been stripped of your belongings! ({len(items_to_transfer)} items lost)"
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=loss_msg, target_display=DisplayTarget.COMBAT_LOG))
                manager._add_to_log(loss_msg)
                current_result_detail["consequences"] = f"Player lost {len(items_to_transfer)} items to enemies."

        except Exception as e:
            logger.error(f"Error stripping player equipment: {e}", exc_info=True)
            current_result_detail["consequences_error"] = f"Error handling equipment loss: {e}"
        # --- End Equipment Stripping ---

        current_result_detail.update({"success": True, "fled": True, "surrendered": True, "message": "Surrender accepted!"})
        performer.is_active_in_combat = False 
        
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
            type=DisplayEventType.APPLY_ENTITY_STATE_UPDATE,
            content={},
            metadata={"entity_id": performer.id, "is_active_in_combat": False}
        ))
    else:
        current_result_detail["intent_clarification"] = "The player attempted to surrender, but the enemies REFUSED. The enemies continue to attack."
        current_result_detail.update({"success": False, "surrendered": False, "message": "Surrender rejected."})

    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail