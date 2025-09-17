"""
Game state for the RPG game.

This module provides the GameState class for managing the overall game state.
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from core.base.state.player_state import PlayerState
from core.base.state.world_state import WorldState
from core.utils.logging_config import get_logger
from core.interaction.enums import InteractionMode


# Import here but use type hints with string to avoid circular imports
# This import is only used for type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.combat.combat_manager import CombatManager

# Get the module logger
logger = get_logger("GAME")

@dataclass
class GameState:
    """
    Overall game state.
    
    This dataclass contains all state information for a game session,
    including player and world state.
    """
    # Session information
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    last_saved_at: Optional[float] = None
    
    # Game version
    game_version: str = "0.1.0"
    
    # States
    player: PlayerState = field(default_factory=lambda: PlayerState(name="Player"))
    world: WorldState = field(default_factory=WorldState)
    
    # Combat manager (optional, only present during combat)
    combat_manager: Optional['CombatManager'] = None
    
    # Conversation history (simple for now, will be expanded)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Event log (game-time receipts of what happened in this session)
    event_log: List[Dict[str, Any]] = field(default_factory=list)
    
    # Last command (for context)
    last_command: Optional[str] = None
    
    
    # Interaction Mode
    current_mode: InteractionMode = field(default=InteractionMode.NARRATIVE)
    
    # Mode-specific state
    current_combatants: List[str] = field(default_factory=list)  # IDs of entities in combat/social conflict
    current_trade_partner_id: Optional[str] = None             # ID of the NPC being traded with
    
    # Cooldowns for mode transitions (target_mode: timestamp_expires)
    mode_transition_cooldowns: Dict[str, float] = field(default_factory=dict)
    
    # Transition state flags
    is_transitioning_to_combat: bool = False  # Flag for narrative->combat transition
    combat_narrative_buffer: List[str] = field(default_factory=list)  # Buffer for combat intro narrative

    @property
    def game_time(self):
        """
        Compatibility property for web server to access game time.
        
        Returns:
            A GameTime object representing the game time from world state.
        """
        from core.base.game_loop import GameTime
        return GameTime(game_time=self.world.game_time)
    
    def add_conversation_entry(self, role: str, content: str) -> None:
        """
        Add an entry to the conversation history.
        
        Args:
            role: The role of the speaker (e.g., "player", "gm").
            content: The content of the message.
        """
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }
        self.conversation_history.append(entry)
        
        # Limit history size (keep last 100 entries)
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
    

    def get_interaction_mode(self) -> InteractionMode:
        """Return the current interaction mode."""
        return self.current_mode

    def set_interaction_mode(self, new_mode: InteractionMode) -> None:
        """
        Set the interaction mode and reset mode-specific state if necessary.

        Args:
            new_mode: The InteractionMode to switch to.
        """
        if new_mode == self.current_mode:
            return  # No change

        old_mode = self.current_mode
        logger.info(f"Changing interaction mode from {old_mode.name} to {new_mode.name}")

        # --- ECFA Change: is_transitioning_to_combat flag management ---
        # This flag is primarily set to True by mode_transitions.py *before* this method is called.
        # This method mainly handles cleanup and ensures the flag is reset appropriately.

        if old_mode == InteractionMode.NARRATIVE and new_mode == InteractionMode.COMBAT:
            # If is_transitioning_to_combat is not already True, it means this is a direct
            # call to set COMBAT mode (e.g., dev command, or unexpected flow).
            # Set it True to ensure UI buffers any initial narrative if it comes *after* this call.
            if not self.is_transitioning_to_combat:
                logger.warning("set_interaction_mode called directly to COMBAT without transition prep. Setting is_transitioning_to_combat=True.")
                self.is_transitioning_to_combat = True
            # The flag (is_transitioning_to_combat) will be reset by MainWindow after
            # it processes the buffered narrative and switches the UI view.
        
        elif old_mode == InteractionMode.COMBAT and new_mode != InteractionMode.COMBAT:
            # Leaving combat mode
            logger.debug(f"Leaving COMBAT mode for {new_mode.name}. Resetting combat transition flags.")
            self.is_transitioning_to_combat = False # Explicitly reset
            self.combat_narrative_buffer = [] # Clear any residual buffer
            # CombatManager itself is cleared by GameEngine or mode_transitions logic
            # when combat actually ends (e.g., PLAYER_DEFEAT, VICTORY).
            # This method simply reacts to the mode having been changed.
            if self.combat_manager:
                 logger.info(f"Combat mode ended. Last CombatManager state: {self.combat_manager.state.name if self.combat_manager.state else 'N/A'}")
            # self.combat_manager = None # This is typically done by the Engine when combat fully resolves.

        elif self.is_transitioning_to_combat and new_mode != InteractionMode.COMBAT:
            # If we were in the process of transitioning TO combat, but are now
            # being set to a different mode (e.g., error, or immediate override),
            # then cancel the combat transition state.
            logger.warning(f"Combat transition was in progress, but now switching to {new_mode.name}. Resetting transition flags.")
            self.is_transitioning_to_combat = False
            self.combat_narrative_buffer = []

        # Reset mode-specific state based on the mode we are *leaving*
        if old_mode in [InteractionMode.COMBAT, InteractionMode.SOCIAL_CONFLICT]:
            if new_mode not in [InteractionMode.COMBAT, InteractionMode.SOCIAL_CONFLICT]:
                logger.debug(f"Clearing current_combatants list when leaving {old_mode.name} for {new_mode.name}.")
                self.current_combatants = []
        
        if old_mode == InteractionMode.TRADE:
            if new_mode != InteractionMode.TRADE:
                logger.debug(f"Clearing current_trade_partner_id when leaving TRADE for {new_mode.name}.")
                self.current_trade_partner_id = None

        # Set the new mode
        self.current_mode = new_mode
        logger.info(f"Interaction mode is now set to {self.current_mode.name}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert GameState to a dictionary for serialization."""
        result = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_saved_at": self.last_saved_at or time.time(),
            "game_version": self.game_version,
            "player": self.player.to_dict(),
            "world": self.world.to_dict(),
            "conversation_history": self.conversation_history,
            "event_log": self.event_log,
            "last_command": self.last_command,
            # Interaction Mode State
            "current_mode": self.current_mode.name,  # Store enum name as string
            "current_combatants": self.current_combatants,
            "current_trade_partner_id": self.current_trade_partner_id,
            "mode_transition_cooldowns": self.mode_transition_cooldowns,
            "is_transitioning_to_combat": self.is_transitioning_to_combat,
            "combat_narrative_buffer": self.combat_narrative_buffer,
        }
        
        # Include journal if present
        if hasattr(self, 'journal') and isinstance(self.journal, dict):
            result["journal"] = self.journal
        
        # Add combat_manager if it exists
        if self.combat_manager is not None:
            result["combat_manager"] = self.combat_manager.to_dict()
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        """Create a GameState from a dictionary."""
        player_data = data.get("player", {})
        world_data = data.get("world", {})
        
        game_state = cls(
            session_id=data.get("session_id", str(uuid.uuid4())),
            created_at=data.get("created_at", time.time()),
            last_saved_at=data.get("last_saved_at"),
            game_version=data.get("game_version", "0.1.0"),
            player=PlayerState.from_dict(player_data),
            world=WorldState.from_dict(world_data),
            conversation_history=data.get("conversation_history", []),
            last_command=data.get("last_command"),
            # Load Interaction Mode State
            current_combatants=data.get("current_combatants", []),
            current_trade_partner_id=data.get("current_trade_partner_id"),
            mode_transition_cooldowns=data.get("mode_transition_cooldowns", {}),
            is_transitioning_to_combat=data.get("is_transitioning_to_combat", False),
            combat_narrative_buffer=data.get("combat_narrative_buffer", []),
        )

        # Convert stored mode name back to enum
        mode_name = data.get("current_mode", InteractionMode.NARRATIVE.name)
        try:
            game_state.current_mode = InteractionMode[mode_name]
        except KeyError:
            logger.warning(f"Unknown interaction mode '{mode_name}' found in save data. Defaulting to NARRATIVE.")
            game_state.current_mode = InteractionMode.NARRATIVE
        
        # Restore journal if present
        if "journal" in data and isinstance(data["journal"], dict):
            game_state.journal = data["journal"]
        
        # Restore event log if present
        if "event_log" in data and isinstance(data["event_log"], list):
            game_state.event_log = data["event_log"]
        else:
            game_state.event_log = []
        
        # Load combat_manager if it exists in data
        if "combat_manager" in data:
            from core.combat.combat_manager import CombatManager
            game_state.combat_manager = CombatManager.from_dict(data["combat_manager"])
            
        return game_state
