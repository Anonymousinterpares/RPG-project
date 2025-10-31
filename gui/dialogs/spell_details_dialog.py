#!/usr/bin/env python3
"""
Dialog showing details of a spell from the catalog.
Non-modal; caller should manage singleton behavior.
"""
from __future__ import annotations

from typing import Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QGroupBox,
    QHBoxLayout, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.utils.logging_config import get_logger

logger = get_logger("SPELL_DETAILS")


class SpellDetailsDialog(QDialog):
    """Enhanced spell details dialog with rich formatted display."""
    
    def __init__(self, spell_obj: Any, parent: Optional[object] = None):
        super().__init__(parent)
        
        self.spell_obj = spell_obj
        name = getattr(spell_obj, 'name', getattr(spell_obj, 'id', 'Spell'))
        
        self.setWindowTitle(f"Spell: {name}")
        self.setModal(False)
        self.resize(500, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D30;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface with formatted sections."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Create scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        
        # Header section
        self._create_header_section(content_layout)
        
        # Description section
        self._create_description_section(content_layout)
        
        # Mechanics section
        self._create_mechanics_section(content_layout)
        
        # Effects section
        self._create_effects_section(content_layout)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
    
    def _create_header_section(self, layout: QVBoxLayout):
        """Create the header with spell name, system, and role."""
        name = getattr(self.spell_obj, 'name', getattr(self.spell_obj, 'id', 'Spell'))
        system_id = getattr(self.spell_obj, 'system_id', 'Unknown System')
        role = getattr(self.spell_obj, 'combat_role', 'offensive').capitalize()
        
        # Role colors
        role_colors = {
            'Offensive': '#D94A38',
            'Defensive': '#0E639C',
            'Utility': '#8B7FBF'
        }
        role_color = role_colors.get(role, '#888888')
        
        header_label = QLabel()
        header_label.setText(f"""
            <div style='padding: 10px;'>
                <h2 style='color: #E0E0E0; margin: 0;'>{name}</h2>
                <p style='color: #BBBBBB; margin: 5px 0 0 0;'>
                    <span style='color: #1178BB;'>📖 {system_id}</span> &nbsp;|&nbsp;
                    <span style='color: {role_color};'>⚔ {role}</span>
                </p>
            </div>
        """)
        header_label.setTextFormat(Qt.RichText)
        header_label.setWordWrap(True)
        header_label.setStyleSheet("""
            QLabel {
                background-color: #3A3A3A;
                border: 1px solid #555555;
                border-radius: 5px;
            }
        """)
        layout.addWidget(header_label)
    
    def _create_description_section(self, layout: QVBoxLayout):
        """Create the thematic description section."""
        data = getattr(self.spell_obj, 'data', {}) or {}
        description = data.get('description', '')
        
        if description:
            group = QGroupBox("Description")
            group.setStyleSheet(self._get_groupbox_style())
            
            group_layout = QVBoxLayout(group)
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #CCCCCC; padding: 5px;")
            group_layout.addWidget(desc_label)
            
            layout.addWidget(group)
    
    def _create_mechanics_section(self, layout: QVBoxLayout):
        """Create the mechanics section with spell statistics."""
        data = getattr(self.spell_obj, 'data', {}) or {}
        
        group = QGroupBox("Mechanics")
        group.setStyleSheet(self._get_groupbox_style())
        
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)
        
        # Extract mechanics data
        mana_cost = data.get('mana_cost') or data.get('cost') or data.get('mp', 'Unknown')
        casting_time = data.get('casting_time') or data.get('cast_time', 'Unknown')
        spell_range = data.get('range', 'Unknown')
        target = data.get('target', 'Unknown')
        tags = data.get('tags', [])
        
        # Create formatted mechanics display
        mechanics_html = f"""
            <table style='width: 100%; color: #E0E0E0;'>
                <tr>
                    <td style='padding: 4px; width: 40%;'><b>💧 Mana Cost:</b></td>
                    <td style='padding: 4px;'>{mana_cost}</td>
                </tr>
                <tr style='background-color: #2A2A2A;'>
                    <td style='padding: 4px;'><b>⏱ Casting Time:</b></td>
                    <td style='padding: 4px;'>{casting_time}</td>
                </tr>
                <tr>
                    <td style='padding: 4px;'><b>📏 Range:</b></td>
                    <td style='padding: 4px;'>{spell_range}</td>
                </tr>
                <tr style='background-color: #2A2A2A;'>
                    <td style='padding: 4px;'><b>🎯 Target:</b></td>
                    <td style='padding: 4px;'>{target}</td>
                </tr>
            </table>
        """
        
        if tags:
            tags_str = ', '.join([str(t) for t in tags])
            mechanics_html += f"""
                <p style='margin-top: 8px; color: #AAAAAA;'>
                    <b>Tags:</b> {tags_str}
                </p>
            """
        
        mechanics_label = QLabel(mechanics_html)
        mechanics_label.setTextFormat(Qt.RichText)
        mechanics_label.setStyleSheet("padding: 5px;")
        group_layout.addWidget(mechanics_label)
        
        layout.addWidget(group)
    
    def _create_effects_section(self, layout: QVBoxLayout):
        """Create the effects section listing all spell effects."""
        atoms = getattr(self.spell_obj, 'effect_atoms', []) or []
        
        group = QGroupBox("Effects")
        group.setStyleSheet(self._get_groupbox_style())
        
        group_layout = QVBoxLayout(group)
        
        if atoms:
            for i, atom in enumerate(atoms, 1):
                effect_widget = self._create_effect_widget(i, atom)
                group_layout.addWidget(effect_widget)
        else:
            no_effects_label = QLabel("No structured effects defined.")
            no_effects_label.setStyleSheet("color: #888888; padding: 5px; font-style: italic;")
            group_layout.addWidget(no_effects_label)
        
        layout.addWidget(group)
    
    def _create_effect_widget(self, index: int, atom: dict) -> QFrame:
        """Create a widget for a single effect atom."""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #252528;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(8, 6, 8, 6)
        frame_layout.setSpacing(4)
        
        # Effect type and icon
        effect_type = atom.get('type', 'effect')
        effect_icons = {
            'damage': '⚔',
            'heal': '❤',
            'buff': '↑',
            'debuff': '↓',
            'status': '✦'
        }
        icon = effect_icons.get(effect_type, '◆')
        
        type_label = QLabel(f"<b>{icon} Effect {index}: {effect_type.capitalize()}</b>")
        type_label.setStyleSheet("color: #E0E0E0;")
        type_label.setTextFormat(Qt.RichText)
        frame_layout.addWidget(type_label)
        
        # Effect details
        details = []
        if 'selector' in atom:
            details.append(f"<b>Target:</b> {atom['selector']}")
        if 'magnitude' in atom:
            details.append(f"<b>Magnitude:</b> {atom['magnitude']}")
        if 'damage_type' in atom:
            details.append(f"<b>Damage Type:</b> {atom['damage_type']}")
        if 'status_type' in atom:
            details.append(f"<b>Status:</b> {atom['status_type']}")
        if 'duration' in atom:
            details.append(f"<b>Duration:</b> {atom['duration']}")
        if 'typed' in atom:
            details.append(f"<b>Type:</b> {atom['typed']}")
        
        if details:
            details_html = " &nbsp;|&nbsp; ".join(details)
            details_label = QLabel(details_html)
            details_label.setTextFormat(Qt.RichText)
            details_label.setWordWrap(True)
            details_label.setStyleSheet("color: #BBBBBB; font-size: 9pt;")
            frame_layout.addWidget(details_label)
        
        return frame
    
    def _get_groupbox_style(self) -> str:
        """Get consistent QGroupBox styling."""
        return """
            QGroupBox {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                color: #E0E0E0;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
                padding-top: 5px;
            }
        """
