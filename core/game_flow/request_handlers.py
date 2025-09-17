#!/usr/bin/env python3
"""
Handles execution of validated structured requests (skill checks, state changes).
"""

import logging
from typing import Dict, List, Optional, Any, TYPE_CHECKING

# --- Core Imports ---
from core.stats.combat_effects import StatusEffect, StatusEffectType
from core.stats.enums import Skill
from core.stats.stats_base import StatType, DerivedStatType
from core.stats.stats_manager import get_stats_manager
from core.interaction.enums import InteractionMode
from core.interaction.social_effects import SocialStatusEffect
from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_manager import CombatManager
from core.combat.enums import CombatState
from core.combat.combat_action import CombatAction, ActionType, AttackAction # Import relevant actions

# --- Utils ---
from core.game_flow.game_flow_utils import get_participant_by_id

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.base.state import GameState

# --- Logger ---
logger = logging.getLogger("INTERACTION_PROC") # Keep original logger name


def _process_skill_check_request(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """
    Processes a skill check request by constructing and performing the corresponding
    CombatAction via the CombatManager. Uses combat_name for lookups.
    """
    skill_name_str = request.get("skill_name")
    # --- MODIFICATION: Get names instead of IDs ---
    actor_combat_name = request.get("actor_id") # This field now holds the combat_name
    target_combat_name = request.get("target_actor_id")
    # --- END MODIFICATION ---
    context_msg = request.get("context", f"Attempting {skill_name_str or 'skill check'}")

    logger.debug(f"Processing SkillCheckRequest for actor '{actor_combat_name}': {request}")

    try:
        if not skill_name_str: raise ValueError("Missing 'skill_name'")
        if not game_state.combat_manager: raise ValueError("CombatManager not found in GameState.")
        if not actor_combat_name: raise ValueError("Missing 'actor_id' (combat_name) in request")

        # --- MODIFICATION: Find entities by combat_name ---
        actor = game_state.combat_manager._find_entity_by_combat_name(actor_combat_name)
        if not actor: raise ValueError(f"Actor '{actor_combat_name}' not found in combat.")
        actor_internal_id = actor.id # Get the actual UUID

        target = None
        target_internal_id = None
        is_attack_skill = skill_name_str.upper() in ["MELEE_ATTACK", "RANGED_ATTACK", "UNARMED_ATTACK", "SPELL_ATTACK"]
        if is_attack_skill:
            if not target_combat_name:
                raise ValueError(f"Attack skill '{skill_name_str}' requires a target_actor_id (combat_name).")
            target = game_state.combat_manager._find_entity_by_combat_name(target_combat_name)
            if not target:
                 # Allow action to proceed but log error and potentially return specific message
                 logger.error(f"Target '{target_combat_name}' not found for skill check {skill_name_str}.")
                 # Return error message immediately, prevents further processing with invalid target
                 return f"Action failed: Target '{target_combat_name}' not found."
            target_internal_id = target.id # Get the actual UUID
        # --- END MODIFICATION ---

        action_to_perform: Optional[CombatAction] = None
        skill_upper = skill_name_str.upper()

        if is_attack_skill:
            # Use internal UUIDs for the action
            action_to_perform = AttackAction(
                performer_id=actor_internal_id,
                target_id=target_internal_id,
                weapon_name=request.get("weapon_name", skill_name_str),
                dice_notation=request.get("dice_notation", "1d6"),
            )
            action_to_perform.action_type = ActionType.ATTACK
        elif skill_upper == "DEFENSE":
             logger.warning("DEFENSE skill check request currently not linked to a CombatAction.")
             return f"{actor.combat_name} attempts to defend (DEFENSE check not fully implemented)."
        elif skill_upper == "DODGE":
             logger.warning("DODGE skill check request currently not linked to a CombatAction.")
             return f"{actor.combat_name} attempts to dodge (DODGE check not fully implemented)."
        else:
             logger.warning(f"Unhandled skill check request type for direct action: {skill_name_str}. Processing as generic check.")
             return f"System Error: Skill check '{skill_name_str}' cannot be directly performed as a combat action in this context."

        if action_to_perform:
            logger.info(f"Attempting to perform action via CombatManager: {action_to_perform.name} by {actor.combat_name} ({actor_internal_id})")
            action_result = game_state.combat_manager.perform_action(action_to_perform)

            # --- Format Narrative from Action Result (Uses combat_names) ---
            performer_name_display = action_result.get("performer", actor.combat_name)
            target_name_display = action_result.get("target", target.combat_name if target else "target")

            if action_result.get("success"):
                damage = action_result.get("damage", 0)
                hp_remaining_val = action_result.get("target_hp_remaining", '?')
                hp_remaining = f"{hp_remaining_val:.0f}" if isinstance(hp_remaining_val, (int, float)) else '?'
                max_hp_val = action_result.get("target_max_hp", '?') # Assuming result might include max hp
                max_hp = f"{max_hp_val:.0f}" if isinstance(max_hp_val, (int, float)) else '?'
                target_defeated = action_result.get("target_defeated", False)
                crit_str = " Critically!" if action_result.get("is_critical") else ""

                if damage > 0:
                    narrative = f"{performer_name_display} hits {target_name_display}{crit_str} for {damage} damage."
                    if target_defeated: narrative += f" {target_name_display} is defeated!"
                    else: narrative += f" (HP: {hp_remaining}/{max_hp})"
                else:
                    narrative = f"{performer_name_display}'s attack hits {target_name_display} but deals no damage."

                stamina_cost_val = action_result.get('stamina_cost')
                stamina_rem_val = action_result.get('stamina_remaining')
                stamina_cost_str = f"{stamina_cost_val:.1f}" if isinstance(stamina_cost_val, (int, float)) else '?'
                stamina_rem_str = f"{stamina_rem_val:.1f}" if isinstance(stamina_rem_val, (int, float)) else '?'
                narrative += f" (Stamina Cost: {stamina_cost_str}, Remaining: {stamina_rem_str})"

            else: # Action failed
                narrative = action_result.get("message", f"{performer_name_display}'s action failed.")
                stamina_cost_val = action_result.get('stamina_cost')
                stamina_rem_val = action_result.get('stamina_remaining')
                if stamina_cost_val is not None and stamina_rem_val is not None:
                    stamina_cost_str = f"{stamina_cost_val:.1f}" if isinstance(stamina_cost_val, (int, float)) else '?'
                    stamina_rem_str = f"{stamina_rem_val:.1f}" if isinstance(stamina_rem_val, (int, float)) else '?'
                    narrative += f" (Stamina Cost: {stamina_cost_str}, Remaining: {stamina_rem_str})"

            logger.info(f"Skill Check Action Result Narrative: {narrative}")
            return narrative
        else:
            logger.error(f"No CombatAction constructed for skill check request: {request}")
            return f"System Error: Could not determine action for skill '{skill_name_str}'."

    except ValueError as e:
        logger.error(f"Validation error processing SkillCheckRequest {request}: {e}")
        return f"System Error: Invalid skill check request ({e})."
    except AttributeError as e:
         logger.error(f"Missing attribute processing SkillCheckRequest {request}: {e}", exc_info=True)
         return f"System Error: Missing data for skill check ({e})."
    except Exception as e:
        logger.error(f"Unexpected error performing skill check {request}: {e}", exc_info=True)
        return f"System Error: Unexpected error during {skill_name_str or 'skill'} check."

def _process_state_change_request(engine: 'GameEngine', game_state: 'GameState', request: Dict[str, Any], effective_actor_id: str) -> str:
    """Processes a single state change request and returns the narrative result. Uses combat_name."""
    # --- MODIFICATION: Get combat_name instead of ID ---
    target_combat_name = request.get("target_entity")
    # --- END MODIFICATION ---
    attribute = request.get("attribute")
    value = request.get("value")
    duration_str = request.get("duration")

    duration_int: Optional[int] = None
    if duration_str is not None:
        try:
            duration_int = int(duration_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid duration format '{duration_str}' in state change request. Ignoring duration.")

    logger.debug(f"Processing StateChangeRequest: {request}")
    if not target_combat_name or not attribute: # Check name
        logger.error(f"StateChangeRequest missing target_entity (combat_name) or attribute: {request}")
        return "System Error: State change request is incomplete."

    try:
        # --- MODIFICATION: Find participant by combat_name ---
        if not game_state.combat_manager: raise ValueError("CombatManager not found.")
        participant = game_state.combat_manager._find_entity_by_combat_name(target_combat_name)
        if not participant:
            # Check if the target is the effective actor (e.g., applying buff to self)
            effective_actor = game_state.combat_manager._find_entity_by_combat_name(effective_actor_id) # Find actor by name
            if effective_actor and effective_actor.combat_name == target_combat_name:
                 participant = effective_actor
                 logger.debug(f"State change target is the actor themselves: {target_combat_name}")
            else:
                 raise ValueError(f"Target entity '{target_combat_name}' not found.")
        # --- END MODIFICATION ---

        target_internal_id = participant.id # Get the actual internal ID
        change_applied = False
        change_narrative = ""
        participant_name_display = participant.combat_name # Use combat name for display

        # Get the StatsManager for the target participant
        stats_manager = engine._get_entity_stats_manager(target_internal_id) # Use internal ID
        if not stats_manager:
            raise ValueError(f"Could not get StatsManager for target '{participant_name_display}' ({target_internal_id}).")

        # --- Apply State Change (using StatsManager) ---
        if attribute == "hp":
            try:
                delta = float(value)
                current_hp = stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
                new_hp = current_hp + delta
                set_ok = stats_manager.set_current_stat(DerivedStatType.HEALTH, new_hp)

                if set_ok:
                    final_hp = stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
                    max_hp = stats_manager.get_stat_value(DerivedStatType.MAX_HEALTH)
                    if delta < 0:
                         change_narrative = f"{participant_name_display} takes {abs(delta):.0f} damage. Current HP: {final_hp:.0f}/{max_hp:.0f}."
                    else:
                         change_narrative = f"{participant_name_display} heals {delta:.0f} HP. Current HP: {final_hp:.0f}/{max_hp:.0f}."
                    change_applied = True
                    if final_hp <= 0 and game_state.combat_manager:
                         # Ensure combat entity HP also reflects 0
                         combat_entity = game_state.combat_manager.get_entity_by_id(target_internal_id)
                         if combat_entity: combat_entity.current_hp = 0
                         change_narrative += f" {participant_name_display} is defeated!"
                         if hasattr(game_state.combat_manager, '_check_combat_state'):
                              game_state.combat_manager._check_combat_state()
                else:
                    change_narrative = f"System Error: Failed to apply HP change to {participant_name_display}."
            except (ValueError, TypeError):
                 change_narrative = f"System Error: Invalid HP change value '{value}'."

        elif attribute == "stamina":
            try:
                delta = float(value)
                current_stamina = stats_manager.get_current_stat_value(DerivedStatType.STAMINA)
                new_stamina = current_stamina + delta
                set_ok = stats_manager.set_current_stat(DerivedStatType.STAMINA, new_stamina)

                if set_ok:
                    final_stamina = stats_manager.get_current_stat_value(DerivedStatType.STAMINA)
                    max_stamina = stats_manager.get_stat_value(DerivedStatType.MAX_STAMINA)
                    if delta < 0:
                        change_narrative = f"{participant_name_display} spends {abs(delta):.1f} stamina. Remaining: {final_stamina:.1f}/{max_stamina:.1f}."
                    else:
                        change_narrative = f"{participant_name_display} recovers {delta:.1f} stamina. Current: {final_stamina:.1f}/{max_stamina:.1f}."
                    change_applied = True
                else:
                    if delta < 0 and current_stamina < abs(delta):
                         change_narrative = f"{participant_name_display} does not have enough stamina (Needs {abs(delta):.1f}, Has {current_stamina:.1f})."
                    else:
                         change_narrative = f"System Error: Failed to apply Stamina change to {participant_name_display}."
            except (ValueError, TypeError):
                 change_narrative = f"System Error: Invalid Stamina change value '{value}'."

        elif attribute == "add_status_effect":
            if isinstance(value, str):
                effect_name = value
                # Pass converted integer duration
                stats_manager.add_status_effect(StatusEffect(name=effect_name, description=f"Applied {effect_name}", effect_type=StatusEffectType.SPECIAL, duration=duration_int if duration_int is not None else -1))
                # Also update the CombatEntity's local status_effects dict
                participant.add_status_effect(effect_name, duration=duration_int)
                duration_str_narrative = f" for {duration_int} turns" if duration_int is not None else ""
                change_narrative = f"{participant_name_display} is now afflicted with {effect_name}{duration_str_narrative}."
                change_applied = True
            else:
                change_narrative = f"System Error: Invalid status effect name '{value}'."

        elif attribute == "remove_status_effect":
            if isinstance(value, str):
                effect_name = value
                removed_count = stats_manager.status_effect_manager.remove_effects_by_name(effect_name)
                # Also remove from CombatEntity's local status_effects dict
                participant.remove_status_effect(effect_name)
                if removed_count > 0:
                     change_narrative = f"{participant_name_display} is no longer affected by {effect_name}."
                     change_applied = True
                else:
                     change_narrative = f"{participant_name_display} was not affected by {effect_name}."
            else:
                change_narrative = f"System Error: Invalid status effect name '{value}'."

        # Add Social Effect / Remove Social Effect (These might need specific logic if not handled by StatsManager)
        # elif attribute == "add_social_effect":
        #      # TODO: Implement social effect handling, potentially on NPC state or a dedicated system
        #      change_narrative = f"Applying social effect '{value}' to {participant_name} (Not fully implemented)."
        #      logger.warning(f"Social effect application for '{value}' on {target_entity_id} not fully implemented.")

        # elif attribute == "remove_social_effect":
        #      # TODO: Implement social effect removal
        #      change_narrative = f"Removing social effect '{value}' from {participant_name} (Not fully implemented)."
        #      logger.warning(f"Social effect removal for '{value}' on {target_entity_id} not fully implemented.")

        # else:
        #     # Fallback for unhandled attributes
        #     logger.warning(f"Unhandled StateChangeRequest attribute: {attribute} for target {participant_name}")
        #     change_narrative = f"State change requested for {target_entity_id}.{attribute} (Unhandled)."

        # Output the narrative result of the state change
        if change_narrative:
            engine._output("system", change_narrative)
        return ""

    except ValueError as e:
         logger.error(f"Invalid value or target in StateChangeRequest: {request} ({e})")
         return f"System Error: Invalid state change request ({e})."
    except AttributeError as e:
        logger.error(f"Missing attribute processing StateChangeRequest {request}: {e}", exc_info=True)
        return f"System Error: Cannot modify {attribute} for {target_combat_name} ({e})."
    except Exception as e:
        logger.error(f"Error applying state change {request}: {e}", exc_info=True)
        return f"Error applying state change for {target_combat_name}.{attribute}."