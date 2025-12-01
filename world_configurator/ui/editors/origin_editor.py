# world_configurator/ui/editors/origin_editor.py
"""
Origin editor component for the World Configurator Tool.
(Formerly Scenario Editor)
"""


import copy
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout,
    QDialog, QMessageBox, QSplitter, QScrollArea, QFrame, QComboBox,
    QInputDialog, QTableWidget, QTableWidgetItem, QHeaderView
)

from ui.dialogs.base_dialog import BaseDialog
from models.base_models import Origin, OriginTrait
from models.origin_data import OriginManager # Renamed import
from models.location_data import LocationManager
from models.origin_data import QuestManager
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.ui.origin_editor") # Updated logger name


class OriginTraitDialog(BaseDialog):
    """Dialog for editing an OriginTrait."""
    def __init__(self, parent=None, trait: Optional[OriginTrait] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Origin Trait")
        self.setMinimumWidth(400)

        self.trait = copy.deepcopy(trait) if trait else OriginTrait(name="New Trait", description="")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.trait.name)
        form.addRow("Trait Name:", self.name_edit)

        self.desc_edit = QTextEdit(self.trait.description)
        self.desc_edit.setMinimumHeight(80)
        form.addRow("Description:", self.desc_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def get_trait(self) -> OriginTrait:
        self.trait.name = self.name_edit.text().strip()
        self.trait.description = self.desc_edit.toPlainText().strip()
        return self.trait

class OriginEditor(QWidget): # Renamed class
    """Origin editor component."""

    # Signals
    origin_modified = Signal() # Renamed signal

    def __init__(self, parent=None):
        """
        Initialize the origin editor.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)

        # Internal state
        self.origin_manager = OriginManager() # Renamed manager
        self.location_manager = LocationManager()
        self.quest_manager: Optional[QuestManager] = None
        self.current_origin: Optional[Origin] = None # Renamed variable

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the editor UI."""
        main_layout = QHBoxLayout(self)

        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel (origin list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_label = QLabel("Starting Origins")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(list_label)

        self.origin_list = QListWidget()
        self.origin_list.setMinimumWidth(200)
        self.origin_list.currentItemChanged.connect(self._on_origin_selected)
        left_layout.addWidget(self.origin_list)

        list_buttons = QHBoxLayout()

        self.add_origin_btn = QPushButton("Add")
        self.add_origin_btn.clicked.connect(self._add_origin)
        list_buttons.addWidget(self.add_origin_btn)

        self.remove_origin_btn = QPushButton("Remove")
        self.remove_origin_btn.clicked.connect(self._remove_origin)
        self.remove_origin_btn.setEnabled(False)
        list_buttons.addWidget(self.remove_origin_btn)

        left_layout.addLayout(list_buttons)
        splitter.addWidget(left_panel)

        # Right panel (origin details)
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setFrameShape(QFrame.NoFrame)

        self.details_widget = QWidget()
        right_panel.setWidget(self.details_widget)
        self.details_layout = QVBoxLayout(self.details_widget)

        self.form_layout = QFormLayout()
        self.name_label = QLabel("")
        self.form_layout.addRow("Name:", self.name_label)
        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True); self.desc_label.setMinimumHeight(60)
        self.form_layout.addRow("Description:", self.desc_label)
        self.location_label = QLabel("")
        self.form_layout.addRow("Starting Location:", self.location_label)
        self.culture_label = QLabel("")
        self.form_layout.addRow("Starting Culture (Optional):", self.culture_label)
        self.intro_label = QLabel("")
        self.intro_label.setWordWrap(True); self.intro_label.setMinimumHeight(100)
        self.form_layout.addRow("Introduction Text:", self.intro_label)

        self.name_label.mouseDoubleClickEvent = self._edit_name
        self.desc_label.mouseDoubleClickEvent = self._edit_description
        self.location_label.mouseDoubleClickEvent = self._edit_location
        self.culture_label.mouseDoubleClickEvent = self._edit_culture
        self.intro_label.mouseDoubleClickEvent = self._edit_introduction
        self.details_layout.addLayout(self.form_layout)

        skills_label = QLabel("Skill Proficiencies")
        skills_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(skills_label)
        self.skills_list = QListWidget()
        self.skills_list.setMinimumHeight(60)
        self.skills_list.itemDoubleClicked.connect(self._edit_skill_proficiency) # Changed from _edit_skill
        self.details_layout.addWidget(self.skills_list)
        skills_buttons = QHBoxLayout()
        self.add_skill_btn = QPushButton("Manage Skills") # Changed button text
        self.add_skill_btn.clicked.connect(self._manage_skill_proficiencies) # Changed slot
        skills_buttons.addWidget(self.add_skill_btn)
        # Remove skill button is no longer needed here as management is via dialog
        # self.remove_skill_btn = QPushButton("Remove Skill")
        # self.remove_skill_btn.clicked.connect(self._remove_skill_proficiency)
        # skills_buttons.addWidget(self.remove_skill_btn)
        self.details_layout.addLayout(skills_buttons)

        traits_label = QLabel("Origin Traits")
        traits_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(traits_label)
        self.traits_table = QTableWidget()
        self.traits_table.setColumnCount(2)
        self.traits_table.setHorizontalHeaderLabels(["Trait Name", "Description"])
        self.traits_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.traits_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.traits_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.traits_table.itemDoubleClicked.connect(self._edit_trait_row)
        self.traits_table.setMinimumHeight(100)
        self.details_layout.addWidget(self.traits_table)
        traits_buttons = QHBoxLayout()
        self.add_trait_btn = QPushButton("Add Trait")
        self.add_trait_btn.clicked.connect(self._add_trait)
        traits_buttons.addWidget(self.add_trait_btn)
        self.edit_trait_btn = QPushButton("Edit Trait")
        self.edit_trait_btn.clicked.connect(self._edit_selected_trait)
        traits_buttons.addWidget(self.edit_trait_btn)
        self.remove_trait_btn = QPushButton("Remove Trait")
        self.remove_trait_btn.clicked.connect(self._remove_trait)
        traits_buttons.addWidget(self.remove_trait_btn)
        self.details_layout.addLayout(traits_buttons)

        items_label = QLabel("Starting Items")
        items_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(items_label)
        self.items_list = QListWidget()
        self.items_list.setMinimumHeight(60)
        self.items_list.itemDoubleClicked.connect(self._edit_starting_item)
        self.details_layout.addWidget(self.items_list)
        items_buttons = QHBoxLayout()
        self.add_item_btn = QPushButton("Manage Items") # Changed button text
        self.add_item_btn.clicked.connect(self._manage_starting_items) # Changed slot
        items_buttons.addWidget(self.add_item_btn)
        self.details_layout.addLayout(items_buttons)

        quests_label = QLabel("Initial Quests")
        quests_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(quests_label)
        self.quests_list = QListWidget()
        self.quests_list.setMinimumHeight(60)
        self.quests_list.itemDoubleClicked.connect(self._edit_quest)
        self.details_layout.addWidget(self.quests_list)
        quests_buttons = QHBoxLayout()
        self.manage_quests_btn = QPushButton("Manage Quests")
        self.manage_quests_btn.clicked.connect(self._manage_initial_quests)
        quests_buttons.addWidget(self.manage_quests_btn)
        self.remove_quest_btn = QPushButton("Remove Selected")
        self.remove_quest_btn.clicked.connect(self._remove_quest)
        quests_buttons.addWidget(self.remove_quest_btn)
        self.details_layout.addLayout(quests_buttons)

        races_label = QLabel("Suitable Races")
        races_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(races_label)
        self.races_list = QListWidget()
        self.races_list.setMinimumHeight(60)
        self.races_list.itemDoubleClicked.connect(self._edit_race)
        self.details_layout.addWidget(self.races_list)
        races_buttons = QHBoxLayout()
        self.add_race_btn = QPushButton("Add Race")
        self.add_race_btn.clicked.connect(self._add_race)
        races_buttons.addWidget(self.add_race_btn)
        self.remove_race_btn = QPushButton("Remove Race")
        self.remove_race_btn.clicked.connect(self._remove_race)
        races_buttons.addWidget(self.remove_race_btn)
        self.details_layout.addLayout(races_buttons)

        classes_label = QLabel("Suitable Classes")
        classes_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(classes_label)
        self.classes_list = QListWidget()
        self.classes_list.setMinimumHeight(60)
        self.classes_list.itemDoubleClicked.connect(self._edit_class)
        self.details_layout.addWidget(self.classes_list)
        classes_buttons = QHBoxLayout()
        self.add_class_btn = QPushButton("Add Class")
        self.add_class_btn.clicked.connect(self._add_class)
        classes_buttons.addWidget(self.add_class_btn)
        self.remove_class_btn = QPushButton("Remove Class")
        self.remove_class_btn.clicked.connect(self._remove_class)
        classes_buttons.addWidget(self.remove_class_btn)
        self.details_layout.addLayout(classes_buttons)

        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_current_origin)
        self.save_btn.setEnabled(False)
        save_layout.addWidget(self.save_btn)
        self.details_layout.addLayout(save_layout)

        splitter.addWidget(right_panel)
        self._disable_details()
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        # Assistant integration methods added at end of class

        # Add imports for new dialogs
        from ..dialogs.skill_selection_dialog import SkillSelectionDialog
        from ..dialogs.item_selection_dialog import ItemSelectionDialog
        self.SkillSelectionDialog = SkillSelectionDialog
        self.ItemSelectionDialog = ItemSelectionDialog

    # Renamed method to accept OriginManager
    def set_managers(self, origin_manager: OriginManager, location_manager: LocationManager, quest_manager: Optional[QuestManager] = None) -> None:
        """
        Set the origin, location and quest managers to use.

        Args:
            origin_manager: The origin manager.
            location_manager: The location manager.
            quest_manager: Optional quest manager to provide quest references.
        """
        self.origin_manager = origin_manager
        self.location_manager = location_manager
        self.quest_manager = quest_manager

        # Refresh origin list
        self._refresh_origin_list() # Renamed method

    def _refresh_origin_list(self) -> None: # Renamed method
        """Refresh the origin list from the manager."""
        # Clear list
        self.origin_list.clear()

        # Add all origins
        for origin_id, origin in self.origin_manager.origins.items(): # Use origin_manager.origins
            item = QListWidgetItem(origin.name)
            item.setData(Qt.UserRole, origin_id)
            self.origin_list.addItem(item)

        # Sort alphabetically
        self.origin_list.sortItems()

        # Select the first item if available
        if self.origin_list.count() > 0:
            self.origin_list.setCurrentRow(0)
        else: # Ensure details are disabled if list is empty
             self._disable_details()
             self.remove_origin_btn.setEnabled(False)

    # Renamed method
    def _on_origin_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        """
        Handle origin selection change.

        Args:
            current: The current selected item, or None.
            previous: The previously selected item, or None.
        """
        if current:
            origin_id = current.data(Qt.UserRole)
            origin = self.origin_manager.get_origin(origin_id) # Use origin_manager

            if origin:
                self._load_origin(origin) # Renamed method
                self.remove_origin_btn.setEnabled(True)
                return

        # No valid selection
        self._disable_details()
        self.remove_origin_btn.setEnabled(False)

    def _load_origin(self, origin: Origin) -> None:
        """
        Load an origin into the editor.

        Args:
            origin: The origin to load.
        """
        try:
            self.current_origin = origin

            self.name_label.setText(origin.name)
            self.desc_label.setText(origin.description)

            if origin.starting_location_id and self.location_manager and self.location_manager.locations:
                location = self.location_manager.locations.get(origin.starting_location_id)
                self.location_label.setText(f"{location.name} ({location.type})" if location else f"(Unknown: {origin.starting_location_id})")
            else:
                self.location_label.setText("(None)")

            if hasattr(self, 'culture_label'):
                self.culture_label.setText(origin.starting_culture_id if origin.starting_culture_id else "(None - uses location default)")

            self.intro_label.setText(origin.introduction_text)

            self.skills_list.clear()
            if hasattr(origin, 'skill_proficiencies'):
                for skill_name in origin.skill_proficiencies: # skill_proficiencies stores names
                    # Use helper to potentially get a more descriptive display if needed in future
                    display_text = self._get_skill_display_name(skill_name)
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, skill_name) # Store the name as data for removal
                    self.skills_list.addItem(item)

            self.traits_table.setRowCount(0)
            if hasattr(origin, 'origin_traits'):
                self.traits_table.setRowCount(len(origin.origin_traits))
                for row, trait in enumerate(origin.origin_traits):
                    name_item = QTableWidgetItem(trait.name)
                    desc_item = QTableWidgetItem(trait.description)
                    self.traits_table.setItem(row, 0, name_item)
                    self.traits_table.setItem(row, 1, desc_item)
                    name_item.setData(Qt.UserRole, row)

            self.items_list.clear()
            if hasattr(origin, 'starting_items'): # Check if attribute exists
                for item_id in origin.starting_items:
                    # Use helper to potentially get item name if available in future
                    display_text = self._get_item_display_name(item_id)
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, item_id) # Store the ID for removal
                    self.items_list.addItem(item)

            self.quests_list.clear()
            for quest_id in origin.initial_quests:
                display_text = self._get_quest_display_name(quest_id)
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, quest_id)
                self.quests_list.addItem(item)

            self.races_list.clear()
            for race_name in origin.suitable_races:
                item = QListWidgetItem(race_name)
                self.races_list.addItem(item)

            self.classes_list.clear()
            for class_name in origin.suitable_classes:
                item = QListWidgetItem(class_name)
                self.classes_list.addItem(item)

            self._enable_details()
            self.save_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"Error loading origin {origin.name}: {str(e)}", exc_info=True)
            QMessageBox.warning(
                self,
                "Error Loading Origin",
                f"There was an error loading the origin '{origin.name}':\n\n{str(e)}\n\nSome data may not be displayed correctly."
            )
            self._enable_details()
            self.save_btn.setEnabled(True)

    def _disable_details(self) -> None:
        """Disable all detail controls."""
        self.current_origin = None

        self.name_label.clear()
        self.desc_label.clear()
        self.location_label.clear()
        if hasattr(self, 'culture_label'): self.culture_label.clear()
        self.intro_label.clear()

        self.skills_list.clear()
        self.traits_table.setRowCount(0)
        self.items_list.clear()
        self.quests_list.clear()
        self.races_list.clear()
        self.classes_list.clear()

        self.skills_list.setEnabled(False)
        self.traits_table.setEnabled(False)
        self.items_list.setEnabled(False)
        self.quests_list.setEnabled(False)
        self.races_list.setEnabled(False)
        self.classes_list.setEnabled(False)

        self.add_skill_btn.setEnabled(False)
        # self.remove_skill_btn.setEnabled(False) # Removed this line
        self.add_trait_btn.setEnabled(False)
        self.edit_trait_btn.setEnabled(False)
        self.remove_trait_btn.setEnabled(False)
        self.add_item_btn.setEnabled(False)
        # self.remove_item_btn.setEnabled(False) # Removed this line
        self.manage_quests_btn.setEnabled(False)
        self.remove_quest_btn.setEnabled(False)
        self.add_race_btn.setEnabled(False)
        self.remove_race_btn.setEnabled(False)
        self.add_class_btn.setEnabled(False)
        self.remove_class_btn.setEnabled(False)

        self.save_btn.setEnabled(False)

    def _enable_details(self) -> None:
        """Enable all detail controls."""
        self.skills_list.setEnabled(True)
        self.traits_table.setEnabled(True)
        self.items_list.setEnabled(True)
        self.quests_list.setEnabled(True)
        self.races_list.setEnabled(True)
        self.classes_list.setEnabled(True)

        self.add_skill_btn.setEnabled(True)
        # self.remove_skill_btn.setEnabled(True) # Removed this line
        self.add_trait_btn.setEnabled(True)
        self.edit_trait_btn.setEnabled(True)
        self.remove_trait_btn.setEnabled(True)
        self.add_item_btn.setEnabled(True)
        # self.remove_item_btn.setEnabled(True) # Removed this line
        self.manage_quests_btn.setEnabled(True)
        self.remove_quest_btn.setEnabled(True)
        self.add_race_btn.setEnabled(True)
        self.remove_race_btn.setEnabled(True)
        self.add_class_btn.setEnabled(True)
        self.remove_class_btn.setEnabled(True)
        # Save button enabled separately when changes occur

    def _save_current_origin(self) -> None:
        """Save the current origin to the manager."""
        if not self.current_origin:
            return

        # Basic fields (name, desc, location_id, culture_id, intro_text) are updated via their respective edit dialogs/methods
        # which directly modify self.current_origin and set self.save_btn.setEnabled(True).

        # Update skill proficiencies (skill names are stored)
        new_skill_proficiencies = []
        for i in range(self.skills_list.count()):
            item = self.skills_list.item(i)
            # The text of the item IS the skill name
            new_skill_proficiencies.append(item.text())
        self.current_origin.skill_proficiencies = sorted(list(set(new_skill_proficiencies))) # Ensure unique and sorted

        # Update origin traits
        new_origin_traits = []
        for row in range(self.traits_table.rowCount()):
            name_item = self.traits_table.item(row, 0)
            desc_item = self.traits_table.item(row, 1)
            if name_item and desc_item and name_item.text().strip(): # Ensure name is not empty
                new_origin_traits.append(
                    OriginTrait(name=name_item.text().strip(), description=desc_item.text().strip())
                )
        self.current_origin.origin_traits = new_origin_traits


        # Update starting items (item IDs are stored)
        new_starting_items = []
        for i in range(self.items_list.count()):
            item = self.items_list.item(i)
            # The data role Qt.UserRole stores the item_id
            item_id = item.data(Qt.UserRole)
            if item_id: # Make sure we have an ID
                new_starting_items.append(item_id)
        self.current_origin.starting_items = sorted(list(set(new_starting_items))) # Ensure unique and sorted

        # Update initial quests
        new_initial_quests = []
        for i in range(self.quests_list.count()):
            item = self.quests_list.item(i)
            qid = item.data(Qt.UserRole) or item.text()
            if isinstance(qid, str) and qid.strip():
                new_initial_quests.append(qid.strip())
        self.current_origin.initial_quests = sorted(list(set(new_initial_quests)))

        # Update suitable races
        new_suitable_races = []
        for i in range(self.races_list.count()):
            item = self.races_list.item(i)
            new_suitable_races.append(item.text())
        self.current_origin.suitable_races = sorted(list(set(new_suitable_races)))

        # Update suitable classes
        new_suitable_classes = []
        for i in range(self.classes_list.count()):
            item = self.classes_list.item(i)
            new_suitable_classes.append(item.text())
        self.current_origin.suitable_classes = sorted(list(set(new_suitable_classes)))

        self.origin_manager.add_origin(self.current_origin)
        self.save_btn.setEnabled(False)
        self._refresh_origin_list()

        for i in range(self.origin_list.count()):
            item = self.origin_list.item(i)
            if item.data(Qt.UserRole) == self.current_origin.id:
                self.origin_list.setCurrentItem(item)
                break
        self.origin_modified.emit()
        logger.info(f"Saved origin: {self.current_origin.name} ({self.current_origin.id})")

    # ===== Assistant integration =====
    def get_assistant_context(self):
        from assistant.context import AssistantContext
        allowed = [
            "/skill_proficiencies",
            "/origin_traits",
            "/starting_items",
            "/initial_quests",
            "/suitable_races",
            "/suitable_classes",
            "/introduction_text",
            "/starting_location_id",
            "/starting_culture_id",
            "/description",
            "/name",
        ]
        content = self.current_origin.to_dict() if self.current_origin else None
        return AssistantContext(
            domain="origins",
            selection_id=self.current_origin.id if self.current_origin else None,
            content=content,
            schema=None,
            allowed_paths=allowed,
        )

    def get_domain_examples(self):
        if self.origin_manager.origins:
            first = next(iter(self.origin_manager.origins.values()))
            return [first.to_dict()]
        return []

    def get_reference_catalogs(self):
        # Provide references to reduce hallucinations and enforce valid IDs
        quests = []
        quest_titles = {}
        try:
            if self.quest_manager and getattr(self.quest_manager, 'quests', None):
                quests = list(self.quest_manager.quests.keys())
                # Build id->title mapping for better LLM grounding
                for qid, q in self.quest_manager.quests.items():
                    quest_titles[qid] = getattr(q, 'title', '')
        except Exception:
            quests = []
            quest_titles = {}
        locations = []
        try:
            if self.location_manager and getattr(self.location_manager, 'locations', None):
                locations = list(self.location_manager.locations.keys())
        except Exception:
            locations = []
        existing_names = []
        try:
            if self.origin_manager and getattr(self.origin_manager, 'origins', None):
                existing_names = sorted({o.name for o in self.origin_manager.origins.values() if o and o.name})
        except Exception:
            existing_names = []
        return {
            "quest_ids": quests,
            "quest_titles": quest_titles,
            "location_ids": locations,
            "existing_names": existing_names,
            # Guidance to LLMs consuming this: initial_quests MUST be array of quest IDs (strings)
            "constraints": {"initial_quests_format": "array_of_ids"},
        }

    def apply_assistant_patch(self, patch_ops):
        from assistant.patching import apply_patch_with_validation
        ctx = self.get_assistant_context()
        if not ctx.content:
            return False, "No origin selected."
        ok, msg, new_content = apply_patch_with_validation(ctx, ctx.content, patch_ops)
        if not ok:
            return False, msg
        try:
            new_content = self._sanitize_origin_payload(new_content)
            updated = Origin.from_dict(new_content)
            updated.id = self.current_origin.id
            self.origin_manager.add_origin(updated)
            self._load_origin(updated)
            self.origin_modified.emit()
            return True, "OK"
        except Exception as e:
            return False, f"Failed to apply: {e}"

    def create_entry_from_llm(self, entry: dict):
        try:
            proposed_name = (entry.get("name") or "New Origin").strip()
            existing_names = {o.name for o in self.origin_manager.origins.values()}
            name = proposed_name
            suffix = 1
            while name in existing_names:
                name = f"{proposed_name} ({suffix})"
                suffix += 1
            desc = entry.get("description", "")
            location_id = entry.get("starting_location_id", "")
            new_origin = Origin.create_new(name, desc, location_id)
            tmp = new_origin.to_dict()
            tmp.update({k: v for k, v in entry.items() if k != "id" and k != "name"})
            tmp["name"] = name
            tmp = self._sanitize_origin_payload(tmp)
            new_obj = Origin.from_dict(tmp)
            new_obj.id = new_origin.id
            self.origin_manager.add_origin(new_obj)
            self._refresh_origin_list()
            # select
            for i in range(self.origin_list.count()):
                it = self.origin_list.item(i)
                if self.origin_manager.get_origin(it.data(Qt.UserRole)).id == new_obj.id:
                    self.origin_list.setCurrentItem(it)
                    break
            self.origin_modified.emit()
            return True, "Created", new_obj.id
        except Exception as e:
            return False, f"Failed to create: {e}", None

    def _manage_skill_proficiencies(self):
        if not self.current_origin:
            return

        current_skill_names = [self.skills_list.item(i).text() for i in range(self.skills_list.count())]

        dialog = self.SkillSelectionDialog(self, existing_skills=current_skill_names)
        if dialog.exec() == QDialog.Accepted:
            selected_skills = dialog.get_selected_skills() # Returns list of skill names

            # Update the QListWidget
            self.skills_list.clear()
            for skill_name in sorted(selected_skills):
                item = QListWidgetItem(skill_name)
                item.setData(Qt.UserRole, skill_name) # Store name as data for consistency
                self.skills_list.addItem(item)

            self.save_btn.setEnabled(True)
            logger.debug(f"Updated skill proficiencies for origin {self.current_origin.id} to: {selected_skills}")

    def _manage_starting_items(self):
        if not self.current_origin:
            return

        current_item_ids = [self.items_list.item(i).data(Qt.UserRole) for i in range(self.items_list.count())]

        # Path to origin_items.json relative to project root
        origin_items_path = "config/items/origin_items.json"
        dialog = self.ItemSelectionDialog(self, existing_item_ids=current_item_ids, item_file_path=origin_items_path)

        if dialog.exec() == QDialog.Accepted:
            selected_item_ids = dialog.get_selected_item_ids() # Returns list of item IDs

            # Update the QListWidget
            self.items_list.clear()
            for item_id in sorted(selected_item_ids):
                display_text = self._get_item_display_name(item_id) # Use helper for display
                list_item = QListWidgetItem(display_text)
                list_item.setData(Qt.UserRole, item_id) # Store actual ID
                self.items_list.addItem(list_item)

            self.save_btn.setEnabled(True)
            # Persist immediately to the model for convenience (parity with Manage Quests)
            self._save_current_origin()
            logger.debug(f"Updated starting items for origin {self.current_origin.id} to: {selected_item_ids} and auto-saved.")

    def _edit_starting_item(self, item: QListWidgetItem):
        """Handles double-click on a starting item: opens manage dialog."""
        if not self.current_origin or not item:
            return
        # Re-purpose the "Manage Items" dialog for editing
        self._manage_starting_items()

    def _edit_skill_proficiency(self, item: QListWidgetItem):
        """Handles double-click on a skill proficiency: opens manage dialog."""
        if not self.current_origin or not item:
            return
        # Re-purpose the "Manage Skills" dialog for editing (which essentially is managing the list)
        self._manage_skill_proficiencies()

    def _add_origin(self) -> None: # Renamed method
        """Add a new origin."""
        # Create new origin (use a default location if available)
        default_location_id = ""
        if self.location_manager and self.location_manager.locations:
            default_location_id = next(iter(self.location_manager.locations.keys()), "")

        # Assume Origin.create_new takes name, description, location_id
        # Need to update Origin model later
        origin = Origin.create_new("New Origin", "Description of the origin", default_location_id)

        # Add to manager
        self.origin_manager.add_origin(origin) # Use origin_manager

        # Refresh list
        self._refresh_origin_list() # Renamed method

        # Find and select the new origin
        for i in range(self.origin_list.count()):
            item = self.origin_list.item(i)
            if item.data(Qt.UserRole) == origin.id:
                self.origin_list.setCurrentItem(item)
                break

        # Trigger name edit dialog for immediate editing
        self._edit_name(None)

        # Emit modified signal
        self.origin_modified.emit() # Renamed signal

        # Log
        logger.info(f"Added new origin: {origin.id}")

    def _remove_origin(self) -> None: # Renamed method
        """Remove the selected origin."""
        current_item = self.origin_list.currentItem()
        if not current_item:
            return

        origin_id = current_item.data(Qt.UserRole)
        origin = self.origin_manager.get_origin(origin_id) # Use origin_manager

        if not origin:
            return

        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the origin '{origin.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result != QMessageBox.Yes:
            return

        # Remove from manager
        self.origin_manager.remove_origin(origin_id) # Use origin_manager

        # Refresh list
        self._refresh_origin_list() # Renamed method

        # Emit modified signal
        self.origin_modified.emit() # Renamed signal

        # Log
        logger.info(f"Removed origin: {origin_id}")

    def _add_trait(self):
        if not self.current_origin: return
        dialog = OriginTraitDialog(self)
        if dialog.exec() == QDialog.Accepted:
            new_trait = dialog.get_trait()
            row = self.traits_table.rowCount()
            self.traits_table.insertRow(row)
            name_item = QTableWidgetItem(new_trait.name)
            desc_item = QTableWidgetItem(new_trait.description)
            self.traits_table.setItem(row, 0, name_item)
            self.traits_table.setItem(row, 1, desc_item)
            name_item.setData(Qt.UserRole, row) # Store index for editing
            self.save_btn.setEnabled(True)
            logger.debug(f"Added origin trait: {new_trait.name}")

    def _edit_selected_trait(self):
         current_row = self.traits_table.currentRow()
         if current_row >= 0:
             self._edit_trait_row(self.traits_table.item(current_row, 0)) # Pass the name item

    def _edit_trait_row(self, item):
        if not self.current_origin or not item: return
        row = item.row()
        name_item = self.traits_table.item(row, 0)
        desc_item = self.traits_table.item(row, 1)

        if not name_item or not desc_item: return # Should not happen

        # Create a temporary trait object to pass to dialog
        current_trait = OriginTrait(name=name_item.text(), description=desc_item.text())

        dialog = OriginTraitDialog(self, current_trait)
        if dialog.exec() == QDialog.Accepted:
            edited_trait = dialog.get_trait()
            name_item.setText(edited_trait.name)
            desc_item.setText(edited_trait.description)
            self.save_btn.setEnabled(True)
            logger.debug(f"Edited origin trait at row {row} to: {edited_trait.name}")


    def _remove_trait(self):
        current_row = self.traits_table.currentRow()
        if current_row >= 0:
            removed_name = self.traits_table.item(current_row, 0).text() if self.traits_table.item(current_row, 0) else "Unknown"
            self.traits_table.removeRow(current_row)
            self.save_btn.setEnabled(True)
            logger.debug(f"Removed origin trait: {removed_name}")

    def _add_quest(self) -> None:
        # Deprecated in favor of _manage_initial_quests
        self._manage_initial_quests()

    def _remove_quest(self) -> None:
        """Remove the selected initial quest."""
        item = self.quests_list.currentItem()
        if not item:
            return

        # Remove item
        self.quests_list.takeItem(self.quests_list.row(item))

        # Mark as modified
        self.save_btn.setEnabled(True)

        # Log
        logger.debug(f"Removed initial quest: {item.text()}")

    def _manage_initial_quests(self) -> None:
        """Open selection dialog to manage initial quests from QuestManager."""
        if not self.current_origin:
            return
        # Collect available quests
        available: list[tuple[str, str]] = []
        if self.quest_manager and getattr(self.quest_manager, 'quests', None):
            for qid, q in self.quest_manager.quests.items():
                title = getattr(q, 'title', '')
                available.append((qid, title))
        # Existing selections: use quest IDs from item data if available
        existing = []
        for i in range(self.quests_list.count()):
            it = self.quests_list.item(i)
            qid = it.data(Qt.UserRole)
            if isinstance(qid, str) and qid:
                existing.append(qid)

        # Lazy import dialog
        try:
            from ..dialogs.quest_selection_dialog import QuestSelectionDialog
        except Exception:
            from ui.dialogs.quest_selection_dialog import QuestSelectionDialog  # fallback absolute

        dlg = QuestSelectionDialog(self, available_quests=available, existing_ids=existing)
        if dlg.exec() == QDialog.Accepted:
            selected_ids = dlg.get_selected_ids()
            # Update list with display names and store IDs
            self.quests_list.clear()
            for qid in sorted(set(selected_ids)):
                text = self._get_quest_display_name(qid)
                it = QListWidgetItem(text)
                it.setData(Qt.UserRole, qid)
                self.quests_list.addItem(it)
            self.save_btn.setEnabled(True)
            # Persist immediately to the model for convenience
            self._save_current_origin()
            logger.debug("Updated initial quests for origin %s to: %s and auto-saved.", self.current_origin.id, selected_ids)

    def _add_race(self) -> None:
        """Add a suitable race."""
        if not self.current_origin:
            return

        # Create simple input dialog
        race_name, ok = QInputDialog.getText(
            self,
            "Add Suitable Race",
            "Enter race name:"
        )

        if ok and race_name.strip():
            # Add to list
            self.races_list.addItem(race_name.strip())

            # Mark as modified
            self.save_btn.setEnabled(True)

            # Log
            logger.debug(f"Added suitable race: {race_name}")

    def _remove_race(self) -> None:
        """Remove the selected suitable race."""
        item = self.races_list.currentItem()
        if not item:
            return

        # Remove item
        self.races_list.takeItem(self.races_list.row(item))

        # Mark as modified
        self.save_btn.setEnabled(True)

        # Log
        logger.debug(f"Removed suitable race: {item.text()}")

    def _add_class(self) -> None:
        """Add a suitable class."""
        if not self.current_origin:
            return

        # Create simple input dialog
        class_name, ok = QInputDialog.getText(
            self,
            "Add Suitable Class",
            "Enter class name:"
        )

        if ok and class_name.strip():
            # Add to list
            self.classes_list.addItem(class_name.strip())

            # Mark as modified
            self.save_btn.setEnabled(True)

            # Log
            logger.debug(f"Added suitable class: {class_name}")

    def _remove_class(self) -> None:
        """Remove the selected suitable class."""
        item = self.classes_list.currentItem()
        if not item:
            return

        # Remove item
        self.classes_list.takeItem(self.classes_list.row(item))

        # Mark as modified
        self.save_btn.setEnabled(True)

        # Log
        logger.debug(f"Removed suitable class: {item.text()}")

    # --- Editing Methods (Double-Click Handlers) ---

    def _edit_name(self, event):
        """Edit origin name on double-click."""
        if not self.current_origin:
            return

        name, ok = QInputDialog.getText(
            self,
            "Edit Origin Name",
            "Enter origin name:",
            QLineEdit.Normal,
            self.current_origin.name
        )

        if ok and name.strip():
            self.current_origin.name = name.strip()
            self.name_label.setText(name.strip())
            self.save_btn.setEnabled(True)
            # Also update the list widget item text
            current_item = self.origin_list.currentItem()
            if current_item:
                current_item.setText(name.strip())
                self.origin_list.sortItems() # Re-sort after name change
            logger.debug(f"Updated origin name to: {name}")

    def _edit_description(self, event):
        """Edit origin description on double-click."""
        if not self.current_origin:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Origin Description")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(200) # Adjusted height

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setPlainText(self.current_origin.description)
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(dialog.accept)
        save_btn.setDefault(True)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            description = text_edit.toPlainText().strip()
            self.current_origin.description = description
            self.desc_label.setText(description)
            self.save_btn.setEnabled(True)
            logger.debug("Updated origin description")

    def _edit_location(self, event):
        """Edit starting location on double-click."""
        if not self.current_origin or not self.location_manager or not self.location_manager.locations:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Starting Location")
        dialog.setMinimumWidth(300)

        layout = QVBoxLayout(dialog)

        combo = QComboBox()
        # Add a "(None)" option
        combo.addItem("(None)", "")
        for location_id, location in self.location_manager.locations.items():
            combo.addItem(f"{location.name} ({location.type})", location_id)
            if location_id == self.current_origin.starting_location_id:
                combo.setCurrentIndex(combo.count() - 1)

        layout.addWidget(combo)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(dialog.accept)
        save_btn.setDefault(True)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            location_id = combo.currentData()
            location = self.location_manager.locations.get(location_id) if location_id else None
            location_display = f"{location.name} ({location.type})" if location else "(None)"

            self.current_origin.starting_location_id = location_id
            self.location_label.setText(location_display)
            self.save_btn.setEnabled(True)
            logger.debug(f"Updated starting location to: {location_display} (ID: {location_id})")


    def _edit_culture(self, event): # NEW METHOD
        """Edit starting culture on double-click."""
        # TODO: Implement this - Requires access to CultureManager
        # Similar logic to _edit_location, using culture data
        # Add a "(None)" option to allow clearing the culture ID
        if not self.current_origin: return
        QMessageBox.information(self, "Edit Culture", "Culture editing not yet implemented.")
        logger.warning("Attempted to edit starting culture - functionality not implemented.")


    def _edit_introduction(self, event):
        """Edit introduction text on double-click."""
        if not self.current_origin:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Introduction Text")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(300) # Adjusted height

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setPlainText(self.current_origin.introduction_text)
        text_edit.setPlaceholderText("Enter introduction text that will be shown to the player at the start of the game...")
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(dialog.accept)
        save_btn.setDefault(True)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            intro_text = text_edit.toPlainText().strip()
            self.current_origin.introduction_text = intro_text
            self.intro_label.setText(intro_text)
            self.save_btn.setEnabled(True)
            logger.debug("Updated introduction text")

    def _edit_quest(self, item):
        """Edit initial quests via the Manage dialog on double-click."""
        if not self.current_origin:
            return
        self._manage_initial_quests()

    def _edit_race(self, item):
        """Edit a suitable race on double-click."""
        if not self.current_origin:
            return

        current_text = item.text()
        new_text, ok = QInputDialog.getText(
            self,
            "Edit Suitable Race",
            "Enter race name:",
            QLineEdit.Normal,
            current_text
        )

        if ok and new_text.strip():
            item.setText(new_text.strip())
            self.save_btn.setEnabled(True)
            logger.debug(f"Updated race from '{current_text}' to '{new_text}'")

    def _edit_class(self, item):
        """Edit a suitable class on double-click."""
        if not self.current_origin:
            return

        current_text = item.text()
        new_text, ok = QInputDialog.getText(
            self,
            "Edit Suitable Class",
            "Enter class name:",
            QLineEdit.Normal,
            current_text
        )

        if ok and new_text.strip():
            item.setText(new_text.strip())
            self.save_btn.setEnabled(True)
            logger.debug(f"Updated class from '{current_text}' to '{new_text}'")

    def refresh(self):
        """Refresh the editor data."""
        self._refresh_origin_list()

    def _get_skill_display_name(self, skill_id_or_name: str) -> str:
        """
        Attempts to find a display name for a skill.
        If skills.json is loaded and contains the ID, use its name.
        Otherwise, return the input string itself (which might already be a name).
        This is a helper for consistent display if skills are sometimes stored by ID
        and sometimes by name. For this task, skill_proficiencies store names.
        """
        # This method is more of a placeholder if skill_ids were stored.
        # Since skill_proficiencies store names directly, this might not be strictly needed
        # but can be useful if a future refactor stores IDs.
        # For now, it will mostly just return the input name.
        # A more robust version would involve loading skills.json here if not already globally available.
        return skill_id_or_name
    
    def _get_item_display_name(self, item_id: str) -> str:
        """
        Attempts to find a display name for an item ID.
        For simplicity, this currently returns the ID itself.
        A more complete implementation would load item data (e.g., from origin_items.json)
        and look up the item's actual name.
        """
        # TODO: Enhance this to load item data and return actual item name.
        # This would require loading the relevant item file.
        # For now, just return the ID. The ItemSelectionDialog shows names.
        return item_id

    def _get_quest_display_name(self, quest_id: str) -> str:
        """Resolve a quest's display name as 'Title (id)' if available."""
        try:
            if self.quest_manager and getattr(self.quest_manager, 'quests', None):
                q = self.quest_manager.quests.get(quest_id)
                if q and getattr(q, 'title', None):
                    return f"{q.title} ({quest_id})"
        except Exception:
            pass
        return quest_id

    # ---- Assistant sanitizers ----
    def _sanitize_origin_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return payload
        sanitized = dict(payload)

        def _to_str_list(value):
            out = []
            if isinstance(value, list):
                for el in value:
                    if isinstance(el, str):
                        s = el.strip()
                        if s:
                            out.append(s)
                    elif isinstance(el, dict):
                        v = el.get("id")
                        if isinstance(v, str) and v.strip():
                            out.append(v.strip())
            return out

        # Coerce list-like fields to list[str]
        for key in ("initial_quests", "starting_items", "suitable_races", "suitable_classes", "skill_proficiencies"):
            if key in sanitized:
                sanitized[key] = _to_str_list(sanitized.get(key))

        # For initial_quests: dedupe, preserve order, and filter to known IDs
        if "initial_quests" in sanitized:
            seen = set()
            filtered: List[str] = []
            allowed_ids = set(self.quest_manager.quests.keys()) if (self.quest_manager and getattr(self.quest_manager, 'quests', None)) else None
            for qid in sanitized["initial_quests"]:
                if not isinstance(qid, str) or not qid.strip():
                    continue
                qid = qid.strip()
                if allowed_ids is not None and qid not in allowed_ids:
                    # Skip unknown quest IDs
                    continue
                if qid not in seen:
                    seen.add(qid)
                    filtered.append(qid)
            sanitized["initial_quests"] = filtered

        # Normalize simple strings
        for key in ("starting_location_id", "starting_culture_id", "name", "description", "introduction_text"):
            if key in sanitized and sanitized[key] is not None:
                sanitized[key] = str(sanitized[key])

        return sanitized
