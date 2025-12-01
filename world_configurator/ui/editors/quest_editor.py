"""
Quest editor component for the World Configurator Tool.
"""

import uuid
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QSpinBox,
    QDialog, QMessageBox, QSplitter, QScrollArea, QFrame, QComboBox,
    
)

from ui.dialogs.base_dialog import BaseDialog
from models.base_models import Quest, QuestObjective
from models.origin_data import QuestManager
from models.location_data import LocationManager
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.ui.quest_editor")

class QuestObjectiveDialog(BaseDialog):
    """Dialog for editing a quest objective."""
    
    def __init__(self, parent=None, objective: Optional[QuestObjective] = None, location_manager=None):
        """
        Initialize the objective edit dialog.
        
        Args:
            parent: The parent widget.
            objective: Optional existing objective to edit.
            location_manager: Manager with location data for dropdown.
        """
        super().__init__(parent)
        self.setWindowTitle("Quest Objective")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Objective to edit
        self.objective = objective or QuestObjective(
            id=str(uuid.uuid4()),
            description="",
            type="fetch"
        )
        self.location_manager = location_manager
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout for fields
        form = QFormLayout()
        
        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.objective.description)
        self.desc_edit.setMinimumHeight(100)
        form.addRow("Description:", self.desc_edit)
        
        # Type field
        self.type_combo = QComboBox()
        self.type_combo.addItems(["fetch", "kill", "escort", "explore", "interact", "deliver", "other"])
        # Set current type if exists
        if self.objective.type:
            index = self.type_combo.findText(self.objective.type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
        form.addRow("Type:", self.type_combo)
        
        # Target ID field
        self.target_edit = QLineEdit(self.objective.target_id)
        form.addRow("Target ID:", self.target_edit)
        
        # Location field
        self.location_combo = QComboBox()
        if self.location_manager:
            self._populate_location_combo()
            
            # Set current location if exists
            if self.objective.location_id:
                index = self.location_combo.findData(self.objective.location_id)
                if index >= 0:
                    self.location_combo.setCurrentIndex(index)
        
        form.addRow("Location:", self.location_combo)
        
        # Mandatory toggle
        from PySide6.QtWidgets import QCheckBox
        self.mandatory_check = QCheckBox("Mandatory objective")
        current_mandatory = getattr(self.objective, 'mandatory', None)
        self.mandatory_check.setChecked(True if current_mandatory is None else bool(current_mandatory))
        form.addRow("Requirement:", self.mandatory_check)
        
        # Completion criteria field
        self.criteria_edit = QTextEdit()
        self.criteria_edit.setPlainText(self.objective.completion_criteria)
        self.criteria_edit.setMinimumHeight(80)
        form.addRow("Completion Criteria:", self.criteria_edit)
        
        # Rewards field
        self.rewards_edit = QTextEdit()
        rewards_text = ""
        if self.objective.rewards:
            for reward_type, value in self.objective.rewards.items():
                rewards_text += f"{reward_type}: {value}\n"
        self.rewards_edit.setPlainText(rewards_text)
        self.rewards_edit.setMinimumHeight(80)
        self.rewards_edit.setPlaceholderText("Format: reward_type: value\nExamples:\nxp: 100\ngold: 50\nitem: sword_01")
        form.addRow("Rewards:", self.rewards_edit)
        
        layout.addLayout(form)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
    
    def _populate_location_combo(self):
        """Populate the location dropdown with available locations."""
        self.location_combo.clear()
        
        if not self.location_manager or not self.location_manager.locations:
            self.location_combo.addItem("No locations available", "")
            return
        
        # Add each location to the combo box
        for location_id, location in self.location_manager.locations.items():
            self.location_combo.addItem(f"{location.name} ({location.type})", location_id)
    
    def get_objective(self) -> QuestObjective:
        """Get the edited objective."""
        self.objective.description = self.desc_edit.toPlainText()
        self.objective.type = self.type_combo.currentText()
        self.objective.target_id = self.target_edit.text()
        self.objective.location_id = self.location_combo.currentData()
        self.objective.completion_criteria = self.criteria_edit.toPlainText()
        # Save mandatory flag
        try:
            setattr(self.objective, 'mandatory', bool(self.mandatory_check.isChecked()))
        except Exception:
            pass
        
        # Parse rewards text to dict
        rewards = {}
        rewards_text = self.rewards_edit.toPlainText().strip()
        if rewards_text:
            for line in rewards_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    # Try to convert value to int if possible
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                    rewards[key] = value
                    
        self.objective.rewards = rewards
        
        return self.objective


class QuestEditor(QWidget):
    """Quest editor component."""
    
    # Signals
    quest_modified = Signal()
    
    def __init__(self, parent=None):
        """
        Initialize the quest editor.
        
        Args:
            parent: The parent widget.
        """
        super().__init__(parent)
        
        # Internal state
        self.quest_manager = QuestManager()
        self.location_manager = LocationManager()
        self.current_quest: Optional[Quest] = None
        
        # Setup UI
        self._setup_ui()

    # ===== Assistant integration =====
    def get_assistant_context(self):
        from assistant.context import AssistantContext
        allowed = [
            "/title",
            "/description",
            "/giver_id",
            "/level",
            "/rewards",
            "/prerequisites",
            "/objectives",
        ]
        content = self.current_quest.to_dict() if self.current_quest else None
        return AssistantContext(
            domain="quests",
            selection_id=self.current_quest.id if self.current_quest else None,
            content=content,
            schema=None,
            allowed_paths=allowed,
        )

    def get_domain_examples(self):
        if self.quest_manager.quests:
            first = next(iter(self.quest_manager.quests.values()))
            return [first.to_dict()]
        return []

    def get_reference_catalogs(self):
        # Provide location IDs and existing quest titles/ids
        location_ids = []
        try:
            if self.location_manager and getattr(self.location_manager, 'locations', None):
                location_ids = list(self.location_manager.locations.keys())
        except Exception:
            location_ids = []
        existing_titles = {}
        try:
            for q in self.quest_manager.quests.values():
                existing_titles[q.id] = q.title
        except Exception:
            existing_titles = {}
        return {
            "location_ids": location_ids,
            "existing_ids": list(existing_titles.keys()),
            "existing_titles": existing_titles,
        }

    def _sanitize_quest_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return payload
        sanitized = dict(payload)
        # Ensure level is int
        if "level" in sanitized:
            try:
                sanitized["level"] = int(sanitized["level"])
            except Exception:
                pass
        # Ensure prerequisites is list[str]
        if "prerequisites" in sanitized and isinstance(sanitized["prerequisites"], list):
            sanitized["prerequisites"] = [p for p in sanitized["prerequisites"] if isinstance(p, str) and p.strip()]
        # Objectives: allow replacing the whole list or editing fields. Coerce dicts to proper shape where obvious.
        if "objectives" in sanitized and isinstance(sanitized["objectives"], list):
            new_objs = []
            for obj in sanitized["objectives"]:
                if isinstance(obj, dict):
                    # ensure id
                    oid = obj.get("id")
                    if not isinstance(oid, str) or not oid:
                        import uuid
                        obj["id"] = str(uuid.uuid4())
                    # Coerce rewards to dict
                    if "rewards" in obj and not isinstance(obj["rewards"], dict):
                        obj["rewards"] = {}
                    new_objs.append(obj)
            sanitized["objectives"] = new_objs
        # Ensure id is slug-like if present
        if "id" in sanitized and isinstance(sanitized["id"], str):
            sanitized["id"] = self._slugify(sanitized["id"]) or sanitized["id"]
        return sanitized

    def _slugify(self, text: str) -> str:
        """Create a lowercase slug id from text (letters, numbers, hyphens)."""
        import re
        t = (text or "").strip().lower()
        t = re.sub(r"[^a-z0-9\s_-]", "", t)
        t = re.sub(r"[\s_-]+", "-", t)
        return t.strip("-")

    def apply_assistant_patch(self, patch_ops):
        from assistant.patching import apply_patch_with_validation
        ctx = self.get_assistant_context()
        if not ctx.content:
            return False, "No quest selected."
        ok, msg, new_content = apply_patch_with_validation(ctx, ctx.content, patch_ops)
        if not ok:
            return False, msg
        try:
            new_content = self._sanitize_quest_payload(new_content)
            updated = Quest.from_dict(new_content)
            updated.id = self.current_quest.id
            self.quest_manager.add_quest(updated)
            self._load_quest(updated)
            self.quest_modified.emit()
            return True, "OK"
        except Exception as e:
            return False, f"Failed to apply: {e}"

    def create_entry_from_llm(self, entry: dict):
        try:
            # Ensure unique, human-friendly title
            proposed_title = (entry.get("title") or "New Quest").strip()
            existing_titles = {q.title for q in self.quest_manager.quests.values()}
            title = proposed_title
            suffix = 1
            while title in existing_titles:
                title = f"{proposed_title} ({suffix})"
                suffix += 1

            # Derive a slug id from the title and ensure uniqueness among quest ids
            base_slug = self._slugify(title)
            quest_ids = set(self.quest_manager.quests.keys())
            slug = base_slug
            i = 1
            while slug in quest_ids:
                i += 1
                slug = f"{base_slug}-{i}"

            desc = entry.get("description", "")
            # Build quest dict using the slug as id
            tmp = {
                "id": slug,
                "title": title,
                "description": desc,
                "giver_id": entry.get("giver_id", ""),
                "level": entry.get("level", 1),
                "objectives": entry.get("objectives", []),
                "rewards": entry.get("rewards", {}),
                "prerequisites": entry.get("prerequisites", []),
            }
            # Merge any extra fields from entry (excluding id/title which we control)
            for k, v in entry.items():
                if k not in ("id", "title"):
                    tmp[k] = v if k not in tmp else tmp[k]

            tmp = self._sanitize_quest_payload(tmp)
            new_obj = Quest.from_dict(tmp)
            new_obj.id = slug  # Ensure id is the slug
            self.quest_manager.add_quest(new_obj)
            self._refresh_quest_list()
            # select new
            for i in range(self.quest_list.count()):
                it = self.quest_list.item(i)
                if self.quest_manager.get_quest(it.data(Qt.UserRole)).id == new_obj.id:
                    self.quest_list.setCurrentItem(it)
                    break
            self.quest_modified.emit()
            return True, "Created", new_obj.id
        except Exception as e:
            return False, f"Failed to create: {e}", None
    
    def _setup_ui(self):
        """Setup the editor UI."""
        main_layout = QHBoxLayout(self)
        
        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel (quest list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = QLabel("Quests")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(list_label)
        
        self.quest_list = QListWidget()
        self.quest_list.setMinimumWidth(200)
        self.quest_list.currentItemChanged.connect(self._on_quest_selected)
        left_layout.addWidget(self.quest_list)
        
        list_buttons = QHBoxLayout()
        
        self.add_quest_btn = QPushButton("Add")
        self.add_quest_btn.clicked.connect(self._add_quest)
        list_buttons.addWidget(self.add_quest_btn)
        
        self.remove_quest_btn = QPushButton("Remove")
        self.remove_quest_btn.clicked.connect(self._remove_quest)
        self.remove_quest_btn.setEnabled(False)
        list_buttons.addWidget(self.remove_quest_btn)
        
        left_layout.addLayout(list_buttons)
        
        # Add left panel to splitter
        splitter.addWidget(left_panel)
        
        # Right panel (quest details)
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setFrameShape(QFrame.NoFrame)
        
        self.details_widget = QWidget()
        right_panel.setWidget(self.details_widget)
        
        self.details_layout = QVBoxLayout(self.details_widget)
        
        # Quest details form
        self.form_layout = QFormLayout()
        
        # Quest title
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter quest title")
        self.title_edit.textChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Title:", self.title_edit)
        
        # Quest description
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Enter quest description")
        self.desc_edit.textChanged.connect(self._on_field_changed)
        self.desc_edit.setMinimumHeight(100)
        self.form_layout.addRow("Description:", self.desc_edit)
        
        # Quest giver
        self.giver_edit = QLineEdit()
        self.giver_edit.setPlaceholderText("Enter NPC ID of quest giver")
        self.giver_edit.textChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Quest Giver ID:", self.giver_edit)
        
        # Quest level
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 50)
        self.level_spin.setValue(1)
        self.level_spin.valueChanged.connect(self._on_field_changed)
        self.form_layout.addRow("Level:", self.level_spin)
        
        self.details_layout.addLayout(self.form_layout)
        
        # Objectives section
        objectives_label = QLabel("Objectives")
        objectives_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(objectives_label)
        
        self.objectives_list = QListWidget()
        self.objectives_list.setMinimumHeight(150)
        self.details_layout.addWidget(self.objectives_list)
        
        objectives_buttons = QHBoxLayout()
        
        self.add_objective_btn = QPushButton("Add Objective")
        self.add_objective_btn.clicked.connect(self._add_objective)
        objectives_buttons.addWidget(self.add_objective_btn)
        
        self.edit_objective_btn = QPushButton("Edit Objective")
        self.edit_objective_btn.clicked.connect(self._edit_objective)
        objectives_buttons.addWidget(self.edit_objective_btn)
        
        self.remove_objective_btn = QPushButton("Remove Objective")
        self.remove_objective_btn.clicked.connect(self._remove_objective)
        objectives_buttons.addWidget(self.remove_objective_btn)
        
        self.details_layout.addLayout(objectives_buttons)
        
        # Rewards section
        rewards_label = QLabel("Rewards")
        rewards_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(rewards_label)
        
        self.rewards_edit = QTextEdit()
        self.rewards_edit.setPlaceholderText("Format: reward_type: value\nExamples:\nxp: 500\ngold: 100\nitem: legendary_sword")
        self.rewards_edit.setMaximumHeight(100)
        self.rewards_edit.textChanged.connect(self._on_field_changed)
        self.details_layout.addWidget(self.rewards_edit)
        
        # Prerequisites section
        prereq_label = QLabel("Prerequisites")
        prereq_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(prereq_label)
        
        self.prereq_edit = QTextEdit()
        self.prereq_edit.setPlaceholderText("Enter one quest ID per line...")
        self.prereq_edit.setMaximumHeight(100)
        self.prereq_edit.textChanged.connect(self._on_field_changed)
        self.details_layout.addWidget(self.prereq_edit)
        
        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_current_quest)
        self.save_btn.setEnabled(False)
        save_layout.addWidget(self.save_btn)
        
        self.details_layout.addLayout(save_layout)
        
        # Add right panel to splitter
        splitter.addWidget(right_panel)
        
        # Set up initial state
        self._disable_details()
        
        # Prioritize the details panel for resizing
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
    
    def set_managers(self, quest_manager: QuestManager, location_manager: LocationManager) -> None:
        """
        Set the quest and location managers to use.
        
        Args:
            quest_manager: The quest manager.
            location_manager: The location manager.
        """
        self.quest_manager = quest_manager
        self.location_manager = location_manager
        
        # Refresh quest list
        self._refresh_quest_list()
    
    def _refresh_quest_list(self) -> None:
        """Refresh the quest list from the manager."""
        # Clear list
        self.quest_list.clear()
        
        # Add all quests
        for quest_id, quest in self.quest_manager.quests.items():
            item = QListWidgetItem(quest.title)
            item.setData(Qt.UserRole, quest_id)
            self.quest_list.addItem(item)
        
        # Sort alphabetically
        self.quest_list.sortItems()
        
        # Select the first item if available
        if self.quest_list.count() > 0:
            self.quest_list.setCurrentRow(0)
    
    def _on_quest_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        """
        Handle quest selection change.
        
        Args:
            current: The current selected item, or None.
            previous: The previously selected item, or None.
        """
        if current:
            quest_id = current.data(Qt.UserRole)
            quest = self.quest_manager.get_quest(quest_id)
            
            if quest:
                self._load_quest(quest)
                self.remove_quest_btn.setEnabled(True)
                return
        
        # No valid selection
        self._disable_details()
        self.remove_quest_btn.setEnabled(False)
    
    def _load_quest(self, quest) -> None:
        """
        Load a quest into the editor.
        
        Args:
            quest: The quest to load (Quest object or dictionary).
        """
        try:
            # Ensure quest is a Quest object
            if isinstance(quest, dict):
                logger.info(f"Converting dictionary to Quest object for {quest.get('title', 'Unknown Quest')}")
                quest = Quest.from_dict(quest)
            
            self.current_quest = quest
            
            # Set form values
            self.title_edit.setText(quest.title)
            self.desc_edit.setPlainText(quest.description)
            self.giver_edit.setText(quest.giver_id)
            self.level_spin.setValue(quest.level)
            
            # Load rewards
            rewards_text = ""
            if quest.rewards:
                for reward_type, value in quest.rewards.items():
                    rewards_text += f"{reward_type}: {value}\n"
            self.rewards_edit.setPlainText(rewards_text)
            
            # Load prerequisites
            self.prereq_edit.setPlainText("\n".join(quest.prerequisites))
            
            # Load objectives
            self.objectives_list.clear()
            for objective in quest.objectives:
                item = QListWidgetItem(objective.description)
                item.setData(Qt.UserRole, objective)
                self.objectives_list.addItem(item)
            
            # Enable controls
            self._enable_details()
            self.save_btn.setEnabled(False)  # Initially not modified
            
        except Exception as e:
            logger.error(f"Error loading quest {quest.title}: {str(e)}")
            QMessageBox.warning(
                self,
                "Error Loading Quest",
                f"There was an error loading the quest '{quest.title}':\n\n{str(e)}\n\nSome data may not be displayed correctly."
            )
            # Still enable the editor to allow fixing the issue
            self._enable_details()
            self.save_btn.setEnabled(True)  # Enable saving to fix issues
    
    def _disable_details(self) -> None:
        """Disable all detail controls."""
        self.current_quest = None
        
        self.title_edit.clear()
        self.desc_edit.clear()
        self.giver_edit.clear()
        self.level_spin.setValue(1)
        self.rewards_edit.clear()
        self.prereq_edit.clear()
        
        self.objectives_list.clear()
        
        self.title_edit.setEnabled(False)
        self.desc_edit.setEnabled(False)
        self.giver_edit.setEnabled(False)
        self.level_spin.setEnabled(False)
        self.rewards_edit.setEnabled(False)
        self.prereq_edit.setEnabled(False)
        
        self.objectives_list.setEnabled(False)
        
        self.add_objective_btn.setEnabled(False)
        self.edit_objective_btn.setEnabled(False)
        self.remove_objective_btn.setEnabled(False)
        
        self.save_btn.setEnabled(False)
    
    def _enable_details(self) -> None:
        """Enable all detail controls."""
        self.title_edit.setEnabled(True)
        self.desc_edit.setEnabled(True)
        self.giver_edit.setEnabled(True)
        self.level_spin.setEnabled(True)
        self.rewards_edit.setEnabled(True)
        self.prereq_edit.setEnabled(True)
        
        self.objectives_list.setEnabled(True)
        
        self.add_objective_btn.setEnabled(True)
        self.edit_objective_btn.setEnabled(True)
        self.remove_objective_btn.setEnabled(True)
    
    def _on_field_changed(self) -> None:
        """Handle field value changes."""
        if self.current_quest:
            self.save_btn.setEnabled(True)
    
    def _save_current_quest(self) -> None:
        """Save the current quest to the manager."""
        if not self.current_quest:
            return
        
        # Update quest from form
        self.current_quest.title = self.title_edit.text()
        self.current_quest.description = self.desc_edit.toPlainText()
        self.current_quest.giver_id = self.giver_edit.text()
        self.current_quest.level = self.level_spin.value()
        
        # Parse rewards text to dict
        rewards = {}
        rewards_text = self.rewards_edit.toPlainText().strip()
        if rewards_text:
            for line in rewards_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    # Try to convert value to int if possible
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                    rewards[key] = value
        
        self.current_quest.rewards = rewards
        
        # Parse prerequisites
        self.current_quest.prerequisites = [prereq.strip() for prereq in self.prereq_edit.toPlainText().split('\n') if prereq.strip()]
        
        # Update quest in manager
        self.quest_manager.add_quest(self.current_quest)
        
        # Mark as saved
        self.save_btn.setEnabled(False)
        
        # Update quest list
        self._refresh_quest_list()
        
        # Find and select the current quest in the list
        for i in range(self.quest_list.count()):
            item = self.quest_list.item(i)
            if item.data(Qt.UserRole) == self.current_quest.id:
                self.quest_list.setCurrentItem(item)
                break
        
        # Emit modified signal
        self.quest_modified.emit()
        
        # Log
        logger.info(f"Saved quest: {self.current_quest.title} ({self.current_quest.id})")
    
    def _add_quest(self) -> None:
        """Add a new quest."""
        # Create new quest
        quest = Quest.create_new("New Quest", "Description of the quest")
        
        # Add to manager
        self.quest_manager.add_quest(quest)
        
        # Refresh list
        self._refresh_quest_list()
        
        # Find and select the new quest
        for i in range(self.quest_list.count()):
            item = self.quest_list.item(i)
            if item.data(Qt.UserRole) == quest.id:
                self.quest_list.setCurrentItem(item)
                break
        
        # Set focus to title for immediate editing
        self.title_edit.setFocus()
        self.title_edit.selectAll()
        
        # Emit modified signal
        self.quest_modified.emit()
        
        # Log
        logger.info(f"Added new quest: {quest.id}")
    
    def _remove_quest(self) -> None:
        """Remove the selected quest."""
        current_item = self.quest_list.currentItem()
        if not current_item:
            return
        
        quest_id = current_item.data(Qt.UserRole)
        quest = self.quest_manager.get_quest(quest_id)
        
        if not quest:
            return
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the quest '{quest.title}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Remove from manager
        self.quest_manager.remove_quest(quest_id)
        
        # Refresh list
        self._refresh_quest_list()
        
        # Emit modified signal
        self.quest_modified.emit()
        
        # Log
        logger.info(f"Removed quest: {quest_id}")
    
    def _add_objective(self) -> None:
        """Add a new objective to the current quest."""
        if not self.current_quest:
            return
        
        dialog = QuestObjectiveDialog(self, location_manager=self.location_manager)
        
        if dialog.exec() == QDialog.Accepted:
            objective = dialog.get_objective()
            
            # Add to quest
            self.current_quest.objectives.append(objective)
            
            # Add to list
            item = QListWidgetItem(objective.description)
            item.setData(Qt.UserRole, objective)
            self.objectives_list.addItem(item)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Added objective to quest {self.current_quest.id}: {objective.description}")
    
    def _edit_objective(self) -> None:
        """Edit the selected objective."""
        if not self.current_quest:
            return
        
        current_item = self.objectives_list.currentItem()
        if not current_item:
            return
        
        objective = current_item.data(Qt.UserRole)
        dialog = QuestObjectiveDialog(self, objective, self.location_manager)
        
        if dialog.exec() == QDialog.Accepted:
            updated_obj = dialog.get_objective()
            
            # Find and update the objective in the quest
            for i, obj in enumerate(self.current_quest.objectives):
                if obj.id == updated_obj.id:
                    self.current_quest.objectives[i] = updated_obj
                    break
            
            # Update item
            current_item.setText(updated_obj.description)
            current_item.setData(Qt.UserRole, updated_obj)
            
            # Mark as modified
            self.save_btn.setEnabled(True)
            
            # Log
            logger.debug(f"Edited objective in quest {self.current_quest.id}: {updated_obj.description}")
    
    def _remove_objective(self) -> None:
        """Remove the selected objective."""
        if not self.current_quest:
            return
        
        current_item = self.objectives_list.currentItem()
        if not current_item:
            return
        
        objective = current_item.data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove this objective?\n\n{objective.description}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Remove from quest
        self.current_quest.objectives = [obj for obj in self.current_quest.objectives if obj.id != objective.id]
        
        # Remove from list
        self.objectives_list.takeItem(self.objectives_list.row(current_item))
        
        # Mark as modified
        self.save_btn.setEnabled(True)
        
        # Log
        logger.debug(f"Removed objective from quest {self.current_quest.id}: {objective.description}")
    
    def refresh(self):
        """Refresh the editor data."""
        self._refresh_quest_list()
    
