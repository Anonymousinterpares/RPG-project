from PySide6.QtCore import QSortFilterProxyModel, Qt, QDateTime
from typing import Set, Dict, Optional, Any
from .log_entry import LogEntry # Assuming LogEntry is in the same directory or accessible

class LogFilterProxyModel(QSortFilterProxyModel):
    """
    A proxy model for filtering and sorting LogEntry data.
    """
    COLUMN_TIMESTAMP = 0
    COLUMN_LOGGER = 1
    COLUMN_LEVEL = 2
    COLUMN_MESSAGE = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text_filters: Dict[int, str] = {} # {column_index: filter_text}
        self._logger_name_filters: Optional[Set[str]] = None # Set of logger names to show, None means show all
        self._level_filters: Optional[Set[str]] = None       # Set of levels to show, None means show all
        self._case_sensitive: bool = False

    def set_text_filter(self, column: int, text: str):
        if not text:
            self._text_filters.pop(column, None)
        else:
            self._text_filters[column] = text
        self.invalidateFilter()

    def get_text_filter(self, column: int) -> str:
        return self._text_filters.get(column, "")

    def set_logger_name_filters(self, active_loggers: Optional[Set[str]]):
        self._logger_name_filters = active_loggers
        self.invalidateFilter()

    def get_logger_name_filters(self) -> Optional[Set[str]]:
        return self._logger_name_filters

    def set_level_filters(self, active_levels: Optional[Set[str]]):
        self._level_filters = active_levels
        self.invalidateFilter()
    
    def get_level_filters(self) -> Optional[Set[str]]:
        return self._level_filters

    def set_filter_case_sensitive(self, sensitive: bool):
        self._case_sensitive = sensitive
        self.invalidateFilter()

    def get_filter_case_sensitive(self) -> bool:
        return self._case_sensitive

    def clear_all_filters(self):
        self._text_filters.clear()
        self._logger_name_filters = None
        self._level_filters = None
        # self._case_sensitive = False # Optionally reset case sensitivity or keep user preference
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: Any) -> bool:
        source_model = self.sourceModel()
        if not source_model:
            return True

        # Checkbox filters (Logger Name and Level)
        if self._logger_name_filters is not None:
            logger_name_index = source_model.index(source_row, self.COLUMN_LOGGER, source_parent)
            logger_name = source_model.data(logger_name_index, Qt.ItemDataRole.DisplayRole)
            if logger_name not in self._logger_name_filters:
                return False

        if self._level_filters is not None:
            level_index = source_model.index(source_row, self.COLUMN_LEVEL, source_parent)
            level = source_model.data(level_index, Qt.ItemDataRole.DisplayRole)
            if level not in self._level_filters:
                return False

        # Text filters for each column
        for col_idx, filter_text in self._text_filters.items():
            if not filter_text:
                continue

            index = source_model.index(source_row, col_idx, source_parent)
            cell_data = source_model.data(index, Qt.ItemDataRole.DisplayRole)
            
            if cell_data is None: # Handle cases where cell might not have display data
                return False

            text_to_check = str(cell_data)
            text_filter_compare = filter_text

            if not self._case_sensitive:
                text_to_check = text_to_check.lower()
                text_filter_compare = filter_text.lower()
            
            if text_filter_compare not in text_to_check:
                return False
                
        return True

    def lessThan(self, source_left: Any, source_right: Any) -> bool:
        """
        Custom sorting for columns.
        Especially important for timestamp sorting if using string representations.
        """
        left_data = self.sourceModel().data(source_left)
        right_data = self.sourceModel().data(source_right)

        if source_left.column() == self.COLUMN_TIMESTAMP:
            # If actual QDateTime objects are stored (e.g., in UserRole), use them for sorting
            left_dt = self.sourceModel().data(source_left, Qt.ItemDataRole.UserRole)
            right_dt = self.sourceModel().data(source_right, Qt.ItemDataRole.UserRole)
            if isinstance(left_dt, QDateTime) and isinstance(right_dt, QDateTime):
                return left_dt < right_dt
            # Fallback to string comparison if QDateTime not available
            # This might happen if data isn't set with UserRole correctly
            
        # Default string-based comparison for other columns or if timestamp isn't QDateTime
        if isinstance(left_data, (int, float)) and isinstance(right_data, (int, float)):
            return left_data < right_data
        
        # Fallback to string comparison
        return str(left_data) < str(right_data)