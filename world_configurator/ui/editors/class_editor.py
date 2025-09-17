# world_configurator/ui/editors/class_editor.py
"""
Character Class editor component for the World Configurator Tool.
"""

import logging
import copy
from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QSpinBox,
    QDialog, QMessageBox, QSplitter, QScrollArea, QFrame, QTabWidget,
    QGridLayout, QInputDialog
)

from ui.dialogs.base_dialog import BaseDialog
from models.base_models import CharacterClass, ClassArchetype
from models.world_data import ClassManager

logger = logging.getLogger("world_configurator.ui.class_editor")

# --- Helper Dialogs ---

class ArchetypeDialog(BaseDialog):
    """Dialog for editing a ClassArchetype."""
    def __init__(self, parent=None, archetype: Optional[ClassArchetype] = None):
        super().__init__(parent)
        self.setWindowTitle("Class Archetype")
        self.setMinimumWidth(450)

        self.archetype = archetype or ClassArchetype(name="New Archetype", description="", stat_distribution={})
        self.possible_stats = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.archetype.name)
        form.addRow("Name:", self.name_edit)

        self.desc_edit = QTextEdit(self.archetype.description)
        self.desc_edit.setMinimumHeight(80)
        form.addRow("Description:", self.desc_edit)

        # Stat Distribution
        form.addRow(QLabel("<b>Stat Distribution Preset:</b>"))
        stats_grid = QGridLayout()
        self.stat_spins: Dict[str, QSpinBox] = {}
        for i, stat in enumerate(self.possible_stats):
            label = QLabel(f"{stat}:")
            spin = QSpinBox()
            spin.setRange(0, 20) # Example range for stats
            spin.setValue(self.archetype.stat_distribution.get(stat, 8)) # Default 8?
            self.stat_spins[stat] = spin
            row, col = divmod(i, 3)
            stats_grid.addWidget(label, row, col * 2)
            stats_grid.addWidget(spin, row, col * 2 + 1)
        form.addRow(stats_grid)

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

    def get_archetype(self) -> ClassArchetype:
        self.archetype.name = self.name_edit.text()
        self.archetype.description = self.desc_edit.toPlainText()
        self.archetype.stat_distribution = {stat: spin.value() for stat, spin in self.stat_spins.items()}
        return self.archetype

# --- Main Class Dialog ---