class QuestDialog(QDialog):
    
    def __init__(self, parent=None, quest: Optional[Quest] = None, location_manager=None):
        """
        Initialize the quest edit dialog.
        
        Args:
            parent: The parent widget.
            quest: Optional existing quest to edit.
            location_manager: Manager with location data for dropdown.
        """
        super().__init__(parent)
        self.setWindowTitle("Quest")
        self.setMinimumWidth(600)
        self.setMinimumHeight(600)
        
        # Quest to edit
        self.quest = quest or Quest.create_new("", "")
        self.location_manager = location_manager
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Form layout for fields
        form = QFormLayout()
        
        # Title field
        self.title_edit = QLineEdit(self.quest.title)
        form.addRow("Title:", self.title_edit)
        
        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.quest.description)
        self.desc_edit.setMinimumHeight(100)
        form.addRow("Description:", self.desc_edit)
        
        # Quest giver field
        self.giver_edit = QLineEdit(self.quest.giver_id)
        form.addRow("Quest Giver ID:", self.giver_edit)
        
        # Level field
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 50)
        self.level_spin.setValue(self.quest.level)
        form.addRow("Level:", self.level_spin)
        
        # Add form to layout
        layout.addLayout(form)
        
        # Objectives section
        objectives_label = QLabel("Objectives")
        objectives_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(objectives_label)
        
        # Objectives list
        self.objectives_list = QListWidget()
        self.objectives_list.setMinimumHeight(150)
        self._populate_objectives_list()
        layout.addWidget(self.objectives_list)
        
        # Objectives buttons
        obj_buttons = QHBoxLayout()
        
        self.add_obj_btn = QPushButton("Add Objective")
        self.add_obj_btn.clicked.connect(self._add_objective)
        obj_buttons.addWidget(self.add_obj_btn)
        
        self.edit_obj_btn = QPushButton("Edit Objective")
        self.edit_obj_btn.clicked.connect(self._edit_objective)
        obj_buttons.addWidget(self.edit_obj_btn)
        
        self.remove_obj_btn = QPushButton("Remove Objective")
        self.remove_obj_btn.clicked.connect(self._remove_objective)
        obj_buttons.addWidget(self.remove_obj_btn)
        
        layout.addLayout(obj_buttons)
        
        # Rewards section
        rewards_label = QLabel("Rewards")
        rewards_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(rewards_label)
        
        # Rewards edit
        self.rewards_edit = QTextEdit()
        rewards_text = ""
        if self.quest.rewards:
            for reward_type, value in self.quest.rewards.items():
                rewards_text += f"{reward_type}: {value}\n"
        self.rewards_edit.setPlainText(rewards_text)
        self.rewards_edit.setMinimumHeight(80)
        self.rewards_edit.setPlaceholderText("Format: reward_type: value\nExamples:\nxp: 500\ngold: 100\nitem: legendary_sword")
        layout.addWidget(self.rewards_edit)
        
        # Prerequisites section
        prereq_label = QLabel("Prerequisites")
        prereq_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(prereq_label)
        
        # Prerequisites edit
        self.prereq_edit = QTextEdit()
        self.prereq_edit.setPlainText("\n".join(self.quest.prerequisites))
        self.prereq_edit.setMinimumHeight(80)
        self.prereq_edit.setPlaceholderText("One quest ID per line...")
        layout.addWidget(self.prereq_edit)
        
        # Dialog buttons
        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
    
    def _populate_objectives_list(self):
        """Populate the objectives list."""
        self.objectives_list.clear()
        
        for objective in self.quest.objectives:
            item = QListWidgetItem(objective.description)
            item.setData(Qt.UserRole, objective)
            self.objectives_list.addItem(item)
    
    def _add_objective(self):
        """Add a new objective."""
        dialog = QuestObjectiveDialog(self, location_manager=self.location_manager)
        
        if dialog.exec() == QDialog.Accepted:
            objective = dialog.get_objective()
            self.quest.objectives.append(objective)
            
            # Update list
            self._populate_objectives_list()
    
    def _edit_objective(self):
        """Edit the selected objective."""
        current_item = self.objectives_list.currentItem()
        if not current_item:
            return
        
        objective = current_item.data(Qt.UserRole)
        dialog = QuestObjectiveDialog(self, objective, self.location_manager)
        
        if dialog.exec() == QDialog.Accepted:
            updated_obj = dialog.get_objective()
            
            # Find and update the objective in the quest
            for i, obj in enumerate(self.quest.objectives):
                if obj.id == updated_obj.id:
                    self.quest.objectives[i] = updated_obj
                    break
            
            # Update list
            self._populate_objectives_list()
    
    def _remove_objective(self):
        """Remove the selected objective."""
        current_item = self.objectives_list.currentItem()
        if not current_item:
            return
        
        objective = current_item.data(Qt.UserRole)
        
        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove this objective?\n\n{objective.description}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            # Remove objective from quest
            self.quest.objectives = [obj for obj in self.quest.objectives if obj.id != objective.id]
            
            # Update list
            self._populate_objectives_list()
    
    def get_quest(self) -> Quest:
        """Get the edited quest."""
        self.quest.title = self.title_edit.text()
        self.quest.description = self.desc_edit.toPlainText()
        self.quest.giver_id = self.giver_edit.text()
        self.quest.level = self.level_spin.value()
        
        # Parse rewards text to dict
        rewards = {}
        rewards_text = self.rewards_edit.toPlainText().strip()
        if rewards_text:
            for line in rewards_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    # Try to convert value to int if possible
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                    rewards[key] = value
        
        self.quest.rewards = rewards
        
        # Parse prerequisites
        self.quest.prerequisites = [prereq.strip() for prereq in self.prereq_edit.toPlainText().split('\n') if prereq.strip()]
        
        return self.quest
