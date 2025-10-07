# world_configurator/ui/widgets/multiselect_combo.py
"""
MultiSelectCombo: A QComboBox that supports multi-select via checkable items.

API:
- set_options(list[str])
- set_selected(list[str])
- get_selected() -> list[str]
- clear_selection()

Shows a comma-separated summary of selected items as the display text.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QComboBox


class MultiSelectCombo(QComboBox):
    selectionChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)  # to show joined text
        self.lineEdit().setReadOnly(True)
        self._model = QStandardItemModel(self)
        self.setModel(self._model)
        # Prevent popup closing on single click
        self.view().pressed.connect(self._on_index_pressed)
        self._options: List[str] = []

    def set_options(self, options: List[str]) -> None:
        self._options = [str(o).strip() for o in options if isinstance(o, str) and o.strip()]
        self._model.clear()
        for opt in self._options:
            item = QStandardItem(opt)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setData(Qt.Unchecked, Qt.CheckStateRole)
            self._model.appendRow(item)
        self._refresh_text()

    def set_selected(self, values: Optional[List[str]]) -> None:
        vals = {str(v).strip() for v in (values or [])}
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if not item: continue
            state = Qt.Checked if item.text() in vals else Qt.Unchecked
            item.setData(state, Qt.CheckStateRole)
        self._refresh_text()
        self.selectionChanged.emit(self.get_selected())

    def get_selected(self) -> List[str]:
        out: List[str] = []
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item and item.checkState() == Qt.Checked:
                out.append(item.text())
        return out

    def clear_selection(self) -> None:
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item:
                item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self._refresh_text()
        self.selectionChanged.emit([])

    def _on_index_pressed(self, index) -> None:
        item = self._model.itemFromIndex(index)
        if not item:
            return
        # Toggle check state
        new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
        item.setData(new_state, Qt.CheckStateRole)
        self._refresh_text()
        # Keep popup open for multi-select
        self.showPopup()
        self.selectionChanged.emit(self.get_selected())

    def _refresh_text(self) -> None:
        selected = self.get_selected()
        self.lineEdit().setText(
            ", ".join(selected) if selected else ""
        )
