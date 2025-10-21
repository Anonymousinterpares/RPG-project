#!/usr/bin/env python3
"""
UI SFX wiring utilities.
Provides a small, centralized way to attach UI interaction sounds to widgets
without duplicating signal connections everywhere.
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QWidget, QAbstractButton, QComboBox, QTabBar, QTabWidget


def _play_ui(kind: str) -> None:
    try:
        from core.base.engine import get_game_engine
        eng = get_game_engine()
        fn = getattr(eng, 'sfx_play', None)
        if callable(fn):
            fn('ui', kind)
    except Exception:
        pass


class _UISFXEventFilter(QObject):
    def __init__(self, click_kind: Optional[str], tab_kind: Optional[str], dropdown_kind: Optional[str]) -> None:
        super().__init__()
        self.click_kind = click_kind
        self.tab_kind = tab_kind
        self.dropdown_kind = dropdown_kind

    def eventFilter(self, obj, event):  # noqa: N802 - Qt API
        try:
            if event.type() == QEvent.MouseButtonPress:
                # Tab bars
                if self.tab_kind and isinstance(obj, (QTabBar,)):
                    _play_ui(self.tab_kind)
                    return False
                # Dropdown click
                if self.dropdown_kind and isinstance(obj, QComboBox):
                    _play_ui(self.dropdown_kind)
                    return False
                # Generic button clicks
                if self.click_kind and isinstance(obj, QAbstractButton):
                    _play_ui(self.click_kind)
                    return False
        except Exception:
            pass
        return super().eventFilter(obj, event)


def map_container(root: QWidget, click_kind: Optional[str] = None, tab_kind: Optional[str] = None, dropdown_kind: Optional[str] = None) -> None:
    """Attach UI SFX to a container and its children via a single event filter.
    - click_kind: plays on QAbstractButton presses
    - tab_kind: plays on QTabBar presses
    - dropdown_kind: plays on QComboBox press/selection
    """
    try:
        if not isinstance(root, QWidget):
            return
        # Avoid duplicate installation
        if getattr(root, '_ui_sfx_filter_attached', False):
            return
        f = _UISFXEventFilter(click_kind, tab_kind, dropdown_kind)
        root._ui_sfx_filter_attached = True  # type: ignore[attr-defined]
        root._ui_sfx_filter_ref = f          # keep a strong ref to avoid GC  # type: ignore[attr-defined]
        # Install on root and all children
        root.installEventFilter(f)
        for w in root.findChildren(QWidget):
            try:
                w.installEventFilter(f)
            except Exception:
                pass
        # Also connect combo selection to dropdown sound
        if dropdown_kind:
            for cb in root.findChildren(QComboBox):
                try:
                    cb.activated.connect(lambda *_: _play_ui(dropdown_kind))
                except Exception:
                    pass
        # Connect tab change as a fallback
        if tab_kind:
            for tw in root.findChildren(QTabWidget):
                try:
                    tw.currentChanged.connect(lambda *_: _play_ui(tab_kind))
                except Exception:
                    pass
    except Exception:
        pass
