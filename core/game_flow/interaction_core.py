#!/usr/bin/env python3
"""
Core interaction processing loop and main entry points for natural language input.
"""

import json
import logging
from typing import Optional, TYPE_CHECKING, Dict, Any, List, Tuple

from core.base.commands import CommandResult
from core.interaction.enums import InteractionMode
from core.interaction.context_builder import ContextBuilder
from core.interaction.structured_requests import AgentOutput 
from core.agents.base_agent import AgentContext
from core.agents.rule_checker import RuleCheckerAgent
from core.base.state import GameState
from core.game_flow.mode_transitions import _handle_transition_request
from core.game_flow.request_handlers import _process_skill_check_request, _process_state_change_request


if TYPE_CHECKING:
    from core.base.engine import GameEngine

logger = logging.getLogger("INTERACTION_PROC") # Keep original logger name for minimal changes

# --- Helper Functions (General) ---

def should_narrative_use_unified_loop(intent: str) -> bool:
    """
    Placeholder function to determine if narrative input requires
    the full unified loop (validation, checks, state changes).
    """
    # TODO: Implement logic to detect narrative requiring specific actions
    # based on keywords, context analysis, or LLM output flags.
    return False # Default to standard narrative processing

# --- Core Interaction Processing ---

def process_interactive_text(engine: 'GameEngine', command_text: str) -> CommandResult:
    """
    Process interactive text input, potentially using LLM.
    
    Args:
        engine: The GameEngine instance.
        command_text: The player's input text.
        
    Returns:
        CommandResult with the response.
    """
    if not engine._state_manager or not engine._state_manager.current_state:
        logger.error("Cannot process interactive text: No current game state.")
        return CommandResult.error("No game in progress.")

    current_game_state = engine._state_manager.current_state

    if engine._use_llm:
        logger.info(f"Processing interactive text with LLM: {command_text[:100]}...")
        # Pass the actual GameState object to process_with_llm
        return process_with_llm(current_game_state, command_text)
    else:
        # Handle non-LLM interactive text (e.g., simple parser, keyword matching)
        # For now, just echo back or provide a canned response
        logger.info(f"LLM disabled. Echoing interactive text: {command_text[:100]}...")
        return CommandResult.success(f"You said: {command_text}")
    
def process_with_llm(game_state: GameState, player_input: str) -> CommandResult:
    """
    Process player input using the LLM agent manager.

    Args:
        game_state: The current game state.
        player_input: The player's input text.

    Returns:
        CommandResult with the LLM's response.
    """
    # Import get_game_engine here to ensure it's available
    from core.base.engine import get_game_engine
    engine = get_game_engine() # Get the engine instance

    if not engine:
        logger.error("GameEngine instance not found in process_with_llm.")
        return CommandResult.error("System error: Game engine unavailable.")

    if not engine._agent_manager:
        logger.error("AgentManager not initialized in process_with_llm.")
        return CommandResult.error("System error: Agent manager unavailable.")

    if not game_state: # Should have been checked by caller, but good to be safe
        logger.error("GameState not provided to process_with_llm.")
        return CommandResult.error("System error: Game state unavailable.")

    logger.info(f"Processing with LLM: {player_input[:100]}...")
    logger.info("LIFECYCLE_DEBUG: Sending request to LLM agent manager")
    
    try:
        # Process the input through the agent manager
        logger.info("LIFECYCLE_DEBUG: About to call agent_manager.process_input()")
        response_text, commands = engine._agent_manager.process_input(
            game_state=game_state, 
            player_input=player_input
        )
        logger.info(f"LIFECYCLE_DEBUG: Received LLM response - Length: {len(response_text) if response_text else 0} chars")
        logger.info(f"LIFECYCLE_DEBUG: Response preview: '{response_text[:150] if response_text else 'None'}...'")
        logger.info(f"LIFECYCLE_DEBUG: Commands returned: {len(commands) if commands else 0}")
        
        # For now, we're primarily interested in the response text.
        # Command processing from LLM output will be handled by the engine
        # if this function is called as part of a larger command processing flow.
        # If called directly for narration (like in lifecycle), commands might be ignored
        # or handled differently depending on context.
        
        if commands:
            logger.info(f"LLM response included {len(commands)} commands: {commands}")
            # Here, we could potentially process these commands immediately if needed,
            # or pass them up for the main game loop to handle.
            # For initial welcome narration, commands are less likely/important.
            # For general input, GameEngine.process_command would handle them.
            
            # If this function is meant to also execute commands, we'd need engine access here.
            # For now, assuming lifecycle uses this primarily for narrative generation.
            # The CommandResult can carry these commands if needed.
            pass # Commands are noted but not processed directly within this function.

        result = CommandResult.success(response_text, data={"commands": commands})
        logger.info(f"LIFECYCLE_DEBUG: Returning CommandResult - Success: {result.is_success}, Message length: {len(result.message) if result.message else 0}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing input with LLM: {e}", exc_info=True)
        logger.error("LIFECYCLE_DEBUG: Exception in process_with_llm, returning error result")
        return CommandResult.error(f"LLM processing error: {e}")
    
