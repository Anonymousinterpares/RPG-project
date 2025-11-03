#!/usr/bin/env python3
"""
Handles logic related to NPC actions and interactions.
"""

import logging
import json
import re # Import re for cleaning intent
from typing import Optional, TYPE_CHECKING, Dict, Any

from core.interaction.enums import InteractionMode
from core.interaction.context_builder import ContextBuilder
from core.combat.combat_entity import EntityType
from core.agents.base_agent import AgentContext
from core.agents.combat_narrator import get_combat_narrator_agent

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.base.state import GameState
    from core.combat.combat_manager import CombatManager 


logger = logging.getLogger("INTERACTION_PROC") # Keep original logger name


def get_npc_intent(engine: 'GameEngine', game_state: 'GameState', npc_id: str) -> Optional[str]:
    """
    Determine the NPC's intended action using an LLM agent.

    Args:
        engine: The GameEngine instance.
        game_state: The current game state.
        npc_id: The ID of the NPC whose turn it is.

    Returns:
        A string describing the NPC's intended action, or None if failed.
    """
    if not engine._use_llm or engine._agent_manager is None:
        logger.warning(f"LLM disabled or AgentManager not available. Cannot get intent for NPC {npc_id}.")
        if game_state.current_mode == InteractionMode.COMBAT:
            logger.info(f"Using fallback combat intent for NPC {npc_id}: 'Attack the player'")
            return "Attack the player"
        return None

    current_mode = game_state.current_mode
    logger.debug(f"Building context for NPC {npc_id} in mode {current_mode.name}")
    try:
        context_builder = ContextBuilder()
        context = context_builder.build_context(game_state, current_mode, actor_id=npc_id)
        
        # --- FIX: Add dynamic combat context to prompt ---
        dynamic_prompt_additions = ""
        if current_mode == InteractionMode.COMBAT and game_state.combat_manager:
            combat_manager = game_state.combat_manager
            npc_entity = combat_manager.entities.get(npc_id)

            # 1. Determine Valid Targets
            valid_targets = []
            is_npc_hostile = npc_id in combat_manager._enemy_entity_ids
            for entity_id, entity in combat_manager.entities.items():
                if not entity.is_alive():
                    continue
                is_entity_hostile = entity_id in combat_manager._enemy_entity_ids
                if is_npc_hostile != is_entity_hostile: # Add if they are on opposing sides
                    valid_targets.append(entity.combat_name)
            
            if valid_targets:
                dynamic_prompt_additions += f"\n- Valid Targets: {valid_targets}"

            # 2. Determine Affordable Actions
            ap_config = getattr(combat_manager, '_ap_config', {})
            if ap_config.get("enabled", False):
                action_costs = ap_config.get("action_costs", {})
                current_ap = combat_manager.ap_pool.get(npc_id, 0.0)
                affordable_actions = [name for name, cost in action_costs.items() if current_ap >= cost]
                if affordable_actions:
                    dynamic_prompt_additions += f"\n- Affordable Actions (AP Cost): { {name: action_costs[name] for name in affordable_actions} }"
        # --- END FIX ---

        prompt = (
            f"You are the AI controlling the character '{npc_id}'.\n"
            f"Current Situation:\n{json.dumps(context, indent=2, default=str)}\n"
            f"Game Mode: {current_mode.name}\n"
            f"It is currently your turn ('{npc_id}').\n"
            f"--- Your Tactical Options ---"
            f"{dynamic_prompt_additions}\n"
            f"-----------------------------\n"
            f"Based on the situation, your character's likely goals, stats, and available abilities (if known), "
            f"state the *single, specific action* you will take this turn. You MUST choose an action from the 'Affordable Actions' list and a target from the 'Valid Targets' list if applicable. Be concise and action-oriented.\n"
            f"Examples: 'Attack the player with sword', 'Cast Fireball at Qa', 'Use Healing Potion on self', 'Defend', 'Attempt to flee'.\n"
            f"Your Action Intent:" 
        )
        logger.debug(f"Generated NPC intent prompt for {npc_id}:\n{prompt[:500]}...")

        intent_agent_context = AgentContext(
             game_state={}, player_state={}, world_state={},
             player_input=prompt, 
             conversation_history=[], relevant_memories=[], additional_context={}
        )
        intent_response = None
        try:
            narrator_agent = engine._agent_manager._narrator_agent 
            if not narrator_agent:
                raise ValueError("NarratorAgent instance not found in AgentManager.")
            if not hasattr(narrator_agent, '_llm_manager'):
                 raise AttributeError("NarratorAgent does not have _llm_manager attribute.")

            llm_manager = narrator_agent._llm_manager
            
            messages = narrator_agent._prepare_messages(intent_agent_context)

            llm_response = llm_manager.get_completion(
                 messages=messages,
                 provider_type=narrator_agent._provider_type,
                 model=narrator_agent._model or None,
                 temperature=0.5, 
                 max_tokens=50 
            )

            if llm_response and llm_response.content:
                 intent_response = llm_response.content
            else:
                 raise ValueError("LLM returned no content for NPC intent.")

        except Exception as e:
            logger.error(f"Error calling LLM for NPC intent string: {e}", exc_info=True) 
            if current_mode == InteractionMode.COMBAT:
                intent_response = "Attack the player"
                logger.info(f"Using fallback combat intent for NPC {npc_id}: '{intent_response}'")
            else:
                intent_response = None 

        if intent_response:
            cleaned_intent = intent_response.strip()
            cleaned_intent = re.sub(r'^(action intent|my action|action|intent)\s*[:\-]\s*', '', cleaned_intent, flags=re.IGNORECASE)
            cleaned_intent = cleaned_intent.strip('"\'')
            logger.info(f"LLM returned intent string for NPC {npc_id}: '{cleaned_intent}'")
            return cleaned_intent
        else:
            logger.error(f"LLM Agent failed to generate intent string for NPC {npc_id}.")
            return None

    except Exception as e:
        logger.error(f"Error getting NPC intent for {npc_id}: {e}", exc_info=True)
        return None

