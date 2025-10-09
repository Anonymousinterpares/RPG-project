# gui/widgets/music_controls.py

import logging
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QPushButton
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon
import os

class MusicControls(QWidget):
    volumeChanged = Signal(int)
    playPauseClicked = Signal()
    nextClicked = Signal()
    previousClicked = Signal()
    muteClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__ + ".MusicControls")
        self.setFixedHeight(32)  # Fixed height for control panel
        self.setup_ui()
        
        # Faster update timer for track info (check 4 times per second)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_track_info)
        self.update_timer.start(250)  # Update 4 times per second
        
        self.is_playing = False
        self.is_muted = False
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)

        # Create buttons with custom styling
        button_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid #999;
                border-radius: 4px;
                font-size: 16px;
                color: black;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(255, 0, 0, 0.7);
                color: yellow;
            }
        """

        # Previous Track Button
        self.btn_previous = QPushButton("⏮")
        self.btn_previous.setFixedSize(30, 30)
        self.btn_previous.setStyleSheet(button_style)
        self.btn_previous.clicked.connect(self.previousClicked.emit)
        
        # Play/Pause Button
        self.btn_play = QPushButton("⏯")
        self.btn_play.setFixedSize(30, 30)
        self.btn_play.setStyleSheet(button_style)
        self.btn_play.clicked.connect(self.on_play_pause)
        
        # Next Track Button
        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(30, 30)
        self.btn_next.setStyleSheet(button_style)
        self.btn_next.clicked.connect(self.nextClicked.emit)
        
        # Mute Button
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setFixedSize(30, 30)
        self.btn_mute.setStyleSheet(button_style)
        self.btn_mute.clicked.connect(self.on_mute)
        
        # Volume Slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)  # Default volume
        self.volume_slider.valueChanged.connect(self.volumeChanged.emit)

        # Add widgets to layout
        layout.addWidget(self.btn_previous)
        layout.addWidget(self.btn_play)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_mute)
        layout.addWidget(self.volume_slider)
        layout.addStretch()

        # Style the volume slider
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff0000, stop:1 #cc0000);
            }
        """)

    def on_play_pause(self):
        """Emit signal when play/pause button is clicked"""
        # Don't toggle state - let the signal handler do it
        self.playPauseClicked.emit()

    def on_mute(self):
        self.is_muted = not self.is_muted
        self.btn_mute.setText("🔇" if self.is_muted else "🔊")
        self.muteClicked.emit()

    # Replace the update_track_info method in MusicControls
    def update_track_info(self):
        """Update volume and mute state from music manager"""
        main_window = self.window()
        if hasattr(main_window, "music_manager"):
            info = main_window.music_manager.get_current_track_info()
            
            # Only update volume and mute - play state comes from signal
            volume = info.get("volume", 70)
            if self.volume_slider.value() != volume:
                self.volume_slider.setValue(volume)
            
            is_muted = info.get("muted", False)
            if self.is_muted != is_muted:
                self.set_muted(is_muted)

    def set_playing_state(self, is_playing: bool):
        """Update play/pause button state - called directly from signal"""
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Setting play button state to: {is_playing}")
        
        # Always update internal state and button
        self.is_playing = is_playing
        self.btn_play.setText("⏸" if is_playing else "⏯")
        # Force immediate update
        self.btn_play.repaint()

    def set_volume(self, volume: int):
        self.volume_slider.setValue(volume)

    def set_muted(self, is_muted: bool):
        self.is_muted = is_muted
        self.btn_mute.setText("🔇" if is_muted else "🔊")