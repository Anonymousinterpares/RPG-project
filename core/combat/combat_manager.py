import random
import logging
import uuid
from typing import Dict, List, Tuple, Any, Optional, Set, Union, TYPE_CHECKING
from PySide6.QtCore import QTimer
from core.agents.base_agent import AgentContext
from core.base.state.state_manager import get_state_manager
from core.interaction.context_builder import ContextBuilder
from core.interaction.enums import InteractionMode
from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
from core.stats.combat_effects import StatusEffect, StatusEffectType
from core.stats.derived_stats import get_modifier_from_stat
from core.stats.modifier import ModifierSource
from core.stats.stats_base import StatType, DerivedStatType
from core.utils.dice import roll_dice_notation, check_success, roll_critical
from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_action import AttackAction, CombatAction, ActionType, DefendAction, FleeAction, SpellAction
from core.stats.stats_manager import StatsManager, get_stats_manager 
from core.inventory import get_inventory_manager
from .enums import CombatState, CombatStep
from .action_handlers import (
    _handle_attack_action,
    _handle_spell_action,
    _handle_defend_action,
    _handle_item_action,
    _handle_flee_action_mechanics
)

if TYPE_CHECKING:
    from core.base.engine import GameEngine # For process_combat_step

logger = logging.getLogger(__name__)