def trigger_combat_narration(engine: 'GameEngine', game_state: 'GameState', narrative_context: Optional[str] = None):
    """Triggers the CombatNarratorAgent to provide initial combat description."""
    if not engine._use_llm:
        logger.warning("Cannot trigger combat narration: LLM disabled.")
        # Basic fallback message
        enemy_names = "some enemies"
        if game_state.combat_manager:
             enemies = [e.name for e in game_state.combat_manager.entities.values() if e.entity_type == EntityType.ENEMY]
             if enemies: enemy_names = ', '.join(enemies)
        engine._output("gm", f"Combat begins against {enemy_names}!")
        return

    # Use the Combat Narrator Agent instance from the engine if available
    combat_narrator = getattr(engine, '_combat_narrator_agent', None)
    if combat_narrator is None:
        logger.error("CombatNarratorAgent not found on engine. Cannot trigger narration.")
        engine._output("system", "Error: Combat narrator is unavailable.")
        return

    logger.info("Triggering CombatNarratorAgent for initial combat description.")
    try:
        context_builder = ContextBuilder()
        context_dict = context_builder.build_context(game_state, InteractionMode.COMBAT)

        # Use a system event description as the "input"
        player_input_event = "[System Event: Combat Started]"
        if narrative_context:
            player_input_event += f"\nInitial Context: {narrative_context}"


        agent_context = AgentContext(
            game_state=context_dict, # Pass the built dictionary
            player_state=context_dict.get('player', {}),
            world_state={k: v for k, v in context_dict.items() if k in ['location', 'time_of_day', 'environment']},
            player_input=player_input_event,
            conversation_history=game_state.conversation_history,
            relevant_memories=[],
            additional_context=context_dict # Pass the full context here too
        )

        # Call the CombatNarratorAgent's process method
        agent_output = combat_narrator.process(agent_context) # Use the instance variable

        if agent_output and agent_output.get("narrative"):
            logger.info("CombatNarratorAgent provided initial narration.")
            engine._output("gm", agent_output["narrative"])
            # Process initial requests if needed (e.g., surprise checks derived from narration)
            # initial_requests = agent_output.get("requests", [])
            # if initial_requests: ... process ...
        else:
            logger.warning("CombatNarratorAgent failed to provide initial narration (or returned empty).")
            # Fallback message
            enemy_names = "some enemies"
            if game_state.combat_manager:
                 enemies = [e.name for e in game_state.combat_manager.entities.values() if e.entity_type == EntityType.ENEMY]
                 if enemies: enemy_names = ', '.join(enemies)
            engine._output("gm", f"Combat begins against {enemy_names}!")

    except Exception as e:
        logger.error(f"Error triggering combat narration: {e}", exc_info=True)
        engine._output("system", f"Error generating combat start narration: {e}")