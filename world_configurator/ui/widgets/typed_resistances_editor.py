# world_configurator/ui/widgets/typed_resistances_editor.py
"""
TypedResistancesEditor: A structured editor widget for item custom_properties typed resistances.

- Percent mode: one numeric spin box per allowed combat damage type.
- Dice mode: one dice notation input per type (NdS±M), with optional tier quick-pick.
- get_values() returns non-zero percent entries.
- get_dice_values() returns non-empty valid dice entries.
- set_values()/set_dice_values() populate from existing dicts.

Usage:
    editor = TypedResistancesEditor(effect_types=["slashing", "fire", ...])
    editor.set_values({"fire": 25, "cold": -10})
    editor.set_dice_values({"fire": "1d6"})
    pct = editor.get_values()          # {"fire": 25, "cold": -10}
    dice = editor.get_dice_values()    # {"fire": "1d6"}
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QVBoxLayout, QLineEdit, QComboBox
)


class TypedResistancesEditor(QWidget):
    """
    A QWidget that renders per-damage-type resistance inputs (percent and dice).

    Args:
        effect_types: Allowed damage types (e.g., from config/combat/combat_config.json damage.types)
        parent: Optional parent widget
        dice_tiers: Optional mapping of tier name -> dice notation (e.g., {"minor": "1d4", "medium": "1d6", ...})
    """

    def __init__(self, effect_types: Optional[List[str]] = None, parent: Optional[QWidget] = None, dice_tiers: Optional[Dict[str, str]] = None):
        super().__init__(parent)
        self._effect_types: List[str] = [str(t).strip().lower() for t in (effect_types or []) if isinstance(t, str)]
        # Map damage_type -> QSpinBox (percent)
        self._spins: Dict[str, QSpinBox] = {}
        # Map damage_type -> QLineEdit (dice)
        self._dice_edits: Dict[str, QLineEdit] = {}
        # Map damage_type -> QComboBox (tier quick-pick)
        self._tier_boxes: Dict[str, QComboBox] = {}
        # Tier mapping
        self._dice_tiers = {k: v for k, v in ((dice_tiers or {
            "minor": "1d4",
            "medium": "1d6",
            "major": "1d8",
            "supreme": "1d10",
        }).items())}
        # Dice regex
        self._dice_re = re.compile(r"^\d+d\d+(?:[+-]\d+)?$")

        self._build_ui()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)

        for dmg_type in self._effect_types:
            row = QHBoxLayout()

            label = QLabel(dmg_type)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Percent spin
            spin = QSpinBox()
            spin.setRange(-100, 100)
            spin.setSingleStep(5)
            spin.setSuffix(" %")
            spin.setValue(0)
            spin.setToolTip("Percentage resistance modifier. Negative means vulnerability.")
            self._spins[dmg_type] = spin

            # Dice editor
            dice_edit = QLineEdit()
            dice_edit.setPlaceholderText("e.g., 1d6")
            dice_edit.setToolTip("Dice-based mitigation rolled per hit (NdS±M).")
            self._dice_edits[dmg_type] = dice_edit

            # Tier pick
            tier = QComboBox()
            tier.addItem("", "")
            for k in ["minor","medium","major","supreme"]:
                if k in self._dice_tiers:
                    tier.addItem(k.title(), k)
            tier.setToolTip("Quick-pick a dice tier (fills dice field).")
            def _bind_tier(box: QComboBox, edit: QLineEdit):
                def _on_change(_idx: int):
                    key = box.currentData()
                    if key:
                        edit.setText(self._dice_tiers.get(key, ""))
                return _on_change
            tier.currentIndexChanged.connect(_bind_tier(tier, dice_edit))
            self._tier_boxes[dmg_type] = tier

            # Layout: label | percent | dice | tier
            row.addWidget(label)
            row.addWidget(spin, 1)
            row.addWidget(dice_edit, 1)
            row.addWidget(tier)

            container = QWidget()
            container.setLayout(row)
            form.addRow(container)

        outer_layout.addLayout(form)

        # Controls
        controls = QHBoxLayout()
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setToolTip("Reset all typed resistances to 0% and empty dice (removes them on save).")
        self.clear_btn.clicked.connect(self.clear_all)
        controls.addStretch(1)
        controls.addWidget(self.clear_btn)
        outer_layout.addLayout(controls)

    # Percent API
    def set_values(self, values: Optional[Dict[str, int]]) -> None:
        """
        Populate percent inputs from {damage_type: percent}. Missing types default to 0.
        """
        vals = values or {}
        for dmg_type, spin in self._spins.items():
            try:
                v = int(vals.get(dmg_type, 0))
            except Exception:
                v = 0
            v = max(-100, min(100, v))
            spin.setValue(v)

    def get_values(self) -> Dict[str, int]:
        """Return only non-zero percent values as {damage_type: percent}."""
        out: Dict[str, int] = {}
        for dmg_type, spin in self._spins.items():
            v = int(spin.value())
            if v != 0:
                out[dmg_type] = v
        return out

    # Dice API
    def set_dice_values(self, values: Optional[Dict[str, str]]) -> None:
        vals = values or {}
        for dmg_type, edit in self._dice_edits.items():
            s = str(vals.get(dmg_type, "") or "").strip()
            edit.setText(s)
            # Best-effort set tier combobox selection if matches mapping
            try:
                matched_key = None
                for k, dn in self._dice_tiers.items():
                    if s and s.lower() == str(dn).lower():
                        matched_key = k
                        break
                box = self._tier_boxes.get(dmg_type)
                if box is not None:
                    # find index by data
                    idx = 0
                    if matched_key:
                        for i in range(box.count()):
                            if box.itemData(i) == matched_key:
                                idx = i; break
                    box.setCurrentIndex(idx)
            except Exception:
                pass

    def get_dice_values(self) -> Dict[str, str]:
        """Return only non-empty, valid dice values as {damage_type: dice}."""
        out: Dict[str, str] = {}
        for dmg_type, edit in self._dice_edits.items():
            s = str(edit.text() or "").strip()
            if s and self._dice_re.match(s):
                out[dmg_type] = s
        return out

    def clear_all(self) -> None:
        """Reset all spinboxes to 0 and dice edits to empty."""
        for spin in self._spins.values():
            spin.setValue(0)
        for edit in self._dice_edits.values():
            edit.clear()
        for box in self._tier_boxes.values():
            box.setCurrentIndex(0)
