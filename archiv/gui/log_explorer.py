# gui/log_explorer.py

import json
import os
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QPushButton, QTextEdit, QComboBox, QCheckBox, QSplitter, QMenu, QFileDialog,
    QApplication, QMessageBox
)
from PySide6.QtGui import QFont, QColor, QTextCursor, QAction
from PySide6.QtCore import Qt, Signal, Slot, QTimer

from core.utils.logging_config import LoggingConfig, LogCategory

class LogExplorer(QDialog):
    """Log Explorer dialog for viewing and searching logs by category"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Explorer")
        
        # Load saved dimensions
        self.load_saved_dimensions()
        
        self.setup_ui()
        self.load_logs()
        
        # Initialize log file tracking for detecting changes
        self.log_file_sizes = {}
        self.update_log_file_sizes()
        
        # Check for new logs every 2 seconds, but only refresh if auto-refresh is enabled
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.check_for_new_logs)
        self.refresh_timer.start(2000)
        
        # Mark setup as complete to enable dimension saving
        self.setup_complete = True
    def load_saved_dimensions(self):
        """Load saved dialog dimensions from game settings"""
        try:
            # Get project root directory to locate settings file
            project_root = Path(__file__).parent.parent
            settings_path = project_root / "config" / "game_settings.json"
            
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                
                # Check if log explorer dimensions are saved
                if "log_explorer" in settings and "size" in settings["log_explorer"]:
                    size = settings["log_explorer"]["size"]
                    width = size.get("width", 900)
                    height = size.get("height", 600)
                    self.resize(width, height)
                    
                    # Also restore other settings if available
                    if "auto_refresh" in settings["log_explorer"]:
                        self.auto_refresh_default = settings["log_explorer"]["auto_refresh"]
                    if "show_timestamps" in settings["log_explorer"]:
                        self.show_timestamps_default = settings["log_explorer"]["show_timestamps"]
                else:
                    # Use default size
                    self.resize(900, 600)
            else:
                self.resize(900, 600)
        except Exception as e:
            print(f"Error loading saved dimensions: {e}")
            self.resize(900, 600)
    
    def save_dimensions(self):
        """Save current dialog dimensions and settings to game_settings.json"""
        try:
            # Get project root directory
            project_root = Path(__file__).parent.parent
            settings_path = project_root / "config" / "game_settings.json"
            
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                
                # Create log_explorer section if it doesn't exist
                if "log_explorer" not in settings:
                    settings["log_explorer"] = {}
                
                # Save current size and settings
                settings["log_explorer"]["size"] = {
                    "width": self.width(),
                    "height": self.height()
                }
                
                # Save auto-refresh and timestamps settings
                if hasattr(self, 'auto_refresh'):
                    settings["log_explorer"]["auto_refresh"] = self.auto_refresh.isChecked()
                if hasattr(self, 'show_timestamps'):
                    settings["log_explorer"]["show_timestamps"] = self.show_timestamps.isChecked()
                
                # Write updated settings
                with open(settings_path, 'w') as f:
                    json.dump(settings, f, indent=2)
                    
        except Exception as e:
            print(f"Error saving log explorer settings: {e}")
                
    def resizeEvent(self, event):
        """Handle resize event to save dimensions"""
        super().resizeEvent(event)
        # Don't save during initialization
        if hasattr(self, 'setup_complete') and self.setup_complete:
            self.save_dimensions()
    
    def setup_ui(self):
        """Set up the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Top controls
        top_layout = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search logs...")
        self.search_input.textChanged.connect(self.filter_logs)
        
        self.category_combo = QComboBox(self)
        self.category_combo.addItem("All Categories")
        for category in LogCategory:
            self.category_combo.addItem(category.name)
        self.category_combo.currentIndexChanged.connect(self.filter_logs)
        
        self.level_combo = QComboBox(self)
        self.level_combo.addItems(["All Levels", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.currentIndexChanged.connect(self.filter_logs)
        
        clear_btn = QPushButton("Clear", self)
        clear_btn.clicked.connect(lambda: [self.search_input.clear(), self.filter_logs()])
        clear_btn.setToolTip("Clear search terms")
        
        refresh_btn = QPushButton("Refresh", self)
        refresh_btn.clicked.connect(self.refresh_logs_preserving_state)
        refresh_btn.setToolTip("Manually refresh logs")
        
        export_btn = QPushButton("Export", self)
        export_btn.clicked.connect(self.export_logs)
        export_btn.setToolTip("Export filtered logs to a file")
        
        # Add Clear Logs button
        clear_logs_btn = QPushButton("Clear Logs", self)
        clear_logs_btn.clicked.connect(self.clear_all_logs)
        clear_logs_btn.setToolTip("Delete all log files (this cannot be undone)")
        
        top_layout.addWidget(QLabel("Search:"))
        top_layout.addWidget(self.search_input, 3)
        top_layout.addWidget(clear_btn)
        top_layout.addWidget(QLabel("Category:"))
        top_layout.addWidget(self.category_combo, 1)
        top_layout.addWidget(QLabel("Level:"))
        top_layout.addWidget(self.level_combo, 1)
        top_layout.addWidget(refresh_btn)
        top_layout.addWidget(export_btn)
        top_layout.addWidget(clear_logs_btn)  # Add the clear logs button
        
        main_layout.addLayout(top_layout)
        
        # Rest of your existing UI setup code...
        # Splitter for tree and content views
        splitter = QSplitter(Qt.Horizontal)
        
        # Tree view for logs
        self.log_tree = QTreeWidget(self)
        self.log_tree.setHeaderLabels(["Logs"])
        self.log_tree.setColumnCount(1)
        self.log_tree.setAlternatingRowColors(True)
        self.log_tree.setUniformRowHeights(True)
        self.log_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.log_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # Enable multi-selection by default
        self.log_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        
        # Content view
        self.log_content = QTextEdit(self)
        self.log_content.setReadOnly(True)
        self.log_content.setFont(QFont("Courier", 10))
        
        splitter.addWidget(self.log_tree)
        splitter.addWidget(self.log_content)
        splitter.setSizes([300, 600])
        
        main_layout.addWidget(splitter, 1)  # 1 is the stretch factor
        
        # Status bar with checkboxes
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        check_layout = QHBoxLayout()
        
        # Auto-refresh checkbox
        self.auto_refresh = QCheckBox("Auto Refresh", self)
        self.auto_refresh.setChecked(getattr(self, 'auto_refresh_default', True))
        self.auto_refresh.setToolTip("Automatically refresh when new log entries are detected")
        check_layout.addWidget(self.auto_refresh)
        
        self.auto_scroll = QCheckBox("Auto-scroll", self)
        self.auto_scroll.setChecked(True)
        self.auto_scroll.setToolTip("Automatically scroll to the newest entries when viewing logs")
        check_layout.addWidget(self.auto_scroll)
        
        self.show_timestamps = QCheckBox("Show Timestamps", self)
        self.show_timestamps.setChecked(getattr(self, 'show_timestamps_default', True))
        self.show_timestamps.setToolTip("Show or hide timestamps in log entries")
        self.show_timestamps.stateChanged.connect(self.filter_logs)
        check_layout.addWidget(self.show_timestamps)
        
        # Delete selected logs button
        delete_selected_btn = QPushButton("Delete Selected", self)
        delete_selected_btn.clicked.connect(self.delete_selected_logs)
        delete_selected_btn.setToolTip("Delete selected log entries (this cannot be undone)")
        check_layout.addWidget(delete_selected_btn)
        
        status_layout.addLayout(check_layout)
        
        main_layout.addLayout(status_layout)

    def clear_all_logs(self):
        """Delete all log files after confirmation"""
        reply = QMessageBox.question(
            self, 
            "Clear All Logs", 
            "Are you sure you want to delete ALL log files? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        logger = LoggingConfig.get_logger(__name__, LogCategory.SYSTEM)
        
        # Get all log files
        log_files = LoggingConfig.get_log_files()
        
        deleted_count = 0
        for log_file in log_files:
            try:
                log_file.unlink()  # Delete the file
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting log file {log_file}: {e}")
        
        # Refresh the log explorer
        self.log_tree.clear()
        self.log_content.clear()
        
        # Update status
        self.status_label.setText(f"Deleted {deleted_count} log files")
        
        # Create a new empty log file for each category to avoid errors
        try:
            project_root = Path(__file__).parent.parent
            logs_dir = project_root / 'logs'
            
            # Create basic log files
            for category in LogCategory:
                log_path = logs_dir / f"{category.name.lower()}.log"
                with open(log_path, 'w') as f:
                    f.write(f"# New log file created at {datetime.now().isoformat()}\n")
        except Exception as e:
            logger.error(f"Error creating new log files: {e}")
        
        # Refresh to show the new empty log files
        self.refresh_logs_preserving_state()

    def delete_selected_logs(self):
        """Delete selected log entries"""
        selected_items = self.log_tree.selectedItems()
        
        if not selected_items:
            QMessageBox.information(self, "Delete Selected", "No log entries selected")
            return
        
        # Count entries and determine if they are categories or individual entries
        category_items = []
        entry_items = []
        
        for item in selected_items:
            # Check if it's a category item (top-level) or entry item (child)
            if item.parent() is None:
                category_items.append(item)
            else:
                entry_items.append(item)
        
        # Build confirmation message
        message = "Are you sure you want to delete:\n"
        if category_items:
            message += f"- {len(category_items)} log categories\n"
        if entry_items:
            message += f"- {len(entry_items)} individual log entries\n"
        message += "\nThis action cannot be undone."
        
        reply = QMessageBox.question(
            self, 
            "Delete Selected Logs", 
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        logger = LoggingConfig.get_logger(__name__, LogCategory.SYSTEM)
        
        # Process category deletions (more complex)
        if category_items:
            for category_item in category_items:
                category_name = category_item.data(0, Qt.UserRole)
                
                # Find and delete the corresponding log file
                try:
                    project_root = Path(__file__).parent.parent
                    log_path = project_root / 'logs' / f"{category_name.lower()}.log"
                    
                    if log_path.exists():
                        # Create a backup before deleting
                        backup_path = log_path.with_suffix(f".log.bak")
                        import shutil
                        shutil.copy2(log_path, backup_path)
                        
                        # Create a new empty file
                        with open(log_path, 'w') as f:
                            f.write(f"# Log file cleared at {datetime.now().isoformat()}\n")
                        
                        logger.info(f"Cleared log file for category: {category_name}")
                    
                except Exception as e:
                    logger.error(f"Error clearing log file for category {category_name}: {e}")
        
        # Process individual entry deletions
        # Note: This is more complex and would require rewriting log files
        # We'll implement a simplified version that removes the entries from the tree view
        if entry_items:
            for entry_item in entry_items:
                parent = entry_item.parent()
                if parent:
                    parent.removeChild(entry_item)
            
            logger.info(f"Removed {len(entry_items)} entries from view (note: they remain in log files)")
            
            # Update the status message
            self.status_label.setText(f"Removed {len(entry_items)} entries from view")
        
        # Refresh the view
        self.filter_logs()    
        
    def update_log_file_sizes(self):
        """Update the dictionary of log file sizes to detect changes"""
        log_files = LoggingConfig.get_log_files()
        
        for log_file in log_files:
            try:
                file_size = log_file.stat().st_size
                self.log_file_sizes[str(log_file)] = file_size
            except Exception:
                pass
    
    def check_for_new_logs(self):
        """Check if any log files have changed and refresh if needed"""
        if not self.auto_refresh.isChecked():
            return
        
        log_files = LoggingConfig.get_log_files()
        found_new_logs = False
        
        for log_file in log_files:
            try:
                file_path = str(log_file)
                current_size = log_file.stat().st_size
                previous_size = self.log_file_sizes.get(file_path, 0)
                
                if current_size > previous_size:
                    found_new_logs = True
                    break
            except Exception:
                pass
        
        if found_new_logs:
            self.refresh_logs_preserving_state()
    
    def refresh_logs_preserving_state(self):
        """Refresh logs while preserving selection and expansion state"""
        # Save current selection
        selected_items = self.log_tree.selectedItems()
        selected_data = None
        if selected_items:
            selected_data = selected_items[0].data(0, Qt.UserRole)
        
        # Save expansion state of categories
        expansion_state = {}
        for i in range(self.log_tree.topLevelItemCount()):
            category_item = self.log_tree.topLevelItem(i)
            category_name = category_item.data(0, Qt.UserRole)
            expansion_state[category_name] = category_item.isExpanded()
        
        # Remember scroll position in content view
        content_scroll_value = self.log_content.verticalScrollBar().value()
        
        # Reload logs
        self.load_logs()
        
        # Restore expansion state
        for i in range(self.log_tree.topLevelItemCount()):
            category_item = self.log_tree.topLevelItem(i)
            category_name = category_item.data(0, Qt.UserRole)
            if category_name in expansion_state:
                category_item.setExpanded(expansion_state[category_name])
        
        # Restore selection if possible
        if selected_data:
            self.restore_selection(selected_data)
        
        # Restore content scroll position if not auto-scrolling
        if not self.auto_scroll.isChecked():
            self.log_content.verticalScrollBar().setValue(content_scroll_value)
        
        # Update log file sizes for change detection
        self.update_log_file_sizes()

    def restore_selection(self, selected_data):
        """Restore the selection in the tree view"""
        # If it was a category
        if selected_data in [cat.name for cat in LogCategory] or selected_data == "UNCATEGORIZED":
            for i in range(self.log_tree.topLevelItemCount()):
                category_item = self.log_tree.topLevelItem(i)
                if category_item.data(0, Qt.UserRole) == selected_data:
                    self.log_tree.setCurrentItem(category_item)
                    return
        
        # If it was a log entry, search all children of all categories
        for i in range(self.log_tree.topLevelItemCount()):
            category_item = self.log_tree.topLevelItem(i)
            for j in range(category_item.childCount()):
                entry_item = category_item.child(j)
                if entry_item.data(0, Qt.UserRole) == selected_data:
                    self.log_tree.setCurrentItem(entry_item)
                    return
    
    def load_logs(self):
        """Load logs from all log files"""
        # Save current selection and expansion state before clearing
        selected_items = self.log_tree.selectedItems()
        selected_data = None
        if selected_items:
            selected_data = selected_items[0].data(0, Qt.UserRole)
        
        # Save expansion state
        expansion_state = {}
        for i in range(self.log_tree.topLevelItemCount()):
            category_item = self.log_tree.topLevelItem(i)
            category_name = category_item.data(0, Qt.UserRole)
            expansion_state[category_name] = category_item.isExpanded()
        
        # Clear the tree
        self.log_tree.clear()
        
        # Create category items
        category_items = {}
        for category in LogCategory:
            item = QTreeWidgetItem(self.log_tree, [category.name])
            item.setData(0, Qt.UserRole, category.name)
            category_items[category.name] = item
            
            # Add a special font and color based on category
            item.setForeground(0, self.get_category_color(category))
            font = self.log_tree.font()
            font.setBold(True)
            item.setFont(0, font)
            
            # Store reference to make log entries children of this category
            category_items[category.name] = item
        
        # Add an "UNCATEGORIZED" item for logs without a category
        uncategorized_item = QTreeWidgetItem(self.log_tree, ["UNCATEGORIZED"])
        uncategorized_item.setData(0, Qt.UserRole, "UNCATEGORIZED")
        category_items["UNCATEGORIZED"] = uncategorized_item
        
        # Get log files
        log_files = LoggingConfig.get_log_files()
        if not log_files:
            self.status_label.setText("No log files found")
            return
        
        # Parse log entries and add to tree
        total_entries = 0
        error_count = 0
        file_error_count = 0
        
        for log_file in log_files:
            try:
                content = LoggingConfig.read_log_file(log_file)
                lines = content.splitlines()
                
                # Process each line
                current_entry = ""
                current_category = None
                
                for line in lines:
                    # If line starts with a timestamp, it's a new log entry
                    if re.match(r'\d{4}-\d{2}-\d{2}', line):
                        # Process previous entry if any
                        if current_entry and current_category:
                            self.add_log_entry(current_entry, current_category, category_items)
                            total_entries += 1
                            
                            # Check if it's an error entry
                            if " ERROR " in current_entry or " CRITICAL " in current_entry:
                                error_count += 1
                        
                        # Start new entry
                        current_entry = line
                        parsed = LoggingConfig.parse_log_entry(line)
                        current_category = parsed['category'] if parsed else "UNCATEGORIZED"
                    else:
                        # Continuation of previous entry
                        current_entry += "\n" + line
                
                # Add the last entry
                if current_entry and current_category:
                    self.add_log_entry(current_entry, current_category, category_items)
                    total_entries += 1
                    
                    # Check if it's an error entry
                    if " ERROR " in current_entry or " CRITICAL " in current_entry:
                        error_count += 1
                    
            except Exception as e:
                print(f"Error processing log file {log_file}: {e}")
                file_error_count += 1
        
        # Restore expansion state where possible
        for category_name, was_expanded in expansion_state.items():
            for i in range(self.log_tree.topLevelItemCount()):
                item = self.log_tree.topLevelItem(i)
                if item.data(0, Qt.UserRole) == category_name:
                    item.setExpanded(was_expanded)
                    break
        
        # Update status
        self.status_label.setText(f"Loaded {total_entries} log entries from {len(log_files)} files. Errors: {error_count}, File processing errors: {file_error_count}")
        
        # Filter logs based on current search/filter settings
        self.filter_logs()
        
        # Restore selection if possible
        if selected_data:
            self.restore_selection(selected_data)
        
        # Update log file sizes for change detection
        self.update_log_file_sizes()
    
    def add_log_entry(self, entry, category, category_items):
        """Add a log entry to the tree under the appropriate category"""
        # Parse the entry to extract components
        parsed = LoggingConfig.parse_log_entry(entry.split('\n')[0])
        if not parsed:
            # If parsing fails, add under UNCATEGORIZED
            category = "UNCATEGORIZED"
            display_text = entry.split('\n')[0][:80]
        else:
            # Use parsed components for display
            timestamp = parsed['timestamp']
            level = parsed['level']
            message = parsed['message']
            display_text = f"{timestamp} [{level}] {message[:80]}"
            if len(message) > 80:
                display_text += "..."
        
        # Find parent category item
        parent_item = category_items.get(category)
        if not parent_item:
            parent_item = category_items["UNCATEGORIZED"]
        
        # Create tree item
        item = QTreeWidgetItem(parent_item, [display_text])
        item.setData(0, Qt.UserRole, entry)
        
        # Style based on level
        if parsed and parsed['level']:
            level = parsed['level']
            if level == "ERROR" or level == "CRITICAL":
                item.setForeground(0, QColor("red"))
            elif level == "WARNING":
                item.setForeground(0, QColor("orange"))
        
        return item
    
    def on_tree_item_clicked(self, item, column):
        """Display the content of the selected log entry"""
        entry_data = item.data(0, Qt.UserRole)
        
        # If it's a category, show all entries in that category
        if entry_data in [cat.name for cat in LogCategory] or entry_data == "UNCATEGORIZED":
            # Collect all child entries
            entries = []
            for i in range(item.childCount()):
                child = item.child(i)
                if not child.isHidden():  # Only include visible entries
                    child_data = child.data(0, Qt.UserRole)
                    if child_data and child_data not in [cat.name for cat in LogCategory]:
                        entries.append(child_data)
            
            # Display all entries
            content = "\n\n".join(entries)
            
            # Apply timestamp filter if needed
            if not self.show_timestamps.isChecked():
                lines = content.split('\n')
                processed_lines = []
                for line in lines:
                    if re.match(r'\d{4}-\d{2}-\d{2}', line):
                        # If line starts with a timestamp, remove the timestamp part
                        parts = line.split(' - ', 1)
                        if len(parts) > 1:
                            processed_lines.append(parts[1])
                        else:
                            processed_lines.append(line)
                    else:
                        processed_lines.append(line)
                content = '\n'.join(processed_lines)
            
            self.log_content.setText(content)
            self.highlight_search_terms()
            
            # Auto-scroll to end if enabled
            if self.auto_scroll.isChecked():
                cursor = self.log_content.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.log_content.setTextCursor(cursor)
        else:
            # Display individual entry
            content = entry_data
            
            # Apply timestamp filter if needed
            if not self.show_timestamps.isChecked():
                lines = content.split('\n')
                processed_lines = []
                for line in lines:
                    if re.match(r'\d{4}-\d{2}-\d{2}', line):
                        # If line starts with a timestamp, remove the timestamp part
                        parts = line.split(' - ', 1)
                        if len(parts) > 1:
                            processed_lines.append(parts[1])
                        else:
                            processed_lines.append(line)
                    else:
                        processed_lines.append(line)
                content = '\n'.join(processed_lines)
            
            self.log_content.setText(content)
            self.highlight_search_terms()
    
    def filter_logs(self):
        """Filter log entries based on search term, category, and level"""
        search_term = self.search_input.text().lower()
        selected_category = self.category_combo.currentText()
        selected_level = self.level_combo.currentText()
        show_timestamps = self.show_timestamps.isChecked()
        
        # Helper function to check if an entry matches filters
        def matches_filters(entry_text, item_category):
            # Check category filter
            if selected_category != "All Categories" and item_category != selected_category:
                return False
            
            # Check if entry contains search term
            if search_term and search_term not in entry_text.lower():
                return False
            
            # Check log level
            if selected_level != "All Levels":
                level_pattern = fr'\[(INFO|DEBUG|WARNING|ERROR|CRITICAL)\]'
                level_match = re.search(level_pattern, entry_text)
                if not level_match or level_match.group(1) != selected_level:
                    return False
            
            return True
        
        # Process all category items
        for i in range(self.log_tree.topLevelItemCount()):
            category_item = self.log_tree.topLevelItem(i)
            category_name = category_item.data(0, Qt.UserRole)
            
            # Check if category should be visible based on filters
            category_visible = (selected_category == "All Categories" or 
                            selected_category == category_name)
            
            # Count matching entries in this category
            matching_count = 0
            
            # Process all entries in this category
            for j in range(category_item.childCount()):
                entry_item = category_item.child(j)
                entry_text = entry_item.data(0, Qt.UserRole)
                
                # Check if entry matches filters
                if matches_filters(entry_text, category_name):
                    entry_item.setHidden(False)
                    matching_count += 1
                    
                    # Update display text based on show_timestamps setting
                    original_display = entry_item.text(0)
                    
                    # Only update if we need to (either adding or removing timestamp)
                    if (not show_timestamps and re.match(r'\d{4}-\d{2}-\d{2}', original_display)) or \
                    (show_timestamps and not re.match(r'\d{4}-\d{2}-\d{2}', original_display)):
                        
                        # Parse the original entry
                        parsed = LoggingConfig.parse_log_entry(entry_text.split('\n')[0])
                        if parsed:
                            if show_timestamps:
                                # Add timestamp back
                                timestamp = parsed['timestamp']
                                level = parsed['level']
                                message = parsed['message']
                                display_text = f"{timestamp} [{level}] {message[:80]}"
                                if len(message) > 80:
                                    display_text += "..."
                                entry_item.setText(0, display_text)
                            else:
                                # Remove timestamp
                                level = parsed['level']
                                message = parsed['message']
                                display_text = f"[{level}] {message[:80]}"
                                if len(message) > 80:
                                    display_text += "..."
                                entry_item.setText(0, display_text)
                else:
                    entry_item.setHidden(True)
            
            # Hide category if no entries match or category filter excludes it
            category_item.setHidden(not category_visible or matching_count == 0)
            
            # Update category item text to show count
            category_item.setText(0, f"{category_name} ({matching_count})")
        
        # Update content view if there's a selection
        selected_items = self.log_tree.selectedItems()
        if selected_items:
            self.on_tree_item_clicked(selected_items[0], 0)
        else:
            # Just highlight search terms in content view
            self.highlight_search_terms()
    
    def highlight_search_terms(self):
        """Highlight search terms in the content view"""
        search_term = self.search_input.text()
        if not search_term:
            return
        
        # Store current position
        cursor = self.log_content.textCursor()
        current_position = cursor.position()
        
        # Reset text format
        self.log_content.selectAll()
        format = self.log_content.currentCharFormat()
        format.setBackground(self.log_content.palette().base())
        format.setForeground(self.log_content.palette().text())
        self.log_content.setCurrentCharFormat(format)
        
        # Restore position
        cursor.setPosition(current_position)
        self.log_content.setTextCursor(cursor)
        
        # Find and highlight all occurrences
        cursor = self.log_content.textCursor()
        cursor.movePosition(QTextCursor.Start)
        
        highlight_format = self.log_content.currentCharFormat()
        highlight_format.setBackground(QColor("yellow"))
        highlight_format.setForeground(QColor("black"))
        
        # Set cursor and format
        self.log_content.setTextCursor(cursor)
        
        while True:
            # The search method returns True if found, False otherwise
            found = self.log_content.find(search_term)
            if not found:
                break
            
            # Get the cursor after finding the text
            cursor = self.log_content.textCursor()
            
            # Apply format to the found text
            cursor.mergeCharFormat(highlight_format)
        
        # Reset cursor to start for better readability
        cursor = self.log_content.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.log_content.setTextCursor(cursor)
        
        # If auto-scroll is enabled, scroll to the end
        if self.auto_scroll.isChecked():
            cursor = self.log_content.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_content.setTextCursor(cursor)
    
    def get_category_color(self, category):
        """Get color for a specific log category"""
        colors = {
            LogCategory.GAME: QColor(64, 128, 255),       # Blue
            LogCategory.LLM: QColor(191, 64, 191),        # Purple
            LogCategory.AGENT: QColor(64, 191, 191),      # Teal
            LogCategory.GUI: QColor(64, 191, 64),         # Green
            LogCategory.SAVE: QColor(191, 191, 64),       # Yellow
            LogCategory.CONTEXT: QColor(191, 64, 64),     # Red
            LogCategory.MUSIC: QColor(128, 128, 128),     # Gray
            LogCategory.CONFIG: QColor(128, 64, 0),       # Brown
            LogCategory.SYSTEM: QColor(0, 0, 0),          # Black
            LogCategory.NETWORK: QColor(0, 64, 128),      # Navy
            LogCategory.DEBUG: QColor(128, 128, 191),     # Light purple
            LogCategory.UNCATEGORIZED: QColor(128, 128, 128)  # Gray
        }
        return colors.get(category, QColor(0, 0, 0))
    
    def show_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.log_tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # Add actions
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(lambda: self.copy_log_entry(item))
        menu.addAction(copy_action)
        
        if item.parent():  # If it's a log entry (not a category)
            show_action = QAction("Show Details", self)
            show_action.triggered.connect(lambda: self.on_tree_item_clicked(item, 0))
            menu.addAction(show_action)
        else:  # It's a category
            expand_action = QAction("Expand All", self)
            expand_action.triggered.connect(lambda: item.setExpanded(True))
            menu.addAction(expand_action)
            
            collapse_action = QAction("Collapse", self)
            collapse_action.triggered.connect(lambda: item.setExpanded(False))
            menu.addAction(collapse_action)
        
        menu.exec_(self.log_tree.viewport().mapToGlobal(position))
    
    def copy_log_entry(self, item):
        """Copy log entry to clipboard"""
        entry_data = item.data(0, Qt.UserRole)
        QApplication.clipboard().setText(entry_data)
        self.status_label.setText("Log entry copied to clipboard")
    
    def export_logs(self):
        """Export filtered logs to a file"""
        # Get filtered logs
        filtered_logs = []
        
        for i in range(self.log_tree.topLevelItemCount()):
            category_item = self.log_tree.topLevelItem(i)
            if category_item.isHidden():
                continue
            
            for j in range(category_item.childCount()):
                entry_item = category_item.child(j)
                if entry_item.isHidden():
                    continue
                
                entry_text = entry_item.data(0, Qt.UserRole)
                filtered_logs.append(entry_text)
        
        if not filtered_logs:
            self.status_label.setText("No logs to export")
            return
        
        # Ask for save location
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", "", "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(filtered_logs))
            
            self.status_label.setText(f"Exported {len(filtered_logs)} log entries to {file_path}")
        except Exception as e:
            self.status_label.setText(f"Error exporting logs: {str(e)}")
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        self.refresh_timer.stop()
        self.save_dimensions()
        super().closeEvent(event)