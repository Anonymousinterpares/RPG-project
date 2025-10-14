"""
Magic Systems editor component for the World Configurator Tool.
"""

import logging
import os
import re
from typing import Dict, List, Optional, Callable, Any

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFormLayout, QSpinBox,
    QDialog, QMessageBox, QSplitter, QScrollArea, QFrame, QComboBox,
    QTabWidget, QGridLayout, QCheckBox, QInputDialog, QTableWidget,
    QTableWidgetItem, QHeaderView
)

# Assuming these models are correctly defined in base_models
from ui.dialogs.base_dialog import BaseDialog
from models.base_models import MagicalSystem, Spell, SpellEffect, RacialAffinity, ClassAffinity
from models.world_data import MagicSystemManager
from utils.file_manager import load_json, get_project_root

logger = logging.getLogger("world_configurator.ui.magic_systems_editor")

class SpellEffectDialog(BaseDialog):
    """Dialog for editing a spell effect."""

    def __init__(self, parent=None, effect: Optional[SpellEffect] = None):
        """
        Initialize the spell effect edit dialog.

        Args:
            parent: The parent widget.
            effect: Optional existing effect to edit.
        """
        super().__init__(parent)
        self.setWindowTitle("Spell Effect")
        self.setMinimumWidth(450)

        # Effect to edit
        self.effect = effect or SpellEffect()

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Form layout for fields
        form = QFormLayout()

        # Target type combo
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(["target", "caster"])
        if self.effect.target_type == "caster":
            self.target_type_combo.setCurrentIndex(1)
        form.addRow("Target:", self.target_type_combo)

        # Effect type combo
        self.effect_type_combo = QComboBox()
        self.effect_type_combo.addItems(["damage", "healing", "stat_modification", "status_effect"])
        if self.effect.effect_type in ["healing", "stat_modification", "status_effect"]:
            self.effect_type_combo.setCurrentText(self.effect.effect_type)
        self.effect_type_combo.currentTextChanged.connect(self._update_form_visibility)
        form.addRow("Effect Type:", self.effect_type_combo)

        # Value field
        self.value_spin = QSpinBox()
        self.value_spin.setRange(-1000, 1000)
        self.value_spin.setValue(int(self.effect.value))
        form.addRow("Value:", self.value_spin)

        # Dice notation field
        self.dice_edit = QLineEdit(self.effect.dice_notation)
        self.dice_edit.setPlaceholderText("e.g., 2d6+3")
        form.addRow("Dice Notation:", self.dice_edit)

        # Stat affected field (for stat modifications)
        self.stat_combo = QComboBox()
        self.stat_combo.addItems(["", "STR", "DEX", "CON", "INT", "WIS", "CHA",
                                 "HP", "MP", "Stamina", "Initiative", "Defense",
                                 "Magic Resistance", "Melee Attack", "Ranged Attack", "Magic Attack"])
        if self.effect.stat_affected:
            self.stat_combo.setCurrentText(self.effect.stat_affected)
        form.addRow("Stat Affected:", self.stat_combo)

        # Status effect field (for status effects)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["", "Burning", "Poisoned", "Stunned", "Bleeding", "Frozen", "Weakened", "Blinded"])
        if self.effect.status_effect:
            self.status_combo.setCurrentText(self.effect.status_effect)
        form.addRow("Status Effect:", self.status_combo)

        # Duration field
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 100)
        self.duration_spin.setValue(self.effect.duration)
        self.duration_spin.setSpecialValueText("Instant")
        form.addRow("Duration (turns):", self.duration_spin)

        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.effect.description)
        self.desc_edit.setMinimumHeight(80)
        form.addRow("Description:", self.desc_edit)

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

        # Update visibility of fields based on initial effect type
        self._update_form_visibility(self.effect_type_combo.currentText())

    def _update_form_visibility(self, effect_type: str):
        """
        Update the visibility of form fields based on the effect type.

        Args:
            effect_type: The type of effect.
        """
        # Get the form layout
        form_layout = self.layout().itemAt(0).layout()

        # Show/hide stat affected field
        stat_visible = effect_type == "stat_modification"
        self.stat_combo.setVisible(stat_visible)
        stat_label = form_layout.labelForField(self.stat_combo)
        if stat_label: stat_label.setVisible(stat_visible)

        # Show/hide status effect field
        status_visible = effect_type == "status_effect"
        self.status_combo.setVisible(status_visible)
        status_label = form_layout.labelForField(self.status_combo)
        if status_label: status_label.setVisible(status_visible)

        # Show/hide duration field (only for non-instant effects)
        duration_visible = effect_type in ["stat_modification", "status_effect"]
        self.duration_spin.setVisible(duration_visible)
        duration_label = form_layout.labelForField(self.duration_spin)
        if duration_label: duration_label.setVisible(duration_visible)

    def get_effect(self) -> SpellEffect:
        """Get the edited effect."""
        self.effect.target_type = self.target_type_combo.currentText()
        self.effect.effect_type = self.effect_type_combo.currentText()
        self.effect.value = float(self.value_spin.value())
        self.effect.dice_notation = self.dice_edit.text()
        self.effect.stat_affected = self.stat_combo.currentText() if self.stat_combo.isVisible() else ""
        self.effect.status_effect = self.status_combo.currentText() if self.status_combo.isVisible() else ""
        self.effect.duration = self.duration_spin.value() if self.duration_spin.isVisible() else 0
        self.effect.description = self.desc_edit.toPlainText()
        return self.effect

