#!/usr/bin/env python3
"""
Enemies panel for the combat display.
"""
from typing import Dict, Any, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Slot

from core.utils.logging_config import get_logger
from gui.components.combat_entity_widget import CombatEntityWidget
from core.utils.logging_config import get_logger
from gui.styles.theme_manager import get_theme_manager

logger = get_logger("GUI")

class EnemiesPanel(QWidget): # Changed base class to QWidget
    """A widget to display the enemy entities in combat."""

class EnemiesPanel(QWidget): # Changed base class to QWidget
    """A widget to display the enemy entities in combat."""

    def __init__(self, parent=None): # Removed title from __init__
        """Initialize the EnemiesPanel."""
        super().__init__(parent) # Changed super() call
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self.apply_theme)
        # --- END THEME MANAGEMENT ---
        
        # Make this widget transparent so the parent's background shows through
        self.setStyleSheet("background-color: transparent; border: none;")
        
        self.entity_widgets: Dict[str, CombatEntityWidget] = {}

        # Main layout for this panel
        self.panel_layout = QVBoxLayout(self)
        self.panel_layout.setContentsMargins(5, 10, 5, 5)
        self.panel_layout.setSpacing(5)
        self.panel_layout.addStretch() 

    @Slot(dict)
    def apply_theme(self, palette: Optional[Dict[str, Any]] = None):
        """Apply theme palette to the panel and its children."""
        if not palette:
            palette = self.theme_manager.get_current_palette()
            
        # Pass the full palette down to child widgets
        for widget in self.entity_widgets.values():
            widget.update_style(palette)

    def apply_settings(self, settings: Dict[str, Any]):
        """Apply style settings to the panel and its children."""
        for widget in self.entity_widgets.values():
            widget.update_style(settings)

    def update_enemies(self, enemies_data: Dict[str, Dict[str, Any]], current_turn_id: Optional[str]):
        """Update the displayed enemy widgets based on the provided data."""
        existing_ids_in_data = set(enemies_data.keys())
        current_widget_ids = set(self.entity_widgets.keys())

        # Remove widgets for enemies no longer in the data
        for entity_id_to_remove in current_widget_ids - existing_ids_in_data:
            if entity_id_to_remove in self.entity_widgets:
                widget = self.entity_widgets.pop(entity_id_to_remove)
                self.panel_layout.removeWidget(widget)
                widget.deleteLater()
                logger.info(f"EnemiesPanel: Removed widget for entity: {entity_id_to_remove}")

        # Update existing widgets and add new ones
        for entity_id, entity_data in enemies_data.items():
            is_active_turn = (entity_id == current_turn_id)
            display_name = entity_data.get("combat_name", entity_data.get("name", entity_id))
            
            # Extract stats
            current_hp = int(entity_data.get("current_hp", 0))
            max_hp = int(entity_data.get("max_hp", 1))
            current_stamina = int(entity_data.get("current_stamina", 0))
            max_stamina = int(entity_data.get("max_stamina", 1))
            current_mana = int(entity_data.get("current_mana", 0))
            max_mana = int(entity_data.get("max_mana", 1))
            status_effects = entity_data.get("status_effects", [])

            if entity_id in self.entity_widgets:
                widget = self.entity_widgets[entity_id]
                widget.name_label.setText(display_name)
                # In combat, full updates are driven by animation phases.
                # This ensures max values and status effects are kept current.
                widget.hp_bar.setRange(0, max_hp if max_hp > 0 else 1)
                widget.stamina_bar.setRange(0, max_stamina if max_stamina > 0 else 1)
                widget.mana_bar.setRange(0, max_mana if max_mana > 0 else 1)
                widget.status_text.setText(", ".join(status_effects) if status_effects else "None")
                widget.highlight_active(is_active_turn)
            else:
                logger.info(f"EnemiesPanel: Creating new widget for {display_name}")
                # Pass the current theme palette on creation
                widget = CombatEntityWidget(entity_id=entity_id, name=display_name, settings=self.theme_manager.get_current_palette(), is_player=False)
                widget.update_stats(current_hp, max_hp, current_stamina, max_stamina, status_effects, current_mana, max_mana)
                widget.highlight_active(is_active_turn)
                
                # Insert the new widget before the stretch item
                self.panel_layout.insertWidget(self.panel_layout.count() - 1, widget)
                self.entity_widgets[entity_id] = widget

    def clear_enemies(self):
        """Remove all enemy widgets from the panel."""
        while self.panel_layout.count() > 1: # Keep the stretch item
            item = self.panel_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.entity_widgets.clear()