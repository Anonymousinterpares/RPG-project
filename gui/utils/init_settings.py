#!/usr/bin/env python3
"""
Initialize application settings with default values if they don't exist.
"""

import logging
from PySide6.QtCore import QSettings

def init_default_settings():
    """Initialize default settings if they don't exist."""

    settings = QSettings("RPGGame", "Settings")

    # Check if style settings exist and create defaults if not
    if not settings.contains("style/output_bg_color"):
        settings.setValue("style/output_bg_color", "#D2B48C")  # Light brown

    if not settings.contains("style/system_msg_color"):
        settings.setValue("style/system_msg_color", "#FF0000")  # Red

    if not settings.contains("style/font_family"):
        settings.setValue("style/font_family", "Garamond")

    if not settings.contains("style/font_size"):
        settings.setValue("style/font_size", 14)

    if not settings.contains("style/font_color"):
        settings.setValue("style/font_color", "#000000")  # Black

    # Initialize texture and transparency settings
    if not settings.contains("style/texture_name"):
        settings.setValue("style/texture_name", "subtle_noise")

    if not settings.contains("style/output_opacity"):
        settings.setValue("style/output_opacity", 100)

    if not settings.contains("style/input_opacity"):
        settings.setValue("style/input_opacity", 100)

    # Initialize display settings if they don't exist
    if not settings.contains("display/resolution"):
        settings.setValue("display/resolution", (1280, 720))

    if not settings.contains("display/mode"):
        settings.setValue("display/mode", "windowed")

    if not settings.contains("display/ui_scale"):
        settings.setValue("display/ui_scale", 1.0)
    # Initialize text speed setting
    if not settings.contains("display/text_speed_delay"):
        settings.setValue("display/text_speed_delay", 30) # Default delay in ms per character

    # Initialize sound settings if they don't exist
    if not settings.contains("sound/master_volume"):
        settings.setValue("sound/master_volume", 100)

    if not settings.contains("sound/music_volume"):
        settings.setValue("sound/music_volume", 100)

    if not settings.contains("sound/effects_volume"):
        settings.setValue("sound/effects_volume", 100)

    if not settings.contains("sound/enabled"):
        settings.setValue("sound/enabled", True)

    # Initialize gameplay settings if they don't exist
    if not settings.contains("gameplay/difficulty"):
        settings.setValue("gameplay/difficulty", "Normal")
    if not settings.contains("gameplay/encounter_size"):
        settings.setValue("gameplay/encounter_size", "Solo")

    if not settings.contains("gameplay/autosave_interval"):
        settings.setValue("gameplay/autosave_interval", 0)

    if not settings.contains("gameplay/tutorial_enabled"):
        settings.setValue("gameplay/tutorial_enabled", True)

    # Initialize developer settings if they don't exist
    if not settings.contains("dev/enabled"):
        settings.setValue("dev/enabled", False)
    if not settings.contains("dev/show_stats_manager_logs"):
        settings.setValue("dev/show_stats_manager_logs", False)

    # Sync settings to disk
    settings.sync()

    logging.info("Default settings initialized")
