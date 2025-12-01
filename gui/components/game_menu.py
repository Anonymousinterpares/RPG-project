#!/usr/bin/env python3
"""
Game menu widget for the RPG game GUI.
This module provides a widget for game menu options.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, 
    QMenu, QToolButton, QSizePolicy
)
from PySide6.QtCore import Signal, Slot

from gui.styles.stylesheet_factory import create_image_button_style
from gui.styles.theme_manager import get_theme_manager

class GameMenuWidget(QWidget):
    """Widget for game menu options."""
    
    # Signals for menu actions
    new_game_requested = Signal()
    save_game_requested = Signal()
    load_game_requested = Signal()
    settings_requested = Signal()
    llm_settings_requested = Signal()
    exit_requested = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the game menu widget."""
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        # Set up the UI
        self._setup_ui()
        
        # Apply initial theme
        self._update_theme()
    
    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
            
        # Use image button style for all main buttons
        btn_style = create_image_button_style(self.palette)
        
        self.new_game_button.setStyleSheet(btn_style)
        self.save_button.setStyleSheet(btn_style)
        self.load_button.setStyleSheet(btn_style)
        self.settings_button.setStyleSheet(btn_style)
        self.exit_button.setStyleSheet(btn_style)

    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        
        # Create menu buttons
        self.new_game_button = QPushButton("New Game")
        self.new_game_button.clicked.connect(self.new_game_requested.emit)
        
        # Save game button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_game_requested.emit)
        
        # Load game button
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.load_game_requested.emit)
        
        # Settings button with dropdown
        self.settings_button = QToolButton()
        self.settings_button.setText("Settings")
        self.settings_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
        self.settings_menu = QMenu(self.settings_button)
        self.settings_action = self.settings_menu.addAction("Game Settings")
        self.settings_action.triggered.connect(self.settings_requested.emit)
        
        self.llm_settings_action = self.settings_menu.addAction("LLM Settings")
        self.llm_settings_action.triggered.connect(self.llm_settings_requested.emit)
        
        self.graphics_action = self.settings_menu.addAction("Graphics Settings")
        self.sound_action = self.settings_menu.addAction("Sound Settings")
        
        self.settings_button.setMenu(self.settings_menu)
        self.settings_button.setPopupMode(QToolButton.InstantPopup)
        
        # Exit button
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.exit_requested.emit)
        
        # Add spacer to push buttons to the left
        layout.addWidget(self.new_game_button)
        layout.addWidget(self.save_button)
        layout.addWidget(self.load_button)
        layout.addWidget(self.settings_button)
        layout.addStretch()
        layout.addWidget(self.exit_button)
