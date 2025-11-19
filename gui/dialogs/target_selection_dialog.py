#!/usr/bin/env python3
"""
Target selection dialog for spell casting.
Shows targets with HP bars, color coding, and icons.
"""
from __future__ import annotations

from typing import Dict, Optional, Any, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QProgressBar, QScrollArea, QWidget
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Slot

from core.utils.logging_config import get_logger
from gui.styles.stylesheet_factory import create_dialog_style, create_styled_button_style
from gui.styles.theme_manager import get_theme_manager

logger = get_logger("TARGET_SELECTION")


class TargetButton(QFrame):
    """Button-like widget for selecting a target with HP visualization."""
    
    clicked = Signal(str)  # entity_id
    
    def __init__(self, entity: Any, palette: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.entity = entity
        self.entity_id = entity.id
        self.palette = palette
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
        
        colors = self.palette['colors']
        pb_styles = self.palette['progress_bars']

        # Name label
        name_label = QLabel(self.name)
        name_label.setFont(QFont("Arial", 11, QFont.Bold))
        name_label.setStyleSheet(f"color: {colors['text_primary']}; background: transparent;")
        layout.addWidget(name_label)
        
        # HP info layout
        hp_layout = QHBoxLayout()
        hp_layout.setSpacing(8)
        
        # HP text
        hp_text = QLabel(f"{int(self.current_hp)} / {int(self.max_hp)}")
        hp_text.setFont(QFont("Arial", 9))
        hp_text.setStyleSheet(f"color: {colors['text_secondary']}; background: transparent;")
        hp_text.setFixedWidth(80)
        hp_layout.addWidget(hp_text)
        
        # HP bar
        hp_bar = QProgressBar()
        hp_bar.setRange(0, 100)
        hp_bar.setValue(int(self.hp_percent))
        hp_bar.setTextVisible(False)
        hp_bar.setFixedHeight(12)
        
        # Color based on HP percentage
        if self.hp_percent > 50:
            bar_color = pb_styles.get('hp_normal', '#D94A38')
        elif self.hp_percent > 25:
            bar_color = pb_styles.get('hp_low', '#cc0000')
        else:
            bar_color = pb_styles.get('hp_critical', '#990000')
        
        hp_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {pb_styles.get('bg', '#1a1410')};
                border: 1px solid {colors['border_dark']};
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
        colors = self.palette['colors']
        self.setStyleSheet(f"""
            TargetButton {{
                background-color: {colors['bg_light']};
                border: 2px solid {colors['border_dark']};
                border-radius: 5px;
            }}
            TargetButton:hover {{
                background-color: {colors['state_hover']};
                border-color: {colors['state_active_border']};
            }}
        """)
    
    def _apply_hover_style(self):
        """Apply hover style."""
        colors = self.palette['colors']
        self.setStyleSheet(f"""
            TargetButton {{
                background-color: {colors['state_hover']};
                border: 2px solid {colors['state_active_border']};
                border-radius: 5px;
            }}
        """)

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
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        self.targets = targets
        self.spell_name = spell_name
        self.selected_target_id: Optional[str] = None
        
        self.setWindowTitle(f"Select Target for {spell_name}")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        self._setup_ui()
        self._update_theme()
    
    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        # Guard against premature call
        if not hasattr(self, 'header'):
            return

        if palette:
            self.palette = palette
            
        colors = self.palette['colors']
        
        self.setStyleSheet(create_dialog_style(self.palette))
        
        self.header.setStyleSheet(f"color: {colors['text_primary']}; padding: 5px;")
        self.cancel_btn.setStyleSheet(create_styled_button_style(self.palette))
        
        # Recreate target buttons to apply new theme
        # Clear existing
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add target buttons with current palette
        for target in self.targets:
            target_btn = TargetButton(target, self.palette)
            target_btn.clicked.connect(self._on_target_clicked)
            self.scroll_layout.addWidget(target_btn)
        
        self.scroll_layout.addStretch()

    def _setup_ui(self):
        """Set up the dialog UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header
        self.header = QLabel(f"🎯 Choose a target for <b>{self.spell_name}</b>")
        self.header.setTextFormat(Qt.RichText)
        self.header.setFont(QFont("Arial", 11))
        self.header.setWordWrap(True)
        main_layout.addWidget(self.header)
        
        # Scroll area for targets
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(8)
        
        # Target buttons will be added in _update_theme
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)
        
        # Cancel button
        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        cancel_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(cancel_layout)