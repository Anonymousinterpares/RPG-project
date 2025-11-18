#!/usr/bin/env python3
"""
Custom spell item widget for displaying individual spells with visual hierarchy.
Features role-based color coding, hover effects, and selection states.
"""
from __future__ import annotations

from typing import Optional, Any, Dict

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QVBoxLayout
from PySide6.QtGui import QFont, QCursor

from core.utils.logging_config import get_logger
from gui.styles.theme_manager import get_theme_manager

logger = get_logger("GRIMOIRE")

class SpellItemWidget(QFrame):
    """
    Widget displaying a single spell with visual styling based on combat role.
    """
    
    # Signals
    clicked = Signal(str)  # spell_id
    double_clicked = Signal(str)  # spell_id
    right_clicked = Signal(str)  # spell_id
    
    def __init__(
        self, 
        spell_id: str,
        spell_name: str,
        spell_obj: Any,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        self.spell_id = spell_id
        self.spell_name = spell_name
        self.spell_obj = spell_obj
        self._is_selected = False
        self._is_on_cooldown = False 
        
        # Extract spell properties
        self.combat_role = getattr(spell_obj, 'combat_role', 'offensive').lower()
        self.mana_cost = self._get_mana_cost()
        self.casting_time = self._get_casting_time()
        self.spell_range = self._get_range()
        
        self._setup_ui()
        
        # Apply initial theme (this will call _apply_normal_style)
        self._update_theme()
    
    def _get_mana_cost(self) -> float:
        try:
            data = getattr(self.spell_obj, 'data', {}) or {}
            cost = data.get('mana_cost') or data.get('cost') or data.get('mp')
            return float(cost) if cost is not None else 0.0
        except Exception:
            return 0.0
    
    def _get_casting_time(self) -> str:
        try:
            data = getattr(self.spell_obj, 'data', {}) or {}
            time = data.get('casting_time') or data.get('cast_time')
            return str(time) if time else "1 action"
        except Exception:
            return "1 action"
    
    def _get_range(self) -> str:
        try:
            data = getattr(self.spell_obj, 'data', {}) or {}
            rng = data.get('range')
            return str(rng) if rng else "Touch"
        except Exception:
            return "Touch"
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(8)
        
        # Left side: spell name
        name_layout = QVBoxLayout()
        name_layout.setSpacing(2)
        
        self.name_label = QLabel(self.spell_name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        name_layout.addWidget(self.name_label)
        
        # Spell info line (mana, time, range icons)
        self.info_label = QLabel(f"💧 {self.mana_cost} | ⏱ {self.casting_time} | 📏 {self.spell_range}")
        self.info_label.setFont(QFont("Arial", 8))
        name_layout.addWidget(self.info_label)
        
        main_layout.addLayout(name_layout, 1)
        
        # Right side: role indicator
        self.role_label = QLabel(self.combat_role.capitalize())
        self.role_label.setFont(QFont("Arial", 8, QFont.Bold))
        self.role_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addWidget(self.role_label)

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        
        # Define role colors based on theme
        self.role_colors = {
            'offensive': colors['accent_negative'],
            'defensive': colors['accent_positive'],
            'utility': colors['text_secondary'],
            'unknown': colors['text_disabled']
        }
        
        # Apply styles to labels
        self.info_label.setStyleSheet("color: #AAAAAA;") # Or theme equivalent
        
        role_color = self.role_colors.get(self.combat_role, self.role_colors['unknown'])
        self.role_label.setStyleSheet(f"color: {role_color};")
        
        # Re-apply frame style
        if self._is_selected:
            self._apply_selected_style()
        else:
            self._apply_normal_style()

    def _apply_normal_style(self):
        """Apply normal (unselected, not hovered) styling."""
        colors = self.palette['colors']
        role_color = self.role_colors.get(self.combat_role, self.role_colors['unknown'])
        
        if self._is_on_cooldown:
            self.setStyleSheet(f"""
                SpellItemWidget {{
                    background-color: {colors['bg_dark']};
                    border-left: 3px solid {colors['text_disabled']};
                    border-radius: 3px;
                    opacity: 0.5;
                }}
                QLabel {{
                    background: transparent;
                    color: {colors['text_disabled']};
                }}
            """)
            self.setEnabled(False)
        else:
            self.setStyleSheet(f"""
                SpellItemWidget {{
                    background-color: {colors['bg_dark']};
                    border-left: 3px solid {role_color};
                    border-radius: 3px;
                }}
                SpellItemWidget:hover {{
                    background-color: {colors['state_hover']};
                }}
                QLabel {{
                    background: transparent;
                    color: {colors['text_bright']};
                }}
            """)
            self.setEnabled(True)
    
    def _apply_selected_style(self):
        """Apply selected styling."""
        colors = self.palette['colors']
        role_color = self.role_colors.get(self.combat_role, self.role_colors['unknown'])
        self.setStyleSheet(f"""
            SpellItemWidget {{
                background-color: {colors['bg_medium']};
                border-left: 4px solid {role_color};
                border-radius: 3px;
                border: 2px solid {role_color};
            }}
            QLabel {{
                background: transparent;
                color: {colors['text_primary']};
            }}
        """)
    
    def set_selected(self, selected: bool):
        """Set the selection state of this spell item."""
        self._is_selected = selected
        if selected:
            self._apply_selected_style()
        else:
            self._apply_normal_style()
    
    def set_on_cooldown(self, on_cooldown: bool):
        """Set the cooldown state."""
        self._is_on_cooldown = on_cooldown
        self._apply_normal_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.spell_id)
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self.spell_id)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.spell_id)
        super().mouseDoubleClickEvent(event)
    
    @property
    def is_selected(self) -> bool:
        return self._is_selected