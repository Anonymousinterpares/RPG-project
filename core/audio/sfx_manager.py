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
import threading
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

from core.utils.logging_config import get_logger

logger = get_logger("SFX")

DEFAULT_MAPPING: Dict[str, Dict[str, str]] = {
    # category -> value -> relative file under sound/sfx
    # Context one-shots (existing)
    "venue": {
        "tavern": "sfx/venue/tavern_bell.mp3",
        "market": "sfx/venue/market_chatter_1.mp3",
        "library": "sfx/venue/library_pageflip.mp3",
        "fireplace": "sfx/venue/fireplace_crackle.mp3",
    },
    "weather": {
        "storm": "sfx/loop/weather/storm_loop_01.mp3",
        "rain": "sfx/loop/weather/rain_loop_01.mp3",
        "windy": "sfx/loop/weather/wind_loop_01.mp3",
    },
    "crowd": {
        "busy": "sfx/crowd/chatter_busy_1.mp3",
        "sparse": "sfx/crowd/footsteps_sparse_1.mp3",
        "empty": "sfx/crowd/empty_room_tail.mp3",
    },
    # Programmed one-shots
    "ui": {
        "click": "sfx/ui/ui_click_01.mp3",
        "loot_pickup": "sfx/ui/loot_pickup_01.mp3"
    },
    "event": {
        "combat_start": "sfx/event/event_combat_start_01.mp3",
        "combat_start_short": "sfx/event/event_combat_start_short_01.mp3",
        "victory": "sfx/event/event_victory_fanfare_01.mp3",
        "defeat": "sfx/event/event_defeat_01.mp3",
        "weapon_draw": "sfx/event/event_weapon_draw_01.mp3",
        "game_start": "sfx/event/event_game_start_01.mp3",
        "alert_short": "sfx/event/event_alert_short_01.mp3"
    },
    "magic": {
        "generic_short": "sfx/magic/magic_generic_cast_short_01.mp3",
        "flames": "sfx/magic/magic_flames_cast_short_01.mp3",
        "lightning": "sfx/magic/magic_lightning_cast_short_01.mp3",
        "heal": "sfx/magic/magic_heal_cast_short_01.mp3",
        "defense": "sfx/magic/magic_defense_cast_short_02.mp3",
        "ashen": "sfx/magic/magic_ashen_cast_short_01.mp3"
    },
}

