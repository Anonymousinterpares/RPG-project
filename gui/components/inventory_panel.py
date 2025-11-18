#!/usr/bin/env python3
"""
Inventory panel widget for the RPG game GUI.
This module provides a widget for displaying and interacting with the player's inventory.
"""
from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, 
    QScrollArea, QGroupBox, QListWidget, QListWidgetItem,
    QPushButton, QMenu, QSizePolicy, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer, Slot
from PySide6.QtGui import QCursor, QColor

from core.inventory.item_manager import get_inventory_manager
from core.inventory.item_enums import ItemType
from core.utils.logging_config import get_logger
from gui.styles.stylesheet_factory import create_combobox_style, create_context_menu_style, create_groupbox_style, create_line_edit_style, create_list_widget_style, create_scroll_area_style, create_styled_button_style
from gui.styles.theme_manager import get_theme_manager

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
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        # Set up the scroll area
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create the main widget
        self.inventory_widget = QWidget()
        self.setWidget(self.inventory_widget)
        
        # Initialize item list
        self.items = []
        
        # Set up the UI
        self._setup_ui()
        
        # Apply initial theme
        self._update_theme()

        QTimer.singleShot(0, self._apply_cursors)

    def _apply_cursors(self):
        """Applies custom cursors to child widgets."""
        main_win = self.window()
        if not main_win:
            return

        if hasattr(main_win, 'link_cursor'):
            self.filter_combo.setCursor(main_win.link_cursor)
            if self.filter_combo.view():
                self.filter_combo.view().setCursor(main_win.link_cursor)
        
        if hasattr(main_win, 'text_cursor'):
            self.search_edit.setCursor(main_win.text_cursor)

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        
        self.setStyleSheet(create_scroll_area_style(self.palette))
        
        # GroupBoxes
        group_style = create_groupbox_style(self.palette)
        for group in self.findChildren(QGroupBox):
            group.setStyleSheet(group_style)
            
        # ListWidget
        self.item_list.setStyleSheet(create_list_widget_style(self.palette))
        
        # Buttons
        btn_style = create_styled_button_style(self.palette)
        for btn in [self.use_button, self.examine_button, self.equip_button, 
                    self.drop_button, self.collect_items_button]:
            btn.setStyleSheet(btn_style)
            
        # Inputs
        self.filter_combo.setStyleSheet(create_combobox_style(self.palette))
        self.search_edit.setStyleSheet(create_line_edit_style(self.palette))
        
        # Specific Label Colors
        # Currency
        self.gold_label.setStyleSheet("color: #FFD700; font-weight: bold;")
        self.gold_value.setStyleSheet("color: #FFD700; font-weight: 600;")
        self.silver_label.setStyleSheet("color: #C0C0C0; font-weight: bold;")
        self.silver_value.setStyleSheet("color: #C0C0C0; font-weight: 600;")
        self.copper_label.setStyleSheet("color: #B87333; font-weight: bold;")
        self.copper_value.setStyleSheet("color: #B87333; font-weight: 600;")
        
        # General Labels
        label_style = f"color: {colors['text_primary']}; font-weight: 600;"
        value_style = f"color: {colors['text_bright']};"
        
        for label in [self.current_weight_label, self.max_weight_label, self.filter_label, self.search_label]:
            label.setStyleSheet(label_style)
            
        for label in [self.current_weight_value, self.max_weight_value]:
            label.setStyleSheet(value_style)
            
        # Item Details
        self.item_name_label.setStyleSheet(f"font-size: 15pt; font-weight: bold; color: {colors['text_primary']};")
        self.item_type_label.setStyleSheet(f"font-size: 12pt; color: {colors['text_secondary']}; font-weight: 600;")
        self.item_description_label.setStyleSheet(f"color: {colors['text_bright']}; font-size: 11pt; line-height: 1.4;")

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
        currency_layout = QHBoxLayout(currency_group)
        currency_layout.setSpacing(12)
        
        # Create labels for currency (Stored as attributes for theming)
        self.gold_label = QLabel("Gold:")
        self.gold_value = QLabel("0")
        
        self.silver_label = QLabel("Silver:")
        self.silver_value = QLabel("0")
        
        self.copper_label = QLabel("Copper:")
        self.copper_value = QLabel("0")
        
        # Add currency labels to layout
        currency_layout.addWidget(self.gold_label)
        currency_layout.addWidget(self.gold_value)
        currency_layout.addWidget(self.silver_label)
        currency_layout.addWidget(self.silver_value)
        currency_layout.addWidget(self.copper_label)
        currency_layout.addWidget(self.copper_value)
        
        # Create weight group
        weight_group = QGroupBox("Weight")
        weight_layout = QHBoxLayout(weight_group)
        weight_layout.setSpacing(12)
        
        # Create labels for weight
        self.current_weight_label = QLabel("Current:")
        self.current_weight_value = QLabel("0.0")
        
        self.max_weight_label = QLabel("Max:")
        self.max_weight_value = QLabel("50.0")
        
        # Add weight labels to layout
        weight_layout.addWidget(self.current_weight_label)
        weight_layout.addWidget(self.current_weight_value)
        weight_layout.addWidget(self.max_weight_label)
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
        item_list_layout = QVBoxLayout(item_list_group)
        item_list_layout.setSpacing(10)
        
        # Create filter layout
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        # Create filter combobox
        self.filter_label = QLabel("Type:")
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All", None)
        for itype in ItemType:
            label = itype.value.replace('_', ' ').title()
            self.filter_combo.addItem(label, itype.value)
        
        # Add a name search field
        self.search_label = QLabel("Search:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to filter by item name...")
        
        # Connect filter changes
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.search_edit.textChanged.connect(self._on_filter_changed)
        
        # Add filter components to layout
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addWidget(self.search_label)
        filter_layout.addWidget(self.search_edit, 1)

        # Create item list
        self.item_list = QListWidget()
        self.item_list.setAlternatingRowColors(True)
        self.item_list.setSelectionMode(QListWidget.SingleSelection)
        
        # Add the filter layout and item list to the item list layout
        item_list_layout.addLayout(filter_layout)
        item_list_layout.addWidget(self.item_list)
        
        # Create action buttons layout
        action_button_layout = QHBoxLayout()
        action_button_layout.setSpacing(8)
        
        # Create action buttons
        self.use_button = QPushButton("Use")
        self.use_button.clicked.connect(self._on_use_clicked)
        
        self.examine_button = QPushButton("Examine")
        self.examine_button.clicked.connect(self._on_examine_clicked)
        
        self.equip_button = QPushButton("Equip")
        self.equip_button.clicked.connect(self._on_equip_clicked)
        
        self.drop_button = QPushButton("Drop")
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
            pass
        
    def _create_item_details(self):
        """Create the item details section."""
        # Create item details group
        item_details_group = QGroupBox("Item Details")
        item_details_layout = QVBoxLayout(item_details_group)
        item_details_layout.setSpacing(8)
        
        # Create labels for item details
        self.item_name_label = QLabel("No item selected")
        
        self.item_type_label = QLabel("")
        
        self.item_description_label = QLabel("")
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
            logger.error(f"[INVENTORY] CRITICAL: Selected item ID {selected_item_id} not found in internal self.items list.")
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
        
        self.item_name_label.setText(selected_item_dict.get('name', 'Unknown Item'))
        self.item_type_label.setText(f"Type: {item_type_val.capitalize()}")
        
        inv_manager = get_inventory_manager() 
        full_item_obj = inv_manager.get_item(selected_item_id)
        if full_item_obj:
            self.item_description_label.setText(getattr(full_item_obj, 'description', 'No description available.'))
        else:
            self.item_description_label.setText(selected_item_dict.get('description', 'No description available.'))
            
    def _show_context_menu(self, position):
        """Show the context menu for the item list."""
        list_widget_item = self.item_list.itemAt(position)
        if not list_widget_item:
            return
        
        selected_item_id = list_widget_item.data(Qt.UserRole)
        if not selected_item_id:
            return

        item_dict = next((it_d for it_d in self.items if it_d['id'] == selected_item_id), None)
        if not item_dict:
            return
        
        item_type_val = item_dict.get('type', 'miscellaneous')
        is_equipped_val = item_dict.get('equipped', False)

        context_menu = QMenu(self)
        # Use the factory for context menu styling
        context_menu.setStyleSheet(create_context_menu_style(self.palette))
        
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
            self.item_examine_requested.emit(selected_item_id)
        elif use_action and action == use_action:
            self.item_use_requested.emit(selected_item_id)
        elif equip_action and action == equip_action:
            if is_equipped_val:
                self.item_unequip_requested.emit(selected_item_id) 
            else:
                self.item_equip_requested.emit(selected_item_id)
        elif action == drop_action:
            self.item_drop_requested.emit(selected_item_id)

    def _on_use_clicked(self):
        """Handle use button click."""
        selected_list_items = self.item_list.selectedItems()
        if not selected_list_items: return
        selected_item_id = selected_list_items[0].data(Qt.UserRole)
        if selected_item_id:
            self.item_use_requested.emit(selected_item_id)
    
    def _on_examine_clicked(self):
        """Handle examine button click."""
        selected_list_items = self.item_list.selectedItems()
        if not selected_list_items: return
        selected_item_id = selected_list_items[0].data(Qt.UserRole)
        if selected_item_id:
            self.item_examine_requested.emit(selected_item_id)
    
    def _on_equip_clicked(self):
        """Handle equip/unequip button click."""
        selected_list_items = self.item_list.selectedItems()
        if not selected_list_items: return
        
        selected_item_id = selected_list_items[0].data(Qt.UserRole)
        if not selected_item_id: return

        item_dict = next((it_d for it_d in self.items if it_d['id'] == selected_item_id), None)
        if not item_dict: return

        if item_dict.get('equipped', False):
            self.item_unequip_requested.emit(selected_item_id) 
        else:
            self.item_equip_requested.emit(selected_item_id)

    def _on_unequip_clicked(self):
        """Handle unequip button click."""
        self._get_selected_item_id(self.item_unequip_requested)
    
    def _on_drop_clicked(self):
        """Handle drop button click."""
        selected_list_items = self.item_list.selectedItems()
        if not selected_list_items: return
        selected_item_id = selected_list_items[0].data(Qt.UserRole)
        if selected_item_id:
            self.item_drop_requested.emit(selected_item_id)
    
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
    
    def update_inventory(self, inventory_manager_instance: Optional[Any]):
        """Update the inventory panel with inventory data."""
        try:
            self.item_list.itemSelectionChanged.disconnect(self._on_item_selection_changed)
        except (TypeError, RuntimeError):
            pass 

        if not inventory_manager_instance:
            self.gold_value.setText("0")
            self.silver_value.setText("0")
            self.copper_value.setText("0")
            self.current_weight_value.setText("0.0")
            self.max_weight_value.setText("0.0") 
            self.item_list.clear()
            self.items = [] 
            self.item_list.itemSelectionChanged.connect(self._on_item_selection_changed)
            self._on_item_selection_changed() 
            return

        inv_manager = inventory_manager_instance

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
        
        for item_obj in actual_item_objects:
            if not hasattr(item_obj, 'id') or not hasattr(item_obj, 'name') or not hasattr(item_obj, 'item_type'):
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

            selected_type = self.filter_combo.currentData()
            item_type_for_filter = gui_item_dict.get('type', '').lower()
            name_query = self.search_edit.text().strip().lower()

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
                    # Use theme accent color for equipped text
                    colors = self.palette['colors']
                    list_widget_item.setForeground(QColor(colors['accent_positive'])) 
                list_widget_item.setText(display_text)
                list_widget_item.setData(Qt.UserRole, gui_item_dict['id']) 
                self.item_list.addItem(list_widget_item)
        
        self.item_list.itemSelectionChanged.connect(self._on_item_selection_changed)
        self._on_item_selection_changed()

    def _create_collect_items_button(self):
        """Creates the 'Collect Items' button."""
        self.collect_button = QPushButton("Collect Dropped Items")
        self.collect_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.collect_button.clicked.connect(self._on_collect_items_clicked)
        self.collect_button.setEnabled(True)
        return self.collect_button
    
    def _on_collect_items_clicked(self):
        """Handle the 'Collect Dropped Items' button click."""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Collect Items", "Functionality to show and collect dropped items at this location is not yet implemented.")
        
        # Future implementation would involve:
        # 1. Get current player location from GameState.
        # 2. Access a (new) system that tracks dropped items per location (e.g., LocationItemManager).
        # 3. Populate a dialog (e.g., DroppedItemsDialog) with these items.
        # 4. DroppedItemsDialog would have its own "Examine" and "Collect" actions.
        #    - "Collect" would move the item from the location's dropped list to player inventory.