# --- Unified Loop Helper Functions ---

def _build_interaction_context(game_state: 'GameState', current_mode: InteractionMode, actor_id: Optional[str]) -> Dict[str, Any]:
    """Builds the context dictionary for the current interaction."""
    logger.debug(f"Building context for Actor: {actor_id}, Mode: {current_mode.name}")
    context_builder = ContextBuilder()
    context = context_builder.build_context(game_state, current_mode, actor_id=actor_id)
    logger.debug("Context built successfully.")
    return context

def _get_agent_response(engine: 'GameEngine', game_state: 'GameState', context: Dict[str, Any], intent: str, current_mode: InteractionMode) -> Optional[AgentOutput]:
    """Calls the appropriate LLM agent based on the mode and returns the structured output."""
    logger.debug(f"Getting agent response for Mode: {current_mode.name}, Intent: '{intent}'")
    agent_context = AgentContext(
        game_state=context, # Pass context dict as game_state for agent
        player_state=context.get('player', {}),
        world_state={
            'location': context.get('location'),
            'time_of_day': context.get('time_of_day'),
            'environment': context.get('environment')
        },
        player_input=intent, # Use the intent as the input
        conversation_history=game_state.conversation_history,
        relevant_memories=[], # Placeholder
        additional_context=context
    )

    agent_output: Optional[AgentOutput] = None
    # Select appropriate agent
    if current_mode == InteractionMode.COMBAT and engine._combat_narrator_agent:
        logger.debug(f"Using CombatNarratorAgent for mode {current_mode.name}")
        agent_output = engine._combat_narrator_agent.process(agent_context)
    # TODO: Add elif for SOCIAL_CONFLICT, TRADE agents
    else:
        # Fallback to default AgentManager (likely Narrator)
        logger.debug(f"Using default AgentManager processing for mode {current_mode.name}")
        # Note: This path might need refinement if default agents should also produce structured requests.
        # The default process_input returns narrative and a list of commands (strings), not AgentOutput
        response_text, commands = engine._agent_manager.process_input(
            game_state=game_state, # Pass original state here? Or context? Needs clarification.
            player_input=intent
        )
        # Reconstruct basic AgentOutput - assumes default path doesn't give structured requests
        agent_output = {"narrative": response_text, "requests": []} # Assuming default agent doesn't return structured requests yet


    if not agent_output:
        logger.error("LLM Agent did not return structured output.")
        return None

    # Log the received output
    logger.debug(f"Agent Output received (JSON): {json.dumps(agent_output, indent=2)}")
    narrative_snippet = agent_output.get('narrative', '')[:50]
    requests_list = agent_output.get('requests', [])
    logger.debug(f"Agent Output received. Narrative: '{narrative_snippet}...', Requests: {len(requests_list)}")

    return agent_output

def _validate_agent_action(engine: 'GameEngine', context: Dict[str, Any], agent_output: AgentOutput, intent: str) -> tuple[bool, str]:
    """Validates the agent's proposed action using the RuleCheckerAgent."""
    logger.debug(f"Validating agent action. Intent: '{intent}', Output: {json.dumps(agent_output, indent=2)}")

    # Prepare validation context, embedding the structured request in the input
    validation_input = f"Action intent: {intent}\nStructured requests: {json.dumps(agent_output.get('requests', []), indent=2)}"
    validation_context = AgentContext(
        game_state=context,
        player_state=context.get('player', {}),
        world_state={
            'location': context.get('location'),
            'time_of_day': context.get('time_of_day'),
            'environment': context.get('environment')
        },
        player_input=validation_input,
        conversation_history=context.get('conversation_history', []), # Get history from context if available
        relevant_memories=[], # Placeholder
        additional_context=context
    )

    # Ensure rule checker agent is available
    if not engine._rule_checker:
        logger.error("RuleCheckerAgent not available for validation.")
        # In a real game, this might be a critical error or allow actions without validation
        # For now, assume validation fails if the agent isn't there.
        return False, "System Error: Rule checker is not available."


    is_valid, validation_feedback = engine._rule_checker.validate_action(validation_context)

    if not is_valid:
        logger.warning(f"Action validation failed: {validation_feedback}")
    else:
        logger.debug("Action validation successful.")

    return is_valid, validation_feedback

