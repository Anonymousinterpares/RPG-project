# world_configurator/ui/editors/skills_editor.py
"""
Skills editor component for the World Configurator Tool.
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any, Tuple

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QComboBox,
    QDialog, QMessageBox, QSplitter, QScrollArea, QFrame, QDialogButtonBox
)

from ui.dialogs.base_dialog import BaseDialog # Assuming base_dialog.py is in gui.dialogs
from utils.file_manager import get_project_root, load_json, save_json

logger = logging.getLogger("world_configurator.ui.skills_editor")

# Define typical RPG stats and categories for dropdowns
PRIMARY_STATS = ["STRENGTH", "DEXTERITY", "CONSTITUTION", "INTELLIGENCE", "WISDOM", "CHARISMA", "WILLPOWER", "INSIGHT", "NONE"]
SKILL_CATEGORIES = ["COMBAT", "PHYSICAL", "MENTAL", "SOCIAL", "KNOWLEDGE", "EXPLORATION", "COVERT", "UTILITY", "MISCELLANEOUS"]


class SkillEditDialog(BaseDialog):
    """Dialog for adding or editing a skill."""
    def __init__(self, parent: Optional[QWidget] = None, skill_id: Optional[str] = None, skill_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.is_new_skill = skill_id is None
        self.skill_id = skill_id if skill_id else ""
        self.skill_data = skill_data if skill_data else {}

        self.setWindowTitle("Add New Skill" if self.is_new_skill else f"Edit Skill: {self.skill_data.get('name', self.skill_id)}")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.id_edit = QLineEdit(self.skill_id)
        self.id_edit.setPlaceholderText("Unique skill ID (e.g., stealth_forest)")
        if not self.is_new_skill:
            self.id_edit.setReadOnly(True) # ID cannot be changed once created
        form.addRow("Skill ID:", self.id_edit)

        self.name_edit = QLineEdit(self.skill_data.get("name", ""))
        self.name_edit.setPlaceholderText("Display name (e.g., Forest Stealth)")
        form.addRow("Display Name:", self.name_edit)

        self.primary_stat_combo = QComboBox()
        self.primary_stat_combo.addItems(PRIMARY_STATS)
        current_primary_stat = self.skill_data.get("primary_stat", "NONE")
        if current_primary_stat in PRIMARY_STATS:
            self.primary_stat_combo.setCurrentText(current_primary_stat)
        else:
            self.primary_stat_combo.setCurrentIndex(self.primary_stat_combo.findText("NONE"))
        form.addRow("Primary Stat:", self.primary_stat_combo)

        self.category_combo = QComboBox()
        self.category_combo.addItems(SKILL_CATEGORIES)
        current_category = self.skill_data.get("category", "MISCELLANEOUS")
        if current_category in SKILL_CATEGORIES:
            self.category_combo.setCurrentText(current_category)
        else:
            self.category_combo.setCurrentIndex(self.category_combo.findText("MISCELLANEOUS"))
        form.addRow("Category:", self.category_combo)

        self.description_edit = QTextEdit(self.skill_data.get("description", ""))
        self.description_edit.setPlaceholderText("Detailed description of the skill and its effects.")
        self.description_edit.setMinimumHeight(100)
        form.addRow("Description:", self.description_edit)

        layout.addLayout(form)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _on_accept(self):
        if not self.id_edit.text().strip():
            QMessageBox.warning(self, "Missing ID", "Skill ID cannot be empty.")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Missing Name", "Skill Name cannot be empty.")
            return
        self.accept()

    def get_skill_data(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        skill_id = self.id_edit.text().strip()
        skill_details = {
            "name": self.name_edit.text().strip(),
            "primary_stat": self.primary_stat_combo.currentText(),
            "category": self.category_combo.currentText(),
            "description": self.description_edit.toPlainText().strip()
        }
        return skill_id, skill_details


class SkillsEditor(QWidget):
    """Editor for managing skills from skills.json."""
    skills_modified = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.skills_data: Dict[str, Dict[str, Any]] = {} # skill_id: {name, desc,...}
        self.current_skill_id: Optional[str] = None
        self.skills_file_path: Optional[str] = None
        self._setup_ui()
        self._load_skills() # Load skills on initialization

    def _get_skills_file_path(self) -> str:
        """Constructs the absolute path to skills.json."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(project_root, "config", "skills.json")

    def _load_skills(self):
        """Load skills from skills.json."""
        self.skills_file_path = self._get_skills_file_path()
        if not os.path.exists(self.skills_file_path):
            logger.warning(f"Skills file not found at {self.skills_file_path}. Creating a default one.")
            self.skills_data = {"skills": {}} # Start with an empty skills dict
            self._save_skills() # Create the file
        else:
            loaded_data = load_json(self.skills_file_path)
            if loaded_data and "skills" in loaded_data and isinstance(loaded_data["skills"], dict):
                self.skills_data = loaded_data["skills"]
            else:
                logger.error(f"Invalid format in skills.json or file is empty. Initializing with empty skills list.")
                self.skills_data = {} # Fallback to empty dict
                # Ensure self.skills_data is a dict for skills, not the root "skills": {} structure
        self._refresh_skill_list()

    def _save_skills(self):
        """Save the current skills data to skills.json."""
        if self.skills_file_path:
            # The data to save should be in the format {"skills": {skill_id: data, ...}}
            data_to_save = {"skills": self.skills_data}
            if save_json(data_to_save, self.skills_file_path):
                logger.info(f"Skills saved to {self.skills_file_path}")
                self.skills_modified.emit()
            else:
                QMessageBox.critical(self, "Save Error", f"Failed to save skills to {self.skills_file_path}")
        else:
            QMessageBox.critical(self, "Save Error", "Skills file path is not set. Cannot save.")


    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Skill list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Skills List"))
        self.skill_list_widget = QListWidget()
        self.skill_list_widget.currentItemChanged.connect(self._on_skill_selected)
        left_layout.addWidget(self.skill_list_widget)
        list_buttons_layout = QHBoxLayout()
        self.add_skill_button = QPushButton("Add Skill")
        self.add_skill_button.clicked.connect(self._add_skill)
        list_buttons_layout.addWidget(self.add_skill_button)
        self.remove_skill_button = QPushButton("Remove Skill")
        self.remove_skill_button.clicked.connect(self._remove_skill)
        self.remove_skill_button.setEnabled(False)
        list_buttons_layout.addWidget(self.remove_skill_button)
        left_layout.addLayout(list_buttons_layout)
        splitter.addWidget(left_panel)

        # Right panel: Skill details
        right_panel_scroll = QScrollArea()
        right_panel_scroll.setWidgetResizable(True)
        right_panel_scroll.setFrameShape(QFrame.NoFrame)
        details_widget = QWidget()
        right_panel_scroll.setWidget(details_widget)
        self.details_layout = QFormLayout(details_widget)
        self.details_layout.setContentsMargins(10, 10, 10, 10)

        self.skill_id_label = QLabel()
        self.details_layout.addRow("Skill ID:", self.skill_id_label)
        self.skill_name_label = QLabel()
        self.details_layout.addRow("Name:", self.skill_name_label)
        self.primary_stat_label = QLabel()
        self.details_layout.addRow("Primary Stat:", self.primary_stat_label)
        self.category_label = QLabel()
        self.details_layout.addRow("Category:", self.category_label)
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMinimumHeight(100)
        self.details_layout.addRow("Description:", self.description_text)

        self.edit_skill_button = QPushButton("Edit Selected Skill")
        self.edit_skill_button.clicked.connect(self._edit_skill)
        self.edit_skill_button.setEnabled(False)
        self.details_layout.addRow(self.edit_skill_button)

        details_widget.setLayout(self.details_layout)
        splitter.addWidget(right_panel_scroll)
        splitter.setSizes([250, 550])
        main_layout.addWidget(splitter)

        self._disable_details_view()

    def _refresh_skill_list(self):
        self.skill_list_widget.clear()
        # Sort skills by name for display
        sorted_skill_ids = sorted(self.skills_data.keys(), key=lambda skill_id: self.skills_data[skill_id].get("name", skill_id))
        for skill_id in sorted_skill_ids:
            skill_entry = self.skills_data.get(skill_id, {})
            display_name = skill_entry.get("name", skill_id) # Fallback to ID if name is missing
            item = QListWidgetItem(f"{display_name} ({skill_id})")
            item.setData(Qt.UserRole, skill_id)
            self.skill_list_widget.addItem(item)
        self.remove_skill_button.setEnabled(False)
        self.edit_skill_button.setEnabled(False)

    def _on_skill_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if current:
            self.current_skill_id = current.data(Qt.UserRole)
            skill_data = self.skills_data.get(self.current_skill_id)
            if skill_data:
                self._populate_details_view(skill_data)
                self.remove_skill_button.setEnabled(True)
                self.edit_skill_button.setEnabled(True)
            else:
                self._disable_details_view()
        else:
            self.current_skill_id = None
            self._disable_details_view()
            self.remove_skill_button.setEnabled(False)
            self.edit_skill_button.setEnabled(False)

    def _populate_details_view(self, skill_data: Dict[str, Any]):
        self.skill_id_label.setText(self.current_skill_id or "N/A")
        self.skill_name_label.setText(skill_data.get("name", "N/A"))
        self.primary_stat_label.setText(skill_data.get("primary_stat", "N/A"))
        self.category_label.setText(skill_data.get("category", "N/A"))
        self.description_text.setPlainText(skill_data.get("description", "N/A"))

    def _disable_details_view(self):
        self.skill_id_label.setText("N/A")
        self.skill_name_label.setText("N/A")
        self.primary_stat_label.setText("N/A")
        self.category_label.setText("N/A")
        self.description_text.setPlainText("Select a skill to view details.")
        self.edit_skill_button.setEnabled(False)

    def _add_skill(self):
        dialog = SkillEditDialog(self)
        if dialog.exec() == QDialog.Accepted:
            skill_id, skill_data = dialog.get_skill_data()
            if skill_id in self.skills_data:
                QMessageBox.warning(self, "Duplicate ID", f"Skill ID '{skill_id}' already exists.")
                return
            self.skills_data[skill_id] = skill_data
            self._save_skills()
            self._refresh_skill_list()
            # Try to select the newly added skill
            for i in range(self.skill_list_widget.count()):
                if self.skill_list_widget.item(i).data(Qt.UserRole) == skill_id:
                    self.skill_list_widget.setCurrentRow(i)
                    break

    def _edit_skill(self):
        if not self.current_skill_id or self.current_skill_id not in self.skills_data:
            return
        current_data = self.skills_data[self.current_skill_id]
        dialog = SkillEditDialog(self, skill_id=self.current_skill_id, skill_data=current_data)
        if dialog.exec() == QDialog.Accepted:
            _, updated_skill_data = dialog.get_skill_data() # ID cannot change
            self.skills_data[self.current_skill_id] = updated_skill_data
            self._save_skills()
            self._refresh_skill_list()
             # Re-select the edited skill
            for i in range(self.skill_list_widget.count()):
                if self.skill_list_widget.item(i).data(Qt.UserRole) == self.current_skill_id:
                    self.skill_list_widget.setCurrentRow(i)
                    break


    def _remove_skill(self):
        if not self.current_skill_id or self.current_skill_id not in self.skills_data:
            return
        skill_name = self.skills_data[self.current_skill_id].get("name", self.current_skill_id)
        reply = QMessageBox.question(self, "Remove Skill",
                                     f"Are you sure you want to remove '{skill_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.skills_data[self.current_skill_id]
            self._save_skills()
            self._refresh_skill_list()
            self._disable_details_view() # Clear details after deletion

    def refresh_data(self):
        """Public method to reload skills, e.g., if file changed externally."""
        self._load_skills()