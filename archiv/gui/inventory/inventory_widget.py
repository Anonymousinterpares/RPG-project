# gui/inventory/inventory_widget.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
                             QScrollArea, QFrame, QPushButton, QSizePolicy,
                             QDialog, QTabWidget, QMenu, QGridLayout,
                             QApplication, QSplitter)
from PySide6.QtGui import QPixmap, QFont, QAction, QCursor
from PySide6.QtCore import Qt, Signal, QTimer

from typing import Dict, List, Optional, Tuple
import os

# Import item classes
from core.inventory.item import Item, ItemType, EquipmentSlot, ItemRarity
from core.utils.logging_config import LogCategory, LoggingConfig

# Import our components from separate modules
from .utils import load_image_with_fallback
from .item_widget import ItemWidget
from .equipment_slot_widget import EquipmentSlotWidget
from .detail_panels import ItemDetailPanel, SelectEquipItemPanel


class InventoryWidget(QWidget):
    """Main inventory widget with equipment and backpack views"""
    itemEquipped = Signal(str)  # Emits item ID
    itemUnequipped = Signal(EquipmentSlot)  # Emits slot
    itemExamined = Signal(str)  # Emits item ID
    itemRemoved = Signal(str)  # Emits item ID
        
    def __init__(self, inventory_manager, parent=None):
        super().__init__(parent)
        self.logger = LoggingConfig.get_logger(__name__, LogCategory.GAME)
        self.inventory_manager = inventory_manager
        self.setStyleSheet("background-color: #d9caaa;")  # Set background color
        
        # Initialize all instance variables first to avoid reference errors
        self.slots_label = QLabel()
        self.weight_label = QLabel()
        self.currency_label = QLabel()
        self.equipment_slots = {}
        self.silhouette_container = None
        self.char_label = None
        self.char_pixmap = None
        self.slots_frame = None
        self.equipment_tab = None
        self.backpack_tab = None
        self.backpack_content = None
        self.backpack_items_layout = None
        self.tabs = None
        self.current_slot_for_equip = None  # Stores the current slot awaiting an item to equip
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        
        # Tabs for equipment and backpack
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { background-color: #d9caaa; }")
        
        # ===== EQUIPMENT TAB =====
        self.equipment_tab = QWidget()
        self.equipment_tab.setStyleSheet("background-color: #d9caaa;")
        
        # Use a vertical layout for equipment tab
        self.equipment_layout = QVBoxLayout(self.equipment_tab)
        self.equipment_layout.setContentsMargins(0, 0, 0, 0)
        self.equipment_layout.setSpacing(5)
        
        # Add weight and currency labels at the top
        stats_panel = QWidget()
        stats_layout = QVBoxLayout(stats_panel)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.addWidget(self.weight_label)
        # Add stretch to push currency label to the right
        stats_layout.addStretch()

        # Add currency label to the right
        self.currency_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        stats_layout.addWidget(self.currency_label)
        self.equipment_layout.addWidget(stats_panel)
        
        # Create a central container for the character display
        self.left_container = QWidget()
        self.left_container.setStyleSheet("background-color: transparent;")
        self.left_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setAlignment(Qt.AlignCenter)
        
        # Character silhouette with proper scaling
        self.silhouette_container = QWidget()
        self.silhouette_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.silhouette_container.setStyleSheet("background-color: transparent;")
        silhouette_layout = QVBoxLayout(self.silhouette_container)
        silhouette_layout.setContentsMargins(5, 5, 5, 5)
        silhouette_layout.setAlignment(Qt.AlignCenter)
        
        # Character silhouette
        try:
            silhouette_path = "images/character/silhouette.png"
            self.char_label = QLabel()
            self.char_label.setAlignment(Qt.AlignCenter)
            self.char_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.char_pixmap = load_image_with_fallback(silhouette_path)
            if self.char_pixmap:
                silhouette_layout.addWidget(self.char_label, 1)
            else:
                raise FileNotFoundError("Character silhouette image not found")
        except Exception as e:
            # Fallback to colored placeholder
            self.char_label = QLabel("Character\nSilhouette")
            self.char_label.setStyleSheet("background-color: #d0d0d0; border: 1px solid #aaa;")
            self.char_label.setAlignment(Qt.AlignCenter)
            self.char_label.setFont(QFont("Arial", 14, QFont.Bold))
            self.char_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            silhouette_layout.addWidget(self.char_label, 1)
            self.logger.warning(f"Using fallback silhouette: {e}")
        
        # Add silhouette container to left layout
        left_layout.addWidget(self.silhouette_container)
        
        # Equipment slots frame - positioned as a child of silhouette container
        self.slots_frame = QFrame(self.silhouette_container)
        self.slots_frame.setStyleSheet("background: transparent;")
        
        # Add left container to equipment layout
        self.equipment_layout.addWidget(self.left_container, 1)  # stretch=1 to fill space
        
        self.tabs.addTab(self.equipment_tab, "Equipment")
        
        # ===== BACKPACK TAB =====
        self.backpack_tab = QWidget()
        self.backpack_tab.setStyleSheet("background-color: #d9caaa;")
        
        # Use a splitter for backpack tab to allow resizing panels
        self.backpack_splitter = QSplitter(Qt.Vertical)
        self.backpack_layout = QVBoxLayout(self.backpack_tab)
        self.backpack_layout.setContentsMargins(0, 0, 0, 0)
        self.backpack_layout.addWidget(self.backpack_splitter)
        
        # Backpack items panel (top part of splitter)
        self.backpack_panel = QWidget()
        self.backpack_panel.setStyleSheet("background-color: #d9caaa;")
        self.backpack_panel_layout = QVBoxLayout(self.backpack_panel)
        
        # Backpack scroll area
        self.backpack_scroll = QScrollArea()
        self.backpack_scroll.setWidgetResizable(True)
        self.backpack_scroll.setFrameShape(QFrame.NoFrame)
        self.backpack_scroll.setStyleSheet("background-color: #d9caaa;")
        
        self.backpack_content = QWidget()
        self.backpack_content.setStyleSheet("background-color: #d9caaa;")
        self.backpack_items_layout = QVBoxLayout(self.backpack_content)
        self.backpack_items_layout.setAlignment(Qt.AlignTop)
        
        # Set up backpack
        self.backpack_scroll.setWidget(self.backpack_content)
        self.backpack_panel_layout.addWidget(self.backpack_scroll)
        self.backpack_panel_layout.addWidget(self.slots_label)
        
        # Add backpack panel to splitter
        self.backpack_splitter.addWidget(self.backpack_panel)
        
        # Create detail panel (bottom part of splitter)
        self.item_detail_panel = ItemDetailPanel()
        self.item_detail_panel.equipItem.connect(self._on_equip_from_panel)
        self.item_detail_panel.dropItem.connect(self._on_drop_from_panel)
        self.backpack_splitter.addWidget(self.item_detail_panel)
        
        # Create select item panel (overlays backpack when active)
        self.select_item_panel = SelectEquipItemPanel()
        self.select_item_panel.itemSelected.connect(self._on_item_selected_for_slot)
        self.select_item_panel.cancelSelection.connect(self._on_item_selection_canceled)
        self.backpack_panel_layout.addWidget(self.select_item_panel)
        
        # Set initial splitter sizes (2:1 ratio)
        self.backpack_splitter.setSizes([700, 300])
        
        # Hide detail panel initially
        self.item_detail_panel.setVisible(False)
        self.select_item_panel.setVisible(False)
        
        self.tabs.addTab(self.backpack_tab, "Backpack")
        
        layout.addWidget(self.tabs)
        
        # Now that everything is set up, initialize and update displays
        self._init_equipment_slots()
        self.update_weight_label()
        self.update_currency_label()
        self.update_slots_label()
        
        # Update backpack display last
        self.update_backpack_display()

        # Force initial layout
        QTimer.singleShot(100, self._update_silhouette_image)
        QTimer.singleShot(100, self._position_equipment_slots)

    def _update_silhouette_image(self):
        """Update silhouette image scaling to fit the container"""
        if hasattr(self, 'char_pixmap') and self.char_pixmap and not self.char_pixmap.isNull():
            container_size = self.silhouette_container.size()
            if container_size.width() > 0 and container_size.height() > 0:
                try:
                    # Scale to fit container with a small margin
                    scaled_pixmap = self.char_pixmap.scaled(
                        container_size.width(),
                        container_size.height(),
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.char_label.setPixmap(scaled_pixmap)
                except Exception as e:
                    self.logger.error(f"Error scaling silhouette image: {e}")

    def resizeEvent(self, event):
        """Handle resize events to scale UI elements properly"""
        super().resizeEvent(event)
        
        # Scale the silhouette image
        self._update_silhouette_image()
        
        # Update equipment slot positions
        self._position_equipment_slots()

    def showEvent(self, event):
        """Handle show events to ensure proper initialization"""
        super().showEvent(event)
        
        # Make sure silhouette is visible and properly sized
        self._update_silhouette_image()
        
        # Make sure equipment slots are positioned correctly
        self._position_equipment_slots()
        
    def _init_equipment_slots(self):
        """Initialize all equipment slots"""
        # Clear any existing slots
        for slot_widget in self.equipment_slots.values():
            if slot_widget.parent() == self.slots_frame:
                slot_widget.setParent(None)
        self.equipment_slots.clear()
        
        # Create equipment slot widgets - exclude TWO_HAND as it's special
        all_slots = [slot for slot in EquipmentSlot if slot not in [EquipmentSlot.TWO_HAND, EquipmentSlot.HANDS]]
        
        for slot in all_slots:
            item = self.inventory_manager.equipped_items.get(slot)
            slot_widget = EquipmentSlotWidget(slot, item, self.slots_frame)
            slot_widget.clicked.connect(self._on_equipment_slot_clicked)
            slot_widget.rightClicked.connect(self._on_equipment_slot_right_clicked)
            self.equipment_slots[slot] = slot_widget
        
        # Position the slots initially
        self._position_equipment_slots()

    def _position_equipment_slots(self):
        """Position equipment slots using relative coordinates on top of silhouette"""
        if not self.slots_frame or not self.silhouette_container:
            return
        
        # Make sure slots frame covers entire silhouette container
        self.slots_frame.setGeometry(0, 0, self.silhouette_container.width(), self.silhouette_container.height())
        
        frame_width = self.slots_frame.width()
        frame_height = self.slots_frame.height()
        
        # Base size for regular slots
        base_size = min(frame_width // 6, frame_height // 9)
        # Smaller size for finger slots
        finger_size = max(int(base_size // 1.5 ), 10)  # Ensure minimum size
        
        # Define positions as percentages of container dimensions
        # Format: (x_percent, y_percent, width, height)
        positions = {
            # Main body parts - centered with better spacing
            EquipmentSlot.HEAD: (50, 0, base_size, base_size),
            EquipmentSlot.NECK: (50, 16, base_size, base_size),
            EquipmentSlot.SHOULDERS: (70, 23, base_size, base_size),
            EquipmentSlot.CHEST: (30, 23, base_size, base_size),
            EquipmentSlot.BACK: (75, 34, base_size, base_size),
            EquipmentSlot.LEFT_WRIST: (65, 44, base_size, base_size), 
            EquipmentSlot.RIGHT_WRIST: (35, 44, base_size, base_size), 
            EquipmentSlot.WAIST: (50, 41, base_size, base_size),
            EquipmentSlot.LEGS: (50, 70, base_size, base_size),
            EquipmentSlot.FEET: (50, 100, base_size, base_size),
            
            # Hands
            EquipmentSlot.LEFT_HAND: (70, 58, base_size, base_size),
            EquipmentSlot.RIGHT_HAND: (30, 58, base_size, base_size),
            
            # Left hand fingers (vertically aligned)
            EquipmentSlot.FINGER_LEFT_THUMB: (80, 44, finger_size, finger_size), 
            EquipmentSlot.FINGER_LEFT_INDEX: (80, 52, finger_size, finger_size),
            EquipmentSlot.FINGER_LEFT_MIDDLE: (80, 60, finger_size, finger_size),
            EquipmentSlot.FINGER_LEFT_RING: (80, 68, finger_size, finger_size),
            EquipmentSlot.FINGER_LEFT_PINKY: (80, 76, finger_size, finger_size),
            
            # Right hand fingers (vertically aligned)
            EquipmentSlot.FINGER_RIGHT_THUMB: (20, 44, finger_size, finger_size),  
            EquipmentSlot.FINGER_RIGHT_INDEX: (20, 52, finger_size, finger_size),
            EquipmentSlot.FINGER_RIGHT_MIDDLE: (20, 60, finger_size, finger_size),
            EquipmentSlot.FINGER_RIGHT_RING: (20, 68, finger_size, finger_size),
            EquipmentSlot.FINGER_RIGHT_PINKY: (20, 76, finger_size, finger_size),
        }
        
        # Position each slot widget
        for slot, pos in positions.items():
            if slot in self.equipment_slots:
                widget = self.equipment_slots[slot]
                x_percent, y_percent, width, height = pos
                
                # Calculate position - centered on percentage point
                x = int((frame_width * x_percent / 100) - (width / 2))
                y = int((frame_height * y_percent / 100) - (height / 2))
                
                # Ensure slots stay within frame boundaries
                x = max(0, min(x, frame_width - width))
                y = max(0, min(y, frame_height - height))
                
                # Set position and size
                widget.setGeometry(x, y, width, height)
                widget.show()

    def update_equipment_display(self):
        """Update equipment display with current items"""
        for slot, widget in self.equipment_slots.items():
            item = self.inventory_manager.equipped_items.get(slot)
            widget.item = item
            widget.update()
        
        self.update_weight_label()
        self.update_currency_label()
    
    def update_backpack_display(self):
        """Update backpack display with current items"""
        # Check if the layout exists
        if not hasattr(self, 'backpack_items_layout') or not self.backpack_items_layout:
            self.logger.warning("Backpack items layout not initialized")
            return
            
        # Clear current items
        for i in reversed(range(self.backpack_items_layout.count())): 
            widget = self.backpack_items_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Add current items
        for item in self.inventory_manager.backpack:
            item_widget = ItemWidget(item)
            item_widget.clicked.connect(self._on_backpack_item_clicked)
            item_widget.rightClicked.connect(self._on_backpack_item_right_clicked)
            self.backpack_items_layout.addWidget(item_widget)

        if hasattr(self, 'slots_label') and self.slots_label:
            self.update_slots_label()
        if hasattr(self, 'weight_label') and self.weight_label:
            self.update_weight_label()
    
    def update_weight_label(self):
        """Update weight display"""
        current_weight = self.inventory_manager.get_current_weight()
        # Use player's STR if available, otherwise use default
        strength = 10
        if hasattr(self, 'parent') and hasattr(self.parent(), 'gm'):
            if self.parent().gm and self.parent().gm.state_manager.state:
                strength = self.parent().gm.state_manager.state.player.stats.get('STR', 10)
        
        weight_limit = self.inventory_manager.get_weight_limit(strength)
        weight_pct = (current_weight / weight_limit) * 100
        
        # Set color based on weight percentage
        if weight_pct >= 90:
            color = "red"
        elif weight_pct >= 75:
            color = "orange"
        else:
            color = "black"
            
        self.weight_label.setText(
            f"Weight: <span style='color:{color};'>{current_weight:.1f}/{weight_limit:.1f} kg</span> ({weight_pct:.1f}%)"
        )
    
    def update_slots_label(self):
        """Update slots display"""
        used_slots = len(self.inventory_manager.backpack)
        max_slots = self.inventory_manager.max_slots
        slots_pct = (used_slots / max_slots) * 100
        
        # Set color based on slots percentage
        if slots_pct >= 90:
            color = "red"
        elif slots_pct >= 75:
            color = "orange"
        else:
            color = "black"
            
        self.slots_label.setText(
            f"Slots: <span style='color:{color};'>{used_slots}/{max_slots}</span> ({slots_pct:.1f}%)"
        )
    
    def update_currency_label(self):
        """Update currency display"""
        currency = self.inventory_manager.currency
        self.currency_label.setText(
            f"Money: {currency['gold']}g {currency['silver']}s {currency['copper']}c"
        )
    
    def _on_equipment_slot_clicked(self, slot):
        """Handle equipment slot clicked"""
        # If there's an item in the slot, unequip it
        item = self.inventory_manager.equipped_items.get(slot)
        if item:
            success, message = self.inventory_manager.unequip_item(slot)
            if success:
                self.itemUnequipped.emit(slot)
                self.update_equipment_display()
                self.update_backpack_display()
                
                # Add to context
                self._add_to_context(f"Unequipped {item.name} from {slot.value.replace('_', ' ')}")
            else:
                # Show error
                QMessageBox.warning(self, "Cannot Unequip", message)
    
    def _on_equipment_slot_right_clicked(self, slot, position):
        """Handle right-click on equipment slot"""
        try:
            # Get item in slot if any
            item = self.inventory_manager.equipped_items.get(slot)
            
            # Create simple menu
            menu = QMenu(self)
            
            if item:
                # Slot has an item
                remove_action = QAction("Remove Item", self)
                remove_action.triggered.connect(lambda: self._remove_item_from_slot(slot))
                menu.addAction(remove_action)
                
                change_action = QAction("Change Item", self)
                change_action.triggered.connect(lambda: self._change_item_in_slot(slot))
                menu.addAction(change_action)
                
                inspect_action = QAction("Inspect Item", self)
                inspect_action.triggered.connect(lambda: self._inspect_equipped_item(slot))
                menu.addAction(inspect_action)
            else:
                # Empty slot
                add_action = QAction("Add Item", self)
                add_action.triggered.connect(lambda: self._add_item_to_slot(slot))
                menu.addAction(add_action)
            
            # Show the menu at the right click position
            menu.exec_(position)
        except Exception as e:
            self.logger.error(f"Error in equipment slot right-click: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def _on_backpack_item_clicked(self, item_id):
        """Handle backpack item clicked by showing it in the detail panel"""
        # Find the item
        item = self._find_backpack_item(item_id)
        if not item:
            return
        
        # Switch to backpack tab if not already there
        self.tabs.setCurrentWidget(self.backpack_tab)
        
        # Show item details in panel
        self.item_detail_panel.set_item(item, self._format_currency)
        
        # Signal item was examined
        self.itemExamined.emit(item_id)
    
    def _on_backpack_item_right_clicked(self, item_id, position):
        """Handle right-click on backpack item"""
        # Find the item
        item = self._find_backpack_item(item_id)
        if not item:
            return
        
        # Create context menu
        menu = QMenu(self)
        
        # Equip option (if equippable)
        if item.is_equippable:
            equip_menu = QMenu("Equip to...", self)
            
            # Get valid slots for this item
            valid_slots = self._get_valid_slots_for_item(item)
            
            for slot in valid_slots:
                slot_name = slot.value.replace('_', ' ').title()
                action = QAction(slot_name, self)
                action.triggered.connect(lambda checked=False, s=slot: self._equip_to_slot(item_id, s))
                equip_menu.addAction(action)
            
            menu.addMenu(equip_menu)
        
        # Investigate option
        investigate_action = QAction("Inspect", self)
        investigate_action.triggered.connect(lambda: self._on_backpack_item_clicked(item_id))
        menu.addAction(investigate_action)
        
        # Drop option
        drop_action = QAction("Drop Item", self)
        drop_action.triggered.connect(lambda: self._drop_item(item_id))
        menu.addAction(drop_action)
        
        menu.exec_(position)
    
    def _find_backpack_item(self, item_id):
        """Find an item in the backpack by ID"""
        for item in self.inventory_manager.backpack:
            if item.id == item_id:
                return item
        return None
    
    def _get_valid_slots_for_item(self, item):
        """Get valid equipment slots for an item"""
        if not item.is_equippable or not item.equipment_slot:
            return []
        
        # Two-handed items can only go in two_hand slot
        if item.equipment_slot == EquipmentSlot.TWO_HAND:
            return [EquipmentSlot.TWO_HAND]
        
        # Allow one-handed items to be equipped in either hand
        if item.equipment_slot == EquipmentSlot.ONE_HAND:
            return [EquipmentSlot.LEFT_HAND, EquipmentSlot.RIGHT_HAND]
        
        # Return the specific slot this item is designed for
        return [item.equipment_slot]
    
    def _remove_item_from_slot(self, slot):
        """Remove item from equipment slot"""
        item = self.inventory_manager.equipped_items.get(slot)
        if item:
            success, message = self.inventory_manager.unequip_item(slot)
            if success:
                self.itemUnequipped.emit(slot)
                self.update_equipment_display()
                self.update_backpack_display()
                
                # Add to context
                self._add_to_context(f"Removed {item.name} from {slot.value.replace('_', ' ')}")
            else:
                # Show error
                QMessageBox.warning(self, "Cannot Remove", message)
        
    def _change_item_in_slot(self, slot):
        """Change item in equipment slot using a simple menu approach"""
        try:
            # Find valid items for this slot
            valid_items = []
            for item in self.inventory_manager.backpack:
                if item.is_equippable:
                    valid_slots = self._get_valid_slots_for_item(item)
                    if slot in valid_slots:
                        valid_items.append(item)
            
            # If no valid items, show a message and exit early
            if not valid_items:
                # Find the top-level window for proper parenting
                from PySide6.QtWidgets import QApplication
                main_window = QApplication.activeWindow()
                
                # Create menu instead of messageBox
                no_items_menu = QMenu(main_window if main_window else self)
                title_action = QAction(f"No Suitable Items", self)
                title_action.setEnabled(False)
                font = title_action.font()
                font.setBold(True)
                title_action.setFont(font)
                no_items_menu.addAction(title_action)
                
                # Add message as a disabled menu item
                message_action = QAction(f"You don't have any items that can be equipped in the {slot.value.replace('_', ' ')} slot.", self)
                message_action.setEnabled(False)
                no_items_menu.addAction(message_action)
                
                # Add an OK button
                no_items_menu.addSeparator()
                ok_action = QAction("OK", self)
                ok_action.triggered.connect(no_items_menu.close)
                no_items_menu.addAction(ok_action)
                
                # Show the menu at the cursor position
                cursor_pos = QCursor.pos()
                no_items_menu.exec_(cursor_pos)
                return
            
            # Create a menu with valid items
            menu = QMenu(self)
            menu.setStyleSheet("QMenu { min-width: 200px; }")
            
            # Title for the menu (non-clickable item)
            title_action = QAction(f"Select item for {slot.value.replace('_', ' ').title()}", self)
            title_action.setEnabled(False)
            font = title_action.font()
            font.setBold(True)
            title_action.setFont(font)
            menu.addAction(title_action)
            menu.addSeparator()
            
            # Add each valid item to the menu
            for item in valid_items:
                action = QAction(item.name, self)
                
                # Set icon if available
                if item.icon and os.path.exists(item.icon):
                    action.setIcon(QPixmap(item.icon))
                
                # Set data for identification
                action.setData(item.id)
                
                # Connect action to equip handler
                action.triggered.connect(
                    lambda checked=False, item_id=item.id: self._equip_after_change(slot, item_id)
                )
                
                menu.addAction(action)
            
            # Show the menu at the cursor position
            cursor_pos = QCursor.pos()
            menu.exec_(cursor_pos)
            
        except Exception as e:
            self.logger.error(f"Error changing item in slot: {e}")
            
            # Show error in a menu instead of messagebox
            try:
                error_menu = QMenu(self)
                title_action = QAction("Error", self)
                title_action.setEnabled(False)
                font = title_action.font()
                font.setBold(True)
                title_action.setFont(font)
                error_menu.addAction(title_action)
                
                # Add error message as a disabled menu item
                message_action = QAction(f"An error occurred: {str(e)}", self)
                message_action.setEnabled(False)
                error_menu.addAction(message_action)
                
                # Add an OK button
                error_menu.addSeparator()
                ok_action = QAction("OK", self)
                ok_action.triggered.connect(error_menu.close)
                error_menu.addAction(ok_action)
                
                # Show the menu at the cursor position
                cursor_pos = QCursor.pos()
                error_menu.exec_(cursor_pos)
            except:
                # Absolute fallback - print to console
                print(f"Critical error: {e}")

    def _equip_after_change(self, slot, item_id):
        """Helper function to equip an item after removing the current one"""
        try:
            # First remove the current item
            current_item = self.inventory_manager.equipped_items.get(slot)
            if current_item:
                success, message = self.inventory_manager.unequip_item(slot)
                if not success:
                    QMessageBox.warning(self, "Cannot Unequip", message)
                    return
            
            # Now equip the new item
            success, message = self.inventory_manager.equip_item(item_id)
            if success:
                item = self._find_backpack_item(item_id)
                if item:
                    self.itemEquipped.emit(item_id)
                    self.update_equipment_display()
                    self.update_backpack_display()
                    self._add_to_context(f"Equipped {item.name} to {slot.value.replace('_', ' ')}")
            else:
                QMessageBox.warning(self, "Cannot Equip", message)
        except Exception as e:
            self.logger.error(f"Error equipping item: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def _add_item_to_slot(self, slot):
        """Add item to empty equipment slot - use the same menu-based approach"""
        self._change_item_in_slot(slot)  # Simply reuse the change item method
    
    def _on_item_selected_for_slot(self, item_id):
        """Handle item selected from the panel to equip to a slot"""
        try:
            if not self.current_slot_for_equip:
                return
            
            slot = self.current_slot_for_equip
            
            # Equip the selected item
            success, message = self.inventory_manager.equip_item(item_id)
            if success:
                item = self._find_backpack_item(item_id)
                if item:
                    self.itemEquipped.emit(item_id)
                    self.update_equipment_display()
                    self.update_backpack_display()
                    self._add_to_context(f"Equipped {item.name} to {slot.value.replace('_', ' ')}")
            else:
                QMessageBox.warning(self, "Cannot Equip", message)
        except Exception as e:
            self.logger.error(f"Error equipping selected item: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
        finally:
            # Reset slot reference
            self.current_slot_for_equip = None
    
    def _on_item_selection_canceled(self):
        """Handle cancellation of item selection"""
        self.current_slot_for_equip = None
    
    def _inspect_equipped_item(self, slot):
        """Inspect item in equipment slot by showing it in the detail panel"""
        item = self.inventory_manager.equipped_items.get(slot)
        if not item:
            QMessageBox.information(
                self, 
                "Empty Slot", 
                f"No item equipped in the {slot.value.replace('_', ' ')} slot."
            )
            return
        
        # Switch to backpack tab to show detail
        self.tabs.setCurrentWidget(self.backpack_tab)
        
        # Show item in panel
        self.item_detail_panel.set_item(item, self._format_currency)
        
        # Signal item was examined
        self.itemExamined.emit(item.id)
    
    def _on_equip_from_panel(self, item_id):
        """Handle equip button clicked in the detail panel"""
        try:
            success, message = self.inventory_manager.equip_item(item_id)
            if success:
                item = self._find_backpack_item(item_id)
                if item:
                    self.itemEquipped.emit(item_id)
                    self.update_equipment_display()
                    self.update_backpack_display()
                    self._add_to_context(f"Equipped {item.name}")
                
                # Hide panel after equipping
                self.item_detail_panel.setVisible(False)
            else:
                QMessageBox.warning(self, "Cannot Equip", message)
        except Exception as e:
            self.logger.error(f"Error equipping from panel: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def _on_drop_from_panel(self, item_id):
        """Handle drop button clicked in the detail panel"""
        # Show confirmation dialog
        reply = QMessageBox.question(
            self, 
            "Drop Item", 
            "Are you sure you want to drop this item?\nIt will be removed from your inventory.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._drop_item(item_id)
            # Hide panel after dropping
            self.item_detail_panel.setVisible(False)
    
    def _equip_to_slot(self, item_id, slot):
        """Equip item from backpack to specific slot"""
        # Find the item
        item = self._find_backpack_item(item_id)
        if not item:
            return
        
        # Check if the slot is already occupied
        current_item = self.inventory_manager.equipped_items.get(slot)
        if current_item:
            reply = QMessageBox.question(
                self, "Replace Item", 
                f"{current_item.name} is already equipped. Replace it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            
            # Unequip current item
            self.inventory_manager.unequip_item(slot)
        
        # Check for two-handed weapon in case of hand slots
        if slot in [EquipmentSlot.LEFT_HAND, EquipmentSlot.RIGHT_HAND]:
            left_item = self.inventory_manager.equipped_items.get(EquipmentSlot.LEFT_HAND)
            right_item = self.inventory_manager.equipped_items.get(EquipmentSlot.RIGHT_HAND)
            
            if left_item and right_item and left_item.id == right_item.id:
                # It's a two-handed weapon
                reply = QMessageBox.question(
                    self, "Replace Two-Handed Weapon", 
                    f"Replace the two-handed weapon {left_item.name}?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
                
                # Unequip both hands
                self.inventory_manager.unequip_item(EquipmentSlot.LEFT_HAND)
        
        # Now equip the new item - for ONE_HAND items, we need to make sure it will work with the specified slot
        if item.equipment_slot == EquipmentSlot.ONE_HAND and slot in [EquipmentSlot.LEFT_HAND, EquipmentSlot.RIGHT_HAND]:
            # We need to do this special logic for equipping one-hand items to either hand
            success = self._equip_one_hand_item(item_id, slot)
        else:
            # For other items, use the normal equipment function
            success, message = self.inventory_manager.equip_item(item_id)
            if not success:
                QMessageBox.warning(self, "Cannot Equip", message)
                return
                
        if success:
            self.itemEquipped.emit(item_id)
            self.update_equipment_display()
            self.update_backpack_display()
            
            # Add to context
            self._add_to_context(f"Equipped {item.name} to {slot.value.replace('_', ' ')}")

    def _equip_one_hand_item(self, item_id, slot):
        """Special handling for equipping one-handed items to either hand"""
        try:
            # For direct equipment of one-handed items to a specific hand
            item = None
            for backpack_item in self.inventory_manager.backpack:
                if backpack_item.id == item_id:
                    item = backpack_item
                    break
            
            if not item:
                return False
                
            # Remove from backpack
            for i, backpack_item in enumerate(self.inventory_manager.backpack):
                if backpack_item.id == item_id:
                    self.inventory_manager.backpack.pop(i)
                    break
            
            # Place in the correct slot
            self.inventory_manager.equipped_items[slot] = item
            return True
            
        except Exception as e:
            self.logger.error(f"Error equipping one-hand item: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            return False

    def _drop_item(self, item_id):
        """Drop (remove) item from inventory using menu-based confirmation"""
        try:
            # Find the item
            item = self._find_backpack_item(item_id)
            if not item:
                return
            
            # Create confirmation menu
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QCursor
            
            main_window = QApplication.activeWindow()
            confirm_menu = QMenu(main_window if main_window else self)
            
            # Title
            title_action = QAction(f"Drop Item: {item.name}", self)
            title_action.setEnabled(False)
            font = title_action.font()
            font.setBold(True)
            title_action.setFont(font)
            confirm_menu.addAction(title_action)
            
            # Message
            message_action = QAction("Are you sure you want to drop this item?\nIt will be removed from your inventory.", self)
            message_action.setEnabled(False)
            confirm_menu.addAction(message_action)
            
            confirm_menu.addSeparator()
            
            # Yes option
            yes_action = QAction("Yes, drop item", self)
            yes_action.triggered.connect(lambda: self._confirm_drop_item(item_id))
            confirm_menu.addAction(yes_action)
            
            # No option
            no_action = QAction("No, keep item", self)
            no_action.triggered.connect(confirm_menu.close)
            confirm_menu.addAction(no_action)
            
            # Show menu at cursor position
            cursor_pos = QCursor.pos()
            confirm_menu.exec_(cursor_pos)
            
        except Exception as e:
            self.logger.error(f"Error preparing to drop item: {e}")
            try:
                # Error menu
                error_menu = QMenu(self)
                title_action = QAction("Error", self)
                title_action.setEnabled(False)
                font = title_action.font()
                font.setBold(True)
                title_action.setFont(font)
                error_menu.addAction(title_action)
                
                # Add error message
                message_action = QAction(f"An error occurred: {str(e)}", self)
                message_action.setEnabled(False)
                error_menu.addAction(message_action)
                
                # Add OK button
                error_menu.addSeparator()
                ok_action = QAction("OK", self)
                ok_action.triggered.connect(error_menu.close)
                error_menu.addAction(ok_action)
                
                # Show menu
                cursor_pos = QCursor.pos()
                error_menu.exec_(cursor_pos)
            except:
                print(f"Critical error in drop item: {e}")

    def _confirm_drop_item(self, item_id):
        """Actually perform the item drop after confirmation"""
        try:
            # Find the item again to be safe
            item = self._find_backpack_item(item_id)
            if not item:
                return
                
            # Remove the item
            removed_item = self.inventory_manager.remove_item(item_id)
            if removed_item:
                self.itemRemoved.emit(item_id)
                self.update_backpack_display()
                
                # Hide detail panel if it was showing this item
                if hasattr(self, 'item_detail_panel') and self.item_detail_panel.isVisible():
                    if hasattr(self.item_detail_panel, 'current_item') and self.item_detail_panel.current_item:
                        if self.item_detail_panel.current_item.id == item_id:
                            self.item_detail_panel.setVisible(False)
                
                # Add to context
                self._add_to_context(f"Dropped {item.name}")
            else:
                # Show failure in a menu
                from PySide6.QtWidgets import QApplication, QMenu
                from PySide6.QtGui import QCursor, QAction
                
                main_window = QApplication.activeWindow()
                error_menu = QMenu(main_window if main_window else self)
                
                title_action = QAction("Cannot Drop Item", self)
                title_action.setEnabled(False)
                font = title_action.font()
                font.setBold(True)
                title_action.setFont(font)
                error_menu.addAction(title_action)
                
                message_action = QAction(f"Failed to drop {item.name}.", self)
                message_action.setEnabled(False)
                error_menu.addAction(message_action)
                
                error_menu.addSeparator()
                
                ok_action = QAction("OK", self)
                ok_action.triggered.connect(error_menu.close)
                error_menu.addAction(ok_action)
                
                cursor_pos = QCursor.pos()
                error_menu.exec_(cursor_pos)
        except Exception as e:
            self.logger.error(f"Error dropping item: {e}")
            # Use menu-based error reporting
            try:
                from PySide6.QtWidgets import QApplication, QMenu
                from PySide6.QtGui import QCursor, QAction
                
                main_window = QApplication.activeWindow()
                error_menu = QMenu(main_window if main_window else self)
                
                title_action = QAction("Error", self)
                title_action.setEnabled(False)
                font = title_action.font()
                font.setBold(True)
                title_action.setFont(font)
                error_menu.addAction(title_action)
                
                message_action = QAction(f"An error occurred: {str(e)}", self)
                message_action.setEnabled(False)
                error_menu.addAction(message_action)
                
                error_menu.addSeparator()
                
                ok_action = QAction("OK", self)
                ok_action.triggered.connect(error_menu.close)
                error_menu.addAction(ok_action)
                
                cursor_pos = QCursor.pos()
                error_menu.exec_(cursor_pos)
            except:
                print(f"Critical error in confirm drop: {e}")
    
    def _format_currency(self, copper_value: int) -> str:
        """Format copper value into gold/silver/copper string"""
        try:
            gold = copper_value // 10000
            silver = (copper_value % 10000) // 100
            copper = copper_value % 100
            
            parts = []
            if gold > 0:
                parts.append(f"{gold}g")
            if silver > 0 or gold > 0:
                parts.append(f"{silver}s")
            parts.append(f"{copper}c")
            
            return " ".join(parts)
        except Exception:
            return str(copper_value)
    
    def _add_to_context(self, message: str):
        """Add inventory action to game context"""
        # Try to find the game manager
        gm = None
        if hasattr(self, 'parent') and hasattr(self.parent(), 'gm'):
            gm = self.parent().gm
        
        if gm and hasattr(gm, 'state_manager') and gm.state_manager.state:
            # Add to conversation history
            gm.state_manager.add_conversation_entry("System", f"Inventory: {message}")
            
            # If context manager exists, add memory
            if hasattr(gm.state_manager, 'context_manager'):
                from core.memory.enums import ContextType
                gm.state_manager.context_manager.add_memory(
                    content=message,
                    context_type=ContextType.INVENTORY,
                    importance=0.5,
                    tags=["inventory", "item"]
                )