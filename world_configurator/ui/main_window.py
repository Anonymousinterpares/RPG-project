"""
Main window for the World Configurator Tool.
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, Tuple

import json
from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QMenuBar, QMenu,
    QToolBar, QFileDialog, QMessageBox, QDialog,
    QStatusBar, QLabel, QSplitter, QTextEdit, QComboBox
)
from PySide6.QtGui import QIcon, QCloseEvent, QAction, QFont

# Corrected import path assumption (models likely in a subfolder)
from models.world_config import WorldConfigManager
from utils.file_manager import get_project_root, get_world_config_dir, load_json

from .editors.culture_editor import CultureEditor
from .editors.location_editor import LocationEditor
from .editors.history_editor import HistoryEditor
# Renamed import
from .editors.origin_editor import OriginEditor
from .editors.quest_editor import QuestEditor
from .editors.magic_systems_editor import MagicSystemsEditor
from .editors.names_editor import NamesEditor
from .editors.class_editor import ClassEditor
from .editors.race_editor import RaceEditor
# Removed BackgroundEditor import
# from .editors.background_editor import BackgroundEditor

from .dialogs.new_project_dialog import NewProjectDialog
from .dialogs.export_dialog import ExportDialog
from .dialogs.settings_dialog import SettingsDialog

logger = logging.getLogger("world_configurator.ui.main_window")

class MainWindow(QMainWindow):
    """Main window for the World Configurator Tool."""

    # Signals
    project_loaded = Signal(str)  # Project path
    project_saved = Signal(str)  # Project path

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        # Initialize world config manager
        self.world_config = WorldConfigManager()

        # Set up UI
        self.setup_ui()

        # Set up actions
        self.setup_actions()

        # Set up menus
        self.setup_menus()

        # Set up toolbar
        self.setup_toolbar()

        # Set up status bar
        self.setup_status_bar()

        # Load settings
        self.load_settings()

        # Set window title
        self.update_window_title()

        logger.info("Main window initialized")

        # Show welcome information
        self.show_welcome_info()

    def show_welcome_info(self):
        """Show welcome information to help users get started."""
        QMessageBox.information(
            self,
            "Welcome to World Configurator",
            "Welcome to the World Configurator Tool!\n\n"
            "Currently, the following editors are fully implemented:\n"
            "- Cultures: Create and edit cultures\n"
            "- Races: Create and edit races\n" # Added
            "- Classes: Create and edit classes\n" # Added
            "- Locations: Create and edit locations\n"
            "- World History: Create and edit historical eras and events\n"
            "- Origins: Create and edit starting origins (scenarios)\n" # Updated
            "- Quests: Create and edit quests and objectives\n"
            "- Magic Systems: Create and edit magic systems\n\n" # Added
            "To edit your existing game data, use the 'File > Load from Game' option.\n"
            "This will load your existing JSON files from your game's configuration directory.\n\n"
            "When you export your changes, backup copies of your original files\n"
            "will be automatically created with timestamped filenames in a 'backup' folder."
        )

    def setup_ui(self):
        """Set up the UI components."""
        # Set window properties
        self.setWindowTitle("World Configurator")
        self.setMinimumSize(1000, 700)

        # Create main layout and central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        # Create splitter for resizable panels
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.main_splitter)

        # Create tab widget for editors
        self.tab_widget = QTabWidget()
        self.main_splitter.addWidget(self.tab_widget)

        # Create editor widgets
        self.create_editor_tabs()

        # Assistant dock
        from assistant.panel import AssistantDock
        self.assistant_dock = AssistantDock(self, get_provider_cb=self._get_active_assistant_provider)
        self.addDockWidget(Qt.RightDockWidgetArea, self.assistant_dock)

        logger.debug("UI components set up")

    def create_editor_tabs(self):
        """Create tabs for the different editors."""
        # Culture editor
        self.culture_editor = CultureEditor()
        self.culture_editor.set_culture_manager(self.world_config.culture_manager)
        self.tab_widget.addTab(self.culture_editor, "Cultures")

        # Race editor
        self.race_editor = RaceEditor()
        self.race_editor.set_race_manager(self.world_config.race_manager)
        self.tab_widget.addTab(self.race_editor, "Races")

        # Class editor
        self.class_editor = ClassEditor()
        self.class_editor.set_class_manager(self.world_config.class_manager)
        self.tab_widget.addTab(self.class_editor, "Classes")

        # Skills editor - NEW
        from .editors.skills_editor import SkillsEditor # Local import
        self.skills_editor = SkillsEditor()
        # self.skills_editor.set_skill_manager(self.world_config.skill_manager) # Assuming skill_manager exists or will be added
        self.tab_widget.addTab(self.skills_editor, "Skills")

        # Items editor panel - NEW
        from .editors.item_editor_panel import ItemEditorPanel # Local import
        self.item_editor_panel = ItemEditorPanel()
        # self.item_editor_panel.set_item_managers(...) # If it needs access to managers
        self.tab_widget.addTab(self.item_editor_panel, "Items")

        # Location editor
        self.location_editor = LocationEditor()
        self.location_editor.set_managers(
            self.world_config.location_manager,
            self.world_config.culture_manager,
            self.world_config.location_defaults_manager
        )
        self.tab_widget.addTab(self.location_editor, "Locations")

        # History editor
        self.history_editor = HistoryEditor()
        self.history_editor.set_managers(
            self.world_config.history_manager,
            self.world_config.culture_manager,
            self.world_config.location_manager
        )
        self.tab_widget.addTab(self.history_editor, "World History")

        # Origin editor
        self.origin_editor = OriginEditor()
        self.origin_editor.set_managers(
            self.world_config.origin_manager,
            self.world_config.location_manager,
            self.world_config.quest_manager
            # Potentially pass skill manager/data source here if needed for selection dialogs
            # self.world_config.skill_manager 
        )
        self.tab_widget.addTab(self.origin_editor, "Origins")

        # Quest editor
        self.quest_editor = QuestEditor()
        self.quest_editor.set_managers(
            self.world_config.quest_manager,
            self.world_config.location_manager
        )
        self.tab_widget.addTab(self.quest_editor, "Quests")

        # Magic Systems editor
        self.magic_systems_editor = MagicSystemsEditor()
        self.magic_systems_editor.set_magic_system_manager(self.world_config.magic_system_manager)
        self.tab_widget.addTab(self.magic_systems_editor, "Magic Systems")

        # Names editor (npc/names.json)
        self.names_editor = NamesEditor()
        self.names_editor.set_manager(self.world_config.names_manager)
        self.tab_widget.addTab(self.names_editor, "Names")
        
        # Variants editor (npc/variants.json)
        from .editors.variants_editor import VariantsEditor
        self.variants_editor = VariantsEditor()
        self.variants_editor.set_manager(self.world_config.variants_manager)
        self.tab_widget.addTab(self.variants_editor, "NPC Variants")

        # Connect modified signals
        self.culture_editor.culture_modified.connect(self.on_data_modified)
        self.race_editor.race_modified.connect(self.on_data_modified)
        self.class_editor.class_modified.connect(self.on_data_modified)
        self.skills_editor.skills_modified.connect(self.on_data_modified) # NEW
        self.item_editor_panel.item_data_modified.connect(self.on_data_modified) # NEW
        self.location_editor.location_modified.connect(self.on_data_modified)
        self.history_editor.history_modified.connect(self.on_data_modified)
        self.origin_editor.origin_modified.connect(self.on_data_modified)
        self.quest_editor.quest_modified.connect(self.on_data_modified)
        self.magic_systems_editor.magic_system_modified.connect(self.on_data_modified)
        if hasattr(self, 'names_editor'):
            self.names_editor.names_modified.connect(self.on_data_modified)
        if hasattr(self, 'variants_editor'):
            self.variants_editor.variants_modified.connect(self.on_data_modified)

        logger.debug("Editor tabs created")
    def setup_actions(self):
        """Set up actions for the main window."""
        # File actions
        self.action_new = QAction(QIcon.fromTheme("document-new", QIcon(os.path.join(get_project_root(), "world_configurator/ui/icons/new.png"))), "New Project", self)
        self.action_new.setShortcut("Ctrl+N")
        self.action_new.triggered.connect(self.on_new_project)

        self.action_open = QAction(QIcon.fromTheme("document-open", QIcon(os.path.join(get_project_root(), "world_configurator/ui/icons/open.png"))), "Open Project", self)
        self.action_open.setShortcut("Ctrl+O")
        self.action_open.triggered.connect(self.on_open_project)

        self.action_load_from_game = QAction(QIcon.fromTheme("document-import", QIcon(os.path.join(get_project_root(), "world_configurator/ui/icons/import.png"))), "Load from Game", self)
        self.action_load_from_game.setShortcut("Ctrl+L")
        self.action_load_from_game.triggered.connect(self.on_load_from_game)

        self.action_save = QAction(QIcon.fromTheme("document-save", QIcon(os.path.join(get_project_root(), "world_configurator/ui/icons/save.png"))), "Save", self)
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.triggered.connect(self.on_save_project)

        self.action_save_as = QAction(QIcon.fromTheme("document-save-as"), "Save As...", self)
        self.action_save_as.setShortcut("Ctrl+Shift+S")
        self.action_save_as.triggered.connect(self.on_save_project_as)

        self.action_export = QAction(QIcon.fromTheme("document-export", QIcon(os.path.join(get_project_root(), "world_configurator/ui/icons/export.png"))), "Export to Game", self)
        self.action_export.setShortcut("Ctrl+E")
        self.action_export.triggered.connect(self.on_export_to_game)

        self.action_exit = QAction(QIcon.fromTheme("application-exit"), "Exit", self)
        self.action_exit.setShortcut("Alt+F4")
        self.action_exit.triggered.connect(self.close)

        # Edit actions
        self.action_settings = QAction(QIcon.fromTheme("preferences-system"), "Settings", self)
        self.action_settings.triggered.connect(self.on_settings)

        self.action_view_json = QAction(QIcon.fromTheme("text-x-generic"), "View JSON Data", self)
        self.action_view_json.setShortcut("Ctrl+J")
        self.action_view_json.triggered.connect(self.on_view_json)

        # Help actions
        self.action_about = QAction(QIcon.fromTheme("help-about"), "About", self)
        self.action_about.triggered.connect(self.on_about)

        logger.debug("Actions set up")

    def setup_menus(self):
        """Set up the application menus."""
        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)

        # File menu
        self.menu_file = self.menu_bar.addMenu("File")
        self.menu_file.addAction(self.action_new)
        self.menu_file.addAction(self.action_open)
        self.menu_file.addAction(self.action_load_from_game)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_save)
        self.menu_file.addAction(self.action_save_as)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_export)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)

        # Edit menu
        self.menu_edit = self.menu_bar.addMenu("Edit")
        self.menu_edit.addAction(self.action_settings)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.action_view_json)

        # Help menu
        self.menu_help = self.menu_bar.addMenu("Help")
        self.menu_help.addAction(self.action_about)

        # Tools menu
        self.menu_tools = self.menu_bar.addMenu("Tools")
        self.action_validate_origins_quests = QAction("Validate Origins ↔ Quests", self)
        self.action_validate_origins_quests.triggered.connect(self.on_validate_origins_quests)
        self.menu_tools.addAction(self.action_validate_origins_quests)

        logger.debug("Menus set up")

    def setup_toolbar(self):
        """Set up the application toolbar."""
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(self.toolbar)

        # Add actions to toolbar
        self.toolbar.addAction(self.action_new)
        self.toolbar.addAction(self.action_open)
        self.toolbar.addAction(self.action_save)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_export)

        logger.debug("Toolbar set up")

    def setup_status_bar(self):
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add status labels
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)

        self.project_label = QLabel("No project loaded")
        self.status_bar.addPermanentWidget(self.project_label)

        logger.debug("Status bar set up")

    def _get_active_assistant_provider(self):
        """Return the current tab widget if it implements the assistant context provider interface."""
        try:
            w = self.tab_widget.currentWidget()
            # duck-typing check for required methods
            needed = [
                hasattr(w, "get_assistant_context"),
                hasattr(w, "apply_assistant_patch"),
                hasattr(w, "get_domain_examples"),
                hasattr(w, "get_reference_catalogs"),
                hasattr(w, "create_entry_from_llm"),
            ]
            return w if all(needed) else None
        except Exception:
            return None

    def load_settings(self):
        """Load application settings."""
        # TODO: Implement settings loading
        logger.debug("Settings loaded")

    def save_settings(self):
        """Save application settings."""
        # TODO: Implement settings saving
        logger.debug("Settings saved")

    def update_window_title(self):
        """Update the window title with the current project name."""
        if self.world_config.state.path:
            modified_indicator = "*" if self.world_config.state.modified else ""
            self.setWindowTitle(f"World Configurator - {self.world_config.project_name}{modified_indicator}")
        else:
            self.setWindowTitle("World Configurator")

        # Update project label in status bar
        if self.world_config.state.path:
            self.project_label.setText(self.world_config.project_name)
        else:
            self.project_label.setText("No project loaded")

    def update_ui_from_model(self):
        """Update UI components with data from the model."""
        # Update editors
        self.culture_editor._refresh_culture_list()
        self.race_editor._refresh_race_list()
        self.class_editor._refresh_class_list()
        if hasattr(self, 'skills_editor'): # Check if skills_editor exists
            self.skills_editor.refresh_data()
        if hasattr(self, 'item_editor_panel'): # Check if item_editor_panel exists
            self.item_editor_panel.refresh_current_editor() # Or a more general refresh

        self.location_editor._refresh_location_list()
        self.location_editor._populate_culture_combo()
        self.history_editor.refresh()
        self.origin_editor.refresh()
        self.quest_editor.refresh()
        self.magic_systems_editor._refresh_system_list()
        if hasattr(self, 'names_editor'):
            self.names_editor.refresh()
        if hasattr(self, 'variants_editor'):
            self.variants_editor.refresh()

        # Update window title
        self.update_window_title()

        # Show data overview
        self._show_data_overview()

        logger.debug("UI updated from model")

    def _show_data_overview(self):
        """Show an overview of the data that has been loaded."""
        loaded_items = []

        if self.world_config.culture_manager.cultures:
            loaded_items.append(f"{len(self.world_config.culture_manager.cultures)} cultures")
        if self.world_config.race_manager.races:
            loaded_items.append(f"{len(self.world_config.race_manager.races)} races")
        if self.world_config.class_manager.classes:
            loaded_items.append(f"{len(self.world_config.class_manager.classes)} classes")
        
        # Skills - check if editor exists and has data
        if hasattr(self, 'skills_editor') and self.skills_editor.skills_data:
            loaded_items.append(f"{len(self.skills_editor.skills_data)} skills")

        # Items - for items, it's more complex as it's per category.
        # For now, just indicate if the item panel is present.
        # A more detailed count would require iterating through ITEM_CATEGORIES and loading each file.
        if hasattr(self, 'item_editor_panel'):
            loaded_items.append("Item categories available")


        if self.world_config.location_manager.locations:
            loaded_items.append(f"{len(self.world_config.location_manager.locations)} locations")
        if hasattr(self.world_config, 'history_manager') and self.world_config.history_manager.history:
            loaded_items.append("World history")
        if hasattr(self.world_config, 'rules_manager') and self.world_config.rules_manager.rules:
            rule_count = len(self.world_config.rules_manager.rules.rules) if hasattr(self.world_config.rules_manager.rules, 'rules') else 0
            loaded_items.append(f"{rule_count} world rules")
        if hasattr(self.world_config, 'origin_manager') and self.world_config.origin_manager.origins:
            loaded_items.append(f"{len(self.world_config.origin_manager.origins)} origins")
        if hasattr(self.world_config, 'quest_manager') and self.world_config.quest_manager.quests:
            loaded_items.append(f"{len(self.world_config.quest_manager.quests)} quests")
        if hasattr(self.world_config, 'magic_system_manager') and self.world_config.magic_system_manager.magic_systems:
             loaded_items.append(f"{len(self.world_config.magic_system_manager.magic_systems)} magic systems")

        if loaded_items:
            overview = "Loaded: " + ", ".join(loaded_items)
            self.status_label.setText(overview)
        else:
            self.status_label.setText("No data loaded")

            # Show a message about using "Load from Game" if no editors are available
            if self.tab_widget.count() <= 7: # Adjusted count based on actual tabs (Cultures, Races, Classes, Skills, Items, Locations, History, Origins, Quests, Magic) -> 10
                QMessageBox.information(
                    self,
                    "Editor Information",
                    "Some editors might be missing or still under development.\n\n"
                    "Use the 'Load from Game' option to import existing game configuration files."
                )

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        if self.check_unsaved_changes():
            # Save settings
            self.save_settings()
            event.accept()
        else:
            event.ignore()

    def check_unsaved_changes(self) -> bool:
        """
        Check if there are unsaved changes and prompt user to save if needed.

        Returns:
            True if it's safe to continue (changes saved or discarded), False to cancel.
        """
        if self.world_config.state.modified:
            response = QMessageBox.question(
                self,
                "Unsaved Changes",
                "There are unsaved changes. Would you like to save before continuing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if response == QMessageBox.Save:
                return self.on_save_project()
            elif response == QMessageBox.Cancel:
                return False

        return True

    @Slot()
    def on_data_modified(self):
        """Slot to mark the project as modified when an editor signals changes."""
        if not self.world_config.state.modified:
            self.world_config.state.mark_modified()
            self.update_window_title()
            logger.debug("Project marked as modified due to editor changes.")

    @Slot()
    def on_new_project(self) -> bool:
        """
        Handle creating a new project.

        Returns:
            True if a new project was created, False otherwise.
        """
        # Check for unsaved changes
        if not self.check_unsaved_changes():
            return False

        # Show new project dialog
        dialog = NewProjectDialog(self)
        if dialog.exec() == QDialog.Accepted:
            # Create new project
            project_name = dialog.get_project_name()
            self.world_config.new_project(project_name)

            # Update UI
            self.update_ui_from_model()

            # Set status
            self.status_label.setText(f"Created new project: {project_name}")
            logger.info(f"Created new project: {project_name}")

            return True

        return False

    @Slot()
    def on_open_project(self) -> bool:
        """
        Handle opening an existing project.

        Returns:
            True if a project was opened, False otherwise.
        """
        # Check for unsaved changes
        if not self.check_unsaved_changes():
            return False

        # Show file dialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Open Project",
            os.path.join(get_project_root(), "projects")
        )

        if directory:
            # Load project
            if self.world_config.load_project(directory):
                # Update UI
                self.update_ui_from_model()

                # Set status
                self.status_label.setText(f"Opened project: {self.world_config.project_name}")
                logger.info(f"Opened project from {directory}")

                # Emit signal
                self.project_loaded.emit(directory)

                return True
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to open project from {directory}. See log for details."
                )

        return False

    @Slot()
    def on_save_project(self) -> bool:
        """
        Handle saving the current project.

        Returns:
            True if the project was saved, False otherwise.
        """
        # If no path set, prompt for save location
        if not self.world_config.state.path:
            return self.on_save_project_as()

        # Save project
        if self.world_config.save_project():
            # Update UI
            self.update_window_title()

            # Set status
            self.status_label.setText(f"Saved project to {self.world_config.state.path}")
            logger.info(f"Saved project to {self.world_config.state.path}")

            # Emit signal
            self.project_saved.emit(self.world_config.state.path)

            return True
        else:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save project. See log for details."
            )
            return False

    @Slot()
    def on_save_project_as(self) -> bool:
        """
        Handle saving the current project to a new location.

        Returns:
            True if the project was saved, False otherwise.
        """
        # Show file dialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Save Project As",
            os.path.join(get_project_root(), "projects")
        )

        if directory:
            # Save project
            if self.world_config.save_project(directory):
                # Update UI
                self.update_window_title()

                # Set status
                self.status_label.setText(f"Saved project to {directory}")
                logger.info(f"Saved project to {directory}")

                # Emit signal
                self.project_saved.emit(directory)

                return True
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save project to {directory}. See log for details."
                )

        return False

    @Slot()
    def on_export_to_game(self) -> bool:
        """
        Handle exporting the current project to the game.

        Returns:
            True if the project was exported, False otherwise.
        """
        # Confirm with user about potential overwrite
        confirm_response = QMessageBox.question(
            self,
            "Confirm Export",
            "This will export your current project to the game files.\n\n"
            "Existing game files will be automatically backed up with timestamps before being replaced.\n\n"
            "Do you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm_response != QMessageBox.Yes:
            return False

        # Show export dialog
        dialog = ExportDialog(self)


        if dialog.exec() == QDialog.Accepted:
            export_options = dialog.get_export_options()
            selected_components = [comp for comp, selected in export_options.items() if selected]
            logger.info(f"Exporting components: {', '.join(selected_components)}")

            # First, flush any unsaved edits from active item editors to disk
            try:
                if hasattr(self, 'item_editor_panel') and self.item_editor_panel:
                    self.item_editor_panel.save_all_item_editors()
            except Exception:
                logger.warning("Failed to flush item editors before export; proceeding anyway.")

            # Export to game with selected options
            # Assumes WorldConfigManager.export_to_game handles calling manager exports
            success, errors = self.world_config.export_to_game(export_options)

            if success:
                QMessageBox.information(
                    self, "Export Successful",
                    f"Successfully exported: {', '.join(selected_components)}\n\n"
                    "Backups created in respective 'backup' folders."
                )
                self.status_label.setText(f"Exported {len(selected_components)} component(s)")
                logger.info(f"Exported {len(selected_components)} component(s) to game")
                return True
            else:
                error_text = "\n".join(errors)
                QMessageBox.critical(self, "Export Failed", f"Failed to export:\n\n{error_text}")
        return False

    @Slot()
    def on_settings(self):
        """Handle showing the settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()

    @Slot()
    def on_load_from_game(self) -> bool:
        """
        Handle loading data directly from the game's config files.

        Returns:
            True if game data was loaded successfully, False otherwise.
        """
        # Check for unsaved changes
        if not self.check_unsaved_changes():
            return False

        # Confirm with user
        response = QMessageBox.question(
            self,
            "Load from Game",
            "This will load world configuration data directly from the game files. \n\n"
            "Any unsaved changes in the current project will be lost. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if response != QMessageBox.Yes:
            return False

        # Load data from game files
        if self.world_config.synchronize_with_game():
            # Update UI with loaded data
            self.update_ui_from_model()

            # Set status message
            self.status_label.setText("Loaded world configuration from game files")
            self.project_label.setText("Game Files (Unsaved Project)")

            # Update project name
            self.world_config.project_name = "Game Configuration"
            self.update_window_title()

            logger.info("Loaded world configuration from game files")
            return True
        else:
            # Show error message
            QMessageBox.critical(
                self,
                "Error",
                "Failed to load world configuration from game files. \n\n"
                "See log for details."
            )
            return False

    @Slot()
    def on_view_json(self):
        """Handle showing the JSON data view dialog."""
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("View JSON Data")
        dialog.resize(800, 600)

        # Create layout
        layout = QVBoxLayout(dialog)

        # Text display
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Courier New", 10)) # Monospaced font for JSON
        layout.addWidget(text_edit)

        # Get data and set text
        data_type_str, json_str = self._get_current_json_data()
        if data_type_str:
            dialog.setWindowTitle(f"View JSON Data - {data_type_str}")
        text_edit.setText(json_str)

        # Add a refresh button (optional, but can be useful if data changes while dialog is open)
        refresh_button = QPushButton("Refresh Current View")
        def _refresh_view():
            dt_str, j_str = self._get_current_json_data()
            if dt_str: dialog.setWindowTitle(f"View JSON Data - {dt_str}")
            text_edit.setText(j_str)
        refresh_button.clicked.connect(_refresh_view)
        layout.addWidget(refresh_button)


        # Show dialog
        dialog.exec()
        
    @Slot()
    def on_about(self):
        """Handle showing the about dialog."""
        QMessageBox.about(
            self,
            "About World Configurator",
            "World Configurator Tool for the RPG Project\n\n"
            "Version 1.0.1 (Origin Refactor)\n\n" # Updated version
            "A tool for creating and editing world configuration data for the RPG game."
        )

    def _get_current_json_data(self) -> Tuple[Optional[str], str]:
        """
        Gets the JSON data for the currently selected tab or component.
        Helper for on_view_json.

        Returns:
            A tuple (Optional[str], str): The data type string and its JSON representation.
            Returns (None, "No active editor found.") if no suitable editor is active.
        """
        current_tab_widget = self.tab_widget.currentWidget()
        data_type = self.tab_widget.tabText(self.tab_widget.currentIndex())
        json_data_str = "{}"

        try:
            if data_type == "Cultures" and self.world_config.culture_manager:
                data_dict = {k: v.to_dict() for k, v in self.world_config.culture_manager.cultures.items()}
                json_data_str = json.dumps({"cultures": data_dict}, indent=2) if data_dict else "No culture data loaded."
            elif data_type == "Races" and self.world_config.race_manager:
                data_dict = {k: v.to_dict() for k, v in self.world_config.race_manager.races.items()}
                json_data_str = json.dumps({"races": data_dict}, indent=2) if data_dict else "No race data loaded."
            elif data_type == "Classes" and self.world_config.class_manager:
                data_dict = {k: v.to_dict() for k, v in self.world_config.class_manager.classes.items()}
                json_data_str = json.dumps({"classes": data_dict}, indent=2) if data_dict else "No class data loaded."
            elif data_type == "Locations" and self.world_config.location_manager:
                data_dict = {k: v.to_dict() for k, v in self.world_config.location_manager.locations.items()}
                json_data_str = json.dumps({"locations": data_dict}, indent=2) if data_dict else "No location data loaded."
            elif data_type == "World History" and self.world_config.history_manager and self.world_config.history_manager.history:
                json_data_str = json.dumps(self.world_config.history_manager.history.to_dict(), indent=2)
            elif data_type == "Fundamental Rules" and self.world_config.rules_manager and self.world_config.rules_manager.rules:
                json_data_str = json.dumps(self.world_config.rules_manager.rules.to_dict(), indent=2)
            elif data_type == "Origins" and self.world_config.origin_manager:
                data_dict = {k: v.to_dict() for k, v in self.world_config.origin_manager.origins.items()}
                json_data_str = json.dumps({"origins": data_dict}, indent=2) if data_dict else "No origin data loaded."
            elif data_type == "Quests" and self.world_config.quest_manager:
                data_dict = {k: v.to_dict() for k, v in self.world_config.quest_manager.quests.items()}
                json_data_str = json.dumps({"quests": data_dict}, indent=2) if data_dict else "No quest data loaded."
            elif data_type == "Magic Systems" and self.world_config.magic_system_manager:
                data_dict = {k: v.to_dict() for k, v in self.world_config.magic_system_manager.magic_systems.items()}
                json_data_str = json.dumps({"magic_systems": data_dict}, indent=2) if data_dict else "No magic system data loaded."
            elif data_type == "Skills" and hasattr(self, 'skills_editor') and self.skills_editor.skills_data:
                # The skills editor stores skills_data directly as the content of "skills" key
                json_data_str = json.dumps({"skills": self.skills_editor.skills_data}, indent=2)
            elif data_type == "Items" and hasattr(self, 'item_editor_panel'):
                active_item_file_path = self.item_editor_panel.get_active_editor_file_path()
                if active_item_file_path:
                    # Determine project root to construct full path
                    project_root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    full_path = os.path.join(project_root_path, active_item_file_path)
                    if os.path.exists(full_path):
                        loaded_item_data = load_json(full_path) # file_manager.load_json
                        if loaded_item_data is not None:
                            json_data_str = json.dumps(loaded_item_data, indent=2)
                            # Update data_type to be more specific for the JSON view title
                            category_name = self.item_editor_panel.current_category_key or "Items"
                            data_type = f"Items ({category_name})"
                        else:
                            json_data_str = f"Could not load data from: {active_item_file_path}"
                    else:
                        json_data_str = f"File not found: {active_item_file_path}"
                else:
                    json_data_str = "No item category selected in the Items editor."
            elif data_type == "Names" and hasattr(self.world_config, 'names_manager') and self.world_config.names_manager:
                try:
                    data_dict = self.world_config.names_manager.data or {}
                    json_data_str = json.dumps(data_dict, indent=2)
                except Exception as e:
                    json_data_str = f"Error reading names data: {e}"
            elif data_type == "NPC Variants" and hasattr(self.world_config, 'variants_manager') and self.world_config.variants_manager:
                try:
                    data_dict = self.world_config.variants_manager.data or {}
                    json_data_str = json.dumps(data_dict, indent=2)
                except Exception as e:
                    json_data_str = f"Error reading variants data: {e}"
            else:
                return None, "No active editor or data source found for this tab."
        except Exception as e:
            logger.error(f"Error generating JSON view for {data_type}: {e}", exc_info=True)
            return data_type, f"Error generating JSON view: {e}"

        return data_type, json_data_str

    @Slot()
    def on_validate_origins_quests(self):
        """Run the Origins↔Quests validator and display a summary."""
        try:
            from world_configurator.validators.origins_quests_validator import validate as validate_oq
        except Exception:
            try:
                from validators.origins_quests_validator import validate as validate_oq
            except Exception as e:
                QMessageBox.critical(self, "Validator Missing", f"Could not import validator: {e}")
                return
        try:
            origins = {k: v.to_dict() for k, v in self.world_config.origin_manager.origins.items()} if hasattr(self.world_config, 'origin_manager') else {}
            quests = {k: v.to_dict() for k, v in self.world_config.quest_manager.quests.items()} if hasattr(self.world_config, 'quest_manager') else {}
            report = validate_oq(origins, quests)
            ok = report.get('ok', False)
            issues = report.get('issues', [])
            stats = report.get('stats', {})
            summary = f"Valid references: {'Yes' if ok else 'No'}\n" \
                      f"Total refs: {stats.get('total_refs', 0)}\n" \
                      f"Invalid refs: {stats.get('invalid_refs', 0)}\n" \
                      f"Duplicates: {stats.get('duplicates', 0)}\n\n"
            if issues:
                summary += "Issues:\n- " + "\n- ".join(issues)
            else:
                summary += "No issues found."
            QMessageBox.information(self, "Origins ↔ Quests Validation", summary)
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"An error occurred during validation:\n{e}")
