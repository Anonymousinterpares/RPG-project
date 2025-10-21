#!/usr/bin/env python3
"""
Enhanced character creation dialog with Origin selection and stat allocation for the RPG game GUI.
"""

import os
import json
import logging
from typing import Dict, Optional, Any, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QGroupBox, QTextEdit, QTabWidget, QWidget, QMessageBox,
    QCheckBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QPixmap, QIcon

from gui.dialogs.new_game_dialog import NewGameDialog
from gui.components.stat_allocation_widget import StatAllocationWidget
from core.stats.stats_manager import StatsManager
from core.utils.logging_config import get_logger
from core.agents.narrator import get_narrator_agent 
from core.agents.base_agent import AgentContext 
from core.base.config import get_config 

logger = get_logger("GUI")

class CharacterCreationDialog(NewGameDialog):
    """Extended dialog for creating a new game character with Origin selection and stat allocation."""

    def __init__(self, parent=None):
        """Initialize the character creation dialog."""
        # We call QDialog's init directly as we heavily override the UI from NewGameDialog
        QDialog.__init__(self, parent)

        # Set window properties from NewGameDialog if desired
        self.setWindowTitle("Create New Character")
        self.setMinimumWidth(800)
        # --- MODIFICATION: Reduced height ---
        self.setMinimumHeight(550) # Adjusted height (was 650)
        # --- END MODIFICATION ---
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
                padding-top: 3px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #0E639C;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #0A4C7C;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #AAAAAA;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px 0 10px;
                color: #E0E0E0;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #333333;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #444444;
                color: #CCCCCC;
                border: 1px solid #555555;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 10px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #333333;
                color: #E0E0E0;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            #OriginDetailsLabel {
                color: #CCCCCC;
                padding-left: 5px;
                padding-top: 0px;
            }
        """)

        # Load data dynamically
        self.available_races = self._load_races()
        self.available_classes = self._load_classes()
        self.available_origins = self._load_origins() # Load origins
        self.available_sexes = ["Male", "Female", "Other"]

        # Initialize other state variables BEFORE UI setup that might use them
        self.llm_enabled = True
        self.selected_icon_path = None
        self.selected_origin_data = None
        self._last_generated_params = None

        # Initialize character icons list BEFORE UI setup
        self.character_icons = []
        self.current_icon_index = 0

        # Create stats manager BEFORE UI setup (StatAllocationWidget needs it)
        self.stats_manager = StatsManager()

        # Set up the UI with tabs SECOND (this creates self.icon_label etc.)
        self._setup_ui_with_tabs()

        # Scan for icons and display the first one THIRD (now self.icon_label exists)
        # Initial scan based on default selections
        self.scan_character_icons(self.race_combo.currentText(), self.path_combo.currentText(), self.sex_combo.currentText())

        # Connect signals FOURTH
        self._connect_signals()

        # Update UI based on initial race/class FIFTH (important for stat allocation)
        self._update_race_class() # This also calls _show_stat_requirements_info

        self._on_origin_selected(self.origin_combo.currentIndex())

        # Initial validation LAST
        self._validate_form()

        # Wire UI sounds for Character Creation dialog: tabs -> tab_click; dropdowns -> dropdown; other clicks -> dropdown
        try:
            from gui.utils.ui_sfx import map_container
            map_container(self, click_kind='dropdown', tab_kind='tab_click', dropdown_kind='dropdown')
        except Exception:
            pass

    def _setup_ui_with_tabs(self):
        """Set up the main UI using tabs."""
        # Main layout for the dialog
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(15, 15, 15, 15)
        dialog_layout.setSpacing(10)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #555555; background-color: #333333; border-radius: 5px; }
            QTabBar::tab { background-color: #444444; color: #CCCCCC; border: 1px solid #555555; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; padding: 6px 10px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #333333; color: #E0E0E0; }
        """)

        # --- Tab 1: Basic Info & Origin ---
        self.basic_info_tab = QWidget()
        basic_info_main_layout = QHBoxLayout(self.basic_info_tab)
        basic_info_main_layout.setSpacing(15)

        # Left Side: Character Info & Portrait
        left_basic_layout = QVBoxLayout()

        info_group = QGroupBox("Character Information")
        info_form_layout = QFormLayout(info_group)
        info_form_layout.setContentsMargins(15, 25, 15, 15)
        info_form_layout.setSpacing(8)

        # Create UI elements (Name, Race, Class, Origin Combo, Sex, LLM Checkbox)
        self.player_name_edit = QLineEdit()
        self.player_name_edit.setPlaceholderText("Enter your character's name...")
        info_form_layout.addRow("Name:", self.player_name_edit)

        self.race_combo = QComboBox()
        self._populate_combo(self.race_combo, self.available_races, "Races") # Populate basic combos early
        info_form_layout.addRow("Race:", self.race_combo)

        self.path_combo = QComboBox() # Represents Class
        self._populate_combo(self.path_combo, self.available_classes, "Classes") # Populate basic combos early
        info_form_layout.addRow("Class:", self.path_combo)

        self.origin_combo = QComboBox() # Create the combo, but DON'T populate yet
        info_form_layout.addRow("Origin:", self.origin_combo)

        self.sex_combo = QComboBox()
        self._populate_combo(self.sex_combo, self.available_sexes, "Sexes") # Populate basic combos early
        info_form_layout.addRow("Sex:", self.sex_combo)

        self.llm_checkbox = QCheckBox("Enable LLM (AI processing)")
        self.llm_checkbox.setChecked(self.llm_enabled)
        info_form_layout.addRow("", self.llm_checkbox)

        left_basic_layout.addWidget(info_group)

        # Portrait Section
        icon_group = QGroupBox("Character Portrait")
        icon_layout = QVBoxLayout(icon_group)
        icon_layout.setContentsMargins(15, 25, 15, 15)
        icon_layout.setSpacing(8)
        self.icon_label = QLabel() # Create icon label
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(150, 150)
        self.icon_label.setStyleSheet("background-color: #1E1E1E; border: 1px solid #3F3F46;")
        self.icon_label.setText("No image")
        icon_layout.addWidget(self.icon_label, 0, Qt.AlignCenter)
        nav_layout = QHBoxLayout()
        self.prev_icon_button = QPushButton("←")
        self.icon_counter_label = QLabel("0 / 0") # Create counter label
        self.icon_counter_label.setAlignment(Qt.AlignCenter)
        self.next_icon_button = QPushButton("→")
        nav_layout.addWidget(self.prev_icon_button)
        nav_layout.addWidget(self.icon_counter_label)
        nav_layout.addWidget(self.next_icon_button)
        icon_layout.addLayout(nav_layout)
        portrait_hint = QLabel("Browse available portraits")
        portrait_hint.setStyleSheet("color: #888888; font-style: italic;")
        portrait_hint.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(portrait_hint)
        left_basic_layout.addWidget(icon_group)
        left_basic_layout.addStretch(1)

        # Right Side: Origin Details & Backstory Seed
        right_basic_layout = QVBoxLayout()

        origin_details_group = QGroupBox("Origin Details")
        origin_details_layout = QVBoxLayout(origin_details_group)
        origin_details_layout.setContentsMargins(15, 25, 15, 15)
        origin_details_layout.setSpacing(8)
        origin_details_layout.addWidget(QLabel("<b>Description:</b>"))
        self.origin_desc_label = QLabel("Select an Origin to see details.") # Create desc label
        self.origin_desc_label.setObjectName("OriginDetailsLabel")
        self.origin_desc_label.setWordWrap(True)
        self.origin_desc_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        origin_details_layout.addWidget(self.origin_desc_label)
        origin_details_layout.addWidget(QLabel("<b>Skill Proficiencies:</b>"))
        self.origin_skills_label = QLabel("-") # Create skills label
        self.origin_skills_label.setObjectName("OriginDetailsLabel")
        self.origin_skills_label.setWordWrap(True)
        origin_details_layout.addWidget(self.origin_skills_label)
        origin_details_layout.addWidget(QLabel("<b>Origin Traits:</b>"))
        self.origin_traits_label = QLabel("-") # Create traits label
        self.origin_traits_label.setObjectName("OriginDetailsLabel")
        self.origin_traits_label.setWordWrap(True)
        self.origin_traits_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        origin_details_layout.addWidget(self.origin_traits_label)
        origin_details_layout.addStretch()

        # Backstory Seed Group
        description_group = QGroupBox("Character Backstory (Seed)")
        description_layout = QVBoxLayout(description_group)
        description_layout.setContentsMargins(15, 25, 15, 15)
        description_layout.setSpacing(5)
        description_label = QLabel("Edit the text below (loaded from Origin) to guide LLM background generation:")
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
        self.description_edit = QTextEdit() # Create text edit
        self.description_edit.setPlaceholderText("Select an Origin to load starting text...")
        self.description_edit.setMinimumHeight(120)
        description_layout.addWidget(description_label)
        description_layout.addWidget(self.description_edit)

        # AI Buttons for Backstory
        ai_button_layout = QHBoxLayout()
        icon_path_improve = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "images", "icons", "ai_improve.svg")
        self.improve_background_button = QPushButton()
        self.improve_background_button.setIcon(QIcon(icon_path_improve))
        self.improve_background_button.setIconSize(QSize(16, 16))
        self.improve_background_button.setToolTip("Improve Backstory Seed via AI")
        self.improve_background_button.setFixedSize(30, 30)

        icon_path_generate = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "images", "icons", "ai_generate.svg")
        self.generate_background_button = QPushButton()
        self.generate_background_button.setIcon(QIcon(icon_path_generate))
        self.generate_background_button.setIconSize(QSize(16, 16))
        self.generate_background_button.setToolTip("Generate Backstory Seed via AI")
        self.generate_background_button.setFixedSize(30, 30)

        ai_button_layout.addStretch()
        ai_button_layout.addWidget(self.improve_background_button)
        ai_button_layout.addWidget(self.generate_background_button)
        description_layout.addLayout(ai_button_layout)

        right_basic_layout.addWidget(origin_details_group)
        right_basic_layout.addWidget(description_group)
        right_basic_layout.addStretch(1)

        basic_info_main_layout.addLayout(left_basic_layout, 1)
        basic_info_main_layout.addLayout(right_basic_layout, 2)

        # --- Tab 2: Stats --- (Will be added later by user)
        # self.stats_tab = QWidget()
        # ...

        # --- Tab 3: Stats (Renamed from Tab 2) ---
        self.stats_tab = QWidget() # Renamed variable for clarity, though index matters more
        stats_layout = QVBoxLayout(self.stats_tab)
        stats_layout.setSpacing(10)

        # Race/Class selectors
        race_class_selection_layout = QVBoxLayout()
        race_selector_layout = QHBoxLayout()
        race_selector_layout.setContentsMargins(0, 5, 0, 0); race_selector_layout.setSpacing(8)
        self.race_prev_button = QPushButton()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "images", "icons", "left_arrow.svg")
        self.race_prev_button.setIcon(QIcon(icon_path))
        self.race_prev_button.setIconSize(QSize(16, 16)); self.race_prev_button.setFixedSize(24, 24)
        self.race_label = QLabel("Race") # Create race label
        self.race_label.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 14px;"); self.race_label.setAlignment(Qt.AlignCenter)
        self.race_next_button = QPushButton()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "images", "icons", "right_arrow.svg")
        self.race_next_button.setIcon(QIcon(icon_path))
        self.race_next_button.setIconSize(QSize(16, 16)); self.race_next_button.setFixedSize(24, 24)
        race_selector_layout.addWidget(self.race_prev_button); race_selector_layout.addWidget(self.race_label, 1); race_selector_layout.addWidget(self.race_next_button)
        race_class_selection_layout.addLayout(race_selector_layout)

        class_selector_layout = QHBoxLayout()
        class_selector_layout.setContentsMargins(0, 5, 0, 10); class_selector_layout.setSpacing(8)
        self.class_prev_button = QPushButton()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "images", "icons", "left_arrow.svg")
        self.class_prev_button.setIcon(QIcon(icon_path))
        self.class_prev_button.setIconSize(QSize(16, 16)); self.class_prev_button.setFixedSize(24, 24)
        self.class_label = QLabel("Class") # Create class label
        self.class_label.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 14px;"); self.class_label.setAlignment(Qt.AlignCenter)
        self.class_next_button = QPushButton()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "images", "icons", "right_arrow.svg")
        self.class_next_button.setIcon(QIcon(icon_path))
        self.class_next_button.setIconSize(QSize(16, 16)); self.class_next_button.setFixedSize(24, 24)
        class_selector_layout.addWidget(self.class_prev_button); class_selector_layout.addWidget(self.class_label, 1); class_selector_layout.addWidget(self.class_next_button)
        race_class_selection_layout.addLayout(class_selector_layout)
        stats_layout.addLayout(race_class_selection_layout)

        # Stat Allocation Widget
        self.stat_allocation = StatAllocationWidget( # Create stat widget
            self.stats_manager,
            self.race_combo.currentText(),
            self.path_combo.currentText()
        )
        stats_layout.addWidget(self.stat_allocation)

        # Info Label for Stats Tab
        self.stat_info_label = QLabel() # Create stat info label
        self.stat_info_label.setWordWrap(True)
        self.stat_info_label.setStyleSheet("color: #E0E0E0; background-color: rgba(0, 0, 0, 0.2); padding: 10px; border-radius: 5px;")
        stats_layout.addWidget(self.stat_info_label)
        stats_layout.addStretch(1)

        # --- Tab 4: Background (Simplified) --- (Renamed from Tab 3)
        self.background_tab = QWidget()
        background_layout = QVBoxLayout(self.background_tab)
        # Maybe repurpose this tab later if needed
        background_layout.addWidget(QLabel("Review Character Summary (Optional Tab)"))
        background_layout.addStretch()

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.basic_info_tab, "1. Basic Info & Origin")
        # --- MODIFICATION: Add placeholder for future Tab 2 ---
        # self.tab_widget.addTab(QWidget(), "2. Skills & Feats (TBD)") # Placeholder
        # --- END MODIFICATION ---
        # --- MODIFICATION: Renamed Stats Tab ---
        self.tab_widget.addTab(self.stats_tab, "3. Stats") # Renamed from "2. Stats"
        # --- END MODIFICATION ---
        # Connect tab changed signal
        self.tab_widget.currentChanged.connect(self._tab_changed)
        # self.tab_widget.addTab(self.background_tab, "4. Review (Optional)") # Renumbered

        dialog_layout.addWidget(self.tab_widget)

        # --- Navigation & Create Buttons ---
        bottom_button_layout = QHBoxLayout()
        self.prev_tab_button = QPushButton("< Previous")
        self.next_tab_button = QPushButton("Next >")
        self.cancel_button = QPushButton("Cancel")
        self.create_button = QPushButton("Create Character")
        self.start_game_button = QPushButton("Start Game")
        self.start_game_button.setStyleSheet("""
            QPushButton {
                background-color: #22863a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a9949;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #AAAAAA;
            }
        """)
        self.start_game_button.hide()  # Initially hidden

        bottom_button_layout.addWidget(self.cancel_button)
        bottom_button_layout.addStretch()
        bottom_button_layout.addWidget(self.prev_tab_button)
        bottom_button_layout.addWidget(self.next_tab_button)
        bottom_button_layout.addWidget(self.create_button)
        # Initially hide the create button until needed
        self.create_button.hide()

        dialog_layout.addLayout(bottom_button_layout)

        # Initialize tab state
        self._tab_changed(0)

        # NOW populate the origin combo, as all widgets exist
        self._populate_origin_combo()

    def _populate_combo(self, combo: QComboBox, items: List[str], item_type: str):
        """Helper to populate QComboBox and handle empty lists."""
        combo.clear()
        if not items:
            combo.addItem(f"No {item_type} Found")
            combo.setEnabled(False)
        else:
            combo.addItems(items)
            combo.setEnabled(True)

    def _populate_origin_combo(self):
        """
        Populate the Origin combo box, filtering based on selected Race and Class.
        """
        combo = self.origin_combo
        all_origins = self.available_origins # List of origin dicts
        item_type = "Origins"

        # Get current selections (ensure combo boxes exist first)
        selected_race = self.race_combo.currentText() if hasattr(self, 'race_combo') else None
        selected_class = self.path_combo.currentText() if hasattr(self, 'path_combo') else None

        previous_origin_id = combo.currentData()

        combo.blockSignals(True) 
        combo.clear()
        combo.addItem("--- Select an Origin ---", None) 

        if not all_origins:
            combo.addItem(f"No {item_type} Found")
            combo.setEnabled(False)
            combo.blockSignals(False)
            self._on_origin_selected(0) 
            return

        if not selected_race or not selected_class:
            combo.addItem("Select Race/Class first")
            combo.setEnabled(False)
            combo.blockSignals(False)
            self._on_origin_selected(0) 
            return

        # --- Filtering Logic ---
        suitable_origins = []
        for origin_data in all_origins:
            races_ok = True 
            if origin_data.get("suitable_races"): 
                races_ok = selected_race in origin_data["suitable_races"]

            classes_ok = True 
            if origin_data.get("suitable_classes"): 
                classes_ok = selected_class in origin_data["suitable_classes"]

            if races_ok and classes_ok:
                suitable_origins.append(origin_data)
        # --- End Filtering Logic ---

        if not suitable_origins:
            combo.addItem(f"No suitable {item_type} found")
            combo.setEnabled(False)
        else:
            reselect_index = 0 # Default to placeholder
            for index, origin_data in enumerate(suitable_origins):
                origin_id = origin_data.get('id')
                origin_name = origin_data.get('name', 'Unknown Origin')
                # Add item with name as text and id as data
                combo.addItem(origin_name, origin_id)
                # Check if this was the previously selected origin
                if origin_id == previous_origin_id:
                    reselect_index = index + 1

            combo.setEnabled(True)
            combo.setCurrentIndex(reselect_index)

        combo.blockSignals(False) # Re-enable signals
        self._on_origin_selected(combo.currentIndex())

    def _toggle_llm(self, state):
        """Toggle LLM enabled state."""
        self.llm_enabled = bool(state)
        # Enable/disable AI buttons based on LLM state
        self.improve_background_button.setEnabled(self.llm_enabled)
        self.generate_background_button.setEnabled(self.llm_enabled)

    # --- Data Loading --- (Keep as is)
    def _load_races(self) -> List[str]:
        races = []
        try:
            config = get_config()
            loaded_races_data = config.get_all("races")
            if loaded_races_data:
                race_names = sorted([data.get('name', race_id) for race_id, data in loaded_races_data.items()])
                if race_names: races = race_names
            if not races: logger.warning("Race config not found or empty.")
        except Exception as e: logger.error(f"Error loading races: {e}.")
        return races if races else ["Human"]

    def _load_classes(self) -> List[str]:
        classes = []
        try:
            config = get_config()
            loaded_classes_data = config.get_all("classes")
            if loaded_classes_data:
                class_names = sorted([data.get('name', class_id) for class_id, data in loaded_classes_data.items()])
                if class_names: classes = class_names
            if not classes: logger.warning("Class config not found or empty.")
        except Exception as e: logger.error(f"Error loading classes: {e}.")
        return classes if classes else ["Wanderer"]

    def _load_origins(self) -> List[Dict[str, Any]]:
        origins_data = []
        try:
            config = get_config()
            loaded_origins_dict = config.get_all("origins") # Load "origins" key
            if loaded_origins_dict and isinstance(loaded_origins_dict, dict):
                origins_data = list(loaded_origins_dict.values())
                origins_data.sort(key=lambda x: x.get('name', 'Unknown Origin'))
                logger.info(f"Loaded {len(origins_data)} origins from config.")
            else:
                logger.warning("Origin configuration domain ('origins') not found or empty.")
        except Exception as e:
            logger.error(f"Error loading origins from config: {e}.")
        return origins_data

    # --- Icon Scanning & Filtering ---
    def scan_character_icons(self, race: str, class_name: str, sex: str):
        """
        Scan for character icons in the specific race/class directory
        and filter based on sex, looking for '_male' or '_female' in filenames.
        """
        self.character_icons = [] # Clear previous icons
        self.current_icon_index = 0

        if not race or not class_name or not sex or "No " in race or "No " in class_name:
            logger.warning(f"Cannot scan icons: Race ('{race}'), Class ('{class_name}'), or Sex ('{sex}') not validly selected.")
            self._display_current_icon()
            return

        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            safe_race = race.replace(" ", "_")
            safe_class_name = class_name.replace(" ", "_")
            specific_icons_dir = os.path.join(project_root, "images", "character_icons", f"{safe_race}_{safe_class_name}")
            logger.debug(f"Scanning for icons in specific directory: {specific_icons_dir}")

            if not os.path.exists(specific_icons_dir):
                logger.warning(f"Icon directory not found: {specific_icons_dir}")
                self._display_current_icon()
                return

            supported_extensions = [".png", ".jpg", ".jpeg", ".gif", ".svg"]

            for filename in os.listdir(specific_icons_dir):
                if any(filename.lower().endswith(ext) for ext in supported_extensions):
                    name_part_lower = os.path.splitext(filename)[0].lower() # Filename without extension, lowercase
                    sex_lower = sex.lower()
                    include_file = False

                    # Check for specific substrings "_male" or "_female"
                    contains_male_tag = "_male" in name_part_lower
                    contains_female_tag = "_female" in name_part_lower

                    if sex_lower == "male":
                        if contains_male_tag: # Only include if it explicitly has "_male"
                            include_file = True
                    elif sex_lower == "female":
                        if contains_female_tag: # Only include if it explicitly has "_female"
                            include_file = True
                    elif sex_lower == "other":
                        # For "Other", include if either tag is present
                        if contains_male_tag or contains_female_tag:
                            include_file = True
                    
                    if include_file:
                        file_path = os.path.join(specific_icons_dir, filename)
                        self.character_icons.append({
                            "filename": filename,
                            "path": file_path
                        })

            self.character_icons.sort(key=lambda x: x["filename"])
            logger.info(f"Found {len(self.character_icons)} suitable icons in {specific_icons_dir} for sex '{sex}' (using _male/_female tags).")

        except OSError as e:
            logger.error(f"Error reading icons directory {specific_icons_dir}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scanning icons: {e}", exc_info=True)

        self._display_current_icon()
        
    # --- Signal Connections ---
    def _connect_signals(self):
        """Connect signals to slots."""
        # Basic Info Tab
        self.player_name_edit.textChanged.connect(self._validate_form)
        self.race_combo.currentIndexChanged.connect(self._validate_form)
        self.race_combo.currentTextChanged.connect(self._update_race_class)
        self.race_combo.currentTextChanged.connect(self._populate_origin_combo) 
        self.path_combo.currentIndexChanged.connect(self._validate_form)
        self.path_combo.currentTextChanged.connect(self._update_race_class)
        self.path_combo.currentTextChanged.connect(self._populate_origin_combo) 

        # Only connect origin index change to validation and details update
        self.origin_combo.currentIndexChanged.connect(self._validate_form)
        self.origin_combo.currentIndexChanged.connect(self._on_origin_selected)

        self.sex_combo.currentIndexChanged.connect(self._validate_form)
        self.llm_checkbox.stateChanged.connect(self._toggle_llm)

        # Update icons when race, class, or sex changes
        self.race_combo.currentIndexChanged.connect(self._update_icons_on_selection_change)
        self.path_combo.currentIndexChanged.connect(self._update_icons_on_selection_change)
        self.sex_combo.currentIndexChanged.connect(self._update_icons_on_selection_change)

        # Portrait
        self.prev_icon_button.clicked.connect(self._show_previous_icon)
        self.next_icon_button.clicked.connect(self._show_next_icon)

        # Stats Tab
        self.race_prev_button.clicked.connect(self._previous_race)
        self.race_next_button.clicked.connect(self._next_race)
        self.class_prev_button.clicked.connect(self._previous_class)
        self.class_next_button.clicked.connect(self._next_class)
        self.stat_allocation.stats_changed.connect(self._stats_changed)

        # Backstory Seed / AI Buttons
        self.improve_background_button.clicked.connect(self._improve_background)
        self.generate_background_button.clicked.connect(self._generate_background)

        # Dialog Buttons
        self.cancel_button.clicked.connect(self.reject)
        self.create_button.clicked.connect(self._finish_character_creation) # Connect create to finish method
        self.start_game_button.clicked.connect(self._start_new_game) # Start game button triggers special method
        self.prev_tab_button.clicked.connect(self._previous_tab)
        self.next_tab_button.clicked.connect(self._next_tab)
        
        # Set tooltips for the buttons
        self.create_button.setToolTip("Create your character and prepare to start the game")
        self.start_game_button.setToolTip("Begin your adventure with this character")
        self.cancel_button.setToolTip("Cancel character creation")

        # Connect race/class/origin/sex change to clear background generation context
        self.race_combo.currentTextChanged.connect(self._check_generated_context)
        self.path_combo.currentTextChanged.connect(self._check_generated_context)
        self.origin_combo.currentTextChanged.connect(self._check_generated_context) # Keep this check
        self.sex_combo.currentTextChanged.connect(self._check_generated_context)

        # Initial UI state update
        self._toggle_llm(self.llm_checkbox.isChecked()) # Set initial AI button state

        # Connect signals that affect AI button state
        self.player_name_edit.textChanged.connect(self._update_ai_button_state)
        self.stat_allocation.stats_changed.connect(self._update_ai_button_state)
        self.stat_allocation.allocation_complete.connect(self._update_ai_button_state)

        # Initial AI button state update
        self._update_ai_button_state()

    # --- Validation ---
    def _validate_form(self):
        """Validate the form and enable/disable the create button."""
        # This validation now applies mainly to the Create button state
        has_name = bool(self.player_name_edit.text().strip())
        race_selected = self.race_combo.isEnabled() and self.race_combo.currentIndex() >= 0
        class_selected = self.path_combo.isEnabled() and self.path_combo.currentIndex() >= 0
        origin_selected = self.origin_combo.isEnabled() and self.origin_combo.currentIndex() > 0 # Check for valid origin index

        can_create = (
            has_name and
            race_selected and
            class_selected and
            origin_selected
        )

        # Get current tab
        current_tab_index = self.tab_widget.currentIndex()
        
        # Set Create button state if visible
        if self.create_button.isVisible():
            logger.debug(f"Setting create button enabled state to: {can_create}")
            self.create_button.setEnabled(can_create)
            if can_create:
                self.create_button.setToolTip("Create your character")
            else:
                self.create_button.setToolTip("Please complete all required fields")

        # Enable/disable next button based on basic info validity if on first tab
        if current_tab_index == 0:
            self.next_tab_button.setEnabled(can_create)
            if can_create:
                self.next_tab_button.setToolTip("Proceed to character stats")
            else:
                self.next_tab_button.setToolTip("Please complete all required fields before proceeding")
        else:
            self.next_tab_button.setEnabled(True) # Always enabled on other tabs (except last)


    # --- Icon Display --- (Keep as is)
    def _show_previous_icon(self):
        if not self.character_icons: return
        self.current_icon_index = (self.current_icon_index - 1 + len(self.character_icons)) % len(self.character_icons)
        self._display_current_icon()

    def _show_next_icon(self):
        if not self.character_icons: return
        self.current_icon_index = (self.current_icon_index + 1) % len(self.character_icons)
        self._display_current_icon()

    def _display_current_icon(self):
        if not self.character_icons:
            self.selected_icon_path = None
            self.icon_label.setText("No Icons Found")
            self.icon_counter_label.setText("0 / 0")
            return

        icon_info = self.character_icons[self.current_icon_index]
        icon_path = icon_info['path']
        self.icon_counter_label.setText(f"{self.current_icon_index + 1} / {len(self.character_icons)}")

        try:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(self.icon_label.width(), self.icon_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_label.setPixmap(pixmap)
                self.selected_icon_path = icon_path
            else:
                self.icon_label.setText("Load Error")
                self.selected_icon_path = None
        except Exception as e:
            logger.error(f"Error loading icon '{icon_path}': {e}")
            self.icon_label.setText("Load Error")
            self.selected_icon_path = None

    # --- Get Character Data ---
    def get_character_data(self) -> Optional[Dict[str, Any]]:
        """Get the final character data from all tabs."""
        # Validate basic info first
        if not self._validate_basic_info():
             QMessageBox.warning(self, "Incomplete Information", "Please complete the basic character information.")
             self.tab_widget.setCurrentIndex(0) # Go back to first tab
             return None

        # Retrieve basic info
        name = self.player_name_edit.text().strip()
        race = self.race_combo.currentText()
        path = self.path_combo.currentText()
        origin_id = self.origin_combo.currentData() # Get the ID stored in data
        sex = self.sex_combo.currentText()

        # Basic validation again (should pass if Create button was enabled)
        if not name or not race or not path or origin_id is None:
             logger.error("Validation failed in get_character_data despite enabled button.")
             return None

        # Retrieve backstory seed text
        # Prioritize user edited text, fallback to origin intro text
        backstory_seed = self.description_edit.toPlainText().strip()
        if not backstory_seed and self.selected_origin_data:
            backstory_seed = self.selected_origin_data.get('introduction_text', '')

        # Retrieve final stats from allocation widget
        allocated_stats = self.stat_allocation.get_allocated_stats()
        if not allocated_stats:
            logger.error("Could not retrieve allocated stats.")
            QMessageBox.critical(self, "Stat Error", "Could not retrieve final stats. Please check the Stats tab.")
            self.tab_widget.setCurrentIndex(1) # Go to stats tab
            return None

        # Build the final data dictionary
        data = {
            'name': name,
            'race': race,
            'path': path,
            'origin_id': origin_id, # Use origin ID
            'sex': sex,
            'description': backstory_seed, # The seed text for LLM
            'use_llm': self.llm_enabled,
            'character_image': self.selected_icon_path,
            'stats': allocated_stats, # Include allocated base stats
            # Add starting items/location based on selected origin
            'starting_location_id': self.selected_origin_data.get('starting_location_id', '') if self.selected_origin_data else '',
            'starting_items': self.selected_origin_data.get('starting_items', []) if self.selected_origin_data else [],
            'initial_quests': self.selected_origin_data.get('initial_quests', []) if self.selected_origin_data else []
        }

        # --- Optional: Add compatibility fields if core engine expects them ---
        # This depends on how core/base/engine.py -> start_new_game is implemented
        # If it still expects individual base stats:
        # for stat_name, value in allocated_stats.items():
        #     data[f'base_{stat_name.lower()}'] = value
        # If it expects background name (use origin name as fallback):
        # data['background'] = self.origin_combo.currentText()
        # ---------------------------------------------------------------------

        logger.info(f"Character data collected: { {k:v for k,v in data.items() if k != 'stats'} }") # Log non-stat data
        logger.debug(f"Character stats: {data.get('stats')}")
        return data


    # --- Methods inherited or potentially modified from NewGameDialog ---
    # These might need adjustments based on the tabbed layout

    def _update_race_class(self, *args):
        """Update stat allocation and labels when race or class changes."""
        race = self.race_combo.currentText()
        class_name = self.path_combo.currentText()

        if hasattr(self, 'race_label'): self.race_label.setText(race)
        if hasattr(self, 'class_label'): self.class_label.setText(class_name)

        if hasattr(self, 'stat_allocation'):
            self.stat_allocation.update_race_class(race, class_name)

        self._show_stat_requirements_info(race, class_name)
        self._validate_form() # Re-validate when race/class changes

    def _previous_race(self):
        current_index = self.race_combo.currentIndex()
        if current_index > 0:
            self.race_combo.setCurrentIndex(current_index - 1)

    def _next_race(self):
        current_index = self.race_combo.currentIndex()
        if current_index < self.race_combo.count() - 1:
            self.race_combo.setCurrentIndex(current_index + 1)

    def _previous_class(self):
        current_index = self.path_combo.currentIndex()
        if current_index > 0:
            self.path_combo.setCurrentIndex(current_index - 1)

    def _next_class(self):
        current_index = self.path_combo.currentIndex()
        if current_index < self.path_combo.count() - 1:
            self.path_combo.setCurrentIndex(current_index + 1)

    def _stats_changed(self, stats: Dict[str, Dict[str, int]]):
        """Handle stat changes from allocation widget."""
        self._validate_form() # Re-validate overall form
        self._update_ai_button_state()

    def _validate_for_ai_generation(self) -> bool:
        """Checks if conditions are met for enabling AI generation buttons."""
        has_name = bool(self.player_name_edit.text().strip())
        stats_allocated = hasattr(self, 'stat_allocation') and self.stat_allocation.are_points_fully_allocated()
        return has_name and stats_allocated

    def _update_ai_button_state(self):
        """Updates the enabled state and tooltip of AI buttons."""
        can_generate = self._validate_for_ai_generation()
        tooltip_text = ""

        if not can_generate:
            missing = []
            if not bool(self.player_name_edit.text().strip()):
                missing.append("Enter a character name")
            if not (hasattr(self, 'stat_allocation') and self.stat_allocation.are_points_fully_allocated()):
                remaining = self.stat_allocation.get_remaining_points() if hasattr(self, 'stat_allocation') else 'N/A'
                missing.append(f"Allocate all stat points ({remaining} remaining)")
            tooltip_text = "Cannot generate backstory:\n- " + "\n- ".join(missing)

        # Update Improve Button
        if hasattr(self, 'improve_background_button'):
            self.improve_background_button.setEnabled(can_generate)
            self.improve_background_button.setToolTip(tooltip_text if not can_generate else "Improve Backstory Seed via AI")

        # Update Generate Button
        if hasattr(self, 'generate_background_button'):
            self.generate_background_button.setEnabled(can_generate)
            self.generate_background_button.setToolTip(tooltip_text if not can_generate else "Generate Backstory Seed via AI")
    
    def _show_stat_requirements_info(self, race: str, class_name: str):
        """Display info about race/class modifiers and requirements."""
        if not hasattr(self, 'stat_allocation') or not hasattr(self, 'stat_info_label'):
            return

        modifier_info = self.stat_allocation.modifier_info
        if not modifier_info:
            self.stat_info_label.setText("Loading stat info...")
            return

        race_mods = modifier_info.race_modifiers
        class_mods = modifier_info.class_modifiers
        reqs = modifier_info.minimum_requirements
        recomm = modifier_info.recommended_stats

        info_text = f"<div style='font-weight: bold; font-size: 13px;'>{race} {class_name} Stat Info</div><hr>"

        def format_mods(mods_dict, color_pos, color_neg):
            if not mods_dict: return "None"
            parts = []
            for stat, mod in sorted(mods_dict.items()):
                if mod != 0:
                    color = color_pos if mod > 0 else color_neg
                    parts.append(f"<span style='color: {color}'>{stat} {mod:+d}</span>")
            return ", ".join(parts) if parts else "None"

        info_text += f"<div style='margin-bottom: 8px;'><b>Race Modifiers:</b> {format_mods(race_mods, '#4CAF50', '#F44336')}</div>"
        info_text += f"<div style='margin-bottom: 8px;'><b>Class Modifiers:</b> {format_mods(class_mods, '#2196F3', '#F44336')}</div>"

        req_text = ", ".join([f"{stat} {val}" for stat, val in sorted(reqs.items())]) if reqs else "None"
        info_text += f"<div style='margin-bottom: 8px;'><b>Minimum Requirements:</b> {req_text}</div>"

        recomm_prim = ", ".join(recomm.get('primary', [])) if recomm.get('primary') else "Balanced"
        info_text += f"<div><b>Recommended Primary:</b> {recomm_prim}</div>"

        self.stat_info_label.setText(info_text)

    @Slot()
    def _improve_background(self):
        if not self._validate_for_ai_generation(): return # Check validation first

        text = self.description_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Text", "Please enter some background seed text first.")
            return

        detailed_context = self._get_detailed_context_for_llm()
        formatted_context = self._format_context_for_llm_prompt(detailed_context)

        prompt = (
            f"Improve the following background seed text for the character described below. "
            f"Make it an engaging character description focusing on personality, motivation, and appearance, "
            f"fitting the provided context. Do not narrate actions, just describe the character.\n\n"
            f"BACKGROUND SEED:\n{text}\n\n"
            f"{formatted_context}"
        )

        logger.debug(f"Sending improve background prompt:\n{prompt}") # Log the prompt

        # Call LLM
        ctx = AgentContext(
            game_state={}, player_state={}, world_state={}, # Minimal state needed
            player_input=prompt, # Use the constructed prompt
            conversation_history=[], relevant_memories=[], additional_context={}
        )
        # Add error handling for LLM calls
        try:
            # Disable buttons during generation
            self.improve_background_button.setEnabled(False)
            self.generate_background_button.setEnabled(False)
            self.repaint() # Force UI update

            response = get_narrator_agent().process(ctx) # Assumes this function exists

            # Re-enable buttons
            self._update_ai_button_state()

            narrative_content = response.get("narrative") if response else None
            if narrative_content:
                self.description_edit.setPlainText(narrative_content.strip())
                # Update context tracking only AFTER successful generation
                self._last_generated_params = (
                    detailed_context.get('race',{}).get('name'),
                    detailed_context.get('class',{}).get('name'),
                    detailed_context.get('origin',{}).get('name'),
                    detailed_context.get('character',{}).get('sex')
                 )
            else:
                 QMessageBox.warning(self, "AI Error", "Could not improve background. No valid response from AI.")
        except Exception as e:
            logger.error(f"Error improving background: {e}", exc_info=True)
            QMessageBox.critical(self, "AI Error", f"An error occurred while improving the background:\n{e}")
            self._update_ai_button_state() # Ensure buttons are re-enabled on error

    @Slot()
    def _generate_background(self):
        if not self._validate_for_ai_generation(): return # Check validation first

        detailed_context = self._get_detailed_context_for_llm()
        formatted_context = self._format_context_for_llm_prompt(detailed_context)

        prompt = (
            f"Generate a short, engaging character description backstory seed (personality, motivation, appearance) "
            f"for the character described below. Do not narrate actions, just describe the character based on the context.\n\n"
            f"{formatted_context}"
        )

        logger.debug(f"Sending generate background prompt:\n{prompt}") # Log the prompt

        # Call LLM
        ctx = AgentContext(
            game_state={}, player_state={}, world_state={}, # Minimal state needed
            player_input=prompt, # Use the constructed prompt
            conversation_history=[], relevant_memories=[], additional_context={}
        )
        # Add error handling for LLM calls
        try:
            # Disable buttons during generation
            self.improve_background_button.setEnabled(False)
            self.generate_background_button.setEnabled(False)
            self.repaint() # Force UI update

            response = get_narrator_agent().process(ctx) # Assumes this function exists

            # Re-enable buttons
            self._update_ai_button_state()

            narrative_content = response.get("narrative") if response else None
            if narrative_content:
                self.description_edit.setPlainText(narrative_content.strip())
                 # Update context tracking only AFTER successful generation
                self._last_generated_params = (
                    detailed_context.get('race',{}).get('name'),
                    detailed_context.get('class',{}).get('name'),
                    detailed_context.get('origin',{}).get('name'),
                    detailed_context.get('character',{}).get('sex')
                 )
            else:
                 QMessageBox.warning(self, "AI Error", "Could not generate background. No valid response from AI.")
        except Exception as e:
            logger.error(f"Error generating background: {e}", exc_info=True)
            QMessageBox.critical(self, "AI Error", f"An error occurred while generating the background:\n{e}")
            self._update_ai_button_state() # Ensure buttons are re-enabled on error

    def _check_generated_context(self):
        """Warn if selections change after background generation."""
        if self._last_generated_params:
            current = (
                self.race_combo.currentText(),
                self.path_combo.currentText(),
                self.origin_combo.currentText(), # Use origin name
                self.sex_combo.currentText()
            )
            if current != self._last_generated_params:
                QMessageBox.warning(
                    self,
                    "Background Mismatch",
                    "The backstory seed was generated for a previous selection. Please regenerate or edit to match."
                )
                # Clear the tracking so it doesn't warn repeatedly
                self._last_generated_params = None

    # --- Tab Navigation Logic ---
    def _previous_tab(self):
        current = self.tab_widget.currentIndex()
        if current > 0:
            self.tab_widget.setCurrentIndex(current - 1)

    def _next_tab(self):
        current = self.tab_widget.currentIndex()
        total = self.tab_widget.count()
        if current < total - 1:
            # Validate basic info before leaving first tab
            if current == 0 and not self._validate_basic_info():
                return # Stay on first tab if invalid
            self.tab_widget.setCurrentIndex(current + 1)
        # Note: Finishing logic is now in _finish_character_creation connected to create_button
        
    def _validate_basic_info(self) -> bool:
        """Validate the basic character information on the first tab."""
        logger.debug("Validating basic character information")
        
        # Check if name is entered
        name = self.player_name_edit.text().strip()
        if not name:
            logger.warning("Character creation validation failed: Missing name")
            QMessageBox.warning(self, "Missing Name", "Please enter a character name.")
            return False
            
        # Check if race is selected
        race_selected = self.race_combo.isEnabled() and self.race_combo.currentIndex() >= 0
        if not race_selected:
            logger.warning("Character creation validation failed: Missing race")
            QMessageBox.warning(self, "Missing Race", "Please select a race for your character.")
            return False
            
        # Check if class is selected
        class_selected = self.path_combo.isEnabled() and self.path_combo.currentIndex() >= 0
        if not class_selected:
            logger.warning("Character creation validation failed: Missing class")
            QMessageBox.warning(self, "Missing Class", "Please select a class for your character.")
            return False
            
        # Check if origin is selected (choosing the first placeholder item doesn't count)
        origin_selected = self.origin_combo.isEnabled() and self.origin_combo.currentIndex() > 0
        if not origin_selected:
            logger.warning("Character creation validation failed: Missing origin")
            QMessageBox.warning(self, "Missing Origin", "Please select an origin for your character.")
            return False
            
        # All basic info is valid
        logger.debug("Basic character information validation passed")
        return True

    def _tab_changed(self, index: int):
        """Handle tab change events for button visibility."""
        logger.debug(f"Tab changed to index {index}")
        total = self.tab_widget.count()
        self.prev_tab_button.setEnabled(index > 0)

        # Find the correct QHBoxLayout holding the buttons
        bottom_layout = None
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if isinstance(item, QHBoxLayout):
                widget_texts = []
                for j in range(item.count()):
                    widget = item.itemAt(j).widget()
                    if isinstance(widget, QPushButton):
                        widget_texts.append(widget.text())
                if "< Previous" in widget_texts:
                    bottom_layout = item
                    break

        if not bottom_layout:
            logger.error("Could not find bottom button layout in _tab_changed")
            return


        stats_tab_index = 1 

        if index == stats_tab_index:  
            logger.debug("Showing 'Create Character' button on Stats tab")
            # Hide the next button if it's visible
            if self.next_tab_button.isVisible():
                bottom_layout.removeWidget(self.next_tab_button)
                self.next_tab_button.hide()

            # Show the create button
            if bottom_layout.indexOf(self.create_button) == -1:
                bottom_layout.addWidget(self.create_button)
            self.create_button.show()
            self._validate_form() 

        elif index < stats_tab_index:
            logger.debug(f"Showing 'Next' button on tab {index}")

            if self.create_button.isVisible():
                bottom_layout.removeWidget(self.create_button)
                self.create_button.hide()

            # Show the next button
            if bottom_layout.indexOf(self.next_tab_button) == -1:

                 stretch_index = -1
                 for i in range(bottom_layout.count()):
                     if bottom_layout.itemAt(i).spacerItem():
                         stretch_index = i
                         break
                 if stretch_index != -1:
                     insert_index = bottom_layout.indexOf(self.create_button)
                     if insert_index == -1: insert_index = stretch_index + 1 
                     bottom_layout.insertWidget(insert_index, self.next_tab_button)
                 else:  
                    bottom_layout.addWidget(self.next_tab_button)
            self.next_tab_button.show()
            self._validate_form()  

    def _finish_character_creation(self):
        """Final validation and show the start game button."""
        logger.info("Finalizing character creation")
        
        # Validate basic info again just in case
        if not self._validate_basic_info():
             logger.warning("Character creation finalization failed: Incomplete basic information")
             QMessageBox.warning(self, "Incomplete Information", "Please complete the basic character information on the first tab.")
             self.tab_widget.setCurrentIndex(0)
             return

        # Validate stats meet class requirements
        if not self.stat_allocation.meets_requirements():
            logger.warning("Character doesn't meet minimum stat requirements for selected class")
            result = QMessageBox.question(
                self,
                "Stat Requirements Not Met",
                "Your character doesn't meet the minimum stat requirements for the selected class. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if result == QMessageBox.No:
                logger.debug("User chose to return to stats tab to adjust requirements")
                self.tab_widget.setCurrentIndex(1) # Go to stats tab
                return
            else:
                logger.info("User chose to continue with character despite unmet stat requirements")

        # If all checks pass, display character confirmation and show start game button
        character_name = self.player_name_edit.text().strip()
        race = self.race_combo.currentText()
        class_name = self.path_combo.currentText()
        origin = self.origin_combo.currentText()
        
        logger.info(f"Character creation complete: {character_name} ({race} {class_name} from {origin})")
        
        message = f"Character Creation Complete!\n\n"
        message += f"Name: {character_name}\n"
        message += f"Race: {race}\n"
        message += f"Class: {class_name}\n"
        message += f"Origin: {origin}\n\n"
        message += f"Click 'Start Game' to begin your adventure or 'Cancel' to discard this character."
        
        QMessageBox.information(self, "Character Created", message)
        
        # Replace create button with start game button
        logger.debug("Replacing 'Create Character' button with 'Start Game' button")
        bottom_layout = None
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if isinstance(item, QHBoxLayout):
                widget_texts = []
                for j in range(item.count()):
                    widget = item.itemAt(j).widget()
                    if isinstance(widget, QPushButton):
                        widget_texts.append(widget.text())
                if "< Previous" in widget_texts:
                    bottom_layout = item
                    break
                    
        if bottom_layout:
            if bottom_layout.indexOf(self.create_button) != -1:
                bottom_layout.removeWidget(self.create_button)
                self.create_button.hide()
                
            if bottom_layout.indexOf(self.start_game_button) == -1:
                bottom_layout.addWidget(self.start_game_button)
            self.start_game_button.show()
            self.start_game_button.setFocus()
            logger.debug("'Start Game' button displayed and focused")
        else:
            logger.error("Could not find bottom button layout to replace buttons")

    def _start_new_game(self):
        """Accept the dialog to start a new game with the created character."""
        logger.info("Starting new game with created character")
        self.accept()
        
    def _get_detailed_context_for_llm(self) -> Dict[str, Any]:
        """Gathers detailed context about race, class, and origin for LLM prompts."""
        context = {}
        config = get_config()

        # --- Race Details ---
        race_name = self.race_combo.currentText()
        race_data = config.get(f"races.{race_name}", {}) # Assumes race name is key
        if not race_data: # Fallback if name isn't key
             all_races = config.get_all("races")
             race_data = next((r for r in all_races.values() if r.get("name") == race_name), {})

        context['race'] = {
            "name": race_name,
            "description": race_data.get('description', 'No description available.'),
            "traits": [f"{t.get('name', 'Unknown')}: {t.get('description', '-')}" for t in race_data.get('traits', [])]
        }

        # --- Class Details ---
        class_name = self.path_combo.currentText()
        class_data = config.get(f"classes.{class_name}", {}) # Assumes class name is key
        if not class_data: # Fallback if name isn't key
            all_classes = config.get_all("classes")
            class_data = next((c for c in all_classes.values() if c.get("name") == class_name), {})

        context['class'] = {
            "name": class_name,
            "description": class_data.get('description', 'No description available.'),
            "recommended_stats": class_data.get('recommended_stats', {}).get('primary', []),
            # Add proficiencies if needed:
            # "weapon_proficiencies": class_data.get('weapon_proficiencies', []),
            # "armor_proficiencies": class_data.get('armor_proficiencies', []),
        }

        # --- Origin Details ---
        origin_id = self.origin_combo.currentData()
        origin_data = self.selected_origin_data # Use stored data from selection
        if origin_data and origin_data.get('id') == origin_id:
            context['origin'] = {
                "name": origin_data.get('name', 'Unknown Origin'),
                "description": origin_data.get('description', 'No description available.'),
                "location": origin_data.get('starting_location_id', 'Unknown Location'), # Location ID
                # Add traits and skills if useful for context
                "traits": [f"{t.get('name', 'Unknown')}: {t.get('description', '-')}" for t in origin_data.get('origin_traits', [])],
                "skills": origin_data.get('skill_proficiencies', [])
            }
        else:
            context['origin'] = {"name": self.origin_combo.currentText(), "description": "Details unavailable."}


        # --- Character Info ---
        context['character'] = {
             "name": self.player_name_edit.text().strip(),
             "sex": self.sex_combo.currentText()
        }

        # --- Allocated Stats ---
        # Get base stats AFTER allocation for context (important!)
        if hasattr(self, 'stat_allocation'):
             context['stats'] = self.stat_allocation.get_allocated_stats() # Get base allocated stats

        return context

    def _format_context_for_llm_prompt(self, detailed_context: Dict[str, Any]) -> str:
        """Formats the detailed context into a string for the LLM prompt."""
        prompt_parts = ["Character Context:\n"]

        # Character Basics
        char_info = detailed_context.get('character', {})
        prompt_parts.append(f"- Name: {char_info.get('name', '(Not Set)')}")
        prompt_parts.append(f"- Sex: {char_info.get('sex', 'Unknown')}")

        # Race
        race_info = detailed_context.get('race', {})
        prompt_parts.append(f"\nRace: {race_info.get('name', 'Unknown')}")
        prompt_parts.append(f"  - Description: {race_info.get('description', 'N/A')}")
        if race_info.get('traits'):
            prompt_parts.append("  - Traits:")
            for trait in race_info['traits']:
                prompt_parts.append(f"    - {trait}")

        # Class
        class_info = detailed_context.get('class', {})
        prompt_parts.append(f"\nClass: {class_info.get('name', 'Unknown')}")
        prompt_parts.append(f"  - Description: {class_info.get('description', 'N/A')}")
        if class_info.get('recommended_stats'):
            prompt_parts.append(f"  - Recommended Primary Stats: {', '.join(class_info['recommended_stats'])}")

        # Origin
        origin_info = detailed_context.get('origin', {})
        prompt_parts.append(f"\nOrigin: {origin_info.get('name', 'Unknown')}")
        prompt_parts.append(f"  - Description: {origin_info.get('description', 'N/A')}")
        prompt_parts.append(f"  - Starting Location ID: {origin_info.get('location', 'N/A')}")
        if origin_info.get('skills'):
             prompt_parts.append(f"  - Origin Skills: {', '.join(origin_info['skills'])}")
        if origin_info.get('traits'):
            prompt_parts.append("  - Origin Traits:")
            for trait in origin_info['traits']:
                 prompt_parts.append(f"    - {trait}")

        # Allocated Stats
        stats_info = detailed_context.get('stats', {})
        if stats_info:
            prompt_parts.append("\nAllocated Base Stats:")
            stat_strs = [f"{name}: {val}" for name, val in sorted(stats_info.items())]
            prompt_parts.append(f"  - {', '.join(stat_strs)}")

        return "\n".join(prompt_parts)

    # --- New Slot for Icon Updates ---
    @Slot()
    def _update_icons_on_selection_change(self):
        """Calls scan_character_icons with current selections."""
        race = self.race_combo.currentText()
        class_name = self.path_combo.currentText()
        sex = self.sex_combo.currentText()
        self.scan_character_icons(race, class_name, sex)