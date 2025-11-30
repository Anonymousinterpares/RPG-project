"""
Placeholder Text-to-Speech (TTS) Manager.
"""
from typing import Optional
from PySide6.QtCore import QObject, Signal, QTimer, Slot

from core.utils.logging_config import get_logger

logger = get_logger("TTS_MANAGER")

class TTSManager(QObject):
    """
    Manages Text-to-Speech functionality.
    Currently a placeholder that simulates playback.
    """
    ttsPlaybackComplete = Signal()
    # Signal to indicate if TTS is enabled/disabled, could be useful for UI
    tts_status_changed = Signal(bool) 

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._is_enabled: bool = False # Default to disabled
        self._playback_timer: QTimer = QTimer(self)
        self._playback_timer.setSingleShot(True)
        self._playback_timer.timeout.connect(self._on_playback_finished)
        self._character_rate_ms = 50 # Milliseconds per character for simulation

        logger.info("TTSManager initialized (Placeholder).")
        # TODO: Load enabled state from settings

    @property
    def is_enabled(self) -> bool:
        """Returns True if TTS is currently enabled."""
        return self._is_enabled

    def set_enabled(self, enabled: bool):
        """Enables or disables TTS."""
        if self._is_enabled != enabled:
            self._is_enabled = enabled
            logger.info(f"TTS functionality set to: {'Enabled' if enabled else 'Disabled'}")
            self.tts_status_changed.emit(enabled) # Emit signal on status change
            if not enabled and self._playback_timer.isActive():
                self.stop_playback() # Stop current playback if disabled

    def speak(self, text: str):
        """
        Speaks the given text using TTS.
        If TTS is disabled or text is empty, emits ttsPlaybackComplete immediately.
        """
        if not self._is_enabled:
            logger.debug("TTS speak called but TTS is disabled. Emitting completion immediately.")
            self.ttsPlaybackComplete.emit()
            return

        if not text or not text.strip():
            logger.debug("TTS speak called with empty text. Emitting completion immediately.")
            self.ttsPlaybackComplete.emit()
            return

        if self._playback_timer.isActive():
            logger.warning("TTS speak called while previous playback was active. Stopping previous.")
            self._playback_timer.stop() # Stop previous timer

        # Simulate playback duration
        # For a real TTS, this would involve calls to a TTS engine
        # and waiting for its completion callback.
        simulated_duration_ms = len(text) * self._character_rate_ms
        # Add a minimum duration to avoid ultra-short timers for very short text
        simulated_duration_ms = max(simulated_duration_ms, 250) 
        
        logger.info(f"TTS (Simulated) Speaking: '{text[:50]}...' (Duration: {simulated_duration_ms}ms)")
        self._playback_timer.start(simulated_duration_ms)

    def stop_playback(self):
        """Stops any ongoing TTS playback immediately."""
        if self._playback_timer.isActive():
            self._playback_timer.stop()
            logger.info("TTS playback stopped.")
            # Emit completion because we've effectively finished (by stopping)
            self.ttsPlaybackComplete.emit() 

    @Slot()
    def _on_playback_finished(self):
        """Called when the simulated TTS playback timer finishes."""
        logger.info("TTS (Simulated) playback finished.")
        self.ttsPlaybackComplete.emit()
        
    def set_character_rate(self, rate_ms: int):
        """Sets the simulated milliseconds per character for playback speed."""
        if rate_ms > 0:
            self._character_rate_ms = rate_ms
            logger.debug(f"TTS simulated character rate set to {rate_ms}ms.")
        else:
            logger.warning(f"Invalid TTS character rate: {rate_ms}. Must be > 0.")