# sound/music_manager.py

import vlc
import os
import random
import logging
import json
import threading
import time
from typing import Dict, List, Optional, Set
from pathlib import Path
from queue import Queue
from dataclasses import dataclass
from datetime import datetime
from PySide6.QtCore import QTimer, QObject, Signal
from core.utils.logging_config import LoggingConfig, LogCategory

@dataclass
class Track:
    """Represents a music track with its metadata"""
    path: str
    mood: str
    duration: float = 0.0
    last_played: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        return os.path.basename(self.path)

class MusicManager(QObject):
    """Manages background music playback with mood-based selection and smooth transitions"""
    stateChanged = Signal(bool)
    
    def __init__(self, root_dir: str = "sound/music", 
                initial_volume: int = 40, 
                crossfade_duration: float = 3.0, 
                default_mood: str = "ambient"):
        super().__init__()
        self.logger = LoggingConfig.get_logger(__name__, LogCategory.MUSIC)
        self.root_dir = Path(root_dir)
        
        # VLC instance and players for crossfading
        self.vlc_instance = vlc.Instance()
        self.current_player = self.vlc_instance.media_player_new()
        self.next_player = self.vlc_instance.media_player_new()
        
        # Track management
        self.tracks: Dict[str, List[Track]] = {}  # mood -> list of tracks
        self.current_track: Optional[Track] = None
        self.next_track_obj: Optional[Track] = None
        self.current_mood: str = default_mood  # set from configuration
        
        # Playback control
        self.is_playing: bool = False
        self.is_muted: bool = False
        self.volume: int = initial_volume  # set from configuration
        self.crossfade_duration: float = crossfade_duration  # set from configuration
        self.played_tracks: Set[str] = set()  # Track rotation management

        self.in_transition = False  # flag to prevent overlapping transitions
        
        # Threading
        self.playback_thread = None
        self.stop_thread = threading.Event()
        self.transition_event = threading.Event()
        self.command_queue = Queue()
        
        # Load tracks
        self._load_tracks()
        
        # Start playback thread
        self._start_playback_thread()
        
        # Log the configuration used for music playback
        self.logger.info(f"MusicManager initialized with volume={self.volume}, "
                        f"crossfade_duration={self.crossfade_duration}, "
                        f"default_mood={self.current_mood}")
        
        self.stateChanged.emit(False)  # Initial state is not playing
        # Add a flag to track first playback
        self.first_playback = True

    def _load_tracks(self) -> None:
        """Load all tracks from the music directory, organizing by mood folders"""
        try:
            self.tracks.clear()
            for mood_dir in self.root_dir.iterdir():
                if mood_dir.is_dir():
                    mood = mood_dir.name
                    self.tracks[mood] = []
                    
                    # Scan for music files
                    for ext in ('*.mp3', '*.wav', '*.flac'):
                        for track_path in mood_dir.glob(ext):
                            # Create media to get duration
                            media = self.vlc_instance.media_new(str(track_path))
                            media.parse()
                            duration = media.get_duration() / 1000.0  # Convert to seconds
                            
                            track = Track(
                                path=str(track_path),
                                mood=mood,
                                duration=duration
                            )
                            self.tracks[mood].append(track)
                            
            self.logger.info(f"Loaded tracks for moods: {list(self.tracks.keys())}")
            
        except Exception as e:
            self.logger.error(f"Error loading tracks: {str(e)}")
            raise

    def _start_playback_thread(self) -> None:
        """Start the background playback management thread"""
        if self.playback_thread is None or not self.playback_thread.is_alive():
            self.stop_thread.clear()
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.playback_thread.start()

    def _playback_loop(self) -> None:
        """Main playback loop handling transitions and track selection"""
        while not self.stop_thread.is_set():
            try:
                # Process any pending commands
                while not self.command_queue.empty():
                    cmd, *args = self.command_queue.get_nowait()
                    self._handle_command(cmd, *args)
                
                if not self.is_playing:
                    time.sleep(0.1)
                    continue
                
                current_pos = self.current_player.get_position()
                if current_pos > 0:  # Ensure we have a valid position
                    time_remaining = (1 - current_pos) * self.current_track.duration
                    
                    # Start transition when approaching end of track
                    if time_remaining <= self.crossfade_duration and not self.transition_event.is_set():
                        self.transition_event.set()
                        self._prepare_next_track()
                        self._start_crossfade()
                    
                    # Check if current track has ended
                    if current_pos >= 0.99:  # Track essentially complete
                        self._finalize_transition()
                        self.transition_event.clear()
                
                time.sleep(0.1)  # Prevent CPU overuse
                
            except Exception as e:
                self.logger.error(f"Error in playback loop: {str(e)}")
                time.sleep(1)  # Prevent rapid error loops

    def _prepare_next_track(self) -> None:
        """Select and prepare the next track to play"""
        try:
            available_tracks = self.tracks[self.current_mood]
            if not available_tracks:
                self.logger.error(f"No tracks available for mood: {self.current_mood}")
                return

            # Reset played tracks if all have been played
            if len(self.played_tracks) >= len(available_tracks):
                self.played_tracks.clear()

            # Select random unplayed track
            unplayed = [t for t in available_tracks if t.path not in self.played_tracks]
            if not unplayed:  # Fallback if somehow all tracks are "played"
                unplayed = available_tracks
                self.played_tracks.clear()

            self.next_track_obj = random.choice(unplayed)
            self.played_tracks.add(self.next_track_obj.path)

            # Prepare the media
            media = self.vlc_instance.media_new(self.next_track_obj.path)
            self.next_player.set_media(media)
            self.next_player.audio_set_volume(0)  # Start silent for crossfade
            
        except Exception as e:
            self.logger.error(f"Error preparing next track: {str(e)}")

    def _start_crossfade(self) -> None:
        """
        When transitioning between moods (or tracks) due to a mood change command,
        perform a sequential fade-out and fade-in.
        The old track will fade out over 4 seconds (from full volume to 0),
        then the new track will start and fade in over 4 seconds.
        """
        try:
            if self.in_transition:
                return
            self.in_transition = True
            if not self.next_track_obj or not self.next_player.get_media():
                self.in_transition = False
                return

            # Fade out the current track over 4 seconds
            fade_out_duration = 4.0
            steps_out = int(fade_out_duration * 10)  # 10 steps per second
            fade_sleep_out = fade_out_duration / steps_out
            for i in range(steps_out):
                if self.stop_thread.is_set():
                    break
                new_vol = int(self.volume * (steps_out - i) / steps_out)
                self.current_player.audio_set_volume(new_vol)
                time.sleep(fade_sleep_out)

            # Stop the old track after fade-out
            self.current_player.stop()

            # Start the new track and fade it in over 4 seconds
            self.next_player.play()
            steps_in = int(4.0 * 10)  # 4 seconds fade-in at 10 steps/second
            fade_sleep_in = 4.0 / steps_in
            for i in range(steps_in):
                if self.stop_thread.is_set():
                    break
                vol = int(self.volume * (i + 1) / steps_in)
                self.next_player.audio_set_volume(vol)
                time.sleep(fade_sleep_in)
        except Exception as e:
            self.logger.error("Error during crossfade: " + str(e))
        finally:
            self._finalize_transition()

    def update_settings(self, volume: int = None, crossfade_duration: float = None, default_mood: str = None) -> None:
        """Update music manager settings after initialization"""
        if volume is not None:
            self.volume = volume
            self.command_queue.put(("volume", volume))
            self.logger.info(f"Updated volume to {volume}")
        
        if crossfade_duration is not None:
            self.crossfade_duration = crossfade_duration
            self.logger.info(f"Updated crossfade duration to {crossfade_duration}")
        
        if default_mood is not None and default_mood in self.tracks:
            if default_mood != self.current_mood:
                self.logger.info(f"Updated default mood from {self.current_mood} to {default_mood}")
                self.current_mood = default_mood
                if self.is_playing:
                    self.command_queue.put(("mood", default_mood))
            else:
                self.logger.debug(f"Mood unchanged: {default_mood}")

    def _finalize_transition(self) -> None:
        try:
            self.current_player.stop()
            self.current_player, self.next_player = self.next_player, self.current_player
            self.current_track = self.next_track_obj
            self.next_track_obj = None
            if self.current_track:
                self.current_player.audio_set_volume(self.volume)
                self.logger.debug(f"Transitioned to track: {self.current_track.name}")
                # Ensure the new track starts playing
                self.current_player.play()
                self.is_playing = True
                self.stateChanged.emit(True)
            else:
                self.logger.debug("No next track available. Preparing a new track.")
                self._prepare_next_track()
                if self.next_track_obj:
                    self.current_track = self.next_track_obj
                    self.next_track_obj = None
                    media = self.vlc_instance.media_new(self.current_track.path)
                    self.current_player.set_media(media)
                    self.current_player.audio_set_volume(self.volume)
                    self.current_player.play()
                    self.is_playing = True
        except Exception as e:
            self.logger.error(f"Error finalizing transition: {str(e)}")
        finally:
            self.in_transition = False

    def _handle_command(self, cmd: str, *args) -> None:
        """Handle playback control commands"""
        try:
            if cmd == "play":
                # Existing code...
                self.current_player.play()
                self.current_player.audio_set_volume(self.volume)
                self.is_playing = True
                # Emit signal for state change
                self.stateChanged.emit(True)
                    
            elif cmd == "pause":
                self.current_player.pause()
                self.is_playing = False
                # Emit signal for state change
                self.stateChanged.emit(False)
                
            elif cmd == "stop":
                self.current_player.stop()
                self.is_playing = False
                
            elif cmd == "next":
                self.transition_event.set()
                self._prepare_next_track()
                self._start_crossfade()
                
            elif cmd == "volume":
                volume = args[0]
                self.volume = max(0, min(100, volume))
                if not self.is_muted:
                    self.current_player.audio_set_volume(self.volume)
                    if self.next_player.is_playing():
                        self.next_player.audio_set_volume(self.volume)
                        
            elif cmd == "mute":
                self.is_muted = not self.is_muted
                vol = 0 if self.is_muted else self.volume
                self.current_player.audio_set_volume(vol)
                if self.next_player.is_playing():
                    self.next_player.audio_set_volume(vol)
                    
            elif cmd == "mood":
                new_mood = args[0]
                if new_mood not in self.tracks:
                    self.logger.warning(f"Unknown mood: {new_mood}")
                else:
                    if new_mood != self.current_mood:
                        self.logger.info(f"Changing mood from {self.current_mood} to {new_mood}. Initiating immediate transition.")
                        self.current_mood = new_mood
                        self.transition_event.set()
                        self._prepare_next_track()
                        self._start_crossfade()
                    else:
                        self.logger.info(f"Music mood remains unchanged: {new_mood}")
                        # ADD THIS SECTION: Start playing if not already playing, regardless of mood change
                        if not self.is_playing or not self.current_player.is_playing():
                            self.logger.info("Music not currently playing - starting playback with current mood")
                            self._prepare_next_track()
                            self.current_track = self.next_track_obj
                            self.next_track_obj = None
                            media = self.vlc_instance.media_new(self.current_track.path)
                            self.current_player.set_media(media)
                            self.current_player.audio_set_volume(self.volume)
                            self.current_player.play()
                            self.is_playing = True
                            self.stateChanged.emit(True)
                    
        except Exception as e:
            self.logger.error(f"Error handling command {cmd}: {str(e)}")

    # Public Control Interface

    def play(self) -> None:
        """Start or resume playback"""
        self.command_queue.put(("play",))
        # Update internal state immediately for better responsiveness
        self.is_playing = True
        self.stateChanged.emit(True)

    def pause(self) -> None:
        """Pause playback"""
        self.command_queue.put(("pause",))
        # Update internal state immediately for better responsiveness
        self.is_playing = False
        self.stateChanged.emit(False)

    def stop(self) -> None:
        """Stop playback"""
        self.command_queue.put(("stop",))

    def next_track(self) -> None:
        """Skip to next track"""
        self.command_queue.put(("next",))

    def set_volume(self, volume: int) -> None:
        """Set volume level (0-100)"""
        self.command_queue.put(("volume", volume))

    def toggle_mute(self) -> None:
        """Toggle mute state"""
        self.command_queue.put(("mute",))

    def change_mood(self, mood: str) -> None:
        """Change the current mood/playlist"""
        self.command_queue.put(("mood", mood))

    def get_current_track_info(self) -> dict:
        """Get information about the currently playing track with improved status detection"""
        if not self.current_track:
            return {"status": "stopped", "mood": self.current_mood}
        
        # More reliable status detection using VLC's state
        state = self.current_player.get_state()
        if state in (vlc.State.Playing, vlc.State.Opening):
            playing_status = "playing"
        elif state == vlc.State.Paused:
            playing_status = "paused"
        else:
            playing_status = "stopped"
        
        # Update internal flag to match actual state
        self.is_playing = playing_status == "playing"
        
        return {
            "status": playing_status,
            "track": self.current_track.name,
            "mood": self.current_track.mood,
            "position": self.current_player.get_position(),
            "volume": self.volume,
            "muted": self.is_muted
        }

    def cleanup(self) -> None:
        """Clean up resources before shutdown"""
        self.stop_thread.set()
        if self.playback_thread:
            self.playback_thread.join(timeout=self.crossfade_duration + 1)
        self.current_player.stop()
        self.next_player.stop()

    def reset(self, new_mood: str, use_crossfade: bool = True) -> None:
        """
        Reset the MusicManager for a new/loaded game.
        If use_crossfade is True and there is an active track whose mood differs from new_mood,
        then crossfade into a new track for the new mood.
        Afterwards, clear internal state and start playback.
        """
        try:
            self.logger.info("Resetting MusicManager with new mood: " + new_mood)
            current_info = self.get_current_track_info()
            if use_crossfade and self.current_track is not None and current_info.get("mood", "ambient") != new_mood:
                # Prepare new ambient track and crossfade from current track
                self._prepare_next_track()  # sets self.next_track_obj
                self._start_crossfade()
            else:
                self.stop()
            # Clear any pending commands
            while not self.command_queue.empty():
                self.command_queue.get_nowait()
            self.is_playing = False
            self.transition_event.clear()
            self.played_tracks.clear()
            self.current_mood = new_mood
            self.current_track = None
            self.next_track_obj = None
            # Start playback automatically (ambient tracks will be played)
            self.play()
        except Exception as e:
            self.logger.error("Error in MusicManager.reset: " + str(e))


