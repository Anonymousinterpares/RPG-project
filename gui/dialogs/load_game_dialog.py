#!/usr/bin/env python3
"""
Load game dialog for the RPG game GUI.
This module provides a dialog for loading a saved game.
"""

import logging
import os
import json
from typing import Optional, List, Dict
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QListWidget, QListWidgetItem,
    QSplitter, QWidget, QTextEdit, QHeaderView, QTableWidget,
    QTableWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon, QFont

from gui.dialogs.base_dialog import BaseDialog

# --- STYLING COLORS ---
COLORS = {
    'background_dark': '#1a1410',
    'background_med': '#2d2520',
    'background_light': '#3a302a',
    'border_dark': '#4a3a30',
    'border_light': '#5a4a40',
    'text_primary': '#c9a875',
    'text_secondary': '#8b7a65',
    'text_disabled': '#5a4a40',  # <-- THIS WAS MISSING
    'text_bright': '#e8d4b8',
    'selected': '#c9a875',
    'hover': '#4a3a30',
    'negative': '#D94A38',
}
# --- END STYLING COLORS ---


class LoadGameDialog(BaseDialog):
    """Dialog for loading a saved game."""
    
    def __init__(self, parent=None):
        """Initialize the load game dialog."""
        super().__init__(parent)
        
        # Set window properties
        self.setWindowTitle("Load Game")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background_med']};
                color: {COLORS['text_bright']};
            }}
            QLabel {{
                color: {COLORS['text_primary']};
            }}
            QPushButton {{
                background-color: {COLORS['background_light']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
                border-color: {COLORS['border_light']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['background_dark']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text_disabled']};
                border-color: {COLORS['background_dark']};
            }}
            QGroupBox {{
                border: 1px solid {COLORS['border_dark']};
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                color: {COLORS['text_primary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
            }}
            QTableWidget {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 4px;
                alternate-background-color: {COLORS['background_med']};
                gridline-color: {COLORS['border_dark']};
            }}
            QTableWidget::item {{
                padding: 5px;
                border-bottom: 1px solid {COLORS['border_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['hover']};
                color: {COLORS['selected']};
            }}
            QTextEdit {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 4px;
                padding: 5px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['background_light']};
                color: {COLORS['text_primary']};
                padding: 5px;
                border: 1px solid {COLORS['border_dark']};
            }}
            QSplitter::handle {{
                background-color: {COLORS['border_dark']};
            }}
        """)
        
        # Selected save
        self.selected_save = None
        self.selected_origin_id = None
        
        # Set up the UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()

        # Wire UI sounds for Load dialog (all clicks -> dropdown style; no tabs)
        try:
            from gui.utils.ui_sfx import map_container
            map_container(self, click_kind='dropdown', dropdown_kind='dropdown')
        except Exception:
            pass

    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Create a splitter for the save list and details
        splitter = QSplitter(Qt.Horizontal)
        
        # Create the saves list widget
        saves_widget = QWidget()
        saves_layout = QVBoxLayout(saves_widget)
        saves_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the saves table
        self.saves_table = QTableWidget()
        self.saves_table.setColumnCount(3)
        self.saves_table.setHorizontalHeaderLabels(["Save Name", "Date", "Character"])
        self.saves_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.saves_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.saves_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.saves_table.verticalHeader().setVisible(False)
        self.saves_table.setAlternatingRowColors(True)
        self.saves_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.saves_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.saves_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Add saves table to layout
        saves_layout.addWidget(self.saves_table)
        
        # Create the details widget
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the details group
        details_group = QGroupBox("Save Details")
        details_group_layout = QVBoxLayout(details_group)
        
        # Create the details text
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        
        # Add details text to group layout
        details_group_layout.addWidget(self.details_text)
        
        # Add details group to layout
        details_layout.addWidget(details_group)
        
        # Add widgets to splitter
        splitter.addWidget(saves_widget)
        splitter.addWidget(details_widget)
        
        # Set initial sizes
        splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Create the dialog buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        # Create cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        # Create delete button
        self.delete_button = QPushButton("Delete Save")
        self.delete_button.setEnabled(False)
        self.delete_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['negative']};
                color: #FFFFFF;
            }}
            QPushButton:hover {{ background-color: #E57373; }}
            QPushButton:pressed {{ background-color: #C62828; }}
            QPushButton:disabled {{ 
                background-color: {COLORS['background_dark']};
                color: {COLORS['text_disabled']};
                border-color: {COLORS['background_dark']};
            }}
        """)
        
        # Create load button
        self.load_button = QPushButton("Load Game")
        self.load_button.setEnabled(False)
        self.load_button.clicked.connect(self.accept)
        
        # Add buttons to layout
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.load_button)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)
        
        # Load saves
        self._load_saves()
    
    def _connect_signals(self):
        """Connect signals to slots."""
        # Connect save selection
        self.saves_table.itemSelectionChanged.connect(self._on_save_selected)
        self.saves_table.doubleClicked.connect(self._on_save_double_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)

    def _on_delete_clicked(self):
        """Handle the delete save button click."""
        if not self.selected_save:
            return

        from PySide6.QtWidgets import QMessageBox
        from core.base.engine import get_game_engine

        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Delete Save",
            f"Are you sure you want to permanently delete the save file:\n\n'{self.selected_save}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            engine = get_game_engine()
            # The state manager's delete_save is designed for simple files,
            # but we can adapt the logic here to remove the directory.
            saves_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saves")
            save_path_to_delete = os.path.join(saves_dir, self.selected_save)
            
            # The actual save file is a .json file, so we target that.
            if os.path.exists(save_path_to_delete):
                try:
                    os.remove(save_path_to_delete)
                    logging.info(f"Successfully deleted save file: {self.selected_save}")
                    
                    # Refresh the saves list
                    self._load_saves()
                    
                    # Clear the details pane and disable buttons
                    self.details_text.clear()
                    self.selected_save = None
                    self.load_button.setEnabled(False)
                    self.delete_button.setEnabled(False)
                    
                    QMessageBox.information(self, "Success", "Save file deleted successfully.")
                except Exception as e:
                    logging.error(f"Error deleting save file {self.selected_save}: {e}")
                    QMessageBox.warning(self, "Error", f"Could not delete the save file.\n\nError: {e}")
            else:
                QMessageBox.warning(self, "Error", "Save file not found. It may have already been deleted.")
                self._load_saves() # Refresh list in case of mismatch

    def _load_saves(self):
        """Load saves into the table using the efficient StateManager method."""
        self.saves_table.setRowCount(0)
        
        try:
            from core.base.state import get_state_manager
            saves = get_state_manager().get_available_saves()
        except Exception as e:
            logging.error(f"Failed to get available saves: {e}")
            # Optionally, show an error message to the user
            return

        self.saves_table.setSortingEnabled(False) # Disable sorting during population

        for i, save_info in enumerate(saves):
            save_name = os.path.splitext(save_info["filename"])[0]
            
            mod_time = datetime.fromtimestamp(save_info.get("mod_time", 0))
            mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M")
            
            character_name = save_info.get("player_name", "Unknown")
            origin_id = save_info.get("origin_id") # This can be None

            self.saves_table.insertRow(i)
            
            # Store filename and origin_id in the first item's data
            name_item = QTableWidgetItem(save_name)
            name_item.setData(Qt.UserRole, {"filename": save_info["filename"], "origin_id": origin_id})
            
            self.saves_table.setItem(i, 0, name_item)
            self.saves_table.setItem(i, 1, QTableWidgetItem(mod_time_str))
            self.saves_table.setItem(i, 2, QTableWidgetItem(character_name))

        self.saves_table.setSortingEnabled(True) # Re-enable sorting
    
    def _get_character_name(self, save_path: str) -> str:
        """Get the character name from a save file.
        
        Args:
            save_path: The path to the save file.
        
        Returns:
            The character name, or "Unknown" if not found.
        """
        try:
            with open(save_path, "r") as f:
                save_data = json.load(f)
                
                # Try to get the character name
                if "player" in save_data and "name" in save_data["player"]:
                    return save_data["player"]["name"]
        except Exception as e:
            pass
        
        return "Unknown"
    
    def _get_save_details(self, save_path: str) -> str:
        """Get the details for a save file.
        
        Args:
            save_path: The path to the save file.
        
        Returns:
            The save details as a formatted string.
        """
        try:
            with open(save_path, "r", encoding='utf-8') as f:
                save_data = json.load(f)
                
                player_data = save_data.get("player", {})
                world_data = save_data.get("world", {})
                
                details = []
                
                # --- Character Information ---
                details.append("<b>Character Information:</b>")
                details.append(f"<b>Name:</b> {player_data.get('name', 'Unknown')}")

                # --- Display Origin ---
                origin_id = player_data.get('origin_id')
                if origin_id:
                    try:
                        from core.base.config import get_config
                        origins_config = get_config().get('origins', {})
                        origin_name = origins_config.get(origin_id, {}).get('name', origin_id)
                        details.append(f"<b>Origin:</b> {origin_name}")
                    except Exception:
                        details.append(f"<b>Origin:</b> {origin_id}") # Fallback to ID

                details.append(f"<b>Race:</b> {player_data.get('race', 'Unknown')}")
                details.append(f"<b>Class:</b> {player_data.get('path', 'Unknown')}")
                details.append(f"<b>Level:</b> {player_data.get('level', 1)}")
                details.append("") # Spacer
                
                # --- Background Summary ---
                background_summary = player_data.get('background_summary')
                if background_summary:
                    details.append("<b>Background:</b>")
                    details.append(background_summary)
                    details.append("") # Spacer
                
                # --- Last Events Summary ---
                last_events_summary = save_data.get('last_events_summary')
                if last_events_summary:
                    details.append("<b>Last Events:</b>")
                    details.append(last_events_summary)
                    details.append("") # Spacer
                
                # --- World Information ---
                if world_data:
                    details.append("<b>World Information:</b>")
                    details.append(f"<b>Location:</b> {player_data.get('current_location', 'Unknown')}")
                    # Use the new, user-friendly calendar string and time of day
                    calendar_str = world_data.get('calendar_string', 'Unknown Date')
                    time_of_day = world_data.get('time_of_day', 'Unknown Time')
                    details.append(f"<b>Time:</b> {calendar_str} ({time_of_day})")
                    details.append("") # Spacer

                # --- Save File Information ---
                mod_time = datetime.fromtimestamp(os.path.getmtime(save_path))
                details.append("<b>Save Information:</b>")
                details.append(f"<b>Saved On:</b> {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                details.append(f"<b>File:</b> {os.path.basename(save_path)}")
                
                # Use html-like formatting for QTextEdit
                return "<br>".join(details)
        except Exception as e:
            logging.error(f"Error loading save details for '{save_path}': {e}", exc_info=True)
            return f"Error loading save details: {str(e)}"
    
    def _on_save_selected(self):
        """Handle save selection."""
        # Get the selected row
        selected_rows = self.saves_table.selectedItems()
        
        if not selected_rows:
            # No selection
            self.selected_save = None
            self.selected_origin_id = None
            self.details_text.clear()
            self.load_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        
        # Retrieve the cached data from the first item in the selected row
        item_data = self.saves_table.item(selected_rows[0].row(), 0).data(Qt.UserRole)
        
        # Set the selected save filename and origin_id
        self.selected_save = item_data.get("filename")
        self.selected_origin_id = item_data.get("origin_id")
        
        # Get the save path
        saves_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saves")
        save_path = os.path.join(saves_dir, self.selected_save)
        
        # Update the details
        self.details_text.setText(self._get_save_details(save_path))
        
        # Enable buttons
        self.load_button.setEnabled(True)
        self.delete_button.setEnabled(True)
    
    def _on_save_double_clicked(self, item):
        """Handle save double click."""
        # Accept the dialog to load the selected save
        self.accept()
