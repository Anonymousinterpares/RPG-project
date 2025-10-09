# gui/advanced_config_editor/advanced_config_editor.py
"""
Advanced configuration editor for the RPG Project.
"""
import os
import json
from pathlib import Path
from datetime import datetime
import shutil
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTreeWidget, QTreeWidgetItem, QPushButton, QStackedWidget,
    QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt

from core.utils.logging_config import LoggingConfig, LogCategory
from .schemas import RACE_SCHEMA, PATH_SCHEMA, BACKGROUND_SCHEMA, validate_entry
from .entry_editor import EntryEditorDialog
from .versioning import backup_file
from .custom_widgets import AutoResizingPlainTextEdit
from .form_views import (
    create_races_form_tab,
    create_paths_form_tab,
    create_world_settings_form_tab,
    create_scenarios_form_tab,
    create_items_form_tab
)

class AdvancedConfigEditor(QDialog):
    """
    Advanced configuration editor for managing game data.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
       
        self.logger = LoggingConfig.get_logger(__name__, LogCategory.SYSTEM)
        self.setWindowTitle("Advanced Configuration Editor")
        self.resize(800, 600)
        self.layout = QVBoxLayout(self)

        # Add a migration button for scenarios at the top
        migration_layout = QHBoxLayout()
        migration_btn = QPushButton("Fix Scenario-Background Links", self)
        migration_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        migration_btn.setToolTip("Run migration to ensure all scenarios have proper background links")
        migration_btn.clicked.connect(self.run_scenario_migration)
        migration_layout.addWidget(migration_btn)
        migration_layout.addStretch()
        self.layout.addLayout(migration_layout)

        # Store reference to custom_widgets module for form views
        self.custom_widgets = type('CustomWidgetsModule', (), {'AutoResizingPlainTextEdit': AutoResizingPlainTextEdit})

        # Add view mode toggle buttons at the top
        view_layout = QHBoxLayout()
        self.btn_json_view = QPushButton("JSON View", self)
        self.btn_form_view = QPushButton("Form View", self)
        self.btn_form_view.setChecked(True)
        self.btn_form_view.setCheckable(True)
        self.btn_json_view.setChecked(True)  # Default to JSON view
        view_layout.addWidget(self.btn_json_view)
        view_layout.addWidget(self.btn_form_view)
        view_layout.addStretch()
        self.layout.addLayout(view_layout)
        
        # Create stacked widget to switch between views
        self.view_stack = QStackedWidget(self)
        self.layout.addWidget(self.view_stack)
        
        # JSON view (tree and editor)
        self.json_view = QWidget(self)
        json_layout = QVBoxLayout(self.json_view)
        
        self.tree = QTreeWidget(self.json_view)
        self.tree.setHeaderLabels(["Configuration Entries"])
        json_layout.addWidget(self.tree)
        
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_edit = QPushButton("Edit")
        self.btn_remove = QPushButton("Remove")
        self.btn_reload = QPushButton("Reload")
        self.btn_version = QPushButton("Version History")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_reload)
        btn_layout.addWidget(self.btn_version)
        json_layout.addLayout(btn_layout)
        
        # Form view
        self.form_view = QWidget(self)
        form_layout = QVBoxLayout(self.form_view)
        self.form_tabs = QTabWidget(self.form_view)
        form_layout.addWidget(self.form_tabs)
        
        # Add views to stack
        self.view_stack.addWidget(self.json_view)
        self.view_stack.addWidget(self.form_view)
        
        # Connect view toggle buttons
        self.btn_json_view.clicked.connect(lambda: self.switch_view(0))
        self.btn_form_view.clicked.connect(lambda: self.switch_view(1))
        
        self.config_files = {
            "Races": "config/game_races.json",
            "Paths": "config/world/characters/paths.json",
            "Backgrounds": "config/world/characters/backgrounds",
            "WorldHistory": "config/world/base/world_history.json", 
            "FundamentalRules": "config/world/base/fundamental_rules.json", 
            "Cultures": "config/world/base/cultures.json", 
            "StartingScenarios": "config/world/scenarios/starting_scenarios.json"
        }
        
        self.data = {
            "Races": {},
            "Paths": {},
            "Backgrounds": {},
            "WorldHistory": {},
            "FundamentalRules": {},
            "Cultures": {},
            "StartingScenarios": {}
        }
        
        # Set default view to form view
        self.view_stack.setCurrentIndex(1)
        
        # Load data and populate UI
        self.load_configurations()
        self.populate_tree()
        self._create_form_view_tabs()
       
        # Connect buttons
        self.btn_reload.clicked.connect(self.reload_configurations)
        self.btn_add.clicked.connect(self.add_entry)
        self.btn_edit.clicked.connect(self.edit_entry)
        self.btn_remove.clicked.connect(self.remove_entry)
        self.btn_version.clicked.connect(self.show_version_history)

    def run_scenario_migration(self):
        """Run migration to link scenarios with backgrounds"""
        try:
            # Create a temporary WorldConfigLoader
            from core.utils.world_config_loader import WorldConfigLoader
            
            config_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).parent / "config"
            
            config_loader = WorldConfigLoader(config_dir)
            
            # Track whether anything changed
            changed = False
            
            # First, load the scenarios
            scenarios_data = self.data.get("StartingScenarios", {})
            if not scenarios_data or "paths" not in scenarios_data:
                QMessageBox.warning(self, "Migration Failed", "No valid starting scenarios found.")
                return
                
            # For each path
            for path_key, path_data in scenarios_data["paths"].items():
                if "scenarios" not in path_data:
                    continue
                    
                # Get backgrounds for this path from the normal path config
                paths_data = self.data.get("Paths", {})
                path_entry = paths_data.get(path_key, {})
                
                bg_keys = []
                # Check for backgrounds in the path entry
                if "backgrounds" in path_entry and isinstance(path_entry["backgrounds"], dict):
                    bg_keys = list(path_entry["backgrounds"].keys())
                
                # For each scenario
                for scenario_key, scenario in path_data["scenarios"].items():
                    # Check if applicable_backgrounds is missing or empty
                    if "applicable_backgrounds" not in scenario or not scenario["applicable_backgrounds"]:
                        # Add all backgrounds for this path
                        scenario["applicable_backgrounds"] = bg_keys
                        changed = True
                        self.logger.info(f"Added {len(bg_keys)} backgrounds to scenario '{scenario_key}' in path '{path_key}'")
            
            if changed:
                # Save the updated config
                self.save_category("StartingScenarios")
                
                # Reload and refresh UI
                self.load_configurations()
                self.populate_tree()
                self._create_form_view_tabs()
                
                QMessageBox.information(self, "Migration Complete", 
                    "Starting scenarios have been updated to include applicable backgrounds. "
                    "This allows proper linking between paths, backgrounds, and scenarios.")
            else:
                QMessageBox.information(self, "No Changes", 
                    "All scenarios already have applicable backgrounds. No changes needed.")
                    
        except Exception as e:
            self.logger.error(f"Error during scenario migration: {e}")
            QMessageBox.critical(self, "Migration Error", 
                f"An error occurred during scenario migration: {str(e)}")

    def load_configurations(self):
        """Load all configuration files."""
        # Load Races
        races_file = self.config_files["Races"]
        if os.path.exists(races_file):
            try:
                with open(races_file, "r", encoding="utf-8") as f:
                    races_json = json.load(f)
                if "races" in races_json:
                    self.data["Races"] = races_json["races"]
                else:
                    self.data["Races"] = races_json
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading Races: {e}")
                self.data["Races"] = {}
        else:
            self.data["Races"] = {}

        # Load Paths
        paths_file = self.config_files["Paths"]
        if os.path.exists(paths_file):
            try:
                with open(paths_file, "r", encoding="utf-8") as f:
                    paths_json = json.load(f)
                if "paths" in paths_json:
                    self.data["Paths"] = paths_json["paths"]
                else:
                    self.data["Paths"] = paths_json
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading Paths: {e}")
                self.data["Paths"] = {}
        else:
            self.data["Paths"] = {}

        # Load Backgrounds from folder
        backgrounds_folder = self.config_files["Backgrounds"]
        self.data["Backgrounds"] = {}
        if os.path.isdir(backgrounds_folder):
            for filename in os.listdir(backgrounds_folder):
                if filename.endswith(".json"):
                    filepath = os.path.join(backgrounds_folder, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            entry = json.load(f)
                        # If file has a top-level "backgrounds" key, iterate its items
                        if "backgrounds" in entry and isinstance(entry["backgrounds"], dict):
                            for bg_key, bg_entry in entry["backgrounds"].items():
                                self.data["Backgrounds"][bg_key] = bg_entry
                                # Also merge into parent Path if "path" property is set
                                path_prop = bg_entry.get("path", "").lower()
                                if path_prop and path_prop in self.data["Paths"]:
                                    parent_entry = self.data["Paths"].get(path_prop)
                                    if "backgrounds" not in parent_entry:
                                        parent_entry["backgrounds"] = {}
                                    parent_entry["backgrounds"][bg_key] = bg_entry
                        else:
                            bg_key = os.path.splitext(filename)[0]
                            self.data["Backgrounds"][bg_key] = entry
                            path_prop = entry.get("path", "").lower()
                            if path_prop and path_prop in self.data["Paths"]:
                                parent_entry = self.data["Paths"].get(path_prop)
                                if "backgrounds" not in parent_entry:
                                    parent_entry["backgrounds"] = {}
                                parent_entry["backgrounds"][bg_key] = entry
                    except Exception as e:
                        self.logger.error(f"Error loading background {filename}: {e}")
        
        # Load World History
        world_history_file = self.config_files["WorldHistory"]
        if os.path.exists(world_history_file):
            try:
                with open(world_history_file, "r", encoding="utf-8") as f:
                    self.data["WorldHistory"] = json.load(f)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading World History: {e}")
                self.data["WorldHistory"] = {}
        
        # Load Fundamental Rules
        rules_file = self.config_files["FundamentalRules"]
        if os.path.exists(rules_file):
            try:
                with open(rules_file, "r", encoding="utf-8") as f:
                    self.data["FundamentalRules"] = json.load(f)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading Fundamental Rules: {e}")
                self.data["FundamentalRules"] = {}
        
        # Load Cultures
        cultures_file = self.config_files["Cultures"]
        if os.path.exists(cultures_file):
            try:
                with open(cultures_file, "r", encoding="utf-8") as f:
                    self.data["Cultures"] = json.load(f)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading Cultures: {e}")
                self.data["Cultures"] = {}
        
        # Load Starting Scenarios
        scenarios_file = self.config_files["StartingScenarios"]
        if os.path.exists(scenarios_file):
            try:
                with open(scenarios_file, "r", encoding="utf-8") as f:
                    self.data["StartingScenarios"] = json.load(f)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading Starting Scenarios: {e}")
                self.data["StartingScenarios"] = {}

    def populate_tree(self):
        """Populate the tree with entries"""
        self.tree.clear()
        
        # Top-level nodes: Races, Paths, World Settings
        races_item = QTreeWidgetItem(self.tree, ["Races"])
        races_item.setData(0, Qt.UserRole, "RacesCategory")  # Add data to identify this as category
        
        paths_item = QTreeWidgetItem(self.tree, ["Paths"])
        paths_item.setData(0, Qt.UserRole, "PathsCategory")
        
        world_item = QTreeWidgetItem(self.tree, ["World Settings"])
        world_item.setData(0, Qt.UserRole, "WorldCategory")
        
        # Add races
        for key, entry in self.data["Races"].items():
            text = entry.get("name", key)
            item = QTreeWidgetItem(races_item, [text])
            item.setData(0, Qt.UserRole, ("Race", key))

        # Add paths and backgrounds
        for path_key, path_entry in self.data["Paths"].items():
            text = path_entry.get("name", path_key)
            path_item = QTreeWidgetItem(paths_item, [text])
            path_item.setData(0, Qt.UserRole, ("Path", path_key))
            if "backgrounds" in path_entry and isinstance(path_entry["backgrounds"], dict):
                for bg_key, bg_entry in path_entry["backgrounds"].items():
                    bg_text = bg_entry.get("name", bg_key)
                    bg_item = QTreeWidgetItem(path_item, [bg_text])
                    bg_item.setData(0, Qt.UserRole, ("Background", path_key, bg_key))
        
        # Add world history
        history_item = QTreeWidgetItem(world_item, ["World History"])
        history_item.setData(0, Qt.UserRole, "WorldHistoryCategory")
        self._add_json_structure(history_item, self.data["WorldHistory"], "WorldHistory")
        
        # Add fundamental rules
        rules_item = QTreeWidgetItem(world_item, ["Fundamental Rules"])
        rules_item.setData(0, Qt.UserRole, "FundamentalRulesCategory")
        self._add_json_structure(rules_item, self.data["FundamentalRules"], "FundamentalRules")
        
        # Add cultures
        cultures_item = QTreeWidgetItem(world_item, ["Cultures"])
        cultures_item.setData(0, Qt.UserRole, "CulturesCategory")
        self._add_json_structure(cultures_item, self.data["Cultures"], "Cultures")
        
        # Add starting scenarios
        scenarios_item = QTreeWidgetItem(world_item, ["Starting Scenarios"])
        scenarios_item.setData(0, Qt.UserRole, "StartingScenariosCategory")
        if "paths" in self.data["StartingScenarios"]:
            for path_key, path_data in self.data["StartingScenarios"]["paths"].items():
                path_scenarios = QTreeWidgetItem(scenarios_item, [path_data.get("name", path_key)])
                path_scenarios.setData(0, Qt.UserRole, ("ScenarioPath", path_key))
                
                if "scenarios" in path_data:
                    for scenario_key, scenario in path_data["scenarios"].items():
                        scenario_item = QTreeWidgetItem(path_scenarios, [scenario.get("name", scenario_key)])
                        scenario_item.setData(0, Qt.UserRole, ("Scenario", path_key, scenario_key))

    def _add_json_structure(self, parent_item, data, prefix, depth=0, max_depth=2):
        """Recursively add JSON structure to tree"""
        if depth >= max_depth:
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ["name", "description"]:  # Skip common metadata fields
                    continue
                    
                display_name = key.replace("_", " ").title()
                item = QTreeWidgetItem(parent_item, [display_name])
                # Store path to this data element for editing
                item.setData(0, Qt.UserRole, (f"{prefix}.{key}" if prefix else key, key))
                
                if isinstance(value, (dict, list)) and depth < max_depth - 1:
                    self._add_json_structure(item, value, f"{prefix}.{key}", depth + 1, max_depth)
        
        elif isinstance(data, list) and len(data) > 0:
            # For lists, add numbered entries
            for i, item_value in enumerate(data[:5]):  # Limit to 5 items for readability
                if isinstance(item_value, dict) and "name" in item_value:
                    display_name = f"[{i}] {item_value['name']}"
                else:
                    display_name = f"Item {i+1}"
                    
                item = QTreeWidgetItem(parent_item, [display_name])
                item.setData(0, Qt.UserRole, (f"{prefix}[{i}]", i))
                
                if isinstance(item_value, (dict, list)) and depth < max_depth - 1:
                    self._add_json_structure(item, item_value, f"{prefix}[{i}]", depth + 1, max_depth)
            
            if len(data) > 5:
                more_item = QTreeWidgetItem(parent_item, [f"... {len(data) - 5} more items"])
                more_item.setDisabled(True)

    def _create_form_view_tabs(self):
        """Create all form view tabs"""
        try:
            # Clear existing tabs
            self.form_tabs.clear()
            
            # Create races tab
            races_tab = create_races_form_tab(self, self.data["Races"], self.save_category)
            self.form_tabs.addTab(races_tab, "Races")
            
            # Create paths tab
            paths_tab = create_paths_form_tab(self, self.data["Paths"], self.data["Backgrounds"], self.save_category)
            self.form_tabs.addTab(paths_tab, "Paths")
            
            # Create world settings tab
            world_tab = create_world_settings_form_tab(self, self.data, self.save_category)
            self.form_tabs.addTab(world_tab, "World Settings")
            
            # Create scenarios tab
            scenarios_tab = create_scenarios_form_tab(self, self.data["StartingScenarios"], self.save_category)
            self.form_tabs.addTab(scenarios_tab, "Starting Scenarios")
            
            # Create items tab
            items_tab = create_items_form_tab(self, self.save_category)
            self.form_tabs.addTab(items_tab, "Items")
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error creating form tabs: {e}")
            traceback.print_exc()
            # Add an error tab to show the problem
            error_tab = QWidget()
            error_layout = QVBoxLayout(error_tab)
            error_text = AutoResizingPlainTextEdit()
            error_text.setPlainText(f"Error creating form view: {str(e)}\n\n{traceback.format_exc()}")
            error_text.setReadOnly(True)
            error_layout.addWidget(error_text)
            self.form_tabs.addTab(error_tab, "Error")

    def switch_view(self, index):
        """Switch between JSON and Form views"""
        if index == 0:  # JSON View
            self.btn_json_view.setChecked(True)
            self.btn_form_view.setChecked(False)
            self.view_stack.setCurrentIndex(0)
        else:  # Form View
            self.btn_json_view.setChecked(False)
            self.btn_form_view.setChecked(True)
            self.view_stack.setCurrentIndex(1)
            # Update form view with latest data
            self._create_form_view_tabs()
            
    def reload_configurations(self):
        """Reload all configurations from files."""
        self.load_configurations()
        self.populate_tree()
        QMessageBox.information(self, "Reload", "Configuration reloaded successfully.")

    def add_entry(self):
        """Add a new entry to the configuration."""
        selected = self.tree.currentItem()
        entry_type = None
        parent_key = None
        
        # Check if a category is selected
        if selected is not None:
            # Get the data or category name from the selected item
            data = selected.data(0, Qt.UserRole)
            
            # Handle special category identifiers
            if isinstance(data, str):
                if data == "RacesCategory":
                    entry_type = "Race"
                elif data == "PathsCategory":
                    entry_type = "Path"
                # Handle more categories as needed
        
        # If no specific type determined yet, ask the user
        if entry_type is None:
            if selected is None or selected.parent() is None:
                items = ["Race", "Path"]
                type_selected, ok = QInputDialog.getItem(self, "Select Type", "Select the type of entry to add:", items, 0, False)
                if not ok:
                    return
                entry_type = type_selected
            else:
                data = selected.data(0, Qt.UserRole)
                if isinstance(data, tuple):
                    if data[0] == "Path":
                        items = ["Path", "Background"]
                        type_selected, ok = QInputDialog.getItem(self, "Select Type", "Add new Path or new Background for this path:", items, 1, False)
                        if not ok:
                            return
                        entry_type = type_selected
                        if entry_type == "Background":
                            parent_key = data[1]
                    elif data[0] == "Background":
                        entry_type = "Background"
                        parent_key = data[1]
                    elif data[0] == "Race":
                        entry_type = "Race"
                elif data is None:
                    label = selected.text(0)
                    if label == "Races":
                        entry_type = "Race"
                    elif label == "Paths":
                        entry_type = "Path"
                    
        editor = EntryEditorDialog(entry_type, parent=self)
        if editor.exec() == QDialog.Accepted:
            new_entry = editor.get_entry_data()
            valid, msg = True, "Valid"
            if entry_type == "Race":
                valid, msg = validate_entry(new_entry, RACE_SCHEMA)
                file_key = "Races"
            elif entry_type == "Path":
                valid, msg = validate_entry(new_entry, PATH_SCHEMA)
                file_key = "Paths"
            elif entry_type == "Background":
                valid, msg = validate_entry(new_entry, BACKGROUND_SCHEMA)
                file_key = "Paths"  # Backgrounds will be nested inside Paths.
            if not valid:
                QMessageBox.critical(self, "Validation Error", msg)
                return
            key = new_entry.get("name", "").replace(" ", "_").lower()
            if entry_type == "Background":
                if parent_key is None:
                    QMessageBox.critical(self, "Error", "No parent path selected for background entry.")
                    return
                parent_entry = self.data["Paths"].get(parent_key)
                if parent_entry is None:
                    QMessageBox.critical(self, "Error", "Parent path not found.")
                    return
                if "backgrounds" not in parent_entry:
                    parent_entry["backgrounds"] = {}
                if key in parent_entry["backgrounds"]:
                    QMessageBox.warning(self, "Duplicate", f"A background with key '{key}' already exists under this path.")
                    return
                new_entry["path"] = parent_key
                parent_entry["backgrounds"][key] = new_entry
                self.data["Backgrounds"][key] = new_entry
            else:
                if key in self.data[file_key]:
                    QMessageBox.warning(self, "Duplicate", f"An entry with key '{key}' already exists.")
                    return
                self.data[file_key][key] = new_entry
            self.save_category("Paths" if entry_type in ["Path", "Background"] else "Races")
            self.populate_tree()
            QMessageBox.information(self, "Added", f"{entry_type} added successfully.")
            if entry_type == "Path":
                reply = QMessageBox.question(self, "Add Background", "Do you want to add a background for this path now?",
                                            QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    bg_editor = EntryEditorDialog("Background", parent=self)
                    if bg_editor.exec() == QDialog.Accepted:
                        new_bg = bg_editor.get_entry_data()
                        new_bg["path"] = key
                        path_entry = self.data["Paths"].get(key)
                        if "backgrounds" not in path_entry:
                            path_entry["backgrounds"] = {}
                        bg_key = new_bg.get("name", "").replace(" ", "_").lower()
                        path_entry["backgrounds"][bg_key] = new_bg
                        self.data["Backgrounds"][bg_key] = new_bg
                        self.save_category("Paths")
                        self.populate_tree()
                        QMessageBox.information(self, "Added", "Background added successfully.")

    def edit_entry(self):
        """Edit an existing entry."""
        selected = self.tree.currentItem()
        if selected is None or selected.parent() is None:
            QMessageBox.warning(self, "Select Entry", "Please select a valid entry (not a category header).")
            return
        data = selected.data(0, Qt.UserRole)
        if data is None:
            QMessageBox.warning(self, "Select Entry", "Please select a valid entry (not a category header).")
            return
        if data[0] == "Path":
            entry_type = "Path"
            key = data[1]
            file_key = "Paths"
            entry = self.data[file_key].get(key)
        elif data[0] == "Background":
            entry_type = "Background"
            parent_key = data[1]
            background_key = data[2]
            file_key = "Paths"
            parent_entry = self.data[file_key].get(parent_key)
            if parent_entry is None or "backgrounds" not in parent_entry:
                QMessageBox.critical(self, "Error", "Parent path or backgrounds not found.")
                return
            entry = parent_entry["backgrounds"].get(background_key)
            key = background_key
        elif data[0] == "Race":
            entry_type = "Race"
            key = data[1]
            file_key = "Races"
            entry = self.data[file_key].get(key)
        else:
            QMessageBox.warning(self, "Select Entry", "Unknown entry type.")
            return
        if entry is None:
            if entry_type == "Background":
                entry = {}
            else:
                QMessageBox.critical(self, "Error", "Selected entry not found.")
                return
        if entry_type == "Background" and "name" not in entry:
            entry["name"] = key
        editor = EntryEditorDialog(entry_type, entry, parent=self)
        if editor.exec() == QDialog.Accepted:
            updated_entry = editor.get_entry_data()
            valid, msg = True, "Valid"
            if entry_type == "Race":
                valid, msg = validate_entry(updated_entry, RACE_SCHEMA)
            elif entry_type == "Path":
                valid, msg = validate_entry(updated_entry, PATH_SCHEMA)
            elif entry_type == "Background":
                valid, msg = validate_entry(updated_entry, BACKGROUND_SCHEMA)
            if not valid:
                QMessageBox.critical(self, "Validation Error", msg)
                return
            if entry_type != "Background":
                backup_file(self.config_files[file_key])
                self.data[file_key][key] = updated_entry
            else:
                parent_entry = self.data["Paths"].get(parent_key)
                if parent_entry is None or "backgrounds" not in parent_entry:
                    QMessageBox.critical(self, "Error", "Parent path not found.")
                    return
                parent_entry["backgrounds"][key] = updated_entry
                self.data["Backgrounds"][key] = updated_entry
            self.save_category("Paths" if entry_type in ["Path", "Background"] else "Races")
            self.populate_tree()
            QMessageBox.information(self, "Updated", f"{entry_type} updated successfully.")

    def remove_entry(self):
        """Remove an existing entry."""
        selected = self.tree.currentItem()
        if selected is None or selected.parent() is None:
            QMessageBox.warning(self, "Select Entry", "Please select a valid entry (not a category header).")
            return
        data = selected.data(0, Qt.UserRole)
        if data is None:
            QMessageBox.warning(self, "Select Entry", "Please select a valid entry (not a category header).")
            return
        entry_type = data[0]
        if entry_type == "Path":
            key = data[1]
            reply = QMessageBox.question(self, "Confirm Removal", "Are you sure you want to remove this Path?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                if key in self.data["Paths"]:
                    del self.data["Paths"][key]
                    self.save_category("Paths")
                    self.populate_tree()
                    QMessageBox.information(self, "Removed", "Path removed successfully.")
        elif entry_type == "Background":
            parent_key = data[1]
            background_key = data[2]
            reply = QMessageBox.question(self, "Confirm Removal", "Are you sure you want to remove this Background?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                parent_entry = self.data["Paths"].get(parent_key)
                if parent_entry is None or "backgrounds" not in parent_entry:
                    QMessageBox.critical(self, "Error", "Parent path not found.")
                    return
                if background_key in parent_entry["backgrounds"]:
                    del parent_entry["backgrounds"][background_key]
                if background_key in self.data["Backgrounds"]:
                    del self.data["Backgrounds"][background_key]
                self.save_category("Paths")
                self.populate_tree()
                QMessageBox.information(self, "Removed", "Background removed successfully.")
        elif entry_type == "Race":
            key = data[1]
            reply = QMessageBox.question(self, "Confirm Removal", "Are you sure you want to remove this Race?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                if key in self.data["Races"]:
                    del self.data["Races"][key]
                    self.save_category("Races")
                    self.populate_tree()
                    QMessageBox.information(self, "Removed", "Race removed successfully.")

    def save_category(self, category):
        """Save a category to its corresponding file."""
        if category in ["Races", "Paths"]:
            filepath = self.config_files[category]
            try:
                backup_file(filepath)
                with open(filepath, "w", encoding="utf-8") as f:
                    if category == "Paths":
                        json.dump({"paths": self.data["Paths"]}, f, indent=2)
                    elif category == "Races":
                        try:
                            filepath = self.config_files["Races"]
                            
                            # Make sure the directory exists
                            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                            
                            # Backup existing file
                            backup_file(filepath)
                            
                            # Save the file
                            with open(filepath, "w", encoding="utf-8") as f:
                                json.dump({"races": self.data["Races"]}, f, indent=2)
                                
                            self.logger.info(f"Saved Races to {filepath}")
                            return True
                        except Exception as e:
                            QMessageBox.critical(self, "Error", f"Failed to save Races: {e}")
                            return False
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save {category}: {e}")
            
            # For each path, update the corresponding backgrounds file
            if category == "Paths":
                for path_key, path_entry in self.data["Paths"].items():
                    if "backgrounds_file" in path_entry and "backgrounds" in path_entry:
                        # Use only the base name from backgrounds_file
                        bg_filename = os.path.basename(path_entry["backgrounds_file"])
                        bg_filepath = os.path.join(self.config_files["Backgrounds"], bg_filename)
                        # Ensure the backgrounds folder exists
                        if not os.path.isdir(self.config_files["Backgrounds"]):
                            os.makedirs(self.config_files["Backgrounds"])
                        try:
                            backup_file(bg_filepath)
                            with open(bg_filepath, "w", encoding="utf-8") as f:
                                json.dump({"backgrounds": path_entry["backgrounds"]}, f, indent=2)
                        except Exception as e:
                            QMessageBox.critical(self, "Error", f"Failed to save backgrounds for path {path_key}: {e}")
        
        # Save world settings files
        elif category == "WorldHistory":
            try:
                backup_file(self.config_files["WorldHistory"])
                with open(self.config_files["WorldHistory"], "w", encoding="utf-8") as f:
                    json.dump(self.data["WorldHistory"], f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save World History: {e}")
        
        elif category == "FundamentalRules":
            try:
                backup_file(self.config_files["FundamentalRules"])
                with open(self.config_files["FundamentalRules"], "w", encoding="utf-8") as f:
                    json.dump(self.data["FundamentalRules"], f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save Fundamental Rules: {e}")
        
        elif category == "Cultures":
            try:
                backup_file(self.config_files["Cultures"])
                with open(self.config_files["Cultures"], "w", encoding="utf-8") as f:
                    json.dump(self.data["Cultures"], f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save Cultures: {e}")
        
        elif category == "StartingScenarios":
            try:
                backup_file(self.config_files["StartingScenarios"])
                with open(self.config_files["StartingScenarios"], "w", encoding="utf-8") as f:
                    json.dump(self.data["StartingScenarios"], f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save Starting Scenarios: {e}")

    def show_version_history(self):
        """Show version history and allow reverting to previous versions."""
        backup_folder = "config/backups"
        if not os.path.exists(backup_folder):
            QMessageBox.information(self, "Version History", "No backups found.")
            return
        files = os.listdir(backup_folder)
        if not files:
            QMessageBox.information(self, "Version History", "No backups found.")
            return
        # Present a list to allow reverting.
        file_selected, ok = QInputDialog.getItem(self, "Version History", "Select a backup to revert to:", files, 0, False)
        if ok and file_selected:
            reply = QMessageBox.question(self, "Confirm Revert", f"Revert changes using backup {file_selected}?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                backup_path = os.path.join(backup_folder, file_selected)
                # For simplicity, ask which file to revert.
                orig_file, ok2 = QInputDialog.getText(self, "Revert Backup", "Enter the original file name (e.g., paths.json):")
                if ok2 and orig_file:
                    orig_path = os.path.join(os.path.dirname(self.config_files.get("Paths", "")), orig_file)
                    try:
                        shutil.copy2(backup_path, orig_path)
                        QMessageBox.information(self, "Reverted", f"Reverted to backup {file_selected} successfully.")
                        self.reload_configurations()
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to revert backup: {e}")

    # Helper for new game loading: returns a list of background names for a given path.
    def get_backgrounds_for_path(self, path_key) -> List[str]:
        """Get available backgrounds for a path."""
        path_entry = self.data["Paths"].get(path_key)
        if path_entry and "backgrounds" in path_entry:
            return [bg_entry.get("name", k) for k, bg_entry in path_entry["backgrounds"].items()]
        return []

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    editor = AdvancedConfigEditor()
    editor.exec()