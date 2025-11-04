#!/usr/bin/env python3
"""
Character sheet widget for the RPG game GUI.
This module provides a widget for displaying the player character's information.
"""

import logging
import re
from typing import Optional, Dict, Any, List, Union, Callable
from PySide6.QtWidgets import (QListWidget,QListWidgetItem,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QTextEdit,
    QScrollArea, QFrame, QGroupBox, QProgressBar, QMenu, QToolTip
)
from PySide6.QtCore import Qt, Slot, Signal, QPoint
from PySide6.QtGui import QFont, QPixmap, QCursor, QMouseEvent,QColor

from core.base.state import get_state_manager
from core.interaction.enums import InteractionMode
from core.inventory.item import Item
from core.inventory.item_enums import EquipmentSlot
from core.inventory.item_manager import get_inventory_manager
from core.stats.modifier import StatModifier
from core.stats.stats_base import StatType, DerivedStatType, Stat, StatCategory
from core.stats.stats_manager import get_stats_manager
from core.utils.logging_config import get_logger
from gui.components.ap_display_widget import APDisplayWidget

logger = get_logger("GUI")

# --- STYLING COLORS ---
COLORS = {
    'background_dark': '#1a1410',
    'background_med': '#2d2520',
    'background_light': '#3a302a',
    'border_dark': '#4a3a30',
    'border_light': '#5a4a40',
    'text_primary': '#c9a875',
    'text_secondary': '#8b7a65',
    'text_disabled': '#5a4a40',
    'text_bright': '#e8d4b8',
    'mana': '#1178BB',
    'mana_dark': '#0b5a8e',
    'health': '#D94A38',
    'health_dark': '#a03628',
    'stamina': '#5a9068',
    'stamina_dark': '#3a6a48',
    'exp': '#c9a875',
    'exp_dark': '#8b7a65',
    'positive': '#5a9068', # Green for buffs/success
    'negative': '#D94A38', # Red for debuffs/damage
    'selected': '#c9a875',
    'hover': '#4a3a30',
}
# --- END STYLING COLORS ---
class StatLabel(QLabel):
    """A label for displaying a stat that shows details on right-click."""
    
    def __init__(self, text: str, stat_name: str, parent=None):
        """
        Initialize the stat label.

        Args:
            text: The initial text to display.
            stat_name: The name of the stat this label represents (e.g., "STR", "MELEE_ATTACK").
            parent: The parent widget.
        """
        super().__init__(text, parent)
        # Store the enum name (e.g., "STR") for consistency with StatsManager keys
        self.stat_name_key = stat_name # Keep the original key passed in
        self.description = ""
        self.base_value = 0
        self.current_value = 0
        # Modifiers will be fetched dynamically for tooltip
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events to show tooltips."""
        if event.button() == Qt.RightButton:
            self.show_tooltip(event.globalPos())
        super().mousePressEvent(event)
    
    def _fetch_modifiers(self) -> List[Dict[str, Any]]:
        """Fetch the list of modifiers for this stat."""
        try:
            # Get the StatsManager instance
            stats_manager = get_stats_manager()
            if not stats_manager:
                return []

            # Convert the stored stat_name_key back to the enum type if possible
            stat_type_enum = None
            try:
                stat_type_enum = StatType[self.stat_name_key]
            except KeyError:
                try:
                    stat_type_enum = DerivedStatType[self.stat_name_key]
                except KeyError:
                    logging.warning(f"Could not convert stat key '{self.stat_name_key}' to StatType or DerivedStatType for fetching modifiers.")
                    return []

            # Check if ModifierManager has a method to get the list
            # Assuming a method get_modifiers_for_stat exists or can be added
            if hasattr(stats_manager.modifier_manager, 'get_modifiers_for_stat'):
                # This method should return List[StatModifier] or List[Dict]
                mods = stats_manager.modifier_manager.get_modifiers_for_stat(stat_type_enum)
                # Convert StatModifier objects to dicts if necessary
                if mods and isinstance(mods[0], StatModifier):
                     return [mod.to_dict() for mod in mods] # Assuming StatModifier has to_dict()
                elif mods and isinstance(mods, list):
                     return mods # Assume it's already a list of dicts
                else:
                     return []
            else:
                # Fallback or log warning if the method doesn't exist
                logging.warning(f"ModifierManager lacks 'get_modifiers_for_stat' method.")
                return []

        except Exception as e:
            logging.error(f"Error fetching modifiers for {self.stat_name_key}: {e}")
            return []

    def show_tooltip(self, position: QPoint) -> None:
        """Show detailed tooltip for the stat."""
        # Fetch modifiers dynamically
        modifiers = self._fetch_modifiers()

        # Get the display name (e.g., "Strength") if available, otherwise use the key
        display_name = self.stat_name_key  # Default to key
        if hasattr(self, 'display_name_override'):  # Check if set by update_stat_data
            display_name = self.display_name_override

        tooltip_text = f"<div style='background-color: {COLORS['background_med']}; padding: 10px; border: 2px solid {COLORS['border_dark']}; border-radius: 4px;'>"
        tooltip_text += f"<b style='color: {COLORS['text_primary']};'>{display_name}</b><hr style='border: 1px solid {COLORS['border_dark']};'>"

        if self.description:
            tooltip_text += f"<i style='color: {COLORS['text_secondary']};'>{self.description}</i><br><br>"

        # Base / Total / Delta header with color-coded delta
        try:
            delta_val = (self.current_value or 0) - (self.base_value or 0)
        except Exception:
            delta_val = 0
        delta_sign = "+" if delta_val > 0 else ""
        delta_color = COLORS['positive'] if delta_val > 0 else (COLORS['negative'] if delta_val < 0 else COLORS['text_secondary'])
        
        tooltip_text += f"<p style='color: {COLORS['text_secondary']}; margin: 2px 0;'>"
        tooltip_text += f"Base: {self.base_value}<br>"
        tooltip_text += f"Total: <b style='color: {COLORS['text_bright']};'>{self.current_value}</b>"
        if delta_val != 0:
            tooltip_text += f" <span style='color:{delta_color}'>({delta_sign}{int(delta_val)})</span>"
        tooltip_text += "</p>"

        # Detailed modifiers list with color-coded values
        if modifiers:
            tooltip_text += f"<br><b style='color: {COLORS['text_primary']};'>Modifiers:</b><br><ul style='margin: 0; padding-left: 15px; color: {COLORS['text_secondary']};'>"
            for mod in modifiers:
                # Access modifier data assuming it's a dictionary now
                mod_source = mod.get('source_name') or mod.get('source') or 'Unknown'
                mod_value = mod.get('value', 0)
                mod_is_percentage = mod.get('is_percentage', False)
                mod_duration = mod.get('duration', None)

                sign = "+" if isinstance(mod_value, (int, float)) and mod_value > 0 else ""
                color = COLORS['positive'] if (isinstance(mod_value, (int, float)) and mod_value > 0) else (COLORS['negative'] if (isinstance(mod_value, (int, float)) and mod_value < 0) else COLORS['text_secondary'])
                val_text = f"<span style='color:{color}'>{sign}{mod_value}{'%' if mod_is_percentage else ''}</span>"
                dur_text = f" ({mod_duration} turns)" if (mod_duration is not None) else ""
                tooltip_text += f"<li>{mod_source}: {val_text}{dur_text}</li>"
            tooltip_text += "</ul>"
        else:
            tooltip_text += f"<br><i style='color: {COLORS['text_disabled']};'>No active modifiers.</i>"
        
        tooltip_text += "</div>"

        QToolTip.showText(position, tooltip_text)

    def show_context_menu(self, position: QPoint) -> None:
        """Show context menu for the stat."""
        # Get the display name (e.g., "Strength") if available, otherwise use the key
        display_name = self.stat_name_key # Default to key
        if hasattr(self, 'display_name_override'): # Check if set by update_stat_data
            display_name = self.display_name_override

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['background_med']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_dark']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['hover']};
                color: {COLORS['selected']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {COLORS['border_dark']};
                margin: 4px 8px;
            }}
        """)
        menu.addAction(f"{display_name} Details", lambda: self.show_tooltip(QCursor.pos()))
        menu.exec_(self.mapToGlobal(position))

    def update_stat_data(self, stat_data: Dict[str, Any]) -> None:
        """
        Update the stat data stored in the label for tooltip display.

        Args:
            stat_data: Dictionary containing stat information from StatsManager.
        """
        # Store the display name ("Strength") if provided, distinct from the key ("STR")
        if 'name' in stat_data:
            self.display_name_override = str(stat_data['name'])

        if 'description' in stat_data:
            self.description = stat_data['description']
        if 'base_value' in stat_data:
            self.base_value = stat_data['base_value']
        if 'value' in stat_data:
            self.current_value = stat_data['value']