# Modify _execute_validated_requests in core/game_flow/interaction_core.py
def _execute_validated_requests(engine: 'GameEngine', game_state: 'GameState', agent_output: AgentOutput, effective_actor_id: str, intent: str) -> list[str]:
    """Processes the validated requests from the agent output."""
    final_narrative_parts = []
    requests_list = agent_output.get('requests', [])
    initial_narrative = agent_output.get('narrative', '') # CAPTURE initial narrative

    logger.debug(f"Executing {len(requests_list)} validated requests for actor {effective_actor_id}.")
    logger.info(f"Request list contents: {json.dumps(requests_list, indent=2)}")

    # --- Separate request types ---
    mode_transitions = []
    other_requests = []
    data_retrieval_requests = []

    for request in requests_list:
        if not isinstance(request, dict):
            logger.warning(f"Skipping non-dictionary request item: {request}")
            continue

        action_type = request.get("action")
        if action_type == "request_mode_transition":
            mode_transitions.append(request)
        elif action_type == "request_data_retrieval":
            data_retrieval_requests.append(request)
        else:
            other_requests.append(request)

    # --- Handle Data Retrieval First (if any) ---
    if data_retrieval_requests:
        logger.info(f"Processing {len(data_retrieval_requests)} data retrieval requests.")
        retrieved_data_narrative = []
        from core.agents.data_retrieval_commands import process_data_retrieval_command # Import here
        for req in data_retrieval_requests:
            data_type = req.get("data_type", "unknown")
            # Format args if needed, currently assuming no args for simple GETs
            retrieved_data = process_data_retrieval_command(f"GET_{data_type.upper()}", "", game_state)
            # Format the retrieved data into a readable string (basic example)
            # In a real scenario, this might call another LLM to summarize or format
            retrieved_data_narrative.append(f"--- {data_type.upper()} ---")
            retrieved_data_narrative.append(json.dumps(retrieved_data, indent=2, default=str))

        if retrieved_data_narrative:
             # Output data retrieval results (usually replaces narrative)
             data_narrative_str = "\n".join(retrieved_data_narrative)
             engine._output("gm", data_narrative_str) # Output retrieved data
             # If data was retrieved, usually we don't process other requests/narrative
             # unless specifically designed otherwise. Clear other lists.
             mode_transitions = []
             other_requests = []
             initial_narrative = "" # Clear original narrative if data was requested


    # --- Process Mode Transitions (if not superseded by data retrieval) ---
    processed_mode_transition = False
    if mode_transitions:
        request = mode_transitions[0]
        logger.info(f"Processing mode transition request: {json.dumps(request, indent=2)}")

        # Pass the INITIAL narrative into the context for the transition function
        if request.get("target_mode") == "COMBAT":
            request["additional_context"] = {
                "original_intent": intent,
                "narrative_context": initial_narrative
            }

        # Call the function from mode_transitions.py
        # This function will now only PREPARE combat, not fully start it.
        # It will output the initiating narrative.
        narrative_result = _handle_transition_request(engine, game_state, request, effective_actor_id)
        # The narrative_result from _handle_transition_request is now mainly for logging/errors,
        # as the initiating narrative is handled within it.
        if narrative_result and "System Error" in narrative_result:
            final_narrative_parts.append(narrative_result) # Append error messages

        processed_mode_transition = True
        if game_state.current_mode.name != request.get("origin_mode", ""):
            logger.info(f"Mode changed to {game_state.current_mode.name}. Clearing other pending requests.")
            other_requests = []

    # --- Process Other Requests (if no mode transition occurred or they weren't cleared) ---
    if not processed_mode_transition or other_requests: # Process if no transition or if requests remain
        for request in other_requests:
            action_type = request.get("action")
            narrative_result = ""

            if action_type == "request_skill_check":
                request["intent_hint"] = intent # Pass intent hint
                narrative_result = _process_skill_check_request(engine, game_state, request, effective_actor_id)
            elif action_type == "request_state_change":
                narrative_result = _process_state_change_request(engine, game_state, request, effective_actor_id)
            else:
                logger.warning(f"Unknown or missing action type in request: {request}")
                narrative_result = f"System Error: Unknown action type '{action_type}'."

            if narrative_result:
                final_narrative_parts.append(narrative_result)

    return final_narrative_parts


