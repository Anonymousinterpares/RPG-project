#!/usr/bin/env python3
"""
Base settings dialog for the RPG game GUI.
This module provides a base dialog class for settings dialogs.
"""

from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton
)
from PySide6.QtCore import Slot, Signal

from core.utils.logging_config import get_logger
from gui.dialogs.base_dialog import BaseDialog
from gui.styles.stylesheet_factory import create_checkbox_style, create_dialog_style, create_groupbox_style, create_main_tab_widget_style

# Get the module logger
logger = get_logger("GUI")

class BaseSettingsDialog(BaseDialog):
    
    """Base dialog for settings dialogs."""
    
    # Signal emitted when settings are saved
    settings_saved = Signal()
    
    def __init__(self, parent=None, title="Settings"):
        """Initialize the base settings dialog."""
        super().__init__(parent)
        
        # Set window properties
        self.setWindowTitle(title)
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        # Create the main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Set up the bottom button layout
        self._setup_button_layout()

    @Slot(dict)
    def _update_theme(self, palette: Optional[Dict[str, Any]] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        
        # Combine base dialog style with specific settings dialog styles
        base_style = create_dialog_style(self.palette)
        tab_style = create_main_tab_widget_style(self.palette)
        group_style = create_groupbox_style(self.palette)
        checkbox_style = create_checkbox_style(self.palette)
        
        # Danger button style
        danger_style = f"""
            QPushButton.danger {{
                background-color: {colors['accent_negative']};
                color: {colors['text_bright']};
                border: 1px solid {colors['border_dark']};
            }}
            QPushButton.danger:hover {{
                background-color: {colors['accent_negative_light']};
            }}
            QPushButton.danger:pressed {{
                background-color: {colors['state_pressed']};
            }}
        """

        self.setStyleSheet(base_style + tab_style + group_style + checkbox_style + danger_style)
        
        # Propagate to children (tabs)
        for child in self.findChildren(object):
            if hasattr(child, '_update_theme') and callable(child._update_theme) and child is not self:
                child._update_theme(self.palette)
    
    def _setup_button_layout(self):
        """Set up the bottom button layout."""
        # Create bottom button layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 10, 0, 0)
        
        # Create cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        # Create save button
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self._on_save)
        
        # Add buttons to layout
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.save_button)
    
    def add_button_layout(self):
        """Add the button layout to the main layout."""
        self.main_layout.addLayout(self.button_layout)
    
    def add_left_button(self, button):
        """Add a button to the left side of the button layout."""
        self.button_layout.insertWidget(0, button)
    
    def _on_save(self):
        """Handle save button click."""
        # Save settings
        if self.save_settings():
            # Emit signal
            self.settings_saved.emit()
            
            # Accept dialog
            self.accept()
    
    def save_settings(self) -> bool:
        """
        Save settings.
        
        This method should be implemented by subclasses.
        
        Returns:
            True if settings were saved successfully, False otherwise.
        """
        return True
