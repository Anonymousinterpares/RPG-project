from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget, QListWidgetItem,
    QPushButton, QCheckBox, QLineEdit, QLabel, QFileDialog, QButtonGroup, QRadioButton
)
from PySide6.QtCore import Qt
from typing import Any, List, Set, Tuple, Dict
import logging

logger = logging.getLogger("LogViewerTool.ExportDialog")

class ExportDialog(QDialog):
    """
    Dialog for configuring log export options.
    """
    def __init__(self, unique_loggers: Set[str], unique_levels: Set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Logs")
        self.setMinimumWidth(400)

        self.unique_loggers = sorted(list(unique_loggers))
        self.unique_levels = sorted(list(unique_levels))

        self._selected_loggers: Set[str] = set(self.unique_loggers) # Default to all selected
        self._selected_levels: Set[str] = set(self.unique_levels)   # Default to all selected
        self._export_format: str = ".log" # Default

        main_layout = QVBoxLayout(self)

        # --- Logger Name Filters ---
        logger_group = QGroupBox("Include Logger Names:")
        logger_layout = QVBoxLayout(logger_group)
        
        self.logger_filter_edit = QLineEdit()
        self.logger_filter_edit.setPlaceholderText("Filter logger names...")
        self.logger_filter_edit.textChanged.connect(self._filter_logger_list)
        logger_layout.addWidget(self.logger_filter_edit)

        self.logger_list_widget = QListWidget()
        self.logger_list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._populate_list_widget(self.logger_list_widget, self.unique_loggers, self._selected_loggers)
        logger_layout.addWidget(self.logger_list_widget)
        
        logger_select_all_button = QPushButton("Select All Loggers")
        logger_select_all_button.clicked.connect(lambda: self._toggle_all_list_widget(self.logger_list_widget, self.unique_loggers, self._selected_loggers, True))
        logger_deselect_all_button = QPushButton("Deselect All Loggers")
        logger_deselect_all_button.clicked.connect(lambda: self._toggle_all_list_widget(self.logger_list_widget, self.unique_loggers, self._selected_loggers, False))
        
        logger_button_layout = QHBoxLayout()
        logger_button_layout.addWidget(logger_select_all_button)
        logger_button_layout.addWidget(logger_deselect_all_button)
        logger_layout.addLayout(logger_button_layout)
        
        main_layout.addWidget(logger_group)

        # --- Log Level Filters ---
        level_group = QGroupBox("Include Log Levels:")
        level_layout = QVBoxLayout(level_group)

        self.level_filter_edit = QLineEdit()
        self.level_filter_edit.setPlaceholderText("Filter log levels...")
        self.level_filter_edit.textChanged.connect(self._filter_level_list)
        level_layout.addWidget(self.level_filter_edit)

        self.level_list_widget = QListWidget()
        self.level_list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._populate_list_widget(self.level_list_widget, self.unique_levels, self._selected_levels)
        level_layout.addWidget(self.level_list_widget)

        level_select_all_button = QPushButton("Select All Levels")
        level_select_all_button.clicked.connect(lambda: self._toggle_all_list_widget(self.level_list_widget, self.unique_levels, self._selected_levels, True))
        level_deselect_all_button = QPushButton("Deselect All Levels")
        level_deselect_all_button.clicked.connect(lambda: self._toggle_all_list_widget(self.level_list_widget, self.unique_levels, self._selected_levels, False))

        level_button_layout = QHBoxLayout()
        level_button_layout.addWidget(level_select_all_button)
        level_button_layout.addWidget(level_deselect_all_button)
        level_layout.addLayout(level_button_layout)

        main_layout.addWidget(level_group)

        # --- Export Format ---
        format_group = QGroupBox("Export Format:")
        format_layout = QHBoxLayout(format_group)
        self.format_button_group = QButtonGroup(self)
        
        self.radio_log = QRadioButton(".log")
        self.radio_log.setChecked(True)
        self.radio_log.toggled.connect(lambda checked: self._set_export_format(".log") if checked else None)
        self.format_button_group.addButton(self.radio_log)
        format_layout.addWidget(self.radio_log)

        self.radio_txt = QRadioButton(".txt")
        self.radio_txt.toggled.connect(lambda checked: self._set_export_format(".txt") if checked else None)
        self.format_button_group.addButton(self.radio_txt)
        format_layout.addWidget(self.radio_txt)
        
        format_layout.addStretch()
        main_layout.addWidget(format_group)

        # --- Dialog Buttons ---
        button_box_layout = QHBoxLayout()
        export_button = QPushButton("Export")
        export_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_box_layout.addStretch()
        button_box_layout.addWidget(export_button)
        button_box_layout.addWidget(cancel_button)
        main_layout.addLayout(button_box_layout)

    def _populate_list_widget(self, list_widget: QListWidget, items: List[str], selected_items: Set[str]):
        list_widget.clear()
        for item_text in items:
            list_item = QListWidgetItem(item_text)
            list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            list_item.setCheckState(Qt.CheckState.Checked if item_text in selected_items else Qt.CheckState.Unchecked)
            list_item.setData(Qt.ItemDataRole.UserRole, item_text) # Store the original text
            list_widget.addItem(list_item)
        list_widget.itemChanged.connect(lambda item, lw=list_widget, sel_set=selected_items: self._update_selection_set(item, lw, sel_set))


    def _update_selection_set(self, item: QListWidgetItem, list_widget: QListWidget, selection_set: Set[str]):
        item_text = item.data(Qt.ItemDataRole.UserRole) # Get original text
        if item.checkState() == Qt.CheckState.Checked:
            selection_set.add(item_text)
        else:
            selection_set.discard(item_text)

    def _filter_list_widget(self, text: str, list_widget: QListWidget, all_items: List[str], selected_items: Set[str]):
        list_widget.clear()
        filter_text_lower = text.lower()
        for item_text in all_items:
            if filter_text_lower in item_text.lower():
                list_item = QListWidgetItem(item_text)
                list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                list_item.setCheckState(Qt.CheckState.Checked if item_text in selected_items else Qt.CheckState.Unchecked)
                list_item.setData(Qt.ItemDataRole.UserRole, item_text)
                list_widget.addItem(list_item)
    
    def _filter_logger_list(self, text: str):
        self._filter_list_widget(text, self.logger_list_widget, self.unique_loggers, self._selected_loggers)

    def _filter_level_list(self, text: str):
        self._filter_list_widget(text, self.level_list_widget, self.unique_levels, self._selected_levels)

    def _toggle_all_list_widget(self, list_widget: QListWidget, all_items_set: Set[str], selection_set: Set[str], select: bool):
        if select:
            selection_set.update(all_items_set)
        else:
            selection_set.clear()
        
        # Repopulate/recheck items based on current filter text
        filter_text = ""
        if list_widget == self.logger_list_widget:
            filter_text = self.logger_filter_edit.text()
            self._filter_logger_list(filter_text)
        elif list_widget == self.level_list_widget:
            filter_text = self.level_filter_edit.text()
            self._filter_level_list(filter_text)


    def _set_export_format(self, fmt: str):
        self._export_format = fmt

    def get_export_options(self) -> Dict[str, Any]:
        return {
            "loggers": self._selected_loggers.copy(), # Return a copy
            "levels": self._selected_levels.copy(),   # Return a copy
            "format": self._export_format
        }