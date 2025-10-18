#!/usr/bin/env python3
"""
SFXManager: lightweight context-aware sound effects trigger.
- Loads simple tag->file mappings from config/audio/sfx_mappings.json if present
- On context changes, optionally plays one-shot SFX for venue/weather/crowd/etc.
- Uses the same backend as MusicDirector if provided (expects play_sfx)
"""
from __future__ import annotations
import os
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from core.utils.logging_config import get_logger

logger = get_logger("SFX")

DEFAULT_MAPPING: Dict[str, Dict[str, str]] = {
    # category -> value -> relative file under sound/sfx
    "venue": {
        "tavern": "sfx/tavern_clink.wav",
        "market": "sfx/market_chatter.wav",
        "library": "sfx/library_pageflip.wav",
        "fireplace": "sfx/campfire_crackle.wav",
    },
    "weather": {
        "storm": "sfx/thunder_rumble.wav",
        "rain": "sfx/rain_patters.wav",
        "windy": "sfx/wind_gust.wav",
    },
    "crowd": {
        "busy": "sfx/crowd_murmur.wav",
        "sparse": "sfx/few_steps.wav",
        "empty": "sfx/silence_tail.wav",
    },
}

class SFXManager:
    def __init__(self, project_root: Optional[str] = None) -> None:
        self._backend = None  # type: ignore
        self._project_root = Path(project_root or os.getcwd())
        self._map: Dict[str, Dict[str, str]] = {}
        self._last_play_ts: Dict[str, float] = {}
        self._min_interval_s: float = 3.0  # avoid spam on rapid toggles per category
        self._enabled: bool = True
        self._load_mappings()

    def set_backend(self, backend) -> None:
        self._backend = backend

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def _load_mappings(self) -> None:
        try:
            cfg = self._project_root / "config" / "audio" / "sfx_mappings.json"
            if cfg.exists():
                with cfg.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._map = data
                        return
        except Exception as e:
            logger.warning(f"Failed reading sfx_mappings.json: {e}")
        self._map = DEFAULT_MAPPING

    def _abs_path(self, rel: str) -> Optional[str]:
        try:
            p = (self._project_root / "sound" / rel).resolve()
            if p.exists():
                return str(p)
        except Exception:
            pass
        return None

    def _maybe_play(self, category: str, value: Optional[str]) -> None:
        if not self._enabled or not self._backend or not value:
            return
        try:
            now = time.time()
            last = self._last_play_ts.get(category, 0.0)
            if (now - last) < self._min_interval_s:
                return
            mapping = self._map.get(category, {})
            file_rel = mapping.get(str(value).strip().lower())
            if not file_rel:
                return
            full = self._abs_path(file_rel)
            if not full:
                return
            self._backend.play_sfx(full, category=category)
            self._last_play_ts[category] = now
        except Exception as e:
            logger.debug(f"SFX play skipped ({category}={value}): {e}")

    def apply_context(self, ctx: Dict[str, Any], changed_keys: Optional[list] = None) -> None:
        """React to context update. Only fire SFX for changed categories."""
        if not self._enabled:
            return
        try:
            loc = (ctx.get("location") or {}) if isinstance(ctx.get("location"), dict) else {}
            weather = (ctx.get("weather") or {}) if isinstance(ctx.get("weather"), dict) else {}
            # Determine categories to consider (only changed to reduce spam)
            changed = set(changed_keys or [])
            # Venue
            if not changed or any(k in changed for k in ("location.location_venue","location_venue","location.venue")):
                self._maybe_play("venue", loc.get("venue"))
            # Weather
            if not changed or any(k in changed for k in ("weather.type","weather_type")):
                self._maybe_play("weather", weather.get("type"))
            # Crowd level
            if not changed or ("crowd_level" in changed):
                self._maybe_play("crowd", ctx.get("crowd_level"))
        except Exception:
            pass
