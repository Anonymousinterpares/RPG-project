#!/usr/bin/env python3
"""
TimeController: central policy for world time progression.

- Freezes tick-based time in NARRATIVE, SOCIAL/TRADE, and COMBAT modes
- Centralizes LLM-based increments and post-combat increments
- Reads toggles from config (game.time.tick_enabled, game.time.post_combat_increment_seconds)

This is an architectural clarification on top of Phase 1 where the tick
is already a no-op for time; the controller provides a single source of truth
for time policy decisions.
"""

from typing import Optional

from core.utils.logging_config import get_logger
from core.base.config import get_config

logger = get_logger("TIME_POLICY")


class TimeController:
    _instance: Optional["TimeController"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.reload()
        self._initialized = True
        logger.info(
            "TimeController initialized: tick_enabled=%s, post_combat_increment_s=%s",
            self._tick_enabled,
            self._post_combat_increment_s,
        )

    def reload(self) -> None:
        cfg = get_config()
        # Global tick toggle (default False as per Phase 1 policy)
        self._tick_enabled = bool(cfg.get("game.time.tick_enabled", False))
        # Post-combat increment (default 300 seconds = 5 minutes)
        try:
            v = cfg.get("game.time.post_combat_increment_seconds", 300)
            self._post_combat_increment_s = int(v) if v is not None else 300
        except Exception:
            self._post_combat_increment_s = 300

    # Policy checks
    def is_tick_enabled(self) -> bool:
        return self._tick_enabled

    def should_advance_on_tick(self, mode_name: str) -> bool:
        """
        Whether tick should advance world time under the current mode.
        mode_name: InteractionMode name (string), e.g., 'NARRATIVE', 'COMBAT', 'TRADE'
        """
        if not self._tick_enabled:
            return False
        # Freeze for narrative/social/trade/combat
        frozen = {"NARRATIVE", "COMBAT", "TRADE", "SOCIAL_CONFLICT"}
        return mode_name not in frozen

    # Actions
    def apply_llm_increment(self, world, seconds: float) -> None:
        """Advance time due to LLM-declared passage, respecting global toggle but ignoring tick policy."""
        try:
            if not seconds:
                return
            # LLM increments are allowed in all modes by design
            world.advance_time(float(seconds))
        except Exception as e:
            logger.warning("apply_llm_increment failed: %s", e)

    def apply_post_combat_increment(self, world) -> None:
        try:
            inc = float(max(0, self._post_combat_increment_s))
            if inc > 0:
                world.advance_time(inc)
        except Exception as e:
            logger.warning("apply_post_combat_increment failed: %s", e)


# Convenience getter
def get_time_controller() -> TimeController:
    return TimeController()