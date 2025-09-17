# --- START OF FILE settings_dialog.py ---

#!/usr/bin/env python3
"""
Settings dialog for the RPG game GUI.
This module provides a dialog for configuring game settings.
"""

import logging
import json
import os
from typing import Dict, Any

from gui.dialogs.base_dialog import BaseDialog
from gui.dialogs.settings.style_tab import StyleTab
from gui.dialogs.settings.background_tab import BackgroundTab 

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTabWidget, QWidget, QFormLayout,
    QCheckBox, QSpinBox, QGroupBox, QRadioButton, QButtonGroup,
    QSlider 
)
from PySide6.QtCore import Qt, Signal, QSettings, QSize, Slot
from PySide6.QtGui import QColor 

class SettingsDialog(BaseDialog):
    """Dialog for configuring game settings."""

    # Signal emitted when settings are saved
    settings_saved = Signal()

    # Signal emitted when a background preview is requested by the BackgroundTab
    background_preview_requested = Signal(str)

    def __init__(self, parent=None):
        """Initialize the settings dialog."""
        super().__init__(parent)


        # # --- ADDED: Ensure dialog has a default background --- 
        # self.setAutoFillBackground(True)
        # palette = self.palette()
        # # Use a light color that usually contrasts well with default black text
        # palette.setColor(self.backgroundRole(), QColor("#F0F0F0")) 
        # self.setPalette(palette)
        # # --- END ADDED --- 

        # Set dialog properties
        self.setWindowTitle("Game Settings")
        self.setMinimumWidth(500)

        # Load current settings
        self.settings = QSettings("RPGGame", "Settings")

        # Set up the UI
        self._setup_ui()

        # Load settings into the UI
        self._load_settings()

    def _setup_ui(self):
        """Set up the user interface."""
        # Create main layout
        layout = QVBoxLayout(self)

        # Create tab widget for settings categories
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { /* The area where tab pages are displayed */
                border: 1px solid #555555;
                background-color: #2D2D30; /* Dark background for the content pane */
                border-top: 1px solid #555555; /* Ensure top border is visible */
            }
            QTabBar::tab { /* Style for individual tabs */
                background-color: #333333; /* Dark background for non-selected tabs */
                color: #CCCCCC; /* Light text for non-selected tabs */
                border: 1px solid #555555;
                border-bottom: none; /* Remove bottom border for non-selected tabs */
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 12px; /* Adjusted padding */
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2D2D30; /* Match pane background for selected tab */
                color: #E0E0E0; /* Brighter text for selected tab */
                border-bottom: 1px solid #2D2D30; /* Blend selected tab with pane */
            }
            QTabBar::tab:!selected:hover {
                background-color: #454545; /* Slightly lighter for hover on non-selected tabs */
            }
            QTabWidget QWidget { /* Ensure widgets inside tabs also have transparent background if needed */
                 background-color: transparent; /* Or match #2D2D30 if transparency causes issues */
            }
        """)

        # Set up tabs
        self._setup_display_tab()
        self._setup_sound_tab()
        self._setup_gameplay_tab()
        self._setup_style_tab()
        self._setup_background_tab()

        # Add tab widget to layout
        layout.addWidget(self.tab_widget)

        # Create button box
        button_layout = QHBoxLayout()

        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_settings)

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        # Add buttons to layout
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        # Add button layout to main layout
        layout.addLayout(button_layout)

    def _setup_display_tab(self):
        """Set up the display settings tab."""
        # Create display tab
        display_tab = QWidget()
        display_layout = QVBoxLayout(display_tab)

        # Create form layout for settings
        form_layout = QFormLayout()

        # --- Window Mode Setting ---
        display_mode_group = QGroupBox("Display Mode")
        display_mode_layout = QVBoxLayout(display_mode_group)
        self.display_mode_group = QButtonGroup(self) # Group for radio buttons

        self.windowed_radio = QRadioButton("Windowed")
        self.windowed_fullscreen_radio = QRadioButton("Windowed Fullscreen (Maximized)")
        self.fullscreen_radio = QRadioButton("Fullscreen")

        self.display_mode_group.addButton(self.windowed_radio, 0)
        self.display_mode_group.addButton(self.windowed_fullscreen_radio, 1)
        self.display_mode_group.addButton(self.fullscreen_radio, 2)

        display_mode_layout.addWidget(self.windowed_radio)
        display_mode_layout.addWidget(self.windowed_fullscreen_radio)
        display_mode_layout.addWidget(self.fullscreen_radio)

        # --- Resolution Setting (Enabled only for Windowed) ---
        resolution_layout = QHBoxLayout()
        self.resolution_label = QLabel("Resolution (Windowed):") # Label clarifies when it applies
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItem("800x600", QSize(800, 600))
        self.resolution_combo.addItem("1024x768", QSize(1024, 768))
        self.resolution_combo.addItem("1280x720", QSize(1280, 720))
        self.resolution_combo.addItem("1366x768", QSize(1366, 768))
        self.resolution_combo.addItem("1600x900", QSize(1600, 900))
        self.resolution_combo.addItem("1920x1080", QSize(1920, 1080))
        # Add more resolutions if needed
        resolution_layout.addWidget(self.resolution_label)
        resolution_layout.addWidget(self.resolution_combo)

        # Connect radio button toggle to enable/disable resolution combo
        self.windowed_radio.toggled.connect(self._update_resolution_state)

        # Add display mode and resolution to the form layout
        display_layout.addWidget(display_mode_group)
        display_layout.addLayout(resolution_layout) # Add the HBox layout

        # --- UI Scale Setting ---
        self.ui_scale_combo = QComboBox()
        self.ui_scale_combo.addItem("100%", 1.0)
        self.ui_scale_combo.addItem("125%", 1.25)
        self.ui_scale_combo.addItem("150%", 1.5)
        self.ui_scale_combo.addItem("175%", 1.75)
        self.ui_scale_combo.addItem("200%", 2.0)
        # Add UI Scale to its own layout or directly if preferred
        ui_scale_layout = QHBoxLayout()
        ui_scale_layout.addWidget(QLabel("UI Scale:"))
        ui_scale_layout.addWidget(self.ui_scale_combo)
        display_layout.addLayout(ui_scale_layout)

        # --- Text Speed Setting ---
        text_speed_layout = QHBoxLayout()
        text_speed_layout.addWidget(QLabel("Gradual Text Speed:"))
        self.text_speed_slider = QSlider(Qt.Horizontal)
        self.text_speed_slider.setRange(5, 100)
        self.text_speed_slider.setTickPosition(QSlider.TicksBelow)
        self.text_speed_slider.setTickInterval(10)
        self.text_speed_label = QLabel("30 ms")
        self.text_speed_slider.valueChanged.connect(
            lambda value: self.text_speed_label.setText(f"{value} ms")
        )
        text_speed_layout.addWidget(self.text_speed_slider)
        text_speed_layout.addWidget(self.text_speed_label)
        display_layout.addLayout(text_speed_layout)

        display_layout.addStretch()

        # Add display tab to tab widget
        self.tab_widget.addTab(display_tab, "Display")

    @Slot(bool)
    def _update_resolution_state(self, checked):
        """Enable/disable resolution combo based on Windowed mode selection."""
        is_windowed = self.windowed_radio.isChecked()
        self.resolution_label.setEnabled(is_windowed)
        self.resolution_combo.setEnabled(is_windowed)

    def _setup_sound_tab(self):
        """Set up the sound settings tab."""
        # Create sound tab
        sound_tab = QWidget()
        sound_layout = QVBoxLayout(sound_tab)

        # Create form layout for settings
        form_layout = QFormLayout()

        # Create master volume setting
        self.master_volume_spin = QSpinBox()
        self.master_volume_spin.setRange(0, 100)
        self.master_volume_spin.setSuffix("%")
        form_layout.addRow("Master Volume:", self.master_volume_spin)

        # Create music volume setting
        self.music_volume_spin = QSpinBox()
        self.music_volume_spin.setRange(0, 100)
        self.music_volume_spin.setSuffix("%")
        form_layout.addRow("Music Volume:", self.music_volume_spin)

        # Create sound effects volume setting
        self.effects_volume_spin = QSpinBox()
        self.effects_volume_spin.setRange(0, 100)
        self.effects_volume_spin.setSuffix("%")
        form_layout.addRow("Sound Effects Volume:", self.effects_volume_spin)

        # Create sound enabled checkbox
        self.sound_enabled_check = QCheckBox("Enable Sound")

        # Add form layout to sound layout
        sound_layout.addLayout(form_layout)
        sound_layout.addWidget(self.sound_enabled_check)
        sound_layout.addStretch()

        # Add sound tab to tab widget
        self.tab_widget.addTab(sound_tab, "Sound")

    def _setup_gameplay_tab(self):
        """Set up the gameplay settings tab."""
        # Create gameplay tab
        gameplay_tab = QWidget()
        gameplay_layout = QVBoxLayout(gameplay_tab)

        # Developer Mode group
        dev_group = QGroupBox("Developer Mode")
        dev_layout = QVBoxLayout(dev_group)
        self.dev_mode_checkbox = QCheckBox("Enable Developer Mode (show debug UI and controls)")
        dev_layout.addWidget(self.dev_mode_checkbox)
        gameplay_layout.addWidget(dev_group)

        # Create form layout for settings
        form_layout = QFormLayout()

        # Create difficulty setting
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItem("Easy")
        self.difficulty_combo.addItem("Normal")
        self.difficulty_combo.addItem("Hard")
        form_layout.addRow("Difficulty:", self.difficulty_combo)

        # Create auto-save interval setting
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(0, 60)
        self.autosave_spin.setSuffix(" minutes")
        self.autosave_spin.setSpecialValueText("Off")
        form_layout.addRow("Auto-save Interval:", self.autosave_spin)

        # Create tutorial checkbox
        self.tutorial_check = QCheckBox("Show Tutorial Tips")

        # Add form layout to gameplay layout
        gameplay_layout.addLayout(form_layout)
        gameplay_layout.addWidget(self.tutorial_check)
        gameplay_layout.addStretch()

        # Add gameplay tab to tab widget
        self.tab_widget.addTab(gameplay_tab, "Gameplay")

    def _load_settings(self):
        """Load settings from QSettings to the UI."""
        # Load display settings
        window_state = self.settings.value("display/window_state", "windowed")
        if window_state == "fullscreen":
            self.fullscreen_radio.setChecked(True)
        elif window_state == "maximized": # Changed key to 'maximized'
            self.windowed_fullscreen_radio.setChecked(True)
        else: # Default to windowed
            self.windowed_radio.setChecked(True)

        # Update resolution combo state initially
        self._update_resolution_state(self.windowed_radio.isChecked())

        # Load windowed resolution (even if not currently windowed)
        default_size = QSize(1280, 720)
        resolution = self.settings.value("display/windowed_size", default_size)
        # Ensure resolution is QSize
        if not isinstance(resolution, QSize):
            if isinstance(resolution, (tuple, list)) and len(resolution) == 2:
                resolution = QSize(resolution[0], resolution[1])
            elif isinstance(resolution, str):
                try:
                    parts = resolution.strip('()').split(',')
                    resolution = QSize(int(parts[0]), int(parts[1]))
                except Exception:
                    resolution = default_size # Fallback on parse error
            else:
                 resolution = default_size # Fallback if type is unexpected

        resolution_str = f"{resolution.width()}x{resolution.height()}"
        found = False
        for i in range(self.resolution_combo.count()):
            if self.resolution_combo.itemText(i) == resolution_str:
                self.resolution_combo.setCurrentIndex(i)
                found = True
                break
        if not found: # If saved resolution isn't in the list, add it? Or default?
            # Option 1: Add it (might make combo long)
            # self.resolution_combo.addItem(resolution_str, resolution)
            # self.resolution_combo.setCurrentIndex(self.resolution_combo.count() - 1)
            # Option 2: Default to first item if not found
             self.resolution_combo.setCurrentIndex(0)
             logging.warning(f"Saved windowed resolution {resolution_str} not found in options. Defaulting.")


        # Load UI scale (unchanged)
        ui_scale = self.settings.value("display/ui_scale", 1.0)
        for i in range(self.ui_scale_combo.count()):
            if self.ui_scale_combo.itemData(i) == ui_scale:
                self.ui_scale_combo.setCurrentIndex(i)
                break

        # Load text speed setting (unchanged)
        text_speed_delay = self.settings.value("display/text_speed_delay", 30, int)
        self.text_speed_slider.setValue(text_speed_delay)
        self.text_speed_label.setText(f"{text_speed_delay} ms")

        # Load sound settings (unchanged)
        self.master_volume_spin.setValue(int(self.settings.value("sound/master_volume", 100)))
        self.music_volume_spin.setValue(int(self.settings.value("sound/music_volume", 100)))
        self.effects_volume_spin.setValue(int(self.settings.value("sound/effects_volume", 100)))
        sound_enabled = self.settings.value("sound/enabled", True)
        if isinstance(sound_enabled, str): sound_enabled = sound_enabled.lower() == "true"
        self.sound_enabled_check.setChecked(sound_enabled)

        # Load gameplay settings (unchanged)
        difficulty = self.settings.value("gameplay/difficulty", "Normal")
        for i in range(self.difficulty_combo.count()):
            if self.difficulty_combo.itemText(i) == difficulty:
                self.difficulty_combo.setCurrentIndex(i)
                break
        self.autosave_spin.setValue(int(self.settings.value("gameplay/autosave_interval", 0)))
        tutorial_enabled = self.settings.value("gameplay/tutorial_enabled", True)
        if isinstance(tutorial_enabled, str): tutorial_enabled = tutorial_enabled.lower() == "true"
        self.tutorial_check.setChecked(tutorial_enabled)

        # Load dev mode
        dev_enabled = self.settings.value("dev/enabled", False)
        if isinstance(dev_enabled, str):
            dev_enabled = dev_enabled.lower() == "true"
        self.dev_mode_checkbox.setChecked(bool(dev_enabled))

        # Load style settings
        if hasattr(self, 'style_tab'):
            self.style_tab._load_settings() 

        if hasattr(self, 'background_tab'):
             self.background_tab.load_settings(self.settings)

    def _setup_style_tab(self):
        """Set up the style settings tab."""
        # Create style tab
        self.style_tab = StyleTab()

        # Add style tab to tab widget
        self.tab_widget.addTab(self.style_tab, "Style")


    def _setup_background_tab(self):
        """Set up the background selection tab."""
        # Create background tab
        self.background_tab = BackgroundTab()

        # Connect the preview signal from the tab to this dialog's signal
        self.background_tab.preview_background_changed.connect(self.background_preview_requested)

        # Add background tab to tab widget
        self.tab_widget.addTab(self.background_tab, "Background")

    def _save_settings(self):
        """Save settings from the UI to QSettings."""
        # Save window state
        window_state_str = "windowed" # Default
        if self.fullscreen_radio.isChecked():
            window_state_str = "fullscreen"
        elif self.windowed_fullscreen_radio.isChecked():
            window_state_str = "maximized" # Use 'maximized' internally
        self.settings.setValue("display/window_state", window_state_str)

        # Save windowed resolution *only* if windowed mode is selected
        if window_state_str == "windowed":
            selected_resolution = self.resolution_combo.currentData()
            if isinstance(selected_resolution, QSize): # Store QSize directly if possible
                self.settings.setValue("display/windowed_size", selected_resolution)
            else: # Fallback to storing tuple if currentData wasn't QSize
                resolution_text = self.resolution_combo.currentText()
                try:
                    w, h = map(int, resolution_text.split('x'))
                    self.settings.setValue("display/windowed_size", (w, h))
                except ValueError:
                    logging.error(f"Could not parse resolution text '{resolution_text}' during save.")
                    # Optionally save a default or skip saving resolution

        # Save UI scale (unchanged)
        self.settings.setValue("display/ui_scale", self.ui_scale_combo.currentData())

        # Save text speed setting (unchanged)
        self.settings.setValue("display/text_speed_delay", self.text_speed_slider.value())

        # Save sound settings (unchanged)
        self.settings.setValue("sound/master_volume", self.master_volume_spin.value())
        self.settings.setValue("sound/music_volume", self.music_volume_spin.value())
        self.settings.setValue("sound/effects_volume", self.effects_volume_spin.value())
        self.settings.setValue("sound/enabled", self.sound_enabled_check.isChecked())

        # Save gameplay settings (unchanged)
        self.settings.setValue("gameplay/difficulty", self.difficulty_combo.currentText())
        self.settings.setValue("gameplay/autosave_interval", self.autosave_spin.value())
        self.settings.setValue("gameplay/tutorial_enabled", self.tutorial_check.isChecked())

        # Save dev mode
        self.settings.setValue("dev/enabled", self.dev_mode_checkbox.isChecked())

        # Save style settings (unchanged)
        if hasattr(self, 'style_tab'):
            self.style_tab.save_settings()

        # Save background settings (unchanged)
        if hasattr(self, 'background_tab'):
            self.background_tab.save_settings(self.settings)

        # Sync settings to disk
        self.settings.sync()

        # Emit signal
        self.settings_saved.emit()

        # Close dialog
        self.accept()

    @staticmethod
    def get_settings():
        """Get the current settings.

        Returns:
            Dict[str, Any]: The current settings.
        """
        settings = QSettings("RPGGame", "Settings")
        # ... (rest of the method implementation) ...

        # Helper to convert loaded QSize to tuple if needed
        def size_to_tuple(size_val):
            if isinstance(size_val, QSize):
                return (size_val.width(), size_val.height())
            # Handle tuple/list potentially saved previously
            elif isinstance(size_val, (tuple, list)) and len(size_val) == 2:
                return tuple(size_val)
            # Handle string format
            elif isinstance(size_val, str):
                try:
                    parts = size_val.strip('()').split(',')
                    return (int(parts[0]), int(parts[1]))
                except Exception:
                    return (1280, 720) # Fallback
            return (1280, 720) # Default fallback

        return {
            "display": {
                "window_state": settings.value("display/window_state", "windowed"),
                "windowed_size": size_to_tuple(settings.value("display/windowed_size", QSize(1280, 720))), # Get saved windowed size
                "ui_scale": settings.value("display/ui_scale", 1.0),
                "text_speed_delay": settings.value("display/text_speed_delay", 30, int)
            },
            "sound": {
                "master_volume": settings.value("sound/master_volume", 100),
                "music_volume": settings.value("sound/music_volume", 100),
                "effects_volume": settings.value("sound/effects_volume", 100),
                "enabled": settings.value("sound/enabled", True)
            },
            "gameplay": {
                "difficulty": settings.value("gameplay/difficulty", "Normal"),
                "autosave_interval": settings.value("gameplay/autosave_interval", 0),
                "tutorial_enabled": settings.value("gameplay/tutorial_enabled", True)
            },
            "style": {
                "output_bg_color": settings.value("style/output_bg_color", "#D2B48C"),
                "system_msg_color": settings.value("style/system_msg_color", "#FF0000"),
                "font_family": settings.value("style/font_family", "Garamond"),
                "font_size": settings.value("style/font_size", 14),
                "font_color": settings.value("style/font_color", "#000000"),
                "user_input_font_family": settings.value("style/user_input_font_family", "Garamond"),
                "user_input_font_size": settings.value("style/user_input_font_size", 14),
                "user_input_font_color": settings.value("style/user_input_font_color", "#0d47a1"),
                "background_filename": settings.value("style/background_filename", None), # Load filename string
                "texture_name": settings.value("style/texture_name", "subtle_noise"),
                "output_opacity": settings.value("style/output_opacity", 100, int),
                "input_opacity": settings.value("style/input_opacity", 100, int)
            }
        }