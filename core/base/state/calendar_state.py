#!/usr/bin/env python3
"""
Canonical calendar state representation for the RPG game.

This defines the hierarchical calendar components:
Era > Cycle > Phase > Tide > Span > Day

The breakdown is computed from the configured unit lengths in config/calendar.
"""

from dataclasses import dataclass, field
from typing import Dict, Any

from core.base.config import get_config
from core.utils.logging_config import get_logger

logger = get_logger("CALENDAR")


@dataclass
class CalendarState:
    era: int = 1
    cycle: int = 1
    phase: int = 1
    tide: int = 1
    span: int = 1
    day: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "era": self.era,
            "cycle": self.cycle,
            "phase": self.phase,
            "tide": self.tide,
            "span": self.span,
            "day": self.day,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalendarState":
        logger.debug(f"CalendarState.from_dict: data received: {data}")
        if not isinstance(data, dict):
            logger.debug("CalendarState.from_dict: data is not a dict, returning default CalendarState.")
            return cls()
        return cls(
            era=int(data.get("era", 1) or 1),
            cycle=int(data.get("cycle", 1) or 1),
            phase=int(data.get("phase", 1) or 1),
            tide=int(data.get("tide", 1) or 1),
            span=int(data.get("span", 1) or 1),
            day=int(data.get("day", 1) or 1),
        )

    def recalc_from_game_time(self, game_time_seconds: float) -> None:
        """Recalculate the calendar breakdown based on game time and configured unit lengths."""
        try:
            cfg = get_config()
            units = cfg.get("calendar.units", {}) or {}
            day_len = int(units.get("day_length_seconds", 86400))
            span_days = int(units.get("span_length_days", 5))
            tide_spans = int(units.get("tide_length_spans", 3))
            phase_tides = int(units.get("phase_length_tides", 4))
            cycle_phases = int(units.get("cycle_length_phases", 6))
            era_cycles = int(units.get("era_length_cycles", 8))

            if day_len <= 0:
                day_len = 86400

            # Total days elapsed since epoch start (0-based)
            total_days = int(max(0, game_time_seconds) // day_len)

            days_per_span = max(1, span_days)
            days_per_tide = days_per_span * max(1, tide_spans)
            days_per_phase = days_per_tide * max(1, phase_tides)
            days_per_cycle = days_per_phase * max(1, cycle_phases)
            days_per_era = days_per_cycle * max(1, era_cycles)

            remaining = total_days
            self.era = (remaining // days_per_era) + 1
            remaining = remaining % days_per_era

            self.cycle = (remaining // days_per_cycle) + 1
            remaining = remaining % days_per_cycle

            self.phase = (remaining // days_per_phase) + 1
            remaining = remaining % days_per_phase

            self.tide = (remaining // days_per_tide) + 1
            remaining = remaining % days_per_tide

            self.span = (remaining // days_per_span) + 1
            remaining = remaining % days_per_span

            self.day = (remaining % days_per_span) + 1
        except Exception as e:
            logger.warning(f"Failed to recalc calendar from game time: {e}")
