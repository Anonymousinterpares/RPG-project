#!/usr/bin/env python3
"""
Right panel widget for the RPG game GUI.
This module provides a collapsible, tabbed right panel.
"""

import logging
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QFrame, 
    QHBoxLayout, QPushButton, QStackedWidget, QToolButton, QTabBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QPropertyAnimation, QSize, QEasingCurve, Property, QSettings
from PySide6.QtGui import QIcon, QPixmap, QCursor

from gui.utils.resource_manager import get_resource_manager
from gui.components.character_sheet import CharacterSheetWidget
from gui.components.inventory_panel import InventoryPanelWidget
from gui.components.journal_panel import JournalPanelWidget
from gui.components.context_panel import ContextPanelWidget
from gui.components.grimoire_panel import GrimoirePanelWidget

class CustomTabBar(QTabBar):
    """Custom tab bar that emits a signal when the selected tab is clicked again."""
    
    tab_clicked_twice = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_index = -1
    
    def mousePressEvent(self, event):
        """Handle mouse press events to detect double clicks on selected tabs."""
        index = self.tabAt(event.pos())
        
        if index != -1 and index == self.currentIndex():
            self.tab_clicked_twice.emit(index)
        
        # Let the normal event processing happen
        super().mousePressEvent(event)

class CollapsibleRightPanel(QFrame):
    """Collapsible, tabbed right panel for the RPG game GUI."""
    
    # Signals
    tab_changed = Signal(int)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the right panel widget."""
        super().__init__(parent)
        
        # Set the desired opacity (0 = fully transparent, 100 = fully opaque)
        right_panel_opacity_percent = 50
        
        # Convert percentage to alpha value (0.0 to 1.0)
        alpha_value = right_panel_opacity_percent / 100.0

        # Define the base background color RGB values (from #333333)
        base_r, base_g, base_b = 51, 51, 51
        
        # Set frame properties using rgba for background
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            CollapsibleRightPanel {{
                /* Use rgba for background color with transparency */
                background-color: rgba({base_r}, {base_g}, {base_b}, {alpha_value}); 
                
                /* Keep other styles */
                border: 1px solid #555555; 
                border-radius: 5px;
            }}
            /* Child widgets like QTabWidget will have their own styles set below */
        """)
        
        # Get resource manager
        self.resource_manager = get_resource_manager()
        
        # Create animation properties
        self._expanded = True
        self._animation = None
        self._expanded_width = 480
        self._collapsed_width = 30
        
        # Set up the UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create tab widget with custom tab bar
        self.tab_widget = QTabWidget()
        self.custom_tab_bar = CustomTabBar()
        self.tab_widget.setTabBar(self.custom_tab_bar)
        
        # Connect custom tab bar signal
        self.custom_tab_bar.tab_clicked_twice.connect(self.toggle_expanded)
        
        # Style the tab widget
        self.tab_widget.setStyleSheet("""
            QTabWidget,
            QTabWidget QWidget, /* Target widgets directly inside QTabWidget */
            QTabWidget QScrollArea,
            QTabWidget QScrollArea > QWidget > QFrame, /* Target frames within scroll areas */
            QTabWidget QScrollArea > QWidget { /* Target viewport widget */
                background-color: transparent; /* Make immediate children transparent */
                color: #E0E0E0;
                border: none;
            }
            QTabWidget::pane { /* The area behind the tabs' content */
                background-color: #2E2E2E; /* Opaque dark color - slightly different from panel bg */
                border: 1px solid #444444;
                border-top: none; /* Remove top border as it's covered by tabs */
                border-radius: 0px; /* Pane doesn't need radius if panel has it */
                padding: 5px; /* Add some padding for content */
                margin: 0px;
            }
            QTabBar::tab { /* Individual tabs */
                background-color: #444444; /* Opaque tab background */
                color: #BBBBBB;
                border: 1px solid #555555;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { /* Selected tab */
                background-color: #2E2E2E; /* Match the pane background */
                color: #E0E0E0;
                border-bottom: 1px solid #2E2E2E; /* Make it look connected */
            }
            QTabBar::tab:hover:!selected { /* Hovered non-selected tab */
                background-color: #505050;
            }
            /* Ensure specific content widgets (like CharacterSheetWidget) have transparent backgrounds */
            /* if you want the pane background (#2E2E2E) to show through */
            CharacterSheetWidget, InventoryPanelWidget, JournalPanelWidget {
                 background-color: transparent;
            }
            /* Inputs across right panel */
            QTabWidget QLineEdit, QTabWidget QComboBox {
                background-color: #2E2E2E;
                color: #E0E0E0;
                border: 1px solid #555555;
                padding: 4px;
            }
        """)
        
        # Create tabs
        self.character_sheet = CharacterSheetWidget()
        self.inventory_panel = InventoryPanelWidget()
        self.journal_panel = JournalPanelWidget()
        self.grimoire_panel = GrimoirePanelWidget()
        
        # Add tabs
        self.tab_widget.addTab(self.character_sheet, "Character")
        self.tab_widget.addTab(self.inventory_panel, "Inventory")
        self.tab_widget.addTab(self.journal_panel, "Journal")
        self.tab_widget.addTab(self.grimoire_panel, "Grimoire")

        # Dev-only: Context tab
        try:
            dev_enabled = QSettings("RPGGame", "Settings").value("dev/enabled", False, type=bool)
            if bool(dev_enabled):
                self.context_panel = ContextPanelWidget()
                self.tab_widget.addTab(self.context_panel, "Context")
        except Exception:
            pass
        
        # Create toggle button (only visible when collapsed)
        self.toggle_button = QToolButton()
        self.toggle_button.setIcon(self.resource_manager.get_icon("toggle_button_right")) # This icon might need to change based on state
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
        
        # Always show the toggle button
        self.toggle_button.setVisible(True)
        
        # Create stacked widget to switch between tab widget and collapsed view
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.tab_widget)  # Index 0: Expanded view with tabs
        
        # We don't use a separate collapsed view anymore
        # Instead, just modify the width of the panel while keeping tabs visible
        # This way, users can always see tab headers and expand the panel by clicking on them
        
        # Add toggle button directly to the main layout
        toggle_container = QWidget()
        toggle_layout = QHBoxLayout(toggle_container) # Changed to QHBoxLayout for horizontal alignment
        toggle_layout.setContentsMargins(0, 5, 5, 0) # Add right margin
        toggle_layout.addStretch() # Push button to the right
        toggle_layout.addWidget(self.toggle_button) # No alignment needed if stretch is used
        
        # Add toggle container to top of main layout
        self.main_layout.addWidget(toggle_container) # Add the container
        
        # Add stacked widget to main layout
        self.main_layout.addWidget(self.stacked_widget)
        
        # Set initial width
        self.setFixedWidth(self._expanded_width)

        # Wire UI sounds: right panel clicks -> tab_click, tabs -> tab_click, dropdowns -> dropdown
        try:
            from gui.utils.ui_sfx import map_container
            map_container(self, click_kind='tab_click', tab_kind='tab_click', dropdown_kind='dropdown')
        except Exception:
            pass
        
        # Connect tab changed signal
        self.tab_widget.currentChanged.connect(self._handle_tab_change)

    def _handle_tab_change(self, index):
        """Handle tab change event."""
        # Emit signal
        self.tab_changed.emit(index)
    
    def toggle_expanded(self, index=None):
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
        
        # When collapsing, don't switch to the collapsed widget view
        # Instead, just resize the panel, keeping the tabs visible
        # This ensures users can still see and click on tabs
        
        # Animate width change
        target_width = self._expanded_width if expanded else self._collapsed_width
        
        if self._animation:
            self._animation.stop()
        
        # Animate the panel's fixedWidth property
        self._animation = QPropertyAnimation(self, b"fixedWidth") # Animate fixedWidth
        self._animation.setDuration(300)
        self._animation.setStartValue(self.width())
        self._animation.setEndValue(target_width)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._animation.start()

        # Update toggle button icon
        if self._expanded:
            self.toggle_button.setIcon(self.resource_manager.get_icon("toggle_button_right"))
            self.toggle_button.setToolTip("Collapse Panel")
        else:
            self.toggle_button.setIcon(self.resource_manager.get_icon("toggle_button_left"))
            self.toggle_button.setToolTip("Expand Panel")
    
    def set_dev_context_tab_enabled(self, enabled: bool):
        """Add or remove the Context tab based on 'enabled'."""
        try:
            from PySide6.QtWidgets import QWidget
            # Check if already present
            idx = -1
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "Context":
                    idx = i
                    break
            if enabled and idx == -1:
                self.context_panel = ContextPanelWidget()
                self.tab_widget.addTab(self.context_panel, "Context")
            elif (not enabled) and idx >= 0:
                w = self.tab_widget.widget(idx)
                self.tab_widget.removeTab(idx)
                try:
                    w.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass

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
    
    def update_character(self, character=None):
        """Update the character sheet tab with character data."""
        # If character is provided directly, update with it
        if character:
            self.character_sheet.update_character(character)
            return
        
        # Otherwise get current character from game state
        from core.base.state import get_state_manager
        state_manager = get_state_manager()
        if state_manager and state_manager.current_state and state_manager.current_state.player:
            # First ensure stats manager is initialized
            if state_manager.stats_manager:
                # Trigger an update with current state's player
                self.character_sheet.update_character(state_manager.current_state.player)
    
    def update_inventory(self, inventory=None):
        """Update the inventory tab with inventory data."""
        self.inventory_panel.update_inventory(inventory)
    
    def update_journal(self, journal_data=None):
        """Update the journal tab with journal data."""
        self.journal_panel.update_journal(journal_data)

    def update_grimoire(self):
        """Update the grimoire tab with player's known spells, current mode, and mana."""
        try:
            from core.base.state import get_state_manager
            from core.magic.spell_catalog import get_spell_catalog
            from core.stats.stats_base import DerivedStatType
            
            state_manager = get_state_manager()
            state = state_manager.current_state if state_manager else None
            player = getattr(state, 'player', None)
            mode = getattr(state, 'current_mode', None)
            
            # Get known spells
            known_spells = player.list_known_spells() if player and hasattr(player, 'list_known_spells') else []
            catalog = get_spell_catalog()
            
            # Build spells grouped by system
            spells_by_system = {}
            for sid in known_spells:
                sp = catalog.get_spell_by_id(sid)
                if not sp:
                    continue
                spells_by_system.setdefault(sp.system_id, []).append(sp)
            
            # Get current and max mana from stats manager
            current_mana = 0.0
            max_mana = 0.0
            if state_manager and state_manager.stats_manager:
                try:
                    current_mana = state_manager.stats_manager.get_stat_value(DerivedStatType.MANA)
                    max_mana = state_manager.stats_manager.get_stat_value(DerivedStatType.MAX_MANA)
                except Exception:
                    pass
            
            self.grimoire_panel.refresh(spells_by_system, mode, current_mana, max_mana)
        except Exception:
            # Fail-safe: clear panel
            try:
                self.grimoire_panel.refresh({}, None, 0.0, 0.0)
            except Exception:
                pass
