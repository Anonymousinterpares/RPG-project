"""
Combat module for handling turn-based combat mechanics.
"""

from core.combat.combat_manager import CombatManager
from core.combat.combat_entity import CombatEntity, EntityType
from core.combat.combat_action import CombatAction, ActionType


def register_combat_commands():
    """Register combat commands and developer commands."""
    # Import here to avoid circular imports
    from core.base.commands import get_command_processor
    from core.utils.logging_config import get_logger
    from core.combat.dev_commands import register_combat_dev_commands
    
    logger = get_logger("GAME")
    
    # Register developer commands
    processor = get_command_processor()
    register_combat_dev_commands(processor)
    
    logger.info("Combat command system initialized")
    
    # Return the processor for testing purposes
    return processor


# Initialize combat commands when the module is imported
try:
    register_combat_commands()
except Exception as e:
    # Import here to avoid circular imports at module level
    from core.utils.logging_config import get_logger
    logger = get_logger("GAME")
    logger.error(f"Error registering combat commands: {e}", exc_info=True)
