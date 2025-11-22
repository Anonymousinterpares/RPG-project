# gui/dialogs/new_game_dialog.py

from typing import Any, Optional, List, Dict

from PySide6.QtWidgets import (QComboBox,QMessageBox)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap
from core.base.config import get_config
from core.utils.logging_config import get_logger
from gui.dialogs.base_dialog import BaseDialog

# Get logger for this module
logger = get_logger(__name__)

class NewGameDialog(BaseDialog):
    """Dialog for creating a new game character using the Origin system."""

    def __init__(self, parent=None):
        """Initialize the new game dialog."""
        super().__init__(parent)

        # Set window properties
        self.setWindowTitle("Create New Character")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        # --- THIS SECTION IS FOR DATA LOADING ONLY ---
        self.available_races = self._load_races()
        self.available_classes = self._load_classes()
        self.available_origins = self._load_origins()
        self.available_sexes = ["Male", "Female", "Other"]
        self.character_icons = []
        self.current_icon_index = 0
        self.llm_enabled = True
        self.selected_icon_path = None
        self.selected_origin_data = None

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

    def scan_character_icons(self):
        """
        Placeholder for icon scanning. The detailed implementation is in the
        CharacterCreationDialog subclass. This base version does nothing to
        avoid errors during initialization.
        """
        # This method is intentionally left empty in the base class.
        # It prevents the TypeError when the constructor calls it.
        logger.debug("Base NewGameDialog.scan_character_icons() called (placeholder).")
        pass

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