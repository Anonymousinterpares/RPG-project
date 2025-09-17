#!/usr/bin/env python3
"""
LLM general settings tab for the RPG game GUI.
This module provides a tab for configuring general LLM settings.
"""

import logging
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, 
    QComboBox, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt

# Get the module logger
logger = logging.getLogger("GUI")

class LLMGeneralTab(QWidget):
    """Tab for general LLM settings."""
    
    def __init__(self, parent=None):
        """Initialize the general settings tab."""
        super().__init__(parent)
        
        # Set up the UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create general settings group
        general_group = QGroupBox("General LLM Settings")
        general_layout = QFormLayout(general_group)
        general_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # Create default provider setting
        self.default_provider_combo = QComboBox()
        self.default_provider_combo.addItem("OpenAI", "OPENAI")
        self.default_provider_combo.addItem("Google", "GOOGLE")
        self.default_provider_combo.addItem("OpenRouter", "OPENROUTER")
        general_layout.addRow("Default Provider:", self.default_provider_combo)
        
        # Create LLM toggle checkbox
        self.llm_enabled_check = QCheckBox("Enable LLM Processing")
        self.llm_enabled_check.setToolTip("Toggle LLM processing for game input")
        general_layout.addRow("", self.llm_enabled_check)
        
        # Create diagnostics at startup checkbox
        self.diagnostics_check = QCheckBox("Run diagnostics at startup")
        self.diagnostics_check.setToolTip("Test LLM connections when the application starts")
        general_layout.addRow("", self.diagnostics_check)
        
        # Create advanced settings group
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout(advanced_group)
        
        # Create timeout setting
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setSuffix(" seconds")
        self.timeout_spin.setToolTip("Maximum time to wait for LLM response")
        advanced_layout.addRow("Request Timeout:", self.timeout_spin)
        
        # Create retry attempts setting
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(1, 10)
        self.retry_spin.setToolTip("Number of retry attempts for failed requests")
        advanced_layout.addRow("Retry Attempts:", self.retry_spin)
        
        # Create retry delay setting
        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(1, 30)
        self.retry_delay_spin.setSuffix(" seconds")
        self.retry_delay_spin.setToolTip("Delay between retry attempts")
        advanced_layout.addRow("Retry Delay:", self.retry_delay_spin)
        
        # Create temperature setting
        self.temperature_combo = QComboBox()
        self.temperature_combo.addItem("Low (0.3) - More focused, less creative", 0.3)
        self.temperature_combo.addItem("Medium (0.7) - Balanced", 0.7)
        self.temperature_combo.addItem("High (1.0) - More creative, less focused", 1.0)
        self.temperature_combo.setToolTip("Controls randomness of LLM responses")
        advanced_layout.addRow("Default Temperature:", self.temperature_combo)
        
        # Add groups to layout
        layout.addWidget(general_group)
        layout.addWidget(advanced_group)
        layout.addStretch(1)
    
    def set_settings(self, settings: Dict[str, Any]):
        """Set the tab settings.
        
        Args:
            settings: Dictionary with settings values
        """
        # Set provider type
        provider_type = settings.get("default_provider_type", "OPENAI")
        index = self.default_provider_combo.findData(provider_type)
        if index >= 0:
            self.default_provider_combo.setCurrentIndex(index)
        
        # Set checkboxes
        self.llm_enabled_check.setChecked(settings.get("llm_enabled", False))
        self.diagnostics_check.setChecked(settings.get("run_diagnostics_on_start", False))
        
        # Set spin boxes
        self.timeout_spin.setValue(settings.get("timeout_seconds", 30))
        self.retry_spin.setValue(settings.get("retry_attempts", 3))
        self.retry_delay_spin.setValue(settings.get("retry_delay_seconds", 2))
        
        # Set temperature combo
        temp = settings.get("default_temperature", 0.7)
        if temp <= 0.3:
            self.temperature_combo.setCurrentIndex(0)
        elif temp >= 1.0:
            self.temperature_combo.setCurrentIndex(2)
        else:
            self.temperature_combo.setCurrentIndex(1)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get the current settings from the tab.
        
        Returns:
            Dictionary with current settings values
        """
        return {
            "default_provider_type": self.default_provider_combo.currentData(),
            "default_temperature": self.temperature_combo.currentData(),
            "timeout_seconds": self.timeout_spin.value(),
            "retry_attempts": self.retry_spin.value(),
            "retry_delay_seconds": self.retry_delay_spin.value(),
            "run_diagnostics_on_start": self.diagnostics_check.isChecked(),
            "llm_enabled": self.llm_enabled_check.isChecked()
        }
