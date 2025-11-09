#!/usr/bin/env python3
"""
Command input widget for the RPG game GUI.
This module provides a widget for entering commands.
"""

from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, 
    QFrame
)
from PySide6.QtCore import Qt, Signal, Slot, QSettings, QSize
from PySide6.QtGui import QColor, QIcon

from gui.styles.stylesheet_factory import create_round_image_button_style
from gui.styles.theme_manager import get_theme_manager
from gui.utils.resource_manager import get_resource_manager

class CommandInputWidget(QFrame):
    """Widget for entering commands."""
    
    # Signal emitted when a command is submitted
    command_submitted = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the command input widget."""
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---

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

        # Apply initial theme
        self._update_theme()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create the command line edit
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("Enter a command or type 'help'...")
        
        # Create the submit button without text and with a fixed size
        self.submit_button = QPushButton("")
        self.submit_button.setFixedSize(40, 40) # Set a fixed size for the round button
        # Set the size for the icon that will be placed on the button
        self.submit_button.setIconSize(QSize(38, 38)) # Slightly smaller for padding
        
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

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        fonts = self.palette['fonts']
        paths = self.palette['paths']

        # Get opacity from QSettings
        settings = QSettings("RPGGame", "Settings")
        input_opacity = int(settings.value("style/input_opacity", 100)) / 100.0
        
        # Extract RGBA components for the background
        try:
            color = QColor(colors['bg_dark_transparent'])
            r, g, b = color.red(), color.green(), color.blue()
        except Exception:
            r, g, b = 26, 20, 16 # Fallback
            
        # Style the main widget background HERE
        self.setStyleSheet(f"""
            CommandInputWidget {{
                background-color: rgba({r}, {g}, {b}, {input_opacity});
                border-radius: 10px;
                padding: 5px;
                border: 2px solid {colors['border_dark']};
            }}
        """)
        
        # Style for the command line edit
        self.command_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {colors['input_background']};
                color: {colors['input_text']};
                border: 1px solid {colors['input_border']};
                border-radius: 4px;
                padding: 8px;
                font-family: '{fonts['family_user_input']}';
                font-size: {fonts['size_user_input']}pt;
                margin-left: 5px;
                margin-right: 5px;
            }}
            QLineEdit:focus {{
                border-color: {colors['text_primary']};
            }}
        """)
        
        # Load the icon from the theme path and set it on the button
        icon_path = paths.get('send_button_icon', '')
        if icon_path:
            self.submit_button.setIcon(QIcon(icon_path))
        
        # Apply the transparent, round stylesheet from the factory
        self.submit_button.setStyleSheet(create_round_image_button_style(self.palette, 40))