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
import os

try:
    import vlc  # type: ignore
except Exception:  # pragma: no cover - environment may lack VLC
    vlc = None

from core.utils.logging_config import get_logger
logger = get_logger("MUSIC_VLC")

def _dev_music_verbose() -> bool:
    try:
        # Prefer QSettings if available (GUI)
        from PySide6.QtCore import QSettings  # type: ignore
        s = QSettings("RPGGame", "Settings")
        return bool(s.value("dev/enabled", False, type=bool))
    except Exception:
        return False

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
        # Intensity state (0..1) for perceptual gain mapping
        self._intensity: float = 0.3
        self._intensity_gamma: float = 1.8  # perceptual curve; tweakable
        # Looped SFX players by channel (e.g., 'environment', 'weather')
        self._loop_players: dict[str, tuple[object, str]] = {}

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
            # Update loop players effects gain
            try:
                vol = 0 if self._muted else int(self._master * self._effects / 100)
                for ch, (p, _) in list(self._loop_players.items()):
                    try:
                        p.audio_set_volume(vol)
                    except Exception:
                        pass
            except Exception:
                pass

    def set_intensity(self, intensity: float, ramp_ms: int = 250) -> None:
        """Update perceived intensity (0..1) and ramp volume to new target.
        This modulates music gain beneath the master/music sliders using a perceptual curve.
        """
        if not self._enabled:
            return
        with self._lock:
            try:
                new_i = max(0.0, min(1.0, float(intensity)))
            except Exception:
                return
            # If no change, nothing to do
            if abs(new_i - self._intensity) < 1e-6:
                return
            old_target = self._current_target_volume_locked()
            self._intensity = new_i
            new_target = self._current_target_volume_locked()
            self._ramp_current_volume_locked(old_target, new_target, max(0, int(ramp_ms)))

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
            # Dev logging entry
            if _dev_music_verbose():
                try:
                    logger.info(f"[DEV][MUSIC][VLC] apply_state: mood={mood}, intensity={intensity}, track={os.path.basename(track_path) if track_path else None}")
                except Exception:
                    pass
            # Update intensity immediately so crossfade targets include it
            try:
                self._intensity = max(0.0, min(1.0, float(intensity)))
            except Exception:
                pass
            # If no track provided, just apply current volume for intensity change
            if not track_path:
                self._apply_current_volume_locked()
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
                res = player_next.play()
                if _dev_music_verbose():
                    try:
                        logger.info(f"[DEV][MUSIC][VLC] play() returned {res} for {os.path.basename(track_path)}")
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Failed to prepare next media '{track_path}': {e}")
                return
            # Crossfade
            cf_ms = int(transition.get("crossfade_ms", self._crossfade_ms_default))
            self._crossfade_locked(cf_ms)
            # Swap players/state
            self._use_a = not self._use_a
            self._current_path = track_path
            # Apply target volume after crossfade (ensures final gain respects intensity)
            self._apply_current_volume_locked()
            if _dev_music_verbose():
                try:
                    tgt = self._current_target_volume_locked()
                    which = 'A' if self._use_a else 'B'
                    # Gather both players' states for diagnostics
                    try:
                        a_state = self._player_a.get_state()
                        a_vol = self._player_a.audio_get_volume()
                        a_mute = self._player_a.audio_get_mute() if hasattr(self._player_a, 'audio_get_mute') else None
                    except Exception:
                        a_state = None; a_vol = None; a_mute = None
                    try:
                        b_state = self._player_b.get_state()
                        b_vol = self._player_b.audio_get_volume()
                        b_mute = self._player_b.audio_get_mute() if hasattr(self._player_b, 'audio_get_mute') else None
                    except Exception:
                        b_state = None; b_vol = None; b_mute = None
                    logger.info(f"[DEV][MUSIC][VLC] Now active player {which}, target volume={tgt} | A: state={a_state}, vol={a_vol}, mute={a_mute} | B: state={b_state}, vol={b_vol}, mute={b_mute}")
                except Exception:
                    pass

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
            target = self._current_target_volume_locked()
            self._current_player_locked().audio_set_volume(target)
        except Exception:
            pass

    def _current_target_volume_locked(self) -> int:
        try:
            base = 0 if self._muted else int(self._master * self._music / 100)
            gain = self._intensity_gain(self._intensity)
            return int(base * gain)
        except Exception:
            return 0

    def _intensity_gain(self, i: float, floor: float = 0.0) -> float:
        """Map 0..1 intensity to 0..1 perceptual gain with gamma curve and optional floor."""
        try:
            i = max(0.0, min(1.0, float(i)))
            if i <= 0.0:
                return 0.0
            g = i ** float(self._intensity_gamma)
            if floor > 0.0:
                g = floor + (1.0 - floor) * g
            return max(0.0, min(1.0, g))
        except Exception:
            return 0.0

    def _ramp_current_volume_locked(self, start: int, end: int, duration_ms: int) -> None:
        """Ramp the current player's volume from start to end over duration_ms (best-effort)."""
        try:
            cur = self._current_player_locked()
            if duration_ms <= 0:
                cur.audio_set_volume(end)
                return
            steps = max(5, int(duration_ms / 50))
            sleep_s = duration_ms / steps / 1000.0
            for i in range(steps + 1):
                try:
                    vol = int(start + (end - start) * (i/steps))
                    cur.audio_set_volume(vol)
                except Exception:
                    pass
                time.sleep(sleep_s)
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
        # Constant-power-ish fade: approximate with small steps
        steps = max(10, int(duration_ms / 50))
        sleep_s = duration_ms / steps / 1000.0
        self._in_fade = True
        try:
            cur = self._current_player_locked()
            nxt = self._other_player_locked()
            tgt = self._current_target_volume_locked()
            for i in range(steps + 1):
                try:
                    # linear ramp (fallback); constant-power would be sqrt-based
                    vol_out = int(tgt * (1.0 - (i/steps)))
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

    # --- Looped SFX API ---
    def play_sfx_loop(self, file_path: str, channel: str = "environment") -> None:
        if not self._enabled or not file_path:
            return
        with self._lock:
            try:
                current = self._loop_players.get(channel)
                if current and current[1] == file_path:
                    # already playing desired loop; ensure volume
                    try:
                        vol = 0 if self._muted else int(self._master * self._effects / 100)
                        current[0].audio_set_volume(vol)
                    except Exception:
                        pass
                    return
                # stop previous
                if current:
                    try:
                        current[0].stop()
                    except Exception:
                        pass
                player = self._vlc_instance.media_player_new()
                media = self._vlc_instance.media_new(file_path)
                try:
                    # loop indefinitely
                    media.add_option("input-repeat=-1")
                except Exception:
                    pass
                player.set_media(media)
                vol = 0 if self._muted else int(self._master * self._effects / 100)
                try:
                    player.audio_set_volume(vol)
                except Exception:
                    pass
                player.play()
                self._loop_players[channel] = (player, file_path)
            except Exception as e:
                logger.warning(f"Looped SFX start failed: {e}")

    def stop_sfx_loop(self, channel: str = "environment") -> None:
        if not self._enabled:
            return
        with self._lock:
            cur = self._loop_players.pop(channel, None)
            if cur:
                try:
                    cur[0].stop()
                except Exception:
                    pass