class AtomDialog(QDialog):
    """Dialog for editing an effect atom (schema-aligned)."""

    def __init__(self, parent=None, atom: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Effect Atom")
        self.setMinimumWidth(520)
        self.atom = atom or {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Type
        self.type_combo = QComboBox(); self.type_combo.addItems([
            "damage", "heal", "resource_change", "buff", "debuff",
            "status_apply", "status_remove", "cleanse", "shield"
        ])
        self.type_combo.setToolTip("What the atom does (damage, heal, apply status, shield, etc.)")
        if isinstance(self.atom.get("type"), str):
            self.type_combo.setCurrentText(self.atom["type"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Type:", self.type_combo)

        # Selector
        self.selector_combo = QComboBox(); self.selector_combo.addItems(["self", "ally", "enemy", "area"])
        self.selector_combo.setToolTip("Who this atom targets: yourself, an ally, an enemy, or an area.")
        if isinstance(self.atom.get("selector"), str):
            self.selector_combo.setCurrentText(self.atom["selector"])
        form.addRow("Selector:", self.selector_combo)

        # Magnitude group (flat/dice/stat)
        self.mag_mode_combo = QComboBox(); self.mag_mode_combo.addItems(["flat", "dice", "stat"])
        self.mag_mode_combo.setToolTip("How the amount is determined: Flat value, Dice roll (NdS±M), or based on a stat.")
        mag = self.atom.get("magnitude") or {}
        if isinstance(mag, dict):
            if "dice" in mag: self.mag_mode_combo.setCurrentText("dice")
            elif "stat" in mag: self.mag_mode_combo.setCurrentText("stat")
            else: self.mag_mode_combo.setCurrentText("flat")
        form.addRow("Magnitude Mode:", self.mag_mode_combo)

        self.mag_flat_spin = QSpinBox(); self.mag_flat_spin.setRange(-100000, 100000)
        self.mag_flat_spin.setToolTip("Flat amount to apply (can be negative).")
        if isinstance(mag, dict) and "flat" in mag:
            try: self.mag_flat_spin.setValue(int(float(mag.get("flat", 0))))
            except Exception: pass
        form.addRow("Flat:", self.mag_flat_spin)

        # Dice magnitude controls (similar to Items editor)
        self.dice_base_combo = QComboBox()
        base_notations: List[str] = []
        for n in (1, 2, 3, 4):
            for s in (4, 6, 8, 10, 12, 20):
                base_notations.append(f"{n}d{s}")
        for bn in base_notations:
            self.dice_base_combo.addItem(bn)
        self.dice_base_combo.setToolTip("Choose NdS base (e.g., 2d6).")
        form.addRow("Dice Base (NdS):", self.dice_base_combo)

        self.dice_mod_sign = QComboBox(); self.dice_mod_sign.addItems(["+", "-"])
        self.dice_mod_sign.setToolTip("Sign for the dice modifier.")
        form.addRow("Modifier Sign:", self.dice_mod_sign)

        self.dice_mod_value = QSpinBox(); self.dice_mod_value.setRange(0, 100)
        self.dice_mod_value.setSpecialValueText("0")
        self.dice_mod_value.setToolTip("Modifier value to add/subtract after the roll.")
        form.addRow("Modifier Value:", self.dice_mod_value)

        # Preselect from magnitude.dice if present
        try:
            existing_dn = str(mag.get("dice", "")) if isinstance(mag, dict) else ""
            m = re.match(r"(\d+d\d+)([+\-])(\d+)$", existing_dn)
            if m:
                base, sign, mv = m.group(1), m.group(2), int(m.group(3))
                idx = self.dice_base_combo.findText(base)
                if idx >= 0:
                    self.dice_base_combo.setCurrentIndex(idx)
                self.dice_mod_sign.setCurrentText(sign)
                self.dice_mod_value.setValue(mv)
            elif existing_dn:
                idx = self.dice_base_combo.findText(existing_dn)
                if idx >= 0:
                    self.dice_base_combo.setCurrentIndex(idx)
        except Exception:
            pass

        mag_stat = mag if isinstance(mag, dict) else {}
        # Stat-based magnitude controls
        self.mag_stat_name_combo = QComboBox()
        self.mag_stat_name_combo.setEditable(False)
        self.mag_stat_name_combo.setToolTip("Which stat to base the amount on. Uses canonical IDs from stat registry.")
        form.addRow("Stat:", self.mag_stat_name_combo)

        self.mag_stat_coeff = QLineEdit(str(mag_stat.get("coeff", "")))
        self.mag_stat_coeff.setToolTip("Coefficient multiplied by the stat value.")
        form.addRow("Stat Coeff:", self.mag_stat_coeff)

        self.mag_stat_base = QLineEdit(str(mag_stat.get("base", "")))
        self.mag_stat_base.setToolTip("Base amount added after stat*coeff.")
        form.addRow("Stat Base:", self.mag_stat_base)

        # Duration
        dur = self.atom.get("duration") or {}
        self.duration_spin = QSpinBox(); self.duration_spin.setRange(0, 999)
        if isinstance(dur, dict):
            try: self.duration_spin.setValue(int(dur.get("value", 0)))
            except Exception: pass
        self.duration_spin.setToolTip("How long it lasts. 0 = instant (no duration). In combat: turns; outside: minutes. Stored as unified duration and translated by engine.")
        form.addRow("Duration:", self.duration_spin)

        # Type-specific fields
        self.damage_type_combo = QComboBox(); self.damage_type_combo.setEditable(True)
        # Populate with canonical list (fallback to built-ins if load fails)
        self.damage_type_combo.addItems(["", "slashing", "piercing", "bludgeoning", "fire", "cold", "lightning", "poison", "acid", "arcane"])
        if isinstance(self.atom.get("damage_type"), str): self.damage_type_combo.setCurrentText(self.atom["damage_type"])
        self.damage_type_combo.setToolTip("Typed damage used for mitigation and typed shields (optional for DoT; required for direct damage).")
        form.addRow("Damage type:", self.damage_type_combo)

        self.resource_combo = QComboBox(); self.resource_combo.addItems(["", "HEALTH", "MANA", "STAMINA", "RESOLVE"])
        self.resource_combo.setToolTip("Which resource changes (for resource change atoms).")
        if isinstance(self.atom.get("resource"), str): self.resource_combo.setCurrentText(self.atom["resource"])
        form.addRow("Resource:", self.resource_combo)

        # Modifiers table (for buff/debuff)
        self.mod_table = QTableWidget(0, 3)
        self.mod_table.setHorizontalHeaderLabels(["Stat", "Value", "%?"])
        self.mod_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for m in (self.atom.get("modifiers") or []):
            if isinstance(m, dict):
                row = self.mod_table.rowCount(); self.mod_table.insertRow(row)
                self.mod_table.setItem(row, 0, QTableWidgetItem(str(m.get("stat", ""))))
                self.mod_table.setItem(row, 1, QTableWidgetItem(str(m.get("value", 0))))
                self.mod_table.setItem(row, 2, QTableWidgetItem("yes" if m.get("is_percentage", False) else ""))
        # Add/remove buttons kept simple via context menu not implemented; instruct to double-click cells to edit
        self.mod_table.setToolTip("Add rows for stat modifiers (stat id, value, %?). Double-click cells to edit. 'yes' in %? column means percentage.")
        form.addRow("Modifiers:", self.mod_table)

        # Status fields
        self.status_edit = QLineEdit(str(self.atom.get("status", "")))
        self.status_types_edit = QLineEdit(", ".join(self.atom.get("status_types", [])) if isinstance(self.atom.get("status_types"), list) else "")
        self.status_edit.setToolTip("Named status to apply (e.g., Burning).")
        self.status_types_edit.setToolTip("For remove/cleanse: which status families to target.")
        form.addRow("Status name:", self.status_edit)
        form.addRow("Status types (for removal/cleanse):", self.status_types_edit)

        # Periodic effect for status_apply (human labels)
        self.periodic_combo = QComboBox(); self.periodic_combo.addItems(["None", "Damage over time", "Healing over time", "Regeneration"])
        self.periodic_combo.setToolTip("Optional periodic behavior for status: DoT/HoT/Regeneration.")
        # infer from tags
        tags_in = set(self.atom.get("tags", []) or [])
        if "damage_over_time" in tags_in:
            self.periodic_combo.setCurrentText("Damage over time")
        elif "healing_over_time" in tags_in:
            self.periodic_combo.setCurrentText("Healing over time")
        elif "regeneration" in tags_in:
            self.periodic_combo.setCurrentText("Regeneration")
        form.addRow("Periodic effect:", self.periodic_combo)

        self.periodic_amount_spin = QSpinBox(); self.periodic_amount_spin.setRange(-100000, 100000)
        self.periodic_amount_spin.setToolTip("Amount applied each turn while the status lasts (negative allowed).")
        # default 0, but if magnitude.flat present and type=status_apply, seed it
        try:
            if (self.atom.get("type") == "status_apply") and isinstance(self.atom.get("magnitude"), dict) and "flat" in self.atom.get("magnitude"):
                self.periodic_amount_spin.setValue(int(float(self.atom["magnitude"]["flat"])))
        except Exception:
            pass
        form.addRow("Amount per turn:", self.periodic_amount_spin)

        # Shield stacking rule
        self.stacking_combo = QComboBox(); self.stacking_combo.addItems(["none", "stack", "refresh", "replace"])
        self.stacking_combo.setToolTip("How repeated applications behave: none (ignore), stack (additive), refresh (reset timer), replace (overwrite).")
        if isinstance(self.atom.get("stacking_rule"), str): self.stacking_combo.setCurrentText(self.atom["stacking_rule"])
        form.addRow("Stacking Rule:", self.stacking_combo)

        # Tags, source_id, notes
        self.tags_edit = QLineEdit(", ".join(self.atom.get("tags", [])) if isinstance(self.atom.get("tags"), list) else "")
        self.tags_edit.setToolTip("Optional comma-separated tags (e.g., damage_over_time). The UI will add required tags for periodic effects.")
        self.source_id_edit = QLineEdit(str(self.atom.get("source_id", "")))
        self.source_id_edit.setToolTip("Stable identifier used for grouping or removing related effects.")
        self.notes_edit = QLineEdit(str(self.atom.get("notes", "")))
        self.notes_edit.setToolTip("Optional notes for authors; ignored by the engine.")
        form.addRow("Tags:", self.tags_edit)
        form.addRow("Source ID:", self.source_id_edit)
        form.addRow("Notes:", self.notes_edit)

        # Initialize canonical damage types list after widgets are created
        try:
            self._init_damage_type_list()
        except Exception:
            pass
        try:
            self._init_stat_list(preselect=str(mag_stat.get("stat", "")))
        except Exception:
            pass

        layout.addLayout(form)
        btns = QHBoxLayout()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        save = QPushButton("Save"); save.clicked.connect(self.accept); save.setDefault(True)
        btns.addWidget(cancel); btns.addWidget(save)
        layout.addLayout(btns)

        self.periodic_combo.currentTextChanged.connect(lambda _t: self._on_type_changed(self.type_combo.currentText()))
        self._on_type_changed(self.type_combo.currentText())

    def _on_type_changed(self, t: str):
        # Toggle relevant widgets
        typ = (t or "").lower()
        # magnitude always visible; resource only for resource_change
        self.resource_combo.setEnabled(typ == "resource_change")
        # damage_type for damage or shield (filter) and for DoT periodic
        enable_damage_type = typ in ("damage", "shield")

        # Show/hide magnitude widgets per mode
        mode = self.mag_mode_combo.currentText().lower()
        self.mag_flat_spin.setVisible(mode == "flat")
        self.dice_base_combo.setVisible(mode == "dice")
        self.dice_mod_sign.setVisible(mode == "dice")
        self.dice_mod_value.setVisible(mode == "dice")
        self.mag_stat_name_combo.setVisible(mode == "stat")
        self.mag_stat_coeff.setVisible(mode == "stat")
        self.mag_stat_base.setVisible(mode == "stat")
        # modifiers for buff/debuff only
        show_mods = typ in ("buff", "debuff")
        self.mod_table.setEnabled(show_mods); self.mod_table.setVisible(show_mods)
        # status fields for status_apply/remove/cleanse
        show_status = typ in ("status_apply", "status_remove", "cleanse")
        self.status_edit.setEnabled(typ == "status_apply")
        self.status_types_edit.setEnabled(typ in ("status_remove", "cleanse"))
        # stacking applicable to shield and statuses
        self.stacking_combo.setEnabled(typ in ("shield", "status_apply", "buff", "debuff"))

        # Periodic controls only meaningful for status_apply
        is_status_apply = (typ == "status_apply")
        self.periodic_combo.setEnabled(is_status_apply)
        self.periodic_amount_spin.setEnabled(is_status_apply)

        # If status/shield and no duration set, default to 1 (unified units)
        try:
            if typ in ("shield", "status_apply") and (self.duration_spin.value() <= 0):
                self.duration_spin.setValue(1)
        except Exception:
            pass

        # magnitude mode toggling (disabled if periodic is active on status_apply)
        periodic_mode = self.periodic_combo.currentText().lower() if hasattr(self, 'periodic_combo') else "none"
        disable_mag_controls = is_status_apply and periodic_mode in ("damage over time", "healing over time", "regeneration")
        mode = self.mag_mode_combo.currentText().lower()
        self.mag_flat_spin.setEnabled((mode == "flat") and not disable_mag_controls)
        self.dice_base_combo.setEnabled((mode == "dice") and not disable_mag_controls)
        self.dice_mod_sign.setEnabled((mode == "dice") and not disable_mag_controls)
        self.dice_mod_value.setEnabled((mode == "dice") and not disable_mag_controls)
        self.mag_stat_name_combo.setEnabled((mode == "stat") and not disable_mag_controls)
        self.mag_stat_coeff.setEnabled((mode == "stat") and not disable_mag_controls)
        self.mag_stat_base.setEnabled((mode == "stat") and not disable_mag_controls)

        # Enable damage type if appropriate
        if is_status_apply and periodic_mode == "damage over time":
            enable_damage_type = True
        self.damage_type_combo.setEnabled(enable_damage_type)

    def get_atom(self) -> Dict[str, Any]:
        atom: Dict[str, Any] = {}
        atom["type"] = self.type_combo.currentText()
        atom["selector"] = self.selector_combo.currentText()
        # magnitude (may be overridden by periodic status)
        mode = self.mag_mode_combo.currentText().lower()
        if mode == "flat":
            atom["magnitude"] = {"flat": float(self.mag_flat_spin.value())}
        elif mode == "dice":
            base = self.dice_base_combo.currentText().strip()
            sign = self.dice_mod_sign.currentText().strip()
            mv = int(self.dice_mod_value.value())
            dice_str = base if mv == 0 else f"{base}{sign}{mv}"
            atom["magnitude"] = {"dice": dice_str}
        else:
            # stat-based
            try:
                coeff = float(self.mag_stat_coeff.text().strip() or 0)
            except Exception:
                coeff = 0.0
            base = float(self.mag_stat_base.text().strip() or 0)
            stat_id = self.mag_stat_name_combo.currentData() or self.mag_stat_name_combo.currentText()
            atom["magnitude"] = {"stat": str(stat_id).strip().upper(), "coeff": coeff, "base": base}
        # duration: unified units (engine translates: turns in combat, minutes outside)
        val = int(self.duration_spin.value())
        # Enforce minimum 1 for status_apply and shield to satisfy schema and gameplay semantics
        if atom["type"] in ("status_apply", "shield") and val <= 0:
            val = 1
        if val > 0:
            atom["duration"] = {"unit": "turns", "value": val}
        # type-specific
        if atom["type"] == "damage":
            dt = self.damage_type_combo.currentText().strip()
            if dt: atom["damage_type"] = dt
        if atom["type"] == "resource_change":
            rc = self.resource_combo.currentText().strip() or "HEALTH"
            atom["resource"] = rc
        if atom["type"] in ("buff", "debuff"):
            mods = []
            for r in range(self.mod_table.rowCount()):
                stat = self.mod_table.item(r,0).text() if self.mod_table.item(r,0) else ""
                val = self.mod_table.item(r,1).text() if self.mod_table.item(r,1) else "0"
                pct = self.mod_table.item(r,2).text() if self.mod_table.item(r,2) else ""
                try:
                    v = float(val)
                except Exception:
                    v = 0.0
                mods.append({"stat": stat.strip().upper(), "value": v, "is_percentage": (pct.strip().lower() in ("y","yes","true","1"))})
            if mods:
                atom["modifiers"] = mods
        if atom["type"] == "status_apply":
            s = self.status_edit.text().strip()
            if s: atom["status"] = s
            # Periodic behavior mapping into tags + magnitude
            periodic = (self.periodic_combo.currentText() or "None").lower()
            tags_set = set([t.strip() for t in self.tags_edit.text().split(',') if t.strip()])
            if periodic == "damage over time":
                tags_set.add("damage_over_time")
                atom["magnitude"] = {"flat": float(self.periodic_amount_spin.value())}
                dt = self.damage_type_combo.currentText().strip()
                if dt: atom["damage_type"] = dt
            elif periodic == "healing over time":
                tags_set.add("healing_over_time")
                atom["magnitude"] = {"flat": float(self.periodic_amount_spin.value())}
            elif periodic == "regeneration":
                tags_set.add("regeneration")
                atom["magnitude"] = {"flat": float(self.periodic_amount_spin.value())}
            # write back tags if any
            if tags_set:
                atom["tags"] = sorted(tags_set)
        if atom["type"] in ("status_remove", "cleanse"):
            sts = [t.strip() for t in self.status_types_edit.text().split(',') if t.strip()]
            if sts:
                atom["status_types"] = sts
        if atom["type"] == "shield":
            # use damage_type as filter if provided
            dt = self.damage_type_combo.currentText().strip()
            if dt: atom["damage_type"] = dt
        # meta
        sr = self.stacking_combo.currentText().strip()
        if sr and sr != "none": atom["stacking_rule"] = sr
        # if tags already set by periodic, merge with free-form tags
        if "tags" not in atom:
            tags = [t.strip() for t in self.tags_edit.text().split(',') if t.strip()]
            if tags: atom["tags"] = tags
        else:
            extra_tags = [t.strip() for t in self.tags_edit.text().split(',') if t.strip()]
            if extra_tags:
                merged = sorted(set(atom["tags"]) | set(extra_tags))
                atom["tags"] = merged
        sid = self.source_id_edit.text().strip()
        if sid: atom["source_id"] = sid
        notes = self.notes_edit.text().strip()
        if notes: atom["notes"] = notes
        return atom


    def _init_damage_type_list(self) -> None:
        """Load canonical damage types from config and populate combos. Warn if missing/discrepant."""
        try:
            root = get_project_root()
            path = os.path.join(root, 'config', 'gameplay', 'canonical_lists.json')
            data = load_json(path) if os.path.exists(path) else None
            types = []
            if isinstance(data, dict) and isinstance(data.get('damage_types'), list):
                types = [str(x).strip() for x in data['damage_types'] if isinstance(x, str)]
            if types:
                # Reset with canonical
                current_dt = self.damage_type_combo.currentText().strip()
                self.damage_type_combo.clear()
                self.damage_type_combo.addItem("")
                self.damage_type_combo.addItems(types)
                if current_dt:
                    self.damage_type_combo.setCurrentText(current_dt)
        except Exception as e:
            # Non-fatal; keep defaults
            logger = logging.getLogger("world_configurator.ui.magic_systems_editor")
            logger.warning(f"Failed to load canonical damage types: {e}")

    def _init_stat_list(self, preselect: str = "") -> None:
        """Load canonical stat ids from config/character/stat_registry.json and populate the stat combo."""
        try:
            root = get_project_root()
            path = os.path.join(root, 'config', 'character', 'stat_registry.json')
            data = load_json(path) if os.path.exists(path) else None
            options = []  # (label, canonical_upper)
            if isinstance(data, dict) and isinstance(data.get('stats'), list):
                for entry in data['stats']:
                    if not isinstance(entry, dict):
                        continue
                    if not bool(entry.get('supported', False)):
                        continue
                    key = str(entry.get('key', '')).strip()
                    label = str(entry.get('label', key.title())).strip()
                    if not key:
                        continue
                    canon = key.replace(' ', '_').upper()
                    options.append((label, canon))
            if options:
                current = self.mag_stat_name_combo.currentData()
                self.mag_stat_name_combo.clear()
                for label, canon in options:
                    self.mag_stat_name_combo.addItem(label, userData=canon)
                pre = (preselect or '').strip()
                if pre:
                    idx = -1
                    for i in range(self.mag_stat_name_combo.count()):
                        if str(self.mag_stat_name_combo.itemData(i)).upper() == pre.upper():
                            idx = i; break
                    if idx >= 0:
                        self.mag_stat_name_combo.setCurrentIndex(idx)
        except Exception as e:
            logger = logging.getLogger("world_configurator.ui.magic_systems_editor")
            logger.warning(f"Failed to load stat registry: {e}")

class SpellDialog(QDialog):
    """Dialog for editing a spell."""

    def __init__(self, parent=None, spell: Optional[Spell] = None):
        """
        Initialize the spell edit dialog.

        Args:
            parent: The parent widget.
            spell: Optional existing spell to edit.
        """
        super().__init__(parent)
        self.setWindowTitle("Spell")
        self.setMinimumWidth(600)
        self.setMinimumHeight(600)

        # Spell to edit
        self.spell = spell or Spell.create_new("New Spell", "")

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Create tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Basic info tab
        basic_tab = QWidget()
        self.tabs.addTab(basic_tab, "Basic Info")

        basic_layout = QFormLayout(basic_tab)

        # Name field
        self.name_edit = QLineEdit(self.spell.name)
        basic_layout.addRow("Name:", self.name_edit)

        # Description field
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.spell.description)
        self.desc_edit.setMinimumHeight(100)
        basic_layout.addRow("Description:", self.desc_edit)

        # Level field
        self.level_spin = QSpinBox()
        self.level_spin.setRange(1, 10)
        self.level_spin.setValue(self.spell.level)
        basic_layout.addRow("Level:", self.level_spin)

        # Mana cost field
        self.mana_spin = QSpinBox()
        self.mana_spin.setRange(0, 1000)
        self.mana_spin.setValue(self.spell.mana_cost)
        basic_layout.addRow("Mana Cost:", self.mana_spin)

        # Casting time field
        self.cast_time_edit = QLineEdit(self.spell.casting_time)
        basic_layout.addRow("Casting Time:", self.cast_time_edit)

        # Range field
        self.range_edit = QLineEdit(self.spell.range)
        basic_layout.addRow("Range:", self.range_edit)

        # Target field
        self.target_combo = QComboBox()
        self.target_combo.addItems(["single", "area", "self", "multiple", "all_enemies", "all_allies"])
        if self.spell.target in ["area", "self", "multiple", "all_enemies", "all_allies"]:
            self.target_combo.setCurrentText(self.spell.target)
        basic_layout.addRow("Target:", self.target_combo)

        # Combat Role field (new)
        self.combat_role_combo = QComboBox()
        self.combat_role_combo.addItems(["offensive", "defensive", "utility"])
        try:
            # Default to 'offensive' if missing
            current_role = getattr(self.spell, 'combat_role', 'offensive') or 'offensive'
            if current_role not in ["offensive", "defensive", "utility"]:
                current_role = 'offensive'
            self.combat_role_combo.setCurrentText(current_role)
        except Exception:
            self.combat_role_combo.setCurrentText('offensive')
        basic_layout.addRow("Combat Role:", self.combat_role_combo)

        # Components field
        self.components_edit = QLineEdit(", ".join(self.spell.components))
        self.components_edit.setPlaceholderText("component1, component2, ...")
        basic_layout.addRow("Components:", self.components_edit)

        # Tags field
        self.tags_edit = QLineEdit(", ".join(self.spell.tags))
        self.tags_edit.setPlaceholderText("tag1, tag2, ...")
        basic_layout.addRow("Tags:", self.tags_edit)

        # Effects tab (legacy effects; kept for backward compatibility)
        effects_tab = QWidget()
        self.tabs.addTab(effects_tab, "Effects (legacy)")

        effects_layout = QVBoxLayout(effects_tab)

        # Effects list
        effects_label = QLabel("Spell Effects:")
        effects_label.setStyleSheet("font-weight: bold;")
        effects_layout.addWidget(effects_label)

        self.effects_list = QListWidget()
        self.effects_list.setMinimumHeight(200)
        self.effects_list.itemDoubleClicked.connect(self._edit_effect)
        effects_layout.addWidget(self.effects_list)

        # Load existing effects
        for effect in self.spell.effects:
            self._add_effect_to_list(effect)

        # Effect buttons
        effect_btn_layout = QHBoxLayout()

        self.add_effect_btn = QPushButton("Add Effect")
        self.add_effect_btn.clicked.connect(self._add_effect)
        effect_btn_layout.addWidget(self.add_effect_btn)

        self.edit_effect_btn = QPushButton("Edit Effect")
        self.edit_effect_btn.clicked.connect(lambda: self._edit_effect(self.effects_list.currentItem()))
        effect_btn_layout.addWidget(self.edit_effect_btn)

        self.remove_effect_btn = QPushButton("Remove Effect")
        self.remove_effect_btn.clicked.connect(self._remove_effect)
        effect_btn_layout.addWidget(self.remove_effect_btn)

        effects_layout.addLayout(effect_btn_layout)

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

        # --- Effect Atoms Tab (NEW) ---
        atoms_tab = QWidget()
        self.tabs.addTab(atoms_tab, "Effect Atoms")
        atoms_layout = QVBoxLayout(atoms_tab)

        atoms_label = QLabel("Effect Atoms:")
        atoms_label.setStyleSheet("font-weight: bold;")
        atoms_layout.addWidget(atoms_label)

        self.atoms_list = QListWidget(); self.atoms_list.setMinimumHeight(200)
        self.atoms_list.itemDoubleClicked.connect(self._edit_atom)
        atoms_layout.addWidget(self.atoms_list)

        # load existing atoms if present
        try:
            for a in getattr(self.spell, 'effect_atoms', []) or []:
                self._add_atom_to_list(a)
        except Exception:
            pass

        atom_btns = QHBoxLayout()
        self.add_atom_btn = QPushButton("Add Atom"); self.add_atom_btn.clicked.connect(self._add_atom)
        self.edit_atom_btn = QPushButton("Edit Atom"); self.edit_atom_btn.clicked.connect(lambda: self._edit_atom(self.atoms_list.currentItem()))
        self.remove_atom_btn = QPushButton("Remove Atom"); self.remove_atom_btn.clicked.connect(self._remove_atom)
        atom_btns.addWidget(self.add_atom_btn); atom_btns.addWidget(self.edit_atom_btn); atom_btns.addWidget(self.remove_atom_btn)
        atoms_layout.addLayout(atom_btns)

    def _add_atom_to_list(self, atom: Dict[str, Any]):
        text = f"{atom.get('type','?')} -> {atom.get('selector','?')}"
        # Append key details
        if atom.get('type') == 'damage':
            text += f" [{atom.get('damage_type','')}]"
        if atom.get('type') == 'resource_change':
            text += f" [{atom.get('resource','')}]"
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, atom)
        self.atoms_list.addItem(item)

    def _add_atom(self):
        dlg = AtomDialog(self)
        if dlg.exec() == QDialog.Accepted:
            atom = dlg.get_atom()
            self._add_atom_to_list(atom)

    def _edit_atom(self, item: Optional[QListWidgetItem]):
        if not item:
            return
        atom = item.data(Qt.UserRole)
        dlg = AtomDialog(self, atom)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.get_atom()
            row = self.atoms_list.row(item)
            self.atoms_list.takeItem(row)
            self._add_atom_to_list(updated)

    def _remove_atom(self):
        item = self.atoms_list.currentItem()
        if not item:
            return
        res = QMessageBox.question(self, "Confirm Deletion", "Delete selected effect atom?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if res == QMessageBox.Yes:
            self.atoms_list.takeItem(self.atoms_list.row(item))

    def _add_effect_to_list(self, effect: SpellEffect):
        """
        Add an effect to the effects list.

        Args:
            effect: The effect to add.
        """
        # Create an effect description for the list
        effect_text = f"{effect.target_type.capitalize()} - {effect.effect_type.capitalize()}"

        if effect.effect_type == "damage" or effect.effect_type == "healing":
            if effect.dice_notation:
                effect_text += f": {effect.dice_notation}"
            else:
                effect_text += f": {int(effect.value)}"

        elif effect.effect_type == "stat_modification":
            effect_text += f": {effect.stat_affected} {'+' if effect.value >= 0 else ''}{int(effect.value)}"
            if effect.duration > 0:
                effect_text += f" for {effect.duration} turns"

        elif effect.effect_type == "status_effect":
            effect_text += f": {effect.status_effect}"
            if effect.duration > 0:
                effect_text += f" for {effect.duration} turns"

        item = QListWidgetItem(effect_text)
        item.setData(Qt.UserRole, effect)
        self.effects_list.addItem(item)

    def _add_effect(self):
        """Add a new spell effect."""
        dialog = SpellEffectDialog(self)

        if dialog.exec() == QDialog.Accepted:
            effect = dialog.get_effect()
            self._add_effect_to_list(effect)

    def _edit_effect(self, item: Optional[QListWidgetItem]):
        """
        Edit a spell effect.

        Args:
            item: The list item to edit, or None.
        """
        if not item:
            return

        effect = item.data(Qt.UserRole)
        dialog = SpellEffectDialog(self, effect)

        if dialog.exec() == QDialog.Accepted:
            updated_effect = dialog.get_effect()

            # Update the effect in the list item's data
            item.setData(Qt.UserRole, updated_effect)

            # Re-render the list item text
            row = self.effects_list.row(item)
            self.effects_list.takeItem(row) # Remove temporarily
            self._add_effect_to_list(updated_effect) # Re-add with new text/data

            # Optionally, re-select the item
            # self.effects_list.setCurrentRow(row) # Might change order if sorting is applied

    def _remove_effect(self):
        """Remove the selected spell effect."""
        item = self.effects_list.currentItem()
        if not item:
            return

        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this effect?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self.effects_list.takeItem(self.effects_list.row(item))

    def get_spell(self) -> Spell:
        """Get the edited spell."""
        # Update basic info
        self.spell.name = self.name_edit.text()
        self.spell.description = self.desc_edit.toPlainText()
        self.spell.level = self.level_spin.value()
        self.spell.mana_cost = self.mana_spin.value()
        self.spell.casting_time = self.cast_time_edit.text()
        self.spell.range = self.range_edit.text()
        self.spell.target = self.target_combo.currentText()

        # Update components and tags (split by comma)
        self.spell.components = [s.strip() for s in self.components_edit.text().split(',') if s.strip()]
        self.spell.tags = [s.strip() for s in self.tags_edit.text().split(',') if s.strip()]

        # Update combat role (new)
        try:
            self.spell.combat_role = self.combat_role_combo.currentText()
        except Exception:
            self.spell.combat_role = 'offensive'

        # Update effects
        self.spell.effects = []
        for i in range(self.effects_list.count()):
            effect = self.effects_list.item(i).data(Qt.UserRole)
            self.spell.effects.append(effect)

        # Update effect atoms
        try:
            self.spell.effect_atoms = []
            for i in range(self.atoms_list.count()):
                atom = self.atoms_list.item(i).data(Qt.UserRole)
                if isinstance(atom, dict):
                    self.spell.effect_atoms.append(atom)
        except Exception:
            pass

        return self.spell

class RacialAffinityDialog(QDialog):
    """
    Dialog for editing racial affinity for a magic system.
    """

    def __init__(self, parent=None, race_name: str = "", affinity: Optional[RacialAffinity] = None):
        """
        Initialize the racial affinity edit dialog.

        Args:
            parent: The parent widget.
            race_name: The name of the race.
            affinity: Optional existing affinity to edit.
        """
        super().__init__(parent)
        self.setWindowTitle(f"Racial Affinity: {race_name}")
        self.setMinimumWidth(400)

        self.race_name = race_name
        self.affinity = affinity or RacialAffinity()

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Form layout for fields
        form = QFormLayout()

        # Affinity level combo
        self.affinity_combo = QComboBox()
        self.affinity_combo.addItems(["Very High", "High", "Medium", "Low", "Very Low"])
        self.affinity_combo.setCurrentText(self.affinity.affinity_level)
        form.addRow("Affinity Level:", self.affinity_combo)

        # Learning difficulty combo
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Very Easy", "Easy", "Moderate", "Hard", "Very Hard", "Extremely Hard"])
        self.difficulty_combo.setCurrentText(self.affinity.learning_difficulty)
        form.addRow("Learning Difficulty:", self.difficulty_combo)

        # Natural talent checkbox
        self.natural_talent_check = QCheckBox("Has Natural Talent")
        self.natural_talent_check.setChecked(self.affinity.natural_talent)
        form.addRow("", self.natural_talent_check)

        # Bonus effects field
        self.bonus_edit = QLineEdit(self.affinity.bonus_effects or "")
        self.bonus_edit.setPlaceholderText("e.g., 20% reduced mana cost for all spells")
        form.addRow("Bonus Effects:", self.bonus_edit)

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

    def get_affinity(self) -> RacialAffinity:
        """Get the edited racial affinity."""
        self.affinity.affinity_level = self.affinity_combo.currentText()
        self.affinity.learning_difficulty = self.difficulty_combo.currentText()
        self.affinity.natural_talent = self.natural_talent_check.isChecked()

        bonus_text = self.bonus_edit.text().strip()
        self.affinity.bonus_effects = bonus_text if bonus_text else None

        return self.affinity

class ClassAffinityDialog(QDialog):
    """
    Dialog for editing class affinity for a magic system.
    """

    def __init__(self, parent=None, class_name: str = "", affinity: Optional[ClassAffinity] = None):
        """
        Initialize the class affinity edit dialog.

        Args:
            parent: The parent widget.
            class_name: The name of the class.
            affinity: Optional existing affinity to edit.
        """
        super().__init__(parent)
        self.setWindowTitle(f"Class Affinity: {class_name}")
        self.setMinimumWidth(400)

        self.class_name = class_name
        self.affinity = affinity or ClassAffinity()

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Form layout for fields
        form = QFormLayout()

        # Affinity level combo
        self.affinity_combo = QComboBox()
        self.affinity_combo.addItems(["Very High", "High", "Medium", "Low", "Very Low"])
        self.affinity_combo.setCurrentText(self.affinity.affinity_level)
        form.addRow("Affinity Level:", self.affinity_combo)

        # Learning difficulty combo
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Very Easy", "Easy", "Moderate", "Hard", "Very Hard", "Extremely Hard"])
        self.difficulty_combo.setCurrentText(self.affinity.learning_difficulty)
        form.addRow("Learning Difficulty:", self.difficulty_combo)

        # Required stats section
        stats_label = QLabel("Required Stats:")
        stats_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        form.addRow(stats_label)

        # Create a grid for stat inputs
        stats_grid = QGridLayout()

        # Define possible stats
        self.stat_edits = {}
        stats = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

        # Create spinboxes for each stat
        for i, stat in enumerate(stats):
            label = QLabel(f"{stat}:")
            spinbox = QSpinBox()
            spinbox.setRange(0, 20)  # Assuming max stat is 20
            spinbox.setValue(self.affinity.required_stats.get(stat, 0))
            spinbox.setSpecialValueText("None")  # Display "None" for 0

            self.stat_edits[stat] = spinbox

            # Position in a 3x2 grid
            row = i // 2
            col = i % 2 * 2  # Use column 0 and 2

            stats_grid.addWidget(label, row, col)
            stats_grid.addWidget(spinbox, row, col + 1)

        form.addRow("", stats_grid) # Add the grid layout to the form

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

    def get_affinity(self) -> ClassAffinity:
        """Get the edited class affinity."""
        self.affinity.affinity_level = self.affinity_combo.currentText()
        self.affinity.learning_difficulty = self.difficulty_combo.currentText()

        # Update required stats
        required_stats = {}
        for stat, spinbox in self.stat_edits.items():
            value = spinbox.value()
            if value > 0:
                required_stats[stat] = value

        self.affinity.required_stats = required_stats

        return self.affinity

class MagicSystemDialog(QDialog):
    """
    Dialog for editing a magic system.
    """

    def __init__(self, parent=None, magic_system: Optional[MagicalSystem] = None):
        """
        Initialize the magic system edit dialog.

        Args:
            parent: The parent widget.
            magic_system: Optional existing magic system to edit.
        """
        super().__init__(parent)
        self.setWindowTitle("Magic System")
        self.setMinimumWidth(650) # Increased width slightly for tabs
        self.setMinimumHeight(600) # Increased height slightly

        # Magic system to edit
        # Make a deep copy to avoid modifying the original if cancelled
        import copy
        self.magic_system = copy.deepcopy(magic_system) if magic_system else MagicalSystem.create_new("New Magic System", "")
        # Ensure spells dict exists if it's a new system or loaded without it
        if not hasattr(self.magic_system, 'spells') or self.magic_system.spells is None:
             self.magic_system.spells = {}
        if not hasattr(self.magic_system, 'racial_affinities') or self.magic_system.racial_affinities is None:
             self.magic_system.racial_affinities = {}
        if not hasattr(self.magic_system, 'class_affinities') or self.magic_system.class_affinities is None:
             self.magic_system.class_affinities = {}


        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Create tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Basic info tab ---
        basic_tab = QWidget()
        self.tabs.addTab(basic_tab, "Basic Info")
        basic_layout = QFormLayout(basic_tab)
        # (Keep all existing fields for Name, Description, Origin, etc. here)
        self.name_edit = QLineEdit(self.magic_system.name)
        basic_layout.addRow("Name:", self.name_edit)
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.magic_system.description)
        self.desc_edit.setMinimumHeight(80)
        basic_layout.addRow("Description:", self.desc_edit)
        self.origin_edit = QTextEdit()
        self.origin_edit.setPlainText(self.magic_system.origin)
        self.origin_edit.setMinimumHeight(50)
        basic_layout.addRow("Origin:", self.origin_edit)
        self.limitations_edit = QTextEdit()
        self.limitations_edit.setPlainText(self.magic_system.limitations)
        self.limitations_edit.setMinimumHeight(50)
        basic_layout.addRow("Limitations:", self.limitations_edit)
        self.practitioners_edit = QTextEdit()
        self.practitioners_edit.setPlainText(self.magic_system.practitioners)
        self.practitioners_edit.setMinimumHeight(50)
        basic_layout.addRow("Practitioners:", self.practitioners_edit)
        self.cultural_edit = QTextEdit()
        self.cultural_edit.setPlainText(self.magic_system.cultural_significance)
        self.cultural_edit.setMinimumHeight(50)
        basic_layout.addRow("Cultural Significance:", self.cultural_edit)
        basic_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)


        # --- Spells Tab (NEW) ---
        spells_tab = QWidget()
        self.tabs.addTab(spells_tab, "Spells")
        spells_layout = QVBoxLayout(spells_tab)

        spells_label = QLabel("Spells:")
        spells_label.setStyleSheet("font-weight: bold;")
        spells_layout.addWidget(spells_label)

        self.spells_list = QListWidget()
        self.spells_list.setMinimumHeight(250)
        self.spells_list.itemDoubleClicked.connect(self._edit_spell)
        spells_layout.addWidget(self.spells_list)

        # Load existing spells
        if self.magic_system.spells: # Check if spells dict exists and is not None
            for spell_id, spell in self.magic_system.spells.items():
                self._add_spell_to_list(spell)

        # Spell buttons
        spell_btn_layout = QHBoxLayout()
        self.add_spell_btn = QPushButton("Add Spell")
        self.add_spell_btn.clicked.connect(self._add_spell)
        spell_btn_layout.addWidget(self.add_spell_btn)

        self.edit_spell_btn = QPushButton("Edit Spell")
        self.edit_spell_btn.clicked.connect(lambda: self._edit_spell(self.spells_list.currentItem()))
        spell_btn_layout.addWidget(self.edit_spell_btn)

        self.remove_spell_btn = QPushButton("Remove Spell")
        self.remove_spell_btn.clicked.connect(self._remove_spell)
        spell_btn_layout.addWidget(self.remove_spell_btn)

        spells_layout.addLayout(spell_btn_layout)


        # --- Racial Affinities tab ---
        racial_tab = QWidget()
        self.tabs.addTab(racial_tab, "Race Affinities")
        racial_layout = QVBoxLayout(racial_tab)
        # (Keep existing Race Affinities list and buttons here)
        race_label = QLabel("Race Affinities:")
        race_label.setStyleSheet("font-weight: bold;")
        racial_layout.addWidget(race_label)
        self.races_list = QListWidget()
        self.races_list.setMinimumHeight(250)
        self.races_list.itemDoubleClicked.connect(self._edit_race_affinity)
        racial_layout.addWidget(self.races_list)
        # Load existing racial affinities
        if self.magic_system.racial_affinities:
            for race_name, affinity in self.magic_system.racial_affinities.items():
                self._add_race_affinity_to_list(race_name, affinity)
        # Race affinity buttons
        race_btn_layout = QHBoxLayout()
        self.add_race_btn = QPushButton("Add Race")
        self.add_race_btn.clicked.connect(self._add_race_affinity)
        race_btn_layout.addWidget(self.add_race_btn)
        self.edit_race_btn = QPushButton("Edit Race")
        self.edit_race_btn.clicked.connect(lambda: self._edit_race_affinity(self.races_list.currentItem()))
        race_btn_layout.addWidget(self.edit_race_btn)
        self.remove_race_btn = QPushButton("Remove Race")
        self.remove_race_btn.clicked.connect(self._remove_race_affinity)
        race_btn_layout.addWidget(self.remove_race_btn)
        racial_layout.addLayout(race_btn_layout)


        # --- Class Affinities tab ---
        class_tab = QWidget()
        self.tabs.addTab(class_tab, "Class Affinities")
        class_layout = QVBoxLayout(class_tab)
        # (Keep existing Class Affinities list and buttons here)
        class_label = QLabel("Class Affinities:")
        class_label.setStyleSheet("font-weight: bold;")
        class_layout.addWidget(class_label)
        self.classes_list = QListWidget()
        self.classes_list.setMinimumHeight(250)
        self.classes_list.itemDoubleClicked.connect(self._edit_class_affinity)
        class_layout.addWidget(self.classes_list)
        # Load existing class affinities
        if self.magic_system.class_affinities:
            for class_name, affinity in self.magic_system.class_affinities.items():
                self._add_class_affinity_to_list(class_name, affinity)
        # Class affinity buttons
        class_btn_layout = QHBoxLayout()
        self.add_class_btn = QPushButton("Add Class")
        self.add_class_btn.clicked.connect(self._add_class_affinity)
        class_btn_layout.addWidget(self.add_class_btn)
        self.edit_class_btn = QPushButton("Edit Class")
        self.edit_class_btn.clicked.connect(lambda: self._edit_class_affinity(self.classes_list.currentItem()))
        class_btn_layout.addWidget(self.edit_class_btn)
        self.remove_class_btn = QPushButton("Remove Class")
        self.remove_class_btn.clicked.connect(self._remove_class_affinity)
        class_btn_layout.addWidget(self.remove_class_btn)
        class_layout.addLayout(class_btn_layout)


        # --- Dialog Buttons ---
        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    # --- Spell Methods (NEW) ---

    def _add_atom_to_list(self, atom: Dict[str, Any]):
        text = f"{atom.get('type','?')} -> {atom.get('selector','?')}"
        # Append key details
        if atom.get('type') == 'damage':
            text += f" [{atom.get('damage_type','')}]"
        if atom.get('type') == 'resource_change':
            text += f" [{atom.get('resource','')}]"
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, atom)
        self.atoms_list.addItem(item)

    def _add_atom(self):
        dlg = AtomDialog(self)
        if dlg.exec() == QDialog.Accepted:
            atom = dlg.get_atom()
            self._add_atom_to_list(atom)

    def _edit_atom(self, item: Optional[QListWidgetItem]):
        if not item:
            return
        atom = item.data(Qt.UserRole)
        dlg = AtomDialog(self, atom)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.get_atom()
            row = self.atoms_list.row(item)
            self.atoms_list.takeItem(row)
            self._add_atom_to_list(updated)

    def _remove_atom(self):
        item = self.atoms_list.currentItem()
        if not item:
            return
        res = QMessageBox.question(self, "Confirm Deletion", "Delete selected effect atom?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if res == QMessageBox.Yes:
            self.atoms_list.takeItem(self.atoms_list.row(item))

    def _add_spell_to_list(self, spell: Spell):
        """Add a spell to the spells list widget."""
        item_text = f"{spell.name}"
        if spell.level > 0: # Show level if > 0
            item_text += f" (Level {spell.level})"
        if spell.mana_cost > 0:
             item_text += f" [{spell.mana_cost} Mana]"

        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, spell) # Store the whole spell object
        self.spells_list.addItem(item)
        # Sort list by name after adding
        self.spells_list.sortItems(Qt.AscendingOrder)


    def _add_spell(self):
        """Add a new spell using the SpellDialog."""
        dialog = SpellDialog(self) # Create a dialog for a new spell

        if dialog.exec() == QDialog.Accepted:
            new_spell = dialog.get_spell()

            # Ensure the new spell has a unique ID within this system
            if not new_spell.id or new_spell.id in self.magic_system.spells:
                new_spell.id = Spell.generate_id()
                while new_spell.id in self.magic_system.spells: # Ensure uniqueness
                    new_spell.id = Spell.generate_id()

            # Add to the internal magic system object
            self.magic_system.spells[new_spell.id] = new_spell

            # Add to the list widget
            self._add_spell_to_list(new_spell)
            logger.info(f"Added spell '{new_spell.name}' to magic system '{self.magic_system.name}' (in dialog).")

    def _edit_spell(self, item: Optional[QListWidgetItem]):
        """Edit the selected spell using the SpellDialog."""
        if not item:
            current_item = self.spells_list.currentItem()
            if not current_item:
                 QMessageBox.information(self, "Edit Spell", "Please select a spell to edit.")
                 return
            item = current_item # Use current selection if item not passed (e.g., from button)

        original_spell = item.data(Qt.UserRole)
        if not original_spell or not isinstance(original_spell, Spell):
            logger.error("Could not retrieve spell data from list item for editing.")
            QMessageBox.critical(self, "Error", "Could not retrieve spell data for editing.")
            return

        # Pass a copy to the dialog, so cancelling doesn't affect the list item's data yet
        import copy
        spell_copy = copy.deepcopy(original_spell)
        dialog = SpellDialog(self, spell_copy)

        if dialog.exec() == QDialog.Accepted:
            updated_spell = dialog.get_spell()
            updated_spell.id = original_spell.id # Ensure ID remains the same

            # Update the spell in the internal magic system object
            self.magic_system.spells[updated_spell.id] = updated_spell

            # Update the list widget: Remove old, add new
            row = self.spells_list.row(item)
            self.spells_list.takeItem(row)
            self._add_spell_to_list(updated_spell)

            # Try to reselect (list might be sorted differently now)
            items = self.spells_list.findItems(updated_spell.name, Qt.MatchExactly)
            if items:
                # Find the one with the correct ID if names aren't unique (though they should be)
                for found_item in items:
                    if found_item.data(Qt.UserRole).id == updated_spell.id:
                        self.spells_list.setCurrentItem(found_item)
                        break

            logger.info(f"Edited spell '{updated_spell.name}' in magic system '{self.magic_system.name}' (in dialog).")


    def _remove_spell(self):
        """Remove the selected spell."""
        item = self.spells_list.currentItem()
        if not item:
            QMessageBox.information(self, "Remove Spell", "Please select a spell to remove.")
            return

        spell_to_remove = item.data(Qt.UserRole)
        if not spell_to_remove or not isinstance(spell_to_remove, Spell):
            logger.error("Could not retrieve spell data from list item for removal.")
            QMessageBox.critical(self, "Error", "Could not retrieve spell data for removal.")
            return

        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the spell '{spell_to_remove.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result == QMessageBox.Yes:
            # Remove from the internal magic system object
            if spell_to_remove.id in self.magic_system.spells:
                del self.magic_system.spells[spell_to_remove.id]
                logger.info(f"Removed spell '{spell_to_remove.name}' (ID: {spell_to_remove.id}) from magic system '{self.magic_system.name}' (in dialog).")
            else:
                 logger.warning(f"Spell ID '{spell_to_remove.id}' not found in internal dictionary for removal.")

            # Remove from the list widget
            self.spells_list.takeItem(self.spells_list.row(item))

    def _add_race_affinity_to_list(self, race_name: str, affinity: RacialAffinity):
        """Add a race affinity to the list widget."""
        item_text = f"{race_name}: {affinity.affinity_level} Affinity ({affinity.learning_difficulty})"
        if affinity.natural_talent: item_text += " - Natural Talent"
        if affinity.bonus_effects: item_text += f" ({affinity.bonus_effects})" # Show bonus effects

        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, race_name) # Store race name as data
        item.setData(Qt.UserRole + 1, affinity) # Store affinity object as well
        self.races_list.addItem(item)
        self.races_list.sortItems(Qt.AscendingOrder) # Sort

    def _add_race_affinity(self):
        """Add a new race affinity."""
        race_name, ok = QInputDialog.getText(self, "Add Race Affinity", "Race name:")
        if ok and race_name:
            race_name = race_name.strip()
            if not race_name:
                QMessageBox.warning(self, "Invalid Name", "Race name cannot be empty.")
                return
            if race_name in self.magic_system.racial_affinities:
                QMessageBox.warning(self, "Duplicate Race", f"Race '{race_name}' already has an affinity defined.")
                return

            dialog = RacialAffinityDialog(self, race_name)
            if dialog.exec() == QDialog.Accepted:
                affinity = dialog.get_affinity()
                self.magic_system.racial_affinities[race_name] = affinity
                self._add_race_affinity_to_list(race_name, affinity)

    def _edit_race_affinity(self, item: Optional[QListWidgetItem]):
        """Edit a race affinity."""
        if not item:
            current_item = self.races_list.currentItem()
            if not current_item:
                 QMessageBox.information(self, "Edit Race Affinity", "Please select a race affinity to edit.")
                 return
            item = current_item

        race_name = item.data(Qt.UserRole)
        affinity = item.data(Qt.UserRole + 1)
        if not affinity: # Fallback
             if race_name in self.magic_system.racial_affinities:
                 affinity = self.magic_system.racial_affinities[race_name]
             else:
                 logger.warning(f"Affinity data mismatch for race '{race_name}' in list.")
                 QMessageBox.critical(self, "Error", f"Could not retrieve affinity data for race '{race_name}'.")
                 return

        import copy
        affinity_copy = copy.deepcopy(affinity)
        dialog = RacialAffinityDialog(self, race_name, affinity_copy)
        if dialog.exec() == QDialog.Accepted:
            updated_affinity = dialog.get_affinity()
            self.magic_system.racial_affinities[race_name] = updated_affinity
            row = self.races_list.row(item)
            self.races_list.takeItem(row)
            self._add_race_affinity_to_list(race_name, updated_affinity)
            # Try re-select
            items = self.races_list.findItems(race_name + ":", Qt.MatchStartsWith)
            if items: self.races_list.setCurrentItem(items[0])


    def _remove_race_affinity(self):
        """Remove a race affinity."""
        item = self.races_list.currentItem()
        if not item:
            QMessageBox.information(self, "Remove Race Affinity", "Please select a race affinity to remove.")
            return

        race_name = item.data(Qt.UserRole)
        result = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to remove the affinity for race '{race_name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if result == QMessageBox.Yes:
            if race_name in self.magic_system.racial_affinities:
                del self.magic_system.racial_affinities[race_name]
            self.races_list.takeItem(self.races_list.row(item))

    # --- Class Affinity Methods ---

    def _add_class_affinity_to_list(self, class_name: str, affinity: ClassAffinity):
        """Add a class affinity to the list widget."""
        item_text = f"{class_name}: {affinity.affinity_level} Affinity ({affinity.learning_difficulty})"
        req_stats = ", ".join([f"{k}={v}" for k, v in affinity.required_stats.items()])
        if req_stats: item_text += f" - Requires: {req_stats}"

        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, class_name) # Store class name as data
        item.setData(Qt.UserRole + 1, affinity) # Store affinity object
        self.classes_list.addItem(item)
        self.classes_list.sortItems(Qt.AscendingOrder) # Sort

    def _add_class_affinity(self):
        """Add a new class affinity."""
        class_name, ok = QInputDialog.getText(self, "Add Class Affinity", "Class name:")
        if ok and class_name:
            class_name = class_name.strip()
            if not class_name:
                QMessageBox.warning(self, "Invalid Name", "Class name cannot be empty.")
                return
            if class_name in self.magic_system.class_affinities:
                QMessageBox.warning(self, "Duplicate Class", f"Class '{class_name}' already has an affinity defined.")
                return

            dialog = ClassAffinityDialog(self, class_name)
            if dialog.exec() == QDialog.Accepted:
                affinity = dialog.get_affinity()
                self.magic_system.class_affinities[class_name] = affinity
                self._add_class_affinity_to_list(class_name, affinity)

    def _edit_class_affinity(self, item: Optional[QListWidgetItem]):
        """Edit a class affinity."""
        if not item:
            current_item = self.classes_list.currentItem()
            if not current_item:
                 QMessageBox.information(self, "Edit Class Affinity", "Please select a class affinity to edit.")
                 return
            item = current_item

        class_name = item.data(Qt.UserRole)
        affinity = item.data(Qt.UserRole + 1)
        if not affinity: # Fallback
            if class_name in self.magic_system.class_affinities:
                affinity = self.magic_system.class_affinities[class_name]
            else:
                logger.warning(f"Affinity data mismatch for class '{class_name}' in list.")
                QMessageBox.critical(self, "Error", f"Could not retrieve affinity data for class '{class_name}'.")
                return

        import copy
        affinity_copy = copy.deepcopy(affinity)
        dialog = ClassAffinityDialog(self, class_name, affinity_copy)
        if dialog.exec() == QDialog.Accepted:
            updated_affinity = dialog.get_affinity()
            self.magic_system.class_affinities[class_name] = updated_affinity
            row = self.classes_list.row(item)
            self.classes_list.takeItem(row)
            self._add_class_affinity_to_list(class_name, updated_affinity)
             # Try re-select
            items = self.classes_list.findItems(class_name + ":", Qt.MatchStartsWith)
            if items: self.classes_list.setCurrentItem(items[0])

    def _remove_class_affinity(self):
        """Remove a class affinity."""
        item = self.classes_list.currentItem()
        if not item:
             QMessageBox.information(self, "Remove Class Affinity", "Please select a class affinity to remove.")
             return

        class_name = item.data(Qt.UserRole)
        result = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to remove the affinity for class '{class_name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if result == QMessageBox.Yes:
            if class_name in self.magic_system.class_affinities:
                del self.magic_system.class_affinities[class_name]
            self.classes_list.takeItem(self.classes_list.row(item))

    def get_magic_system(self) -> MagicalSystem:
        """Get the edited magic system."""
        # Update basic info from the edits
        self.magic_system.name = self.name_edit.text()
        self.magic_system.description = self.desc_edit.toPlainText()
        self.magic_system.origin = self.origin_edit.toPlainText()
        self.magic_system.limitations = self.limitations_edit.toPlainText()
        self.magic_system.practitioners = self.practitioners_edit.toPlainText()
        self.magic_system.cultural_significance = self.cultural_edit.toPlainText()

        return self.magic_system


