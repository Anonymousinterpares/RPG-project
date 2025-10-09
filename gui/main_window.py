#!/usr/bin/env python3
"""
Main window for the RPG game GUI.
This module provides the MainWindow class that serves as the primary GUI container.
"""

import logging
import os
import weakref
from typing import Optional, List, Dict, Any, Tuple
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QDialog, QLabel, QPushButton, 
    QTextEdit, QScrollArea, QGraphicsOpacityEffect, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QSize, QSettings, QObject, QThread, Signal, QParallelAnimationGroup, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPixmap, QPalette, QBrush, QColor, QMovie, QTextCursor # Added QTextCursor
from core.inventory import get_inventory_manager
from core.inventory.item import Item
from core.inventory.item_enums import EquipmentSlot
from gui.dialogs.game_over_dialog import GameOverDialog
from core.base.engine import GameEngine, get_game_engine
from core.combat.enums import CombatState, CombatStep
from core.interaction.enums import InteractionMode # Added import
from core.base.state import GameState, get_state_manager # Added imports
from core.utils.logging_config import get_logger
from gui.components.game_output import GameOutputWidget
from gui.components.command_input import CommandInputWidget
from gui.components.menu_panel import MenuPanelWidget
from gui.components.right_panel import CollapsibleRightPanel
from gui.components.status_bar import GameStatusBar
from gui.components.combat_display import CombatDisplay # Added import
from gui.utils.resource_manager import get_resource_manager
from gui.dialogs.settings.llm_settings_dialog import LLMSettingsDialog

logger = get_logger("GUI")

