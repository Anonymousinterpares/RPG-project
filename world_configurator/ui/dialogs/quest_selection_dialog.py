"""
Quest selection dialog for choosing existing quest IDs from QuestManager.
"""
from __future__ import annotations

from typing import List, Tuple, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox
)


class QuestSelectionDialog(QDialog):
    """Dialog to select one or more existing quest IDs.

    Args:
        parent: Parent widget.
        available_quests: A list of tuples (quest_id, title) to choose from.
        existing_ids: The list of quest IDs currently selected (to pre-check).
    """

    def __init__(self, parent=None, available_quests: Optional[List[Tuple[str, str]]] = None, existing_ids: Optional[List[str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Initial Quests")
        self.setMinimumWidth(420)
        self.available_quests = available_quests or []
        self.existing_ids = set(existing_ids or [])

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Type to filter by ID or title…")
        self.filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_edit)
        layout.addLayout(filter_row)

        # Quest list (checkable)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.list_widget)

        # Populate items
        for qid, title in sorted(self.available_quests, key=lambda x: (x[1].lower(), x[0].lower())):
            text = f"{title} ({qid})" if title else qid
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, qid)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if qid in self.existing_ids else Qt.Unchecked)
            self.list_widget.addItem(item)

        # Quick actions
        actions = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_all)
        actions.addWidget(select_all_btn)
        actions.addWidget(clear_btn)
        actions.addStretch()
        layout.addLayout(actions)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_filter(self) -> None:
        term = (self.filter_edit.text() or "").strip().lower()
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            visible = term in it.text().lower()
            it.setHidden(not visible)

    def _select_all(self) -> None:
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if not it.isHidden():
                it.setCheckState(Qt.Checked)

    def _clear_all(self) -> None:
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if not it.isHidden():
                it.setCheckState(Qt.Unchecked)

    def get_selected_ids(self) -> List[str]:
        selected: List[str] = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.checkState() == Qt.Checked:
                qid = it.data(Qt.UserRole)
                if isinstance(qid, str):
                    selected.append(qid)
        return selected

