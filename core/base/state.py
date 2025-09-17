"""
State management for the RPG game.

This module provides classes for managing the overall game state,
including player state, world state, and game session information.

Note: This module is now a wrapper around the more granular modules in core.base.state package.
"""

# Re-export from the new modules
from core.base.state.player_state import PlayerState
from core.base.state.world_state import WorldState
from core.base.state.game_state import GameState
from core.base.state.state_manager import StateManager, get_state_manager

__all__ = [
    'PlayerState',
    'WorldState',
    'GameState',
    'StateManager',
    'get_state_manager',
]
