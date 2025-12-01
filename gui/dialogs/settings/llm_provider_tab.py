#!/usr/bin/env python3
"""
LLM provider settings tab for the RPG game GUI.
This module provides a base tab for configuring LLM provider settings.
"""

from typing import Dict, Any, List, Tuple, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, 
    QLineEdit, QCheckBox, QLabel
)
from PySide6.QtCore import Slot

from core.utils.logging_config import get_logger
from gui.styles.theme_manager import get_theme_manager
from gui.styles.stylesheet_factory import create_checkbox_style, create_groupbox_style, create_line_edit_style

# Get the module logger
logger = get_logger("GUI")

class LLMProviderTab(QWidget):
    """Base tab for provider LLM settings."""
    
    def __init__(self, parent=None, provider_name="Provider"):
        """Initialize the provider settings tab."""
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        # Provider properties
        self.provider_name = provider_name
        self.api_key_setting_name = "api_key"
        self.models = []  # Will be set by subclasses: List of (display_name, value) tuples
        
        # Set up the UI
        self._setup_ui()
        
        # Apply initial theme
        self._update_theme()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # Create API settings group
        self.api_group = QGroupBox(f"{self.provider_name} API Settings")
        api_layout = QFormLayout(self.api_group)
        
        # Create enabled checkbox
        self.enabled_check = QCheckBox(f"Enable {self.provider_name}")
        self.enabled_check.setToolTip(f"Enable/disable {self.provider_name} provider")
        self.enabled_check.toggled.connect(self._toggle_fields)
        api_layout.addRow("", self.enabled_check)
        
        # Create API key field
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText(f"Enter your {self.provider_name} API key")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.api_key_edit)
        
        # Add info section (to be overridden by subclasses)
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        
        # Add groups to layout
        self.main_layout.addWidget(self.api_group)
        self.main_layout.addWidget(self.info_label)
        self.main_layout.addStretch(1)

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        
        # Style group box
        self.api_group.setStyleSheet(create_groupbox_style(self.palette))
        
        # Style line edit
        self.api_key_edit.setStyleSheet(create_line_edit_style(self.palette))
        
        # Style info label
        self.info_label.setStyleSheet(f"color: {colors['text_secondary']}; font-style: italic;")
        
        # Style checkbox
        self.enabled_check.setStyleSheet(create_checkbox_style(self.palette))
        
        # Propagate to children (like ModelManagementWidget in subclasses)
        for child in self.findChildren(QWidget):
            if hasattr(child, '_update_theme') and callable(child._update_theme) and child is not self:
                child._update_theme(self.palette)
    
    def add_models(self, models: List[Tuple[str, str]]):
        """Store models data.
        
        Args:
            models: List of (display_name, value) tuples
        """
        self.models = models
    
    def _toggle_fields(self, enabled: bool):
        """Toggle fields based on enabled state."""
        self.api_key_edit.setEnabled(enabled)
    
    def set_settings(self, settings: Dict[str, Any]):
        """Set the tab settings.
        
        Args:
            settings: Dictionary with settings values
        """
        # Set enabled checkbox
        self.enabled_check.setChecked(settings.get("enabled", True))
        
        # Set API key
        self.api_key_edit.setText(settings.get(self.api_key_setting_name, ""))
        
        # Toggle fields based on enabled state
        self._toggle_fields(self.enabled_check.isChecked())
    
    def get_settings(self) -> Dict[str, Any]:
        """Get the current settings from the tab.
        
        Returns:
            Dictionary with current settings values
        """
        settings = {
            "enabled": self.enabled_check.isChecked(),
            self.api_key_setting_name: self.api_key_edit.text()
        }
        
        return settings