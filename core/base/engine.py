#!/usr/bin/env python3
"""
Game engine for the RPG game.

This module provides the central GameEngine class that coordinates
between state management, command processing, and game loop components.
"""

import time
from typing import Any, Dict, List, Optional
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

# Import Refactored Subsystems
from core.base.context_controller import GameContextController
from core.base.audio_controller import GameAudioController
from core.game_flow.spell_handler import execute_cast_spell as _execute_cast_spell_logic

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
    
    # Signals delegated from subsystems (re-emitted for API compatibility)
    context_updated = Signal(object)
    playback_updated = Signal(object)
    music_state_updated = Signal(object)
    
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
        
        # Initialize Sub-Controllers
        self.context_controller = GameContextController(self)
        self.audio_controller = GameAudioController(self)
        
        # Connect sub-controller signals to engine signals
        self.context_controller.context_updated.connect(self.context_updated)
        self.audio_controller.playback_updated.connect(self.playback_updated)
        self.audio_controller.music_state_updated.connect(self.music_state_updated)

        # Parallel initialization of managers
        import concurrent.futures
        from core.character.npc_system import NPCSystem
        from core.music.director import get_music_director
        from core.audio.sfx_manager import SFXManager

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_npc_system = executor.submit(NPCSystem)
            future_agent_manager = executor.submit(get_agent_manager)
            future_entity_manager = executor.submit(get_entity_manager)
            future_item_manager = executor.submit(get_item_manager)
            future_stats_manager = executor.submit(get_stats_manager)
            future_combat_narrator = executor.submit(get_combat_narrator_agent)
            future_music_director = executor.submit(get_music_director, project_root=self._config.project_root if hasattr(self._config, 'project_root') else None)
            future_sfx_manager = executor.submit(SFXManager, project_root=self._config.project_root if hasattr(self._config, 'project_root') else None)

            self._npc_system = future_npc_system.result()
            self._agent_manager = future_agent_manager.result()
            self._entity_manager = future_entity_manager.result()
            self._item_manager = future_item_manager.result()
            self._stats_manager = future_stats_manager.result()
            self._combat_narrator_agent = future_combat_narrator.result()
            self._music_director = future_music_director.result()
            self._sfx_manager = future_sfx_manager.result()

        self._state_manager.set_npc_system(self._npc_system)
        logger.info("All managers initialized and ready.")

        # Phase 1: One-time log: GameLoop time advancement is disabled.
        try:
            logger.info("PHASE 1: GameLoop time advancement is DISABLED. World time advances only via LLM time_passage and post-combat increments.")
        except Exception:
            pass
        
        self._rule_checker = RuleCheckerAgent(
            entity_manager=self._entity_manager,
            item_manager=self._item_manager,
            stats_manager=self._stats_manager,
        )
        
        self._running = False
        self._auto_save_timer = 0

        from core.orchestration.combat_orchestrator import CombatOutputOrchestrator
        from core.audio.tts_manager import TTSManager 
        self._combat_orchestrator = CombatOutputOrchestrator(self) 
        self._tts_manager = TTSManager(self) 
        self._combat_orchestrator.set_references(self, self._tts_manager)
        self._combat_orchestrator.load_config() 

        self._game_loop.add_tick_callback(self._handle_tick_callback)
        
        # Phase 1 autosave refactor: turn-based autosave settings
        self._autosave_turns: int = 0  # 0 = off
        self._turns_since_autosave: int = 0
        try:
            self.reload_autosave_settings()
            logger.info(f"Autosave configured: every {self._autosave_turns} turns (0=off)")
        except Exception as e:
            logger.warning(f"Failed to load autosave settings: {e}")

        # Apply QSettings gameplay values
        try:
            from PySide6.QtCore import QSettings
            s = QSettings("RPGGame", "Settings")
            diff_ui = s.value("gameplay/difficulty", None)
            enc_ui = s.value("gameplay/encounter_size", None)
            diff_map = {"Story": "story", "Normal": "normal", "Hard": "hard", "Expert": "expert"}
            enc_map = {"Solo": "solo", "Pack": "pack", "Mixed": "mixed"}
            if diff_ui:
                self._config._config_data.setdefault("game", {})
                self._config._config_data["game"]["difficulty"] = diff_map.get(diff_ui, "normal")
            if enc_ui:
                self._config._config_data.setdefault("game", {})
                self._config._config_data["game"]["encounter_size"] = enc_map.get(enc_ui, "solo")
        except Exception:
            pass
        
        register_inventory_commands()
        
        self._input_router = get_input_router()
        self._use_llm = True  
        self._waiting_for_closing_narrative_display: bool = False
        self._post_combat_finalization_in_progress: bool = False

        self.sfx_play = None # Will be set by audio_controller via init_audio_backend

        self._initialized = True
        logger.info("GameEngine initialized")

    def init_audio_backend(self):
        """Delegate to AudioController."""
        self.audio_controller.init_audio_backend()

    # Compatibility properties and methods for web server integration
    @property
    def state_manager(self):
        return self._state_manager
    
    @property
    def game_loop(self):
        return self._game_loop
    
    def initialize(self, new_game=True, player_name="Player", race="Human", 
                   path="Wanderer", background="Commoner", sex="Male",
                   character_image=None, use_llm=True, 
                   origin_id: Optional[str] = None):
        game_state = None
        if new_game:
            game_state = self.start_new_game(
                player_name=player_name, 
                race=race,
                path=path, 
                background=background,
                sex=sex,
                character_image=character_image,
                origin_id=origin_id
            )
        else:
            game_state = self._state_manager.current_state
        
        if use_llm != self._use_llm:
            self.set_llm_enabled(use_llm)
        
        return game_state
    
    def start_new_game(self, player_name: str, race: str = "Human", 
                        path: str = "Wanderer", background: str = "Commoner",
                        sex: str = "Male", character_image: Optional[str] = None,
                        stats: Optional[Dict[str, int]] = None,
                        skills: Optional[Dict[str, int]] = None,
                        origin_id: Optional[str] = None) -> GameState:
        logger.info(f"Starting new game for player {player_name}")
        
        if self._state_manager.current_state is not None:
            logger.info("Cleaning up existing game before starting new one")
            if self._game_loop.is_running:
                self._game_loop.pause()
            if self._agent_manager is not None and self._use_llm:
                try:
                    self._agent_manager.reset_state()
                except Exception as e:
                    logger.warning(f"Error resetting agent state: {e}")
        
        # Reset orchestrator and NPC system
        try:
            self._waiting_for_closing_narrative_display = False
            self._post_combat_finalization_in_progress = False
            if hasattr(self, '_combat_orchestrator') and self._combat_orchestrator:
                try:
                    self._combat_orchestrator.set_combat_manager(None)
                except Exception:
                    pass
                self._combat_orchestrator.clear_queue_and_reset_flags()
                try:
                    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
                    clear_event = DisplayEvent(
                        type=DisplayEventType.COMBAT_LOG_SET_HTML,
                        content="",
                        role='system',
                        target_display=DisplayTarget.COMBAT_LOG,
                        gradual_visual_display=False,
                        tts_eligible=False,
                        source_step='NEW_GAME_RESET'
                    )
                    self._combat_orchestrator.add_event_to_queue(clear_event)
                except Exception:
                    pass
            try:
                if hasattr(self, '_npc_system') and self._npc_system:
                    self._npc_system.clear_all_npcs()
                    logger.info("NPCSystem cleared for new game session.")
            except Exception as npce:
                logger.warning(f"Failed to clear NPCSystem for new game: {npce}")
        except Exception as e:
            logger.warning(f"Error resetting orchestrator/flags before new game: {e}")

        game_state = self._state_manager.create_new_game(
            player_name=player_name,
            race=race,
            path=path,
            background=background,
            sex=sex,
            character_image=character_image,
            stats=stats,
            skills=skills,
            origin_id=origin_id
        )
        if background:
            game_state.player.background = background

        # Autoplay music setup
        try:
            if hasattr(self, '_music_director') and self._music_director:
                try:
                    from PySide6.QtCore import QSettings
                    s = QSettings("RPGGame", "Settings")
                    min_i = s.value("sound/autoplay_min_intensity", 0.6)
                    try:
                        min_i = float(min_i)
                    except Exception:
                        min_i = 0.6
                    autoplay_i = max(0.0, min(1.0, float(min_i)))
                except Exception:
                    autoplay_i = 0.6
                self._music_director.hard_set("ambient", intensity=autoplay_i, reason="new_game")
        except Exception:
            pass

        gs = lifecycle.start_new_game_with_state(self, game_state)
        
        try:
            if hasattr(self, '_sfx_manager') and self._sfx_manager:
                self._sfx_manager.play_one_shot('event','game_start')
        except Exception:
            pass
        
        return gs
    
    def load_game(self, filename: str) -> Optional[GameState]:
        loaded_state = lifecycle.load_game(self, filename)
        # Ensure music/context active
        try:
            md = getattr(self, 'get_music_director', lambda: None)()
            if loaded_state:
                try:
                    saved_ctx = getattr(loaded_state, 'game_context', None)
                    if isinstance(saved_ctx, dict) and saved_ctx:
                        self.set_game_context(saved_ctx, source="load_game")
                    else:
                        loc_name = getattr(getattr(loaded_state, 'world', None), 'current_location', None) or getattr(getattr(loaded_state, 'player', None), 'current_location', '')
                        loc_major = self.context_controller.get_location_major()
                        tod = getattr(getattr(loaded_state, 'world', None), 'time_of_day', None)
                        self.set_game_context({"location": {"name": str(loc_name or ""), "major": loc_major}, "time_of_day": tod})
                except Exception:
                    pass
            if md and loaded_state:
                # Restore music mood
                mood = getattr(loaded_state, 'music_mood', None)
                intensity = getattr(loaded_state, 'music_intensity', None)
                try:
                    from PySide6.QtCore import QSettings
                    s = QSettings("RPGGame", "Settings")
                    min_i = s.value("sound/autoplay_min_intensity", 0.6)
                    try:
                        min_i = float(min_i)
                    except Exception:
                        min_i = 0.6
                    min_i = max(0.0, min(1.0, float(min_i)))
                except Exception:
                    min_i = 0.6
                if isinstance(mood, str) and mood:
                    try:
                        if isinstance(intensity, (int, float)):
                            final_i = max(float(intensity), min_i)
                        else:
                            final_i = min_i
                    except Exception:
                        final_i = min_i
                    md.hard_set(mood, intensity=final_i, reason="load_game")
                else:
                    md.hard_set("ambient", intensity=min_i, reason="load_game_fallback")
        except Exception:
            pass
        
        try:
            if loaded_state and hasattr(self, '_sfx_manager') and self._sfx_manager:
                self._sfx_manager.play_one_shot('event', 'game_start')
        except Exception:
            pass
        return loaded_state

    def save_game(self, filename: Optional[str] = None, 
                 auto_save: bool = False) -> Optional[str]:
        if self._state_manager.current_state is None:
            logger.error("Cannot save: No current game state")
            self._output("system", "Cannot save: No game in progress")
            return None

        # Capture music/context into state before save
        try:
            md = getattr(self, 'get_music_director', lambda: None)()
            st = self._state_manager.current_state
            if st:
                try:
                    if md:
                        st.music_mood = getattr(md, '_mood', None)
                        st.music_intensity = float(getattr(md, '_intensity', 0.3))
                except Exception:
                    pass
                try:
                    st.game_context = self.get_game_context()
                except Exception:
                    pass
        except Exception:
            pass

        # Generate Summaries using LLM (logic delegated to lifecycle via state manager hook)
        # Note: logic remains largely in lifecycle/engine currently for prompt gen.
        background_summary = None
        last_events_summary = None
        
        if self._use_llm and self._agent_manager:
            state = self._state_manager.current_state
            try:
                if state.player and state.player.background:
                    prompt = (
                        f"Summarize the following character background in one or two engaging sentences. "
                        f"Focus on the character's origin and key identity.\n\n"
                        f"BACKGROUND:\n{state.player.background}"
                    )
                    messages = [{"role": "user", "content": prompt}]
                    response = self._agent_manager._narrator_agent._llm_manager.get_completion(messages, max_tokens=100)
                    if response and response.content:
                        background_summary = response.content.strip()
            except Exception:
                pass

            try:
                if state.conversation_history:
                    recent_history = state.conversation_history[-10:]
                    formatted_history = "\n".join([f"{entry['role']}: {entry['content']}" for entry in recent_history])
                    prompt = (
                        f"Based on the following recent conversation log, write a brief, one-paragraph summary "
                        f"of the player's most recent activities and current situation.\n\n"
                        f"RECENT LOG:\n{formatted_history}"
                    )
                    messages = [{"role": "user", "content": prompt}]
                    response = self._agent_manager._narrator_agent._llm_manager.get_completion(messages, max_tokens=150)
                    if response and response.content:
                        last_events_summary = response.content.strip()
            except Exception:
                pass

        return lifecycle.save_game(self, filename, auto_save, background_summary, last_events_summary)

    def reload_autosave_settings(self) -> None:
        try:
            from PySide6.QtCore import QSettings
            s = QSettings("RPGGame", "Settings")
            turns = s.value("gameplay/autosave_interval", 0, int)
            if turns is None:
                turns = 0
            self._autosave_turns = max(0, int(turns))
            self._turns_since_autosave = 0
            logger.info(f"Reloaded autosave setting: {self._autosave_turns} turns (0=off)")
        except Exception as e:
            logger.warning(f"Could not reload autosave settings: {e}")
    
    def _maybe_autosave_after_narrative(self) -> None:
        try:
            try:
                from PySide6.QtCore import QSettings
                turns = QSettings("RPGGame", "Settings").value("gameplay/autosave_interval", 0, int)
                self._autosave_turns = max(0, int(turns or 0))
            except Exception:
                pass
            
            if self._autosave_turns and self._autosave_turns > 0:
                self._turns_since_autosave += 1
                if self._turns_since_autosave >= self._autosave_turns:
                    self._turns_since_autosave = 0
                    try:
                        lifecycle.save_game(self, auto_save=True)
                        logger.info("Auto-saved game after reaching narrative turn threshold.")
                    except Exception as e:
                        logger.warning(f"Autosave failed: {e}")
        except Exception as e:
            logger.warning(f"Autosave counter error: {e}")
    
    def process_command(self, command_text: str) -> CommandResult:
        return command_router.route_command(self, command_text)
        
    def execute_cast_spell(self, spell_id: str, target_id: Optional[str] = None, enforce_known_spells: bool = True) -> CommandResult:
        """Delegate spell casting to the new spell handler."""
        return _execute_cast_spell_logic(self, spell_id, target_id, enforce_known_spells)

    def process_input(self, command_text: str) -> CommandResult:
        """
        Process player input. Checks for combat end state first.
        """
        game_state = self._state_manager.current_state
        if not game_state:
            return CommandResult.error("No game in progress.")

        if self._waiting_for_closing_narrative_display:
            logger.info("Input received while waiting for closing narrative display. Ignoring.")
            return CommandResult.error("Please wait for the current action to complete.")

        # Check Combat End State
        if game_state.current_mode == InteractionMode.COMBAT:
            combat_manager = game_state.combat_manager
            if combat_manager and combat_manager.current_step == CombatStep.COMBAT_ENDED:
                logger.info("CombatManager step is COMBAT_ENDED. Transitioning to NARRATIVE mode.")
                
                game_state.set_interaction_mode(InteractionMode.NARRATIVE)
                try:
                    if getattr(game_state, 'world', None):
                        from core.time.time_controller import get_time_controller
                        get_time_controller().apply_post_combat_increment(game_state.world)
                except Exception:
                    pass
                final_combat_outcome = combat_manager.state.name if combat_manager.state else "Unknown"
                
                game_state.combat_manager = None 
                if hasattr(self, '_combat_orchestrator'):
                    self._combat_orchestrator.set_combat_manager(None)
                    self._combat_orchestrator.clear_queue_and_reset_flags()

                from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
                
                system_end_event = DisplayEvent(
                    type=DisplayEventType.SYSTEM_MESSAGE,
                    content=f"Combat has concluded. Outcome: {final_combat_outcome}.",
                    target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                    gradual_visual_display=False,
                    tts_eligible=False 
                )
                self._combat_orchestrator.add_event_to_queue(system_end_event)

                if self._use_llm:
                    closing_prompt = f"The combat has just ended. The outcome was: {final_combat_outcome}. Provide a brief, immersive closing narrative (1-2 sentences) describing the aftermath for the player."
                    self._waiting_for_closing_narrative_display = True

                    try:
                        from core.game_flow.interaction_core import _build_interaction_context, _get_agent_response
                        logger.info(f"Requesting closing combat narrative with prompt: {closing_prompt}")
                        context = _build_interaction_context(game_state, InteractionMode.COMBAT, actor_id=getattr(game_state.player, 'id', None))
                        agent_output = _get_agent_response(self, game_state, context, closing_prompt, InteractionMode.COMBAT)
                        closing_text = agent_output.get('narrative') if agent_output else None
                        if closing_text:
                            closing_narrative_event = DisplayEvent(
                                type=DisplayEventType.NARRATIVE_GENERAL,
                                content=closing_text,
                                role="gm",
                                target_display=DisplayTarget.MAIN_GAME_OUTPUT,
                                gradual_visual_display=True,
                                tts_eligible=True
                            )
                            self._combat_orchestrator.add_event_to_queue(closing_narrative_event)
                            logger.info(f"Queued closing combat narrative. Waiting for display.")
                        else:
                            self._waiting_for_closing_narrative_display = False
                            
                    except Exception as e:
                        logger.error(f"Error generating closing combat narrative: {e}", exc_info=True)
                        self._waiting_for_closing_narrative_display = False

                else:
                    logger.info(f"LLM disabled. Combat concluded ({final_combat_outcome}).")

                if not self._waiting_for_closing_narrative_display:
                    logger.info(f"Mode transitioned to NARRATIVE. Now processing initial input: '{command_text}'")
                else:
                    logger.info("Waiting for closing combat narrative to display before processing new input.")
                    return CommandResult.success("Concluding combat...")

            elif not combat_manager and game_state.current_mode == InteractionMode.COMBAT:
                logger.error("In COMBAT mode but CombatManager is None. Resetting to NARRATIVE.")
                game_state.set_interaction_mode(InteractionMode.NARRATIVE)
                if hasattr(self, '_combat_orchestrator'):
                    self._combat_orchestrator.set_combat_manager(None)

        return self._input_router.route_input(self, command_text)

    def _finalize_combat_transition_if_needed(self) -> None:
        """Automatically transition to NARRATIVE and queue post-combat output when combat ends successfully."""
        try:
            game_state = self._state_manager.current_state
            if not game_state:
                return
            if game_state.current_mode != InteractionMode.COMBAT:
                return
            combat_manager = getattr(game_state, 'combat_manager', None)
            if not combat_manager:
                return
            if combat_manager.current_step != CombatStep.COMBAT_ENDED:
                return
            if getattr(combat_manager, 'state', None) == CombatState.PLAYER_DEFEAT:
                return

            if self._post_combat_finalization_in_progress:
                return
            self._post_combat_finalization_in_progress = True

            # Transition mode and detach combat manager
            game_state.set_interaction_mode(InteractionMode.NARRATIVE)
            try:
                if getattr(game_state, 'world', None):
                    from core.time.time_controller import get_time_controller
                    get_time_controller().apply_post_combat_increment(game_state.world)
            except Exception:
                pass
            final_combat_outcome = combat_manager.state.name if getattr(combat_manager, 'state', None) else "Unknown"
            
            try:
                if hasattr(self, '_sfx_manager') and self._sfx_manager:
                    st = getattr(combat_manager, 'state', None)
                    if st == CombatState.PLAYER_DEFEAT:
                        self._sfx_manager.play_one_shot('event','defeat')
                    elif st == CombatState.FLED:
                        self._sfx_manager.play_one_shot('event','flee')
                    else:
                        self._sfx_manager.play_one_shot('event','victory')
            except Exception:
                pass

            try:
                participants = []
                if combat_manager.entities:
                    for entity in combat_manager.entities.values():
                        participants.append(f"{entity.name} ({entity.entity_type.name})")
                summary_text = f"[COMBAT ENDED] Outcome: {final_combat_outcome}. Participants: {', '.join(participants)}."
                game_state.add_conversation_entry("system", summary_text)
            except Exception as e:
                logger.warning(f"Failed to add combat summary to history: {e}")

            game_state.combat_manager = None

            if hasattr(self, '_combat_orchestrator') and self._combat_orchestrator:
                self._combat_orchestrator.set_combat_manager(None)
                self._combat_orchestrator.clear_queue_and_reset_flags()

            try:
                from PySide6.QtCore import QTimer
                if hasattr(self, 'main_window_ref') and self.main_window_ref:
                    main_window = self.main_window_ref()
                    if main_window and hasattr(main_window, '_update_ui'):
                        QTimer.singleShot(0, main_window._update_ui)
            except Exception:
                pass

            try:
                md = getattr(self, 'get_music_director', lambda: None)()
                prev_mood = getattr(self, '_pre_combat_mood', None)
                prev_i = getattr(self, '_pre_combat_intensity', None)
                if md and prev_mood:
                    md.hard_set(prev_mood, intensity=prev_i if isinstance(prev_i, (int, float)) else None, reason="return_from_combat")
                self._pre_combat_mood = None
                self._pre_combat_intensity = None
            except Exception:
                pass

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
                            self._waiting_for_closing_narrative_display = False
                    except Exception as e:
                        logger.error(f"Error generating closing combat narrative after auto-finalize: {e}", exc_info=True)
                        self._waiting_for_closing_narrative_display = False
            except Exception as e:
                logger.error(f"Error queuing post-combat messages during auto-finalize: {e}", exc_info=True)
        finally:
            self._post_combat_finalization_in_progress = False

    def set_llm_enabled(self, enabled: bool) -> None:
        self._use_llm = enabled
        logger.info(f"LLM system {'enabled' if enabled else 'disabled'}")
        if hasattr(self, '_initialized') and self._initialized and not enabled:
            self._output("system", f"LLM system disabled")

    def reload_llm_settings(self) -> None:
        try:
            from core.llm.llm_manager import get_llm_manager
            llm_manager = get_llm_manager()
            if hasattr(llm_manager, 'reload_settings'):
                llm_manager.reload_settings()
                logger.info("LLMManager and ProviderManager settings reloaded.")
        except Exception as e:
            logger.warning(f"Error reloading LLMManager/ProviderManager settings: {e}")

        try:
            if hasattr(self, '_agent_manager') and self._agent_manager is not None:
                self._agent_manager.reload_settings()
                try:
                    self._agent_manager.reset_state()
                except Exception as e_reset:
                    logger.warning(f"Error resetting AgentManager state after reload: {e_reset}")
                logger.info("AgentManager settings reloaded.")
        except Exception as e:
            logger.warning(f"Error reloading AgentManager settings: {e}")
        
        try:
            if hasattr(self, '_combat_narrator_agent') and self._combat_narrator_agent is not None:
                self._combat_narrator_agent.reload_settings()
                logger.info("CombatNarratorAgent settings reloaded.")
        except Exception as e:
            logger.warning(f"Error reloading CombatNarratorAgent settings: {e}")
        
        try:
            self._output("system", "LLM settings reloaded.")
        except Exception:
            pass

    def _output(self, role: str, content: str) -> None:
        """
        Output a message by emitting the output_generated signal.
        """
        logger.info(f"ENGINE._output called with role='{role}', content='{content[:50]}...'")
        
        if self._state_manager.current_state is not None and role != "system":
            self._state_manager.current_state.add_conversation_entry(role, content)

        try:
            self.output_generated.emit(role, content) 
        except Exception as e:
            logger.error(f"Error emitting output_generated signal: {e}", exc_info=True)
        
        try:
            state = self._state_manager.current_state
            if role == "gm" and state is not None:
                try:
                    from core.interaction.enums import InteractionMode as _IM
                    if getattr(state, 'current_mode', None) == _IM.NARRATIVE:
                        self._maybe_autosave_after_narrative()
                except Exception:
                    mode = getattr(getattr(state, 'current_mode', None), 'name', '')
                    if mode == 'NARRATIVE':
                        self._maybe_autosave_after_narrative()
        except Exception:
            pass

    def _handle_tick_callback(self, elapsed_game_time: float) -> None:
        lifecycle.handle_tick(self, elapsed_game_time)

    def run(self, target_fps: int = 30) -> None:
        logger.warning(f"Engine.run() invoked with target FPS: {target_fps}. Time advancement is DISABLED (Phase 1).")
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
        logger.info("Stopping game engine")
        self._running = False
        self._game_loop.pause()
        try:
            self._turns_since_autosave = 0
        except Exception:
            pass

    def set_game_speed(self, speed: GameSpeed) -> None:
        self._game_loop.speed = speed
        logger.info(f"Game speed set to {speed.name}")
        self._output("system", f"Game speed set to {speed.name.lower()} (no time progression in Phase 1)")

    def toggle_pause(self) -> bool:
        paused = self._game_loop.toggle_pause()
        if paused:
            self._output("system", "Game paused")
        else:
            self._output("system", "Game unpaused")
        return paused
    
    @Slot(object)
    def main_window_handle_orchestrated_event(self, display_event):
        """
        Called by the CombatOutputOrchestrator to route a DisplayEvent's
        content to the MainWindow's _handle_game_output method.
        """
        from core.orchestration.events import DisplayEvent
        if not isinstance(display_event, DisplayEvent):
            logger.error(f"Engine received non-DisplayEvent object: {type(display_event)}")
            return

        if hasattr(self, 'main_window_ref') and self.main_window_ref:
            main_window = self.main_window_ref()
            if main_window:
                if hasattr(main_window, 'process_orchestrated_display_event'):
                    main_window.process_orchestrated_display_event(display_event)
                else:
                    # Fallback
                    if isinstance(display_event.content, str):
                        self._output(display_event.role or "system", display_event.content)
                    elif isinstance(display_event.content, list) and display_event.type == DisplayEventType.BUFFER_FLUSH:
                        for line in display_event.content:
                             self._output(display_event.role or "gm", line)
            else:
                logger.error("MainWindow reference lost in GameEngine.")
        else:
            logger.error("GameEngine does not have a reference to MainWindow to send orchestrated event.")    

    @Slot()
    def on_orchestrator_idle_and_combat_manager_resumed(self):
        if self._waiting_for_closing_narrative_display:
            logger.info("Orchestrator idle and CM resumed. Closing narrative display should be complete.")
            self._waiting_for_closing_narrative_display = False

    def request_ui_update(self) -> None:
        try:
            from PySide6.QtCore import QTimer
            if hasattr(self, 'main_window_ref') and self.main_window_ref:
                main_window = self.main_window_ref()
                if main_window and hasattr(main_window, '_update_ui'):
                    QTimer.singleShot(0, main_window._update_ui)
        except Exception as e:
            logger.error(f"Failed to request UI update: {e}")

    # --- Delegated Music Accessors ---
    def get_music_director(self):
        return getattr(self, '_music_director', None)

    def get_playback_snapshot(self) -> list[str]:
        return self.audio_controller.get_playback_snapshot()

    # --- Delegated Context Accessors ---
    def get_game_context(self) -> Dict[str, Any]:
        return self.context_controller.get_game_context()

    def set_game_context(self, ctx: Optional[Dict[str, Any]] = None, source: Optional[str] = None, **kwargs) -> None:
        self.context_controller.set_game_context(ctx, source, **kwargs)

    def get_location_major(self) -> Optional[str]:
        return self.context_controller.get_location_major()

def get_game_engine() -> GameEngine:
    return GameEngine()