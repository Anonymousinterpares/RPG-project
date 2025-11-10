#!/usr/bin/env python3
"""
Combat display component for the RPG game.

This module provides a GUI component for displaying combat status and log,
with customizable appearance settings.
"""

import json
import os
from typing import Dict, Iterator, List, Any, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QFrame, QPushButton, QGridLayout
)
from PySide6.QtCore import QSettings, Signal, Slot, QTimer, Qt
from PySide6.QtGui import QColor, QTextCharFormat, QFont, QTextCursor
from gui.components.allies_panel import AlliesPanel
from gui.components.enemies_panel import EnemiesPanel
from core.base.engine import get_game_engine
from core.interaction.enums import InteractionMode
from gui.styles.stylesheet_factory import create_combat_display_style
from gui.styles.theme_manager import get_theme_manager

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Configuration Constants - Adjusted paths based on project structure
CONFIG_DIR = os.path.join(project_root, "config")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "combat_display_settings.json")
IMAGE_DIR = os.path.join(project_root, "images", "gui", "combat_display") # Path to background images

# Ensure directories exist
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True) # Create image dir if it doesn't exist

# Import after defining project_root if necessary for other modules
from core.utils.logging_config import get_logger
from core.combat.enums import CombatState
from core.combat.combat_entity import EntityType
from core.stats.stats_base import DerivedStatType
from core.base.state import GameState
from core.stats.stats_manager import get_stats_manager

# Get the module logger
logger = get_logger("GUI")

