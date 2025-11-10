#!/usr/bin/env python3
"""
Status bar for the RPG game GUI.
This module provides a status bar widget for displaying game status information.
"""

from typing import Any, Dict, Optional
from enum import Enum

from PySide6.QtWidgets import QStatusBar, QLabel, QWidget
from PySide6.QtCore import Slot

from gui.styles.theme_manager import get_theme_manager
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
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        # Get resource manager
        self.resource_manager = get_resource_manager()
        
        # Current game mode
        self.current_mode = GameMode.NORMAL
        
        # Create status labels
        self.location_label = QLabel("Location: Not in game")
        self.time_label = QLabel("Time: Not in game")
        self.calendar_label = QLabel("Calendar: -")
        self.mode_label = QLabel("Mode: Normal")
        self.context_label = QLabel("Ctx: -")
        
        # Add permanent widgets
        self.addPermanentWidget(self.location_label)
        self.addPermanentWidget(self.time_label)
        self.addPermanentWidget(self.calendar_label)
        self.addPermanentWidget(self.mode_label)
        self.addPermanentWidget(self.context_label)
        
        # Apply initial theme
        self._update_theme()

    @Slot(dict)
    def _update_theme(self, palette: Optional[Dict[str, Any]] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        fonts = self.palette['fonts']

        self.setStyleSheet(f"""
            QStatusBar {{
                background-color: {colors['bg_dark']};
                color: {colors['text_bright']};
                border-top: 1px solid {colors['border_dark']};
            }}
            QStatusBar::item {{
                border: none;
            }}
            QLabel {{
                color: {colors['text_bright']};
                padding: 2px 10px;
                font-family: {fonts['family_fantasy']};
            }}
        """)
    
    def update_status(self, location: str = "", game_time: str = "", calendar: str = "", mode: str = ""):
        """Update the status bar with the provided information.
        
        Args:
            location: The current location name.
            game_time: The current game time.
            mode: The current game mode (Normal, Combat, Barter).
        """
        if location:
            self.location_label.setText(f"Location: {location}")
        
        if game_time:
            capitalized_time = game_time.capitalize()
            self.time_label.setText(f"Time: {capitalized_time}")
        
        if calendar:
            self.calendar_label.setText(f"Calendar: {calendar}")
        
        # Update mode if provided
        if mode:
            try:
                self.current_mode = GameMode(mode)
                self.mode_label.setText(f"Mode: {self.current_mode.value}")
            except ValueError:
                # If invalid mode name, default to Normal
                self.current_mode = GameMode.NORMAL
                self.mode_label.setText(f"Mode: {self.current_mode.value}")

    def update_context(self, ctx: Optional[dict]) -> None:
        try:
            if not isinstance(ctx, dict):
                self.context_label.setText("Ctx: -")
                return
            loc = ctx.get('location') or {}
            w = ctx.get('weather') or {}
            bits = []
            if loc.get('major'): bits.append(str(loc.get('major')))
            if loc.get('venue'): bits.append(str(loc.get('venue')))
            if ctx.get('biome'): bits.append(str(ctx.get('biome')))
            if w.get('type'): bits.append(str(w.get('type')))
            if ctx.get('time_of_day'): bits.append(str(ctx.get('time_of_day')))
            if ctx.get('crowd_level'): bits.append(f"crowd:{ctx.get('crowd_level')}")
            if ctx.get('danger_level'): bits.append(f"danger:{ctx.get('danger_level')}")
            flags = []
            if bool(ctx.get('interior')): flags.append('interior')
            if bool(ctx.get('underground')): flags.append('underground')
            if flags: bits.append("+"+ ",".join(flags))
            text = " | ".join([b for b in bits if b]) or "-"
            self.context_label.setText(f"Ctx: {text}")
        except Exception:
            self.context_label.setText("Ctx: -")
