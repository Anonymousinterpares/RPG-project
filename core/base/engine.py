#!/usr/bin/env python3
"""
Game engine for the RPG game.

This module provides the central GameEngine class that coordinates
between state management, command processing, and game loop components.
"""


import time
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, Signal, Slot
from core.combat.enums import CombatStep, CombatState
from core.interaction.enums import InteractionMode
from core.orchestration.events import DisplayEventType
from core.utils.logging_config import get_logger
from core.base.state import StateManager, GameState
from core.base.commands import CommandProcessor, CommandResult
from core.base.game_loop import GameLoop, GameSpeed
from core.base.config import get_config
from core.agents.agent_manager import get_agent_manager 
from core.agents.rule_checker import RuleCheckerAgent
from core.agents.combat_narrator import get_combat_narrator_agent 
from core.stats.stats_manager import get_stats_manager 
from core.character.npc_manager import get_npc_manager as get_entity_manager 
from core.inventory.item_manager import get_inventory_manager as get_item_manager 
from core.inventory import register_inventory_commands 

# Import the new game flow modules
from core.game_flow import lifecycle
from core.game_flow import command_router
from core.game_flow.input_router import get_input_router

logger = get_logger("GAME_ENGINE") 

class GameEngine(QObject): 
    """
    Central game engine.
    
    This class coordinates between the state manager, command processor,
    and game loop. It provides a high-level API for controlling the game.
    """
    output_generated = Signal(str, str) 
    
    _instance = None
    orchestrated_event_to_ui = Signal(object)

    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(GameEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the game engine."""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        super().__init__()
        logger.info("Initializing GameEngine")
        
        self._config = get_config()
        self._state_manager = StateManager()
        self._command_processor = CommandProcessor()
        self._game_loop = GameLoop()

        try:
            from core.character.npc_system import NPCSystem
            self._npc_system = NPCSystem() 
            self._state_manager.set_npc_system(self._npc_system) 
            logger.info("NPCSystem initialized and set in StateManager.")
        except Exception as e:
            logger.error(f"Failed to initialize or set NPCSystem in StateManager: {e}", exc_info=True)
            self._npc_system = None 

        self._agent_manager = get_agent_manager()
        self._entity_manager = get_entity_manager() 
        self._item_manager = get_item_manager() 
        self._stats_manager = get_stats_manager() 
        
        self._rule_checker = RuleCheckerAgent(
            entity_manager=self._entity_manager,
            item_manager=self._item_manager,
            stats_manager=self._stats_manager,
        )
        
        self._running = False
        self._auto_save_timer = 0

        self._combat_narrator_agent = get_combat_narrator_agent()
        logger.info(f"Combat narrator agent initialized: {self._combat_narrator_agent is not None}")
        logger.info(f"Combat narrator has narrate_outcome: {hasattr(self._combat_narrator_agent, 'narrate_outcome')}")

        from core.orchestration.combat_orchestrator import CombatOutputOrchestrator
        from core.audio.tts_manager import TTSManager 
        self._combat_orchestrator = CombatOutputOrchestrator(self) 
        self._tts_manager = TTSManager(self) 
        self._combat_orchestrator.set_references(self, self._tts_manager)
        self._combat_orchestrator.load_config() 

        self._game_loop.add_tick_callback(self._handle_tick_callback)
        
        self._auto_save_interval = self._config.get("game.auto_save_interval", 300)  
        
        register_inventory_commands()
        
        self._input_router = get_input_router()
        
        self._use_llm = True  
        self._waiting_for_closing_narrative_display: bool = False # New flag for ECFA
        self._post_combat_finalization_in_progress: bool = False  # Prevent duplicate auto-finalization
        
        self._initialized = True
        logger.info("GameEngine initialized")
    
    # Compatibility properties and methods for web server integration
    @property
    def state_manager(self):
        """Compatibility property for web server."""
        return self._state_manager
    
    @property
    def game_loop(self):
        """Compatibility property for web server."""
        return self._game_loop
    
    def initialize(self, new_game=True, player_name="Player", race="Human", 
                   path="Wanderer", background="Commoner", sex="Male",
                   character_image=None, use_llm=True, 
                   origin_id: Optional[str] = None): # Added origin_id
        """
        Initialize the game engine with a new or loaded game.
        
        This is a compatibility method for the web server integration.
        
        Args:
            new_game: Whether to start a new game or not.
            player_name: The name of the player character (for new games).
            race: The race of the player character (for new games).
            path: The class/path of the player character (for new games).
            background: The background of the player character (for new games).
            sex: The sex/gender of the player character (for new games).
            character_image: Path to character image (for new games).
            use_llm: Whether to enable LLM functionality.
            origin_id: The ID of the player's chosen origin (for new games).
        
        Returns:
            The game state.
        """
        # First, handle game initialization
        game_state = None
        if new_game:
            game_state = self.start_new_game(
                player_name=player_name, 
                race=race,
                path=path, 
                background=background,
                sex=sex,
                character_image=character_image,
                origin_id=origin_id # Pass origin_id
            )
        else:
            game_state = self._state_manager.current_state
        
        # Then, configure LLM as requested
        if use_llm != self._use_llm:
            self.set_llm_enabled(use_llm)
        
        return game_state
    
    def start_new_game(self, player_name: str, race: str = "Human", 
                        path: str = "Wanderer", background: str = "Commoner",
                        sex: str = "Male", character_image: Optional[str] = None,
                        stats: Optional[Dict[str, int]] = None, 
                        origin_id: Optional[str] = None) -> GameState:
        """
        Start a new game.
        
        This method properly handles starting a new game regardless of the current state.
        If there's an ongoing game, it will be properly cleaned up first.
        
        Args:
            player_name: The name of the player character.
            race: The race of the player character.
            path: The class/path of the player character.
            background: The background of the player character.
            sex: The sex/gender of the player character.
            character_image: Path to character image.
        
        Returns:
            The new game state.
        """
        logger.info(f"Starting new game for player {player_name}")
        
        # Clean up existing game if present
        if self._state_manager.current_state is not None:
            logger.info("Cleaning up existing game before starting new one")
            # Stop the game loop if it's running
            if self._game_loop.is_running:
                self._game_loop.pause()
                
            # Reset agent state if LLM is enabled
            if self._agent_manager is not None and self._use_llm:
                try:
                    self._agent_manager.reset_state()
                except Exception as e:
                    logger.warning(f"Error resetting agent state: {e}")
        
        # Create new game state - this will be passed to lifecycle.start_new_game
        # We don't want to create a new one there as well
        game_state = self._state_manager.create_new_game(
            player_name=player_name,
            race=race,
            path=path,
            background=background,
            sex=sex,
            character_image=character_image,
            stats=stats,
            origin_id=origin_id # Pass origin_id
        )
        if background: # background from params is the origin description
            game_state.player.background = background # Ensure it's set if not already set by StateManager

        return lifecycle.start_new_game_with_state(
            self, game_state
        )
    
    def load_game(self, filename: str) -> Optional[GameState]:
        """
        Load a game from a save file.
        
        This method handles loading a game state with proper initialization of
        all systems, including LLM integration if enabled.
        
        Args:
            filename: The name of the save file.
        
        Returns:
            The loaded game state, or None if the load failed.
        """
        # Delegate to the lifecycle module
        return lifecycle.load_game(self, filename)

    
    def save_game(self, filename: Optional[str] = None, 
                 auto_save: bool = False) -> Optional[str]:
        """
        Save the current game.
        
        Args:
            filename: The name of the save file. If None, generates a name.
            auto_save: Whether this is an auto-save.
        
        Returns:
            The path to the save file, or None if the save failed.
        """
        # Delegate to the lifecycle module
        return lifecycle.save_game(self, filename, auto_save)

    
    def process_command(self, command_text: str) -> CommandResult:
        """
        Process a command.
        
        This method delegates to the CommandProcessor or AgentManager to handle the command,
        then processes any side effects (like exiting the game).
        
        Args:
            command_text: The command text to process.
        
        Returns:
            The result of executing the command.
        """
        # Delegate command processing to the command router module
        return command_router.route_command(self, command_text)
        
    def process_input(self, command_text: str) -> CommandResult:
        """
        Process player input. Checks for combat end state first.

        Args:
            command_text: The text input from the player.

        Returns:
            The result of processing the input.
        """
        game_state = self._state_manager.current_state
        if not game_state:
            logger.warning("Cannot process input: No current game state")
            return CommandResult.error("No game in progress.")

        # If waiting for closing narrative, don't process new input
        if self._waiting_for_closing_narrative_display:
            logger.info("Input received while waiting for closing narrative display. Ignoring.")
            return CommandResult.error("Please wait for the current action to complete.")

        # --- Check for Combat End State First ---
        if game_state.current_mode == InteractionMode.COMBAT:
            combat_manager = game_state.combat_manager
            if combat_manager and combat_manager.current_step == CombatStep.COMBAT_ENDED:
                logger.info("CombatManager step is COMBAT_ENDED. Transitioning to NARRATIVE mode.")
                
                game_state.set_interaction_mode(InteractionMode.NARRATIVE)
                final_combat_outcome = combat_manager.state.name if combat_manager.state else "Unknown"
                
                # Clear combat manager from game state and orchestrator
                game_state.combat_manager = None 
                if hasattr(self, '_combat_orchestrator'):
                    self._combat_orchestrator.set_combat_manager(None)
                    self._combat_orchestrator.clear_queue_and_reset_flags() # Clear any pending combat events

                # Queue system message for "Combat has concluded" via orchestrator for MAIN_GAME_OUTPUT
                # This assumes the orchestrator might be used for NARRATIVE mode outputs too, or a similar one exists.
                # For now, we'll make the orchestrator handle this specific post-combat sequence.
                from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
                
                system_end_event = DisplayEvent(
                    type=DisplayEventType.SYSTEM_MESSAGE,
                    content=f"Combat has concluded. Outcome: {final_combat_outcome}.",
                    target_display=DisplayTarget.MAIN_GAME_OUTPUT, # Important: To GameOutputWidget
                    gradual_visual_display=False,
                    tts_eligible=False 
                )
                self._combat_orchestrator.add_event_to_queue(system_end_event)

                if self._use_llm:
                    closing_prompt = f"The combat has just ended. The outcome was: {final_combat_outcome}. Provide a brief, immersive closing narrative (1-2 sentences) describing the aftermath for the player."
                    
                    # This needs to be handled carefully. We need the LLM call to happen,
                    # then its result queued with the orchestrator.
                    # The actual input processing (command_text) should wait until this whole sequence is done.
                    
                    # For now, let's set a flag and the orchestrator will handle the LLM call after the system message.
                    # This is complex. Simpler: GameEngine makes LLM call, then queues result.
                    self._waiting_for_closing_narrative_display = True # Block further input

                    # Perform LLM call for closing narrative (can be async or in a separate thread later)
                    try:
                        from core.game_flow.interaction_core import process_with_llm # Local import
                        logger.info(f"Requesting closing combat narrative with prompt: {closing_prompt}")
                        closing_result = process_with_llm(game_state, closing_prompt) # Pass GameState to LLM
                        
                        if closing_result.is_success and closing_result.message:
                            closing_narrative_event = DisplayEvent(
                                type=DisplayEventType.NARRATIVE_GENERAL,
                                content=closing_result.message,
                                role="gm",
                                target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                                gradual_visual_display=True,
                                tts_eligible=True
                            )
                            self._combat_orchestrator.add_event_to_queue(closing_narrative_event)
                            logger.info(f"Queued closing combat narrative. Waiting for display.")
                        else:
                            logger.warning("Failed to generate closing combat narrative from LLM.")
                            self._waiting_for_closing_narrative_display = False # Allow input if LLM fails
                            
                    except Exception as e:
                        logger.error(f"Error generating closing combat narrative: {e}", exc_info=True)
                        self._waiting_for_closing_narrative_display = False # Allow input on error

                else: # LLM disabled, just log conclusion
                    logger.info(f"LLM disabled. Combat concluded ({final_combat_outcome}).")

                # If not waiting for LLM narrative (or it failed), allow new input.
                # Otherwise, return "processing" to block further input until narrative displays.
                if not self._waiting_for_closing_narrative_display:
                    logger.info(f"Mode transitioned to NARRATIVE. Now processing initial input: '{command_text}'")
                    # Fall through to process the current command_text in NARRATIVE mode
                else:
                    logger.info("Waiting for closing combat narrative to display before processing new input.")
                    return CommandResult.success("Concluding combat...") # Indicate processing

            elif not combat_manager and game_state.current_mode == InteractionMode.COMBAT:
                logger.error("In COMBAT mode but CombatManager is None. Resetting to NARRATIVE.")
                game_state.set_interaction_mode(InteractionMode.NARRATIVE)
                if hasattr(self, '_combat_orchestrator'):
                    self._combat_orchestrator.set_combat_manager(None)


        # --- Proceed with Input Routing (using the potentially updated mode) ---
        return self._input_router.route_input(self, command_text)

    def _finalize_combat_transition_if_needed(self) -> None:
        """Automatically transition to NARRATIVE and queue post-combat output when combat ends successfully.
        This is invoked by the Orchestrator when it becomes idle after the final combat event.
        It intentionally does nothing for PLAYER_DEFEAT because Game Over is handled elsewhere in the GUI.
        """
        try:
            game_state = self._state_manager.current_state
            if not game_state:
                return
            # Only react if currently in COMBAT mode
            if game_state.current_mode != InteractionMode.COMBAT:
                return
            combat_manager = getattr(game_state, 'combat_manager', None)
            if not combat_manager:
                return
            # Only proceed when CombatManager signaled the end of combat
            if combat_manager.current_step != CombatStep.COMBAT_ENDED:
                return
            # Skip auto-transition on player defeat (Game Over flow handles this)
            if getattr(combat_manager, 'state', None) == CombatState.PLAYER_DEFEAT:
                logger.info("Auto finalize skipped: PLAYER_DEFEAT handled by Game Over flow.")
                return

            if self._post_combat_finalization_in_progress:
                # Avoid duplicate invocations
                return
            self._post_combat_finalization_in_progress = True

            # Transition mode and detach combat manager
            game_state.set_interaction_mode(InteractionMode.NARRATIVE)
            final_combat_outcome = combat_manager.state.name if getattr(combat_manager, 'state', None) else "Unknown"
            game_state.combat_manager = None

            # Reset orchestrator for post-combat messages
            if hasattr(self, '_combat_orchestrator') and self._combat_orchestrator:
                self._combat_orchestrator.set_combat_manager(None)
                self._combat_orchestrator.clear_queue_and_reset_flags()

            # Ensure UI reflects the mode change promptly
            try:
                from PySide6.QtCore import QTimer
                if hasattr(self, 'main_window_ref') and self.main_window_ref:
                    main_window = self.main_window_ref()
                    if main_window and hasattr(main_window, '_update_ui'):
                        QTimer.singleShot(0, main_window._update_ui)
            except Exception:
                pass

            # Queue post-combat system message and closing narrative via orchestrator
            try:
                from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
                system_end_event = DisplayEvent(
                    type=DisplayEventType.SYSTEM_MESSAGE,
                    content=f"Combat has concluded. Outcome: {final_combat_outcome}.",
                    target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                    gradual_visual_display=False,
                    tts_eligible=False
                )
                if hasattr(self, '_combat_orchestrator') and self._combat_orchestrator:
                    self._combat_orchestrator.add_event_to_queue(system_end_event)

                if self._use_llm and hasattr(self, '_combat_orchestrator') and self._combat_orchestrator:
                    # Request a short closing narrative
                    self._waiting_for_closing_narrative_display = True
                    try:
                        from core.game_flow.interaction_core import process_with_llm
                        closing_prompt = (
                            f"The combat has just ended. The outcome was: {final_combat_outcome}. "
                            f"Provide a brief, immersive closing narrative (1-2 sentences) describing the aftermath for the player."
                        )
                        logger.info(f"Requesting closing combat narrative with prompt: {closing_prompt}")
                        closing_result = process_with_llm(game_state, closing_prompt)
                        if closing_result.is_success and closing_result.message:
                            closing_narrative_event = DisplayEvent(
                                type=DisplayEventType.NARRATIVE_GENERAL,
                                content=closing_result.message,
                                role="gm",
                                target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                                gradual_visual_display=True,
                                tts_eligible=True
                            )
                            self._combat_orchestrator.add_event_to_queue(closing_narrative_event)
                            logger.info("Queued closing combat narrative after auto-finalize.")
                        else:
                            logger.warning("Failed to generate closing combat narrative after auto-finalize.")
                            self._waiting_for_closing_narrative_display = False
                    except Exception as e:
                        logger.error(f"Error generating closing combat narrative after auto-finalize: {e}", exc_info=True)
                        self._waiting_for_closing_narrative_display = False
            except Exception as e:
                logger.error(f"Error queuing post-combat messages during auto-finalize: {e}", exc_info=True)
        finally:
            self._post_combat_finalization_in_progress = False

    def set_llm_enabled(self, enabled: bool) -> None:
        """
        Enable or disable the LLM system.

        Args:
            enabled: Whether to enable the LLM system.
        """
        self._use_llm = enabled
        logger.info(f"LLM system {'enabled' if enabled else 'disabled'}")
        if hasattr(self, '_initialized') and self._initialized and not enabled:
            self._output("system", f"LLM system disabled")

    def reload_llm_settings(self) -> None:
        """
        Reload LLM-related agent settings at runtime so provider/model changes
        take effect immediately (including during ongoing combat).
        """
        # Reload AgentManager-managed agents
        try:
            if hasattr(self, '_agent_manager') and self._agent_manager is not None:
                self._agent_manager.reload_settings()
                # After reloading settings, fully reset agent state to reinitialize any cached clients/models
                try:
                    self._agent_manager.reset_state()
                except Exception as e_reset:
                    logger.warning(f"Error resetting AgentManager state after reload: {e_reset}")
                logger.info("AgentManager settings reloaded.")
        except Exception as e:
            logger.warning(f"Error reloading AgentManager settings: {e}")
        
        # Reload Combat Narrator agent (owned by GameEngine)
        try:
            if hasattr(self, '_combat_narrator_agent') and self._combat_narrator_agent is not None:
                self._combat_narrator_agent.reload_settings()
                logger.info("CombatNarratorAgent settings reloaded.")
        except Exception as e:
            logger.warning(f"Error reloading CombatNarratorAgent settings: {e}")
        
        # Optional: Provide user feedback in UI
        try:
            self._output("system", "LLM settings reloaded.")
        except Exception:
            # Avoid failing if UI is not connected yet
            pass

    def _output(self, role: str, content: str) -> None:
        """
        Output a message by emitting the output_generated signal.
        This method is now simplified. The primary responsibility is to add to
        conversation history (if applicable) and emit the signal.
        Buffering and complex routing are handled by MainWindow and Orchestrator
        based on DisplayEvents.
        Args:
            role: The role of the speaker (e.g., "system", "gm", "player").
            content: The content of the message.
        """
        logger.info(f"ENGINE._output called with role='{role}', content='{content[:50]}...'")
        
        # Special logging for reintroductory narrative debugging
        if role == "gm" and ("night air" in content or "find yourself" in content):
            logger.info(f"LIFECYCLE_DEBUG: ENGINE._output - This appears to be reintroductory narrative")
            logger.info(f"LIFECYCLE_DEBUG: Full content length: {len(content)}")
            logger.info(f"LIFECYCLE_DEBUG: Content preview: '{content[:300]}...'")
        
        if self._state_manager.current_state is not None and role != "system":
            self._state_manager.current_state.add_conversation_entry(role, content)
            logger.debug(f"Added to conversation history: role='{role}'")

        try:
            logger.debug(f"Emitting output_generated signal with role='{role}', content (type: {type(content).__name__})")
            logger.info(f"LIFECYCLE_DEBUG: About to emit output_generated signal to GUI")
            self.output_generated.emit(role, content) # MainWindow will handle DisplayEvent objects if content is one
            logger.debug("Signal emission successful")
            logger.info(f"LIFECYCLE_DEBUG: output_generated signal emitted successfully")
        except RuntimeError as e:
            logger.error(f"RuntimeError emitting output_generated signal: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error emitting output_generated signal: {e}", exc_info=True)

    def _handle_tick_callback(self, elapsed_game_time: float) -> None:
        """Callback for game loop tick, delegates to lifecycle module."""
        lifecycle.handle_tick(self, elapsed_game_time)

    def run(self, target_fps: int = 30) -> None:
        """
        Run the game loop.
        (Kept in Engine as it manages the loop state)
        Args:
            target_fps: The target frames per second.
        """
        logger.info(f"Starting game engine with target FPS: {target_fps}")
        self._running = True
        self._game_loop.unpause()
        try:
            while self._running:
                self._game_loop.tick()
                time.sleep(1.0 / target_fps)
        except KeyboardInterrupt:
            logger.info("Game engine interrupted")
        except Exception as e:
            logger.error(f"Error in game engine: {e}", exc_info=True)
        finally:
            self._game_loop.pause()
            logger.info("Game engine stopped")

    def stop(self) -> None:
        """Stop the game engine."""
        logger.info("Stopping game engine")
        self._running = False
        self._game_loop.pause()

    def set_game_speed(self, speed: GameSpeed) -> None:
        """
        Set the game speed.
        (Kept in Engine as it controls the game loop)
        Args:
            speed: The new game speed.
        """
        self._game_loop.speed = speed
        logger.info(f"Game speed set to {speed.name}")
        self._output("system", f"Game speed set to {speed.name.lower()}")

    def toggle_pause(self) -> bool:
        """
        Toggle the game pause state.
        (Kept in Engine as it controls the game loop)
        Returns:
            The new pause state (True if paused, False if unpaused).
        """
        paused = self._game_loop.toggle_pause()
        if paused:
            self._output("system", "Game paused")
        else:
            self._output("system", "Game unpaused")
        return paused
    
    # --- ECFA Change: New method for MainWindow to call ---
    @Slot(object) # Use object for DisplayEvent type hint if DisplayEvent is complex
    def main_window_handle_orchestrated_event(self, display_event): # game_state is implicit via self._state_manager
        """
        Called by the CombatOutputOrchestrator to route a DisplayEvent's
        content to the MainWindow's _handle_game_output method.
        This decouples Orchestrator from directly knowing MainWindow.
        """
        from core.orchestration.events import DisplayEvent # Local import for type check
        if not isinstance(display_event, DisplayEvent):
            logger.error(f"Engine received non-DisplayEvent object: {type(display_event)}")
            return

        logger.debug(f"Engine routing orchestrated event to MainWindow: {display_event}")
        
        # MainWindow's _handle_game_output will now need to understand DisplayEvent or its parts
        # It's better if _handle_game_output is adapted or a new method is called.
        # For now, we pass DisplayEvent directly and expect MainWindow to adapt.
        
        # We emit a new signal or call a direct method on MainWindow.
        # Let's assume MainWindow has a slot `handle_orchestrated_display_event(DisplayEvent)`
        
        # To avoid direct MainWindow dependency here, GameEngine can emit a specific signal
        # that MainWindow listens to, or MainWindow can connect to a slot on the engine.
        # For simplicity with current structure, assuming GameEngine's output_generated
        # is caught by MainWindow which then checks if the content is a DisplayEvent.
        # This is not ideal. A more direct call/signal is better.

        # Alternative: Add a new signal on GameEngine for orchestrated events
        # class GameEngine(QObject):
        #     orchestrated_event_for_main_window = Signal(DisplayEvent) # Define this signal

        # Then emit it:
        # self.orchestrated_event_for_main_window.emit(display_event)

        # For now, re-using _output with a special role or by passing the event itself.
        # Let's modify _output slightly or add a new way for MainWindow to get this.

        # The simplest for now is to call MainWindow's handler directly if MainWindow ref is stored.
        # Assuming MainWindow is accessible via engine for this example, though this creates coupling.
        # A better way is a new signal from engine that MainWindow connects to.
        if hasattr(self, 'main_window_ref') and self.main_window_ref: # Assuming MainWindow registers itself
            main_window = self.main_window_ref()
            if main_window:
                # MainWindow needs a method to handle this, e.g., process_display_event_from_orchestrator
                if hasattr(main_window, 'process_orchestrated_display_event'):
                    main_window.process_orchestrated_display_event(display_event)
                else:
                    # Fallback: use existing _output, MainWindow's _handle_game_output must adapt
                    if isinstance(display_event.content, str):
                        self._output(display_event.role or "system", display_event.content)
                    elif isinstance(display_event.content, list) and display_event.type == DisplayEventType.BUFFER_FLUSH:
                        for line in display_event.content:
                             self._output(display_event.role or "gm", line) # Assume buffer is GM narrative
                    else:
                        logger.warning(f"Orchestrated event content type not directly printable: {type(display_event.content)}")
            else:
                logger.error("MainWindow reference lost in GameEngine.")
        else:
            logger.error("GameEngine does not have a reference to MainWindow to send orchestrated event.")    

    @Slot()
    def on_orchestrator_idle_and_combat_manager_resumed(self):
        """
        Called by the orchestrator when it's idle AND after it has signaled
        CombatManager to resume (if CM was waiting).
        This specifically handles the post-combat closing narrative.
        """
        if self._waiting_for_closing_narrative_display:
            logger.info("Orchestrator idle and CM resumed (or was not waiting). Closing narrative display should be complete.")
            self._waiting_for_closing_narrative_display = False
            # Potentially trigger UI re-enable or next game prompt if needed here.
            # For now, just unblocks further input in process_input.

# Convenience function (remains the same)
def get_game_engine() -> GameEngine:
    """Get the game engine instance."""
    return GameEngine()