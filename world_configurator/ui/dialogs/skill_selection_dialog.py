# world_configurator/ui/dialogs/skill_selection_dialog.py
"""
Dialog for selecting skills from a filterable, sortable list.
"""

import os
from typing import Any, List, Dict, Optional, Set

from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox, QLabel, QMessageBox
)

from ui.dialogs.base_dialog import BaseDialog # Assuming base_dialog.py is in gui.dialogs
from utils.file_manager import load_json
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.ui.skill_selection_dialog")

class SkillSortFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for sorting and filtering skills."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterKeyColumn(0) # Assuming skill name is in the first (and only) column

    def filterAcceptsRow(self, source_row: int, source_parent: Any) -> bool:
        # Default behavior: if filter is set, check it.
        # We'll use QListWidget's built-in text filtering for simplicity first,
        # but this proxy could be used for more complex filtering if needed.
        # For now, let QListWidget handle filtering via textChanged signal.
        # This proxy is mainly for potential future sorting if QListWidget sorting isn't enough.
        # However, QListWidget.sortItems() is often sufficient.
        # Let's ensure it passes through if no filter is set from here.
        return super().filterAcceptsRow(source_row, source_parent)


class SkillSelectionDialog(BaseDialog):
    """
    A dialog that allows users to select skills from a list.
    The list is populated from skills.json, supports filtering, sorting,
    and pre-checks existing skills.
    """

    def __init__(self, parent: Optional[QWidget] = None, existing_skills: Optional[List[str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Skill Proficiencies")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

        self.all_skills: Dict[str, Dict[str, str]] = {} # Stores skill_id: {name, ...}
        self.selected_skill_names: Set[str] = set(existing_skills) if existing_skills else set()

        self._load_skills_data()
        self._setup_ui()
        self._populate_skill_list()

    def _load_skills_data(self):
        """Load skills from skills.json."""
        try:
            # Construct path to skills.json relative to project root
            # utils/file_manager.py -> gui/dialogs (2 levels up) -> project_root
            # config is a sibling of world_configurator
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            skills_file_path = os.path.join(project_root, "config", "skills.json")

            if not os.path.exists(skills_file_path):
                logger.error(f"Skills file not found at: {skills_file_path}")
                QMessageBox.critical(self, "Error", f"Could not find skills.json at {skills_file_path}")
                return

            data = load_json(skills_file_path)
            if data and "skills" in data:
                # Store as skill_id: {name, description, ...}
                # The key in skills.json *is* the skill_id
                for skill_id, skill_data in data["skills"].items():
                    if "name" in skill_data:
                        self.all_skills[skill_id] = skill_data
                    else:
                        logger.warning(f"Skill entry '{skill_id}' missing 'name' field. Skipping.")
            else:
                logger.warning(f"No 'skills' key found or data is empty in {skills_file_path}")
        except Exception as e:
            logger.error(f"Error loading skills data: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred while loading skills: {str(e)}")


    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)

        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter skills...")
        self.filter_edit.textChanged.connect(self._filter_skills)
        filter_layout.addWidget(self.filter_edit)
        layout.addLayout(filter_layout)

        # Sorting (simple buttons for now)
        sort_layout = QHBoxLayout()
        self.sort_asc_button = QPushButton("Sort A-Z")
        self.sort_asc_button.clicked.connect(lambda: self.skill_list_widget.sortItems(Qt.AscendingOrder))
        sort_layout.addWidget(self.sort_asc_button)

        self.sort_desc_button = QPushButton("Sort Z-A")
        self.sort_desc_button.clicked.connect(lambda: self.skill_list_widget.sortItems(Qt.DescendingOrder))
        sort_layout.addWidget(self.sort_desc_button)
        sort_layout.addStretch()
        layout.addLayout(sort_layout)

        # Skill list
        self.skill_list_widget = QListWidget()
        self.skill_list_widget.setSelectionMode(QListWidget.NoSelection) # Checkboxes handle selection
        layout.addWidget(self.skill_list_widget)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _populate_skill_list(self):
        """Populate the skill list widget with checkboxes."""
        self.skill_list_widget.clear()
        # Sort by display name for initial population
        sorted_skill_ids = sorted(self.all_skills.keys(), key=lambda skill_id: self.all_skills[skill_id].get("name", skill_id))

        for skill_id in sorted_skill_ids:
            skill_data = self.all_skills[skill_id]
            display_name = skill_data.get("name", skill_id) # Use skill_id as fallback

            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, skill_id) # Store the skill_id (key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            # Check if the skill (by name or ID) is in existing_skills
            # The Origin stores skill proficiencies by their name (e.g., "Diplomacy")
            if display_name in self.selected_skill_names or skill_id in self.selected_skill_names:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.skill_list_widget.addItem(item)

    def _filter_skills(self, text: str):
        """Filter the skill list based on input text."""
        for i in range(self.skill_list_widget.count()):
            item = self.skill_list_widget.item(i)
            # Filter by display name
            if text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _on_accept(self):
        """Update the selected_skill_names set before accepting."""
        self.selected_skill_names.clear()
        for i in range(self.skill_list_widget.count()):
            item = self.skill_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                # Return the display name, as this is what's stored in Origin.skill_proficiencies
                self.selected_skill_names.add(item.text())
        self.accept()

    def get_selected_skills(self) -> List[str]:
        """
        Return a list of the display names of the selected skills.
        This is called after the dialog is accepted.
        """
        return sorted(list(self.selected_skill_names))