class SFXManager:
    def __init__(self, project_root: Optional[str] = None) -> None:
        self._backend = None  # type: ignore
        self._project_root = Path(project_root or os.getcwd())
        self._map: Dict[str, Dict[str, str]] = {}
        self._last_play_ts: Dict[str, float] = {}
        self._min_interval_s: float = 0.5  # allow faster UI/magic, still debounce
        self._enabled: bool = True
        # Looped SFX management (channels: environment, weather)
        self._loop_active: Dict[str, Optional[str]] = {"environment": None, "weather": None}
        self._loop_last_change_ts: Dict[str, float] = {"environment": 0.0, "weather": 0.0}
        self._loop_min_interval_s: float = 1.0
        self._load_mappings()
        # Rotation management for looped channels
        self._loop_pool: Dict[str, List[str]] = {"environment": [], "weather": []}
        self._loop_next_swap_ts: Dict[str, float] = {"environment": 0.0, "weather": 0.0}
        self._loop_rotation_period_s: float = 120.0  # default rotation cadence for ambience
        # Background rotator
        try:
            t = threading.Thread(target=self._rotator_worker, daemon=True)
            t.start()
            self._rotator_thread = t  # keep ref
        except Exception:
            self._rotator_thread = None

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
        """React to context update. One-shots for venue/weather/crowd; manage looped ambience.
        Looped channels: 'environment' (major/venue/biome/region + time_of_day) and 'weather' (weather.type).
        """
        if not self._enabled:
            return
        try:
            loc = (ctx.get("location") or {}) if isinstance(ctx.get("location"), dict) else {}
            weather = (ctx.get("weather") or {}) if isinstance(ctx.get("weather"), dict) else {}
            tod = str(ctx.get("time_of_day") or "").strip().lower() or None
            major = str(loc.get("major") or "").strip().lower() or None
            venue = str(loc.get("venue") or "").strip().lower() or None
            biome = str(ctx.get("biome") or "").strip().lower() or None
            region = str(ctx.get("region") or "").strip().lower() or None
            wtype = str(weather.get("type") or "").strip().lower() or None

            # One-shots (debounced)
            changed = set(changed_keys or [])
            if not changed or any(k in changed for k in ("location.location_venue","location_venue","location.venue")):
                self._maybe_play("venue", venue)
            if not changed or any(k in changed for k in ("weather.type","weather_type")):
                self._maybe_play("weather", wtype)
            if not changed or ("crowd_level" in changed):
                self._maybe_play("crowd", ctx.get("crowd_level"))

            # Looped ambience management
            self._update_environment_loop(major=major or biome or region or venue, tod=tod)
            self._update_weather_loop(wtype)
        except Exception:
            pass

    # --- Programmed one-shots API ---
    def play_one_shot(self, category: str, name: str) -> None:
        if not self._enabled or not self._backend:
            return
        try:
            cat = str(category).strip().lower()
            nm = str(name).strip().lower()
            mapping = self._map.get(cat, {})
            file_rel = mapping.get(nm)
            if not file_rel:
                return
            full = self._abs_path(file_rel)
            if not full:
                return
            self._backend.play_sfx(full, category=cat)
        except Exception:
            pass

    # --- Loops helpers ---
    def _update_environment_loop(self, major: Optional[str], tod: Optional[str]) -> None:
        ch = "environment"
        now = time.time()
        if (now - self._loop_last_change_ts.get(ch, 0.0)) < self._loop_min_interval_s:
            return
        target, pool = self._pick_env_loop(major, tod, return_pool=True)
        cur = self._loop_active.get(ch)
        # record pool for rotation
        self._loop_pool[ch] = pool or []
        if target != cur:
            self._loop_last_change_ts[ch] = now
            self._loop_active[ch] = target
            self._loop_next_swap_ts[ch] = now + self._loop_rotation_period_s
            try:
                if target and hasattr(self._backend, "play_sfx_loop"):
                    self._backend.play_sfx_loop(target, channel=ch)  # type: ignore[attr-defined]
                elif hasattr(self._backend, "stop_sfx_loop"):
                    self._backend.stop_sfx_loop(channel=ch)  # type: ignore[attr-defined]
            except Exception:
                pass

    def _update_weather_loop(self, wtype: Optional[str]) -> None:
        ch = "weather"
        now = time.time()
        if (now - self._loop_last_change_ts.get(ch, 0.0)) < self._loop_min_interval_s:
            return
        target, pool = self._pick_weather_loop(wtype, return_pool=True)
        cur = self._loop_active.get(ch)
        self._loop_pool[ch] = pool or []
        if target != cur:
            self._loop_last_change_ts[ch] = now
            self._loop_active[ch] = target
            self._loop_next_swap_ts[ch] = now + self._loop_rotation_period_s
            try:
                if target and hasattr(self._backend, "play_sfx_loop"):
                    self._backend.play_sfx_loop(target, channel=ch)  # type: ignore[attr-defined]
                elif hasattr(self._backend, "stop_sfx_loop"):
                    self._backend.stop_sfx_loop(channel=ch)  # type: ignore[attr-defined]
            except Exception:
                pass

    def _pick_env_loop(self, major: Optional[str], tod: Optional[str], return_pool: bool = False) -> Tuple[Optional[str], List[str]]:
        """Select best environment loop and pool for rotation.
        Returns (best_path, pool_paths). Pool is all files in domain; best favors tokens.
        """
        try:
            root = (self._project_root / "sound" / "sfx" / "loop")
            if not major:
                return (None, [])
            dom = root / major
            if not dom.exists():
                return (None, [])
            files: List[Path] = [p for p in dom.iterdir() if p.is_file() and p.suffix.lower() in {".mp3",".ogg",".wav",".flac"}]
            if not files:
                return (None, [])
            def score(p: Path) -> int:
                name = p.stem.lower()
                s = 0
                if major and major in name: s += 2
                if "loop" in name: s += 1
                if tod and tod in name: s += 2
                return s
            files.sort(key=score, reverse=True)
            best = str(files[0].resolve())
            pool = [str(p.resolve()) for p in files]
            return (best, pool)
        except Exception:
            return (None, [])

    def _rotator_worker(self) -> None:
        # Background rotation of looped channels
        while True:
            try:
                if not self._enabled or not self._backend:
                    time.sleep(1.0)
                    continue
                now = time.time()
                for ch in ("environment", "weather"):
                    target = self._loop_active.get(ch)
                    pool = self._loop_pool.get(ch) or []
                    if not target or not pool:
                        continue
                    if now >= self._loop_next_swap_ts.get(ch, 0.0) and hasattr(self._backend, "play_sfx_loop"):
                        # choose a new file different from current
                        candidates = [p for p in pool if p != target] or pool
                        import random as _rnd
                        new_path = _rnd.choice(candidates)
                        try:
                            self._backend.play_sfx_loop(new_path, channel=ch)  # type: ignore[attr-defined]
                            self._loop_active[ch] = new_path
                        except Exception:
                            pass
                        self._loop_next_swap_ts[ch] = now + self._loop_rotation_period_s
                time.sleep(1.0)
            except Exception:
                time.sleep(1.0)

    def _pick_weather_loop(self, wtype: Optional[str], return_pool: bool = False) -> Tuple[Optional[str], List[str]]:
        try:
            if not wtype:
                return (None, [])
            dom = (self._project_root / "sound" / "sfx" / "loop" / "weather")
            if not dom.exists():
                return (None, [])
            files: List[Path] = [p for p in dom.iterdir() if p.is_file() and p.suffix.lower() in {".mp3",".ogg",".wav",".flac"}]
            if not files:
                return (None, [])
            def score(p: Path) -> int:
                name = p.stem.lower()
                s = 0
                if wtype and wtype in name: s += 3
                if "storm" in name and wtype == "storm": s += 1
                if "thunder" in name and wtype in ("storm","thunder"): s += 1
                if "loop" in name: s += 1
                return s
            files.sort(key=score, reverse=True)
            best = files[0]
            best_path = str(best.resolve()) if score(best) > 0 else None
            pool = [str(p.resolve()) for p in files]
            return (best_path, pool)
        except Exception:
            return (None, [])
