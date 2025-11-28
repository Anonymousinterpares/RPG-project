#!/usr/bin/env python3
"""
Display handler for processing orchestrated events and general output.
"""

from PySide6.QtCore import QObject, Slot, QTimer
from PySide6.QtGui import QTextCursor
from core.orchestration.events import DisplayEvent, DisplayEventType, DisplayTarget
from core.interaction.enums import InteractionMode
from core.utils.logging_config import get_logger

logger = get_logger("GUI_DISPLAY")

class DisplayHandler(QObject):
    """
    Handles display events from the game engine and orchestrator, 
    routing them to the appropriate UI widgets (GameOutput or CombatDisplay).
    """
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window # Reference to MainWindow

    @Slot(object)
    def process_event(self, event):
        """
        Handles DisplayEvents routed from the CombatOutputOrchestrator via the GameEngine.
        """
        if not isinstance(event, DisplayEvent):
            logger.error(f"DisplayHandler received non-DisplayEvent object: {type(event)}")
            self._signal_visual_complete_if_needed()
            return

        logger.info(f"DisplayHandler processing orchestrated event: {event}")
        state = self.mw.game_engine.state_manager.current_state

        # --- AP System: Handle AP_UPDATE event ---
        if event.type == DisplayEventType.AP_UPDATE:
            self._handle_ap_update(event, state)
            return

        target_widget = self._determine_target_widget(event, state)
        
        if not target_widget and event.type not in [
            DisplayEventType.TURN_ORDER_UPDATE, 
            DisplayEventType.UI_BAR_UPDATE_PHASE1, 
            DisplayEventType.UI_BAR_UPDATE_PHASE2, 
            DisplayEventType.COMBAT_LOG_REBUILD
        ]:
            logger.error(f"No target widget found for orchestrated event: {event} and not a special UI event.")
            self._signal_visual_complete_if_needed()
            return

        # Handle event types
        if event.type == DisplayEventType.COMBAT_LOG_REBUILD:
            if self.mw.combat_display and isinstance(event.content, list):
                self.mw.combat_display.rebuild_log_from_history(event.content)
            # Synchronous, signal completion immediately
            QTimer.singleShot(0, self._signal_visual_complete_if_needed)

        elif event.type == DisplayEventType.BUFFER_FLUSH:
            self._handle_buffer_flush(event, target_widget)

        elif event.type in [DisplayEventType.UI_BAR_UPDATE_PHASE1, DisplayEventType.UI_BAR_UPDATE_PHASE2]:
            self._handle_ui_bar_update(event, state)

        elif event.type == DisplayEventType.TURN_ORDER_UPDATE:
            if self.mw.right_panel.character_sheet:
                self.mw.right_panel.character_sheet.handle_turn_order_update(event.content)
            QTimer.singleShot(0, self._signal_visual_complete_if_needed)

        elif event.type == DisplayEventType.COMBAT_LOG_SET_HTML:
            self._handle_combat_log_set_html(event, target_widget)

        elif isinstance(event.content, str): # Narrative, System Message
            self._handle_string_content(event, target_widget)
        
        else:
            logger.error(f"Orchestrated event has non-string content and is not a known special type: {event}")
            self._signal_visual_complete_if_needed()

    @Slot()
    def handle_game_output(self, role: str, content: str):
        """
        Handle non-orchestrated output from the game engine.
        """
        # Prevent echoing the player's command if it somehow comes through this path
        input_handler = self.mw.input_handler
        
        is_ui_generated_command_pattern = False
        try:
            parts = content.split(maxsplit=1)
            if len(parts) > 0 and parts[0].lower() in ["examine", "equip", "unequip", "drop", "use"]:
                if len(parts) > 1 and '-' in parts[1] and len(parts[1]) > 10:
                    is_ui_generated_command_pattern = True
        except: 
            pass

        if role == "player" and ( 
            (input_handler.last_submitted_command is not None and content == input_handler.last_submitted_command) 
            or is_ui_generated_command_pattern 
        ):
            if input_handler.last_submitted_command == content:
                 input_handler.last_submitted_command = None 
            return
            
        if input_handler.last_submitted_command is not None and content != input_handler.last_submitted_command:
             input_handler.last_submitted_command = None

        # Route to GameOutputWidget
        if role == "system":
            self.mw.game_output.append_system_message(content, gradual=False)
        elif role == "gm":
            self.mw.game_output.append_gm_message(content, gradual=True)
        elif role == "player":
            try:
                state = self.mw.game_engine.state_manager.current_state
                if state and state.current_mode == InteractionMode.COMBAT:
                    return
            except Exception:
                pass
            self.mw.game_output.append_player_message(content, gradual=False)
        else:
            self.mw.game_output.append_text(f"[{role}] {content}", gradual=False)
                      
        self.mw._update_ui()

    @Slot()
    def on_combat_display_complete(self):
        """Filtered slot for CombatDisplay visual completion."""
        self._forward_visual_complete(DisplayTarget.COMBAT_LOG)

    @Slot()
    def on_narrative_display_complete(self):
        """Filtered slot for GameOutputWidget visual completion."""
        self._forward_visual_complete(DisplayTarget.MAIN_GAME_OUTPUT)

    # --- Internal Helpers ---

    def _determine_target_widget(self, event, state):
        if event.target_display == DisplayTarget.COMBAT_LOG:
            return self.mw.combat_display
        elif event.target_display == DisplayTarget.MAIN_GAME_OUTPUT:
            # Ensure narrative view is visible if needed
            if state and state.current_mode != InteractionMode.COMBAT:
                if self.mw.mode_stacked_widget.currentWidget() != self.mw.narrative_view:
                    self.mw.mode_stacked_widget.setCurrentWidget(self.mw.narrative_view)
                    self.mw.narrative_view.setVisible(True)
            return self.mw.game_output
        else:
            if state and state.current_mode == InteractionMode.COMBAT:
                return self.mw.combat_display
            else:
                return self.mw.game_output

    def _handle_ap_update(self, event, state):
        metadata = event.metadata or {}
        entity_id = metadata.get("entity_id")
        
        player_id = None
        if state and state.player:
            player_id = getattr(state.player, 'id', getattr(state.player, 'stats_manager_id', None))

        if entity_id == player_id and self.mw.right_panel.character_sheet:
            current_ap = metadata.get("current_ap", 0.0)
            max_ap = metadata.get("max_ap", 0.0)
            self.mw.right_panel.character_sheet.update_ap_display(current_ap, max_ap)
        
        QTimer.singleShot(0, self._signal_visual_complete_if_needed)

    def _handle_buffer_flush(self, event, target_widget):
        if isinstance(event.content, list) and target_widget == self.mw.combat_display:
            try:
                if hasattr(self.mw.combat_display, '_suppress_visual_complete'):
                    self.mw.combat_display._suppress_visual_complete = True
                for item in event.content:
                    if isinstance(item, dict) and 'text' in item:
                        line_text = str(item.get('text', ''))
                        line_role = item.get('role', event.role or 'gm')
                        if line_text:
                            self.mw.combat_display.append_orchestrated_event_content(line_text, line_role, is_gradual=False)
                    else:
                        self.mw.combat_display.append_orchestrated_event_content(str(item), event.role or 'gm', is_gradual=False)
            except Exception as e:
                logger.error(f"Error during BUFFER_FLUSH replay: {e}", exc_info=True)
            finally:
                if hasattr(self.mw.combat_display, '_suppress_visual_complete'):
                    self.mw.combat_display._suppress_visual_complete = False
            
            QTimer.singleShot(0, self._signal_visual_complete_if_needed)
        else:
            self._signal_visual_complete_if_needed()

    def _handle_ui_bar_update(self, event, state):
        entity_id = event.metadata.get("entity_id")
        bar_type = event.metadata.get("bar_type")
        
        # Player update via CharacterSheet
        player_id = getattr(state.player, 'id', getattr(state.player, 'stats_manager_id', None)) if state and state.player else None
        
        if entity_id == player_id and self.mw.right_panel.character_sheet:
            try:
                if event.type == DisplayEventType.UI_BAR_UPDATE_PHASE1:
                    self.mw.right_panel.character_sheet.player_resource_bar_update_phase1(bar_type, event.metadata)
                elif event.type == DisplayEventType.UI_BAR_UPDATE_PHASE2:
                    self.mw.right_panel.character_sheet.player_resource_bar_update_phase2(bar_type, event.metadata)
            except Exception as e:
                logger.error(f"Error updating CharacterSheet for player bar: {e}")

        # Entity update via CombatDisplay
        entity_widget = None
        if hasattr(self.mw.combat_display, 'allies_panel') and entity_id in self.mw.combat_display.allies_panel.entity_widgets:
            entity_widget = self.mw.combat_display.allies_panel.entity_widgets.get(entity_id)
        elif hasattr(self.mw.combat_display, 'enemies_panel') and entity_id in self.mw.combat_display.enemies_panel.entity_widgets:
            entity_widget = self.mw.combat_display.enemies_panel.entity_widgets.get(entity_id)
        
        animation_invoked = False
        if entity_widget:
            method_name = f"animate_{event.type.name.lower()}"
            try:
                if hasattr(entity_widget, method_name):
                    getattr(entity_widget, method_name)(event.metadata)
                    animation_invoked = True
            except Exception as e:
                logger.error(f"Error invoking {method_name}: {e}")

        if not animation_invoked:
            self._signal_visual_complete_if_needed()
        
        # Safety net
        QTimer.singleShot(10, lambda ev_id=event.event_id: self._complete_if_same_event(ev_id))

    def _handle_combat_log_set_html(self, event, target_widget):
        try:
            if target_widget == self.mw.combat_display and isinstance(event.content, str):
                self.mw.combat_display.log_text.setUpdatesEnabled(False)
                self.mw.combat_display.log_text.setHtml(event.content)
                self.mw.combat_display.log_text.moveCursor(QTextCursor.MoveOperation.End)
                self.mw.combat_display.log_text.ensureCursorVisible()
                self.mw.combat_display.log_text.setUpdatesEnabled(True)
        except Exception as e:
            logger.error(f"Error applying COMBAT_LOG_SET_HTML: {e}")

    def _handle_string_content(self, event, target_widget):
        if target_widget == self.mw.combat_display:
            self.mw.combat_display.append_orchestrated_event_content(
                event_content=event.content,
                event_role=event.role or "system",
                is_gradual=event.gradual_visual_display,
                event_id=event.event_id
            )
        elif target_widget == self.mw.game_output:
            from PySide6.QtCore import QSettings
            # Check dev flag hiding
            try:
                if event.content.strip().startswith("[DEV]"):
                    q_settings = QSettings("RPGGame", "Settings")
                    if not q_settings.value("dev/enabled", False, type=bool):
                        self._signal_visual_complete_if_needed()
                        return
            except Exception:
                pass
            
            # Formats are handled by GameOutputWidget internally based on role mostly, 
            # but we can pass raw text.
            # Append method handles role logic if we used specific methods, 
            # but here we use append_text with role-based format deduction or direct string.
            text_format = None
            if event.role == "system": text_format = self.mw.game_output.system_format
            elif event.role == "gm": text_format = self.mw.game_output.gm_format
            elif event.role == "player": text_format = self.mw.game_output.player_format
            
            self.mw.game_output.append_text(event.content, text_format, event.gradual_visual_display)

    def _forward_visual_complete(self, expected_target):
        """Helper to forward signals to orchestrator if the event target matches."""
        try:
            orch = getattr(self.mw.game_engine, '_combat_orchestrator', None)
            if orch and orch.is_processing_event and orch.current_event:
                if orch.current_event.target_display == expected_target:
                    logger.debug(f"[GUI] Forwarding visual display completion for event {orch.current_event.event_id}")
                    orch._handle_visual_display_complete()
        except Exception as e:
            logger.error(f"Error forwarding visual completion: {e}")

    def _signal_visual_complete_if_needed(self):
        """Signals orchestrator completion immediately (for non-visual events)."""
        if hasattr(self.mw.game_engine, '_combat_orchestrator') and self.mw.game_engine._combat_orchestrator.is_waiting_for_visual:
            self.mw.game_engine._combat_orchestrator._handle_visual_display_complete()

    def _complete_if_same_event(self, event_id: str):
        """Safety net for events that might stall."""
        try:
            orch = getattr(self.mw.game_engine, '_combat_orchestrator', None)
            if orch and getattr(orch, 'is_processing_event', False) and getattr(orch, 'is_waiting_for_visual', False):
                current_id = getattr(orch, 'current_event_id_for_signals', None)
                if current_id == event_id:
                    logger.warning(f"Safety net: Completing event {event_id} to avoid stall.")
                    try:
                        orch._handle_visual_display_complete()
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"_complete_if_same_event guard failed: {e}")