#!/usr/bin/env python3
"""
Target selection dialog for spell casting.
Shows targets with HP bars, color coding, and icons.
"""
from __future__ import annotations

from typing import Optional, Any, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QProgressBar, QScrollArea, QWidget
)
from PySide6.QtGui import QFont

from core.utils.logging_config import get_logger

logger = get_logger("TARGET_SELECTION")


class TargetButton(QFrame):
    """Button-like widget for selecting a target with HP visualization."""
    
    clicked = Signal(str)  # entity_id
    
    def __init__(self, entity: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.entity = entity
        self.entity_id = entity.id
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        
        # Get entity info
        self.name = getattr(entity, 'combat_name', 'Unknown')
        
        # Get HP info
        try:
            self.current_hp = getattr(entity, 'current_hp', 0)
            self.max_hp = getattr(entity, 'max_hp', 1)
            self.hp_percent = (self.current_hp / self.max_hp * 100) if self.max_hp > 0 else 0
        except Exception:
            self.current_hp = 0
            self.max_hp = 1
            self.hp_percent = 0
        
        self._setup_ui()
        self._apply_normal_style()
    
    def _setup_ui(self):
        """Set up the UI for this target button."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # Name label
        name_label = QLabel(self.name)
        name_label.setFont(QFont("Arial", 11, QFont.Bold))
        name_label.setStyleSheet("color: #E0E0E0; background: transparent;")
        layout.addWidget(name_label)
        
        # HP info layout
        hp_layout = QHBoxLayout()
        hp_layout.setSpacing(8)
        
        # HP text
        hp_text = QLabel(f"{int(self.current_hp)} / {int(self.max_hp)}")
        hp_text.setFont(QFont("Arial", 9))
        hp_text.setStyleSheet("color: #BBBBBB; background: transparent;")
        hp_text.setFixedWidth(80)
        hp_layout.addWidget(hp_text)
        
        # HP bar
        hp_bar = QProgressBar()
        hp_bar.setRange(0, 100)
        hp_bar.setValue(int(self.hp_percent))
        hp_bar.setTextVisible(False)
        hp_bar.setFixedHeight(12)
        
        # Color based on HP percentage
        if self.hp_percent > 75:
            bar_color = "#28A745"  # Green - healthy
        elif self.hp_percent > 50:
            bar_color = "#FFC107"  # Yellow - moderate
        elif self.hp_percent > 25:
            bar_color = "#FF9800"  # Orange - low
        else:
            bar_color = "#DC3545"  # Red - critical
        
        hp_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #2A2A2A;
                border: 1px solid #555555;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 2px;
            }}
        """)
        hp_layout.addWidget(hp_bar, 1)
        
        layout.addLayout(hp_layout)
    
    def _apply_normal_style(self):
        """Apply normal (not hovered) style."""
        self.setStyleSheet("""
            TargetButton {
                background-color: #2D2D30;
                border: 2px solid #555555;
                border-radius: 5px;
            }
            TargetButton:hover {
                background-color: #353538;
                border-color: #0E639C;
            }
        """)
    
    def _apply_hover_style(self):
        """Apply hover style."""
        self.setStyleSheet("""
            TargetButton {
                background-color: #353538;
                border: 2px solid #0E639C;
                border-radius: 5px;
            }
        """)
    
    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.entity_id)
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse enter."""
        self._apply_hover_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._apply_normal_style()
        super().leaveEvent(event)


class TargetSelectionDialog(QDialog):
    """Dialog for selecting a spell target with visual HP indicators."""
    
    # Signal emitted when target is selected
    target_selected = Signal(str)  # entity_id
    
    def __init__(
        self, 
        targets: List[Any], 
        spell_name: str = "Spell",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self.targets = targets
        self.spell_name = spell_name
        self.selected_target_id: Optional[str] = None
        
        self.setWindowTitle(f"Select Target for {spell_name}")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header
        header = QLabel(f"🎯 Choose a target for <b>{self.spell_name}</b>")
        header.setTextFormat(Qt.RichText)
        header.setFont(QFont("Arial", 11))
        header.setStyleSheet("color: #E0E0E0; padding: 5px;")
        header.setWordWrap(True)
        main_layout.addWidget(header)
        
        # Scroll area for targets
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)
        
        # Add target buttons
        for target in self.targets:
            target_btn = TargetButton(target)
            target_btn.clicked.connect(self._on_target_clicked)
            scroll_layout.addWidget(target_btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)
        
        # Cancel button
        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: 2px solid #666666;
                border-radius: 6px;
                font-size: 10pt;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        cancel_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(cancel_layout)
    
    def _on_target_clicked(self, entity_id: str):
        """Handle target button click."""
        self.selected_target_id = entity_id
        self.target_selected.emit(entity_id)
        self.accept()
    
    def get_selected_target(self) -> Optional[str]:
        """Get the selected target ID."""
        return self.selected_target_id
