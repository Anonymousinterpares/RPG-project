from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QColorDialog, QHeaderView, QAbstractItemView,
    QGroupBox
)
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtCore import Qt, Signal
from typing import Dict, Optional, Set

from core.utils.logging_config import get_logger


from .settings_manager import SettingsManager

logger = get_logger("LogViewerTool.ColorSettings")

class ColorSettingsDialog(QDialog):
    """
    Dialog for managing color settings for log levels and logger names.
    """
    settings_changed = Signal()

    def __init__(self, settings_manager: SettingsManager, unique_loggers: Set[str], unique_levels: Set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Color Settings")
        self.settings_manager = settings_manager
        self.unique_loggers = sorted(list(unique_loggers))
        self.unique_levels = sorted(list(unique_levels))

        self._level_colors: Dict[str, QColor] = {}
        self._logger_colors: Dict[str, QColor] = {}
        
        self._load_initial_colors()
        self._setup_ui()
        self.setMinimumSize(600, 400)


    def _load_initial_colors(self):
        """Load colors from settings manager into local dicts."""
        self._level_colors = self.settings_manager.get_log_level_colors()
        self._logger_colors = self.settings_manager.get_logger_name_colors()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Log Level Colors ---
        level_group = QGroupBox("Log Level Colors")
        level_layout = QVBoxLayout(level_group)
        
        self.level_table = QTableWidget(len(self.unique_levels) + 1, 2) # Name, Color + Default
        self.level_table.setHorizontalHeaderLabels(["Log Level", "Color"])
        self.level_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.level_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.level_table.setColumnWidth(1, 100)
        self.level_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.level_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Populate level table
        for i, level in enumerate(self.unique_levels):
            self.level_table.setItem(i, 0, QTableWidgetItem(level))
            color_button = QPushButton("Change")
            color_button.clicked.connect(lambda checked=False, l=level: self._pick_color_for_level(l))
            self.level_table.setCellWidget(i, 1, color_button)
            self._update_table_row_color(self.level_table, i, self._level_colors.get(level))

        # Add "DEFAULT" for unknown levels
        default_row_idx = len(self.unique_levels)
        self.level_table.setItem(default_row_idx, 0, QTableWidgetItem("DEFAULT (Unknown Levels)"))
        default_color_button = QPushButton("Change")
        default_color_button.clicked.connect(lambda checked=False: self._pick_color_for_level("DEFAULT"))
        self.level_table.setCellWidget(default_row_idx, 1, default_color_button)
        self._update_table_row_color(self.level_table, default_row_idx, self._level_colors.get("DEFAULT"))


        level_layout.addWidget(self.level_table)
        reset_levels_button = QPushButton("Reset Level Colors to Default")
        reset_levels_button.clicked.connect(self._reset_level_colors)
        level_layout.addWidget(reset_levels_button)
        main_layout.addWidget(level_group)

        # --- Logger Name Colors ---
        logger_group = QGroupBox("Logger Name Colors (Overrides Level Colors)")
        logger_layout = QVBoxLayout(logger_group)

        self.logger_table = QTableWidget(len(self.unique_loggers), 2) # Name, Color
        self.logger_table.setHorizontalHeaderLabels(["Logger Name", "Color"])
        self.logger_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.logger_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.logger_table.setColumnWidth(1, 100)
        self.logger_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.logger_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Populate logger table
        for i, logger_name in enumerate(self.unique_loggers):
            self.logger_table.setItem(i, 0, QTableWidgetItem(logger_name))
            color_button = QPushButton("Change")
            color_button.clicked.connect(lambda checked=False, ln=logger_name: self._pick_color_for_logger(ln))
            self.logger_table.setCellWidget(i, 1, color_button)
            self._update_table_row_color(self.logger_table, i, self._logger_colors.get(logger_name))
        
        logger_layout.addWidget(self.logger_table)
        reset_loggers_button = QPushButton("Clear All Logger Name Colors")
        reset_loggers_button.clicked.connect(self._reset_logger_colors)
        logger_layout.addWidget(reset_loggers_button)
        main_layout.addWidget(logger_group)

        # --- Dialog Buttons ---
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply_changes)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept) # accept will also trigger save via DialogButtonBox
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(apply_button)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

    def _update_table_row_color(self, table: QTableWidget, row: int, color: Optional[QColor]):
        """Updates the background color swatch for a table row."""
        item = table.item(row, 0) # Get the item in the first column (name)
        if item:
            if color and color.isValid():
                # Create a small pixmap with the color for visual feedback next to button
                pixmap = QPixmap(16, 16)
                pixmap.fill(color)
                item.setIcon(QIcon(pixmap))
                # Set text color for readability against potential dark backgrounds
                # item.setForeground(QColor("black") if color.lightness() > 127 else QColor("white"))
            else:
                item.setIcon(QIcon()) # Clear icon if no color
                # item.setForeground(QApplication.palette().color(QPalette.WindowText)) # Reset to default text color

    def _pick_color_for_level(self, level: str):
        current_color = self._level_colors.get(level, QColor(Qt.GlobalColor.white))
        color = QColorDialog.getColor(current_color, self, f"Select Color for {level}")
        if color.isValid():
            self._level_colors[level] = color
            if level == "DEFAULT":
                row_idx = self.level_table.rowCount() -1
            else:
                try:
                    row_idx = self.unique_levels.index(level)
                except ValueError:
                    logger.error(f"Level {level} not found in unique_levels during color pick.")
                    return
            self._update_table_row_color(self.level_table, row_idx, color)

    def _pick_color_for_logger(self, logger_name: str):
        current_color = self._logger_colors.get(logger_name, QColor(Qt.GlobalColor.white)) # Default to white if not set
        color = QColorDialog.getColor(current_color, self, f"Select Color for Logger: {logger_name}")
        if color.isValid():
            self._logger_colors[logger_name] = color
            try:
                row_idx = self.unique_loggers.index(logger_name)
                self._update_table_row_color(self.logger_table, row_idx, color)
            except ValueError:
                logger.error(f"Logger name {logger_name} not found in unique_loggers list.")
        elif not color.isValid() and logger_name in self._logger_colors: # User cancelled, reset if color was set
             self._logger_colors.pop(logger_name) # Remove to use level color
             row_idx = self.unique_loggers.index(logger_name)
             self._update_table_row_color(self.logger_table, row_idx, None)


    def _reset_level_colors(self):
        self._level_colors = self.settings_manager.DEFAULT_LOG_LEVEL_COLORS.copy()
        # Convert hex strings to QColor for internal use
        self._level_colors = {k: QColor(v) for k,v in self._level_colors.items()}
        for i, level in enumerate(self.unique_levels):
            self._update_table_row_color(self.level_table, i, self._level_colors.get(level))
        # Update default row as well
        self._update_table_row_color(self.level_table, len(self.unique_levels), self._level_colors.get("DEFAULT"))


    def _reset_logger_colors(self):
        self._logger_colors.clear()
        for i in range(self.logger_table.rowCount()):
            self._update_table_row_color(self.logger_table, i, None) # None will clear the color swatch


    def _apply_changes(self):
        """Saves the current color selections to settings and emits signal."""
        self.settings_manager.set_log_level_colors(self._level_colors)
        self.settings_manager.set_logger_name_colors(self._logger_colors)
        self.settings_changed.emit()
        logger.info("Color settings applied and saved.")

    def accept(self):
        self._apply_changes()
        super().accept()

    def get_level_colors(self) -> Dict[str, QColor]:
        return self._level_colors.copy()

    def get_logger_colors(self) -> Dict[str, QColor]:
        return self._logger_colors.copy()