class CombatManager:
    def __init__(self):
        """Initialize a new combat manager."""
        self.id = str(uuid.uuid4())
        self.entities: Dict[str, CombatEntity] = {}
        self.turn_order: List[str] = []
        self.current_turn_index: int = 0
        self.round_number: int = 0
        self.state: CombatState = CombatState.NOT_STARTED 
        self.current_step: CombatStep = CombatStep.NOT_STARTED 
        self.combat_log: List[str] = [] # Raw chronological log for debugging/internal history
        self.display_log_html: str = "" # HTML snapshot of Combat Log for instant rehydrate
        self.last_action_results: Dict[str, Any] = {} 

        self._player_entity_id: Optional[str] = None
        self._enemy_entity_ids: List[str] = []
        self._surprise_attack: bool = False
        self._is_surprise_round: bool = False # Retained for surprise round logic differentiation
        self._initiating_intent: Optional[str] = None
        self._pending_action: Optional[CombatAction] = None
        self._last_action_result_detail: Optional[Dict] = None 
        self._current_intent: Optional[str] = None
        self._active_entity_id: Optional[str] = None 
        self._surprise_round_entities: List[str] = [] # Retained for surprise round actor selection

        # --- ECFA Change: Flag for orchestrator control ---
        self.waiting_for_display_completion: bool = False
        # --- End ECFA Change ---

    def start_combat(self, player_entity: CombatEntity, enemy_entities: List[CombatEntity]) -> None:
        self.entities = {}
        self.turn_order = []
        self.current_turn_index = 0
        self.round_number = 0
        self.state = CombatState.NOT_STARTED
        self.combat_log = []
        self.last_action_results = {}
        self._surprise_round_entities = []
        self._is_surprise_round = False

        if not hasattr(player_entity, 'combat_name') or not player_entity.combat_name:
            logger.error(f"Player entity missing combat_name: {player_entity.name}")
            player_entity.combat_name = player_entity.name
        self.entities[player_entity.id] = player_entity

        for enemy in enemy_entities:
            if not hasattr(enemy, 'combat_name') or not enemy.combat_name:
                logger.error(f"Enemy entity missing combat_name: {enemy.name}")
                enemy.combat_name = enemy.name
            self.entities[enemy.id] = enemy
            logger.info(f"Added entity to combat: {enemy.name} (Combat Name: {enemy.combat_name}, ID: {enemy.id})")

        self._determine_initiative()

        self.state = CombatState.IN_PROGRESS
        self.round_number = 1

        enemy_combat_names = ", ".join(e.combat_name for e in enemy_entities)
        self._add_to_log(f"Combat started! {player_entity.combat_name} vs {enemy_combat_names}")

        surprised_entity_ids = [eid for eid, entity in self.entities.items() if entity.has_status_effect("Surprised")]

        if surprised_entity_ids:
            self._add_to_log("Surprise Round!")
            logger.info(f"Surprise round initiated. Surprised entities: {surprised_entity_ids}")

            non_surprised_entity_ids = [eid for eid in self.turn_order if eid not in surprised_entity_ids]

            if non_surprised_entity_ids:
                surprise_turn_order = [eid for eid in self.turn_order if eid in non_surprised_entity_ids]
                self._add_to_log("Entities acting in the surprise round:")
                self._add_to_log(", ".join(self.entities[eid].combat_name for eid in surprise_turn_order))
                self._is_surprise_round = True
                self._surprise_round_entities = surprise_turn_order
                self.current_turn_index = 0
                logger.info(f"Surprise round activated with {len(surprise_turn_order)} entities: {surprise_turn_order}")
                self._add_to_log("Processing surprise round actions...")
                logger.debug("Surprise round setup complete. Main loop will process turns.")
            else:
                self._add_to_log("No entities are able to act in the surprise round.")
                self._end_surprise_round()
        else:
            self.round_number = 1
            self.current_turn_index = 0
            self._add_to_log(f"Round {self.round_number} begins!")
            self._log_turn_order()

    def process_combat_step(self, engine): # Engine is received here
        """Processes the current step and triggers the next one if appropriate."""
        # Guard: ignore callbacks on an inactive/old manager (e.g., after New Game)
        try:
            state_manager = getattr(engine, '_state_manager', None)
            current_state = state_manager.current_state if state_manager else None
            active_cm = getattr(current_state, 'combat_manager', None) if current_state else None
            if active_cm is not self:
                logger.info("CombatManager.process_combat_step invoked on inactive manager. Ignoring callback.")
                return
        except Exception:
            # If we cannot verify, proceed cautiously
            pass
        
        max_steps = 20 
        steps_processed = 0
        while steps_processed < max_steps:
            steps_processed += 1
            current_step_before_processing = self.current_step

            if self.state != CombatState.IN_PROGRESS and self.current_step not in [CombatStep.ENDING_COMBAT, CombatStep.COMBAT_ENDED]:
                logger.warning(f"Combat state changed to {self.state.name} during step processing. Stopping.")
                if self.current_step != CombatStep.ENDING_COMBAT:
                    self.current_step = CombatStep.ENDING_COMBAT 
                if self.current_step == CombatStep.ENDING_COMBAT: self._step_ending_combat(engine) # Pass engine
                break 

            if self.current_step in [CombatStep.AWAITING_PLAYER_INPUT, CombatStep.COMBAT_ENDED, CombatStep.NOT_STARTED, CombatStep.AWAITING_TRANSITION_DATA]:
                logger.debug(f"Stopping step processing loop at step: {self.current_step.name}")
                # If orchestrator is idle and CM was waiting, it should have been resumed by orchestrator.
                # If CM is now at AWAITING_PLAYER_INPUT, it's genuinely waiting.
                break 

            # --- ECFA Change: Ensure orchestrator is set on engine for step handlers ---
            if not hasattr(engine, '_combat_orchestrator'):
                logger.critical("CRITICAL: GameEngine instance in CombatManager does not have _combat_orchestrator. Aborting combat.")
                self.end_combat("Internal Engine Error: Orchestrator missing.")
                self.current_step = CombatStep.COMBAT_ENDED
                break
            # --- End ECFA Change ---

            try:
                logger.debug(f"Processing Combat Step: {self.current_step.name} (Loop Iteration: {steps_processed})")

                step_handlers = {
                    CombatStep.STARTING_COMBAT: self._step_starting_combat,
                    CombatStep.HANDLING_SURPRISE_CHECK: self._step_handling_surprise_check,
                    CombatStep.PERFORMING_SURPRISE_ATTACK: self._step_performing_surprise_attack,
                    CombatStep.NARRATING_SURPRISE_OUTCOME: self._step_narrating_surprise_outcome,
                    CombatStep.ENDING_SURPRISE_ROUND: self._step_ending_surprise_round,
                    CombatStep.ROLLING_INITIATIVE: self._step_rolling_initiative,
                    CombatStep.STARTING_ROUND: self._step_starting_round,
                    CombatStep.PROCESSING_PLAYER_ACTION: self._step_processing_player_action,
                    CombatStep.AWAITING_NPC_INTENT: self._step_awaiting_npc_intent,
                    CombatStep.PROCESSING_NPC_ACTION: self._step_processing_npc_action,
                    CombatStep.RESOLVING_ACTION_MECHANICS: self._step_resolving_action_mechanics,
                    CombatStep.NARRATING_ACTION_OUTCOME: self._step_narrating_action_outcome,
                    CombatStep.APPLYING_STATUS_EFFECTS: self._step_applying_status_effects,
                    CombatStep.ADVANCING_TURN: self._step_advancing_turn,
                    CombatStep.ENDING_COMBAT: self._step_ending_combat,
                }

                handler = step_handlers.get(self.current_step)

                if handler:
                    # --- ECFA Change: Pass engine to handlers that need it ---
                    # Most handlers will now need `engine` to access `_combat_orchestrator`
                    # We can inspect handler signature or just pass it if common.
                    # For simplicity, let's update handlers to accept `engine` if they interact with orchestrator.
                    
                    # Determine if handler needs engine (could be more sophisticated)
                    # For now, assume all step handlers might need it or are refactored to accept it.
                    handler(engine) # Pass engine to all step handlers
                    # --- End ECFA Change ---

                    # If the handler set waiting_for_display_completion, break the loop
                    if self.waiting_for_display_completion:
                        logger.debug(f"Step {current_step_before_processing.name} set waiting_for_display_completion. Pausing CM.")
                        break 
                elif self.current_step not in [CombatStep.NOT_STARTED, CombatStep.AWAITING_TRANSITION_DATA, CombatStep.COMBAT_ENDED, CombatStep.AWAITING_PLAYER_INPUT]:
                    logger.warning(f"No handler defined for combat step: {self.current_step.name}")
                    break

                if self.current_step == current_step_before_processing and not self.waiting_for_display_completion:
                    logger.error(f"Combat step {self.current_step.name} did not transition state or set wait flag. Breaking loop.")
                    # This is a safeguard. If a step runs, doesn't queue events (so waiting_for_display is false),
                    # and doesn't change current_step, it's an infinite loop.
                    break

            except Exception as e:
                logger.exception(f"Error processing combat step {self.current_step.name}: {e}")
                # Try to queue an error message via orchestrator if available
                if hasattr(engine, '_combat_orchestrator'):
                    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
                    err_event = DisplayEvent(
                        type=DisplayEventType.SYSTEM_MESSAGE,
                        content=f"System Error during {self.current_step.name}: {e}",
                        target_display=DisplayTarget.COMBAT_LOG
                    )
                    engine._combat_orchestrator.add_event_to_queue(err_event)
                self.end_combat(f"Error during step {self.current_step.name}: {e}")
                self.current_step = CombatStep.COMBAT_ENDED # Ensure it stops
                break 
        else: 
            if steps_processed >= max_steps:
                logger.error(f"Exceeded maximum combat steps ({max_steps}). Forcing combat end.")
                self.end_combat("Error: Combat processing limit exceeded.")
                self.current_step = CombatStep.COMBAT_ENDED

    def _step_starting_combat(self, engine):
        """Handles the initial combat announcement AND THEN decides the next step."""
        if not hasattr(engine, '_combat_orchestrator'): 
            logger.error("CombatOutputOrchestrator not found on engine in _step_starting_combat.")
            self.end_combat("Internal error: Orchestrator unavailable.")
            self.current_step = CombatStep.COMBAT_ENDED
            return

        # This method will now execute its full logic in one go.
        # It queues its message, then determines the next step, then sets the wait flag.
        
        player = self.entities.get(self._player_entity_id)
        enemies = [self.entities[eid] for eid in self._enemy_entity_ids if eid in self.entities]
        enemy_names_display = ', '.join(e.combat_name for e in enemies)
        player_name_display = player.combat_name if player else "Player"

        start_msg = f"Combat started! {player_name_display} vs {enemy_names_display}"
        self._add_to_log(start_msg) 

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
        event = DisplayEvent(
            type=DisplayEventType.SYSTEM_MESSAGE,
            content=start_msg,
            target_display=DisplayTarget.COMBAT_LOG,
            gradual_visual_display=False, tts_eligible=False,
            source_step=self.current_step.name # Current step is STARTING_COMBAT
        )
        engine._combat_orchestrator.add_event_to_queue(event)
        
        # Now, determine the *actual next game step*
        if self._surprise_attack:
            logger.info("Surprise attack indicated. Next actual game step: HANDLING_SURPRISE_CHECK.")
            self.current_step = CombatStep.HANDLING_SURPRISE_CHECK
        else:
            logger.info("No surprise attack. Next actual game step: ROLLING_INITIATIVE.")
            self.current_step = CombatStep.ROLLING_INITIATIVE
            
        # Pause for the "Combat Started!" message to display.
        # When process_combat_step resumes, it will pick up the new current_step.
        self.waiting_for_display_completion = True

    def _step_handling_surprise_check(self, engine):
        """Determines surprise effects, queues messages, sets up surprise action, sets next step, then pauses."""
        if not hasattr(engine, '_combat_orchestrator') or not hasattr(engine, '_combat_narrator_agent'):
            logger.error("Orchestrator or CombatNarratorAgent not found on engine in _step_handling_surprise_check.")
            self.end_combat("Internal error: Core components unavailable for surprise check.")
            self.current_step = CombatStep.COMBAT_ENDED
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        from core.interaction.context_builder import ContextBuilder
        from core.agents.base_agent import AgentContext

        attacker = self.entities.get(self._player_entity_id)
        if not attacker:
            logger.error("Cannot handle surprise: Attacker (player) not found.")
            self.current_step = CombatStep.ROLLING_INITIATIVE 
            self.waiting_for_display_completion = False 
            return

        targets = [self.entities.get(eid) for eid in self._enemy_entity_ids if self.entities.get(eid) and self.entities.get(eid).is_alive()]

        if not targets:
            logger.info("No valid enemy targets for surprise attack. Ending surprise sequence.")
            self.current_step = CombatStep.ENDING_SURPRISE_ROUND
            self.waiting_for_display_completion = False
            if not engine._combat_orchestrator.is_processing_event and not engine._combat_orchestrator.event_queue:
                QTimer.singleShot(0, lambda: self.process_combat_step(engine))
            return

        surprised_target_names = []
        for target_entity in targets:
            if not target_entity: continue
            target_stats_manager = self._get_entity_stats_manager(target_entity.id)
            if target_stats_manager:
                surprise_effect = StatusEffect(name="Surprised", description="Caught off guard", effect_type=StatusEffectType.DEBUFF, duration=1)
                target_stats_manager.add_status_effect(surprise_effect)
                target_entity.add_status_effect("Surprised", duration=1) 
                surprised_target_names.append(target_entity.combat_name)

        if not self._is_surprise_round: self._is_surprise_round = True # Should be true if surprise_attack was true
        # _surprise_round_entities for CM's internal logic (who *can* act)
        # This should be only non-surprised entities IF enemies attack first by surprise.
        # For player surprise, only player acts.
        self._surprise_round_entities = [attacker.id] # Player is the one acting in surprise

        event_round_msg = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content="Round 1 (Surprise Attack!)", target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name)
        engine._combat_orchestrator.add_event_to_queue(event_round_msg)

        if surprised_target_names:
            event_surprised_targets = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=f"Targets Surprised: {', '.join(surprised_target_names)}", target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name)
            engine._combat_orchestrator.add_event_to_queue(event_surprised_targets)
        else:
            event_no_surprise = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content="No targets were successfully surprised.", target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name)
            engine._combat_orchestrator.add_event_to_queue(event_no_surprise)
        
        self._active_entity_id = attacker.id 
        self._pending_action = None 

        # Queue TURN_ORDER_UPDATE for surprise round. This will be handled by _set_next_actor_step
        # after the initial messages are processed.
        # _set_next_actor_step is called via perform_action or advancing turn.
        # For surprise, we will call _set_next_actor_step(attacker.id) before PROCESSING_PLAYER_ACTION effectively.

        if "attack" in self._initiating_intent.lower() and targets: 
            target_to_attack = targets[0] 
            self._pending_action = AttackAction(
                performer_id=attacker.id, target_id=target_to_attack.id,
                weapon_name="surprise attack", dice_notation="1d6" 
            )
            self._add_to_log(f"[INTERNAL] Pending surprise action: {self._pending_action.name} on {target_to_attack.combat_name}")

            game_state = engine._state_manager.current_state
            if not game_state:
                logger.error("GameState not found for surprise narrative.")
                self.current_step = CombatStep.ENDING_SURPRISE_ROUND 
                self.waiting_for_display_completion = True 
                return

            context_builder = ContextBuilder() 
            agent_call_context_dict = context_builder.build_context(game_state, InteractionMode.COMBAT, actor_id=attacker.id)
            narrator_input_for_surprise = (
                f"[System Event: Surprise Attack Attempt]\nActor: '{attacker.combat_name}'\n"
                f"Target: '{target_to_attack.combat_name}' (Status: Surprised)\nOriginal Intent: '{self._initiating_intent}'\n"
                f"Action: Attempting a surprise attack.\nDescribe the attacker's initial move and the target's "
                f"unawareness leading up to the strike. Focus on the *attempt*, not the outcome."
            )
            agent_context_for_narrator = AgentContext(
                game_state=agent_call_context_dict, player_state=agent_call_context_dict.get('player',{}), 
                world_state=agent_call_context_dict.get('world',{}), player_input=narrator_input_for_surprise,
                conversation_history=game_state.conversation_history if game_state else [], additional_context=agent_call_context_dict
            )
            attempt_narrative = f"{attacker.combat_name} launches a swift surprise attack on {target_to_attack.combat_name}!" 
            try:
                narrator_output = engine._combat_narrator_agent.process(agent_context_for_narrator)
                if narrator_output and narrator_output.get("narrative"): attempt_narrative = narrator_output["narrative"]
            except Exception as e: logger.error(f"Error getting surprise attempt narrative: {e}", exc_info=True)
            
            event_attempt_narrative = DisplayEvent(type=DisplayEventType.NARRATIVE_ATTEMPT, content=attempt_narrative, role="gm", tts_eligible=True, gradual_visual_display=True, target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name)
            engine._combat_orchestrator.add_event_to_queue(event_attempt_narrative)
            # This will call _set_next_actor_step which queues the TURN_ORDER_UPDATE for surprise
            self._set_next_actor_step(attacker.id) # Ensure correct step (PROCESSING_PLAYER_ACTION for surprise)
            self.current_step = CombatStep.PERFORMING_SURPRISE_ATTACK # Correct target step for surprise action
        else: 
            no_action_narrative = f"{attacker.combat_name} looks for an opening, but the moment for a surprise attack passes."
            event_no_action = DisplayEvent(type=DisplayEventType.NARRATIVE_GENERAL, content=no_action_narrative, role="gm", tts_eligible=True, gradual_visual_display=True, target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name)
            engine._combat_orchestrator.add_event_to_queue(event_no_action)
            self._pending_action = None 
            self.current_step = CombatStep.ENDING_SURPRISE_ROUND
            
        self.waiting_for_display_completion = True

    def _step_performing_surprise_attack(self, engine): # Added engine parameter
        """
        Initiates the processing of the pending surprise attack action by calling self.perform_action.
        The perform_action method (and its called handlers) will queue all necessary 
        DisplayEvents for rolls, UI updates, and system messages.
        """
        if not hasattr(engine, '_combat_orchestrator'):
            logger.error("Orchestrator not found on engine in _step_performing_surprise_attack.")
            self.current_step = CombatStep.ENDING_SURPRISE_ROUND
            self.waiting_for_display_completion = False 
            # QTimer.singleShot(0, lambda: self.process_combat_step(engine)) # No need if loop continues
            return

        if not self._pending_action:
            logger.error("No pending action found for surprise attack step.")
            self.current_step = CombatStep.ENDING_SURPRISE_ROUND
            self.waiting_for_display_completion = False 
            # QTimer.singleShot(0, lambda: self.process_combat_step(engine))
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget # Local import

        action_to_process = self._pending_action
        # self._pending_action = None # Clear this LATER, after perform_action and narration

        logger.info(f"Initiating surprise action mechanics for: {action_to_process.name}")

        # Call perform_action. It will handle all sub-steps of mechanics execution
        # and queueing display events. _last_action_result_detail will be set within perform_action.
        action_execution_summary = self.perform_action(action_to_process, engine)

        # Check if perform_action itself failed catastrophically or didn't queue anything
        # unexpectedly (though it should always queue something, even a failure message).
        if not action_execution_summary.get("queued_events", False) and not action_execution_summary.get("success", False):
            logger.warning(f"perform_action for surprise attack {action_to_process.name} did not queue events and reported failure. "
                           f"Message: {action_execution_summary.get('message')}")
            # Ensure a generic failure message is shown if perform_action didn't.
            # This is a fallback.
            if not engine._combat_orchestrator.event_queue: # Check if queue is truly empty
                fail_msg = self._last_action_result_detail.get("message") if self._last_action_result_detail else f"Surprise attack {action_to_process.name} by {self.entities[action_to_process.performer_id].combat_name} could not be resolved."
                event_action_fail = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=fail_msg, target_display=DisplayTarget.COMBAT_LOG)
                engine._combat_orchestrator.add_event_to_queue(event_action_fail)
        
        # The actual outcome (hit/miss/damage) is in self._last_action_result_detail,
        # which was updated by perform_action (via its call to the specific action handler).
        
        # Regardless of the mechanical success/failure, we move to narrate the outcome.
        # The NARRATING step will use self._last_action_result_detail.
        self.current_step = CombatStep.NARRATING_SURPRISE_OUTCOME
        
        # We must pause here to let the orchestrator display all events queued by perform_action.
        self.waiting_for_display_completion = True

    def _step_narrating_surprise_outcome(self, engine):
        """Generates and outputs the narrative description of the surprise attack's outcome, then sets next step."""
        if not hasattr(engine, '_combat_orchestrator') or not hasattr(engine, '_combat_narrator_agent'):
            logger.error("Orchestrator or CombatNarratorAgent not found in _step_narrating_surprise_outcome.")
            self.current_step = CombatStep.ENDING_SURPRISE_ROUND
            self.waiting_for_display_completion = False
            return

        if not self._last_action_result_detail:
            logger.warning("No action result found to narrate surprise outcome. Skipping narration.")
            self.current_step = CombatStep.ENDING_SURPRISE_ROUND
            self.waiting_for_display_completion = False # No event queued for this path
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        logger.info("Generating narrative for surprise attack outcome.")

        outcome_narrative = None
        # ... (logic to get outcome_narrative from LLM or placeholder, as before) ...
        agent_failed = False
        try:
            outcome_narrative = engine._combat_narrator_agent.narrate_outcome(self._last_action_result_detail, self)
            if not outcome_narrative: agent_failed = True
        except Exception as e: logger.error(f"Error calling narrate_outcome for surprise: {e}", exc_info=True); agent_failed = True
        if agent_failed:
            result = self._last_action_result_detail
            performer_name = result.get("performer_name", "Attacker")
            target_name = result.get("target_name", "Target")
            if result.get("success"):
                damage = result.get("damage", 0)
                outcome_narrative = f"The surprise attack by {performer_name} connects against {target_name}, dealing {damage:.0f} damage."
                if result.get("target_defeated"): outcome_narrative += f" {target_name} is defeated!"
            else: outcome_narrative = f"Despite the surprise, {performer_name}'s attack on {target_name} misses!"
        # --- End outcome_narrative generation ---

        if outcome_narrative:
            event_outcome_narrative = DisplayEvent(
                type=DisplayEventType.NARRATIVE_IMPACT, content=outcome_narrative,
                role="gm", tts_eligible=True, gradual_visual_display=True,
                target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name
            )
            engine._combat_orchestrator.add_event_to_queue(event_outcome_narrative)
            self.waiting_for_display_completion = True
        else: # Should not happen if placeholder is good
            self.waiting_for_display_completion = False

        self._last_action_result_detail = None # Clear after use
        self.current_step = CombatStep.ENDING_SURPRISE_ROUND # Always go to this step after narration (or lack thereof)

    def _step_ending_surprise_round(self, engine):
        """Cleans up surprise status, queues message, sets next step to ROLLING_INITIATIVE, then pauses."""
        if not hasattr(engine, '_combat_orchestrator'):
            logger.error("Orchestrator not found on engine in _step_ending_surprise_round.")
            self.current_step = CombatStep.ROLLING_INITIATIVE 
            self.waiting_for_display_completion = False
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
        
        self._add_to_log("Surprise round ends.") 
        event_surprise_end = DisplayEvent(
            type=DisplayEventType.SYSTEM_MESSAGE, content="Surprise round ends.",
            target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name
        )
        engine._combat_orchestrator.add_event_to_queue(event_surprise_end)

        for entity_id in list(self.entities.keys()): 
            entity = self.entities.get(entity_id)
            if entity and entity.has_status_effect("Surprised"):
                stats_manager = self._get_entity_stats_manager(entity_id)
                if stats_manager:
                    stats_manager.status_effect_manager.remove_effects_by_name("Surprised")
                entity.remove_status_effect("Surprised") 
                logger.debug(f"Removed Surprised status from {entity.combat_name}")

        self._surprise_attack = False 
        self._initiating_intent = None 
        self._is_surprise_round = False # Explicitly set to False
        
        self.current_step = CombatStep.ROLLING_INITIATIVE 
        self.waiting_for_display_completion = True 

    def _step_rolling_initiative(self, engine):
        """Rolls initiative, queues messages, sets next step to STARTING_ROUND, then pauses if messages were queued."""
        if not hasattr(engine, '_combat_orchestrator'):
            logger.error("Orchestrator not found on engine in _step_rolling_initiative.")
            self.end_combat("Internal error: Orchestrator unavailable for initiative.")
            self.current_step = CombatStep.COMBAT_ENDED
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget

        events_queued_this_pass = False
        if not self.turn_order: # Only roll if not already determined
            initiative_values = [] 
            for entity_id, entity in self.entities.items():
                if not entity.is_alive() or not getattr(entity, 'is_active_in_combat', True): continue
                base_initiative = entity.get_stat(DerivedStatType.INITIATIVE)
                roll = random.randint(1, 6)
                total_initiative = base_initiative + roll
                entity.initiative = total_initiative
                initiative_values.append((entity_id, total_initiative))
                roll_detail_msg = f"{entity.combat_name} rolls initiative: {total_initiative:.0f} (Base:{base_initiative:.0f} + Roll:{roll})"
                self._add_to_log(roll_detail_msg) 
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=roll_detail_msg, target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name))
                events_queued_this_pass = True

            initiative_values.sort(key=lambda x: x[1], reverse=True)
            self.turn_order = [entity_id for entity_id, _ in initiative_values]
            self.current_turn_index = 0 # Reset for new turn order
            
            # Note: Turn order string is queued by _step_starting_round now for better flow.
        else:
            logger.debug("Initiative already determined.")

        self.round_number = 0 # Initialize for the first regular round
        self.current_turn_index = -1 # Will be set by _step_starting_round
        self.current_step = CombatStep.STARTING_ROUND
        
        if events_queued_this_pass:
            self.waiting_for_display_completion = True
        else:
            self.waiting_for_display_completion = False # No new messages, proceed

    def _step_starting_round(self, engine):
        """Increments round, queues messages, sets first actor step, then pauses."""
        if not hasattr(engine, '_combat_orchestrator'):
            logger.error("Orchestrator not found on engine in _step_starting_round.")
            self.end_combat("Internal error: Orchestrator unavailable for round start.")
            self.current_step = CombatStep.COMBAT_ENDED
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        
        self.round_number += 1
        round_start_msg = f"Round {self.round_number} begins!"
        self._add_to_log(round_start_msg) 
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=round_start_msg, target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name))

        if not self.turn_order:
            logger.error("Cannot start round: Turn order is empty. This should have been set by _step_rolling_initiative.")
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content="System Error: Turn order missing for round start.", target_display=DisplayTarget.COMBAT_LOG))
            self.end_combat("Error: Turn order missing.")
            self.current_step = CombatStep.ENDING_COMBAT
            self.waiting_for_display_completion = True 
            return
            
        turn_order_log_msg = "Turn order: " + ", ".join(self.entities[eid].combat_name for eid in self.turn_order if eid in self.entities and self.entities[eid].is_alive() and getattr(self.entities[eid], 'is_active_in_combat', True))
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=turn_order_log_msg, target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name + "_order_display"))
            
        first_actor_this_round_id = None
        first_actor_index_this_round = -1
        for i, entity_id_in_order in enumerate(self.turn_order):
            entity = self.entities.get(entity_id_in_order)
            if entity and entity.is_alive() and getattr(entity, 'is_active_in_combat', True):
                if first_actor_this_round_id is None: 
                    first_actor_this_round_id = entity_id_in_order
                    first_actor_index_this_round = i
        
        if first_actor_this_round_id:
            self.current_turn_index = first_actor_index_this_round 
            self._active_entity_id = first_actor_this_round_id
            logger.info(f"Round {self.round_number}. First active entity identified: {self.entities[self._active_entity_id].combat_name}")
            self._set_next_actor_step(self._active_entity_id, engine) # Pass engine here
        else:
            logger.warning("No active entities found to start the round. Ending combat.")
            self._check_combat_state() 
            if self.state == CombatState.IN_PROGRESS: self.end_combat("No active combatants to start round.")
            self.current_step = CombatStep.ENDING_COMBAT
        
        self.waiting_for_display_completion = True
    def receive_player_action(self, engine: 'GameEngine', intent: str):
        if self.current_step != CombatStep.AWAITING_PLAYER_INPUT:
            logger.warning(f"Received player action intent '{intent[:50]}...' but current step is {self.current_step}. Ignoring.")
            return
        logger.info(f"Player action intent received: '{intent}'")
        self._current_intent = intent
        self.current_step = CombatStep.PROCESSING_PLAYER_ACTION
        self.process_combat_step(engine)

    def prepare_for_combat(self, player_entity: CombatEntity, enemy_entities: List[CombatEntity], surprise: bool, initiating_intent: str):
        logger.info(f"Preparing for combat. Surprise: {surprise}. Intent: '{initiating_intent[:50]}...'")
        self.entities = {}
        self.turn_order = []
        self.current_turn_index = 0
        self.round_number = 0
        self.state = CombatState.NOT_STARTED # Will be set to IN_PROGRESS after sync
        self.combat_log = []
        self.last_action_results = {}
        self._pending_action = None
        self._last_action_result_detail = None
        self._current_intent = None
        self._active_entity_id = None
        self._surprise_attack = surprise
        self._initiating_intent = initiating_intent
        self._is_surprise_round = False # Initialize
        self._surprise_round_entities = [] # Initialize

        if not hasattr(player_entity, 'combat_name') or not player_entity.combat_name:
            logger.error(f"Player entity missing combat_name: {player_entity.name}")
            player_entity.combat_name = player_entity.name # Fallback
        self.entities[player_entity.id] = player_entity
        self._player_entity_id = player_entity.id
        
        self._enemy_entity_ids = []
        for enemy in enemy_entities:
            if not hasattr(enemy, 'combat_name') or not enemy.combat_name:
                logger.error(f"Enemy entity missing combat_name: {enemy.name}")
                enemy.combat_name = enemy.name # Fallback
            self.entities[enemy.id] = enemy
            self._enemy_entity_ids.append(enemy.id)
            logger.info(f"Added entity to combat prep: {enemy.name} (Combat Name: {enemy.combat_name}, ID: {enemy.id})")

        # Explicitly sync CombatEntity fields with their StatsManagers
        for entity_id, combat_entity_obj in self.entities.items():
            entity_stats_manager = self._get_entity_stats_manager(entity_id)
            if entity_stats_manager:
                try:
                    combat_entity_obj.max_hp = entity_stats_manager.get_stat_value(DerivedStatType.MAX_HEALTH)
                    combat_entity_obj.current_hp = entity_stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
                    
                    combat_entity_obj.max_stamina = entity_stats_manager.get_stat_value(DerivedStatType.MAX_STAMINA)
                    combat_entity_obj.current_stamina = entity_stats_manager.get_current_stat_value(DerivedStatType.STAMINA)
                    
                    combat_entity_obj.max_mp = entity_stats_manager.get_stat_value(DerivedStatType.MAX_MANA)
                    combat_entity_obj.current_mp = entity_stats_manager.get_current_stat_value(DerivedStatType.MANA)
                    
                    combat_entity_obj.initiative = entity_stats_manager.get_stat_value(DerivedStatType.INITIATIVE) # Sync initiative base
                    
                    # Sync status effects from StatsManager to CombatEntity's simple dict
                    # This ensures CombatEntity.status_effects (Dict[str, Optional[int]]) is up-to-date
                    # for display purposes and simple checks, while StatsManager.status_effect_manager
                    # holds the full StatusEffect objects.
                    combat_entity_obj.status_effects.clear()
                    active_stat_effects = entity_stats_manager.status_effect_manager.active_effects
                    for effect_id, status_effect_obj in active_stat_effects.items():
                        combat_entity_obj.add_status_effect(status_effect_obj.name, status_effect_obj.duration)

                    logger.debug(f"Synced CombatEntity {combat_entity_obj.combat_name} with its StatsManager: "
                                f"HP: {combat_entity_obj.current_hp}/{combat_entity_obj.max_hp}, "
                                f"Stamina: {combat_entity_obj.current_stamina}/{combat_entity_obj.max_stamina}, "
                                f"MP: {combat_entity_obj.current_mp}/{combat_entity_obj.max_mp}, "
                                f"Status: {list(combat_entity_obj.status_effects.keys())}")
                except Exception as e:
                    logger.error(f"Error syncing CombatEntity {entity_id} with its StatsManager in prepare_for_combat: {e}", exc_info=True)
            else:
                logger.warning(f"Could not find StatsManager for entity {entity_id} during combat prep sync.")
        
        if self._surprise_attack and self._player_entity_id:
            # For player-initiated surprise, player is the one acting
            self._is_surprise_round = True
            self._surprise_round_entities = [self._player_entity_id]
            # Enemies would get "Surprised" status in _step_handling_surprise_check

        self.state = CombatState.IN_PROGRESS
        self.current_step = CombatStep.STARTING_COMBAT
        logger.info("CombatManager prepared. Next step: STARTING_COMBAT.")

    def _determine_initiative(self) -> None:
        initiative_rolls = []
        for entity_id, entity in self.entities.items():
            base_initiative = entity.get_stat(DerivedStatType.INITIATIVE)
            roll = random.randint(1, 6)
            total_initiative = base_initiative + roll
            entity.initiative = total_initiative
            initiative_rolls.append((entity_id, total_initiative))
            self._add_to_log(f"{entity.name} rolled initiative: {total_initiative} ({base_initiative} + {roll})")
        initiative_rolls.sort(key=lambda x: x[1], reverse=True)
        self.turn_order = [entity_id for entity_id, _ in initiative_rolls]
        self.current_turn_index = 0

    def _log_turn_order(self) -> None:
        turn_order_str = "Turn order: "
        turn_order_str += ", ".join(self.entities[entity_id].combat_name for entity_id in self.turn_order if entity_id in self.entities)
        self._add_to_log(turn_order_str)

    def get_current_entity(self) -> Optional[CombatEntity]:
        if self.state != CombatState.IN_PROGRESS: return None
        if self._is_surprise_round:
            if self._active_entity_id: return self.entities.get(self._active_entity_id)
            else: logger.warning("In surprise round but _active_entity_id is not set."); return None
        elif self.turn_order and self.current_turn_index < len(self.turn_order):
            entity_id = self.turn_order[self.current_turn_index]
            if entity_id != self._active_entity_id:
                logger.warning(f"Mismatch between turn order index ({self.current_turn_index} -> {entity_id}) and active entity ({self._active_entity_id}). Using turn order.")
                self._active_entity_id = entity_id
            return self.entities.get(entity_id)
        elif self._active_entity_id:
            logger.warning("Turn order invalid, but _active_entity_id is set. Returning entity based on active ID.")
            return self.entities.get(self._active_entity_id)
        logger.debug("No current entity could be determined.")
        return None

    def get_current_entity_id(self) -> Optional[str]:
        return self._active_entity_id

    def is_player_turn(self) -> bool:
        current_entity = self.get_current_entity()
        return current_entity is not None and current_entity.entity_type == EntityType.PLAYER

    def _calculate_stamina_cost(self, action: CombatAction, performer: CombatEntity) -> Tuple[float, List[str]]:
        cost_details = []
        from core.stats.derived_stats import get_modifier_from_stat
        base_cost = 0.0
        if action.action_type == ActionType.ATTACK: base_cost = 5.0
        elif action.action_type == ActionType.SPELL: base_cost = 2.0
        elif action.action_type == ActionType.SKILL: base_cost = 10.0
        elif action.action_type == ActionType.DEFEND: base_cost = 3.0
        elif action.action_type == ActionType.MOVE: base_cost = 2.0
        elif action.action_type == ActionType.FLEE: base_cost = 8.0
        base_cost = action.cost_stamina if action.cost_stamina > 0 else base_cost
        cost_details.append(f"Base Cost: {base_cost}")
        con_mod = 0
        try:
            con_value = performer.get_stat(StatType.CONSTITUTION)
            con_mod = get_modifier_from_stat(con_value)
            base_cost -= con_mod
            cost_details.append(f"CON Mod: {-con_mod}")
        except Exception as e: logger.warning(f"Could not get CON modifier for stamina cost: {e}")
        encumbrance_multiplier = 1.0
        try:
            inventory_manager = get_inventory_manager()
            current_weight = inventory_manager.get_current_weight()
            max_carry_capacity = performer.get_stat(DerivedStatType.CARRY_CAPACITY)
            if max_carry_capacity > 0:
                encumbrance_percent = (current_weight / max_carry_capacity) * 100
                if encumbrance_percent > 100: encumbrance_multiplier = 2.0; cost_details.append("Encumbrance: Over (>100%, x2.0)")
                elif encumbrance_percent > 75: encumbrance_multiplier = 1.5; cost_details.append(f"Encumbrance: Heavy ({encumbrance_percent:.0f}%, x1.5)")
                elif encumbrance_percent > 50: encumbrance_multiplier = 1.25; cost_details.append(f"Encumbrance: Medium ({encumbrance_percent:.0f}%, x1.25)")
                else: cost_details.append(f"Encumbrance: Light ({encumbrance_percent:.0f}%, x1.0)")
            else: cost_details.append("Encumbrance: N/A (Max Capacity 0)")
        except Exception as e: logger.warning(f"Could not calculate encumbrance modifier: {e}"); cost_details.append("Encumbrance: Error")
        status_multiplier = 1.0
        if performer.has_status_effect("Fatigued"): status_multiplier = 1.5; cost_details.append("Status: Fatigued (x1.5)")
        if performer.has_status_effect("Energized"): status_multiplier = 0.75; cost_details.append("Status: Energized (x0.75)")
        final_cost = max(0, base_cost * encumbrance_multiplier * status_multiplier)
        cost_details.append(f"Final Cost: {final_cost:.2f}")
        return final_cost, cost_details

    def perform_action(self, action: CombatAction, engine: Optional['GameEngine'] = None) -> Dict[str, Any]:
        """
        Performs the *mechanics* of a combat action, updating state via StatsManager.
        It now also queues DisplayEvents for rolls, damage, UI updates via the orchestrator
        by calling handlers from action_handlers.py.
        Stamina/Mana costs are now applied *before* the action handler is called.
        Does NOT call agents or advance turns. Returns a detailed result dictionary for internal use
        and a flag if events were queued.

        Args:
            action: The action to perform.
            engine: The GameEngine instance (for accessing orchestrator).

        Returns:
            Dictionary with the detailed results and a 'queued_events': True/False flag.
        """
        if not engine or not hasattr(engine, '_combat_orchestrator'):
            logger.error("Engine or Orchestrator unavailable in perform_action. Cannot queue display events.")
            return {"success": False, "message": "Internal Error: Orchestrator missing.", "queued_events": False}

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 

        default_result = {"success": False, "message": "Action could not be performed.", "queued_events": False}
        if self.state != CombatState.IN_PROGRESS:
            return {**default_result, "message": "Combat is not in progress"}

        performer = self.entities.get(action.performer_id)
        if not performer:
            return {**default_result, "message": "Performer entity not found"}

        performer_stats_manager = self._get_entity_stats_manager(performer.id)
        if not performer_stats_manager:
            logger.error(f"Could not find StatsManager for performer {performer.id}.")
            err_msg = f"Internal Error: Stats missing for {performer.combat_name}."
            event_err = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=err_msg, target_display=DisplayTarget.COMBAT_LOG)
            engine._combat_orchestrator.add_event_to_queue(event_err)
            return {**default_result, "message": err_msg, "queued_events": True}

        queued_events_flag = False 

        stamina_cost, cost_details_stamina = self._calculate_stamina_cost(action, performer)
        mana_cost = action.cost_mp
        current_stamina_val = performer_stats_manager.get_current_stat_value(DerivedStatType.STAMINA)
        current_mana_val = performer_stats_manager.get_current_stat_value(DerivedStatType.MANA)
        
        self._last_action_result_detail = {
            "performer_id": performer.id, "performer_name": performer.combat_name,
            "action_name": action.name, "stamina_cost_calculated": stamina_cost,
            "mana_cost_calculated": mana_cost,
            "action_id_for_narration": action.id # Store action ID for outcome narration matching
        }
        if action.targets:
            target_obj = self.entities.get(action.targets[0])
            if target_obj: self._last_action_result_detail["target_name"] = target_obj.combat_name
            self._last_action_result_detail["target_id"] = action.targets[0]

        if current_stamina_val < stamina_cost:
            cost_fail_msg = f"{performer.combat_name} tries to {action.name} but lacks stamina ({current_stamina_val:.1f}/{stamina_cost:.1f})"
            self._add_to_log(cost_fail_msg) 
            event_cost_fail = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=cost_fail_msg, target_display=DisplayTarget.COMBAT_LOG)
            engine._combat_orchestrator.add_event_to_queue(event_cost_fail)
            queued_events_flag = True
            self._last_action_result_detail.update({"success": False, "message": "Not enough stamina."})
            return {**default_result, "message": "Not enough stamina.", "queued_events": queued_events_flag}
        
        if mana_cost > 0 and current_mana_val < mana_cost:
            cost_fail_msg = f"{performer.combat_name} tries to {action.name} but lacks mana ({current_mana_val:.1f}/{mana_cost:.1f})"
            self._add_to_log(cost_fail_msg)
            event_cost_fail = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=cost_fail_msg, target_display=DisplayTarget.COMBAT_LOG)
            engine._combat_orchestrator.add_event_to_queue(event_cost_fail)
            queued_events_flag = True
            self._last_action_result_detail.update({"success": False, "message": "Not enough mana."})
            return {**default_result, "message": "Not enough mana.", "queued_events": queued_events_flag}

        # --- Defer resource cost visual updates to the action handler (after roll/attempt text) ---
        # Costs are recorded here to be applied (and displayed) by the handler at the correct timing
        self._last_action_result_detail["stamina_spent"] = stamina_cost
        self._last_action_result_detail["stamina_remaining_after_action_preview"] = current_stamina_val - stamina_cost
        self._last_action_result_detail["mana_spent"] = mana_cost if mana_cost > 0 else 0
        self._last_action_result_detail["mana_remaining_after_action_preview"] = (current_mana_val - mana_cost) if mana_cost > 0 else current_mana_val
        new_mana_preview = current_mana_val
        
        # Action handler execution
        try:
            action_handler_func = None
            if action.action_type == ActionType.ATTACK: action_handler_func = _handle_attack_action 
            elif action.action_type == ActionType.SPELL: action_handler_func = _handle_spell_action   
            elif action.action_type == ActionType.DEFEND: action_handler_func = _handle_defend_action 
            elif action.action_type == ActionType.ITEM: action_handler_func = _handle_item_action   
            elif action.action_type == ActionType.FLEE: action_handler_func = _handle_flee_action_mechanics

            if action_handler_func:
                # _last_action_result_detail is passed to be updated by the handler
                handler_result_dict = action_handler_func(self, action, performer, performer_stats_manager, engine, self._last_action_result_detail)
                # The handler_result_dict is now effectively the updated self._last_action_result_detail
                if handler_result_dict.get("queued_events", False): queued_events_flag = True
            else:
                generic_action_msg = f"{performer.combat_name} performs action: {action.name} (Type: {action.action_type.name}) - No specific handler."
                self._add_to_log(generic_action_msg)
                event_generic = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=generic_action_msg, target_display=DisplayTarget.COMBAT_LOG)
                engine._combat_orchestrator.add_event_to_queue(event_generic)
                queued_events_flag = True
                self._last_action_result_detail.update({"success": True, "message": f"Performed generic action: {action.name}"})

        except Exception as e:
            logger.error(f"Error executing action {action.name} mechanics for {performer.combat_name}: {e}", exc_info=True)
            exec_err_msg = f"System Error during {action.name}: {e}"
            event_exec_err = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=exec_err_msg, target_display=DisplayTarget.COMBAT_LOG)
            engine._combat_orchestrator.add_event_to_queue(event_exec_err)
            queued_events_flag = True
            self._last_action_result_detail.update({"success": False, "message": f"Error during execution: {e}"})
            return {**default_result, "message": f"Error: {e}", "queued_events": queued_events_flag}
        
        # Update the main result dict with success being the success of the mechanical action itself
        # (e.g., hit, spell landed, item used as intended)
        # The handlers directly modify self._last_action_result_detail.
        final_action_success = self._last_action_result_detail.get("success", False)
        final_action_message = self._last_action_result_detail.get("message", "Action processed.")
        
        return {"success": final_action_success, "message": final_action_message, "queued_events": queued_events_flag, "details": self._last_action_result_detail}
    
    def _step_processing_npc_action(self, engine):
        """Processes the NPC's stored intent, queues attempt narrative, converts to action, sets next step, then pauses."""
        if not hasattr(engine, '_combat_orchestrator') or not hasattr(engine, '_combat_narrator_agent'):
            logger.error("Orchestrator or CombatNarratorAgent not found in _step_processing_npc_action.")
            self.current_step = CombatStep.ADVANCING_TURN 
            self.waiting_for_display_completion = False
            return

        active_id = self._active_entity_id
        if not self._current_intent or not active_id:
            logger.error(f"Processing NPC action step for {active_id}, but no intent or active_id. Advancing turn.")
            self.current_step = CombatStep.ADVANCING_TURN 
            self.waiting_for_display_completion = False
            return

        npc_entity = self.entities.get(active_id)
        if not npc_entity: # Should not happen
            logger.error(f"Cannot process NPC action: NPC entity {active_id} not found. Advancing turn.")
            self.current_step = CombatStep.ADVANCING_TURN 
            self.waiting_for_display_completion = False
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        from core.interaction.context_builder import ContextBuilder
        from core.agents.base_agent import AgentContext
        logger.info(f"Processing NPC Intent ({npc_entity.combat_name}): '{self._current_intent}'")

        game_state = engine._state_manager.current_state
        if not game_state:
            logger.error("GameState not found for NPC action processing. Advancing.")
            self.current_step = CombatStep.ADVANCING_TURN
            self.waiting_for_display_completion = False
            return

        context_dict = ContextBuilder().build_context(game_state, InteractionMode.COMBAT, actor_id=active_id)
        agent_context = AgentContext(
            game_state=context_dict, player_state=context_dict.get('player', {}),
            world_state={k: v for k, v in context_dict.items() if k in ['location', 'time_of_day', 'environment']},
            player_input=self._current_intent, conversation_history=game_state.conversation_history,
            additional_context=context_dict
        )
        
        agent_output = None; conversion_success = False
        try: agent_output = engine._combat_narrator_agent.process(agent_context)
        except Exception as e: logger.error(f"Error calling CombatNarratorAgent for NPC {active_id} action: {e}", exc_info=True)

        if not agent_output or "narrative" not in agent_output:
            logger.error(f"Combat Narrator failed for NPC {active_id}. Fallback: Attack player.")
            fallback_narrative = f"{npc_entity.combat_name} looks confused, then lashes out wildly!"
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.NARRATIVE_ATTEMPT, content=fallback_narrative, role="gm", tts_eligible=True, gradual_visual_display=True, target_display=DisplayTarget.COMBAT_LOG))
            player_target = next((e for e in self.entities.values() if e.entity_type == EntityType.PLAYER and e.is_alive()), None)
            if player_target: self._pending_action = AttackAction(performer_id=active_id, target_id=player_target.id, weapon_name="fallback attack")
            else: self._pending_action = None
        else:
            if agent_output["narrative"]:
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.NARRATIVE_ATTEMPT, content=agent_output["narrative"], role="gm", tts_eligible=True, gradual_visual_display=True, target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name))
            
            self._pending_action = None 
            validated_requests = agent_output.get("requests", [])
            if not validated_requests:
                no_req_msg = f"{npc_entity.combat_name} considers their options but doesn't act this turn."
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.NARRATIVE_GENERAL, content=no_req_msg, role="gm", tts_eligible=True, gradual_visual_display=True, target_display=DisplayTarget.COMBAT_LOG))
            else: # Process first request to form an action
                action_request = validated_requests[0]
                try:
                    def normalize_action_type(action_name_str: str) -> str: return action_name_str.upper().strip().replace(' ', '_')
                    action_type_map = {"MELEE_ATTACK": ActionType.ATTACK, "RANGED_ATTACK": ActionType.ATTACK, "UNARMED_ATTACK": ActionType.ATTACK, "SPELL_ATTACK": ActionType.SPELL, "DEFEND": ActionType.DEFEND, "FLEE": ActionType.FLEE, "USE_ITEM": ActionType.ITEM}
                    
                    skill_name = action_request.get("skill_name") # e.g., "SPELL_ATTACK" or "Fireball"
                    combat_action_type = ActionType.OTHER
                    normalized_skill_for_action_name = skill_name or "action" # Use skill_name for spell/weapon name
                    if skill_name:
                        normalized_skill = normalize_action_type(skill_name)
                        combat_action_type = action_type_map.get(normalized_skill, ActionType.OTHER)
                        # If it's a generic type like "SPELL_ATTACK", the action name should be more specific if possible
                        # For example, if the intent was "cast fireball", skill_name from agent might be "Fireball"
                        if normalized_skill in ["SPELL_ATTACK", "MELEE_ATTACK", "RANGED_ATTACK"]:
                            # Use a more generic name for the action object if skill_name itself is generic
                            # The action_handlers will use dice_notation etc from the action object.
                            # The specific skill_name is more for display and determining type.
                            pass # normalized_skill_for_action_name is already skill_name

                    target_internal_id = None
                    target_combat_name_req = action_request.get("target_actor_id")
                    if target_combat_name_req:
                        target_entity = self._find_entity_by_combat_name(target_combat_name_req)
                        if target_entity: target_internal_id = target_entity.id
                        else: engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=f"{npc_entity.combat_name} looks for '{target_combat_name_req}' but can't find them!", target_display=DisplayTarget.COMBAT_LOG))

                    if combat_action_type == ActionType.ATTACK and target_internal_id:
                        self._pending_action = AttackAction(performer_id=active_id, target_id=target_internal_id, weapon_name=normalized_skill_for_action_name, dice_notation=action_request.get("dice_notation", "1d6"))
                    elif combat_action_type == ActionType.SPELL: # Fixed: Check if target_internal_id exists for targeted spells
                        # Assume for now that if target_internal_id is None, it's an area spell or self-buff
                        # This needs more robust handling based on spell type from agent
                        self._pending_action = SpellAction(
                            performer_id=active_id, spell_name=normalized_skill_for_action_name, 
                            target_ids=[target_internal_id] if target_internal_id else [], # Empty list if no target
                            cost_mp=float(action_request.get("cost_mp", 5.0)), 
                            dice_notation=action_request.get("dice_notation", "1d8" if target_internal_id else ""), # No dice if no target for default
                            description=action_request.get("description", f"Casting {normalized_skill_for_action_name}")
                        )
                    elif combat_action_type == ActionType.DEFEND:
                         self._pending_action = DefendAction(performer_id=active_id)
                    elif combat_action_type == ActionType.FLEE:
                         self._pending_action = FleeAction(performer_id=active_id)
                    
                    if self._pending_action:
                        logger.info(f"NPC ({npc_entity.combat_name}) action request converted to CombatAction: {self._pending_action.name}")
                        conversion_success = True
                    else: # Conversion failed or required target missing
                        # Only queue this if error wasn't already about target not found
                        if not (target_internal_id is None and (combat_action_type == ActionType.ATTACK or (combat_action_type == ActionType.SPELL and action_request.get("dice_notation")) )): 
                            conversion_fail_msg = f"{npc_entity.combat_name} attempts to {skill_name or 'act'}, but hesitates."
                            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.NARRATIVE_GENERAL, content=conversion_fail_msg, role="gm", tts_eligible=True, gradual_visual_display=True, target_display=DisplayTarget.COMBAT_LOG))
                except Exception as e:
                    logger.exception(f"Error converting NPC {active_id} action request: {e}")
                    engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=f"[System Error: Could not process {npc_entity.combat_name}'s action.]", target_display=DisplayTarget.COMBAT_LOG))
        
        # Determine next step based on whether an action was successfully prepared
        if self._pending_action:
            self.current_step = CombatStep.RESOLVING_ACTION_MECHANICS
        else: # No action prepared (conversion fail, no request, fallback failed)
            self.current_step = CombatStep.APPLYING_STATUS_EFFECTS # Skip to end of turn

        self._current_intent = None 
        self.waiting_for_display_completion = True 

    def _step_resolving_action_mechanics(self, engine): # Added engine parameter
        """
        Initiates the processing of the current pending action (player or NPC regular turn)
        by calling self.perform_action.
        """
        if not hasattr(engine, '_combat_orchestrator'):
            logger.error("Orchestrator not found on engine in _step_resolving_action_mechanics.")
            self.current_step = CombatStep.ADVANCING_TURN 
            self.waiting_for_display_completion = False
            return

        if not self._pending_action:
            logger.error("Resolving mechanics step, but no pending action stored.")
            self.current_step = CombatStep.APPLYING_STATUS_EFFECTS 
            self.waiting_for_display_completion = False
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 

        action_to_process = self._pending_action
        # self._pending_action = None # Clear this LATER

        logger.info(f"Initiating regular action mechanics for: {action_to_process.name} by entity {action_to_process.performer_id}")

        action_execution_summary = self.perform_action(action_to_process, engine)

        if not action_execution_summary.get("queued_events", False) and not action_execution_summary.get("success", False):
            logger.warning(f"perform_action for {action_to_process.name} did not queue events and reported failure. "
                           f"Message: {action_execution_summary.get('message')}")
            if not engine._combat_orchestrator.event_queue:
                fail_msg = self._last_action_result_detail.get("message") if self._last_action_result_detail else f"Action {action_to_process.name} by {self.entities[action_to_process.performer_id].combat_name} could not be resolved."
                event_action_fail = DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=fail_msg, target_display=DisplayTarget.COMBAT_LOG)
                engine._combat_orchestrator.add_event_to_queue(event_action_fail)
        
        self.current_step = CombatStep.NARRATING_ACTION_OUTCOME
        self.waiting_for_display_completion = True

    def _step_narrating_action_outcome(self, engine):
        """Generates and outputs the narrative description of the action's outcome, then sets next step."""
        if not hasattr(engine, '_combat_orchestrator') or not hasattr(engine, '_combat_narrator_agent'):
            logger.error("Orchestrator or CombatNarratorAgent not found in _step_narrating_action_outcome.")
            self.current_step = CombatStep.APPLYING_STATUS_EFFECTS
            self.waiting_for_display_completion = False
            return

        if not self._last_action_result_detail:
            logger.warning("No action result found to narrate outcome. Skipping narration.")
            self.current_step = CombatStep.APPLYING_STATUS_EFFECTS 
            self.waiting_for_display_completion = False
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        action_name_log = self._last_action_result_detail.get('action_name', 'Unknown Action')
        logger.info(f"Generating narrative for action outcome: {action_name_log}")

        outcome_narrative = None; agent_failed = False
        try:
            outcome_narrative = engine._combat_narrator_agent.narrate_outcome(self._last_action_result_detail, self)
            if not outcome_narrative: agent_failed = True
        except Exception as e: logger.error(f"Error calling narrate_outcome: {e}", exc_info=True); agent_failed = True

        if agent_failed: # Fallback narrative
            result = self._last_action_result_detail
            performer_name = result.get("performer_name", "Actor")
            target_name = result.get("target_name", "Target")
            action_name_disp = result.get("action_name", "action")
            damage = result.get("damage", 0)
            success_flag = result.get("success", False) # This is mechanical success of the action handler

            if success_flag: 
                if result.get("fled") is True: outcome_narrative = f"{performer_name} successfully flees the battle!"
                elif result.get("action_type") == ActionType.DEFEND: outcome_narrative = f"{performer_name} braces defensively."
                elif damage > 0: outcome_narrative = f"The {action_name_disp} from {performer_name} strikes {target_name} for {damage:.0f} damage."
                else: outcome_narrative = f"{performer_name}'s {action_name_disp} affects {target_name}, but deals no direct damage."
                if result.get("target_defeated"): outcome_narrative += f" {target_name} is overcome and falls!"
            else: # Mechanical failure
                if result.get("fled") is False : outcome_narrative = f"{performer_name} tries to flee but cannot escape!"
                else: outcome_narrative = f"{performer_name}'s {action_name_disp} against {target_name} fails utterly."
        
        if outcome_narrative:
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.NARRATIVE_IMPACT, content=outcome_narrative, role="gm", tts_eligible=True, gradual_visual_display=True, target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name))
            self.waiting_for_display_completion = True
        else:
            self.waiting_for_display_completion = False # No narrative, proceed faster

        # Decide whether combat should end right after outcome narrative
        end_player_victory = False
        end_player_defeat = False
        try:
            from core.combat.combat_entity import EntityType
            # Player defeat if player entity is not alive
            player_id = getattr(self, '_player_entity_id', None)
            if player_id and player_id in self.entities:
                player_entity_obj = self.entities.get(player_id)
                if player_entity_obj and not player_entity_obj.is_alive():
                    end_player_defeat = True
            # Victory if no active, alive enemies remain
            remaining_enemies = [e for e in self.entities.values() if getattr(e, 'entity_type', None) == EntityType.ENEMY and getattr(e, 'is_active_in_combat', True) and e.is_alive()]
            if len(remaining_enemies) == 0:
                end_player_victory = True
        except Exception:
            pass

        # Clear pending action only AFTER narration is done with its details
        if self._pending_action and self._pending_action.id == self._last_action_result_detail.get("action_id_for_narration"):
            self._pending_action = None
        self._last_action_result_detail = None # Clear after use

        if end_player_defeat:
            self.state = CombatState.PLAYER_DEFEAT
            self.current_step = CombatStep.ENDING_COMBAT
            # keep waiting_for_display_completion as set above when narrative was queued
        elif end_player_victory:
            self.state = CombatState.PLAYER_VICTORY
            self.current_step = CombatStep.ENDING_COMBAT
        else:
            self.current_step = CombatStep.APPLYING_STATUS_EFFECTS 

    def _step_applying_status_effects(self, engine): # Added engine parameter
        """Applies end-of-turn status effects, regeneration, and updates durations. Queues messages."""
        if not hasattr(engine, '_combat_orchestrator'):
            logger.error("Orchestrator not found on engine in _step_applying_status_effects.")
            self.current_step = CombatStep.ADVANCING_TURN
            self.waiting_for_display_completion = False
            return

        if not self._active_entity_id: 
            logger.warning("Cannot apply status effects: No _active_entity_id set.")
            self.current_step = CombatStep.ADVANCING_TURN
            self.waiting_for_display_completion = False
            return

        entity = self.entities.get(self._active_entity_id)
        if not entity:
            logger.warning(f"Cannot apply status effects: Entity {self._active_entity_id} not found.")
            self.current_step = CombatStep.ADVANCING_TURN
            self.waiting_for_display_completion = False
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        logger.debug(f"Applying end-of-turn effects for {entity.combat_name} ({entity.id})")
        queued_any_effect_event = False

        stats_manager_for_actor = self._get_entity_stats_manager(entity.id)
        if not stats_manager_for_actor:
            logger.warning(f"Cannot process status effects for {entity.combat_name}: StatsManager not found.")
            self.current_step = CombatStep.ADVANCING_TURN
            self.waiting_for_display_completion = False
            return

        # --- DOT/HOT processing ---
        if entity.has_status_effect("Poisoned"): 
            poison_damage = 3.0 
            hp_before_poison = stats_manager_for_actor.get_current_stat_value(DerivedStatType.HEALTH)
            hp_after_poison_preview = hp_before_poison - poison_damage
            
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={}, metadata={"entity_id": entity.id, "bar_type": "hp", "old_value": hp_before_poison, "new_value_preview": hp_after_poison_preview, "max_value": entity.max_hp})); queued_any_effect_event = True
            
            stats_manager_for_actor.set_current_stat(DerivedStatType.HEALTH, hp_after_poison_preview)
            entity.set_current_hp(hp_after_poison_preview) 

            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={}, metadata={"entity_id": entity.id, "bar_type": "hp", "final_new_value": hp_after_poison_preview, "max_value": entity.max_hp})); queued_any_effect_event = True
            
            poison_msg = f"{entity.combat_name} takes {poison_damage:.0f} damage from Poison. (HP: {int(hp_after_poison_preview)}/{int(entity.max_hp)})"
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=poison_msg, target_display=DisplayTarget.COMBAT_LOG)); self._add_to_log(poison_msg)
            queued_any_effect_event = True
            if hp_after_poison_preview <=0 and entity.is_alive(): 
                entity.is_active_in_combat = False 
                defeat_msg = f"{entity.combat_name} succumbs to poison!"
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=defeat_msg, target_display=DisplayTarget.COMBAT_LOG)); self._add_to_log(defeat_msg)
                queued_any_effect_event = True
        
        # --- Stamina Regeneration ---
        if entity.is_alive() and hasattr(stats_manager_for_actor, 'regenerate_combat_stamina'):
            regen_amount, regen_narrative = stats_manager_for_actor.regenerate_combat_stamina()
            if regen_amount > 0 and regen_narrative:
                # Note: regenerate_combat_stamina already calls set_current_stat, which emits stats_changed.
                # The UI will react to stats_changed for CharacterSheet.
                # For CombatDisplayWidget, we need explicit PHASE1/PHASE2 for stamina.
                current_stam_after_action_before_regen = stats_manager_for_actor.get_current_stat_value(DerivedStatType.STAMINA) - regen_amount #Approximate before regen
                current_stam_after_regen = stats_manager_for_actor.get_current_stat_value(DerivedStatType.STAMINA)
                max_stam = stats_manager_for_actor.get_stat_value(DerivedStatType.MAX_STAMINA)

                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={}, metadata={"entity_id": entity.id, "bar_type": "stamina", "old_value": current_stam_after_action_before_regen, "new_value_preview": current_stam_after_regen, "max_value": max_stam}))
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={}, metadata={"entity_id": entity.id, "bar_type": "stamina", "final_new_value": current_stam_after_regen, "max_value": max_stam}))
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=regen_narrative, target_display=DisplayTarget.COMBAT_LOG))
                self._add_to_log(regen_narrative)
                queued_any_effect_event = True


        # --- Decrement durations ---
        expired_effect_names_this_turn = entity.decrement_status_effect_durations() 
        
        if expired_effect_names_this_turn:
            for expired_name in expired_effect_names_this_turn:
                stats_manager_for_actor.modifier_manager.remove_modifiers_by_source(ModifierSource.CONDITION, expired_name)
                
                expired_msg_content = f"Status effect '{expired_name}' has worn off {entity.combat_name}."
                engine._combat_orchestrator.add_event_to_queue(
                    DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=expired_msg_content, target_display=DisplayTarget.COMBAT_LOG)
                ); self._add_to_log(expired_msg_content)
                queued_any_effect_event = True
        
        self.current_step = CombatStep.ADVANCING_TURN
        if queued_any_effect_event:
            self.waiting_for_display_completion = True 
        else: 
            self.waiting_for_display_completion = False
            
    def _step_processing_player_action(self, engine): # Engine is passed
        """Processes the player's stored intent, queues attempt narrative, converts to action or mode transition, then sets next step and pauses."""
        if not hasattr(engine, '_combat_orchestrator') or not hasattr(engine, '_combat_narrator_agent'):
            logger.error("Orchestrator or CombatNarratorAgent not found in _step_processing_player_action.")
            self.current_step = CombatStep.AWAITING_PLAYER_INPUT 
            self.waiting_for_display_completion = False
            return

        if not self._current_intent:
            logger.error("Processing player action step, but no intent stored. Reverting to AWAITING_PLAYER_INPUT.")
            self.current_step = CombatStep.AWAITING_PLAYER_INPUT 
            self.waiting_for_display_completion = False
            return

        player_id = self._player_entity_id
        if not player_id: 
            logger.error("Cannot process player action: Player ID unknown. Advancing turn.")
            self.current_step = CombatStep.ADVANCING_TURN 
            self.waiting_for_display_completion = False
            return
            
        player_entity = self.entities.get(player_id)
        if not player_entity:
            logger.error(f"Player entity {player_id} not found for action processing. Advancing turn.")
            self.current_step = CombatStep.ADVANCING_TURN
            self.waiting_for_display_completion = False
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        from core.interaction.context_builder import ContextBuilder
        from core.agents.base_agent import AgentContext
        logger.info(f"Processing Player Intent ({player_entity.combat_name}): '{self._current_intent}'")

        game_state = engine._state_manager.current_state
        if not game_state: 
            logger.error("GameState not found for player action processing. Reverting.")
            self.current_step = CombatStep.AWAITING_PLAYER_INPUT
            self.waiting_for_display_completion = False
            return
            
        context_dict = ContextBuilder().build_context(game_state, InteractionMode.COMBAT, actor_id=player_id)
        agent_context = AgentContext(
            game_state=context_dict, player_state=context_dict.get('player', {}),
            world_state={k: v for k, v in context_dict.items() if k in ['location', 'time_of_day', 'environment']},
            player_input=self._current_intent, conversation_history=game_state.conversation_history if game_state else [],
            additional_context=context_dict
        )

        agent_output = None
        try:
            agent_output = engine._combat_narrator_agent.process(agent_context)
        except Exception as e: logger.error(f"Error calling CombatNarratorAgent for player action: {e}", exc_info=True)
        
        action_processed_this_step = False # Flag to track if any action path was taken

        if not agent_output or "narrative" not in agent_output:
            err_msg = "[System Error: Failed to interpret action. Please try again, perhaps phrase differently.]"
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=err_msg, target_display=DisplayTarget.COMBAT_LOG))
            self.current_step = CombatStep.AWAITING_PLAYER_INPUT 
        else:
            if agent_output["narrative"]:
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.NARRATIVE_ATTEMPT, content=agent_output["narrative"], role="gm", tts_eligible=True, gradual_visual_display=True, target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name))
            
            self._pending_action = None 
            validated_requests = agent_output.get("requests", [])

            if not validated_requests:
                no_req_msg = f"{player_entity.combat_name} considers their options but doesn't commit to an action."
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.NARRATIVE_GENERAL, content=no_req_msg, role="gm", tts_eligible=True, gradual_visual_display=True, target_display=DisplayTarget.COMBAT_LOG))
                self.current_step = CombatStep.APPLYING_STATUS_EFFECTS 
                action_processed_this_step = True
            else:
                action_request = validated_requests[0]
                
                if action_request.get("action") == "request_mode_transition":
                    action_processed_this_step = True
                    logger.info(f"Player action interpreted as mode transition: {action_request}")
                    # Ensure actor_id from request is valid, fallback to current player_entity if needed
                    actor_combat_name_from_req = action_request.get("actor_id", player_entity.combat_name)
                    actor_for_transition = self._find_entity_by_combat_name(actor_combat_name_from_req)
                    if not actor_for_transition: actor_for_transition = player_entity 

                    from core.game_flow.mode_transitions import _handle_transition_request 
                    
                    if action_request.get("target_mode") == "NARRATIVE" and action_request.get("origin_mode") == "COMBAT":
                        action_request["additional_context"] = {
                            "original_intent": self._current_intent,
                            "narrative_context": agent_output["narrative"] 
                        }
                    
                    # _handle_transition_request will manage messages and potential mode changes.
                    # It returns a narrative string, which might be an error or success confirmation for non-combat transitions.
                    # For flee/surrender, it internally calls other functions that queue messages.
                    _handle_transition_request(engine, game_state, action_request, actor_for_transition.id)
                    
                    # After _handle_transition_request, check if mode actually changed
                    if game_state.current_mode != InteractionMode.COMBAT: 
                        self.current_step = CombatStep.ENDING_COMBAT # If mode changed, combat is ending.
                    else: 
                        # Mode is still COMBAT. This means flee/surrender failed or was not applicable.
                        # Player's turn ends.
                        self.current_step = CombatStep.APPLYING_STATUS_EFFECTS
                else: 
                    # Process as a regular combat action (attack, spell, etc.)
                    action_processed_this_step = True
                    try:
                        def normalize_action_type(action_name_str: str) -> str: return action_name_str.upper().strip().replace(' ', '_')
                        action_type_map = {"MELEE_ATTACK": ActionType.ATTACK, "RANGED_ATTACK": ActionType.ATTACK, "UNARMED_ATTACK": ActionType.ATTACK, "SPELL_ATTACK": ActionType.SPELL, "DEFEND": ActionType.DEFEND, "FLEE": ActionType.FLEE, "USE_ITEM": ActionType.ITEM}
                        
                        skill_name = action_request.get("skill_name")
                        combat_action_type = ActionType.OTHER
                        normalized_skill_for_action_name = skill_name or "action"
                        if skill_name:
                            normalized_skill = normalize_action_type(skill_name)
                            combat_action_type = action_type_map.get(normalized_skill, ActionType.OTHER)
                        
                        target_internal_id = None
                        target_combat_name_req = action_request.get("target_actor_id")
                        if target_combat_name_req:
                            target_entity = self._find_entity_by_combat_name(target_combat_name_req)
                            if target_entity: target_internal_id = target_entity.id
                            else: engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=f"Cannot perform action: Target '{target_combat_name_req}' not found.", target_display=DisplayTarget.COMBAT_LOG))
                        
                        if combat_action_type == ActionType.ATTACK and target_internal_id:
                            self._pending_action = AttackAction(performer_id=player_id, target_id=target_internal_id, weapon_name=normalized_skill_for_action_name, dice_notation=action_request.get("dice_notation", "1d6"))
                        elif combat_action_type == ActionType.SPELL:
                            self._pending_action = SpellAction(performer_id=player_id, spell_name=normalized_skill_for_action_name, target_ids=[target_internal_id] if target_internal_id else [], cost_mp=float(action_request.get("cost_mp", 5.0)), dice_notation=action_request.get("dice_notation", "1d8"))
                        elif combat_action_type == ActionType.DEFEND:
                            self._pending_action = DefendAction(performer_id=player_id)
                        elif combat_action_type == ActionType.FLEE: # Explicit FleeAction if CombatNarrator suggests it
                            self._pending_action = FleeAction(performer_id=player_id)
                        elif combat_action_type == ActionType.ITEM:
                            item_name_from_skill = skill_name 
                            item_id_placeholder = action_request.get("item_id", item_name_from_skill.lower().replace(" ","_")) if item_name_from_skill else "unknown_item"
                            self._pending_action = CombatAction(action_type=ActionType.ITEM, performer_id=player_id, name=f"Use {item_name_from_skill or 'Item'}", targets=[target_internal_id] if target_internal_id else [player_id], special_effects={"item_id": item_id_placeholder, "effect_type": "healing_potion", "heal_amount": 10})
                        
                        if self._pending_action:
                            logger.info(f"Player action request converted to CombatAction: {self._pending_action.name}")
                            self.current_step = CombatStep.RESOLVING_ACTION_MECHANICS
                        else: 
                            if not (target_internal_id is None and (combat_action_type == ActionType.ATTACK or (combat_action_type == ActionType.SPELL and not (skill_name and skill_name.lower().startswith("self")) ))):
                                conversion_fail_msg = f"Could not prepare action '{skill_name or 'unknown'}'. Try again."
                                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=conversion_fail_msg, target_display=DisplayTarget.COMBAT_LOG))
                            self.current_step = CombatStep.AWAITING_PLAYER_INPUT 
                    except Exception as e:
                        logger.exception(f"Error converting player action request: {e}")
                        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=f"[System Error: Could not process action. Please rephrase.]", target_display=DisplayTarget.COMBAT_LOG))
                        self.current_step = CombatStep.AWAITING_PLAYER_INPUT
            
            if not action_processed_this_step: # Fallback if no request path was taken (should be rare)
                logger.warning("No specific action path taken in _step_processing_player_action. Defaulting to end turn.")
                self.current_step = CombatStep.APPLYING_STATUS_EFFECTS
        
        self._current_intent = None 
        self.waiting_for_display_completion = True

    def _get_entity_stats_manager(self, entity_id: str, quiet: bool = False) -> Optional['StatsManager']:
        state_manager = get_state_manager()
        if not state_manager.current_state:
            if not quiet:
                logger.error("Current game state not found in StateManager.")
            return None
        player_id = getattr(state_manager.current_state.player, 'id', None) or getattr(state_manager.current_state.player, 'stats_manager_id', None)
        if entity_id == player_id:
            if hasattr(state_manager, 'stats_manager') and state_manager.stats_manager:
                logger.debug(f"Retrieved main StatsManager for player ID {entity_id}")
                return state_manager.stats_manager
            else:
                if not quiet:
                    logger.error(f"Could not retrieve main StatsManager for player ID {entity_id}")
                return None
        npc_system = state_manager.get_npc_system()
        if npc_system:
            npc = None
            if hasattr(npc_system, 'get_npc_by_id'):
                npc = npc_system.get_npc_by_id(entity_id)
                if npc: logger.debug(f"Found NPC {entity_id} via get_npc_by_id")
            else:
                if not quiet:
                    logger.warning("NPCSystem does not have get_npc_by_id method.")
            if npc is None and hasattr(npc_system, 'get_npc_by_name'):
                try:
                    combat_entity = self.entities.get(entity_id)
                    if combat_entity:
                        entity_name = combat_entity.name
                        if not quiet:
                            logger.warning(f"Attempting fallback lookup for NPC '{entity_name}' (ID: {entity_id}) via get_npc_by_name.")
                        npc = npc_system.get_npc_by_name(entity_name)
                        if npc: logger.debug(f"Found NPC {entity_name} via get_npc_by_name")
                    else:
                        if not quiet:
                            logger.warning(f"Cannot find entity name for ID {entity_id} to use get_npc_by_name.")
                except Exception as e:
                    if not quiet:
                        logger.error(f"Error looking up NPC by name '{entity_id}': {e}")
            if npc and hasattr(npc, 'stats_manager'):
                logger.debug(f"Retrieved StatsManager from NPCSystem for NPC ID {entity_id}")
                return npc.stats_manager
            elif npc:
                if not quiet:
                    logger.warning(f"NPC {entity_id} found via NPCSystem, but lacks a 'stats_manager' attribute.")
            else:
                if not quiet:
                    logger.warning(f"Could not find NPC for ID {entity_id} via NPCSystem using available methods.")
        else:
            if not quiet:
                logger.warning("NPCSystem not available via StateManager to retrieve NPC StatsManager.")
        if not quiet:
            logger.error(f"Could not retrieve StatsManager for entity ID {entity_id}")
        return None

    def _step_ending_combat(self, engine): # Engine is passed
        """Handles the end of combat, cleanup. Queues final message FOR COMBAT LOG."""
        if not hasattr(engine, '_combat_orchestrator'):
            logger.error("Orchestrator not found on engine in _step_ending_combat.")
            self.current_step = CombatStep.COMBAT_ENDED 
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
        logger.info(f"Processing ENDING_COMBAT step. Final State: {self.state.name}")
        
        # Clean up combat effects
        for entity in self.entities.values():
            stats_manager = self._get_entity_stats_manager(entity.id)
            if stats_manager:
                stats_manager.status_effect_manager.remove_effects_by_name("Defending")
                stats_manager.status_effect_manager.remove_effects_by_name("Advantage") 
                stats_manager.status_effect_manager.remove_effects_by_name("Surprised") 
            if hasattr(entity, 'remove_status_effect'): 
                entity.remove_status_effect("Defending") 
                entity.remove_status_effect("Advantage")
                entity.remove_status_effect("Surprised")

        # Generate loot from defeated NPCs
        self._generate_combat_loot(engine)

        # This message is the LAST message for the COMBAT LOG.
        # The GameEngine will handle the overall "Combat has concluded. Outcome: ..." for GameOutputWidget
        # and the LLM closing narrative AFTER the mode changes.
        final_combat_log_message = f"--- Combat Concluded ({self.state.name}) ---"
        self._add_to_log(final_combat_log_message) 

        event_combat_end_log = DisplayEvent(
            type=DisplayEventType.SYSTEM_MESSAGE, content=final_combat_log_message,
            target_display=DisplayTarget.COMBAT_LOG, 
            source_step=self.current_step.name,
            gradual_visual_display=False # Make this last one quick
        )
        engine._combat_orchestrator.add_event_to_queue(event_combat_end_log)
        
        self.current_step = CombatStep.COMBAT_ENDED # This signals GameEngine to take over for mode change etc.
        self.waiting_for_display_completion = True # Pause for this last combat log message

    def _step_advancing_turn(self, engine):
        """Advances the turn, queues message, sets next actor step, then pauses."""
        if not hasattr(engine, '_combat_orchestrator'):
            logger.error("Orchestrator not found on engine in _step_advancing_turn.")
            self.end_combat("Internal error: Orchestrator unavailable for turn advancement.")
            self.current_step = CombatStep.COMBAT_ENDED
            return

        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
        logger.debug("Executing step: ADVANCING_TURN")

        self._last_action_result_detail = None 

        next_entity_id = self._advance_turn() 

        if self.state != CombatState.IN_PROGRESS:
            logger.info(f"Combat ended ({self.state.name}) during/after _advance_turn. Moving to ENDING_COMBAT step.")
            self.current_step = CombatStep.ENDING_COMBAT
            self.waiting_for_display_completion = False 
            return

        if next_entity_id is None: # Should be caught by _advance_turn's _check_combat_state
            logger.error("Advancing turn failed to find next active entity, but combat state is IN_PROGRESS. This indicates an issue in _advance_turn or _check_combat_state. Forcing end.")
            if self.state == CombatState.IN_PROGRESS: self.end_combat("Error: Could not determine next turn.")
            self.current_step = CombatStep.ENDING_COMBAT
            self.waiting_for_display_completion = False
            return

        # --- Logic to queue "It is now X's turn" and set next step ---
        next_entity_obj = self.entities.get(next_entity_id)
        queued_turn_message = False
        if next_entity_obj:
            turn_msg = f"It is now {next_entity_obj.combat_name}'s turn."
            # _add_to_log for this message is handled in _advance_turn
            event_next_turn = DisplayEvent(
                type=DisplayEventType.SYSTEM_MESSAGE, content=turn_msg,
                target_display=DisplayTarget.COMBAT_LOG, source_step=self.current_step.name
            )
            engine._combat_orchestrator.add_event_to_queue(event_next_turn)
            queued_turn_message = True
        
        # Determine the actual next game step (AWAITING_PLAYER_INPUT or AWAITING_NPC_INTENT)
        self._set_next_actor_step(next_entity_id) 
        # self.current_step is now updated by _set_next_actor_step

        if queued_turn_message:
            self.waiting_for_display_completion = True # Pause for the "next turn" message
        else:
            # If no message was queued (should not happen if next_entity_obj exists),
            # don't pause, let process_combat_step loop continue to the new current_step.
            self.waiting_for_display_completion = False

    def _advance_turn(self) -> Optional[str]:
        if not self.turn_order:
            logger.error("Cannot advance turn: Turn order is empty.")
            self._check_combat_state(); return None
        self._check_combat_state()
        if self.state != CombatState.IN_PROGRESS:
            logger.info(f"Combat ended ({self.state.name}) during turn advancement check."); return None
        start_index = self.current_turn_index
        num_entities = len(self.turn_order)
        for i in range(1, num_entities + 1):
            next_index = (start_index + i) % num_entities
            next_entity_id = self.turn_order[next_index]
            next_entity = self.entities.get(next_entity_id)
            if next_entity and next_entity.is_alive() and getattr(next_entity, 'is_active_in_combat', True):
                self.current_turn_index = next_index
                self._active_entity_id = next_entity_id
                logger.info(f"Advanced turn. It is now {next_entity.combat_name}'s turn.")
                self._add_to_log(f"{next_entity.combat_name}'s turn.")
                return next_entity_id
            elif next_entity:
                reason = "inactive/fled" if not getattr(next_entity, 'is_active_in_combat', True) else "defeated"
                logger.debug(f"Skipping turn for {reason} entity: {next_entity.combat_name}")
        logger.warning("Looped through turn order and found no active entities.")
        self._check_combat_state(); return None

    def _set_next_actor_step(self, entity_id: str, engine: Optional['GameEngine'] = None): # Added engine parameter
        entity = self.entities.get(entity_id)
        if not entity:
            logger.error(f"Cannot set next step: Entity {entity_id} not found.")
            self.current_step = CombatStep.ADVANCING_TURN; return
        
        # --- Use passed engine parameter ---
        # engine = get_state_manager().current_state.game_engine if get_state_manager().current_state else None # Get engine # REMOVE THIS LINE
        
        if engine and hasattr(engine, '_combat_orchestrator'):
            turn_order_display_list = []
            for i, id_in_order in enumerate(self.turn_order):
                e = self.entities.get(id_in_order)
                if e and e.is_alive() and getattr(e, 'is_active_in_combat', True):
                    prefix = "→ " if id_in_order == entity_id else "  "
                    turn_order_display_list.append(f"{prefix}{getattr(e, 'combat_name', e.name)}")
                elif e:
                    turn_order_display_list.append(f"  [{getattr(e, 'combat_name', e.name)} - Defeated/Inactive]")
            
            active_entity_combat_name = getattr(entity, 'combat_name', entity.name)
            
            turn_order_event_content = {
                "turn_order_display_list": turn_order_display_list,
                "active_entity_combat_name": active_entity_combat_name,
                "is_surprise": self._is_surprise_round, 
                "round_number": self.round_number
            }
            from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
            engine._combat_orchestrator.add_event_to_queue(
                DisplayEvent(
                    type=DisplayEventType.TURN_ORDER_UPDATE, 
                    content=turn_order_event_content, 
                    target_display=DisplayTarget.MAIN_GAME_OUTPUT, 
                    source_step=f"SET_ACTOR_{entity_id}"
                )
            )
            logger.debug(f"Queued TURN_ORDER_UPDATE for CharacterSheet on {entity.combat_name}'s turn start.")
        elif not engine:
            logger.warning("_set_next_actor_step: Engine reference not provided, cannot queue TURN_ORDER_UPDATE for CharacterSheet.")

        if entity.has_status_effect("Stunned") or entity.has_status_effect("Immobilized") or entity.has_status_effect("Asleep"):
            status_name = "Stunned"
            if entity.has_status_effect("Immobilized"): status_name = "Immobilized"
            elif entity.has_status_effect("Asleep"): status_name = "Asleep"
            
            skip_turn_msg = f"{entity.combat_name} cannot act this turn (Status: {status_name})."
            if engine and hasattr(engine, '_combat_orchestrator'):
                from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
                engine._combat_orchestrator.add_event_to_queue(
                    DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=skip_turn_msg, target_display=DisplayTarget.COMBAT_LOG)
                )
            else: 
                self._add_to_log(skip_turn_msg)

            logger.info(f"{entity.combat_name}'s turn skipped due to status: {status_name}")
            self.current_step = CombatStep.APPLYING_STATUS_EFFECTS 
            return

        if entity.entity_type == EntityType.PLAYER:
            logger.info("Next step: AWAITING_PLAYER_INPUT")
            self.current_step = CombatStep.AWAITING_PLAYER_INPUT
        else:
            logger.info("Next step: AWAITING_NPC_INTENT")
            self.current_step = CombatStep.AWAITING_NPC_INTENT

    def _step_awaiting_npc_intent(self, engine): # Engine is passed
        """Retrieves the NPC's intended action for the turn."""
        if not self._active_entity_id:
            logger.error("Awaiting NPC intent step, but _active_entity_id is not set.")
            self.current_step = CombatStep.ADVANCING_TURN
            self.waiting_for_display_completion = False # No display event, allow immediate next step
            QTimer.singleShot(0, lambda: self.process_combat_step(engine)) # Nudge
            return
        
        from core.game_flow.npc_interaction import get_npc_intent

        npc_id = self._active_entity_id
        npc_entity = self.entities.get(npc_id)
        if not npc_entity:
            logger.error(f"Cannot get NPC intent: Entity {npc_id} not found.")
            self.current_step = CombatStep.ADVANCING_TURN
            self.waiting_for_display_completion = False
            QTimer.singleShot(0, lambda: self.process_combat_step(engine))
            return

        logger.info(f"Requesting intent for NPC: {npc_entity.combat_name} ({npc_id})")
        from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget # Local import

        # This step is purely logical for now; LLM call happens here.
        # If there was a "NPC is thinking..." message, it would be queued.
        game_state = engine._state_manager.current_state
        if not game_state:
            logger.error("GameState not found for NPC intent.")
            self.current_step = CombatStep.ADVANCING_TURN
            self.waiting_for_display_completion = False
            QTimer.singleShot(0, lambda: self.process_combat_step(engine))
            return
            
        intent = get_npc_intent(engine, game_state, npc_id)

        if intent:
            self._current_intent = intent
            logger.info(f"NPC Intent received for {npc_entity.combat_name}: '{intent}'")
            self.current_step = CombatStep.PROCESSING_NPC_ACTION
        else:
            logger.warning(f"Failed to get intent for NPC {npc_id}. NPC will falter.")
            self._current_intent = "Falter" # Give a default intent for processing
            # The "falters" narrative will be generated in the next step
            self.current_step = CombatStep.PROCESSING_NPC_ACTION 
            # (No, if no intent, directly to APPLYING_STATUS_EFFECTS after a message)
            # Correction: If intent is None/empty, generate falter message and go to APPLYING_STATUS_EFFECTS
            # Forcing PROCESSING_NPC_ACTION with "Falter" intent allows narrator to describe it.

        self.waiting_for_display_completion = False # No display events generated *in this specific step*
        # The next step (PROCESSING_NPC_ACTION) will queue display events.
        # We can let the process_combat_step loop continue if no display events were queued here.
        # However, to maintain consistency of Orchestrator driving resumption:
        if not engine._combat_orchestrator.event_queue and not engine._combat_orchestrator.is_processing_event:
             QTimer.singleShot(0, lambda: self.process_combat_step(engine))
        # This ensures that if this step doesn't queue anything, the CM loop continues.

    def _end_surprise_round(self) -> None:
        logger.info("Ending surprise round and transitioning to normal combat.")
        self._is_surprise_round = False
        self._surprise_round_entities = []
        for entity in self.entities.values():
            if entity.has_status_effect("Surprised"):
                entity.remove_status_effect("Surprised")
                logger.debug(f"Removed Surprised status from {entity.name} at end of surprise round")
        self.round_number = 1
        self.current_turn_index = 0
        self._add_to_log(f"Round {self.round_number} begins!")
        self._log_turn_order()

    def _process_status_effects(self, entity_id: str) -> None:
        entity = self.entities.get(entity_id)
        if not entity or not entity.is_alive(): return
        if hasattr(entity, 'decrement_status_effect_durations'):
            expired_effects = entity.decrement_status_effect_durations()
            if expired_effects:
                self._add_to_log(f"{entity.name} status effects expired: {', '.join(expired_effects)}")
                logger.debug(f"Status effects expired for {entity.name}: {expired_effects}")
            if "Defending" in expired_effects: self._add_to_log(f"{entity.name} stops defending.")
        else: logger.debug(f"Entity {entity.name} does not support timed status effects.")

    def _check_combat_state(self) -> None:
        if self.state != CombatState.IN_PROGRESS: return
        alive_players = 0; alive_enemies = 0
        for entity in self.entities.values():
            if entity.is_alive() and getattr(entity, 'is_active_in_combat', True):
                if entity.entity_type == EntityType.PLAYER or entity.entity_type == EntityType.ALLY: alive_players += 1
                elif entity.entity_type == EntityType.ENEMY: alive_enemies += 1
        if alive_players == 0:
            self.state = CombatState.PLAYER_DEFEAT
            self._add_to_log("Combat ended: All players defeated!")
        elif alive_enemies == 0:
            self.state = CombatState.PLAYER_VICTORY
            escaped_enemies = [e.name for e in self.entities.values() if e.entity_type == EntityType.ENEMY and not getattr(e, 'is_active_in_combat', False) and e.is_alive()]
            if escaped_enemies: self._add_to_log(f"Combat ended: Victory! All active enemies defeated! ({', '.join(escaped_enemies)} escaped)")
            else: self._add_to_log("Combat ended: Victory! All enemies defeated!")

    def _add_to_log(self, message: str) -> None:
        self.combat_log.append(message)
        logger.debug(f"Combat log: {message}")

    def get_combat_summary(self) -> Dict[str, Any]:
        current_entity = self.get_current_entity()
        return {
            "id": self.id, "state": self.state.name, "round": self.round_number,
            "current_turn": current_entity.name if current_entity else None,
            "entities": {
                entity_id: {
                    "name": entity.name, "hp": f"{int(entity.current_hp)}/{int(entity.max_hp)}",
                    "mp": f"{int(entity.current_mp)}/{int(entity.max_mp)}",
                    "stamina": f"{int(entity.current_stamina)}/{int(entity.max_stamina)}",
                    "status": list(entity.status_effects.keys()), "is_alive": entity.is_alive(),
                    "type": entity.entity_type.name
                } for entity_id, entity in self.entities.items()
            },
            "log": self.combat_log[-10:],
            "turn_order": [self.entities[entity_id].name for entity_id in self.turn_order if entity_id in self.entities]
        }

    def get_entity_by_id(self, entity_id: str) -> Optional[CombatEntity]:
        return self.entities.get(entity_id)

    def apply_surprise(self, surprised_entities: Optional[List[str]] = None, attacker_id: Optional[str] = None) -> None:
        if self.state != CombatState.IN_PROGRESS:
            logger.warning("Cannot apply surprise: Combat not in progress."); return
        if surprised_entities is None:
            player_ids = [eid for eid, e in self.entities.items() if e.entity_type in [EntityType.PLAYER, EntityType.ALLY]]
            enemy_ids = [eid for eid, e in self.entities.items() if e.entity_type == EntityType.ENEMY]
            if attacker_id in player_ids: surprised_entities = enemy_ids
            elif attacker_id in enemy_ids: surprised_entities = player_ids
            else: surprised_entities = player_ids
        for entity_id in surprised_entities:
            entity = self.entities.get(entity_id)
            if entity and entity.is_alive():
                if hasattr(entity, 'add_status_effect'):
                    entity.add_status_effect("Surprised", duration=1)
                    logger.debug(f"Applied Surprised status to {entity.name} for 1 turn")

    def end_combat(self, reason: str = "Combat ended") -> None:
        if self.state != CombatState.IN_PROGRESS:
            logger.warning(f"Attempted to end combat but state was {self.state.name}")
        previous_state = self.state
        if self.state == CombatState.IN_PROGRESS:
             if "fled" in reason.lower(): self.state = CombatState.FLED
             else: self.state = CombatState.NOT_STARTED
        self._add_to_log(f"Combat ended: {reason} (Final State: {self.state.name})")
        logger.info(f"Ending combat. Reason: {reason}. State changed from {previous_state.name} to {self.state.name}")
        for entity in self.entities.values():
            if hasattr(entity, 'remove_status_effect'):
                 entity.remove_status_effect("Defending")
                 entity.remove_status_effect("Surprised")
        self.current_turn_index = 0
        self.round_number = 0
        self.last_action_results = {}
        self._surprise_round_entities = []
        self._is_surprise_round = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entities": {entity_id: entity.to_dict() for entity_id, entity in self.entities.items()},
            "turn_order": self.turn_order,
            "current_turn_index": self.current_turn_index,
            "round_number": self.round_number,
            "state": self.state.name,
            "current_step": self.current_step.name if hasattr(self.current_step, 'name') else str(self.current_step),
            "active_entity_id": self._active_entity_id,
            "player_entity_id": self._player_entity_id,
            "enemy_entity_ids": self._enemy_entity_ids,
            "is_surprise_round": self._is_surprise_round,
            "surprise_round_entities": self._surprise_round_entities,
            "combat_log": self.combat_log,
            "combat_log_html": self.display_log_html,
            "last_action_results": self.last_action_results
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CombatManager':
        manager = cls()
        manager.id = data.get("id", str(uuid.uuid4()))
        manager.entities = {
            entity_id: CombatEntity.from_dict(entity_data)
            for entity_id, entity_data in data.get("entities", {}).items()
        }
        manager.turn_order = data.get("turn_order", [])
        manager.current_turn_index = data.get("current_turn_index", 0)
        manager.round_number = data.get("round_number", 0)
        manager.state = CombatState[data.get("state", "NOT_STARTED")]
        # Restore current step and pointers
        from .enums import CombatStep as _CombatStep
        try:
            manager.current_step = _CombatStep[data.get("current_step", "NOT_STARTED")]
        except Exception:
            manager.current_step = _CombatStep.NOT_STARTED
        manager._active_entity_id = data.get("active_entity_id")
        manager._player_entity_id = data.get("player_entity_id")
        manager._enemy_entity_ids = data.get("enemy_entity_ids", [])
        manager._is_surprise_round = data.get("is_surprise_round", False)
        manager._surprise_round_entities = data.get("surprise_round_entities", [])

        # Logs / HTML snapshot
        manager.combat_log = data.get("combat_log", [])
        manager.display_log_html = data.get("combat_log_html", "")

        manager.last_action_results = data.get("last_action_results", {})
        return manager

    def sync_stats_with_managers_from_entities(self) -> None:
        """Sync StatsManager current values to match saved CombatEntity values.
        Player is always synced. NPCs are synced only if an NPC StatsManager is available.
        """
        for entity_id, combat_entity in self.entities.items():
            try:
                stats_manager = self._get_entity_stats_manager(entity_id, quiet=True)
                if not stats_manager:
                    # Quietly skip if we cannot obtain a stats manager (e.g., NPC without NPCSystem linkage)
                    continue
                # Sync HP/Stamina/Mana current values (best effort)
                try:
                    stats_manager.set_current_stat(DerivedStatType.HEALTH, combat_entity.current_hp)
                except Exception:
                    pass
                try:
                    stats_manager.set_current_stat(DerivedStatType.STAMINA, combat_entity.current_stamina)
                except Exception:
                    pass
                try:
                    stats_manager.set_current_stat(DerivedStatType.MANA, combat_entity.current_mp)
                except Exception:
                    pass
                # Optional: Attempt to reconstruct status effects on the StatsManager
                try:
                    from core.stats.combat_effects import StatusEffect, StatusEffectType
                    if hasattr(stats_manager, 'status_effect_manager'):
                        for eff_name, duration in (combat_entity.status_effects or {}).items():
                            try:
                                se = StatusEffect(name=eff_name, description=eff_name, effect_type=StatusEffectType.DEBUFF, duration=duration)
                                if hasattr(stats_manager, 'add_status_effect'):
                                    stats_manager.add_status_effect(se)
                            except Exception:
                                continue
                except Exception:
                    pass
            except Exception:
                # Never escalate here; this is a best-effort re-sync to avoid noisy logs
                continue

    def _find_entity_by_combat_name(self, combat_name: str) -> Optional[CombatEntity]:
        if not combat_name: return None
        name_lower = combat_name.lower()
        for entity in self.entities.values():
            entity_combat_name = getattr(entity, 'combat_name', None)
            if entity_combat_name and entity_combat_name.lower() == name_lower:
                return entity
        logger.debug(f"Could not find entity with combat_name: '{combat_name}' in current combat.")
        return None
    
    def _generate_combat_loot(self, engine):
        """Generate loot from defeated NPCs and make it available to the player."""
        if self.state != CombatState.PLAYER_VICTORY:
            return  # Only generate loot on player victory
        
        try:
            from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
            
            # Get state manager to access NPCs
            state_manager = engine._state_manager if hasattr(engine, '_state_manager') else None
            if not state_manager or not state_manager.current_state:
                logger.warning("Cannot generate loot: State manager unavailable")
                return
            
            game_state = state_manager.current_state
            available_loot = []
            loot_sources = []
            
            # Check each defeated enemy entity for loot
            for entity_id, entity in self.entities.items():
                if entity.entity_type == EntityType.ENEMY and not entity.is_alive():
                    # Try to get the NPC from the NPC system
                    npc = None
                    if hasattr(game_state, 'npc_system') and game_state.npc_system:
                        npc = game_state.npc_system.get_npc_by_id(entity_id)
                    
                    if npc and hasattr(npc, 'equipment_manager') and npc.equipment_manager:
                        # Extract equipment from defeated NPC
                        npc_loot = self._extract_npc_equipment(npc, entity.combat_name)
                        if npc_loot:
                            available_loot.extend(npc_loot)
                            loot_sources.append(entity.combat_name)
            
            # Store loot in game state for player to collect
            if available_loot:
                if not hasattr(game_state, 'available_loot'):
                    game_state.available_loot = []
                game_state.available_loot.extend(available_loot)
                
                # Generate loot message
                loot_count = len(available_loot)
                source_names = ", ".join(loot_sources)
                loot_message = f"Victory! Found {loot_count} item(s) from defeated enemies: {source_names}. Use 'loot' to examine available items."
                
                # Queue loot notification
                loot_event = DisplayEvent(
                    type=DisplayEventType.SYSTEM_MESSAGE,
                    content=loot_message,
                    target_display=DisplayTarget.COMBAT_LOG,
                    gradual_visual_display=False
                )
                engine._combat_orchestrator.add_event_to_queue(loot_event)
                
                logger.info(f"Generated {loot_count} loot items from {len(loot_sources)} defeated enemies")
            else:
                logger.debug("No loot generated from combat - no equipped items found on defeated enemies")
                
        except Exception as e:
            logger.error(f"Error generating combat loot: {e}", exc_info=True)
    
    def _extract_npc_equipment(self, npc, combat_name: str) -> List[Dict[str, Any]]:
        """Extract equipment from a defeated NPC as loot items."""
        loot_items = []
        
        try:
            if not hasattr(npc, 'equipment_manager') or not npc.equipment_manager:
                return loot_items
            
            # Get all equipped items
            equipped_items = npc.equipment_manager.equipment
            for slot, item in equipped_items.items():
                if item is not None:
                    # Create loot entry
                    from core.inventory.item_serialization import item_to_dict
                    loot_item = {
                        'item_data': item_to_dict(item),
                        'source': combat_name,
                        'source_type': 'defeated_enemy',
                        'slot': slot.value if hasattr(slot, 'value') else str(slot)
                    }
                    loot_items.append(loot_item)
                    logger.debug(f"Added {item.name} to loot from {combat_name}")
            
            # Clear the NPC's equipment (they're defeated)
            if loot_items:
                npc.equipment_manager.unequip_all()
                
        except Exception as e:
            logger.error(f"Error extracting equipment from NPC {combat_name}: {e}", exc_info=True)
        
        return loot_items