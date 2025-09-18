"""
Headless testing utilities package.

Provides utilities for running the game in a headless (no-GUI) mode for
manual and automated testing without touching core logic.
"""

from .headless_ui_listener import HeadlessUIListener
from .headless_env import bootstrap_headless, run_in_qt_thread
from .scenario_runner import run_scenario

__all__ = [
    "HeadlessUIListener",
    "bootstrap_headless",
    "run_in_qt_thread",
    "run_scenario",
]

