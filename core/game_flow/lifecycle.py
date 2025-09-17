#!/usr/bin/env python3
"""
Handles game lifecycle operations like starting, loading, saving, and ticking.
"""

import os
import logging
from typing import Any, Dict, Optional

# Need to import GameEngine for type hinting and accessing its members
# Use a forward reference (string) to avoid circular import at runtime
# from core.base.engine import GameEngine
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.base.state import GameState # Keep GameState

# Import interaction_core to call its functions
from core.game_flow import interaction_core
from core.base.state import GameState
from core.utils.logging_config import get_logger
from core.inventory import get_inventory_manager, get_item_factory

# Get the module logger (using a distinct name)
logger = get_logger("LIFECYCLE")


def start_new_game_with_state(engine: 'GameEngine', game_state: 'GameState') -> 'GameState':
    """
    Initializes systems for a new game using an already created GameState.
    
    Args:
        engine: The game engine instance.
        game_state: The pre-created and StatManager-initialized game state.
    
    Returns:
        The initialized game state.
    """
    logger.info(f"Starting new game for player {game_state.player.name} using existing game state")
    
    # Set current state in state manager
    engine._state_manager._current_state = game_state
    
    # Initialize memory/context system
    engine._state_manager.initialize_memory_context(game_state)
    logger.info("Memory/context system initialized for new game")

    # Initialize player's inventory
    inventory_manager = get_inventory_manager()
    logger.info(f"LIFECYCLE: Using InventoryManager instance ID: {getattr(inventory_manager, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}")
    inventory_manager.clear() 
    if hasattr(inventory_manager, 'inventory_id_for_debug'): # Check for the debug ID
        game_state.player.inventory_id = inventory_manager.inventory_id_for_debug
    elif hasattr(inventory_manager, 'instance_id_for_debug'): # Fallback to the new debug ID
         game_state.player.inventory_id = inventory_manager.instance_id_for_debug
    else: # Fallback if InventoryManager doesn't have a direct inventory_id attribute
        import uuid
        inventory_manager_id = str(uuid.uuid4())
        try:
            setattr(inventory_manager, 'inventory_id_for_debug', inventory_manager_id) 
        except AttributeError:
            logger.warning("Could not set 'inventory_id_for_debug' on InventoryManager instance.")
        game_state.player.inventory_id = inventory_manager_id
        logger.warning(f"InventoryManager instance did not have 'inventory_id_for_debug'. Assigned new ID for player state: {inventory_manager_id}")


    # Configure world time and settings based on origin
    origin_id = game_state.player.origin_id 

    if origin_id:
        from core.base.config import get_config
        config = get_config() 
        origins_config = config.get('origins') 

        if origins_config and isinstance(origins_config, dict) and origin_id in origins_config:
            origin_data = origins_config[origin_id]
            
            # Set starting location based on origin settings
            starting_location_id = origin_data.get('starting_location_id')
            if starting_location_id:
                # Resolve to location name via GameConfig locations domain
                location_name = config.get(f"locations.{starting_location_id}.name")
                resolved_location = location_name or starting_location_id
                game_state.player.current_location = resolved_location
                game_state.world.current_location = resolved_location
                logger.info(f"Set starting location to '{resolved_location}' (id='{starting_location_id}') for origin '{origin_id}'")
            else:
                logger.warning(f"Origin '{origin_id}' has no starting_location_id. Leaving current_location unchanged.")
            
            # Set up world time based on origin settings
            starting_time_period = origin_data.get('starting_time_period')
            starting_season = origin_data.get('starting_season')
            
            if starting_time_period:
                # Convert time period to actual game time
                from core.utils.enhanced_time_manager import get_enhanced_time_manager, TimePeriod
                from core.utils.time_utils import HOUR
                
                # Map time periods to approximate hours
                time_period_hours = {
                    'deep_night': 2, 'pre_dawn': 4.5, 'dawn': 6, 'morning': 9,
                    'noon': 12, 'afternoon': 15, 'evening': 18, 'sunset': 20.5, 'night': 22
                }
                
                if starting_time_period in time_period_hours:
                    target_hour = time_period_hours[starting_time_period]
                    game_state.world.game_time = target_hour * HOUR
                    logger.info(f"Set starting time to {starting_time_period} ({target_hour}:00) for origin '{origin_id}'")
                
            if starting_season:
                # Set the season in world global variables
                game_state.world.set_global_var('current_season', starting_season)
                logger.info(f"Set starting season to {starting_season} for origin '{origin_id}'")
            
            # Add starting items from origin
            starting_item_ids_from_origin = origin_data.get('starting_items', [])
            item_factory = get_item_factory()

            logger.info(f"Processing starting items for origin '{origin_id}': {starting_item_ids_from_origin}")
            for item_template_id in starting_item_ids_from_origin:
                logger.debug(f"Attempting to create starting item from template_id: '{item_template_id}'")
                item_instance = item_factory.create_item_from_template(item_template_id, variation=False)
                if item_instance:
                    added_ids = inventory_manager.add_item(item_instance)
                    if added_ids:
                        logger.info(f"Added starting item '{item_instance.name}' (ID: {added_ids[0]}) to inventory via manager {getattr(inventory_manager, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}.")
                    else:
                        logger.warning(f"Failed to add starting item '{item_template_id}' to inventory for player '{game_state.player.name}'.")
                else:
                    logger.warning(f"Could not create starting item from template_id: '{item_template_id}' for player '{game_state.player.name}'. Template not found or creation failed.")
        elif not origins_config:
            logger.warning("Origins configuration data not found or is not a dictionary. Cannot add starting items.")
        else: 
            logger.warning(f"Origin ID '{origin_id}' not found in origins configuration. Cannot add starting items.")
    else:
        logger.warning("No origin_id found on game_state.player. Cannot add starting items.")

    # --- Activate initial quests from origin ---
    try:
        origin_id = game_state.player.origin_id
        if origin_id:
            from core.base.config import get_config
            config = get_config()
            origins_cfg = config.get('origins') or {}
            quests_cfg = config.get('quests') or {}
            if isinstance(origins_cfg, dict) and isinstance(quests_cfg, dict) and origin_id in origins_cfg:
                init_ids = origins_cfg[origin_id].get('initial_quests', []) or []
                # Ensure journal exists on state
                if not hasattr(game_state, 'journal') or not isinstance(getattr(game_state, 'journal'), dict):
                    game_state.journal = {"character": "", "quests": {}, "notes": []}
                started_events: list[tuple[str, str]] = []  # (id, title)
                # Activate each quest: add to journal.quests with status=active and copy objectives
                for qid in init_ids:
                    if qid in quests_cfg and qid not in game_state.journal["quests"]:
                        qdef = quests_cfg[qid]
                        # Build objectives with default mandatory=True unless marked (O)
                        built_objectives = []
                        for index, obj in enumerate(qdef.get("objectives", [])):
                            if isinstance(obj, dict):
                                desc_text = obj.get("description") or ""
                                oid = obj.get("id") or str(index)
                                mandatory = obj.get("mandatory")
                            else:
                                desc_text = str(obj)
                                oid = str(index)
                                mandatory = None
                            text_lower = desc_text.lower()
                            is_optional = "(o)" in text_lower if isinstance(desc_text, str) else False
                            # If 'mandatory' explicitly given, use it; otherwise infer from tags
                            is_mandatory = (mandatory if isinstance(mandatory, bool) else ("(m)" in text_lower or not is_optional))
                            built_objectives.append({
                                "id": oid,
                                "description": desc_text,
                                "completed": False,
                                "failed": False,
                                "mandatory": bool(is_mandatory),
                            })

                        title = qdef.get("title", qid)
                        game_state.journal["quests"][qid] = {
                            "title": title,
                            "description": qdef.get("description", ""),
                            "status": "active",
                            "objectives": built_objectives,
                            "rewards": qdef.get("rewards", {}),
                            "prerequisites": qdef.get("prerequisites", []),
                            "tags": qdef.get("tags", []),
                        }
                        started_events.append((qid, title))
                logger.info(f"Activated {len(init_ids)} initial quests for origin '{origin_id}'.")
    except Exception as e:
        logger.error(f"Failed to activate initial quests: {e}")

    # Send welcome message
    welcome_message_base = f"==== WELCOME TO YOUR ADVENTURE ====\n\nGreetings, {game_state.player.name} the {game_state.player.race} {game_state.player.path} from {game_state.player.background}!"
    
    introduction_text_for_llm = game_state.player.background 
    if origin_id: 
        from core.base.config import get_config
        config = get_config() 
        origins_config = config.get('origins') 
        if origins_config and isinstance(origins_config, dict) and origin_id in origins_config:
            introduction_text_for_llm = origins_config[origin_id].get('introduction_text', game_state.player.background)
    
    full_welcome_message = f"{welcome_message_base}\n\nYour journey begins now..." 
    
    logger.info(f"Sending welcome message: '{full_welcome_message[:100]}...' with role 'gm'")
    engine._output("gm", full_welcome_message)
    
    # Send help message
    help_message = "Type 'help' for a list of commands."
    engine._output("system", help_message)
    
    # Generate initial narrative if LLM is enabled
    if engine._use_llm:
        logger.info("Generating welcome narration")
        narration_prompt = (
            f"I've just started a new game as {game_state.player.name}, a {game_state.player.race} {game_state.player.path}. "
            f"My background is: \"{introduction_text_for_llm}\". "
            f"Please provide an initial immersive narration based on this, describing my immediate surroundings and current situation as the game begins. "
            f"This is the first narrative in the game, so make it welcoming and informative."
        )

        from core.game_flow.interaction_core import process_with_llm 
        result = process_with_llm(game_state, narration_prompt) 
        
        narrative_text = None
        if result.is_success and result.message:
            logger.info(f"Received welcome narrative from LLM, first 100 chars: '{result.message[:100]}...'")
            narrative_text = result.message
        else:
            logger.warning("Failed to generate welcome narrative from LLM.")
            narrative_text = "The world awaits your command..."

        # Route the initial narrative through the orchestrator so we can append quest-start messages afterwards
        try:
            if hasattr(engine, '_combat_orchestrator') and engine._combat_orchestrator:
                from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
                engine._combat_orchestrator.add_event_to_queue(
                    DisplayEvent(
                        type=DisplayEventType.NARRATIVE_GENERAL,
                        content=narrative_text,
                        role="gm",
                        target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                        gradual_visual_display=True,
                        tts_eligible=True,
                    )
                )
                # After the narrative is queued, append quest-start system messages to the queue
                try:
                    started_events = locals().get('started_events', [])
                except Exception:
                    started_events = []
                for qid_title in started_events:
                    qid, title = qid_title
                    msg = f"Quest Started: {title}"
                    engine._combat_orchestrator.add_event_to_queue(
                        DisplayEvent(
                            type=DisplayEventType.SYSTEM_MESSAGE,
                            content=msg,
                            target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                            gradual_visual_display=False,
                            tts_eligible=False,
                        )
                    )
            else:
                # Fallback: no orchestrator. Output narrative immediately, then quest messages.
                engine._output("gm", narrative_text)
                for qid, title in locals().get('started_events', []):
                    engine._output("system", f"Quest Started: {title}")
        except Exception as e:
            logger.warning(f"Failed to route initial narrative/quest-start via orchestrator: {e}")
    else:
        engine._output("gm", "The world awaits your command...")
        # With LLM disabled, we can emit quest start messages immediately afterwards (no gradual display to wait for)
        try:
            for qid, title in locals().get('started_events', []):
                engine._output("system", f"Quest Started: {title}")
        except Exception:
            pass
        
    logger.info(f"New game started for {game_state.player.name}")
    return game_state

