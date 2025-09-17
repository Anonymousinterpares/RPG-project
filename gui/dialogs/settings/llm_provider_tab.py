#!/usr/bin/env python3
"""
LLM provider settings tab for the RPG game GUI.
This module provides a base tab for configuring LLM provider settings.
"""

import logging
from typing import Dict, Any, List, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, 
    QLineEdit, QComboBox, QCheckBox, QLabel
)
from PySide6.QtCore import Qt

# Get the module logger
logger = logging.getLogger("GUI")

class LLMProviderTab(QWidget):
    """Base tab for provider LLM settings."""
    
    def __init__(self, parent=None, provider_name="Provider"):
        """Initialize the provider settings tab."""
        super().__init__(parent)
        
        # Provider properties
        self.provider_name = provider_name
        self.api_key_setting_name = "api_key"
        self.models = []  # Will be set by subclasses: List of (display_name, value) tuples
        
        # Set up the UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # Create API settings group
        api_group = QGroupBox(f"{self.provider_name} API Settings")
        api_layout = QFormLayout(api_group)
        
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
        self.info_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
        
        # Add groups to layout
        self.main_layout.addWidget(api_group)
        self.main_layout.addWidget(self.info_label)
        self.main_layout.addStretch(1)
    
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
