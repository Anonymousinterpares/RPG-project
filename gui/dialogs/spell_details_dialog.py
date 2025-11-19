#!/usr/bin/env python3
"""
Dialog showing details of a spell from the catalog.
Non-modal; caller should manage singleton behavior.
"""
from __future__ import annotations

from typing import Any, Optional, Dict

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QGroupBox,
    QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont

from core.utils.logging_config import get_logger
from gui.dialogs.base_dialog import BaseDialog
from gui.styles.theme_manager import get_theme_manager
from gui.styles.stylesheet_factory import create_dialog_style, create_groupbox_style

logger = get_logger("SPELL_DETAILS")

class SpellDetailsDialog(BaseDialog):
    """Enhanced spell details dialog with rich formatted display."""
    
    def __init__(self, spell_obj: Any, parent: Optional[object] = None):
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---
        
        self.spell_obj = spell_obj
        name = getattr(spell_obj, 'name', getattr(spell_obj, 'id', 'Spell'))
        
        self.setWindowTitle(f"Spell: {name}")
        self.setModal(False)
        self.resize(500, 600)
        
        self._setup_ui()
        self._update_theme()

        QTimer.singleShot(0, self._apply_cursors)
    
    def _setup_ui(self):
        """Set up the user interface structure."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)
        
        # Create scroll area for content
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

    @Slot(dict)
    def _update_theme(self, palette: Optional[Dict[str, Any]] = None):
        """Update styles from the theme palette."""
        # Guard against premature call from BaseDialog.__init__
        if not hasattr(self, 'scroll_area'):
            return

        if palette:
            self.palette = palette
            
        colors = self.palette['colors']
        
        # Apply dialog style
        self.setStyleSheet(create_dialog_style(self.palette))
        
        # Style scroll area
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
        """)
        
        # Rebuild content to apply new colors to HTML labels
        self._rebuild_content()

    def _rebuild_content(self):
        """Rebuilds the content layout with current theme colors."""
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Recreate sections
        self._create_header_section(self.content_layout)
        self._create_description_section(self.content_layout)
        self._create_mechanics_section(self.content_layout)
        self._create_effects_section(self.content_layout)
        
        self.content_layout.addStretch()

    def _create_header_section(self, layout: QVBoxLayout):
        """Create the header with spell name, system, and role."""
        colors = self.palette['colors']
        
        name = getattr(self.spell_obj, 'name', getattr(self.spell_obj, 'id', 'Spell'))
        system_id = getattr(self.spell_obj, 'system_id', 'Unknown System')
        role = getattr(self.spell_obj, 'combat_role', 'offensive').capitalize()
        
        # Map roles to theme colors
        role_colors = {
            'Offensive': colors['accent_negative'],
            'Defensive': colors['accent_positive'],
            'Utility': colors['text_secondary']
        }
        role_color = role_colors.get(role, colors['text_secondary'])
        
        header_label = QLabel()
        header_label.setText(f"""
            <div style='padding: 10px;'>
                <h2 style='color: {colors['text_primary']}; margin: 0;'>{name}</h2>
                <p style='color: {colors['text_secondary']}; margin: 5px 0 0 0;'>
                    <span style='color: {colors['res_mana']};'>📖 {system_id}</span> &nbsp;|&nbsp;
                    <span style='color: {role_color};'>⚔ {role}</span>
                </p>
            </div>
        """)
        header_label.setTextFormat(Qt.RichText)
        header_label.setWordWrap(True)
        header_label.setStyleSheet(f"""
            QLabel {{
                background-color: {colors['bg_light']};
                border: 1px solid {colors['border_dark']};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(header_label)

    def _create_description_section(self, layout: QVBoxLayout):
        """Create the thematic description section."""
        colors = self.palette['colors']
        data = getattr(self.spell_obj, 'data', {}) or {}
        description = data.get('description', '')
        
        if description:
            group = QGroupBox("Description")
            group.setStyleSheet(create_groupbox_style(self.palette))
            
            group_layout = QVBoxLayout(group)
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"color: {colors['text_secondary']}; padding: 5px;")
            group_layout.addWidget(desc_label)
            
            layout.addWidget(group)

    def _create_mechanics_section(self, layout: QVBoxLayout):
        """Create the mechanics section with spell statistics."""
        colors = self.palette['colors']
        data = getattr(self.spell_obj, 'data', {}) or {}
        
        group = QGroupBox("Mechanics")
        group.setStyleSheet(create_groupbox_style(self.palette))
        
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)
        
        mechanics_frame = QFrame()
        mechanics_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['bg_dark']};
                border: 1px solid {colors['border_dark']};
                border-radius: 4px;
                padding: 5px;
            }}
        """)
        mechanics_layout = QVBoxLayout(mechanics_frame)
        
        mana_cost = data.get('mana_cost') or data.get('cost') or data.get('mp', 'Unknown')
        casting_time = data.get('casting_time') or data.get('cast_time', 'Unknown')
        spell_range = data.get('range', 'Unknown')
        target = data.get('target', 'Unknown')
        tags = data.get('tags', [])
        
        mechanics_html = f"""
            <table style='width: 100%; color: {colors['text_bright']};'>
                <tr>
                    <td style='padding: 4px; width: 40%;'><b style='color: {colors['text_primary']};'>💧 Mana Cost:</b></td>
                    <td style='padding: 4px;'>{mana_cost}</td>
                </tr>
                <tr style='background-color: {colors['bg_light']};'>
                    <td style='padding: 4px;'><b style='color: {colors['text_primary']};'>⏱ Casting Time:</b></td>
                    <td style='padding: 4px;'>{casting_time}</td>
                </tr>
                <tr>
                    <td style='padding: 4px;'><b style='color: {colors['text_primary']};'>📏 Range:</b></td>
                    <td style='padding: 4px;'>{spell_range}</td>
                </tr>
                <tr style='background-color: {colors['bg_light']};'>
                    <td style='padding: 4px;'><b style='color: {colors['text_primary']};'>🎯 Target:</b></td>
                    <td style='padding: 4px;'>{target}</td>
                </tr>
            </table>
        """
        
        mechanics_label = QLabel(mechanics_html)
        mechanics_label.setTextFormat(Qt.RichText)
        mechanics_layout.addWidget(mechanics_label)

        if tags:
            tags_str = ', '.join([str(t) for t in tags])
            tags_html = f"<p style='margin-top: 8px; color: {colors['text_secondary']};'><b>Tags:</b> {tags_str}</p>"
            tags_label = QLabel(tags_html)
            tags_label.setTextFormat(Qt.RichText)
            tags_label.setStyleSheet("padding-top: 5px;") 
            mechanics_layout.addWidget(tags_label)

        group_layout.addWidget(mechanics_frame)
        
        layout.addWidget(group)

    def _apply_cursors(self):
        """Applies custom cursors to child widgets of this dialog."""
        main_win = self.window()
        if not main_win:
            # This dialog is parented to the Grimoire panel, so we need to get the main window from there.
            if self.parent() and hasattr(self.parent(), 'window'):
                 main_win = self.parent().window()
            else:
                return

        if hasattr(main_win, 'normal_cursor'):
            # Set normal cursor on read-only text areas
            text_areas = self.findChildren(QLabel) 
            for widget in text_areas:
                widget.setCursor(main_win.normal_cursor)

    def _create_effects_section(self, layout: QVBoxLayout):
        """Create the effects section listing all spell effects."""
        colors = self.palette['colors']
        atoms = getattr(self.spell_obj, 'effect_atoms', []) or []
        
        group = QGroupBox("Effects")
        group.setStyleSheet(create_groupbox_style(self.palette))
        
        group_layout = QVBoxLayout(group)
        
        if atoms:
            for i, atom in enumerate(atoms, 1):
                effect_widget = self._create_effect_widget(i, atom)
                group_layout.addWidget(effect_widget)
        else:
            no_effects_label = QLabel("No structured effects defined.")
            no_effects_label.setStyleSheet(f"color: {colors['text_secondary']}; padding: 5px; font-style: italic;")
            group_layout.addWidget(no_effects_label)
        
        layout.addWidget(group)
    
    def _create_effect_widget(self, index: int, atom: dict) -> QFrame:
        """Create a widget for a single effect atom."""
        colors = self.palette['colors']
        
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['bg_dark']};
                border: 1px solid {colors['border_dark']};
                border-radius: 4px;
                padding: 8px;
            }}
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
        type_label.setStyleSheet(f"color: {colors['text_primary']};")
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
            details_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 9pt;")
            frame_layout.addWidget(details_label)
        
        return frame