class CombatDisplay(QWidget):
    """Widget for displaying combat status and log."""

    visualDisplayComplete = Signal()

    def __init__(self, parent=None):
        """Initialize the combat display widget."""
        super().__init__(parent)

        self.setObjectName("combatDisplayWidget")

        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self.apply_theme)
        # --- END THEME MANAGEMENT ---

        self.combat_active = False 
        self.stats_manager = get_stats_manager() 
        
        self.command_input_widget: Optional[QWidget] = None

        # This is the root layout of the entire CombatDisplay widget
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0); root_layout.setSpacing(0)
        
        # This frame will hold the main stone background image
        self.background_frame = QFrame()
        self.background_frame.setObjectName("combatBackgroundFrame")
        root_layout.addWidget(self.background_frame)

        # This layout will contain the border frame
        background_layout = QVBoxLayout(self.background_frame)
        background_layout.setContentsMargins(0,0,0,0)

        # This new inner frame will hold the border and the actual content grid
        self.border_frame = QFrame()
        self.border_frame.setObjectName("combatBorderFrame")
        background_layout.addWidget(self.border_frame)

        # The grid layout now goes inside the border_frame
        grid_layout = QGridLayout(self.border_frame)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setSpacing(10)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0); status_layout.setSpacing(10)

        self.status_label = QLabel("Status: Narrative") 
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)

        self.round_label = QLabel("Round: 0")
        self.round_label.setVisible(False) 
        self.round_label.setObjectName("roundLabel")
        status_layout.addWidget(self.round_label)

        status_layout.addStretch()

        self.dev_controls_container = QWidget()
        dev_controls_layout = QHBoxLayout(self.dev_controls_container)
        dev_controls_layout.setContentsMargins(0, 0, 0, 0); dev_controls_layout.setSpacing(6)
        self.dev_step_mode_btn = QPushButton("Step Mode")
        self.dev_step_mode_btn.setCheckable(True)
        self.dev_next_step_btn = QPushButton("Next Step")
        self.dev_next_step_btn.setEnabled(False)
        dev_controls_layout.addWidget(self.dev_step_mode_btn)
        dev_controls_layout.addWidget(self.dev_next_step_btn)
        status_layout.addWidget(self.dev_controls_container)

        sections_layout = QHBoxLayout()
        sections_layout.setContentsMargins(0, 0, 0, 0); sections_layout.setSpacing(20)

        # --- Allies Panel Structure (with nested border frame) ---
        self.allies_panel_container = QWidget()
        allies_panel_layout = QVBoxLayout(self.allies_panel_container)
        allies_panel_layout.setContentsMargins(0,0,0,0); allies_panel_layout.setSpacing(0)
        allies_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.allies_header_label = QLabel("Bard")
        self.allies_header_label.setObjectName("panelHeaderLabel")
        self.allies_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.allies_bg_frame = QFrame()
        self.allies_bg_frame.setObjectName("alliesBGFrame")
        allies_bg_layout = QVBoxLayout(self.allies_bg_frame) 
        allies_bg_layout.setContentsMargins(0,0,0,0)
        self.allies_border_frame = QFrame() 
        self.allies_border_frame.setObjectName("panelBorderFrame")
        allies_bg_layout.addWidget(self.allies_border_frame)
        allies_panel_layout.addWidget(self.allies_header_label)
        allies_panel_layout.addWidget(self.allies_bg_frame, 1)
        allies_content_layout = QVBoxLayout(self.allies_border_frame) 
        self.allies_panel = AlliesPanel()
        allies_content_layout.addWidget(self.allies_panel)

        # --- Enemies Panel Structure (with nested border frame) ---
        self.enemies_panel_container = QWidget()
        enemies_panel_layout = QVBoxLayout(self.enemies_panel_container)
        enemies_panel_layout.setContentsMargins(0,0,0,0); enemies_panel_layout.setSpacing(0)
        enemies_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.enemies_header_label = QLabel("Enemy")
        self.enemies_header_label.setObjectName("panelHeaderLabel")
        self.enemies_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.enemies_bg_frame = QFrame()
        self.enemies_bg_frame.setObjectName("enemiesBGFrame")
        enemies_bg_layout = QVBoxLayout(self.enemies_bg_frame)
        enemies_bg_layout.setContentsMargins(0,0,0,0)
        self.enemies_border_frame = QFrame() 
        self.enemies_border_frame.setObjectName("panelBorderFrame")
        enemies_bg_layout.addWidget(self.enemies_border_frame)
        enemies_panel_layout.addWidget(self.enemies_header_label)
        enemies_panel_layout.addWidget(self.enemies_bg_frame, 1)
        enemies_content_layout = QVBoxLayout(self.enemies_border_frame) 
        self.enemies_panel = EnemiesPanel()
        enemies_content_layout.addWidget(self.enemies_panel)
        
        # --- Center Panel Structure (with nested border frame) ---
        self.center_panel_container = QWidget()
        center_panel_layout = QVBoxLayout(self.center_panel_container)
        center_panel_layout.setContentsMargins(0,0,0,0); center_panel_layout.setSpacing(0)
        center_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.center_header_label = QLabel("Turn Order")
        self.center_header_label.setObjectName("panelHeaderLabel")
        self.center_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_bg_frame = QFrame()
        self.center_bg_frame.setObjectName("centerBGFrame")
        center_bg_layout = QVBoxLayout(self.center_bg_frame)
        center_bg_layout.setContentsMargins(0,0,0,0)
        self.center_border_frame = QFrame() 
        self.center_border_frame.setObjectName("panelBorderFrame")
        center_bg_layout.addWidget(self.center_border_frame)
        center_panel_layout.addWidget(self.center_header_label)
        center_panel_layout.addWidget(self.center_bg_frame, 1)
        center_content_layout = QVBoxLayout(self.center_border_frame) 
        center_content_layout.setContentsMargins(15, 15, 15, 15); center_content_layout.setSpacing(15)

        turn_order_placeholder = QLabel("Turn order portraits will go here.")
        turn_order_placeholder.setMinimumHeight(80)

        # --- Combat Log Structure (with nested border frame) ---
        self.log_container = QWidget()
        log_layout = QVBoxLayout(self.log_container)
        log_layout.setContentsMargins(0,0,0,0); log_layout.setSpacing(0)
        log_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.log_header_label = QLabel("Combat Log")
        self.log_header_label.setObjectName("panelHeaderLabel")
        self.log_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.log_bg_frame = QFrame()
        self.log_bg_frame.setObjectName("logBGFrame")
        log_bg_layout = QVBoxLayout(self.log_bg_frame)
        log_bg_layout.setContentsMargins(0,0,0,0)
        self.log_border_frame = QFrame() 
        self.log_border_frame.setObjectName("panelBorderFrame")
        log_bg_layout.addWidget(self.log_border_frame)
        log_layout.addWidget(self.log_header_label)
        log_layout.addWidget(self.log_bg_frame, 1)
        log_content_layout = QVBoxLayout(self.log_border_frame) 
        log_content_layout.setContentsMargins(0,0,0,0); log_content_layout.setSpacing(0)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setObjectName("combatLogText")
        log_content_layout.addWidget(self.log_text)

        center_content_layout.addWidget(turn_order_placeholder, 1)
        center_content_layout.addWidget(self.log_container, 5)

        sections_layout.addWidget(self.allies_panel_container, 3)
        sections_layout.addWidget(self.center_panel_container, 4)
        sections_layout.addWidget(self.enemies_panel_container, 3)

        grid_layout.addLayout(status_layout, 0, 0)
        grid_layout.addLayout(sections_layout, 1, 0)
        
        grid_layout.setRowMinimumHeight(2, 70) 
        
        grid_layout.setRowStretch(1, 1)

        self.last_log_index = -1 
        self._gradual_log_iterator: Optional[Iterator[str]] = None
        self._gradual_log_format: Optional[QTextCharFormat] = None
        self._gradual_log_timer: Optional[QTimer] = None
        self._is_gradual_log_active: bool = False
        self._pending_log_messages: List[Tuple[str, QTextCharFormat, bool]] = [] 

        self.apply_theme()
        self.clear_display()
        self._suppress_visual_complete = False
        self._init_dev_controls()

    def set_command_input_widget(self, command_widget: QWidget):
        """Stores a reference to the command input widget and sets its parent."""
        self.command_input_widget = command_widget
        self.command_input_widget.setParent(self)
        self.command_input_widget.show()

    def resizeEvent(self, event):
        """Handle resize events to manually position the command input overlay."""
        super().resizeEvent(event)
        
        if self.command_input_widget:
            # Position the command input widget at the very bottom of the CombatDisplay
            margin = 10
            # Use a fixed height hint for the command input
            widget_height = self.command_input_widget.sizeHint().height()
            
            # Calculate geometry relative to the CombatDisplay widget itself
            x = margin
            # Position it in the reserved space at the bottom
            y = self.height() - widget_height - margin
            width = self.width() - (2 * margin)
            
            self.command_input_widget.setGeometry(x, y, width, widget_height)

    def save_settings(self):
        """Save current settings to JSON file."""
        logger.info(f"Saving combat display settings to: {SETTINGS_FILE}")
        try:
            # Ensure config directory exists before writing
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.current_settings, f, indent=4)
            logger.info("Settings saved successfully.")
        except IOError as e:
            logger.error(f"Error saving combat display settings: {e}")

    def _init_dev_controls(self):
        """Initialize dev controls based on QSettings and wire their signals."""
        try:
            settings = QSettings("RPGGame", "Settings")
            dev_enabled = settings.value("dev/enabled", False, type=bool)
        except Exception:
            dev_enabled = False
        self.dev_controls_container.setVisible(bool(dev_enabled))
        # Wire buttons to orchestrator
        try:
            engine = get_game_engine()
            orch = getattr(engine, '_combat_orchestrator', None)
            if orch:
                # Disconnect existing to avoid duplicates
                try:
                    self.dev_step_mode_btn.toggled.disconnect(orch.toggle_dev_step_mode)
                except Exception:
                    pass
                try:
                    self.dev_next_step_btn.clicked.disconnect(orch.dev_release_next_step)
                except Exception:
                    pass
                self.dev_step_mode_btn.toggled.connect(orch.toggle_dev_step_mode)
                self.dev_next_step_btn.clicked.connect(orch.dev_release_next_step)
                # Listen to waiting state to enable/disable Next button
                try:
                    orch.dev_waiting_state_changed.disconnect(self._on_orchestrator_dev_waiting_changed)
                except Exception:
                    pass
                orch.dev_waiting_state_changed.connect(self._on_orchestrator_dev_waiting_changed)
        except Exception as e:
            logger.warning(f"Failed initializing dev controls: {e}")

    def clear_display(self):
        """Clear the display and set to inactive/narrative state."""
        self.combat_active = False
        self.status_label.setText("Status: Narrative")
        self.round_label.setText("Round: 0")
        self.round_label.setVisible(False)
        self.last_log_index = -1

        try:
            self.clear_log()
        except Exception:
            pass

        # Use the new container names and panel instances
        if hasattr(self, 'allies_panel_container'):
            self.allies_panel.clear_allies()
            self.allies_panel_container.setVisible(False)
        if hasattr(self, 'enemies_panel_container'):
            self.enemies_panel.clear_enemies()
            self.enemies_panel_container.setVisible(False)
        if hasattr(self, 'center_panel_container'):
            self.center_panel_container.setVisible(False)

    def rebuild_log_from_history(self, history: List[Dict[str, str]]):
        """
        Clears the current log and rebuilds it from a list of historical entries,
        applying current theme settings based on the stored role.
        """
        logger.info(f"Rebuilding combat log from a history of {len(history)} entries.")
        if self._is_gradual_log_active:
            self.stop_gradual_display()
        
        self.log_text.clear()
        
        # Process each entry from the history
        for entry in history:
            if isinstance(entry, dict):
                content = entry.get("content", "")
                role = entry.get("role", "system")
                if content:
                    # Use the main rendering function to apply theme-correct formatting
                    self.append_orchestrated_event_content(content, role, is_gradual=False)
            else:
                # Fallback for old save format (plain strings)
                self.append_orchestrated_event_content(str(entry), "system", is_gradual=False)

    def _update_combat_log(self, log_entries: List[str]): # Added type hint
        """Update the combat log incrementally with new entries."""
        if not log_entries:
            return
        # Gate [DEV] lines if dev mode is disabled
        try:
            settings = QSettings("RPGGame", "Settings")
            dev_enabled = settings.value("dev/enabled", False, type=bool)
            if not dev_enabled:
                log_entries = [e for e in log_entries if not (isinstance(e, str) and e.strip().startswith("[DEV]"))]
                if not log_entries:
                    return
        except Exception:
            pass

        scrollbar = self.log_text.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 10 # Is the user scrolled near the bottom?

        start_index = self.last_log_index + 1
        if start_index >= len(log_entries):
            return

        new_entries_to_process = log_entries[start_index:]
        logger.debug(f"Processing {len(new_entries_to_process)} new log entries (from index {start_index})")

        new_entries_added = False
        for entry_index, entry in enumerate(new_entries_to_process):
            # Determine color/format based on entry content and settings
            color_hex = self.current_settings.get("color_log_default", "#E0E0E0")
            is_bold = False
            is_italic = False
            is_narrative = True # Assume GM/Narrative by default

            entry_lower = entry.lower()

            # Simplified system message check (more robust checks might be needed)
            if entry.startswith("[SYSTEM]") or \
            "roll" in entry_lower and "vs" in entry_lower or \
            "takes" in entry_lower and "damage" in entry_lower or \
            "misses" in entry_lower or \
            "defeated" in entry_lower or \
            "fumble" in entry_lower or \
            "critical hit" in entry_lower or \
            "status expire" in entry_lower or \
            "turn." in entry_lower or \
            "round" in entry_lower and "begins" in entry_lower or \
            entry.startswith("Turn order:") or \
            "Stamina Cost:" in entry: # Check for stamina cost message
                is_narrative = False # Mark as system message

            # --- Color/Style Logic (using settings) ---
            # (Keep existing color logic)
            if entry.startswith("[DEV]"): color_hex = self.current_settings.get("color_log_dev", "#888888"); is_italic = True; is_narrative = False
            elif "critical hit" in entry_lower or "defeated!" in entry_lower or "was defeated" in entry_lower: color_hex = self.current_settings.get("color_log_crit", "#FF4444"); is_bold = True; is_narrative = False
            elif "healed" in entry_lower or "gains" in entry_lower and ("hp" in entry_lower or "stamina" in entry_lower): color_hex = self.current_settings.get("color_log_heal", "#44FF44"); is_narrative = False # Healing is often systemic
            elif "round" in entry_lower and "begins" in entry_lower: color_hex = self.current_settings.get("color_log_round", "#66AAFF"); is_bold = True; is_narrative = False
            elif "turn" in entry_lower or "'s turn" in entry_lower: color_hex = self.current_settings.get("color_log_turn", "#88CCFF"); is_narrative = False
            elif "combat started" in entry_lower or "combat ended" in entry_lower or "victory!" in entry_lower or "defeat!" in entry_lower or "fled!" in entry_lower or "surrender" in entry_lower: color_hex = self.current_settings.get("color_log_combat_event", "#FFFFFF"); is_bold = True; is_narrative = False
            elif "misses" in entry_lower or "fails" in entry_lower or "resisted" in entry_lower or "escape fails" in entry_lower: color_hex = self.current_settings.get("color_log_miss", "#AAAAAA"); is_italic = True; is_narrative = False
            elif "damage" in entry_lower or "loses" in entry_lower and ("hp" in entry_lower or "resolve" in entry_lower): color_hex = self.current_settings.get("color_log_damage", "#FF8888"); is_narrative = False
            elif "roll" in entry_lower or "vs" in entry_lower: color_hex = self.current_settings.get("color_log_roll", "#FFCC66"); is_narrative = False

            # Append with determined format and gradual flag
            text_format = QTextCharFormat()
            try:
                text_format.setForeground(QColor(color_hex))
            except ValueError:
                logger.warning(f"Invalid color hex '{color_hex}' for log entry. Using default.")
                text_format.setForeground(QColor(self.current_settings.get("color_log_default", "#E0E0E0")))

            if is_bold: text_format.setFontWeight(QFont.Weight.Bold)
            if is_italic: text_format.setFontItalic(True)

            # Use gradual display ONLY for narrative messages
            self._append_formatted_text(entry, text_format, gradual=is_narrative) # Pass gradual flag
            new_entries_added = True

            # Update last processed index
            self.last_log_index = start_index + entry_index

    def _append_formatted_text(self, text: str, text_format: QTextCharFormat, gradual: bool = False):
        """Appends text to the log, either immediately or gradually."""
        settings = QSettings("RPGGame", "Settings")
        use_gradual = gradual and settings.value("display/gradual_text_combat_log", True, type=bool) # Check setting

        if not text.strip(): # Don't append empty or whitespace-only lines
            logger.debug("Skipping append of empty/whitespace log message.")
            self.visualDisplayComplete.emit() # Emit completion even for skipped empty text
            return

        if not text.endswith('\n'):
            text += '\n'

        if self._is_gradual_log_active:
            logger.debug(f"Queueing log message (Gradual: {use_gradual}): '{text[:50]}...'")
            self._pending_log_messages.append((text, text_format, use_gradual))
            return

        if not use_gradual:
            logger.debug(f"Appending immediate log message: '{text[:50]}...'")
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(text, text_format)
            self.log_text.setTextCursor(cursor) 
            self.log_text.ensureCursorVisible()
            if not getattr(self, '_suppress_visual_complete', False):
                logger.info(f"CombatDisplay: immediate display complete; emitting visualDisplayComplete for id={getattr(self, '_current_text_event_id', None)}")
                self.visualDisplayComplete.emit() # --- ECFA Change: Emit signal ---
                # Event-based direct notify to orchestrator as well
                try:
                    eng = get_game_engine()
                    if eng and hasattr(eng, '_combat_orchestrator') and eng._combat_orchestrator.is_waiting_for_visual:
                        logger.debug(f"CombatDisplay: immediate direct orchestrator complete for id={getattr(self, '_current_text_event_id', None)}")
                        eng._combat_orchestrator._handle_visual_display_complete()
                except Exception:
                    pass
            self._process_next_pending_log_message()
            return

        logger.debug(f"Starting gradual log display: '{text[:50]}...'")
        self._is_gradual_log_active = True
        self._gradual_log_iterator = iter(text)
        self._gradual_log_format = text_format

        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

        if not self._gradual_log_timer:
            self._gradual_log_timer = QTimer(self)
            self._gradual_log_timer.setSingleShot(True)
            self._gradual_log_timer.timeout.connect(self._display_next_log_char)

        QTimer.singleShot(1, self._display_next_log_char)

    @Slot()
    def _display_next_log_char(self):
        """Displays the next character for the combat log gradual display."""
        if not self._is_gradual_log_active or not self._gradual_log_iterator:
            if self._is_gradual_log_active: 
                self._is_gradual_log_active = False
                if not getattr(self, '_suppress_visual_complete', False):
                    self.visualDisplayComplete.emit() 
                self._process_next_pending_log_message()
            return

        try:
            char = next(self._gradual_log_iterator)
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            if self._gradual_log_format:
                cursor.insertText(char, self._gradual_log_format)
            else:
                cursor.insertText(char) 
            self.log_text.setTextCursor(cursor) 
            self.log_text.ensureCursorVisible() 

            settings = QSettings("RPGGame", "Settings")
            char_delay = settings.value("display/text_speed_delay", 30, type=int) 
            char_delay = max(5, int(char_delay)) 
            if self._gradual_log_timer: 
                self._gradual_log_timer.start(char_delay)

        except StopIteration:
            self._is_gradual_log_active = False
            self._gradual_log_iterator = None
            self._gradual_log_format = None
            logger.info(f"CombatDisplay: gradual display finished; emitting visualDisplayComplete for id={getattr(self, '_current_text_event_id', None)}")
            if not getattr(self, '_suppress_visual_complete', False):
                self.visualDisplayComplete.emit() 
                # Event-based direct notify to orchestrator as well
                try:
                    eng = get_game_engine()
                    if eng and hasattr(eng, '_combat_orchestrator') and eng._combat_orchestrator.is_waiting_for_visual:
                        logger.debug(f"CombatDisplay: gradual direct orchestrator complete for id={getattr(self, '_current_text_event_id', None)}")
                        eng._combat_orchestrator._handle_visual_display_complete()
                except Exception:
                    pass
            self._process_next_pending_log_message()

        except Exception as e:
            logger.error(f"Error during gradual log display: {e}", exc_info=True)
            self._is_gradual_log_active = False
            self._gradual_log_iterator = None
            self._gradual_log_format = None
            if self._gradual_log_timer and self._gradual_log_timer.isActive():
                self._gradual_log_timer.stop()
            if not getattr(self, '_suppress_visual_complete', False):
                logger.info(f"CombatDisplay: gradual error path; emitting visualDisplayComplete for id={getattr(self, '_current_text_event_id', None)}")
                self.visualDisplayComplete.emit() 
                # Event-based direct notify to orchestrator as well
                try:
                    eng = get_game_engine()
                    if eng and hasattr(eng, '_combat_orchestrator') and eng._combat_orchestrator.is_waiting_for_visual:
                        logger.debug(f"CombatDisplay: error direct orchestrator complete for id={getattr(self, '_current_text_event_id', None)}")
                        eng._combat_orchestrator._handle_visual_display_complete()
                except Exception:
                    pass
            self._pending_log_messages.clear() 
            self._process_next_pending_log_message() # Process queue even on error

    def _process_next_pending_log_message(self):
        """Processes the next message in the pending queue."""
        if not self._is_gradual_log_active and self._pending_log_messages:
            text, text_format, is_gradual = self._pending_log_messages.pop(0)
            logger.debug(f"Processing pending log message (Gradual: {is_gradual}): '{text[:50]}...'")
            # Call _append_formatted_text again - it will handle starting gradual or immediate append
            self._append_formatted_text(text, text_format, gradual=is_gradual)

    def clear_log(self):
        """Clear the combat log."""
        self.log_text.clear()
        logger.info("Combat log cleared.")
        # Add header back immediately after clearing?
        # header_format = QTextCharFormat()
        # header_format.setFontWeight(QFont.Bold)
        # header_format.setForeground(QColor(self.current_settings.get("color_log_header", "#A0A0A0")))
        # self._append_formatted_text("===== COMBAT LOG =====", header_format)


    def open_settings_dialog(self):
        """
        --- SETTINGS UI DISCONNECTED ---
        This function is no longer used. Styling is controlled by the
        COMBAT_DISPLAY_THEME dictionary in the code.
        """
        logger.info("Combat settings dialog is currently disconnected.")
        # dialog = CombatSettingsDialog(self.current_settings.copy(), IMAGE_DIR, self)
        # if dialog.exec():
        #     new_settings = dialog.get_settings()
        #     if new_settings != self.current_settings:
        #         logger.info("Settings changed. Saving and applying...")
        #         self.current_settings = new_settings
        #         # self.save_settings() # Saving is also disconnected
        #         self.apply_settings()

    def append_buffered_messages(self, messages: List[str], gradual: bool):
        """
        Appends a list of messages, typically from the combat_narrative_buffer.
        The visualDisplayComplete signal will be emitted after the *last* message in the list
        has finished displaying.
        """
        if not messages:
            self.visualDisplayComplete.emit() # Emit if buffer is empty
            return

        logger.debug(f"Appending {len(messages)} buffered messages. Gradual: {gradual}")
        
        # Use default GM format for buffered messages (usually narrative)
        # This format should be configurable or passed with the event in a richer system
        gm_format = QTextCharFormat()
        gm_format.setForeground(QColor(self.current_settings.get("color_log_default", "#E0E0E0"))) # Example color
        # font_family = self.current_settings.get("font_family", "Arial")
        # font_size = self.current_settings.get("font_size", 10)
        # gm_format.setFont(QFont(font_family, font_size))


        for i, message_content in enumerate(messages):
            is_last_message = (i == len(messages) - 1)
            
            # If it's the last message, its completion will trigger the main visualDisplayComplete.
            # For other messages, we don't want them to trigger the orchestrator's main logic.
            # This requires _append_formatted_text to know if it's part of a batch.
            # Simpler for now: _append_formatted_text always emits. Orchestrator ignores intermediate ones
            # if it knows it's processing a BUFFER_FLUSH event with multiple items.
            # This detail depends on how Orchestrator handles BUFFER_FLUSH DisplayEvents.

            # For now, let's assume _append_formatted_text handles queuing and will eventually
            # emit visualDisplayComplete after the *entire sequence* of buffered messages.
            # This means _append_formatted_text needs to be smarter or we need a different approach.

            # Refined approach: _append_formatted_text queues. The final visualDisplayComplete
            # will be emitted when the *last* character of the *last* message is displayed.
            self._append_formatted_text(message_content, gm_format, gradual)

    def stop_gradual_display(self):
        """Immediately stops any ongoing gradual text display and processes pending messages quickly."""
        logger.info("Stopping current gradual display and flushing pending messages.")
        if self._gradual_log_timer and self._gradual_log_timer.isActive():
            self._gradual_log_timer.stop()
        
        # If an iterator was active, display remaining text immediately
        if self._gradual_log_iterator:
            remaining_text = "".join(list(self._gradual_log_iterator))
            if remaining_text:
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                if self._gradual_log_format:
                    cursor.insertText(remaining_text, self._gradual_log_format)
                else:
                    cursor.insertText(remaining_text)
                self.log_text.setTextCursor(cursor)
                self.log_text.ensureCursorVisible()
            self._gradual_log_iterator = None
            self._gradual_log_format = None

        self._is_gradual_log_active = False # Mark as not active
        
        # Process all pending messages immediately (non-gradual)
        while self._pending_log_messages:
            text, text_format, _ = self._pending_log_messages.pop(0) # Ignore original gradual flag
            logger.debug(f"Flushing pending message immediately: '{text[:50]}...'")
            if not text.endswith('\n'): text += '\n'
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(text, text_format)
            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()
            
        self.visualDisplayComplete.emit()

    def append_orchestrated_event_content(self, event_content: str, event_role: str, is_gradual: bool, event_id: Optional[str] = None):
        """
        Appends orchestrated event content to the combat log, using the theme palette
        for color formatting based on the message role.
        """
        try:
            self._current_text_event_id = event_id
            logger.info(f"CombatDisplay: render string event id={event_id} gradual={bool(is_gradual)} len={len(event_content) if isinstance(event_content, str) else 'N/A'}")
        except Exception:
            pass
        
        try:
            if isinstance(event_content, str) and event_content.strip().startswith("[DEV]"):
                settings = QSettings("RPGGame", "Settings")
                if not settings.value("dev/enabled", False, type=bool):
                    self.visualDisplayComplete.emit()
                    try:
                        eng = get_game_engine()
                        if eng and hasattr(eng, '_combat_orchestrator') and eng._combat_orchestrator.is_waiting_for_visual:
                            logger.debug(f"CombatDisplay: Direct notify orchestrator complete for DEV-suppressed id={event_id}")
                            eng._combat_orchestrator._handle_visual_display_complete()
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        
        colors = self.palette.get('colors', {})
        color_hex = colors.get("log_narrative", "#3D2B1F")
        is_bold = False
        is_italic = False

        role_lower = event_role.lower() if event_role else "system"
        content_lower = event_content.lower()

        if role_lower == "gm":
            color_hex = colors.get("log_narrative", "#3D2B1F")
        
        elif role_lower == "system":
            color_hex = colors.get("log_system_message", "#00008B")
            
            if "critical hit" in content_lower or "defeated!" in content_lower or "was defeated" in content_lower:
                color_hex = colors.get("log_crit", "#FF0000")
                is_bold = True
            elif "healed" in content_lower or ("gains" in content_lower and ("hp" in content_lower or "stamina" in content_lower)):
                color_hex = colors.get("log_heal", "#009600")
            elif "round" in content_lower and "begins" in content_lower:
                color_hex = colors.get("log_round", "#0064FF")
                is_bold = True
            elif "turn order:" in content_lower or "'s turn" in content_lower:
                color_hex = colors.get("log_turn", "#0064C8")
            elif "combat started" in content_lower or "combat ended" in content_lower or "victory!" in content_lower or "defeat!" in content_lower or "fled!" in content_lower or "surrender" in content_lower:
                color_hex = colors.get("log_combat_event", "#000000")
                is_bold = True
            elif "misses" in content_lower or "fails" in content_lower or "resisted" in content_lower or "escape fails" in content_lower or "fumble" in content_lower:
                color_hex = colors.get("log_miss", "#6c5b4b")
                is_italic = True
            elif "damage" in content_lower or ("loses" in content_lower and ("hp" in content_lower or "resolve" in content_lower)):
                color_hex = colors.get("log_damage", "#C80000")
            elif "roll" in content_lower or "vs" in content_lower:
                color_hex = colors.get("log_roll", "#C87800")
            elif event_content.startswith("[DEV]"):
                color_hex = colors.get("log_dev", "#646464")
                is_italic = True

        text_format = QTextCharFormat()
        try:
            text_format.setForeground(QColor(color_hex))
        except (ValueError, TypeError):
            logger.warning(f"Invalid color hex '{color_hex}' for combat log. Using default.")
            text_format.setForeground(QColor(colors.get("log_narrative", "#3D2B1F")))

        if is_bold: text_format.setFontWeight(QFont.Weight.Bold)
        if is_italic: text_format.setFontItalic(True)
        
        self._append_formatted_text(event_content, text_format, gradual=is_gradual)

    @Slot(bool)
    def _on_orchestrator_dev_waiting_changed(self, waiting: bool):
        self.dev_next_step_btn.setEnabled(bool(waiting))

    @Slot(GameState)
    def update_display(self, game_state: GameState):
        """Update the display based on the current GameState."""
        if game_state is None:
            logger.warning("CombatDisplay.update_display received None GameState, clearing display.")
            self.clear_display()
            return

        current_mode_enum = getattr(game_state, 'current_mode', InteractionMode.NARRATIVE)
        mode = current_mode_enum.name if hasattr(current_mode_enum, 'name') else str(current_mode_enum)
        
        logger.info(f"CombatDisplay.update_display called. Game Mode: {mode}")

        if mode in ["COMBAT", "SOCIAL_CONFLICT"]:
            try:
                settings = QSettings("RPGGame", "Settings")
                dev_enabled = settings.value("dev/enabled", False, type=bool)
                self.dev_controls_container.setVisible(bool(dev_enabled))
            except Exception:
                self.dev_controls_container.setVisible(False)
            self.setVisible(True)
            
            if not self.combat_active: 
                logger.info(f"CombatDisplay: First entry into {mode} view. Setting up UI visibility.")
                # Use the new container names
                self.allies_panel_container.setVisible(True)
                self.enemies_panel_container.setVisible(True)
                self.center_panel_container.setVisible(True)
                self.combat_active = True
                self.apply_settings()
            
            combat_manager = getattr(game_state, 'combat_manager', None)
            if not combat_manager:
                logger.warning(f"CombatDisplay: {mode} mode active but no CombatManager found. Clearing panels.")
                self.status_label.setText(f"Status: {mode} (Error - No Manager)")
                self.allies_panel.clear_allies()
                self.enemies_panel.clear_enemies()
                return
            
            logger.info(f"CombatDisplay: CombatManager found (ID: {getattr(combat_manager, 'id', 'N/A')}). Entities in CM: {len(getattr(combat_manager, 'entities', {}))}")

            round_num = getattr(combat_manager, 'round_number', 0)
            cm_state_attr = getattr(combat_manager, 'state', None)
            cm_state_name = cm_state_attr.name if hasattr(cm_state_attr, 'name') else "Unknown State"

            if mode == "COMBAT":
                self.round_label.setVisible(True)
                self.round_label.setText(f"Round: {round_num}")
                if cm_state_name == "IN_PROGRESS": self.status_label.setText("Status: Combat Active")
                elif cm_state_name == "PLAYER_VICTORY": self.status_label.setText("Status: Victory!")
                elif cm_state_name == "PLAYER_DEFEAT": self.status_label.setText("Status: Defeat!")
                elif cm_state_name == "FLED": self.status_label.setText("Status: Fled from Combat")
                else: self.status_label.setText(f"Status: Combat - {cm_state_name}")
            else: 
                self.status_label.setText("Status: Social Conflict")
                self.round_label.setVisible(False)

            current_turn_id = getattr(combat_manager, 'get_current_entity_id', lambda: None)()
            
            allies_data = {}
            enemies_data = {}
            cm_entities = getattr(combat_manager, 'entities', {})

            if cm_entities:
                for entity_id, combat_entity in cm_entities.items():
                    if not getattr(combat_entity, 'is_active_in_combat', True):
                        continue

                    raw_status_effects = getattr(combat_entity, 'status_effects', {})
                    display_status_effects = []
                    if isinstance(raw_status_effects, dict):
                        display_status_effects = [f"{name}({dur})" if dur not in [None, float('inf')] else name for name, dur in raw_status_effects.items()]
                    elif isinstance(raw_status_effects, (list, set)):
                        display_status_effects = [str(eff_name) for eff_name in raw_status_effects]
                    
                    entity_type_enum = getattr(combat_entity, 'entity_type', EntityType.ENEMY)
                    is_player_side = entity_type_enum == EntityType.PLAYER

                    entity_dict = {
                        "id": entity_id, 
                        "name": getattr(combat_entity, 'name', 'N/A'), 
                        "combat_name": getattr(combat_entity, 'combat_name', 'N/A'), 
                        "current_hp": getattr(combat_entity, 'current_hp', 0), 
                        "max_hp": getattr(combat_entity, 'max_hp', 1) if getattr(combat_entity, 'max_hp', 0) > 0 else 1,
                        "current_stamina": getattr(combat_entity, 'current_stamina', 0), 
                        "max_stamina": getattr(combat_entity, 'max_stamina', 1) if getattr(combat_entity, 'max_stamina', 0) > 0 else 1,
                        "current_mana": getattr(combat_entity, 'current_mp', 0),
                        "max_mana": getattr(combat_entity, 'max_mp', 1) if getattr(combat_entity, 'max_mp', 0) > 0 else 1,
                        "status_effects": display_status_effects,
                    }

                    if is_player_side:
                        allies_data[entity_id] = entity_dict
                    else:
                        enemies_data[entity_id] = entity_dict
            
            self.allies_panel.update_allies(allies_data, current_turn_id)
            self.enemies_panel.update_enemies(enemies_data, current_turn_id)

        elif self.combat_active: 
            logger.info(f"CombatDisplay: Exiting {mode} view (was active). Clearing display.")
            self.clear_display() 
            self.setVisible(False)

    @Slot(dict)
    def apply_theme(self, palette: Optional[Dict[str, Any]] = None):
        """Apply the current theme palette to the combat display UI."""
        if palette:
            self.palette = palette
        else:
            self.palette = self.theme_manager.get_current_palette()
        
        full_stylesheet = create_combat_display_style(self.palette)
        self.setStyleSheet(full_stylesheet)
        
        # Pass the complete theme palette to child panels
        self.allies_panel.apply_settings(self.palette)
        self.enemies_panel.apply_settings(self.palette)
        
        self.update()
        logger.info("Combat display theme updated.")

