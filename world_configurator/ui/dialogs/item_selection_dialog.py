# world_configurator/ui/dialogs/item_selection_dialog.py
"""
Dialog for selecting items from a filterable, sortable list.
"""

import logging
import os
import json
from typing import List, Dict, Optional, Set, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox, QLabel, QMessageBox
)

from ui.dialogs.base_dialog import BaseDialog
from utils.file_manager import get_project_root, load_json

logger = logging.getLogger("world_configurator.ui.item_selection_dialog")

class ItemSelectionDialog(BaseDialog):
    """
    A dialog that allows users to select items from a list.
    The list is populated from a specified JSON file, supports filtering, sorting,
    and pre-checks existing items.
    """

    def __init__(self, parent: Optional[QWidget] = None,
                 existing_item_ids: Optional[List[str]] = None,
                 item_file_path: str = "config/items/origin_items.json"):
        super().__init__(parent)
        self.setWindowTitle("Select Items")
        self.setMinimumWidth(450)
        self.setMinimumHeight(500)

        self.all_items: Dict[str, Dict[str, Any]] = {}  # Stores item_id: {name, description, ...}
        self.selected_item_ids: Set[str] = set(existing_item_ids) if existing_item_ids else set()
        self.item_file_path_relative = item_file_path # Store relative path for logging

        self._load_items_data(item_file_path)
        self._setup_ui()
        self._populate_item_list()

    def _load_items_data(self, relative_item_file_path: str):
        """Load items from the specified JSON file."""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            full_item_file_path = os.path.join(project_root, relative_item_file_path)

            if not os.path.exists(full_item_file_path):
                logger.error(f"Item file not found at: {full_item_file_path}")
                QMessageBox.critical(self, "Error", f"Could not find item file: {relative_item_file_path}")
                return

            data = load_json(full_item_file_path) # load_json expects a list of items for these files
            if data and isinstance(data, list):
                for item_data in data:
                    item_id = item_data.get("id")
                    item_name = item_data.get("name")
                    if item_id and item_name:
                        self.all_items[item_id] = item_data
                    else:
                        logger.warning(f"Item entry missing 'id' or 'name' in {relative_item_file_path}. Entry: {item_data}")
            else:
                logger.warning(f"Item data is not a list or is empty in {relative_item_file_path}")
        except Exception as e:
            logger.error(f"Error loading items data from {relative_item_file_path}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred while loading items from {relative_item_file_path}: {str(e)}")

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)

        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter items by name or ID...")
        self.filter_edit.textChanged.connect(self._filter_items)
        filter_layout.addWidget(self.filter_edit)
        layout.addLayout(filter_layout)

        # Sorting
        sort_layout = QHBoxLayout()
        self.sort_asc_button = QPushButton("Sort A-Z")
        self.sort_asc_button.clicked.connect(lambda: self.item_list_widget.sortItems(Qt.AscendingOrder))
        sort_layout.addWidget(self.sort_asc_button)

        self.sort_desc_button = QPushButton("Sort Z-A")
        self.sort_desc_button.clicked.connect(lambda: self.item_list_widget.sortItems(Qt.DescendingOrder))
        sort_layout.addWidget(self.sort_desc_button)
        sort_layout.addStretch()
        layout.addLayout(sort_layout)

        # Item list
        self.item_list_widget = QListWidget()
        self.item_list_widget.setSelectionMode(QListWidget.NoSelection) # Checkboxes handle selection
        layout.addWidget(self.item_list_widget)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _populate_item_list(self):
        """Populate the item list widget with checkboxes."""
        self.item_list_widget.clear()
        sorted_item_ids = sorted(self.all_items.keys(), key=lambda item_id: self.all_items[item_id].get("name", item_id))

        for item_id in sorted_item_ids:
            item_data = self.all_items[item_id]
            display_name = item_data.get("name", item_id)
            item_type = item_data.get("item_type", "unknown")
            list_display_text = f"{display_name} (ID: {item_id}, Type: {item_type})"

            item = QListWidgetItem(list_display_text)
            item.setData(Qt.UserRole, item_id) # Store the item_id
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            if item_id in self.selected_item_ids:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.item_list_widget.addItem(item)

    def _filter_items(self, text: str):
        """Filter the item list based on input text."""
        for i in range(self.item_list_widget.count()):
            item = self.item_list_widget.item(i)
            # Filter by display text (which includes name, ID, and type)
            if text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _on_accept(self):
        """Update the selected_item_ids set before accepting."""
        self.selected_item_ids.clear()
        for i in range(self.item_list_widget.count()):
            item = self.item_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                self.selected_item_ids.add(item.data(Qt.UserRole)) # Store item_id
        self.accept()

    def get_selected_item_ids(self) -> List[str]:
        """
        Return a list of the IDs of the selected items.
        This is called after the dialog is accepted.
        """
        return sorted(list(self.selected_item_ids))