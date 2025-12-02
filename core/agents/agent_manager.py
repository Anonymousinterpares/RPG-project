"""
Agent manager for coordinating between different agent types.

This module provides an AgentManager class that initializes, coordinates,
and manages interactions between different agent types, including
context evaluation, rule checking, and narrative generation.
"""

from typing import List, Optional, Any, Tuple

from core.interaction.enums import InteractionMode
from core.stats.stats_base import DerivedStatType
from core.stats.stats_manager import get_stats_manager
from core.utils.logging_config import get_logger
from core.base.state import GameState
from core.base.commands import get_command_processor
from core.inventory import get_narrative_item_manager
from core.agents.base_agent import AgentContext, AgentResponse
from core.agents.narrator import get_narrator_agent
from core.agents.rule_checker import get_rule_checker_agent
from core.agents.context_evaluator import get_context_evaluator_agent
from core.agents.data_retrieval_commands import process_data_retrieval_command
from core.agents.archivist import ArchivistAgent

# Get the module logger
logger = get_logger("AGENT")

class AgentManager:
    """
    Manager for coordinating between different agent types.
    
    This class handles initialization, coordination, and management of
    different agent types, including context evaluation, rule checking,
    and narrative generation.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the agent manager."""
        if self._initialized:
            return
        
        logger.info("Initializing AgentManager")
        
        # Initialize agents
        self._narrator_agent = get_narrator_agent()
        self._rule_checker_agent = get_rule_checker_agent()
        self._context_evaluator_agent = get_context_evaluator_agent()
        
        # Initialize Archivist
        self._archivist_agent = ArchivistAgent()
        
        # Initialize command processor
        self._command_processor = get_command_processor()
        
        # Initialize narrative item manager
        self._narrative_item_manager = get_narrative_item_manager()
        
        # Settings
        self._perform_rule_check = True
        self._perform_context_evaluation = True
        
        self._initialized = True
        logger.info("AgentManager initialized")
    
    def reset_state(self):
        """
        Reset the state of all agents.
        
        This should be called when starting a new game to ensure no state
        from previous games affects the new game's narrative.
        """
        logger.info("Resetting agent state")
        
        try:
            # Reset narrator agent if it has a reset method
            if hasattr(self._narrator_agent, 'reset'):
                self._narrator_agent.reset()
                logger.info("Reset narrator agent state")
            
            # Reset rule checker agent if it has a reset method
            if hasattr(self._rule_checker_agent, 'reset'):
                self._rule_checker_agent.reset()
                logger.info("Reset rule checker agent state")
            
            # Reset context evaluator agent if it has a reset method
            if hasattr(self._context_evaluator_agent, 'reset'):
                self._context_evaluator_agent.reset()
                logger.info("Reset context evaluator agent state")
            
            # Reset narrative item manager if needed
            if hasattr(self._narrative_item_manager, 'reset'):
                self._narrative_item_manager.reset()
                logger.info("Reset narrative item manager state")
        except Exception as e:
            logger.error(f"Error resetting agent state: {e}", exc_info=True)
    
    def reload_settings(self):
        """
        Reload settings for all agents.
        
        This should be called when LLM settings are updated.
        """
        logger.info("Reloading agent settings")
        
        try:
            # Reload settings for each agent
            if hasattr(self._narrator_agent, 'reload_settings'):
                self._narrator_agent.reload_settings()
            
            if hasattr(self._rule_checker_agent, 'reload_settings'):
                self._rule_checker_agent.reload_settings()
            
            if hasattr(self._context_evaluator_agent, 'reload_settings'):
                self._context_evaluator_agent.reload_settings()
            
            logger.info("Agent settings reloaded")
        except Exception as e:
            logger.error(f"Error reloading agent settings: {e}", exc_info=True)
    
    def process_input(self, 
                      game_state: GameState, 
                      player_input: str,
                      perform_rule_check: bool = True,
                      perform_context_evaluation: bool = True) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Process player input through the appropriate agents.
        
        Args:
            game_state: The current game state.
            player_input: The player's input text.
            perform_rule_check: Whether to perform rule checking.
            perform_context_evaluation: Whether to perform context evaluation.
        
        Returns:
            A tuple of (response_text, commands), where commands is a list of
            (command, args) tuples extracted from the response.
        """
        logger.info(f"Processing player input with LLM: {player_input}")
        
        # Update settings
        self._perform_rule_check = perform_rule_check
        self._perform_context_evaluation = perform_context_evaluation
        
        # Create base context
        context = self._create_agent_context(game_state, player_input)

        # Opportunistically prefetch inventory when input is item/inventory-related so validation sees real items
        try:
            lower_in = (player_input or "").lower()
            inventory_triggers = [
                "inventory", "pack", "backpack", "bag", "use ", "consume", "eat", "drink",
                "equip", "unequip", "drop", "take", "pick", "obtain", "get ", "have ", "has ", "hold"
            ]
            should_prefetch_inv = any(t in lower_in for t in inventory_triggers)
            if should_prefetch_inv:
                from core.agents.data_retrieval_commands import get_inventory_data
                pre_inv = get_inventory_data(game_state)
                if pre_inv and isinstance(pre_inv, dict):
                    context.additional_context = {**(context.additional_context or {}), "inventory": pre_inv}
                    logger.info("Prefetched inventory into LLM context based on user input.")
        except Exception as e:
            logger.warning(f"Prefetch inventory failed: {e}")

        # Prefetch quests when the user explicitly asks about them (single-output UX)
        try:
            if isinstance(player_input, str) and "quest" in player_input.lower():
                from core.agents.data_retrieval_commands import get_quest_data
                pre_q = get_quest_data(game_state)
                if pre_q and isinstance(pre_q, dict):
                    context.additional_context = {**(context.additional_context or {}), "quests": pre_q}
                    logger.info("Prefetched quests into LLM context based on user input.")
        except Exception as e:
            logger.warning(f"Prefetch quests failed: {e}")
        
        try:
            # Step 1: Evaluate context
            if self._perform_context_evaluation:
                context = self._evaluate_context(context)
            
            # Step 2: Check rules
            if self._perform_rule_check:
                is_valid, reason = self._check_rules(context)
                
                if not is_valid:
                    # Ensure we have a meaningful error message
                    if not reason:
                        reason = "Unknown rule violation"
                    # Return rule violation message
                    return f"Invalid action: {reason}", []
            
            # Step 3: First phase - Generate initial narrative to check for data retrieval needs
            logger.info("Phase 1: Generating initial narrative to identify data needs...")
            initial_response = self._generate_narrative(context)
            
            # Check if there are any data retrieval commands in the response
            data_commands = [
                (cmd, args) for cmd, args in initial_response.commands 
                if cmd in ["GET_INVENTORY", "GET_STATS", "GET_QUESTS", "GET_LOCATION_INFO"]
            ]
            
            # If data retrieval commands exist, process them and regenerate the narrative
            if data_commands:
                logger.info(f"Found {len(data_commands)} data retrieval commands")
                
                # Process data retrieval commands
                additional_context = {}
                for cmd, args in data_commands:
                    logger.info(f"Processing data retrieval command: {cmd}")
                    
                    # Get data based on command
                    data = process_data_retrieval_command(cmd, args, game_state)
                    
                    # Add to additional context
                    if cmd == "GET_INVENTORY":
                        additional_context["inventory"] = data
                    elif cmd == "GET_STATS":
                        additional_context["character_stats"] = data
                    elif cmd == "GET_QUESTS":
                        additional_context["quests"] = data
                    elif cmd == "GET_LOCATION_INFO":
                        additional_context["location_info"] = data
                
                # Update context with retrieved data
                context.additional_context = {
                    **(context.additional_context or {}),
                    **additional_context
                }
                
                # Step 3.5: Regenerate narrative with enhanced context
                logger.info("Phase 2: Regenerating narrative with retrieved data...")
                response = self._generate_narrative(context)
                # If the regenerated narrative is empty but we have retrieved data, generate a default response
                if (not response.content or len(response.content.strip()) == 0) and additional_context:
                    default_message = "Here is the information you requested:\n\n"
                    
                    if "character_stats" in additional_context:
                        stats = additional_context["character_stats"]
                        default_message += "=== CHARACTER STATS ===\n"
                        if "character" in stats:
                            char_info = stats["character"]
                            default_message += f"Name: {char_info.get('name', 'Unknown')}\n"
                            default_message += f"Race: {char_info.get('race', 'Unknown')}\n"
                            default_message += f"Class: {char_info.get('path', 'Unknown')}\n"
                            default_message += f"Level: {char_info.get('level', 1)}\n"
                        
                        default_message += "\nPrimary Stats:\n"
                        if "primary_stats" in stats:
                            for stat_name, stat_data in stats["primary_stats"].items():
                                default_message += f"- {stat_name}: {stat_data.get('value', 0)}\n"
                        
                        default_message += "\nDerived Stats:\n"
                        if "derived_stats" in stats:
                            for stat_name, stat_data in stats["derived_stats"].items():
                                default_message += f"- {stat_name}: {stat_data.get('value', 0)}\n"
                        
                        default_message += "\nSkills:\n"
                        if "skills" in stats:
                            for skill_name, skill_data in stats["skills"].items():
                                default_message += f"- {skill_name}: {skill_data.get('value', 0)}\n"
                    
                    if "inventory" in additional_context:
                        inventory = additional_context["inventory"]
                        default_message += "\n=== INVENTORY ===\n"
                        if "equipped" in inventory and inventory["equipped"]: # Check if equipped dict is not empty
                            default_message += "Equipped Items:\n"
                            for slot, item_data in inventory["equipped"].items(): # Iterate over items in dict
                                if isinstance(item_data, dict): # Ensure item_data is a dict
                                    default_message += f"- {slot}: {item_data.get('name', 'Unknown Item')}\n"
                                elif item_data: # Fallback if it's just a string/ID (less likely with new structure)
                                    default_message += f"- {slot}: {item_data}\n"
                        else:
                            default_message += "Equipped Items: None\n"

                        if "backpack" in inventory and inventory["backpack"]:
                            default_message += "\nBackpack Items:\n"
                            for item_data in inventory["backpack"]: # Iterate over items in list
                                if isinstance(item_data, dict): # Ensure item_data is a dict
                                    quantity = item_data.get("quantity", 1)
                                    quantity_str = f" (x{quantity})" if quantity > 1 else ""
                                    default_message += f"- {item_data.get('name', 'Unknown Item')}{quantity_str}\n"
                                else: # Fallback if it's just a string/ID
                                    default_message += f"- {item_data}\n"
                        else:
                            default_message += "\nBackpack Items: Empty\n"

                        if "currency" in inventory:
                            currency = inventory["currency"]
                            gold = currency.get("gold", 0)
                            silver = currency.get("silver", 0)
                            copper = currency.get("copper", 0)
                            default_message += f"\nCurrency: {gold}g {silver}s {copper}c\n"
                    
                    if "quests" in additional_context:
                        quests = additional_context["quests"]
                        default_message += "\n=== QUESTS ===\n"
                        if "active_quests" in quests:
                            default_message += "Active Quests:\n"
                            for quest in quests["active_quests"]:
                                if isinstance(quest, dict):
                                    default_message += f"- {quest.get('name', 'Unknown Quest')}\n"
                                    if 'description' in quest:
                                        default_message += f"  {quest['description']}\n"
                                else:
                                    default_message += f"- {quest}\n"
                    
                    if "location_info" in additional_context:
                        location = additional_context["location_info"]
                        default_message += "\n=== LOCATION ===\n"
                        default_message += f"Current Location: {location.get('current_location', 'Unknown')}\n"
                        default_message += f"District/Area: {location.get('current_district', 'Unknown')}\n"
                        if "weather" in location:
                            default_message += f"Weather: {location['weather']}\n"
                    
                    # Update the response with our default message
                    response.content = default_message
                    logger.info("Generated default data retrieval response")
                
                logger.info(f"Received final response from LLM: {len(response.content)} chars")
            else:
                # No data retrieval needed, use the initial response
                logger.info("No data retrieval commands found, using initial response")
                response = initial_response
            
            # Step 4: Process narrative item commands
            processed_text, item_results = self._process_narrative_items(game_state, response.content)
            
            # Update response with processed text
            response.content = processed_text
            
            # Step 5: Process remaining commands in the response
            # Filter out data retrieval commands as they've already been processed
            # Also filter out CONSUME_ITEM commands, as they will be handled by game logic post-narration.
            commands_to_return = []
            for cmd, args in response.commands:
                if cmd in ["GET_INVENTORY", "GET_STATS", "GET_QUESTS", "GET_LOCATION_INFO"]:
                    logger.debug(f"Filtering out already processed data retrieval command: {cmd}")
                    continue
                elif cmd == "CONSUME_ITEM": # This is an example, actual command might differ
                    logger.debug(f"Noting CONSUME_ITEM command for game logic: {cmd} {args}")
                    # This command is now passed through for GameEngine to handle
                    commands_to_return.append((cmd, args))
                else:
                    commands_to_return.append((cmd, args))

            logger.info(f"Extracted {len(commands_to_return)} action commands to return from response")

            # Route special LLM commands (including quest updates) immediately through LLM handlers
            routed_commands: list[tuple[str, str]] = []
            for cmd, args in commands_to_return:
                if cmd in ["MODE_TRANSITION", "QUEST_UPDATE", "QUEST_STATUS"]:
                    try:
                        from core.game_flow.command_handlers import process_llm_command
                        from core.base.engine import get_game_engine
                        engine = get_game_engine()
                        logger.info(f"Routing special LLM command now: {cmd}")
                        # Ensure args are provided as a list of one string per our handler signature
                        _ = process_llm_command(engine, cmd, [args] if not isinstance(args, list) else args, game_state)
                        # We do not append these to the returned list; they are handled immediately
                    except Exception as e:
                        logger.error(f"Error routing LLM command {cmd}: {e}")
                else:
                    routed_commands.append((cmd, args))

            # Return the response text and only the remaining commands (non-LLM-special)
            return response.content, routed_commands
            
        except Exception as e:
            logger.error(f"Error in agent processing: {e}", exc_info=True)
            return f"I'm sorry, but I encountered an error while processing your input: {str(e)}", []
    
    def _create_agent_context(self, game_state: GameState, player_input: str) -> AgentContext:
        """
        Create an agent context from the game state and player input using the ContextBuilder.
        This ensures deep context (like present NPCs, environment tags) is included.
        
        Args:
            game_state: The current game state.
            player_input: The player's input text.
        
        Returns:
            An AgentContext object.
        """
        # Import locally to avoid circular dependencies
        from core.interaction.context_builder import ContextBuilder
        
        # Determine current mode
        current_mode = getattr(game_state, 'current_mode', InteractionMode.NARRATIVE)
        
        # Build rich context using the builder (this fetches NPCs, rich location data, etc.)
        builder = ContextBuilder()
        player_id = getattr(game_state.player, 'id', getattr(game_state.player, 'stats_manager_id', 'player'))
        
        # Generate the structured context dictionary
        rich_context = builder.build_context(game_state, current_mode, actor_id=player_id)
        
        # Extract/Construct specific state dicts for AgentContext compatibility
        game_state_dict = {
            "session_id": game_state.session_id,
            "created_at": game_state.created_at,
            "last_saved_at": game_state.last_saved_at,
            "game_version": game_state.game_version,
            "last_command": game_state.last_command,
            "mode": current_mode.name if hasattr(current_mode, 'name') else str(current_mode)
        }
        
        # Add dynamic stamina regeneration note if applicable (NARRATIVE mode only)
        if current_mode == InteractionMode.NARRATIVE:
            player_stats_manager = get_stats_manager()
            if player_stats_manager:
                try:
                    current_stamina = player_stats_manager.get_current_stat_value(DerivedStatType.STAMINA)
                    max_stamina = player_stats_manager.get_stat_value(DerivedStatType.MAX_STAMINA)
                    if current_stamina < max_stamina:
                        rich_context["player_stamina_status"] = (
                            f"Player stamina is {current_stamina:.0f}/{max_stamina:.0f}. "
                            f"Consider if regeneration is appropriate based on recent actions and time passed."
                        )
                        logger.debug(f"Stamina note added to rich context: {rich_context['player_stamina_status']}")
                except Exception as e:
                    logger.warning(f"Could not get player stamina for agent context note: {e}")

        # Create agent context
        # We pass 'rich_context' as additional_context so the NarratorAgent can access keys 
        # like 'present_npcs', 'environment', 'inventory' which are populated by ContextBuilder.
        context = AgentContext(
            game_state=game_state_dict,
            player_state=rich_context.get('player', {}),
            world_state={
                'location': rich_context.get('location', {}),
                'time_of_day': rich_context.get('time_of_day', 'Unknown'),
                'weather': rich_context.get('weather', {}),
                'environment': rich_context.get('environment', [])
            },
            player_input=player_input,
            conversation_history=game_state.conversation_history if game_state else [],
            relevant_memories=[],  # Will be populated by context evaluator if enabled
            additional_context=rich_context
        )
        
        return context
    
    def _evaluate_context(self, context: AgentContext) -> AgentContext:
        """
        Evaluate the context using the context evaluator agent.
        
        Args:
            context: The agent context.
        
        Returns:
            An updated agent context with relevant memories and a context summary.
        """
        logger.info("Evaluating context")
        
        try:
            # Check for cached summary first
            cached_summary = self._context_evaluator_agent.get_cached_summary(context)
            
            if cached_summary:
                # Use cached summary
                context.context_summary = cached_summary
                logger.info("Using cached context summary")
            else:
                # Process context evaluation
                eval_result = self._context_evaluator_agent.evaluate_context(context)
                
                # Update context with evaluation results
                if eval_result:
                    context.context_summary = eval_result.get("context_summary")
                    
                    # In a full implementation, we would retrieve relevant memories
                    # based on the evaluation results and add them to context.relevant_memories
                    
                    logger.info("Context evaluation completed")
                else:
                    logger.warning("Context evaluation failed")
        
        except Exception as e:
            logger.error(f"Error evaluating context: {e}")
            # Proceed without context evaluation
        
        return context
    
    def _check_rules(self, context: AgentContext) -> Tuple[bool, Optional[str]]:
        """
        Check rules using the rule checker agent.
        
        Args:
            context: The agent context.
        
        Returns:
            A tuple of (is_valid, reason), where reason is None if valid.
        """
        logger.info("Checking rules")
        
        try:
            # Special case for welcome narration - always allow it
            if "starting a new game as" in context.player_input and "introduce me to the game world" in context.player_input:
                logger.info("Allowing welcome narration to bypass rule check")
                return True, None
                
            # Use the rule checker's validate_action method
            is_valid, reason = self._rule_checker_agent.validate_action(context)
            
            if is_valid:
                logger.info("Rule check passed")
            else:
                # Make sure reason is not None when action is invalid
                if not reason:
                    reason = "Unknown rule violation"
                logger.info(f"Rule check failed: {reason}")
            
            return is_valid, reason
            
        except Exception as e:
            logger.error(f"Error checking rules: {e}")
            # Proceed with rule check passed by default
            return True, None
    
    def _generate_narrative(self, context: AgentContext) -> AgentResponse:
        """
        Generate narrative using the narrator agent.
        
        Args:
            context: The agent context.
        
        Returns:
            An AgentResponse object with narrative content and commands.
        """
        logger.info("Generating narrative")
        
        # Filter error messages from conversation history to prevent cascading errors
        self._filter_error_messages_from_history(context)
        
        try:
            # Check if narrator agent is available
            if self._narrator_agent is None:
                raise ValueError("Narrator agent is not initialized")
                
            # Log that we're about to call the narrator agent
            logger.info("Calling narrator agent process() method")
            
            # Process the context with the narrator agent
            agent_output = self._narrator_agent.process(context)
            
            # Check if we got a valid response
            if agent_output is None:
                raise ValueError("Narrator agent returned None response")
                
            if "narrative" not in agent_output:
                raise ValueError("Narrator agent returned response without narrative")
            
            # Convert AgentOutput to AgentResponse
            narrative = agent_output.get("narrative", "")
            requests = agent_output.get("requests", [])
            
            # Command conversion - map structured requests to simple commands
            commands = []
            for req in requests:
                if isinstance(req, dict) and "action" in req:
                    action = req["action"]
                    # Format depends on action type
                    if action == "request_skill_check":
                        skill_name = req.get("skill_name", "unknown")
                        difficulty = req.get("difficulty_class", 10)
                        commands.append(("STAT_CHECK", f"{skill_name}:{difficulty}"))
                    elif action == "request_state_change":
                        # Preserve all fields by passing JSON; normalize target_id if only target_entity/target provided
                        import json
                        payload = dict(req)
                        if "target_id" not in payload:
                            payload["target_id"] = (
                                req.get("target_entity") or req.get("target") or req.get("actor_id")
                            )
                        commands.append(("STATE_CHANGE", json.dumps(payload)))
                    elif action == "request_data_retrieval":
                        data_type = req.get("data_type", "unknown")
                        if data_type.upper() in ["INVENTORY", "STATS", "QUESTS", "LOCATION_INFO"]:
                            commands.append((f"GET_{data_type.upper()}", ""))
                    elif action == "request_quest_update":
                        # Pass whole request as JSON payload
                        import json
                        commands.append(("QUEST_UPDATE", json.dumps(req)))
                    elif action == "request_quest_status":
                        import json
                        commands.append(("QUEST_STATUS", json.dumps(req)))
                    elif action == "request_mode_transition":
                        # Add support for mode transitions
                        target_mode = req.get("target_mode", "UNKNOWN")
                        origin_mode = req.get("origin_mode", "UNKNOWN")
                        reason = req.get("reason", "")
                        target_entity_id = req.get("target_entity_id", "")
                        surprise = "true" if req.get("surprise", False) else "false"
                        # Format as a MODE_TRANSITION command
                        commands.append(("MODE_TRANSITION", 
                                       f"{target_mode}:{origin_mode}:{surprise}:{target_entity_id}:{reason}"))
            
            # Create AgentResponse object
            response = AgentResponse(
                content=narrative,
                commands=commands,
                metadata={"structured_requests": requests} 
            )
            
            logger.info("Narrative generation completed successfully")
            logger.debug(f"Generated content: {response.content[:100]}...")
            return response
        
        except Exception as e:
            logger.error(f"Narrator agent failed to get LLM response: {e}", exc_info=True)
            
            # Generate a more specific error message based on the exception type
            error_message = "Error: Narrator agent failed to generate a response."
            
            # Check for specific error types
            if "NoneType object is not subscriptable" in str(e):
                error_message = "Error: Communication with the LLM service failed. The server may be experiencing issues or the API format may have changed."
            elif "api_key" in str(e).lower():
                error_message = "Error: API key issues detected. Please check your LLM provider settings."
            elif "timeout" in str(e).lower():
                error_message = "Error: The LLM service timed out. Please try again later."
            elif "rate limit" in str(e).lower() or "rate_limit" in str(e).lower():
                error_message = "Error: Rate limit exceeded with the LLM service. Please try again in a few moments."
            
            # Return a fallback response with the specific error message
            return AgentResponse(
                content=error_message,
                commands=[],
                metadata={"error": f"narrative_generation_failure: {str(e)}"}
            )

    def _filter_error_messages_from_history(self, context: AgentContext) -> None:
        """
        Filter out error messages from conversation history to prevent cascading errors.
        
        Args:
            context: The agent context containing conversation history.
        """
        if not context.conversation_history:
            return
        
        # Look for error patterns in assistant/gm responses
        error_patterns = [
            "[Narrator Error:",
            "[System Error:",
            "Error:",
            "cannot process",
            "failed to generate",
            "```json", # Don't want raw JSON in history either
            "I'm sorry, but I encountered an error"
        ]
        
        # Create a new filtered history
        filtered_history = []
        removed_count = 0
        
        for entry in context.conversation_history:
            role = entry.get("role", "")
            content = entry.get("content", "")
            
            # Only filter assistant/gm messages, keep all player messages
            if role in ["assistant", "gm"]:
                # Check if the message contains error patterns
                if any(pattern in content for pattern in error_patterns):
                    removed_count += 1
                    # Skip this message - don't add to filtered history
                    continue
            
            # This message passed all filters, keep it
            filtered_history.append(entry)
        
        if removed_count > 0:
            logger.info(f"Filtered {removed_count} error messages from conversation history")
            context.conversation_history = filtered_history    

    def _process_narrative_items(self, game_state: GameState, response_text: str) -> Tuple[str, List[Any]]:
        """
        Process narrative item commands in the response text.
        
        Args:
            game_state: The current game state.
            response_text: The response text from the narrator agent.
        
        Returns:
            A tuple of (processed_text, results).
        """
        logger.info("Processing narrative item commands")
        
        try:
            # Process narrative item commands
            processed_text, results = self._narrative_item_manager.process_narrative_commands(
                response_text, game_state
            )
            
            logger.info(f"Processed {len(results)} narrative item commands")
            return processed_text, results
            
        except Exception as e:
            logger.error(f"Error processing narrative items: {e}", exc_info=True)
            # Return original text if there's an error
            return response_text, []
    
    def process_commands(self, game_state: GameState, commands: List[Tuple[str, str]]) -> List[Any]:
        """
        Process commands extracted from agent responses.
        
        Args:
            game_state: The current game state.
            commands: A list of (command, args) tuples.
        
        Returns:
            A list of command results.
        """
        logger.info(f"Processing {len(commands)} commands")
        
        results = []
        
        for cmd, args in commands:
            try:
                # Import the LLM command handler
                from core.game_flow.command_handlers import process_llm_command
                
                # Get game engine
                from core.base.engine import get_game_engine
                engine = get_game_engine()
                
                # Process special commands directly first
                if cmd == "MODE_TRANSITION":
                    logger.info(f"Handling MODE_TRANSITION command: {args}")
                    result = process_llm_command(engine, cmd, [args], game_state)
                    results.append(result)
                    logger.info(f"MODE_TRANSITION command processed: {result.message}")
                # Process skill checks and other special commands
                elif cmd == "STAT_CHECK" or cmd == "RULE_CHECK":
                    # Process skill check with the rule checker agent
                    result = self._process_skill_check_command(cmd, args, game_state)
                    results.append(result)
                    logger.info(f"Processed skill check command {cmd}")
                else:
                    # Process other commands with the command processor
                    result = self._command_processor.process_llm_commands(
                        game_state, f"{{{cmd} {args}}}"
                    )
                    
                    # Add the result to the list
                    results.append(result)
                    
                    logger.info(f"Processed command {cmd}")
            
            except Exception as e:
                logger.error(f"Error processing command {cmd}: {e}", exc_info=True)
                # Add error result
                results.append((f"Error processing command {cmd}: {e}", []))
        
        return results
        
    def _process_skill_check_command(self, cmd: str, args: str, game_state: GameState) -> Any:
        """
        Process a skill check command.
        
        Args:
            cmd: The command (STAT_CHECK or RULE_CHECK).
            args: The command arguments.
            game_state: The current game state.
            
        Returns:
            The result of the skill check.
        """
        logger.info(f"Processing skill check command: {cmd} {args}")
        
        try:
            # Parse the command arguments
            parts = args.split(':') if ':' in args else args.split()
            
            if len(parts) < 2:
                return {"error": f"Invalid {cmd} command format: {args}"}
                
            # Extract the stat type and difficulty
            stat_type = parts[0].strip().upper()
            difficulty = int(parts[1].strip())
            
            # Extract context if available
            context = parts[2].strip() if len(parts) > 2 else ""
            
            # Use the rule checker's perform_skill_check method
            check_result = self._rule_checker_agent.perform_skill_check(
                stat_type=stat_type,
                difficulty=difficulty,
                context=context
            )
            
            return check_result
        except Exception as e:
            logger.error(f"Error processing skill check command: {e}")
            return {"error": f"Error processing skill check: {str(e)}"}
        


# Convenience function
def get_agent_manager() -> AgentManager:
    """Get the agent manager instance."""
    return AgentManager()


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    get_logger.basicConfig(level=get_logger.INFO)
    
    # Create an agent manager
    manager = get_agent_manager()
    
    # Create a dummy game state for testing
    from core.base.state import GameState, PlayerState, WorldState
    
    game_state = GameState(
        player=PlayerState(
            name="Test Player",
            race="Human",
            path="Wanderer",
            background="Commoner",
            current_location="Test Town",
            current_district="Town Square"
        ),
        world=WorldState()
    )
    
    # Add some conversation history
    game_state.add_conversation_entry("player", "Hello, world!")
    game_state.add_conversation_entry("gm", "Welcome to the game!")
    
    # Process player input
    response_text, commands = manager.process_input(
        game_state=game_state,
        player_input="I look around to see what's in the town square."
    )
    
    # Print the response
    print(f"Response: {response_text}")
    
    if commands:
        print("\nCommands:")
        for cmd, args in commands:
            print(f"  {cmd}: {args}")
