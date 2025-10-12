#!/usr/bin/env python3
"""
MusicDirector: authoritative orchestrator for music state.
- Maintains mood/intensity/mute/volume state
- Selects tracks per mood (folder-based) with rotation fairness
- Applies transitions via the desktop backend (if present)
- Notifies listeners (e.g., web server) of state changes

This v1 focuses on core flow for Milestone 1. Advanced features (stingers, layers,
loudness normalization manifests) are stubbed and safe to ignore if absent.
"""
from __future__ import annotations
import os
import random
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from core.utils.logging_config import get_logger
logger = get_logger("MUSIC_DIRECTOR")

ALLOWED_EXTS = {".mp3", ".ogg", ".wav", ".flac"}

class MusicDirector:
    def __init__(self, project_root: Optional[str] = None):
        self._lock = threading.RLock()
        self._listeners: List[Callable[[Dict], None]] = []
        self._backend = None  # type: ignore
        self._project_root = Path(project_root or os.getcwd())
        # State
        self._mood: str = "ambient"
        self._intensity: float = 0.3
        self._muted: bool = False
        self._master: int = 100
        self._music: int = 100
        self._effects: int = 100
        self._current_track: Optional[str] = None  # absolute path (desktop)
        self._rotation: Dict[str, List[str]] = {}
        self._played: Dict[str, set] = {}
        # Scan once on init
        try:
            self._scan_tracks()
        except Exception as e:
            logger.warning(f"Music scan failed: {e}")

    # --- Public API ---
    def set_backend(self, backend) -> None:
        with self._lock:
            self._backend = backend
            # ensure current volumes/mute are applied
            if self._backend:
                self._backend.set_volumes(self._master, self._music, self._effects, self._muted)

    def set_volumes(self, master: int, music: int, effects: int) -> None:
        with self._lock:
            self._master = max(0, min(100, int(master)))
            self._music = max(0, min(100, int(music)))
            self._effects = max(0, min(100, int(effects)))
            if self._backend:
                self._backend.set_volumes(self._master, self._music, self._effects, self._muted)
            self._emit_state_locked(reason="volumes_changed")

    def set_muted(self, muted: bool) -> None:
        with self._lock:
            self._muted = bool(muted)
            if self._backend:
                self._backend.set_volumes(self._master, self._music, self._effects, self._muted)
            self._emit_state_locked(reason="muted_changed")

    def hard_set(self, mood: str, intensity: Optional[float] = None, reason: str = "") -> None:
        with self._lock:
            self._mood = (mood or "ambient").lower()
            if intensity is not None:
                self._intensity = float(max(0.0, min(1.0, intensity)))
            track = self._select_next_track_locked(self._mood)
            self._apply_locked(track, reason or "hard_set")

    def suggest(self, mood: str, intensity: float, source: str, confidence: float, evidence: str = "") -> None:
        # Milestone 1: accept all suggestions (later: thresholds/hysteresis)
        with self._lock:
            self._mood = (mood or self._mood).lower()
            self._intensity = float(max(0.0, min(1.0, intensity if intensity is not None else self._intensity)))
            track = self._select_next_track_locked(self._mood)
            self._apply_locked(track, f"suggest:{source}:{confidence:.2f}")

    def next_track(self, reason: str = "user_skip") -> None:
        with self._lock:
            track = self._select_next_track_locked(self._mood, force_unplayed=True)
            self._apply_locked(track, reason)

    def add_state_listener(self, callback: Callable[[Dict], None]) -> None:
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    # --- Internals ---
    def _scan_tracks(self) -> None:
        base = (self._project_root / "sound" / "music")
        if not base.exists():
            logger.info(f"No sound/music directory at {base}")
            return
        for mood_dir in base.iterdir():
            if not mood_dir.is_dir():
                continue
            mood = mood_dir.name.lower()
            files: List[str] = []
            for p in mood_dir.iterdir():
                if p.is_file() and p.suffix.lower() in ALLOWED_EXTS:
                    files.append(str(p.resolve()))
            files.sort()
            self._rotation[mood] = files
            self._played[mood] = set()
        logger.info(f"MusicDirector scanned moods: {list(self._rotation.keys())}")

    def _select_next_track_locked(self, mood: str, force_unplayed: bool = False) -> Optional[str]:
        pool = self._rotation.get(mood) or []
        if not pool:
            # no tracks for this mood; keep current
            return self._current_track
        # compute unplayed set
        unplayed = [p for p in pool if p not in self._played.get(mood, set())]
        if not unplayed:
            # reset rotation
            self._played[mood] = set()
            unplayed = pool[:]
        # If forcing unplayed to change track, remove current from candidates if possible
        candidates = unplayed if force_unplayed else pool
        if self._current_track in candidates and len(candidates) > 1:
            candidates = [c for c in candidates if c != self._current_track]
        choice = random.choice(candidates) if candidates else self._current_track
        if choice:
            self._played[mood].add(choice)
        return choice

    def _apply_locked(self, track: Optional[str], reason: str) -> None:
        # Apply to backend (desktop)
        transition = {"crossfade_ms": 3000}
        if self._backend:
            try:
                self._backend.apply_state(self._mood, self._intensity, track, transition)
            except Exception as e:
                logger.warning(f"Backend apply_state failed: {e}")
        # Update current and notify
        self._current_track = track or self._current_track
        self._emit_state_locked(reason=reason)

    def _emit_state_locked(self, reason: str) -> None:
        payload = {
            "mood": self._mood,
            "intensity": self._intensity,
            "track": os.path.basename(self._current_track) if self._current_track else None,
            "track_path": self._current_track,
            # web URL (if file is under sound/): replace project_root with /sound
            "url": self._to_web_url(self._current_track),
            "muted": self._muted,
            "master": self._master,
            "music": self._music,
            "effects": self._effects,
            "reason": reason,
        }
        for cb in list(self._listeners):
            try:
                cb(payload)
            except Exception as e:
                logger.debug(f"MusicDirector listener error: {e}")

    def _to_web_url(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        try:
            p = Path(path).resolve()
            base = (self._project_root / "sound").resolve()
            if str(p).startswith(str(base)):
                relative = p.relative_to(base)
                # web served under /sound
                return f"/sound/{relative.as_posix()}"
        except Exception:
            pass
        return None

# Convenience accessor for construction elsewhere if desired
_director_singleton: Optional[MusicDirector] = None

def get_music_director(project_root: Optional[str] = None) -> MusicDirector:
    global _director_singleton
    if _director_singleton is None:
        _director_singleton = MusicDirector(project_root=project_root)
    return _director_singleton