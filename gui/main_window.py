#!/usr/bin/env python3
"""
Main window for the RPG game GUI.
This module provides the MainWindow class that serves as the primary GUI container.
"""

import os
import weakref
from typing import Optional, List, Dict, Any, Tuple

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QDialog, QLabel, QPushButton, 
    QToolButton, QGraphicsOpacityEffect, QMessageBox, QSizePolicy,
    QMenu, QSlider, QWidgetAction, QLineEdit, QTextEdit, QPlainTextEdit, QTabBar
)
from PySide6.QtCore import Qt, Slot, QTimer, QSize, QSettings, QThread, QParallelAnimationGroup, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from core.inventory import get_inventory_manager
from core.inventory.item import Item
from core.inventory.item_enums import EquipmentSlot
from gui.dialogs.game_over_dialog import GameOverDialog
from core.base.engine import get_game_engine
from core.combat.enums import CombatState, CombatStep
from core.interaction.enums import InteractionMode
from core.utils.logging_config import get_logger
from gui.components.game_output import GameOutputWidget
from gui.components.command_input import CommandInputWidget
from gui.components.menu_panel import MenuPanelWidget
from gui.components.right_panel import CollapsibleRightPanel
from gui.components.status_bar import GameStatusBar
from gui.components.combat_display import CombatDisplay
from gui.utils.resource_manager import get_resource_manager
from gui.dialogs.settings.llm_settings_dialog import LLMSettingsDialog
from gui.styles.theme_manager import get_theme_manager
from gui.dialogs.settings.settings_dialog import SettingsDialog
from gui.dialogs.load_game_dialog import LoadGameDialog
from gui.workers import SaveGameWorker, LoadGameWorker, NewGameWorker
from gui.components.loading_bar import LoadingProgressBar
from gui.workers import ArchivistWorker


# New Handlers
from gui.handlers.input_handler import InputHandler
from gui.handlers.display_handler import DisplayHandler

logger = get_logger("GUI")