class CharacterSheetWidget(QScrollArea):
    """Widget for displaying character information."""

    item_unequip_from_slot_requested = Signal(EquipmentSlot)
    item_examine_requested = Signal(str) 
    item_drop_from_slot_requested = Signal(EquipmentSlot, str)
    
    def __init__(self, parent: Optional[QWidget] = None):
            """Initialize the character sheet widget."""
            super().__init__(parent)

            self.setWidgetResizable(True)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setStyleSheet(f"""
                QScrollArea {{
                    background-color: transparent;
                    border: none;
                }}
            """)

            self.character_widget = QWidget()
            self.setWidget(self.character_widget)
            self.state_manager = get_state_manager()
            self._signal_connected = False

            self._pending_player_bar_updates: Dict[str, Dict[str, Any]] = {} 

            self._setup_ui() 
            self._clear_stat_displays()

    def _setup_ui(self):
        # Create the main layout
        self.main_layout = QVBoxLayout(self.character_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(15)
        
        # Initialize dictionaries for stat labels
        self.primary_stat_labels = {}
        self.derived_stat_labels = {}
        
        # Create character header
        self._create_header()
        
        # Create stats section
        self._create_stats_section()
        
        # Create skills section
        self._create_skills_section()
        
        # Create equipment section
        self._create_equipment_section()

    def _create_header(self):
        """Create the character header section with enhanced styling."""
        header_group = QGroupBox("Character")
        header_group.setStyleSheet(self._get_groupbox_style())
        
        header_layout = QHBoxLayout(header_group)
        
        # Character portrait frame
        portrait_frame = QFrame()
        portrait_frame.setFrameShape(QFrame.StyledPanel)
        portrait_frame.setFixedSize(100, 100)
        portrait_frame.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {COLORS['border_dark']};
                background-color: {COLORS['background_dark']};
                border-radius: 4px;
            }}
        """)
        
        self.portrait_label = QLabel("Portrait")
        self.portrait_label.setAlignment(Qt.AlignCenter)
        self.portrait_label.setStyleSheet(f"color: {COLORS['text_disabled']};")
        self.portrait_label.setScaledContents(True)
        
        portrait_layout = QVBoxLayout(portrait_frame)
        portrait_layout.addWidget(self.portrait_label)
        
        # Character info
        info_layout = QVBoxLayout()
        
        self.name_label = QLabel("Name: Unknown")
        self.name_label.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {COLORS['text_primary']};")
        
        self.race_class_label = QLabel("Race: Unknown | Class: Unknown")
        self.race_class_label.setStyleSheet(f"font-size: 12pt; color: {COLORS['text_primary']};")
        
        self.level_exp_label = QLabel("Level: 1 | Experience: 0/100")
        self.level_exp_label.setStyleSheet(f"font-size: 11pt; color: {COLORS['text_secondary']};")
        
        # Experience bar with gradient styling
        self.exp_bar = QProgressBar()
        self.exp_bar.setRange(0, 100)
        self.exp_bar.setValue(0)
        self.exp_bar.setTextVisible(True)
        self.exp_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['background_dark']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 3px;
                text-align: center;
                color: {COLORS['text_bright']};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['exp']}, stop:1 {COLORS['exp_dark']});
                border-radius: 3px;
            }}
        """)
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.race_class_label)
        info_layout.addWidget(self.level_exp_label)
        info_layout.addWidget(self.exp_bar)
        
        header_layout.addWidget(portrait_frame)
        header_layout.addLayout(info_layout, 1)
        
        self.main_layout.addWidget(header_group)
    
    def _create_stats_section(self):
        """Create the character stats section with enhanced styling."""
        
        # --- Primary Stats Group ---
        primary_stats_group = QGroupBox("Primary Stats")
        primary_stats_group.setStyleSheet(self._get_groupbox_style())
        primary_stats_layout = QGridLayout(primary_stats_group)
        primary_stats_layout.setColumnStretch(0, 1)
        primary_stats_layout.setColumnStretch(1, 0)
        primary_stats_layout.setColumnStretch(2, 1)
        primary_stats_layout.setColumnStretch(3, 0)
        primary_stats_layout.setColumnMinimumWidth(1, 50)
        primary_stats_layout.setColumnMinimumWidth(3, 50)
        primary_stats_layout.setHorizontalSpacing(10)

        self._add_stat(primary_stats_layout, 0, 0, StatType.STRENGTH.name, "Strength", "")
        self._add_stat(primary_stats_layout, 0, 1, StatType.DEXTERITY.name, "Dexterity", "")
        self._add_stat(primary_stats_layout, 1, 0, StatType.CONSTITUTION.name, "Constitution", "")
        self._add_stat(primary_stats_layout, 1, 1, StatType.INTELLIGENCE.name, "Intelligence", "")
        self._add_stat(primary_stats_layout, 2, 0, StatType.WISDOM.name, "Wisdom", "")
        self._add_stat(primary_stats_layout, 2, 1, StatType.CHARISMA.name, "Charisma", "")
        self._add_stat(primary_stats_layout, 3, 0, StatType.WILLPOWER.name, "Willpower", "")
        self._add_stat(primary_stats_layout, 3, 1, StatType.INSIGHT.name, "Insight", "")

        # --- Resources Group ---
        resources_group = QGroupBox("Resources")
        resources_group.setStyleSheet(self._get_groupbox_style())
        resources_layout = QVBoxLayout(resources_group)

        self.resource_bars = {}
        self._add_resource_bar(resources_layout, "Health", 100, 100, COLORS['health'], COLORS['health_dark'])
        self._add_resource_bar(resources_layout, "Mana", 50, 50, COLORS['mana'], COLORS['mana_dark'])
        self._add_resource_bar(resources_layout, "Stamina", 100, 100, COLORS['stamina'], COLORS['stamina_dark'])

        # --- Combat Info Group ---
        combat_info_group = QGroupBox("Combat Info")
        combat_info_group.setStyleSheet(self._get_groupbox_style())
        combat_info_layout = QVBoxLayout(combat_info_group)

        self.ap_display = APDisplayWidget(self)
        combat_info_layout.addWidget(self.ap_display)

        # Status Effects section
        status_label = QLabel("Status Effects:")
        status_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 13px; margin-top: 10px;")
        combat_info_layout.addWidget(status_label)

        self.status_effects_list = QTextEdit()
        self.status_effects_list.setReadOnly(True)
        self.status_effects_list.setMaximumHeight(60)
        self.status_effects_list.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['background_dark']};
                border: 1px solid {COLORS['border_dark']};
                color: {COLORS['text_bright']};
                padding: 5px;
                border-radius: 3px;
            }}
        """)
        combat_info_layout.addWidget(self.status_effects_list)
        
        # Turn Order section
        turn_label = QLabel("Turn Order:")
        turn_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 13px; margin-top: 10px;")
        combat_info_layout.addWidget(turn_label)

        self.turn_order_list = QTextEdit()
        self.turn_order_list.setReadOnly(True)
        self.turn_order_list.setMaximumHeight(80)
        self.turn_order_list.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['background_dark']};
                border: 1px solid {COLORS['border_dark']};
                color: {COLORS['text_bright']};
                padding: 5px;
                border-radius: 3px;
                line-height: 1.2;
            }}
        """)
        combat_info_layout.addWidget(self.turn_order_list)

        # Initiative label
        initiative_layout = QHBoxLayout()
        initiative_title_label = QLabel("Initiative:")
        initiative_title_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 13px;")
        self.initiative_value = QLabel("0")
        self.initiative_value.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: 13px;")
        self.initiative_value.setAlignment(Qt.AlignRight)
        initiative_layout.addWidget(initiative_title_label)
        initiative_layout.addWidget(self.initiative_value)
        combat_info_layout.addLayout(initiative_layout)

        # --- Derived Stats Group ---
        derived_stats_group = QGroupBox("Derived Stats")
        derived_stats_group.setStyleSheet(self._get_groupbox_style())
        derived_stats_layout = QGridLayout(derived_stats_group)
        derived_stats_layout.setColumnStretch(0, 1)
        derived_stats_layout.setColumnStretch(1, 0)
        derived_stats_layout.setColumnStretch(2, 1)
        derived_stats_layout.setColumnStretch(3, 0)
        derived_stats_layout.setColumnMinimumWidth(1, 50)
        derived_stats_layout.setColumnMinimumWidth(3, 50)
        derived_stats_layout.setHorizontalSpacing(10)

        self._add_stat(derived_stats_layout, 0, 0, DerivedStatType.MELEE_ATTACK.name, "Melee Attack", "")
        self._add_stat(derived_stats_layout, 0, 1, DerivedStatType.RANGED_ATTACK.name, "Ranged Attack", "")
        self._add_stat(derived_stats_layout, 1, 0, DerivedStatType.MAGIC_ATTACK.name, "Magic Attack", "")
        self._add_stat(derived_stats_layout, 1, 1, DerivedStatType.DEFENSE.name, "Defense", "")
        self._add_stat(derived_stats_layout, 2, 0, DerivedStatType.MAGIC_DEFENSE.name, "Magic Defense", "")
        self._add_stat(derived_stats_layout, 3, 0, DerivedStatType.CARRY_CAPACITY.name, "Carry Capacity", "")
        self._add_stat(derived_stats_layout, 3, 1, DerivedStatType.MOVEMENT.name, "Movement", "")
        self._add_stat(derived_stats_layout, 2, 1, DerivedStatType.DAMAGE_REDUCTION.name, "Damage Reduction", "")

        # Add all groups to main layout
        self.main_layout.addWidget(resources_group)
        self.main_layout.addWidget(combat_info_group)
        self.main_layout.addWidget(primary_stats_group)
        self.main_layout.addWidget(derived_stats_group)
        
    def _add_stat(self, layout, row, col, stat_id, stat_name, value):
        """Add a stat to the stats layout with enhanced styling."""
        label = QLabel(f"{stat_name}:")
        label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600; padding-right: 5px; font-size: 13px;")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        value_label = StatLabel(value, stat_id)
        try:
            value_label.setTextFormat(Qt.RichText)
        except Exception:
            pass
        value_label.setStyleSheet(f"color: {COLORS['text_bright']}; min-width: 50px; padding-left: 5px; font-size: 13px;")
        value_label.setAlignment(Qt.AlignLeft)

        if stat_id in [s.name for s in StatType]:
            self.primary_stat_labels[stat_id] = value_label
        else:
            self.derived_stat_labels[stat_id] = value_label

        layout.addWidget(label, row, col * 2)
        layout.addWidget(value_label, row, col * 2 + 1)

    def _add_resource_bar(self, layout, name, value, max_value, light_color, dark_color):
        """Add a resource bar with gradient styling."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)
        
        label = QLabel(f"{name}: {value}/{max_value}")
        label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 13px;")
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, max_value)
        progress_bar.setValue(value)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat(f"%v/%m")
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['background_dark']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 3px;
                text-align: center;
                color: {COLORS['text_bright']};
                height: 22px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {light_color}, stop:1 {dark_color});
                border-radius: 3px;
            }}
        """)
        
        container_layout.addWidget(label)
        container_layout.addWidget(progress_bar)
        
        self.resource_bars[name.lower()] = (label, progress_bar)
        
        layout.addWidget(container)

    def _create_skills_section(self):
        """Create the character skills section with enhanced styling."""
        skills_group = QGroupBox("Skills")
        skills_group.setStyleSheet(self._get_groupbox_style())
        
        skills_layout = QVBoxLayout(skills_group)
        
        self.no_skills_label = QLabel("No skills available yet.")
        self.no_skills_label.setStyleSheet(f"color: {COLORS['text_disabled']}; font-style: italic;")
        self.no_skills_label.setAlignment(Qt.AlignCenter)
        
        skills_layout.addWidget(self.no_skills_label)
        
        self.main_layout.addWidget(skills_group)

    def _create_equipment_section(self):
        """Create the character equipment section with enhanced styling."""
        equipment_group = QGroupBox("Equipment")
        equipment_group.setStyleSheet(self._get_groupbox_style())
        
        equipment_layout = QGridLayout(equipment_group)
        equipment_layout.setSpacing(5)
        
        self.equip_labels: Dict[str, CharacterSheetWidget.EquippedItemLabel] = {}
        slots_to_display = [
            EquipmentSlot.HEAD, EquipmentSlot.NECK,
            EquipmentSlot.CHEST, EquipmentSlot.BACK,
            EquipmentSlot.SHOULDERS, EquipmentSlot.WRISTS,
            EquipmentSlot.HANDS, EquipmentSlot.WAIST,
            EquipmentSlot.LEGS, EquipmentSlot.FEET,
            EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND,
            EquipmentSlot.FINGER_1, EquipmentSlot.FINGER_2,
            EquipmentSlot.TRINKET_1, EquipmentSlot.TRINKET_2
        ]

        num_cols = 2
        for i, slot_enum in enumerate(slots_to_display):
            row = i // num_cols
            col = i % num_cols
            
            slot_display_name = slot_enum.value.replace('_', ' ').title()
            
            slot_label_widget = QLabel(f"{slot_display_name}:")
            slot_label_widget.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600; padding-right: 5px; font-size: 13px;")
            slot_label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            value_label_widget = CharacterSheetWidget.EquippedItemLabel("None", slot_enum, None, self)
            value_label_widget.set_item_data("None", None)
            value_label_widget.setMinimumWidth(120)
            value_label_widget.setWordWrap(True)
            value_label_widget.context_menu_requested_for_slot.connect(self._handle_equipped_item_context_menu)
            
            self.equip_labels[slot_enum.value] = value_label_widget
            
            equipment_layout.addWidget(slot_label_widget, row, col * 2)
            equipment_layout.addWidget(value_label_widget, row, col * 2 + 1)
        
        self.main_layout.addWidget(equipment_group)

    def update_character(self, character=None):
            """
            Update the character sheet with character data.

            Args:
                character: The character data object (PlayerState). If None, uses current state.
            """
            if not self._signal_connected:
                self._connect_stats_signal()

            try:
                if character is None:
                    if self.state_manager and self.state_manager.current_state:
                        character = self.state_manager.current_state.player
                    else:
                        logger.warning("No character data available to update character sheet")
                        self._clear_stat_displays()
                        return

                self.name_label.setText(f"Name: {character.name}")
                self.race_class_label.setText(f"Race: {character.race} | Class: {character.path}")
                exp_current = character.experience
                exp_next = character.experience_to_next_level
                self.level_exp_label.setText(f"Level: {character.level} | Experience: {exp_current}/{exp_next}")
                self.exp_bar.setRange(0, exp_next if exp_next > 0 else 100) 
                self.exp_bar.setValue(exp_current)

                if self.state_manager and self.state_manager.stats_manager:
                    stats_manager = self.state_manager.stats_manager
                    all_stats = stats_manager.get_all_stats()

                    if 'primary' in all_stats:
                        self._update_primary_stats(all_stats["primary"])
                    else:
                        logger.warning("Primary stats category not found in stats data.")

                    for category in ["combat", "social", "other"]: 
                        if category in all_stats:
                            self._update_derived_stats(all_stats[category], category)
                        else:
                            logger.warning(f"Derived stats category '{category}' not found in stats data.")

                    if "resources" in all_stats:
                        self._update_resources(all_stats["resources"], all_player_stats=all_stats)
                    else:
                        logger.warning("Resources category not found in stats data.")
                    self._update_combat_status(character)
                else:
                    logger.warning("Stats manager not available during update_character, stats will not be displayed.")
                    self._clear_stat_displays()

                inventory_manager = get_inventory_manager()
                if inventory_manager:
                    for slot_key_str, label_widget in self.equip_labels.items():
                        # Reset with default text and no item_id
                        label_widget.set_item_data("None", None) 
                    
                    if hasattr(inventory_manager, 'equipment'):
                        two_handed_weapon_equipped: Optional[Item] = None
                        # inventory_manager.equipment is Dict[EquipmentSlot, Optional[Item]]
                        potential_two_handed_item_obj = inventory_manager.equipment.get(EquipmentSlot.TWO_HAND)
                        if potential_two_handed_item_obj and isinstance(potential_two_handed_item_obj, Item):
                             two_handed_weapon_equipped = potential_two_handed_item_obj

                        for slot_enum, item_obj_from_inv_mgr in inventory_manager.equipment.items():
                            slot_key = slot_enum.value 
                            if item_obj_from_inv_mgr and isinstance(item_obj_from_inv_mgr, Item) and slot_key in self.equip_labels:
                                current_label_widget = self.equip_labels[slot_key]
                                if two_handed_weapon_equipped and item_obj_from_inv_mgr.id == two_handed_weapon_equipped.id:
                                    if EquipmentSlot.MAIN_HAND.value in self.equip_labels:
                                        self.equip_labels[EquipmentSlot.MAIN_HAND.value].set_item_data(f"{item_obj_from_inv_mgr.name} (2H)", item_obj_from_inv_mgr.id)
                                        self.equip_labels[EquipmentSlot.MAIN_HAND.value].setToolTip(item_obj_from_inv_mgr.description or item_obj_from_inv_mgr.name)
                                    if EquipmentSlot.OFF_HAND.value in self.equip_labels:
                                        self.equip_labels[EquipmentSlot.OFF_HAND.value].set_item_data(f"- (2H: {item_obj_from_inv_mgr.name}) -", None) # No item_id for placeholder
                                        self.equip_labels[EquipmentSlot.OFF_HAND.value].setStyleSheet("color: #777777;")
                                        self.equip_labels[EquipmentSlot.OFF_HAND.value].setToolTip(f"Occupied by Two-Handed: {item_obj_from_inv_mgr.name}")
                                    if EquipmentSlot.TWO_HAND.value in self.equip_labels:
                                         self.equip_labels[EquipmentSlot.TWO_HAND.value].set_item_data(item_obj_from_inv_mgr.name, item_obj_from_inv_mgr.id)
                                         self.equip_labels[EquipmentSlot.TWO_HAND.value].setToolTip(item_obj_from_inv_mgr.description or item_obj_from_inv_mgr.name)
                                elif slot_enum == EquipmentSlot.MAIN_HAND and two_handed_weapon_equipped:
                                    continue 
                                elif slot_enum == EquipmentSlot.OFF_HAND and two_handed_weapon_equipped:
                                    continue
                                else: 
                                    current_label_widget.set_item_data(item_obj_from_inv_mgr.name, item_obj_from_inv_mgr.id)
                                    current_label_widget.setToolTip(item_obj_from_inv_mgr.description or item_obj_from_inv_mgr.name)
                else:
                    logger.warning("CharacterSheetWidget: InventoryManager not available for equipment update.")

                if hasattr(character, 'character_image') and character.character_image:
                    try:
                        pixmap = QPixmap(character.character_image)
                        if not pixmap.isNull():
                            scaled_pixmap = pixmap.scaled(self.portrait_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            self.portrait_label.setPixmap(scaled_pixmap)
                            self.portrait_label.setStyleSheet("")
                        else:
                            self.portrait_label.setText("Portrait")
                            self.portrait_label.setStyleSheet("color: #888888;")
                    except Exception as image_err:
                        logging.error(f"Error loading character portrait: {image_err}")
                        self.portrait_label.setText("Portrait")
                        self.portrait_label.setStyleSheet("color: #888888;")
                else:
                    self.portrait_label.setText("Portrait")
                    self.portrait_label.setStyleSheet("color: #888888;")

            except Exception as e:
                logger.error(f"Error updating character sheet: {e}", exc_info=True)

    def _update_combat_status(self, character):
        """Update combat status information.
        This method is now less critical for turn order if TURN_ORDER_UPDATE events are used,
        but kept for fallback and status effects.
        Args:
            character: The player character instance.
        """
        if not character:
            return
            
        from core.base.state import get_state_manager # Local import
        state_manager = get_state_manager()
        if not state_manager or not state_manager.current_state:
            self.status_effects_list.clear()
            self.turn_order_list.setText("Turn Order: N/A") # Default text
            self.initiative_value.setText("0")
            return
            
        game_state = state_manager.current_state
        combat_manager = getattr(game_state, 'combat_manager', None)
        
        # Update status effects (Logic for status effects seems okay, no changes here unless explicitly requested)
        self.status_effects_list.clear()
        status_text = ""
        player_entity_for_effects = None

        if combat_manager:
            player_id_for_lookup = getattr(character, 'id', None) or getattr(character, 'stats_manager_id', None)
            if player_id_for_lookup and player_id_for_lookup in combat_manager.entities:
                player_entity_for_effects = combat_manager.entities[player_id_for_lookup]
        
        source_for_effects = player_entity_for_effects if player_entity_for_effects else character

        if hasattr(source_for_effects, 'status_effects'):
            effects_data = source_for_effects.status_effects
            if isinstance(effects_data, dict):
                for effect_name, duration_data in effects_data.items():
                    duration = None
                    if isinstance(duration_data, int): 
                        duration = duration_data
                    
                    if duration is not None and duration > 0 : 
                        status_text += f"{effect_name} ({duration} turns)\n"
                    elif duration is None: 
                        status_text += f"{effect_name}\n"
            elif isinstance(effects_data, (list, set)):
                for effect_name in effects_data:
                    status_text += f"{effect_name}\n"
        
        self.status_effects_list.setText(status_text.strip())
        
        # Turn order display will be primarily handled by handle_turn_order_update event.
        # This section can act as a fallback or for initial display if no event received yet.
        if not combat_manager:
            self.turn_order_list.setText("Turn Order: N/A (Not in Combat)")
            self.initiative_value.setText("0")
        elif not hasattr(self, '_last_turn_order_event_data') or not self._last_turn_order_event_data:
            # Fallback logic if no TURN_ORDER_UPDATE event has populated the display yet
            logger.debug("CharacterSheet: _update_combat_status using fallback for turn order.")
            turn_text = ""
            if getattr(combat_manager, '_is_surprise_round', False) and hasattr(combat_manager, '_surprise_round_entities') and combat_manager._surprise_round_entities:
                turn_text += "[Surprise Round]\n"
                current_actor_id_for_highlight = getattr(combat_manager, '_active_entity_id', None)
                for entity_id_in_surprise_order in combat_manager._surprise_round_entities:
                    if entity_id_in_surprise_order in combat_manager.entities:
                        entity = combat_manager.entities[entity_id_in_surprise_order]
                        prefix = "→ " if entity_id_in_surprise_order == current_actor_id_for_highlight else "  "
                        turn_text += f"{prefix}{getattr(entity, 'combat_name', entity.name)}\n"
            elif hasattr(combat_manager, 'turn_order') and combat_manager.turn_order: # Regular round
                current_turn_idx = getattr(combat_manager, 'current_turn_index', 0)
                for i, entity_id_in_order in enumerate(combat_manager.turn_order):
                    if entity_id_in_order in combat_manager.entities:
                        entity = combat_manager.entities[entity_id_in_order]
                        is_current_actor_by_index = (i == current_turn_idx)
                        prefix = "→ " if is_current_actor_by_index else "  "
                        turn_text += f"{prefix}{getattr(entity, 'combat_name', entity.name)}\n"
            else:
                turn_text = "Turn Order: Initializing..."
            self.turn_order_list.setText(turn_text.strip())

            player_id_for_initiative = getattr(character, 'id', None) or getattr(character, 'stats_manager_id', None)
            entity_for_initiative_display = combat_manager.entities.get(player_id_for_initiative)
            if entity_for_initiative_display and hasattr(entity_for_initiative_display, 'initiative'):
                initiative_value = getattr(entity_for_initiative_display, 'initiative', 0)
                self.initiative_value.setText(str(int(initiative_value)))
            else:
                self.initiative_value.setText("N/A")

    def _connect_stats_signal(self):
        """Connect to the stats_changed signal of the StatsManager."""
        if self._signal_connected:
            logging.debug("Signal already connected, skipping.")
            return

        try:
            if self.state_manager and self.state_manager.stats_manager:
                stats_manager = self.state_manager.stats_manager
                signal_exists = hasattr(stats_manager, 'stats_changed')

                if signal_exists:
                    try:
                        # Disconnect first to avoid duplicates if connection attempt repeats
                        stats_manager.stats_changed.disconnect(self._update_from_stats)
                    except (TypeError, RuntimeError): # Catch specific Qt signal errors
                        pass # Ignore if not connected

                    stats_manager.stats_changed.connect(self._update_from_stats)
                    self._signal_connected = True
                    logging.info("Connected CharacterSheetWidget to stats_changed signal")
            else:
                 logging.debug("StatsManager not yet available for signal connection.")

        except Exception as e:
            logging.error(f"Failed to connect to stats_changed signal: {e}")
    
    def _update_from_stats(self, stats_data):
        """Update the character sheet directly from stats data provided by the signal."""
        logging.info("Updating character sheet from stats_changed signal")

        try:
            # Provide detailed logging about the stats data received
            if isinstance(stats_data, dict):
                category_counts = {k: len(v) for k, v in stats_data.items() if isinstance(v, dict)}
                logging.info(f"Stats data categories from signal: {category_counts}")
                # ...(rest of logging as before)...

                # Check for empty or invalid stats before proceeding
                has_valid_stats = any(
                    category in stats_data and isinstance(stats_data[category], dict) and stats_data[category]
                    for category in ['primary', 'resources', 'combat', 'social', 'other']
                )

                if not has_valid_stats:
                    logging.warning("Stats data from signal appears empty or invalid.")
                    # Optionally, could trigger a full update here, but might cause loops
                    # self.update_character()
                    return

                # Update primary stats
                if 'primary' in stats_data:
                    self._update_primary_stats(stats_data['primary'])
                    logging.info(f"Updated {len(stats_data['primary'])} primary stats from signal")

                # Update derived stats including combat, social, other
                for category in ['combat', 'social', 'other']:
                    if category in stats_data:
                        self._update_derived_stats(stats_data[category], category)
                        logging.info(f"Updated {len(stats_data[category])} {category} stats from signal")

                # Update resource bars (HP, Mana, Stamina)
                if 'resources' in stats_data:
                    # Pass the full stats_data (which is all_stats) to _update_resources
                    self._update_resources(stats_data['resources'], all_player_stats=stats_data)
                    logging.info(f"Updated {len(stats_data['resources'])} resources from signal")
                
                # Update combat status (turn order, status effects) if player data is available
                if self.state_manager and self.state_manager.current_state and self.state_manager.current_state.player:
                    self._update_combat_status(self.state_manager.current_state.player)
                    logging.info("Updated combat status from stats_changed signal context.")
                else:
                    logging.warning("Could not update combat status from signal: player state unavailable.")


                logging.info("Character sheet updated directly from stats data via signal")
            else:
                # Fallback to full update if data format isn't as expected (less likely now)
                logging.warning(f"Stats data from signal is not a dict: {type(stats_data)}, falling back to full update")
                self.update_character() # Trigger full refresh as fallback

        except Exception as e:
            logging.error(f"Error updating from stats signal: {e}", exc_info=True)
            # Fallback to full update on error
            try:
                self.update_character()
            except Exception as update_err:
                logging.error(f"Fallback update after signal error also failed: {update_err}")
                
    def _update_primary_stats(self, primary_stats):
        """Update just the primary stats from stats data, showing colored deltas."""
        for stat_name, stat_data in primary_stats.items():
            # stat_name here is expected to be "STR", "DEX", etc.
            if stat_name in self.primary_stat_labels:
                try:
                    value = int(stat_data.get('value', 0))
                    base = int(stat_data.get('base_value', value))
                    delta = value - base
                    delta_sign = "+" if delta > 0 else ""
                    delta_color = COLORS['positive'] if delta > 0 else (COLORS['negative'] if delta < 0 else COLORS['text_bright'])

                    # Compose HTML with colored delta
                    new_text = f"{value}"
                    if delta != 0:
                        new_text += f" <span style='color:{delta_color}'>({delta_sign}{delta})</span>"

                    old_text = self.primary_stat_labels[stat_name].text()
                    if old_text != new_text:
                        self.primary_stat_labels[stat_name].setText(new_text)
                        logging.info(f"Updated primary stat {stat_name} from '{old_text}' to '{new_text}'")

                    # Update tooltip data regardless
                    self.primary_stat_labels[stat_name].update_stat_data(stat_data)
                except Exception as e:
                    logging.error(f"Error updating primary stat {stat_name}: {e}", exc_info=True)
            else:
                logging.warning(f"Stat key '{stat_name}' from primary stats data not found in UI labels.")
    
    def _update_derived_stats(self, derived_stats, category):
        """Update derived stats from stats data, showing colored deltas."""
        for stat_name, stat_data in derived_stats.items():
            # stat_name here is expected to be "MELEE_ATTACK", "DEFENSE", etc.
            if stat_name in self.derived_stat_labels:
                try:
                    value = int(stat_data.get('value', 0))
                    base = int(stat_data.get('base_value', value))
                    delta = value - base
                    delta_sign = "+" if delta > 0 else ""
                    delta_color = COLORS['positive'] if delta > 0 else (COLORS['negative'] if delta < 0 else COLORS['text_bright'])

                    new_text = f"{value}"
                    if delta != 0:
                        new_text += f" <span style='color:{delta_color}'>({delta_sign}{delta})</span>"

                    old_text = self.derived_stat_labels[stat_name].text()
                    if old_text != new_text:
                        self.derived_stat_labels[stat_name].setText(new_text)
                        logging.info(f"Updated {category} stat {stat_name} from '{old_text}' to '{new_text}'")

                    # Update tooltip data regardless
                    self.derived_stat_labels[stat_name].update_stat_data(stat_data)

                    # Special case for initiative display
                    if stat_name == "INITIATIVE":
                        if self.initiative_value.text() != str(value):
                            self.initiative_value.setText(str(value))
                            logging.info(f"Updated initiative display to {value}")
                except Exception as e:
                    logging.error(f"Error updating derived stat {stat_name}: {e}", exc_info=True)
            else:
                logging.warning(f"Stat key '{stat_name}' from {category} stats data not found in UI labels.")
    
    def _update_resources(self, resources: Dict[str, Any], all_player_stats: Optional[Dict[str, Any]] = None):
        """
        Update resource bars. During COMBAT, current values for HP, Mana, Stamina are primarily
        updated via orchestrated events (player_resource_bar_update_phaseX). This method will
        still update MAX values and, outside of combat, current values directly.
        """
        resource_key_map = {
            "HEALTH": "health", "MANA": "mana", "STAMINA": "stamina",
            "RESOLVE": "resolve" 
        }
        max_resource_map = {
            "HEALTH": "MAX_HEALTH", "MANA": "MAX_MANA", 
            "STAMINA": "MAX_STAMINA", "RESOLVE": "MAX_RESOLVE" 
        }

        for stat_name_key, resource_data in resources.items():
            ui_key = resource_key_map.get(stat_name_key.upper()) 

            if ui_key and ui_key in self.resource_bars:
                label, bar = self.resource_bars[ui_key]
                
                game_mode = InteractionMode.NARRATIVE # Default
                if self.state_manager and self.state_manager.current_state:
                    game_mode = self.state_manager.current_state.current_mode
                
                try:
                    current_value_from_model = int(resource_data.get('value', 0)) # Actual current value from stats model
                    max_stat_name_key = max_resource_map.get(stat_name_key.upper())
                    
                    # Determine Max Value (this should always reflect the true current max)
                    max_value_from_model = bar.maximum() if bar.maximum() > 0 else 100 
                    if all_player_stats and max_stat_name_key:
                        found_max_in_all_stats = False
                        for category_key in ['resources', 'other', 'primary', 'combat', 'social']: 
                            if category_key in all_player_stats and max_stat_name_key in all_player_stats[category_key]:
                                max_value_from_model = int(all_player_stats[category_key][max_stat_name_key].get('value', max_value_from_model))
                                found_max_in_all_stats = True
                                break
                        if not found_max_in_all_stats:
                           logger.warning(f"MAX stat {max_stat_name_key} not found in all_player_stats for {stat_name_key} in _update_resources. Using bar's current max.")
                    elif 'base_value' in resource_data and stat_name_key.upper().startswith("MAX_"): 
                         max_value_from_model = int(resource_data.get('base_value', max_value_from_model))
                    
                    max_value_from_model = max(1, max_value_from_model) 
                    display_name = resource_data.get("name", ui_key.capitalize()) 

                    # Always update the bar's range if the max value from model has changed
                    if bar.maximum() != max_value_from_model:
                        bar.setRange(0, max_value_from_model)
                        logger.info(f"CharacterSheet: {ui_key} bar max updated to {max_value_from_model} via _update_resources (model changed).")
                        # If max changed, the label will need updating too, unless an animation is active
                        if not (game_mode == InteractionMode.COMBAT and ui_key in self._pending_player_bar_updates):
                            current_display_val = bar.value() if game_mode == InteractionMode.COMBAT and ui_key in self._pending_player_bar_updates and self._pending_player_bar_updates[ui_key].get('phase1_preview_value') is not None else current_value_from_model
                            label.setText(f"{display_name}: {int(current_display_val)}/{max_value_from_model}")


                    # Handle current value updates
                    if game_mode == InteractionMode.COMBAT:
                        # In COMBAT, current value updates for HP, Mana, Stamina are driven by phase1/phase2 events.
                        # This method, when called by stats_changed, should not directly set the current value
                        # for these, to avoid conflicts with the animation.
                        # It only ensures MAX is correct. Resolve, if not animated, could be updated here.
                        if ui_key == "resolve": # Example: Resolve updates directly if not animated
                             if bar.value() != current_value_from_model: bar.setValue(current_value_from_model)
                             label.setText(f"{display_name}: {current_value_from_model}/{max_value_from_model}")
                        else:
                             logger.debug(f"CharacterSheet: In COMBAT, _update_resources deferring current value update for {ui_key} to orchestration.")
                             # If a phase1 animation is active, the label might show "X -> Y".
                             # If max_value changed, it's already updated above.
                             # If no animation is active, the label might be stale until phase1/2.
                             # Let's ensure label reflects at least the old value against new max if max changed.
                             if bar.maximum() == max_value_from_model and ui_key not in self._pending_player_bar_updates:
                                  current_on_bar = bar.value() # What the bar visually shows
                                  if label.text() != f"{display_name}: {int(current_on_bar)}/{max_value_from_model}":
                                       label.setText(f"{display_name}: {int(current_on_bar)}/{max_value_from_model}")


                    else: # Not in COMBAT mode, update directly
                        if bar.value() != current_value_from_model:
                            bar.setValue(current_value_from_model)
                        
                        new_text_direct = f"{display_name}: {current_value_from_model}/{max_value_from_model}"
                        if label.text() != new_text_direct:
                            label.setText(new_text_direct)
                        
                        # If there was any pending animation from a previous mode (unlikely but possible), clear it.
                        if ui_key in self._pending_player_bar_updates:
                            self._pending_player_bar_updates.pop(ui_key, None)
                        
                        logger.debug(f"CharacterSheet: Directly updated {ui_key} to {current_value_from_model}/{max_value_from_model} via _update_resources (not in combat).")
                    
                except Exception as e:
                    logging.error(f"CharacterSheet: Error updating resource bar for {stat_name_key} in _update_resources: {e}", exc_info=True)
            elif ui_key:
                logging.warning(f"UI key '{ui_key}' (from resource '{stat_name_key}') not found in self.resource_bars.")

    def _clear_stat_displays(self):
        """Helper method to reset all stat displays to default/empty."""
        logging.debug("Clearing character sheet stat displays.")
        # Clear primary stats
        for label in self.primary_stat_labels.values():
            label.setText("0") # Or "?" or ""
            label.update_stat_data({}) # Clear tooltip data

        # Clear derived stats
        for label in self.derived_stat_labels.values():
            label.setText("0") # Or "?" or ""
            label.update_stat_data({}) # Clear tooltip data

        # Clear resource bars
        for label, bar in self.resource_bars.values():
            label.setText(f"{label.text().split(':')[0]}: 0/0") # Keep name, reset values
            bar.setRange(0, 100) # Reset range
            bar.setValue(0) # Reset value

        # Clear initiative display
        self.initiative_value.setText("0")

        # Clear combat status
        self.status_effects_list.clear()
        self.turn_order_list.clear()
    
    def showEvent(self, event):
        """Handler called when widget is shown."""
        super().showEvent(event)

    @Slot(str, dict)
    def animate_resource_bar_ui_bar_update_phase1(self, bar_type_key: str, update_data: Dict[str, Any]):
        """
        Handles Phase 1 of a bar update: show impending loss/gain.
        bar_type_key: "hp", "stamina", "mana", "resolve"
        update_data: { "old_value": X, "new_value_preview": Y, "max_value": M }
        """
        bar_type_key_internal = bar_type_key
        if bar_type_key == "hp": # Normalize "hp" to "health" for internal lookup
            bar_type_key_internal = "health"
        
        if bar_type_key_internal not in self.resource_bars:
            logging.warning(f"CharacterSheet: Bar type '{bar_type_key_internal}' (from original key '{bar_type_key}') not found for phase 1 animation.")
            return

        label, bar = self.resource_bars[bar_type_key_internal]
        new_value_preview = update_data.get("new_value_preview")
        max_value = update_data.get("max_value")
        
        if new_value_preview is None or max_value is None:
            logging.error(f"CharacterSheet: Missing new_value_preview or max_value for phase 1 of {bar_type_key_internal}")
            return
            
        is_loss = new_value_preview < bar.value()

        logging.debug(f"CharacterSheet: Phase 1 Anim for {bar_type_key_internal} - Preview: {new_value_preview}/{max_value}")

        display_name = label.text().split(':')[0] 
        label.setText(f"{display_name}: {bar.value()}/{max_value} -> {new_value_preview}/{max_value}")
        
        self._pending_bar_updates[bar_type_key_internal] = {
            "final_value": new_value_preview,
            "max_value": max_value,
            "is_loss": is_loss
        }

    @Slot(str, dict)
    def animate_resource_bar_ui_bar_update_phase2(self, bar_type_key: str, update_data: Dict[str, Any]):
        """
        Handles Phase 2 of a bar update: finalize the bar to its new value.
        bar_type_key: "hp", "stamina", "mana", "resolve"
        update_data: { "final_new_value": Y, "max_value": M } (or use stored from pending)
        """
        bar_type_key_internal = bar_type_key
        if bar_type_key == "hp": # Normalize "hp" to "health" for internal lookup
            bar_type_key_internal = "health"

        if bar_type_key_internal not in self.resource_bars:
            logging.warning(f"CharacterSheet: Bar type '{bar_type_key_internal}' (from original key '{bar_type_key}') not found for phase 2 animation.")
            return
        
        pending_data = self._pending_bar_updates.pop(bar_type_key_internal, None)
        final_value = update_data.get("final_new_value", pending_data.get("final_value") if pending_data else None)
        max_value = update_data.get("max_value", pending_data.get("max_value") if pending_data else None)

        if final_value is None or max_value is None:
            # Attempt to get current value from bar if update_data is incomplete and no pending_data
            label_fallback, bar_fallback = self.resource_bars[bar_type_key_internal]
            final_value_fb = bar_fallback.value()
            max_value_fb = bar_fallback.maximum()

            if final_value is None: final_value = final_value_fb
            if max_value is None: max_value = max_value_fb
            
            logging.warning(f"CharacterSheet: Missing final_value or max_value for phase 2 of {bar_type_key_internal}. Using current/fallback: {final_value}/{max_value}")
            # Do not return; attempt to update with best available info.

        logging.debug(f"CharacterSheet: Phase 2 Anim for {bar_type_key_internal} - Final: {final_value}/{max_value}")

        label, bar = self.resource_bars[bar_type_key_internal]
        # Try to get original name part, handle cases where "->" might not be present
        original_name_part_match = re.match(r"([^:]+):", label.text())
        display_name = original_name_part_match.group(1).strip() if original_name_part_match else bar_type_key_internal.capitalize()


        label.setText(f"{display_name}: {int(final_value)}/{int(max_value)}")
        if bar.maximum() != int(max_value):
            bar.setRange(0, int(max_value))
        bar.setValue(int(final_value))

        logging.debug(f"CharacterSheet: {bar_type_key_internal} bar finalized to {int(final_value)}/{int(max_value)}")

    def _finalize_bar_animation(self, bar_type_key: str):
        """Helper to finalize a bar after a QTimer, if used internally (less common now)."""
        # This method is less likely to be used if Orchestrator handles delays.
        # Kept for potential future internal animation needs.
        if bar_type_key in self._pending_bar_updates:
            data = self._pending_bar_updates.pop(bar_type_key)
            self.animate_resource_bar_ui_bar_update_phase2(bar_type_key, {"final_new_value": data["final_value"], "max_value": data["max_value"]})

    def update_ap_display(self, current_ap: float, max_ap: float):
        """Updates the AP display widget with new values."""
        logger.info(f"[CharacterSheet] update_ap_display called with current_ap: {current_ap}, max_ap: {max_ap}")
        if hasattr(self, 'ap_display'):
            self.ap_display.update_ap(current_ap, max_ap)
        else:
            logger.error("[CharacterSheet] update_ap_display called, but self.ap_display widget does not exist!")

    @Slot(dict)
    def handle_turn_order_update(self, event_data: Dict[str, Any]):
        """
        Handles TURN_ORDER_UPDATE events from the orchestrator to update
        the turn order display and player initiative.
        """
        logger.info(f"CharacterSheet received TURN_ORDER_UPDATE: {event_data}")
        self._last_turn_order_event_data = event_data # Store for fallback if needed

        turn_text = ""
        is_surprise = event_data.get("is_surprise", False)
        round_num = event_data.get("round_number", "")
        turn_order_display_list = event_data.get("turn_order_display_list", []) # This should contain pre-formatted strings with "→"
        active_entity_name = event_data.get("active_entity_combat_name", "") # For initiative context

        if is_surprise:
            turn_text += f"[Surprise Round]\n"
        elif round_num:
            turn_text += f"Round {round_num}\n"
        
        if turn_order_display_list:
            turn_text += "\n".join(turn_order_display_list)
        else:
            turn_text += "Turn order not yet determined."

        self.turn_order_list.setText(turn_text.strip())

        # Update player's initiative display
        # If player is in the turn_order_display_list, try to extract their initiative
        # This assumes player's combat name is consistent
        player_id = getattr(self.state_manager.current_state.player, 'id', None) or getattr(self.state_manager.current_state.player, 'stats_manager_id', None)
        player_combat_name = getattr(self.state_manager.current_state.player, 'name', "Player") # Fallback
        
        # Get CombatManager to access player's CombatEntity for initiative
        combat_manager = getattr(self.state_manager.current_state, 'combat_manager', None)
        if combat_manager and player_id:
            player_combat_entity = combat_manager.entities.get(player_id)
            if player_combat_entity and hasattr(player_combat_entity, 'initiative'):
                self.initiative_value.setText(str(int(player_combat_entity.initiative)))
            else:
                self.initiative_value.setText("N/A")
        elif combat_manager: # Player ID not found, but CM exists
             self.initiative_value.setText("N/A (Player not in combat)")
        else: # Not in combat
            self.initiative_value.setText("0")

    @Slot(str, dict)
    def player_resource_bar_update_phase1(self, bar_type_key: str, update_data: Dict[str, Any]):
        """
        Handles Phase 1 of a player's resource bar update: show impending loss/gain in label.
        bar_type_key: "hp", "stamina", "mana", "resolve" (from event metadata)
        update_data: { "old_value": X, "new_value_preview": Y, "max_value": M, "entity_id": player_id }
        """
        logger.debug(f"CharacterSheet: Player Phase 1 Anim for event bar_type '{bar_type_key}' - Data: {update_data}")
        
        event_to_internal_key_map = {"hp": "health", "mp": "mana", "stamina": "stamina", "resolve": "resolve"}
        internal_ui_key = event_to_internal_key_map.get(bar_type_key.lower(), bar_type_key.lower())

        if internal_ui_key not in self.resource_bars:
            logging.warning(f"CharacterSheet: Player bar type '{internal_ui_key}' (mapped from event '{bar_type_key}') not found for phase 1 animation.")
            return

        label, bar = self.resource_bars[internal_ui_key]
        
        new_value_preview = update_data.get("new_value_preview")
        max_value = update_data.get("max_value")
        
        if new_value_preview is None or max_value is None:
            logging.error(f"CharacterSheet: Missing new_value_preview or max_value for player phase 1 of {internal_ui_key}")
            return
        
        current_bar_visual_value = bar.value() 
        
        display_name_match = re.match(r"([^:]+):", label.text())
        display_name = display_name_match.group(1).strip() if display_name_match else internal_ui_key.capitalize()
        
        label.setText(f"{display_name}: {int(current_bar_visual_value)}/{int(max_value)} -> {int(new_value_preview)}/{int(max_value)}")
        
        if bar.maximum() != int(max_value):
            bar.setRange(0, int(max_value))
            logger.info(f"CharacterSheet (Phase1): {internal_ui_key} bar max updated to {max_value}")

        self._pending_player_bar_updates[internal_ui_key] = {
            "final_value": new_value_preview, 
            "max_value": max_value,
            "phase1_preview_value": current_bar_visual_value 
        }

        # Signal orchestrator completion to avoid stalls when no CombatEntityWidget animation handles it
        try:
            from core.base.engine import get_game_engine
            from PySide6.QtCore import QTimer
            eng = get_game_engine()
            if eng and hasattr(eng, "_combat_orchestrator"):
                logger.debug("CharacterSheet: Signaling orchestrator visual completion for Phase 1 player bar update")
                QTimer.singleShot(0, eng._combat_orchestrator._handle_visual_display_complete)
        except Exception:
            pass

    @Slot(str, dict)
    def player_resource_bar_update_phase2(self, bar_type_key: str, update_data: Dict[str, Any]):
        """
        Handles Phase 2 of a player's resource bar update: finalize the bar to its new value.
        bar_type_key: "hp", "stamina", "mana", "resolve" (from event metadata)
        update_data: { "final_new_value": Y, "max_value": M, "entity_id": player_id }
        """
        event_to_internal_key_map = {"hp": "health", "mp": "mana", "stamina": "stamina", "resolve": "resolve"}
        internal_ui_key = event_to_internal_key_map.get(bar_type_key.lower(), bar_type_key.lower())

        logger.debug(f"CharacterSheet: Player Phase 2 Anim for internal_ui_key '{internal_ui_key}' (from event '{bar_type_key}') - Data: {update_data}")

        if internal_ui_key not in self.resource_bars:
            logging.warning(f"CharacterSheet: Player bar type '{internal_ui_key}' (mapped from event '{bar_type_key}') not found for phase 2 animation.")
            if internal_ui_key in self._pending_player_bar_updates:
                self._pending_player_bar_updates.pop(internal_ui_key, None)
            return
        
        pending_data = self._pending_player_bar_updates.pop(internal_ui_key, None)
        
        label, bar = self.resource_bars[internal_ui_key]

        final_value = update_data.get("final_new_value")
        max_val = update_data.get("max_value")

        if final_value is None:
            if pending_data and "final_value" in pending_data:
                final_value = pending_data["final_value"]
            else: 
                final_value = bar.value() 
                logger.warning(f"CharacterSheet (Phase2): for {internal_ui_key} missing final_new_value. Using current bar value {final_value}.")
        
        if max_val is None:
            if pending_data and "max_value" in pending_data:
                max_val = pending_data["max_value"]
            else: 
                max_val = bar.maximum()
                logger.warning(f"CharacterSheet (Phase2): for {internal_ui_key} missing max_value. Using current bar max {max_val}.")
        
        final_value = int(final_value)
        max_val = int(max_val)
        max_val = max(1, max_val)

        current_label_text = label.text()
        display_name_match = re.match(r"([^:]+):", current_label_text)
        display_name = display_name_match.group(1).strip() if display_name_match else internal_ui_key.capitalize()

        label.setText(f"{display_name}: {final_value}/{max_val}")
        if bar.maximum() != max_val: 
            bar.setRange(0, max_val)
        bar.setValue(final_value)

        logger.debug(f"CharacterSheet: Player {internal_ui_key} bar finalized to {final_value}/{max_val}")
        logging.info(f"CharacterSheet (Phase2 player): set {internal_ui_key} to {final_value}/{max_val}")

        # Signal orchestrator completion to avoid stalls when CharacterSheet handles the update without a CombatEntityWidget animation
        try:
            from core.base.engine import get_game_engine
            from PySide6.QtCore import QTimer
            eng = get_game_engine()
            if eng and hasattr(eng, "_combat_orchestrator"):
                logger.debug("CharacterSheet: Signaling orchestrator visual completion for Phase 2 player bar update")
                QTimer.singleShot(0, eng._combat_orchestrator._handle_visual_display_complete)
        except Exception:
            pass

    def _get_groupbox_style(self) -> str:
        """Helper to get consistent QGroupBox styling."""
        return f"""
            QGroupBox {{
                background-color: {COLORS['background_med']};
                border: 2px solid {COLORS['border_dark']};
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
                color: {COLORS['text_primary']};
                padding-top: 20px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
                color: {COLORS['text_primary']};
            }}
        """

    @Slot(QPoint, EquipmentSlot, str)
    def _handle_equipped_item_context_menu(self, global_pos: QPoint, slot: EquipmentSlot, item_id: str):
        inventory_manager = get_inventory_manager()
        item_obj = inventory_manager.get_item(item_id)
        if not item_obj:
            logger.error(f"[CHAR_SHEET_CTX] Item ID {item_id} not found for context menu in slot {slot.value}.")
            return

        logger.info(f"[CHAR_SHEET_CTX] Context menu for equipped item: '{item_obj.name}' in slot {slot.value}")

        context_menu = QMenu(self)
        # Apply styling similar to InventoryPanelWidget's context menu
        context_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['background_med']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_dark']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['hover']};
                color: {COLORS['selected']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {COLORS['border_dark']};
                margin: 4px 8px;
            }}
        """)

        unequip_action = context_menu.addAction(f"Unequip {item_obj.name}")
        info_action = context_menu.addAction("Item Information")
        drop_action = context_menu.addAction(f"Drop {item_obj.name}")
        
        action = context_menu.exec_(global_pos)

        if action == unequip_action:
            self.item_unequip_from_slot_requested.emit(slot)
        elif action == info_action:
            self.item_examine_requested.emit(item_id)
        elif action == drop_action:
            self.item_drop_from_slot_requested.emit(slot, item_id)            
    class EquippedItemLabel(QLabel):
        context_menu_requested_for_slot = Signal(QPoint, EquipmentSlot, str) # Global pos, slot, item_id

        def __init__(self, text: str, slot: EquipmentSlot, item_id: Optional[str] = None, parent: Optional[QWidget] = None):
            super().__init__(text, parent)
            self.slot = slot
            self.item_id = item_id
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu_slot)

        def set_item_data(self, text: str, item_id: Optional[str]):
            self.setText(text)
            self.item_id = item_id
            if item_id:
                # --- FIX: Use the parent's link_cursor if available ---
                main_win = self.window()
                if hasattr(main_win, 'link_cursor'):
                    self.setCursor(main_win.link_cursor)
                else:
                    self.setCursor(Qt.PointingHandCursor)
                # --- END FIX ---
                self.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: 13px;")
            else:
                self.unsetCursor() # Revert to the parent's cursor
                self.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic; font-size: 13px;")

        def show_context_menu_slot(self, position: QPoint):
            if self.item_id: # Only show menu if an item is equipped
                self.context_menu_requested_for_slot.emit(self.mapToGlobal(position), self.slot, self.item_id)