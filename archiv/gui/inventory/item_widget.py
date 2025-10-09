# gui/inventory/item_widget.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, Signal, QPoint

import os
from typing import Optional

from core.inventory.item import Item, ItemType
from core.utils.logging_config import LogCategory, LoggingConfig
from .utils import load_image_with_fallback


class ItemWidget(QWidget):
    """Widget representing a single item in inventory"""
    clicked = Signal(str)
    rightClicked = Signal(str, QPoint) 
    
    def __init__(self, item: Item, parent=None):
        super().__init__(parent)
        self.logger = LoggingConfig.get_logger(__name__, LogCategory.GAME)
        self.item = item
        self.setMinimumHeight(60)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Set up hover effects
        self.setMouseTracking(True)
        self.setStyleSheet("""
            ItemWidget {
                background-color: rgba(255, 255, 255, 180);
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            ItemWidget:hover {
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid #aaa;
            }
        """)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Add icon
        self.icon_label = QLabel()
        try:
            icon_path = item.icon if item.icon and os.path.exists(item.icon) else ""
            if icon_path:
                pixmap = QPixmap(icon_path)
                self.icon_label.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio))
            else:
                # Create colored background based on item type
                bg_color = {
                    ItemType.WEAPON: "#ffb380",      # Light orange
                    ItemType.ARMOR: "#a6c8ff",       # Light blue
                    ItemType.ACCESSORY: "#d9b3ff",   # Light purple
                    ItemType.CONSUMABLE: "#b3ffb3",  # Light green  
                    ItemType.QUEST: "#ffff99",       # Light yellow
                    ItemType.MISCELLANEOUS: "#d9d9d9" # Light gray
                }.get(item.item_type, "#d9d9d9")
                
                self.icon_label.setText(item.name[0])  # First letter of item name
                self.icon_label.setStyleSheet(f"background-color: {bg_color}; padding: 5px; "
                                            f"font-weight: bold; font-size: 20px; "
                                            f"color: #333; border-radius: 5px;")
        except Exception as e:
            self.icon_label.setText("!")
            self.icon_label.setStyleSheet("background-color: #fdd; padding: 5px; "
                                        "font-size: 20px; font-weight: bold; "
                                        "color: red; border-radius: 5px;")
            print(f"Error loading item icon: {e}")
            
        self.icon_label.setFixedSize(50, 50)
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)
        
        # Add info
        info_layout = QVBoxLayout()
        
        # Item name with rarity color
        self.name_label = QLabel(item.name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        
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
        self.name_label.setStyleSheet(f"color: {color};")
        
        info_layout.addWidget(self.name_label)
        
        # Item type and weight
        self.details_label = QLabel(f"{item.item_type.value.capitalize()} | {item.weight} kg")
        self.details_label.setFont(QFont("Arial", 8))
        info_layout.addWidget(self.details_label)
        
        layout.addLayout(info_layout)
        
        # Add indicators for equipped/damaged
        self.status_layout = QVBoxLayout()
        
        if item.is_equippable:
            self.equipped_label = QLabel("E")
            self.equipped_label.setToolTip("Equippable")
            self.equipped_label.setStyleSheet("background-color: #dfd; padding: 3px; border-radius: 3px;")
            self.status_layout.addWidget(self.equipped_label)
            
        if item.is_damaged:
            durability_pct = (item.durability / item.max_durability) * 100
            durability_label = QLabel(f"{durability_pct:.0f}%")
            durability_label.setToolTip(f"Durability: {item.durability}/{item.max_durability}")
            
            # Color based on durability
            if durability_pct < 25:
                durability_label.setStyleSheet("background-color: #fdd; padding: 3px; border-radius: 3px;")
            elif durability_pct < 50:
                durability_label.setStyleSheet("background-color: #ffd; padding: 3px; border-radius: 3px;")
            else:
                durability_label.setStyleSheet("background-color: #dfd; padding: 3px; border-radius: 3px;")
                
            self.status_layout.addWidget(durability_label)
            
        if item.stackable and item.stack_size > 1:
            stack_label = QLabel(f"x{item.stack_size}")
            stack_label.setToolTip(f"Stack size: {item.stack_size}")
            stack_label.setStyleSheet("background-color: #ddf; padding: 3px; border-radius: 3px;")
            self.status_layout.addWidget(stack_label)
            
        layout.addLayout(self.status_layout)
        
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.item.id)
        elif event.button() == Qt.RightButton:
            self.rightClicked.emit(self.item.id, event.globalPos())
        # Accept the event to prevent propagation and grabbing issues
        event.accept()