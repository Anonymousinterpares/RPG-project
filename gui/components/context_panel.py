#!/usr/bin/env python3
"""
Developer Context Panel for viewing and editing GameContext (desktop GUI).
Gated by dev flag at tab insertion time.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QHBoxLayout,
    QPushButton, QCheckBox, QLabel
)
from PySide6.QtCore import Qt

from core.base.engine import get_game_engine
from core.context.game_context import load_context_enums


class ContextPanelWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._engine = get_game_engine()
        self._enums: Dict[str, Any] = load_context_enums()
        self._build_ui()
        # Dirty-state to avoid overwriting user edits; cleared on Apply/Refresh
        self._dirty: bool = False
        self._pending_engine_ctx: Optional[dict] = None
        # Refresh when engine pushes updates
        try:
            if hasattr(self._engine, 'context_updated'):
                self._engine.context_updated.connect(self._on_engine_context_updated)
        except Exception:
            pass
        # Style to match dark panel (legible inputs)
        self.setStyleSheet("""
            QLabel { color: #E0E0E0; }
            QLineEdit, QComboBox { background-color: #2E2E2E; color: #E0E0E0; border: 1px solid #555555; padding: 4px; }
            QCheckBox { color: #E0E0E0; }
        """)

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self._loc_name = QLineEdit()
        self._loc_major = QComboBox()
        self._loc_venue = QComboBox()
        self._weather = QComboBox()
        self._tod = QComboBox()
        self._biome = QComboBox()
        self._interior = QCheckBox("Interior")
        self._underground = QCheckBox("Underground")
        self._crowd = QComboBox()
        self._danger = QComboBox()

        def fill(cb: QComboBox, values: Any):
            try:
                cb.clear()
                for v in (values or []):
                    cb.addItem(str(v))
            except Exception:
                pass

        fill(self._loc_major, self._enums.get('location', {}).get('major'))
        fill(self._loc_venue, self._enums.get('location', {}).get('venue'))
        fill(self._weather, self._enums.get('weather', {}).get('type'))
        fill(self._tod, self._enums.get('time_of_day'))
        fill(self._biome, self._enums.get('biome'))
        fill(self._crowd, self._enums.get('crowd_level'))
        fill(self._danger, self._enums.get('danger_level'))

        form.addRow("Location Name", self._loc_name)
        form.addRow("Major", self._loc_major)
        form.addRow("Venue", self._loc_venue)
        form.addRow("Weather", self._weather)
        form.addRow("Time of Day", self._tod)
        form.addRow("Biome", self._biome)
        form.addRow(self._interior)
        form.addRow(self._underground)
        form.addRow("Crowd", self._crowd)
        form.addRow("Danger", self._danger)

        lay.addLayout(form)

        btn_row = QHBoxLayout()
        self._refresh_btn = QPushButton("Refresh")
        self._apply_btn = QPushButton("Apply")
        self._status = QLabel("")
        self._status.setWordWrap(True)
        btn_row.addWidget(self._refresh_btn)
        btn_row.addWidget(self._apply_btn)
        lay.addLayout(btn_row)
        # JSON captured values viewer
        from PySide6.QtWidgets import QPlainTextEdit
        self._json_view = QPlainTextEdit()
        self._json_view.setReadOnly(True)
        self._json_view.setStyleSheet("QPlainTextEdit { background-color: #1E1E1E; color: #C8C8C8; font-family: Consolas, 'Courier New', monospace; font-size: 12px; border: 1px solid #555; }")
        self._json_view.setPlaceholderText("Captured GameContext (read-only)")
        lay.addWidget(self._json_view, stretch=1)

        # Now Playing list (music + up to 4 SFX)
        from PySide6.QtWidgets import QListWidget
        self._now_playing = QListWidget()
        self._now_playing.setStyleSheet("QListWidget { background-color: #1E1E1E; color: #E0E0E0; border: 1px solid #555; }")
        self._now_playing.setMaximumHeight(110)
        lay.addWidget(QLabel("Now Playing (music + SFX):"))
        lay.addWidget(self._now_playing)

        lay.addWidget(self._status)
        lay.addStretch(1)

        self._refresh_btn.clicked.connect(self.refresh_from_engine)
        self._apply_btn.clicked.connect(self.apply_to_engine)

        # Mark form dirty on any change
        try:
            self._loc_name.textEdited.connect(self._mark_dirty)
            for cb in (self._loc_major, self._loc_venue, self._weather, self._tod, self._biome, self._crowd, self._danger):
                cb.currentIndexChanged.connect(self._mark_dirty)
            self._interior.stateChanged.connect(self._mark_dirty)
            self._underground.stateChanged.connect(self._mark_dirty)
        except Exception:
            pass

        # Subscribe to playback updates
        try:
            if hasattr(self._engine, 'playback_updated'):
                self._engine.playback_updated.connect(self._on_playback_updated)
        except Exception:
            pass

        # Initial load
        self.refresh_from_engine()
        try:
            self._on_playback_updated(self._engine.get_playback_snapshot())
        except Exception:
            pass

    def _on_engine_context_updated(self, payload: dict) -> None:
        # If the user is editing, do not clobber inputs; stash for later
        if self._dirty:
            self._pending_engine_ctx = payload
            try:
                self._status.setText("Engine updated context. Finish editing then Refresh/Apply.")
            except Exception:
                pass
            return
        self.refresh_from_engine()


    def refresh_from_engine(self) -> None:
        try:
            import json as _json
            ctx = self._engine.get_game_context() if hasattr(self._engine, 'get_game_context') else {}
            loc = ctx.get('location', {}) if isinstance(ctx, dict) else {}
            self._loc_name.setText(str(loc.get('name', '') or ''))
            self._select_combo(self._loc_major, loc.get('major'))
            self._select_combo(self._loc_venue, loc.get('venue'))
            w = ctx.get('weather', {}) if isinstance(ctx, dict) else {}
            self._select_combo(self._weather, w.get('type'))
            self._select_combo(self._tod, ctx.get('time_of_day'))
            self._select_combo(self._biome, ctx.get('biome'))
            self._interior.setChecked(bool(ctx.get('interior', False)))
            self._underground.setChecked(bool(ctx.get('underground', False)))
            self._select_combo(self._crowd, ctx.get('crowd_level'))
            self._select_combo(self._danger, ctx.get('danger_level'))
            # Update captured JSON view
            try:
                self._json_view.setPlainText(_json.dumps(ctx, indent=2, ensure_ascii=False))
            except Exception:
                self._json_view.setPlainText(str(ctx))
            self._status.setText("Loaded current context.")
        except Exception as e:
            self._status.setText(f"Failed to refresh: {e}")

    def _select_combo(self, cb: QComboBox, value: Optional[str]) -> None:
        try:
            if value:
                idx = cb.findText(str(value))
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            else:
                # Show no selection if no value provided
                cb.setCurrentIndex(-1)
        except Exception:
            pass

    def _mark_dirty(self, *args, **kwargs) -> None:
        self._dirty = True

    def _on_playback_updated(self, items: list) -> None:
        try:
            self._now_playing.clear()
            for entry in (items or [])[:5]:
                self._now_playing.addItem(str(entry))
        except Exception:
            pass

    def apply_to_engine(self) -> None:
        payload = {
            'location': {
                'name': self._loc_name.text().strip(),
                'major': self._current_text(self._loc_major),
                'venue': self._current_text(self._loc_venue),
            },
            'weather': { 'type': self._current_text(self._weather) },
            'time_of_day': self._current_text(self._tod),
            'biome': self._current_text(self._biome),
            'interior': self._interior.isChecked(),
            'underground': self._underground.isChecked(),
            'crowd_level': self._current_text(self._crowd),
            'danger_level': self._current_text(self._danger),
        }
        try:
            if hasattr(self._engine, 'set_game_context'):
                self._engine.set_game_context(payload, source="gui_dev_panel")
                self._status.setText("Applied context to engine.")
                # Clear dirty state and pending engine push
                self._dirty = False
                self._pending_engine_ctx = None
        except Exception as e:
            self._status.setText(f"Failed to apply: {e}")

    def _current_text(self, cb: QComboBox) -> Optional[str]:
        try:
            return cb.currentText() or None
        except Exception:
            return None