# --- Main Unified Loop Function ---

def run_unified_loop(engine: 'GameEngine', game_state: 'GameState', intent: str, actor_id: Optional[str] = None) -> CommandResult:
    """
    Implements the Unified Core Loop using helper methods.
    Handles context building, agent calls, validation, and execution for an actor's intent.

    Args:
        engine: The GameEngine instance.
        game_state: The current game state.
        intent: The description of the intended action (from player or generated for NPC).
        actor_id: The ID of the entity performing the action. Defaults to player if None.

    Returns:
        The result of processing the action.
    """
    current_mode = game_state.current_mode
    # Determine the acting entity's ID, defaulting to player if not specified
    effective_actor_id = actor_id or getattr(game_state.player, 'id', getattr(game_state.player, 'stats_manager_id', 'player_default_id'))
    logger.debug(f"Entering Unified Loop for Actor ID: {effective_actor_id}, Mode: {current_mode.name}, Intent: '{intent}'")

    # --- Get Actor Combat Name ---
    actor_combat_name = "Unknown" # Default
    actor_entity = None
    if game_state.combat_manager:
         actor_entity = game_state.combat_manager.get_entity_by_id(effective_actor_id)
         if actor_entity:
             actor_combat_name = getattr(actor_entity, 'combat_name', actor_entity.name)
         else:
             logger.warning(f"Could not find actor entity with ID {effective_actor_id} in combat manager.")
    elif effective_actor_id == getattr(game_state.player, 'id', 'player_default_id'):
         actor_combat_name = getattr(game_state.player, 'name', 'Player') # Fallback for player outside combat?
    else:
         # Try getting from NPC system if not in combat? Less likely scenario.
         pass
    logger.debug(f"Determined effective actor combat name: '{actor_combat_name}'")
    # --- End Get Actor Combat Name ---


    try:
        # 1. Build Context
        context = _build_interaction_context(game_state, current_mode, effective_actor_id)

        # 2. Get Agent Response
        agent_output = _get_agent_response(engine, game_state, context, intent, current_mode)
        if not agent_output:
            engine._output("system", "Sorry, I couldn't process that request properly (Agent Error).")
            return CommandResult.error("Agent failed to produce structured output.")

        requests_list = agent_output.get('requests', [])
        if requests_list and actor_combat_name != "Unknown":
            corrected_requests = []
            for req in requests_list:
                 if isinstance(req, dict) and "actor_id" in req:
                     llm_actor_id = req.get("actor_id")
                     if not llm_actor_id or llm_actor_id == "Unknown" or llm_actor_id != actor_combat_name:
                          if llm_actor_id and llm_actor_id != "Unknown":
                              logger.warning(f"Correcting actor_id in request: LLM provided '{llm_actor_id}', expected '{actor_combat_name}'.")
                          else:
                               logger.debug(f"Setting actor_id in request to known actor: '{actor_combat_name}' (LLM provided '{llm_actor_id}').")
                          req["actor_id"] = actor_combat_name 
                 corrected_requests.append(req)
            agent_output["requests"] = corrected_requests

        # 3. Validate Action
        is_valid, validation_feedback = _validate_agent_action(engine, context, agent_output, intent)
        if not is_valid:
            is_npc_action = hasattr(game_state, 'is_processing_npc_action') and game_state.is_processing_npc_action
            if is_npc_action:
                logger.warning(f"NPC action validation failed: {validation_feedback}")
                logger.info("Proceeding with NPC action despite validation failure to maintain combat flow")
            else:
                engine._output("system", f"Action cannot be performed: {validation_feedback}")
                return CommandResult.invalid(f"Action invalid: {validation_feedback}")


        # 4. Execute Validated Requests & Handle Narrative
        final_narrative_parts = _execute_validated_requests(engine, game_state, agent_output, effective_actor_id, intent)

        # 5. Output Final System Messages (Results of checks/changes)
        if final_narrative_parts:
            final_outcome_narrative = "\n".join(final_narrative_parts)
            engine._output("system", final_outcome_narrative)

        processed_requests_count = len(agent_output.get('requests', []))
        return CommandResult.success("Action processed.", data={"processed_requests": processed_requests_count})

    except Exception as e:
        logger.error(f"Error in Unified Core Loop for mode {current_mode.name}: {e}", exc_info=True)
        engine._output("system", f"An unexpected error occurred while processing your action: {e}")
        return CommandResult.error(f"Internal error processing action: {e}")