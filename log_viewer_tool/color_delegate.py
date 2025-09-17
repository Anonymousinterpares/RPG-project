from typing import Dict
from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtGui import QColor, QBrush
from PySide6.QtCore import QModelIndex, Qt

from .settings_manager import SettingsManager

class ColorDelegate(QStyledItemDelegate):
    """
    Applies custom background colors to rows based on log level and logger name.
    """
    COLUMN_LOGGER = 1
    COLUMN_LEVEL = 2

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._level_colors: Dict[str, QColor] = {}
        self._logger_colors: Dict[str, QColor] = {}
        self._default_level_color: QColor = QColor(Qt.GlobalColor.transparent) # Default to transparent
        self.load_colors()

    def load_colors(self):
        """Loads color settings from the SettingsManager."""
        self._level_colors = self.settings_manager.get_log_level_colors()
        self._logger_colors = self.settings_manager.get_logger_name_colors()
        self._default_level_color = self.settings_manager.get_default_log_level_color()


    def paint(self, painter, option, index: QModelIndex):
        # Determine the background color for the entire row
        background_color = self.background_color_for_row(index)
        if background_color.isValid() and background_color != Qt.GlobalColor.transparent :
            painter.save()
            painter.fillRect(option.rect, background_color)
            painter.restore()
        
        # Let the base class handle the text and other painting
        super().paint(painter, option, index)

    def background_color_for_row(self, index: QModelIndex) -> QColor:
        """
        Determines the background color for the entire row based on logger name or log level.
        Logger name color takes precedence.
        """
        if not index.isValid():
            return QColor(Qt.GlobalColor.transparent)

        # Check logger name color first
        logger_name_index = index.sibling(index.row(), self.COLUMN_LOGGER)
        logger_name = logger_name_index.data(Qt.ItemDataRole.DisplayRole)
        if logger_name and logger_name in self._logger_colors:
            return self._logger_colors[logger_name]

        # Then check log level color
        level_index = index.sibling(index.row(), self.COLUMN_LEVEL)
        level_str = level_index.data(Qt.ItemDataRole.DisplayRole)
        if level_str and level_str in self._level_colors:
            return self._level_colors[level_str]
        
        # Fallback to default if level is unknown but a default is set
        if level_str and self._default_level_color.isValid() and level_str not in self._level_colors:
            return self._default_level_color

        return QColor(Qt.GlobalColor.transparent) # Default transparent if no match