"""
World state for the RPG game.

This module provides the WorldState class for managing the game world.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from core.utils.logging_config import get_logger
from core.utils.enhanced_time_manager import get_enhanced_time_manager
from core.base.state.calendar_state import CalendarState
from core.base.config import get_config

# Get the module logger
logger = get_logger("WORLD")

@dataclass
class WorldState:
    """
    World state information.
    
    This dataclass contains information about the game world,
    including time, weather, and global variables.
    """
    # Game time
    # Phase 1: Do not initialize from real-world time. Start from 0.0 and
    # advance explicitly via engine logic (LLM time_passage, etc.).
    game_time: float = 0.0  # Seconds since epoch (logical counter)
    game_date: str = "Day 1"  # In-game calendar date
    
    # Canonical calendar (era/cycle/phase/tide/span/day)
    calendar: CalendarState = field(default_factory=CalendarState)
    
    # World conditions
    weather: str = "Clear"
    is_day: bool = True
    
    # Special conditions
    magical_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Global variables (for quest states, world events, etc.)
    global_vars: Dict[str, Any] = field(default_factory=dict)
    
    # Active world events
    active_events: List[str] = field(default_factory=list)
    
    # For web server compatibility - will be updated by engine
    _current_location: str = ""
    
    @property
    def current_location(self) -> str:
        """
        Compatibility property for web server - returns the current location.
        This should be kept in sync with player.current_location.
        """
        return self._current_location
    
    @current_location.setter
    def current_location(self, value: str) -> None:
        """Set the current location."""
        self._current_location = value
    
    def advance_time(self, seconds: float) -> None:
        """
        Advance game time by the specified number of seconds.
        
        Args:
            seconds: Number of seconds to advance.
        """
        self.game_time += seconds
        
        # Recalculate canonical calendar from game time
        try:
            self.calendar.recalc_from_game_time(self.game_time)
            # Update game_date string for backward compatibility / display
            names = get_config().get("calendar.names", {}) or {}
            self.game_date = (
                f"{names.get('era','Era')} {self.calendar.era}, "
                f"{names.get('cycle','Cycle')} {self.calendar.cycle}, "
                f"{names.get('phase','Phase')} {self.calendar.phase}, "
                f"{names.get('tide','Tide')} {self.calendar.tide}, "
                f"{names.get('span','Span')} {self.calendar.span}, "
                f"{names.get('day','Day')} {self.calendar.day}"
            )
        except Exception as e:
            logger.warning(f"Failed to recalc calendar on advance_time: {e}")
        
        # Update day/night cycle using enhanced time manager
        time_manager = get_enhanced_time_manager()
        self.is_day = time_manager.is_daylight_period(self.game_time)
    
    def __post_init__(self):
        """Initialize or recalc calendar and date from current game_time at creation."""
        try:
            self.calendar.recalc_from_game_time(self.game_time)
            names = get_config().get("calendar.names", {}) or {}
            self.game_date = (
                f"{names.get('era','Era')} {self.calendar.era}, "
                f"{names.get('cycle','Cycle')} {self.calendar.cycle}, "
                f"{names.get('phase','Phase')} {self.calendar.phase}, "
                f"{names.get('tide','Tide')} {self.calendar.tide}, "
                f"{names.get('span','Span')} {self.calendar.span}, "
                f"{names.get('day','Day')} {self.calendar.day}"
            )
        except Exception as e:
            logger.debug(f"WorldState __post_init__ calendar setup skipped: {e}")
    
    @property
    def time_of_day(self) -> str:
        """
        Get the current time of day as a narrative description.
        
        This replaces the old clock-based time display with rich narrative descriptions.
        
        Returns:
            A narrative description of the current time (e.g., "morning", "sunset", "deep night")
        """
        time_manager = get_enhanced_time_manager()
        season = self.get_global_var("current_season")
        return time_manager.get_time_description(self.game_time, "primary", season)
    
    @property 
    def atmospheric_time(self) -> str:
        """
        Get an atmospheric description of the current time for narrative contexts.
        
        Returns:
            An atmospheric time description (e.g., "as the first rays pierce the darkness")
        """
        time_manager = get_enhanced_time_manager()
        season = self.get_global_var("current_season")
        return time_manager.get_contextual_time(self.game_time, "narrative", season)
    
    @property
    def time_period_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the current time period.
        
        Returns:
            Dictionary with detailed time period information
        """
        time_manager = get_enhanced_time_manager()
        return time_manager.get_period_info(self.game_time)
    
    def get_time_of_day(self) -> str:
        """
        Legacy method for backward compatibility.
        
        DEPRECATED: Use time_of_day property instead.
        This method now returns narrative time instead of clock time.
        """
        logger.warning("get_time_of_day() is deprecated, use time_of_day property instead")
        return self.time_of_day
    
    def update_weather(self, new_weather: str) -> None:
        """
        Update the current weather.
        
        Args:
            new_weather: The new weather condition.
        """
        self.weather = new_weather
        logger.info(f"Weather changed to {new_weather}")
    
    def set_global_var(self, key: str, value: Any) -> None:
        """
        Set a global variable.
        
        Args:
            key: The variable name.
            value: The variable value.
        """
        self.global_vars[key] = value
        logger.debug(f"Global variable {key} set to {value}")
    
    def get_global_var(self, key: str, default: Any = None) -> Any:
        """
        Get a global variable.
        
        Args:
            key: The variable name.
            default: The default value if the variable doesn't exist.
        
        Returns:
            The variable value, or the default if not found.
        """
        return self.global_vars.get(key, default)
    
    def add_event(self, event_id: str) -> None:
        """
        Add an active world event.
        
        Args:
            event_id: The ID of the event to add.
        """
        if event_id not in self.active_events:
            self.active_events.append(event_id)
            logger.info(f"World event added: {event_id}")
    
    def remove_event(self, event_id: str) -> None:
        """
        Remove an active world event.
        
        Args:
            event_id: The ID of the event to remove.
        """
        if event_id in self.active_events:
            self.active_events.remove(event_id)
            logger.info(f"World event removed: {event_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert WorldState to a dictionary for serialization."""
        return {
            "game_time": self.game_time,
            "game_date": self.game_date,
            "calendar": self.calendar.to_dict(),
            "weather": self.weather,
            "is_day": self.is_day,
            "magical_conditions": self.magical_conditions,
            "global_vars": self.global_vars,
            "active_events": self.active_events,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldState':
        """Create a WorldState from a dictionary with legacy fallbacks."""
        # Legacy fallback: if game_time is missing but time_of_day provided, map to an approximate hour
        game_time_val = data.get("game_time")
        if game_time_val is None and isinstance(data.get("time_of_day"), str):
            try:
                from core.utils.time_utils import HOUR
                time_period_hours = {
                    'deep_night': 2, 'pre_dawn': 4.5, 'dawn': 6, 'morning': 9,
                    'noon': 12, 'afternoon': 15, 'evening': 18, 'sunset': 20.5, 'night': 22
                }
                period = str(data.get("time_of_day")).strip().lower()
                # Normalize some common human words
                aliases = {
                    'midday': 'noon', 'dusk': 'sunset', 'twilight': 'sunset', 'daybreak': 'dawn', 'sunrise': 'dawn'
                }
                if period in aliases:
                    period = aliases[period]
                hour = time_period_hours.get(period, 9)
                game_time_val = hour * HOUR
            except Exception:
                game_time_val = 0.0
        if game_time_val is None:
            game_time_val = 0.0
        
        # Construct instance
        instance = cls(
            game_time=game_time_val,
            game_date=data.get("game_date", "Day 1"),
            weather=data.get("weather", "Clear"),
            is_day=data.get("is_day", True),
            magical_conditions=data.get("magical_conditions", {}),
            global_vars=data.get("global_vars", {}),
            active_events=data.get("active_events", []),
        )
        
        # Load or compute calendar state
        try:
            if isinstance(data.get("calendar"), dict):
                instance.calendar = CalendarState.from_dict(data.get("calendar"))
            else:
                instance.calendar.recalc_from_game_time(instance.game_time)
            # Update game_date string to reflect canonical calendar
            names = get_config().get("calendar.names", {}) or {}
            instance.game_date = (
                f"{names.get('era','Era')} {instance.calendar.era}, "
                f"{names.get('cycle','Cycle')} {instance.calendar.cycle}, "
                f"{names.get('phase','Phase')} {instance.calendar.phase}, "
                f"{names.get('tide','Tide')} {instance.calendar.tide}, "
                f"{names.get('span','Span')} {instance.calendar.span}, "
                f"{names.get('day','Day')} {instance.calendar.day}"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize calendar from saved data: {e}")
        
        return instance