class MainWindow(QMainWindow):
    """Main window for the RPG game GUI."""
    
    def __init__(self):
            super().__init__()
            
            self._previous_mode = None # Track previous mode for transitions
            
            # Get resource manager
            self.resource_manager = get_resource_manager()
            
            # Get game engine
            self.game_engine = get_game_engine()

            # Register this MainWindow with the engine so orchestrator/engine can nudge UI updates
            try:
                self.game_engine.main_window_ref = weakref.ref(self)
            except Exception:
                pass

            # Set minimum size based on reasonable content size hint
            self.setMinimumSize(1024, 700) # Set a sensible minimum size

            # Store character data temporarily during animation
            self._character_data_for_new_game: Optional[Dict[str, Any]] = None

            # Set up the UI
            self._setup_ui()
            
            # Connect signals and slots
            self._connect_signals()
            
            # Apply initial styling
            self._update_styling()

            self._last_submitted_command = None

    def _apply_initial_window_state(self):
        """Apply saved window state and geometry when the window is first shown."""
        settings = QSettings("RPGGame", "Settings")
        window_state = settings.value("display/window_state", "windowed") # Default to windowed
        
        logger.info(f"Applying initial window state: {window_state}")

        if window_state == "fullscreen":
            self.showFullScreen()
        elif window_state == "maximized":
            self.showMaximized()
        else: # windowed
            # Load saved windowed size or default
            default_size = QSize(1280, 720)
            windowed_size = settings.value("display/windowed_size", default_size)
            # Ensure windowed_size is a QSize object
            if not isinstance(windowed_size, QSize):
                # Attempt conversion if it's a tuple/list or handle potential string format
                if isinstance(windowed_size, (tuple, list)) and len(windowed_size) == 2:
                    windowed_size = QSize(windowed_size[0], windowed_size[1])
                elif isinstance(windowed_size, str):
                     try:
                         parts = windowed_size.strip('()').split(',')
                         windowed_size = QSize(int(parts[0]), int(parts[1]))
                     except Exception:
                         windowed_size = default_size # Fallback on parse error
                else:
                    windowed_size = default_size # Fallback if type is unexpected

            self.showNormal() # Ensure not maximized/fullscreen first
            self.resize(windowed_size) # Apply the loaded/default size
            # Optional: Center the window
            screen_geometry = self.screen().availableGeometry()
            self.move(screen_geometry.center() - self.rect().center())        

    def showEvent(self, event):
        """Override showEvent to apply initial window state after the window is shown."""
        super().showEvent(event)
        # Apply the state only once when the window is first shown
        if not hasattr(self, '_initial_state_applied') or not self._initial_state_applied:
             self._apply_initial_window_state()
             self._initial_state_applied = True

    def closeEvent(self, event):
        """Handle window close event, saving window state."""
        # Ask for confirmation
        reply = QMessageBox.question(
            self, 
            "Exit Game", 
            "Are you sure you want to exit? Unsaved progress will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # --- Save Window State ---
            settings = QSettings("RPGGame", "Settings")
            current_state_str = "windowed" # Default
            if self.isFullScreen():
                current_state_str = "fullscreen"
            elif self.isMaximized():
                current_state_str = "maximized"
            
            settings.setValue("display/window_state", current_state_str)
            
            # Save the *current* size only if the state is 'windowed'
            if current_state_str == "windowed":
                 settings.setValue("display/windowed_size", self.size())
            logger.info(f"Saved window state ({current_state_str}) and size ({self.size() if current_state_str == 'windowed' else 'N/A'}) on exit.")
            # --- End Save Window State ---

            # Stop the game engine
            self.game_engine.stop()

            # Stop background movie if playing
            bg_movie = self.background_label.movie()
            if bg_movie:
                bg_movie.stop()

            event.accept()
        else:
            event.ignore()

    def _apply_saved_resolution(self):
        """Apply saved resolution from settings."""
        settings = QSettings("RPGGame", "Settings")
        resolution = settings.value("display/resolution", (1280, 720))
        
        # Convert to tuple if it's a string (can happen with some QSettings implementations)
        if isinstance(resolution, str):
            try:
                # Handle string format like "(1280, 720)"
                if resolution.startswith("(") and resolution.endswith(")"):
                    parts = resolution.strip("()").split(",")
                    resolution = (int(parts[0].strip()), int(parts[1].strip()))
            except:
                # Fallback to default if parsing fails
                resolution = (1280, 720)
                logging.warning("Failed to parse resolution setting, using default")
        
        # Set window size
        self.setFixedSize(*resolution)
        logging.info(f"Applied saved resolution: {resolution}")
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("RPG Game")
        
        self.background_container = QWidget()
        self.setCentralWidget(self.background_container)
        self.background_container.setStyleSheet("background-color: transparent;")

        self.background_label = QLabel(self.background_container)
        self.background_label.setGeometry(0, 0, self.width(), self.height()) 
        self.background_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.background_label.setScaledContents(True) 

        self.main_content_widget = QWidget(self.background_container)
        self.main_content_widget.setGeometry(0, 0, self.width(), self.height()) 
        self.main_content_widget.setStyleSheet("background-color: transparent;") 

        self.main_layout = QVBoxLayout(self.main_content_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10) 
        self.main_layout.setSpacing(5)
        
        self.mode_stacked_widget = QStackedWidget()
        
        self.narrative_view = QWidget()
        self.narrative_layout = QVBoxLayout(self.narrative_view)
        self.narrative_layout.setContentsMargins(0, 0, 0, 0)
        self.narrative_layout.setSpacing(0)
        
        self.combat_view = QWidget()
        self.combat_layout = QVBoxLayout(self.combat_view)
        self.combat_layout.setContentsMargins(0, 0, 0, 0)
        self.combat_layout.setSpacing(0)
        
        title_pixmap = self.resource_manager.get_pixmap("title_banner")
        if not title_pixmap.isNull():
            self.title_label = QLabel()
            target_height = 100
            scaled_pixmap = title_pixmap.scaled(
                QSize(1000, target_height), 
                Qt.KeepAspectRatio,         
                Qt.SmoothTransformation     
            )
            self.title_label.setPixmap(scaled_pixmap)
            self.title_label.setAlignment(Qt.AlignCenter)
            self.title_label.setContentsMargins(0, 0, 0, 5)
            self.main_layout.addWidget(self.title_label)
        
        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        
        self.menu_panel = MenuPanelWidget()
        
        self.game_output = GameOutputWidget()
        if hasattr(self.game_output, 'visualDisplayComplete') and hasattr(self.game_engine._combat_orchestrator, '_handle_visual_display_complete'):
            self.game_output.visualDisplayComplete.connect(self.game_engine._combat_orchestrator._handle_visual_display_complete)
            logger.info("Connected GameOutputWidget.visualDisplayComplete to Orchestrator.")
        else:
            logger.error("Failed to connect GameOutputWidget.visualDisplayComplete: Attribute or slot missing.")
        self.narrative_layout.addWidget(self.game_output, 1)
        
        self.narrative_command_input = CommandInputWidget()
        self.narrative_layout.addWidget(self.narrative_command_input, 0)
        
        self.combat_display = CombatDisplay()
        if hasattr(self.combat_display, 'visualDisplayComplete') and hasattr(self.game_engine._combat_orchestrator, '_handle_visual_display_complete'):
            self.combat_display.visualDisplayComplete.connect(self.game_engine._combat_orchestrator._handle_visual_display_complete)
            logger.info("Connected CombatDisplay.visualDisplayComplete to Orchestrator.")
        else:
            logger.error("Failed to connect CombatDisplay.visualDisplayComplete: Attribute or slot missing.")
        self.combat_layout.addWidget(self.combat_display, 1)
        
        self.combat_command_input = CommandInputWidget()
        self.combat_layout.addWidget(self.combat_command_input, 0)
        
        self.mode_stacked_widget.addWidget(self.narrative_view)
        self.mode_stacked_widget.addWidget(self.combat_view)
        
        self.center_widget = QWidget()
        center_layout = QVBoxLayout(self.center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.mode_stacked_widget)
        
        self.mode_stacked_widget.setCurrentWidget(self.narrative_view)
        
        self.right_panel = CollapsibleRightPanel()
        
        self.content_layout.addWidget(self.menu_panel, 0) # Stretch factor 0 for menu_panel
        self.content_layout.addWidget(self.center_widget, 1) # Stretch factor 1 for center_widget
        self.content_layout.addWidget(self.right_panel, 0) # Stretch factor 0 for right_panel
        
        self.main_layout.addLayout(self.content_layout, 1)
        
        self.music_controls = self._create_music_controls()
        
        self.status_bar = GameStatusBar()
        self.setStatusBar(self.status_bar)

        self._load_and_apply_initial_background()

        self._initialize_panel_effects() 
        
        # Initial state: center, right, and status bar are part of the layout but fully transparent and disabled.
        # setVisible(True) is important for them to be considered by the layout manager from the start.
        self.center_widget.setVisible(True) 
        self.center_widget.setEnabled(False)
        if hasattr(self, 'center_opacity_effect'):
            self.center_opacity_effect.setOpacity(0.0)

        self.right_panel.setVisible(True)
        self.right_panel.setEnabled(False)
        if hasattr(self, 'right_panel_opacity_effect'):
            self.right_panel_opacity_effect.setOpacity(0.0)
            
        self.status_bar.setVisible(True)
        self.status_bar.setEnabled(False)
        if hasattr(self, 'status_bar_opacity_effect'):
             self.status_bar_opacity_effect.setOpacity(0.0)

    def _create_music_controls(self):
        """Create music control widgets."""
        # Create a widget for the music controls
        music_widget = QWidget()
        music_layout = QHBoxLayout(music_widget)
        music_layout.setContentsMargins(0, 0, 0, 0)
        music_layout.setSpacing(5)
        
        # Create music control buttons
        play_pause_button = QPushButton()
        play_pause_button.setIcon(self.resource_manager.get_icon("music_play"))
        play_pause_button.setIconSize(QSize(24, 24))
        play_pause_button.setFixedSize(32, 32)
        play_pause_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        next_button = QPushButton()
        next_button.setIcon(self.resource_manager.get_icon("music_next"))
        next_button.setIconSize(QSize(24, 24))
        next_button.setFixedSize(32, 32)
        next_button.setStyleSheet(play_pause_button.styleSheet())
        
        volume_button = QPushButton()
        volume_button.setIcon(self.resource_manager.get_icon("music_volume"))
        volume_button.setIconSize(QSize(24, 24))
        volume_button.setFixedSize(32, 32)
        volume_button.setStyleSheet(play_pause_button.styleSheet())
        
        # Add buttons to layout
        music_layout.addWidget(play_pause_button)
        music_layout.addWidget(next_button)
        music_layout.addWidget(volume_button)
        
        # Add music controls to the top-right corner
        self.main_layout.insertWidget(0, music_widget, 0, Qt.AlignRight)
        
        # Return the widget for reference
        return music_widget
    
    def _connect_signals(self):
        """Connect signals and slots."""
        self.narrative_command_input.command_submitted.connect(self._process_command)
        self.combat_command_input.command_submitted.connect(self._process_command)

        logger.info("Connecting GameEngine.orchestrated_event_to_ui signal to MainWindow.process_orchestrated_display_event")
        try:
            self.game_engine.orchestrated_event_to_ui.connect(self.process_orchestrated_display_event)
            logger.info("Successfully connected orchestrated_event_to_ui signal")
        except Exception as e:
            logger.error(f"Failed to connect orchestrated_event_to_ui signal: {e}")
        
        logger.info("Connecting game engine output_generated signal to _handle_game_output (for non-orchestrated events)")
        try:
            self.game_engine.output_generated.connect(self._handle_game_output)
            logger.info("Successfully connected engine.output_generated signal")
        except Exception as e:
            logger.error(f"Failed to connect output_generated signal: {e}")

        self.menu_panel.new_game_requested.connect(self._show_new_game_dialog)
        self.menu_panel.save_game_requested.connect(self._show_save_game_dialog)
        self.menu_panel.load_game_requested.connect(self._show_load_game_dialog)
        self.menu_panel.settings_requested.connect(self._show_settings_dialog)
        self.menu_panel.llm_settings_requested.connect(self._show_llm_settings_dialog)
        self.menu_panel.exit_requested.connect(self.close)

        self.right_panel.tab_changed.connect(self._handle_tab_change)

        if hasattr(self.right_panel, 'inventory_panel'):
            self.right_panel.inventory_panel.item_use_requested.connect(self._handle_item_use_requested)
            self.right_panel.inventory_panel.item_examine_requested.connect(self._handle_item_examine_requested)
            self.right_panel.inventory_panel.item_equip_requested.connect(self._handle_item_equip_requested)
            self.right_panel.inventory_panel.item_unequip_requested.connect(self._handle_item_unequip_requested)
            self.right_panel.inventory_panel.item_drop_requested.connect(self._handle_item_drop_requested)
            logger.info("[GUI] MainWindow: Connected signals from InventoryPanelWidget (via right_panel).")
        else:
            logger.error("[GUI] MainWindow: CRITICAL - self.right_panel.inventory_panel not found during signal connection.")

        # Connect signals from CharacterSheetWidget (via right_panel)
        if hasattr(self.right_panel, 'character_sheet'):
            self.right_panel.character_sheet.item_unequip_from_slot_requested.connect(self._handle_item_unequip_from_slot_requested)
            self.right_panel.character_sheet.item_examine_requested.connect(self._handle_item_examine_requested) # Can reuse the same handler
            self.right_panel.character_sheet.item_drop_from_slot_requested.connect(self._handle_item_drop_from_slot_requested)
            logger.info("[GUI] MainWindow: Connected signals from CharacterSheetWidget (via right_panel).")
        else:
            logger.error("[GUI] MainWindow: CRITICAL - self.right_panel.character_sheet not found for signal connection.")


        if self.game_engine.state_manager.stats_manager:
            try:
                self.game_engine.state_manager.stats_manager.stats_changed.disconnect(self._handle_stats_update)
            except (TypeError, RuntimeError): pass 
            self.game_engine.state_manager.stats_manager.stats_changed.connect(self._handle_stats_update)
            logger.info("Connected StatsManager stats_changed signal to MainWindow handler.")
        else:
            logger.warning("StatsManager not available at signal connection time in MainWindow.")
        
        if hasattr(self.game_engine._combat_orchestrator, 'resume_combat_manager') and hasattr(self.game_engine, 'on_orchestrator_idle_and_combat_manager_resumed'):
             self.game_engine._combat_orchestrator.resume_combat_manager.connect(self.game_engine.on_orchestrator_idle_and_combat_manager_resumed)
             logger.info("Connected orchestrator's resume_combat_manager to engine's handler for post-closing-narrative.")
        else:
             logger.error("Could not connect orchestrator's resume signal to engine.")
             
    @Slot(dict)
    def _handle_stats_update(self, stats_data: dict):
        """Handle updates received directly from StatsManager."""
        logger.debug("Received stats update signal in MainWindow")
        state = self.game_engine.state_manager.current_state
        if state:
            # Update Character Sheet (Right Panel)
            # This ensures character sheet gets all data including combat status
            if self.right_panel and hasattr(self.right_panel, 'update_character'):
                self.right_panel.update_character(state.player) # Pass player state for full context
                logger.debug("Updated CharacterSheet (RightPanel) from stats signal.")

            # Update Combat Display if in Combat Mode
            if state.current_mode == InteractionMode.COMBAT:
                logger.debug("Updating CombatDisplay from stats signal")
                self.combat_display.update_display(state) 
            
            # Any other UI elements that need to react to general stats changes can be updated here.

    def _setup_stats_refresh(self):
        """Set up player command tracking and direct signal connections instead of timer-based refresh."""
        # Store the last command submitted by the player to prevent echo
        self._last_submitted_command: Optional[str] = None
        
        # We don't need timer-based stats refresh anymore since we'll use direct signal connections
    
    # The _refresh_stats method is removed since we're using direct signal connections now
    
    def _handle_tab_change(self, index):
        """Handle tab change event."""
        # Update the active tab content
        if index == 0:  # Character tab
            self.right_panel.update_character()
        elif index == 1:  # Inventory tab
            if self.game_engine.state_manager.current_state:
                # Get inventory manager instance
                from core.inventory import get_inventory_manager
                inventory_manager = get_inventory_manager()
                
                if inventory_manager:
                    self.right_panel.update_inventory(inventory_manager)
                else:
                    logger.warning("No inventory manager available")
        elif index == 2:  # Journal tab
            if self.game_engine.state_manager.current_state:
                # Check if journal data exists, create it if not
                if not hasattr(self.game_engine.state_manager.current_state, "journal"):
                    self.game_engine.state_manager.current_state.journal = {
                        "character": "",
                        "quests": {},
                        "notes": []
                    }
                
                self.right_panel.update_journal(
                    self.game_engine.state_manager.current_state.journal
                )
    
    # Define a worker for running commands in a separate thread
    class CommandWorker(QObject):
        finished = Signal()
        error = Signal(str)
        processing = Signal(bool)  # Signal to show/hide processing indicator
        
        def __init__(self, game_engine, command):
            super().__init__()
            self.game_engine = game_engine
            self.command = command
        
        def run(self):
            try:
                self.processing.emit(True)
                # Process input in the worker thread using the new InputRouter-based approach
                command_result = self.game_engine.process_input(self.command) # Original call
                
                # NEW: Process commands returned by LLM
                if command_result.data and "commands" in command_result.data:
                    llm_commands: List[Tuple[str, str]] = command_result.data["commands"]
                    if llm_commands:
                        logger.info(f"CommandWorker: Processing {len(llm_commands)} commands from LLM response: {llm_commands}")
                        # Ensure current_state is available
                        current_game_state = self.game_engine._state_manager.current_state
                        if not current_game_state:
                            logger.error("CommandWorker: Cannot process LLM commands, current_game_state is None.")
                        else:
                            for cmd, args_str in llm_commands:
                                try:
                                    # We need to call the central LLM command processor
                                    # command_handlers.process_llm_command takes (engine, command, args_list, game_state)
                                    # The args_str from the tuple is a single string, so wrap it in a list.
                                    logger.debug(f"CommandWorker: Executing LLM command '{cmd}' with args '{args_str}'")
                                    # Import locally if not already available or pass engine components if needed
                                    from core.game_flow.command_handlers import process_llm_command
                                    
                                    # process_llm_command itself might call engine._output, which triggers _update_ui.
                                    # This is fine, as _update_ui will reflect the state *after* each command.
                                    cmd_exec_result = process_llm_command(self.game_engine, cmd, [args_str], current_game_state)
                                    logger.info(f"CommandWorker: LLM command '{cmd}' execution result: {cmd_exec_result.message if cmd_exec_result else 'No result'}")
                                    if cmd_exec_result and not cmd_exec_result.is_success and cmd_exec_result.message:
                                        # If an LLM command itself fails, output its error message
                                        self.game_engine._output("system", f"Error processing internal command '{cmd}': {cmd_exec_result.message}")

                                except Exception as e_cmd:
                                    logger.error(f"CommandWorker: Error processing extracted LLM command '{cmd}': {e_cmd}", exc_info=True)
                                    self.game_engine._output("system", f"System error processing internal command '{cmd}'.")
                
                self.finished.emit()
            except Exception as e:
                logging.error(f"Error processing input: {e}", exc_info=True)
                self.error.emit(str(e))
            finally:
                self.processing.emit(False)
                
    def _process_command(self, command: str):
        """Process a command using the game engine in a separate thread."""
        if not command.strip():
            return
        
        # --- ECFA Change: Check if waiting for closing narrative ---
        if self.game_engine._waiting_for_closing_narrative_display:
            self.game_output.append_system_message("Please wait, concluding previous actions...", gradual=False)
            # Re-enable input field as this input is being ignored.
            if self.mode_stacked_widget.currentWidget() == self.narrative_view:
                self.narrative_command_input.setEnabled(True)
                self.narrative_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")
            else:
                self.combat_command_input.setEnabled(True)
                self.combat_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")
            return
        # --- End ECFA Change ---

        # Check if this command is UI-generated and should not be echoed as player input
        is_ui_generated_command = False
        try:
            parts = command.split(maxsplit=1)
            if len(parts) > 0 and parts[0].lower() in ["examine", "equip", "unequip", "drop", "use"]:
                if len(parts) > 1 and '-' in parts[1] and len(parts[1]) > 10: # Basic UUID-like check
                    is_ui_generated_command = True
        except Exception:
            pass

        # Echo player input only in narrative mode; suppress in combat mode
        try:
            state = self.game_engine.state_manager.current_state
            if not is_ui_generated_command and (not state or state.current_mode != InteractionMode.COMBAT):
                self.game_output.append_player_message(command)
            else:
                logger.info("Suppressing player echo in GameOutputWidget (combat mode or UI-generated command).")
        except Exception:
            if not is_ui_generated_command:
                self.game_output.append_player_message(command)
            
        self._last_submitted_command = command # Still store it to prevent potential echoes from engine if it's re-output
        
        active_command_input = self.narrative_command_input if self.mode_stacked_widget.currentWidget() == self.narrative_view else self.combat_command_input
        active_command_input.clear()
        active_command_input.setEnabled(False)
        active_command_input.command_edit.setPlaceholderText("Processing...")
        
        self.status_bar.showMessage("Processing command...", 0)
        
        self.worker_thread = QThread()
        self.worker = self.CommandWorker(self.game_engine, command)
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_command_processed)
        self.worker.error.connect(self._on_command_error)
        self.worker.processing.connect(self._set_processing_state) 
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        self.worker_thread.start()

    def _on_command_processed(self):
        """Handle completion of command processing."""
        # Update UI components
        self._update_ui()
        self.status_bar.clearMessage()
        self.narrative_command_input.setEnabled(True)
        self.combat_command_input.setEnabled(True)
        self.narrative_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")
        self.combat_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")
    
    def _on_command_error(self, error_msg):
        """Handle error in command processing."""
        self.game_output.append_system_message(f"Error: {error_msg}")
        self.status_bar.clearMessage()
        self.narrative_command_input.setEnabled(True)
        self.combat_command_input.setEnabled(True)
        self.narrative_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")
        self.combat_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")

    def _complete_if_same_event(self, event_id: str) -> None:
        """If the orchestrator is still waiting on this exact event, complete it.
        This guards against UI paths that failed to emit completion and prevents stalls.
        """
        try:
            orch = getattr(self.game_engine, '_combat_orchestrator', None)
            if orch is None:
                return
            # Only complete if we are still on the same event and waiting for visual
            if getattr(orch, 'is_processing_event', False) and getattr(orch, 'is_waiting_for_visual', False):
                current_id = getattr(orch, 'current_event_id_for_signals', None)
                if current_id == event_id:
                    logger.warning(f"Safety net: Completing UI_BAR_UPDATE event {event_id} to avoid stall.")
                    try:
                        orch._handle_visual_display_complete()
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"_complete_if_same_event guard failed: {e}")
    
    def _set_processing_state(self, is_processing):
        """Update UI to show processing state."""
        if is_processing:
            self.status_bar.showMessage("Processing command...")
            self.narrative_command_input.command_edit.setPlaceholderText("Processing...")
            self.combat_command_input.command_edit.setPlaceholderText("Processing...")
        else:
            self.status_bar.clearMessage()
            self.narrative_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")
            self.combat_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")
            self.narrative_command_input.setEnabled(True)
            self.combat_command_input.setEnabled(True)
    
    def _handle_game_output(self, role: str, content: str):
        """
        Handle non-orchestrated output from the game engine.
        Orchestrated events are handled by `process_orchestrated_display_event`.
        This method is now for general system messages or direct player echoes
        that are NOT part of the CombatOutputOrchestrator's flow.
        """
        logger.info(f"[LEGACY_OUTPUT] Received: role='{role}', content='{content[:200]}...'")
        
        # Special logging for reintroductory narrative debugging
        if role == "gm" and ("night air" in content.lower() or "find yourself" in content.lower()):
            logger.info(f"LIFECYCLE_DEBUG: _handle_game_output - This appears to be reintroductory narrative")
            logger.info(f"LIFECYCLE_DEBUG: Content length: {len(content)}")
            logger.info(f"LIFECYCLE_DEBUG: About to route to GameOutputWidget")
        
        # Prevent echoing the player's command if it somehow comes through this path
        # This also handles the case where UI-generated commands might be echoed by the engine.
        is_ui_generated_command_pattern = False
        try:
            parts = content.split(maxsplit=1)
            if len(parts) > 0 and parts[0].lower() in ["examine", "equip", "unequip", "drop", "use"]:
                if len(parts) > 1 and '-' in parts[1] and len(parts[1]) > 10:
                    is_ui_generated_command_pattern = True
        except: # pylint: disable=bare-except
            pass

        if role == "player" and ( (self._last_submitted_command is not None and content == self._last_submitted_command) or is_ui_generated_command_pattern ):
            logger.warning(f"Skipping potential echo of last command or UI-generated command via _handle_game_output: role='{role}', content='{content[:50]}...'")
            if self._last_submitted_command == content: # Clear only if it was an exact match of last submitted
                 self._last_submitted_command = None 
            return
            
        # Clear last submitted command if this output is different, to allow next player input to be echoed
        if self._last_submitted_command is not None and content != self._last_submitted_command:
             self._last_submitted_command = None

        # Route to GameOutputWidget. The append_text method now takes 'gradual'
        # For non-orchestrated output, usually display immediately (gradual=False)
        if role == "system":
            logger.info(f"LIFECYCLE_DEBUG: Routing system message to game_output.append_system_message")
            self.game_output.append_system_message(content, gradual=False)
        elif role == "gm":
            # General GM messages not part of orchestrated combat flow
            logger.info(f"LIFECYCLE_DEBUG: Routing GM message to game_output.append_gm_message with gradual=True")
            self.game_output.append_gm_message(content, gradual=True) # Allow GM narrative to be gradual
        elif role == "player":
            # Do not echo player messages to narrative output while in COMBAT
            try:
                state = self.game_engine.state_manager.current_state
                if state and state.current_mode == InteractionMode.COMBAT:
                    logger.info("Skipping player role output to GameOutputWidget because we're in COMBAT mode.")
                    return
            except Exception:
                pass
            # This path should be rare now, as player input is directly echoed then processed.
            # This will only catch player output if it's *not* the last submitted command.
            self.game_output.append_player_message(content, gradual=False)
        else:
            self.game_output.append_text(f"[{role}] {content}", gradual=False)
                      
        self._update_ui() # Still update UI for general status, etc.
        
    def _update_ui(self):
            """Update UI components based on the current game state."""
            state = self.game_engine.state_manager.current_state
            if not state:
                logger.debug("MainWindow._update_ui: No game state to update UI from.")
                self.status_bar.update_status(location="Not in game", game_time="", mode="N/A")
                if hasattr(self.right_panel, 'character_sheet') and self.right_panel.character_sheet: 
                    self.right_panel.character_sheet._clear_stat_displays() 
                
                inventory_manager_for_clear = get_inventory_manager() 
                logger.info(f"MainWindow._update_ui (no game state): Using InventoryManager instance ID: {getattr(inventory_manager_for_clear, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}")
                if hasattr(self.right_panel, 'update_inventory'): self.right_panel.update_inventory(inventory_manager_for_clear) 
                return

            game_over = False
            if state.current_mode == InteractionMode.COMBAT and state.combat_manager:
                if state.combat_manager.state == CombatState.PLAYER_DEFEAT:
                    game_over = True
            elif state.current_mode != InteractionMode.COMBAT: 
                try:
                    stats_manager = self.game_engine._stats_manager
                    if stats_manager:
                        from core.stats.stats_base import DerivedStatType
                        player_hp = stats_manager.get_current_stat_value(DerivedStatType.HEALTH)
                        if player_hp <= 0: game_over = True
                except Exception as e: logger.error(f"MainWindow._update_ui: Error checking player HP for game over: {e}", exc_info=True)

            if game_over and not hasattr(self, '_game_over_dialog_shown'):
                logger.info("MainWindow._update_ui: Player defeat detected. Showing Game Over dialog.")
                self._game_over_dialog_shown = True 
                self.narrative_command_input.setEnabled(False)
                self.combat_command_input.setEnabled(False)
                dialog = GameOverDialog(self)
                dialog.set_reason("You have been defeated!") 
                dialog.new_game_requested.connect(self._show_new_game_dialog)
                dialog.load_game_requested.connect(self._show_load_game_dialog)
                dialog.load_last_save_requested.connect(self._load_last_save)
                dialog.exec()
                self.narrative_command_input.setEnabled(True)
                self.combat_command_input.setEnabled(True)
                if hasattr(self, '_game_over_dialog_shown'): 
                    delattr(self, '_game_over_dialog_shown') 
                return 
            
            current_mode_enum = state.current_mode
            current_mode_name = current_mode_enum.name if hasattr(current_mode_enum, 'name') else str(current_mode_enum)
            logger.info(f"MainWindow._update_ui: Updating UI. Target mode: {current_mode_name}. Current QStackedWidget widget: {self.mode_stacked_widget.currentWidget().objectName() if self.mode_stacked_widget.currentWidget() else 'None'}")

            is_transitioning_to_combat = getattr(state, 'is_transitioning_to_combat', False)
            combat_narrative_buffer = getattr(state, 'combat_narrative_buffer', [])

            if current_mode_name == "COMBAT":
                view_switched_this_call = False
                if self.mode_stacked_widget.currentWidget() != self.combat_view:
                    logger.info(f"MainWindow._update_ui: Switching to combat_view.")
                    self.mode_stacked_widget.setCurrentWidget(self.combat_view)
                    view_switched_this_call = True
                else:
                    logger.info("MainWindow._update_ui: combat_view is already the current widget.")

                # Ensure combat_view is visible and updated, regardless of whether it was just switched.
                self.combat_view.setVisible(True) # Explicitly ensure visibility
                self.combat_view.update() # Request a repaint of the combat_view
                self.mode_stacked_widget.update() # Request a repaint of the QStackedWidget
                
                if view_switched_this_call:
                    current_widget_after_switch = self.mode_stacked_widget.currentWidget()
                    if current_widget_after_switch == self.combat_view:
                        logger.info(f"MainWindow._update_ui: Successfully set combat_view as current widget in QStackedWidget.")
                    else:
                        logger.error(f"MainWindow._update_ui: FAILED to set combat_view. Current widget is still: {current_widget_after_switch.objectName() if current_widget_after_switch else 'None'}")
                    
                    if hasattr(self.right_panel, 'tab_widget'): 
                        self.right_panel.tab_widget.setCurrentIndex(0)

                if is_transitioning_to_combat and combat_narrative_buffer:
                    logger.info(f"MainWindow._update_ui: Combat transition: Queuing {len(combat_narrative_buffer)} buffered messages with Orchestrator.")
                    from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget 
                    
                    buffer_event = DisplayEvent(
                        type=DisplayEventType.BUFFER_FLUSH,
                        content=list(combat_narrative_buffer), 
                        role="gm", 
                        target_display=DisplayTarget.COMBAT_LOG,
                        gradual_visual_display=True,
                        tts_eligible=True
                    )
                    self.game_engine._combat_orchestrator.add_event_to_queue(buffer_event)
                    
                    state.combat_narrative_buffer.clear() 
                    state.is_transitioning_to_combat = False 
                    logger.debug("MainWindow._update_ui: Cleared combat_narrative_buffer and reset is_transitioning_to_combat flag.")
                
                # Call combat_display.update_display to refresh its content
                logger.info("MainWindow._update_ui (COMBAT mode): Calling combat_display.update_display.")
                self.combat_display.update_display(state) 
                
                if state.player and hasattr(self.right_panel, 'update_character'): self.right_panel.update_character(state.player) 

                combat_manager = state.combat_manager 
                if view_switched_this_call and combat_manager and combat_manager.current_step == CombatStep.STARTING_COMBAT:
                    if not self.game_engine._combat_orchestrator.is_processing_event and not self.game_engine._combat_orchestrator.event_queue:
                        logger.info(f"MainWindow._update_ui (view switched to COMBAT this call) triggering initial CombatManager.process_combat_step() as Orchestrator is idle.")
                        QTimer.singleShot(10, lambda cm=combat_manager, eng=self.game_engine: cm.process_combat_step(eng))
                elif combat_manager and combat_manager.current_step == CombatStep.AWAITING_PLAYER_INPUT:
                     logger.debug("MainWindow._update_ui: CombatManager is AWAITING_PLAYER_INPUT. No nudge needed.")


            else: # Not in Combat mode
                if self.mode_stacked_widget.currentWidget() != self.narrative_view:
                    logger.info(f"MainWindow._update_ui: Switching to narrative_view.")
                    self.mode_stacked_widget.setCurrentWidget(self.narrative_view)
                    current_widget_after_switch = self.mode_stacked_widget.currentWidget()
                    if current_widget_after_switch == self.narrative_view:
                        logger.info(f"MainWindow._update_ui: Successfully set narrative_view as current widget.")
                    else:
                        logger.error(f"MainWindow._update_ui: FAILED to set narrative_view. Current widget is still: {current_widget_after_switch.objectName() if current_widget_after_switch else 'None'}")
                
                self.narrative_view.setVisible(True) # Ensure narrative view is visible
                self.narrative_view.update()
                self.mode_stacked_widget.update()


                if is_transitioning_to_combat: 
                    logger.warning("MainWindow._update_ui: Was transitioning to combat, but now in narrative. Resetting transition flag.")
                    state.is_transitioning_to_combat = False 
                    state.combat_narrative_buffer.clear()


            if current_mode_enum == InteractionMode.TRADE and \
               (self._previous_mode is None or self._previous_mode != InteractionMode.TRADE):
                partner_id = getattr(state, 'current_trade_partner_id', None)
                partner_name = "Unknown NPC"
                if partner_id and state.world: 
                    partner_obj = getattr(state.world, 'get_character', lambda pid: None)(partner_id)
                    if partner_obj: partner_name = getattr(partner_obj, 'name', "Unknown NPC")
                self.game_output.append_system_message(f"Trade started with {partner_name}.", gradual=False)

            self._previous_mode = current_mode_enum
            if state.player and hasattr(self.right_panel, 'update_character'): self.right_panel.update_character(state.player)

            inventory_manager = get_inventory_manager() 
            logger.info(f"MainWindow._update_ui: Using InventoryManager instance ID: {getattr(inventory_manager, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}")
            if hasattr(self.right_panel, 'update_inventory'): self.right_panel.update_inventory(inventory_manager)
            
            journal_data = getattr(state, "journal", None)
            if journal_data is not None and hasattr(self.right_panel, 'update_journal'): self.right_panel.update_journal(journal_data)

            self.status_bar.update_status(
                location=getattr(state.player, 'current_location', 'Unknown') if state.player else 'N/A',
                game_time=getattr(state.world, 'time_of_day', ''),
                mode=current_mode_name 
            )

    def _show_game_panels_for_loaded_game(self):
        """Make game panels visible and enabled when loading a saved game."""
        self._initialize_panel_effects()
        
        # Make center widget visible and enabled
        self.center_widget.setVisible(True)
        self.center_widget.setEnabled(True)
        if hasattr(self, 'center_opacity_effect'):
            self.center_opacity_effect.setOpacity(1.0)
        
        # Make right panel visible and enabled
        self.right_panel.setVisible(True)
        self.right_panel.setEnabled(True)
        if hasattr(self, 'right_panel_opacity_effect'):
            self.right_panel_opacity_effect.setOpacity(1.0)
        # Ensure right panel is in expanded state for loaded games
        if not self.right_panel.isExpanded():
            self.right_panel.setExpanded(True)
        
        # Make status bar visible and enabled
        self.status_bar.setVisible(True)
        self.status_bar.setEnabled(True)
        if hasattr(self, 'status_bar_opacity_effect'):
            self.status_bar_opacity_effect.setOpacity(1.0)
        
        logger.info("Game panels made visible and enabled for loaded game")

    def _show_new_game_dialog(self):
        """Show dialog for creating a new game."""
        from gui.dialogs.character_creation_dialog import CharacterCreationDialog
        dialog = CharacterCreationDialog(self)
        if dialog.exec():
            character_data = dialog.get_character_data()
            if not character_data: 
                logger.warning("New game character creation cancelled or failed validation in dialog.")
                return

            logger.info(f"Character data received from dialog. Preparing to start panel animations.")
            
            # Start panel animations, passing character_data to be used after animation
            # This will eventually call _start_game_flow_after_animation
            self._start_panel_animations(character_data)
            
            # DO NOT start game engine here. It will be started by _start_game_flow_after_animation.
        else:
            logger.info("New game dialog cancelled by user.")

    def _show_save_game_dialog(self):
        """Show dialog for saving the game."""
        from gui.dialogs.save_game_dialog import SaveGameDialog
        dialog = SaveGameDialog(self)
        if dialog.exec():
            # Save the game with the provided name
            save_name = dialog.save_name_edit.text()
            # Capture current combat log HTML snapshot if in COMBAT
            try:
                state = self.game_engine.state_manager.current_state
                if state and state.current_mode.name == 'COMBAT' and state.combat_manager:
                    # Ensure current Combat Log HTML is stored for save
                    html_snapshot = ""
                    if hasattr(self, 'combat_display') and hasattr(self.combat_display, 'log_text'):
                        html_snapshot = self.combat_display.log_text.toHtml()
                    state.combat_manager.display_log_html = html_snapshot or state.combat_manager.display_log_html
            except Exception as e:
                logger.warning(f"Failed to snapshot Combat Log HTML before save: {e}")
            saved_path = self.game_engine.save_game(save_name)
            
            if saved_path:
                QMessageBox.information(
                    self, 
                    "Game Saved", 
                    f"Game saved successfully to {saved_path}"
                )
    
    def _show_load_game_dialog(self):
        """Show dialog for loading a saved game."""
        from gui.dialogs.load_game_dialog import LoadGameDialog
        dialog = LoadGameDialog(self)
        if dialog.exec():
            # Load the selected save
            save_filename = dialog.selected_save
            if save_filename:
                # Pre-clear orchestrator and displays before loading save to preserve new outputs
                try:
                    if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator:
                        self.game_engine._combat_orchestrator.clear_queue_and_reset_flags()
                except Exception as e:
                    logger.warning(f"Failed to clear orchestrator state before load: {e}")
                try:
                    self.game_output.clear()
                except Exception as e:
                    logger.warning(f"Failed to clear GameOutputWidget before load: {e}")
                try:
                    self.combat_display.clear_display()
                except Exception as e:
                    logger.warning(f"Failed to clear CombatDisplay before load: {e}")
                self._last_submitted_command = None
                loaded_state = self.game_engine.load_game(save_filename)
                
                if loaded_state:
                    # Clear right panel tabs to avoid stale data before repopulating
                    try:
                        if hasattr(self.right_panel, 'journal_panel'):
                            self.right_panel.journal_panel.clear_all()
                        if hasattr(self.right_panel, 'inventory_panel') and hasattr(self.right_panel.inventory_panel, 'clear'):
                            # If a clear method exists use it; otherwise update_inventory will refresh
                            try:
                                self.right_panel.inventory_panel.clear()
                            except Exception:
                                pass
                        if hasattr(self.right_panel, 'character_sheet') and hasattr(self.right_panel.character_sheet, '_clear_stat_displays'):
                            self.right_panel.character_sheet._clear_stat_displays()
                    except Exception as e:
                        logger.warning(f"Failed to clear right panel widgets prior to load repopulation: {e}")

                    # Ensure journal exists
                    if not hasattr(self.game_engine.state_manager.current_state, "journal"):
                        self.game_engine.state_manager.current_state.journal = {
                            "character": self.game_engine.state_manager.current_state.player.background,
                            "quests": {},
                            "notes": []
                        }
                    
                    # Ensure the stats manager is fully initialized
                    self.game_engine.state_manager.ensure_stats_manager_initialized()

                    # Make game panels visible and enabled for loaded games
                    self._show_game_panels_for_loaded_game()
                    
                    # Update UI
                    self._update_ui()

                    # Bind orchestrator to loaded CombatManager if save is in COMBAT
                    try:
                        state = self.game_engine.state_manager.current_state
                        if state and state.current_mode.name == 'COMBAT' and getattr(state, 'combat_manager', None):
                            if hasattr(self.game_engine, '_combat_orchestrator'):
                                self.game_engine._combat_orchestrator.set_combat_manager(state.combat_manager)
                                logger.info("Bound loaded CombatManager to Orchestrator in MainWindow (load dialog).")
                    except Exception as e:
                        logger.warning(f"Failed to bind CombatManager after load in MainWindow: {e}")

                    # Emit consolidated stats_changed to refresh UI listeners
                    try:
                        sm = self.game_engine.state_manager.stats_manager
                        if sm and hasattr(sm, 'stats_changed'):
                            sm.stats_changed.emit(sm.get_all_stats())
                            logger.info("Emitted consolidated stats_changed after load to refresh UI.")
                    except Exception as e:
                        logger.warning(f"Failed to emit stats_changed after load: {e}")
                    
                    # Force character sheet update with current player
                    if self.game_engine.state_manager.current_state and self.game_engine.state_manager.current_state.player:
                        self.right_panel.update_character(self.game_engine.state_manager.current_state.player)
                else:
                    QMessageBox.warning(
                        self, 
                        "Load Failed", 
                        f"Failed to load game from {save_filename}"
                    )
    
    def _show_settings_dialog(self):
        """Show dialog for game settings."""
        logger.info("Attempting to show SettingsDialog...") # Log entry
        from gui.dialogs.settings.settings_dialog import SettingsDialog
        logger.info("Imported SettingsDialog.") # Log import success

        try:
            dialog = SettingsDialog(self)
            logger.info("SettingsDialog instance created.") # Log instance creation
        except Exception as e:
            logger.error(f"Error INSTANTIATING SettingsDialog: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to create settings dialog:\n{e}")
            return

        # Connect the background preview signal from the BackgroundTab within the SettingsDialog
        connected = False
        if hasattr(dialog, 'background_tab') and hasattr(dialog.background_tab, 'preview_background_changed'):
            try:
                # Connect the signal that now emits the full filename
                dialog.background_tab.preview_background_changed.connect(self.update_background)
                connected = True
                logger.info("Connected background_preview_changed signal for live preview.")
            except Exception as e:
                 logger.error(f"Error connecting background_preview_changed signal: {e}")
        else:
            logger.warning("Could not find background_tab or preview_background_changed signal in SettingsDialog.")

        saved = False
        try:
            logger.info("Attempting to execute SettingsDialog...") # Log before exec
            # Execute the dialog
            result = dialog.exec()
            logger.info(f"SettingsDialog execution finished with result: {result}") # Log after exec
            if result == QDialog.Accepted: # Check result code
                saved = True
        except Exception as e:
             logger.error(f"Error EXECUTING SettingsDialog: {e}", exc_info=True)
             QMessageBox.critical(self, "Error", f"Failed to execute settings dialog:\n{e}")
        finally:
            # Disconnect signal after dialog is closed
            if connected:
                try:
                    dialog.background_tab.preview_background_changed.disconnect(self.update_background)
                    logger.info("Disconnected background_preview_changed signal.")
                except Exception as e:
                     logger.warning(f"Failed to disconnect background_preview_changed signal: {e}")

        if saved: # Process saved settings only if dialog was accepted
            logger.info("Settings dialog accepted. Applying settings...") # Log applying settings
            # Apply new settings
            settings = SettingsDialog.get_settings() # Re-fetch to be sure

            # Update dev controls visibility immediately after settings change
            try:
                q_settings = QSettings("RPGGame", "Settings")
                dev_enabled = q_settings.value("dev/enabled", False, type=bool)
                if hasattr(self, 'combat_display') and hasattr(self.combat_display, 'dev_controls_container'):
                    self.combat_display.dev_controls_container.setVisible(bool(dev_enabled))
                # Also toggle orchestrator step mode to match dev setting default (off until user toggles)
                if hasattr(self.game_engine, '_combat_orchestrator') and hasattr(self.game_engine._combat_orchestrator, 'toggle_dev_step_mode'):
                    self.game_engine._combat_orchestrator.toggle_dev_step_mode(False)
            except Exception as e:
                logger.warning(f"Failed to update dev controls visibility post settings: {e}")

            # Update resolution if needed
            resolution = settings["display"]["windowed_size"] # Use windowed_size now
            current_state = settings["display"]["window_state"]

            logger.info(f"Applying settings - State: {current_state}, Windowed Size: {resolution}")

            # Apply window state changes
            if current_state == "fullscreen":
                if not self.isFullScreen(): self.showFullScreen()
            elif current_state == "maximized":
                 if not self.isMaximized(): self.showMaximized()
            else: # windowed
                 if self.isFullScreen() or self.isMaximized(): self.showNormal()
                 # Check if size actually needs changing
                 if QSize(resolution[0], resolution[1]) != self.size():
                     self.resize(resolution[0], resolution[1]) # Use tuple values

            # Update styling (includes non-background styles)
            self._update_styling()

            # Explicitly apply the *saved* background setting after dialog closes
            q_settings = QSettings("RPGGame", "Settings")
            saved_filename = q_settings.value("style/background_filename", None)
            if saved_filename:
                 logger.info(f"Applying saved background from QSettings: {saved_filename}")
                 self.update_background(saved_filename)
            else:
                 logger.warning("Could not read saved background filename after settings dialog closed.")

            # Update UI based on new settings (e.g., status bar, panels)
            # self._update_ui() # Update UI can be complex, might re-trigger things, maybe call specific updates?
            # Let's rely on the window state change and styling update for now.

            # Reload autosave settings (turn-based) in the engine
            try:
                if hasattr(self.game_engine, 'reload_autosave_settings'):
                    self.game_engine.reload_autosave_settings()
            except Exception as e:
                logger.warning(f"Failed to reload autosave settings after saving: {e}")

            # Show confirmation
            self.game_output.append_system_message("Settings saved successfully.")
            logger.info("Settings applied successfully.")
        else:
             logger.info("Settings dialog cancelled or closed without saving.")
    
    def update_background(self, filename: Optional[str]):
        """Load and apply a new background image or GIF to the main window."""
        logger.info(f"Attempting to update background to: {filename}")

        # Stop and clear any existing movie/pixmap
        current_movie = self.background_label.movie()
        if current_movie:
            current_movie.stop()
            self.background_label.setMovie(None)
        self.background_label.setPixmap(QPixmap())
        # Reset palette to default in case previous was PNG
        self.background_container.setAutoFillBackground(False) # Important! Don't let palette fill container
        self.background_label.setProperty("current_background", None) # Store current bg filename

        if not filename:
            logger.warning("No background filename provided, clearing background.")
            # Optionally set a default color on the label if needed
            self.background_label.setStyleSheet("background-color: #1E1E1E;")
            return

        name, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        if ext_lower == ".png":
            pixmap = self.resource_manager.get_background_pixmap(name)
            if not pixmap.isNull():
                self.background_label.setPixmap(pixmap) # Label scales content
                self.background_label.setStyleSheet("") # Clear any fallback color
                self.background_label.setProperty("current_background", filename)
                logger.info(f"Successfully applied PNG background: {filename}")
            else:
                logger.warning(f"Failed to load PNG background '{filename}', applying fallback color.")
                self.background_label.setStyleSheet("background-color: #1E1E1E;")

        elif ext_lower == ".gif":
            movie = self.resource_manager.get_background_movie(name)
            if movie.isValid():
                self.background_label.setMovie(movie)
                movie.start()
                self.background_label.setStyleSheet("") # Clear any fallback color
                self.background_label.setProperty("current_background", filename)
                logger.info(f"Successfully applied GIF background: {filename}")
            else:
                logger.warning(f"Failed to load GIF background '{filename}', applying fallback color.")
                self.background_label.setStyleSheet("background-color: #1E1E1E;")
        else:
            logger.error(f"Unsupported background file type: {filename}")
            self.background_label.setStyleSheet("background-color: #1E1E1E;") # Fallback color

    def _load_and_apply_initial_background(self):
        """Load the saved background filename from settings and apply it.
        If no valid setting is found, use the first available background alphabetically.
        """
        settings = QSettings("RPGGame", "Settings")
        # Read the full filename setting
        saved_filename = settings.value("style/background_filename", None)

        available_backgrounds = self.resource_manager.list_background_names() # Gets list of (name, ext)
        final_filename = None

        # Check if saved filename exists in the available list
        if saved_filename:
            found = False
            for name, ext in available_backgrounds:
                if f"{name}{ext}" == saved_filename:
                    final_filename = saved_filename
                    found = True
                    break
            if found:
                logger.info(f"Using saved background: {final_filename}")
            else:
                logger.warning(f"Saved background '{saved_filename}' not found in available list.")
                saved_filename = None # Treat as not found

        # If no valid saved name, use the first available background
        if not final_filename and available_backgrounds:
            first_name, first_ext = available_backgrounds[0] # Use first alphabetically
            final_filename = f"{first_name}{first_ext}"
            logger.info(f"No valid saved background found. Using first available: {final_filename}")
        elif not final_filename:
             logger.warning("No saved background setting found and no backgrounds available in images/gui/background/. Applying fallback color.")
             # update_background will handle the fallback color if name is None

        self.update_background(final_filename) # Pass None if no background is available

    def _update_styling(self):
        """Update UI styling based on saved settings."""
        # Update game output styling and formats
        self.game_output._update_formats()
        self.game_output._setup_background()
        
        # Get settings for command input styling
        settings = QSettings("RPGGame", "Settings")
        
        # Update command input styling
        user_input_font_family = settings.value("style/user_input_font_family", "Garamond")
        user_input_font_size = int(settings.value("style/user_input_font_size", 14))
        user_input_font_color = settings.value("style/user_input_font_color", "#0d47a1")
        
        # Create a dark frame around command input and enter button
        # Get transparency setting
        input_opacity = int(settings.value("style/input_opacity", 100))
        opacity_percent = input_opacity / 100.0
        
        # Calculate RGB values for the background
        bg_color_obj = QColor("#333333")
        r, g, b = bg_color_obj.red(), bg_color_obj.green(), bg_color_obj.blue()
        
        # Common style for command inputs
        command_input_style = f"""
            CommandInputWidget {{
                background-color: rgba({r}, {g}, {b}, {opacity_percent});
                border-radius: 10px;
                padding: 5px;
                border: 2px solid #333333; /* Same as left/right panels */
            }}
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.7);
                color: {user_input_font_color};
                border: 1px solid #c4b59d;
                border-radius: 4px;
                padding: 8px;
                font-family: '{user_input_font_family}';
                font-size: {user_input_font_size}pt;
                margin-left: 5px;
                margin-right: 5px;
            }}
        """
        
        # Apply style to both command inputs
        self.narrative_command_input.setStyleSheet(command_input_style)
        self.combat_command_input.setStyleSheet(command_input_style)
    
    def _show_llm_settings_dialog(self):
        """Show dialog for LLM settings."""
        dialog = LLMSettingsDialog(self)
        dialog.settings_saved.connect(self._on_llm_settings_saved)
        dialog.exec()
    
    def _on_llm_settings_saved(self):
        """Handle LLM settings saved event."""
        # Update UI elements that depend on LLM settings
        is_llm_enabled = self.game_engine._use_llm
        
        # Add UI feedback to show LLM status when explicitly changed through settings
        if is_llm_enabled:
            self.game_output.append_system_message("LLM processing is now enabled.")
        else:
            self.game_output.append_system_message("LLM processing is now disabled.")

    # Removed _delayed_character_update method - we now use direct update instead of timers
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Ask for confirmation
        reply = QMessageBox.question(
            self, 
            "Exit Game", 
            "Are you sure you want to exit? Unsaved progress will be lost.",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Stop the game engine
            self.game_engine.stop()

            # Stop background movie if playing
            bg_movie = self.background_label.movie()
            if bg_movie:
                bg_movie.stop()

            event.accept()
        else:
            event.ignore()

    def resizeEvent(self, event):
        """Handle window resize event to keep background and content sized correctly."""
        super().resizeEvent(event)
        # Keep background label and content widget filling the container
        if hasattr(self, 'background_label'): # Check if widgets exist yet
             self.background_label.setGeometry(0, 0, event.size().width(), event.size().height())
        if hasattr(self, 'main_content_widget'):
             self.main_content_widget.setGeometry(0, 0, event.size().width(), event.size().height())

    def _load_last_save(self):
        """Loads the most recent non-auto save file."""
        logger.info("Attempting to load last save.")
        from core.utils.save_manager import SaveManager # Local import
        save_manager = SaveManager()
        try:
            # Get recent saves, excluding backups and auto-saves initially
            saves = save_manager.get_recent_saves(count=10, include_backups=False) # Get a few recent ones
            last_manual_save = None
            for save in saves:
                 if not save.auto_save:
                      last_manual_save = save
                      break # Found the most recent manual save

            if last_manual_save:
                save_filename = f"{last_manual_save.save_id}/{SaveManager.STATE_FILENAME}" # Need correct path format if StateManager expects full path or just ID
                save_id = last_manual_save.save_id # Use the ID for loading
                logger.info(f"Found last manual save: {last_manual_save.save_name} (ID: {save_id})")

                # Clear any previous UI content and pending orchestrator events BEFORE loading
                try:
                    if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator:
                        self.game_engine._combat_orchestrator.clear_queue_and_reset_flags()
                except Exception as e:
                    logger.warning(f"Failed to clear orchestrator state before load: {e}")
                
                try:
                    self.game_output.clear()
                except Exception as e:
                    logger.warning(f"Failed to clear GameOutputWidget before load: {e}")
                
                try:
                    self.combat_display.clear_display()
                except Exception as e:
                    logger.warning(f"Failed to clear CombatDisplay before load: {e}")
                
                # Also clear right panel content to avoid stale state
                try:
                    if hasattr(self.right_panel, 'journal_panel'):
                        self.right_panel.journal_panel.clear_all()
                    if hasattr(self.right_panel, 'inventory_panel') and hasattr(self.right_panel.inventory_panel, 'clear'):
                        try:
                            self.right_panel.inventory_panel.clear()
                        except Exception:
                            pass
                    if hasattr(self.right_panel, 'character_sheet') and hasattr(self.right_panel.character_sheet, '_clear_stat_displays'):
                        self.right_panel.character_sheet._clear_stat_displays()
                except Exception as e:
                    logger.warning(f"Failed to clear right panel widgets before load: {e}")
                
                self._last_submitted_command = None
                
                # Call engine's load_game method
                loaded_state = self.game_engine.load_game(save_id) # Pass save_id

                if loaded_state:
                    # Ensure journal exists (similar to _show_load_game_dialog)
                    if not hasattr(self.game_engine.state_manager.current_state, "journal"):
                        self.game_engine.state_manager.current_state.journal = {
                            "character": getattr(self.game_engine.state_manager.current_state.player, 'background', ''),
                            "quests": {},
                            "notes": []
                        }
                    self.game_engine.state_manager.ensure_stats_manager_initialized()

                    # Make game panels visible and enabled for loaded games
                    self._show_game_panels_for_loaded_game()
                    
                    self._update_ui() # Update UI after load

                    # Bind orchestrator to loaded CombatManager if save is in COMBAT
                    try:
                        state = self.game_engine.state_manager.current_state
                        if state and state.current_mode.name == 'COMBAT' and getattr(state, 'combat_manager', None):
                            if hasattr(self.game_engine, '_combat_orchestrator'):
                                self.game_engine._combat_orchestrator.set_combat_manager(state.combat_manager)
                                logger.info("Bound loaded CombatManager to Orchestrator in MainWindow (load last save).")
                    except Exception as e:
                        logger.warning(f"Failed to bind CombatManager after loading last save: {e}")

                    # Emit consolidated stats_changed to refresh UI listeners
                    try:
                        sm = self.game_engine.state_manager.stats_manager
                        if sm and hasattr(sm, 'stats_changed'):
                            sm.stats_changed.emit(sm.get_all_stats())
                            logger.info("Emitted consolidated stats_changed after loading last save.")
                    except Exception as e:
                        logger.warning(f"Failed to emit stats_changed after loading last save: {e}")

                    if self.game_engine.state_manager.current_state and self.game_engine.state_manager.current_state.player:
                        self.right_panel.update_character(self.game_engine.state_manager.current_state.player)
                    self.game_output.append_system_message(f"Loaded last save: {last_manual_save.save_name}")
                else:
                    QMessageBox.warning(self, "Load Failed", f"Failed to load last save: {last_manual_save.save_name}")
                    # If last save fails, open the regular load dialog
                    self._show_load_game_dialog()
            else:
                logger.warning("No manual saves found to load.")
                QMessageBox.information(self, "No Last Save", "No manual save file found. Please load manually or start a new game.")
                # Open the regular load dialog as fallback
                self._show_load_game_dialog()
        except Exception as e:
            logger.error(f"Error loading last save: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred while trying to load the last save:\n{e}")
            self._show_load_game_dialog() # Fallback to regular load dialog

    @Slot(object) 
    def process_orchestrated_display_event(self, event):
        """
        Handles DisplayEvents routed from the CombatOutputOrchestrator via the GameEngine.
        This method sends the content to the appropriate UI display widget.
        """
        from core.orchestration.events import DisplayEvent, DisplayTarget, DisplayEventType 
        if not isinstance(event, DisplayEvent):
            logger.error(f"MainWindow received non-DisplayEvent object: {type(event)}")
            if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator.is_waiting_for_visual:
                self.game_engine._combat_orchestrator._handle_visual_display_complete()
            return

        logger.info(f"MainWindow processing orchestrated event: {event}")
        state = self.game_engine.state_manager.current_state

        target_widget = None
        # Determine primary target widget
        if event.target_display == DisplayTarget.COMBAT_LOG:
            target_widget = self.combat_display
        elif event.target_display == DisplayTarget.MAIN_GAME_OUTPUT:
            target_widget = self.game_output
            # Ensure the narrative view is visible if routing to MAIN_GAME_OUTPUT AND we are not currently in COMBAT mode
            try:
                state_for_switch = self.game_engine.state_manager.current_state
                if state_for_switch and state_for_switch.current_mode != InteractionMode.COMBAT:
                    if self.mode_stacked_widget.currentWidget() != self.narrative_view:
                        logger.info("MainWindow: MAIN_GAME_OUTPUT event and current mode not COMBAT. Switching to narrative_view.")
                        self.mode_stacked_widget.setCurrentWidget(self.narrative_view)
                        self.narrative_view.setVisible(True)
                        self.mode_stacked_widget.update()
            except Exception as e:
                logger.warning(f"Failed conditional switch to narrative_view on MAIN_GAME_OUTPUT event: {e}")
        else: # Default based on mode if target not explicit
            if state and state.current_mode == InteractionMode.COMBAT:
                target_widget = self.combat_display
            else:
                target_widget = self.game_output
        
        if not target_widget and event.type not in [DisplayEventType.TURN_ORDER_UPDATE, DisplayEventType.UI_BAR_UPDATE_PHASE1, DisplayEventType.UI_BAR_UPDATE_PHASE2]: # These might not have a primary text widget
            logger.error(f"No target widget found for orchestrated event: {event} and not a special UI event.")
            if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator.is_waiting_for_visual:
                self.game_engine._combat_orchestrator._handle_visual_display_complete() 
            return

        # Handle event types
        if event.type == DisplayEventType.BUFFER_FLUSH:
            if isinstance(event.content, list) and target_widget == self.combat_display:
                # New: perfect fidelity replay with role per line, batched to a single completion
                try:
                    # Suppress per-line completion during batch
                    if hasattr(self.combat_display, '_suppress_visual_complete'):
                        self.combat_display._suppress_visual_complete = True
                    for item in event.content:
                        if isinstance(item, dict) and 'text' in item:
                            line_text = str(item.get('text', ''))
                            line_role = item.get('role', event.role or 'gm')
                            if line_text:
                                self.combat_display.append_orchestrated_event_content(line_text, line_role, is_gradual=False)
                        else:
                            # Fallback: treat as plain string
                            self.combat_display.append_orchestrated_event_content(str(item), event.role or 'gm', is_gradual=False)
                except Exception as e:
                    logger.error(f"Error during BUFFER_FLUSH replay: {e}", exc_info=True)
                finally:
                    if hasattr(self.combat_display, '_suppress_visual_complete'):
                        self.combat_display._suppress_visual_complete = False
                # Signal completion once for the whole batch (async to avoid re-entrancy)
                if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator.is_waiting_for_visual:
                    try:
                        QTimer.singleShot(0, self.game_engine._combat_orchestrator._handle_visual_display_complete)
                    except Exception:
                        # Fallback to direct call if QTimer not available
                        self.game_engine._combat_orchestrator._handle_visual_display_complete()
            else:
                logger.error(f"Invalid content type or target for BUFFER_FLUSH event: {type(event.content)}, target: {target_widget}")
                if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator.is_waiting_for_visual:
                    self.game_engine._combat_orchestrator._handle_visual_display_complete()

        elif event.type == DisplayEventType.UI_BAR_UPDATE_PHASE1 or event.type == DisplayEventType.UI_BAR_UPDATE_PHASE2:
            logger.debug(f"Handling UI_BAR_UPDATE event: {event.metadata}")
            entity_id = event.metadata.get("entity_id")
            bar_type = event.metadata.get("bar_type") 
            
            # Diagnostic: player mapping and widget presence
            player_id_diag = None
            state_for_diag = self.game_engine.state_manager.current_state
            if state_for_diag and state_for_diag.player:
                player_id_diag = getattr(state_for_diag.player, 'id', getattr(state_for_diag.player, 'stats_manager_id', None))
            logger.info(f"UI_BAR_UPDATE {event.type.name}: bar={bar_type}, entity={entity_id}, is_player={(entity_id==player_id_diag)}")
            
            # Update CharacterSheet if it's the player (do this first to align visual timing with CombatDisplay)
            player_id = None
            if state and state.player:
                 player_id = getattr(state.player, 'id', getattr(state.player, 'stats_manager_id', None))

            player_bar_updated = False
            if entity_id == player_id and self.right_panel and self.right_panel.character_sheet:
                try:
                    if event.type == DisplayEventType.UI_BAR_UPDATE_PHASE1:
                        self.right_panel.character_sheet.player_resource_bar_update_phase1(bar_type, event.metadata)
                        player_bar_updated = True
                    elif event.type == DisplayEventType.UI_BAR_UPDATE_PHASE2:
                        self.right_panel.character_sheet.player_resource_bar_update_phase2(bar_type, event.metadata)
                        player_bar_updated = True
                except Exception as e:
                    logger.error(f"Error updating CharacterSheet for player bar update: {e}", exc_info=True)

            # Update CombatEntityWidget in CombatDisplay
            entity_widget_combat_display = self.combat_display.entity_widgets.get(entity_id)
            logger.info(f"CombatDisplay widget exists for entity? {bool(entity_widget_combat_display)}")
            animation_invoked = False
            if entity_widget_combat_display:
                method_name = f"animate_{event.type.name.lower()}"
                try:
                    if hasattr(entity_widget_combat_display, method_name):
                        getattr(entity_widget_combat_display, method_name)(event.metadata)
                        animation_invoked = True
                    else:
                        logger.warning(f"CombatEntityWidget missing method {method_name} for entity {entity_id}. Will complete event to prevent stall.")
                except Exception as e:
                    logger.error(f"Error invoking {method_name} on CombatEntityWidget for entity {entity_id}: {e}", exc_info=True)

            # If no animation method was invoked, or if widget is missing, proactively complete to avoid stall
            if (not entity_widget_combat_display) or (not animation_invoked):
                 if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator.is_waiting_for_visual:
                    try:
                        QTimer.singleShot(0, self.game_engine._combat_orchestrator._handle_visual_display_complete)
                    except Exception:
                        self.game_engine._combat_orchestrator._handle_visual_display_complete()
                 if not entity_widget_combat_display:
                     logger.warning(f"UI_BAR_UPDATE for entity {entity_id} but no CombatEntityWidget found. Signalled completion to avoid stall.")
                 else:
                     logger.info(f"UI_BAR_UPDATE fallback completion invoked (no animation) for entity {entity_id}.")

            # Final safety net: if the orchestrator is still processing this same event shortly after, complete it
            try:
                QTimer.singleShot(10, lambda ev_id=event.event_id: self._complete_if_same_event(ev_id))
            except Exception:
                pass


        elif event.type == DisplayEventType.TURN_ORDER_UPDATE:
            if self.right_panel and self.right_panel.character_sheet and hasattr(self.right_panel.character_sheet, 'handle_turn_order_update'):
                self.right_panel.character_sheet.handle_turn_order_update(event.content) # event.content is the data dict
            # This event is primarily for CharacterSheet, CombatDisplay updates turn order itself.
            # Signal completion immediately as CharacterSheet update is synchronous.
            if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator.is_waiting_for_visual:
                 QTimer.singleShot(0, self.game_engine._combat_orchestrator._handle_visual_display_complete)


        elif event.type == DisplayEventType.COMBAT_LOG_SET_HTML:
            # Directly set Combat Log HTML for instant rehydration
            try:
                if target_widget == self.combat_display and isinstance(event.content, str):
                    # Freeze updates for fast set
                    self.combat_display.log_text.setUpdatesEnabled(False)
                    self.combat_display.log_text.setHtml(event.content)
                    # Move caret to end and ensure visible using correct API
                    self.combat_display.log_text.moveCursor(QTextCursor.MoveOperation.End)
                    self.combat_display.log_text.ensureCursorVisible()
                    self.combat_display.log_text.setUpdatesEnabled(True)
                else:
                    logger.error(f"COMBAT_LOG_SET_HTML received but target or content invalid: {target_widget}, {type(event.content)}")
            except Exception as e:
                logger.error(f"Error applying COMBAT_LOG_SET_HTML: {e}", exc_info=True)
            # No need to explicitly call visual completion; orchestrator doesn't wait for this type
        elif isinstance(event.content, str): # For NARRATIVE_*, SYSTEM_MESSAGE
            if target_widget == self.combat_display:
                # Log event routing for diagnostics
                logger.info(f"MainWindow: Routing string event to CombatDisplay id={event.event_id} type={event.type.name} gradual={bool(event.gradual_visual_display)}")
                self.combat_display.append_orchestrated_event_content(
                    event_content=event.content,
                    event_role=event.role or "system",
                    is_gradual=event.gradual_visual_display,
                    event_id=event.event_id
                )
            elif target_widget == self.game_output:
                text_format = None 
                if event.role == "system": text_format = self.game_output.system_format
                elif event.role == "gm": text_format = self.game_output.gm_format
                elif event.role == "player": text_format = self.game_output.player_format
                # Hide [DEV] messages unless dev mode is enabled
                try:
                    if isinstance(event.content, str) and event.content.strip().startswith("[DEV]"):
                        q_settings = QSettings("RPGGame", "Settings")
                        if not q_settings.value("dev/enabled", False, type=bool):
                            if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator.is_waiting_for_visual:
                                self.game_engine._combat_orchestrator._handle_visual_display_complete()
                            return
                except Exception:
                    pass
                self.game_output.append_text(event.content, text_format, event.gradual_visual_display)
            elif target_widget is None and event.type == DisplayEventType.TURN_ORDER_UPDATE:
                 # This was already handled above, but log if it falls through
                 logger.debug("TURN_ORDER_UPDATE already handled for CharacterSheet, no primary text widget needed.")
            else:
                logger.error(f"Unhandled target widget for orchestrated string event: {target_widget}")
                if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator.is_waiting_for_visual:
                    self.game_engine._combat_orchestrator._handle_visual_display_complete()
        else:
            logger.error(f"Orchestrated event has non-string content and is not a known special type: {event}")
            if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator.is_waiting_for_visual:
                self.game_engine._combat_orchestrator._handle_visual_display_complete()

    def _initialize_panel_effects(self):
        """Initialize QGraphicsOpacityEffect for panels that will be animated."""
        if not hasattr(self, 'center_opacity_effect'):
            self.center_opacity_effect = QGraphicsOpacityEffect(self.center_widget)
            self.center_widget.setGraphicsEffect(self.center_opacity_effect)
            self.center_opacity_effect.setOpacity(0.0)

        if not hasattr(self, 'right_panel_opacity_effect'):
            self.right_panel_opacity_effect = QGraphicsOpacityEffect(self.right_panel)
            self.right_panel.setGraphicsEffect(self.right_panel_opacity_effect)
            self.right_panel_opacity_effect.setOpacity(0.0)

        if not hasattr(self, 'status_bar_opacity_effect'):
            self.status_bar_opacity_effect = QGraphicsOpacityEffect(self.status_bar)
            self.status_bar.setGraphicsEffect(self.status_bar_opacity_effect)
            self.status_bar_opacity_effect.setOpacity(0.0)

    def _start_panel_animations(self, character_data: Dict[str, Any]):
        """Starts the animation sequence for showing the main game panels."""
        self._character_data_for_new_game = character_data 

        self._initialize_panel_effects()

        # 1. Make panels visible (for layout) but keep them disabled and transparent
        self.center_widget.setVisible(True)
        self.center_widget.setEnabled(False) # Keep disabled during animation
        self.center_opacity_effect.setOpacity(0.0)

        self.right_panel.setVisible(True)
        self.right_panel.setEnabled(False) # Keep disabled during animation
        # Ensure right_panel is set to its desired initial expanded state before animation
        if not self.right_panel.isExpanded(): 
             self.right_panel.setExpanded(True) # Set its state, width animation will be part of its logic
        self.right_panel_opacity_effect.setOpacity(0.0)

        animation_duration = 300 

        center_anim = QPropertyAnimation(self.center_opacity_effect, b"opacity", self)
        center_anim.setDuration(animation_duration)
        center_anim.setStartValue(0.0)
        center_anim.setEndValue(1.0)
        center_anim.setEasingCurve(QEasingCurve.InOutQuad)

        right_panel_anim = QPropertyAnimation(self.right_panel_opacity_effect, b"opacity", self)
        right_panel_anim.setDuration(animation_duration)
        right_panel_anim.setStartValue(0.0)
        right_panel_anim.setEndValue(1.0)
        right_panel_anim.setEasingCurve(QEasingCurve.InOutQuad)

        self.parallel_anim_group = QParallelAnimationGroup(self)
        self.parallel_anim_group.addAnimation(center_anim)
        self.parallel_anim_group.addAnimation(right_panel_anim)

        self.parallel_anim_group.finished.connect(self._animate_status_bar_in)
        self.parallel_anim_group.start(QPropertyAnimation.DeleteWhenStopped)

    @Slot()
    def _animate_status_bar_in(self):
        """Makes the status bar visible and animates its fade-in."""
        # Enable the center and right panels now that their fade-in is complete
        self.center_widget.setEnabled(True)
        self.right_panel.setEnabled(True)
        logger.info("Center widget and Right panel enabled after fade-in.")

        self.status_bar.setVisible(True)
        self.status_bar.setEnabled(False) # Keep disabled during its own animation
        self.status_bar_opacity_effect.setOpacity(0.0)

        status_bar_anim = QPropertyAnimation(self.status_bar_opacity_effect, b"opacity", self)
        status_bar_anim.setDuration(200) 
        status_bar_anim.setStartValue(0.0)
        status_bar_anim.setEndValue(1.0)
        status_bar_anim.setEasingCurve(QEasingCurve.InOutQuad)

        status_bar_anim.finished.connect(self._start_game_flow_after_animation)
        status_bar_anim.start(QPropertyAnimation.DeleteWhenStopped) 

    @Slot()
    def _start_game_flow_after_animation(self):
        """Final step after all panel animations are complete. Starts the game engine flow."""
        self.status_bar.setEnabled(True)
        logger.info("Status bar enabled after fade-in.")
        logger.info("All panel animations complete. Starting game engine flow.")

        character_data = getattr(self, '_character_data_for_new_game', None)
        if not character_data:
            logger.error("Character data not found after animation. Cannot start new game.")
            QMessageBox.critical(self, "Error", "Failed to retrieve character data to start the game.")
            # Reset UI to pre-new-game state
            self.center_widget.setVisible(False)
            self.center_widget.setEnabled(False)
            if hasattr(self, 'center_opacity_effect'): self.center_opacity_effect.setOpacity(0.0)
            
            self.right_panel.setVisible(False)
            self.right_panel.setEnabled(False)
            if hasattr(self, 'right_panel_opacity_effect'): self.right_panel_opacity_effect.setOpacity(0.0)

            self.status_bar.setVisible(False)
            self.status_bar.setEnabled(False)
            if hasattr(self, 'status_bar_opacity_effect'): self.status_bar_opacity_effect.setOpacity(0.0)
            return

        player_name = character_data['name']
        race = character_data['race']
        path = character_data['path']
        origin_id = character_data.get('origin_id', '') # Get origin_id
        sex = character_data.get('sex', 'Male')
        # 'description' from character_data is the origin's intro_text/background
        origin_description_as_background = character_data.get('description', '') 
        character_image = character_data.get('character_image')
        use_llm = character_data.get('use_llm', True)
        custom_stats = None
        if 'stats' in character_data:
            if all(isinstance(val, int) for val in character_data['stats'].values()):
                custom_stats = character_data['stats']
            else: 
                logger.warning("Unexpected stats format from character_data, attempting to parse.")
                temp_stats = {}
                for stat_name, stat_info in character_data['stats'].items():
                    if isinstance(stat_info, dict) and 'base' in stat_info:
                        temp_stats[stat_name] = stat_info['base']
                    elif isinstance(stat_info, int):
                         temp_stats[stat_name] = stat_info
                if temp_stats: custom_stats = temp_stats
        
        logger.info(f"Starting new game with resolved data: Name={player_name}, Race={race}, Path={path}, OriginID={origin_id}, Sex={sex}, LLM={use_llm}, Stats={custom_stats is not None}")

        # Pre-clear any previous session UI and orchestrator state if starting a new game during an ongoing session
        try:
            if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator:
                # Detach any existing CombatManager and clear queued events
                try:
                    self.game_engine._combat_orchestrator.set_combat_manager(None)
                except Exception:
                    pass
                self.game_engine._combat_orchestrator.clear_queue_and_reset_flags()
        except Exception as e:
            logger.warning(f"Failed to clear orchestrator state before starting new game: {e}")
        # Ensure any lingering closing-narrative wait flag is reset
        try:
            if hasattr(self.game_engine, '_waiting_for_closing_narrative_display'):
                self.game_engine._waiting_for_closing_narrative_display = False
        except Exception:
            pass
        # Clear visible outputs to avoid mixing old content
        try:
            self.game_output.clear()
        except Exception as e:
            logger.warning(f"Failed to clear GameOutputWidget before starting new game: {e}")
        try:
            self.combat_display.clear_display()
        except Exception as e:
            logger.warning(f"Failed to clear CombatDisplay before starting new game: {e}")
        # Clear right panel widgets to avoid stale state
        try:
            if hasattr(self.right_panel, 'journal_panel'):
                self.right_panel.journal_panel.clear_all()
            if hasattr(self.right_panel, 'inventory_panel') and hasattr(self.right_panel.inventory_panel, 'clear'):
                try:
                    self.right_panel.inventory_panel.clear()
                except Exception:
                    pass
            if hasattr(self.right_panel, 'character_sheet') and hasattr(self.right_panel.character_sheet, '_clear_stat_displays'):
                self.right_panel.character_sheet._clear_stat_displays()
        except Exception as e:
            logger.warning(f"Failed to clear right panel widgets before starting new game: {e}")
        # Reset last submitted command tracking
        self._last_submitted_command = None

        self.game_engine.start_new_game(
            player_name=player_name, 
            race=race, 
            path=path, 
            background=origin_description_as_background, # Pass origin description as background
            sex=sex,
            character_image=character_image,
            stats=custom_stats,
            origin_id=origin_id # Pass origin_id here
        )
        
        self.game_engine.set_llm_enabled(use_llm)
        
        # Ensure journal quests is a dictionary
        initial_quests_data = character_data.get('initial_quests', [])
        journal_quests = {}
        if isinstance(initial_quests_data, dict):
            journal_quests = initial_quests_data
        elif isinstance(initial_quests_data, list):
            logger.warning(f"Initial quests from origin is a list: {initial_quests_data}. Initializing journal quests as an empty dictionary. Full quest population from origin list is not yet implemented here.")
        
        current_game_state = self.game_engine.state_manager.current_state
        if current_game_state:
            if not hasattr(current_game_state, "journal") or current_game_state.journal is None:
                current_game_state.journal = {
                    "character": origin_description_as_background, # Use the same background/origin text
                    "quests": journal_quests,
                    "notes": []
                }
            # Ensure player state's origin_id is set, if GameEngine.start_new_game didn't already
            if not current_game_state.player.origin_id:
                 current_game_state.player.origin_id = origin_id
        
        self._update_ui() 
        self.game_engine.state_manager.ensure_stats_manager_initialized()
        
        if current_game_state and current_game_state.player:
            self.right_panel.update_character(current_game_state.player)

        # Clean up the temporary data
        if hasattr(self, '_character_data_for_new_game'):
            delattr(self, '_character_data_for_new_game')

    @Slot(str)
    def _handle_item_use_requested(self, item_id: str):
        """Handle item use request from inventory panel."""
        logger.info(f"[GUI] MainWindow: Item use requested for ID: {item_id}")
        # Placeholder: Implement logic to use the item via InventoryManager or GameEngine
        # For example, this might involve checking if the item is consumable,
        # applying its effects, and removing it from inventory.
        # This could also involve a command like "use <item_id>"
        
        # Example:
        # result = self.game_engine.process_command(f"use {item_id}")
        # self._update_ui() # Update UI after action
        self.game_output.append_system_message(f"Attempting to use item: {item_id} (Handler not fully implemented).")
        # This should ideally go through the command processing loop if 'use' is a player command
        self._process_command(f"use {item_id}")

    @Slot(str)
    def _handle_item_examine_requested(self, item_id: str):
        """Handle item examine request from inventory panel."""
        logger.info(f"[GUI] MainWindow: Item examine requested for ID: {item_id}")
        
        inventory_manager = get_inventory_manager()
        item = inventory_manager.get_item_details_for_dialog(item_id)

        if item:
            from gui.dialogs.item_info_dialog import ItemInfoDialog # Local import
            dialog = ItemInfoDialog(item, self)
            dialog.exec()
        else:
            self.game_output.append_system_message(f"Could not find details for item ID: {item_id}", gradual=False)
            logger.error(f"Could not get item details for ID: {item_id} to show dialog.")
        
        self._update_ui() # Update UI in case item properties were discovered

    @Slot(str) 
    def _handle_item_unequip_requested(self, item_identifier: str): 
        """Handle item unequip request from inventory panel. This is now fully mechanical.
           item_identifier is expected to be an item_id from InventoryPanel.
        """
        logger.info(f"[GUI] MainWindow: Mechanical item unequip requested for ITEM_ID: {item_identifier}")
        inventory_manager = get_inventory_manager()
        
        item_to_unequip = inventory_manager.get_item(item_identifier) 
        if not item_to_unequip: 
            logger.error(f"Cannot unequip: Item ID '{item_identifier}' not found.")
            self._update_ui()
            return
        
        slot_found: Optional[EquipmentSlot] = None
        # inventory_manager.equipment is Dict[EquipmentSlot, Optional[Item]]
        for slot_enum_loop, item_obj_loop in inventory_manager.equipment.items(): 
            if item_obj_loop and isinstance(item_obj_loop, Item) and item_obj_loop.id == item_to_unequip.id:
                slot_found = slot_enum_loop
                break
        
        if not slot_found:
            logger.info(f"{item_to_unequip.name} is not currently equipped (triggered by ID from InventoryPanel).")
            self._update_ui()
            return
        
        item_name_unequipped = item_to_unequip.name
        slot_unequipped_from_str = slot_found.value.replace("_", " ")

        if inventory_manager.unequip_item(slot_found): # unequip_item takes slot
            logger.info(f"Successfully unequipped {item_name_unequipped} from {slot_unequipped_from_str}.")
        else:
            logger.warning(f"Failed to unequip {item_name_unequipped} (Identifier: {item_identifier}).")

        self._update_ui()

    @Slot(str)
    def _handle_item_drop_requested(self, item_id: str):
        """Handle item drop request from inventory panel."""
        logger.info(f"[GUI] MainWindow: Item drop requested for ID: {item_id}")
        inventory_manager = get_inventory_manager()
        item = inventory_manager.get_item(item_id)

        if not item:
            logger.error(f"Drop requested for non-existent item ID: {item_id}")
            self._update_ui()
            return

        if inventory_manager.is_item_equipped(item_id):
            reply = QMessageBox.question(
                self,
                "Confirm Drop Equipped Item",
                f"'{item.name}' is currently equipped. Are you sure you want to drop it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                logger.info(f"Drop cancelled by user for equipped item: {item.name}")
                return 

            slot_to_unequip: Optional[EquipmentSlot] = None
            for slot_enum, equipped_item_obj in inventory_manager.equipment.items(): 
                if equipped_item_obj and isinstance(equipped_item_obj, Item) and equipped_item_obj.id == item_id: # Check type
                    slot_to_unequip = slot_enum
                    break
            if slot_to_unequip:
                inventory_manager.unequip_item(slot_to_unequip)
                logger.info(f"Unequipped '{item.name}' from {slot_to_unequip.value} prior to dropping.")
                self._update_ui() 
            else:
                logger.error(f"Could not find slot for equipped item '{item.name}' to unequip before dropping.")
                return
        
        logger.info(f"Processing drop command for item ID: {item_id} via LLM.")
        self._process_command(f"drop {item_id}") 

    @Slot(str) 
    def _handle_item_equip_requested(self, item_id: str): 
        """Handle item equip request from inventory panel. This is now fully mechanical."""
        logger.info(f"[GUI] MainWindow: Mechanical item equip requested for ID: {item_id}")
        inventory_manager = get_inventory_manager()
        item = inventory_manager.get_item(item_id)

        if not item:
            # self.game_output.append_system_message(f"Cannot equip: Item ID {item_id} not found.", gradual=False)
            logger.error(f"Failed to equip item {item_id}: Not found in InventoryManager.")
            self._update_ui() # Update UI to reflect potential state changes even on error
            return

        if not item.is_equippable:
            # self.game_output.append_system_message(f"Cannot equip {item.name}: It is not equippable.", gradual=False)
            logger.info(f"Cannot equip {item.name}: It is not equippable.")
            self._update_ui()
            return

        if inventory_manager.equip_item(item.id): # Preferred slot logic is inside equip_item
            equipped_slot_str = "a suitable slot"
            for slot_enum, equipped_item_id in inventory_manager.equipment.items():
                if equipped_item_id == item.id:
                    equipped_slot_str = slot_enum.value.replace("_", " ")
                    break
            logger.info(f"Successfully equipped {item.name} to {equipped_slot_str}.")
            # No direct output to GameOutputWidget here for mechanical actions
        else:
            # self.game_output.append_system_message(f"Could not equip {item.name}. No suitable slot available or other restriction.", gradual=False)
            logger.warning(f"Failed to equip {item.name} (ID: {item.id}). InventoryManager.equip_item returned false.")

        self._update_ui()

    @Slot(EquipmentSlot)
    def _handle_item_unequip_from_slot_requested(self, slot_to_unequip: EquipmentSlot):
        """Handles unequip request specifically from a known slot (e.g., CharacterSheet)."""
        logger.info(f"[GUI] MainWindow: Mechanical item unequip from slot requested: {slot_to_unequip.value}")
        inventory_manager = get_inventory_manager()
        
        item_obj_in_slot = inventory_manager.equipment.get(slot_to_unequip) # This is an Item object or None
        item_name = "Item"
        if item_obj_in_slot and isinstance(item_obj_in_slot, Item): # Check type
            item_name = item_obj_in_slot.name
        
        if inventory_manager.unequip_item(slot_to_unequip):
            logger.info(f"Successfully unequipped {item_name} from {slot_to_unequip.value}.")
        else:
            logger.warning(f"Failed to unequip item from slot: {slot_to_unequip.value}")
        
        self._update_ui()

    @Slot(EquipmentSlot, str)
    def _handle_item_drop_from_slot_requested(self, slot_to_unequip: EquipmentSlot, item_id_to_drop: str):
        """Handles drop request for an item currently equipped in a slot."""
        logger.info(f"[GUI] MainWindow: Item drop from slot requested. Slot: {slot_to_unequip.value}, Item ID: {item_id_to_drop}")
        inventory_manager = get_inventory_manager()
        item = inventory_manager.get_item(item_id_to_drop)
        item_name = item.name if item else "the item"

        reply = QMessageBox.question(
            self,
            "Confirm Drop",
            f"Are you sure you want to drop the equipped item '{item_name}' from your {slot_to_unequip.value.replace('_',' ')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if inventory_manager.unequip_item(slot_to_unequip):
                logger.info(f"Unequipped {item_name} from {slot_to_unequip.value} prior to dropping.")
                self._process_command(f"drop {item_id_to_drop}") 
            else:
                logger.error(f"Failed to unequip {item_name} (ID: {item_id_to_drop}) from slot {slot_to_unequip.value} before dropping.")
        else:
            logger.info(f"Drop cancelled for item {item_name} from slot {slot_to_unequip.value}.")
        
        self._update_ui()