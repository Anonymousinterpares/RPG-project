#!/usr/bin/env python3
"""
Dialog showing details of a spell from the catalog.
Non-modal; caller should manage singleton behavior.
"""
from __future__ import annotations

from typing import Any, Optional

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit
from PySide6.QtCore import Qt

from core.utils.logging_config import get_logger

logger = get_logger("SPELL_DETAILS")


class SpellDetailsDialog(QDialog):
    def __init__(self, spell_obj: Any, parent: Optional[object] = None):
        super().__init__(parent)
        self.setWindowTitle(getattr(spell_obj, 'name', getattr(spell_obj, 'id', 'Spell')))
        self.setModal(False)
        self.resize(420, 480)

        layout = QVBoxLayout(self)
        name = getattr(spell_obj, 'name', getattr(spell_obj, 'id', 'Spell'))
        system_id = getattr(spell_obj, 'system_id', 'Unknown System')
        role = getattr(spell_obj, 'combat_role', 'offensive')
        header = QLabel(f"<b>{name}</b><br><i>System:</i> {system_id} &nbsp; <i>Role:</i> {role}")
        header.setTextFormat(Qt.RichText)
        layout.addWidget(header)

        details = QTextEdit()
        details.setReadOnly(True)
        details.setMinimumHeight(360)
        details.setStyleSheet("QTextEdit { background-color: #2D2D30; color: #E0E0E0; border: 1px solid #555; border-radius: 4px; padding: 6px; }")

        # Build formatted details
        txt_lines = []
        data = getattr(spell_obj, 'data', {}) or {}
        if data:
            for k in ("mana_cost", "cost", "casting_time", "cast_time", "range", "target", "tags"):
                if k in data:
                    txt_lines.append(f"{k}: {data[k]}")
        atoms = getattr(spell_obj, 'effect_atoms', []) or []
        if atoms:
            txt_lines.append("\nEffects:")
            for i, a in enumerate(atoms, 1):
                try:
                    at = a.get('type', 'effect')
                    sel = a.get('selector')
                    mag = a.get('magnitude')
                    dt = a.get('damage_type') or a.get('status_type')
                    dur = a.get('duration')
                    line = f"  {i}. type={at}"
                    if sel: line += f", selector={sel}"
                    if mag is not None: line += f", magnitude={mag}"
                    if dt: line += f", typed={dt}"
                    if dur: line += f", duration={dur}"
                    txt_lines.append(line)
                except Exception:
                    txt_lines.append(f"  {i}. {a}")
        else:
            txt_lines.append("(No structured effect atoms)")

        details.setPlainText("\n".join(txt_lines))
        layout.addWidget(details)
