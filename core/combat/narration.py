from typing import Dict, Any, Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from core.agents.base_agent import AgentContext
from core.combat.enums import CombatStep
from core.combat.combat_action import ActionType
from core.utils.logging_config import get_logger

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.combat.combat_manager import CombatManager

logger = get_logger(__name__)

class LLMAttemptWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, engine: 'GameEngine', agent_context: AgentContext):
        super().__init__()
        self._engine = engine
        self._agent_context = agent_context

    @Slot()
    def run(self):
        try:
            narrator_output = self._engine._combat_narrator_agent.process(self._agent_context)
            narrative = ""
            if isinstance(narrator_output, dict):
                narrative = narrator_output.get("narrative", "") or ""
            self.finished.emit(narrative)
        except Exception as e:
            logger.exception(f"Error in LLMAttemptWorker: {e}")
            self.error.emit(str(e))


class LLMOutcomeWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, engine: 'GameEngine', action_result: Dict[str, Any], combat_manager: 'CombatManager'):
        super().__init__()
        self._engine = engine
        self._action_result = action_result
        self._combat_manager = combat_manager

    @Slot()
    def run(self):
        try:
            narrative = self._engine._combat_narrator_agent.narrate_outcome(self._action_result, self._combat_manager) or ""
            self.finished.emit(narrative)
        except Exception as e:
            logger.exception(f"Error in LLMOutcomeWorker: {e}")
            self.error.emit(str(e))


class LLMResultBridge(QObject):
    """Runs in the GUI thread; receives worker results and queues display events safely."""
    def __init__(self, engine: 'GameEngine', combat_manager: 'CombatManager'):
        super().__init__()
        self._engine = engine
        self._cm = combat_manager
        # Fields configured by callers per-use
        self._attempt_attacker_id: Optional[str] = None
        self._attempt_default_text: str = ""
        self._outcome_is_surprise: bool = False
        self._outcome_action_result: Dict[str, Any] = {}

    @Slot(str)
    def handle_attempt_finished(self, narrative: str):
        try:
            from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
            
            text = (narrative or self._attempt_default_text or "").strip()
            if not text:
                text = "A swift surprise attack is launched!"
            
            # Append to persistent log
            self._cm.combat_log.append({"role": "gm", "content": text})

            event = DisplayEvent(
                type=DisplayEventType.NARRATIVE_ATTEMPT,
                content=text,
                role="gm",
                tts_eligible=True,
                gradual_visual_display=True,
                target_display=DisplayTarget.COMBAT_LOG,
                source_step=self._cm.current_step.name if hasattr(self._cm.current_step, 'name') else str(self._cm.current_step)
            )
            self._engine._combat_orchestrator.add_event_to_queue(event)
            
            # Logic Access via Flow
            try:
                if self._attempt_attacker_id:
                    self._cm.flow.set_next_actor_step(self._attempt_attacker_id, self._engine)
            except Exception:
                pass
            self._cm.current_step = CombatStep.PERFORMING_SURPRISE_ATTACK
        except Exception as e:
            logger.error(f"Bridge handle_attempt_finished failed: {e}", exc_info=True)

    @Slot(str)
    def handle_attempt_error(self, _err: str):
        self.handle_attempt_finished("")

    def _compute_regular_outcome_next_step(self):
        """Replicates end-of-combat checks."""
        from core.combat.enums import CombatStep, CombatState
        from core.combat.combat_entity import EntityType
        
        end_player_victory = False
        end_player_defeat = False
        try:
            player_id = getattr(self._cm, '_player_entity_id', None)
            if player_id and player_id in self._cm.entities:
                player_entity_obj = self._cm.entities.get(player_id)
                if player_entity_obj and not player_entity_obj.is_alive():
                    end_player_defeat = True
            
            remaining_enemies = [e for e in self._cm.entities.values() 
                                 if getattr(e, 'entity_type', None) == EntityType.ENEMY 
                                 and getattr(e, 'is_active_in_combat', True) 
                                 and e.is_alive()]
            if len(remaining_enemies) == 0:
                end_player_victory = True
        except Exception:
            pass

        if end_player_defeat:
            self._cm.state = CombatState.PLAYER_DEFEAT
            self._cm.current_step = CombatStep.ENDING_COMBAT
        elif end_player_victory:
            self._cm.state = CombatState.PLAYER_VICTORY
            self._cm.current_step = CombatStep.ENDING_COMBAT
        else:
            self._cm.current_step = CombatStep.APPLYING_STATUS_EFFECTS

    @Slot(str)
    def handle_outcome_finished(self, narrative: str):
        try:
            from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
            
            text = (narrative or "").strip()
            if not text:
                # Fallback narrative generation
                result = self._outcome_action_result or {}
                performer_name = result.get("performer_name", "Actor")
                target_name = result.get("target_name", "Target")
                action_name_disp = result.get("action_name", "action")
                damage = result.get("damage", 0)
                success_flag = result.get("success", False)
                action_type = result.get("action_type")

                if self._outcome_is_surprise:
                    if success_flag:
                        text = f"The surprise attack by {performer_name} connects against {target_name}, dealing {damage:.0f} damage."
                        if result.get("target_defeated"):
                            text += f" {target_name} is defeated!"
                    else:
                        text = f"Despite the surprise, {performer_name}'s attack on {target_name} misses!"
                else:
                    if success_flag:
                        if result.get("fled") is True:
                            text = f"{performer_name} successfully flees the battle!"
                        elif action_type == ActionType.DEFEND:
                            text = f"{performer_name} braces defensively."
                        elif action_type == ActionType.WAIT:
                            text = f"{performer_name} chooses to wait and observe the battlefield."
                        elif damage > 0:
                            text = f"The {action_name_disp} from {performer_name} strikes {target_name} for {damage:.0f} damage."
                        else:
                            text = f"{performer_name}'s {action_name_disp} affects {target_name}, but deals no direct damage."
                        if result.get("target_defeated"):
                            text += f" {target_name} is overcome and falls!"
                    else:
                        if result.get("fled") is False:
                            text = f"{performer_name} tries to flee but cannot escape!"
                        else:
                            text = f"{performer_name}'s {action_name_disp} against {target_name} fails utterly."

            self._cm.combat_log.append({"role": "gm", "content": text})
            
            event = DisplayEvent(
                type=DisplayEventType.NARRATIVE_IMPACT,
                content=text,
                role="gm",
                tts_eligible=True,
                gradual_visual_display=True,
                target_display=DisplayTarget.COMBAT_LOG,
                source_step=self._cm.current_step.name if hasattr(self._cm.current_step, 'name') else str(self._cm.current_step)
            )
            self._engine._combat_orchestrator.add_event_to_queue(event)
            
            # Clear pending data
            try:
                if getattr(self._cm, '_pending_action', None) and self._outcome_action_result.get("action_id_for_narration"):
                    if self._cm._pending_action.id == self._outcome_action_result.get("action_id_for_narration"):
                        self._cm._pending_action = None
            except Exception:
                pass

            # Set next step
            if self._outcome_is_surprise:
                self._cm.current_step = CombatStep.ENDING_SURPRISE_ROUND
            else:
                self._compute_regular_outcome_next_step()
            
            self._cm._last_action_result_detail = None
        except Exception as e:
            logger.error(f"Bridge handle_outcome_finished failed: {e}", exc_info=True)

    @Slot(str)
    def handle_outcome_error(self, _err: str):
        self.handle_outcome_finished("")