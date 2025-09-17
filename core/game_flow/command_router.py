#!/usr/bin/env python3
"""
Handles routing of player commands based on game mode and input type.

This module now serves as a compatibility layer that delegates to InputRouter.
"""

from typing import TYPE_CHECKING

from core.base.commands import CommandResult
from core.utils.logging_config import get_logger
from core.game_flow.input_router import get_input_router

if TYPE_CHECKING:
    from core.base.engine import GameEngine

# Get the module logger
logger = get_logger("COMMAND_ROUTER")

def route_command(engine: 'GameEngine', command_text: str) -> CommandResult:
    """
    Process a command by routing it based on game state and input type.
    This function is now a compatibility wrapper for InputRouter.
    
    Args:
        engine: The GameEngine instance.
        command_text: The raw command text from the player.

    Returns:
        The result of executing the command.
    """
    logger.debug(f"Routing raw input (legacy): '{command_text}'")
    logger.warning("route_command is deprecated - use InputRouter.route_input directly")
    
    # Use InputRouter for processing
    input_router = get_input_router()
    return input_router.route_input(engine, command_text)
