"""
Manages the sequential display of combat events, including narratives,
system messages, and UI updates, respecting delays and completion signals.
"""
import collections
import logging
import weakref
from typing import Dict, Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.combat.combat_manager import CombatManager
    from core.audio.tts_manager import TTSManager # Placeholder

logger = logging.getLogger("ORCHESTRATOR") # New logger category

class CombatOutputOrchestrator(QObject):
    """
    Orchestrates the output of combat-related information to ensure
    sequential display, inter-step delays, and TTS compatibility.
    """
    # Signal to resume CombatManager processing
    resume_combat_manager = Signal()
    # Developer-mode: notify UI whether orchestrator is waiting for manual release
    dev_waiting_state_changed = Signal(bool)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.event_queue: collections.deque[DisplayEvent] = collections.deque()
        self.is_processing_event: bool = False
        self.is_waiting_for_visual: bool = False
        self.is_waiting_for_tts: bool = False # Placeholder for TTS

        self.inter_step_delay_timer: QTimer = QTimer(self)
        self.inter_step_delay_timer.setSingleShot(True)
        self.inter_step_delay_timer.timeout.connect(self._on_inter_step_delay_timeout)

        self.engine_ref: Optional[weakref.ref['GameEngine']] = None
        self.combat_manager_ref: Optional[weakref.ref['CombatManager']] = None
        self.tts_manager_ref: Optional[weakref.ref['TTSManager']] = None # Placeholder

        self.config_delay_ms: int = 1000 # Default 1 second, load from config later
        self.current_event: Optional[DisplayEvent] = None

        # Developer mode controls
        self.dev_manual_step_mode: bool = False
        self.dev_waiting_for_next_click: bool = False
        self.dev_last_skip_delay: bool = False

    def set_references(self, engine: 'GameEngine', tts_manager: Optional['TTSManager'] = None):
        """Set references to other core components. CombatManager is set per combat."""
        self.engine_ref = weakref.ref(engine)
        if tts_manager:
            self.tts_manager_ref = weakref.ref(tts_manager)
        logger.info("CombatOutputOrchestrator references set.")

    def set_combat_manager(self, combat_manager: Optional['CombatManager']):
        """Set or clear the current CombatManager reference."""
        if combat_manager:
            self.combat_manager_ref = weakref.ref(combat_manager)
            logger.debug(f"Orchestrator now referencing CombatManager: {combat_manager.id if combat_manager else 'None'}")
        else:
            self.combat_manager_ref = None
            logger.debug("Orchestrator cleared CombatManager reference.")


    def load_config(self):
        """Loads configuration, e.g., inter-step delay."""
        engine = self.engine_ref() if self.engine_ref else None
        if engine and hasattr(engine, '_config'):
            self.config_delay_ms = engine._config.get("combat.inter_step_delay_ms", 1000)
            logger.info(f"Orchestrator inter-step delay set to {self.config_delay_ms}ms from config.")
        else:
            logger.warning("Could not load orchestrator config, using default delay.")


    def add_event_to_queue(self, event: DisplayEvent):
        """Adds a DisplayEvent to the processing queue."""
        # Guard against stale rehydrate events crossing session boundaries
        try:
            engine = self.engine_ref() if self.engine_ref else None
            if engine and getattr(event, 'source_step', None) == 'REHYDRATE_FROM_SAVE':
                # Accept only if session_id matches current state's session
                expected = None
                try:
                    meta = getattr(event, 'metadata', None) or {}
                    expected = meta.get('session_id')
                except Exception:
                    expected = None
                curr_state = getattr(engine, '_state_manager', None).current_state if engine and hasattr(engine, '_state_manager') else None
                curr_sess = getattr(curr_state, 'session_id', None) if curr_state else None
                if expected is not None and curr_sess is not None and expected != curr_sess:
                    logger.info("Dropping stale REHYDRATE_FROM_SAVE event due to session_id mismatch.")
                    return
        except Exception:
            # Non-fatal: if guard fails, proceed to enqueue (better to over-show than crash)
            pass

        self.event_queue.append(event)
        logger.debug(f"Event added to queue: {event}. Queue size: {len(self.event_queue)}")
        if not self.is_processing_event and not self.inter_step_delay_timer.isActive():
            # If nothing is currently happening (not processing, not in delay), start processing.
            # This handles the case where CombatManager queues an event and immediately pauses.
            logger.debug("Orchestrator was idle, triggering _process_next_event_from_queue.")
            self._process_next_event_from_queue()


    @Slot()
    def _process_next_event_from_queue(self):
        """Processes the next event from the queue if conditions allow."""
        if self.is_processing_event or self.inter_step_delay_timer.isActive():
            logger.debug("Orchestrator busy or in delay, skipping _process_next_event_from_queue.")
            return

        if not self.event_queue:
            logger.debug("Event queue empty. Orchestrator idle.")
            combat_manager = self.combat_manager_ref() if self.combat_manager_ref else None
            engine = self.engine_ref() if self.engine_ref else None
            if combat_manager and getattr(combat_manager, 'waiting_for_display_completion', False):
                 logger.debug("Event queue empty, but CombatManager was waiting. Signalling resume (end of sub-step).")
                 self._signal_combat_manager_resume()
            elif engine and getattr(engine, '_waiting_for_closing_narrative_display', False):
                 logger.info("Orchestrator queue empty, and engine was waiting for closing narrative. Signaling engine completion.")
                 if hasattr(engine, 'on_orchestrator_idle_and_combat_manager_resumed'):
                     engine.on_orchestrator_idle_and_combat_manager_resumed()
            return

        # --- ECFA Fix: Use a local variable for the event being processed ---
        event_being_processed = self.event_queue.popleft()
        # Guard again at processing time against stale rehydrate events that were enqueued before a session change
        try:
            engine = self.engine_ref() if self.engine_ref else None
            if engine and getattr(event_being_processed, 'source_step', None) == 'REHYDRATE_FROM_SAVE':
                meta = getattr(event_being_processed, 'metadata', None) or {}
                expected = meta.get('session_id')
                curr_state = getattr(engine, '_state_manager', None).current_state if engine and hasattr(engine, '_state_manager') else None
                curr_sess = getattr(curr_state, 'session_id', None) if curr_state else None
                if expected is not None and curr_sess is not None and expected != curr_sess:
                    logger.info("Skipping processing of stale REHYDRATE_FROM_SAVE event due to session_id mismatch.")
                    # Immediately move on to next event
                    self.is_processing_event = False
                    self.current_event_id_for_signals = None
                    # Recurse to process next event quickly
                    self._process_next_event_from_queue()
                    return
        except Exception:
            pass

        self.current_event_id_for_signals = event_being_processed.event_id # Store ID for slots to check
        # Track the current event object for timing decisions later
        self.current_event = event_being_processed
        # --- End ECFA Fix ---
        
        logger.info(f"Processing event: {event_being_processed}")
        self.is_processing_event = True # Mark orchestrator as busy with THIS event
        self.is_waiting_for_visual = False
        self.is_waiting_for_tts = False

        engine = self.engine_ref() if self.engine_ref else None
        if not engine:
            logger.error("Engine reference not available in Orchestrator. Cannot process event.")
            self.is_processing_event = False
            self.current_event_id_for_signals = None
            # If an event was popped, try to simulate its completion to avoid stall
            # by directly calling check_event_processing_complete as if it finished.
            self._check_event_processing_complete(event_being_processed.event_id)
            return

        if event_being_processed.type == DisplayEventType.REQUEST_CLOSING_NARRATIVE:
            logger.info("Orchestrator handling REQUEST_CLOSING_NARRATIVE.")
            self._handle_request_closing_narrative(engine, event_being_processed.metadata)
            self.is_processing_event = False 
            self.current_event_id_for_signals = None
            self._process_next_event_from_queue() 
            return

        if event_being_processed.type == DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE:
            logger.debug(f"Applying model resource update: {event_being_processed.metadata}")
            try:
                meta = event_being_processed.metadata or {}
                entity_id = meta.get("entity_id")
                bar_type = str(meta.get("bar_type", "")).lower()
                value = meta.get("final_new_value")
                max_value = meta.get("max_value")
                if entity_id is not None and value is not None:
                    # Clamp value between 0 and max_value if provided
                    try:
                        if max_value is not None:
                            value = max(0, min(int(value), int(max_value)))
                        else:
                            value = max(0, int(value))
                    except Exception:
                        pass
                    cm = self.combat_manager_ref() if self.combat_manager_ref else None
                    if cm:
                        # Update through entity-specific stats manager when available
                        stats_mgr = getattr(cm, '_get_entity_stats_manager', None)
                        entity_stats_mgr = stats_mgr(entity_id) if stats_mgr else None
                        from core.stats.stats_base import DerivedStatType
                        # Map bar_type to stat
                        if bar_type in ("hp", "health"):
                            if entity_stats_mgr:
                                entity_stats_mgr.set_current_stat(DerivedStatType.HEALTH, value)
                            entity = cm.entities.get(entity_id)
                            if entity: entity.set_current_hp(value)
                        elif bar_type in ("stamina",):
                            if entity_stats_mgr:
                                entity_stats_mgr.set_current_stat(DerivedStatType.STAMINA, value)
                            entity = cm.entities.get(entity_id)
                            if entity: entity.set_current_stamina(value)
                        elif bar_type in ("mana", "mp"):
                            if entity_stats_mgr:
                                entity_stats_mgr.set_current_stat(DerivedStatType.MANA, value)
                            entity = cm.entities.get(entity_id)
                            if entity is not None:
                                try:
                                    entity.current_mp = value
                                except Exception:
                                    pass
                        else:
                            logger.warning(f"Unknown bar_type '{bar_type}' in APPLY_ENTITY_RESOURCE_UPDATE")
                    else:
                        logger.error("CombatManager reference missing; cannot apply resource update.")
            except Exception as e:
                logger.error(f"Error applying entity resource update: {e}", exc_info=True)
            # Event-based completion for this non-visual event: keep is_processing_event True so completion advances queue
            logger.debug(f"APPLY_ENTITY_RESOURCE_UPDATE done for {event_being_processed.event_id}; advancing queue")
            self._check_event_processing_complete(event_being_processed.event_id)
            return

        if event_being_processed.type == DisplayEventType.APPLY_ENTITY_STATE_UPDATE:
            logger.debug(f"Applying model state update: {event_being_processed.metadata}")
            try:
                meta = event_being_processed.metadata or {}
                entity_id = meta.get("entity_id")
                cm = self.combat_manager_ref() if self.combat_manager_ref else None
                if cm and entity_id in cm.entities:
                    entity = cm.entities.get(entity_id)
                    if entity is not None:
                        if "is_active_in_combat" in meta:
                            try:
                                entity.is_active_in_combat = bool(meta.get("is_active_in_combat"))
                            except Exception:
                                pass
                else:
                    logger.warning("Cannot apply entity state update; missing CombatManager or entity.")
            except Exception as e:
                logger.error(f"Error applying entity state update: {e}", exc_info=True)
            # Event-based completion for this non-visual event: keep is_processing_event True so completion advances queue
            logger.debug(f"APPLY_ENTITY_STATE_UPDATE done for {event_being_processed.event_id}; advancing queue")
            self._check_event_processing_complete(event_being_processed.event_id)
            return

        # --- Handle special non-visual events ---

        # --- Route event content to UI for visual display ---
        # Assuming UI_BAR_UPDATE and VISUAL_EFFECT also go through orchestrated_event_to_ui
        # and their handlers in MainWindow will call _handle_visual_display_complete appropriately.
        self.is_waiting_for_visual = True
        engine.orchestrated_event_to_ui.emit(event_being_processed)

        # Special case: BUFFER_FLUSH to text displays does not need visual completion waiting
        try:
            if event_being_processed.type in (DisplayEventType.BUFFER_FLUSH, DisplayEventType.COMBAT_LOG_SET_HTML):
                # We consider batch text append immediate for orchestrator purposes
                self.is_waiting_for_visual = False
        except Exception:
            pass

        # No persistence needed here; HTML snapshot approach will be used for rehydration.
        
        # --- Handle TTS ---
        tts_manager = self.tts_manager_ref() if self.tts_manager_ref else None
        if event_being_processed.tts_eligible and tts_manager and tts_manager.is_enabled:
            content_to_speak = ""
            if isinstance(event_being_processed.content, str):
                content_to_speak = event_being_processed.content
            elif isinstance(event_being_processed.content, list) and event_being_processed.type == DisplayEventType.BUFFER_FLUSH:
                content_to_speak = "\n".join(str(item) for item in event_being_processed.content)
            
            if content_to_speak.strip():
                self.is_waiting_for_tts = True
                tts_manager.speak(content_to_speak)
        
        # If neither visual nor TTS is awaited (e.g., event type doesn't require it, or TTS disabled)
        # then call _check_event_processing_complete.
        # This path is tricky because is_waiting_for_visual is set true, expecting a signal.
        # If an event type TRULY has no visual and no TTS, it should bypass setting these flags.
        # For now, assume all emitted events will lead to _handle_visual_display_complete.
        if not self.is_waiting_for_visual and not self.is_waiting_for_tts:
            logger.debug(f"No visual or TTS initially awaited for event {event_being_processed.event_id}. Checking completion.")
            self._check_event_processing_complete(event_being_processed.event_id)

    @Slot()
    def _handle_visual_display_complete(self):
        """Slot called when a UI widget finishes displaying text."""
        # --- ECFA Fix: Check against stored event ID ---
        # This slot might be called for an event that's already "completed" if UI signals are rapid
        # or if a previous event's signal arrives late.
        # We only care if it's for the event we are currently marked as 'processing'.
        if not self.is_processing_event: 
            logger.debug(f"Received visualDisplayComplete but Orchestrator not actively processing an event (or already completed it). Ignoring.")
            return
        # If we want to be super sure, we could pass event_id with the signal, but that makes UI more complex.
        # For now, if is_processing_event is true, assume it's for the event whose ID is in self.current_event_id_for_signals.
        logger.debug(f"Received visualDisplayComplete for current processing cycle (event_id around: {self.current_event_id_for_signals}).")
        # --- End ECFA Fix ---
        
        self.is_waiting_for_visual = False
        self._check_event_processing_complete(self.current_event_id_for_signals)

    @Slot()
    def _handle_tts_playback_complete(self):
        """Slot called when TTS finishes speaking."""
        if not self.is_processing_event:
            logger.debug(f"Received ttsPlaybackComplete but Orchestrator not actively processing an event. Ignoring.")
            return
        logger.debug(f"Received ttsPlaybackComplete for current processing cycle (event_id around: {self.current_event_id_for_signals}).")
        self.is_waiting_for_tts = False
        self._check_event_processing_complete(self.current_event_id_for_signals)

    def _check_event_processing_complete(self, event_id_completed: Optional[str]):
        """
        Checks if all parts of the current event are done (visual, TTS).
        Uses event_id_completed to ensure we are finalizing the correct event.
        """
        # --- ECFA Fix: Only proceed if this completion matches the event being processed ---
        if not self.is_processing_event or self.current_event_id_for_signals != event_id_completed:
            if self.is_processing_event: # Mismatch
                logger.warning(f"_check_event_processing_complete called for event '{event_id_completed}', "
                               f"but currently processing event '{self.current_event_id_for_signals}'. Ignoring this completion call.")
            # Else, already not processing, so this is a late signal for a past event.
            return 
        # --- End ECFA Fix ---

        if not self.is_waiting_for_visual and not self.is_waiting_for_tts:
            logger.info(f"Event processing truly complete for: {self.current_event_id_for_signals}")
            self.is_processing_event = False
            self.current_event_id_for_signals = None # Clear the ID of the event just completed

            # Decide whether to apply an inter-step delay based on event type
            skip_delay = False
            try:
                from core.orchestration.events import DisplayEventType
                if hasattr(self, 'current_event') and self.current_event and \
                   self.current_event.type in (DisplayEventType.UI_BAR_UPDATE_PHASE1, DisplayEventType.UI_BAR_UPDATE_PHASE2,
                                               DisplayEventType.APPLY_ENTITY_RESOURCE_UPDATE, DisplayEventType.APPLY_ENTITY_STATE_UPDATE):
                    skip_delay = True
            except Exception:
                pass

            # Always clear current_event once we've computed skip_delay
            self.dev_last_skip_delay = skip_delay
            self.current_event = None

            # Developer manual step gating
            if getattr(self, 'dev_manual_step_mode', False):
                logger.debug("Developer Step Mode: waiting for manual release before continuing.")
                self.dev_waiting_for_next_click = True
                try:
                    self.dev_waiting_state_changed.emit(True)
                except Exception:
                    pass
                return

            if skip_delay:
                logger.debug("Skipping inter-step delay after UI_BAR_UPDATE event to keep UI updates in sync.")
                self._process_next_event_from_queue()
            else:
                self.inter_step_delay_timer.start(self.config_delay_ms)
                logger.debug(f"Started inter-step delay: {self.config_delay_ms}ms after event {event_id_completed}")

    @Slot()
    def _on_inter_step_delay_timeout(self):
        logger.debug("Inter-step delay timeout.")
        
        # If we were in dev manual step mode and waiting, clear waiting state upon timeout
        if getattr(self, 'dev_manual_step_mode', False) and getattr(self, 'dev_waiting_for_next_click', False):
            self.dev_waiting_for_next_click = False
            try:
                self.dev_waiting_state_changed.emit(False)
            except Exception:
                pass
        
        engine = self.engine_ref() if self.engine_ref else None
        if engine and hasattr(engine, 'main_window_ref'): # Assuming MainWindow registers itself with engine
            main_window = engine.main_window_ref()
            if main_window and hasattr(main_window, '_update_ui'):
                 logger.debug("Orchestrator delay timeout: Triggering MainWindow._update_ui()")
                 QTimer.singleShot(0, main_window._update_ui) # Schedule UI update
        
        # Root-cause fix: only resume CombatManager when queue is empty; otherwise continue processing next event.
        if not self.is_processing_event and self.event_queue:
            logger.debug("Processing next event from queue after delay.")
            self._process_next_event_from_queue()
        elif not self.is_processing_event and not self.event_queue:
            logger.debug("Queue empty after delay. Resuming CombatManager for next step.")
            self._signal_combat_manager_resume()
            # If combat just ended successfully, trigger engine's auto-finalization to switch to narrative mode.
            try:
                engine = self.engine_ref() if self.engine_ref else None
                if engine:
                    from core.interaction.enums import InteractionMode
                    from core.combat.enums import CombatStep, CombatState
                    state_manager = getattr(engine, '_state_manager', None)
                    game_state = state_manager.current_state if state_manager else None
                    if game_state and game_state.current_mode == InteractionMode.COMBAT and getattr(game_state, 'combat_manager', None):
                        cm = game_state.combat_manager
                        if getattr(cm, 'current_step', None) == CombatStep.COMBAT_ENDED and getattr(cm, 'state', None) != CombatState.PLAYER_DEFEAT:
                            QTimer.singleShot(0, engine._finalize_combat_transition_if_needed)
            except Exception as e:
                logger.error(f"Error scheduling automatic post-combat finalization: {e}", exc_info=True)


    def _signal_combat_manager_resume(self) -> bool:
        """Signals CM to resume. Returns True if CM was resumed and is NOT now waiting."""
        combat_manager = self.combat_manager_ref() if self.combat_manager_ref else None
        engine = self.engine_ref() if self.engine_ref else None
        resumed_and_not_waiting_again = False

        if combat_manager and getattr(combat_manager, 'waiting_for_display_completion', False):
            # Do not resume if combat is no longer in progress
            try:
                from core.combat.enums import CombatState
                cm_state = getattr(combat_manager, 'state', None)
                logger.info(f"CombatManager resume check. State: {cm_state.name if cm_state else 'Not available'}")
                if cm_state is not None and cm_state != CombatState.IN_PROGRESS:
                    logger.info(f"CombatManager state is {cm_state.name}, not IN_PROGRESS. Clearing stale events and nudging CM for final messages.")
                    # 1. Clear any stale events from the normal combat flow.
                    self.clear_queue_and_reset_flags()
                    # 2. Nudge the CombatManager to run its final step (_step_ending_combat).
                    #    This will add the correct final messages (loot, conclusion) to the now-clean queue.
                    if engine:
                        QTimer.singleShot(0, lambda: combat_manager.process_combat_step(engine))
                    # 3. Return False because we are not resuming the normal combat loop.
                    return False
            except Exception:
                pass
            logger.info("Signaling CombatManager to resume processing.")
            combat_manager.waiting_for_display_completion = False
            if engine:
                # Use QTimer to allow event loop to process signals first.
                QTimer.singleShot(0, lambda: combat_manager.process_combat_step(engine))
                resumed_and_not_waiting_again = not getattr(combat_manager, 'waiting_for_display_completion', True)
            else:
                logger.error("Cannot resume CombatManager: Engine reference missing.")
        else:
            logger.debug("CombatManager not waiting or not available. No resume signal sent.")
        return resumed_and_not_waiting_again
    
    def clear_queue_and_reset_flags(self):
        """Resets the orchestrator state, typically when combat ends or is forcefully stopped."""
        logger.info("Clearing event queue and resetting orchestrator flags.")
        self.event_queue.clear()
        if self.inter_step_delay_timer.isActive():
            self.inter_step_delay_timer.stop()
        self.is_processing_event = False
        self.is_waiting_for_visual = False
        self.is_waiting_for_tts = False
        self.current_event = None
        # Do not clear combat_manager_ref here, it's managed by set_combat_manager

    def shutdown(self):
        """Called when the engine is shutting down to stop timers."""
        logger.info("Shutting down CombatOutputOrchestrator.")
        self.clear_queue_and_reset_flags()
        self.dev_manual_step_mode = False
        self.dev_waiting_for_next_click = False
        if self.inter_step_delay_timer:
            self.inter_step_delay_timer.timeout.disconnect(self._on_inter_step_delay_timeout)

    def _handle_request_closing_narrative(self, engine: 'GameEngine', metadata: Optional[Dict]):
        """Handles the event to request and queue the closing combat narrative."""
        if not metadata or "outcome" not in metadata:
            logger.error("REQUEST_CLOSING_NARRATIVE missing outcome metadata.")
            # To prevent stalling, we should still allow engine to proceed
            if getattr(engine, '_waiting_for_closing_narrative_display', False):
                 engine._waiting_for_closing_narrative_display = False
            return

        outcome = metadata["outcome"]
        closing_prompt = f"The combat has just ended. The outcome was: {outcome}. Provide a brief, immersive closing narrative (1-2 sentences) describing the aftermath for the player."
        
        llm_narrative = "[Default Closing: The dust settles on the battlefield.]" # Fallback
        if engine._use_llm:
            try:
                logger.info(f"Orchestrator requesting closing combat narrative with prompt: {closing_prompt}")
                from core.game_flow.interaction_core import _build_interaction_context, _get_agent_response
                from core.interaction.enums import InteractionMode
                gs = engine._state_manager.current_state if hasattr(engine, '_state_manager') and engine._state_manager else None
                context = _build_interaction_context(gs, InteractionMode.COMBAT, actor_id=getattr(getattr(gs, 'player', None), 'id', None)) if gs else {}
                agent_output = _get_agent_response(engine, gs, context, closing_prompt, InteractionMode.COMBAT) or {}
                narrative = agent_output.get('narrative')
                if narrative:
                    llm_narrative = narrative
                    logger.info(f"Orchestrator received closing narrative: {llm_narrative[:70]}...")
                else:
                    logger.warning("Failed to generate closing combat narrative from LLM (no narrative).")
            except Exception as e:
                logger.error(f"Error generating closing combat narrative via structured path: {e}", exc_info=True)
        else:
            logger.info("LLM disabled, using default closing narrative.")

        closing_narrative_event = DisplayEvent(
            type=DisplayEventType.NARRATIVE_GENERAL,
            content=llm_narrative,
            role="gm",
            target_display=DisplayTarget.MAIN_GAME_OUTPUT,
            gradual_visual_display=True,
            tts_eligible=True,
            source_step="CLOSING_COMBAT_NARRATIVE"
        )
        # Add to the front of the queue to be processed next
        self.event_queue.appendleft(closing_narrative_event)
        logger.debug(f"Queued closing narrative event: {closing_narrative_event}")

    @Slot(bool)
    def toggle_dev_step_mode(self, enabled: bool) -> None:
        """Enable/disable developer manual step mode."""
        prev = getattr(self, 'dev_manual_step_mode', False)
        self.dev_manual_step_mode = bool(enabled)
        logger.info(f"Developer Step Mode set to {self.dev_manual_step_mode}")
        if prev and not self.dev_manual_step_mode:
            # If we were waiting and dev mode is turned off, release automatically
            if getattr(self, 'dev_waiting_for_next_click', False):
                logger.debug("Developer Step Mode disabled during waiting; auto-releasing next step.")
                self.dev_waiting_for_next_click = False
                try:
                    self.dev_waiting_state_changed.emit(False)
                except Exception:
                    pass
                # Follow normal path depending on last skip decision
                if getattr(self, 'dev_last_skip_delay', False):
                    self._process_next_event_from_queue()
                else:
                    self.inter_step_delay_timer.start(self.config_delay_ms)

    @Slot()
    def dev_release_next_step(self) -> None:
        """When in developer manual step mode, release the next event step."""
        if not getattr(self, 'dev_manual_step_mode', False):
            logger.debug("dev_release_next_step called but Developer Step Mode is OFF. Ignoring.")
            return
        if not getattr(self, 'dev_waiting_for_next_click', False):
            logger.debug("dev_release_next_step called but orchestrator is not waiting.")
            return
        logger.info("Developer Step Mode: releasing next step.")
        self.dev_waiting_for_next_click = False
        try:
            self.dev_waiting_state_changed.emit(False)
        except Exception:
            pass
        # Continue according to the last skip-delay decision
        if getattr(self, 'dev_last_skip_delay', False):
            self._process_next_event_from_queue()
        else:
            self.inter_step_delay_timer.start(self.config_delay_ms)

