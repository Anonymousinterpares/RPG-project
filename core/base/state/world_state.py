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
            # Build rich calendar string (with names)
            self.game_date = self._build_calendar_string()
        except Exception as e:
            logger.warning(f"Failed to recalc calendar on advance_time: {e}")
        
        # Update day/night cycle using enhanced time manager
        time_manager = get_enhanced_time_manager()
        self.is_day = time_manager.is_daylight_period(self.game_time)
    
    def __post_init__(self):
        """Initialize or recalc calendar and date from current game_time at creation."""
        try:
            self.calendar.recalc_from_game_time(self.game_time)
            self.game_date = self._build_calendar_string()
        except Exception as e:
            logger.debug(f"WorldState __post_init__ calendar setup skipped: {e}")
    
    def _build_calendar_string(self) -> str:
        """Build a rich, named calendar string using config-driven names and current indices."""
        try:
            cfg = get_config()
            units = cfg.get("calendar.units", {}) or {}
            day_len = int(units.get("day_length_seconds", 86400)) or 86400
            if day_len <= 0:
                day_len = 86400
            names_map = cfg.get("calendar.names", {}) or {}
            year_label = names_map.get("year", "Year")
            start_year = int(cfg.get("calendar.start_year", 1) or 1)
            # Name arrays
            era_names = cfg.get("calendar.era_names", []) or []
            phase_names = cfg.get("calendar.phase_names", []) or []
            tide_names = cfg.get("calendar.tide_names", []) or []
            span_names = cfg.get("calendar.span_names", []) or []  # treat as months across a cycle (wrap around)
            dow_names = cfg.get("calendar.day_of_week_names", []) or []
            # Compute helper totals
            total_days = int(max(0, self.game_time) // day_len)
            # Year = cycle
            era_name = None
            if era_names:
                era_name = era_names[(self.calendar.era - 1) % len(era_names)]
            # Names for phase/tide
            phase_name = phase_names[(self.calendar.phase - 1) % len(phase_names)] if phase_names else f"Phase {self.calendar.phase}"
            tide_name = tide_names[(self.calendar.tide - 1) % len(tide_names)] if tide_names else f"Tide {self.calendar.tide}"
            # Determine span index across the cycle for month name
            span_days = int(units.get("span_length_days", 5)) or 5
            tide_spans = int(units.get("tide_length_spans", 3)) or 3
            phase_tides = int(units.get("phase_length_tides", 4)) or 4
            cycle_phases = int(units.get("cycle_length_phases", 6)) or 6
            days_per_span = max(1, span_days)
            days_per_tide = days_per_span * max(1, tide_spans)
            days_per_phase = days_per_tide * max(1, phase_tides)
            days_per_cycle = days_per_phase * max(1, cycle_phases)
            days_into_cycle = total_days % days_per_cycle
            span_index_in_cycle = (days_into_cycle // days_per_span) + 1
            month_name = span_names[(span_index_in_cycle - 1) % len(span_names)] if span_names else f"Span {span_index_in_cycle}"
            # Day-of-week
            if dow_names:
                day_of_week_name = dow_names[total_days % len(dow_names)]
            else:
                day_of_week_name = f"Day {((total_days % 7) + 1)}"
            # Compose
            parts = []
            parts.append(era_name if era_name else f"{names_map.get('era','Era')} {self.calendar.era}")
            year_number = start_year + (self.calendar.cycle - 1)
            parts.append(f"{year_label} {year_number}")
            parts.append(phase_name)
            parts.append(tide_name)
            parts.append(f"{month_name} {self.calendar.day} ({day_of_week_name})")
            return ", ".join(parts)
        except Exception as e:
            logger.debug(f"Failed to build calendar string: {e}")
            # Fallback to numeric representation
            names = get_config().get("calendar.names", {}) or {}
            return (
                f"{names.get('era','Era')} {self.calendar.era}, "
                f"{names.get('cycle','Cycle')} {self.calendar.cycle}, "
                f"{names.get('phase','Phase')} {self.calendar.phase}, "
                f"{names.get('tide','Tide')} {self.calendar.tide}, "
                f"{names.get('span','Span')} {self.calendar.span}, "
                f"{names.get('day','Day')} {self.calendar.day}"
            )
    
    @property
    def calendar_string(self) -> str:
        """Public accessor for the rich calendar string."""
        try:
            return self._build_calendar_string()
        except Exception:
            return self.game_date or ""
    
    @property
    def calendar_compact(self) -> str:
        """
        Return a compact canonical calendar string for auditing/debugging.
        Format: E{era}.C{cycle}.PH{phase}.TD{tide}.SP{span}.D{day} HH:MM
        """
        try:
            cfg = get_config()
            units = cfg.get("calendar.units", {}) or {}
            day_len = int(units.get("day_length_seconds", 86400)) or 86400
            if day_len <= 0:
                day_len = 86400
            secs = int(max(0, self.game_time)) % day_len
            hh = secs // 3600
            mm = (secs % 3600) // 60
            return (
                f"E{self.calendar.era}.C{self.calendar.cycle}.PH{self.calendar.phase}."
                f"TD{self.calendar.tide}.SP{self.calendar.span}.D{self.calendar.day} "
                f"{hh:02d}:{mm:02d}"
            )
        except Exception:
            # Fallback to numeric without time-of-day
            return (
                f"E{getattr(self.calendar, 'era', 1)}.C{getattr(self.calendar, 'cycle', 1)}.PH{getattr(self.calendar, 'phase', 1)}."
                f"TD{getattr(self.calendar, 'tide', 1)}.SP{getattr(self.calendar, 'span', 1)}.D{getattr(self.calendar, 'day', 1)}"
            )
    
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
            # Add computed properties for easy access in saves
            "time_of_day": self.time_of_day,
            "calendar_string": self.calendar_string,
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
            calendar_data = data.get("calendar")
            logger.debug(f"WorldState.from_dict: calendar_data received: {calendar_data}")
            if isinstance(calendar_data, dict):
                instance.calendar = CalendarState.from_dict(calendar_data)
            else:
                logger.debug("WorldState.from_dict: 'calendar' data not a dict or missing, recalculating from game_time.")
                instance.calendar.recalc_from_game_time(instance.game_time)
            # Build rich calendar string
            instance.game_date = instance._build_calendar_string()
        except Exception as e:
            logger.warning(f"Failed to initialize calendar from saved data: {e}")
        
        return instance