def start_new_game(engine: 'GameEngine', player_name: str, race: str = "Human",
                   path: str = "Wanderer", background: str = "Commoner",
                   sex: str = "Male", character_image: Optional[str] = None,
                   stats: Optional[Dict[str, int]] = None) -> GameState:
    """
    Start a new game.

    Args:
        engine: The GameEngine instance.
        player_name: The name of the player character.
        race: The race of the player character.
        path: The class/path of the player character.
        background: The background of the player character.
        sex: The sex/gender of the player character.
        character_image: Path to character image.
        stats: Optional dictionary of starting stats.

    Returns:
        The new game state.
    """
    logger.info(f"Starting new game for player {player_name}")

    # Clean up existing game if present
    if engine._state_manager.current_state is not None:
        logger.info("Cleaning up existing game before starting new one")
        if engine._game_loop.is_running:
            engine._game_loop.pause()
        if engine._agent_manager is not None and engine._use_llm:
            try:
                engine._agent_manager.reset_state()
            except Exception as e:
                logger.warning(f"Error resetting agent state: {e}")

    # Create new game state
    game_state = engine._state_manager.create_new_game(
        player_name=player_name,
        race=race,
        path=path,
        background=background,
        sex=sex,
        character_image=character_image,
        stats=stats
    )
    
    # Now use the shared function to start the game with this state
    return start_new_game_with_state(engine, game_state)