class MainWindow(QMainWindow):
    """Main window for the RPG game GUI."""
    
    def __init__(self):
        super().__init__()
        
        # --- CURSOR SETUP ---
        self._setup_cursors()
        self.setCursor(self.normal_cursor)
        
        self._previous_mode = None 
        
        self.resource_manager = get_resource_manager()
        self.game_engine = get_game_engine()

        try:
            self.game_engine.main_window_ref = weakref.ref(self)
        except Exception:
            pass

        self.setMinimumSize(1024, 700) 
        self._character_data_for_new_game: Optional[Dict[str, Any]] = None

        # Setup Logic Handlers
        self.input_handler = InputHandler(self)
        self.display_handler = DisplayHandler(self)

        # Set up the UI
        self._setup_ui()
        
        self._apply_link_cursor_to_buttons()
        self._apply_text_cursor_to_text_widgets()

        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self._update_theme)

        # Connect signals and slots
        self._connect_signals()

        self._update_theme()

    def _setup_cursors(self):
        """Load custom cursors from image files."""
        try:
            normal_pixmap = QPixmap("images/gui/cursors/NORMAL.cur")
            link_pixmap = QPixmap("images/gui/cursors/LINK-SELECT.cur")
            text_pixmap = QPixmap("images/gui/cursors/TEXT.cur")

            if normal_pixmap.isNull():
                self.normal_cursor = QCursor(Qt.ArrowCursor)
            else:
                self.normal_cursor = QCursor(normal_pixmap, 0, 0)

            if link_pixmap.isNull():
                self.link_cursor = QCursor(Qt.PointingHandCursor)
            else:
                self.link_cursor = QCursor(link_pixmap, 0, 0)

            if text_pixmap.isNull():
                self.text_cursor = QCursor(Qt.IBeamCursor)
            else:
                self.text_cursor = QCursor(text_pixmap, int(text_pixmap.width() / 2), int(text_pixmap.height() / 2))

        except Exception as e:
            logger.error(f"Error setting up custom cursors: {e}")
            self.normal_cursor = QCursor(Qt.ArrowCursor)
            self.link_cursor = QCursor(Qt.PointingHandCursor)
            self.text_cursor = QCursor(Qt.IBeamCursor)
    
    def _apply_link_cursor_to_buttons(self):
        widgets = self.findChildren(QPushButton) + self.findChildren(QToolButton) + self.findChildren(QTabBar)
        for widget in widgets:
            widget.setCursor(self.link_cursor)

    def _apply_text_cursor_to_text_widgets(self):
        line_edits = [w for w in self.findChildren(QLineEdit) if not w.isReadOnly()]
        for widget in line_edits:
            widget.setCursor(self.text_cursor)

        text_areas = self.findChildren(QTextEdit) + self.findChildren(QPlainTextEdit)
        editable_text_areas = [widget for widget in text_areas if not widget.isReadOnly()]
        
        for widget in editable_text_areas:
            widget.viewport().setCursor(self.text_cursor)

        read_only_text_areas = [widget for widget in text_areas if widget.isReadOnly()]
        for widget in read_only_text_areas:
            widget.viewport().setCursor(self.normal_cursor)

    def _apply_initial_window_state(self):
        settings = QSettings("RPGGame", "Settings")
        window_state = settings.value("display/window_state", "windowed") 
        
        if window_state == "fullscreen":
            self.showFullScreen()
        elif window_state == "maximized":
            self.showMaximized()
        else:
            default_size = QSize(1280, 720)
            windowed_size = settings.value("display/windowed_size", default_size)
            if not isinstance(windowed_size, QSize):
                if isinstance(windowed_size, (tuple, list)) and len(windowed_size) == 2:
                    windowed_size = QSize(windowed_size[0], windowed_size[1])
                elif isinstance(windowed_size, str):
                     try:
                         parts = windowed_size.strip('()').split(',')
                         windowed_size = QSize(int(parts[0]), int(parts[1]))
                     except Exception:
                         windowed_size = default_size 
                else:
                    windowed_size = default_size 

            self.showNormal() 
            self.resize(windowed_size) 
            screen_geometry = self.screen().availableGeometry()
            self.move(screen_geometry.center() - self.rect().center())        

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_initial_state_applied') or not self._initial_state_applied:
             self._apply_initial_window_state()
             self._initial_state_applied = True

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 
            "Exit Game", 
            "Are you sure you want to exit? Unsaved progress will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            settings = QSettings("RPGGame", "Settings")
            current_state_str = "windowed" 
            if self.isFullScreen():
                current_state_str = "fullscreen"
            elif self.isMaximized():
                current_state_str = "maximized"
            
            settings.setValue("display/window_state", current_state_str)
            if current_state_str == "windowed":
                 settings.setValue("display/windowed_size", self.size())
            
            self.game_engine.stop()

            bg_movie = self.background_label.movie()
            if bg_movie:
                bg_movie.stop()

            event.accept()
        else:
            event.ignore()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'background_label'): 
             self.background_label.setGeometry(0, 0, event.size().width(), event.size().height())
        if hasattr(self, 'main_content_widget'):
             self.main_content_widget.setGeometry(0, 0, event.size().width(), event.size().height())
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.setGeometry(self.rect())
    
    def _setup_ui(self):
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
        self.game_output.text_edit.setCursor(self.normal_cursor) 
        self.game_output.text_edit.viewport().setCursor(self.normal_cursor) 
        
        self.narrative_command_input = CommandInputWidget()
        self.narrative_command_input.setObjectName("NarrativeCommandInput")
        self.game_output.set_command_input_widget(self.narrative_command_input)
        self.narrative_layout.addWidget(self.game_output, 1)
        
        self.combat_display = CombatDisplay()
        self.combat_display.playerActionSelected.connect(self.input_handler.process_command)
        self.combat_display.log_text.setCursor(self.normal_cursor) 
        self.combat_display.log_text.viewport().setCursor(self.normal_cursor)
        
        self.combat_command_input = CommandInputWidget()
        self.combat_command_input.setObjectName("CombatCommandInput")
        self.combat_display.set_command_input_widget(self.combat_command_input)
        self.combat_layout.addWidget(self.combat_display, 1)
        
        self.mode_stacked_widget.addWidget(self.narrative_view)
        self.mode_stacked_widget.addWidget(self.combat_view)
        
        self.center_widget = QWidget()
        center_layout = QVBoxLayout(self.center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.mode_stacked_widget)
        
        self.mode_stacked_widget.setCurrentWidget(self.narrative_view)
        
        self.right_panel = CollapsibleRightPanel()
        
        self.content_layout.addWidget(self.menu_panel, 0) 
        self.content_layout.addWidget(self.center_widget, 1) 
        self.content_layout.addWidget(self.right_panel, 0) 
        
        self.main_layout.addLayout(self.content_layout, 1)
        
        self.music_controls = self._create_music_controls()
        
        self.status_bar = GameStatusBar()
        self.setStatusBar(self.status_bar)

        self._load_and_apply_initial_background()
        self._initialize_panel_effects() 
        
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

        self.loading_overlay = QWidget(self.centralWidget())
        self.loading_overlay.setObjectName("loadingOverlay")
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.85);")
        
        loading_layout = QVBoxLayout(self.loading_overlay)
        loading_layout.setAlignment(Qt.AlignCenter)
        loading_layout.setSpacing(20)

        self.video_widget = QVideoWidget(self.loading_overlay)
        self.video_widget.setFixedSize(720, 720)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.audio_output.setVolume(0) 

        self.fallback_loading_bar = LoadingProgressBar(self.loading_overlay)
        self.fallback_loading_bar.setFixedSize(720, 20)

        self.loading_label = QLabel("Loading...", self.loading_overlay)
        self.loading_label.setStyleSheet("color: white; font-size: 24px; background-color: transparent;")
        self.loading_label.setAlignment(Qt.AlignCenter)

        loading_layout.addWidget(self.video_widget, 0, Qt.AlignCenter)
        loading_layout.addWidget(self.fallback_loading_bar, 0, Qt.AlignCenter)
        self.loading_overlay.hide()

        self.loading_opacity_effect = QGraphicsOpacityEffect(self.loading_overlay)
        self.loading_overlay.setGraphicsEffect(self.loading_opacity_effect)
        self.loading_opacity_effect.setOpacity(0.0)

        # Connect specific journal signals
        if hasattr(self.right_panel, 'journal_panel'):
            # When manual notes are saved, ensure GameState is updated so save game works
            self.right_panel.journal_panel.journal_updated.connect(self._on_journal_data_updated)

    def _on_journal_data_updated(self, new_data):
        """Syncs GUI journal changes back to the GameState."""
        state = self.game_engine.state_manager.current_state
        if state:
            state.journal = new_data

    def trigger_archivist_update(self, topic: str):
        """
        Called by JournalPanel to trigger an AI update for a Codex entry.
        """
        
        state = self.game_engine.state_manager.current_state
        if not state: return

        # 1. Get Agent
        agent = self.game_engine._agent_manager._archivist_agent
        
        # 2. Prepare Data
        existing_entry = state.journal.get("codex", {}).get(topic, {}).get("content", "")
        # Get full conversation history
        history = state.conversation_history 
        
        # 3. Setup Worker
        self.archivist_thread = QThread()
        self.archivist_worker = ArchivistWorker(agent, existing_entry, history, topic)
        self.archivist_worker.moveToThread(self.archivist_thread)
        
        # 4. Connect Signals
        self.archivist_thread.started.connect(self.archivist_worker.run)
        self.archivist_worker.finished.connect(self._on_archivist_finished)
        self.archivist_worker.error.connect(self._on_archivist_error)
        self.archivist_worker.finished.connect(self.archivist_thread.quit)
        self.archivist_worker.finished.connect(self.archivist_worker.deleteLater)
        self.archivist_thread.finished.connect(self.archivist_thread.deleteLater)
        
        # 5. Start
        self.archivist_thread.start()
        self.game_output.append_system_message(f"Archivist is updating entry for '{topic}'...")

    def _on_archivist_finished(self, topic, content):
        """Handle successful Codex update."""
        state = self.game_engine.state_manager.current_state
        if state:
            # Update state
            if "codex" not in state.journal: state.journal["codex"] = {}
            
            # Preserve metadata if exists, update content
            if topic not in state.journal["codex"]:
                state.journal["codex"][topic] = {"type": "general", "created_at": 0}
            
            state.journal["codex"][topic]["content"] = content
            
            # Refresh UI
            self.right_panel.journal_panel.update_journal(state.journal)
            
            # Reset button state in panel
            self.right_panel.journal_panel.btn_update_entry.setText("Update Entry (AI)")
            self.right_panel.journal_panel.btn_update_entry.setEnabled(True)
            
            self.game_output.append_system_message(f"Codex updated: {topic}")

    def _on_archivist_error(self, error_msg):
        logger.error(f"Archivist failed: {error_msg}")
        self.right_panel.journal_panel.btn_update_entry.setText("Update Failed")
        self.right_panel.journal_panel.btn_update_entry.setEnabled(True)

    def _create_music_controls(self):
        music_widget = QWidget()
        music_layout = QHBoxLayout(music_widget)
        music_layout.setContentsMargins(0, 0, 0, 0)
        music_layout.setSpacing(5)
        
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
        
        music_layout.addWidget(play_pause_button)
        music_layout.addWidget(next_button)
        music_layout.addWidget(volume_button)
        
        self.main_layout.insertWidget(0, music_widget, 0, Qt.AlignRight)
        
        try:
            self._btn_music_play_pause = play_pause_button
            self._btn_music_next = next_button
            self._btn_music_volume = volume_button

            def _on_play_pause():
                try:
                    s = QSettings("RPGGame", "Settings")
                    director = getattr(self.game_engine, 'get_music_director', lambda: None)()
                    if director:
                        currently_muted = bool(getattr(director, '_muted', False))
                        director.set_muted(not currently_muted)
                        s.setValue("sound/enabled", not (not currently_muted)) 
                        s.sync()
                except Exception:
                    pass
            play_pause_button.clicked.connect(_on_play_pause)

            def _on_next():
                try:
                    director = getattr(self.game_engine, 'get_music_director', lambda: None)()
                    if director:
                        director.next_track("user_skip_gui")
                except Exception:
                    pass
            next_button.clicked.connect(_on_next)

            self._music_volume_menu = QMenu(self)
            vol_container = QWidget(self._music_volume_menu)
            vol_layout = QHBoxLayout(vol_container)
            vol_layout.setContentsMargins(10, 8, 10, 8)
            vol_layout.setSpacing(8)
            vol_label = QLabel("Master")
            self._music_slider = QSlider(Qt.Horizontal, vol_container)
            self._music_slider.setRange(0, 100)
            self._music_slider.setFixedWidth(150)
            self._music_slider.setSingleStep(2)
            self._music_slider.setPageStep(10)
            self._music_slider.setToolTip("Master volume (affects all sounds)")
            self._music_slider_value_label = QLabel("100%")
            vol_layout.addWidget(vol_label)
            vol_layout.addWidget(self._music_slider)
            vol_layout.addWidget(self._music_slider_value_label)
            vol_action = QWidgetAction(self._music_volume_menu)
            vol_action.setDefaultWidget(vol_container)
            self._music_volume_menu.addAction(vol_action)

            self._music_volume_menu.addSeparator()
            open_settings_action = self._music_volume_menu.addAction("Open Sound Settings…")
            open_settings_action.triggered.connect(self._show_settings_dialog)

            def _apply_master_volume(value: int):
                try:
                    self._music_slider_value_label.setText(f"{int(value)}%")
                    s = QSettings("RPGGame", "Settings")
                    master = int(value)
                    music  = int(s.value("sound/music_volume", 100))
                    effects= int(s.value("sound/effects_volume", 100))
                    director = getattr(self.game_engine, 'get_music_director', lambda: None)()
                    if director:
                        director.set_volumes(master, music, effects)
                    s.setValue("sound/master_volume", master)
                    s.sync()
                except Exception:
                    pass
            self._music_slider.valueChanged.connect(_apply_master_volume)

            def _on_open_volume_menu():
                s = QSettings("RPGGame", "Settings")
                try:
                    current_master = int(s.value("sound/master_volume", 100))
                except Exception:
                    current_master = 100
                self._music_slider.blockSignals(True)
                self._music_slider.setValue(current_master)
                self._music_slider_value_label.setText(f"{current_master}%")
                self._music_slider.blockSignals(False)
                pos = volume_button.mapToGlobal(QPoint(0, volume_button.height()))
                try:
                    self._music_volume_menu.exec(pos)
                except Exception:
                    self._music_volume_menu.popup(pos)
            volume_button.clicked.connect(_on_open_volume_menu)
        except Exception:
            pass

        return music_widget
    
    def _connect_signals(self):
        """Connect signals and slots using specific handlers."""
        # Input Handler
        self.narrative_command_input.command_submitted.connect(self.input_handler.process_command)
        self.combat_command_input.command_submitted.connect(self.input_handler.process_command)

        # Display Handler
        self.game_engine.orchestrated_event_to_ui.connect(self.display_handler.process_event)
        self.game_engine.output_generated.connect(self.display_handler.handle_game_output)
        
        # Display Handler (Visual Completion Signals)
        # Disconnect old logic if present just in case
        try:
            self.combat_display.visualDisplayComplete.disconnect()
            self.game_output.visualDisplayComplete.disconnect()
        except Exception: pass
        self.combat_display.visualDisplayComplete.connect(self.display_handler.on_combat_display_complete)
        self.game_output.visualDisplayComplete.connect(self.display_handler.on_narrative_display_complete)

        # UI Navigation Signals
        self.menu_panel.new_game_requested.connect(self._show_new_game_dialog)
        self.menu_panel.save_game_requested.connect(self._show_save_game_dialog)
        self.menu_panel.load_game_requested.connect(self._show_load_game_dialog)
        self.menu_panel.settings_requested.connect(self._show_settings_dialog)
        self.menu_panel.llm_settings_requested.connect(self._show_llm_settings_dialog)
        self.menu_panel.exit_requested.connect(self.close)

        self.right_panel.tab_changed.connect(self._handle_tab_change)

        # Action Signals
        if hasattr(self.right_panel, 'inventory_panel'):
            self.right_panel.inventory_panel.item_use_requested.connect(self._handle_item_use_requested)
            self.right_panel.inventory_panel.item_examine_requested.connect(self._handle_item_examine_requested)
            self.right_panel.inventory_panel.item_equip_requested.connect(self._handle_item_equip_requested)
            self.right_panel.inventory_panel.item_unequip_requested.connect(self._handle_item_unequip_requested)
            self.right_panel.inventory_panel.item_drop_requested.connect(self._handle_item_drop_requested)

        if hasattr(self.right_panel, 'grimoire_panel'):
            try:
                self.right_panel.grimoire_panel.cast_spell_requested.disconnect(self._handle_cast_spell_requested)
            except Exception: pass
            self.right_panel.grimoire_panel.cast_spell_requested.connect(self._handle_cast_spell_requested)

        if hasattr(self.right_panel, 'character_sheet'):
            self.right_panel.character_sheet.item_unequip_from_slot_requested.connect(self._handle_item_unequip_from_slot_requested)
            self.right_panel.character_sheet.item_examine_requested.connect(self._handle_item_examine_requested)
            self.right_panel.character_sheet.item_drop_from_slot_requested.connect(self._handle_item_drop_from_slot_requested)

        if self.game_engine.state_manager.stats_manager:
            try:
                self.game_engine.state_manager.stats_manager.stats_changed.disconnect(self._handle_stats_update)
            except (TypeError, RuntimeError): pass 
            self.game_engine.state_manager.stats_manager.stats_changed.connect(self._handle_stats_update)
        
        if hasattr(self.game_engine._combat_orchestrator, 'resume_combat_manager') and hasattr(self.game_engine, 'on_orchestrator_idle_and_combat_manager_resumed'):
             self.game_engine._combat_orchestrator.resume_combat_manager.connect(self.game_engine.on_orchestrator_idle_and_combat_manager_resumed)

    def _handle_tab_change(self, index):
        if index == 0:  # Character tab
            self.right_panel.update_character()
        elif index == 1:  # Inventory tab
            if self.game_engine.state_manager.current_state:
                inventory_manager = get_inventory_manager()
                if inventory_manager:
                    self.right_panel.update_inventory(inventory_manager)
        elif index == 2:  # Journal tab
            if self.game_engine.state_manager.current_state:
                if not hasattr(self.game_engine.state_manager.current_state, "journal"):
                    self.game_engine.state_manager.current_state.journal = {
                        "character": "", "quests": {}, "notes": []
                    }
                self.right_panel.update_journal(self.game_engine.state_manager.current_state.journal)
        elif index == 3:  # Grimoire tab
            self.right_panel.update_grimoire()
    
    # --- Action Handlers (Inventory / Spell) ---
    
    @Slot(str)
    def _handle_item_use_requested(self, item_id: str):
        self.game_output.append_system_message(f"Attempting to use item: {item_id} (Handler not fully implemented).")
        self.input_handler.process_command(f"use {item_id}")

    @Slot(str)
    def _handle_item_examine_requested(self, item_id: str):
        inventory_manager = get_inventory_manager()
        item = inventory_manager.get_item_details_for_dialog(item_id)
        if item:
            from gui.dialogs.item_info_dialog import ItemInfoDialog 
            dialog = ItemInfoDialog(item, parent=self)
            dialog.exec()
        else:
            self.game_output.append_system_message(f"Could not find details for item ID: {item_id}", gradual=False)
        self._update_ui()

    @Slot(str) 
    def _handle_item_unequip_requested(self, item_identifier: str): 
        inventory_manager = get_inventory_manager()
        item_to_unequip = inventory_manager.get_item(item_identifier) 
        if not item_to_unequip: 
            self._update_ui()
            return
        
        slot_found: Optional[EquipmentSlot] = None
        for slot_enum_loop, item_obj_loop in inventory_manager.equipment.items(): 
            if item_obj_loop and isinstance(item_obj_loop, Item) and item_obj_loop.id == item_to_unequip.id:
                slot_found = slot_enum_loop
                break
        
        if slot_found:
            inventory_manager.unequip_item(slot_found)
        self._update_ui()

    @Slot(str)
    def _handle_item_drop_requested(self, item_id: str):
        inventory_manager = get_inventory_manager()
        item = inventory_manager.get_item(item_id)
        if not item:
            self._update_ui()
            return

        if inventory_manager.is_item_equipped(item_id):
            reply = QMessageBox.question(
                self, "Confirm Drop Equipped Item",
                f"'{item.name}' is currently equipped. Are you sure you want to drop it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return 

            slot_to_unequip: Optional[EquipmentSlot] = None
            for slot_enum, equipped_item_obj in inventory_manager.equipment.items(): 
                if equipped_item_obj and isinstance(equipped_item_obj, Item) and equipped_item_obj.id == item_id:
                    slot_to_unequip = slot_enum
                    break
            if slot_to_unequip:
                inventory_manager.unequip_item(slot_to_unequip)
                self._update_ui() 
            else:
                return
        self.input_handler.process_command(f"drop {item_id}") 

    @Slot(str) 
    def _handle_item_equip_requested(self, item_id: str): 
        inventory_manager = get_inventory_manager()
        item = inventory_manager.get_item(item_id)
        if item and item.is_equippable:
            inventory_manager.equip_item(item.id)
        self._update_ui()

    @Slot(EquipmentSlot)
    def _handle_item_unequip_from_slot_requested(self, slot_to_unequip: EquipmentSlot):
        get_inventory_manager().unequip_item(slot_to_unequip)
        self._update_ui()

    @Slot(str, object)
    def _handle_cast_spell_requested(self, spell_id: str, target_id: object):
        try:
            state = self.game_engine.state_manager.current_state
            if not state or state.current_mode != InteractionMode.COMBAT or not getattr(state, 'combat_manager', None):
                self.game_output.append_system_message("Casting is only available during combat.", gradual=False)
                return
            cm = state.combat_manager
            if cm.current_step != CombatStep.AWAITING_PLAYER_INPUT:
                self.game_output.append_system_message("Please wait until your turn to act.", gradual=False)
                return
            performer_id = getattr(cm, '_player_entity_id', None)
            if not performer_id:
                self.game_output.append_system_message("Cannot cast: player entity not set in combat.", gradual=False)
                return
            try:
                from core.magic.spell_catalog import get_spell_catalog
                cat = get_spell_catalog()
                sp = cat.get_spell_by_id(spell_id)
                data = getattr(sp, 'data', {}) if sp else {}
                cost_mp = float(data.get('mana_cost', data.get('cost', 0)) or 0)
            except Exception:
                cost_mp = 0.0
            from core.combat.combat_action import SpellAction
            action = SpellAction(
                performer_id=performer_id, spell_name=str(spell_id),
                target_ids=[str(target_id)] if target_id else [],
                cost_mp=cost_mp, dice_notation="", description=f"Casting {spell_id}"
            )
            cm._pending_action = action
            cm.current_step = CombatStep.RESOLVING_ACTION_MECHANICS
            cm.process_combat_step(self.game_engine)
        except Exception as e:
            logger.error(f"Failed to handle UI cast for {spell_id}: {e}", exc_info=True)
            self.game_output.append_system_message("System error preparing spell cast.", gradual=False)

    @Slot(EquipmentSlot, str)
    def _handle_item_drop_from_slot_requested(self, slot_to_unequip: EquipmentSlot, item_id_to_drop: str):
        inventory_manager = get_inventory_manager()
        item = inventory_manager.get_item(item_id_to_drop)
        item_name = item.name if item else "the item"

        reply = QMessageBox.question(
            self, "Confirm Drop",
            f"Are you sure you want to drop the equipped item '{item_name}' from your {slot_to_unequip.value.replace('_',' ')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if inventory_manager.unequip_item(slot_to_unequip):
                self.input_handler.process_command(f"drop {item_id_to_drop}") 
        self._update_ui()

    @Slot(dict)
    def _handle_stats_update(self, stats_data: dict):
        state = self.game_engine.state_manager.current_state
        if state:
            if self.right_panel:
                self.right_panel.update_character(state.player)
            if state.current_mode == InteractionMode.COMBAT:
                self.combat_display.update_display(state) 

    def _update_ui(self):
        """Update UI components based on the current game state."""
        state = self.game_engine.state_manager.current_state
        if not state:
            self.status_bar.update_status(location="Not in game", game_time="", calendar="", mode="N/A")
            if hasattr(self.right_panel, 'character_sheet') and self.right_panel.character_sheet: 
                self.right_panel.character_sheet._clear_stat_displays() 
            
            inventory_manager_for_clear = get_inventory_manager() 
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
            except Exception: pass

        if game_over and not hasattr(self, '_game_over_dialog_shown'):
            self._game_over_dialog_shown = True 
            self.narrative_command_input.setEnabled(False)
            self.combat_command_input.setEnabled(False)

            dialog = GameOverDialog(parent=self)
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

        is_transitioning_to_combat = getattr(state, 'is_transitioning_to_combat', False)
        combat_narrative_buffer = getattr(state, 'combat_narrative_buffer', [])

        if current_mode_name == "COMBAT":
            view_switched_this_call = False
            if self.mode_stacked_widget.currentWidget() != self.combat_view:
                self.mode_stacked_widget.setCurrentWidget(self.combat_view)
                view_switched_this_call = True

            self.combat_view.setVisible(True) 
            self.combat_view.update() 
            self.mode_stacked_widget.update() 
            
            if view_switched_this_call:
                if hasattr(self.right_panel, 'tab_widget'): 
                    self.right_panel.tab_widget.setCurrentIndex(0)

            if is_transitioning_to_combat and combat_narrative_buffer:
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
            
            self.combat_display.update_display(state) 
            
            if state.player and hasattr(self.right_panel, 'update_character'): self.right_panel.update_character(state.player) 

            combat_manager = state.combat_manager 
            if view_switched_this_call and combat_manager and combat_manager.current_step == CombatStep.STARTING_COMBAT:
                if not self.game_engine._combat_orchestrator.is_processing_event and not self.game_engine._combat_orchestrator.event_queue:
                    QTimer.singleShot(10, lambda cm=combat_manager, eng=self.game_engine: cm.process_combat_step(eng))

        else: 
            if self.mode_stacked_widget.currentWidget() != self.narrative_view:
                self.mode_stacked_widget.setCurrentWidget(self.narrative_view)
            
            self.narrative_view.setVisible(True) 
            self.narrative_view.update()
            self.mode_stacked_widget.update()
            
            # Removed: self.combat_display.update_display(state)
            # Optimization: Do not update combat display when in Narrative mode.
            # This prevents errors if combat state is cleared or partial.

            if is_transitioning_to_combat: 
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
        if hasattr(self.right_panel, 'update_inventory'): self.right_panel.update_inventory(inventory_manager)
        
        journal_data = getattr(state, "journal", None)
        if journal_data is not None and hasattr(self.right_panel, 'update_journal'): self.right_panel.update_journal(journal_data)

        if hasattr(self.right_panel, 'update_grimoire'):
            self.right_panel.update_grimoire()

        self.status_bar.update_status(
            location=getattr(state.player, 'current_location', 'Unknown') if state.player else 'N/A',
            game_time=getattr(state.world, 'time_of_day', ''),
            calendar=getattr(state.world, 'calendar_string', ''),
            mode=current_mode_name 
        )
        try:
            ctx_payload = self.game_engine.get_game_context() if hasattr(self.game_engine, 'get_game_context') else {}
            self.status_bar.update_context(ctx_payload)
        except Exception:
            pass

    def _show_new_game_dialog(self):
        from gui.dialogs.character_creation_dialog import CharacterCreationDialog
        dialog = CharacterCreationDialog(parent=self)
        if dialog.exec():
            character_data = dialog.get_character_data()
            if not character_data: 
                return
            self._start_panel_animations(character_data)

    def _initialize_panel_effects(self):
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

    def _start_panel_animations(self, character_data: dict):
        self._initialize_panel_effects()
        
        self.center_widget.setVisible(True)
        self.right_panel.setVisible(True)
        self.status_bar.setVisible(True)

        self.anim_group = QParallelAnimationGroup(self)
        
        anim_center = QPropertyAnimation(self.center_opacity_effect, b"opacity")
        anim_center.setDuration(1500)
        anim_center.setStartValue(0.0)
        anim_center.setEndValue(1.0)
        anim_center.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim_group.addAnimation(anim_center)
        
        anim_right = QPropertyAnimation(self.right_panel_opacity_effect, b"opacity")
        anim_right.setDuration(1500)
        anim_right.setStartValue(0.0)
        anim_right.setEndValue(1.0)
        anim_right.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim_group.addAnimation(anim_right)

        anim_status = QPropertyAnimation(self.status_bar_opacity_effect, b"opacity")
        anim_status.setDuration(1000) 
        anim_status.setStartValue(0.0)
        anim_status.setEndValue(1.0)
        self.anim_group.addAnimation(anim_status)

        self.anim_group.finished.connect(lambda: self._on_panel_animations_finished(character_data))
        self.anim_group.start()

    def _on_panel_animations_finished(self, character_data: dict):
        self.center_widget.setEnabled(True)
        self.right_panel.setEnabled(True)
        self.status_bar.setEnabled(True)
        self.start_new_game(character_data)

    def start_new_game(self, character_data: dict):
        self.game_output.clear()
        
        worker_character_data = character_data.copy()
        stats_instance = worker_character_data.get("stats")
        if hasattr(stats_instance, 'get_base_stats'):
            character_stats = stats_instance.get_base_stats()
            worker_character_data['stats'] = character_stats
        
        self._show_loading_overlay("Starting new game...", origin_id=worker_character_data.get('origin_id'))

        self.new_game_thread = QThread()
        self.new_game_worker = NewGameWorker(self.game_engine, worker_character_data)
        self.new_game_worker.moveToThread(self.new_game_thread)
        self.new_game_thread.started.connect(self.new_game_worker.run)
        self.new_game_worker.finished.connect(self._on_new_game_finished)
        self.new_game_worker.error.connect(self._on_new_game_error)
        self.new_game_worker.finished.connect(self.new_game_thread.quit)
        self.new_game_worker.finished.connect(self.new_game_worker.deleteLater)
        self.new_game_thread.finished.connect(self.new_game_thread.deleteLater)
        self.new_game_thread.start()

    def _on_new_game_finished(self, initial_narration: str):
        self._hide_loading_overlay()
        if initial_narration:
            self.game_output.append_gm_message(initial_narration, gradual=True)
        else:
            self.game_output.append_system_message("A new world awaits...", gradual=False)
        self._update_ui()
    
    def _on_new_game_error(self, error_msg):
        self._hide_loading_overlay()
        QMessageBox.critical(self, "New Game Failed", f"Failed to start new game: {error_msg}")
        self._reset_ui_after_error()

    def _reset_ui_after_error(self):
        self.center_widget.setVisible(False)
        self.center_widget.setEnabled(False)
        if hasattr(self, 'center_opacity_effect'): self.center_opacity_effect.setOpacity(0.0)
        
        self.right_panel.setVisible(False)
        self.right_panel.setEnabled(False)
        if hasattr(self, 'right_panel_opacity_effect'): self.right_panel_opacity_effect.setOpacity(0.0)

        self.status_bar.setVisible(False)
        self.status_bar.setEnabled(False)
        if hasattr(self, 'status_bar_opacity_effect'): self.status_bar_opacity_effect.setOpacity(0.0)

    def _show_save_game_dialog(self):
        if not self.game_engine.state_manager.current_state:
            QMessageBox.warning(self, "Cannot Save", "There is no active game to save.")
            return

        from gui.dialogs.save_game_dialog import SaveGameDialog
        dialog = SaveGameDialog(parent=self)
        if dialog.exec():
            save_name = dialog.save_name_edit.text()
            if not save_name:
                QMessageBox.warning(self, "Invalid Name", "Save name cannot be empty.")
                return

            self._show_loading_overlay(f"Saving game: {save_name}...")

            self.save_thread = QThread()
            self.save_worker = SaveGameWorker(self.game_engine, save_name)
            self.save_worker.moveToThread(self.save_thread)
            self.save_thread.started.connect(self.save_worker.run)
            self.save_worker.finished.connect(self._on_save_finished)
            self.save_worker.error.connect(lambda msg: self._on_worker_error(msg, context="save"))
            self.save_worker.finished.connect(self.save_thread.quit)
            self.save_worker.finished.connect(self.save_worker.deleteLater)
            self.save_thread.finished.connect(self.save_thread.deleteLater)
            self.save_thread.start()

    def _on_save_finished(self, saved_path):
        self._hide_loading_overlay()
        QMessageBox.information(self, "Game Saved", f"Game saved successfully to {saved_path}")

    def _show_load_game_dialog(self):
        dialog = LoadGameDialog(parent=self)
        if dialog.exec():
            save_filename = dialog.selected_save
            origin_id = dialog.selected_origin_id
            if save_filename:
                self.game_output.clear()
                self._show_loading_overlay(f"Loading game: {save_filename}", origin_id=origin_id)

                self.load_thread = QThread()
                self.load_worker = LoadGameWorker(self.game_engine, save_filename)
                self.load_worker.moveToThread(self.load_thread)
                self.load_thread.started.connect(self.load_worker.run)
                self.load_worker.finished.connect(self._on_load_finished)
                self.load_worker.error.connect(lambda msg: self._on_worker_error(msg, context="load"))
                self.load_worker.finished.connect(self.load_thread.quit)
                self.load_worker.finished.connect(self.load_worker.deleteLater)
                self.load_thread.finished.connect(self.load_thread.deleteLater)
                self.load_thread.start()

    def _on_load_finished(self):
        self._hide_loading_overlay()
        self._show_game_panels_for_loaded_game()
        self._update_ui()
        QMessageBox.information(self, "Game Loaded", "Game loaded successfully.")

    def _show_game_panels_for_loaded_game(self):
        self._initialize_panel_effects()
        
        self.center_widget.setVisible(True)
        self.center_widget.setEnabled(True)
        if hasattr(self, 'center_opacity_effect'):
            self.center_opacity_effect.setOpacity(1.0)
        
        self.right_panel.setVisible(True)
        self.right_panel.setEnabled(True)
        if hasattr(self, 'right_panel_opacity_effect'):
            self.right_panel_opacity_effect.setOpacity(1.0)
        if not self.right_panel.isExpanded():
            self.right_panel.setExpanded(True)
        
        self.status_bar.setVisible(True)
        self.status_bar.setEnabled(True)
        if hasattr(self, 'status_bar_opacity_effect'):
            self.status_bar_opacity_effect.setOpacity(1.0)

    def _load_and_apply_initial_background(self):
        settings = QSettings("RPGGame", "Settings")
        saved_filename = settings.value("style/background_filename", None)

        available_backgrounds = self.resource_manager.list_background_names() 
        final_filename = None

        if saved_filename:
            found = False
            for name, ext in available_backgrounds:
                if f"{name}{ext}" == saved_filename:
                    final_filename = saved_filename
                    found = True
                    break
            if not found:
                saved_filename = None 

        if not final_filename and available_backgrounds:
            first_name, first_ext = available_backgrounds[0] 
            final_filename = f"{first_name}{first_ext}"

        self.update_background(final_filename) 

    @Slot(str)
    def update_background(self, filename: Optional[str]):
        current_movie = self.background_label.movie()
        if current_movie:
            current_movie.stop()
            self.background_label.setMovie(None)
        self.background_label.setPixmap(QPixmap())
        self.background_container.setAutoFillBackground(False) 
        self.background_label.setProperty("current_background", None) 

        if not filename:
            self.background_label.setStyleSheet("background-color: #1E1E1E;")
            return

        name, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        if ext_lower == ".png":
            pixmap = self.resource_manager.get_background_pixmap(name)
            if not pixmap.isNull():
                self.background_label.setPixmap(pixmap) 
                self.background_label.setStyleSheet("") 
                self.background_label.setProperty("current_background", filename)
            else:
                self.background_label.setStyleSheet("background-color: #1E1E1E;")

        elif ext_lower == ".gif":
            movie = self.resource_manager.get_background_movie(name)
            if movie.isValid():
                self.background_label.setMovie(movie)
                movie.start()
                self.background_label.setStyleSheet("") 
                self.background_label.setProperty("current_background", filename)
            else:
                self.background_label.setStyleSheet("background-color: #1E1E1E;")
        else:
            self.background_label.setStyleSheet("background-color: #1E1E1E;") 

    def _on_worker_error(self, error_message: str, context: str = "unknown"):
        logger.error(f"Worker error (context: {context}): {error_message}")
        if context in ["save", "load"]:
            self._hide_loading_overlay()
            QMessageBox.warning(self, "Operation Failed", f"The operation failed: {error_message}")
        else:
            self._hide_loading_overlay()
            QMessageBox.critical(self, "Error", f"A critical error occurred: {error_message}")
            self._reset_ui_after_error()

    def _show_loading_overlay(self, text: str, origin_id: Optional[str] = None):
        self.loading_label.setText(text)
        self.loading_overlay.setGeometry(self.rect())

        video_path_abs = ""
        if origin_id:
            video_path_rel = os.path.join("images", "gui", f"{origin_id}_loading.mp4")
            video_path_abs = os.path.abspath(video_path_rel)

        if origin_id and os.path.exists(video_path_abs):
            self.video_widget.setVisible(True)
            self.fallback_loading_bar.setVisible(False)
            self.fallback_loading_bar.stop_animation()
            
            from PySide6.QtCore import QUrl
            self.player.setSource(QUrl.fromLocalFile(video_path_abs))
            self.player.play()
        else:
            self.video_widget.setVisible(False)
            self.fallback_loading_bar.setVisible(True)
            self.fallback_loading_bar.start_animation()
            self.player.stop()

        self.loading_overlay.show()
        self.loading_overlay.raise_()

        self.fade_in_anim = QPropertyAnimation(self.loading_opacity_effect, b"opacity")
        self.fade_in_anim.setDuration(300)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_in_anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _hide_loading_overlay(self):
        self.player.stop()
        self.fallback_loading_bar.stop_animation()
        
        self.fade_out_anim = QPropertyAnimation(self.loading_opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_out_anim.finished.connect(self.loading_overlay.hide)
        self.fade_out_anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _show_settings_dialog(self):
        if not hasattr(self, '_settings_dialog'):
            self._settings_dialog = SettingsDialog(parent=self)

        dialog = self._settings_dialog
        
        connected = False
        if hasattr(dialog, 'background_tab') and hasattr(dialog.background_tab, 'preview_background_changed'):
            try:
                dialog.background_tab.preview_background_changed.connect(self.update_background)
                connected = True
            except Exception: pass

        saved = False
        try:
            result = dialog.exec()
            if result == QDialog.Accepted: 
                saved = True
        except Exception as e:
             QMessageBox.critical(self, "Error", f"Failed to execute settings dialog:\n{e}")
        finally:
            if connected:
                try:
                    dialog.background_tab.preview_background_changed.disconnect(self.update_background)
                except Exception: pass

        if saved: 
            settings = SettingsDialog.get_settings() 

            try:
                q_settings = QSettings("RPGGame", "Settings")
                dev_enabled = q_settings.value("dev/enabled", False, type=bool)
                if hasattr(self, 'combat_display') and hasattr(self.combat_display, 'dev_controls_container'):
                    self.combat_display.dev_controls_container.setVisible(bool(dev_enabled))
                if hasattr(self, 'right_panel') and hasattr(self.right_panel, 'set_dev_context_tab_enabled'):
                    self.right_panel.set_dev_context_tab_enabled(bool(dev_enabled))
                if hasattr(self.game_engine, '_combat_orchestrator') and hasattr(self.game_engine._combat_orchestrator, 'toggle_dev_step_mode'):
                    self.game_engine._combat_orchestrator.toggle_dev_step_mode(False)
            except Exception: pass

            resolution = settings["display"]["windowed_size"] 
            current_state = settings["display"]["window_state"]

            if current_state == "fullscreen":
                if not self.isFullScreen(): self.showFullScreen()
            elif current_state == "maximized":
                 if not self.isMaximized(): self.showMaximized()
            else: 
                 if self.isFullScreen() or self.isMaximized(): self.showNormal()
                 if QSize(resolution[0], resolution[1]) != self.size():
                     self.resize(resolution[0], resolution[1]) 

            self._update_theme()

            q_settings = QSettings("RPGGame", "Settings")
            saved_filename = q_settings.value("style/background_filename", None)
            if saved_filename:
                 self.update_background(saved_filename)

            try:
                if hasattr(self.game_engine, 'reload_autosave_settings'):
                    self.game_engine.reload_autosave_settings()
            except Exception: pass

            try:
                master = int(q_settings.value("sound/master_volume", 100))
                music  = int(q_settings.value("sound/music_volume", 100))
                effects= int(q_settings.value("sound/effects_volume", 100))
                enabled= q_settings.value("sound/enabled", True, type=bool)
                director = getattr(self.game_engine, 'get_music_director', lambda: None)()
                if director:
                    director.set_volumes(master, music, effects)
                    director.set_muted(not bool(enabled))
            except Exception: pass

            self.game_output.append_system_message("Settings saved successfully.")

    def _show_llm_settings_dialog(self):
        if not hasattr(self, '_llm_settings_dialog'):
            self._llm_settings_dialog = LLMSettingsDialog(parent=self)
            self._llm_settings_dialog.settings_saved.connect(self._on_llm_settings_saved)
        self._llm_settings_dialog.exec()
    
    def _on_llm_settings_saved(self):
        is_llm_enabled = self.game_engine._use_llm
        if is_llm_enabled:
            self.game_output.append_system_message("LLM processing is now enabled.")
        else:
            self.game_output.append_system_message("LLM processing is now disabled.")

    def _load_last_save(self):
        from core.utils.save_manager import SaveManager
        save_manager = SaveManager()
        try:
            saves = save_manager.get_recent_saves(count=10, include_backups=False) 
            last_manual_save = None
            for save in saves:
                 if not save.auto_save:
                      last_manual_save = save
                      break 

            if last_manual_save:
                save_filename = f"{last_manual_save.save_id}/{SaveManager.STATE_FILENAME}" 
                save_id = last_manual_save.save_id 

                try:
                    if hasattr(self.game_engine, '_combat_orchestrator') and self.game_engine._combat_orchestrator:
                        self.game_engine._combat_orchestrator.clear_queue_and_reset_flags()
                except Exception: pass
                
                try:
                    self.game_output.clear()
                    self.combat_display.clear_display()
                except Exception: pass
                
                try:
                    if hasattr(self.right_panel, 'journal_panel'): self.right_panel.journal_panel.clear_all()
                    if hasattr(self.right_panel, 'inventory_panel'): self.right_panel.inventory_panel.clear()
                    if hasattr(self.right_panel, 'character_sheet'): self.right_panel.character_sheet._clear_stat_displays()
                except Exception: pass
                
                self.input_handler.last_submitted_command = None
                
                loaded_state = self.game_engine.load_game(save_id) 

                if loaded_state:
                    if not hasattr(self.game_engine.state_manager.current_state, "journal"):
                        self.game_engine.state_manager.current_state.journal = {
                            "character": getattr(self.game_engine.state_manager.current_state.player, 'background', ''),
                            "quests": {}, "notes": []
                        }
                    self.game_engine.state_manager.ensure_stats_manager_initialized()

                    self._show_game_panels_for_loaded_game()
                    self._update_ui() 

                    try:
                        state = self.game_engine.state_manager.current_state
                        if state and state.current_mode.name == 'COMBAT' and getattr(state, 'combat_manager', None):
                            if hasattr(self.game_engine, '_combat_orchestrator'):
                                self.game_engine._combat_orchestrator.set_combat_manager(state.combat_manager)
                    except Exception: pass

                    try:
                        sm = self.game_engine.state_manager.stats_manager
                        if sm and hasattr(sm, 'stats_changed'):
                            sm.stats_changed.emit(sm.get_all_stats())
                    except Exception: pass

                    if self.game_engine.state_manager.current_state and self.game_engine.state_manager.current_state.player:
                        self.right_panel.update_character(self.game_engine.state_manager.current_state.player)
                    self.game_output.append_system_message(f"Loaded last save: {last_manual_save.save_name}")
                else:
                    QMessageBox.warning(self, "Load Failed", f"Failed to load last save: {last_manual_save.save_name}")
                    self._show_load_game_dialog()
            else:
                QMessageBox.information(self, "No Last Save", "No manual save file found. Please load manually or start a new game.")
                self._show_load_game_dialog()
        except Exception as e:
            logger.error(f"Error loading last save: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred while trying to load the last save:\n{e}")
            self._show_load_game_dialog() 

    @Slot()
    def _update_theme(self):
        self.palette = self.theme_manager.get_current_palette()
        if hasattr(self, 'game_output'):
            self.game_output._update_formats()
            self.game_output._setup_background()