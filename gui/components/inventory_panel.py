#!/usr/bin/env python3
"""
Inventory panel widget for the RPG game GUI.
This module provides a widget for displaying and interacting with the player's inventory.
"""

import logging
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, 
    QScrollArea, QFrame, QGroupBox, QListWidget, QListWidgetItem,
    QPushButton, QMenu, QToolButton, QSizePolicy, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QPixmap, QIcon, QCursor, QColor

from core.inventory.item_manager import get_inventory_manager
from core.inventory.item_enums import ItemType
from core.utils.logging_config import get_logger

logger = get_logger("INVENTORY")

class InventoryPanelWidget(QScrollArea):
    """Widget for displaying and interacting with inventory."""
    
    # Signals for inventory actions
    item_use_requested = Signal(str)
    item_examine_requested = Signal(str)
    item_equip_requested = Signal(str)
    item_unequip_requested = Signal(str)
    item_drop_requested = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the inventory panel widget."""
        super().__init__(parent)
        
        # Set up the scroll area
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #2D2D30;
                border: none;
            }
        """)
        
        # Create the main widget
        self.inventory_widget = QWidget()
        self.setWidget(self.inventory_widget)
        
        # Initialize item list
        self.items = []
        
        # Set up the UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        self.main_layout = QVBoxLayout(self.inventory_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(15)
        
        # Create inventory header
        self._create_header()
        
        # Create item list section
        self._create_item_list()
        
        # Create item details section
        self._create_item_details()
    
    def _create_header(self):
        """Create the inventory header section."""
        # Create header layout
        header_layout = QHBoxLayout()
        
        # Create currency group
        currency_group = QGroupBox("Currency")
        currency_group.setStyleSheet("""
            QGroupBox {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                color: #E0E0E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
            }
        """)
        
        currency_layout = QHBoxLayout(currency_group)
        
        # Create labels for currency
        gold_label = QLabel("Gold:")
        gold_label.setStyleSheet("color: #FFD700; font-weight: bold;")
        self.gold_value = QLabel("0")
        self.gold_value.setStyleSheet("color: #FFD700;")
        
        silver_label = QLabel("Silver:")
        silver_label.setStyleSheet("color: #C0C0C0; font-weight: bold;")
        self.silver_value = QLabel("0")
        self.silver_value.setStyleSheet("color: #C0C0C0;")
        
        copper_label = QLabel("Copper:")
        copper_label.setStyleSheet("color: #B87333; font-weight: bold;")
        self.copper_value = QLabel("0")
        self.copper_value.setStyleSheet("color: #B87333;")
        
        # Add currency labels to layout
        currency_layout.addWidget(gold_label)
        currency_layout.addWidget(self.gold_value)
        currency_layout.addWidget(silver_label)
        currency_layout.addWidget(self.silver_value)
        currency_layout.addWidget(copper_label)
        currency_layout.addWidget(self.copper_value)
        
        # Create weight group
        weight_group = QGroupBox("Weight")
        weight_group.setStyleSheet("""
            QGroupBox {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                color: #E0E0E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
            }
        """)
        
        weight_layout = QHBoxLayout(weight_group)
        
        # Create labels for weight
        current_weight_label = QLabel("Current:")
        current_weight_label.setStyleSheet("color: #BBBBBB; font-weight: bold;")
        self.current_weight_value = QLabel("0.0")
        self.current_weight_value.setStyleSheet("color: #E0E0E0;")
        
        max_weight_label = QLabel("Max:")
        max_weight_label.setStyleSheet("color: #BBBBBB; font-weight: bold;")
        self.max_weight_value = QLabel("50.0")
        self.max_weight_value.setStyleSheet("color: #E0E0E0;")
        
        # Add weight labels to layout
        weight_layout.addWidget(current_weight_label)
        weight_layout.addWidget(self.current_weight_value)
        weight_layout.addWidget(max_weight_label)
        weight_layout.addWidget(self.max_weight_value)
        
        # Add groups to header layout
        header_layout.addWidget(currency_group)
        header_layout.addWidget(weight_group)
        
        # Add header layout to main layout
        self.main_layout.addLayout(header_layout)
    
    def _create_item_list(self):
        """Create the item list section."""
        # Create item list group
        item_list_group = QGroupBox("Items")
        item_list_group.setStyleSheet("""
            QGroupBox {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                color: #E0E0E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
            }
        """)
        
        item_list_layout = QVBoxLayout(item_list_group)
        
        # Create filter layout
        filter_layout = QHBoxLayout()
        
        # Create filter combobox
        filter_label = QLabel("Type:")
        filter_label.setStyleSheet("color: #BBBBBB;")
        
        self.filter_combo = QComboBox()
        # Populate from ItemType enum; store enum value as userData, None for All
        self.filter_combo.addItem("All", None)
        for itype in ItemType:
            label = itype.value.replace('_', ' ').title()
            self.filter_combo.addItem(label, itype.value)
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
            }
            QComboBox::drop-down {
                border: none;
                border-left: 1px solid #555555;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2D30;
                color: #E0E0E0;
                selection-background-color: #0E639C;
            }
        """)
        
        # Add a name search field
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #BBBBBB;")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to filter by item name...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        # Connect filter changes
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.search_edit.textChanged.connect(self._on_filter_changed)
        
        # Add filter components to layout
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addWidget(search_label)
        filter_layout.addWidget(self.search_edit, 1)
        
        # Create item list
        self.item_list = QListWidget()
        self.item_list.setStyleSheet("""
            QListWidget {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 3px;
                alternate-background-color: #383838;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #444444;
            }
            QListWidget::item:selected {
                background-color: #0E639C;
            }
            QListWidget::item:hover {
                background-color: #383838;
            }
        """)
        self.item_list.setAlternatingRowColors(True)
        self.item_list.setSelectionMode(QListWidget.SingleSelection)
        
        # Add the filter layout and item list to the item list layout
        item_list_layout.addLayout(filter_layout)
        item_list_layout.addWidget(self.item_list)
        
        # Create action buttons layout (for Use, Examine, Equip, Drop)
        action_button_layout = QHBoxLayout()
        action_button_layout.setSpacing(5)
        
        # Style for buttons
        button_style = """
            QPushButton {
                background-color: #333333;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 10px;
                min-height: 25px; /* Ensure consistent height */
            }
            QPushButton:hover {
                background-color: #444444;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #222222;
                border-color: #777777;
            }
            QPushButton:disabled {
                background-color: #2A2A2A;
                color: #666666;
                border-color: #444444;
            }
        """
        
        # Create action buttons
        self.use_button = QPushButton("Use")
        self.use_button.setStyleSheet(button_style)
        self.use_button.clicked.connect(self._on_use_clicked)
        
        self.examine_button = QPushButton("Examine")
        self.examine_button.setStyleSheet(button_style)
        self.examine_button.clicked.connect(self._on_examine_clicked)
        
        self.equip_button = QPushButton("Equip")
        self.equip_button.setStyleSheet(button_style)
        self.equip_button.clicked.connect(self._on_equip_clicked)
        
        self.drop_button = QPushButton("Drop")
        self.drop_button.setStyleSheet(button_style)
        self.drop_button.clicked.connect(self._on_drop_clicked)
        
        # Disable buttons initially
        self.use_button.setEnabled(False)
        self.examine_button.setEnabled(False)
        self.equip_button.setEnabled(False)
        self.drop_button.setEnabled(False)
        
        # Add buttons to button layout
        action_button_layout.addWidget(self.use_button)
        action_button_layout.addWidget(self.examine_button)
        action_button_layout.addWidget(self.equip_button)
        action_button_layout.addWidget(self.drop_button)
        
        # Add action button layout to item list layout
        item_list_layout.addLayout(action_button_layout)

        # Create and add the "Collect Dropped Items" button
        self.collect_items_button = self._create_collect_items_button()
        item_list_layout.addWidget(self.collect_items_button)
        
        # Add item list group to main layout
        self.main_layout.addWidget(item_list_group)
        
        # Connect item selection signal
        self.item_list.itemSelectionChanged.connect(self._on_item_selection_changed)
        
        # Connect right-click context menu
        self.item_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self._show_context_menu)
        
    def _on_filter_changed(self):
        """Refresh the displayed inventory when filter changes."""
        try:
            inv_manager = get_inventory_manager()
            self.update_inventory(inv_manager)
        except Exception:
            # Safe fallback if inventory not available yet
            pass
        
    def _create_item_details(self):
        """Create the item details section."""
        # Create item details group
        item_details_group = QGroupBox("Item Details")
        item_details_group.setStyleSheet("""
            QGroupBox {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                color: #E0E0E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
            }
        """)
        
        item_details_layout = QVBoxLayout(item_details_group)
        
        # Create labels for item details
        self.item_name_label = QLabel("No item selected")
        self.item_name_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #E0E0E0;")
        
        self.item_type_label = QLabel("")
        self.item_type_label.setStyleSheet("font-size: 12pt; color: #CCCCCC;")
        
        self.item_description_label = QLabel("")
        self.item_description_label.setStyleSheet("color: #BBBBBB;")
        self.item_description_label.setWordWrap(True)
        
        # Add labels to item details layout
        item_details_layout.addWidget(self.item_name_label)
        item_details_layout.addWidget(self.item_type_label)
        item_details_layout.addWidget(self.item_description_label)
        
        # Create stats layout
        stats_layout = QGridLayout()
        
        # Add stats layout to item details layout
        item_details_layout.addLayout(stats_layout)
        
        # Add item details group to main layout
        self.main_layout.addWidget(item_details_group)
        
        # Add a stretch to push everything up
        self.main_layout.addStretch(1)
    
    def _on_item_selection_changed(self):
        """Handle item selection change."""
        logger.info("[INVENTORY] _on_item_selection_changed called.")
        selected_list_items = self.item_list.selectedItems()
        
        if not selected_list_items:
            logger.info("[INVENTORY] No item selected in QListWidget.")
            self.use_button.setEnabled(False)
            self.examine_button.setEnabled(False)
            self.equip_button.setEnabled(False)
            self.drop_button.setEnabled(False)
            self.item_name_label.setText("No item selected")
            self.item_type_label.setText("")
            self.item_description_label.setText("")
            logger.info("[INVENTORY] Buttons disabled, details cleared.")
            return
        
        list_item = selected_list_items[0]
        selected_item_id = list_item.data(Qt.UserRole) # Retrieve item_id
        logger.info(f"[INVENTORY] QListWidget selected item_id: {selected_item_id}")

        # Find the corresponding item dict in self.items (list of dicts)
        selected_item_dict = None
        for item_d in self.items:
            if item_d['id'] == selected_item_id:
                selected_item_dict = item_d
                break
        
        if not selected_item_dict:
            logger.error(f"[INVENTORY] CRITICAL: Selected item ID {selected_item_id} not found in internal self.items list. This should not happen if update_inventory is correct.")
            # Clear details and disable buttons as a fallback
            self.use_button.setEnabled(False); self.examine_button.setEnabled(False)
            self.equip_button.setEnabled(False); self.drop_button.setEnabled(False)
            self.item_name_label.setText("Error: Item not found"); self.item_type_label.setText(""); self.item_description_label.setText("")
            logger.info("[INVENTORY] Buttons disabled due to item not found in self.items.")
            return

        logger.info(f"[INVENTORY] Found item in self.items: {selected_item_dict.get('name')}")
        self.examine_button.setEnabled(True)
        self.drop_button.setEnabled(True)
        
        item_type_val = selected_item_dict.get('type', 'miscellaneous')
        is_equipped_val = selected_item_dict.get('equipped', False)

        can_use = item_type_val == 'consumable'
        self.use_button.setEnabled(can_use)
        
        can_be_equipped = item_type_val in ['weapon', 'armor', 'shield', 'accessory']
        if can_be_equipped:
            self.equip_button.setEnabled(True)
            self.equip_button.setText("Unequip" if is_equipped_val else "Equip")
        else:
            self.equip_button.setEnabled(False)
            self.equip_button.setText("Equip") 
        
        logger.info(f"[INVENTORY] Button states: Examine={self.examine_button.isEnabled()}, Drop={self.drop_button.isEnabled()}, Use={self.use_button.isEnabled()}, Equip={self.equip_button.isEnabled()} (Text: {self.equip_button.text()})")
            
        self.item_name_label.setText(selected_item_dict.get('name', 'Unknown Item'))
        self.item_type_label.setText(f"Type: {item_type_val.capitalize()}")
        
        inv_manager = get_inventory_manager() 
        full_item_obj = inv_manager.get_item(selected_item_id)
        if full_item_obj:
            self.item_description_label.setText(getattr(full_item_obj, 'description', 'No description available.'))
        else:
            self.item_description_label.setText(selected_item_dict.get('description', 'No description available.'))
            logger.warning(f"[INVENTORY] Could not fetch full Item object for ID {selected_item_id} to display description.")
            
    def _show_context_menu(self, position):
        """Show the context menu for the item list."""
        list_widget_item = self.item_list.itemAt(position)
        if not list_widget_item:
            return
        
        selected_item_id = list_widget_item.data(Qt.UserRole)
        if not selected_item_id:
            logger.warning("[INVENTORY] Context menu triggered on item with no ID.")
            return

        # Find the item dict in self.items to get its properties like type and equipped status
        item_dict = next((it_d for it_d in self.items if it_d['id'] == selected_item_id), None)
        if not item_dict:
            logger.error(f"[INVENTORY] Context menu: Item ID {selected_item_id} not found in internal self.items list.")
            return
        
        item_type_val = item_dict.get('type', 'miscellaneous')
        is_equipped_val = item_dict.get('equipped', False)
        item_name_for_log = item_dict.get('name', 'Unknown Item')

        logger.info(f"[INVENTORY] Showing context menu for item: '{item_name_for_log}' (ID: {selected_item_id})")

        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D30;
                color: #E0E0E0;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #0E639C;
            }
        """)
        
        examine_action = context_menu.addAction("Examine")
        use_action = None
        if item_type_val == 'consumable':
            use_action = context_menu.addAction("Use")
        
        equip_action = None
        can_be_equipped = item_type_val in ['weapon', 'armor', 'shield', 'accessory']
        if can_be_equipped:
            equip_action_text = "Unequip" if is_equipped_val else "Equip"
            equip_action = context_menu.addAction(equip_action_text)
        
        drop_action = context_menu.addAction("Drop")
        
        action = context_menu.exec_(QCursor.pos())
        
        if action == examine_action:
            logger.info(f"[INVENTORY] Context menu: Examine selected for {selected_item_id}")
            self.item_examine_requested.emit(selected_item_id)
        elif use_action and action == use_action:
            logger.info(f"[INVENTORY] Context menu: Use selected for {selected_item_id}")
            self.item_use_requested.emit(selected_item_id)
        elif equip_action and action == equip_action:
            if is_equipped_val:
                logger.info(f"[INVENTORY] Context menu: Unequip selected for {selected_item_id}")
                self.item_unequip_requested.emit(selected_item_id) 
            else:
                logger.info(f"[INVENTORY] Context menu: Equip selected for {selected_item_id}")
                self.item_equip_requested.emit(selected_item_id)
        elif action == drop_action:
            logger.info(f"[INVENTORY] Context menu: Drop selected for {selected_item_id}")
            self.item_drop_requested.emit(selected_item_id)
        else:
            logger.debug(f"[INVENTORY] Context menu dismissed or unknown action for {selected_item_id}")
            
    def _on_use_clicked(self):
        """Handle use button click."""
        logger.info("[INVENTORY] _on_use_clicked called.")
        selected_list_items = self.item_list.selectedItems()
        if not selected_list_items: 
            logger.warning("[INVENTORY] Use clicked, but no item selected.")
            return
        selected_item_id = selected_list_items[0].data(Qt.UserRole)
        if selected_item_id:
            logger.info(f"[INVENTORY] Emitting item_use_requested for item ID: {selected_item_id}")
            self.item_use_requested.emit(selected_item_id)
        else:
            logger.warning("[INVENTORY] Use clicked, selected item has no ID.")
    
    def _on_examine_clicked(self):
        """Handle examine button click."""
        logger.info("[INVENTORY] _on_examine_clicked called.")
        selected_list_items = self.item_list.selectedItems()
        if not selected_list_items: 
            logger.warning("[INVENTORY] Examine clicked, but no item selected.")
            return
        selected_item_id = selected_list_items[0].data(Qt.UserRole)
        if selected_item_id:
            logger.info(f"[INVENTORY] Emitting item_examine_requested for item ID: {selected_item_id}")
            self.item_examine_requested.emit(selected_item_id)
        else:
            logger.warning("[INVENTORY] Examine clicked, selected item has no ID.")
    
    def _on_equip_clicked(self):
        """Handle equip/unequip button click."""
        logger.info("[INVENTORY] _on_equip_clicked called.")
        selected_list_items = self.item_list.selectedItems()
        if not selected_list_items: 
            logger.warning("[INVENTORY] Equip/Unequip clicked, but no item selected.")
            return
        
        selected_item_id = selected_list_items[0].data(Qt.UserRole)
        if not selected_item_id: 
            logger.warning("[INVENTORY] Equip/Unequip clicked, selected item has no ID.")
            return

        item_dict = next((it_d for it_d in self.items if it_d['id'] == selected_item_id), None)
        if not item_dict: 
            logger.error(f"[INVENTORY] Equip/Unequip clicked, but item ID {selected_item_id} not found in self.items.")
            return

        # Directly emit signals, MainWindow will handle mechanically
        if item_dict.get('equipped', False):
            logger.info(f"[INVENTORY] Emitting item_unequip_requested for item ID: {selected_item_id} (from button)")
            self.item_unequip_requested.emit(selected_item_id) 
        else:
            logger.info(f"[INVENTORY] Emitting item_equip_requested for item ID: {selected_item_id} (from button)")
            self.item_equip_requested.emit(selected_item_id)

    def _on_unequip_clicked(self):
        """Handle unequip button click."""
        self._get_selected_item_id(self.item_unequip_requested)
    
    def _on_drop_clicked(self):
        """Handle drop button click."""
        logger.info("[INVENTORY] _on_drop_clicked called.")
        selected_list_items = self.item_list.selectedItems()
        if not selected_list_items: 
            logger.warning("[INVENTORY] Drop clicked, but no item selected.")
            return
        selected_item_id = selected_list_items[0].data(Qt.UserRole)
        if selected_item_id:
            logger.info(f"[INVENTORY] Emitting item_drop_requested for item ID: {selected_item_id}")
            self.item_drop_requested.emit(selected_item_id)
        else:
            logger.warning("[INVENTORY] Drop clicked, selected item has no ID.")
    
    def _get_selected_item_id(self, signal):
        """Get the selected item ID and emit the signal."""
        # Get the selected item
        selected_items = self.item_list.selectedItems()
        
        if not selected_items:
            return
        
        # Get the item data
        item_index = self.item_list.row(selected_items[0])
        item = self.items[item_index]
        
        # Emit the signal with the item ID
        signal.emit(item.get('id', ''))
    
    def update_inventory(self, inventory_manager_instance: Optional[Any]): # Renamed for clarity
        """Update the inventory panel with inventory data.
        
        Args:
            inventory_manager_instance: The InventoryManager instance.
        """
        # Temporarily disconnect the signal to prevent issues during list update
        try:
            self.item_list.itemSelectionChanged.disconnect(self._on_item_selection_changed)
            logger.debug("InventoryPanelWidget: Disconnected itemSelectionChanged for update.")
        except (TypeError, RuntimeError):  # Catch if not connected or other Qt errors
            logger.debug("InventoryPanelWidget: itemSelectionChanged was not connected or error on disconnect.")
            pass 

        if not inventory_manager_instance:
            self.gold_value.setText("0")
            self.silver_value.setText("0")
            self.copper_value.setText("0")
            self.current_weight_value.setText("0.0")
            self.max_weight_value.setText("0.0") 
            self.item_list.clear()
            self.items = [] 
            # Reconnect the signal after clearing and before manual trigger
            self.item_list.itemSelectionChanged.connect(self._on_item_selection_changed)
            logger.debug("InventoryPanelWidget: Reconnected itemSelectionChanged after clear (no inventory manager).")
            self._on_item_selection_changed() 
            logger.warning("InventoryPanelWidget.update_inventory called with no InventoryManager instance.")
            return

        inv_manager = inventory_manager_instance
        logger.info(f"InventoryPanelWidget: Updating with InventoryManager instance ID: {getattr(inv_manager, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}")


        if hasattr(inv_manager, 'currency') and inv_manager.currency:
            currency_obj = inv_manager.currency
            self.gold_value.setText(str(getattr(currency_obj, 'gold', 0)))
            self.silver_value.setText(str(getattr(currency_obj, 'silver', 0)))
            total_copper_val = getattr(currency_obj, '_copper', 0) 
            copper_per_silver_val = getattr(currency_obj, '_copper_per_silver', 100)
            self.copper_value.setText(str(total_copper_val % copper_per_silver_val))
        else:
            self.gold_value.setText("0")
            self.silver_value.setText("0")
            self.copper_value.setText("0")

        current_weight = getattr(inv_manager, 'get_current_weight', lambda: 0.0)()
        weight_limit = getattr(inv_manager, 'weight_limit', 0.0)
        self.current_weight_value.setText(f"{current_weight:.1f}")
        self.max_weight_value.setText(f"{weight_limit:.1f}")
        
        self.items = [] 
        self.item_list.clear()

        actual_item_objects = getattr(inv_manager, 'items', []) 
        
        logger.debug(f"InventoryPanel: Found {len(actual_item_objects)} item objects from InventoryManager instance {getattr(inv_manager, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}.")

        for item_obj in actual_item_objects:
            if not hasattr(item_obj, 'id') or not hasattr(item_obj, 'name') or not hasattr(item_obj, 'item_type'):
                logger.warning(f"InventoryPanel: Skipping item object due to missing attributes: {item_obj}")
                continue

            is_equipped_flag = False
            if hasattr(inv_manager, 'is_item_equipped'):
                is_equipped_flag = inv_manager.is_item_equipped(item_obj.id)
            
            gui_item_dict = {
                'id': item_obj.id,
                'name': item_obj.name,
                'type': item_obj.item_type.value.lower() if hasattr(item_obj.item_type, 'value') else str(item_obj.item_type).lower(),
                'description': getattr(item_obj, 'description', ''),
                'count': getattr(item_obj, 'quantity', 1),
                'equipped': is_equipped_flag,
            }
            self.items.append(gui_item_dict) 

            # Unified filter: type (from ItemType) AND name query
            selected_type = self.filter_combo.currentData() if hasattr(self, 'filter_combo') else None
            item_type_for_filter = gui_item_dict.get('type', '').lower()
            name_query = (self.search_edit.text().strip().lower() if hasattr(self, 'search_edit') and self.search_edit else '')

            type_match = (selected_type is None) or (item_type_for_filter == str(selected_type).lower())
            item_name_display = gui_item_dict.get('name', 'Unknown Item')
            name_match = (not name_query) or (name_query in item_name_display.lower())

            if type_match and name_match:
                item_count_display = gui_item_dict.get('count', 1)
                list_widget_item = QListWidgetItem()
                display_text = item_name_display
                if item_count_display > 1 and getattr(item_obj, 'is_stackable', False):
                    display_text += f" ({item_count_display})"
                if gui_item_dict.get('equipped', False):
                    display_text += " (Equipped)"
                    list_widget_item.setForeground(QColor('#4CAF50')) 
                list_widget_item.setText(display_text)
                list_widget_item.setData(Qt.UserRole, gui_item_dict['id']) 
                self.item_list.addItem(list_widget_item)
        
        # Reconnect the signal and manually trigger update for item details
        self.item_list.itemSelectionChanged.connect(self._on_item_selection_changed)
        logger.debug("InventoryPanelWidget: Reconnected itemSelectionChanged after repopulation.")
        self._on_item_selection_changed() # Manually trigger to update details for the current selection (or no selection)

        logger.info(f"InventoryPanel updated with manager {getattr(inv_manager, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}. Displaying {self.item_list.count()} items after filter. Internal self.items count: {len(self.items)}.")
        """Update the inventory panel with inventory data.
        
        Args:
            inventory_manager_instance: The InventoryManager instance.
        """
        if not inventory_manager_instance:
            self.gold_value.setText("0")
            self.silver_value.setText("0")
            self.copper_value.setText("0")
            self.current_weight_value.setText("0.0")
            self.max_weight_value.setText("0.0") 
            self.item_list.clear()
            self.items = [] 
            self._on_item_selection_changed() 
            logger.warning("InventoryPanelWidget.update_inventory called with no InventoryManager instance.")
            return

        inv_manager = inventory_manager_instance
        logger.info(f"InventoryPanelWidget: Updating with InventoryManager instance ID: {getattr(inv_manager, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}")


        if hasattr(inv_manager, 'currency') and inv_manager.currency:
            currency_obj = inv_manager.currency
            self.gold_value.setText(str(getattr(currency_obj, 'gold', 0)))
            self.silver_value.setText(str(getattr(currency_obj, 'silver', 0)))
            total_copper_val = getattr(currency_obj, '_copper', 0) 
            copper_per_silver_val = getattr(currency_obj, '_copper_per_silver', 100)
            self.copper_value.setText(str(total_copper_val % copper_per_silver_val))
        else:
            self.gold_value.setText("0")
            self.silver_value.setText("0")
            self.copper_value.setText("0")

        current_weight = getattr(inv_manager, 'get_current_weight', lambda: 0.0)()
        weight_limit = getattr(inv_manager, 'weight_limit', 0.0)
        self.current_weight_value.setText(f"{current_weight:.1f}")
        self.max_weight_value.setText(f"{weight_limit:.1f}")
        
        self.items = [] 
        self.item_list.clear()

        actual_item_objects = getattr(inv_manager, 'items', []) 
        
        logger.debug(f"InventoryPanel: Found {len(actual_item_objects)} item objects from InventoryManager instance {getattr(inv_manager, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}.")

        for item_obj in actual_item_objects:
            if not hasattr(item_obj, 'id') or not hasattr(item_obj, 'name') or not hasattr(item_obj, 'item_type'):
                logger.warning(f"InventoryPanel: Skipping item object due to missing attributes: {item_obj}")
                continue

            is_equipped_flag = False
            if hasattr(inv_manager, 'is_item_equipped'):
                is_equipped_flag = inv_manager.is_item_equipped(item_obj.id)
            
            gui_item_dict = {
                'id': item_obj.id,
                'name': item_obj.name,
                'type': item_obj.item_type.value.lower() if hasattr(item_obj.item_type, 'value') else str(item_obj.item_type).lower(),
                'description': getattr(item_obj, 'description', ''),
                'count': getattr(item_obj, 'quantity', 1),
                'equipped': is_equipped_flag,
            }
            self.items.append(gui_item_dict) 

            # Unified filter: type (from ItemType) AND name query
            selected_type = self.filter_combo.currentData() if hasattr(self, 'filter_combo') else None
            item_type_for_filter = gui_item_dict.get('type', '').lower()
            name_query = (self.search_edit.text().strip().lower() if hasattr(self, 'search_edit') and self.search_edit else '')

            type_match = (selected_type is None) or (item_type_for_filter == str(selected_type).lower())
            item_name_display = gui_item_dict.get('name', 'Unknown Item')
            name_match = (not name_query) or (name_query in item_name_display.lower())

            if type_match and name_match:
                item_count_display = gui_item_dict.get('count', 1)
                list_widget_item = QListWidgetItem()
                display_text = item_name_display
                if item_count_display > 1 and getattr(item_obj, 'is_stackable', False):
                    display_text += f" ({item_count_display})"
                if gui_item_dict.get('equipped', False):
                    display_text += " (Equipped)"
                    list_widget_item.setForeground(QColor('#4CAF50')) 
                list_widget_item.setText(display_text)
                list_widget_item.setData(Qt.UserRole, gui_item_dict['id']) 
                self.item_list.addItem(list_widget_item)
        
        self._on_item_selection_changed()
        logger.info(f"InventoryPanel updated with manager {getattr(inv_manager, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}. Displaying {self.item_list.count()} items after filter. Internal self.items count: {len(self.items)}.")

    def _create_collect_items_button(self):
        """Creates the 'Collect Items' button."""
        self.collect_button = QPushButton("Collect Dropped Items")
        self.collect_button.setStyleSheet(self.use_button.styleSheet()) # Reuse style
        self.collect_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) # Expand horizontally
        self.collect_button.clicked.connect(self._on_collect_items_clicked)
        self.collect_button.setEnabled(True) # Assuming always enabled, logic can be added if needed
        return self.collect_button
    
    def _on_collect_items_clicked(self):
        """Handle the 'Collect Dropped Items' button click."""
        logger.info("[INVENTORY] Collect Dropped Items button clicked.")
        # This is where the dialog for showing dropped items at the current location would be displayed.
        # For now, let's log and maybe show a placeholder message.
        
        # Placeholder for actual dialog:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Collect Items", "Functionality to show and collect dropped items at this location is not yet implemented.")
        
        # Future implementation would involve:
        # 1. Get current player location from GameState.
        # 2. Access a (new) system that tracks dropped items per location (e.g., LocationItemManager).
        # 3. Populate a dialog (e.g., DroppedItemsDialog) with these items.
        # 4. DroppedItemsDialog would have its own "Examine" and "Collect" actions.
        #    - "Collect" would move the item from the location's dropped list to player inventory.