def load_game(engine: 'GameEngine', filename: str) -> Optional[GameState]:
    """
    Load a game from a save file.

    Args:
        engine: The GameEngine instance.
        filename: The name of the save file.

    Returns:
        The loaded game state, or None if the load failed.
    """
    logger.info(f"Loading game from {filename}")

    # Clean up existing game if present
    if engine._state_manager.current_state is not None:
        logger.info("Cleaning up existing game before loading")
        if engine._game_loop.is_running:
            engine._game_loop.pause()
        if engine._agent_manager is not None and engine._use_llm:
            try:
                engine._agent_manager.reset_state()
            except Exception as e:
                logger.warning(f"Error resetting agent state: {e}")

    # Load the game state
    game_state = engine._state_manager.load_game(filename)

    if game_state is None:
        logger.error(f"Failed to load game from {filename}")
        engine._output("system", f"Failed to load game from {filename}")
        return None

    # Set up the game loop with the loaded world state
    engine._game_loop.set_world_state(game_state.world)

    # Sync player location with world current_location for web server compatibility
    game_state.world.current_location = game_state.player.current_location

    # Reset auto-save timer
    engine._auto_save_timer = 0

    # Initialize memory/context system if available
    try:
        if hasattr(engine._state_manager, 'initialize_memory_context'):
            engine._state_manager.initialize_memory_context(game_state)
            logger.info("Memory/context system initialized for loaded game")
    except Exception as e:
        logger.warning(f"Error initializing memory/context system: {e}")

    # Prepare agent system for the loaded game if LLM is enabled
    if engine._use_llm and engine._agent_manager is not None:
        try:
            logger.info("Preparing agent system for loaded game")
            # Reset agent state to prepare for loaded context
            engine._agent_manager.reset_state()
            logger.info("Agent manager state reset for loaded game")
        except Exception as e:
            logger.warning(f"Error preparing agent system: {e}")

    # Start/unpause the game loop if it was paused
    if engine._game_loop.is_paused:
        logger.info("Unpausing game loop for loaded game")
        engine._game_loop.unpause()

    # Output welcome back message
    engine._output(
        "gm",
        f"Welcome back, {game_state.player.name}! You are currently at {game_state.player.current_location}."
    )

    # Output system info about time using narrative description
    world_state = game_state.world
    time_description = world_state.time_of_day
    engine._output(
        "system",
        f"It is {time_description}."
    )

    # Generate reintroductory narrative if LLM is enabled (AFTER initial messages like new game)
    if engine._use_llm:
        logger.info("Generating reintroductory narrative for loaded game")
        reintroductory_narrative = _generate_reintroductory_narrative_content(engine, game_state)
        
        if reintroductory_narrative:
            logger.info(f"Received reintroductory narrative from LLM, first 100 chars: '{reintroductory_narrative[:100]}...'")
            engine._output("gm", reintroductory_narrative)
        else:
            logger.warning("Failed to generate reintroductory narrative from LLM.")
            engine._output("system", "You continue your adventure...")

    return game_state


