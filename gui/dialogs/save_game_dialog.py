#!/usr/bin/env python3
"""
Save game dialog for the RPG game GUI.
This module provides a dialog for saving the game.
"""

import logging
import os
from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, Slot

class SaveGameDialog(QDialog):
    """Dialog for saving the game."""
    
    def __init__(self, parent=None):
        """Initialize the save game dialog."""
        super().__init__(parent)
        
        # Set window properties
        self.setWindowTitle("Save Game")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QLineEdit {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus {
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
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
                color: #E0E0E0;
            }
            QListWidget {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                alternate-background-color: #383838;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #444444;
            }
            QListWidget::item:selected {
                background-color: #0E639C;
            }
            QListWidget::item:hover {
                background-color: #383838;
            }
        """)
        
        # Set up the UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Create save name input section
        name_layout = QVBoxLayout()
        
        # Create save name label
        name_label = QLabel("Save Name:")
        
        # Create save name edit
        self.save_name_edit = QLineEdit()
        self.save_name_edit.setPlaceholderText("Enter a name for this save...")
        
        # Add widgets to name layout
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.save_name_edit)
        
        # Add name layout to main layout
        main_layout.addLayout(name_layout)
        
        # Create existing saves group
        existing_group = QGroupBox("Existing Saves")
        existing_layout = QVBoxLayout(existing_group)
        existing_layout.setContentsMargins(10, 20, 10, 10)
        
        # Create existing saves list
        self.saves_list = QListWidget()
        self.saves_list.setAlternatingRowColors(True)
        
        # Add saves list to existing layout
        existing_layout.addWidget(self.saves_list)
        
        # Add existing group to main layout
        main_layout.addWidget(existing_group)
        
        # Create the dialog buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        # Create cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        # Create save button
        self.save_button = QPushButton("Save Game")
        self.save_button.setEnabled(False)  # Disable until name is entered
        self.save_button.clicked.connect(self.accept)
        
        # Add buttons to layout
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)
        
        # Load existing saves
        self._load_existing_saves()
    
    def _connect_signals(self):
        """Connect signals to slots."""
        # Enable/disable save button based on name field
        self.save_name_edit.textChanged.connect(self._validate_form)
        
        # Update name field when an existing save is selected
        self.saves_list.itemClicked.connect(self._on_save_selected)
    
    def _validate_form(self):
        """Validate the form and enable/disable the save button."""
        # Check if name is not empty
        has_name = bool(self.save_name_edit.text().strip())
        
        # Enable/disable save button
        self.save_button.setEnabled(has_name)
    
    def _load_existing_saves(self):
        """Load existing saves into the list."""
        # Clear the list
        self.saves_list.clear()
        
        # Get the saves directory
        saves_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saves")
        
        # Check if the directory exists
        if not os.path.exists(saves_dir):
            return
        
        # Get all save files
        save_files = [f for f in os.listdir(saves_dir) if f.endswith(".json")]
        
        # Sort by modification time (newest first)
        save_files.sort(key=lambda x: os.path.getmtime(os.path.join(saves_dir, x)), reverse=True)
        
        # Add to list
        for save_file in save_files:
            # Get the save name without extension
            save_name = os.path.splitext(save_file)[0]
            
            # Create and add the item
            item = QListWidgetItem(save_name)
            self.saves_list.addItem(item)
    
    def _on_save_selected(self, item):
        """Handle save selection."""
        # Set the save name edit to the selected save
        self.save_name_edit.setText(item.text())
