import logging
import uuid
import random
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_action import CombatAction, ActionType
from core.combat.enums import CombatState, CombatStep
from core.stats.stats_base import DerivedStatType
from core.base.state.state_manager import get_state_manager
from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
from core.combat.flow import CombatFlow

if TYPE_CHECKING:
    from core.base.engine import GameEngine
    from core.orchestration.combat_orchestrator import CombatOutputOrchestrator
    from core.stats.stats_manager import StatsManager

logger = logging.getLogger(__name__)

class CombatManager:
    """
    Central facade for the combat system.
    Manages state (Entities, Turn Order) and delegates logic to CombatFlow.
    """
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.entities: Dict[str, CombatEntity] = {}
        self.turn_order: List[str] = []
        self.current_turn_index: int = 0
        self.round_number: int = 0
        self.state: CombatState = CombatState.NOT_STARTED 
        self.current_step: CombatStep = CombatStep.NOT_STARTED 
        self.combat_log: List[Dict[str, str]] = [] 
        self.display_log_html: str = "" 
        self.last_action_results: Dict[str, Any] = {} 
        self.game_state = None 
        self._orchestrator: Optional['CombatOutputOrchestrator'] = None

        # Cache for StatsManagers of dynamic entities not found in NPCSystem
        self._stats_manager_cache: Dict[str, 'StatsManager'] = {}

        # Combat Flow Flags
        self._player_entity_id: Optional[str] = None
        self._enemy_entity_ids: List[str] = []
        self._surprise_attack: bool = False
        self._is_surprise_round: bool = False 
        self._initiating_intent: Optional[str] = None
        self._pending_action: Optional[CombatAction] = None
        self._last_action_result_detail: Optional[Dict] = None 
        self._current_intent: Optional[str] = None
        self._last_performed_action_type: Optional[ActionType] = None
        self._active_entity_id: Optional[str] = None 
        self._surprise_round_entities: List[str] = [] 
        self._player_surrendered: bool = False
        self.player_fled_combat: bool = False

        # Control Flags
        self.waiting_for_display_completion: bool = False
        
        # AP System
        self.ap_pool: Dict[str, float] = {}
        self._ap_config: Dict[str, Any] = {}

        # Initialize Logic Flow Delegate
        self.flow = CombatFlow(self)

        # Load Configuration
        try:
            from core.utils.json_utils import load_json
            combat_config = load_json("config/combat/combat_config.json")
            self._ap_config = combat_config.get("ap_system", {})
        except Exception:
            self._ap_config = {}

    def set_orchestrator(self, orchestrator: 'CombatOutputOrchestrator'):
        self._orchestrator = orchestrator

    def start_combat(self, player_entity: CombatEntity, enemy_entities: List[CombatEntity]) -> None:
        """Initialize combat state with provided entities."""
        self.entities = {player_entity.id: player_entity}
        self.turn_order = []
        self._enemy_entity_ids = []
        self._player_entity_id = player_entity.id
        
        for enemy in enemy_entities:
            self.entities[enemy.id] = enemy
            self._enemy_entity_ids.append(enemy.id)

        # Initiative Roll
        init_vals = []
        for eid, e in self.entities.items():
            # Ensure StatsManager is synced for initiative if possible, else use entity snapshot
            sm = self._get_entity_stats_manager(eid, quiet=True)
            if sm:
                base = sm.get_stat_value(DerivedStatType.INITIATIVE)
            else:
                base = e.get_stat(DerivedStatType.INITIATIVE)
                
            val = base + random.randint(1, 6)
            e.initiative = val
            init_vals.append((eid, val))
            
        init_vals.sort(key=lambda x: x[1], reverse=True)
        self.turn_order = [x[0] for x in init_vals]

        self.state = CombatState.IN_PROGRESS
        self.round_number = 1
        
        # Initialize AP for all participants
        if self._ap_config.get("enabled", False):
            base_ap = self._ap_config.get("base_ap", 4.0)
            for eid in self.entities:
                self.ap_pool[eid] = float(base_ap)

    def prepare_for_combat(self, engine, player_entity, enemy_entities, surprise, initiating_intent):
        """Setup called by Engine/Transitions."""
        self.game_state = engine.state_manager.current_state
        self.start_combat(player_entity, enemy_entities)
        self._surprise_attack = surprise
        self._initiating_intent = initiating_intent
        self.current_step = CombatStep.STARTING_COMBAT

    def process_combat_step(self, engine):
        """Delegates processing to the Flow logic."""
        self.flow.process_step(engine)

    def receive_player_action(self, engine, intent: str):
        if self.current_step != CombatStep.AWAITING_PLAYER_INPUT: return
        self._current_intent = intent
        self.current_step = CombatStep.PROCESSING_PLAYER_ACTION
        self.process_combat_step(engine)

    def register_stats_manager(self, entity_id: str, stats_manager: 'StatsManager'):
        """Explicitly register a StatsManager for an entity (used for dynamic NPCs)."""
        self._stats_manager_cache[entity_id] = stats_manager

    def _calculate_stamina_cost(self, action: CombatAction, performer: CombatEntity) -> float:
        """Calculates stamina cost based on action type, stats, and encumbrance."""
        from core.stats.derived_stats import get_modifier_from_stat
        from core.stats.stats_base import StatType, DerivedStatType
        
        # Base costs
        base_cost = action.cost_stamina
        if base_cost == 0:
            if action.action_type == ActionType.ATTACK: base_cost = 5.0
            elif action.action_type == ActionType.SPELL: base_cost = 2.0
            elif action.action_type == ActionType.DEFEND: base_cost = 2.0
            elif action.action_type == ActionType.FLEE: base_cost = 10.0
            elif action.action_type == ActionType.ITEM: base_cost = 0.0
        
        # Stat modifiers (Constitution reduces cost)
        sm = self._get_entity_stats_manager(performer.id, quiet=True)
        if sm:
            con = sm.get_stat_value(StatType.CONSTITUTION)
            mod = get_modifier_from_stat(con)
            # Reduce cost by modifier, min 1.0 for strenuous actions
            base_cost = max(1.0 if base_cost > 0 else 0.0, base_cost - (mod * 0.5))
        
        # Status Multipliers
        if performer.has_status_effect("Fatigued"): base_cost *= 1.5
        if performer.has_status_effect("Energized"): base_cost *= 0.75

        return round(base_cost, 1)

    def perform_action(self, action: CombatAction, engine=None) -> Dict[str, Any]:
        """
        Executes action mechanics via handlers.
        Handles AP deduction, Stamina calculation, and StatsManager lookup.
        """
        from core.combat.action_handlers import (
            _handle_attack_action, _handle_spell_action, _handle_defend_action,
            _handle_item_action, _handle_flee_action_mechanics, _handle_surrender_action_mechanics
        )
        
        # --- FIX: Store Action Type persistently for flow logic ---
        self._last_performed_action_type = action.action_type
        
        if not engine: 
            return {"success": False, "message": "Internal Error: No Engine provided to perform_action"}
        
        performer = self.entities.get(action.performer_id)
        if not performer: 
            return {"success": False, "message": f"Internal Error: Performer {action.performer_id} not found"}
        
        sm = self._get_entity_stats_manager(performer.id)
        if not sm: 
            return {"success": False, "message": f"Internal Error: StatsManager missing for {performer.combat_name}"}

        # --- 1. Stamina Calculation (Restored) ---
        stamina_cost = self._calculate_stamina_cost(action, performer)
        
        self._last_action_result_detail = {
            "performer_id": performer.id, 
            "performer_name": performer.combat_name,
            "action_name": action.name, 
            "action_id_for_narration": action.id,
            "action_type": action.action_type,
            "stamina_spent": stamina_cost, # Passed to handler
            "mana_spent": action.cost_mp    # Passed to handler
        }
        
        if action.targets:
            t = self.entities.get(action.targets[0])
            if t: self._last_action_result_detail["target_name"] = t.combat_name

        # --- 2. AP Deduction Logic ---
        SKIP_AP_CHECK_TYPES = [ActionType.WAIT, ActionType.DEFEND, ActionType.FLEE, ActionType.SURRENDER]
        
        if self._ap_config.get("enabled", False) and action.action_type not in SKIP_AP_CHECK_TYPES:
            action_costs = self._ap_config.get("action_costs", {})
            type_key = action.action_type.name.lower()
            ap_cost = action_costs.get(type_key, 0.0)
            
            current_ap = self.ap_pool.get(performer.id, 0.0)
            
            if current_ap < ap_cost:
                msg = f"Not enough AP. Need {ap_cost}, have {current_ap:.1f}."
                self._log_and_dispatch_event(msg, DisplayEventType.SYSTEM_MESSAGE, engine=engine)
                return {"success": False, "message": msg, "queued_events": True}
            
            self.ap_pool[performer.id] = max(0.0, current_ap - ap_cost)
            self._queue_ap_update(performer.id, engine)

        # --- 3. Execute Specific Handler ---
        handler = None
        if action.action_type == ActionType.ATTACK: handler = _handle_attack_action
        elif action.action_type == ActionType.SPELL: handler = _handle_spell_action
        elif action.action_type == ActionType.DEFEND: handler = _handle_defend_action
        elif action.action_type == ActionType.ITEM: handler = _handle_item_action
        elif action.action_type == ActionType.FLEE: handler = _handle_flee_action_mechanics
        elif action.action_type == ActionType.SURRENDER: handler = _handle_surrender_action_mechanics
        elif action.action_type == ActionType.WAIT:
            # Modified: Do NOT queue any system message here to avoid redundancy.
            # We explicitly mark success in _last_action_result_detail so the Outcome Narrator knows it succeeded.
            if self._last_action_result_detail:
                self._last_action_result_detail["success"] = True

            # Return success with queued_events=False. 
            # This signals the Flow logic (in flow.py) NOT to wait for display completion, avoiding the stall.
            return {"success": True, "message": "Wait action performed.", "queued_events": False}

        if handler:
            # Handler will read 'stamina_spent' from _last_action_result_detail and apply it
            res = handler(self, action, performer, sm, engine, self._last_action_result_detail)
            if res.get("success") and action.action_type == ActionType.SURRENDER:
                self._player_surrendered = True
            if res.get("success") and action.action_type == ActionType.FLEE:
                self.player_fled_combat = True
            return res
        
        return {"success": False, "message": f"Unknown Action Type: {action.action_type}"}

    def _get_entity_stats_manager(self, entity_id: str, quiet: bool = False) -> Optional['StatsManager']:
        """
        Retrieves the StatsManager for a given entity ID.
        Checks cache first, then Player, then NPC System.
        """
        # 0. Check internal cache (for dynamic entities)
        if entity_id in self._stats_manager_cache:
            return self._stats_manager_cache[entity_id]

        sm = get_state_manager()
        if not sm.current_state: 
            if not quiet: logger.error("No current state in StateManager.")
            return None
            
        # 1. Check if it's the Player
        pid = getattr(sm.current_state.player, 'id', None) or getattr(sm.current_state.player, 'stats_manager_id', None)
        if entity_id == pid: 
            return sm.stats_manager
            
        # 2. Check NPC System
        npc_sys = sm.get_npc_system()
        if npc_sys:
            npc = npc_sys.get_npc_by_id(entity_id)
            if npc and hasattr(npc, 'stats_manager'): 
                return npc.stats_manager
            if not quiet: logger.warning(f"StatsManager not found in NPCSystem for ID: {entity_id}")
        else:
            if not quiet: logger.error("NPCSystem not available.")
            
        return None

    def _find_entity_by_combat_name(self, name: str) -> Optional[CombatEntity]:
        if not name: return None
        nl = name.lower()
        for e in self.entities.values():
            if getattr(e, 'combat_name', '').lower() == nl: return e
        return None

    def _log_and_dispatch_event(self, content, type, role="system", gradual=False, tts=False, metadata=None, engine=None):
        """Helper to queue display events. Accepts optional engine to resolve orchestrator dynamically."""
        # Persistence
        if isinstance(content, str) and type in [DisplayEventType.SYSTEM_MESSAGE, DisplayEventType.NARRATIVE_IMPACT, DisplayEventType.NARRATIVE_ATTEMPT]:
            self.combat_log.append({"role": role, "content": content})
        
        # Resolve Orchestrator
        orch = self._orchestrator
        if not orch and engine and hasattr(engine, '_combat_orchestrator'):
            orch = engine._combat_orchestrator
            # Auto-repair the link if missing
            self._orchestrator = orch

        if orch:
            evt = DisplayEvent(type=type, content=content, role=role, target_display=DisplayTarget.COMBAT_LOG, gradual_visual_display=gradual, tts_eligible=tts, metadata=metadata, source_step=self.current_step.name)
            orch.add_event_to_queue(evt)
        else:
            logger.error(f"Failed to dispatch event: Orchestrator not found. Content: {content[:50]}...")

    def _queue_ap_update(self, entity_id: str, engine):
        """Helper to queue an AP update event for the UI."""
        if not engine or not hasattr(engine, '_combat_orchestrator'): return
        
        sm = self._get_entity_stats_manager(entity_id, quiet=True)
        max_ap = sm.get_stat_value(DerivedStatType.MAX_AP) if sm else 4.0
        current = self.ap_pool.get(entity_id, 0.0)
        
        evt = DisplayEvent(
            type=DisplayEventType.AP_UPDATE, 
            content={}, 
            metadata={"entity_id": entity_id, "current_ap": current, "max_ap": max_ap}, 
            target_display=DisplayTarget.MAIN_GAME_OUTPUT
        )
        engine._combat_orchestrator.add_event_to_queue(evt)

    def _check_combat_state(self) -> bool:
        alive_p = 0
        alive_e = 0
        for e in self.entities.values():
            if e.is_alive() and getattr(e, 'is_active_in_combat', True):
                if e.entity_type == EntityType.PLAYER: alive_p += 1
                elif e.entity_type == EntityType.ENEMY: alive_e += 1
        
        if alive_p == 0:
            if self.player_fled_combat:
                self.state = CombatState.FLED
                return True 
            if self._player_surrendered:
                self.state = CombatState.PLAYER_SURRENDERED
                return True
            
            else:
                self.state = CombatState.PLAYER_DEFEAT
                return True
                    
        if alive_e == 0:
            self.state = CombatState.PLAYER_VICTORY
            return True
        return False

    def _advance_turn(self) -> Optional[str]:
        if not self.turn_order: return None
        for _ in range(len(self.turn_order)):
            self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
            eid = self.turn_order[self.current_turn_index]
            e = self.entities.get(eid)
            if e and e.is_alive() and getattr(e, 'is_active_in_combat', True):
                self._active_entity_id = eid
                return eid
        return None

    def get_current_entity(self) -> Optional[CombatEntity]:
        if self._active_entity_id: return self.entities.get(self._active_entity_id)
        return None
    
    def get_current_entity_id(self) -> Optional[str]:
        return self._active_entity_id

    def get_player_entity(self) -> Optional[CombatEntity]:
        if self._player_entity_id: return self.entities.get(self._player_entity_id)
        return None

    def end_combat(self, reason: str):
        self.state = CombatState.NOT_STARTED if self.state == CombatState.IN_PROGRESS else self.state
        self._log_and_dispatch_event(f"Combat Ended: {reason}", DisplayEventType.SYSTEM_MESSAGE)

    def sync_stats_with_managers_from_entities(self):
        """Resyncs stats on load."""
        for eid, e in self.entities.items():
            sm = self._get_entity_stats_manager(eid, quiet=True)
            if sm:
                try:
                    sm.set_current_stat(DerivedStatType.HEALTH, e.current_hp)
                    sm.set_current_stat(DerivedStatType.STAMINA, e.current_stamina)
                    sm.set_current_stat(DerivedStatType.MANA, e.current_mp)
                except Exception: pass

    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "turn_order": self.turn_order,
            "current_turn_index": self.current_turn_index,
            "round_number": self.round_number,
            "state": self.state.name,
            "current_step": self.current_step.name,
            "active_entity_id": self._active_entity_id,
            "player_entity_id": self._player_entity_id,
            "enemy_entity_ids": self._enemy_entity_ids,
            "is_surprise_round": self._is_surprise_round,
            "surprise_round_entities": self._surprise_round_entities,
            "combat_log": self.combat_log,
            "last_action_results": self.last_action_results
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CombatManager':
        cm = cls()
        cm.id = data.get("id", str(uuid.uuid4()))
        cm.entities = {k: CombatEntity.from_dict(v) for k, v in data.get("entities", {}).items()}
        cm.turn_order = data.get("turn_order", [])
        cm.current_turn_index = data.get("current_turn_index", 0)
        cm.round_number = data.get("round_number", 0)
        cm.state = CombatState[data.get("state", "NOT_STARTED")]
        try:
            cm.current_step = CombatStep[data.get("current_step", "NOT_STARTED")]
        except Exception:
            cm.current_step = CombatStep.NOT_STARTED
        cm._active_entity_id = data.get("active_entity_id")
        cm._player_entity_id = data.get("player_entity_id")
        cm._enemy_entity_ids = data.get("enemy_entity_ids", [])
        cm._is_surprise_round = data.get("is_surprise_round", False)
        cm._surprise_round_entities = data.get("surprise_round_entities", [])
        cm.combat_log = data.get("combat_log", [])
        cm.last_action_results = data.get("last_action_results", {})

        # --- FIX: Hydrate StatsManager Cache for loaded entities ---
        # This ensures stats exist even if the NPC isn't in the global NPCSystem registry
        from core.stats.stats_manager import StatsManager
        from core.stats.stats_base import StatType, DerivedStatType
        
        for entity in cm.entities.values():
            if entity.entity_type == EntityType.PLAYER: continue # Player handled globally
            
            # Create a transient StatsManager
            sm = StatsManager()
            # Populate it from the saved CombatEntity stats
            for stat_key, value in entity.stats.items():
                # Handle both Enum keys and string keys
                key = stat_key
                if isinstance(stat_key, str):
                    # Try to resolve to enum
                    try: key = StatType.from_string(stat_key)
                    except: 
                        try: key = DerivedStatType.from_string(stat_key)
                        except: pass
                
                # Set value (direct base_value setting for reconstruction)
                if isinstance(key, StatType):
                    sm.set_base_stat(key, float(value))
                elif isinstance(key, DerivedStatType):
                    if key not in sm.derived_stats:
                        # Initialize if missing
                        from core.stats.stats_base import Stat, StatCategory
                        sm.derived_stats[key] = Stat(name=key, base_value=float(value), category=StatCategory.DERIVED)
                    else:
                        sm.derived_stats[key].base_value = float(value)

            # Register it
            cm.register_stats_manager(entity.id, sm)
            logger.info(f"Hydrated transient StatsManager for loaded entity: {entity.combat_name} ({entity.id})")
        # -----------------------------------------------------------

        return cm