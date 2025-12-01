# world_configurator/ui/editors/race_editor.py
"""
Race editor component for the World Configurator Tool.
"""

import copy
from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QSpinBox,
    QDialog, QMessageBox, QSplitter, QScrollArea, QFrame, QTabWidget,
    QGridLayout, QInputDialog
)

from ui.dialogs.base_dialog import BaseDialog
from models.base_models import Race, RaceTrait
from models.world_data import RaceManager
from world_configurator.utils.logging_setup import setup_logging

logger = setup_logging("world_configurator.ui.race_editor")

# --- Helper Dialogs ---

class TraitDialog(BaseDialog):
    """Dialog for editing a RaceTrait."""
    def __init__(self, parent=None, trait: Optional[RaceTrait] = None):
        super().__init__(parent)
        self.setWindowTitle("Race Trait")
        self.setMinimumWidth(400)

        self.trait = trait or RaceTrait(name="New Trait", description="")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.trait.name)
        form.addRow("Name:", self.name_edit)

        self.desc_edit = QTextEdit(self.trait.description)
        self.desc_edit.setMinimumHeight(80)
        form.addRow("Description:", self.desc_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def get_trait(self) -> RaceTrait:
        self.trait.name = self.name_edit.text()
        self.trait.description = self.desc_edit.toPlainText()
        return self.trait

# --- Main Race Dialog ---

class RaceDialog(QDialog):
    """Dialog for editing a Race."""
    def __init__(self, parent=None, race: Optional[Race] = None):
        super().__init__(parent)
        self.setWindowTitle("Race Editor")
        self.setMinimumWidth(600)
        self.setMinimumHeight(550)

        self.race = copy.deepcopy(race) if race else Race.create_new("New Race", "")
        self.possible_stats = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Basic Info Tab
        basic_tab = QWidget()
        self.tabs.addTab(basic_tab, "Basic Info")
        basic_layout = QFormLayout(basic_tab)
        self.name_edit = QLineEdit(self.race.name)
        basic_layout.addRow("Name:", self.name_edit)
        self.desc_edit = QTextEdit(self.race.description)
        self.desc_edit.setMinimumHeight(100)
        basic_layout.addRow("Description:", self.desc_edit)

        # Stat Modifiers Tab
        stats_tab = QWidget()
        self.tabs.addTab(stats_tab, "Stat Modifiers")
        stats_layout = QGridLayout(stats_tab)
        self.stat_spins: Dict[str, QSpinBox] = {}
        for i, stat in enumerate(self.possible_stats):
            label = QLabel(f"{stat}:")
            spin = QSpinBox()
            spin.setRange(-5, 5) # Example range
            spin.setValue(self.race.stat_modifiers.get(stat, 0))
            self.stat_spins[stat] = spin
            row, col = divmod(i, 3) # Arrange in 2 rows
            stats_layout.addWidget(label, row, col * 2)
            stats_layout.addWidget(spin, row, col * 2 + 1)
        stats_layout.setColumnStretch(1, 1)
        stats_layout.setColumnStretch(3, 1)
        stats_layout.setColumnStretch(5, 1)

        # Traits Tab
        traits_tab = QWidget()
        self.tabs.addTab(traits_tab, "Traits")
        traits_layout = QVBoxLayout(traits_tab)
        traits_layout.addWidget(QLabel("Racial Traits:"))
        self.traits_list = QListWidget()
        self.traits_list.itemDoubleClicked.connect(self._edit_trait)
        traits_layout.addWidget(self.traits_list)
        for trait in self.race.traits:
            self._add_trait_to_list(trait)
        trait_btns = QHBoxLayout()
        add_trait_btn = QPushButton("Add Trait")
        add_trait_btn.clicked.connect(self._add_trait)
        edit_trait_btn = QPushButton("Edit Trait")
        edit_trait_btn.clicked.connect(lambda: self._edit_trait(self.traits_list.currentItem()))
        remove_trait_btn = QPushButton("Remove Trait")
        remove_trait_btn.clicked.connect(self._remove_trait)
        trait_btns.addWidget(add_trait_btn)
        trait_btns.addWidget(edit_trait_btn)
        trait_btns.addWidget(remove_trait_btn)
        traits_layout.addLayout(trait_btns)

        # Recommended Classes Tab
        rec_class_tab = QWidget()
        self.tabs.addTab(rec_class_tab, "Recommended Classes")
        rec_class_layout = QVBoxLayout(rec_class_tab)
        rec_class_layout.addWidget(QLabel("Recommended Classes:"))
        self.rec_class_list = QListWidget()
        rec_class_layout.addWidget(self.rec_class_list)
        for class_name in self.race.recommended_classes:
            self.rec_class_list.addItem(QListWidgetItem(class_name))
        rec_class_btns = QHBoxLayout()
        add_rec_btn = QPushButton("Add Class")
        add_rec_btn.clicked.connect(self._add_rec_class)
        remove_rec_btn = QPushButton("Remove Class")
        remove_rec_btn.clicked.connect(self._remove_rec_class)
        rec_class_btns.addWidget(add_rec_btn)
        rec_class_btns.addWidget(remove_rec_btn)
        rec_class_layout.addLayout(rec_class_btns)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def _add_trait_to_list(self, trait: RaceTrait):
        item = QListWidgetItem(f"{trait.name}")
        item.setToolTip(trait.description)
        item.setData(Qt.UserRole, trait)
        self.traits_list.addItem(item)
        self.traits_list.sortItems()

    def _add_trait(self):
        dialog = TraitDialog(self)
        if dialog.exec() == QDialog.Accepted:
            new_trait = dialog.get_trait()
            # Check for duplicate names
            for i in range(self.traits_list.count()):
                if self.traits_list.item(i).data(Qt.UserRole).name == new_trait.name:
                    QMessageBox.warning(self, "Duplicate Trait", f"A trait named '{new_trait.name}' already exists.")
                    return
            self._add_trait_to_list(new_trait)

    def _edit_trait(self, item: Optional[QListWidgetItem]):
        if not item:
            item = self.traits_list.currentItem()
        if not item: return

        original_trait = item.data(Qt.UserRole)
        dialog = TraitDialog(self, copy.deepcopy(original_trait))
        if dialog.exec() == QDialog.Accepted:
            updated_trait = dialog.get_trait()
            # Check if name changed and conflicts
            if original_trait.name != updated_trait.name:
                 for i in range(self.traits_list.count()):
                    existing_trait = self.traits_list.item(i).data(Qt.UserRole)
                    if self.traits_list.item(i) != item and existing_trait.name == updated_trait.name:
                        QMessageBox.warning(self, "Duplicate Trait", f"A trait named '{updated_trait.name}' already exists.")
                        return

            item.setText(updated_trait.name)
            item.setToolTip(updated_trait.description)
            item.setData(Qt.UserRole, updated_trait)
            self.traits_list.sortItems()

    def _remove_trait(self):
        item = self.traits_list.currentItem()
        if not item: return
        result = QMessageBox.question(self, "Confirm Removal", "Remove this trait?", QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            self.traits_list.takeItem(self.traits_list.row(item))

    def _add_rec_class(self):
        class_name, ok = QInputDialog.getText(self, "Add Recommended Class", "Class Name:")
        if ok and class_name:
            class_name = class_name.strip()
            if class_name and not self.rec_class_list.findItems(class_name, Qt.MatchExactly):
                self.rec_class_list.addItem(QListWidgetItem(class_name))
                self.rec_class_list.sortItems()

    def _remove_rec_class(self):
        item = self.rec_class_list.currentItem()
        if not item: return
        result = QMessageBox.question(self, "Confirm Removal", "Remove this recommended class?", QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            self.rec_class_list.takeItem(self.rec_class_list.row(item))

    def get_race(self) -> Race:
        self.race.name = self.name_edit.text()
        self.race.description = self.desc_edit.toPlainText()

        self.race.stat_modifiers = {stat: spin.value() for stat, spin in self.stat_spins.items()}

        self.race.traits = []
        for i in range(self.traits_list.count()):
            self.race.traits.append(self.traits_list.item(i).data(Qt.UserRole))

        self.race.recommended_classes = []
        for i in range(self.rec_class_list.count()):
            self.race.recommended_classes.append(self.rec_class_list.item(i).text())

        return self.race

# --- Main Editor Widget ---

class RaceEditor(QWidget):
    """Editor component for Races."""
    race_modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.race_manager = RaceManager()
        self.current_race: Optional[Race] = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel (List)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Races", styleSheet="font-weight: bold; font-size: 14px;"))
        self.race_list = QListWidget()
        self.race_list.setMinimumWidth(200)
        self.race_list.currentItemChanged.connect(self._on_race_selected)
        left_layout.addWidget(self.race_list)
        list_btns = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_race)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_race)
        self.edit_btn.setEnabled(False)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_race)
        self.remove_btn.setEnabled(False)
        list_btns.addWidget(self.add_btn)
        list_btns.addWidget(self.edit_btn)
        list_btns.addWidget(self.remove_btn)
        left_layout.addLayout(list_btns)
        splitter.addWidget(left_panel)

        # Right panel (Details - Read Only)
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setFrameShape(QFrame.NoFrame)
        self.details_widget = QWidget()
        right_panel.setWidget(self.details_widget)
        self.details_layout = QVBoxLayout(self.details_widget)

        self.details_form = QFormLayout()
        self.name_label = QLabel()
        self.name_label.setWordWrap(True)
        self.details_form.addRow("<b>Name:</b>", self.name_label)
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.details_form.addRow("<b>Description:</b>", self.desc_label)
        self.details_layout.addLayout(self.details_form)

        self.details_layout.addWidget(QLabel("<b>Stat Modifiers:</b>", styleSheet="margin-top: 10px;"))
        self.stats_display_list = QListWidget()
        self.stats_display_list.setEnabled(False)
        self.details_layout.addWidget(self.stats_display_list)

        self.details_layout.addWidget(QLabel("<b>Traits:</b>", styleSheet="margin-top: 10px;"))
        self.traits_display_list = QListWidget()
        self.traits_display_list.setEnabled(False)
        self.details_layout.addWidget(self.traits_display_list)

        self.details_layout.addWidget(QLabel("<b>Recommended Classes:</b>", styleSheet="margin-top: 10px;"))
        self.rec_class_display_list = QListWidget()
        self.rec_class_display_list.setEnabled(False)
        self.details_layout.addWidget(self.rec_class_display_list)

        self.details_layout.addStretch()
        splitter.addWidget(right_panel)

        self._disable_details_display()
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

    def set_race_manager(self, manager: RaceManager):
        self.race_manager = manager
        self._refresh_race_list()

    def _refresh_race_list(self):
        current_name = self.race_list.currentItem().data(Qt.UserRole) if self.race_list.currentItem() else None # Store name
        self.race_list.clear()
        items_to_add = []
        # 'race_name' here is the key from the manager's dict
        for race_name, race in self.race_manager.races.items():
            item = QListWidgetItem(race.name)
            item.setData(Qt.UserRole, race_name) # Store the name
            items_to_add.append(item)
        items_to_add.sort(key=lambda x: x.text())
        new_selection = None
        for item in items_to_add:
            self.race_list.addItem(item)
            if item.data(Qt.UserRole) == current_name: # Compare names
                new_selection = item

        if new_selection:
            self.race_list.setCurrentItem(new_selection)
        elif self.race_list.count() > 0:
            self.race_list.setCurrentRow(0)
        else:
            self._disable_details_display()
            self.edit_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)

    def _on_race_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if current:
            race_name = current.data(Qt.UserRole) # Retrieve the name
            race = self.race_manager.get_race(race_name) # Use name to get race
            if race:
                self._load_race_display(race)
                self.edit_btn.setEnabled(True)
                self.remove_btn.setEnabled(True)
                return
        self._disable_details_display()
        self.edit_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)

    def _load_race_display(self, race: Race):
        self.current_race = race
        self.name_label.setText(race.name or "N/A")
        self.desc_label.setText(race.description or "N/A")

        self.stats_display_list.clear()
        for stat, mod in race.stat_modifiers.items():
            if mod != 0:
                sign = "+" if mod > 0 else ""
                self.stats_display_list.addItem(f"{stat}: {sign}{mod}")

        self.traits_display_list.clear()
        for trait in race.traits:
            item = QListWidgetItem(trait.name)
            item.setToolTip(trait.description)
            self.traits_display_list.addItem(item)

        self.rec_class_display_list.clear()
        for class_name in race.recommended_classes:
            self.rec_class_display_list.addItem(class_name)

        self.details_widget.setEnabled(True)

    def _disable_details_display(self):
        self.current_race = None
        self.name_label.clear()
        self.desc_label.clear()
        self.stats_display_list.clear()
        self.traits_display_list.clear()
        self.rec_class_display_list.clear()
        self.details_widget.setEnabled(False)

    def _add_race(self):
        dialog = RaceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            new_race = dialog.get_race()
            new_race.id = new_race.name
            if not new_race.id: new_race.id = Race.generate_id() # Should be handled by create_new
            self.race_manager.add_race(new_race)
            self._refresh_race_list()
            # Select the new item
            items = self.race_list.findItems(new_race.name, Qt.MatchExactly)
            if items: self.race_list.setCurrentItem(items[0])
            self.race_modified.emit()
            logger.info(f"Added race: {new_race.name}")

    def _edit_race(self):
        if not self.current_race: return

        original_name = self.current_race.name # Store original name

        dialog = RaceDialog(self, self.current_race) # Pass current race (dialog makes copy)
        if dialog.exec() == QDialog.Accepted:
            edited_race = dialog.get_race()

            edited_race.id = edited_race.name
            # Check if the name was changed and if the new name conflicts
            if original_name != edited_race.name:
                if self.race_manager.get_race(edited_race.name):
                    QMessageBox.warning(self, "Duplicate Race", f"A race named '{edited_race.name}' already exists.")
                    return
                # Remove the entry with the old name if name changed
                self.race_manager.remove_race(original_name)

            # Add/Update using the (potentially new) name as the key
            self.race_manager.add_race(edited_race)
            self._refresh_race_list() # Will re-select and update display
            self.race_modified.emit()
            logger.info(f"Edited race: {edited_race.name}")

    def _remove_race(self):
        if not self.current_race: return
        result = QMessageBox.question(self, "Confirm Deletion", f"Delete race '{self.current_race.name}'?", QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            removed = self.race_manager.remove_race(self.current_race.name) # Use name
            if removed:
                self._refresh_race_list()
                self.race_modified.emit()
                logger.info(f"Removed race: {self.current_race.name}") # Use name
            else:
                 QMessageBox.critical(self, "Error", "Failed to remove race.")