def _generate_reintroductory_narrative_content(engine: 'GameEngine', game_state: 'GameState') -> Optional[str]:
    """
    Generate reintroductory narrative content for loaded games (without sending it).
    
    This provides context to help players re-engage with their saved game,
    summarizing their current situation and recent context.
    
    Args:
        engine: The game engine instance.
        game_state: The loaded game state.
        
    Returns:
        The generated narrative content, or None if generation failed.
    """
    try:
        # Build contextual prompt for reintroduction
        player = game_state.player
        current_location = player.current_location or "an unknown location"
        
        # Use enhanced time descriptions instead of clock time
        world_state = game_state.world
        time_of_day = world_state.atmospheric_time  # Rich atmospheric description
        
        # Get player's background/origin context if available
        background_context = ""
        if hasattr(player, 'background') and player.background:
            background_context = f"Background: {player.background}. "
        
        # Build the reintroduction prompt
        reintro_prompt = (
            f"I'm continuing my adventure as {player.name}, a {player.race} {player.path}. "
            f"{background_context}"
            f"I'm currently at {current_location}. "
            f"It is {time_of_day}. "
            f"Please provide an immersive narrative that reintroduces me to my current situation. "
            f"Describe my immediate surroundings and give me a sense of what I was doing or what's happening. "
            f"Make it atmospheric, but not overly narrative and help me get back into the story - I need all most important details from my previous game."
        )
        
        # Generate the narrative using the LLM
        logger.info("LIFECYCLE_DEBUG: About to call process_with_llm for reintroductory narrative")
        logger.info(f"LIFECYCLE_DEBUG: Prompt length: {len(reintro_prompt)} chars")
        from core.game_flow.interaction_core import process_with_llm 
        result = process_with_llm(game_state, reintro_prompt)
        
        logger.info(f"LIFECYCLE_DEBUG: process_with_llm returned - Success: {result.is_success}")
        if result.message:
            logger.info(f"LIFECYCLE_DEBUG: Result message length: {len(result.message)} chars")
            logger.info(f"LIFECYCLE_DEBUG: Result message preview: '{result.message[:200]}...'")
        else:
            logger.warning("LIFECYCLE_DEBUG: Result message is None or empty")
            
        if result.is_success and result.message:
            logger.info(f"Generated reintroductory narrative: '{result.message[:100]}...'")
            logger.info("LIFECYCLE_DEBUG: Returning generated narrative content")
            return result.message
        else:
            logger.warning("Failed to generate reintroductory narrative from LLM")
            logger.warning(f"LIFECYCLE_DEBUG: Result details - Success: {result.is_success}, Message: {result.message}")
            # Provide a simple fallback narrative
            fallback_message = (
                f"You find yourself at {current_location} as {time_of_day.lower()} settles in. "
                f"The familiar surroundings remind you of your ongoing adventure."
            )
            logger.info("LIFECYCLE_DEBUG: Returning fallback narrative content")
            return fallback_message
            
    except Exception as e:
        logger.error(f"Error generating reintroductory narrative: {e}", exc_info=True)
        # Provide a minimal fallback
        return "You take a moment to gather your bearings and continue your adventure."


