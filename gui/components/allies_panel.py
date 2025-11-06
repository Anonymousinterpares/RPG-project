#!/usr/bin/env python3
"""
Allies panel for the combat display.
"""
import logging
from typing import Dict, Any, Optional

from PySide6.QtWidgets import QGroupBox, QVBoxLayout
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtCore import Qt

from gui.components.combat_entity_widget import CombatEntityWidget
from core.utils.logging_config import get_logger

logger = get_logger("GUI")

class AlliesPanel(QGroupBox):
    """A widget to display the player and their allies in combat."""

    def __init__(self, title: str, parent=None):
        """Initialize the AlliesPanel."""
        super().__init__(title, parent)
        self.entity_widgets: Dict[str, CombatEntityWidget] = {}
        self._setup_cursors()

        # Main layout for this panel
        self.panel_layout = QVBoxLayout(self)
        self.panel_layout.setContentsMargins(5, 10, 5, 5)
        self.panel_layout.setSpacing(5)
        self.panel_layout.addStretch() # Add initial stretch

    def _setup_cursors(self):
        """Load custom cursors from image files for this component."""
        try:
            normal_pixmap = QPixmap("images/gui/cursors/NORMAL.cur")
            link_pixmap = QPixmap("images/gui/cursors/LINK-SELECT.cur")
            text_pixmap = QPixmap("images/gui/cursors/TEXT.cur")

            if normal_pixmap.isNull():
                self.normal_cursor = QCursor(Qt.ArrowCursor)
            else:
                self.normal_cursor = QCursor(normal_pixmap, 0, 0)

            if link_pixmap.isNull():
                self.link_cursor = QCursor(Qt.PointingHandCursor)
            else:
                self.link_cursor = QCursor(link_pixmap, 0, 0)

            if text_pixmap.isNull():
                self.text_cursor = QCursor(Qt.IBeamCursor)
            else:
                self.text_cursor = QCursor(text_pixmap, int(text_pixmap.width() / 2), int(text_pixmap.height() / 2))

        except Exception as e:
            logger.error(f"AlliesPanel: Error setting up custom cursors: {e}")
            self.normal_cursor = QCursor(Qt.ArrowCursor)
            self.link_cursor = QCursor(Qt.PointingHandCursor)
            self.text_cursor = QCursor(Qt.IBeamCursor)
        
        self.setCursor(self.normal_cursor)

    def apply_settings(self, settings: Dict[str, Any]):
        """Apply style settings to the panel and its children."""
        for widget in self.entity_widgets.values():
            widget.update_style(settings)

    def update_allies(self, allies_data: Dict[str, Dict[str, Any]], current_turn_id: Optional[str]):
        """Update the displayed ally widgets based on the provided data."""
        existing_ids_in_data = set(allies_data.keys())
        current_widget_ids = set(self.entity_widgets.keys())

        # Remove widgets for allies no longer in the data
        for entity_id_to_remove in current_widget_ids - existing_ids_in_data:
            if entity_id_to_remove in self.entity_widgets:
                widget = self.entity_widgets.pop(entity_id_to_remove)
                self.panel_layout.removeWidget(widget)
                widget.deleteLater()
                logger.info(f"AlliesPanel: Removed widget for entity: {entity_id_to_remove}")

        # Update existing widgets and add new ones
        for entity_id, entity_data in allies_data.items():
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
                logger.info(f"AlliesPanel: Creating new widget for {display_name}")
                widget = CombatEntityWidget(entity_id=entity_id, name=display_name, settings={}, is_player=True)
                widget.update_stats(current_hp, max_hp, current_stamina, max_stamina, status_effects, current_mana, max_mana)
                widget.highlight_active(is_active_turn)
                
                # Insert the new widget before the stretch item
                self.panel_layout.insertWidget(self.panel_layout.count() - 1, widget)
                self.entity_widgets[entity_id] = widget

    def clear_allies(self):
        """Remove all ally widgets from the panel."""
        while self.panel_layout.count() > 1: # Keep the stretch item
            item = self.panel_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.entity_widgets.clear()