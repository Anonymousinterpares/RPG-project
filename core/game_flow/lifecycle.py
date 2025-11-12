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

from core.stats.stats_base import DerivedStatType
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

    # Ensure the engine-level RuleChecker (used by GUI flow) is clean for this session
    try:
        if hasattr(engine, "_rule_checker") and hasattr(engine._rule_checker, "reset"):
            engine._rule_checker.reset()
            logger.info("Engine RuleChecker reset for new game session.")
    except Exception as e:
        logger.warning(f"Failed to reset engine RuleChecker for new game: {e}")
    
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
                try:
                    from core.utils.logging_config import get_logger as _gl
                    _gl('GAME').info("LOCATION_MGMT: origin starting_location applied id=%s name=%s", starting_location_id, resolved_location)
                except Exception:
                    pass
            else:
                logger.warning(f"Origin '{origin_id}' has no starting_location_id. Leaving current_location unchanged.")
            
            # Set up world time/season and authoritative GameContext based on origin (or defaults)
            starting_time_period = origin_data.get('starting_time_period')
            starting_season = origin_data.get('starting_season')

            # Decide effective starting period: origin wins; else config default
            from core.base.config import get_config as _get_cfg
            cfg = _get_cfg()
            effective_period = (starting_time_period or (cfg.get("calendar.initial_time_of_day") or "morning")).strip().lower()

            # Initialize Engine GameContext BEFORE first LLM prompt (authoritative for Calendar)
            try:
                engine.set_game_context({
                    'location': { 'name': resolved_location },
                    'time_of_day': effective_period
                }, location_id=starting_location_id)
                try:
                    from core.utils.logging_config import get_logger as _gl
                    _gl('GAME').info("LOCATION_MGMT: initialized GameContext before welcome prompt id=%s name=%s tod=%s", starting_location_id, resolved_location, effective_period)
                except Exception:
                    pass
            except Exception as _e_gc_init:
                logger.warning(f"Failed to initialize GameContext before welcome prompt: {_e_gc_init}")

            # Convert time period to world.game_time so Calendar tracks GameContext
            try:
                from core.utils.time_utils import HOUR
                time_period_hours = {
                    'deep_night': 2, 'pre_dawn': 4.5, 'dawn': 6, 'morning': 9,
                    'noon': 12, 'afternoon': 15, 'evening': 18, 'sunset': 20.5, 'night': 22
                }
                target_hour = time_period_hours.get(effective_period, 9)
                game_state.world.game_time = float(target_hour) * HOUR
                logger.info(f"Set starting time (from GameContext) to {effective_period} ({target_hour}:00) for origin '{origin_id}'")
            except Exception as _e_time_map:
                logger.warning(f"Failed to set world.game_time from GameContext period: {_e_time_map}")

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

    # world.game_time is now set from GameContext period; no separate calendar time override needed.
    pass

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

                            # Build hydrated objective entry with all relevant fields for evaluation
                            hydrated_obj = {
                                "id": oid,
                                "description": desc_text,
                                "completed": False,
                                "failed": False,
                                "mandatory": bool(is_mandatory),
                            }
                            if isinstance(obj, dict):
                                for k in ["type", "target_id", "location_id", "completion_criteria", "condition_dsl", "time_limit_s", "fail_if"]:
                                    if k in obj:
                                        hydrated_obj[k] = obj[k]
                            built_objectives.append(hydrated_obj)

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

    # Seed calendar journal entry (Resonance Calendar) if configured
    try:
        from core.base.config import get_config
        cfg = get_config()
        cal_entry = (cfg.get('calendar_master.journal_entry') or {}) if cfg else {}
        if isinstance(cal_entry, dict) and cal_entry:
            # Ensure journal exists
            if not hasattr(game_state, 'journal') or not isinstance(getattr(game_state, 'journal'), dict):
                game_state.journal = {"character": "", "quests": {}, "notes": []}
            notes = game_state.journal.get('notes') if isinstance(game_state.journal, dict) else None
            if isinstance(notes, list):
                # Avoid duplicates by id or title
                entry_id = cal_entry.get('id', 'resonance_calendar')
                title = cal_entry.get('title', 'Resonance Calendar')
                already = any((isinstance(n, dict) and (n.get('id') == entry_id or n.get('title') == title)) for n in notes)
                if not already:
                    notes.append({
                        'id': entry_id,
                        'type': cal_entry.get('type', 'lore'),
                        'title': title,
                        'summary': cal_entry.get('summary', ''),
                        'content': cal_entry.get('body', cal_entry.get('content', '')),
                        'pinned': bool(cal_entry.get('pinned', False)),
                    })
    except Exception as _e_seed:
        logger.warning(f"Failed to seed calendar journal entry: {_e_seed}")

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
        logger.info("Generating welcome narration (structured)")
        narration_prompt = (
            f"I've just started a new game as {game_state.player.name}, a {game_state.player.race} {game_state.player.path}. "
            f"My background is: \"{introduction_text_for_llm}\". "
            f"Please provide an initial immersive narration based on this, describing my immediate surroundings and current situation as the game begins. "
            f"This is the first narrative in the game, so make it welcoming and informative."
        )

        # Use structured narrator path to obtain narrative and time_passage
        try:
            from core.game_flow.interaction_core import _build_interaction_context, _get_agent_response
            from core.interaction.enums import InteractionMode
            context = _build_interaction_context(game_state, InteractionMode.NARRATIVE, actor_id=getattr(game_state.player, 'id', None))
            agent_output = _get_agent_response(engine, game_state, context, narration_prompt, InteractionMode.NARRATIVE) or {}
            # Log structured agent output for welcome
            try:
                import json as _json
                logger.info(f"[LLM_AGENT_OUTPUT_STRUCTURED] {_json.dumps(agent_output, ensure_ascii=False)}")
            except Exception:
                logger.info("[LLM_AGENT_OUTPUT_STRUCTURED] <unavailable>")
            narrative_text = agent_output.get('narrative') or "The world awaits your command..."
            # Advance time for NARRATIVE welcome based on time_passage (fallback to 1m)
            try:
                from core.utils.time_utils import parse_time_string, MINUTE
                tp = agent_output.get('time_passage')
                logger.info(f"[TIME_CAPTURE] raw_time_passage_field={tp!r}")
                seconds = parse_time_string(tp) if tp else None
                if seconds is None:
                    seconds = 1 * MINUTE
                if getattr(game_state, 'world', None):
                    logger.info(f"[TIME_CAPTURE] computed_seconds={seconds}")
                    from core.time.time_controller import get_time_controller
                    get_time_controller().apply_llm_increment(game_state.world, seconds)
            except Exception as e_time:
                logger.warning(f"Welcome time passage handling failed: {e_time}")
        except Exception as e:
            logger.warning(f"Structured welcome generation failed: {e}")
            narrative_text = "The world awaits your command..."
    else:
        narrative_text = "The world awaits your command..."
        # With LLM disabled, we can emit quest start messages immediately afterwards (no gradual display to wait for)
        try:
            titles = [title for _, title in locals().get('started_events', [])]
            if titles:
                engine._output("system", "Quests started: " + "; ".join(titles))
        except Exception:
            pass
    
    # Attach the generated narration to the game state so the worker can retrieve it
    game_state.initial_narration = narrative_text if 'narrative_text' in locals() else "The world awaits..."
        
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

    # --- FIX: Reset input-blocking flags from previous sessions ---
    if hasattr(engine, '_waiting_for_closing_narrative_display'):
        engine._waiting_for_closing_narrative_display = False
        logger.info("Reset _waiting_for_closing_narrative_display flag on engine.")
    # --- END FIX ---

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
        # Also reset the engine-level RuleChecker which is used for validation in GUI
        try:
            if hasattr(engine, "_rule_checker") and hasattr(engine._rule_checker, "reset"):
                engine._rule_checker.reset()
                logger.info("Engine RuleChecker reset before load.")
        except Exception as e:
            logger.warning(f"Failed to reset engine RuleChecker before load: {e}")

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
    # Ensure the engine-level RuleChecker is also cleared for the loaded session
    try:
        if hasattr(engine, "_rule_checker") and hasattr(engine._rule_checker, "reset"):
            engine._rule_checker.reset()
            logger.info("Engine RuleChecker reset for loaded game.")
    except Exception as e:
        logger.warning(f"Failed to reset engine RuleChecker after load: {e}")

    # Start/unpause the game loop if it was paused
    if engine._game_loop.is_paused:
        logger.info("Unpausing game loop for loaded game")
        engine._game_loop.unpause()

    # Output welcome back message
    engine._output(
        "gm",
        f"Welcome back, {game_state.player.name}! You are currently at {game_state.player.current_location}."
    )

    # If we loaded into an active combat, rehydrate turn order UI and log
    try:
        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        from core.interaction.enums import InteractionMode
        state = engine._state_manager.current_state
        cm = getattr(state, 'combat_manager', None)
        if state and state.current_mode == InteractionMode.COMBAT and cm and hasattr(engine, '_combat_orchestrator'):
            # 1) Rehydrate combat log HTML if present
            html = getattr(cm, 'display_log_html', '') or ''
            if html:
                engine._combat_orchestrator.add_event_to_queue(
                    DisplayEvent(
                        type=DisplayEventType.COMBAT_LOG_SET_HTML,
                        content=html,
                        target_display=DisplayTarget.COMBAT_LOG,
                        gradual_visual_display=False,
                        source_step='LOAD_GAME_REHYDRATE'
                    )
                )
            # 2) Emit a TURN_ORDER_UPDATE for CharacterSheet
            active_id = cm.get_current_entity_id() if hasattr(cm, 'get_current_entity_id') else getattr(cm, '_active_entity_id', None)
            turn_order_display_list = []
            for eid in getattr(cm, 'turn_order', []) or []:
                entity = cm.entities.get(eid)
                if not entity:
                    continue
                if not getattr(entity, 'is_active_in_combat', True) or not entity.is_alive():
                    turn_order_display_list.append(f"  [{getattr(entity, 'combat_name', entity.name)} - Defeated/Inactive]")
                else:
                    prefix = "→ " if eid == active_id else "  "
                    turn_order_display_list.append(f"{prefix}{getattr(entity, 'combat_name', entity.name)}")
            turn_order_event_content = {
                "turn_order_display_list": turn_order_display_list,
                "active_entity_combat_name": getattr(cm.entities.get(active_id), 'combat_name', '') if active_id in cm.entities else '',
                "is_surprise": getattr(cm, '_is_surprise_round', False),
                "round_number": getattr(cm, 'round_number', 1)
            }
            engine._combat_orchestrator.add_event_to_queue(
                DisplayEvent(
                    type=DisplayEventType.TURN_ORDER_UPDATE,
                    content=turn_order_event_content,
                    target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                    source_step='LOAD_GAME_REHYDRATE'
                )
            )
            # --- FIX: Rehydrate AP pool and UI ---
            if hasattr(cm, 'ap_pool'):
                # Fallback for old saves: if ap_pool is missing or empty, initialize it
                if not cm.ap_pool:
                    logger.info("AP pool empty on load, initializing for all combatants.")
                    if hasattr(cm, '_initialize_ap_for_all'): # Check for new helper method
                        cm._initialize_ap_for_all()
                    else: # Manual fallback
                        ap_config = getattr(cm, '_ap_config', {})
                        base_ap = ap_config.get("base_ap", 4.0)
                        for entity_id in cm.entities:
                            cm.ap_pool[entity_id] = float(base_ap)

                # Queue AP_UPDATE events for all entities to populate the UI
                for entity_id, entity in cm.entities.items():
                    stats_manager = cm._get_entity_stats_manager(entity_id)
                    if stats_manager:
                        max_ap = stats_manager.get_stat_value(DerivedStatType.MAX_AP)
                        current_ap = cm.ap_pool.get(entity_id, 0.0)
                        ap_update_event = DisplayEvent(
                            type=DisplayEventType.AP_UPDATE,
                            content={},
                            metadata={"entity_id": entity_id, "current_ap": current_ap, "max_ap": max_ap},
                            target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                            source_step='LOAD_GAME_REHYDRATE'
                        )
                        engine._combat_orchestrator.add_event_to_queue(ap_update_event)
                logger.info("Queued AP_UPDATE events for all combatants on load.")
            # --- END FIX ---
    except Exception as rehyd_err:
        logger.warning(f"Could not rehydrate combat UI on load: {rehyd_err}")

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
        
        # Generate the narrative using structured narrator
        try:
            from core.game_flow.interaction_core import _build_interaction_context, _get_agent_response
            from core.interaction.enums import InteractionMode
            context = _build_interaction_context(game_state, InteractionMode.NARRATIVE, actor_id=getattr(game_state.player, 'id', None))
            agent_output = _get_agent_response(engine, game_state, context, reintro_prompt, InteractionMode.NARRATIVE) or {}
            # Log structured agent output for reintro
            try:
                import json as _json
                logger.info(f"[LLM_AGENT_OUTPUT_STRUCTURED] {_json.dumps(agent_output, ensure_ascii=False)}")
            except Exception:
                logger.info("[LLM_AGENT_OUTPUT_STRUCTURED] <unavailable>")
            narrative = agent_output.get('narrative')
            if narrative:
                # Advance time outside combat (NARRATIVE): use time_passage fallback to 1m
                try:
                    from core.utils.time_utils import parse_time_string, MINUTE
                    tp = agent_output.get('time_passage')
                    logger.info(f"[TIME_CAPTURE] raw_time_passage_field={tp!r}")
                    seconds = parse_time_string(tp) if tp else None
                    if seconds is None:
                        seconds = 1 * MINUTE
                    if getattr(game_state, 'world', None):
                        logger.info(f"[TIME_CAPTURE] computed_seconds={seconds}")
                        from core.time.time_controller import get_time_controller
                        get_time_controller().apply_llm_increment(game_state.world, seconds)
                except Exception as e_time:
                    logger.warning(f"Reintro time passage handling failed: {e_time}")
                return narrative
        except Exception as e:
            logger.warning(f"Structured reintro generation failed: {e}")

        # Fallback logic for when narrative generation fails or returns empty.
        logger.warning("Failed to generate reintroductory narrative. Using fallback.")
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
              auto_save: bool = False, background_summary: Optional[str] = None, 
              last_events_summary: Optional[str] = None) -> Optional[str]:
    """
    Save the current game.

    Args:
        engine: The GameEngine instance.
        filename: The name of the save file. If None, generates a name.
        auto_save: Whether this is an auto-save.
        background_summary: An optional LLM-generated summary of the player's background.
        last_events_summary: An optional LLM-generated summary of recent events.

    Returns:
        The path to the save file, or None if the save failed.
    """
    logger.info(f"Saving game{' (auto)' if auto_save else ''}")

    if engine._state_manager.current_state is None:
        logger.error("Cannot save: No current game state")
        engine._output("system", "Cannot save: No game in progress")
        return None

    # Pass the summaries to the state manager's save method
    save_path = engine._state_manager.save_game(filename, auto_save, background_summary, last_events_summary)

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
    DEPRECATED (Phase 1): Tick-driven autosave has been migrated to a scheduler
    independent of GameLoop. This function remains for backward compatibility
    but should no longer be used as a driver for autosave or time-based logic.

    Args:
        engine: The GameEngine instance.
        elapsed_game_time: The elapsed game time in seconds since the last tick.
    """
    logger.debug("handle_tick called but deprecated in Phase 1; no autosave triggered here.")
    # If any future non-time-driving periodic tasks are needed, they can be handled elsewhere.
    return
