#!/usr/bin/env python3
"""
Custom spell item widget for displaying individual spells with visual hierarchy.
Features role-based color coding, hover effects, and selection states.
"""
from __future__ import annotations

from typing import Optional, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QVBoxLayout
from PySide6.QtGui import QFont, QCursor

from core.utils.logging_config import get_logger

logger = get_logger("GRIMOIRE")


class SpellItemWidget(QFrame):
    """
    Widget displaying a single spell with visual styling based on combat role.
    """
    
    # Signals
    clicked = Signal(str)  # spell_id
    double_clicked = Signal(str)  # spell_id
    right_clicked = Signal(str)  # spell_id
    
    # Role-based colors
    ROLE_COLORS = {
        'offensive': '#D94A38',  # Red/Orange
        'defensive': '#0E639C',  # Blue
        'utility': '#8B7FBF',    # Purple/Gray
        'unknown': '#666666'     # Dark gray fallback
    }
    
    def __init__(
        self, 
        spell_id: str,
        spell_name: str,
        spell_obj: Any,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the spell item widget.
        
        Args:
            spell_id: Internal spell identifier
            spell_name: Display name of the spell
            spell_obj: The spell object from catalog
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.spell_id = spell_id
        self.spell_name = spell_name
        self.spell_obj = spell_obj
        self._is_selected = False
        self._is_on_cooldown = False  # Placeholder for future cooldown system
        
        # Extract spell properties
        self.combat_role = getattr(spell_obj, 'combat_role', 'offensive').lower()
        self.mana_cost = self._get_mana_cost()
        self.casting_time = self._get_casting_time()
        self.spell_range = self._get_range()
        
        self._setup_ui()
        self._apply_normal_style()
    
    def _get_mana_cost(self) -> float:
        """Extract mana cost from spell object."""
        try:
            data = getattr(self.spell_obj, 'data', {}) or {}
            cost = data.get('mana_cost') or data.get('cost') or data.get('mp')
            return float(cost) if cost is not None else 0.0
        except Exception:
            return 0.0
    
    def _get_casting_time(self) -> str:
        """Extract casting time from spell object."""
        try:
            data = getattr(self.spell_obj, 'data', {}) or {}
            time = data.get('casting_time') or data.get('cast_time')
            return str(time) if time else "1 action"
        except Exception:
            return "1 action"
    
    def _get_range(self) -> str:
        """Extract range from spell object."""
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
        info_label = QLabel(f"💧 {self.mana_cost} | ⏱ {self.casting_time} | 📏 {self.spell_range}")
        info_label.setFont(QFont("Arial", 8))
        info_label.setStyleSheet("color: #AAAAAA;")
        name_layout.addWidget(info_label)
        
        main_layout.addLayout(name_layout, 1)
        
        # Right side: role indicator
        role_label = QLabel(self.combat_role.capitalize())
        role_label.setFont(QFont("Arial", 8, QFont.Bold))
        role_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        role_color = self.ROLE_COLORS.get(self.combat_role, self.ROLE_COLORS['unknown'])
        role_label.setStyleSheet(f"color: {role_color};")
        main_layout.addWidget(role_label)
    
    def _apply_normal_style(self):
        """Apply normal (unselected, not hovered) styling."""
        role_color = self.ROLE_COLORS.get(self.combat_role, self.ROLE_COLORS['unknown'])
        
        if self._is_on_cooldown:
            # Grayed out for cooldown
            self.setStyleSheet(f"""
                SpellItemWidget {{
                    background-color: #2A2A2A;
                    border-left: 3px solid #555555;
                    border-radius: 3px;
                    opacity: 0.5;
                }}
                QLabel {{
                    background: transparent;
                    color: #777777;
                }}
            """)
            self.setEnabled(False)
        else:
            self.setStyleSheet(f"""
                SpellItemWidget {{
                    background-color: #2D2D30;
                    border-left: 3px solid {role_color};
                    border-radius: 3px;
                }}
                SpellItemWidget:hover {{
                    background-color: #353538;
                }}
                QLabel {{
                    background: transparent;
                    color: #E0E0E0;
                }}
            """)
            self.setEnabled(True)
    
    def _apply_selected_style(self):
        """Apply selected styling."""
        role_color = self.ROLE_COLORS.get(self.combat_role, self.ROLE_COLORS['unknown'])
        self.setStyleSheet(f"""
            SpellItemWidget {{
                background-color: #3E3E42;
                border-left: 4px solid {role_color};
                border-radius: 3px;
                border: 2px solid {role_color};
            }}
            QLabel {{
                background: transparent;
                color: #FFFFFF;
            }}
        """)
    
    def set_selected(self, selected: bool):
        """
        Set the selection state of this spell item.
        
        Args:
            selected: True if selected, False otherwise
        """
        self._is_selected = selected
        if selected:
            self._apply_selected_style()
        else:
            self._apply_normal_style()
    
    def set_on_cooldown(self, on_cooldown: bool):
        """
        Set the cooldown state (placeholder for future implementation).
        
        Args:
            on_cooldown: True if spell is on cooldown
        """
        self._is_on_cooldown = on_cooldown
        self._apply_normal_style()
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.spell_id)
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self.spell_id)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click events."""
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.spell_id)
        super().mouseDoubleClickEvent(event)
    
    @property
    def is_selected(self) -> bool:
        """Check if this spell is currently selected."""
        return self._is_selected
