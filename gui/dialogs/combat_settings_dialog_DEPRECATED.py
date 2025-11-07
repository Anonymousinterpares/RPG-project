# gui/dialogs/combat_settings_dialog.py

import os
import logging
from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QGroupBox, QDialogButtonBox, QFontDialog, QColorDialog,
    QFrame, QScrollArea, QSpinBox
)
from PySide6.QtGui import QPixmap, QFont, QColor
from PySide6.QtCore import Qt, Slot

from gui.dialogs.base_dialog import BaseDialog

# Get logger for the dialog
logger = logging.getLogger("GUI") # Use the same logger name as combat_display

class CombatSettingsDialog(BaseDialog):
    """Dialog for configuring Combat Display settings."""

    def __init__(self, current_settings: Dict[str, Any], image_dir: str, parent: Optional[QWidget] = None):
        """Initialize the settings dialog."""
        super().__init__(parent)
        self.setWindowTitle("Combat Display Settings")
        self.setMinimumHeight(600)
        self.setMinimumWidth(850)

        self.settings = current_settings.copy()
        self.image_dir = image_dir
        self.available_images: List[str] = []
        self.current_image_index: int = -1
        self.color_buttons: Dict[str, QPushButton] = {}

        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()

        # Left side for Background and Fonts
        left_v_layout = QVBoxLayout()
        left_v_layout.addWidget(self._setup_background_section())
        left_v_layout.addWidget(self._setup_font_section())
        left_v_layout.addStretch()
        top_layout.addLayout(left_v_layout, 1)

        # Right side for Colors
        color_group = self._setup_color_section()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(color_group)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        top_layout.addWidget(scroll_area, 1)

        main_layout.addLayout(top_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self._load_settings_to_ui()

    # --- Section Setup Methods ---

    def _setup_background_section(self) -> QGroupBox:
        """Create the GroupBox for background image settings."""
        group = QGroupBox("Main Background Image") # Renamed for clarity
        layout = QVBoxLayout(group)
        h_layout = QHBoxLayout() # Layout for controls

        # Image Preview
        self.bg_preview_label = QLabel("No Image Selected")
        self.bg_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bg_preview_label.setFixedSize(200, 112) # 16:9 aspect ratio approx
        self.bg_preview_label.setFrameShape(QFrame.Shape.StyledPanel)
        self.bg_preview_label.setStyleSheet("background-color: #333;") # Dark background for preview

        # Controls Layout
        controls_layout = QVBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Image Filename Label
        self.bg_filename_label = QLabel("Current: None")
        self.bg_filename_label.setWordWrap(True)
        controls_layout.addWidget(self.bg_filename_label)

        # Navigation Buttons
        nav_layout = QHBoxLayout()
        prev_button = QPushButton("< Prev") # Use standard characters
        prev_button.setToolTip("Select previous background image")
        prev_button.clicked.connect(self._browse_image_left)
        next_button = QPushButton("Next >") # Use standard characters
        next_button.setToolTip("Select next background image")
        next_button.clicked.connect(self._browse_image_right)
        nav_layout.addWidget(prev_button)
        nav_layout.addWidget(next_button)
        controls_layout.addLayout(nav_layout)

        # Clear Button
        clear_button = QPushButton("Clear Background")
        clear_button.setToolTip("Remove background image selection")
        clear_button.clicked.connect(self._clear_background)
        controls_layout.addWidget(clear_button)

        # Add preview and controls to horizontal layout
        h_layout.addWidget(self.bg_preview_label)
        h_layout.addLayout(controls_layout)
        layout.addLayout(h_layout)

        # Scan for available images
        self._scan_images()

        return group

    def _setup_font_section(self) -> QGroupBox:
        """Create the GroupBox for all font and header settings."""
        group = QGroupBox("Fonts & Headers")
        layout = QFormLayout(group)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # --- Header Font ---
        header_font_button = QPushButton("Choose Header Font...")
        header_font_button.clicked.connect(self._choose_header_font)
        self.header_font_preview = QLabel("Header Preview")
        header_font_layout = QHBoxLayout()
        header_font_layout.addWidget(header_font_button)
        header_font_layout.addWidget(self.header_font_preview)
        layout.addRow("Panel Headers:", header_font_layout)

        # --- Header Vertical Offset ---
        self.header_offset_spinbox = QSpinBox()
        self.header_offset_spinbox.setRange(0, 50)
        self.header_offset_spinbox.setSuffix(" px")
        self.header_offset_spinbox.setToolTip("Sets the vertical space between a header and the content below it.")
        layout.addRow("Header Vertical Offset:", self.header_offset_spinbox)

        # --- Log Font ---
        log_font_button = QPushButton("Choose Log Font...")
        log_font_button.clicked.connect(self._choose_log_font)
        self.log_font_preview = QLabel("Combat Log Preview")
        log_font_layout = QHBoxLayout()
        log_font_layout.addWidget(log_font_button)
        log_font_layout.addWidget(self.log_font_preview)
        layout.addRow("Combat Log:", log_font_layout)

        return group

    def _setup_color_section(self) -> QGroupBox:
        """Create the GroupBox for color settings, organized into columns."""
        group = QGroupBox("Color Settings")
        main_h_layout = QHBoxLayout(group)

        categories = {
            "Log General": [
                "color_log_default", "color_log_header", "color_log_dev",
                "color_log_system_message", "color_log_narrative", "color_log_combat_event",
                "color_log_group_bg", "color_log_text_bg"
            ],
            "Log Specific Events": [
                "color_log_damage", "color_log_heal", "color_log_crit", "color_log_miss",
                "color_log_roll", "color_log_turn", "color_log_round"
            ],
            "Entity Display": [
                "color_entity_player_bg", "color_entity_player_border",
                "color_entity_player_bg_active", "color_entity_player_border_active",
                "color_entity_enemy_bg", "color_entity_enemy_border",
                "color_entity_enemy_bg_active", "color_entity_enemy_border_active"
            ],
            "Progress Bars": [
                "color_hp_bar_chunk_normal", "color_hp_bar_chunk_low", "color_hp_bar_chunk_critical",
                "color_hp_bar_chunk_normal_bleak", "color_hp_bar_chunk_low_bleak", "color_hp_bar_chunk_critical_bleak",
                "color_stamina_bar_chunk", "color_stamina_bar_chunk_bleak",
                "color_mana_bar_chunk", "color_mana_bar_chunk_bleak", # Added Mana Bleak
                "color_resolve_bar_chunk", "color_progressbar_text", "color_progressbar_bg"
            ],
            "Section & UI Text": [
                "color_player_group_bg", "color_enemies_group_bg",
                "color_groupbox_title_text", "color_groupbox_title_bg",
                "color_status_text", "color_round_text"
            ]
        }

        for category_name, keys in categories.items():
            valid_keys_in_category = [k for k in keys if k in self.settings]
            if not valid_keys_in_category:
                continue

            category_v_layout = QVBoxLayout()
            category_v_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            category_label = QLabel(f"<b>{category_name}</b>")
            category_v_layout.addWidget(category_label)

            form_layout = QFormLayout()
            form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
            form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)


            valid_keys_in_category.sort() 

            for key in valid_keys_in_category:
                label_text_parts = key.replace("color_", "").replace("_", " ").split(" ")
                # Capitalize each part and join
                label_text = " ".join([part.capitalize() for part in label_text_parts]) + ":"
                
                # Specific label overrides for better readability
                if key == "color_log_default": label_text = "Log Default Text:"
                elif key == "color_log_header": label_text = "Log Header Text:"
                elif key == "color_log_dev": label_text = "Log Dev Message:"
                elif key == "color_log_system_message": label_text = "Log System Message:"
                elif key == "color_log_narrative": label_text = "Log Narrative/GM Text:"
                elif key == "color_log_combat_event": label_text = "Log Major Combat Event:"
                elif key == "color_log_group_bg": label_text = "Log Section BG:"
                elif key == "color_log_text_bg": label_text = "Log Text Area BG:"
                elif key == "color_log_damage": label_text = "Log Damage Text:"
                elif key == "color_log_heal": label_text = "Log Heal Text:"
                elif key == "color_log_crit": label_text = "Log Critical Hit:"
                elif key == "color_log_miss": label_text = "Log Miss/Fail:"
                elif key == "color_log_roll": label_text = "Log Dice Roll:"
                elif key == "color_log_turn": label_text = "Log Turn Change:"
                elif key == "color_log_round": label_text = "Log Round Change:"
                elif key == "color_entity_player_bg": label_text = "Player Entity BG:"
                elif key == "color_entity_player_border": label_text = "Player Entity Border:"
                elif key == "color_entity_player_bg_active": label_text = "Player Active BG:"
                elif key == "color_entity_player_border_active": label_text = "Player Active Border:"
                elif key == "color_entity_enemy_bg": label_text = "Enemy Entity BG:"
                elif key == "color_hp_bar_chunk_normal": label_text = "HP Bar Normal:"
                elif key == "color_hp_bar_chunk_low": label_text = "HP Bar Low:"
                elif key == "color_hp_bar_chunk_critical": label_text = "HP Bar Critical:"
                elif key == "color_hp_bar_chunk_normal_bleak": label_text = "HP Bar Normal (Bleak):"
                elif key == "color_hp_bar_chunk_low_bleak": label_text = "HP Bar Low (Bleak):"
                elif key == "color_hp_bar_chunk_critical_bleak": label_text = "HP Bar Critical (Bleak):"
                elif key == "color_stamina_bar_chunk": label_text = "Stamina Bar:"
                elif key == "color_stamina_bar_chunk_bleak": label_text = "Stamina Bar (Bleak):"
                elif key == "color_mana_bar_chunk": label_text = "Mana Bar:" # Added Mana Bar
                elif key == "color_mana_bar_chunk_bleak": label_text = "Mana Bar (Bleak):" # Added Mana Bar Bleak
                elif key == "color_resolve_bar_chunk": label_text = "Resolve Bar:"
                elif key == "color_progressbar_text": label_text = "Progress Bar Text:"
                elif key == "color_progressbar_bg": label_text = "Progress Bar BG:"
                elif key == "color_player_group_bg": label_text = "Player Section BG:"
                elif key == "color_enemies_group_bg": label_text = "Enemies Section BG:"
                elif key == "color_groupbox_title_text": label_text = "Section Title Text:"
                elif key == "color_groupbox_title_bg": label_text = "Section Title BG:"
                elif key == "color_status_text": label_text = "Status Label Text:"
                elif key == "color_round_text": label_text = "Round Label Text:"


                color_button = self._create_color_button(key)
                form_layout.addRow(label_text, color_button)
                self.color_buttons[key] = color_button

            category_v_layout.addLayout(form_layout)
            main_h_layout.addLayout(category_v_layout)

        main_h_layout.addStretch()
        return group
    # --- Helper Methods ---

    def _scan_images(self):
        """Scan the image directory for valid image files."""
        self.available_images = []
        try:
            if os.path.isdir(self.image_dir):
                for filename in sorted(os.listdir(self.image_dir)):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                        self.available_images.append(filename)
                logger.info(f"Found {len(self.available_images)} images in {self.image_dir}")
            else:
                logger.warning(f"Image directory not found: {self.image_dir}")
        except OSError as e:
            logger.error(f"Error scanning image directory {self.image_dir}: {e}")

    def _update_background_preview(self):
        """Update the background image preview label and filename."""
        if 0 <= self.current_image_index < len(self.available_images):
            relative_path = self.available_images[self.current_image_index]
            full_path = os.path.join(self.image_dir, relative_path)
            pixmap = QPixmap(full_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(self.bg_preview_label.size(),
                                              Qt.AspectRatioMode.KeepAspectRatioByExpanding, # Fill the space better
                                              Qt.TransformationMode.SmoothTransformation)
                # Crop the pixmap to the label size after scaling
                rect = scaled_pixmap.rect()
                rect.setSize(self.bg_preview_label.size())
                cropped_pixmap = scaled_pixmap.copy(rect)

                self.bg_preview_label.setPixmap(cropped_pixmap)
                self.bg_filename_label.setText(f"Current: {relative_path}")
                self.settings["background_image"] = relative_path # Store relative path
            else:
                logger.warning(f"Failed to load image: {full_path}")
                self._clear_background_ui() # Show error state
                self.bg_filename_label.setText(f"Error loading: {relative_path}")
        else:
            self._clear_background_ui()

    def _clear_background_ui(self):
        """Clear the background preview and filename label."""
        self.bg_preview_label.clear()
        self.bg_preview_label.setText("No Image Selected")
        self.bg_preview_label.setStyleSheet("background-color: #333;") # Reset background
        self.bg_filename_label.setText("Current: None")
        self.settings["background_image"] = None # Clear setting

    def _update_font_previews(self):
        """Update all font preview labels based on current settings."""
        # Header Preview
        header_family = self.settings.get("font_family_header", "Garamond")
        header_size = self.settings.get("font_size_header", 20)
        header_font = QFont(header_family, header_size)
        self.header_font_preview.setFont(header_font)
        self.header_font_preview.setText(f"{header_family}, {header_size}pt")

        # Log Preview
        log_family = self.settings.get("font_family_log", "Garamond")
        log_size = self.settings.get("font_size_log", 14)
        log_font = QFont(log_family, log_size)
        self.log_font_preview.setFont(log_font)
        self.log_font_preview.setText(f"{log_family}, {log_size}pt - Sample Text")

    def _create_color_button(self, setting_key: str) -> QPushButton:
        """Create a button for selecting a color."""
        button = QPushButton()
        button.setProperty("setting_key", setting_key) # Store key on button
        button.setToolTip(f"Click to change color for '{setting_key}'")
        button.setMinimumHeight(25)
        button.clicked.connect(self._choose_color)
        return button

    def _update_color_button_preview(self, button: QPushButton, color_value: str):
        """Update the appearance of a color selection button."""
        try:
            qcolor = QColor(color_value)
            if qcolor.isValid():
                # Set background color
                # Determine text color based on background brightness for readability
                brightness = (qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114) / 1000
                text_color = "#000000" if brightness > 128 else "#FFFFFF"
                # Combine styles
                button.setStyleSheet(f"background-color: {color_value}; color: {text_color}; border: 1px solid #888;") # Add border for definition
                button.setText(color_value) # Display the color value
            else:
                button.setText("Invalid Color")
                button.setStyleSheet("") # Reset style
        except Exception as e:
            logger.error(f"Error updating color button preview for '{color_value}': {e}")
            button.setText("Error")
            button.setStyleSheet("")

    def _load_settings_to_ui(self):
        """Load the initial settings values into the UI controls."""
        # Background
        current_bg = self.settings.get("background_image")
        if current_bg and self.available_images:
            try:
                self.current_image_index = self.available_images.index(current_bg)
            except ValueError:
                self.current_image_index = -1
        else:
            self.current_image_index = -1
        self._update_background_preview()

        # Font Previews and Offset
        self._update_font_previews()
        self.header_offset_spinbox.setValue(self.settings.get("header_vertical_offset", 5))

        # Colors
        for key, button in self.color_buttons.items():
            color_value = self.settings.get(key, "#ffffff")
            self._update_color_button_preview(button, color_value)

    # --- Slots ---

    @Slot()
    def _browse_image_left(self):
        """Select the previous image."""
        if not self.available_images: return
        self.current_image_index -= 1
        if self.current_image_index < 0:
            self.current_image_index = len(self.available_images) - 1 # Wrap around
        self._update_background_preview()

    @Slot()
    def _browse_image_right(self):
        """Select the next image."""
        if not self.available_images: return
        self.current_image_index += 1
        if self.current_image_index >= len(self.available_images):
            self.current_image_index = 0 # Wrap around
        self._update_background_preview()

    @Slot()
    def _clear_background(self):
        """Clear the background image selection."""
        self.current_image_index = -1
        self._update_background_preview()

    @Slot()
    def _choose_font(self):
        """Open the QFontDialog to select a font."""
        current_family = self.settings.get("font_family", "Arial")
        current_size = self.settings.get("font_size", 10)
        current_font = QFont(current_family, current_size)

        ok, font = QFontDialog.getFont(current_font, self, "Select Base Font")
        if ok:
            self.settings["font_family"] = font.family()
            self.settings["font_size"] = font.pointSize()
            self._update_font_preview() # Update the preview label

    @Slot()
    def _choose_color(self):
        """Open the QColorDialog to select a color for the clicked button."""
        sender_button = self.sender()
        if not isinstance(sender_button, QPushButton):
            return

        setting_key = sender_button.property("setting_key")
        if not setting_key:
            logger.warning("Color button clicked without a 'setting_key' property.")
            return

        current_color_value = self.settings.get(setting_key, "#000000")
        try:
            current_qcolor = QColor(current_color_value)
            if not current_qcolor.isValid():
                logger.warning(f"Invalid current color '{current_color_value}' for key '{setting_key}'. Defaulting to black.")
                current_qcolor = QColor("#000000")
        except Exception:
             logger.warning(f"Error parsing current color '{current_color_value}' for key '{setting_key}'. Defaulting to black.")
             current_qcolor = QColor("#000000")


        # Open color dialog, always allow alpha for background colors or if current value suggests it
        options = QColorDialog.ColorDialogOption(0)
        # Enable alpha if it's a background setting OR if the current color has alpha OR if it's an rgba string
        if "bg" in setting_key.lower() or current_qcolor.alpha() < 255 or 'rgba' in current_color_value.lower():
             options = QColorDialog.ColorDialogOption.ShowAlphaChannel

        new_color = QColorDialog.getColor(current_qcolor, self, f"Select Color for {setting_key}", options=options)

        if new_color.isValid():
            # Store color. Use RGBA string if alpha is not 255, otherwise use hex.
            if new_color.alpha() < 255:
                # Store rgba string directly as it's often more CSS friendly.
                # Use integer values for RGB, float for alpha
                rgba_string = f"rgba({new_color.red()}, {new_color.green()}, {new_color.blue()}, {new_color.alphaF():.3f})"
                self.settings[setting_key] = rgba_string
                self._update_color_button_preview(sender_button, rgba_string)
            else:
                hex_name = new_color.name(QColor.NameFormat.HexRgb) # Format like #RRGGBB
                self.settings[setting_key] = hex_name
                self._update_color_button_preview(sender_button, hex_name)

    @Slot()
    def _choose_header_font(self):
        """Open a font dialog to choose the header font."""
        current_family = self.settings.get("font_family_header", "Garamond")
        current_size = self.settings.get("font_size_header", 20)
        current_font = QFont(current_family, current_size)

        ok, font = QFontDialog.getFont(current_font, self, "Select Header Font")
        if ok:
            self.settings["font_family_header"] = font.family()
            self.settings["font_size_header"] = font.pointSize()
            self._update_font_previews()

    @Slot()
    def _choose_log_font(self):
        """Open a font dialog to choose the combat log font."""
        current_family = self.settings.get("font_family_log", "Garamond")
        current_size = self.settings.get("font_size_log", 14)
        current_font = QFont(current_family, current_size)

        ok, font = QFontDialog.getFont(current_font, self, "Select Combat Log Font")
        if ok:
            self.settings["font_family_log"] = font.family()
            self.settings["font_size_log"] = font.pointSize()
            self._update_font_previews()

    # --- Public Method ---

    def get_settings(self) -> Dict[str, Any]:
        """Return the modified settings dictionary."""
        # Save the final value from the spinbox
        self.settings["header_vertical_offset"] = self.header_offset_spinbox.value()

        if not self.available_images or self.current_image_index < 0:
            self.settings["background_image"] = None
        else:
            self.settings["background_image"] = self.available_images[self.current_image_index]

        return self.settings

