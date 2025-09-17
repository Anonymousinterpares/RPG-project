#!/usr/bin/env python3
"""
Base settings dialog for the RPG game GUI.
This module provides a base dialog class for settings dialogs.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

# Get the module logger
logger = logging.getLogger("GUI")

class BaseSettingsDialog(QDialog):
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
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #0E639C;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #0A4C7C;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #AAAAAA;
            }
            QPushButton.danger {
                background-color: #D32F2F;
            }
            QPushButton.danger:hover {
                background-color: #F44336;
            }
            QPushButton.danger:pressed {
                background-color: #B71C1C;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                color: #E0E0E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2D2D30;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background-color: #333333;
                border: 1px solid #555555;
                border-bottom-color: #555555;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 10px;
                color: #CCCCCC;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0E639C;
                color: white;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
            QCheckBox {
                color: #E0E0E0;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555555;
                border-radius: 2px;
                background-color: #1E1E1E;
            }
            QCheckBox::indicator:checked {
                background-color: #0E639C;
                border-color: #0E639C;
            }
        """)
        
        # Create the main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        
        # Set up the bottom button layout
        self._setup_button_layout()
    
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
