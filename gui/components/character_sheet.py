#!/usr/bin/env python3
"""
Character sheet widget for the RPG game GUI.
This module provides a widget for displaying the player character's information.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGridLayout, QTextEdit,
    QScrollArea, QFrame, QGroupBox, QProgressBar, QMenu, QToolTip
)
from PySide6.QtCore import Qt, Slot, Signal, QPoint
from PySide6.QtGui import  QPixmap, QCursor, QMouseEvent

from core.base.state import get_state_manager
from core.interaction.enums import InteractionMode
from core.inventory.item import Item
from core.inventory.item_enums import EquipmentSlot
from core.inventory.item_manager import get_inventory_manager
from core.stats.modifier import StatModifier
from core.stats.stats_base import StatType, DerivedStatType
from core.stats.stats_manager import get_stats_manager
from core.utils.logging_config import get_logger
from gui.components.ap_display_widget import APDisplayWidget
from gui.styles.stylesheet_factory import create_groupbox_style
from gui.styles.theme_manager import get_theme_manager

logger = get_logger("GUI")

class StatLabel(QLabel):
    """A label for displaying a stat that shows details on right-click."""
    
    def __init__(self, text: str, stat_name: str, parent=None):
        super().__init__(text, parent)
        self.stat_name_key = stat_name 
        self.description = ""
        self.base_value = 0
        self.current_value = 0
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Get theme manager for tooltip styling
        self.theme_manager = get_theme_manager()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:
            self.show_tooltip(event.globalPos())
        super().mousePressEvent(event)
    
    def _fetch_modifiers(self) -> List[Dict[str, Any]]:
        try:
            stats_manager = get_stats_manager()
            if not stats_manager:
                return []

            stat_type_enum = None
            try:
                stat_type_enum = StatType[self.stat_name_key]
            except KeyError:
                try:
                    stat_type_enum = DerivedStatType[self.stat_name_key]
                except KeyError:
                    return []

            if hasattr(stats_manager.modifier_manager, 'get_modifiers_for_stat'):
                mods = stats_manager.modifier_manager.get_modifiers_for_stat(stat_type_enum)
                if mods and isinstance(mods[0], StatModifier):
                     return [mod.to_dict() for mod in mods]
                elif mods and isinstance(mods, list):
                     return mods
                else:
                     return []
            return []

        except Exception as e:
            return []

    def show_tooltip(self, position: QPoint) -> None:
        modifiers = self._fetch_modifiers()
        display_name = self.stat_name_key
        if hasattr(self, 'display_name_override'):
            display_name = self.display_name_override

        # Get colors from theme
        palette = self.theme_manager.get_current_palette()
        colors = palette['colors']

        tooltip_text = f"<div style='background-color: {colors['bg_medium']}; padding: 10px; border: 2px solid {colors['border_dark']}; border-radius: 4px;'>"
        tooltip_text += f"<b style='color: {colors['text_primary']};'>{display_name}</b><hr style='border: 1px solid {colors['border_dark']};'>"

        if self.description:
            tooltip_text += f"<i style='color: {colors['text_secondary']};'>{self.description}</i><br><br>"

        try:
            delta_val = (self.current_value or 0) - (self.base_value or 0)
        except Exception:
            delta_val = 0
        delta_sign = "+" if delta_val > 0 else ""
        delta_color = colors['accent_positive'] if delta_val > 0 else (colors['accent_negative'] if delta_val < 0 else colors['text_secondary'])
        
        tooltip_text += f"<p style='color: {colors['text_secondary']}; margin: 2px 0;'>"
        tooltip_text += f"Base: {self.base_value}<br>"
        tooltip_text += f"Total: <b style='color: {colors['text_bright']};'>{self.current_value}</b>"
        if delta_val != 0:
            tooltip_text += f" <span style='color:{delta_color}'>({delta_sign}{int(delta_val)})</span>"
        tooltip_text += "</p>"

        if modifiers:
            tooltip_text += f"<br><b style='color: {colors['text_primary']};'>Modifiers:</b><br><ul style='margin: 0; padding-left: 15px; color: {colors['text_secondary']};'>"
            for mod in modifiers:
                mod_source = mod.get('source_name') or mod.get('source') or 'Unknown'
                mod_value = mod.get('value', 0)
                mod_is_percentage = mod.get('is_percentage', False)
                mod_duration = mod.get('duration', None)

                sign = "+" if isinstance(mod_value, (int, float)) and mod_value > 0 else ""
                color = colors['accent_positive'] if (isinstance(mod_value, (int, float)) and mod_value > 0) else (colors['accent_negative'] if (isinstance(mod_value, (int, float)) and mod_value < 0) else colors['text_secondary'])
                val_text = f"<span style='color:{color}'>{sign}{mod_value}{'%' if mod_is_percentage else ''}</span>"
                dur_text = f" ({mod_duration} turns)" if (mod_duration is not None) else ""
                tooltip_text += f"<li>{mod_source}: {val_text}{dur_text}</li>"
            tooltip_text += "</ul>"
        else:
            tooltip_text += f"<br><i style='color: {colors['text_disabled']};'>No active modifiers.</i>"
        
        tooltip_text += "</div>"

        QToolTip.showText(position, tooltip_text)

    def show_context_menu(self, position: QPoint) -> None:
        display_name = self.stat_name_key
        if hasattr(self, 'display_name_override'):
            display_name = self.display_name_override

        palette = self.theme_manager.get_current_palette()
        from gui.styles.stylesheet_factory import create_context_menu_style
        
        menu = QMenu(self)
        menu.setStyleSheet(create_context_menu_style(palette))
        menu.addAction(f"{display_name} Details", lambda: self.show_tooltip(QCursor.pos()))
        menu.exec_(self.mapToGlobal(position))

    def update_stat_data(self, stat_data: Dict[str, Any]) -> None:
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
            
            # --- THEME MANAGEMENT ---
            self.theme_manager = get_theme_manager()
            self.palette = self.theme_manager.get_current_palette()
            self.theme_manager.theme_changed.connect(self._update_theme)
            # --- END THEME MANAGEMENT ---

            self.setWidgetResizable(True)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            self.character_widget = QWidget()
            self.setWidget(self.character_widget)
            self.state_manager = get_state_manager()
            self._signal_connected = False

            self._pending_player_bar_updates: Dict[str, Dict[str, Any]] = {} 
            self._pending_bar_updates: Dict[str, Dict[str, Any]] = {} # For internal anim

            self._setup_ui() 
            self._clear_stat_displays()
            
            # Apply initial theme
            self._update_theme()

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        fonts = self.palette['fonts']
        pb_styles = self.palette['progress_bars']
        
        self.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        # GroupBoxes
        group_style = create_groupbox_style(self.palette)
        for group in self.findChildren(QGroupBox):
            group.setStyleSheet(group_style)
            
        # Labels
        self.name_label.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {colors['text_primary']};")
        self.race_class_label.setStyleSheet(f"font-size: 12pt; color: {colors['text_primary']};")
        self.level_exp_label.setStyleSheet(f"font-size: 11pt; color: {colors['text_secondary']};")
        
        # Stat Labels (Keys/Titles)
        for label in self.findChildren(QLabel):
            if label.alignment() & Qt.AlignRight: # Heuristic for stat name labels
                label.setStyleSheet(f"color: {colors['text_primary']}; font-weight: 600; padding-right: 5px; font-size: 13px;")
        
        # Stat Values (StatLabels)
        for label in self.primary_stat_labels.values():
            label.setStyleSheet(f"color: {colors['text_bright']}; min-width: 50px; padding-left: 5px; font-size: 13px;")
        for label in self.derived_stat_labels.values():
            label.setStyleSheet(f"color: {colors['text_bright']}; min-width: 50px; padding-left: 5px; font-size: 13px;")
            
        # Equipment Labels
        for label in self.equip_labels.values():
            if label.item_id:
                label.setStyleSheet(f"color: {colors['text_bright']}; font-size: 13px;")
            else:
                label.setStyleSheet(f"color: {colors['text_secondary']}; font-style: italic; font-size: 13px;")

        # Text Edits (Status/Turn Order)
        text_edit_style = f"""
            QTextEdit {{
                background-color: {colors['bg_dark']};
                border: 1px solid {colors['border_dark']};
                color: {colors['text_bright']};
                padding: 5px;
                border-radius: 3px;
            }}
        """
        self.status_effects_list.setStyleSheet(text_edit_style)
        self.turn_order_list.setStyleSheet(text_edit_style)
        
        # Progress Bars (EXP)
        self.exp_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {pb_styles['bg']};
                border: 1px solid {colors['border_dark']};
                border-radius: 3px;
                text-align: center;
                color: {pb_styles['text']};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {colors['res_exp']};
                border-radius: 2px;
            }}
        """)
        
        # Resource Bars (HP, Mana, Stamina)
        for key, (label, bar) in self.resource_bars.items():
            label.setStyleSheet(f"color: {colors['text_primary']}; font-weight: 600; font-size: 13px;")
            
            chunk_color = "#888888"
            if "health" in key: chunk_color = pb_styles['hp_normal']
            elif "mana" in key: chunk_color = pb_styles['mana']
            elif "stamina" in key: chunk_color = pb_styles['stamina']
            
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {pb_styles['bg']};
                    border: 1px solid {colors['border_dark']};
                    border-radius: 3px;
                    text-align: center;
                    color: {pb_styles['text']};
                    height: 22px;
                }}
                QProgressBar::chunk {{
                    background-color: {chunk_color};
                    border-radius: 2px;
                }}
            """)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self.character_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(15)
        
        self.primary_stat_labels = {}
        self.derived_stat_labels = {}
        
        self._create_header()
        self._create_stats_section()
        self._create_skills_section()
        self._create_equipment_section()

    def _create_header(self):
        header_group = QGroupBox("Character")
        header_layout = QHBoxLayout(header_group)
        
        portrait_frame = QFrame()
        portrait_frame.setFrameShape(QFrame.StyledPanel)
        portrait_frame.setFixedSize(100, 100)
        
        self.portrait_label = QLabel("Portrait")
        self.portrait_label.setAlignment(Qt.AlignCenter)
        self.portrait_label.setScaledContents(True)
        
        portrait_layout = QVBoxLayout(portrait_frame)
        portrait_layout.addWidget(self.portrait_label)
        
        info_layout = QVBoxLayout()
        self.name_label = QLabel("Name: Unknown")
        self.race_class_label = QLabel("Race: Unknown | Class: Unknown")
        self.level_exp_label = QLabel("Level: 1 | Experience: 0/100")
        
        self.exp_bar = QProgressBar()
        self.exp_bar.setRange(0, 100)
        self.exp_bar.setValue(0)
        self.exp_bar.setTextVisible(True)
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.race_class_label)
        info_layout.addWidget(self.level_exp_label)
        info_layout.addWidget(self.exp_bar)
        
        header_layout.addWidget(portrait_frame)
        header_layout.addLayout(info_layout, 1)
        
        self.main_layout.addWidget(header_group)
    
    def _create_stats_section(self):
        # Primary Stats
        primary_stats_group = QGroupBox("Primary Stats")
        primary_stats_layout = QGridLayout(primary_stats_group)
        primary_stats_layout.setColumnStretch(0, 1); primary_stats_layout.setColumnStretch(2, 1)
        primary_stats_layout.setColumnMinimumWidth(1, 50); primary_stats_layout.setColumnMinimumWidth(3, 50)
        primary_stats_layout.setHorizontalSpacing(10)

        self._add_stat(primary_stats_layout, 0, 0, StatType.STRENGTH.name, "Strength", "")
        self._add_stat(primary_stats_layout, 0, 1, StatType.DEXTERITY.name, "Dexterity", "")
        self._add_stat(primary_stats_layout, 1, 0, StatType.CONSTITUTION.name, "Constitution", "")
        self._add_stat(primary_stats_layout, 1, 1, StatType.INTELLIGENCE.name, "Intelligence", "")
        self._add_stat(primary_stats_layout, 2, 0, StatType.WISDOM.name, "Wisdom", "")
        self._add_stat(primary_stats_layout, 2, 1, StatType.CHARISMA.name, "Charisma", "")
        self._add_stat(primary_stats_layout, 3, 0, StatType.WILLPOWER.name, "Willpower", "")
        self._add_stat(primary_stats_layout, 3, 1, StatType.INSIGHT.name, "Insight", "")

        # Resources
        resources_group = QGroupBox("Resources")
        resources_layout = QVBoxLayout(resources_group)
        self.resource_bars = {}
        self._add_resource_bar(resources_layout, "Health", 100, 100)
        self._add_resource_bar(resources_layout, "Mana", 50, 50)
        self._add_resource_bar(resources_layout, "Stamina", 100, 100)

        # Combat Info
        combat_info_group = QGroupBox("Combat Info")
        combat_info_layout = QVBoxLayout(combat_info_group)

        self.ap_display = APDisplayWidget(self)
        combat_info_layout.addWidget(self.ap_display)

        status_label = QLabel("Status Effects:")
        combat_info_layout.addWidget(status_label)

        self.status_effects_list = QTextEdit()
        self.status_effects_list.setReadOnly(True)
        self.status_effects_list.setMaximumHeight(60)
        combat_info_layout.addWidget(self.status_effects_list)
        
        turn_label = QLabel("Turn Order:")
        combat_info_layout.addWidget(turn_label)

        self.turn_order_list = QTextEdit()
        self.turn_order_list.setReadOnly(True)
        self.turn_order_list.setMaximumHeight(80)
        combat_info_layout.addWidget(self.turn_order_list)

        initiative_layout = QHBoxLayout()
        initiative_title_label = QLabel("Initiative:")
        self.initiative_value = QLabel("0")
        self.initiative_value.setAlignment(Qt.AlignRight)
        initiative_layout.addWidget(initiative_title_label)
        initiative_layout.addWidget(self.initiative_value)
        combat_info_layout.addLayout(initiative_layout)

        # Derived Stats
        derived_stats_group = QGroupBox("Derived Stats")
        derived_stats_layout = QGridLayout(derived_stats_group)
        derived_stats_layout.setColumnStretch(0, 1); derived_stats_layout.setColumnStretch(2, 1)
        derived_stats_layout.setColumnMinimumWidth(1, 50); derived_stats_layout.setColumnMinimumWidth(3, 50)
        derived_stats_layout.setHorizontalSpacing(10)

        self._add_stat(derived_stats_layout, 0, 0, DerivedStatType.MELEE_ATTACK.name, "Melee Attack", "")
        self._add_stat(derived_stats_layout, 0, 1, DerivedStatType.RANGED_ATTACK.name, "Ranged Attack", "")
        self._add_stat(derived_stats_layout, 1, 0, DerivedStatType.MAGIC_ATTACK.name, "Magic Attack", "")
        self._add_stat(derived_stats_layout, 1, 1, DerivedStatType.DEFENSE.name, "Defense", "")
        self._add_stat(derived_stats_layout, 2, 0, DerivedStatType.MAGIC_DEFENSE.name, "Magic Defense", "")
        self._add_stat(derived_stats_layout, 3, 0, DerivedStatType.CARRY_CAPACITY.name, "Carry Capacity", "")
        self._add_stat(derived_stats_layout, 3, 1, DerivedStatType.MOVEMENT.name, "Movement", "")
        self._add_stat(derived_stats_layout, 2, 1, DerivedStatType.DAMAGE_REDUCTION.name, "Damage Reduction", "")

        self.main_layout.addWidget(resources_group)
        self.main_layout.addWidget(combat_info_group)
        self.main_layout.addWidget(primary_stats_group)
        self.main_layout.addWidget(derived_stats_group)
        
    def _add_stat(self, layout, row, col, stat_id, stat_name, value):
        label = QLabel(f"{stat_name}:")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label = StatLabel(value, stat_id)
        value_label.setAlignment(Qt.AlignLeft)
        if stat_id in [s.name for s in StatType]:
            self.primary_stat_labels[stat_id] = value_label
        else:
            self.derived_stat_labels[stat_id] = value_label
        layout.addWidget(label, row, col * 2)
        layout.addWidget(value_label, row, col * 2 + 1)

    def _add_resource_bar(self, layout, name, value, max_value):
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)
        label = QLabel(f"{name}: {value}/{max_value}")
        progress_bar = QProgressBar()
        progress_bar.setRange(0, max_value)
        progress_bar.setValue(value)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat(f"%v/%m")
        container_layout.addWidget(label)
        container_layout.addWidget(progress_bar)
        self.resource_bars[name.lower()] = (label, progress_bar)
        layout.addWidget(container)

    def _create_skills_section(self):
        skills_group = QGroupBox("Skills")
        self.skills_layout = QGridLayout(skills_group)
        self.skills_layout.setColumnStretch(0, 1); self.skills_layout.setColumnStretch(2, 1)
        self.skills_layout.setColumnMinimumWidth(1, 50); self.skills_layout.setColumnMinimumWidth(3, 50)
        self.skills_layout.setHorizontalSpacing(10)
        
        self.skill_labels = {}
        self.main_layout.addWidget(skills_group)

    def _update_skills(self, skills_data: Dict[str, Any]):
        colors = self.palette['colors']
        
        # Sort skills by name
        sorted_skills = sorted(skills_data.items(), key=lambda x: x[1].get('name', x[0]))
        
        # Rebuild layout if number of skills changed (simplest approach to handle init)
        if len(sorted_skills) != len(self.skill_labels):
            # Clear existing
            for i in reversed(range(self.skills_layout.count())): 
                widget = self.skills_layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
            self.skill_labels = {}
            
            row = 0
            col = 0
            for skill_key, skill_data in sorted_skills:
                name = skill_data.get('name', skill_key)
                label = QLabel(f"{name}:")
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                label.setStyleSheet(f"color: {colors['text_primary']}; font-weight: 600; padding-right: 5px; font-size: 13px;")
                
                value_label = StatLabel("0", skill_key)
                value_label.setAlignment(Qt.AlignLeft)
                value_label.setStyleSheet(f"color: {colors['text_bright']}; min-width: 50px; padding-left: 5px; font-size: 13px;")
                
                self.skill_labels[skill_key] = value_label
                self.skills_layout.addWidget(label, row, col * 2)
                self.skills_layout.addWidget(value_label, row, col * 2 + 1)
                
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

        # Update values
        for skill_key, skill_data in skills_data.items():
            if skill_key in self.skill_labels:
                try:
                    value = int(skill_data.get('value', 0))
                    new_text = f"{value}"
                    if self.skill_labels[skill_key].text() != new_text:
                        self.skill_labels[skill_key].setText(new_text)
                    self.skill_labels[skill_key].update_stat_data(skill_data)
                except Exception: pass

    def _create_equipment_section(self):
        equipment_group = QGroupBox("Equipment")
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
            if not self._signal_connected:
                self._connect_stats_signal()

            try:
                if character is None:
                    if self.state_manager and self.state_manager.current_state:
                        character = self.state_manager.current_state.player
                    else:
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

                    if 'primary' in all_stats: self._update_primary_stats(all_stats["primary"])
                    for category in ["combat", "social", "other"]: 
                        if category in all_stats: self._update_derived_stats(all_stats[category], category)
                    if "resources" in all_stats:
                        self._update_resources(all_stats["resources"], all_player_stats=all_stats)
                    if "skills" in all_stats:
                        self._update_skills(all_stats["skills"])
                    self._update_combat_status(character)
                else:
                    self._clear_stat_displays()

                inventory_manager = get_inventory_manager()
                if inventory_manager:
                    for slot_key_str, label_widget in self.equip_labels.items():
                        label_widget.set_item_data("None", None) 
                    
                    if hasattr(inventory_manager, 'equipment'):
                        two_handed_weapon_equipped: Optional[Item] = None
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
                                        self.equip_labels[EquipmentSlot.OFF_HAND.value].set_item_data(f"- (2H: {item_obj_from_inv_mgr.name}) -", None) 
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

                if hasattr(character, 'character_image') and character.character_image:
                    try:
                        pixmap = QPixmap(character.character_image)
                        if not pixmap.isNull():
                            scaled_pixmap = pixmap.scaled(self.portrait_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            self.portrait_label.setPixmap(scaled_pixmap)
                            self.portrait_label.setStyleSheet("")
                        else:
                            self.portrait_label.setText("Portrait")
                    except Exception:
                        self.portrait_label.setText("Portrait")
                else:
                    self.portrait_label.setText("Portrait")

            except Exception as e:
                logger.error(f"Error updating character sheet: {e}", exc_info=True)

    def _update_combat_status(self, character):
        if not character: return
        from core.base.state import get_state_manager 
        state_manager = get_state_manager()
        if not state_manager or not state_manager.current_state:
            self.status_effects_list.clear()
            self.turn_order_list.setText("Turn Order: N/A") 
            self.initiative_value.setText("0")
            return
            
        game_state = state_manager.current_state
        combat_manager = getattr(game_state, 'combat_manager', None)
        
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
                    if isinstance(duration_data, int): duration = duration_data
                    if duration is not None and duration > 0 : status_text += f"{effect_name} ({duration} turns)\n"
                    elif duration is None: status_text += f"{effect_name}\n"
            elif isinstance(effects_data, (list, set)):
                for effect_name in effects_data: status_text += f"{effect_name}\n"
        
        self.status_effects_list.setText(status_text.strip())
        
        if not combat_manager:
            self.turn_order_list.setText("Turn Order: N/A (Not in Combat)")
            self.initiative_value.setText("0")
        elif not hasattr(self, '_last_turn_order_event_data') or not self._last_turn_order_event_data:
            turn_text = ""
            if hasattr(combat_manager, 'turn_order') and combat_manager.turn_order: 
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
        if self._signal_connected: return
        try:
            if self.state_manager and self.state_manager.stats_manager:
                stats_manager = self.state_manager.stats_manager
                if hasattr(stats_manager, 'stats_changed'):
                    try: stats_manager.stats_changed.disconnect(self._update_from_stats)
                    except (TypeError, RuntimeError): pass
                    stats_manager.stats_changed.connect(self._update_from_stats)
                    self._signal_connected = True
        except Exception as e:
            logger.error(f"Failed to connect to stats_changed signal: {e}")
    
    def _update_from_stats(self, stats_data):
        try:
            if isinstance(stats_data, dict):
                has_valid_stats = any(cat in stats_data for cat in ['primary', 'resources', 'combat', 'social', 'other', 'skills'])
                if not has_valid_stats: return

                if 'primary' in stats_data: self._update_primary_stats(stats_data['primary'])
                for category in ['combat', 'social', 'other']:
                    if category in stats_data: self._update_derived_stats(stats_data[category], category)
                if 'resources' in stats_data: self._update_resources(stats_data['resources'], all_player_stats=stats_data)
                if 'skills' in stats_data: self._update_skills(stats_data['skills'])
                
                if self.state_manager and self.state_manager.current_state and self.state_manager.current_state.player:
                    self._update_combat_status(self.state_manager.current_state.player)
            else:
                self.update_character() 
        except Exception as e:
            logger.error(f"Error updating from stats signal: {e}", exc_info=True)
            try: self.update_character()
            except Exception: pass
                
    def _update_primary_stats(self, primary_stats):
        colors = self.palette['colors']
        for stat_name, stat_data in primary_stats.items():
            if stat_name in self.primary_stat_labels:
                try:
                    value = int(stat_data.get('value', 0))
                    base = int(stat_data.get('base_value', value))
                    delta = value - base
                    delta_sign = "+" if delta > 0 else ""
                    delta_color = colors['accent_positive'] if delta > 0 else (colors['accent_negative'] if delta < 0 else colors['text_bright'])

                    new_text = f"{value}"
                    if delta != 0: new_text += f" <span style='color:{delta_color}'>({delta_sign}{delta})</span>"

                    if self.primary_stat_labels[stat_name].text() != new_text:
                        self.primary_stat_labels[stat_name].setText(new_text)
                    self.primary_stat_labels[stat_name].update_stat_data(stat_data)
                except Exception: pass
    
    def _update_derived_stats(self, derived_stats, category):
        colors = self.palette['colors']
        for stat_name, stat_data in derived_stats.items():
            if stat_name in self.derived_stat_labels:
                try:
                    value = int(stat_data.get('value', 0))
                    base = int(stat_data.get('base_value', value))
                    delta = value - base
                    delta_sign = "+" if delta > 0 else ""
                    delta_color = colors['accent_positive'] if delta > 0 else (colors['accent_negative'] if delta < 0 else colors['text_bright'])

                    new_text = f"{value}"
                    if delta != 0: new_text += f" <span style='color:{delta_color}'>({delta_sign}{delta})</span>"

                    if self.derived_stat_labels[stat_name].text() != new_text:
                        self.derived_stat_labels[stat_name].setText(new_text)
                    self.derived_stat_labels[stat_name].update_stat_data(stat_data)

                    if stat_name == "INITIATIVE" and self.initiative_value.text() != str(value):
                        self.initiative_value.setText(str(value))
                except Exception: pass
    
    def _update_resources(self, resources: Dict[str, Any], all_player_stats: Optional[Dict[str, Any]] = None):
        resource_key_map = { "HEALTH": "health", "MANA": "mana", "STAMINA": "stamina", "RESOLVE": "resolve" }
        max_resource_map = { "HEALTH": "MAX_HEALTH", "MANA": "MAX_MANA", "STAMINA": "MAX_STAMINA", "RESOLVE": "MAX_RESOLVE" }

        for stat_name_key, resource_data in resources.items():
            ui_key = resource_key_map.get(stat_name_key.upper()) 
            if ui_key and ui_key in self.resource_bars:
                label, bar = self.resource_bars[ui_key]
                game_mode = InteractionMode.NARRATIVE
                if self.state_manager and self.state_manager.current_state:
                    game_mode = self.state_manager.current_state.current_mode
                
                try:
                    current_value_from_model = int(resource_data.get('value', 0))
                    max_stat_name_key = max_resource_map.get(stat_name_key.upper())
                    max_value_from_model = bar.maximum() if bar.maximum() > 0 else 100 
                    
                    if all_player_stats and max_stat_name_key:
                        for category_key in ['resources', 'other', 'primary', 'combat', 'social']: 
                            if category_key in all_player_stats and max_stat_name_key in all_player_stats[category_key]:
                                max_value_from_model = int(all_player_stats[category_key][max_stat_name_key].get('value', max_value_from_model))
                                break
                    elif 'base_value' in resource_data and stat_name_key.upper().startswith("MAX_"): 
                         max_value_from_model = int(resource_data.get('base_value', max_value_from_model))
                    
                    max_value_from_model = max(1, max_value_from_model) 
                    display_name = resource_data.get("name", ui_key.capitalize()) 

                    if bar.maximum() != max_value_from_model:
                        bar.setRange(0, max_value_from_model)
                        if not (game_mode == InteractionMode.COMBAT and ui_key in self._pending_player_bar_updates):
                            current_display_val = bar.value() if game_mode == InteractionMode.COMBAT and ui_key in self._pending_player_bar_updates and self._pending_player_bar_updates[ui_key].get('phase1_preview_value') is not None else current_value_from_model
                            label.setText(f"{display_name}: {int(current_display_val)}/{max_value_from_model}")

                    if game_mode == InteractionMode.COMBAT:
                        if ui_key == "resolve": 
                             if bar.value() != current_value_from_model: bar.setValue(current_value_from_model)
                             label.setText(f"{display_name}: {current_value_from_model}/{max_value_from_model}")
                        else:
                             if bar.maximum() == max_value_from_model and ui_key not in self._pending_player_bar_updates:
                                  current_on_bar = bar.value() 
                                  if label.text() != f"{display_name}: {int(current_on_bar)}/{max_value_from_model}":
                                       label.setText(f"{display_name}: {int(current_on_bar)}/{max_value_from_model}")
                    else: 
                        if bar.value() != current_value_from_model: bar.setValue(current_value_from_model)
                        new_text_direct = f"{display_name}: {current_value_from_model}/{max_value_from_model}"
                        if label.text() != new_text_direct: label.setText(new_text_direct)
                        if ui_key in self._pending_player_bar_updates: self._pending_player_bar_updates.pop(ui_key, None)
                except Exception: pass

    def _clear_stat_displays(self):
        for label in self.primary_stat_labels.values():
            label.setText("0") 
            label.update_stat_data({}) 
        for label in self.derived_stat_labels.values():
            label.setText("0") 
            label.update_stat_data({}) 
        for label, bar in self.resource_bars.values():
            label.setText(f"{label.text().split(':')[0]}: 0/0") 
            bar.setRange(0, 100) 
            bar.setValue(0) 
            
        # Clear skills
        if hasattr(self, 'skill_labels'):
            for label in self.skill_labels.values():
                label.setText("0")
                label.update_stat_data({})

        # Clear equipment
        if hasattr(self, 'equip_labels'):
            for label in self.equip_labels.values():
                label.set_item_data("None", None)

        self.initiative_value.setText("0")
        self.status_effects_list.clear()
        self.turn_order_list.clear()
    
    def showEvent(self, event):
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

    def _finalize_bar_animation(self, bar_type_key: str):
        """Helper to finalize a bar after a QTimer, if used internally (less common now)."""
        # This method is less likely to be used if Orchestrator handles delays.
        # Kept for potential future internal animation needs.
        if bar_type_key in self._pending_bar_updates:
            data = self._pending_bar_updates.pop(bar_type_key)
            self.player_resource_bar_update_phase2(bar_type_key, {"final_new_value": data["final_value"], "max_value": data["max_value"]})

    def update_ap_display(self, current_ap: float, max_ap: float):
        """Updates the AP display widget with new values."""
        logger.info(f"[CharacterSheet] update_ap_display called with current_ap: {current_ap}, max_ap: {max_ap}")
        if hasattr(self, 'ap_display'):
            self.ap_display.update_ap(current_ap, max_ap)
        else:
            logger.error("[CharacterSheet] update_ap_display called, but self.ap_display widget does not exist!")

    @Slot(dict)
    def handle_turn_order_update(self, event_data: Dict[str, Any]):
        self._last_turn_order_event_data = event_data 
        turn_text = ""
        is_surprise = event_data.get("is_surprise", False)
        round_num = event_data.get("round_number", "")
        turn_order_display_list = event_data.get("turn_order_display_list", []) 
        if is_surprise: turn_text += f"[Surprise Round]\n"
        elif round_num: turn_text += f"Round {round_num}\n"
        if turn_order_display_list: turn_text += "\n".join(turn_order_display_list)
        else: turn_text += "Turn order not yet determined."
        self.turn_order_list.setText(turn_text.strip())

        player_id = getattr(self.state_manager.current_state.player, 'id', None) or getattr(self.state_manager.current_state.player, 'stats_manager_id', None)
        combat_manager = getattr(self.state_manager.current_state, 'combat_manager', None)
        if combat_manager and player_id:
            player_combat_entity = combat_manager.entities.get(player_id)
            if player_combat_entity and hasattr(player_combat_entity, 'initiative'):
                self.initiative_value.setText(str(int(player_combat_entity.initiative)))
            else: self.initiative_value.setText("N/A")
        elif combat_manager: self.initiative_value.setText("N/A (Player not in combat)")
        else: self.initiative_value.setText("0")

    @Slot(str, dict)
    def player_resource_bar_update_phase1(self, bar_type_key: str, update_data: Dict[str, Any]):
        event_to_internal_key_map = {"hp": "health", "mp": "mana", "stamina": "stamina", "resolve": "resolve"}
        internal_ui_key = event_to_internal_key_map.get(bar_type_key.lower(), bar_type_key.lower())
        if internal_ui_key not in self.resource_bars: return
        label, bar = self.resource_bars[internal_ui_key]
        new_value_preview = update_data.get("new_value_preview")
        max_value = update_data.get("max_value")
        if new_value_preview is None or max_value is None: return
        
        current_bar_visual_value = bar.value() 
        display_name_match = re.match(r"([^:]+):", label.text())
        display_name = display_name_match.group(1).strip() if display_name_match else internal_ui_key.capitalize()
        label.setText(f"{display_name}: {int(current_bar_visual_value)}/{int(max_value)} -> {int(new_value_preview)}/{int(max_value)}")
        if bar.maximum() != int(max_value): bar.setRange(0, int(max_value))

        self._pending_player_bar_updates[internal_ui_key] = {
            "final_value": new_value_preview, 
            "max_value": max_value,
            "phase1_preview_value": current_bar_visual_value 
        }
        try:
            from core.base.engine import get_game_engine
            from PySide6.QtCore import QTimer
            eng = get_game_engine()
            if eng and hasattr(eng, "_combat_orchestrator"):
                QTimer.singleShot(0, eng._combat_orchestrator._handle_visual_display_complete)
        except Exception: pass

    @Slot(str, dict)
    def player_resource_bar_update_phase2(self, bar_type_key: str, update_data: Dict[str, Any]):
        event_to_internal_key_map = {"hp": "health", "mp": "mana", "stamina": "stamina", "resolve": "resolve"}
        internal_ui_key = event_to_internal_key_map.get(bar_type_key.lower(), bar_type_key.lower())
        if internal_ui_key not in self.resource_bars:
            if internal_ui_key in self._pending_player_bar_updates: self._pending_player_bar_updates.pop(internal_ui_key, None)
            return
        
        pending_data = self._pending_player_bar_updates.pop(internal_ui_key, None)
        label, bar = self.resource_bars[internal_ui_key]
        final_value = update_data.get("final_new_value")
        max_val = update_data.get("max_value")

        if final_value is None:
            if pending_data and "final_value" in pending_data: final_value = pending_data["final_value"]
            else: final_value = bar.value() 
        if max_val is None:
            if pending_data and "max_value" in pending_data: max_val = pending_data["max_value"]
            else: max_val = bar.maximum()
        
        final_value = int(final_value)
        max_val = max(1, int(max_val))

        current_label_text = label.text()
        display_name_match = re.match(r"([^:]+):", current_label_text)
        display_name = display_name_match.group(1).strip() if display_name_match else internal_ui_key.capitalize()

        label.setText(f"{display_name}: {final_value}/{max_val}")
        if bar.maximum() != max_val: bar.setRange(0, max_val)
        bar.setValue(final_value)

        try:
            from core.base.engine import get_game_engine
            from PySide6.QtCore import QTimer
            eng = get_game_engine()
            if eng and hasattr(eng, "_combat_orchestrator"):
                QTimer.singleShot(0, eng._combat_orchestrator._handle_visual_display_complete)
        except Exception: pass

    @Slot(QPoint, EquipmentSlot, str)
    def _handle_equipped_item_context_menu(self, global_pos: QPoint, slot: EquipmentSlot, item_id: str):
        inventory_manager = get_inventory_manager()
        item_obj = inventory_manager.get_item(item_id)
        if not item_obj: return

        palette = self.theme_manager.get_current_palette()
        from gui.styles.stylesheet_factory import create_context_menu_style
        
        context_menu = QMenu(self)
        context_menu.setStyleSheet(create_context_menu_style(palette))

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
        context_menu_requested_for_slot = Signal(QPoint, EquipmentSlot, str) 

        def __init__(self, text: str, slot: EquipmentSlot, item_id: Optional[str] = None, parent: Optional[QWidget] = None):
            super().__init__(text, parent)
            self.slot = slot
            self.item_id = item_id
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu_slot)
            self.theme_manager = get_theme_manager()

        def set_item_data(self, text: str, item_id: Optional[str]):
            self.setText(text)
            self.item_id = item_id
            
            palette = self.theme_manager.get_current_palette()
            colors = palette['colors']
            
            if item_id:
                main_win = self.window()
                if hasattr(main_win, 'link_cursor'):
                    self.setCursor(main_win.link_cursor)
                else:
                    self.setCursor(Qt.PointingHandCursor)
                self.setStyleSheet(f"color: {colors['text_bright']}; font-size: 13px;")
            else:
                self.unsetCursor() 
                self.setStyleSheet(f"color: {colors['text_secondary']}; font-style: italic; font-size: 13px;")

        def show_context_menu_slot(self, position: QPoint):
            if self.item_id: 
                self.context_menu_requested_for_slot.emit(self.mapToGlobal(position), self.slot, self.item_id)