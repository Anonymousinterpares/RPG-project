from enum import Enum, auto

class InteractionMode(Enum):
    """
    Represents the different modes of interaction the player can be in.
    """
    NARRATIVE = auto()        # Default mode, story progression, exploration
    COMBAT = auto()           # Turn-based or real-time combat encounters
    SOCIAL_CONFLICT = auto()  # Debates, negotiations, persuasion challenges
    TRADE = auto()            # Exchanging goods or services with NPCs


class EnvironmentalTag(Enum):
    """
    Represents descriptive tags for environmental features in a scene.
    """
    LOW_COVER = auto()
    HIGH_COVER = auto()
    FLAMMABLE_OBJECT = auto()
    UNSTABLE_GROUND = auto()
    THROWABLE_OBJECT = auto()
    DARK = auto()
    BRIGHT_LIGHT = auto()
    OBSTACLE_SMALL = auto()
    OBSTACLE_LARGE = auto()
    INTERACTIVE_LEVER = auto() # Added an example interactive object
    WATER_SOURCE = auto()
    DIFFICULT_TERRAIN = auto()
