# gui/dialogs/new_game_dialog.py

import os
import json
import logging
from typing import Any, Optional, List, Dict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QGroupBox, QTextEdit, QMessageBox, QFormLayout,
    QCheckBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap
from core.base.config import get_config

# Get logger for this module
logger = logging.getLogger(__name__)

class NewGameDialog(QDialog):
    """Dialog for creating a new game character using the Origin system."""

    def __init__(self, parent=None):
        """Initialize the new game dialog."""
        super().__init__(parent)

        # Set window properties
        self.setWindowTitle("Create New Character")
        self.setMinimumWidth(700) # Increased width for more details
        self.setMinimumHeight(600) # Increased height
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
                padding-top: 3px; /* Add some vertical space */
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
                margin-top: 10px; /* Reduced margin */
                padding-top: 10px; /* Add padding inside */
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px 0 10px;
                color: #E0E0E0;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            #OriginDetailsLabel { /* Style for the details labels */
                color: #CCCCCC;
                padding-left: 5px;
            }
        """)

        # Load data dynamically
        self.available_races = self._load_races()
        self.available_classes = self._load_classes()
        self.available_origins = self._load_origins() # Load origins instead of backgrounds
        self.available_sexes = ["Male", "Female", "Other"] # Added 'Other'

        # Set up character icon browsing
        self.character_icons = []
        self.current_icon_index = 0
        self.scan_character_icons()

        # Default to LLM enabled
        self.llm_enabled = True
        self.selected_icon_path = None
        self.selected_origin_data = None # Store full data of selected origin

        # Set up the UI
        self._setup_ui()

        # Connect signals
        self._connect_signals()

        # Initial validation
        self._validate_form()

    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10) # Reduced spacing

        # Layout for character details (info, description) and portrait
        details_layout = QHBoxLayout()
        details_layout.setSpacing(15)

        # --- Left Column: Info, Origin Details, Description ---
        left_column_widget = QWidget() # Create a widget for the scroll area
        left_column_layout = QVBoxLayout(left_column_widget)
        left_column_layout.setContentsMargins(0,0,0,0)
        left_column_layout.setSpacing(10)

        # --- Character Info Group ---
        info_group = QGroupBox("Character Information")
        info_layout = QFormLayout(info_group)
        info_layout.setContentsMargins(15, 25, 15, 15) # Adjusted margins
        info_layout.setSpacing(8) # Reduced spacing

        self.player_name_edit = QLineEdit()
        self.player_name_edit.setPlaceholderText("Enter your character's name...")
        info_layout.addRow("Name:", self.player_name_edit)

        self.race_combo = QComboBox()
        self._populate_combo(self.race_combo, self.available_races, "Races")
        info_layout.addRow("Race:", self.race_combo)

        self.path_combo = QComboBox() # Represents Class
        self._populate_combo(self.path_combo, self.available_classes, "Classes")
        info_layout.addRow("Class:", self.path_combo)

        # --- Origin Selection (Replaces Background) ---
        self.origin_combo = QComboBox()
        self._populate_origin_combo() # Custom population method
        info_layout.addRow("Origin:", self.origin_combo)
        # --- End Origin Selection ---

        self.sex_combo = QComboBox()
        self._populate_combo(self.sex_combo, self.available_sexes, "Sexes")
        info_layout.addRow("Sex:", self.sex_combo)

        self.llm_checkbox = QCheckBox("Enable LLM (AI processing)")
        self.llm_checkbox.setChecked(self.llm_enabled)
        info_layout.addRow("", self.llm_checkbox)
        left_column_layout.addWidget(info_group)

        # --- Origin Details Group (NEW) ---
        origin_details_group = QGroupBox("Origin Details")
        origin_details_layout = QVBoxLayout(origin_details_group)
        origin_details_layout.setContentsMargins(15, 25, 15, 15)
        origin_details_layout.setSpacing(8)

        self.origin_desc_label = QLabel("Select an Origin to see details.")
        self.origin_desc_label.setObjectName("OriginDetailsLabel")
        self.origin_desc_label.setWordWrap(True)
        self.origin_desc_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        origin_details_layout.addWidget(QLabel("<b>Description:</b>"))
        origin_details_layout.addWidget(self.origin_desc_label)

        self.origin_skills_label = QLabel("-")
        self.origin_skills_label.setObjectName("OriginDetailsLabel")
        self.origin_skills_label.setWordWrap(True)
        origin_details_layout.addWidget(QLabel("<b>Skill Proficiencies:</b>"))
        origin_details_layout.addWidget(self.origin_skills_label)

        self.origin_traits_label = QLabel("-")
        self.origin_traits_label.setObjectName("OriginDetailsLabel")
        self.origin_traits_label.setWordWrap(True)
        self.origin_traits_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        origin_details_layout.addWidget(QLabel("<b>Origin Traits:</b>"))
        origin_details_layout.addWidget(self.origin_traits_label)
        origin_details_layout.addStretch() # Push details up
        left_column_layout.addWidget(origin_details_group)


        # --- Description Group (Backstory) ---
        description_group = QGroupBox("Character Backstory (Optional Seed)")
        description_layout = QVBoxLayout(description_group)
        description_layout.setContentsMargins(15, 25, 15, 15)
        description_layout.setSpacing(5)

        description_label = QLabel("Optionally edit the text below (based on selected Origin) to guide the LLM background generation:")
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #AAAAAA; font-style: italic;")

        self.description_edit = QTextEdit() # Player editable backstory seed
        self.description_edit.setPlaceholderText("Select an Origin to load starting text...")
        self.description_edit.setMinimumHeight(100) # Ensure decent height

        description_layout.addWidget(description_label)
        description_layout.addWidget(self.description_edit)
        left_column_layout.addWidget(description_group)
        left_column_layout.addStretch(1) # Add stretch to push content up

        # --- Add Left Column Scroll Area ---
        left_scroll_area = QScrollArea()
        left_scroll_area.setWidgetResizable(True)
        left_scroll_area.setWidget(left_column_widget)


        # --- Right Column: Portrait ---
        right_column_widget = QWidget()
        right_column_layout = QVBoxLayout(right_column_widget)
        right_column_layout.setContentsMargins(0,0,0,0)
        right_column_layout.setSpacing(10)

        icon_group = QGroupBox("Character Portrait")
        icon_layout = QVBoxLayout(icon_group)
        icon_layout.setContentsMargins(15, 25, 15, 15)
        icon_layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(150, 150) # Fixed size for portrait
        self.icon_label.setStyleSheet("background-color: #1E1E1E; border: 1px solid #3F3F46;")
        self.icon_label.setText("No image")
        icon_layout.addWidget(self.icon_label, 0, Qt.AlignCenter) # Center the label

        nav_layout = QHBoxLayout()
        self.prev_icon_button = QPushButton("←")
        self.icon_counter_label = QLabel("0 / 0")
        self.icon_counter_label.setAlignment(Qt.AlignCenter)
        self.next_icon_button = QPushButton("→")
        nav_layout.addWidget(self.prev_icon_button)
        nav_layout.addWidget(self.icon_counter_label)
        nav_layout.addWidget(self.next_icon_button)
        icon_layout.addLayout(nav_layout)

        portrait_hint = QLabel("Browse available character portraits")
        portrait_hint.setStyleSheet("color: #888888; font-style: italic;")
        portrait_hint.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(portrait_hint)
        right_column_layout.addWidget(icon_group)
        right_column_layout.addStretch(1) # Push portrait group up


        # Add columns to main details layout
        details_layout.addWidget(left_scroll_area, 3)  # Left column takes more space
        details_layout.addWidget(right_column_widget, 1) # Right column for portrait

        main_layout.addLayout(details_layout, 1) # Make details layout stretch

        # --- Dialog Buttons ---
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        self.cancel_button = QPushButton("Cancel")
        self.create_button = QPushButton("Create Character")
        self.create_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.create_button)
        main_layout.addLayout(button_layout)

    def _populate_combo(self, combo: QComboBox, items: List[str], item_type: str):
        """Helper to populate QComboBox and handle empty lists."""
        if not items:
            combo.addItem(f"No {item_type} Found")
            combo.setEnabled(False)
        else:
            combo.addItems(items)
            combo.setEnabled(True)

    def _populate_origin_combo(self):
        """Populate the Origin combo box."""
        combo = self.origin_combo
        items = self.available_origins
        item_type = "Origins"

        combo.clear() # Clear previous items
        if not items:
            combo.addItem(f"No {item_type} Found")
            combo.setEnabled(False)
        else:
            combo.addItem("--- Select an Origin ---", None) # Placeholder item
            for origin_data in items:
                # Add item with name as text and id as data
                combo.addItem(origin_data.get('name', 'Unknown Origin'), origin_data.get('id'))
            combo.setEnabled(True)

    @Slot(int)
    def _on_origin_selected(self, index: int):
        """Update details display when an origin is selected."""
        self.selected_origin_data = None # Reset selected data
        origin_id = self.origin_combo.itemData(index)

        if origin_id is None: # Handle placeholder selection
            self.origin_desc_label.setText("Select an Origin to see details.")
            self.origin_skills_label.setText("-")
            self.origin_traits_label.setText("-")
            self.description_edit.setPlainText("") # Clear backstory seed
            self.description_edit.setPlaceholderText("Select an Origin to load starting text...")
            self._validate_form() # Re-validate as origin is deselected
            return

        # Find the full origin data using the ID
        origin = next((o for o in self.available_origins if o.get('id') == origin_id), None)

        if origin:
            self.selected_origin_data = origin # Store the full data
            self.origin_desc_label.setText(origin.get('description', 'No description available.'))

            # Format skills
            skills = origin.get('skill_proficiencies', [])
            self.origin_skills_label.setText(", ".join(skills) if skills else "None")

            # Format traits
            traits = origin.get('origin_traits', [])
            traits_text = ""
            if traits:
                trait_lines = [f"<b>{t.get('name', 'Unnamed Trait')}:</b> {t.get('description', 'No description.')}" for t in traits]
                traits_text = "<br>".join(trait_lines) # Use HTML for formatting
            else:
                traits_text = "None"
            self.origin_traits_label.setText(traits_text)

            # Pre-populate backstory seed if empty
            if not self.description_edit.toPlainText().strip():
                 self.description_edit.setPlainText(origin.get('introduction_text', ''))

        else:
            # Handle case where origin ID is found but data isn't (shouldn't happen)
            self.origin_desc_label.setText("Error: Could not load details.")
            self.origin_skills_label.setText("-")
            self.origin_traits_label.setText("-")
            self.description_edit.setPlainText("")
            logger.error(f"Could not find origin data for ID: {origin_id}")

        self._validate_form() # Re-validate after selection change


    def _toggle_llm(self, state):
        """Toggle LLM enabled state."""
        self.llm_enabled = bool(state)

    def _load_races(self) -> List[str]:
        """Load race names from the configuration."""
        races = [] # Start empty, rely on config
        try:
            config = get_config()
            loaded_races_data = config.get_all("races")
            if loaded_races_data:
                race_names = sorted([data.get('name', race_id) for race_id, data in loaded_races_data.items()])
                if race_names:
                    races = race_names
                    logger.info(f"Loaded {len(races)} races from config.")
                else:
                    logger.warning("No race names found in loaded race data.")
            else:
                logger.warning("Race configuration domain ('races') not found or empty.")
        except Exception as e:
            logger.error(f"Error loading races from config: {e}.")
        return races if races else ["Human"] # Fallback if loading fails

    def _load_classes(self) -> List[str]:
        """Load class names from the configuration."""
        classes = [] # Start empty
        try:
            config = get_config()
            loaded_classes_data = config.get_all("classes")
            if loaded_classes_data:
                class_names = sorted([data.get('name', class_id) for class_id, data in loaded_classes_data.items()])
                if class_names:
                    classes = class_names
                    logger.info(f"Loaded {len(classes)} classes from config.")
                else:
                    logger.warning("No class names found in loaded class data.")
            else:
                logger.warning("Class configuration domain ('classes') not found or empty.")
        except Exception as e:
            logger.error(f"Error loading classes from config: {e}.")
        return classes if classes else ["Wanderer"] # Fallback

    def _load_origins(self) -> List[Dict[str, Any]]:
        """Load origin data (id and name initially) from configuration."""
        origins_data = []
        try:
            config = get_config()
            # Assuming origins.json is loaded under the 'origins' key
            loaded_origins_dict = config.get_all("origins")
            if loaded_origins_dict and isinstance(loaded_origins_dict, dict):
                 # Store the full data for later lookup
                origins_data = list(loaded_origins_dict.values())
                # Sort by name for display
                origins_data.sort(key=lambda x: x.get('name', 'Unknown Origin'))
                logger.info(f"Loaded {len(origins_data)} origins from config.")
            else:
                logger.warning("Origin configuration domain ('origins') not found or empty.")
        except Exception as e:
            logger.error(f"Error loading origins from config: {e}.")
        return origins_data

    def scan_character_icons(self, race: str, class_name: str, sex: str):
        """
        Scan for character icons in the specific race/class directory
        and filter based on sex.
        """
        self.character_icons = [] # Clear previous icons
        self.current_icon_index = 0

        if not race or not class_name or not sex or "No " in race or "No " in class_name: # Added check for placeholder text
            logger.warning(f"Cannot scan icons: Race ('{race}'), Class ('{class_name}'), or Sex ('{sex}') not validly selected.")
            self._display_current_icon() # Display "No Icons Found" or similar
            return

        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            # Construct specific directory path (e.g., images/character_icons/Human_Warrior)
            safe_race = race.replace(" ", "_")
            safe_class_name = class_name.replace(" ", "_")
            specific_icons_dir = os.path.join(project_root, "images", "character_icons", f"{safe_race}_{safe_class_name}")
            logger.debug(f"Scanning for icons in specific directory: {specific_icons_dir}")

            if not os.path.exists(specific_icons_dir):
                logger.warning(f"Icon directory not found: {specific_icons_dir}")
                self._display_current_icon() # Display "No Icons Found"
                return

            supported_extensions = [".png", ".jpg", ".jpeg", ".gif", ".svg"]

            # Scan and filter files
            for filename in os.listdir(specific_icons_dir):
                if any(filename.lower().endswith(ext) for ext in supported_extensions):
                    name_part_lower = os.path.splitext(filename)[0].lower()
                    sex_lower = sex.lower()
                    include_file = False

                    contains_male_keyword = "male" in name_part_lower
                    contains_female_keyword = "female" in name_part_lower

                    if sex_lower == "male":
                        # Include if "male" is present AND "female" is NOT present
                        if contains_male_keyword and not contains_female_keyword:
                            include_file = True
                    elif sex_lower == "female":
                        # Include if "female" is present
                        if contains_female_keyword:
                            include_file = True
                    elif sex_lower == "other":
                        # Include if either "male" or "female" is present
                        if contains_male_keyword or contains_female_keyword:
                            include_file = True
                    
                    if include_file:
                        file_path = os.path.join(specific_icons_dir, filename)
                        self.character_icons.append({
                            "filename": filename,
                            "path": file_path
                        })

            # Sort the icons by filename
            self.character_icons.sort(key=lambda x: x["filename"])

            logger.info(f"Found {len(self.character_icons)} suitable icons in {specific_icons_dir} for sex '{sex}'.")

        except OSError as e:
            logger.error(f"Error reading icons directory {specific_icons_dir}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scanning icons: {e}", exc_info=True)

        # Display the first found icon (or "No Icons Found")
        self._display_current_icon()
    def _connect_signals(self):
        """Connect signals to slots."""
        self.player_name_edit.textChanged.connect(self._validate_form)
        self.race_combo.currentIndexChanged.connect(self._validate_form)
        self.path_combo.currentIndexChanged.connect(self._validate_form)
        self.origin_combo.currentIndexChanged.connect(self._validate_form) # Validate on origin change too
        self.origin_combo.currentIndexChanged.connect(self._on_origin_selected) # Update details on change

        self.llm_checkbox.stateChanged.connect(self._toggle_llm)
        self.prev_icon_button.clicked.connect(self._show_previous_icon)
        self.next_icon_button.clicked.connect(self._show_next_icon)

        self.cancel_button.clicked.connect(self.reject)
        self.create_button.clicked.connect(self.accept)

    def _validate_form(self):
        """Validate the form and enable/disable the create button."""
        has_name = bool(self.player_name_edit.text().strip())
        race_selected = self.race_combo.isEnabled() and self.race_combo.currentIndex() >= 0 # Check index too
        class_selected = self.path_combo.isEnabled() and self.path_combo.currentIndex() >= 0
        # Check if a valid origin (not the placeholder) is selected
        origin_selected = self.origin_combo.isEnabled() and self.origin_combo.currentIndex() > 0

        self.create_button.setEnabled(
            has_name and
            race_selected and
            class_selected and
            origin_selected
        )

    def _show_previous_icon(self):
        """Show the previous character icon."""
        # (Keep existing implementation)
        if not self.character_icons: return
        self.current_icon_index = (self.current_icon_index - 1 + len(self.character_icons)) % len(self.character_icons)
        self._display_current_icon()


    def _show_next_icon(self):
        """Show the next character icon."""
        # (Keep existing implementation)
        if not self.character_icons: return
        self.current_icon_index = (self.current_icon_index + 1) % len(self.character_icons)
        self._display_current_icon()

    def _display_current_icon(self):
        """Display the current character icon."""
        # (Keep existing implementation, ensure counter updates)
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

    def get_character_data(self) -> Optional[Dict[str, Any]]:
        """Get the character data from the form, including origin_id."""
        name = self.player_name_edit.text().strip()
        race = self.race_combo.currentText() if self.race_combo.isEnabled() else None
        path = self.path_combo.currentText() if self.path_combo.isEnabled() else None
        origin_id = self.origin_combo.currentData() if self.origin_combo.isEnabled() else None # Get origin ID from data

        # Basic validation
        if not name or not race or not path or origin_id is None: # Check origin_id too
             logger.error("Cannot get character data: Name, Race, Class, or Origin is missing or invalid.")
             QMessageBox.warning(self, "Missing Information", "Please select a valid Race, Class, and Origin.")
             return None

        data = {
            'name': name,
            'race': race,
            'path': path,
            'origin_id': origin_id, # Add origin ID
            'sex': self.sex_combo.currentText(),
            # Use edited description if provided, otherwise use the original intro text from selected origin
            'description': self.description_edit.toPlainText().strip() if self.description_edit.toPlainText().strip() else (self.selected_origin_data.get('introduction_text', '') if self.selected_origin_data else ''),
            'use_llm': self.llm_enabled,
            'character_image': self.selected_icon_path
        }

        return data