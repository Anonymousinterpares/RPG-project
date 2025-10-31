#!/usr/bin/env python3
"""
Collapsible section widget for grouping spells by magic system.
Features smooth animations using QPropertyAnimation.
"""
from __future__ import annotations

from typing import Optional, List, Any, Callable

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize, Property
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSizePolicy
)
from PySide6.QtGui import QFont, QTransform, QPainter, QPixmap

from core.utils.logging_config import get_logger

logger = get_logger("GRIMOIRE")


class CollapsibleMagicSystemSection(QWidget):
    """
    A collapsible section widget that contains spells for a single magic system.
    Features animated expand/collapse with arrow rotation.
    """
    
    # Signal emitted when expansion state changes
    expansion_changed = Signal(bool)  # True if expanded, False if collapsed
    
    def __init__(
        self, 
        system_id: str, 
        system_name: str,
        spell_count: int = 0,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the collapsible section.
        
        Args:
            system_id: Internal ID of the magic system
            system_name: Display name of the magic system
            spell_count: Number of spells in this system
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.system_id = system_id
        self.system_name = system_name
        self._spell_count = spell_count
        self._is_expanded = True
        self._content_height = 0
        
        # Animation
        self._animation: Optional[QPropertyAnimation] = None
        self._arrow_rotation = 90  # 0 = right, 90 = down
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header
        self._create_header()
        
        # Create content area (spells container)
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 5, 10, 5)
        self.content_layout.setSpacing(3)
        
        # Style content area
        self.content_area.setStyleSheet("""
            QWidget {
                background-color: #2A2A2A;
                border: none;
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 5px;
            }
        """)
        
        self.main_layout.addWidget(self.content_area)
        
        # Start expanded
        self.content_area.setVisible(True)
    
    def _create_header(self):
        """Create the clickable header section."""
        self.header = QFrame()
        self.header.setFrameShape(QFrame.StyledPanel)
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setStyleSheet("""
            QFrame {
                background-color: #3A3A3A;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
            }
            QFrame:hover {
                background-color: #454545;
            }
        """)
        
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        
        # Arrow indicator (will be rotated)
        self.arrow_label = QLabel("▶")
        self.arrow_label.setFont(QFont("Arial", 10))
        self.arrow_label.setStyleSheet("color: #BBBBBB; background: transparent; border: none;")
        self.arrow_label.setFixedSize(16, 16)
        self.arrow_label.setAlignment(Qt.AlignCenter)
        self._update_arrow_rotation()
        
        # System name
        self.title_label = QLabel(f"{self.system_name} ({self._spell_count})")
        self.title_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.title_label.setStyleSheet("color: #E0E0E0; background: transparent; border: none;")
        
        header_layout.addWidget(self.arrow_label)
        header_layout.addWidget(self.title_label, 1)
        
        # Make header clickable
        self.header.mousePressEvent = lambda event: self.toggle_expansion()
        
        self.main_layout.addWidget(self.header)
    
    def add_spell_widget(self, spell_widget: QWidget):
        """
        Add a spell widget to this section's content area.
        
        Args:
            spell_widget: The spell item widget to add
        """
        self.content_layout.addWidget(spell_widget)
        self._spell_count += 1
        self._update_title()
    
    def clear_spells(self):
        """Remove all spell widgets from the content area."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._spell_count = 0
        self._update_title()
    
    def toggle_expansion(self):
        """Toggle between expanded and collapsed states with animation."""
        if self._is_expanded:
            self.collapse()
        else:
            self.expand()
    
    def expand(self):
        """Expand the section with animation."""
        if self._is_expanded:
            return
        
        self._is_expanded = True
        self.expansion_changed.emit(True)
        
        # Animate content visibility
        self.content_area.setVisible(True)
        
        # Animate arrow rotation
        self._animate_arrow(90)
        
        # Animate height (content area will grow)
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self._animation.setDuration(250)
        self._animation.setStartValue(0)
        
        # Calculate target height
        target_height = self.content_area.sizeHint().height()
        self._animation.setEndValue(target_height if target_height > 0 else 300)
        
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._animation.start()
    
    def collapse(self):
        """Collapse the section with animation."""
        if not self._is_expanded:
            return
        
        self._is_expanded = False
        self.expansion_changed.emit(False)
        
        # Animate arrow rotation
        self._animate_arrow(0)
        
        # Animate height (content area will shrink)
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self._animation.setDuration(250)
        self._animation.setStartValue(self.content_area.height())
        self._animation.setEndValue(0)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._animation.finished.connect(lambda: self.content_area.setVisible(False))
        self._animation.start()
    
    def _animate_arrow(self, target_rotation: int):
        """
        Animate the arrow rotation.
        
        Args:
            target_rotation: Target rotation angle (0 for right, 90 for down)
        """
        # Simple approach: directly set rotation and update
        self._arrow_rotation = target_rotation
        self._update_arrow_rotation()
    
    def _update_arrow_rotation(self):
        """Update the arrow label based on current rotation."""
        if self._arrow_rotation == 0:
            self.arrow_label.setText("▶")
        else:
            self.arrow_label.setText("▼")
    
    def _update_title(self):
        """Update the section title with current spell count."""
        self.title_label.setText(f"{self.system_name} ({self._spell_count})")
    
    @property
    def is_expanded(self) -> bool:
        """Check if the section is currently expanded."""
        return self._is_expanded
    
    def set_spell_count(self, count: int):
        """
        Update the spell count display.
        
        Args:
            count: Number of spells in this system
        """
        self._spell_count = count
        self._update_title()
