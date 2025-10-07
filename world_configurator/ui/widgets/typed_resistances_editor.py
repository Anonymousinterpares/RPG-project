# world_configurator/ui/widgets/typed_resistances_editor.py
"""
TypedResistancesEditor: A structured editor widget for item custom_properties.typed_resistances.

- Presents one numeric spin box per allowed combat damage type.
- Values are integer percentages in range [-100, 100].
- get_values() returns only non-zero entries to keep JSON compact.
- set_values() populates from an existing dict.

Usage:
    editor = TypedResistancesEditor(effect_types=["slashing", "fire", ...])
    editor.set_values({"fire": 25, "cold": -10})
    values = editor.get_values()  # {"fire": 25, "cold": -10}
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QVBoxLayout
)


class TypedResistancesEditor(QWidget):
    """
    A QWidget that renders per-damage-type resistance percentage inputs.

    Args:
        effect_types: Allowed damage types (e.g., from config/combat/combat_config.json damage.types)
        parent: Optional parent widget
    """

    def __init__(self, effect_types: Optional[List[str]] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._effect_types: List[str] = [str(t).strip().lower() for t in (effect_types or []) if isinstance(t, str)]
        # Map damage_type -> QSpinBox
        self._spins: Dict[str, QSpinBox] = {}

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

            spin = QSpinBox()
            spin.setRange(-100, 100)
            spin.setSingleStep(5)
            spin.setSuffix(" %")
            spin.setValue(0)
            spin.setToolTip("Percentage resistance modifier. Negative means vulnerability.")
            self._spins[dmg_type] = spin

            row.addWidget(label)
            row.addWidget(spin, 1)
            container = QWidget()
            container.setLayout(row)
            form.addRow(container)

        outer_layout.addLayout(form)

        # Controls
        controls = QHBoxLayout()
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setToolTip("Reset all typed resistances to 0% (removes them on save).")
        self.clear_btn.clicked.connect(self.clear_all)
        controls.addStretch(1)
        controls.addWidget(self.clear_btn)
        outer_layout.addLayout(controls)

    # Public API
    def set_values(self, values: Optional[Dict[str, int]]) -> None:
        """
        Populate the inputs from a dict of {damage_type: percent}.
        Missing types default to 0. Extra keys are ignored.
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
        """
        Return only non-zero values as {damage_type: percent}.
        """
        out: Dict[str, int] = {}
        for dmg_type, spin in self._spins.items():
            v = int(spin.value())
            if v != 0:
                out[dmg_type] = v
        return out

    def clear_all(self) -> None:
        """Reset all spinboxes to 0 (no entries will be saved)."""
        for spin in self._spins.values():
            spin.setValue(0)
