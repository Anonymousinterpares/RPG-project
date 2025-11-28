import logging
from typing import TYPE_CHECKING

# Logic has been refactored into the 'handlers' package for better modularity.
# This file serves as a backward-compatibility facade for the CombatManager.

from core.combat.handlers.physical import handle_attack_action, handle_defend_action
from core.combat.handlers.magic import handle_spell_action
from core.combat.handlers.items import handle_item_action
from core.combat.handlers.movement import handle_flee_action_mechanics, handle_surrender_action_mechanics

if TYPE_CHECKING:
    from typing import Dict, Any
    from core.combat.combat_manager import CombatManager
    from core.stats.stats_manager import StatsManager
    from core.base.engine import GameEngine
    from core.combat.combat_entity import CombatEntity
    from core.combat.combat_action import CombatAction

logger = logging.getLogger(__name__)

# --- Handler Mappings ---
# These aliases map the internal handler names expected by CombatManager
# to the new organized functions in core/combat/handlers/.

_handle_attack_action = handle_attack_action
_handle_spell_action = handle_spell_action
_handle_defend_action = handle_defend_action
_handle_item_action = handle_item_action
_handle_flee_action_mechanics = handle_flee_action_mechanics
_handle_surrender_action_mechanics = handle_surrender_action_mechanics