class MagicSystemsEditor(QWidget):
    """
    Magic systems editor component.
    """

    # Signals
    magic_system_modified = Signal()

    def __init__(self, parent=None):
        """
        Initialize the magic systems editor.

        Args:
            parent: The parent widget.
        """
        super().__init__(parent)

        # Internal state
        self.magic_system_manager = MagicSystemManager()
        self.current_system: Optional[MagicalSystem] = None

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the editor UI."""
        main_layout = QHBoxLayout(self)

        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel (magic system list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_label = QLabel("Magic Systems")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(list_label)

        self.system_list = QListWidget()
        self.system_list.setMinimumWidth(200)
        self.system_list.currentItemChanged.connect(self._on_system_selected)
        left_layout.addWidget(self.system_list)

        list_buttons = QHBoxLayout()

        self.add_system_btn = QPushButton("Add")
        self.add_system_btn.clicked.connect(self._add_system)
        list_buttons.addWidget(self.add_system_btn)

        self.edit_system_btn = QPushButton("Edit") # Added Edit button
        self.edit_system_btn.clicked.connect(self._edit_system)
        self.edit_system_btn.setEnabled(False)
        list_buttons.addWidget(self.edit_system_btn)

        self.remove_system_btn = QPushButton("Remove")
        self.remove_system_btn.clicked.connect(self._remove_system)
        self.remove_system_btn.setEnabled(False)
        list_buttons.addWidget(self.remove_system_btn)

        left_layout.addLayout(list_buttons)

        # Add left panel to splitter
        splitter.addWidget(left_panel)

        # Right panel (magic system details - simplified view)
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setFrameShape(QFrame.NoFrame)

        self.details_widget = QWidget()
        right_panel.setWidget(self.details_widget)

        self.details_layout = QVBoxLayout(self.details_widget)

        # Display fields (read-only in this view)
        self.details_form_layout = QFormLayout()

        self.name_label = QLabel()
        self.name_label.setWordWrap(True)
        self.details_form_layout.addRow("<b>Name:</b>", self.name_label)

        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.details_form_layout.addRow("<b>Description:</b>", self.desc_label)

        self.origin_label = QLabel()
        self.origin_label.setWordWrap(True)
        self.details_form_layout.addRow("<b>Origin:</b>", self.origin_label)

        self.limitations_label = QLabel()
        self.limitations_label.setWordWrap(True)
        self.details_form_layout.addRow("<b>Limitations:</b>", self.limitations_label)

        self.practitioners_label = QLabel()
        self.practitioners_label.setWordWrap(True)
        self.details_form_layout.addRow("<b>Practitioners:</b>", self.practitioners_label)

        self.cultural_label = QLabel()
        self.cultural_label.setWordWrap(True)
        self.details_form_layout.addRow("<b>Cultural Significance:</b>", self.cultural_label)

        self.details_layout.addLayout(self.details_form_layout)

        # Spells section (read-only list in this view)
        spells_label = QLabel("Spells")
        spells_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(spells_label)

        self.spells_list_display = QListWidget()
        self.spells_list_display.setMinimumHeight(150)
        self.spells_list_display.setEnabled(False) # Read-only display
        self.details_layout.addWidget(self.spells_list_display)

        # Affinities display (read-only)
        affinities_label = QLabel("Affinities")
        affinities_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.details_layout.addWidget(affinities_label)

        self.affinities_list_display = QListWidget()
        self.affinities_list_display.setMinimumHeight(150)
        self.affinities_list_display.setEnabled(False) # Read-only display
        self.details_layout.addWidget(self.affinities_list_display)


        self.details_layout.addStretch() # Push content up

        # Add right panel to splitter
        splitter.addWidget(right_panel)

        # Set up initial state
        self._disable_details_display()

        # Prioritize the details panel for resizing
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

    def set_magic_system_manager(self, manager: MagicSystemManager) -> None:
        """
        Set the magic system manager to use.

        Args:
            manager: The magic system manager.
        """
        self.magic_system_manager = manager
        self._refresh_system_list()

    def _refresh_system_list(self) -> None:
        """Refresh the magic system list from the manager."""
        current_id = None
        if self.system_list.currentItem():
            current_id = self.system_list.currentItem().data(Qt.UserRole)

        # Clear list
        self.system_list.clear()

        # Add all magic systems
        items_to_add = []
        for system_id, system in self.magic_system_manager.magic_systems.items():
            item = QListWidgetItem(system.name)
            item.setData(Qt.UserRole, system_id)
            items_to_add.append(item)

        # Sort alphabetically by name before adding
        items_to_add.sort(key=lambda x: x.text())
        for item in items_to_add:
            self.system_list.addItem(item)

        # Reselect previous item if possible
        new_selection = None
        if current_id:
            for i in range(self.system_list.count()):
                if self.system_list.item(i).data(Qt.UserRole) == current_id:
                    new_selection = self.system_list.item(i)
                    break

        if new_selection:
            self.system_list.setCurrentItem(new_selection)
        elif self.system_list.count() > 0:
            self.system_list.setCurrentRow(0)
        else:
             # No items left, disable details
            self._disable_details_display()
            self.edit_system_btn.setEnabled(False)
            self.remove_system_btn.setEnabled(False)


    def _on_system_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        """
        Handle magic system selection change.

        Args:
            current: The current selected item, or None.
            previous: The previously selected item, or None.
        """
        if current:
            system_id = current.data(Qt.UserRole)
            magic_system = self.magic_system_manager.get_magic_system(system_id)

            if magic_system:
                self._load_system_display(magic_system)
                self.edit_system_btn.setEnabled(True)
                self.remove_system_btn.setEnabled(True)
                return

        # No valid selection
        self._disable_details_display()
        self.edit_system_btn.setEnabled(False)
        self.remove_system_btn.setEnabled(False)

    def _load_system_display(self, magic_system: MagicalSystem) -> None:
        """
        Load a magic system into the read-only display area.

        Args:
            magic_system: The magic system to load.
        """
        try:
            self.current_system = magic_system # Keep track of the current system object

            # Set display labels
            self.name_label.setText(magic_system.name or "N/A")
            self.desc_label.setText(magic_system.description or "N/A")
            self.origin_label.setText(magic_system.origin or "N/A")
            self.limitations_label.setText(magic_system.limitations or "N/A")
            self.practitioners_label.setText(magic_system.practitioners or "N/A")
            self.cultural_label.setText(magic_system.cultural_significance or "N/A")

            # Load spells display
            self.spells_list_display.clear()
            for spell_id, spell in magic_system.spells.items():
                item_text = f"{spell.name}"
                if spell.level > 1:
                    item_text += f" (Level {spell.level})"
                self.spells_list_display.addItem(item_text)

            # Load affinities display
            self.affinities_list_display.clear()
            # Races
            for race_name, affinity in magic_system.racial_affinities.items():
                 item_text = f"Race - {race_name}: {affinity.affinity_level} ({affinity.learning_difficulty})"
                 if affinity.natural_talent: item_text += " [Natural Talent]"
                 if affinity.bonus_effects: item_text += f" ({affinity.bonus_effects})"
                 self.affinities_list_display.addItem(item_text)
            # Classes
            for class_name, affinity in magic_system.class_affinities.items():
                item_text = f"Class - {class_name}: {affinity.affinity_level} ({affinity.learning_difficulty})"
                req_stats = ", ".join([f"{k}={v}" for k, v in affinity.required_stats.items()])
                if req_stats: item_text += f" [Req: {req_stats}]"
                self.affinities_list_display.addItem(item_text)


            # Enable display area (conceptually, it's always visible)
            self.details_widget.setEnabled(True)

        except Exception as e:
            logger.error(f"Error loading display for magic system {magic_system.name}: {str(e)}")
            QMessageBox.warning(
                self,
                "Error Loading Magic System Display",
                f"There was an error displaying the magic system '{magic_system.name}':\n\n{str(e)}"
            )
            self._disable_details_display()

    def _disable_details_display(self) -> None:
        """Disable/clear the detail display controls."""
        self.current_system = None

        self.name_label.clear()
        self.desc_label.clear()
        self.origin_label.clear()
        self.limitations_label.clear()
        self.practitioners_label.clear()
        self.cultural_label.clear()

        self.spells_list_display.clear()
        self.affinities_list_display.clear()

        self.details_widget.setEnabled(False)


    def _add_system(self) -> None:
        """Add a new magic system using the dialog."""
        # Create a new blank system to pass to the dialog
        new_system = MagicalSystem.create_new("New Magic System", "")
        dialog = MagicSystemDialog(self, new_system) # Pass the new system

        if dialog.exec() == QDialog.Accepted:
            # Get the potentially modified system from the dialog
            magic_system = dialog.get_magic_system()

            # Ensure it has a unique ID if it's truly new
            if not magic_system.id:
                 magic_system.id = MagicalSystem.generate_id()

            # Add to manager
            self.magic_system_manager.add_magic_system(magic_system)

            # Refresh list
            self._refresh_system_list()

            # Find and select the new magic system
            for i in range(self.system_list.count()):
                item = self.system_list.item(i)
                if item.data(Qt.UserRole) == magic_system.id:
                    self.system_list.setCurrentItem(item)
                    break

            # Emit modified signal
            self.magic_system_modified.emit()

            # Log
            logger.info(f"Added new magic system: {magic_system.name} ({magic_system.id})")

    def _edit_system(self) -> None:
        """Edit the selected magic system using the dialog."""
        current_item = self.system_list.currentItem()
        if not current_item:
            return

        system_id = current_item.data(Qt.UserRole)
        magic_system = self.magic_system_manager.get_magic_system(system_id)

        if not magic_system:
            logger.error(f"Could not find magic system with ID {system_id} for editing.")
            return

        # Pass a deep copy to the dialog to avoid modifying the original if cancelled
        import copy
        system_copy = copy.deepcopy(magic_system)
        dialog = MagicSystemDialog(self, system_copy)

        if dialog.exec() == QDialog.Accepted:
            # Get the edited system from the dialog
            edited_system = dialog.get_magic_system()

            # Update the manager with the edited system (using the original ID)
            edited_system.id = system_id # Ensure ID remains the same
            self.magic_system_manager.add_magic_system(edited_system) # Overwrites existing

            # Refresh the list (might update name) and details display
            self._refresh_system_list() # This will re-select and trigger _load_system_display

            # Emit modified signal
            self.magic_system_modified.emit()

            # Log
            logger.info(f"Edited magic system: {edited_system.name} ({edited_system.id})")


    def _remove_system(self) -> None:
        """Remove the selected magic system."""
        current_item = self.system_list.currentItem()
        if not current_item:
            return

        system_id = current_item.data(Qt.UserRole)
        magic_system = self.magic_system_manager.get_magic_system(system_id)

        if not magic_system:
            logger.error(f"Could not find magic system with ID {system_id} for removal.")
            return

        # Confirm deletion
        result = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the magic system '{magic_system.name}'?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result != QMessageBox.Yes:
            return

        # Remove from manager
        removed = self.magic_system_manager.remove_magic_system(system_id)

        if removed:
            # Refresh list
            self._refresh_system_list() # Will select next/first or disable details

            # Emit modified signal
            self.magic_system_modified.emit()

            # Log
            logger.info(f"Removed magic system: {magic_system.name} ({system_id})")
        else:
             logger.error(f"Failed to remove magic system: {magic_system.name} ({system_id})")
             QMessageBox.critical(self, "Error", f"Could not remove magic system '{magic_system.name}'.")