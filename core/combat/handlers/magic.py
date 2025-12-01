import random
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from core.stats.combat_effects import StatusEffect, StatusEffectType
from core.stats.derived_stats import get_modifier_from_stat
from core.stats.stats_base import StatType, DerivedStatType
from core.utils.dice import roll_dice_notation
from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_action import CombatAction
from core.base.config import get_config
from core.orchestration.events import DisplayEvent, DisplayEventType
from core.effects.effects_engine import apply_effects, TargetContext

# Relative import for shared resource logic
from .resource_utils import apply_and_display_costs

if TYPE_CHECKING:
    from core.combat.combat_manager import CombatManager
    from core.stats.stats_manager import StatsManager
    from core.base.engine import GameEngine
from core.utils.logging_config import get_logger

logger = get_logger(__name__)

# -----------------------------------------------------------------------------
# Main Handler Function
# -----------------------------------------------------------------------------

def handle_spell_action(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict) -> Dict[str, Any]:
    """
    Handle a spell casting action. 
    Dispatches to Effects Engine if available, else Legacy.
    """
    queued_events_this_handler = False
    handler_result_summary = {"success": False, "message": "Spell casting failed or target invalid."} 
    current_result_detail.update(handler_result_summary) 

    if "targets_processed" not in current_result_detail:
        current_result_detail["targets_processed"] = []

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

# -----------------------------------------------------------------------------
# Internal Helper Functions
# -----------------------------------------------------------------------------

def _handle_spell_with_effects_engine(manager: 'CombatManager', action: CombatAction, performer: CombatEntity, performer_stats_manager: 'StatsManager', engine: 'GameEngine', current_result_detail: Dict, spell_obj, effect_atoms: List) -> Dict[str, Any]:
    """Handle spell using the new effects engine."""
    from core.combat.enums import CombatState, CombatStep
    
    queued_events_this_handler = False
    
    # Apply and display resource costs first (shared utility)
    apply_and_display_costs(manager, performer, performer_stats_manager, engine, current_result_detail)
    
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
        manager._log_and_dispatch_event(cast_msg, DisplayEventType.SYSTEM_MESSAGE)
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
                
                manager._log_and_dispatch_event(msg, DisplayEventType.SYSTEM_MESSAGE)
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
                manager._log_and_dispatch_event(defeat_msg, DisplayEventType.SYSTEM_MESSAGE)
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
    from core.combat.enums import CombatState, CombatStep
    
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

            # Apply and display resource costs (shared utility)
            apply_and_display_costs(manager, performer, performer_stats_manager, engine, current_result_detail)

            base_damage = base_damage_result["total"]
            damage_rolls_str = base_damage_result['rolls_str']
            
            spell_stat_type_str = getattr(action, 'spell_stat_override', 'INTELLIGENCE') 
            spell_stat_type = StatType.from_string(spell_stat_type_str)
            spell_stat_modifier = get_modifier_from_stat(performer_stats_manager.get_stat_value(spell_stat_type))

            total_raw_damage = base_damage + spell_stat_modifier
            raw_dmg_msg = f"  {action.name} raw damage on {target.combat_name}: {total_raw_damage:.0f} ({damage_rolls_str} + {spell_stat_modifier} mod)"
            manager._log_and_dispatch_event(raw_dmg_msg, DisplayEventType.SYSTEM_MESSAGE)
            queued_events_this_handler = True

            magic_defense_val = target_stats_manager.get_stat_value(DerivedStatType.MAGIC_DEFENSE)
            after_flat = max(0, total_raw_damage - magic_defense_val)
            final_damage = round(after_flat)
            
            mitigation_msg = f"  {target.combat_name} resists ({magic_defense_val:.0f} M.Def). After M.Def: {after_flat:.0f}"
            manager._log_and_dispatch_event(mitigation_msg, DisplayEventType.SYSTEM_MESSAGE)
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
                manager._log_and_dispatch_event(type_msg, DisplayEventType.SYSTEM_MESSAGE)
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
                            manager._log_and_dispatch_event(status_msg, DisplayEventType.SYSTEM_MESSAGE)
                            queued_events_this_handler = True
                except Exception as rider_err:
                    logger.debug(f"Typed rider (spell) failed or skipped: {rider_err}")
                
                # STRICT ORDER: announce damage before bar changes
                damage_taken_msg = f"  {target.combat_name} takes {final_damage:.0f} {dmg_type} damage from {action.name}! (HP: {int(target_hp_preview)}/{int(target.max_hp)})"
                manager._log_and_dispatch_event(damage_taken_msg, DisplayEventType.SYSTEM_MESSAGE, gradual=True)
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
                    manager._log_and_dispatch_event(defeat_msg, DisplayEventType.SYSTEM_MESSAGE)
                    queued_events_this_handler = True
                    target_processing_summary["defeated"] = True
                    # Delay removing the entity from active combat until after defeat text
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                        type=DisplayEventType.APPLY_ENTITY_STATE_UPDATE,
                        content={},
                        metadata={"entity_id": target.id, "is_active_in_combat": False}
                    ))
                    # If defeat ends combat
                    try:
                        from core.combat.combat_entity import EntityType
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

        for effect_name_key, effect_params in action.special_effects.items():
            at_least_one_target_processed = True
            if effect_name_key == "apply_status": 
                status_to_apply = effect_params.get("name", "UnknownEffect")
                status_duration = effect_params.get("duration") 
                
                target_stats_manager.add_status_effect(StatusEffect(name=status_to_apply, description=f"From {action.name}", effect_type=StatusEffectType.SPECIAL, duration=status_duration))
                target.add_status_effect(status_to_apply, duration=status_duration)
                
                duration_text = f" for {status_duration} turns" if status_duration is not None else ""
                status_msg = f"  {target.combat_name} is now {status_to_apply}{duration_text} due to {action.name}!"
                manager._log_and_dispatch_event(status_msg, DisplayEventType.SYSTEM_MESSAGE)
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
        manager._log_and_dispatch_event(no_effect_msg, DisplayEventType.SYSTEM_MESSAGE)
        queued_events_this_handler = True


    current_result_detail["queued_events"] = queued_events_this_handler
    return current_result_detail