class ClassDialog(QDialog):
    """Dialog for editing a CharacterClass."""
    def __init__(self, parent=None, char_class: Optional[CharacterClass] = None):
        super().__init__(parent)
        self.setWindowTitle("Class Editor")
        self.setMinimumWidth(650)
        self.setMinimumHeight(600)

        self.char_class = copy.deepcopy(char_class) if char_class else CharacterClass.create_new("New Class", "")
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
        self.name_edit = QLineEdit(self.char_class.name)
        basic_layout.addRow("Name:", self.name_edit)
        self.desc_edit = QTextEdit(self.char_class.description)
        self.desc_edit.setMinimumHeight(100)
        basic_layout.addRow("Description:", self.desc_edit)

        # Stats Tab
        stats_tab = QWidget()
        self.tabs.addTab(stats_tab, "Stats")
        stats_layout = QVBoxLayout(stats_tab)
        stats_form = QFormLayout()
        # Stat Modifiers
        stats_form.addRow(QLabel("<b>Stat Modifiers:</b>"))
        mod_grid = QGridLayout()
        self.stat_mod_spins: Dict[str, QSpinBox] = {}
        for i, stat in enumerate(self.possible_stats):
            label = QLabel(f"{stat}:")
            spin = QSpinBox()
            spin.setRange(-5, 5)
            spin.setValue(self.char_class.stat_modifiers.get(stat, 0))
            self.stat_mod_spins[stat] = spin
            row, col = divmod(i, 3)
            mod_grid.addWidget(label, row, col * 2)
            mod_grid.addWidget(spin, row, col * 2 + 1)
        stats_form.addRow(mod_grid)
        # Minimum Stats
        stats_form.addRow(QLabel("<b>Minimum Stats:</b>"))
        min_grid = QGridLayout()
        self.min_stat_spins: Dict[str, QSpinBox] = {}
        for i, stat in enumerate(self.possible_stats):
            label = QLabel(f"{stat}:")
            spin = QSpinBox()
            spin.setRange(0, 20)
            spin.setValue(self.char_class.minimum_stats.get(stat, 0))
            spin.setSpecialValueText("None") # Show 0 as None
            self.min_stat_spins[stat] = spin
            row, col = divmod(i, 3)
            min_grid.addWidget(label, row, col * 2)
            min_grid.addWidget(spin, row, col * 2 + 1)
        stats_form.addRow(min_grid)
        stats_layout.addLayout(stats_form)

        # Recommendations Tab
        rec_tab = QWidget()
        self.tabs.addTab(rec_tab, "Recommendations")
        rec_layout = QFormLayout(rec_tab)
        rec_layout.addRow(QLabel("<b>Recommended Stats (comma-separated):</b>"))
        self.rec_primary_edit = QLineEdit(", ".join(self.char_class.recommended_stats.get("primary", [])))
        rec_layout.addRow("Primary:", self.rec_primary_edit)
        self.rec_secondary_edit = QLineEdit(", ".join(self.char_class.recommended_stats.get("secondary", [])))
        rec_layout.addRow("Secondary:", self.rec_secondary_edit)
        self.rec_tertiary_edit = QLineEdit(", ".join(self.char_class.recommended_stats.get("tertiary", [])))
        rec_layout.addRow("Tertiary:", self.rec_tertiary_edit)

        # Archetypes Tab
        arch_tab = QWidget()
        self.tabs.addTab(arch_tab, "Archetypes")
        arch_layout = QVBoxLayout(arch_tab)
        arch_layout.addWidget(QLabel("Class Archetypes:"))
        self.arch_list = QListWidget()
        self.arch_list.itemDoubleClicked.connect(self._edit_archetype)
        arch_layout.addWidget(self.arch_list)
        for arch_name, archetype in self.char_class.archetypes.items():
            self._add_archetype_to_list(archetype)
        arch_btns = QHBoxLayout()
        add_arch_btn = QPushButton("Add Archetype")
        add_arch_btn.clicked.connect(self._add_archetype)
        edit_arch_btn = QPushButton("Edit Archetype")
        edit_arch_btn.clicked.connect(lambda: self._edit_archetype(self.arch_list.currentItem()))
        remove_arch_btn = QPushButton("Remove Archetype")
        remove_arch_btn.clicked.connect(self._remove_archetype)
        arch_btns.addWidget(add_arch_btn)
        arch_btns.addWidget(edit_arch_btn)
        arch_btns.addWidget(remove_arch_btn)
        arch_layout.addLayout(arch_btns)

        # Proficiencies Tab
        prof_tab = QWidget()
        self.tabs.addTab(prof_tab, "Proficiencies")
        prof_layout = QFormLayout(prof_tab)
        prof_layout.addRow(QLabel("<b>Proficiencies (comma-separated):</b>"))
        self.weapon_prof_edit = QLineEdit(", ".join(self.char_class.weapon_proficiencies))
        prof_layout.addRow("Weapons:", self.weapon_prof_edit)
        self.armor_prof_edit = QLineEdit(", ".join(self.char_class.armor_proficiencies))
        prof_layout.addRow("Armor:", self.armor_prof_edit)

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

    def _add_archetype_to_list(self, archetype: ClassArchetype):
        item = QListWidgetItem(f"{archetype.name}")
        item.setToolTip(archetype.description)
        item.setData(Qt.UserRole, archetype)
        self.arch_list.addItem(item)
        self.arch_list.sortItems()

    def _add_archetype(self):
        dialog = ArchetypeDialog(self)
        if dialog.exec() == QDialog.Accepted:
            new_arch = dialog.get_archetype()
            if new_arch.name in self.char_class.archetypes: # Check internal dict
                 QMessageBox.warning(self, "Duplicate Archetype", f"An archetype named '{new_arch.name}' already exists.")
                 return
            self._add_archetype_to_list(new_arch)
            self.char_class.archetypes[new_arch.name] = new_arch # Add to internal dict

    def _edit_archetype(self, item: Optional[QListWidgetItem]):
        if not item: item = self.arch_list.currentItem()
        if not item: return

        original_arch = item.data(Qt.UserRole)
        dialog = ArchetypeDialog(self, copy.deepcopy(original_arch))
        if dialog.exec() == QDialog.Accepted:
            updated_arch = dialog.get_archetype()

            # Check if name changed and conflicts
            if original_arch.name != updated_arch.name:
                if updated_arch.name in self.char_class.archetypes:
                    QMessageBox.warning(self, "Duplicate Archetype", f"An archetype named '{updated_arch.name}' already exists.")
                    return
                # Remove old name from internal dict
                if original_arch.name in self.char_class.archetypes:
                    del self.char_class.archetypes[original_arch.name]

            # Update item and internal dict
            item.setText(updated_arch.name)
            item.setToolTip(updated_arch.description)
            item.setData(Qt.UserRole, updated_arch)
            self.char_class.archetypes[updated_arch.name] = updated_arch
            self.arch_list.sortItems()

    def _remove_archetype(self):
        item = self.arch_list.currentItem()
        if not item: return
        archetype = item.data(Qt.UserRole)
        result = QMessageBox.question(self, "Confirm Removal", f"Remove archetype '{archetype.name}'?", QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            if archetype.name in self.char_class.archetypes:
                del self.char_class.archetypes[archetype.name] # Remove from internal dict
            self.arch_list.takeItem(self.arch_list.row(item))

    def _parse_comma_list(self, text: str) -> List[str]:
        return [s.strip() for s in text.split(',') if s.strip()]

    def get_class(self) -> CharacterClass:
        self.char_class.name = self.name_edit.text()
        self.char_class.description = self.desc_edit.toPlainText()

        self.char_class.stat_modifiers = {stat: spin.value() for stat, spin in self.stat_mod_spins.items()}
        self.char_class.minimum_stats = {stat: spin.value() for stat, spin in self.min_stat_spins.items() if spin.value() > 0} # Only store non-zero minimums

        self.char_class.recommended_stats = {
            "primary": self._parse_comma_list(self.rec_primary_edit.text()),
            "secondary": self._parse_comma_list(self.rec_secondary_edit.text()),
            "tertiary": self._parse_comma_list(self.rec_tertiary_edit.text()),
        }

        # Archetypes are updated directly in the internal dict by add/edit/remove methods
        # self.char_class.archetypes = {}
        # for i in range(self.arch_list.count()):
        #     arch = self.arch_list.item(i).data(Qt.UserRole)
        #     self.char_class.archetypes[arch.name] = arch

        self.char_class.weapon_proficiencies = self._parse_comma_list(self.weapon_prof_edit.text())
        self.char_class.armor_proficiencies = self._parse_comma_list(self.armor_prof_edit.text())

        return self.char_class

# --- Main Editor Widget ---

class ClassEditor(QWidget):
    """Editor component for Character Classes."""
    class_modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.class_manager = ClassManager()
        self.current_class: Optional[CharacterClass] = None
        self._setup_ui()

    # Assistant integration
    def get_assistant_context(self):
        from assistant.context import AssistantContext
        allowed = [
            "/stat_modifiers",
            "/minimum_stats",
            "/recommended_stats",
            "/weapon_proficiencies",
            "/armor_proficiencies",
            "/description",
            "/archetypes",
        ]
        content = self.current_class.to_dict() if self.current_class else None
        return AssistantContext(
            domain="classes",
            selection_id=self.current_class.id if self.current_class else None,
            content=content,
            schema=None,
            allowed_paths=allowed,
        )

    def get_domain_examples(self):
        # Return first available class as exemplar
        if self.class_manager.classes:
            first = next(iter(self.class_manager.classes.values()))
            return [first.to_dict()]
        return []

    def get_reference_catalogs(self):
        # Provide known stat keys and possibly known prof lists from current data
        stat_keys = ["STR","DEX","CON","INT","WIS","CHA","WIL","INS"]
        known_weapons = sorted({w for c in self.class_manager.classes.values() for w in c.weapon_proficiencies})
        known_armors = sorted({a for c in self.class_manager.classes.values() for a in c.armor_proficiencies})
        existing_names = sorted({c.name for c in self.class_manager.classes.values() if c and c.name})
        existing_summaries = {c.name: c.description for c in self.class_manager.classes.values() if c and c.name}
        return {
            "stats": stat_keys,
            "weapon_proficiencies": known_weapons,
            "armor_proficiencies": known_armors,
            "existing_names": existing_names,
            "existing_summaries": existing_summaries,
        }

    def _sanitize_class_payload(self, payload: dict) -> dict:
        """Sanitize incoming class payload to fit CharacterClass schema.
        - For archetypes, drop unknown keys (e.g., 'abilities').
        - If 'abilities' provided, append them to description as text for preservation.
        """
        if not isinstance(payload, dict):
            return payload
        sanitized = dict(payload)
        arches = sanitized.get("archetypes")
        if isinstance(arches, dict):
            new_arches = {}
            for arch_name, arch_data in arches.items():
                if not isinstance(arch_data, dict):
                    new_arches[arch_name] = arch_data
                    continue
                desc = arch_data.get("description", "")
                # Preserve abilities by appending to description
                abilities = arch_data.get("abilities")
                if abilities:
                    if isinstance(abilities, list):
                        bullets = "\n".join(f"- {a}" for a in abilities if isinstance(a, str) and a.strip())
                    elif isinstance(abilities, str) and abilities.strip():
                        bullets = f"- {abilities.strip()}"
                    else:
                        bullets = ""
                    if bullets:
                        desc = (desc + ("\n\nAbilities:\n" if desc else "Abilities:\n") + bullets).strip()
                cleaned = {
                    "name": arch_data.get("name", arch_name),
                    "description": desc,
                    "stat_distribution": arch_data.get("stat_distribution", {}),
                }
                new_arches[arch_name] = cleaned
            sanitized["archetypes"] = new_arches
        return sanitized

    def apply_assistant_patch(self, patch_ops):
        from assistant.patching import apply_patch_with_validation
        from assistant.context import PatchOp
        ctx = self.get_assistant_context()
        if not ctx.content:
            return False, "No class selected."
        ok, msg, new_content = apply_patch_with_validation(ctx, ctx.content, patch_ops)
        if not ok:
            return False, msg
        try:
            new_content = self._sanitize_class_payload(new_content)
            # Map back to CharacterClass
            updated = CharacterClass.from_dict(new_content)
            updated.id = self.current_class.id  # preserve id
            self.class_manager.add_class(updated)
            # refresh UI
            self._load_class_display(updated)
            self.class_modified.emit()
            return True, "OK"
        except Exception as e:
            return False, f"Failed to apply: {e}"

    def create_entry_from_llm(self, entry: dict):
        try:
            # Ensure minimal required fields and unique name
            proposed_name = (entry.get("name") or "New Class").strip()
            existing_names = {c.name for c in self.class_manager.classes.values()}
            name = proposed_name
            suffix = 1
            while name in existing_names:
                name = f"{proposed_name} ({suffix})"
                suffix += 1
            desc = entry.get("description", "")
            new_cls = CharacterClass.create_new(name, desc)
            # Merge remaining fields
            tmp = new_cls.to_dict()
            tmp.update({k: v for k, v in entry.items() if k != "id" and k != "name"})
            tmp["name"] = name
            tmp = self._sanitize_class_payload(tmp)
            new_obj = CharacterClass.from_dict(tmp)
            new_obj.id = new_cls.id  # keep generated id
            self.class_manager.add_class(new_obj)
            self._refresh_class_list()
            # select new
            for i in range(self.class_list.count()):
                it = self.class_list.item(i)
                if self.class_manager.get_class(it.data(Qt.UserRole)).id == new_obj.id:
                    self.class_list.setCurrentItem(it)
                    break
            self.class_modified.emit()
            return True, "Created", new_obj.id
        except Exception as e:
            return False, f"Failed to create: {e}", None

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel (List)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Classes", styleSheet="font-weight: bold; font-size: 14px;"))
        self.class_list = QListWidget()
        self.class_list.setMinimumWidth(200)
        self.class_list.currentItemChanged.connect(self._on_class_selected)
        left_layout.addWidget(self.class_list)
        list_btns = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_class)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_class)
        self.edit_btn.setEnabled(False)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_class)
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
        self.stats_mod_display_list = QListWidget()
        self.stats_mod_display_list.setEnabled(False)
        self.details_layout.addWidget(self.stats_mod_display_list)

        self.details_layout.addWidget(QLabel("<b>Minimum Stats:</b>", styleSheet="margin-top: 5px;"))
        self.min_stats_display_list = QListWidget()
        self.min_stats_display_list.setEnabled(False)
        self.details_layout.addWidget(self.min_stats_display_list)

        self.details_layout.addWidget(QLabel("<b>Archetypes:</b>", styleSheet="margin-top: 10px;"))
        self.arch_display_list = QListWidget()
        self.arch_display_list.setEnabled(False)
        self.details_layout.addWidget(self.arch_display_list)

        self.details_layout.addWidget(QLabel("<b>Proficiencies:</b>", styleSheet="margin-top: 10px;"))
        self.prof_display_list = QListWidget()
        self.prof_display_list.setEnabled(False)
        self.details_layout.addWidget(self.prof_display_list)

        self.details_layout.addStretch()
        splitter.addWidget(right_panel)

        self._disable_details_display()
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

    def set_class_manager(self, manager: ClassManager):
        self.class_manager = manager
        self._refresh_class_list()

    def _refresh_class_list(self):
        current_id = self.class_list.currentItem().data(Qt.UserRole) if self.class_list.currentItem() else None
        self.class_list.clear()
        items_to_add = []
        for class_id, char_class in self.class_manager.classes.items():
            item = QListWidgetItem(char_class.name)
            item.setData(Qt.UserRole, class_id)
            items_to_add.append(item)
        items_to_add.sort(key=lambda x: x.text())
        new_selection = None
        for item in items_to_add:
            self.class_list.addItem(item)
            if item.data(Qt.UserRole) == current_id:
                new_selection = item

        if new_selection:
            self.class_list.setCurrentItem(new_selection)
        elif self.class_list.count() > 0:
            self.class_list.setCurrentRow(0)
        else:
            self._disable_details_display()
            self.edit_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)

    def _on_class_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        if current:
            class_id = current.data(Qt.UserRole)
            char_class = self.class_manager.get_class(class_id)
            if char_class:
                self._load_class_display(char_class)
                self.edit_btn.setEnabled(True)
                self.remove_btn.setEnabled(True)
                return
        self._disable_details_display()
        self.edit_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)

    def _load_class_display(self, char_class: CharacterClass):
        self.current_class = char_class
        self.name_label.setText(char_class.name or "N/A")
        self.desc_label.setText(char_class.description or "N/A")

        self.stats_mod_display_list.clear()
        for stat, mod in char_class.stat_modifiers.items():
            if mod != 0:
                sign = "+" if mod > 0 else ""
                self.stats_mod_display_list.addItem(f"{stat}: {sign}{mod}")

        self.min_stats_display_list.clear()
        for stat, val in char_class.minimum_stats.items():
             if val > 0:
                self.min_stats_display_list.addItem(f"{stat}: {val}")

        self.arch_display_list.clear()
        for arch_name, archetype in char_class.archetypes.items():
            item = QListWidgetItem(arch_name)
            item.setToolTip(archetype.description)
            self.arch_display_list.addItem(item)

        self.prof_display_list.clear()
        if char_class.weapon_proficiencies:
            self.prof_display_list.addItem(f"Weapons: {', '.join(char_class.weapon_proficiencies)}")
        if char_class.armor_proficiencies:
            self.prof_display_list.addItem(f"Armor: {', '.join(char_class.armor_proficiencies)}")

        self.details_widget.setEnabled(True)

    def _disable_details_display(self):
        self.current_class = None
        self.name_label.clear()
        self.desc_label.clear()
        self.stats_mod_display_list.clear()
        self.min_stats_display_list.clear()
        self.arch_display_list.clear()
        self.prof_display_list.clear()
        self.details_widget.setEnabled(False)

    def _add_class(self):
        dialog = ClassDialog(self)
        if dialog.exec() == QDialog.Accepted:
            new_class = dialog.get_class()
            if not new_class.id: new_class.id = CharacterClass.generate_id() # Should be handled by create_new
            self.class_manager.add_class(new_class)
            self._refresh_class_list()
            items = self.class_list.findItems(new_class.name, Qt.MatchExactly)
            if items: self.class_list.setCurrentItem(items[0])
            self.class_modified.emit()
            logger.info(f"Added class: {new_class.name}")

    def _edit_class(self):
        if not self.current_class: return
        dialog = ClassDialog(self, self.current_class)
        if dialog.exec() == QDialog.Accepted:
            edited_class = dialog.get_class()
            edited_class.id = self.current_class.id
            self.class_manager.add_class(edited_class)
            self._refresh_class_list()
            self.class_modified.emit()
            logger.info(f"Edited class: {edited_class.name}")

    def _remove_class(self):
        if not self.current_class: return
        result = QMessageBox.question(self, "Confirm Deletion", f"Delete class '{self.current_class.name}'?", QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            removed = self.class_manager.remove_class(self.current_class.id)
            if removed:
                self._refresh_class_list()
                self.class_modified.emit()
                logger.info(f"Removed class: {self.current_class.name}")
            else:
                 QMessageBox.critical(self, "Error", "Failed to remove class.")

