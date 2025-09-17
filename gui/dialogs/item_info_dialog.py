#!/usr/bin/env python3
"""
Dialog for displaying detailed item information.
"""

import logging
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QTextBrowser, QPushButton, QSizePolicy, QScrollArea, QWidget, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from core.inventory.item import Item
from core.inventory.currency_manager import CurrencyManager 

logger = logging.getLogger("GUI")

class ItemInfoDialog(QDialog):
    """Dialog to display detailed information about an item."""

    def __init__(self, item: Optional[Item] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Item Information")
        self.setMinimumSize(400, 550) # Increased min height
        self.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                color: #E0E0E0;
                border: 1px solid #555555;
            }
            QLabel {
                color: #E0E0E0;
                background-color: transparent;
            }
            QTextBrowser {
                background-color: #252525;
                color: #CFCFCF;
                border: 1px solid #444444;
                border-radius: 3px;
                padding: 5px; /* Added padding */
            }
            QPushButton {
                background-color: #4A4A4A;
                color: #E0E0E0;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
            }
            QPushButton:pressed {
                background-color: #3A3A3A;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#scrollAreaWidgetContents { 
                background-color: transparent;
            }
            QGroupBox { /* Basic style for potential future group boxes */
                color: #E0E0E0;
                font-weight: bold;
                border: 1px solid #444444;
                border-radius: 3px;
                margin-top: 10px; /* Space above groupbox */
                padding-top: 15px; /* Space for title */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        self._setup_ui()
        if self.item:
            self.populate_data()

    def _setup_ui(self):
        """Set up the UI elements for the dialog."""
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.scroll_content_widget = QWidget(scroll_area)
        self.scroll_content_widget.setObjectName("scrollAreaWidgetContents")
        scroll_area.setWidget(self.scroll_content_widget)

        self.content_layout = QVBoxLayout(self.scroll_content_widget)
        self.content_layout.setSpacing(12) # Increased spacing

        # Name and Rarity
        name_rarity_layout = QHBoxLayout()
        self.name_label = QLabel("Item Name")
        self.name_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        name_rarity_layout.addWidget(self.name_label)
        name_rarity_layout.addStretch()
        self.rarity_label = QLabel("(Rarity)")
        self.rarity_label.setStyleSheet("font-size: 10pt; font-style: italic;")
        name_rarity_layout.addWidget(self.rarity_label)
        self.content_layout.addLayout(name_rarity_layout)

        # Type
        self.type_label = QLabel("Type: ?")
        self.type_label.setStyleSheet("font-size: 11pt;")
        self.content_layout.addWidget(self.type_label)
        
        self.content_layout.addWidget(self._create_separator())

        # Description
        self.description_title_label = QLabel("<b>Description:</b>")
        self.content_layout.addWidget(self.description_title_label)
        self.description_browser = QTextBrowser()
        self.description_browser.setPlaceholderText("?")
        self.description_browser.setOpenExternalLinks(True)
        self.description_browser.setMinimumHeight(60) 
        self.description_browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.content_layout.addWidget(self.description_browser)

        # Grid for Weight, Value, Durability, Equip Slots
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(8) # Adjusted spacing
        self.grid_layout.setColumnStretch(1, 1) # Allow value column to stretch
        self.content_layout.addLayout(self.grid_layout)

        # Metrics rows
        self.weight_label = self._add_grid_row("Weight:", "?", 0)
        self.value_label = self._add_grid_row("Value:", "?", 1)
        self.quantity_label = self._add_grid_row("Quantity:", "?", 2)
        self.stack_limit_label = self._add_grid_row("Stack limit:", "?", 3)
        self.durability_label = self._add_grid_row("Durability:", "?", 4)
        self.equip_slots_label = self._add_grid_row("Equip Slots:", "?", 5)
        self.equip_slots_label.setWordWrap(True)
        
        self.content_layout.addWidget(self._create_separator())

        # Stats & Effects
        self.stats_effects_title_label = QLabel("<b>Stats & Effects:</b>")
        self.content_layout.addWidget(self.stats_effects_title_label)
        self.stats_browser = QTextBrowser()
        self.stats_browser.setPlaceholderText("?")
        self.stats_browser.setMinimumHeight(80)
        self.stats_browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.content_layout.addWidget(self.stats_browser)
        
        # Custom Properties
        self.custom_props_title_label = QLabel("<b>Properties:</b>") # Changed title slightly for clarity
        self.content_layout.addWidget(self.custom_props_title_label)
        self.custom_props_browser = QTextBrowser()
        self.custom_props_browser.setPlaceholderText("?")
        self.custom_props_browser.setMinimumHeight(40)
        self.custom_props_browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.content_layout.addWidget(self.custom_props_browser)

        # Tags
        self.tags_label = QLabel("Tags: ?")
        self.tags_label.setWordWrap(True)
        self.content_layout.addWidget(self.tags_label)

        self.content_layout.addStretch()
        self.main_layout.addWidget(scroll_area)

        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        self.main_layout.addWidget(self.close_button, 0, Qt.AlignRight)

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #444444;") # Make it slightly visible
        return sep

    def _add_grid_row(self, label_text: str, value_text: str, row: int) -> QLabel:
        """Helper to add a row to the grid layout."""
        label = QLabel(label_text)
        label.setStyleSheet("font-weight: bold;")
        label.setAlignment(Qt.AlignRight | Qt.AlignTop) # Align right and top for multi-line values
        value = QLabel(value_text)
        value.setWordWrap(True) # Allow values to wrap
        self.grid_layout.addWidget(label, row, 0)
        self.grid_layout.addWidget(value, row, 1)
        return value

    def populate_data(self):
        """Populate the dialog with item data."""
        if not self.item:
            self.name_label.setText("No Item Selected")
            self.description_browser.setHtml("<i>No item selected.</i>")
            self.stats_browser.setHtml("<i>No item selected.</i>")
            self.custom_props_browser.setHtml("<i>No item selected.</i>")
            self.description_title_label.setVisible(True)
            self.stats_effects_title_label.setVisible(True)
            self.custom_props_title_label.setVisible(True)
            return

        item = self.item
        known = item.known_properties

        # Name and Rarity
        title_name = item.name if "name" in known else "Unknown Item"
        if getattr(item, 'quantity', 1) > 1 and getattr(item, 'is_stackable', False):
            title_name = f"{title_name} × {int(item.quantity)}"
        self.name_label.setText(title_name)
        
        rarity_str = "?"
        rarity_color = "#CFCFCF" 
        if "rarity" in known and item.rarity:
            rarity_str = item.rarity.value.capitalize()
            rarity_color = item.rarity.color
        self.rarity_label.setText(f"({rarity_str})")
        self.rarity_label.setStyleSheet(f"font-size: 10pt; font-style: italic; color: {rarity_color};")

        # Type
        self.type_label.setText(f"Type: {item.item_type.value.capitalize() if 'item_type' in known and item.item_type else '?'}")

        # Description
        self.description_title_label.setVisible(True)
        if "description" in known:
            self.description_browser.setHtml(item.description if item.description else "<i>No description available.</i>")
        else:
            self.description_browser.setHtml("<i>Description currently unknown.</i>")


        # Weight, Value, Quantity/Stack
        if "weight" in known and item.weight is not None:
            if getattr(item, 'quantity', 1) > 1 and getattr(item, 'is_stackable', False):
                total_weight = (item.weight or 0.0) * int(item.quantity)
                self.weight_label.setText(f"{item.weight:.2f} kg (Total: {total_weight:.2f} kg)")
            else:
                self.weight_label.setText(f"{item.weight:.2f} kg")
        else:
            self.weight_label.setText("?")
        
        value_str = "?"
        if "value" in known and isinstance(item.value, int):
            cm_unit = CurrencyManager(); cm_unit.set_currency(int(item.value))
            value_str = cm_unit.get_formatted_currency()
            if getattr(item, 'quantity', 1) > 1 and getattr(item, 'is_stackable', False):
                total_val = int(item.value) * int(item.quantity)
                cm_total = CurrencyManager(); cm_total.set_currency(total_val)
                value_str = f"{value_str} (Total: {cm_total.get_formatted_currency()})"
        self.value_label.setText(value_str)

        # Quantity and Stack limit
        qty_str = str(getattr(item, 'quantity', 1)) if "quantity" in known else "?"
        self.quantity_label.setText(qty_str)
        if getattr(item, 'is_stackable', False):
            self.stack_limit_label.setText(str(getattr(item, 'stack_limit', ''))) 
        else:
            self.stack_limit_label.setText("N/A")

        durability_str = "?"
        if "durability" in known and item.durability is not None: # Check if durability itself is known
            # current_durability is also a knowable property. If item.durability is known, current_durability might also be.
            current_dur_known = "current_durability" in known
            current_dur = item.current_durability if current_dur_known and item.current_durability is not None else item.durability if item.durability is not None else "?"
            max_dur = item.durability if item.durability is not None else "?"
            if current_dur != "?" and max_dur != "?":
                durability_str = f"{current_dur} / {max_dur}"
            elif max_dur != "?": # Only max is known
                 durability_str = f"? / {max_dur}"
            else: # Neither known or only current is known (less likely)
                 durability_str = "?"

        elif "durability" not in known and item.durability is not None: # Durability exists but is not known
            durability_str = "? / ?"
        elif item.durability is None: # Item has no durability system
            durability_str = "N/A"
        self.durability_label.setText(durability_str)

        equip_slots_str = "?"
        if "is_equippable" in known: 
            if item.is_equippable:
                if "equip_slots" in known and item.equip_slots:
                    equip_slots_str = ", ".join(slot.value.replace('_', ' ').title() for slot in item.equip_slots)
                elif "equip_slots" in known: 
                     equip_slots_str = "None (Special)"
                else: 
                    equip_slots_str = "?" 
            else:
                equip_slots_str = "Not Equippable"
        self.equip_slots_label.setText(equip_slots_str)

        # Stats & Effects
        self.stats_effects_title_label.setVisible(True)
        stats_html_parts = []
        # Only try to display stats if the "stats" category itself is known
        if "stats" in known and item.stats: 
            known_item_stats_found = False
            temp_stats_list = []
            for stat_obj in item.stats:
                if f"stat_{stat_obj.name}" in known: 
                    known_item_stats_found = True
                    val_str = f"{stat_obj.value:+.1f}" if isinstance(stat_obj.value, (int, float)) and stat_obj.value != 0 else str(stat_obj.value)
                    if stat_obj.is_percentage and isinstance(stat_obj.value, (int,float)): val_str += "%"
                    display_name = stat_obj.display_name if stat_obj.display_name else stat_obj.name.replace('_', ' ').title()
                    temp_stats_list.append(f"<li><b>{display_name}:</b> {val_str}</li>")
            if known_item_stats_found:
                stats_html_parts.append("<u>Stats:</u><ul>" + "".join(temp_stats_list) + "</ul>")
        
        # Only try to display dice_roll_effects if the "dice_roll_effects" category is known
        if item.dice_roll_effects and "dice_roll_effects" in known:
            known_dice_effects_found = False
            temp_dice_effects_list = []
            for effect in item.dice_roll_effects:
                # Assume individual dice effects become known if the "dice_roll_effects" category is known
                known_dice_effects_found = True
                desc = f"{effect.dice_notation} {effect.effect_type.replace('_', ' ').title()}"
                if effect.description:
                    desc += f" <small><i>({effect.description})</i></small>"
                temp_dice_effects_list.append(f"<li>{desc}</li>")
            if known_dice_effects_found:
                 stats_html_parts.append("<u>Effects:</u><ul>" + "".join(temp_dice_effects_list) + "</ul>")
            
        if stats_html_parts:
            final_stats_html = "<br>".join(stats_html_parts)
            self.stats_browser.setHtml(final_stats_html)
        else: # No known stats or effects
            self.stats_browser.setHtml("<i>Unknown stats or effects.</i>")


        # Custom Properties
        self.custom_props_title_label.setVisible(True)
        custom_props_html = ""
        if "custom_properties" in known and item.custom_properties: 
            known_custom_prop_details = []
            for key, value in item.custom_properties.items():
                if f"custom_{key}" in known: 
                    known_custom_prop_details.append(f"<li><b>{key.replace('_', ' ').title()}:</b> {value}</li>")
            if known_custom_prop_details:
                custom_props_html = "<ul>" + "".join(known_custom_prop_details) + "</ul>"
        
        self.custom_props_browser.setHtml(custom_props_html if custom_props_html else "<i>No special properties known.</i>")


        # Tags
        self.tags_label.setVisible(True) # Always show the Tags label
        self.tags_label.setText(f"Tags: {', '.join(item.tags) if 'tags' in known and item.tags else '?'}")