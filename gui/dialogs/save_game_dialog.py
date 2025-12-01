#!/usr/bin/env python3
"""
Save game dialog for the RPG game GUI.
This module provides a dialog for saving the game.
"""

import os
from typing import Optional

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Slot

from gui.dialogs.base_dialog import BaseDialog
from gui.styles.stylesheet_factory import create_dialog_style, create_groupbox_style, create_line_edit_style, create_list_widget_style, create_styled_button_style
from gui.styles.theme_manager import get_theme_manager
from core.base.state import get_state_manager  # Import StateManager

class SaveGameDialog(BaseDialog):
    """Dialog for saving the game."""
    
    def __init__(self, parent=None):
        """Initialize the save game dialog."""
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        # Set window properties
        self.setWindowTitle("Save Game")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        # Set up the UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()

        # Apply initial theme
        self._update_theme()

        # Wire UI sounds for Save dialog (all clicks -> dropdown style; no tabs)
        try:
            from gui.utils.ui_sfx import map_container
            map_container(self, click_kind='dropdown', dropdown_kind='dropdown')
        except Exception:
            pass

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        # Guard against premature call
        if not hasattr(self, 'save_name_edit'):
            return

        if palette:
            self.palette = palette
        
        # Base dialog style
        self.setStyleSheet(create_dialog_style(self.palette))
        
        # Input style
        self.save_name_edit.setStyleSheet(create_line_edit_style(self.palette))
        
        # GroupBox style
        self.existing_group.setStyleSheet(create_groupbox_style(self.palette))
        
        # List style
        self.saves_list.setStyleSheet(create_list_widget_style(self.palette))
        
        # Button styles
        btn_style = create_styled_button_style(self.palette)
        self.save_button.setStyleSheet(btn_style)
        self.cancel_button.setStyleSheet(btn_style)

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
        self.existing_group = QGroupBox("Existing Saves")
        existing_layout = QVBoxLayout(self.existing_group)
        existing_layout.setContentsMargins(10, 20, 10, 10)
        
        # Create existing saves list
        self.saves_list = QListWidget()
        self.saves_list.setAlternatingRowColors(True)
        
        # Add saves list to existing layout
        existing_layout.addWidget(self.saves_list)
        
        # Add existing group to main layout
        main_layout.addWidget(self.existing_group)
        
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
        """Load existing saves into the list using the centralized StateManager."""
        # Clear the list
        self.saves_list.clear()
        
        # Use StateManager to get saves (consistent with LoadGameDialog)
        try:
            state_manager = get_state_manager()
            saves = state_manager.get_available_saves()
            
            # Add to list
            for save_info in saves:
                # 'filename' in the dict represents the folder name (Save ID)
                save_name = save_info.get('filename', 'Unknown')
                
                # Create and add the item
                item = QListWidgetItem(save_name)
                self.saves_list.addItem(item)
                
        except Exception as e:
            # Fallback (empty list) if state manager fails
            print(f"Error loading saves list in dialog: {e}")
    
    def _on_save_selected(self, item):
        """Handle save selection."""
        # Set the save name edit to the selected save
        self.save_name_edit.setText(item.text())