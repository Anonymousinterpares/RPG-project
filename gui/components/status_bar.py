#!/usr/bin/env python3
"""
Status bar for the RPG game GUI.
This module provides a status bar widget for displaying game status information.
"""

import logging
from typing import Optional
from enum import Enum

from PySide6.QtWidgets import QStatusBar, QLabel, QWidget, QHBoxLayout, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from gui.utils.resource_manager import get_resource_manager

class GameMode(Enum):
    """Different game modes that affect time progression."""
    NORMAL = "Normal"
    COMBAT = "Combat"
    BARTER = "Barter"

class GameStatusBar(QStatusBar):
    """Status bar for displaying game status information."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the status bar."""
        super().__init__(parent)
        
        # Get resource manager
        self.resource_manager = get_resource_manager()
        
        # Apply styling
        self.setStyleSheet("""
            QStatusBar {
                background-color: #333333;
                color: #E0E0E0;
                border-top: 1px solid #555555;
            }
            QStatusBar::item {
                border: none;
            }
            QLabel {
                color: #E0E0E0;
                padding: 2px 10px;
                font-family: 'Times New Roman', serif;
            }
        """)
        
        # Current game mode
        self.current_mode = GameMode.NORMAL
        
        # Create status labels
        self.location_label = QLabel("Location: Not in game")
        self.time_label = QLabel("Time: Not in game")
        self.mode_label = QLabel("Mode: Normal")
        
        # Add permanent widgets
        self.addPermanentWidget(self.location_label)
        self.addPermanentWidget(self.time_label)
        self.addPermanentWidget(self.mode_label)
    
    def update_status(self, location: str = "", game_time: str = "", speed: str = "", mode: str = ""):
        """Update the status bar with the provided information.
        
        Args:
            location: The current location name.
            game_time: The current game time.
            speed: The current game speed.
            mode: The current game mode (Normal, Combat, Barter).
        """
        if location:
            self.location_label.setText(f"Location: {location}")
        
        if game_time:
            self.time_label.setText(f"Time: {game_time}")
        
        # Update mode if provided
        if mode:
            try:
                self.current_mode = GameMode(mode)
                self.mode_label.setText(f"Mode: {self.current_mode.value}")
            except ValueError:
                # If invalid mode name, default to Normal
                self.current_mode = GameMode.NORMAL
                self.mode_label.setText(f"Mode: {self.current_mode.value}")
        
        # If no mode specified but speed is, derive from speed
        elif speed:
            if speed.lower() == "combat":
                self.current_mode = GameMode.COMBAT
            elif speed.lower() == "pause":
                # Paused but maintain the current mode type
                pass
            else:
                self.current_mode = GameMode.NORMAL
                
            self.mode_label.setText(f"Mode: {self.current_mode.value}")
