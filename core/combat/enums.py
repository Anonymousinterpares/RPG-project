from enum import Enum, auto

class CombatState(Enum):
    """Possible states of combat."""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    PLAYER_VICTORY = auto()
    PLAYER_DEFEAT = auto()
    FLED = auto()

class CombatStep(Enum):
    NOT_STARTED = auto()
    AWAITING_TRANSITION_DATA = auto() # New step for data arrival
    STARTING_COMBAT = auto()
    HANDLING_SURPRISE_CHECK = auto()
    PERFORMING_SURPRISE_ATTACK = auto()
    NARRATING_SURPRISE_OUTCOME = auto()
    ENDING_SURPRISE_ROUND = auto()
    ROLLING_INITIATIVE = auto()
    STARTING_ROUND = auto()
    AWAITING_PLAYER_INPUT = auto()
    PROCESSING_PLAYER_ACTION = auto()
    AWAITING_NPC_INTENT = auto()
    PROCESSING_NPC_ACTION = auto()
    RESOLVING_ACTION_MECHANICS = auto()
    NARRATING_ACTION_OUTCOME = auto()
    APPLYING_STATUS_EFFECTS = auto()
    ADVANCING_TURN = auto()
    ENDING_COMBAT = auto()
    COMBAT_ENDED = auto()