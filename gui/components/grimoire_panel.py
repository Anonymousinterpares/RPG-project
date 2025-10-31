#!/usr/bin/env python3
"""
Grimoire panel widget for listing known spells and initiating casting in combat.
Refactored with custom widgets, animated accordion, search/filter, and mana validation.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QGroupBox, QMenu, QMessageBox, QFrame, QPushButton
)

from core.base.state import get_state_manager
from core.interaction.enums import InteractionMode
from core.combat.combat_entity import EntityType
from core.stats.stats_base import DerivedStatType
from core.utils.logging_config import get_logger

# Import custom grimoire components
from gui.components.grimoire.collapsible_section import CollapsibleMagicSystemSection
from gui.components.grimoire.spell_item_widget import SpellItemWidget
from gui.components.grimoire.cast_button import CastButton, CastButtonState

logger = get_logger("GRIMOIRE")


class GrimoirePanelWidget(QScrollArea):
    """Enhanced widget to display player's spells with search, filter, mana validation, and animated UI."""

    # Emitted when user requests to cast a spell with target
    cast_spell_requested = Signal(str, object)  # spell_id, target_id or None
    
    # Emitted when cast completes (for success/fail feedback)
    cast_completed = Signal(bool)  # True if successful, False if failed

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        # State tracking
        self._spells_by_system: Dict[str, List[Any]] = {}
        self._all_spells: List[Any] = []
        self._current_mode: Optional[InteractionMode] = None
        self._selected_spell_id: Optional[str] = None
        self._selected_spell_widget: Optional[SpellItemWidget] = None
        self._current_mana: float = 0.0
        self._max_mana: float = 0.0
        
        # Spell widgets by system
        self._section_widgets: Dict[str, CollapsibleMagicSystemSection] = {}
        self._spell_widgets: Dict[str, SpellItemWidget] = {}  # spell_id -> widget
        
        # Create container
        container = QWidget()
        self.setWidget(container)
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # Build UI sections
        self._create_quick_stats_section()
        self._create_search_filter_section()
        self._create_spells_section()
        self._create_action_bar()
        
        # Spacer at bottom
        self.main_layout.addStretch()
    
    def _create_quick_stats_section(self):
        """Create the quick stats section showing mana and spell count."""
        self.stats_group = QGroupBox("Mana")
        self.stats_group.setStyleSheet(self._get_groupbox_style())
        
        stats_layout = QHBoxLayout(self.stats_group)
        
        # Mana display
        self.mana_label = QLabel("0 / 0")
        self.mana_label.setStyleSheet("color: #1178BB; font-size: 14pt; font-weight: bold;")
        stats_layout.addWidget(QLabel("💧"), 0)
        stats_layout.addWidget(self.mana_label, 1)
        
        # Spell count
        self.spell_count_label = QLabel("Spells: 0")
        self.spell_count_label.setStyleSheet("color: #BBBBBB; font-size: 10pt;")
        stats_layout.addWidget(self.spell_count_label, 0)
        
        self.main_layout.addWidget(self.stats_group)
    
    def _create_search_filter_section(self):
        """Create the search and filter controls."""
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #2D2D30;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        
        filter_layout = QVBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 6, 8, 6)
        filter_layout.setSpacing(6)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Search:")
        search_label.setStyleSheet("color: #BBBBBB;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by spell name...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        self.search_input.textChanged.connect(self._on_filter_changed)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)
        
        # Filter dropdowns
        filters_layout = QHBoxLayout()
        
        # Role filter
        role_label = QLabel("Role:")
        role_label.setStyleSheet("color: #BBBBBB;")
        self.role_filter = QComboBox()
        self.role_filter.addItems(["All", "Offensive", "Defensive", "Utility"])
        self.role_filter.setStyleSheet("""
            QComboBox {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2D30;
                color: #E0E0E0;
                selection-background-color: #0E639C;
            }
        """)
        self.role_filter.currentTextChanged.connect(self._on_filter_changed)
        
        # System filter
        system_label = QLabel("System:")
        system_label.setStyleSheet("color: #BBBBBB;")
        self.system_filter = QComboBox()
        self.system_filter.addItem("All")
        self.system_filter.setStyleSheet(self.role_filter.styleSheet())
        self.system_filter.currentTextChanged.connect(self._on_filter_changed)
        
        filters_layout.addWidget(role_label)
        filters_layout.addWidget(self.role_filter, 1)
        filters_layout.addWidget(system_label)
        filters_layout.addWidget(self.system_filter, 1)
        
        filter_layout.addLayout(search_layout)
        filter_layout.addLayout(filters_layout)
        
        self.main_layout.addWidget(filter_frame)
    
    def _create_spells_section(self):
        """Create the collapsible spells section."""
        self.spells_group = QGroupBox("Known Spells")
        self.spells_group.setStyleSheet(self._get_groupbox_style())
        
        self.spells_layout = QVBoxLayout(self.spells_group)
        self.spells_layout.setContentsMargins(8, 10, 8, 8)
        self.spells_layout.setSpacing(5)
        
        # Empty state message
        self.empty_state_label = QLabel(
            "✨ No spells learned yet.\n\n"
            "Discover spells by reading grimoires,\n"
            "training with NPCs, or completing quests."
        )
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setStyleSheet("""
            color: #888888;
            font-style: italic;
            font-size: 11pt;
            padding: 40px;
        """)
        self.empty_state_label.setVisible(False)
        self.spells_layout.addWidget(self.empty_state_label)
        
        self.main_layout.addWidget(self.spells_group)
    
    def _create_action_bar(self):
        """Create the action bar with Cast and Details buttons."""
        action_frame = QFrame()
        action_frame.setStyleSheet("""
            QFrame {
                background-color: #2D2D30;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(8, 6, 8, 6)
        
        # Cast button (enhanced)
        self.cast_btn = CastButton()
        self.cast_btn.cast_requested.connect(self._on_cast_requested)
        
        # Details button
        self.details_btn = QPushButton("View Details")
        self.details_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: 2px solid #666666;
                border-radius: 6px;
                font-size: 10pt;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
            QPushButton:disabled {
                background-color: #3A3A3A;
                color: #777777;
            }
        """)
        self.details_btn.setEnabled(False)
        self.details_btn.clicked.connect(self._on_details_clicked)
        
        action_layout.addWidget(self.cast_btn, 2)
        action_layout.addWidget(self.details_btn, 1)
        
        self.main_layout.addWidget(action_frame)
    
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
    
    def refresh(self, spells_by_system: Dict[str, List[Any]], mode: Optional[InteractionMode], current_mana: float = 0.0, max_mana: float = 0.0):
        """Rebuild the grimoire UI with spells, update mana, and set mode."""
        self._spells_by_system = spells_by_system or {}
        self._current_mode = mode
        self._current_mana = current_mana
        self._max_mana = max_mana
        
        # Update stats display
        self.mana_label.setText(f"{int(current_mana)} / {int(max_mana)}")
        
        # Count total spells
        total_spells = sum(len(spells) for spells in self._spells_by_system.values())
        self.spell_count_label.setText(f"Spells: {total_spells}")
        
        # Update system filter dropdown
        current_system = self.system_filter.currentText()
        self.system_filter.clear()
        self.system_filter.addItem("All")
        for system_id in sorted(self._spells_by_system.keys()):
            self.system_filter.addItem(system_id)
        
        # Restore selection if possible
        idx = self.system_filter.findText(current_system)
        if idx >= 0:
            self.system_filter.setCurrentIndex(idx)
        
        # Flatten spell list for filtering
        self._all_spells = []
        for spells in self._spells_by_system.values():
            self._all_spells.extend(spells)
        
        # Rebuild UI
        self._rebuild_spell_widgets()
        
        # Update button states
        self._update_button_states()
    
    def _rebuild_spell_widgets(self):
        """Rebuild all spell widgets based on current filters."""
        # Clear existing sections
        for section in self._section_widgets.values():
            section.deleteLater()
        self._section_widgets.clear()
        self._spell_widgets.clear()
        
        # Apply filters
        filtered_by_system = self._apply_filters()
        
        # Show/hide empty state
        total_filtered = sum(len(spells) for spells in filtered_by_system.values())
        self.empty_state_label.setVisible(total_filtered == 0)
        
        # Create collapsible sections for each system
        for system_id in sorted(filtered_by_system.keys()):
            spells = filtered_by_system[system_id]
            if not spells:
                continue
            
            # Get readable system name (you might want to load from config)
            system_name = system_id.replace('_', ' ').title()
            
            section = CollapsibleMagicSystemSection(
                system_id=system_id,
                system_name=system_name,
                spell_count=len(spells)
            )
            
            # Add spell widgets to section
            for spell in sorted(spells, key=lambda s: getattr(s, 'name', getattr(s, 'id', ''))):
                spell_id = spell.id
                spell_name = getattr(spell, 'name', spell_id)
                
                spell_widget = SpellItemWidget(
                    spell_id=spell_id,
                    spell_name=spell_name,
                    spell_obj=spell
                )
                
                # Connect signals
                spell_widget.clicked.connect(self._on_spell_selected)
                spell_widget.double_clicked.connect(self._on_spell_double_clicked)
                
                # Add rich tooltip
                tooltip_html = self._build_rich_tooltip(spell)
                spell_widget.setToolTip(tooltip_html)
                
                section.add_spell_widget(spell_widget)
                self._spell_widgets[spell_id] = spell_widget
            
            self.spells_layout.addWidget(section)
            self._section_widgets[system_id] = section
    
    def _apply_filters(self) -> Dict[str, List[Any]]:
        """Apply search and filter criteria to spells."""
        search_text = self.search_input.text().lower().strip()
        role_filter = self.role_filter.currentText()
        system_filter = self.system_filter.currentText()
        
        filtered = {}
        
        for system_id, spells in self._spells_by_system.items():
            # System filter
            if system_filter != "All" and system_id != system_filter:
                continue
            
            filtered_spells = []
            for spell in spells:
                # Search filter
                spell_name = getattr(spell, 'name', getattr(spell, 'id', '')).lower()
                if search_text and search_text not in spell_name:
                    continue
                
                # Role filter
                spell_role = getattr(spell, 'combat_role', 'offensive').capitalize()
                if role_filter != "All" and spell_role != role_filter:
                    continue
                
                filtered_spells.append(spell)
            
            if filtered_spells:
                filtered[system_id] = filtered_spells
        
        return filtered
    
    def _build_rich_tooltip(self, spell: Any) -> str:
        """Build rich HTML tooltip for a spell."""
        try:
            name = getattr(spell, 'name', getattr(spell, 'id', 'Spell'))
            role = getattr(spell, 'combat_role', 'offensive').capitalize()
            data = getattr(spell, 'data', {}) or {}
            
            mana_cost = data.get('mana_cost') or data.get('cost') or data.get('mp', '?')
            cast_time = data.get('casting_time') or data.get('cast_time', '?')
            spell_range = data.get('range', '?')
            
            # Role color
            role_colors = {
                'Offensive': '#D94A38',
                'Defensive': '#0E639C',
                'Utility': '#8B7FBF'
            }
            role_color = role_colors.get(role, '#888888')
            
            # Build effect summary
            atoms = getattr(spell, 'effect_atoms', []) or []
            effect_summary = "No effects"
            if atoms:
                effect_types = {}
                for atom in atoms:
                    etype = atom.get('type', 'effect')
                    effect_types[etype] = effect_types.get(etype, 0) + 1
                effect_summary = ", ".join(f"{k.capitalize()} x{effect_types[k]}" for k in effect_types)
            
            tooltip_html = f"""
            <div style='background-color: #2D2D30; padding: 8px; border: 1px solid #555;'>
                <p style='margin: 0; color: #E0E0E0; font-size: 11pt;'><b>{name}</b></p>
                <p style='margin: 2px 0; color: {role_color}; font-size: 9pt;'><b>⚔ {role}</b></p>
                <hr style='border: 1px solid #555; margin: 4px 0;'>
                <table style='color: #BBBBBB; font-size: 9pt;'>
                    <tr><td>💧 Mana:</td><td><b>{mana_cost}</b></td></tr>
                    <tr><td>⏱ Cast Time:</td><td><b>{cast_time}</b></td></tr>
                    <tr><td>📏 Range:</td><td><b>{spell_range}</b></td></tr>
                </table>
                <hr style='border: 1px solid #555; margin: 4px 0;'>
                <p style='margin: 2px 0; color: #AAAAAA; font-size: 9pt;'>{effect_summary}</p>
            </div>
            """
            return tooltip_html
        except Exception as e:
            logger.warning(f"Failed to build tooltip: {e}")
            return "Spell"
    
    def _on_filter_changed(self):
        """Handle filter changes by rebuilding the spell list."""
        self._rebuild_spell_widgets()
    
    def _on_spell_selected(self, spell_id: str):
        """Handle spell selection."""
        # Deselect previous
        if self._selected_spell_widget:
            self._selected_spell_widget.set_selected(False)
        
        # Select new
        self._selected_spell_id = spell_id
        self._selected_spell_widget = self._spell_widgets.get(spell_id)
        if self._selected_spell_widget:
            self._selected_spell_widget.set_selected(True)
        
        self._update_button_states()
    
    def _on_spell_double_clicked(self, spell_id: str):
        """Handle spell double-click to show details."""
        self._open_details_dialog(spell_id)
    
    def _update_button_states(self):
        """Update Cast and Details button states based on selection and mana."""
        has_selection = bool(self._selected_spell_id)
        
        # Details button
        self.details_btn.setEnabled(has_selection)
        
        # Cast button logic
        if not has_selection:
            self.cast_btn.set_state(CastButtonState.DISABLED)
        elif self._current_mode != InteractionMode.COMBAT:
            self.cast_btn.set_state(CastButtonState.DISABLED)
        else:
            # Check mana
            if self._selected_spell_id:
                try:
                    from core.magic.spell_catalog import get_spell_catalog
                    cat = get_spell_catalog()
                    spell = cat.get_spell_by_id(self._selected_spell_id)
                    if spell:
                        spell_widget = self._spell_widgets.get(self._selected_spell_id)
                        if spell_widget:
                            mana_cost = spell_widget.mana_cost
                            if mana_cost > self._current_mana:
                                self.cast_btn.set_state(CastButtonState.INSUFFICIENT_MANA)
                            else:
                                self.cast_btn.set_state(CastButtonState.ENABLED)
                        else:
                            self.cast_btn.set_state(CastButtonState.ENABLED)
                    else:
                        self.cast_btn.set_state(CastButtonState.DISABLED)
                except Exception:
                    self.cast_btn.set_state(CastButtonState.ENABLED)
            else:
                self.cast_btn.set_state(CastButtonState.ENABLED)
    
    def _on_details_clicked(self):
        """Handle Details button click."""
        if self._selected_spell_id:
            self._open_details_dialog(self._selected_spell_id)
    
    def _open_details_dialog(self, spell_id: str):
        """Open the spell details dialog."""
        try:
            from core.magic.spell_catalog import get_spell_catalog
            from gui.dialogs.spell_details_dialog import SpellDetailsDialog
            
            cat = get_spell_catalog()
            spell = cat.get_spell_by_id(spell_id)
            if not spell:
                QMessageBox.information(self, "Spell", f"Spell '{spell_id}' not found.")
                return
            
            # Close previous dialog if exists
            if hasattr(self, '_details_dialog') and self._details_dialog:
                try:
                    self._details_dialog.close()
                except Exception:
                    pass
            
            self._details_dialog = SpellDetailsDialog(spell, self)
            self._details_dialog.show()
        except Exception as e:
            logger.exception(f"Failed to open spell details: {e}")
    
    def _on_cast_requested(self):
        """Handle cast button click - initiate spell casting with target selection."""
        sid = self._selected_spell_id
        if not sid:
            return
        if self._current_mode != InteractionMode.COMBAT:
            QMessageBox.information(self, "Casting", "Casting is disabled outside combat.")
            return
        # Determine target candidates based on role
        try:
            from core.magic.spell_catalog import get_spell_catalog
            cat = get_spell_catalog()
            sp = cat.get_spell_by_id(sid)
        except Exception:
            sp = None
        role = getattr(sp, 'combat_role', 'offensive') if sp else 'offensive'
        # Build target list
        state = get_state_manager().current_state if get_state_manager() else None
        cm = getattr(state, 'combat_manager', None) if state else None
        if not cm or not getattr(state, 'current_mode', None) == InteractionMode.COMBAT:
            QMessageBox.information(self, "Casting", "No active combat.")
            return
        # Collect entities
        alive_enemies = []
        allies_or_self = []
        try:
            for ent in (cm.entities or {}).values():
                if not ent.is_alive() or not getattr(ent, 'is_active_in_combat', True):
                    continue
                if ent.entity_type == EntityType.ENEMY:
                    alive_enemies.append(ent)
                else:
                    allies_or_self.append(ent)
        except Exception:
            pass
        # Auto/select menu
        if role == 'offensive':
            if len(alive_enemies) == 0:
                QMessageBox.information(self, "Casting", "No valid enemy targets.")
                return
            if len(alive_enemies) == 1:
                self.cast_spell_requested.emit(sid, alive_enemies[0].id)
                return
            menu = QMenu(self)
            actions = []
            for e in alive_enemies:
                act = menu.addAction(e.combat_name)
                act.setData(e.id)
                actions.append(act)
            sel = menu.exec(self.cast_btn.mapToGlobal(self.cast_btn.rect().bottomLeft()))
            if sel and sel.data():
                self.cast_spell_requested.emit(sid, sel.data())
        elif role == 'defensive':
            if len(allies_or_self) == 0:
                QMessageBox.information(self, "Casting", "No valid allies.")
                return
            # Default to self if single-party
            if len(allies_or_self) == 1:
                self.cast_spell_requested.emit(sid, allies_or_self[0].id)
                return
            menu = QMenu(self)
            actions = []
            for e in allies_or_self:
                act = menu.addAction(e.combat_name)
                act.setData(e.id)
                actions.append(act)
            sel = menu.exec(self.cast_btn.mapToGlobal(self.cast_btn.rect().bottomLeft()))
            if sel and sel.data():
                self.cast_spell_requested.emit(sid, sel.data())
        else:
            # utility: disabled in combat per design
            QMessageBox.information(self, "Casting", "This spell is not available during combat.")
