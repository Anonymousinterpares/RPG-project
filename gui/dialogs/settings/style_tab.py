#!/usr/bin/env python3
"""
Style settings tab for the RPG game GUI.
This module provides a tab for configuring UI style settings.
"""

import os
import logging
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFormLayout, QGroupBox, QRadioButton, 
    QButtonGroup, QColorDialog, QFontDialog, QGridLayout,
    QFrame, QSlider
)
from PySide6.QtCore import Qt, Signal, QSettings, QSize
from PySide6.QtGui import QFont, QColor, QPixmap, QIcon

class StyleTab(QWidget):
    """Tab for configuring UI style settings."""
    
    def __init__(self, parent=None):
        """Initialize the style tab."""
        super().__init__(parent)
        
        # Set up the UI
        self._setup_ui()
        
        # Load settings
        self._load_settings()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Create form layout for settings
        form_layout = QFormLayout()
        
        # Output area background color
        self.output_bg_group = QGroupBox("Output Area Background")
        self.output_bg_layout = QVBoxLayout(self.output_bg_group)
        
        # Predefined colors
        self.predefined_colors_layout = QGridLayout()
        self.predefined_colors_layout.setSpacing(5)
        
        # Add predefined color options
        self.color_buttons = {}
        predefined_colors = [
            ("Light Brown", "#D2B48C"),
            ("Dark Brown", "#8B4513"),
            ("Beige", "#F5F5DC"),
            ("Cream", "#FFFDD0"),
            ("Tan", "#D2B48C"),
            ("Ivory", "#FFFFF0"),
            ("Light Gray", "#D3D3D3"),
            ("Light Blue", "#ADD8E6"),
            ("Light Green", "#90EE90"),
            ("Light Red", "#FFCCCB"),
        ]
        
        # Create a button group for color selection
        self.bg_color_group = QButtonGroup(self)
        self.bg_color_group.setExclusive(True)
        
        # Add color buttons to grid
        row, col = 0, 0
        for i, (color_name, color_hex) in enumerate(predefined_colors):
            button = QRadioButton(color_name)
            # Set a background color style for the button
            button.setStyleSheet(f"QRadioButton {{ background-color: {color_hex}; padding: 5px; border-radius: 3px; }}")
            button.setProperty("color_hex", color_hex)
            
            self.predefined_colors_layout.addWidget(button, row, col)
            self.color_buttons[color_name] = button
            self.bg_color_group.addButton(button)
            
            col += 1
            if col > 2:  # 3 columns per row
                col = 0
                row += 1
        
        # Custom color picker
        self.custom_color_layout = QHBoxLayout()
        self.custom_color_radio = QRadioButton("Custom:")
        self.bg_color_group.addButton(self.custom_color_radio)
        
        self.custom_color_button = QPushButton("Choose...")
        self.custom_color_button.clicked.connect(self._choose_custom_bg_color)
        
        self.custom_color_preview = QFrame()
        self.custom_color_preview.setFixedSize(20, 20)
        self.custom_color_preview.setFrameShape(QFrame.StyledPanel)
        self.custom_color_preview.setStyleSheet("background-color: #D2B48C; border: 1px solid gray;")
        
        self.custom_color_layout.addWidget(self.custom_color_radio)
        self.custom_color_layout.addWidget(self.custom_color_button)
        self.custom_color_layout.addWidget(self.custom_color_preview)
        self.custom_color_layout.addStretch()
        
        # Add layouts to output bg group
        self.output_bg_layout.addLayout(self.predefined_colors_layout)
        self.output_bg_layout.addLayout(self.custom_color_layout)
        
        # System message color
        self.system_msg_group = QGroupBox("System Message Color")
        self.system_msg_layout = QVBoxLayout(self.system_msg_group)
        
        # Predefined system colors
        self.sys_colors_layout = QGridLayout()
        self.sys_colors_layout.setSpacing(5)
        
        # Add predefined system color options
        self.sys_color_buttons = {}
        predefined_sys_colors = [
            ("Red", "#FF0000"),
            ("Orange", "#FFA500"),
            ("Yellow", "#FFFF00"),
            ("Green", "#00FF00"),
            ("Blue", "#0000FF"),
            ("Purple", "#800080"),
            ("Pink", "#FFC0CB"),
            ("Black", "#000000"),
        ]
        
        # Create a button group for system color selection
        self.sys_color_group = QButtonGroup(self)
        self.sys_color_group.setExclusive(True)
        
        # Add system color buttons to grid
        row, col = 0, 0
        for i, (color_name, color_hex) in enumerate(predefined_sys_colors):
            button = QRadioButton(color_name)
            # Set a foreground color style for the button
            button.setStyleSheet(f"QRadioButton {{ color: {color_hex}; font-weight: bold; }}")
            button.setProperty("color_hex", color_hex)
            
            self.sys_colors_layout.addWidget(button, row, col)
            self.sys_color_buttons[color_name] = button
            self.sys_color_group.addButton(button)
            
            col += 1
            if col > 2:  # 3 columns per row
                col = 0
                row += 1
        
        # Custom system color picker
        self.custom_sys_color_layout = QHBoxLayout()
        self.custom_sys_color_radio = QRadioButton("Custom:")
        self.sys_color_group.addButton(self.custom_sys_color_radio)
        
        self.custom_sys_color_button = QPushButton("Choose...")
        self.custom_sys_color_button.clicked.connect(self._choose_custom_sys_color)
        
        self.custom_sys_color_preview = QFrame()
        self.custom_sys_color_preview.setFixedSize(20, 20)
        self.custom_sys_color_preview.setFrameShape(QFrame.StyledPanel)
        self.custom_sys_color_preview.setStyleSheet("background-color: #FF0000; border: 1px solid gray;")
        
        self.custom_sys_color_layout.addWidget(self.custom_sys_color_radio)
        self.custom_sys_color_layout.addWidget(self.custom_sys_color_button)
        self.custom_sys_color_layout.addWidget(self.custom_sys_color_preview)
        self.custom_sys_color_layout.addStretch()
        
        # Add layouts to system msg group
        self.system_msg_layout.addLayout(self.sys_colors_layout)
        self.system_msg_layout.addLayout(self.custom_sys_color_layout)
        
        # Output Text Font settings
        self.font_group = QGroupBox("Output Text Font")
        self.font_layout = QVBoxLayout(self.font_group)
        
        self.font_button = QPushButton("Choose Font...")
        self.font_button.clicked.connect(self._choose_font)
        
        self.font_preview = QLabel("AaBbCcDdEe 12345")
        self.font_preview.setAlignment(Qt.AlignCenter)
        self.font_preview.setFrameShape(QFrame.StyledPanel)
        self.font_preview.setMinimumHeight(40)
        
        self.font_layout.addWidget(self.font_button)
        self.font_layout.addWidget(self.font_preview)
        
        # Font color
        self.font_color_layout = QHBoxLayout()
        self.font_color_label = QLabel("Font Color:")
        self.font_color_button = QPushButton("Choose...")
        self.font_color_button.clicked.connect(self._choose_font_color)
        
        self.font_color_preview = QFrame()
        self.font_color_preview.setFixedSize(20, 20)
        self.font_color_preview.setFrameShape(QFrame.StyledPanel)
        self.font_color_preview.setStyleSheet("background-color: #000000; border: 1px solid gray;")
        
        self.font_color_layout.addWidget(self.font_color_label)
        self.font_color_layout.addWidget(self.font_color_button)
        self.font_color_layout.addWidget(self.font_color_preview)
        self.font_color_layout.addStretch()
        
        self.font_layout.addLayout(self.font_color_layout)
        
        # User Input Text Font settings
        self.user_input_font_group = QGroupBox("User Input Text Font")
        self.user_input_font_layout = QVBoxLayout(self.user_input_font_group)
        
        self.user_input_font_button = QPushButton("Choose Font...")
        self.user_input_font_button.clicked.connect(self._choose_user_input_font)
        
        self.user_input_font_preview = QLabel("AaBbCcDdEe 12345")
        self.user_input_font_preview.setAlignment(Qt.AlignCenter)
        self.user_input_font_preview.setFrameShape(QFrame.StyledPanel)
        self.user_input_font_preview.setMinimumHeight(40)
        
        self.user_input_font_layout.addWidget(self.user_input_font_button)
        self.user_input_font_layout.addWidget(self.user_input_font_preview)
        
        # User input font color
        self.user_input_font_color_layout = QHBoxLayout()
        self.user_input_font_color_label = QLabel("Font Color:")
        self.user_input_font_color_button = QPushButton("Choose...")
        self.user_input_font_color_button.clicked.connect(self._choose_user_input_font_color)
        
        self.user_input_font_color_preview = QFrame()
        self.user_input_font_color_preview.setFixedSize(20, 20)
        self.user_input_font_color_preview.setFrameShape(QFrame.StyledPanel)
        self.user_input_font_color_preview.setStyleSheet("background-color: #0d47a1; border: 1px solid gray;")
        
        self.user_input_font_color_layout.addWidget(self.user_input_font_color_label)
        self.user_input_font_color_layout.addWidget(self.user_input_font_color_button)
        self.user_input_font_color_layout.addWidget(self.user_input_font_color_preview)
        self.user_input_font_color_layout.addStretch()
        
        self.user_input_font_layout.addLayout(self.user_input_font_color_layout)
        
        # Add all settings to the form layout
        layout.addWidget(self.output_bg_group)
        layout.addWidget(self.system_msg_group)
        layout.addWidget(self.font_group)
        layout.addWidget(self.user_input_font_group)
        
        # Add texture and transparency settings
        self._setup_texture_settings(layout)
        self._setup_transparency_settings(layout)
        
        layout.addStretch()
    
    def _setup_texture_settings(self, parent_layout):
        """Set up texture settings."""
        # Create a group box for texture settings
        self.texture_group = QGroupBox("Background Texture")
        texture_layout = QVBoxLayout(self.texture_group)
        
        # Create radio buttons for texture selection
        self.texture_radio_group = QButtonGroup(self)
        self.texture_radio_group.setExclusive(True)
        
        # Define available textures
        textures = [
            ("None", "none"),
            ("Subtle Noise", "subtle_noise"),
            ("Parchment", "parchment"),
            ("Leather", "leather"),
            ("Stone", "stone")
        ]
        
        # Create a grid layout for texture options
        texture_grid = QGridLayout()
        texture_grid.setSpacing(10)
        
        # Create radio buttons for each texture
        self.texture_buttons = {}
        row, col = 0, 0
        for i, (display_name, texture_name) in enumerate(textures):
            button = QRadioButton(display_name)
            button.setProperty("texture_name", texture_name)
            self.texture_buttons[texture_name] = button
            self.texture_radio_group.addButton(button)
            
            texture_grid.addWidget(button, row, col)
            
            col += 1
            if col > 2:  # 3 columns per row
                col = 0
                row += 1
        
        # Add grid to layout
        texture_layout.addLayout(texture_grid)
        
        # Add group to parent layout
        parent_layout.addWidget(self.texture_group)
    
    def _setup_transparency_settings(self, parent_layout):
        """Set up transparency settings."""
        # Create group box
        self.transparency_group = QGroupBox("Transparency Settings")
        transparency_layout = QFormLayout(self.transparency_group)
        
        # Create output transparency slider
        self.output_transparency_slider = QSlider(Qt.Horizontal)
        self.output_transparency_slider.setRange(0, 100)
        self.output_transparency_slider.setValue(100)  # Default to fully opaque
        self.output_transparency_slider.setTickPosition(QSlider.TicksBelow)
        self.output_transparency_slider.setTickInterval(10)
        
        # Create input transparency slider
        self.input_transparency_slider = QSlider(Qt.Horizontal)
        self.input_transparency_slider.setRange(0, 100)
        self.input_transparency_slider.setValue(100)  # Default to fully opaque
        self.input_transparency_slider.setTickPosition(QSlider.TicksBelow)
        self.input_transparency_slider.setTickInterval(10)
        
        # Add sliders to layout
        transparency_layout.addRow("Output Area Opacity:", self.output_transparency_slider)
        transparency_layout.addRow("Command Input Opacity:", self.input_transparency_slider)
        
        # Add value labels
        self.output_transparency_value = QLabel("100%")
        self.input_transparency_value = QLabel("100%")
        
        transparency_layout.addRow("", self.output_transparency_value)
        transparency_layout.addRow("", self.input_transparency_value)
        
        # Connect sliders to update value labels
        self.output_transparency_slider.valueChanged.connect(
            lambda v: self.output_transparency_value.setText(f"{v}%")
        )
        self.input_transparency_slider.valueChanged.connect(
            lambda v: self.input_transparency_value.setText(f"{v}%")
        )
        
        # Add group to parent layout
        parent_layout.addWidget(self.transparency_group)
    
    def _choose_custom_bg_color(self):
        """Open color dialog for custom background color."""
        settings = QSettings("RPGGame", "Settings")
        current_color = QColor(settings.value("style/output_bg_color", "#D2B48C"))
        
        color = QColorDialog.getColor(current_color, self, "Select Background Color")
        if color.isValid():
            # Update preview
            self.custom_color_preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid gray;")
            # Select custom radio button
            self.custom_color_radio.setChecked(True)
            # Store color hex
            self.custom_color_radio.setProperty("color_hex", color.name())
    
    def _choose_custom_sys_color(self):
        """Open color dialog for custom system message color."""
        settings = QSettings("RPGGame", "Settings")
        current_color = QColor(settings.value("style/system_msg_color", "#FF0000"))
        
        color = QColorDialog.getColor(current_color, self, "Select System Message Color")
        if color.isValid():
            # Update preview
            self.custom_sys_color_preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid gray;")
            # Select custom radio button
            self.custom_sys_color_radio.setChecked(True)
            # Store color hex
            self.custom_sys_color_radio.setProperty("color_hex", color.name())
    
    def _choose_font(self):
        """Open font dialog."""
        settings = QSettings("RPGGame", "Settings")
        current_font = QFont()
        font_family = settings.value("style/font_family", "Garamond")
        font_size = int(settings.value("style/font_size", 14))
        current_font.setFamily(font_family)
        current_font.setPointSize(font_size)
        
        ok, font = QFontDialog.getFont(current_font, self, "Select Font")
        if ok:
            # Update preview
            self.font_preview.setFont(font)
            # Store font
            self.font_preview.setProperty("selected_font", font)
    
    def _choose_user_input_font(self):
        """Open font dialog for user input text."""
        settings = QSettings("RPGGame", "Settings")
        current_font = QFont()
        font_family = settings.value("style/user_input_font_family", "Garamond")
        font_size = int(settings.value("style/user_input_font_size", 14))
        current_font.setFamily(font_family)
        current_font.setPointSize(font_size)
        
        ok, font = QFontDialog.getFont(current_font, self, "Select User Input Font")
        if ok:
            # Update preview
            self.user_input_font_preview.setFont(font)
            # Store font
            self.user_input_font_preview.setProperty("selected_font", font)
    
    def _choose_user_input_font_color(self):
        """Open color dialog for user input font color."""
        settings = QSettings("RPGGame", "Settings")
        current_color = QColor(settings.value("style/user_input_font_color", "#0d47a1"))
        
        color = QColorDialog.getColor(current_color, self, "Select User Input Font Color")
        if color.isValid():
            # Update preview
            self.user_input_font_color_preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid gray;")
            # Update font preview
            self.user_input_font_preview.setStyleSheet(f"color: {color.name()};")
            # Store color
            self.user_input_font_color_preview.setProperty("color_hex", color.name())
    
    def _choose_font_color(self):
        """Open color dialog for font color."""
        settings = QSettings("RPGGame", "Settings")
        current_color = QColor(settings.value("style/font_color", "#000000"))
        
        color = QColorDialog.getColor(current_color, self, "Select Font Color")
        if color.isValid():
            # Update preview
            self.font_color_preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid gray;")
            # Update font preview
            self.font_preview.setStyleSheet(f"color: {color.name()};")
            # Store color
            self.font_color_preview.setProperty("color_hex", color.name())
    
    def _load_settings(self):
        """Load settings from QSettings to the UI."""
        settings = QSettings("RPGGame", "Settings")
        
        # Load output background color
        bg_color = settings.value("style/output_bg_color", "#D2B48C")
        
        # Check if it's one of the predefined colors
        found_predefined = False
        for button in self.color_buttons.values():
            if button.property("color_hex") == bg_color:
                button.setChecked(True)
                found_predefined = True
                break
        
        # If not found, use custom color
        if not found_predefined:
            self.custom_color_radio.setChecked(True)
            self.custom_color_preview.setStyleSheet(f"background-color: {bg_color}; border: 1px solid gray;")
            self.custom_color_radio.setProperty("color_hex", bg_color)
        
        # Load system message color
        sys_color = settings.value("style/system_msg_color", "#FF0000")
        
        # Check if it's one of the predefined colors
        found_predefined = False
        for button in self.sys_color_buttons.values():
            if button.property("color_hex") == sys_color:
                button.setChecked(True)
                found_predefined = True
                break
        
        # If not found, use custom color
        if not found_predefined:
            self.custom_sys_color_radio.setChecked(True)
            self.custom_sys_color_preview.setStyleSheet(f"background-color: {sys_color}; border: 1px solid gray;")
            self.custom_sys_color_radio.setProperty("color_hex", sys_color)
        
        # Load output font settings
        font_family = settings.value("style/font_family", "Garamond")
        font_size = int(settings.value("style/font_size", 14))
        font = QFont(font_family, font_size)
        self.font_preview.setFont(font)
        self.font_preview.setProperty("selected_font", font)
        
        # Load output font color
        font_color = settings.value("style/font_color", "#000000")
        self.font_color_preview.setStyleSheet(f"background-color: {font_color}; border: 1px solid gray;")
        self.font_preview.setStyleSheet(f"color: {font_color};")
        self.font_color_preview.setProperty("color_hex", font_color)
        
        # Load user input font settings
        user_input_font_family = settings.value("style/user_input_font_family", "Garamond")
        user_input_font_size = int(settings.value("style/user_input_font_size", 14))
        user_input_font = QFont(user_input_font_family, user_input_font_size)
        self.user_input_font_preview.setFont(user_input_font)
        self.user_input_font_preview.setProperty("selected_font", user_input_font)
        
        # Load user input font color
        user_input_font_color = settings.value("style/user_input_font_color", "#0d47a1")
        self.user_input_font_color_preview.setStyleSheet(f"background-color: {user_input_font_color}; border: 1px solid gray;")
        self.user_input_font_preview.setStyleSheet(f"color: {user_input_font_color};")
        self.user_input_font_color_preview.setProperty("color_hex", user_input_font_color)
        
        # Load texture setting
        texture_name = settings.value("style/texture_name", "subtle_noise")
        if texture_name in self.texture_buttons:
            self.texture_buttons[texture_name].setChecked(True)
        else:
            # Default to subtle noise
            self.texture_buttons["subtle_noise"].setChecked(True)
        
        # Load transparency settings
        output_opacity = int(settings.value("style/output_opacity", 100))
        input_opacity = int(settings.value("style/input_opacity", 100))
        
        self.output_transparency_slider.setValue(output_opacity)
        self.input_transparency_slider.setValue(input_opacity)
        self.output_transparency_value.setText(f"{output_opacity}%")
        self.input_transparency_value.setText(f"{input_opacity}%")
    
    def save_settings(self):
        """Save settings from the UI to QSettings."""
        settings = QSettings("RPGGame", "Settings")
        
        # Save output background color
        if self.custom_color_radio.isChecked():
            bg_color = self.custom_color_radio.property("color_hex")
        else:
            # Get selected button
            for button in self.color_buttons.values():
                if button.isChecked():
                    bg_color = button.property("color_hex")
                    break
            else:
                # Default if none selected
                bg_color = "#D2B48C"
        
        settings.setValue("style/output_bg_color", bg_color)
        
        # Save system message color
        if self.custom_sys_color_radio.isChecked():
            sys_color = self.custom_sys_color_radio.property("color_hex")
        else:
            # Get selected button
            for button in self.sys_color_buttons.values():
                if button.isChecked():
                    sys_color = button.property("color_hex")
                    break
            else:
                # Default if none selected
                sys_color = "#FF0000"
        
        settings.setValue("style/system_msg_color", sys_color)
        
        # Save output font settings
        font = self.font_preview.property("selected_font")
        if font:
            settings.setValue("style/font_family", font.family())
            settings.setValue("style/font_size", font.pointSize())
        
        # Save output font color
        font_color = self.font_color_preview.property("color_hex")
        if font_color:
            settings.setValue("style/font_color", font_color)
            
        # Save user input font settings
        user_input_font = self.user_input_font_preview.property("selected_font")
        if user_input_font:
            settings.setValue("style/user_input_font_family", user_input_font.family())
            settings.setValue("style/user_input_font_size", user_input_font.pointSize())
        
        # Save user input font color
        user_input_font_color = self.user_input_font_color_preview.property("color_hex")
        if user_input_font_color:
            settings.setValue("style/user_input_font_color", user_input_font_color)
        
        # Save texture setting
        for button in self.texture_buttons.values():
            if button.isChecked():
                texture_name = button.property("texture_name")
                settings.setValue("style/texture_name", texture_name)
                break
        
        # Save transparency settings
        output_opacity = self.output_transparency_slider.value()
        input_opacity = self.input_transparency_slider.value()
        
        settings.setValue("style/output_opacity", output_opacity)
        settings.setValue("style/input_opacity", input_opacity)
