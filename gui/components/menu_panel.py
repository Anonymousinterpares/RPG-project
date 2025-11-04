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

COLORS = {
    'background_med_transparent': 'rgba(45, 37, 32, 0.5)', # rgba version of #2d2520
    'border_light': '#5a4a40',
    'text_ivory': '#fff5cc',
    'background_light': '#3a302a',
    'border_dark': '#4a3a30',
    'hover': '#4a3a30',
    'pressed': '#1a1410',
    'negative_text': '#D94A38',
}
# --- END STYLING COLORS ---

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
        
        # Set frame properties using rgba for background
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            MenuPanelWidget {{
                background-color: {COLORS['background_med_transparent']}; 
                border: 1px solid {COLORS['border_light']}; 
                border-radius: 5px;
            }}
        """)
        
        # Get resource manager
        self.resource_manager = get_resource_manager()
        
        # Create animation properties
        self._expanded = True
        self._animation = None
        self._expanded_width = 150
        self._collapsed_width = 40
        
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
        self.toggle_button.setStyleSheet(f"""
            QToolButton {{
                background-color: {COLORS['background_light']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 3px;
                padding: 3px;
            }}
            QToolButton:hover {{
                background-color: {COLORS['hover']};
            }}
            QToolButton:pressed {{
                background-color: {COLORS['pressed']};
            }}
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

        # Wire UI sounds for left menu clicks (generic)
        try:
            from gui.utils.ui_sfx import map_container
            map_container(self, click_kind='click')
        except Exception:
            pass
    
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
        button.setStyleSheet(f"""
            QPushButton {{
                background-image: url('images/gui/button_normal.png');
                background-position: center;
                background-repeat: no-repeat;
                background-color: transparent;
                color: {COLORS['text_ivory']};
                border: none;
                padding: 8px;
                text-align: center;
                min-width: 100px;
                max-width: 110px;
                min-height: 35px;
                border-radius: 5px;
                margin-left: 5px;
                margin-right: 10px;
            }}
            QPushButton:hover {{
                background-image: url('images/gui/button_hover.png');
            }}
            QPushButton:pressed {{
                background-image: url('images/gui/button_pressed.png');
                color: {COLORS['negative_text']};
                font-weight: bold;
            }}
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
