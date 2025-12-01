import random
import copy
from typing import Optional, TYPE_CHECKING

from PySide6.QtCore import QTimer, QThread, QObject

from core.combat.enums import CombatStep, CombatState
from core.combat.combat_entity import EntityType
from core.combat.combat_action import AttackAction, SpellAction, DefendAction, FleeAction, SurrenderAction, ActionType, CombatAction
from core.stats.stats_base import DerivedStatType
from core.stats.combat_effects import StatusEffect, StatusEffectType
from core.game_flow.npc_interaction import get_npc_intent
from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
from core.combat.narration import LLMAttemptWorker, LLMOutcomeWorker, LLMResultBridge
from core.combat.loot import generate_combat_loot

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.combat.combat_manager import CombatManager
from core.utils.logging_config import get_logger

logger = get_logger(__name__)

class CombatFlow:
    """Handles the state transitions and logic steps of the combat loop."""

    def __init__(self, manager: 'CombatManager'):
        self.manager = manager
        # Keep references to offloaded LLM worker objects
        self._llm_threads = []
        self._llm_workers = []
        self._llm_bridges = []

    def _cleanup_llm_objects(self, thread: QThread, worker: QObject, bridge: QObject) -> None:
        """Remove references to finished LLM thread/worker/bridge objects."""
        try:
            if thread in self._llm_threads: self._llm_threads.remove(thread)
        except Exception: pass
        try:
            if worker in self._llm_workers: self._llm_workers.remove(worker)
        except Exception: pass
        try:
            if bridge in self._llm_bridges: self._llm_bridges.remove(bridge)
        except Exception: pass

    def process_step(self, engine: 'GameEngine'):
        """Processes the current step and triggers the next one."""
        logger.info(f"[FLOW] process_step called. Step: {self.manager.current_step}, Waiting: {self.manager.waiting_for_display_completion}")

        # Guard against inactive manager
        try:
            state_manager = getattr(engine, '_state_manager', None)
            current_state = state_manager.current_state if state_manager else None
            active_cm = getattr(current_state, 'combat_manager', None) if current_state else None
            if active_cm is not self.manager:
                logger.info("CombatFlow invoked on inactive manager. Ignoring.")
                return
        except Exception:
            pass

        max_steps = 20
        steps_processed = 0
        while steps_processed < max_steps:
            steps_processed += 1
            current_step_before = self.manager.current_step

            if self.manager.state != CombatState.IN_PROGRESS and self.manager.current_step not in [CombatStep.ENDING_COMBAT, CombatStep.COMBAT_ENDED]:
                if self.manager.current_step != CombatStep.ENDING_COMBAT:
                    self.manager.current_step = CombatStep.ENDING_COMBAT
                if self.manager.current_step == CombatStep.ENDING_COMBAT:
                    self._step_ending_combat(engine)
                break

            if self.manager.current_step in [CombatStep.AWAITING_PLAYER_INPUT, CombatStep.COMBAT_ENDED, CombatStep.NOT_STARTED, CombatStep.AWAITING_TRANSITION_DATA]:
                break

            if not hasattr(engine, '_combat_orchestrator'):
                logger.critical("CRITICAL: Orchestrator missing. Aborting.")
                self.manager.end_combat("Internal Error")
                self.manager.current_step = CombatStep.COMBAT_ENDED
                break

            try:
                handler = self._get_step_handler(self.manager.current_step)
                if handler:
                    handler(engine)
                    if self.manager.waiting_for_display_completion:
                        break
                elif self.manager.current_step not in [CombatStep.NOT_STARTED, CombatStep.COMBAT_ENDED]:
                    logger.warning(f"No handler for {self.manager.current_step}")
                    break

                if self.manager.current_step == current_step_before and not self.manager.waiting_for_display_completion:
                    logger.error(f"Step {self.manager.current_step.name} did not transition. Breaking loop.")
                    break

            except Exception as e:
                logger.exception(f"Error in step {self.manager.current_step.name}: {e}")
                self.manager.end_combat(f"Error: {e}")
                self.manager.current_step = CombatStep.COMBAT_ENDED
                break

    def _get_step_handler(self, step: CombatStep):
        handlers = {
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
        return handlers.get(step)

    # --- Step Handlers ---

    def _step_starting_combat(self, engine):
        player = self.manager.get_player_entity()
        enemies = [self.manager.entities[eid] for eid in self.manager._enemy_entity_ids if eid in self.manager.entities]
        
        start_msg = f"Combat started! {player.combat_name if player else 'Player'} vs {', '.join(e.combat_name for e in enemies)}"
        self.manager._log_and_dispatch_event(start_msg, DisplayEventType.SYSTEM_MESSAGE, role="system", engine=engine)

        if self.manager._surprise_attack:
            self.manager.current_step = CombatStep.HANDLING_SURPRISE_CHECK
        else:
            self.manager.current_step = CombatStep.ROLLING_INITIATIVE
        
        self.manager.waiting_for_display_completion = True

    def _step_handling_surprise_check(self, engine):
        from core.interaction.context_builder import ContextBuilder
        from core.agents.base_agent import AgentContext

        attacker = self.manager.get_player_entity()
        if not attacker:
            self.manager.current_step = CombatStep.ROLLING_INITIATIVE
            self.manager.waiting_for_display_completion = False
            return

        targets = [self.manager.entities.get(eid) for eid in self.manager._enemy_entity_ids if self.manager.entities.get(eid) and self.manager.entities.get(eid).is_alive()]

        if not targets:
            self.manager.current_step = CombatStep.ENDING_SURPRISE_ROUND
            self.manager.waiting_for_display_completion = False
            return

        surprised_names = []
        for target in targets:
            sm = self.manager._get_entity_stats_manager(target.id)
            if sm:
                sm.add_status_effect(StatusEffect(name="Surprised", description="Caught off guard", effect_type=StatusEffectType.DEBUFF, duration=1))
                target.add_status_effect("Surprised", duration=1)
                surprised_names.append(target.combat_name)

        if not self.manager._is_surprise_round: self.manager._is_surprise_round = True
        self.manager._surprise_round_entities = [attacker.id]

        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content="Round 1 (Surprise Attack!)", target_display=DisplayTarget.COMBAT_LOG))
        
        if surprised_names:
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=f"Targets Surprised: {', '.join(surprised_names)}", target_display=DisplayTarget.COMBAT_LOG))
        
        self.manager._active_entity_id = attacker.id
        self.manager._pending_action = None

        if "attack" in (self.manager._initiating_intent or "").lower() and targets:
            target = targets[0]
            self.manager._pending_action = AttackAction(performer_id=attacker.id, target_id=target.id, weapon_name="surprise attack", dice_notation="1d6")
            
            game_state = engine._state_manager.current_state
            ctx_builder = ContextBuilder()
            ctx = ctx_builder.build_context(game_state, self.manager.game_state.current_mode, actor_id=attacker.id)
            
            narrator_input = f"[System: Surprise Attack] Actor: {attacker.combat_name}, Target: {target.combat_name}. Original Intent: {self.manager._initiating_intent}"
            # Ensure AgentContext fields are valid
            agent_ctx = AgentContext(game_state=ctx, player_state=ctx.get('player', {}), world_state=ctx.get('world', {}), player_input=narrator_input, conversation_history=[], additional_context=ctx)
            
            self.manager.waiting_for_display_completion = True
            try:
                thread = QThread()
                worker = LLMAttemptWorker(engine, agent_ctx)
                worker.moveToThread(thread)
                bridge = LLMResultBridge(engine, self.manager)
                bridge._attempt_attacker_id = attacker.id
                bridge._attempt_default_text = f"{attacker.combat_name} launches a surprise attack on {target.combat_name}!"
                
                self._llm_threads.append(thread)
                self._llm_workers.append(worker)
                self._llm_bridges.append(bridge)
                
                thread.started.connect(worker.run)
                worker.finished.connect(bridge.handle_attempt_finished)
                worker.error.connect(bridge.handle_attempt_error)
                worker.finished.connect(thread.quit)
                worker.finished.connect(worker.deleteLater)
                thread.finished.connect(thread.deleteLater)
                thread.finished.connect(lambda t=thread, w=worker, b=bridge: self._cleanup_llm_objects(t, w, b))
                thread.start()
            except Exception as e:
                logger.error(f"LLM fail: {e}")
                self.set_next_actor_step(attacker.id, engine)
                self.manager.current_step = CombatStep.PERFORMING_SURPRISE_ATTACK
        else:
            self.manager.current_step = CombatStep.ENDING_SURPRISE_ROUND
            self.manager.waiting_for_display_completion = True

    def _step_performing_surprise_attack(self, engine):
        if not self.manager._pending_action:
            self.manager.current_step = CombatStep.ENDING_SURPRISE_ROUND
            self.manager.waiting_for_display_completion = False
            return

        summary = self.manager.perform_action(self.manager._pending_action, engine)
        
        # Ensure fallback message if nothing queued
        if not summary.get("queued_events", False) and not summary.get("success", False):
             fail_msg = self.manager._last_action_result_detail.get("message", "Action failed.")
             engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=fail_msg, target_display=DisplayTarget.COMBAT_LOG))

        self.manager.current_step = CombatStep.NARRATING_SURPRISE_OUTCOME
        self.manager.waiting_for_display_completion = True

    def _step_narrating_surprise_outcome(self, engine):
        if not self.manager._last_action_result_detail:
            self.manager.current_step = CombatStep.ENDING_SURPRISE_ROUND
            self.manager.waiting_for_display_completion = False
            return

        result_copy = copy.deepcopy(self.manager._last_action_result_detail)
        self.manager.waiting_for_display_completion = True
        
        try:
            thread = QThread()
            worker = LLMOutcomeWorker(engine, result_copy, self.manager)
            worker.moveToThread(thread)
            bridge = LLMResultBridge(engine, self.manager)
            bridge._outcome_is_surprise = True
            bridge._outcome_action_result = result_copy
            
            self._llm_threads.append(thread)
            self._llm_workers.append(worker)
            self._llm_bridges.append(bridge)
            
            thread.started.connect(worker.run)
            worker.finished.connect(bridge.handle_outcome_finished)
            worker.error.connect(bridge.handle_outcome_error)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(lambda t=thread, w=worker, b=bridge: self._cleanup_llm_objects(t, w, b))
            thread.start()
        except Exception:
            self.manager._last_action_result_detail = None
            self.manager.current_step = CombatStep.ENDING_SURPRISE_ROUND

    def _step_ending_surprise_round(self, engine):
        self.manager._log_and_dispatch_event("Surprise round ends.", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
        
        for eid, entity in self.manager.entities.items():
            if entity.has_status_effect("Surprised"):
                sm = self.manager._get_entity_stats_manager(eid)
                if sm: sm.status_effect_manager.remove_effects_by_name("Surprised")
                entity.remove_status_effect("Surprised")

        self.manager._surprise_attack = False
        self.manager._is_surprise_round = False
        self.manager.current_step = CombatStep.ROLLING_INITIATIVE
        self.manager.waiting_for_display_completion = True

    def _step_rolling_initiative(self, engine):
        queued = False
        if not self.manager.turn_order:
            init_vals = []
            for eid, entity in self.manager.entities.items():
                if not entity.is_alive() or not getattr(entity, 'is_active_in_combat', True): continue
                # Use StatsManager based logic from CombatManager._get_entity_stats_manager for initiative if possible
                sm = self.manager._get_entity_stats_manager(eid, quiet=True)
                base = sm.get_stat_value(DerivedStatType.INITIATIVE) if sm else entity.get_stat(DerivedStatType.INITIATIVE)
                
                roll = random.randint(1, 6)
                total = base + roll
                entity.initiative = total
                init_vals.append((eid, total))
                msg = f"{entity.combat_name} rolls initiative: {total:.0f} (Base:{base:.0f} + Roll:{roll})"
                self.manager._log_and_dispatch_event(msg, DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                
                # AP Bonus
                if self.manager._ap_config.get("enabled", False) and total > 15:
                    bonus = self.manager._ap_config.get("initiative_bonus_ap", 2.0)
                    self.manager.ap_pool[eid] = self.manager.ap_pool.get(eid, 0.0) + bonus
                    self.manager._log_and_dispatch_event(f"{entity.combat_name} gets initiative bonus of {bonus} AP!", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                queued = True
            
            init_vals.sort(key=lambda x: x[1], reverse=True)
            self.manager.turn_order = [eid for eid, _ in init_vals]
            self.manager.current_turn_index = 0
        
        self.manager.round_number = 0
        self.manager.current_turn_index = -1
        self.manager.current_step = CombatStep.STARTING_ROUND
        self.manager.waiting_for_display_completion = queued

    def _step_starting_round(self, engine):
        self.manager.round_number += 1
        self.manager._log_and_dispatch_event(f"Round {self.manager.round_number} begins!", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
        
        active_ids = [eid for eid in self.manager.turn_order if eid in self.manager.entities and self.manager.entities[eid].is_alive() and getattr(self.manager.entities[eid], 'is_active_in_combat', True)]
        
        if not active_ids:
            self.manager.end_combat("No active combatants.")
            self.manager.current_step = CombatStep.ENDING_COMBAT
            self.manager.waiting_for_display_completion = True
            return

        turn_str = "Turn order: " + ", ".join(self.manager.entities[eid].combat_name for eid in active_ids)
        self.manager._log_and_dispatch_event(turn_str, DisplayEventType.SYSTEM_MESSAGE, engine=engine)

        first_id = active_ids[0]
        self.manager.current_turn_index = self.manager.turn_order.index(first_id)
        self.manager._active_entity_id = first_id

        # AP Regen
        if self.manager._ap_config.get("enabled", False):
            sm = self.manager._get_entity_stats_manager(first_id)
            if sm:
                regen = sm.get_stat_value(DerivedStatType.AP_REGENERATION)
                max_ap = sm.get_stat_value(DerivedStatType.MAX_AP)
                cur = self.manager.ap_pool.get(first_id, 0.0)
                new_ap = min(max_ap, cur + regen)
                self.manager.ap_pool[first_id] = new_ap
                self.manager._log_and_dispatch_event(f"{self.manager.entities[first_id].combat_name} regenerates {regen:.0f} AP.", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.AP_UPDATE, content={}, metadata={"entity_id": first_id, "current_ap": new_ap, "max_ap": max_ap}, target_display=DisplayTarget.MAIN_GAME_OUTPUT))

        self.manager._log_and_dispatch_event(f"It is now {self.manager.entities[first_id].combat_name}'s turn.", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
        self.set_next_actor_step(first_id, engine)
        self.manager.waiting_for_display_completion = True

    def _step_processing_player_action(self, engine):
        from core.interaction.context_builder import ContextBuilder
        from core.agents.base_agent import AgentContext
        from core.game_flow.mode_transitions import _handle_transition_request

        if not self.manager._current_intent:
            self.manager.current_step = CombatStep.AWAITING_PLAYER_INPUT
            self.manager.waiting_for_display_completion = False
            return

        player_id = self.manager._player_entity_id
        player = self.manager.entities.get(player_id)
        
        # --- FIX: Pre-identify Deterministic Actions ---
        # This ensures button clicks like 'Wait', 'Defend' work even if LLM returns no requests.
        intent_lower = self.manager._current_intent.lower().strip()
        deterministic_action = None
        
        if intent_lower == "wait":
            deterministic_action = CombatAction(action_type=ActionType.WAIT, performer_id=player_id, name="Wait")
        elif intent_lower == "defend":
            deterministic_action = DefendAction(performer_id=player_id)
        elif intent_lower == "flee":
            deterministic_action = FleeAction(performer_id=player_id)
        elif intent_lower == "surrender":
            deterministic_action = SurrenderAction(performer_id=player_id)
        # -----------------------------------------------

        ctx_builder = ContextBuilder()
        ctx = ctx_builder.build_context(self.manager.game_state, self.manager.game_state.current_mode, actor_id=player_id)
        
        try:
            from core.magic.spell_catalog import get_spell_catalog
            cat = get_spell_catalog()
            known = getattr(self.manager.game_state.player, 'known_spells', [])
            hints = []
            for sid in known:
                sp = cat.get_spell_by_id(sid)
                if sp: hints.append({'id': sp.id, 'name': sp.name})
            if hints: ctx['player_known_spells_hint'] = hints
        except Exception: pass

        agent_ctx = AgentContext(game_state=ctx, player_state=ctx.get('player', {}), world_state=ctx.get('world', {}), player_input=self.manager._current_intent, conversation_history=[], additional_context=ctx)
        
        # Pre-validation (RuleChecker)
        if not deterministic_action and hasattr(engine, '_rule_checker') and engine._rule_checker:
            valid, reason = engine._rule_checker.validate_action(agent_ctx)
            if not valid and reason and "unspecified" not in reason.lower():
                self.manager._log_and_dispatch_event(f"Action blocked: {reason}", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                self.manager.current_step = CombatStep.AWAITING_PLAYER_INPUT
                self.manager.waiting_for_display_completion = True
                self.manager._current_intent = None
                return

        agent_out = engine._combat_narrator_agent.process(agent_ctx)
        
        narrative = ""
        reqs = []
        if agent_out:
            narrative = agent_out.get("narrative", "")
            reqs = agent_out.get("requests", [])
        
        # Display Narrative
        if narrative:
            self.manager._log_and_dispatch_event(narrative, DisplayEventType.NARRATIVE_ATTEMPT, role="gm", gradual=True, engine=engine)
        elif not agent_out and not deterministic_action:
            self.manager._log_and_dispatch_event("[System Error] Could not interpret action.", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
            self.manager.current_step = CombatStep.AWAITING_PLAYER_INPUT
            self.manager.waiting_for_display_completion = True
            return

        # Determine Action to Perform
        if deterministic_action:
            self.manager._pending_action = deterministic_action
            self.manager.current_step = CombatStep.RESOLVING_ACTION_MECHANICS
        elif reqs:
            req = reqs[0]
            # Bridge Logic for Defend
            if req.get("action") == "request_state_change":
                val = str(req.get("value", "")).upper()
                attr = str(req.get("attribute", "")).lower()
                if val == "DEFENDING" or (attr == "add_status_effect" and "defend" in val.lower()):
                    req["skill_name"] = "DEFEND"

            if req.get("action") == "request_mode_transition":
                _handle_transition_request(engine, self.manager.game_state, req, player_id)
                if self.manager.game_state.current_mode != self.manager.game_state.current_mode.COMBAT:
                    self.manager.current_step = CombatStep.ENDING_COMBAT
                else:
                    self.manager.current_step = CombatStep.APPLYING_STATUS_EFFECTS
                self.manager._current_intent = None
                self.manager.waiting_for_display_completion = True
                return
            else:
                action = self._convert_request_to_action(req, player_id, self.manager._current_intent)
                if action:
                    self.manager._pending_action = action
                    self.manager.current_step = CombatStep.RESOLVING_ACTION_MECHANICS
                else:
                    self.manager._log_and_dispatch_event("Action could not be formed from intent.", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                    self.manager.current_step = CombatStep.AWAITING_PLAYER_INPUT
        else:
            # No requests and not deterministic
            self.manager._log_and_dispatch_event(f"{player.combat_name} considers options but acts not.", DisplayEventType.NARRATIVE_GENERAL, role="gm", engine=engine)
            self.manager.current_step = CombatStep.APPLYING_STATUS_EFFECTS

        self.manager._current_intent = None
        self.manager.waiting_for_display_completion = True

    def _step_awaiting_npc_intent(self, engine):
        npc_id = self.manager._active_entity_id
        if not npc_id:
            self.manager.current_step = CombatStep.ADVANCING_TURN
            self.manager.waiting_for_display_completion = False
            QTimer.singleShot(0, lambda: self.manager.process_combat_step(engine))
            return

        intent = get_npc_intent(engine, self.manager.game_state, npc_id)
        if intent:
            self.manager._current_intent = intent
            self.manager.current_step = CombatStep.PROCESSING_NPC_ACTION
        else:
            self.manager._current_intent = "Falter"
            self.manager.current_step = CombatStep.PROCESSING_NPC_ACTION
        
        self.manager.waiting_for_display_completion = False
        if not engine._combat_orchestrator.event_queue:
            QTimer.singleShot(0, lambda: self.manager.process_combat_step(engine))

    def _step_processing_npc_action(self, engine):
        from core.interaction.context_builder import ContextBuilder
        from core.agents.base_agent import AgentContext
        
        npc_id = self.manager._active_entity_id
        npc = self.manager.entities.get(npc_id)
        
        ctx_builder = ContextBuilder()
        ctx = ctx_builder.build_context(self.manager.game_state, self.manager.game_state.current_mode, actor_id=npc_id)
        agent_ctx = AgentContext(game_state=ctx, player_state=ctx.get('player'), world_state=ctx.get('world'), player_input=self.manager._current_intent, conversation_history=[], additional_context=ctx)
        
        agent_out = engine._combat_narrator_agent.process(agent_ctx)
        
        if not agent_out or "narrative" not in agent_out:
            # Fallback
            self.manager._log_and_dispatch_event(f"{npc.combat_name} lashes out wildly!", DisplayEventType.NARRATIVE_ATTEMPT, role="gm", engine=engine)
            target = next((e for e in self.manager.entities.values() if e.entity_type == EntityType.PLAYER and e.is_alive()), None)
            if target:
                self.manager._pending_action = AttackAction(performer_id=npc_id, target_id=target.id, weapon_name="fallback attack")
                self.manager.current_step = CombatStep.RESOLVING_ACTION_MECHANICS
            else:
                self.manager.current_step = CombatStep.APPLYING_STATUS_EFFECTS
        else:
            narrative = agent_out.get("narrative", "")
            if narrative: self.manager._log_and_dispatch_event(narrative, DisplayEventType.NARRATIVE_ATTEMPT, role="gm", gradual=True, engine=engine)
            
            reqs = agent_out.get("requests", [])
            if reqs:
                action = self._convert_request_to_action(reqs[0], npc_id, self.manager._current_intent)
                
                # --- FIX: Enforce NPC AP Affordability ---
                # If the LLM chose an action the NPC cannot afford, force a Wait.
                if action and self.manager._ap_config.get("enabled", False):
                    action_costs = self.manager._ap_config.get("action_costs", {})
                    type_key = action.action_type.name.lower()
                    cost = action_costs.get(type_key, 0.0)
                    current_ap = self.manager.ap_pool.get(npc_id, 0.0)
                    
                    if current_ap < cost:
                        logger.info(f"NPC {npc.combat_name} chose {action.name} (Cost {cost}) but has {current_ap} AP. Forcing WAIT.")
                        action = CombatAction(action_type=ActionType.WAIT, performer_id=npc_id, name="Wait (Low AP)")
                # -----------------------------------------

                if action:
                    self.manager._pending_action = action
                    self.manager.current_step = CombatStep.RESOLVING_ACTION_MECHANICS
                else:
                    self.manager.current_step = CombatStep.APPLYING_STATUS_EFFECTS
            else:
                self.manager.current_step = CombatStep.APPLYING_STATUS_EFFECTS

        self.manager._current_intent = None
        self.manager.waiting_for_display_completion = True

    def _step_resolving_action_mechanics(self, engine):
        if not self.manager._pending_action:
            self.manager.current_step = CombatStep.APPLYING_STATUS_EFFECTS
            self.manager.waiting_for_display_completion = False
            return

        summary = self.manager.perform_action(self.manager._pending_action, engine)
        
        # Check if events were actually queued to determine if we should wait
        queued_events = summary.get("queued_events", False)
        success = summary.get("success", False)
        
        # Handle explicit failure that wasn't already queued
        if not queued_events and not success:
             if self.manager._last_action_result_detail:
                 fail_msg = self.manager._last_action_result_detail.get("message", "Action failed.")
             else:
                 fail_msg = summary.get("message", "Action failed (Internal Error).")
                 
             # Queue the failure message
             engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.SYSTEM_MESSAGE, content=fail_msg, target_display=DisplayTarget.COMBAT_LOG))
             queued_events = True 

        self.manager.current_step = CombatStep.NARRATING_ACTION_OUTCOME
        
        # CRITICAL FIX: Only pause the flow if visual events were actually queued.
        # For 'Wait' (where queued_events is False), we proceed immediately to the narration step.
        # This prevents the stall where the engine waits for a signal from the Orchestrator that never comes.
        self.manager.waiting_for_display_completion = queued_events

    def _step_narrating_action_outcome(self, engine):
        if not self.manager._last_action_result_detail:
            self.manager.current_step = CombatStep.APPLYING_STATUS_EFFECTS
            self.manager.waiting_for_display_completion = False
            return

        result_copy = copy.deepcopy(self.manager._last_action_result_detail)
        self.manager.waiting_for_display_completion = True
        
        try:
            thread = QThread()
            worker = LLMOutcomeWorker(engine, result_copy, self.manager)
            worker.moveToThread(thread)
            bridge = LLMResultBridge(engine, self.manager)
            bridge._outcome_is_surprise = False
            bridge._outcome_action_result = result_copy
            
            self._llm_threads.append(thread)
            self._llm_workers.append(worker)
            self._llm_bridges.append(bridge)
            
            thread.started.connect(worker.run)
            worker.finished.connect(bridge.handle_outcome_finished)
            worker.error.connect(bridge.handle_outcome_error)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(lambda t=thread, w=worker, b=bridge: self._cleanup_llm_objects(t, w, b))
            thread.start()
        except Exception:
            self.manager._last_action_result_detail = None
            self.manager.current_step = CombatStep.APPLYING_STATUS_EFFECTS

    def _step_applying_status_effects(self, engine):
        entity = self.manager.entities.get(self.manager._active_entity_id)
        if not entity:
            self.manager.current_step = CombatStep.ADVANCING_TURN
            self.manager.waiting_for_display_completion = False
            return

        sm = self.manager._get_entity_stats_manager(entity.id)
        queued = False
        
        if sm:
            # DOT/HOT
            for seff in list(sm.status_effect_manager.active_effects.values()):
                cd = getattr(seff, 'custom_data', {}) or {}
                tick_dmg = float(cd.get('damage_per_turn', 0) or 0)
                tick_heal = float(cd.get('heal_per_turn', 0) or 0)
                
                if tick_heal > 0:
                    hp = sm.get_current_stat_value(DerivedStatType.HEALTH)
                    max_hp = entity.max_hp
                    new_hp = min(max_hp, hp + tick_heal)
                    if new_hp > hp:
                        sm.set_current_stat(DerivedStatType.HEALTH, new_hp)
                        entity.set_current_hp(new_hp)
                        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={}, metadata={"entity_id": entity.id, "bar_type": "hp", "final_new_value": new_hp, "max_value": max_hp}))
                        self.manager._log_and_dispatch_event(f"{entity.combat_name} heals {tick_heal:.0f} from {seff.name}.", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                        queued = True
                
                if tick_dmg > 0:
                    hp = sm.get_current_stat_value(DerivedStatType.HEALTH)
                    max_hp = entity.max_hp
                    # Simplified absorb logic here for brevity, real implementation in StatsManager
                    new_hp = max(0, hp - tick_dmg)
                    if new_hp < hp:
                        sm.set_current_stat(DerivedStatType.HEALTH, new_hp)
                        entity.set_current_hp(new_hp)
                        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={}, metadata={"entity_id": entity.id, "bar_type": "hp", "final_new_value": new_hp, "max_value": max_hp}))
                        self.manager._log_and_dispatch_event(f"{entity.combat_name} takes {tick_dmg:.0f} dmg from {seff.name}.", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                        queued = True
                        if new_hp <= 0: entity.is_active_in_combat = False

            # Stamina Regen
            regen, msg = sm.regenerate_combat_stamina()
            if regen > 0:
                engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={}, metadata={"entity_id": entity.id, "bar_type": "stamina", "final_new_value": sm.get_current_stat_value(DerivedStatType.STAMINA), "max_value": sm.get_stat_value(DerivedStatType.MAX_STAMINA)}))
                self.manager._log_and_dispatch_event(msg, DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                queued = True

            # Expirations
            expired = sm.status_effect_manager.update_durations(timing_filter="end_turn")
            for eid in expired:
                self.manager._log_and_dispatch_event(f"Effect expired on {entity.combat_name}", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                queued = True

        # Legacy Expirations
        legacy_expired = entity.decrement_status_effect_durations(exclude_effects=["Defending"])
        if legacy_expired:
            self.manager._log_and_dispatch_event(f"Effects expired: {', '.join(legacy_expired)}", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
            queued = True

        self.manager.current_step = CombatStep.ADVANCING_TURN
        self.manager.waiting_for_display_completion = queued

    def _step_advancing_turn(self, engine):
        # --- FIX: Multi-Action Logic with Strict Restrictions ---
        allow_multi_action = False
        
        if self.manager._ap_config.get("enabled", False):
            # 1. Check if previous action Failed
            last_result = self.manager._last_action_result_detail or {}
            if not last_result.get("success", True): # If success is False
                 logger.info("Turn ending because last action failed.")
                 allow_multi_action = False
            else:
                # 2. Check if previous action was Turn-Ending
                last_type = self.manager._last_performed_action_type
                TURN_ENDING_TYPES = [ActionType.DEFEND, ActionType.FLEE, ActionType.SURRENDER, ActionType.WAIT]
                
                if last_type in TURN_ENDING_TYPES:
                    logger.info(f"Turn ending forced by action type: {last_type}")
                    allow_multi_action = False
                else:
                    # 3. Check remaining AP
                    aid = self.manager._active_entity_id
                    current_ap = self.manager.ap_pool.get(aid, 0.0)
                    min_cost = self.manager._ap_config.get("min_ap_for_action", 1.0)
                    
                    if aid and current_ap >= min_cost:
                        allow_multi_action = True
                        self.manager._log_and_dispatch_event(f"{self.manager.entities[aid].combat_name} has AP for another action.", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                        self.set_next_actor_step(aid, engine)
        
        self.manager._last_performed_action_type = None
        
        if allow_multi_action:
            return
        # ----------------------------------------------------------

        if self.manager._check_combat_state():
            self.manager.current_step = CombatStep.ENDING_COMBAT
            return

        self.manager._last_action_result_detail = None
        next_id = self.manager._advance_turn()
        
        if self.manager.state != CombatState.IN_PROGRESS:
            self.manager.current_step = CombatStep.ENDING_COMBAT
            self.manager.waiting_for_display_completion = False
            return

        if next_id:
            if self.manager._ap_config.get("enabled", False):
                sm = self.manager._get_entity_stats_manager(next_id)
                if sm:
                    regen = sm.get_stat_value(DerivedStatType.AP_REGENERATION)
                    max_ap = sm.get_stat_value(DerivedStatType.MAX_AP)
                    cur = self.manager.ap_pool.get(next_id, 0.0)
                    new_ap = min(max_ap, cur + regen)
                    self.manager.ap_pool[next_id] = new_ap
                    
                    if self.manager.entities[next_id].entity_type == EntityType.PLAYER:
                        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.AP_UPDATE, content={}, metadata={"entity_id": next_id, "current_ap": new_ap, "max_ap": max_ap}, target_display=DisplayTarget.MAIN_GAME_OUTPUT))

            self.manager._log_and_dispatch_event(f"It is now {self.manager.entities[next_id].combat_name}'s turn.", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
            self.set_next_actor_step(next_id, engine)
            self.manager.waiting_for_display_completion = True
        else:
            pass

    def _step_ending_combat(self, engine):
        # Cleanup
        for e in self.manager.entities.values():
            if hasattr(e, 'remove_status_effect'):
                e.remove_status_effect("Defending")
                e.remove_status_effect("Advantage")
                e.remove_status_effect("Surprised")
        
        generate_combat_loot(self.manager, engine)
        
        self.manager._log_and_dispatch_event(f"--- Combat Concluded ({self.manager.state.name}) ---", DisplayEventType.SYSTEM_MESSAGE, gradual=False, engine=engine)
        self.manager.current_step = CombatStep.COMBAT_ENDED
        self.manager.waiting_for_display_completion = True

    # --- Helpers ---

    def set_next_actor_step(self, entity_id: str, engine):
        entity = self.manager.entities.get(entity_id)
        if not entity:
            self.manager.current_step = CombatStep.ADVANCING_TURN
            return

        # Start-of-turn ticks (Defending, etc)
        def_dur = entity.get_status_effect_duration("Defending")
        if def_dur is not None:
            new_dur = def_dur - 1
            if new_dur <= 0:
                entity.remove_status_effect("Defending")
                self.manager._log_and_dispatch_event(f"Defending worn off {entity.combat_name}", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
            else:
                entity.add_status_effect("Defending", new_dur)

        # Update UI Turn Order
        to_list = []
        for eid in self.manager.turn_order:
            e = self.manager.entities.get(eid)
            p = "→ " if eid == entity_id else "  "
            if e and e.is_alive(): to_list.append(f"{p}{e.combat_name}")
            elif e: to_list.append(f"  [{e.combat_name} - Dead]")
        
        engine._combat_orchestrator.add_event_to_queue(DisplayEvent(type=DisplayEventType.TURN_ORDER_UPDATE, content={"turn_order_display_list": to_list, "active_entity_combat_name": entity.combat_name, "round_number": self.manager.round_number}, target_display=DisplayTarget.MAIN_GAME_OUTPUT))

        # Status check
        if entity.has_status_effect("Stunned") or entity.has_status_effect("Immobilized") or entity.has_status_effect("Asleep"):
            self.manager._log_and_dispatch_event(f"{entity.combat_name} cannot act (Stunned/Immobilized).", DisplayEventType.SYSTEM_MESSAGE, engine=engine)
            self.manager.current_step = CombatStep.APPLYING_STATUS_EFFECTS
            return

        if entity.entity_type == EntityType.PLAYER:
            self.manager.current_step = CombatStep.AWAITING_PLAYER_INPUT
        else:
            self.manager.current_step = CombatStep.AWAITING_NPC_INTENT

    def _convert_request_to_action(self, req: dict, actor_id: str, intent: str) -> Optional[CombatAction]:
        """Helper to convert JSON request to CombatAction."""
        try:
            skill = (req.get("skill_name") or "").upper().replace(" ", "_")
            target_name = req.get("target_actor_id")
            target_id = None
            if target_name:
                t = self.manager._find_entity_by_combat_name(target_name)
                if t: target_id = t.id
            
            # --- FIX: Robust Friendly Fire Prevention for Enemies ---
            if actor_id in self.manager._enemy_entity_ids:
                # List of skills considered attacks that shouldn't hit allies
                attack_skills = ["ATTACK", "MELEE_ATTACK", "RANGED_ATTACK", "UNARMED_ATTACK", "SPELL_ATTACK"]
                
                is_attack = skill in attack_skills
                
                # Condition 1: Targeting Self or Ally
                if is_attack and target_id in self.manager._enemy_entity_ids:
                    logger.info(f"Redirecting Enemy {actor_id} friendly fire (Target: {target_id}) to Player.")
                    target_id = self.manager._player_entity_id
                
                # Condition 2: Targeting None/Unknown (Hallucination)
                if is_attack and target_id is None:
                    logger.info(f"Enemy {actor_id} targeted invalid entity ('{target_name}'). Defaulting to Player.")
                    target_id = self.manager._player_entity_id
            # --------------------------------------------------------

            if skill in ["MELEE_ATTACK", "RANGED_ATTACK", "UNARMED_ATTACK"]:
                return AttackAction(performer_id=actor_id, target_id=target_id, weapon_name=skill, dice_notation=req.get("dice_notation", "1d6"))
            elif skill == "SPELL_ATTACK" or req.get("action") == "request_skill_check" and "spell" in (req.get("context") or "").lower():
                return SpellAction(performer_id=actor_id, spell_name=req.get("skill_name", "Spell"), target_ids=[target_id] if target_id else [], cost_mp=5.0, dice_notation=req.get("dice_notation", "1d6"))
            elif skill == "DEFEND":
                return DefendAction(performer_id=actor_id)
            elif skill == "FLEE":
                return FleeAction(performer_id=actor_id)
            elif skill == "SURRENDER":
                return SurrenderAction(performer_id=actor_id)
            elif skill == "USE_ITEM":
                return CombatAction(action_type=ActionType.ITEM, performer_id=actor_id, name="Use Item", targets=[target_id] if target_id else [actor_id], special_effects={"item_id": req.get("item_id", "unknown")})
            
            # --- FIX: Handle WAIT explicitly ---
            elif skill == "WAIT":
                return CombatAction(action_type=ActionType.WAIT, performer_id=actor_id, name="Wait")
            # -----------------------------------

            # Fallback for generic attack
            if target_id:
                return AttackAction(performer_id=actor_id, target_id=target_id, weapon_name="Attack")
                
        except Exception as e:
            logger.error(f"Action conversion failed: {e}")
        return None