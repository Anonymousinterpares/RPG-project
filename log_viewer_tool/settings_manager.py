from PySide6.QtCore import QSettings, QSize, QPoint, QByteArray
from PySide6.QtGui import QColor
from typing import Dict, Any, Optional, List, Set, Tuple
import json
import logging

logger = logging.getLogger("LogViewerTool.Settings")

class SettingsManager:
    """
    Manages saving and loading application settings using QSettings.
    """
    ORGANIZATION_NAME = "RPGGameTools"
    APPLICATION_NAME = "LogViewer"

    # Keys for settings
    LAST_LOG_FOLDER = "paths/last_log_folder"
    WINDOW_GEOMETRY = "window/geometry"
    WINDOW_STATE = "window/state"
    FILTERS_TEXT = "filters/text" # Stores a dict: {column_index: text}
    FILTERS_CHECKBOX_LOGGER = "filters/checkbox_logger" # Stores a list of checked logger names
    FILTERS_CHECKBOX_LEVEL = "filters/checkbox_level"   # Stores a list of checked log levels
    FILTER_CASE_SENSITIVE = "filters/case_sensitive"
    SORT_COLUMN = "sort/column"
    SORT_ORDER = "sort/order" # Qt.SortOrder enum value (0 or 1)
    LOG_LEVEL_COLORS = "colors/log_levels" # Stores a dict: {level_str: hex_color_str}
    LOGGER_NAME_COLORS = "colors/logger_names" # Stores a dict: {logger_name_str: hex_color_str}
    COLUMN_WIDTHS = "table/column_widths" # Stores a list of integers

    DEFAULT_LOG_LEVEL_COLORS = {
        "DEBUG": "#A9A9A9",    # DarkGray
        "INFO": "#00BFFF",     # DeepSkyBlue
        "WARNING": "#FFD700",  # Gold
        "ERROR": "#FF4500",    # OrangeRed
        "CRITICAL": "#DC143C", # Crimson
        "MIGRATION": "#9370DB", # MediumPurple
        "DEFAULT": "#E0E0E0"   # LightGray for unknown levels
    }
    # Default logger name colors can be empty, user adds them.

    def __init__(self):
        self.settings = QSettings(self.ORGANIZATION_NAME, self.APPLICATION_NAME)
        logger.info(f"Settings file location: {self.settings.fileName()}")

    def save_setting(self, key: str, value: Any):
        self.settings.setValue(key, value)
        self.settings.sync() # Ensure data is written to disk

    def load_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.value(key, default)

    # Specific getters/setters
    def get_last_log_folder(self, default_path: str = ".") -> str:
        return str(self.load_setting(self.LAST_LOG_FOLDER, default_path))

    def set_last_log_folder(self, folder_path: str):
        self.save_setting(self.LAST_LOG_FOLDER, folder_path)

    def get_window_geometry(self) -> Optional[QByteArray]:
        return self.load_setting(self.WINDOW_GEOMETRY)

    def set_window_geometry(self, geometry: QByteArray):
        self.save_setting(self.WINDOW_GEOMETRY, geometry)

    def get_window_state(self) -> Optional[QByteArray]:
        return self.load_setting(self.WINDOW_STATE)

    def set_window_state(self, state: QByteArray):
        self.save_setting(self.WINDOW_STATE, state)

    def get_text_filters(self) -> Dict[int, str]:

        variant_map = self.load_setting(self.FILTERS_TEXT, {})
        if isinstance(variant_map, dict): # If it was stored correctly by python
            return {int(k): str(v) for k, v in variant_map.items()} # Ensure keys are int, values str
        return {}


    def set_text_filters(self, filters: Dict[int, str]):
        self.save_setting(self.FILTERS_TEXT, filters)

    def get_checkbox_logger_filters(self) -> List[str]:
        return self.load_setting(self.FILTERS_CHECKBOX_LOGGER, [])

    def set_checkbox_logger_filters(self, filters: List[str]):
        self.save_setting(self.FILTERS_CHECKBOX_LOGGER, filters)

    def get_checkbox_level_filters(self) -> List[str]:
        return self.load_setting(self.FILTERS_CHECKBOX_LEVEL, [])

    def set_checkbox_level_filters(self, filters: List[str]):
        self.save_setting(self.FILTERS_CHECKBOX_LEVEL, filters)

    def get_case_sensitive_filter(self) -> bool:
        return bool(self.load_setting(self.FILTER_CASE_SENSITIVE, False))

    def set_case_sensitive_filter(self, is_sensitive: bool):
        self.save_setting(self.FILTER_CASE_SENSITIVE, is_sensitive)

    def get_sort_info(self) -> Tuple[int, int]:
        column = int(self.load_setting(self.SORT_COLUMN, 0)) # Default sort by Timestamp
        order = int(self.load_setting(self.SORT_ORDER, 0))   # Default Qt.AscendingOrder
        return column, order

    def set_sort_info(self, column: int, order: int):
        self.save_setting(self.SORT_COLUMN, column)
        self.save_setting(self.SORT_ORDER, order)

    def get_log_level_colors(self) -> Dict[str, QColor]:
        saved_colors_str = self.load_setting(self.LOG_LEVEL_COLORS, self.DEFAULT_LOG_LEVEL_COLORS)
        # Ensure conversion from hex strings to QColor objects
        return {level: QColor(hex_color) for level, hex_color in saved_colors_str.items()}


    def set_log_level_colors(self, colors: Dict[str, QColor]):
        # Store colors as hex strings for QSettings compatibility
        colors_str = {level: color.name() for level, color in colors.items()}
        self.save_setting(self.LOG_LEVEL_COLORS, colors_str)

    def get_logger_name_colors(self) -> Dict[str, QColor]:
        saved_colors_str = self.load_setting(self.LOGGER_NAME_COLORS, {})
        return {name: QColor(hex_color) for name, hex_color in saved_colors_str.items()}

    def set_logger_name_colors(self, colors: Dict[str, QColor]):
        colors_str = {name: color.name() for name, color in colors.items()}
        self.save_setting(self.LOGGER_NAME_COLORS, colors_str)

    def get_column_widths(self) -> Optional[List[int]]:
        return self.load_setting(self.COLUMN_WIDTHS)

    def set_column_widths(self, widths: List[int]):
        self.save_setting(self.COLUMN_WIDTHS, widths)

    def get_default_log_level_color(self) -> QColor:
        return QColor(self.DEFAULT_LOG_LEVEL_COLORS["DEFAULT"])