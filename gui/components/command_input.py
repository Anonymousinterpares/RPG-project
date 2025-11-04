#!/usr/bin/env python3
"""
Command input widget for the RPG game GUI.
This module provides a widget for entering commands.
"""

import logging
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, 
    QCompleter, QVBoxLayout, QListWidget, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QIcon, QPalette, QBrush, QPixmap

from gui.utils.resource_manager import get_resource_manager

# --- STYLING COLORS ---
COLORS = {
    'background_dark': '#1a1410',
    'border_dark': '#4a3a30',
    'text_primary': '#c9a875',
}

class CommandInputWidget(QFrame):
    """Widget for entering commands."""
    
    # Signal emitted when a command is submitted
    command_submitted = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the command input widget."""
        super().__init__(parent)
        
        # Set frame properties
        self.setFrameShape(QFrame.StyledPanel)
        self.setContentsMargins(0, 0, 0, 0)
        
        # Command history
        self.command_history: List[str] = []
        self.history_index = -1
        
        # Get resource manager
        self.resource_manager = get_resource_manager()
        
        # Set up the UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Set frame background to transparent
        self.setStyleSheet("""
            CommandInputWidget {
                background-color: transparent;
                border: none;
            }
        """)
        
        # Create the command line edit with fantasy theme
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("Enter a command or type 'help'...")
        self.command_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Garamond', serif;
                font-size: 14pt;
                margin-left: 5px;
                margin-right: 5px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['text_primary']};
            }}
        """)
        
        # Create the submit button with the original image-based styling
        self.submit_button = QPushButton("Enter")
        self.submit_button.setStyleSheet("""
            QPushButton {
                background-image: url('images/gui/button_normal.png');
                background-position: center;
                background-repeat: no-repeat;
                background-color: transparent;
                color: #2e2e2e;
                border: none;
                padding: 8px 15px;
                font-weight: bold;
                font-family: 'Times New Roman', serif;
                min-width: 80px;
                min-height: 30px;
                max-width: 100px;
                margin-right: 5px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-image: url('images/gui/button_hover.png');
            }
            QPushButton:pressed {
                background-image: url('images/gui/button_pressed.png');
                color: #FF0000;
                font-weight: bold;
            }
        """)
        # Add widgets to the layout
        layout.addWidget(self.command_edit, 1)
        layout.addWidget(self.submit_button)
    
    def _connect_signals(self):
        """Connect signals to slots."""
        # Connect the submit button click
        self.submit_button.clicked.connect(self._submit_command)
        
        # Connect the command edit return key
        self.command_edit.returnPressed.connect(self._submit_command)
        
        # Connect the command edit key press event
        self.command_edit.keyPressEvent = self._command_key_press
    
    def _submit_command(self):
        """Submit the current command."""
        # Get the command text
        command = self.command_edit.text().strip()
        
        # Skip if empty
        if not command:
            return
        
        # Add to history
        if not self.command_history or self.command_history[-1] != command:
            self.command_history.append(command)
            if len(self.command_history) > 50:
                self.command_history.pop(0)
        
        # Reset history index
        self.history_index = -1
        
        # Emit signal
        self.command_submitted.emit(command)
        
        # Clear the edit
        self.command_edit.clear()
    
    def _command_key_press(self, event):
        """Handle key press events for the command edit."""
        # Check for up/down arrow keys for command history
        if event.key() == Qt.Key_Up:
            self._navigate_history(1)
        elif event.key() == Qt.Key_Down:
            self._navigate_history(-1)
        else:
            # Default handling
            QLineEdit.keyPressEvent(self.command_edit, event)
    
    def _navigate_history(self, direction: int):
        """Navigate the command history.
        
        Args:
            direction: 1 for older commands, -1 for newer commands.
        """
        if not self.command_history:
            return
        
        # Update history index
        new_index = self.history_index + direction
        
        # Clamp index
        if new_index >= len(self.command_history):
            new_index = len(self.command_history) - 1
        elif new_index < -1:
            new_index = -1
        
        self.history_index = new_index
        
        # Set text from history or clear
        if self.history_index == -1:
            self.command_edit.clear()
        else:
            self.command_edit.setText(self.command_history[-(self.history_index+1)])
            self.command_edit.selectAll()
    
    def clear(self):
        """Clear the command input."""
        self.command_edit.clear()
