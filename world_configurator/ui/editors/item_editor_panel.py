# world_configurator/ui/editors/item_editor_panel.py
"""
Main panel for managing different types of items.
"""

import logging
import os
from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QSplitter, QFrame, QStackedWidget, QMessageBox
)

# Placeholder for individual item category editors
# from .specific_item_editor import SpecificItemEditor # Example, will be created later

logger = logging.getLogger("world_configurator.ui.item_editor_panel")

ITEM_CATEGORIES = {
    "Starting Items": "config/items/origin_items.json",
    "Weapon Templates": "config/items/base_weapons.json",
    "Armor Templates": "config/items/base_armor.json",
    "Consumable Templates": "config/items/consumables.json",
    "Miscellaneous Templates": "config/items/miscellaneous.json"
}

class ItemEditorPanel(QWidget):
    """
    Main panel for editing various item categories.
    It features a list of item categories on the left and a
    stacked widget on the right to display the editor for the selected category.
    """
    item_data_modified = Signal(str) # Emits category name on modification

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_category_key: Optional[str] = None
        self.category_editors: Dict[str, QWidget] = {} # To store instances of specific editors

        self._setup_ui()
        self._populate_category_list()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Category list
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Item Categories"))
        self.category_list_widget = QListWidget()
        self.category_list_widget.currentItemChanged.connect(self._on_category_selected)
        left_layout.addWidget(self.category_list_widget)
        splitter.addWidget(left_panel)

        # Right panel: Stacked widget for editors
        self.editor_stack = QStackedWidget()
        # Add a default placeholder widget
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_widget)
        placeholder_label = QLabel("Select an item category to edit.")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)
        self.editor_stack.addWidget(placeholder_widget)

        splitter.addWidget(self.editor_stack)
        splitter.setSizes([200, 600]) # Initial sizes for panels

        main_layout.addWidget(splitter)

    def _populate_category_list(self):
        self.category_list_widget.clear()
        for category_name in ITEM_CATEGORIES.keys():
            item = QListWidgetItem(category_name)
            item.setData(Qt.UserRole, category_name) # Store category name as data
            self.category_list_widget.addItem(item)

        if self.category_list_widget.count() > 0:
            self.category_list_widget.setCurrentRow(0)

    @Slot(QListWidgetItem, QListWidgetItem)
    def _on_category_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if not current:
            self.editor_stack.setCurrentIndex(0) # Show placeholder
            self.current_category_key = None
            return

        category_key = current.data(Qt.UserRole) # This is the display name like "Starting Items"
        self.current_category_key = category_key

        if category_key in self.category_editors:
            self.editor_stack.setCurrentWidget(self.category_editors[category_key])
            # Optionally refresh data if needed when switching back to an existing editor
            # editor_instance = self.category_editors[category_key]
            # if hasattr(editor_instance, 'refresh_data'):
            #     editor_instance.refresh_data()
        else:
            editor_widget = self._create_editor_for_category(category_key)
            if editor_widget:
                self.category_editors[category_key] = editor_widget
                self.editor_stack.addWidget(editor_widget)
                self.editor_stack.setCurrentWidget(editor_widget)
                # Connect the specific editor's data_modified signal
                if hasattr(editor_widget, 'data_modified') and isinstance(editor_widget.data_modified, Signal):
                    # Use a lambda to pass the category_key along with the signal
                    editor_widget.data_modified.connect(
                        lambda cat_key=category_key: self.item_data_modified.emit(cat_key)
                    )
            else:
                self.editor_stack.setCurrentIndex(0)
                logger.error(f"Failed to create editor for category: {category_key}")

    def _create_editor_for_category(self, category_key: str) -> Optional[QWidget]:
        """
        Creates the appropriate editor widget for the given item category.
        This will now instantiate SpecificItemEditor for all categories.
        """
        file_path_relative = ITEM_CATEGORIES.get(category_key)
        if not file_path_relative:
            logger.error(f"No file path defined for item category: {category_key}")
            # Fallback to a placeholder if a category key is somehow unknown
            editor = QWidget()
            layout = QVBoxLayout(editor)
            label = QLabel(f"Error: No file path configured for category: {category_key}")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            return editor

        # Import SpecificItemEditor here to avoid potential circular dependencies if it were at module level
        from .SpecificItemEditor import SpecificItemEditor # Assuming it's in the same directory

        try:
            # Pass the category_key (display name from ITEM_CATEGORIES) and the relative file path
            editor = SpecificItemEditor(item_file_key=category_key, # This is the display name like "Starting Items"
                                        item_file_path_relative=file_path_relative,
                                        parent=self)
            logger.info(f"Created SpecificItemEditor for category '{category_key}' with file '{file_path_relative}'")
            
            # Connect the specific editor's data_modified signal
            if hasattr(editor, 'data_modified') and isinstance(editor.data_modified, Signal):
                # Use a lambda to pass the category_key along with the signal
                # This allows the main panel to know which category's data was modified.
                editor.data_modified.connect(
                    lambda cat_key=category_key: self.item_data_modified.emit(cat_key)
                )
            else:
                logger.warning(f"SpecificItemEditor for '{category_key}' does not have a 'data_modified' signal.")

            return editor
        except ImportError:
            logger.error(f"Could not import SpecificItemEditor. Ensure it's in the correct location.", exc_info=True)
            editor_placeholder = QWidget()
            layout_placeholder = QVBoxLayout(editor_placeholder)
            label_placeholder = QLabel(f"Error: Could not load editor for {category_key}.\nSpecificItemEditor not found.")
            label_placeholder.setAlignment(Qt.AlignCenter)
            layout_placeholder.addWidget(label_placeholder)
            return editor_placeholder
        except Exception as e:
            logger.error(f"Error creating SpecificItemEditor for {category_key}: {e}", exc_info=True)
            QMessageBox.critical(self, "Editor Creation Error",
                                 f"Could not create editor for {category_key}.\nError: {e}")
            # Return a placeholder on error
            editor_placeholder_err = QWidget()
            layout_placeholder_err = QVBoxLayout(editor_placeholder_err)
            label_placeholder_err = QLabel(f"Error creating editor for {category_key}:\n{e}")
            label_placeholder_err.setAlignment(Qt.AlignCenter)
            layout_placeholder_err.addWidget(label_placeholder_err)
            return editor_placeholder_err
 
    def refresh_current_editor(self):
        """Refreshes the data in the currently active editor."""
        if self.current_category_key and self.current_category_key in self.category_editors:
            editor = self.category_editors[self.current_category_key]
            if hasattr(editor, 'refresh_data'): # Assuming editors will have a refresh_data method
                editor.refresh_data()
            else:
                logger.warning(f"Editor for {self.current_category_key} does not have a refresh_data method.")
        elif self.current_category_key: # Editor not yet created, but category selected
            # This might happen if data is loaded before UI fully interacts
            # Triggering selection again might recreate/load it
             current_item = self.category_list_widget.currentItem()
             if current_item:
                 self._on_category_selected(current_item, None)


    def save_all_item_editors(self) -> bool:
        """Iterates through all instantiated editors and calls their save_data method."""
        all_saved = True
        if not self.category_editors:
            logger.info("No item editors have been instantiated. Nothing to save.")
            return True # No editors, so technically all (zero) saved.

        for category_key, editor_instance in self.category_editors.items():
            if hasattr(editor_instance, 'save_data') and callable(editor_instance.save_data):
                try:
                    if not editor_instance.save_data():
                        all_saved = False
                        logger.error(f"Failed to save data for item category: {category_key} via its editor.")
                    else:
                        logger.info(f"Successfully saved item category: {category_key}")
                except Exception as e:
                    all_saved = False
                    logger.error(f"Exception while saving item category {category_key}: {e}", exc_info=True)
            else:
                logger.warning(f"Editor for {category_key} does not have a callable save_data method.")
        
        if all_saved:
            logger.info("All active item editors saved successfully.")
        else:
            QMessageBox.warning(self, "Save Error", "Some item categories could not be saved. Check logs for details.")
        return all_saved

    def get_active_editor_file_path(self) -> Optional[str]:
        """Returns the file path associated with the currently active item editor."""
        if self.current_category_key:
            return ITEM_CATEGORIES.get(self.current_category_key)
        return None