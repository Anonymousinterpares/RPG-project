#!/usr/bin/env python3
"""
Menu panel widget for the RPG game GUI.
This module provides a collapsible left menu panel.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFrame, 
    QToolButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QPropertyAnimation, QSize, QEasingCurve

from gui.styles.stylesheet_factory import create_image_button_style
from gui.styles.theme_manager import get_theme_manager
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
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---

        # Set frame properties
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        
        # Create the new root layout that will hold the content and spacer
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # Get resource manager
        self.resource_manager = get_resource_manager()
        
        # Create animation properties
        self._expanded = True
        self._animation = None
        self._expanded_width = 150
        self._collapsed_width = 40
        
        # Set up the UI
        self._setup_ui()

        # Apply initial theme
        self._update_theme()

    def _setup_ui(self):
        """Set up the user interface."""
        # This frame will contain the buttons and have the background image
        self.content_container = QFrame()
        
        # This is the original layout, now placed inside the content_container
        self.main_layout = QVBoxLayout(self.content_container)
        self.main_layout.setContentsMargins(5, 5, 10, 5)
        self.main_layout.setSpacing(10)
        
        # Create toggle button
        self.toggle_button = QToolButton()
        self.toggle_button.setIcon(self.resource_manager.get_icon("toggle_button_left"))
        self.toggle_button.setIconSize(QSize(16, 16))
        self.toggle_button.clicked.connect(self.toggle_expanded)
        
        # Create menu buttons
        self.new_game_button = self._create_menu_button("New Game", "new_game")
        self.new_game_button.clicked.connect(self.new_game_requested.emit)
        
        self.save_button = self._create_menu_button("Save", "save_game")
        self.save_button.clicked.connect(self.save_game_requested.emit)
        
        self.load_button = self._create_menu_button("Load", "load_game")
        self.load_button.clicked.connect(self.load_game_requested.emit)
        
        self.settings_button = self._create_menu_button("Settings", "settings")
        self.settings_button.clicked.connect(self.settings_requested.emit)
        
        self.llm_settings_button = self._create_menu_button("LLM", "llm_settings")
        self.llm_settings_button.clicked.connect(self.llm_settings_requested.emit)
        
        self.exit_button = self._create_menu_button("Exit", "exit")
        self.exit_button.clicked.connect(self.exit_requested.emit)
        
        # Add buttons to the content_container's layout
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
        
        # This is the transparent spacer at the bottom
        self.bottom_spacer = QFrame()
        self.bottom_spacer.setFixedHeight(50) # Default height, will be updated by MainWindow

        # Add the two main components to the root layout
        self._root_layout.addWidget(self.content_container, 1) # Content stretches
        self._root_layout.addWidget(self.bottom_spacer, 0)   # Spacer has fixed height

        # Set initial width of the entire panel
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
        
        # Use the centralized stylesheet factory
        button.setStyleSheet(create_image_button_style(self.palette))
        
        return button
    
    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        paths = self.palette['paths']

        # The main MenuPanelWidget is now just a transparent container
        self.setStyleSheet("MenuPanelWidget { background-color: transparent; border: none; }")

        # Apply the background image to the content_container
        background_path = paths.get('menu_panel_background', '').replace("\\", "/")
        self.content_container.setStyleSheet(f"""
            QFrame {{
                background-color: transparent; /* Make base transparent for image */
                border-image: url('{background_path}') 0 0 0 0 stretch stretch;
                border: 1px solid {colors['border_light']}; 
                border-radius: 5px;
            }}
        """)

        # The bottom spacer should be fully transparent
        self.bottom_spacer.setStyleSheet("background-color: transparent; border: none;")

        self.toggle_button.setStyleSheet(f"""
            QToolButton {{
                background-color: {colors['bg_light']};
                border: 1px solid {colors['border_dark']};
                border-radius: 3px;
                padding: 3px;
            }}
            QToolButton:hover {{
                background-color: {colors['state_hover']};
            }}
            QToolButton:pressed {{
                background-color: {colors['state_pressed']};
            }}
        """)

        # Re-apply styles to all menu buttons
        for button in [self.new_game_button, self.save_button, self.load_button,
                       self.settings_button, self.llm_settings_button, self.exit_button]:
            button.setStyleSheet(create_image_button_style(self.palette))

    def setBottomSpacerHeight(self, height: int):
        """Sets the fixed height of the transparent spacer at the bottom."""
        self.bottom_spacer.setFixedHeight(height)
    
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
