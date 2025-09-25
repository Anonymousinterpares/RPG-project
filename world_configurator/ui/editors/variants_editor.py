"""
Variants editor for config/npc/variants.json.
"""
import logging
import os
from typing import Dict, Any, Optional, List

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QDoubleSpinBox,
    QComboBox, QMessageBox, QSplitter, QFrame, QCheckBox, QSpinBox,
    QGroupBox, QScrollArea, QTabWidget
)

from models.variants_manager import VariantsManager
from utils.file_manager import get_config_dir

logger = logging.getLogger("world_configurator.ui.variants_editor")

class StatModifierWidget(QWidget):
    """Widget for editing stat modifiers."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.data = {}
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # HP Modifier
        hp_group = QGroupBox("HP Modifier")
        hp_layout = QFormLayout(hp_group)
        self.hp_add_spin = QDoubleSpinBox()
        self.hp_add_spin.setRange(-100, 100)
        self.hp_add_spin.setValue(0)
        self.hp_mul_spin = QDoubleSpinBox()
        self.hp_mul_spin.setRange(0.1, 5.0)
        self.hp_mul_spin.setSingleStep(0.1)
        self.hp_mul_spin.setValue(1.0)
        hp_layout.addRow("Add:", self.hp_add_spin)
        hp_layout.addRow("Multiply:", self.hp_mul_spin)
        layout.addWidget(hp_group)
        
        # Damage Modifier
        damage_group = QGroupBox("Damage Modifier")
        damage_layout = QFormLayout(damage_group)
        self.damage_add_spin = QDoubleSpinBox()
        self.damage_add_spin.setRange(-100, 100)
        self.damage_add_spin.setValue(0)
        self.damage_mul_spin = QDoubleSpinBox()
        self.damage_mul_spin.setRange(0.1, 5.0)
        self.damage_mul_spin.setSingleStep(0.1)
        self.damage_mul_spin.setValue(1.0)
        damage_layout.addRow("Add:", self.damage_add_spin)
        damage_layout.addRow("Multiply:", self.damage_mul_spin)
        layout.addWidget(damage_group)
        
        # Defense Modifier
        defense_group = QGroupBox("Defense Modifier")
        defense_layout = QFormLayout(defense_group)
        self.defense_add_spin = QDoubleSpinBox()
        self.defense_add_spin.setRange(-100, 100)
        self.defense_add_spin.setValue(0)
        self.defense_mul_spin = QDoubleSpinBox()
        self.defense_mul_spin.setRange(0.1, 5.0)
        self.defense_mul_spin.setSingleStep(0.1)
        self.defense_mul_spin.setValue(1.0)
        defense_layout.addRow("Add:", self.defense_add_spin)
        defense_layout.addRow("Multiply:", self.defense_mul_spin)
        layout.addWidget(defense_group)
        
        # Initiative Modifier
        initiative_group = QGroupBox("Initiative Modifier")
        initiative_layout = QFormLayout(initiative_group)
        self.initiative_add_spin = QDoubleSpinBox()
        self.initiative_add_spin.setRange(-100, 100)
        self.initiative_add_spin.setValue(0)
        self.initiative_mul_spin = QDoubleSpinBox()
        self.initiative_mul_spin.setRange(0.1, 5.0)
        self.initiative_mul_spin.setSingleStep(0.1)
        self.initiative_mul_spin.setValue(1.0)
        initiative_layout.addRow("Add:", self.initiative_add_spin)
        initiative_layout.addRow("Multiply:", self.initiative_mul_spin)
        layout.addWidget(initiative_group)
    
    def set_data(self, data: Dict[str, Dict[str, float]]):
        """Set the stat modifier data."""
        self.data = data or {}
        
        # HP
        hp_data = self.data.get("hp", {})
        self.hp_add_spin.setValue(hp_data.get("add", 0))
        self.hp_mul_spin.setValue(hp_data.get("mul", 1.0))
        
        # Damage
        damage_data = self.data.get("damage", {})
        self.damage_add_spin.setValue(damage_data.get("add", 0))
        self.damage_mul_spin.setValue(damage_data.get("mul", 1.0))
        
        # Defense
        defense_data = self.data.get("defense", {})
        self.defense_add_spin.setValue(defense_data.get("add", 0))
        self.defense_mul_spin.setValue(defense_data.get("mul", 1.0))
        
        # Initiative
        initiative_data = self.data.get("initiative", {})
        self.initiative_add_spin.setValue(initiative_data.get("add", 0))
        self.initiative_mul_spin.setValue(initiative_data.get("mul", 1.0))
    
    def get_data(self) -> Dict[str, Dict[str, float]]:
        """Get the stat modifier data."""
        data = {}
        
        # Only include non-default values
        if self.hp_add_spin.value() != 0 or self.hp_mul_spin.value() != 1.0:
            hp_mod = {}
            if self.hp_add_spin.value() != 0:
                hp_mod["add"] = self.hp_add_spin.value()
            if self.hp_mul_spin.value() != 1.0:
                hp_mod["mul"] = self.hp_mul_spin.value()
            if hp_mod:
                data["hp"] = hp_mod
        
        if self.damage_add_spin.value() != 0 or self.damage_mul_spin.value() != 1.0:
            damage_mod = {}
            if self.damage_add_spin.value() != 0:
                damage_mod["add"] = self.damage_add_spin.value()
            if self.damage_mul_spin.value() != 1.0:
                damage_mod["mul"] = self.damage_mul_spin.value()
            if damage_mod:
                data["damage"] = damage_mod
        
        if self.defense_add_spin.value() != 0 or self.defense_mul_spin.value() != 1.0:
            defense_mod = {}
            if self.defense_add_spin.value() != 0:
                defense_mod["add"] = self.defense_add_spin.value()
            if self.defense_mul_spin.value() != 1.0:
                defense_mod["mul"] = self.defense_mul_spin.value()
            if defense_mod:
                data["defense"] = defense_mod
        
        if self.initiative_add_spin.value() != 0 or self.initiative_mul_spin.value() != 1.0:
            initiative_mod = {}
            if self.initiative_add_spin.value() != 0:
                initiative_mod["add"] = self.initiative_add_spin.value()
            if self.initiative_mul_spin.value() != 1.0:
                initiative_mod["mul"] = self.initiative_mul_spin.value()
            if initiative_mod:
                data["initiative"] = initiative_mod
        
        return data

class VariantsEditor(QWidget):
    variants_modified = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager: Optional[VariantsManager] = None
        self._current_variant: Optional[str] = None
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Create splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel: Variant list and filter controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Filter controls
        filter_group = QGroupBox("Filter")
        filter_layout = QVBoxLayout(filter_group)
        
        # Role filter
        role_filter_layout = QHBoxLayout()
        role_filter_layout.addWidget(QLabel("Role:"))
        self.role_filter_combo = QComboBox()
        self.role_filter_combo.addItems(["All", "guard", "official", "scholar"])
        self.role_filter_combo.currentTextChanged.connect(self._on_filter_changed)
        role_filter_layout.addWidget(self.role_filter_combo)
        filter_layout.addLayout(role_filter_layout)
        
        # Culture filter
        culture_filter_layout = QHBoxLayout()
        culture_filter_layout.addWidget(QLabel("Culture:"))
        self.culture_filter_combo = QComboBox()
        self.culture_filter_combo.addItems(["All", "concordant", "verdant", "crystalline", "ashen", "tempest"])
        self.culture_filter_combo.currentTextChanged.connect(self._on_filter_changed)
        culture_filter_layout.addWidget(self.culture_filter_combo)
        filter_layout.addLayout(culture_filter_layout)
        
        left_layout.addWidget(filter_group)
        
        # Variant list
        variants_label = QLabel("Variants")
        variants_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(variants_label)
        
        self.variants_list = QListWidget()
        self.variants_list.setMinimumWidth(250)
        self.variants_list.currentItemChanged.connect(self._on_variant_selected)
        left_layout.addWidget(self.variants_list)
        
        # List controls
        list_controls = QHBoxLayout()
        self.add_variant_btn = QPushButton("Add")
        self.add_variant_btn.clicked.connect(self._on_add_variant)
        list_controls.addWidget(self.add_variant_btn)
        
        self.remove_variant_btn = QPushButton("Remove")
        self.remove_variant_btn.clicked.connect(self._on_remove_variant)
        self.remove_variant_btn.setEnabled(False)
        list_controls.addWidget(self.remove_variant_btn)
        
        left_layout.addLayout(list_controls)
        
        # Actions
        actions_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load from Game")
        self.load_btn.clicked.connect(self.load_from_game)
        actions_layout.addWidget(self.load_btn)
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        actions_layout.addWidget(self.save_btn)
        
        left_layout.addLayout(actions_layout)
        
        splitter.addWidget(left_panel)
        
        # Right panel: Variant details
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setFrameShape(QFrame.NoFrame)
        
        self.details_widget = QWidget()
        right_panel.setWidget(self.details_widget)
        self.details_layout = QVBoxLayout(self.details_widget)
        
        # Basic info
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout(basic_group)
        
        self.id_edit = QLineEdit()
        self.id_edit.textChanged.connect(self._on_field_changed)
        basic_layout.addRow("ID:", self.id_edit)
        
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._on_field_changed)
        basic_layout.addRow("Name:", self.name_edit)
        
        self.family_id_edit = QLineEdit()
        self.family_id_edit.setPlaceholderText("e.g., concordant_citizen, verdant_wanderer")
        self.family_id_edit.textChanged.connect(self._on_field_changed)
        basic_layout.addRow("Family ID:", self.family_id_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.textChanged.connect(self._on_field_changed)
        basic_layout.addRow("Description:", self.description_edit)
        
        self.details_layout.addWidget(basic_group)
        
        # Stat modifiers
        stat_group = QGroupBox("Stat Modifiers")
        stat_layout = QVBoxLayout(stat_group)
        self.stat_modifier_widget = StatModifierWidget()
        stat_layout.addWidget(self.stat_modifier_widget)
        self.details_layout.addWidget(stat_group)
        
        # Lists section
        lists_group = QGroupBox("Roles, Abilities, and Tags")
        lists_layout = QVBoxLayout(lists_group)
        
        # Roles
        roles_layout = QHBoxLayout()
        roles_layout.addWidget(QLabel("Roles Add:"))
        self.roles_edit = QLineEdit()
        self.roles_edit.setPlaceholderText("Comma-separated: striker, tank, controller, support, skirmisher")
        self.roles_edit.textChanged.connect(self._on_field_changed)
        roles_layout.addWidget(self.roles_edit)
        lists_layout.addLayout(roles_layout)
        
        # Abilities
        abilities_layout = QHBoxLayout()
        abilities_layout.addWidget(QLabel("Abilities Add:"))
        self.abilities_edit = QLineEdit()
        self.abilities_edit.setPlaceholderText("Comma-separated ability IDs")
        self.abilities_edit.textChanged.connect(self._on_field_changed)
        abilities_layout.addWidget(self.abilities_edit)
        lists_layout.addLayout(abilities_layout)
        
        # Tags
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(QLabel("Tags Add:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Comma-separated: role:guard, duty:watch, etc.")
        self.tags_edit.textChanged.connect(self._on_field_changed)
        tags_layout.addWidget(self.tags_edit)
        lists_layout.addLayout(tags_layout)
        
        self.details_layout.addWidget(lists_group)
        
        # Quick social role creation
        quick_group = QGroupBox("Quick Social Role Creation")
        quick_layout = QFormLayout(quick_group)
        
        self.quick_culture_combo = QComboBox()
        self.quick_culture_combo.addItems(["concordant", "verdant", "crystalline", "ashen", "tempest"])
        quick_layout.addRow("Culture:", self.quick_culture_combo)
        
        self.quick_role_combo = QComboBox()
        self.quick_role_combo.addItems(["guard", "official", "scholar"])
        quick_layout.addRow("Role:", self.quick_role_combo)
        
        self.quick_family_edit = QLineEdit()
        self.quick_family_edit.setPlaceholderText("Leave blank to auto-determine")
        quick_layout.addRow("Family ID:", self.quick_family_edit)
        
        self.create_social_role_btn = QPushButton("Create Social Role Variant")
        self.create_social_role_btn.clicked.connect(self._on_create_social_role)
        quick_layout.addRow(self.create_social_role_btn)
        
        self.details_layout.addWidget(quick_group)
        
        # Validation and preview
        validation_group = QGroupBox("Validation & Preview")
        validation_layout = QVBoxLayout(validation_group)
        
        self.validate_btn = QPushButton("Validate Current Variant")
        self.validate_btn.clicked.connect(self._on_validate_current)
        validation_layout.addWidget(self.validate_btn)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        validation_layout.addWidget(self.preview_text)
        
        self.details_layout.addWidget(validation_group)
        
        splitter.addWidget(right_panel)
        
        # Initially disable details
        self._disable_details()
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
    
    def set_manager(self, manager: VariantsManager):
        """Set the variants manager."""
        self._manager = manager
        self.refresh()
    
    def refresh(self):
        """Refresh the UI from the manager."""
        if not self._manager:
            return
        self._refresh_variants_list()
        self._disable_details()
        self._current_variant = None
    
    def load_from_game(self):
        """Load variants from the game's config file."""
        path = os.path.join(get_config_dir(), "npc", "variants.json")
        if self._manager and self._manager.load_from_file(path):
            self.refresh()
            QMessageBox.information(self, "Loaded", f"Loaded variants from {path}")
        else:
            QMessageBox.critical(self, "Error", f"Failed to load variants from {path}")
    
    def save_changes(self):
        """Save changes to the manager."""
        if not self._manager:
            return
        
        # Save current variant first
        if self._current_variant:
            self._save_current_variant()
        
        # Validate all variants
        errors = []
        for variant_id, variant_data in self._manager.data.get("variants", {}).items():
            variant_errors = self._manager.validate_variant(variant_data)
            if variant_errors:
                errors.extend([f"{variant_id}: {err}" for err in variant_errors])
        
        if errors:
            QMessageBox.warning(self, "Validation Errors", "Some variants have validation errors:\\n\\n" + "\\n".join(errors))
            return
        
        # Save to manager's current path or show save dialog
        try:
            if self._manager.state.path:
                success = self._manager.save_to_file()
            else:
                # Fallback to game file
                path = os.path.join(get_config_dir(), "npc", "variants.json")
                success = self._manager.save_to_file(path)
            
            if success:
                self.variants_modified.emit()
                QMessageBox.information(self, "Saved", "Variants saved successfully.")
            else:
                QMessageBox.critical(self, "Error", "Failed to save variants.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save variants: {e}")
    
    def _refresh_variants_list(self):
        """Refresh the variants list."""
        if not self._manager:
            return
        
        self.variants_list.clear()
        
        variants = self._manager.data.get("variants", {})
        role_filter = self.role_filter_combo.currentText()
        culture_filter = self.culture_filter_combo.currentText()
        
        for variant_id, variant_data in variants.items():
            # Apply filters
            if role_filter != "All":
                tags = variant_data.get("tags_add", [])
                role_tag = f"role:{role_filter}"
                if role_tag not in tags:
                    continue
            
            if culture_filter != "All":
                if not variant_id.startswith(f"{culture_filter}_"):
                    continue
            
            item = QListWidgetItem(f"{variant_data.get('name', variant_id)}")
            item.setData(Qt.UserRole, variant_id)
            self.variants_list.addItem(item)
        
        # Sort alphabetically
        self.variants_list.sortItems()
    
    def _on_filter_changed(self):
        """Handle filter changes."""
        self._refresh_variants_list()
    
    def _on_variant_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        """Handle variant selection."""
        if previous and self._current_variant:
            # Save previous variant
            self._save_current_variant()
        
        if current:
            variant_id = current.data(Qt.UserRole)
            self._load_variant(variant_id)
            self.remove_variant_btn.setEnabled(True)
        else:
            self._disable_details()
            self.remove_variant_btn.setEnabled(False)
            self._current_variant = None
    
    def _load_variant(self, variant_id: str):
        """Load a variant into the editor."""
        if not self._manager:
            return
        
        variant_data = self._manager.get_variant(variant_id)
        if not variant_data:
            return
        
        self._current_variant = variant_id
        
        # Load basic info
        self.id_edit.setText(variant_data.get("id", variant_id))
        self.name_edit.setText(variant_data.get("name", ""))
        self.family_id_edit.setText(variant_data.get("family_id", ""))
        self.description_edit.setPlainText(variant_data.get("description", ""))
        
        # Load stat modifiers
        self.stat_modifier_widget.set_data(variant_data.get("stat_modifiers", {}))
        
        # Load lists
        self.roles_edit.setText(", ".join(variant_data.get("roles_add", [])))
        self.abilities_edit.setText(", ".join(variant_data.get("abilities_add", [])))
        self.tags_edit.setText(", ".join(variant_data.get("tags_add", [])))
        
        self._enable_details()
        self._update_preview()
    
    def _save_current_variant(self):
        """Save the current variant from UI."""
        if not self._manager or not self._current_variant:
            return
        
        variant_data = {
            "id": self.id_edit.text().strip(),
            "family_id": self.family_id_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip()
        }
        
        # Add stat modifiers if any
        stat_mods = self.stat_modifier_widget.get_data()
        if stat_mods:
            variant_data["stat_modifiers"] = stat_mods
        
        # Add lists if not empty
        roles = [r.strip() for r in self.roles_edit.text().split(",") if r.strip()]
        if roles:
            variant_data["roles_add"] = roles
        
        abilities = [a.strip() for a in self.abilities_edit.text().split(",") if a.strip()]
        if abilities:
            variant_data["abilities_add"] = abilities
        
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        if tags:
            variant_data["tags_add"] = tags
        
        self._manager.add_variant(self._current_variant, variant_data)
    
    def _enable_details(self):
        """Enable detail editing controls."""
        self.details_widget.setEnabled(True)
    
    def _disable_details(self):
        """Disable detail editing controls."""
        self.details_widget.setEnabled(False)
        self.id_edit.clear()
        self.name_edit.clear()
        self.family_id_edit.clear()
        self.description_edit.clear()
        self.stat_modifier_widget.set_data({})
        self.roles_edit.clear()
        self.abilities_edit.clear()
        self.tags_edit.clear()
        self.preview_text.clear()
    
    def _on_field_changed(self):
        """Handle field changes to update preview."""
        if self._current_variant:
            self._update_preview()
    
    def _update_preview(self):
        """Update the preview text."""
        if not self._current_variant:
            return
        
        # Build preview text
        preview = f"ID: {self.id_edit.text()}\n"
        preview += f"Name: {self.name_edit.text()}\n"
        preview += f"Family: {self.family_id_edit.text()}\n"
        preview += f"Description: {self.description_edit.toPlainText()}\n\n"
        
        stat_mods = self.stat_modifier_widget.get_data()
        if stat_mods:
            preview += "Stat Modifiers:\n"
            for stat, mods in stat_mods.items():
                preview += f"  {stat}: {mods}\n"
            preview += "\n"
        
        roles = [r.strip() for r in self.roles_edit.text().split(",") if r.strip()]
        if roles:
            preview += f"Roles: {', '.join(roles)}\n"
        
        abilities = [a.strip() for a in self.abilities_edit.text().split(",") if a.strip()]
        if abilities:
            preview += f"Abilities: {', '.join(abilities)}\n"
        
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        if tags:
            preview += f"Tags: {', '.join(tags)}\n"
        
        self.preview_text.setPlainText(preview)
    
    def _on_add_variant(self):
        """Handle adding a new variant."""
        if not self._manager:
            return
        
        # Simple dialog to get variant ID
        from PySide6.QtWidgets import QInputDialog
        variant_id, ok = QInputDialog.getText(self, "New Variant", "Variant ID:")
        
        if ok and variant_id.strip():
            variant_id = variant_id.strip()
            
            # Check if already exists
            if self._manager.get_variant(variant_id):
                QMessageBox.warning(self, "Exists", f"Variant '{variant_id}' already exists.")
                return
            
            # Create empty variant
            variant_data = {
                "id": variant_id,
                "family_id": "",
                "name": variant_id.replace("_", " ").title(),
                "description": f"A {variant_id} variant."
            }
            
            self._manager.add_variant(variant_id, variant_data)
            self._refresh_variants_list()
            
            # Select the new variant
            for i in range(self.variants_list.count()):
                item = self.variants_list.item(i)
                if item.data(Qt.UserRole) == variant_id:
                    self.variants_list.setCurrentItem(item)
                    break
    
    def _on_remove_variant(self):
        """Handle removing a variant."""
        if not self._manager or not self._current_variant:
            return
        
        result = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove variant '{self._current_variant}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            self._manager.remove_variant(self._current_variant)
            self._refresh_variants_list()
            self._disable_details()
            self._current_variant = None
    
    def _on_create_social_role(self):
        """Handle creating a social role variant."""
        if not self._manager:
            return
        
        culture = self.quick_culture_combo.currentText()
        role = self.quick_role_combo.currentText()
        family_id = self.quick_family_edit.text().strip()
        
        if not family_id:
            # Auto-determine family based on culture
            family_mapping = {
                "concordant": "concordant_citizen",
                "verdant": "verdant_wanderer",
                "crystalline": "crystalline_adept",
                "ashen": "ashen_nomad",
                "tempest": "tempest_swashbuckler"
            }
            family_id = family_mapping.get(culture, "humanoid_normal_base")
        
        # Generate names
        role_names = {
            "guard": {"concordant": "Concordant Guard", "verdant": "Verdant Warden", "crystalline": "Crystalline Sentinel", "ashen": "Ashen Guardian", "tempest": "Tempest Harbor Guard"},
            "official": {"concordant": "Concordant Official", "verdant": "Verdant Envoy", "crystalline": "Crystalline Official", "ashen": "Ashen Elder", "tempest": "Tempest Quartermaster"},
            "scholar": {"concordant": "Concordant Scholar", "verdant": "Verdant Scholar", "crystalline": "Crystalline Scholar", "ashen": "Ashen Scholar", "tempest": "Tempest Scholar"}
        }
        
        name = role_names.get(role, {}).get(culture, f"{culture.title()} {role.title()}")
        description = f"A {name.lower()} serving their community."
        
        try:
            variant_id = self._manager.create_social_role_variant(
                culture=culture,
                role=role,
                family_id=family_id,
                name=name,
                description=description
            )
            
            self._refresh_variants_list()
            
            # Select the new variant
            for i in range(self.variants_list.count()):
                item = self.variants_list.item(i)
                if item.data(Qt.UserRole) == variant_id:
                    self.variants_list.setCurrentItem(item)
                    break
            
            QMessageBox.information(self, "Created", f"Created social role variant: {variant_id}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create social role variant: {e}")
    
    def _on_validate_current(self):
        """Validate the current variant."""
        if not self._manager or not self._current_variant:
            return
        
        # First save current changes
        self._save_current_variant()
        
        variant_data = self._manager.get_variant(self._current_variant)
        if not variant_data:
            return
        
        errors = self._manager.validate_variant(variant_data)
        
        if errors:
            QMessageBox.warning(self, "Validation Errors", "\\n".join(errors))
        else:
            QMessageBox.information(self, "Valid", "Current variant is valid!")
    
    # AI Assistant integration methods
    def get_assistant_context(self):
        """Get context for the AI assistant."""
        from assistant.context import AssistantContext
        
        # Define allowed paths that the AI can modify
        allowed = [
            "/name",
            "/description", 
            "/family_id",
            "/stat_modifiers",
            "/roles_add",
            "/abilities_add",
            "/tags_add"
        ]
        
        content = None
        if self._manager and self._current_variant:
            # Save current UI state first
            self._save_current_variant()
            variant_data = self._manager.get_variant(self._current_variant)
            if variant_data:
                content = dict(variant_data)  # Make a copy
        
        return AssistantContext(
            domain="variants",
            selection_id=self._current_variant,
            content=content,
            schema=None,
            allowed_paths=allowed
        )
    
    def apply_assistant_patch(self, patch_ops):
        """Apply AI assistant patch to the current variant."""
        from assistant.patching import apply_patch_with_validation
        
        if not self._manager or not self._current_variant:
            return False, "No variant selected."
        
        ctx = self.get_assistant_context()
        if not ctx.content:
            return False, "No variant data available."
        
        ok, msg, new_content = apply_patch_with_validation(ctx, ctx.content, patch_ops)
        if not ok:
            return False, msg
        
        try:
            # Sanitize and validate the new content
            new_content = self._sanitize_variant_payload(new_content)
            
            # Update the manager
            self._manager.add_variant(self._current_variant, new_content)
            
            # Refresh the UI to reflect changes
            self._load_variant(self._current_variant)
            
            self.variants_modified.emit()
            return True, "Successfully applied changes."
        
        except Exception as e:
            logger.error(f"Failed to apply assistant patch: {e}", exc_info=True)
            return False, f"Failed to apply changes: {e}"
    
    def create_entry_from_llm(self, entry: dict):
        """Create a new variant from AI assistant suggestion."""
        if not self._manager:
            return False, "No manager available.", None
        
        try:
            # Ensure minimal required fields and generate unique ID
            proposed_name = (entry.get("name") or "New Variant").strip()
            
            # Generate variant ID from name or use provided ID
            if "id" in entry and entry["id"].strip():
                variant_id = entry["id"].strip()
            else:
                # Generate ID from name
                variant_id = proposed_name.lower().replace(" ", "_").replace("-", "_")
                # Remove special characters
                import re
                variant_id = re.sub(r'[^a-z0-9_]', '', variant_id)
            
            # Ensure uniqueness
            existing_variants = self._manager.data.get("variants", {})
            original_id = variant_id
            suffix = 1
            while variant_id in existing_variants:
                variant_id = f"{original_id}_{suffix}"
                suffix += 1
            
            # Sanitize and prepare variant data
            variant_data = self._sanitize_variant_payload(entry)
            variant_data["id"] = variant_id
            variant_data["name"] = proposed_name
            
            # Ensure required fields have defaults
            if "family_id" not in variant_data:
                variant_data["family_id"] = "humanoid_normal_base"
            if "description" not in variant_data:
                variant_data["description"] = f"A {proposed_name.lower()} variant."
            
            # Add to manager
            self._manager.add_variant(variant_id, variant_data)
            
            # Refresh UI
            self._refresh_variants_list()
            
            # Select the new variant
            for i in range(self.variants_list.count()):
                item = self.variants_list.item(i)
                if item.data(Qt.UserRole) == variant_id:
                    self.variants_list.setCurrentItem(item)
                    break
            
            self.variants_modified.emit()
            return True, "Successfully created variant.", variant_id
        
        except Exception as e:
            logger.error(f"Failed to create variant from LLM: {e}", exc_info=True)
            return False, f"Failed to create variant: {e}", None
    
    def get_domain_examples(self):
        """Get example variants for the AI assistant."""
        if not self._manager:
            return []
        
        variants = self._manager.data.get("variants", {})
        if not variants:
            return []
        
        # Return the first few variants as examples
        examples = []
        for variant_id, variant_data in list(variants.items())[:3]:
            example = dict(variant_data)
            example["_example_id"] = variant_id
            examples.append(example)
        
        return examples
    
    def get_reference_catalogs(self):
        """Get reference data for the AI assistant."""
        if not self._manager:
            return {}
        
        variants = self._manager.data.get("variants", {})
        
        # Collect existing names and IDs
        existing_names = []
        existing_ids = []
        existing_families = set()
        existing_roles = set()
        existing_abilities = set()
        existing_tags = set()
        
        for variant_id, variant_data in variants.items():
            existing_ids.append(variant_id)
            if "name" in variant_data:
                existing_names.append(variant_data["name"])
            if "family_id" in variant_data:
                existing_families.add(variant_data["family_id"])
            
            # Collect roles, abilities, and tags
            for role in variant_data.get("roles_add", []):
                existing_roles.add(role)
            for ability in variant_data.get("abilities_add", []):
                existing_abilities.add(ability)
            for tag in variant_data.get("tags_add", []):
                existing_tags.add(tag)
        
        # Common stat modifier fields
        stat_fields = ["hp", "damage", "defense", "initiative"]
        modifier_ops = ["add", "mul"]
        
        # Common role types
        common_roles = ["striker", "tank", "controller", "support", "skirmisher", "scout"]
        
        # Common culture prefixes
        cultures = ["concordant", "verdant", "crystalline", "ashen", "tempest"]
        
        # Common family patterns
        common_families = [
            "concordant_citizen", "verdant_wanderer", "crystalline_adept", 
            "ashen_nomad", "tempest_swashbuckler", "humanoid_normal_base",
            "beast_normal_base", "beast_easy_base", "beast_hard_base"
        ]
        
        return {
            "existing_names": sorted(existing_names),
            "existing_ids": sorted(existing_ids),
            "existing_families": sorted(existing_families),
            "common_families": common_families,
            "existing_roles": sorted(existing_roles),
            "common_roles": common_roles,
            "existing_abilities": sorted(existing_abilities),
            "existing_tags": sorted(existing_tags),
            "stat_fields": stat_fields,
            "modifier_operations": modifier_ops,
            "cultures": cultures,
            "stat_modifiers_structure": {
                "description": "Stat modifiers have 'add' and 'mul' operations applied in that order",
                "example": {"hp": {"add": 5, "mul": 1.2}, "damage": {"mul": 0.9}}
            }
        }
    
    def _sanitize_variant_payload(self, payload: dict) -> dict:
        """Sanitize incoming variant payload to fit the expected schema."""
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dictionary")
        
        sanitized = {}
        
        # Copy basic string fields
        for field in ["id", "name", "description", "family_id"]:
            if field in payload and isinstance(payload[field], str):
                sanitized[field] = payload[field].strip()
        
        # Handle stat modifiers
        if "stat_modifiers" in payload and isinstance(payload["stat_modifiers"], dict):
            stat_mods = {}
            for stat, mods in payload["stat_modifiers"].items():
                if isinstance(mods, dict):
                    clean_mods = {}
                    for op in ["add", "mul"]:
                        if op in mods and isinstance(mods[op], (int, float)):
                            clean_mods[op] = float(mods[op])
                    if clean_mods:
                        stat_mods[stat] = clean_mods
            if stat_mods:
                sanitized["stat_modifiers"] = stat_mods
        
        # Handle list fields
        for list_field in ["roles_add", "abilities_add", "tags_add"]:
            if list_field in payload:
                if isinstance(payload[list_field], list):
                    clean_list = [str(item).strip() for item in payload[list_field] if str(item).strip()]
                elif isinstance(payload[list_field], str):
                    # Handle comma-separated strings
                    clean_list = [item.strip() for item in payload[list_field].split(",") if item.strip()]
                else:
                    continue
                
                if clean_list:
                    sanitized[list_field] = clean_list
        
        return sanitized
