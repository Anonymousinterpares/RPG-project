#!/usr/bin/env python3
"""
PySide6.QtMultimedia-based desktop music backend.
Provides dual-player crossfades, low-latency SFX, and looping.
"""
from __future__ import annotations
import threading
import time
from typing import Optional, Dict
import os
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QSoundEffect

from core.utils.logging_config import get_logger
logger = get_logger("MUSIC_QT")

class QtMultimediaBackend:
    def __init__(self):
        self._lock = threading.RLock()
        self._master = 100
        self._music = 100
        self._effects = 100
        self._muted = False
        self._on_track_end = None
        self._crossfade_ms_default = 3000
        self._current_path: Optional[str] = None

        # Music players
        self._player_a = QMediaPlayer()
        self._player_b = QMediaPlayer()
        self._audio_output_a = QAudioOutput()
        self._audio_output_b = QAudioOutput()
        self._player_a.setAudioOutput(self._audio_output_a)
        self._player_b.setAudioOutput(self._audio_output_b)
        self._use_a = True

        # SFX management
        self._active_sfx: list[QSoundEffect] = []

        # Looped SFX players
        self._sfx_loop_players: Dict[str, QMediaPlayer] = {}
        self._sfx_loop_outputs: Dict[str, QAudioOutput] = {}
        for channel in ["environment", "weather"]:
            player = QMediaPlayer()
            output = QAudioOutput()
            player.setAudioOutput(output)
            self._sfx_loop_players[channel] = player
            self._sfx_loop_outputs[channel] = output

        # Connect signals
        self._player_a.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player_b.mediaStatusChanged.connect(self._on_media_status_changed)

        logger.info("QtMultimedia backend initialized")

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self._on_track_end:
                # Run callback in a timer to avoid issues with signal context
                QTimer.singleShot(0, self._on_track_end)

    def set_volumes(self, master: int, music: int, effects: int, muted: bool) -> None:
        with self._lock:
            self._master = max(0, min(100, int(master)))
            self._music = max(0, min(100, int(music)))
            self._effects = max(0, min(100, int(effects)))
            self._muted = bool(muted)
            self._apply_current_volume_locked()
            
            # Also update loop volumes
            loop_vol = 0 if self._muted else (self._master / 100.0) * (self._effects / 100.0)
            for output in self._sfx_loop_outputs.values():
                output.setVolume(loop_vol)

    def _apply_current_volume_locked(self):
        vol = 0 if self._muted else (self._master / 100.0) * (self._music / 100.0)
        active_output = self._audio_output_a if self._use_a else self._audio_output_b
        active_output.setVolume(vol)
        # Apply to inactive player too, so it's correct on next fade
        inactive_output = self._audio_output_b if self._use_a else self._audio_output_a
        inactive_output.setVolume(vol)

    def apply_state(self, mood: str, intensity: float, track_path: Optional[str], transition: Dict) -> None:
        if not track_path:
            self._player_a.stop()
            self._player_b.stop()
            self._current_path = None
            return

        with self._lock:
            if self._current_path == track_path:
                return

            self._current_path = track_path
            
            player_next = self._player_b if self._use_a else self._player_a
            output_next = self._audio_output_b if self._use_a else self._audio_output_a
            
            player_current = self._player_a if self._use_a else self._player_b
            output_current = self._audio_output_a if self._use_a else self._audio_output_b

            url = QUrl.fromLocalFile(track_path)
            player_next.setSource(url)
            
            loop = transition.get("loop_single", False)
            player_next.setLoops(QMediaPlayer.Loops.Infinite if loop else 1)

            cf_ms = transition.get("crossfade_ms", self._crossfade_ms_default)
            
            # If current player is not playing anything, just start the next one
            if player_current.mediaStatus() == QMediaPlayer.MediaStatus.NoMedia:
                self._apply_current_volume_locked()
                player_next.play()
            else:
                self._crossfade(output_current, output_next, cf_ms)
                player_next.play()

            self._use_a = not self._use_a

    def _crossfade(self, fade_out_output, fade_in_output, duration_ms):
        steps = 50
        step_interval = duration_ms / steps
        
        target_volume = 0 if self._muted else (self._master / 100.0) * (self._music / 100.0)
        
        fade_in_output.setVolume(0)

        def fade_step(step):
            if step <= steps:
                out_vol = target_volume * (1 - (step / steps))
                in_vol = target_volume * (step / steps)
                fade_out_output.setVolume(out_vol)
                fade_in_output.setVolume(in_vol)
                QTimer.singleShot(step_interval, lambda: fade_step(step + 1))
            else:
                fade_out_output.setVolume(0)
                (self._player_b if self._use_a else self._player_a).stop()


        fade_step(1)

    def play_sfx(self, file_path: str, category: str) -> None:
        try:
            sfx = QSoundEffect()
            self._active_sfx.append(sfx)
            
            sfx.setSource(QUrl.fromLocalFile(file_path))
            vol = 0 if self._muted else (self._master / 100.0) * (self._effects / 100.0)
            sfx.setVolume(vol)
            
            # Connect a slot to clean up the QSoundEffect object after it finishes
            sfx.playingChanged.connect(lambda: self._on_sfx_finished(sfx))
            
            sfx.play()
        except Exception as e:
            logger.error(f"SFX playback failed: {e}")

    def _on_sfx_finished(self, sfx_instance: QSoundEffect):
        """Removes a finished QSoundEffect instance from the active list."""
        if not sfx_instance.isPlaying():
            try:
                self._active_sfx.remove(sfx_instance)
                sfx_instance.deleteLater() # Ensure Qt cleans up the object
            except ValueError:
                # May have already been removed, which is fine
                pass

    def set_track_end_callback(self, callback):
        self._on_track_end = callback
        
    def play_sfx_loop(self, file_path: str, channel: str = "environment") -> None:
        if channel in self._sfx_loop_players:
            try:
                player = self._sfx_loop_players[channel]
                output = self._sfx_loop_outputs[channel]
                
                player.setSource(QUrl.fromLocalFile(file_path))
                player.setLoops(QMediaPlayer.Loops.Infinite)
                
                vol = 0 if self._muted else (self._master / 100.0) * (self._effects / 100.0)
                output.setVolume(vol)
                
                player.play()
                logger.info(f"Started SFX loop on channel '{channel}': {file_path}")
            except Exception as e:
                logger.error(f"Failed to play SFX loop on channel '{channel}': {e}")

    def stop_sfx_loop(self, channel: str = "environment") -> None:
        if channel in self._sfx_loop_players:
            try:
                self._sfx_loop_players[channel].stop()
                logger.info(f"Stopped SFX loop on channel '{channel}'")
            except Exception as e:
                logger.error(f"Failed to stop SFX loop on channel '{channel}': {e}")
