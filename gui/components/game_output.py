# --- START OF FILE game_output.py ---

"""
Game output widget for the RPG game GUI.
This module provides a widget for displaying game output.
"""

import logging
from typing import List, Optional, Dict, Any, Iterator, Tuple

from PySide6.QtWidgets import QTextEdit, QWidget, QHBoxLayout, QFrame, QStackedLayout, QVBoxLayout
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont
from PySide6.QtCore import Qt, QTimer, Signal, QSettings, QDir, Slot

from core.utils.logging_config import get_logger
from gui.components.skill_check_display import SkillCheckDisplay
from gui.styles.theme_manager import get_theme_manager
from gui.utils.resource_manager import get_resource_manager
from core.stats.skill_check import SkillCheckResult
import os
print(os.getcwd())

background_path = os.path.join(QDir.currentPath(), "images/gui/background_game_output.png").replace("\\", "/")

logger = get_logger("GUI")

class GameOutputWidget(QFrame):
    """Widget for displaying game output."""

    # --- ECFA Change: Add visualDisplayComplete signal ---
    visualDisplayComplete = Signal()
    # --- End ECFA Change ---

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the game output widget."""
        super().__init__(parent)

        self.setFrameShape(QFrame.NoFrame) # Make the outer frame invisible
        self.setContentsMargins(0, 0, 0, 0)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---

        self.resource_manager = get_resource_manager()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setAcceptRichText(True)

        self.settings = QSettings("RPGGame", "Settings") 

        # Initialize format attributes
        self.system_format = QTextCharFormat()
        self.gm_format = QTextCharFormat()
        self.player_format = QTextCharFormat()
        self.default_format = QTextCharFormat()
        
        # This will hold the reference to the command input overlay
        self.command_input_widget: Optional[QWidget] = None

        self._update_theme() # Apply theme on init

        self.skill_check_display = SkillCheckDisplay()
        self.skill_check_display.setVisible(False)
        self.skill_check_display.display_finished.connect(self._on_skill_check_finished)

        # Use a simple QVBoxLayout containing only the text edit
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.text_edit)

        # The skill check display will be a direct child for overlaying
        self.skill_check_display.setParent(self)

        self._gradual_text_iterator: Optional[Iterator[str]] = None
        self._gradual_text_format: Optional[QTextCharFormat] = None
        self._gradual_timer: Optional[QTimer] = None 
        self._is_gradual_display_active: bool = False
        self._pending_immediate_messages: List[Tuple[str, QTextCharFormat]] = []

    @Slot(dict)
    def _update_theme(self, palette: Optional[Dict[str, Any]] = None):
        """Update all styles from the theme palette."""
        if palette:
            self.palette = palette
        self._update_formats()
        self._setup_background()

    def _update_formats(self):
        """Update text formats based on the current theme palette."""
        colors = self.palette.get('colors', {})
        fonts = self.palette.get('fonts', {})
        
        # Get font settings from QSettings (user configurable)
        settings = self.settings
        font_family = settings.value("style/font_family", fonts.get('family_main', "Garamond"))
        font_size = int(settings.value("style/font_size", fonts.get('size_main_output', 14)))
        user_input_font_family = settings.value("style/user_input_font_family", fonts.get('family_user_input', "Garamond"))
        user_input_font_size = int(settings.value("style/user_input_font_size", fonts.get('size_user_input', 14)))

        # System message format
        self.system_format.setForeground(QColor(colors.get('output_text_system', '#a03628')))
        self.system_format.setFontWeight(QFont.Bold)

        # GM/narrator format
        self.gm_format.setForeground(QColor(colors.get('output_text_main', '#3b2f1e')))
        self.gm_format.setFont(QFont(font_family, font_size))

        # Player format
        self.player_format.setForeground(QColor(colors.get('output_text_player', '#0b5a8e')))
        player_font = QFont(user_input_font_family, user_input_font_size)
        player_font.setItalic(True)  
        self.player_format.setFont(player_font)

        # Default format
        self.default_format.setForeground(QColor(colors.get('output_text_main', '#3b2f1e')))  
        self.default_format.setFont(QFont(font_family, font_size))

    def _setup_background(self):
        """Set up the styled background for the game output."""
        colors = self.palette.get('colors', {})
        fonts = self.palette.get('fonts', {})
        paths = self.palette.get('paths', {})
        
        settings = self.settings
        font_family = settings.value("style/font_family", fonts.get('family_main', "Garamond"))
        font_size = int(settings.value("style/font_size", fonts.get('size_main_output', 14)))
        
        background_image_path = paths.get('background_main_output', "images/gui/background_game_output.png")

        # Set the background on the parent frame (GameOutputWidget itself)
        self.setStyleSheet(f"""
            GameOutputWidget {{
                background-image: url('{background_image_path}');
                background-attachment: fixed;
                border: 2px solid {colors.get('border_dark', '#4a3a30')};
                border-radius: 15px;
            }}
        """)

        # Make the QTextEdit transparent and add bottom padding for the command input
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {colors.get('output_text_main', '#3b2f1e')};
                border: none;
                font-family: '{font_family}';
                font-size: {font_size}pt;
                padding-left: 20px;
                padding-right: 20px;
                padding-top: 20px;
                padding-bottom: 70px; /* Creates space for the command input */
            }}
            QScrollBar:vertical {{
                border: none;
                background-color: transparent;
                width: 14px;
                margin: 15px 0 15px 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {colors.get('text_secondary', '#8b7a65')};
                min-height: 30px;
                border-radius: 7px;
            }}
        """)

        self.text_edit.viewport().setAutoFillBackground(False)

    def set_command_input_widget(self, command_widget: QWidget):
        """Stores a reference to the command input widget and sets its parent."""
        self.command_input_widget = command_widget
        self.command_input_widget.setParent(self)
        self.command_input_widget.show()

    def resizeEvent(self, event):
        """Handle resize events to manually position overlay widgets."""
        super().resizeEvent(event)
        
        # Position the command input widget at the bottom
        if self.command_input_widget:
            # Use a small margin from the edges
            margin = 10
            widget_height = self.command_input_widget.sizeHint().height()
            
            # Calculate geometry
            x = margin
            y = self.height() - widget_height - margin
            width = self.width() - (2 * margin)
            
            self.command_input_widget.setGeometry(x, y, width, widget_height)

        # Position the skill check display in the center
        if self.skill_check_display and self.skill_check_display.isVisible():
            x = (self.width() - self.skill_check_display.width()) / 2
            y = (self.height() - self.skill_check_display.height()) / 2
            self.skill_check_display.move(int(x), int(y))

    def append_text(self, text: str, format: Optional[QTextCharFormat] = None, gradual: bool = True):
        """Append text to the output with the specified format.

        Args:
            text: The text to append
            format: The text format to apply
            gradual: Whether to display the text gradually (respects settings)
        """
        format_name = "None" # For logging
        if format == self.gm_format: format_name = "gm_format"
        elif format == self.system_format: format_name = "system_format"
        elif format == self.player_format: format_name = "player_format"
        elif format == self.default_format: format_name = "default_format"
        logging.debug(f"GameOutputWidget.append_text: Format: '{format_name}', Requested Gradual: {gradual}, Active Gradual: {self._is_gradual_display_active}, Text: '{text[:50]}...'")

        # Determine if gradual display should actually be used based on request AND global setting
        gradual_display_enabled_by_setting = self.settings.value("display/gradual_text_narrative", True, type=bool)
        effective_gradual = gradual and gradual_display_enabled_by_setting
        
        # Override for specific welcome/background texts to always be immediate
        if "CHARACTER BACKGROUND" in text.upper() or "WELCOME TO YOUR ADVENTURE" in text.upper() or "WELCOME BACK" in text.upper():
            logging.info("Special text detected, forcing immediate display for GameOutputWidget.")
            effective_gradual = False

        if not text.strip():
            logging.warning("GameOutputWidget: Attempting to append empty text, ignoring.")
            self.visualDisplayComplete.emit() 
            return

        if not effective_gradual and self._is_gradual_display_active:
            logging.info(f"GameOutputWidget: Queueing immediate message '{text[:50]}...' as a gradual display is active.")
            self._pending_immediate_messages.append((text, format if format else self.default_format))
            return

        if not self._is_gradual_display_active: # Can only start new display if not already active
            if not effective_gradual:
                logging.debug("GameOutputWidget: Appending immediate message directly.")
                self._insert_text_immediately(text, format) 
                self.visualDisplayComplete.emit() 
                self._process_pending_immediate_messages() 
            else:
                logging.debug(f"GameOutputWidget: Starting gradual display: '{text[:50]}...'")
                self._is_gradual_display_active = True
                # Ensure pending immediate queue is cleared *before* starting new gradual display
                # if any were processed just before this.
                if self._pending_immediate_messages:
                    logger.warning("GameOutputWidget: Starting new gradual display while pending immediate messages existed. This might indicate a logic flaw if they weren't processed.")
                    # self._process_pending_immediate_messages() # Process them now before starting new gradual one.

                self._gradual_text_iterator = iter(text)
                self._gradual_text_format = format if format else self.default_format

                cursor = self.text_edit.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.text_edit.setTextCursor(cursor)

                if not self._gradual_timer:
                     self._gradual_timer = QTimer(self)
                     self._gradual_timer.setSingleShot(True)
                     self._gradual_timer.timeout.connect(self._display_next_char)
                
                char_delay_initial = self.settings.value("display/text_speed_delay_narrative", 30, type=int)
                char_delay_initial = max(1, char_delay_initial) # Ensure at least 1ms for timer
                QTimer.singleShot(char_delay_initial, self._display_next_char) # Start with configured delay
        else: # Gradual display is already active
            if effective_gradual: 
                logger.warning(f"GameOutputWidget: Ignoring NEW gradual text '{text[:30]}' because a gradual display is ALREADY active. This text should have been queued by the Orchestrator.")
                # To prevent stalling, immediately emit completion for this ignored text.
                self.visualDisplayComplete.emit()
            # If it was an *immediate* message while gradual was active, it was already queued above.

    def _insert_text_immediately(self, text: str, format: Optional[QTextCharFormat]):
        """Helper to append text immediately and add newlines."""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.text_edit.setTextCursor(cursor)
        
        current_format = format if format else self.default_format
        cursor.setCharFormat(current_format)
        
        cursor.insertText(text)
        if not text.endswith('\n'):
            cursor.insertText('\n')
        cursor.insertText('\n') # Extra blank line
        self.text_edit.ensureCursorVisible()

    def _process_pending_immediate_messages(self):
        """Processes any queued immediate messages if gradual display is not active."""
        if self._is_gradual_display_active:
            return # Don't process if gradual is still running
        
        while self._pending_immediate_messages:
            text, text_format = self._pending_immediate_messages.pop(0)
            logging.info(f"GameOutputWidget: Processing pending immediate message '{text[:50]}...'")
            self._insert_text_immediately(text, text_format)
            # Emitting visualDisplayComplete for each processed pending message
            # might be too chatty for the orchestrator.
            # The orchestrator should ideally wait for the original gradual display to finish,
            # then this queue is flushed, and *then* the "overall" completion is signaled.
            # However, for simplicity, let's emit for each. Orchestrator must handle this.
            self.visualDisplayComplete.emit()

    def _display_next_char(self):
        """Displays the next character from the iterator and schedules the next call."""
        if not self._is_gradual_display_active or not self._gradual_text_iterator:
            if self._is_gradual_display_active: 
                self._is_gradual_display_active = False
                self.visualDisplayComplete.emit()
                self._process_pending_immediate_messages() 
            return

        try:
            char = next(self._gradual_text_iterator)
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.text_edit.setTextCursor(cursor)

            if self._gradual_text_format:
                cursor.setCharFormat(self._gradual_text_format)
            cursor.insertText(char)
            self.text_edit.ensureCursorVisible()

            # Use QSettings for user-configurable speed
            char_delay = self.settings.value("display/text_speed_delay", 30, type=int) 
            char_delay = max(5, char_delay)
            
            if self._gradual_timer: 
                self._gradual_timer.start(char_delay)

        except StopIteration:
            logging.debug("GameOutputWidget: Gradual display finished for one segment.")
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.text_edit.setTextCursor(cursor)
            if not self.text_edit.toPlainText().endswith('\n\n'): 
                 if self.text_edit.toPlainText().endswith('\n'):
                     cursor.insertText('\n')
                 else:
                     cursor.insertText('\n\n')
            self.text_edit.ensureCursorVisible()

            self._is_gradual_display_active = False
            self._gradual_text_iterator = None
            self._gradual_text_format = None
            
            self.visualDisplayComplete.emit() 
            
            self._process_pending_immediate_messages()

        except Exception as e:
             logging.error(f"GameOutputWidget: Error during gradual display: {e}", exc_info=True)
             self._is_gradual_display_active = False
             self._gradual_text_iterator = None
             self._gradual_text_format = None
             if self._gradual_timer and self._gradual_timer.isActive():
                 self._gradual_timer.stop()
             self.visualDisplayComplete.emit() 
             self._pending_immediate_messages.clear()
             self._process_pending_immediate_messages()
             
    def _insert_text(self, text: str, format: Optional[QTextCharFormat] = None):
        """Helper method to insert text directly with a format."""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.text_edit.setTextCursor(cursor)
        if format:
            cursor.setCharFormat(format)
        else:
            cursor.setCharFormat(self.default_format) # Fallback to default
        cursor.insertText(text)
        self.text_edit.ensureCursorVisible()

    def append_system_message(self, message: str, gradual: bool = False):
        """Append a system message."""
        logging.debug(f"GAME_OUTPUT: append_system_message called. Gradual: {gradual}, Content: '{message[:50]}...'")
        self.append_text("[SYSTEM] " + message, self.system_format, gradual=gradual)

    def append_gm_message(self, message: str, gradual: bool = True):
        """Append a game master message."""
        logging.debug(f"GAME_OUTPUT: append_gm_message called. Gradual: {gradual}, Content: '{message[:50]}...'")
        
        # Special logging for reintroductory narrative debugging
        if "night air" in message.lower() or "find yourself" in message.lower():
            logging.info(f"LIFECYCLE_DEBUG: append_gm_message - This appears to be reintroductory narrative")
            logging.info(f"LIFECYCLE_DEBUG: Message length: {len(message)}")
            logging.info(f"LIFECYCLE_DEBUG: Gradual setting: {gradual}")
            logging.info(f"LIFECYCLE_DEBUG: Current gradual display active: {self._is_gradual_display_active}")
            logging.info(f"LIFECYCLE_DEBUG: Message preview: '{message[:200]}...'")
        
        processed_message = "\n".join(message.split("\n"))
        if "===== CHARACTER BACKGROUND =====" in message:
            logging.info("Character background detected, using immediate display for GM message")
            gradual = False
            
        logging.info(f"LIFECYCLE_DEBUG: About to call append_text with gradual={gradual}")
        self.append_text(processed_message, self.gm_format, gradual=gradual)
        logging.info(f"LIFECYCLE_DEBUG: append_text call completed")

    def append_player_message(self, message: str, gradual: bool = False):
        """Append a player message."""
        logging.debug(f"GAME_OUTPUT: append_player_message called. Gradual: {gradual}, Content: '{message[:50]}...'")
        self.append_text("You: " + message, self.player_format, gradual=gradual)

    def clear(self):
        """Clear the output."""
        # Stop any gradual display and clear state before clearing
        if self._gradual_timer and self._gradual_timer.isActive():
            self._gradual_timer.stop()
        self._is_gradual_display_active = False
        self._gradual_text_iterator = None
        self._gradual_text_format = None
        self._pending_immediate_message = None
        # Clear the text edit
        self.text_edit.clear()

    def show_skill_check(self, result: SkillCheckResult, context: str = "", duration_ms: int = 3000) -> None:
        """
        Display a skill check result with animation.

        Args:
            result: The SkillCheckResult object containing the check details
            context: Optional context description for the check
            duration_ms: How long to display the result (in milliseconds)
        """
        # Stop any gradual display and clear state before showing skill check
        if self._gradual_timer and self._gradual_timer.isActive():
            logging.debug("Stopping gradual display for skill check.")
            self._gradual_timer.stop()
        self._is_gradual_display_active = False
        self._gradual_text_iterator = None
        self._gradual_text_format = None
        self._pending_immediate_message = None

        # Show the skill check
        self.skill_check_display.show_check_result(result, context, duration_ms)

    def _on_skill_check_finished(self) -> None:
        """
        Handler for when the skill check display is finished.
        Returns focus to the text edit.
        """
        # Ensure the text edit is visible and has focus
        self.text_edit.setFocus()

    def process_skill_check_command(self, command: str) -> bool:
        """
        Process a skill check command from the narrative.

        Args:
            command: The command string in format {STAT_CHECK:<stat>:<difficulty>:<context>}

        Returns:
            True if the command was processed successfully, False otherwise
        """
        from core.agents.rule_checker import get_rule_checker_agent

        try:
            # Parse the command format {STAT_CHECK:<stat>:<difficulty>:<context>}
            parts = command.strip().split(':')
            if len(parts) < 3:
                logging.warning(f"Invalid STAT_CHECK command format: {command}")
                return False

            stat_type = parts[1].strip().upper()
            difficulty = int(parts[2].strip())
            context = parts[3].strip() if len(parts) > 3 else ""

            # Get the rule checker agent to perform the skill check
            rule_checker = get_rule_checker_agent()
            check_result = rule_checker.perform_skill_check(stat_type, difficulty, context)

            if not check_result["success"]:
                logging.error(f"Skill check failed: {check_result.get('error', 'Unknown error')}")
                return False

            # Display the skill check result
            self.show_skill_check(check_result["result"], check_result["context"])

            return True

        except Exception as e:
            logging.error(f"Error processing skill check command: {e}")
            return False

    def stop_gradual_display(self):
        """Immediately stops any ongoing gradual text display and processes pending messages quickly."""
        logging.info("GameOutputWidget: Stopping current gradual display and flushing pending messages.")
        if self._gradual_timer and self._gradual_timer.isActive():
            self._gradual_timer.stop()
        
        # If an iterator was active, display remaining text immediately
        if self._gradual_text_iterator:
            remaining_text = "".join(list(self._gradual_text_iterator))
            if remaining_text:
                self._insert_text_immediately(remaining_text, self._gradual_text_format)
            self._gradual_text_iterator = None
            self._gradual_text_format = None

        self._is_gradual_display_active = False # Mark as not active
        
        # Process all pending immediate messages
        self._process_pending_immediate_messages()
            
        # Emit completion after flushing everything, if no pending messages started new gradual display
        if not self._is_gradual_display_active:
            self.visualDisplayComplete.emit()