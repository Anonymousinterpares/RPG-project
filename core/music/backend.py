#!/usr/bin/env python3
"""
Abstract interfaces for music and SFX backends.
Backends implement platform/runtime-specific playback (e.g., VLC for desktop,
Web Audio in browser – the latter lives client-side and is not represented here).
"""
from __future__ import annotations
from typing import Optional, Protocol, Dict

class MusicBackend(Protocol):
    """Protocol for music playback backends (desktop)."""

    def apply_state(self,
                    mood: str,
                    intensity: float,
                    track_path: Optional[str],
                    transition: Dict) -> None:
        """
        Apply a new music state.
        transition may include:
          - crossfade_ms: int
          - stinger: Optional[dict]
          - loudness_offset_db: float
        """
        ...

    def set_volumes(self, master: int, music: int, effects: int, muted: bool) -> None:
        """Set master/music/effects volume levels (0-100) and mute flag."""
        ...

    def set_intensity(self, intensity: float, ramp_ms: int = 250) -> None:
        """Set perceived intensity (0..1) and optionally ramp gain to the new target over ramp_ms."""
        ...

    def next_track(self) -> None:
        """Request the backend to proceed to the next track within the current mood/playlist."""
        ...

    def play_stinger(self, file_path: str, duck_db: float, restore_ms: int) -> None:
        """Play a stinger over the current music with ducking. Safe to no-op if unsupported."""
        ...

    def play_sfx(self, file_path: str, category: str) -> None:
        """Play a one-shot SFX. Category may inform routing/volume caps."""
        ...

    # Optional looped SFX API (used when available)
    def play_sfx_loop(self, file_path: str, channel: str) -> None:  # pragma: no cover - optional
        ...

    def stop_sfx_loop(self, channel: str) -> None:  # pragma: no cover - optional
        ...
