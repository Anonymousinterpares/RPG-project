import logging
from typing import Dict, TYPE_CHECKING
from core.stats.stats_base import DerivedStatType
from core.orchestration.events import DisplayEvent, DisplayEventType

if TYPE_CHECKING:
    from core.combat.combat_manager import CombatManager
    from core.stats.stats_manager import StatsManager
    from core.base.engine import GameEngine
    from core.combat.combat_entity import CombatEntity

logger = logging.getLogger(__name__)

def apply_and_display_costs(manager: 'CombatManager', performer: 'CombatEntity', performer_stats_manager: 'StatsManager', engine: 'GameEngine', result_detail: Dict):
    """
    Helper to deduct resources (Stamina/Mana) based on result_detail calculations
    and queue the appropriate UI bar update events.
    """
    try:
        stamina_spent = result_detail.get("stamina_spent", 0)
        mana_spent = result_detail.get("mana_spent", 0)

        if stamina_spent and stamina_spent > 0:
            prev_stam = performer_stats_manager.get_current_stat_value(DerivedStatType.STAMINA)
            new_stam = max(0, prev_stam - stamina_spent)
            
            # Phase 1: Preview
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={},
                metadata={"entity_id": performer.id, "bar_type": "stamina", "old_value": prev_stam, "new_value_preview": new_stam, "max_value": performer.max_stamina}
            ))
            
            # Update Model
            performer_stats_manager.set_current_stat(DerivedStatType.STAMINA, new_stam)
            performer.set_current_stamina(new_stam)
            
            # Phase 2: Finalize
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={},
                metadata={"entity_id": performer.id, "bar_type": "stamina", "final_new_value": new_stam, "max_value": performer.max_stamina}
            ))
            
            manager._log_and_dispatch_event(f"{performer.combat_name} spent {stamina_spent:.1f} stamina. Rem: {new_stam:.1f}", DisplayEventType.SYSTEM_MESSAGE)

        if mana_spent and mana_spent > 0:
            prev_mp = performer_stats_manager.get_current_stat_value(DerivedStatType.MANA)
            new_mp = max(0, prev_mp - mana_spent)
            
            # Phase 1: Preview
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE1, content={},
                metadata={"entity_id": performer.id, "bar_type": "mana", "old_value": prev_mp, "new_value_preview": new_mp, "max_value": performer.max_mp}
            ))
            
            # Update Model
            performer_stats_manager.set_current_stat(DerivedStatType.MANA, new_mp)
            performer.current_mp = new_mp
            
            # Phase 2: Finalize
            engine._combat_orchestrator.add_event_to_queue(DisplayEvent(
                type=DisplayEventType.UI_BAR_UPDATE_PHASE2, content={},
                metadata={"entity_id": performer.id, "bar_type": "mana", "final_new_value": new_mp, "max_value": performer.max_mp}
            ))
            
            manager._log_and_dispatch_event(f"{performer.combat_name} spent {mana_spent:.1f} mana. Rem: {new_mp:.1f}", DisplayEventType.SYSTEM_MESSAGE)

    except Exception as e_cost:
        logger.warning(f"Failed to apply/display resource costs: {e_cost}")