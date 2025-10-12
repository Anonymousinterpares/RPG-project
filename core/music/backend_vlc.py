#!/usr/bin/env python3
"""
VLC-based desktop music backend implementing MusicBackend.
Provides dual-player crossfades, stinger ducking, and basic SFX playback.
This is intentionally conservative: if VLC is unavailable or a media load fails,
we log and continue without crashing.
"""
from __future__ import annotations
import threading
import time
from typing import Optional, Dict

try:
    import vlc  # type: ignore
except Exception:  # pragma: no cover - environment may lack VLC
    vlc = None

from core.utils.logging_config import get_logger
logger = get_logger("MUSIC_VLC")

class VLCBackend:
    def __init__(self):
        self._lock = threading.RLock()
        self._enabled = vlc is not None
        self._master = 100
        self._music = 100
        self._effects = 100
        self._muted = False
        self._crossfade_ms_default = 3000
        self._in_fade = False
        self._current_path: Optional[str] = None
        self._next_path: Optional[str] = None
        self._vol_loudness_db: float = 0.0

        if self._enabled:
            try:
                self._vlc_instance = vlc.Instance()
                self._player_a = self._vlc_instance.media_player_new()
                self._player_b = self._vlc_instance.media_player_new()
                self._use_a = True  # which player is active
                logger.info("VLC backend initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize VLC instance: {e}")
                self._enabled = False
        else:
            logger.warning("python-vlc not available; VLC backend disabled (no-op)")

    # --- Public API ---
    def set_volumes(self, master: int, music: int, effects: int, muted: bool) -> None:
        with self._lock:
            self._master = max(0, min(100, int(master)))
            self._music = max(0, min(100, int(music)))
            self._effects = max(0, min(100, int(effects)))
            self._muted = bool(muted)
            self._apply_current_volume_locked()

    def next_track(self) -> None:
        # The director will set apply_state with a new track_path; backend doesn't pick tracks alone.
        # We keep this as a no-op placeholder or stop current and let director re-apply state soon.
        with self._lock:
            # Gentle fade-out then restart same player (director should call apply_state quickly with next track)
            self._fade_out_current_locked(500)

    def play_stinger(self, file_path: str, duck_db: float, restore_ms: int) -> None:
        if not self._enabled or not file_path:
            return
        try:
            st_player = self._vlc_instance.media_player_new()
            media = self._vlc_instance.media_new(file_path)
            st_player.set_media(media)
            # Duck current
            self._duck_locked(duck_db)
            st_player.play()
            # Monitor until end in a small thread
            def _wait_and_restore():
                try:
                    # wait up to 10s
                    for _ in range(100):
                        time.sleep(0.1)
                        if st_player.get_state() in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error):
                            break
                except Exception:
                    pass
                finally:
                    try:
                        st_player.stop()
                    except Exception:
                        pass
                    self._restore_duck_locked(restore_ms)
            threading.Thread(target=_wait_and_restore, daemon=True).start()
        except Exception as e:
            logger.warning(f"Stinger playback failed: {e}")

    def play_sfx(self, file_path: str, category: str) -> None:
        if not self._enabled or not file_path:
            return
        try:
            sfx = self._vlc_instance.media_player_new()
            media = self._vlc_instance.media_new(file_path)
            sfx.set_media(media)
            # Set effects volume scaled by master
            vol = 0 if self._muted else int(self._master * self._effects / 100)
            sfx.audio_set_volume(vol)
            sfx.play()
            # Let VLC clean this up as it ends
        except Exception as e:
            logger.warning(f"SFX playback failed: {e}")

    def apply_state(self,
                    mood: str,
                    intensity: float,
                    track_path: Optional[str],
                    transition: Dict) -> None:
        if not self._enabled:
            return
        with self._lock:
            # If no track provided, do nothing; director may be testing mood only
            if not track_path:
                return
            # If same track and we're already playing, keep going (no forced restart)
            if self._current_path == track_path and self._is_current_playing_locked():
                self._apply_current_volume_locked()
                return
            # Set up next player with media
            try:
                player_next = self._player_b if self._use_a else self._player_a
                media = self._vlc_instance.media_new(track_path)
                player_next.set_media(media)
                # Start silent
                player_next.audio_set_volume(0)
                player_next.play()
            except Exception as e:
                logger.warning(f"Failed to prepare next media '{track_path}': {e}")
                return
            # Crossfade
            cf_ms = int(transition.get("crossfade_ms", self._crossfade_ms_default))
            self._crossfade_locked(cf_ms)
            # Swap players/state
            self._use_a = not self._use_a
            self._current_path = track_path
            # Apply target volume after crossfade
            self._apply_current_volume_locked()

    # --- Internals ---
    def _is_current_playing_locked(self) -> bool:
        try:
            p = self._player_a if self._use_a else self._player_b
            st = p.get_state()
            return st in (vlc.State.Opening, vlc.State.Playing)
        except Exception:
            return False

    def _current_player_locked(self):
        return self._player_a if self._use_a else self._player_b

    def _other_player_locked(self):
        return self._player_b if self._use_a else self._player_a

    def _apply_current_volume_locked(self) -> None:
        try:
            target = 0 if self._muted else int(self._master * self._music / 100)
            self._current_player_locked().audio_set_volume(target)
        except Exception:
            pass

    def _crossfade_locked(self, duration_ms: int) -> None:
        if duration_ms <= 0:
            try:
                # immediate swap: stop old, start new at target volume
                self._other_player_locked().audio_set_volume(0)
                self._current_player_locked().stop()
                return
            except Exception:
                return
        # Constant-power-ish fade: approximate with 20 steps
        steps = max(10, int(duration_ms / 50))
        sleep_s = duration_ms / steps / 1000.0
        self._in_fade = True
        try:
            cur = self._current_player_locked()
            nxt = self._other_player_locked()
            tgt = 0 if self._muted else int(self._master * self._music / 100)
            for i in range(steps + 1):
                try:
                    # theta 0..pi/2
                    theta = (i / steps) * 1.57079632679
                    vol_out = int(tgt * (1.0 - ( (i/steps) )))  # linear fallback
                    vol_in  = int(tgt * (i/steps))
                    cur.audio_set_volume(vol_out)
                    nxt.audio_set_volume(vol_in)
                except Exception:
                    pass
                time.sleep(sleep_s)
            try:
                cur.stop()
            except Exception:
                pass
        finally:
            self._in_fade = False

    def _fade_out_current_locked(self, duration_ms: int) -> None:
        try:
            cur = self._current_player_locked()
            if duration_ms <= 0:
                cur.audio_set_volume(0)
                return
            steps = max(5, int(duration_ms / 50))
            sleep_s = duration_ms / steps / 1000.0
            start = int(self._master * self._music / 100)
            for i in range(steps + 1):
                try:
                    vol = int(start * (1 - i/steps))
                    cur.audio_set_volume(vol)
                except Exception:
                    pass
                time.sleep(sleep_s)
        except Exception:
            pass

    def _duck_locked(self, duck_db: float) -> None:
        try:
            # crude: reduce volume by factor; 6 dB ~ half power; we'll use 8 dB ≈ ~0.4
            factor = 10 ** (-abs(duck_db) / 20.0)
            cur = self._current_player_locked()
            current_vol = max(0, cur.audio_get_volume())
            new_vol = int(current_vol * factor)
            cur.audio_set_volume(new_vol)
        except Exception:
            pass

    def _restore_duck_locked(self, restore_ms: int) -> None:
        try:
            cur = self._current_player_locked()
            target = 0 if self._muted else int(self._master * self._music / 100)
            if restore_ms <= 0:
                cur.audio_set_volume(target)
                return
            steps = max(5, int(restore_ms / 50))
            sleep_s = restore_ms / steps / 1000.0
            start = max(0, cur.audio_get_volume())
            for i in range(steps + 1):
                try:
                    vol = int(start + (target - start) * (i/steps))
                    cur.audio_set_volume(vol)
                except Exception:
                    pass
                time.sleep(sleep_s)
        except Exception:
            pass