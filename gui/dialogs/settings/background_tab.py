#!/usr/bin/env python3
"""
Background selection tab for the settings dialog.
"""

import logging
import os
from typing import List, Optional, Tuple # Added Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSettings, QSize
from PySide6.QtGui import QPixmap, QMovie # Added QMovie

from gui.utils.resource_manager import get_resource_manager

logger = logging.getLogger(__name__)

class BackgroundTab(QWidget):
    """Widget for selecting the main window background."""

    # Signal emitted when the user previews a different background
    # Argument is the full filename of the background (e.g., 'my_bg.gif')
    preview_background_changed = Signal(str)

    def __init__(self, parent=None):
        """Initialize the background tab."""
        super().__init__(parent)

        self.resource_manager = get_resource_manager()
        self.backgrounds: List[Tuple[str, str]] = [] # Stores (name, ext) tuples
        self.current_index: int = -1
        # Default should ideally include extension, but resource manager might find it
        self.default_background_filename = "main_background.png"

        self._setup_ui()
        self._load_available_backgrounds()

    def _setup_ui(self):
        """Set up the user interface for the tab."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Preview Area
        preview_layout = QVBoxLayout()
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview_label = QLabel("Background Preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(400, 225) # Aspect ratio 16:9
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setStyleSheet("border: 1px solid gray; background-color: #333;")
        preview_layout.addWidget(self.preview_label)

        self.name_label = QLabel("Background: N/A")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.name_label)

        layout.addLayout(preview_layout)

        # Navigation Controls
        nav_layout = QHBoxLayout()
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.prev_button = QPushButton("< Prev")
        self.prev_button.clicked.connect(self._show_previous_background)
        self.prev_button.setFixedWidth(100)

        self.next_button = QPushButton("Next >")
        self.next_button.clicked.connect(self._show_next_background)
        self.next_button.setFixedWidth(100)

        nav_layout.addWidget(self.prev_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_button)

        layout.addLayout(nav_layout)
        layout.addStretch() # Push controls to the top

    def _load_available_backgrounds(self):
        """Load the list of available background image/animation names and extensions."""
        self.backgrounds = self.resource_manager.list_background_names()
        logger.info(f"Found backgrounds: {self.backgrounds}")
        if not self.backgrounds:
            logger.warning("No background images or GIFs found in images/gui/background/")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
        else:
            # Try to set initial index based on saved setting later in load_settings
            self.prev_button.setEnabled(len(self.backgrounds) > 1)
            self.next_button.setEnabled(len(self.backgrounds) > 1)

    def _update_preview(self):
        """Update the preview label with the current background (PNG or GIF)."""
        # Stop any existing movie
        current_movie = self.preview_label.movie()
        if current_movie:
            current_movie.stop()
            self.preview_label.setMovie(None) # Clear movie reference

        # Clear existing pixmap
        self.preview_label.setPixmap(QPixmap())

        if 0 <= self.current_index < len(self.backgrounds):
            name, ext = self.backgrounds[self.current_index]
            filename = f"{name}{ext}"
            self.name_label.setText(f"Background: {filename}")

            if ext.lower() == ".png":
                pixmap = self.resource_manager.get_background_pixmap(name)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(self.preview_label.size(),
                                                  Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
                    self.preview_label.setPixmap(scaled_pixmap)
                else:
                    self.preview_label.setText(f"Failed to load:\n{filename}")

            elif ext.lower() == ".gif":
                movie = self.resource_manager.get_background_movie(name)
                if movie.isValid():
                    self.preview_label.setMovie(movie)
                    # Scale movie if possible (QMovie doesn't scale directly like QPixmap)
                    # We might need to adjust label size policy or container layout
                    # For now, just set it and start
                    movie.setScaledSize(self.preview_label.size()) # Attempt scaling
                    movie.start()
                else:
                    self.preview_label.setText(f"Failed to load:\n{filename}")

            # Emit signal for live preview in main window with full filename
            self.preview_background_changed.emit(filename)
        else:
            self.name_label.setText("Background: N/A")
            self.preview_label.setText("No Background Selected")
            # Ensure both pixmap and movie are cleared
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setMovie(None)

    def _show_previous_background(self):
        """Navigate to the previous background image/animation."""
        if not self.backgrounds:
            return
        self.current_index = (self.current_index - 1) % len(self.backgrounds)
        self._update_preview()

    def _show_next_background(self):
        """Navigate to the next background image/animation."""
        if not self.backgrounds:
            return
        self.current_index = (self.current_index + 1) % len(self.backgrounds)
        self._update_preview()

    def load_settings(self, settings: QSettings):
        """Load the saved background setting (full filename). Defaults to first available if saved is invalid."""
        # Save/Load the full filename now, e.g., "my_background.gif"
        saved_filename = settings.value("style/background_filename", None)
        logger.info(f"Attempting to load background setting: '{saved_filename}'")

        self.current_index = -1 # Reset index

        if saved_filename:
            # Find the index corresponding to the saved filename
            found = False
            for i, (name, ext) in enumerate(self.backgrounds):
                if f"{name}{ext}" == saved_filename:
                    self.current_index = i
                    logger.info(f"Found saved background '{saved_filename}' at index {self.current_index}")
                    found = True
                    break
            if not found:
                 logger.warning(f"Saved background '{saved_filename}' not found in available list: {self.backgrounds}")
                 if self.backgrounds:
                     self.current_index = 0 # Fallback to first available
                     logger.info(f"Falling back to first available: '{self.backgrounds[self.current_index][0]}{self.backgrounds[self.current_index][1]}'")

        elif self.backgrounds:
            # No setting saved, use the first available
            self.current_index = 0
            logger.info(f"No background setting saved. Using first available: '{self.backgrounds[self.current_index][0]}{self.backgrounds[self.current_index][1]}'")
        else:
            # No setting saved and no backgrounds available
             logger.warning("No saved background setting and no backgrounds available.")
             self.current_index = -1

        # Update preview even if index is -1 (will show N/A)
        self._update_preview()

    def save_settings(self, settings: QSettings):
        """Save the currently selected background filename."""
        if 0 <= self.current_index < len(self.backgrounds):
            selected_name, selected_ext = self.backgrounds[self.current_index]
            selected_filename = f"{selected_name}{selected_ext}"
            settings.setValue("style/background_filename", selected_filename)
            logger.info(f"Saving background setting: '{selected_filename}'")
        else:
            # If somehow no valid index, try saving the default filename
            settings.setValue("style/background_filename", self.default_background_filename)
            logger.warning(f"No valid background selected, saving default filename: {self.default_background_filename}")