import sys
import os
from typing import Any, Dict, List, Optional, Set
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QMenuBar, QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QLineEdit, QCheckBox, QPushButton, QMenu, QWidgetAction,
    QStyledItemDelegate, QApplication
)
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem, QColor, QPalette, QIcon, QFont
from PySide6.QtCore import Qt, Slot, QSortFilterProxyModel, QSettings, QDateTime, QSize, QModelIndex

from log_viewer_tool.color_delegate import ColorDelegate
from log_viewer_tool.export_dialog import ExportDialog

from .log_entry import LogEntry
from .log_parser import LogParser
from .settings_manager import SettingsManager
from .color_settings_dialog import ColorSettingsDialog # To be created
from .filter_model import LogFilterProxyModel # Import the new filter model

import logging
logger = logging.getLogger("LogViewerTool.MainWindow")

# Determine project root assuming run_log_viewer.py is in the root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")


class MainWindow(QMainWindow):
    COLUMN_TIMESTAMP = 0
    COLUMN_LOGGER = 1
    COLUMN_LEVEL = 2
    COLUMN_MESSAGE = 3

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Log Viewer")
        self.settings_manager = SettingsManager()
        self.log_entries: List[LogEntry] = []
        self.current_log_file_path: Optional[str] = None

        self.unique_loggers: Set[str] = set()
        self.unique_levels: Set[str] = set()

        self._active_logger_filters: Optional[Set[str]] = None # Initialize as None
        self._active_level_filters: Optional[Set[str]] = None  # Initialize as None

        self._setup_ui()
        self._load_settings()
        self._create_color_delegate() # Create and set delegate after UI setup
        self._apply_loaded_filters() 
        self._try_load_latest_log()

    def _setup_ui(self):
        # Import partial from functools
        from functools import partial

        self.resize(1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        
        open_action = QAction(QIcon.fromTheme("document-open", QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-open-32.png")), "&Open Log File...", self)
        open_action.setObjectName("openAction") 
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_log_file_dialog)
        file_menu.addAction(open_action)

        refresh_action = QAction(QIcon.fromTheme("view-refresh", QIcon(":/qt-project.org/styles/commonstyle/images/refresh-32.png")), "&Refresh Current Log", self)
        refresh_action.setObjectName("refreshAction") 
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_current_log)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        export_action = QAction(QIcon.fromTheme("document-save-as", QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-save-32.png")), "&Export Visible Logs...", self)
        export_action.setObjectName("exportAction") 
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_logs_dialog)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(QIcon.fromTheme("application-exit", QIcon(":/qt-project.org/styles/commonstyle/images/standardbutton-cancel-32.png")), "E&xit", self)
        exit_action.setObjectName("exitAction") 
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("&View")
        color_settings_action = QAction("Color Settings...", self)
        color_settings_action.setObjectName("colorSettingsAction") 
        color_settings_action.triggered.connect(self.open_color_settings_dialog)
        view_menu.addAction(color_settings_action)

        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("mainToolBar") 
        toolbar.setIconSize(QSize(24,24))
        self.addToolBar(toolbar)
        toolbar.addAction(open_action)
        toolbar.addAction(refresh_action)
        toolbar.addAction(export_action)

        filter_widget = QWidget()
        filter_widget.setObjectName("filterWidget") 
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0,5,0,5)

        self.text_filter_inputs: List[QLineEdit] = []
        column_names_for_filter = ["Timestamp", "Logger", "Level", "Message"]
        self.filter_buttons: List[Optional[QPushButton]] = [] 

        for i, name in enumerate(column_names_for_filter):
            le = QLineEdit()
            le.setObjectName(f"filterLineEdit_{name.replace(' ', '')}") 
            le.setPlaceholderText(f"Filter {name}...")
            le.textChanged.connect(self.apply_text_filters)
            filter_layout.addWidget(le)
            self.text_filter_inputs.append(le)

            if name == "Logger":
                btn = QPushButton("▼")
                btn.setObjectName("loggerFilterButton") 
                btn.setFixedSize(25, le.sizeHint().height())
                btn.setToolTip(f"Filter {name} by values")
                # Pass the button 'btn' itself as an argument to the slot
                btn.clicked.connect(partial(self.show_checkbox_filter_menu, btn, self.COLUMN_LOGGER))
                filter_layout.addWidget(btn)
                self.filter_buttons.append(btn)
            elif name == "Level":
                btn = QPushButton("▼")
                btn.setObjectName("levelFilterButton") 
                btn.setFixedSize(25, le.sizeHint().height())
                btn.setToolTip(f"Filter {name} by values")
                # Pass the button 'btn' itself as an argument to the slot
                btn.clicked.connect(partial(self.show_checkbox_filter_menu, btn, self.COLUMN_LEVEL))
                filter_layout.addWidget(btn)
                self.filter_buttons.append(btn)
            else:
                self.filter_buttons.append(None) 

        self.case_sensitive_checkbox = QCheckBox("Case Sensitive")
        self.case_sensitive_checkbox.setObjectName("caseSensitiveCheckbox") 
        self.case_sensitive_checkbox.stateChanged.connect(self.apply_filters_due_to_case_change)
        filter_layout.addWidget(self.case_sensitive_checkbox)
        
        clear_filters_button = QPushButton("Clear Filters")
        clear_filters_button.setObjectName("clearFiltersButton") 
        clear_filters_button.clicked.connect(self.clear_all_filters)
        filter_layout.addWidget(clear_filters_button)

        main_layout.addWidget(filter_widget)

        self.log_table_view = QTableView()
        self.log_table_view.setObjectName("logTableView") 
        self.log_table_view.setAlternatingRowColors(True)
        self.log_table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.log_table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.log_table_view.setSortingEnabled(True)
        self.log_table_view.horizontalHeader().setStretchLastSection(True)
        
        self.log_model = QStandardItemModel(0, 4, self) 
        self.log_model.setHorizontalHeaderLabels(["Timestamp", "Logger", "Level", "Message"])
        
        self.filter_proxy_model = LogFilterProxyModel(self)
        self.filter_proxy_model.setSourceModel(self.log_model)
        self.log_table_view.setModel(self.filter_proxy_model)
        
        self.log_table_view.horizontalHeader().sortIndicatorChanged.connect(self._handle_sort_indicator_changed)

        main_layout.addWidget(self.log_table_view)

        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("mainStatusBar") 
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Log Viewer Ready. Open a log file or refresh.")

    def _load_settings(self):
        logger.info("Loading settings...")
        geometry = self.settings_manager.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self.settings_manager.get_window_state()
        if state:
            self.restoreState(state)

        widths = self.settings_manager.get_column_widths()
        if widths and len(widths) == self.log_model.columnCount():
            for i, width_val in enumerate(widths):
                try:
                    # Ensure width_val is an integer
                    self.log_table_view.setColumnWidth(i, int(width_val))
                except ValueError:
                    logger.warning(f"Could not convert column width '{width_val}' to int for column {i}. Using default.")
                    # Fallback or skip setting this width
                    if i == self.COLUMN_TIMESTAMP: self.log_table_view.setColumnWidth(i, 180)
                    elif i == self.COLUMN_LOGGER: self.log_table_view.setColumnWidth(i, 150)
                    elif i == self.COLUMN_LEVEL: self.log_table_view.setColumnWidth(i, 80)

        else: # Default widths if not saved or mismatch
            self.log_table_view.setColumnWidth(self.COLUMN_TIMESTAMP, 180) 
            self.log_table_view.setColumnWidth(self.COLUMN_LOGGER, 150)
            self.log_table_view.setColumnWidth(self.COLUMN_LEVEL, 80)
            # Message column will stretch due to setStretchLastSection(True)

        sort_col_raw = self.settings_manager.get_sort_info()[0]
        sort_order_raw = self.settings_manager.get_sort_info()[1]
        
        try:
            sort_col = int(sort_col_raw)
            sort_order = Qt.SortOrder(int(sort_order_raw))
            self.log_table_view.sortByColumn(sort_col, sort_order)
            self.filter_proxy_model.sort(sort_col, sort_order)
        except ValueError:
            logger.warning(f"Could not convert sort_col '{sort_col_raw}' or sort_order '{sort_order_raw}' to int. Using defaults.")
            self.log_table_view.sortByColumn(self.COLUMN_TIMESTAMP, Qt.SortOrder.AscendingOrder)
            self.filter_proxy_model.sort(self.COLUMN_TIMESTAMP, Qt.SortOrder.AscendingOrder)


        text_filters = self.settings_manager.get_text_filters()
        for col_idx_str, text_val in text_filters.items(): # col_idx might be string from QSettings
            try:
                col_idx = int(col_idx_str)
                if col_idx < len(self.text_filter_inputs):
                    self.text_filter_inputs[col_idx].setText(str(text_val))
            except ValueError:
                logger.warning(f"Invalid column index '{col_idx_str}' for text filter.")

        self.case_sensitive_checkbox.setChecked(self.settings_manager.get_case_sensitive_filter())
        
        # Load checkbox logger filters
        loaded_logger_filters_list = self.settings_manager.get_checkbox_logger_filters()
        if not loaded_logger_filters_list:  # Key not in settings or legacy empty list
            self._active_logger_filters = None  # Default to "Show All"
        elif loaded_logger_filters_list == ["__ALL__"]:
            self._active_logger_filters = None  # Show All
        elif loaded_logger_filters_list == ["__NONE__"]:
            self._active_logger_filters = set()  # Show None
        else:
            self._active_logger_filters = set(loaded_logger_filters_list)

        # Load checkbox level filters
        loaded_level_filters_list = self.settings_manager.get_checkbox_level_filters()
        if not loaded_level_filters_list:  # Key not in settings or legacy empty list
            self._active_level_filters = None  # Default to "Show All"
        elif loaded_level_filters_list == ["__ALL__"]:
            self._active_level_filters = None  # Show All
        elif loaded_level_filters_list == ["__NONE__"]:
            self._active_level_filters = set()  # Show None
        else:
            self._active_level_filters = set(loaded_level_filters_list)
        
        logger.info("Settings loaded. Filters will be applied by _apply_loaded_filters.")

    def _apply_loaded_filters(self):
        """Applies all loaded/current filters to the proxy model."""
        logger.debug("Applying all loaded filters to proxy model.")
        # Text filters
        for i, le in enumerate(self.text_filter_inputs):
            self.filter_proxy_model.set_text_filter(i, le.text())
        
        # Case sensitivity
        self.filter_proxy_model.set_filter_case_sensitive(self.case_sensitive_checkbox.isChecked())

        # Checkbox Logger filters
        if self._active_logger_filters is None: # "Show All"
            self.filter_proxy_model.set_logger_name_filters(None)
        else: # Specific set, even if empty (for "Show None")
            self.filter_proxy_model.set_logger_name_filters(self._active_logger_filters.copy())
        
        # Checkbox Level filters
        if self._active_level_filters is None: # "Show All"
            self.filter_proxy_model.set_level_filters(None)
        else: # Specific set, even if empty
            self.filter_proxy_model.set_level_filters(self._active_level_filters.copy())

        self.filter_proxy_model.invalidateFilter()
        logger.debug("All filters (text, case, checkbox) applied.")

    def _save_settings(self):
        logger.info("Saving settings...")
        self.settings_manager.set_window_geometry(self.saveGeometry())
        self.settings_manager.set_window_state(self.saveState())

        widths = [self.log_table_view.columnWidth(i) for i in range(self.log_model.columnCount())]
        self.settings_manager.set_column_widths(widths)
        
        sort_col = self.log_table_view.horizontalHeader().sortIndicatorSection()
        sort_order_enum = self.log_table_view.horizontalHeader().sortIndicatorOrder()
        self.settings_manager.set_sort_info(sort_col, sort_order_enum.value) # Use .value here

        text_filters = {i: self.text_filter_inputs[i].text() for i in range(len(self.text_filter_inputs))}
        self.settings_manager.set_text_filters(text_filters)
        self.settings_manager.set_case_sensitive_filter(self.case_sensitive_checkbox.isChecked())
        
        # Save checkbox logger filters
        logger_filters_to_save: List[str]
        if self._active_logger_filters is None:  # Show All
            logger_filters_to_save = ["__ALL__"]
        elif not self._active_logger_filters:  # Empty set, Show None
            logger_filters_to_save = ["__NONE__"]
        else:  # Specific filters
            logger_filters_to_save = sorted(list(self._active_logger_filters))
        self.settings_manager.set_checkbox_logger_filters(logger_filters_to_save)

        # Save checkbox level filters
        level_filters_to_save: List[str]
        if self._active_level_filters is None:  # Show All
            level_filters_to_save = ["__ALL__"]
        elif not self._active_level_filters:  # Empty set, Show None
            level_filters_to_save = ["__NONE__"]
        else:  # Specific filters
            level_filters_to_save = sorted(list(self._active_level_filters))
        self.settings_manager.set_checkbox_level_filters(level_filters_to_save)
        
        logger.info("Settings saved.")

    def _try_load_latest_log(self):
        if not os.path.isdir(DEFAULT_LOGS_DIR):
            self.status_bar.showMessage(f"Logs directory not found: {DEFAULT_LOGS_DIR}")
            logger.warning(f"Default logs directory does not exist: {DEFAULT_LOGS_DIR}")
            return

        try:
            log_files = [
                f for f in os.listdir(DEFAULT_LOGS_DIR)
                if os.path.isfile(os.path.join(DEFAULT_LOGS_DIR, f))
                and f.startswith("game_") and f.endswith(".log")
            ]
            if not log_files:
                self.status_bar.showMessage("No game_*.log files found in logs directory.")
                return

            log_files.sort(key=lambda name: os.path.getmtime(os.path.join(DEFAULT_LOGS_DIR, name)), reverse=True)
            latest_log_path = os.path.join(DEFAULT_LOGS_DIR, log_files[0])
            self.load_log_file(latest_log_path)
        except Exception as e:
            self.status_bar.showMessage(f"Error loading latest log: {e}")
            logger.error(f"Error trying to load latest log: {e}", exc_info=True)

    @Slot()
    def open_log_file_dialog(self):
        last_folder = self.settings_manager.get_last_log_folder(DEFAULT_LOGS_DIR)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Log File",
            last_folder,
            "Log Files (*.log *.txt);;All Files (*)"
        )
        if file_path:
            self.settings_manager.set_last_log_folder(os.path.dirname(file_path))
            self.load_log_file(file_path)

    @Slot()
    def refresh_current_log(self):
        if self.current_log_file_path and os.path.exists(self.current_log_file_path):
            logger.info(f"Refreshing log file: {self.current_log_file_path}")
            self.load_log_file(self.current_log_file_path)
        elif self.current_log_file_path:
            QMessageBox.warning(self, "Refresh Error", f"Previously loaded file not found:\n{self.current_log_file_path}\nPlease open a new file.")
            self.current_log_file_path = None
            self.status_bar.showMessage("Previous log file not found. Please open a new one.")
        else:
            self._try_load_latest_log()

    def load_log_file(self, file_path: str):
        logger.info(f"Attempting to load log file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            self.log_entries = LogParser.parse_file_content(content)
            self.current_log_file_path = file_path
            
            # Populate unique sets before populating table, as checkbox menus might need them
            self.unique_loggers.clear()
            self.unique_levels.clear()
            for entry in self.log_entries:
                self.unique_loggers.add(entry.logger_name)
                self.unique_levels.add(entry.level)

            self._populate_table() # This populates the source model
            
            # After table (and source model) is populated, apply all filters
            self._apply_loaded_filters() 

            self.status_bar.showMessage(f"Loaded {len(self.log_entries)} entries from {os.path.basename(file_path)}", 5000)
            logger.info(f"Successfully loaded {len(self.log_entries)} entries from {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error Loading Log", f"Failed to load log file:\n{file_path}\n\nError: {e}")
            self.status_bar.showMessage(f"Error loading {os.path.basename(file_path)}", 5000)
            logger.error(f"Error loading log file {file_path}: {e}", exc_info=True)
    
    def _populate_table(self):
        self.log_model.removeRows(0, self.log_model.rowCount())
        
        items_to_add = []
        for entry in self.log_entries:
            timestamp_item = QStandardItem(entry.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
            timestamp_item.setData(QDateTime(entry.timestamp), Qt.ItemDataRole.UserRole)
            timestamp_item.setToolTip(entry.timestamp.isoformat())

            logger_item = QStandardItem(entry.logger_name)
            level_item = QStandardItem(entry.level)
            message_item = QStandardItem(entry.message)
            message_item.setToolTip(entry.message) # Full message on tooltip

            items_to_add.append([timestamp_item, logger_item, level_item, message_item])
        
        for row_items in items_to_add:
            self.log_model.appendRow(row_items)

        # Restore column widths if previously set, or set defaults
        widths = self.settings_manager.get_column_widths()
        if widths and len(widths) == self.log_model.columnCount():
            for i, width_val in enumerate(widths):
                try:
                    self.log_table_view.setColumnWidth(i, int(width_val))
                except ValueError:
                    logger.warning(f"Could not convert column width '{width_val}' to int for column {i} during populate. Using default.")
                    # Fallback or skip setting this width
                    if i == self.COLUMN_TIMESTAMP: self.log_table_view.setColumnWidth(i, 180)
                    elif i == self.COLUMN_LOGGER: self.log_table_view.setColumnWidth(i, 150)
                    elif i == self.COLUMN_LEVEL: self.log_table_view.setColumnWidth(i, 80)
        else:
            # Default widths if not saved or mismatch, or first run
            self.log_table_view.resizeColumnsToContents() # Fallback to content size initially
            self.log_table_view.setColumnWidth(self.COLUMN_TIMESTAMP, 180)
            self.log_table_view.setColumnWidth(self.COLUMN_LOGGER, 150)
            self.log_table_view.setColumnWidth(self.COLUMN_LEVEL, 80)
        
        self.log_table_view.horizontalHeader().setStretchLastSection(True)
        # Ensure message column has a decent minimum width if it exists and is not the last stretched section
        if self.log_model.columnCount() > self.COLUMN_MESSAGE and not self.log_table_view.horizontalHeader().stretchLastSection():
             current_message_width = self.log_table_view.columnWidth(self.COLUMN_MESSAGE)
             if current_message_width < 300 : 
                 self.log_table_view.setColumnWidth(self.COLUMN_MESSAGE, 300)
        elif self.log_model.columnCount() > self.COLUMN_MESSAGE and self.log_table_view.horizontalHeader().stretchLastSection():
             # If message is last section and stretched, we don't need to force a min width here
             # as it will take available space. But ensure it's not too small if table is narrow.
             pass


        # Re-apply sorting after populating
        # Use the current sort indicator from the header if available, otherwise from settings
        header = self.log_table_view.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()

        if sort_col == -1: # No current sort indicator set by user click yet this session
            sort_col_setting, sort_order_raw_setting = self.settings_manager.get_sort_info()
            try:
                sort_col = int(sort_col_setting)
                sort_order = Qt.SortOrder(int(sort_order_raw_setting))
            except ValueError:
                logger.warning(f"Invalid sort settings from manager '{sort_col_setting}', '{sort_order_raw_setting}'. Defaulting.")
                sort_col = self.COLUMN_TIMESTAMP
                sort_order = Qt.SortOrder.AscendingOrder
        
        self.filter_proxy_model.sort(sort_col, sort_order)

    @Slot()
    def apply_text_filters(self):
        for i, le in enumerate(self.text_filter_inputs):
            self.filter_proxy_model.set_text_filter(i, le.text())
        self.filter_proxy_model.invalidateFilter()

    @Slot()
    def apply_filters_due_to_case_change(self):
        self.filter_proxy_model.set_filter_case_sensitive(self.case_sensitive_checkbox.isChecked())
        # No need to call invalidateFilter here, as set_filter_case_sensitive does it.

    @Slot(QPushButton, int)
    def show_checkbox_filter_menu(self, sender_button: QPushButton, column_index: int, _checked: bool = False):
        if not isinstance(sender_button, QPushButton):
            logger.warning(f"show_checkbox_filter_menu called with invalid sender_button type: {type(sender_button)}. Aborting.")
            return

        logger.debug(f"Attempting to show checkbox filter menu for column_index: {column_index}, triggered by: {sender_button.objectName()}")

        menu = QMenu(self)
        menu.setObjectName(f"checkboxFilterMenu_col{column_index}")
        
        unique_values_set: Set[str] = set()
        active_filters_attr_name: str = "" 
        filter_proxy_setter_func = None

        if column_index == self.COLUMN_LOGGER:
            unique_values_set = self.unique_loggers
            active_filters_attr_name = "_active_logger_filters"
            filter_proxy_setter_func = self.filter_proxy_model.set_logger_name_filters
            logger.debug(f"Targeting logger filters. Unique count: {len(self.unique_loggers)}")
        elif column_index == self.COLUMN_LEVEL:
            unique_values_set = self.unique_levels
            active_filters_attr_name = "_active_level_filters"
            filter_proxy_setter_func = self.filter_proxy_model.set_level_filters
            logger.debug(f"Targeting level filters. Unique count: {len(self.unique_levels)}")
        else:
            logger.error(f"show_checkbox_filter_menu called with invalid column_index: {column_index}. Aborting.")
            return

        current_active_filters: Optional[Set[str]] = getattr(self, active_filters_attr_name)
        logger.debug(f"Current active filters for '{active_filters_attr_name}': {current_active_filters}")

        item_checkboxes: List[QCheckBox] = [] # To store individual QCheckBoxes

        # --- Create QWidgetAction for "Select All / Show All" ---
        # (Container widget for better spacing/alignment if needed, though QCheckBox can be directly set)
        select_all_container_widget = QWidget(menu) 
        select_all_layout = QHBoxLayout(select_all_container_widget)
        select_all_layout.setContentsMargins(5, 3, 5, 3) 
        select_all_checkbox = QCheckBox("Select All / Show All")
        select_all_layout.addWidget(select_all_checkbox)
        select_all_container_widget.setLayout(select_all_layout)

        select_all_widget_action = QWidgetAction(menu)
        select_all_widget_action.setDefaultWidget(select_all_container_widget)
        menu.addAction(select_all_widget_action)
        
        initial_sa_checked_state = (current_active_filters is None) or \
                                 (current_active_filters is not None and 
                                  len(unique_values_set) > 0 and
                                  unique_values_set.issubset(current_active_filters))
        if not unique_values_set and current_active_filters is None: 
            initial_sa_checked_state = True
        elif not unique_values_set and current_active_filters is not None: 
            initial_sa_checked_state = False
        
        select_all_checkbox.setChecked(initial_sa_checked_state)
        logger.debug(f"'Select All / Show All' QCheckBox created. Initial checked state: {initial_sa_checked_state}")
        
        menu.addSeparator()

        # Populate individual QCheckBoxes within QWidgetActions for each unique value
        if not unique_values_set:
            logger.debug("No unique values found to populate specific filter items in the menu.")
        
        sorted_unique_values = sorted(list(unique_values_set))
        for i, value in enumerate(sorted_unique_values):
            item_container_widget = QWidget(menu)
            item_layout = QHBoxLayout(item_container_widget)
            item_layout.setContentsMargins(5, 2, 5, 2) # Slightly less vertical padding for items
            
            item_cb = QCheckBox(value)
            item_layout.addWidget(item_cb)
            item_container_widget.setLayout(item_layout)

            is_item_checked = (current_active_filters is None) or \
                              (current_active_filters is not None and value in current_active_filters)
            item_cb.setChecked(is_item_checked)
            
            item_widget_action = QWidgetAction(menu)
            item_widget_action.setDefaultWidget(item_container_widget)
            
            item_cb.toggled.connect(
                lambda checked_state, val=value, cb=item_cb, sa_cb=select_all_checkbox,
                       uvs=unique_values_set, fpsf=filter_proxy_setter_func, afan=active_filters_attr_name: 
                self._toggle_single_checkbox_filter(checked_state, val, sa_cb, uvs, fpsf, afan)
            )
            item_checkboxes.append(item_cb) 
            menu.addAction(item_widget_action)
            if i < 5: logger.debug(f"Added item checkbox for: '{value}', Checked: {is_item_checked}")
        if len(sorted_unique_values) > 5: logger.debug(f"...and {len(sorted_unique_values) - 5} more item checkboxes.")

        # Connect the select_all_checkbox's toggled signal AFTER item_checkboxes list is populated
        select_all_checkbox.toggled.connect(
            lambda checked_state, sa_cb=select_all_checkbox, ic_list=item_checkboxes, 
                   uvs=unique_values_set, fpsf=filter_proxy_setter_func, afan=active_filters_attr_name:
            self._handle_select_all_widget_toggled(checked_state, sa_cb, ic_list, uvs, fpsf, afan)
        )
        
        if not menu.actions(): 
            logger.warning("Menu has no actions. It will not be displayed.")
            return
            
        logger.debug(f"Menu prepared with {len(menu.actions())} total entries. Executing.")
        try:
            global_pos = sender_button.mapToGlobal(sender_button.rect().bottomLeft())
            menu.exec(global_pos)
            logger.debug("Menu execution finished.")
        except Exception as e:
            logger.error(f"Exception during menu.exec: {e}", exc_info=True)

    def _toggle_single_checkbox_filter(self, item_checkbox_checked_state: bool, value: str, # First param is item's QCheckBox state
                                       select_all_checkbox: QCheckBox, 
                                       unique_values_set: Set[str],
                                       filter_proxy_setter_func, active_filters_attr_name: str):
        """Toggles a single item's QCheckBox filter, updates proxy, and updates 'Select All' checkbox state."""
        logger.debug(f"Single item QCheckBox toggled: '{value}', Checked: {item_checkbox_checked_state} for {active_filters_attr_name}")
        current_active_set_on_self: Optional[Set[str]] = getattr(self, active_filters_attr_name)

        new_modified_set: Optional[Set[str]]
        if current_active_set_on_self is None: 
            if not item_checkbox_checked_state: 
                new_modified_set = unique_values_set.copy()
                new_modified_set.discard(value)
            else: 
                new_modified_set = None 
        else: 
            new_modified_set = current_active_set_on_self.copy()
            if item_checkbox_checked_state:
                new_modified_set.add(value)
            else:
                new_modified_set.discard(value)

        final_filter_state_for_proxy: Optional[Set[str]]
        current_is_show_all = False
        if new_modified_set is None: 
            setattr(self, active_filters_attr_name, None)
            final_filter_state_for_proxy = None
            current_is_show_all = True
        elif len(unique_values_set) > 0 and new_modified_set == unique_values_set: 
            setattr(self, active_filters_attr_name, None) 
            final_filter_state_for_proxy = None
            current_is_show_all = True
        elif not new_modified_set: 
            setattr(self, active_filters_attr_name, set()) 
            final_filter_state_for_proxy = set()
        else: 
            setattr(self, active_filters_attr_name, new_modified_set)
            final_filter_state_for_proxy = new_modified_set.copy() 

        filter_proxy_setter_func(final_filter_state_for_proxy)
        logger.debug(f"Filter for {active_filters_attr_name} set to: {getattr(self, active_filters_attr_name)}")

        should_select_all_be_checked: bool
        final_active_set_on_self = getattr(self, active_filters_attr_name) 

        if final_active_set_on_self is None: 
            should_select_all_be_checked = True
        elif not unique_values_set : 
             should_select_all_be_checked = (final_active_set_on_self is None)
        else:  
            # If we have a set, "Select All" is false unless this set happens to be equal to unique_values_set,
            # which is handled by the normalization that sets final_active_set_on_self to None in that case.
            # So, if final_active_set_on_self is a set, should_select_all_be_checked is false.
            should_select_all_be_checked = False
        
        was_blocked = select_all_checkbox.blockSignals(True)
        if select_all_checkbox.isChecked() != should_select_all_be_checked:
            select_all_checkbox.setChecked(should_select_all_be_checked)
            logger.debug(f"Updating 'Select All' checkbox to {should_select_all_be_checked}")
        select_all_checkbox.blockSignals(was_blocked)
        
    def _handle_select_all_widget_toggled(self, is_select_all_checked: bool,
                                           select_all_checkbox_ref: QCheckBox, 
                                           item_checkboxes_list: List[QCheckBox], # Changed from item_actions_list
                                           unique_values_set: Set[str],
                                           filter_proxy_setter_func, active_filters_attr_name: str):
        """Handles toggling of the 'Select All / Show All' QCheckBox in the QWidgetAction."""
        logger.debug(f"'Select All' QCheckBox toggled to: {is_select_all_checked} for {active_filters_attr_name}")

        # 1. Update internal filter state and apply to proxy model
        if is_select_all_checked: 
            setattr(self, active_filters_attr_name, None) # None means show all
            filter_proxy_setter_func(None)
        else: 
            setattr(self, active_filters_attr_name, set()) # Empty set means show none
            filter_proxy_setter_func(set()) 
        
        logger.debug(f"Filter for {active_filters_attr_name} set to: {getattr(self, active_filters_attr_name)} by 'Select All' toggle.")

        # 2. Update the check state of all individual item_checkboxes in the menu
        logger.debug(f"Updating {len(item_checkboxes_list)} individual item checkboxes based on 'Select All' state.")
        for item_cb in item_checkboxes_list: # Iterate through QCheckBoxes
            # Block signals temporarily to prevent _toggle_single_checkbox_filter from firing recursively
            was_blocked = item_cb.blockSignals(True)
            if item_cb.isChecked() != is_select_all_checked:
                item_cb.setChecked(is_select_all_checked)
            item_cb.blockSignals(was_blocked)
        logger.debug(f"Finished updating individual item checkboxes. 'Select All' state: {is_select_all_checked}")

    @Slot()
    def clear_all_filters(self):
        for le in self.text_filter_inputs:
            le.clear() # This will trigger apply_text_filters for each if still connected one by one
        
        # Instead of relying on individual signals, set proxy filters directly then invalidate
        self.filter_proxy_model.clear_all_filters() # This should handle text filters in proxy too.

        self._active_logger_filters = None # None means show all
        self.filter_proxy_model.set_logger_name_filters(None)

        self._active_level_filters = None  # None means show all
        self.filter_proxy_model.set_level_filters(None)
        
        self.case_sensitive_checkbox.setChecked(False) # This will trigger its own update
        self.filter_proxy_model.set_filter_case_sensitive(False) # Ensure proxy model is also updated
        
        # One final invalidation after all changes
        self.filter_proxy_model.invalidateFilter()
        logger.info("All filters cleared.")

    @Slot(int, Qt.SortOrder)
    def _handle_sort_indicator_changed(self, logical_index: int, order: Qt.SortOrder):
        """Saves sort info when table header is clicked."""
        # Qt.SortOrder is an enum; QSettings can store its integer value.
        self.settings_manager.set_sort_info(logical_index, order.value) 
        logger.debug(f"Sort indicator changed: Column {logical_index}, Order {order}. Settings saved.")

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    def _create_color_delegate(self):
        """Creates and sets the color delegate for the log table."""
        self.color_delegate = ColorDelegate(self.settings_manager, self)
        self.log_table_view.setItemDelegate(self.color_delegate)
        logger.debug("Color delegate created and set for log table.")

    def open_color_settings_dialog(self):
        """Opens the dialog to manage color settings."""
        # Ensure unique_loggers and unique_levels are up-to-date before opening dialog
        # This is important if a new log file was loaded since the last time these were populated.
        self.unique_loggers.clear()
        self.unique_levels.clear()
        for entry in self.log_entries:
            self.unique_loggers.add(entry.logger_name)
            self.unique_levels.add(entry.level)
        
        dialog = ColorSettingsDialog(self.settings_manager, self.unique_loggers, self.unique_levels, self)
        dialog.settings_changed.connect(self._on_color_settings_changed)
        dialog.exec()

    def export_logs_dialog(self):
        """Opens a dialog to configure and export logs."""
        if not self.log_entries:
            QMessageBox.information(self, "Export Logs", "No logs loaded to export.")
            return

        # Ensure unique sets are up-to-date
        self.unique_loggers.clear()
        self.unique_levels.clear()
        for entry in self.log_entries:
            self.unique_loggers.add(entry.logger_name)
            self.unique_levels.add(entry.level)

        dialog = ExportDialog(self.unique_loggers, self.unique_levels, self)
        if dialog.exec():
            options = dialog.get_export_options()
            self._perform_export(options)

    def _perform_export(self, options: Dict[str, Any]):
        """Performs the actual log export based on selected options."""
        default_filename = f"exported_logs_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}{options['format']}"
        
        last_export_folder = self.settings_manager.load_setting("paths/last_export_folder", DEFAULT_LOGS_DIR)

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Exported Logs",
            os.path.join(last_export_folder, default_filename),
            f"Log Files (*{options['format']});;All Files (*)"
        )

        if not file_path:
            return

        self.settings_manager.save_setting("paths/last_export_folder", os.path.dirname(file_path))
        
        # Get currently visible (filtered and sorted) log entries from the proxy model
        # This ensures we export what the user sees, respecting all active filters.
        # The proxy model must have a method to get all *source* indices that are currently visible.
        
        # The QSortFilterProxyModel itself acts on the source model.
        # We need to iterate through the proxy model's rows.
        
        log_lines_to_export = []
        proxy = self.filter_proxy_model
        source_model = proxy.sourceModel()

        for proxy_row in range(proxy.rowCount()):
            source_index = proxy.mapToSource(proxy.index(proxy_row, 0)) # Map to source model index
            if source_index.isValid():
                # Assuming log_entries are in the same order as the source_model initially.
                # This might be fragile if source_model can be reordered independently of log_entries.
                # A more robust way is to store LogEntry objects directly in QStandardItem.setData
                # or have a direct mapping from source_model row to LogEntry.
                # For now, let's assume the order corresponds.
                try:
                    log_entry = self.log_entries[source_index.row()] # Get LogEntry from original list
                    
                    # Apply export filters (logger name, level)
                    if log_entry.logger_name not in options["loggers"]:
                        continue
                    if log_entry.level not in options["levels"]:
                        continue
                    
                    log_lines_to_export.append(log_entry.raw_line)
                except IndexError:
                    logger.error(f"IndexError while trying to get log entry for export at source row {source_index.row()}. Proxy row {proxy_row}.")
                    continue # Skip problematic entry

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for line in log_lines_to_export:
                    f.write(line + "\n")
            
            QMessageBox.information(self, "Export Successful", f"Successfully exported {len(log_lines_to_export)} log entries to:\n{file_path}")
            self.status_bar.showMessage(f"Exported {len(log_lines_to_export)} entries.", 5000)
            logger.info(f"Exported {len(log_lines_to_export)} log entries to {file_path} with options: {options}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export logs:\n{e}")
            logger.error(f"Error exporting logs to {file_path}: {e}", exc_info=True)

    def _on_color_settings_changed(self):
        """Handles updates when color settings are changed and applied."""
        logger.info("Color settings changed, reloading delegate colors and repainting table.")
        if hasattr(self, 'color_delegate') and self.color_delegate:
            self.color_delegate.load_colors() # Reload colors in the delegate
            self.log_table_view.viewport().update() # Force repaint
        else:
            logger.warning("Color delegate not found, cannot update colors.")

if __name__ == '__main__': # Basic test
    # This is for testing the MainWindow of the log viewer directly
    # For the full game, run_log_viewer.py is the entry point
    from core.utils.logging_config import setup_logging
    setup_logging()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())