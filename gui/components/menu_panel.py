#!/usr/bin/env python3
"""
Menu panel widget for the RPG game GUI.
This module provides a collapsible left menu panel.
"""

import logging
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFrame, 
    QToolButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QPropertyAnimation, QSize, QEasingCurve, Property
from PySide6.QtGui import QIcon, QPixmap

from gui.utils.resource_manager import get_resource_manager

class MenuPanelWidget(QFrame):
    """Collapsible left menu panel for the RPG game GUI."""
    
    # Signals for menu actions
    new_game_requested = Signal()
    save_game_requested = Signal()
    load_game_requested = Signal()
    settings_requested = Signal()
    llm_settings_requested = Signal()
    exit_requested = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the menu panel widget."""
        super().__init__(parent)

        # Set the desired opacity (0 = fully transparent, 100 = fully opaque)
        menu_panel_opacity_percent = 50 # Example: 85% opaque (adjust as needed)

        # Convert percentage to alpha value (0.0 to 1.0)
        alpha_value = menu_panel_opacity_percent / 100.0

        # Define the base background color RGB values (from #333333)
        base_r, base_g, base_b = 51, 51, 51
        
        # Set frame properties using rgba for background
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            MenuPanelWidget {{
                /* Use rgba for background color with transparency */
                background-color: rgba({base_r}, {base_g}, {base_b}, {alpha_value}); 
                
                /* Keep other styles */
                border: 1px solid #555555; 
                border-radius: 5px;
            }}
            /* Ensure buttons inside the panel remain opaque (using their own styles) */
            /* No changes needed here as buttons have specific styles set later */
        """)
        

        
        # Get resource manager
        self.resource_manager = get_resource_manager()
        
        # Create animation properties
        self._expanded = True
        self._animation = None
        self._expanded_width = 150  # Increase width from 100 to 120
        self._collapsed_width = 40  # Increase collapsed width from 30 to 40
        
        # Set up the UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 10, 5)
        self.main_layout.setSpacing(10)
        
        # Create toggle button
        self.toggle_button = QToolButton()
        self.toggle_button.setIcon(self.resource_manager.get_icon("toggle_button_left"))
        self.toggle_button.setIconSize(QSize(16, 16))
        self.toggle_button.setStyleSheet("""
            QToolButton {
                background-color: #444444;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
            }
            QToolButton:hover {
                background-color: #555555;
            }
            QToolButton:pressed {
                background-color: #333333;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_expanded)
        
        # Create menu buttons
        self.new_game_button = self._create_menu_button("New Game", "new_game")
        self.new_game_button.clicked.connect(self.new_game_requested.emit)
        
        self.save_button = self._create_menu_button("Save", "save_game")
        self.save_button.clicked.connect(self.save_game_requested.emit)
        
        self.load_button = self._create_menu_button("Load", "load_game")
        self.load_button.clicked.connect(self.load_game_requested.emit)
        
        # Settings button
        self.settings_button = self._create_menu_button("Settings", "settings")
        self.settings_button.clicked.connect(self.settings_requested.emit)
        
        self.llm_settings_button = self._create_menu_button("LLM", "llm_settings")
        self.llm_settings_button.clicked.connect(self.llm_settings_requested.emit)
        
        self.exit_button = self._create_menu_button("Exit", "exit")
        self.exit_button.clicked.connect(self.exit_requested.emit)
        
        # Add buttons to layout
        self.main_layout.addWidget(self.toggle_button, 0, Qt.AlignRight)
        self.main_layout.addSpacing(50)
        self.main_layout.addWidget(self.new_game_button)
        self.main_layout.addWidget(self.save_button)
        self.main_layout.addWidget(self.load_button)
        self.main_layout.addWidget(self.settings_button)
        self.main_layout.addWidget(self.llm_settings_button)
        self.main_layout.addSpacing(100)
        self.main_layout.addWidget(self.exit_button)
        self.main_layout.addStretch(1)  
        
        # Set initial width
        self.setFixedWidth(self._expanded_width)
    
    def _create_menu_button(self, text: str, icon_name: str) -> QPushButton:
        """Create a styled menu button.
        
        Args:
            text: The button text
            icon_name: The icon name (without path or extension)
            
        Returns:
            The created button
        """
        button = QPushButton(text)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Use generic button backgrounds instead of specific ones
        button.setStyleSheet("""
            QPushButton {
                background-image: url('images/gui/button_normal.png');
                background-position: center;
                background-repeat: no-repeat;
                background-color: transparent;

                color: #E0E0E0;
                border: none;
                padding: 8px;
                text-align: center;
                min-width: 100px;
                max-width: 110px;
                min-height: 35px;
                border-radius: 5px;
                margin-left: 5px;
                margin-right: 10px;
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
        
        return button
    
    def toggle_expanded(self):
        """Toggle the expanded/collapsed state of the panel."""
        self.setExpanded(not self._expanded)
    
    def setExpanded(self, expanded: bool):
        """Set the expanded/collapsed state of the panel.
        
        Args:
            expanded: True to expand, False to collapse
        """
        if self._expanded == expanded:
            return
        
        # Update state
        self._expanded = expanded
        
        # Update toggle button icon
        if expanded:
            self.toggle_button.setIcon(self.resource_manager.get_icon("toggle_button_left"))
        else:
            self.toggle_button.setIcon(self.resource_manager.get_icon("toggle_button_right"))
        
        # Hide/show buttons when collapsed/expanded
        for button in [
            self.new_game_button,
            self.save_button,
            self.load_button,
            self.settings_button,
            self.llm_settings_button,
            self.exit_button
        ]:
            # Store original text when collapsing
            if expanded:
                button.setText(button.property("original_text"))
                button.setVisible(True)
            else:
                if not button.property("original_text"):
                    button.setProperty("original_text", button.text())
                button.setText("")
                button.setVisible(False)
        
        # Only toggle button remains visible when collapsed
        if not expanded:
            self.toggle_button.setVisible(True)
        
        # Animate width change
        target_width = self._expanded_width if expanded else self._collapsed_width
        
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"minimumWidth")
        self._animation.setDuration(300)
        self._animation.setStartValue(self.width())
        self._animation.setEndValue(target_width)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._animation.start()
    
    def isExpanded(self) -> bool:
        """Get the expanded/collapsed state of the panel.
        
        Returns:
            True if expanded, False if collapsed
        """
        return self._expanded
    
    def sizeHint(self) -> QSize:
        """Get the recommended size for the widget.
        
        Returns:
            The recommended size
        """
        if self._expanded:
            return QSize(self._expanded_width, super().sizeHint().height())
        else:
            return QSize(self._collapsed_width, super().sizeHint().height())