def save_game(engine: 'GameEngine', filename: Optional[str] = None,
              auto_save: bool = False) -> Optional[str]:
    """
    Save the current game.

    Args:
        engine: The GameEngine instance.
        filename: The name of the save file. If None, generates a name.
        auto_save: Whether this is an auto-save.

    Returns:
        The path to the save file, or None if the save failed.
    """
    logger.info(f"Saving game{' (auto)' if auto_save else ''}")

    if engine._state_manager.current_state is None:
        logger.error("Cannot save: No current game state")
        engine._output("system", "Cannot save: No game in progress")
        return None

    # Save the game state
    save_path = engine._state_manager.save_game(filename, auto_save)

    if save_path is None:
        logger.error("Failed to save game")
        engine._output("system", "Failed to save game")
        return None

    # Output save confirmation (unless auto-save)
    if not auto_save:
        engine._output("system", f"Game saved to {os.path.basename(save_path)}")

    return save_path


def handle_tick(engine: 'GameEngine', elapsed_game_time: float) -> None:
    """
    Handle a game loop tick, primarily for auto-saving.

    Args:
        engine: The GameEngine instance.
        elapsed_game_time: The elapsed game time in seconds since the last tick.
    """
    # Increment auto-save timer (assuming _auto_save_timer is still managed by engine)
    engine._auto_save_timer += elapsed_game_time

    # Auto-save if interval has passed
    if engine._auto_save_timer >= engine._auto_save_interval:
        engine._auto_save_timer = 0
        save_game(engine, auto_save=True) # Call the save_game function in this module
