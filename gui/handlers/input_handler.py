#!/usr/bin/env python3
"""
Input handler for processing user commands from the GUI.
"""

from typing import Optional, List, Tuple
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QMessageBox

from core.utils.logging_config import get_logger

logger = get_logger("GUI_INPUT")

class CommandWorker(QObject):
    """Worker for running commands in a separate thread."""
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
            # Process input in the worker thread
            command_result = self.game_engine.process_input(self.command) 
            
            # Process commands returned by LLM
            if command_result.data and "commands" in command_result.data:
                llm_commands: List[Tuple[str, str]] = command_result.data["commands"]
                if llm_commands:
                    logger.info(f"CommandWorker: Processing {len(llm_commands)} commands from LLM response.")
                    # Ensure current_state is available
                    current_game_state = self.game_engine._state_manager.current_state
                    if not current_game_state:
                        logger.error("CommandWorker: Cannot process LLM commands, current_game_state is None.")
                    else:
                        for cmd, args_str in llm_commands:
                            try:
                                logger.debug(f"CommandWorker: Executing LLM command '{cmd}' with args '{args_str}'")
                                # Import locally to avoid circular imports
                                from core.game_flow.command_handlers import process_llm_command
                                
                                cmd_exec_result = process_llm_command(self.game_engine, cmd, [args_str], current_game_state)
                                if cmd_exec_result and not cmd_exec_result.is_success and cmd_exec_result.message:
                                    self.game_engine._output("system", f"Error processing internal command '{cmd}': {cmd_exec_result.message}")

                            except Exception as e_cmd:
                                logger.error(f"CommandWorker: Error processing extracted LLM command '{cmd}': {e_cmd}", exc_info=True)
                                self.game_engine._output("system", f"System error processing internal command '{cmd}'.")
            
            self.finished.emit()
        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.processing.emit(False)

class InputHandler(QObject):
    """
    Handles command input from the GUI, managing the worker thread
    and UI state updates during processing.
    """
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window # Reference to MainWindow
        self.last_submitted_command: Optional[str] = None
        self.worker_thread = None
        self.worker = None

    @Slot(str)
    def process_command(self, command: str):
        """Process a command using the game engine in a separate thread."""
        if not command.strip():
            return
        
        # Check if waiting for closing narrative
        if self.mw.game_engine._waiting_for_closing_narrative_display:
            self.mw.game_output.append_system_message("Please wait, concluding previous actions...", gradual=False)
            self._reenable_input_fields()
            return

        # Check for UI-generated command pattern (internal flag)
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
            from core.interaction.enums import InteractionMode
            state = self.mw.game_engine.state_manager.current_state
            if not is_ui_generated_command and (not state or state.current_mode != InteractionMode.COMBAT):
                self.mw.game_output.append_player_message(command)
            else:
                logger.info("Suppressing player echo in GameOutputWidget (combat mode or UI-generated command).")
        except Exception:
            if not is_ui_generated_command:
                self.mw.game_output.append_player_message(command)
            
        self.last_submitted_command = command 
        
        # Update UI state for processing
        active_command_input = self.mw.narrative_command_input if self.mw.mode_stacked_widget.currentWidget() == self.mw.narrative_view else self.mw.combat_command_input
        active_command_input.clear()
        active_command_input.setEnabled(False)
        active_command_input.command_edit.setPlaceholderText("Processing...")
        
        self.mw.status_bar.showMessage("Processing command...", 0)
        
        # Setup worker
        self.worker_thread = QThread()
        self.worker = CommandWorker(self.mw.game_engine, command)
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
        self.mw._update_ui()
        self.mw.status_bar.clearMessage()
        self._reenable_input_fields()
    
    def _on_command_error(self, error_msg):
        """Handle error in command processing."""
        self.mw.game_output.append_system_message(f"Error: {error_msg}")
        self.mw.status_bar.clearMessage()
        self._reenable_input_fields()

    def _set_processing_state(self, is_processing):
        """Update UI to show processing state."""
        if is_processing:
            self.mw.status_bar.showMessage("Processing command...")
            self.mw.narrative_command_input.command_edit.setPlaceholderText("Processing...")
            self.mw.combat_command_input.command_edit.setPlaceholderText("Processing...")
        else:
            self.mw.status_bar.clearMessage()
            self._reenable_input_fields()

    def _reenable_input_fields(self):
        """Helper to reset input fields to ready state."""
        self.mw.narrative_command_input.setEnabled(True)
        self.mw.combat_command_input.setEnabled(True)
        self.mw.narrative_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")
        self.mw.combat_command_input.command_edit.setPlaceholderText("Enter command or type 'help'...")