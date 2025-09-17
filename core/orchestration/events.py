"""
Defines event structures for the CombatOutputOrchestrator.
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Union, Dict, Any, Optional, List
import uuid

class DisplayEventType(Enum):
    """Types of events the CombatOutputOrchestrator can handle."""
    NARRATIVE_ATTEMPT = auto()      # LLM narrative describing an action attempt
    NARRATIVE_IMPACT = auto()       # LLM narrative describing an action's outcome
    NARRATIVE_GENERAL = auto()      # Other general narrative from LLM during combat or post-combat
    SYSTEM_MESSAGE = auto()         # Game system messages (rolls, status changes, turns)
    UI_BAR_UPDATE_PHASE1 = auto()   # Initiate visual phase 1 for HP/Stamina/Mana bar decrease
    UI_BAR_UPDATE_PHASE2 = auto()   # Finalize visual phase 2 for HP/Stamina/Mana bar decrease
    VISUAL_EFFECT_TRIGGER = auto()  # Placeholder for triggering visual effects
    BUFFER_FLUSH = auto()           # Special event to process buffered narrative
    REQUEST_CLOSING_NARRATIVE = auto() # New: Event to trigger LLM call for closing combat summary
    TURN_ORDER_UPDATE = auto()      # New: Event to update turn order displays
    COMBAT_LOG_SET_HTML = auto()    # New: Directly set Combat Log HTML (rehydration)
    APPLY_ENTITY_RESOURCE_UPDATE = auto()  # New: Apply a resource (hp/mp/stamina) change to an entity's model
    APPLY_ENTITY_STATE_UPDATE = auto()     # New: Apply state flags (e.g., is_active_in_combat)
    # Add more event types as needed
    
class DisplayTarget(Enum):
    """Specifies where the display event should be primarily rendered."""
    COMBAT_LOG = auto()
    MAIN_GAME_OUTPUT = auto()
    # UI_ELEMENT (for direct UI manipulations not via text, like bar animations) - handled by metadata for now

@dataclass
class DisplayEvent:
    """
    Represents a piece of information to be displayed to the player,
    managed by the CombatOutputOrchestrator.
    """
    type: DisplayEventType
    content: Union[str, List[str], Dict[str, Any]] # Text, list of texts (for buffer), or data for UI updates
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: Optional[str] = "system" # Default role for MainWindow._handle_game_output
    target_display: DisplayTarget = DisplayTarget.COMBAT_LOG
    gradual_visual_display: bool = False # Hint for UI on how to display text
    tts_eligible: bool = False # Whether this content should be spoken by TTS
    source_step: Optional[str] = None # For debugging, e.g., CombatManager's current_step.name
    metadata: Optional[Dict[str, Any]] = None # For UI_BAR_UPDATE, VISUAL_EFFECT, etc.

    def __str__(self):
        content_str = ""
        if isinstance(self.content, list):
            content_str = f"[{len(self.content)} items]"
        elif isinstance(self.content, dict):
            content_str = f"{ {k: str(v)[:20] + '...' if len(str(v)) > 20 else str(v) for k, v in self.content.items()} }"
        else:
            content_str = str(self.content)[:50] + ('...' if len(str(self.content)) > 50 else '')

        return (f"DisplayEvent(id={self.event_id}, type={self.type.name}, target={self.target_display.name}, "
                f"tts={self.tts_eligible}, gradual={self.gradual_visual_display}, content='{content_str}')")