import os
import logging
from typing import Optional, List
from PySide6.QtCore import QObject, Signal, QSettings

logger = logging.getLogger("AUDIO_CTRL")

class GameAudioController(QObject):
    """
    Manages audio backend initialization and playback state aggregation.
    """
    # Emitted when music/SFX playback state changes (list of display strings)
    playback_updated = Signal(object)
    # Emitted with full MusicDirector state (dict) when music changes
    music_state_updated = Signal(object)

    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        self._playing_snapshot: list[str] = []
        self._last_music_item: Optional[str] = None
        self._last_sfx_items: list[str] = []
        self._music_backend = None

    def init_audio_backend(self):
        """Initialize the audio backend."""
        try:
            import os as _os
            web_mode = str(_os.environ.get("RPG_WEB_MODE", "0")) == "1"
            
            music_director = self._engine._music_director
            sfx_manager = self._engine._sfx_manager

            if not web_mode:
                # Desktop/GUI: use QtMultimedia backend
                from core.music.backend_qt import QtMultimediaBackend
                self._music_backend = QtMultimediaBackend()
                
                if music_director:
                    music_director.set_backend(self._music_backend)
                    # Subscribe to playback updates
                    music_director.add_state_listener(self._on_music_state)
                
                if sfx_manager:
                    sfx_manager.set_backend(self._music_backend)
                    sfx_manager.add_listener(self._on_sfx_update)

                # Apply QSettings sound immediately
                s = QSettings("RPGGame", "Settings")
                master = int(s.value("sound/master_volume", 100))
                music  = int(s.value("sound/music_volume", 100))
                effects= int(s.value("sound/effects_volume", 100))
                enabled= s.value("sound/enabled", True, type=bool)
                muted = not bool(enabled)
                
                if music_director:
                    music_director.set_volumes(master, music, effects)
                    music_director.set_muted(muted)
                
                logger.info(f"Music/SFX system initialized (QtMultimedia backend, enabled={bool(enabled)}, master={master}, music={music}, effects={effects})")
                
                # Expose play method to engine for backward compatibility
                if sfx_manager:
                    self._engine.sfx_play = getattr(sfx_manager, 'play_one_shot', None)
            else:
                # Web/server mode
                logger.info("Music/SFX system initialized in WEB mode (no desktop audio backend)")
        except Exception as e:
            logger.warning(f"Failed to initialize music/SFX system: {e}")

    def _on_music_state(self, payload: dict) -> None:
        try:
            track = payload.get('track') or ''
            if track:
                self._last_music_item = f"music: {track}"
            
            self.music_state_updated.emit(dict(payload))
            self._emit_playback()
        except Exception:
            pass

    def _on_sfx_update(self, payload: dict) -> None:
        try:
            loops = payload.get('loops', {}) if isinstance(payload, dict) else {}
            ones = payload.get('oneshots', []) if isinstance(payload, dict) else []
            items: list[str] = []
            for ch, path in loops.items():
                base = os.path.basename(path)
                items.append(f"sfx:{ch}: {base}")
            for p in ones:
                items.append(f"sfx:oneshot: {os.path.basename(p)}")
            self._last_sfx_items = items
            self._emit_playback()
        except Exception:
            pass

    def _emit_playback(self) -> None:
        try:
            items: list[str] = []
            if self._last_music_item:
                items.append(self._last_music_item)
            if self._last_sfx_items:
                items.extend(self._last_sfx_items)
            # Trim and store
            self._playing_snapshot = items[:5]
            self.playback_updated.emit(list(self._playing_snapshot))
        except Exception:
            pass

    def get_playback_snapshot(self) -> list[str]:
        try:
            return list(self._playing_snapshot)
        except Exception:
            return []