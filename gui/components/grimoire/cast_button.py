#!/usr/bin/env python3
"""
Enhanced Cast button with support for 7 visual states and image backgrounds.
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QPixmap, QIcon, QPalette, QColor

from core.utils.logging_config import get_logger

logger = get_logger("GRIMOIRE")


class CastButtonState(Enum):
    """Enumeration of possible Cast button states."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    CLICKING = "clicking"
    HOVERING = "hovering"
    INSUFFICIENT_MANA = "insufficient_mana"
    SUCCESS = "success"
    FAIL = "fail"


class CastButton(QPushButton):
    """
    Enhanced Cast button supporting 7 visual states with image backgrounds.
    Falls back to colored styles if images are not found.
    """
    
    # Signal emitted when button is clicked in valid state
    cast_requested = Signal()
    
    # Image paths for each state (relative to images/gui/)
    STATE_IMAGE_PATHS = {
        CastButtonState.ENABLED: "cast_button_enabled.png",
        CastButtonState.DISABLED: "cast_button_disabled.png",
        CastButtonState.CLICKING: "cast_button_clicking.png",
        CastButtonState.HOVERING: "cast_button_hovering.png",
        CastButtonState.INSUFFICIENT_MANA: "cast_button_insufficient_mana.png",
        CastButtonState.SUCCESS: "cast_button_success.png",
        CastButtonState.FAIL: "cast_button_fail.png"
    }
    
    # Fallback colors for each state
    STATE_FALLBACK_COLORS = {
        CastButtonState.ENABLED: "#0E639C",      # Blue
        CastButtonState.DISABLED: "#555555",      # Gray
        CastButtonState.CLICKING: "#083D5F",      # Dark blue
        CastButtonState.HOVERING: "#1178BB",      # Light blue
        CastButtonState.INSUFFICIENT_MANA: "#D97728",  # Orange
        CastButtonState.SUCCESS: "#28A745",       # Green
        CastButtonState.FAIL: "#8B0000"           # Dark red
    }
    
    def __init__(self, parent: Optional[QPushButton] = None):
        """
        Initialize the Cast button.
        
        Args:
            parent: Parent widget
        """
        super().__init__("Cast Spell", parent)
        
        self._current_state = CastButtonState.DISABLED
        self._state_images = {}
        self._using_images = False
        
        # Flash timer for success/fail states
        self._flash_timer: Optional[QTimer] = None
        self._flash_restore_state: Optional[CastButtonState] = None
        
        # Load images
        self._load_state_images()
        
        # Set initial size
        self.setMinimumSize(QSize(120, 40))
        self.setMaximumHeight(50)
        
        # Apply initial state
        self.set_state(CastButtonState.DISABLED)
        
        # Connect click signal
        self.clicked.connect(self._on_clicked)
    
    def _load_state_images(self):
        """Load state images from disk or prepare fallback styles."""
        try:
            # Try to find the images directory
            # Search from current file location upward
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # Navigate up to project root (look for 'images' folder)
            for _ in range(5):  # Max 5 levels up
                images_dir = os.path.join(project_root, 'images', 'gui')
                if os.path.exists(images_dir):
                    break
                project_root = os.path.dirname(project_root)
            else:
                logger.warning("Could not find images/gui directory, using fallback colors")
                self._using_images = False
                return
            
            # Load each state image
            loaded_count = 0
            for state, filename in self.STATE_IMAGE_PATHS.items():
                image_path = os.path.join(images_dir, filename)
                if os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        self._state_images[state] = pixmap
                        loaded_count += 1
            
            if loaded_count > 0:
                self._using_images = True
                logger.info(f"Loaded {loaded_count}/7 cast button state images")
            else:
                logger.info("No cast button images found, using fallback colors")
                self._using_images = False
        
        except Exception as e:
            logger.warning(f"Error loading cast button images: {e}, using fallback")
            self._using_images = False
    
    def set_state(self, state: CastButtonState):
        """
        Set the visual state of the button.
        
        Args:
            state: The desired button state
        """
        self._current_state = state
        
        # Enable/disable button based on state
        is_interactive = state not in [
            CastButtonState.DISABLED,
            CastButtonState.INSUFFICIENT_MANA,
            CastButtonState.SUCCESS,
            CastButtonState.FAIL
        ]
        super().setEnabled(is_interactive)
        
        # Apply visual styling
        if self._using_images and state in self._state_images:
            self._apply_image_style(state)
        else:
            self._apply_fallback_style(state)
    
    def _apply_image_style(self, state: CastButtonState):
        """
        Apply image-based styling for the given state.
        
        Args:
            state: The button state
        """
        pixmap = self._state_images.get(state)
        if pixmap:
            self.setIcon(QIcon(pixmap))
            self.setIconSize(self.size())
            # Minimal text styling for image buttons
            self.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    color: #FFFFFF;
                    font-size: 12pt;
                    font-weight: bold;
                    text-align: center;
                }
            """)
    
    def _apply_fallback_style(self, state: CastButtonState):
        """
        Apply color-based fallback styling for the given state.
        
        Args:
            state: The button state
        """
        base_color = self.STATE_FALLBACK_COLORS.get(state, "#555555")
        
        # Calculate hover and press colors (slightly lighter/darker)
        hover_color = self._adjust_color_brightness(base_color, 1.2)
        press_color = self._adjust_color_brightness(base_color, 0.8)
        
        stylesheet = f"""
            QPushButton {{
                background-color: {base_color};
                color: #FFFFFF;
                border: 2px solid #666666;
                border-radius: 6px;
                font-size: 12pt;
                font-weight: bold;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border-color: #888888;
            }}
            QPushButton:pressed {{
                background-color: {press_color};
            }}
            QPushButton:disabled {{
                background-color: #3A3A3A;
                color: #777777;
                border-color: #555555;
            }}
        """
        self.setStyleSheet(stylesheet)
    
    def _adjust_color_brightness(self, hex_color: str, factor: float) -> str:
        """
        Adjust the brightness of a hex color.
        
        Args:
            hex_color: Hex color string (e.g., "#0E639C")
            factor: Brightness factor (> 1 = lighter, < 1 = darker)
        
        Returns:
            Adjusted hex color string
        """
        try:
            # Remove '#' if present
            hex_color = hex_color.lstrip('#')
            
            # Convert to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Adjust brightness
            r = min(255, int(r * factor))
            g = min(255, int(g * factor))
            b = min(255, int(b * factor))
            
            # Convert back to hex
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color
    
    def flash_success(self):
        """Flash the button to SUCCESS state for 250ms, then restore previous state."""
        self._flash_state(CastButtonState.SUCCESS, 250)
    
    def flash_fail(self):
        """Flash the button to FAIL state for 250ms, then restore previous state."""
        self._flash_state(CastButtonState.FAIL, 250)
    
    def _flash_state(self, flash_state: CastButtonState, duration_ms: int):
        """
        Temporarily flash a state, then restore the previous state.
        
        Args:
            flash_state: The state to flash
            duration_ms: Duration in milliseconds
        """
        # Store current state for restoration
        self._flash_restore_state = self._current_state
        
        # Apply flash state
        self.set_state(flash_state)
        
        # Set timer to restore
        if self._flash_timer:
            self._flash_timer.stop()
            self._flash_timer.deleteLater()
        
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._restore_from_flash)
        self._flash_timer.start(duration_ms)
    
    def _restore_from_flash(self):
        """Restore the button state after a flash."""
        if self._flash_restore_state:
            self.set_state(self._flash_restore_state)
            self._flash_restore_state = None
    
    def _on_clicked(self):
        """Handle button click."""
        if self._current_state == CastButtonState.ENABLED or self._current_state == CastButtonState.HOVERING:
            # Briefly show clicking state
            self.set_state(CastButtonState.CLICKING)
            
            # Emit the cast requested signal
            QTimer.singleShot(100, self.cast_requested.emit)
            
            # Return to enabled state after brief delay
            QTimer.singleShot(150, lambda: self.set_state(CastButtonState.ENABLED))
    
    def enterEvent(self, event):
        """Handle mouse enter event."""
        if self._current_state == CastButtonState.ENABLED:
            self.set_state(CastButtonState.HOVERING)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave event."""
        if self._current_state == CastButtonState.HOVERING:
            self.set_state(CastButtonState.ENABLED)
        super().leaveEvent(event)
    
    def setEnabled(self, enabled: bool):
        """
        Override setEnabled to manage state properly.
        
        Args:
            enabled: True to enable, False to disable
        """
        if enabled:
            if self._current_state == CastButtonState.DISABLED:
                self.set_state(CastButtonState.ENABLED)
        else:
            self.set_state(CastButtonState.DISABLED)
