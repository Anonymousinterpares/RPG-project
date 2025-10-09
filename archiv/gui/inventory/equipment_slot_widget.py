# gui/inventory/equipment_slot_widget.py
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter, QPen
from PySide6.QtCore import Qt, Signal, QPoint

import os
from typing import Optional

from core.inventory.item import Item, ItemType, EquipmentSlot
from core.utils.logging_config import LogCategory, LoggingConfig


class EquipmentSlotWidget(QWidget):
    """Widget representing an equipment slot"""
    clicked = Signal(EquipmentSlot)  # Emits slot when clicked
    rightClicked = Signal(EquipmentSlot, QPoint)  # Emits slot and global position
    
    def __init__(self, slot: EquipmentSlot, item: Optional[Item] = None, parent=None):
        super().__init__(parent)
        self.logger = LoggingConfig.get_logger(__name__, LogCategory.GAME)
        self.slot = slot
        self.item = item
        self.setMinimumSize(10, 10)  # Minimum size for visibility
        self.setMouseTracking(True)
        self.hovered = False
        
        # Slot appearance
        self.setStyleSheet("""
            EquipmentSlotWidget {
                background-color: rgba(255, 255, 255, 120);
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            EquipmentSlotWidget:hover {
                background-color: rgba(255, 255, 255, 180);
                border: 1px solid #aaa;
            }
        """)
    
    def paintEvent(self, event):
        """Custom painting for equipment slot"""
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw slot background
        if self.hovered:
            painter.fillRect(self.rect(), QColor(255, 255, 255, 180))
        else:
            painter.fillRect(self.rect(), QColor(255, 255, 255, 120))
            
        if self.item:
            # Check if we have a valid icon
            has_valid_icon = self.item.icon and os.path.exists(self.item.icon)
            
            if has_valid_icon:
                # Draw the item icon with proper scaling
                pixmap = QPixmap(self.item.icon)
                margin = int(self.width() * 0.1)
                painter.drawPixmap(
                    margin, margin,
                    self.width() - 2*margin, self.height() - 2*margin, 
                    pixmap
                )
            else:
                # No valid icon, draw colored placeholder with item's first letter
                bg_color = {
                    ItemType.WEAPON: "#ffb380",      # Light orange
                    ItemType.ARMOR: "#a6c8ff",       # Light blue
                    ItemType.ACCESSORY: "#d9b3ff",   # Light purple
                    ItemType.CONSUMABLE: "#b3ffb3",  # Light green  
                    ItemType.QUEST: "#ffff99",       # Light yellow
                    ItemType.MISCELLANEOUS: "#d9d9d9" # Light gray
                }.get(self.item.item_type, "#d9d9d9")
                
                # Draw colored background
                margin = int(self.width() * 0.1)
                rect_size = self.width() - (2 * margin)
                painter.fillRect(
                    margin, margin, 
                    rect_size, rect_size,
                    QColor(bg_color)
                )
                
                # Draw item's first letter
                painter.setPen(QPen(QColor("#333")))
                font_size = max(7, int(self.width() / 5))
                font = QFont("Arial", font_size, QFont.Bold)
                painter.setFont(font)
                
                # Item's first letter
                first_letter = self.item.name[0] if self.item.name else "?"
                painter.drawText(
                    margin, margin, rect_size, rect_size,
                    Qt.AlignCenter, 
                    first_letter
                )
        else:
            # Draw slot label if no item
            painter.setPen(QPen(QColor(100, 100, 100)))
            # Scale font based on widget size
            font_size = max(7, int(self.width() / 10))
            font = QFont("Arial", font_size)
            painter.setFont(font)
            slot_name = self.slot.value.replace('_', ' ').title()
            
            # Handle finger slots specially to make them more readable
            if "finger" in self.slot.value:
                # For example: "finger_left_index" -> "L. Index"
                parts = self.slot.value.split('_')
                if len(parts) >= 3:
                    hand = parts[1][0].upper() + "."  # First letter of left/right
                    finger = parts[2].title()
                    slot_name = f"{hand} {finger}"
            
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                slot_name
            )
            
        # Draw border
        if self.hovered:
            painter.setPen(QPen(QColor("#aaa"), 2))
        else:
            painter.setPen(QPen(QColor("#ccc"), 1))
        painter.drawRect(1, 1, self.width()-2, self.height()-2)
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slot)
        elif event.button() == Qt.RightButton:
            self.rightClicked.emit(self.slot, event.globalPos())
        # Accept the event to prevent propagation and grabbing issues
        event.accept()
    
    def enterEvent(self, event):
        """Handle mouse enter events"""
        self.hovered = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave events"""
        self.hovered = False
        self.update()
        super().leaveEvent(event)