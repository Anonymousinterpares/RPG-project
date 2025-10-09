# gui/inventory/detail_panels.py
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
                             QPushButton, QListWidget, QListWidgetItem, QSizePolicy)
from PySide6.QtGui import QPixmap, QFont, QColor
from PySide6.QtCore import Qt, Signal

import os
from typing import List, Optional

from core.inventory.item import Item, ItemType, EquipmentSlot, ItemRarity


class ItemDetailPanel(QFrame):
    """Panel for displaying item details within the inventory tab"""
    equipItem = Signal(str)
    dropItem = Signal(str)
    closePanel = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item = None
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setStyleSheet("""
            ItemDetailPanel {
                background-color: #e9e1d3;
                border: 1px solid #a89f8c;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)
        
        # Header with icon and name
        self.header_layout = QHBoxLayout()
        
        # Item icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.header_layout.addWidget(self.icon_label)
        
        # Item name and basic info
        self.title_layout = QVBoxLayout()
        
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.title_layout.addWidget(self.name_label)
        
        self.type_label = QLabel()
        self.title_layout.addWidget(self.type_label)
        
        self.header_layout.addLayout(self.title_layout)
        self.header_layout.addStretch()
        
        self.layout.addLayout(self.header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(separator)
        
        # Description
        self.description_label = QLabel("Description:")
        self.description_label.setStyleSheet("font-weight: bold;")
        self.layout.addWidget(self.description_label)
        
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(80)
        self.description_text.setStyleSheet("background-color: rgba(255, 255, 255, 120);")
        self.layout.addWidget(self.description_text)
        
        # Stats
        self.stats_label = QLabel("Properties:")
        self.stats_label.setStyleSheet("font-weight: bold;")
        self.layout.addWidget(self.stats_label)
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(80)
        self.stats_text.setStyleSheet("background-color: rgba(255, 255, 255, 120);")
        self.layout.addWidget(self.stats_text)
        
        # Physical properties
        self.props_layout = QVBoxLayout()
        
        self.weight_label = QLabel()
        self.props_layout.addWidget(self.weight_label)
        
        self.value_label = QLabel()
        self.props_layout.addWidget(self.value_label)
        
        self.durability_label = QLabel()
        self.props_layout.addWidget(self.durability_label)
        
        self.layout.addLayout(self.props_layout)
        
        # Action buttons
        self.button_layout = QHBoxLayout()
        
        self.equip_btn = QPushButton("Equip")
        self.equip_btn.clicked.connect(self._on_equip_clicked)
        self.button_layout.addWidget(self.equip_btn)
        
        self.drop_btn = QPushButton("Drop")
        self.drop_btn.clicked.connect(self._on_drop_clicked)
        self.button_layout.addWidget(self.drop_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self._on_close_clicked)
        self.button_layout.addWidget(self.close_btn)
        
        self.layout.addLayout(self.button_layout)
        
        # Initial state
        self.setVisible(False)
    
    def set_item(self, item, currency_formatter=None):
        """Set the item to display in the detail panel"""
        try:
            self.current_item = item
            
            # Set item name and type - corrected variable names
            self.name_label.setText(f"<b>{item.name}</b>")
            self.type_label.setText(f"Type: {item.item_type.value.title()}")
            
            # Create rarity label if it doesn't exist
            if not hasattr(self, 'rarity_label'):
                self.rarity_label = QLabel()
                self.title_layout.addWidget(self.rarity_label)
            
            # Set rarity with color
            rarity_colors = {
                "common": "#FFFFFF",    # White
                "uncommon": "#1EFF00",  # Green
                "rare": "#0070DD",      # Blue
                "epic": "#A335EE",      # Purple
                "legendary": "#FF8000", # Orange
                "mythic": "#FF0000"     # Red
            }
            rarity_color = rarity_colors.get(item.rarity.value, "#FFFFFF")
            self.rarity_label.setText(f"Rarity: <span style='color:{rarity_color};'>{item.rarity.value.title()}</span>")
            
            # Set description - corrected variable name
            self.description_text.setText(item.description)
            
            # Set icon if available
            self.icon_label.clear()
            if item.icon and os.path.exists(item.icon):
                pixmap = QPixmap(item.icon)
                if not pixmap.isNull():
                    self.icon_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            # Set basic info
            self.value_label.setText(f"Value: {self._format_currency(item.value, currency_formatter)}")
            self.weight_label.setText(f"Weight: {item.weight} kg")
            
            # Create equip_slot_label if it doesn't exist
            if not hasattr(self, 'equip_slot_label'):
                self.equip_slot_label = QLabel()
                self.props_layout.addWidget(self.equip_slot_label)
            
            # Handle equipment info
            if item.is_equippable:
                slot_name = item.equipment_slot.value.replace('_', ' ').title()
                self.equip_slot_label.setText(f"Equip Slot: {slot_name}")
                self.equip_slot_label.setVisible(True)
                
                if hasattr(item, 'durability') and item.durability is not None and hasattr(item, 'max_durability') and item.max_durability is not None:
                    durability_pct = (item.durability / item.max_durability) * 100 if item.max_durability > 0 else 0
                    
                    # Set color based on durability
                    if durability_pct <= 25:
                        color = "red"
                    elif durability_pct <= 50:
                        color = "orange" 
                    else:
                        color = "green"
                        
                    self.durability_label.setText(
                        f"Durability: <span style='color:{color};'>{item.durability}/{item.max_durability}</span> ({durability_pct:.1f}%)"
                    )
                    self.durability_label.setVisible(True)
                else:
                    self.durability_label.setVisible(False)
                
                # Show equip button - corrected variable name
                self.equip_btn.setVisible(True)
            else:
                self.equip_slot_label.setVisible(False)
                self.durability_label.setVisible(False)
                self.equip_btn.setVisible(False)
            
            # Clear and update stats - using stats_text instead of stats_list
            self.stats_text.clear()
            stats_html = ""
            
            if hasattr(item, 'stats'):
                for stat in item.stats:
                    # Check if stat is a dictionary or an ItemStat object
                    if isinstance(stat, dict):
                        stat_name = stat.get('name', 'Unknown')
                        stat_value = stat.get('value', 0)
                        is_percentage = stat.get('is_percentage', False)
                        
                        # Check if this stat is known (if known_properties exists)
                        is_known = True
                        if hasattr(item, 'known_properties') and isinstance(item.known_properties, dict):
                            is_known = item.known_properties.get(stat_name, True)
                    else:
                        # It's an ItemStat object
                        stat_name = getattr(stat, 'name', 'Unknown')
                        stat_value = getattr(stat, 'value', 0)
                        is_percentage = getattr(stat, 'is_percentage', False)
                        
                        # Check if this stat is known
                        is_known = True
                        if hasattr(item, 'known_properties') and isinstance(item.known_properties, dict):
                            is_known = item.known_properties.get(stat_name, True)
                    
                    if is_known:
                        # Format the stat value with sign and percentage if applicable
                        if is_percentage:
                            display_value = f"{stat_value:+.1f}%"
                        else:
                            display_value = f"{stat_value:+.1f}"
                        
                        stats_html += f"{stat_name}: {display_value}<br>"
                
                self.stats_text.setHtml(stats_html)
            
            # Show the panel
            self.setVisible(True)
        except Exception as e:
            from core.utils.logging_config import LoggingConfig, LogCategory
            logger = LoggingConfig.get_logger(__name__, LogCategory.GAME)
            logger.error(f"Error setting item details: {str(e)}", exc_info=True)
            
    def _format_currency(self, value, formatter=None):
        """Format currency value"""
        if formatter:
            return formatter(value)
        else:
            # Default formatting
            return f"{value} copper"
    
    def _on_equip_clicked(self):
        if self.current_item:
            self.equipItem.emit(self.current_item.id)
    
    def _on_drop_clicked(self):
        if self.current_item:
            self.dropItem.emit(self.current_item.id)
    
    def _on_close_clicked(self):
        self.setVisible(False)
        self.closePanel.emit()


class SelectEquipItemPanel(QFrame):
    """Panel for selecting an item to equip to a slot"""
    itemSelected = Signal(str)  # Emits item ID when selected
    cancelSelection = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setStyleSheet("""
            SelectEquipItemPanel {
                background-color: #e9e1d3;
                border: 1px solid #a89f8c;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)
        
        # Title
        self.title_label = QLabel("Select an item to equip")
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout.addWidget(self.title_label)
        
        # Instructions
        self.instr_label = QLabel("Click on an item to equip it to the selected slot.")
        self.layout.addWidget(self.instr_label)
        
        # Item list
        self.item_list = QListWidget()
        self.item_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(255, 255, 255, 120);
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: rgba(100, 149, 237, 150);
            }
            QListWidget::item:hover {
                background-color: rgba(176, 196, 222, 100);
            }
        """)
        self.item_list.itemClicked.connect(self._on_item_clicked)
        self.layout.addWidget(self.item_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_btn)
        
        self.select_btn = QPushButton("Select")
        self.select_btn.clicked.connect(self._on_select_clicked)
        button_layout.addWidget(self.select_btn)
        
        self.layout.addLayout(button_layout)
        
        # Initialize
        self.setVisible(False)
        self.current_slot = None
    
    def set_slot_and_items(self, slot: EquipmentSlot, items: List[Item]):
        """Set the target slot and available items"""
        self.current_slot = slot
        slot_name = slot.value.replace('_', ' ').title()
        
        self.title_label.setText(f"Select an item for {slot_name}")
        
        # Clear list
        self.item_list.clear()
        
        # Safety check - if no items, don't show panel
        if not items:
            self.setVisible(False)
            return
        
        # Add items to list
        for item in items:
            list_item = QListWidgetItem()
            list_item.setText(item.name)
            list_item.setData(Qt.UserRole, item.id)  # Store item ID
            
            # Set color based on rarity
            rarity_colors = {
                "common": "#aaaaaa",
                "uncommon": "#1eff00",
                "rare": "#0070dd",
                "epic": "#a335ee",
                "legendary": "#ff8000",
                "mythic": "#ff0000"
            }
            color = rarity_colors.get(item.rarity.value, "#aaaaaa")
            list_item.setForeground(QColor(color))
            
            # Add icon if available
            if item.icon and os.path.exists(item.icon):
                list_item.setIcon(QPixmap(item.icon))
            
            self.item_list.addItem(list_item)
        
        # Show the panel
        self.setVisible(True)
    
    def _on_item_clicked(self, item):
        self.select_btn.setEnabled(True)
    
    def _on_select_clicked(self):
        selected_items = self.item_list.selectedItems()
        if selected_items:
            item_id = selected_items[0].data(Qt.UserRole)
            self.itemSelected.emit(item_id)
            self.setVisible(False)
    
    def _on_cancel_clicked(self):
        self.setVisible(False)
        self.cancelSelection.emit()