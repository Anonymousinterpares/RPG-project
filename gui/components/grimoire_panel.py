#!/usr/bin/env python3
"""
Grimoire panel widget for listing known spells and initiating casting in combat.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QHBoxLayout, QPushButton, QMenu, QMessageBox
)

from core.base.state import get_state_manager
from core.interaction.enums import InteractionMode
from core.combat.combat_entity import EntityType
from core.utils.logging_config import get_logger

logger = get_logger("GRIMOIRE")


class GrimoirePanelWidget(QScrollArea):
    """Widget to display the player's known spells grouped by Magic System and support casting in combat."""

    # Emitted when user selects a spell and target to cast deterministically in combat
    cast_spell_requested = Signal(str, object)  # spell_id, target_id or None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._spells_by_system: Dict[str, List[Any]] = {}

        container = QWidget()
        self.setWidget(container)
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Tree: Systems -> Spells
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.main_layout.addWidget(self.tree)

        # Action bar
        btns = QHBoxLayout()
        self.cast_btn = QPushButton("Cast")
        self.details_btn = QPushButton("Details")
        self.cast_btn.setEnabled(False)
        self.details_btn.setEnabled(False)
        self.cast_btn.clicked.connect(self._on_cast_clicked)
        self.details_btn.clicked.connect(self._on_details_clicked)
        btns.addWidget(self.cast_btn)
        btns.addWidget(self.details_btn)
        btns.addStretch()
        self.main_layout.addLayout(btns)

        # Track mode for enabling cast
        self._current_mode: Optional[InteractionMode] = None

    def refresh(self, spells_by_system: Dict[str, List[Any]], mode: Optional[InteractionMode]):
        """Rebuild the tree from provided spells_by_system and set cast enable based on mode."""
        self._spells_by_system = spells_by_system or {}
        self._current_mode = mode
        self.tree.clear()

        for system_id, spells in sorted(self._spells_by_system.items(), key=lambda t: t[0]):
            sys_node = QTreeWidgetItem([system_id])
            sys_node.setData(0, Qt.UserRole, ("system", system_id))
            self.tree.addTopLevelItem(sys_node)
            for sp in sorted(spells, key=lambda s: getattr(s, 'name', getattr(s, 'id', '')) or ''):
                label = f"{getattr(sp, 'name', sp.id)}"
                item = QTreeWidgetItem([label])
                item.setData(0, Qt.UserRole, ("spell", sp.id))
                # Tooltip: mana cost, cast time, brief effect summary when available
                tip = self._build_spell_tooltip(sp)
                item.setToolTip(0, tip)
                sys_node.addChild(item)
            sys_node.setExpanded(True)

        self._update_buttons_enabled()

    def _build_spell_tooltip(self, sp: Any) -> str:
        try:
            data = getattr(sp, 'data', {}) or {}
            # Try common keys
            mana_cost = data.get('mana_cost') or data.get('cost') or data.get('mp')
            cast_time = data.get('casting_time') or data.get('cast_time')
            parts = []
            if mana_cost is not None:
                parts.append(f"Mana: {mana_cost}")
            if cast_time is not None:
                parts.append(f"Cast Time: {cast_time}")
            # effect summary
            atoms = getattr(sp, 'effect_atoms', []) or []
            if atoms:
                kinds = {}
                for a in atoms:
                    k = str(a.get('type', 'effect'))
                    kinds[k] = kinds.get(k, 0) + 1
                summary = ', '.join(f"{k} x{kinds[k]}" for k in kinds)
                if summary:
                    parts.append(summary)
            role = getattr(sp, 'combat_role', 'offensive')
            parts.append(f"Role: {role}")
            return '\n'.join(parts) if parts else "Spell"
        except Exception:
            return "Spell"

    def _current_selected_spell_id(self) -> Optional[str]:
        sel = self.tree.selectedItems()
        if not sel:
            return None
        tag = sel[0].data(0, Qt.UserRole)
        if isinstance(tag, tuple) and tag[0] == "spell":
            return str(tag[1])
        return None

    def _on_selection_changed(self):
        self._update_buttons_enabled()

    def _update_buttons_enabled(self):
        sid = self._current_selected_spell_id()
        self.details_btn.setEnabled(bool(sid))
        cast_enabled = bool(sid and self._current_mode == InteractionMode.COMBAT)
        self.cast_btn.setEnabled(cast_enabled)

    def _on_item_double_clicked(self, item: QTreeWidgetItem):
        tag = item.data(0, Qt.UserRole)
        if isinstance(tag, tuple) and tag[0] == "spell":
            self._open_details_dialog(str(tag[1]))

    def _on_details_clicked(self):
        sid = self._current_selected_spell_id()
        if sid:
            self._open_details_dialog(sid)

    def _open_details_dialog(self, spell_id: str):
        # Import lazily to avoid circulars
        try:
            from core.magic.spell_catalog import get_spell_catalog
            from gui.dialogs.spell_details_dialog import SpellDetailsDialog
            cat = get_spell_catalog()
            sp = cat.get_spell_by_id(spell_id)
            if not sp:
                QMessageBox.information(self, "Spell", f"Spell '{spell_id}' not found in catalog.")
                return
            try:
                # Close any previous instance stored on self
                if hasattr(self, '_details_dialog') and getattr(self, '_details_dialog') is not None:
                    try:
                        self._details_dialog.close()
                    except Exception:
                        pass
            except Exception:
                pass
            dlg = SpellDetailsDialog(sp, self)
            self._details_dialog = dlg
            dlg.show()
        except Exception as e:
            logger.warning(f"Failed to open spell details: {e}")

    def _on_cast_clicked(self):
        sid = self._current_selected_spell_id()
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
