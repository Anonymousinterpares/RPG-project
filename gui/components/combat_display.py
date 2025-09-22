#!/usr/bin/env python3
"""
Combat display component for the RPG game.

This module provides a GUI component for displaying combat status and log,
with customizable appearance settings.
"""

import json
import logging
import os
import re # Added for stylesheet manipulation
from typing import Dict, Iterator, List, Any, Optional, Callable, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QGroupBox, QProgressBar, QScrollArea, QFrame, QSizePolicy, QPushButton,
    QDialog # Added for placeholder dialog
)
from PySide6.QtCore import QSettings, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QTextCharFormat, QFont, QTextCursor, QFontDatabase

from core.base.engine import get_game_engine
from core.interaction.enums import InteractionMode # Added QFontDatabase
from ..dialogs.combat_settings_dialog import CombatSettingsDialog

# Assuming core is in the parent directory of gui
# Adjust if your project structure is different
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

class CombatEntityWidget(QWidget):
    """Widget for displaying a combat entity status."""

    def __init__(self, entity_id: str, name: str, settings: dict, is_player: bool = False, parent=None):
        """Initialize the combat entity widget."""
        super().__init__(parent)

        self.entity_id = entity_id
        self.is_player = is_player
        self.settings = settings

        self._bar_animation_timer = QTimer(self)
        self._bar_animation_timer.setSingleShot(True)
        self._bar_animation_timer.timeout.connect(self._finalize_bar_update)
        self._pending_bar_update_data: Optional[Dict[str, Any]] = None


        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        self.name_label = QLabel(name)
        layout.addWidget(self.name_label)

        # HP Bar
        self.hp_widget_container = QWidget() # Container for HP bar and label
        hp_layout = QHBoxLayout(self.hp_widget_container)
        hp_layout.setContentsMargins(0, 0, 0, 0); hp_layout.setSpacing(5)
        self.hp_bar = QProgressBar()
        self.hp_bar.setRange(0, 100); self.hp_bar.setValue(100) 
        self.hp_bar.setTextVisible(True); self.hp_bar.setFormat("%v / %m")
        self.hp_label = QLabel("HP:")
        hp_layout.addWidget(self.hp_label); hp_layout.addWidget(self.hp_bar)
        layout.addWidget(self.hp_widget_container) # Add container to main layout

        # Stamina Bar
        self.stamina_widget_container = QWidget() # Container for stamina bar and label
        stamina_layout = QHBoxLayout(self.stamina_widget_container)
        stamina_layout.setContentsMargins(0, 0, 0, 0); stamina_layout.setSpacing(5)
        self.stamina_bar = QProgressBar() 
        self.stamina_bar.setRange(0, 100); self.stamina_bar.setValue(100) 
        self.stamina_bar.setTextVisible(True); self.stamina_bar.setFormat("%v / %m")
        self.stamina_label = QLabel("Stamina:") 
        stamina_layout.addWidget(self.stamina_label); stamina_layout.addWidget(self.stamina_bar)
        layout.addWidget(self.stamina_widget_container) # Add container to main layout

        # Mana Bar 
        self.mana_widget_container = QWidget() # Container for mana bar and label
        mana_layout = QHBoxLayout(self.mana_widget_container) 
        mana_layout.setContentsMargins(0, 0, 0, 0); mana_layout.setSpacing(5)
        self.mana_bar = QProgressBar()
        self.mana_bar.setRange(0, 1); self.mana_bar.setValue(0) # Default to 0/1
        self.mana_bar.setTextVisible(True); self.mana_bar.setFormat("%v / %m")
        self.mana_label = QLabel("Mana:")
        mana_layout.addWidget(self.mana_label); mana_layout.addWidget(self.mana_bar)
        layout.addWidget(self.mana_widget_container) # Add container to main layout

        # Status Effects
        self.status_widget_container = QWidget() # Container for status label and text
        status_layout = QHBoxLayout(self.status_widget_container)
        status_layout.setContentsMargins(0, 0, 0, 0); status_layout.setSpacing(5)
        self.status_label_title = QLabel("Status:")
        status_layout.addWidget(self.status_label_title)
        self.status_text = QLabel("") 
        status_layout.addWidget(self.status_text); status_layout.addStretch()
        layout.addWidget(self.status_widget_container) # Add container to main layout

        self.setMinimumHeight(110) 
        self.setMinimumWidth(250 if is_player else 200)
        self.update_style(self.settings)

    def update_stats(self, current_hp: int, max_hp: int,
                    current_stamina: int, max_stamina: int,
                    status_effects: Optional[List[str]] = None,
                    current_mana: Optional[int] = None, max_mana: Optional[int] = None):
        """Update the entity stats display. This is now the final update (Phase 2)."""
        
        old_hp = self.hp_bar.value()
        # Ensure HP bar is always visible if HP stat is relevant
        self.hp_widget_container.setVisible(True) # Make container visible
        self.hp_bar.setRange(0, max_hp if max_hp > 0 else 1) 
        self.hp_bar.setValue(current_hp)
        self.hp_bar.setFormat(f"{current_hp} / {max_hp}")
        self._update_hp_bar_color(current_hp, max_hp) 

        if old_hp != current_hp:
            logger.debug(f"EntityWidget {self.entity_id} HP directly updated to {current_hp}/{max_hp}")

        old_stamina = self.stamina_bar.value()
        if max_stamina > 0:
            self.stamina_widget_container.setVisible(True) # Make container visible
            self.stamina_bar.setRange(0, max_stamina)
            self.stamina_bar.setValue(current_stamina)
            self.stamina_bar.setFormat(f"{current_stamina} / {max_stamina}")
        else: 
            self.stamina_widget_container.setVisible(False) # Hide whole container
        
        if old_stamina != current_stamina:
            logger.debug(f"EntityWidget {self.entity_id} Stamina directly updated to {current_stamina}/{max_stamina}")

        if current_mana is not None and max_mana is not None:
            old_mana = self.mana_bar.value()
            if max_mana > 0:
                self.mana_widget_container.setVisible(True) # Make container visible
                self.mana_bar.setRange(0, max_mana)
                self.mana_bar.setValue(current_mana)
                self.mana_bar.setFormat(f"{current_mana} / {max_mana}")
            else: 
                self.mana_widget_container.setVisible(False) # Hide whole container
            
            if old_mana != current_mana:
                logger.debug(f"EntityWidget {self.entity_id} Mana directly updated to {current_mana}/{max_mana}")
        else: 
            self.mana_widget_container.setVisible(False) # Hide container if no mana data

        if status_effects:
            self.status_widget_container.setVisible(True) # Make container visible
            self.status_text.setText(", ".join(status_effects))
        else:
            self.status_widget_container.setVisible(True) # Still show "Status: None"
            self.status_text.setText("None")

    def _update_hp_bar_color(self, current_hp: int, max_hp: int):
        """Helper method to update HP bar color based on settings."""
        hp_percent = (current_hp / max_hp) * 100 if max_hp > 0 else 0
        style_sheet = self.hp_bar.styleSheet() # Get current base style
        chunk_style = ""

        # Use settings for colors
        critical_color = self.settings.get("color_hp_bar_chunk_critical", "#990000")
        low_color = self.settings.get("color_hp_bar_chunk_low", "#cc0000")
        normal_color = self.settings.get("color_hp_bar_chunk_normal", "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff0000, stop:1 #aa0000)")

        if hp_percent < self.settings.get("hp_threshold_critical", 25): # Make threshold configurable? (Future idea)
            chunk_color = critical_color
        elif hp_percent < self.settings.get("hp_threshold_low", 50): # Make threshold configurable? (Future idea)
            chunk_color = low_color
        else:
            chunk_color = normal_color

        chunk_style = f"background-color: {chunk_color};"

        # Find and replace the chunk part of the stylesheet
        # This assumes the base style is set correctly in update_style
        new_style_sheet = re.sub(r"(QProgressBar::chunk\s*{)[^}]*(})",
                                 r"\1 " + chunk_style + r" \2",
                                 style_sheet, count=1, flags=re.IGNORECASE | re.DOTALL)

        if new_style_sheet != style_sheet: # Apply only if changed
            self.hp_bar.setStyleSheet(new_style_sheet)

    def setFrameStyle(self, active=False):
        """Set the frame style based on entity type, active state, and settings."""
        if self.is_player:
            if active:
                bg_color = self.settings.get("color_entity_player_bg_active", "rgba(200, 220, 255, 80)")
                border_color = self.settings.get("color_entity_player_border_active", "#00aaff")
                border_width = 3
            else:
                bg_color = self.settings.get("color_entity_player_bg", "rgba(200, 220, 255, 30)")
                border_color = self.settings.get("color_entity_player_border", "#0077cc")
                border_width = 2
        else: # Enemy
            if active:
                bg_color = self.settings.get("color_entity_enemy_bg_active", "rgba(255, 200, 200, 80)")
                border_color = self.settings.get("color_entity_enemy_border_active", "#ff5500")
                border_width = 3
            else:
                bg_color = self.settings.get("color_entity_enemy_bg", "rgba(255, 200, 200, 30)")
                border_color = self.settings.get("color_entity_enemy_border", "#cc0000")
                border_width = 2

        explicit_text_color = self.settings.get("color_groupbox_title_text", "#FFFFFF")

        self.setStyleSheet(f"""
            CombatEntityWidget {{
                border: {border_width}px solid {border_color};
                border-radius: 5px;
                background-color: {bg_color};
                /* color: {explicit_text_color}; */ /* Removing this default color for the widget itself */
            }}
            /* QLabel styling will be handled in update_style or by direct application */
        """)
        
        self.name_label.setStyleSheet(f"color: {explicit_text_color}; background-color: transparent;")
        self.hp_label.setStyleSheet(f"color: {explicit_text_color}; background-color: transparent;")
        self.stamina_label.setStyleSheet(f"color: {explicit_text_color}; background-color: transparent;")
        self.status_label_title.setStyleSheet(f"color: {explicit_text_color}; background-color: transparent;")
        self.status_text.setStyleSheet(f"color: {explicit_text_color}; background-color: transparent;")

    def highlight_active(self, active: bool = True):
        """Highlight the entity if it's their turn, using settings."""
        self.setFrameStyle(active=active)

    def update_style(self, settings: dict):
        """Update the widget's style based on the provided settings."""
        self.settings = settings
        # is_active_currently = False # Not needed here, setFrameStyle handles active state

        base_font_family = self.settings.get("font_family", "Arial")
        base_font_size = self.settings.get("font_size", 10)

        label_text_color = self.settings.get("color_groupbox_title_text", "#FFFFFF")

        name_font = QFont(base_font_family, base_font_size)
        name_font.setBold(True)
        if self.is_player: name_font.setPointSize(base_font_size + self.settings.get("font_size_player_name_offset", 1))
        self.name_label.setFont(name_font)
        self.name_label.setStyleSheet(f"color: {label_text_color}; background-color: transparent;")


        base_font = QFont(base_font_family, base_font_size)
        self.hp_label.setFont(base_font)
        self.hp_label.setStyleSheet(f"color: {label_text_color}; background-color: transparent;")

        self.stamina_label.setFont(base_font) 
        self.stamina_label.setStyleSheet(f"color: {label_text_color}; background-color: transparent;")
        
        self.mana_label.setFont(base_font) 
        self.mana_label.setStyleSheet(f"color: {label_text_color}; background-color: transparent;")

        self.status_label_title.setFont(base_font)
        self.status_label_title.setStyleSheet(f"color: {label_text_color}; background-color: transparent;")

        self.status_text.setFont(base_font)
        self.status_text.setStyleSheet(f"color: {label_text_color}; background-color: transparent;")

        hp_chunk_normal = self.settings.get("color_hp_bar_chunk_normal", "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff0000, stop:1 #aa0000)")
        stamina_chunk = self.settings.get("color_stamina_bar_chunk", "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66CC33, stop:1 #44AA22)")
        mana_chunk = self.settings.get("color_mana_bar_chunk", "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3366CC, stop:1 #2244AA)") 
        pb_text_color = self.settings.get("color_progressbar_text", "#FFFFFF") 
        pb_bg_color = self.settings.get("color_progressbar_bg", "#555555") 

        pb_base_style = f"""
            QProgressBar {{
                border: 1px solid #444; border-radius: 3px; text-align: center;
                height: 18px; color: {pb_text_color}; background-color: {pb_bg_color};
            }}
        """
        self.hp_bar.setStyleSheet(f"{pb_base_style} QProgressBar::chunk {{ background-color: {hp_chunk_normal}; }}")
        self.stamina_bar.setStyleSheet(f"{pb_base_style} QProgressBar::chunk {{ background-color: {stamina_chunk}; }}")
        self.mana_bar.setStyleSheet(f"{pb_base_style} QProgressBar::chunk {{ background-color: {mana_chunk}; }}") 

        self.setFrameStyle(active=False) # Apply default inactive frame style

        current_hp = self.hp_bar.value(); max_hp = self.hp_bar.maximum()
        self._update_hp_bar_color(current_hp, max_hp)
        self.update()
        
    @Slot(dict)
    def animate_ui_bar_update_phase1(self, update_data: Dict[str, Any]):
        """
        Handles Phase 1 of a bar update: show impending loss.
        update_data: { "bar_type": "hp"|"stamina"|"mana", "old_value": X, "new_value_preview": Y, "max_value": M }
        """
        bar_type = update_data.get("bar_type")
        new_value_preview = update_data.get("new_value_preview") 
        max_value = update_data.get("max_value")

        logger.debug(f"EntityWidget {self.entity_id} PHASE 1 ANIM: {bar_type} to preview {new_value_preview}/{max_value}")

        target_bar = None
        original_stylesheet = ""
        bleak_color_key_suffix = "_bleak" # e.g. color_hp_bar_chunk_normal_bleak

        if bar_type == "hp": 
            target_bar = self.hp_bar
            hp_percent_preview = (new_value_preview / max_value) * 100 if max_value > 0 else 0
            if hp_percent_preview < self.settings.get("hp_threshold_critical", 25): bleak_color_key = "color_hp_bar_chunk_critical" + bleak_color_key_suffix
            elif hp_percent_preview < self.settings.get("hp_threshold_low", 50): bleak_color_key = "color_hp_bar_chunk_low" + bleak_color_key_suffix
            else: bleak_color_key = "color_hp_bar_chunk_normal" + bleak_color_key_suffix
        elif bar_type == "stamina": 
            target_bar = self.stamina_bar
            bleak_color_key = "color_stamina_bar_chunk" + bleak_color_key_suffix
        elif bar_type == "mana": # NEW for Mana
            target_bar = self.mana_bar
            bleak_color_key = "color_mana_bar_chunk" + bleak_color_key_suffix # Assuming similar setting key
        else:
            logger.warning(f"EntityWidget {self.entity_id}: Unknown bar_type '{bar_type}' for phase 1 animation.")
            if hasattr(get_game_engine()._combat_orchestrator, '_handle_visual_display_complete'): # Ensure orchestrator can proceed
                QTimer.singleShot(0, get_game_engine()._combat_orchestrator._handle_visual_display_complete)
            return

        if target_bar and new_value_preview is not None and max_value is not None:
            original_stylesheet = target_bar.styleSheet() # Store current full stylesheet
            
            bleak_color = self.settings.get(bleak_color_key, "#777777A0") # Default semi-transparent gray

            new_chunk_style = f"background-color: {bleak_color};"
            # Replace only the background-color of the chunk part
            updated_stylesheet = re.sub(r"(QProgressBar::chunk\s*{\s*background-color:\s*)[^;]+(;[^}]*})",
                                        rf"\1{bleak_color}\2",
                                        original_stylesheet, count=1, flags=re.IGNORECASE | re.DOTALL)
            if not re.search(r"QProgressBar::chunk\s*{", updated_stylesheet, re.IGNORECASE): # If no chunk style existed
                base_pb_style = re.match(r"(QProgressBar\s*{[^}]*})", original_stylesheet, re.IGNORECASE | re.DOTALL)
                if base_pb_style:
                    updated_stylesheet = base_pb_style.group(1) + f" QProgressBar::chunk {{ {new_chunk_style} }}"
                else: # Fallback: just append
                    updated_stylesheet = original_stylesheet + f" QProgressBar::chunk {{ {new_chunk_style} }}"


            target_bar.setStyleSheet(updated_stylesheet)
            target_bar.setFormat(f"{new_value_preview} / {max_value} (...)") # Indicate change

            self._pending_bar_update_data = {
                "bar_type": bar_type,
                "final_value": new_value_preview, # This is preview, Phase2 will get actual final
                "max_value": max_value,
                "original_stylesheet": original_stylesheet 
            }
        else:
            logger.warning(f"Could not animate phase 1 for {self.entity_id}, bar_type: {bar_type}, data: {update_data}")

        # Visual update is considered complete for Phase 1 after style is set.
        if hasattr(get_game_engine()._combat_orchestrator, '_handle_visual_display_complete'):
            QTimer.singleShot(0, get_game_engine()._combat_orchestrator._handle_visual_display_complete)
    @Slot(dict)
    def animate_ui_bar_update_phase2(self, update_data: Dict[str, Any]):
        """
        Handles Phase 2 of a bar update: finalize the bar to its new value.
        update_data: { "bar_type": "hp"|"stamina"|"mana", "final_new_value": Y, "max_value": M }
        """
        bar_type = update_data.get("bar_type")
        final_value = update_data.get("final_new_value")
        max_value = update_data.get("max_value")
        
        logger.debug(f"EntityWidget {self.entity_id} PHASE 2 ANIM: {bar_type} to final {final_value}/{max_value}")

        target_bar = None
        if bar_type == "hp": target_bar = self.hp_bar
        elif bar_type == "stamina": target_bar = self.stamina_bar
        elif bar_type == "mana": target_bar = self.mana_bar # NEW for Mana
        else:
            logger.warning(f"EntityWidget {self.entity_id}: Unknown bar_type '{bar_type}' for phase 2 animation.")
            if hasattr(get_game_engine()._combat_orchestrator, '_handle_visual_display_complete'):
                QTimer.singleShot(0, get_game_engine()._combat_orchestrator._handle_visual_display_complete)
            return

        if target_bar and final_value is not None and max_value is not None:
            # Restore original base stylesheet if it was stored and modified for bleak color
            if self._pending_bar_update_data and self._pending_bar_update_data.get("bar_type") == bar_type:
                original_style = self._pending_bar_update_data.get("original_stylesheet")
                if original_style:
                    target_bar.setStyleSheet(original_style) # Restore base before applying final color logic
            
            # Call update_stats to set value and apply final color logic
            # Need to fetch other stats if update_stats requires all of them
            # For simplicity, assuming update_stats can handle partial updates or we reconstruct args
            if bar_type == "hp":
                self.update_stats(final_value, max_value, self.stamina_bar.value(), self.stamina_bar.maximum(), current_mana=self.mana_bar.value(), max_mana=self.mana_bar.maximum())
            elif bar_type == "stamina":
                self.update_stats(self.hp_bar.value(), self.hp_bar.maximum(), final_value, max_value, current_mana=self.mana_bar.value(), max_mana=self.mana_bar.maximum())
            elif bar_type == "mana": # NEW for Mana
                self.update_stats(self.hp_bar.value(), self.hp_bar.maximum(), self.stamina_bar.value(), self.stamina_bar.maximum(), current_mana=final_value, max_mana=max_value)

            
            target_bar.setFormat(f"{final_value} / {max_value}") # Ensure format is correct
            logger.debug(f"EntityWidget {self.entity_id} {bar_type} bar finalized to {final_value}/{max_value}")
        else:
            logger.warning(f"Could not animate phase 2 for {self.entity_id}, bar_type: {bar_type}, data: {update_data}")
            
        self._pending_bar_update_data = None 
        
        if hasattr(get_game_engine()._combat_orchestrator, '_handle_visual_display_complete'):
            QTimer.singleShot(0, get_game_engine()._combat_orchestrator._handle_visual_display_complete)

    @Slot()
    def _finalize_bar_update(self):
        """Actually updates the bar value and color after the delay (Old method, for reference if needed)."""
        # This method is less used now as Orchestrator controls delays and Phase 2 trigger.
        # Kept for potential direct use or if animation needs its own timer.
        if self._pending_bar_update_data:
            bar_type = self._pending_bar_update_data["bar_type"]
            final_value = self._pending_bar_update_data["final_value"]
            max_value = self._pending_bar_update_data["max_value"]
            # original_stylesheet = self._pending_bar_update_data["original_stylesheet"] # Not used if update_stats handles colors

            target_bar = None
            if bar_type == "hp": target_bar = self.hp_bar
            elif bar_type == "stamina": target_bar = self.stamina_bar

            if target_bar:
                # target_bar.setStyleSheet(original_stylesheet) # Restore base if needed
                target_bar.setValue(final_value)
                target_bar.setFormat(f"{final_value} / {max_value}")
                if bar_type == "hp": self._update_hp_bar_color(final_value, max_value)
                # Add similar for stamina if it has dynamic coloring

            self._pending_bar_update_data = None

class CombatDisplay(QWidget):
    """Widget for displaying combat status and log."""

    # --- ECFA Change: Add visualDisplayComplete signal ---
    visualDisplayComplete = Signal()
    # --- End ECFA Change ---

    def __init__(self, parent=None):
        """Initialize the combat display widget."""
        super().__init__(parent)

        self.setObjectName("combatDisplayWidget")

        self.entity_widgets: Dict[str, CombatEntityWidget] = {}
        self.combat_active = False 
        self.stats_manager = get_stats_manager() 
        self.current_settings: Dict[str, Any] = {} 

        self.load_settings()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) 
        main_layout.setSpacing(0)
        
        self.content_frame = QFrame()
        self.content_frame.setObjectName("combatContentFrame") 
        self.content_frame.setFrameShape(QFrame.Shape.StyledPanel) 
        self.content_frame.setFrameShadow(QFrame.Shadow.Raised) 
        main_layout.addWidget(self.content_frame) 

        layout = QVBoxLayout(self.content_frame) 
        layout.setContentsMargins(10, 10, 10, 10) 
        layout.setSpacing(10) 

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)

        self.status_label = QLabel("Status: Narrative") 
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)

        self.round_label = QLabel("Round: 0")
        self.round_label.setVisible(False) 
        self.round_label.setObjectName("roundLabel")
        status_layout.addWidget(self.round_label)

        status_layout.addStretch()

        self.settings_button = QPushButton("⚙️")
        self.settings_button.setToolTip("Combat Display Settings")
        self.settings_button.setFixedSize(25, 25)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        status_layout.addWidget(self.settings_button)

        # Developer controls (hidden unless dev mode enabled)
        self.dev_controls_container = QWidget()
        dev_controls_layout = QHBoxLayout(self.dev_controls_container)
        dev_controls_layout.setContentsMargins(0, 0, 0, 0)
        dev_controls_layout.setSpacing(6)
        self.dev_step_mode_btn = QPushButton("Step Mode")
        self.dev_step_mode_btn.setCheckable(True)
        self.dev_next_step_btn = QPushButton("Next Step")
        self.dev_next_step_btn.setEnabled(False)
        dev_controls_layout.addWidget(self.dev_step_mode_btn)
        dev_controls_layout.addWidget(self.dev_next_step_btn)
        status_layout.addWidget(self.dev_controls_container)

        layout.addLayout(status_layout)

        self.entities_frame = QFrame() 
        self.entities_frame.setFrameShape(QFrame.Shape.NoFrame) 
        self.entities_frame.setFrameShadow(QFrame.Shadow.Plain) 
        self.entities_frame.setObjectName("entitiesFrame")
        entities_layout = QVBoxLayout(self.entities_frame)
        entities_layout.setContentsMargins(0,0,0,0) 
        entities_layout.setSpacing(10) 

        self.player_group = QGroupBox("Player") 
        self.player_group.setObjectName("playerGroup")
        player_layout = QHBoxLayout(self.player_group)
        player_layout.setContentsMargins(5, 10, 5, 5) 
        player_layout.setSpacing(5)
        self.player_layout = player_layout
        entities_layout.addWidget(self.player_group)

        self.enemies_group = QGroupBox("Enemies") 
        self.enemies_group.setObjectName("enemiesGroup")
        enemies_layout = QHBoxLayout(self.enemies_group)
        enemies_layout.setContentsMargins(5, 10, 5, 5) 
        enemies_layout.setSpacing(5)
        self.enemies_layout = enemies_layout
        entities_layout.addWidget(self.enemies_group)

        layout.addWidget(self.entities_frame)

        self.log_group = QGroupBox("Combat Log") 
        self.log_group.setObjectName("logGroup")
        log_layout = QVBoxLayout(self.log_group)
        log_layout.setContentsMargins(5, 10, 5, 5) 
        log_layout.setSpacing(0)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setObjectName("combatLogText")
        log_layout.addWidget(self.log_text)

        layout.addWidget(self.log_group)

        self.last_log_index = -1 

        self._gradual_log_iterator: Optional[Iterator[str]] = None
        self._gradual_log_format: Optional[QTextCharFormat] = None
        self._gradual_log_timer: Optional[QTimer] = None
        self._is_gradual_log_active: bool = False
        self._pending_log_messages: List[Tuple[str, QTextCharFormat, bool]] = [] 

        self.apply_settings()
        self.clear_display()
        
        # Suppress visualComplete during batched replays
        self._suppress_visual_complete: bool = False

        # Initialize dev controls visibility from QSettings
        self._init_dev_controls()

    def load_settings(self):
        """Load settings from JSON file or use defaults."""
        self.current_settings = self.get_default_settings() # Start with defaults
        logger.info(f"Loading combat display settings from: {SETTINGS_FILE}")
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    loaded_settings = json.load(f)
                    logger.debug(f"Loaded settings: {loaded_settings}")
                    # Merge loaded settings carefully, only overwriting defaults
                    for key, value in loaded_settings.items():
                         # Check if key exists in defaults OR if it's a known pattern (future-proofing slightly)
                         if key in self.current_settings or key.startswith("color_") or key.startswith("font_"):
                             self.current_settings[key] = value
                         else:
                             logger.warning(f"Ignoring unknown setting '{key}' from file.")
            else:
                logger.info("Settings file not found. Using default settings.")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading combat display settings: {e}. Using defaults.")
        logger.info(f"Final settings after load: {self.current_settings}")


    def get_default_settings(self):
        """Return a dictionary of default settings."""
        default_font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
        return {
            # Background
            "background_image": None,
            # Fonts
            "font_family": default_font.family(),
            "font_size": default_font.pointSize() if default_font.pointSize() > 0 else 10,
            "font_size_player_name_offset": 1,
            "font_size_status_offset": 2,
            # Log Colors
            "color_log_damage": "#C80000",
            "color_log_heal": "#009600",
            "color_log_crit": "#FF0000", # Brighter red for crits
            "color_log_miss": "#969696",
            "color_log_roll": "#C87800",
            "color_log_turn": "#0064C8",
            "color_log_round": "#0064FF",
            "color_log_dev": "#646464",
            "color_log_header": "#A0A0A0", 
            "color_log_default": "#E0E0E0", 
            "color_log_combat_event": "#FFFFFF", 
            "color_log_system_message": "#FFFF00", # Default Yellow for system messages
            "color_log_narrative": "#FFD700", # Default Golden for narrative/GM messages
            "color_log_group_bg": "rgba(40, 40, 40, 0.75)", 
            "color_log_text_bg": "rgba(25, 25, 25, 0.85)", # Slightly darker text edit bg
            # General UI Colors
            "color_status_text": "#FFFFFF", 
            "color_round_text": "#E0E0E0", 
            "color_groupbox_title_text": "#FFFFFF", 
            "color_groupbox_title_bg": "rgba(0, 0, 0, 0.6)", 
            # Section Background Colors 
            "color_player_group_bg": "rgba(60, 80, 120, 0.7)", 
            "color_enemies_group_bg": "rgba(120, 60, 60, 0.7)", 
            # Entity Colors
            "color_entity_player_bg": "rgba(200, 220, 255, 0.3)",
            "color_entity_player_border": "#0077cc",
            "color_entity_player_bg_active": "rgba(200, 220, 255, 0.8)",
            "color_entity_player_border_active": "#00aaff",
            "color_entity_enemy_bg": "rgba(255, 200, 200, 0.3)",
            "color_entity_enemy_border": "#cc0000",
            "color_entity_enemy_bg_active": "rgba(255, 200, 200, 0.8)",
            "color_entity_enemy_border_active": "#ff5500",
            # Progress Bar Colors
            "color_hp_bar_chunk_normal": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff0000, stop:1 #aa0000)",
            "color_hp_bar_chunk_low": "#cc0000",
            "color_hp_bar_chunk_critical": "#990000",
            "color_hp_bar_chunk_normal_bleak": "#AA0000A0", 
            "color_hp_bar_chunk_low_bleak": "#880000A0",   
            "color_hp_bar_chunk_critical_bleak": "#600000A0",
            "color_stamina_bar_chunk": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66CC33, stop:1 #44AA22)",
            "color_stamina_bar_chunk_bleak": "#44AA22A0",
            "color_mana_bar_chunk": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3366CC, stop:1 #2244AA)", # Added Mana Chunk
            "color_mana_bar_chunk_bleak": "#2244AAA0",  # Added Mana Bleak
            "color_resolve_bar_chunk": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9b59b6, stop:1 #8e44ad)",
            "color_progressbar_text": "#FFFFFF", 
            "color_progressbar_bg": "#555555",

            "gradual_text_combat_log": True, 
            "display_text_speed_delay": 30,
        }

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

    @Slot(bool)
    def _on_orchestrator_dev_waiting_changed(self, waiting: bool):
        self.dev_next_step_btn.setEnabled(bool(waiting))

    def apply_settings(self):
        """Apply loaded or default settings to the combat display UI."""
        if not self.current_settings:
            logger.warning("Attempted to apply settings before loading. Loading defaults.")
            self.load_settings() # This populates self.current_settings

        logger.debug(f"Applying settings to CombatDisplay: {self.current_settings}")

        # --- ECFA Change: Ensure text speed setting is loaded into self.current_settings ---
        # If load_settings doesn't get specific combat speed, use general one.
        q_settings = QSettings("RPGGame", "Settings")
        general_text_speed = q_settings.value("display/text_speed_delay", 30, type=int)
        self.current_settings.setdefault("display_text_speed_delay_combat", general_text_speed)
        # --- End ECFA Change ---

        bg_image_relative = self.current_settings.get("background_image")
        main_widget_style_parts = [] 
        image_path_for_log = "None" 
        if bg_image_relative:
            image_path = os.path.join(IMAGE_DIR, bg_image_relative).replace("\\", "/")
            image_path_for_log = image_path 
            if os.path.exists(image_path):
                main_widget_style_parts.append(f"border-image: url(\"{image_path}\") 0 0 0 0 stretch stretch;")
                logger.info(f"Applying background image using border-image: {image_path}")
            else:
                logger.warning(f"Background image not found: {image_path}")
                main_widget_style_parts.append("border-image: none;")
        else:
             main_widget_style_parts.append("border-image: none;")
             logger.info("No background image selected, applying 'border-image: none;'")

        try:
            fallback_bg_color_str = self.current_settings.get("color_fallback_bg", "rgba(30, 30, 30, 0.9)")
            QColor(fallback_bg_color_str) 
        except (ValueError, TypeError):
            logger.warning(f"Invalid fallback background color '{fallback_bg_color_str}'. Using default.")
            fallback_bg_color_str = "rgba(30, 30, 30, 0.9)"
        main_widget_style_parts.append(f"background-color: {fallback_bg_color_str};")

        main_widget_style = "\n    ".join(main_widget_style_parts)

        def get_safe_color(key, default):
            color_str = self.current_settings.get(key, default)
            try:
                QColor(color_str); return color_str
            except (ValueError, TypeError):
                logger.warning(f"Invalid color value '{color_str}' for key '{key}'. Using default '{default}'.")
                return default

        player_group_bg = get_safe_color("color_player_group_bg", "rgba(60, 80, 120, 0.7)")
        enemies_group_bg = get_safe_color("color_enemies_group_bg", "rgba(120, 60, 60, 0.7)")
        log_group_bg = get_safe_color("color_log_group_bg", "rgba(40, 40, 40, 0.75)")
        log_default_text_color = get_safe_color("color_log_default", "#E0E0E0")
        log_text_bg_color = get_safe_color("color_log_text_bg", "rgba(255, 255, 255, 0.05)") # Ensure this is a valid key or provide default
        groupbox_title_text = get_safe_color("color_groupbox_title_text", "#FFFFFF")
        groupbox_title_bg = get_safe_color("color_groupbox_title_bg", "rgba(0, 0, 0, 0.6)")
        status_text_color = get_safe_color("color_status_text", "#FFFFFF")
        round_text_color = get_safe_color("color_round_text", "#E0E0E0")


        full_stylesheet = f"""
            QWidget#{self.objectName()} {{ background-color: transparent; border: none; }}
            QFrame#combatContentFrame {{ {main_widget_style} background-clip: padding-box; background-origin: border-box; border-radius: 5px; }}
            QFrame#{self.entities_frame.objectName()} {{ background-color: transparent; border: none; }}
            QGroupBox#{self.player_group.objectName()} {{ background-color: {player_group_bg}; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 4px; margin-top: 15px; padding-top: 5px; }}
            QGroupBox#{self.enemies_group.objectName()} {{ background-color: {enemies_group_bg}; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 4px; margin-top: 15px; padding-top: 5px; }}
            QGroupBox#{self.log_group.objectName()} {{ background-color: {log_group_bg}; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 4px; margin-top: 15px; padding-top: 5px; }}
            QGroupBox::title {{ color: {groupbox_title_text}; background-color: {groupbox_title_bg}; padding: 3px 8px; border-radius: 3px; subcontrol-origin: margin; subcontrol-position: top left; margin-left: 5px; }}
            QTextEdit#{self.log_text.objectName()} {{ background-color: {log_text_bg_color}; color: {log_default_text_color}; border: 1px solid rgba(0, 0, 0, 0.2); border-radius: 3px; padding: 2px; }}
            QLabel#{self.status_label.objectName()} {{ background-color: transparent; color: {status_text_color}; padding: 2px; }}
            QLabel#{self.round_label.objectName()} {{ background-color: transparent; color: {round_text_color}; padding: 2px; }}
        """
        self.setStyleSheet(full_stylesheet)

        font_family = self.current_settings.get("font_family", "Arial")
        font_size = self.current_settings.get("font_size", 10)
        
        status_font_size_offset = self.current_settings.get("font_size_status_offset", 2)
        status_font = QFont(font_family, font_size + status_font_size_offset)
        status_font.setBold(True)
        self.status_label.setFont(status_font)

        round_font = QFont(font_family, font_size)
        self.round_label.setFont(round_font)

        log_font = QFont(font_family, font_size)
        self.log_text.setFont(log_font) 

        title_font = QFont(font_family, font_size) 
        title_font.setBold(True) 
        self.player_group.setFont(title_font)
        self.enemies_group.setFont(title_font)
        self.log_group.setFont(title_font)

        for entity_widget in self.entity_widgets.values():
            entity_widget.update_style(self.current_settings)
        self.update()
        logger.info("Combat display settings applied.")

    def clear_display(self):
        """Clear the display and set to inactive/narrative state."""
        self.combat_active = False
        self.status_label.setText("Status: Narrative")
        self.round_label.setText("Round: 0")
        self.round_label.setVisible(False) # Hide round counter
        self.last_log_index = -1

        # Clear the combat log text content as well
        try:
            self.clear_log()
        except Exception:
            pass

        # Clear entity widgets
        self._clear_entity_widgets()

        # Hide the entities frame and log_group for clean UI
        if hasattr(self, 'entities_frame'):
            self.entities_frame.setVisible(False)
        if hasattr(self, 'log_group'):
            self.log_group.setVisible(False)

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
            # Update dev controls visibility on entering these modes
            try:
                settings = QSettings("RPGGame", "Settings")
                dev_enabled = settings.value("dev/enabled", False, type=bool)
                self.dev_controls_container.setVisible(bool(dev_enabled))
            except Exception:
                self.dev_controls_container.setVisible(False)
            self.setVisible(True) # Ensure the CombatDisplay widget itself is visible
            initial_setup_done_this_call = False
            if not self.combat_active: 
                logger.info(f"CombatDisplay: First entry into {mode} view. Setting up UI visibility and styles.")
                if hasattr(self, 'entities_frame'): self.entities_frame.setVisible(True)
                if hasattr(self, 'log_group'): self.log_group.setVisible(True)
                if hasattr(self, 'player_group'): self.player_group.setVisible(True)
                if hasattr(self, 'enemies_group'): self.enemies_group.setVisible(True)
                self.combat_active = True
                self.apply_settings() # Apply styles
                initial_setup_done_this_call = True
            
            combat_manager = getattr(game_state, 'combat_manager', None)
            if not combat_manager:
                logger.warning(f"CombatDisplay: {mode} mode active but no CombatManager found. Clearing entity widgets.")
                self.status_label.setText(f"Status: {mode} (Error - No Manager)")
                self._clear_entity_widgets() 
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
            combatants_widget_data = {}
            cm_entities = getattr(combat_manager, 'entities', {})
            if cm_entities:
                logger.debug(f"CombatDisplay: Building combatants_widget_data from CM entities. Count: {len(cm_entities)}")
                for entity_id, combat_entity in cm_entities.items():
                    if not getattr(combat_entity, 'is_active_in_combat', True):
                        logger.debug(f"CombatDisplay: Skipping display of inactive entity: {getattr(combat_entity, 'combat_name', entity_id)}")
                        if entity_id in self.entity_widgets: 
                            widget_to_remove = self.entity_widgets.pop(entity_id)
                            if widget_to_remove.parentWidget() and widget_to_remove.parentWidget().layout():
                                widget_to_remove.parentWidget().layout().removeWidget(widget_to_remove)
                            widget_to_remove.deleteLater()
                        continue

                    raw_status_effects = getattr(combat_entity, 'status_effects', {})
                    display_status_effects = []
                    if isinstance(raw_status_effects, dict):
                        display_status_effects = [f"{name}({dur})" if dur not in [None, float('inf')] else name for name, dur in raw_status_effects.items()]
                    elif isinstance(raw_status_effects, (list, set)):
                        display_status_effects = [str(eff_name) for eff_name in raw_status_effects]
                    
                    entity_type_enum = getattr(combat_entity, 'entity_type', None)

                    combatants_widget_data[entity_id] = {
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
                        "is_player": entity_type_enum == EntityType.PLAYER if entity_type_enum else False,
                        "entity_type_str": entity_type_enum.name if hasattr(entity_type_enum, 'name') else str(entity_type_enum)
                    }
            else:
                logger.warning("CombatDisplay: combat_manager has no 'entities' or it's empty.")

            if not combatants_widget_data:
                logger.warning("CombatDisplay: combatants_widget_data is empty. No entity widgets will be updated/created for this call.")
                if initial_setup_done_this_call:
                    self._clear_entity_widgets() 
            else:
                logger.info(f"CombatDisplay: Queuing _update_entity_widgets with {len(combatants_widget_data)} entries. Current turn ID: {current_turn_id}")
                is_combat_mode = (mode == "COMBAT")
                QTimer.singleShot(0, lambda data=combatants_widget_data.copy(), turn_id=current_turn_id, is_combat=is_combat_mode: self._update_entity_widgets(data, turn_id, is_combat))

        elif self.combat_active: 
            logger.info(f"CombatDisplay: Exiting {mode} view (was active). Clearing display.")
            self.clear_display() 
            self.setVisible(False) # Hide the CombatDisplay widget when not in combat
            
    def _clear_entity_widgets(self):
        """Clear all entity widgets."""
        layouts_to_clear = [self.player_layout, self.enemies_layout]
        for layout in layouts_to_clear:
            if not layout: continue
            # Remove stretch item first if it exists
            stretch_index = -1
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.spacerItem():
                    stretch_index = i
                    break
            if stretch_index != -1:
                layout.takeAt(stretch_index) # Remove stretch

            # Remove widgets
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        self.entity_widgets.clear()

    def _update_entity_widgets(self, combatants_data: Dict[str, Dict[str, Any]], current_turn_id: Optional[str], is_combat_mode: bool):
        """Update entity widgets based on combatant data."""
        logger.info(f"CombatDisplay._update_entity_widgets: Received {len(combatants_data)} combatants. Current turn: {current_turn_id}")
        if not combatants_data:
            logger.warning("CombatDisplay._update_entity_widgets: combatants_data is empty. Clearing existing widgets if any.")
            self._clear_entity_widgets() # Clear if no data
            return

        existing_ids_in_data = set(combatants_data.keys())
        current_widget_ids = set(self.entity_widgets.keys())

        # Remove widgets for entities no longer in combatants_data
        for entity_id_to_remove in current_widget_ids - existing_ids_in_data:
            if entity_id_to_remove in self.entity_widgets:
                widget = self.entity_widgets.pop(entity_id_to_remove)
                parent_layout = widget.parentWidget().layout() if widget.parentWidget() else None
                if parent_layout: parent_layout.removeWidget(widget)
                widget.deleteLater()
                logger.info(f"CombatDisplay: Removed entity widget for no longer present/active entity: {entity_id_to_remove}")

        player_widgets_present = False
        enemy_widgets_present = False

        for entity_id, entity_data in combatants_data.items():
            is_player = entity_data.get("is_player", False)
            entity_type_str = entity_data.get("entity_type_str", "UNKNOWN") # For logging
            logger.debug(f"CombatDisplay: Processing entity widget for ID {entity_id}, Name: {entity_data.get('combat_name', 'N/A')}, IsPlayer: {is_player}, Type: {entity_type_str}")
            
            is_active_turn = entity_id == current_turn_id
            display_name = entity_data.get("combat_name", entity_data.get("name", entity_id))
            
            current_hp = int(entity_data.get("current_hp", 0)) 
            max_hp = int(entity_data.get("max_hp", 1)) 
            current_stamina = int(entity_data.get("current_stamina", 0)) 
            max_stamina = int(entity_data.get("max_stamina", 1))
            current_mana = int(entity_data.get("current_mana", 0))
            max_mana = int(entity_data.get("max_mana", 1))
            status_effects = entity_data.get("status_effects", [])

            if entity_id in self.entity_widgets:
                widget = self.entity_widgets[entity_id]
                logger.debug(f"CombatDisplay: Updating existing widget for {display_name}")
                widget.name_label.setText(display_name)
                widget.update_style(self.current_settings)
                # In COMBAT mode, do NOT override current values for existing widgets; only update max ranges and labels
                if is_combat_mode:
                    try:
                        # Update ranges only; keep current values as shown (driven by PHASE events)
                        widget.hp_bar.setRange(0, max_hp if max_hp > 0 else 1)
                        widget.stamina_bar.setRange(0, max_stamina if max_stamina > 0 else 1)
                        widget.mana_bar.setRange(0, max_mana if max_mana > 0 else 1)
                        # Update status effects text
                        if status_effects:
                            widget.status_text.setText(", ".join(status_effects))
                        else:
                            widget.status_text.setText("None")
                    except Exception as e:
                        logger.warning(f"CombatDisplay: Failed to apply COMBAT safe update for {display_name}: {e}")
                else:
                    widget.update_stats(current_hp, max_hp, current_stamina, max_stamina, status_effects, current_mana, max_mana)
                widget.highlight_active(is_active_turn)
            else:
                logger.info(f"CombatDisplay: Creating NEW widget for {display_name} (ID: {entity_id}, IsPlayer: {is_player})")
                widget = CombatEntityWidget(entity_id=entity_id, name=display_name, settings=self.current_settings, is_player=is_player)
                # On first creation, seed values fully
                widget.update_stats(current_hp, max_hp, current_stamina, max_stamina, status_effects, current_mana, max_mana)
                widget.highlight_active(is_active_turn)
                
                target_layout = self.player_layout if is_player else self.enemies_layout
                if target_layout:
                    # Remove existing stretch if present before adding widget
                    stretch_item = target_layout.takeAt(target_layout.count() -1) if target_layout.count() >0 and target_layout.itemAt(target_layout.count()-1).spacerItem() else None

                    target_layout.addWidget(widget) # Add the new widget

                    if stretch_item: # Add stretch back if it was removed
                        target_layout.addSpacerItem(stretch_item)
                    else: # Or ensure stretch is there if layout was empty
                        target_layout.addStretch()

                    logger.debug(f"CombatDisplay: Added widget for {display_name} to {'player' if is_player else 'enemies'} layout.")
                else:
                    logger.error(f"CombatDisplay: Target layout (player/enemy) not found for {display_name}!")
                self.entity_widgets[entity_id] = widget
            
            if is_player: player_widgets_present = True
            else: enemy_widgets_present = True

        # This ensures layouts with no widgets don't have a lingering stretch
        self._ensure_stretch(self.player_layout, player_widgets_present)
        self._ensure_stretch(self.enemies_layout, enemy_widgets_present)
        logger.info(f"CombatDisplay._update_entity_widgets: Finished. Player widgets: {player_widgets_present}, Enemy widgets: {enemy_widgets_present}. Total widgets in dict: {len(self.entity_widgets)}")

    def _ensure_stretch(self, layout: Optional[QHBoxLayout], widgets_present: bool):
        """Adds or removes stretch item from a layout as needed."""
        if not layout: return

        stretch_index = -1
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.spacerItem():
                stretch_index = i
                break

        if widgets_present and stretch_index == -1:
            layout.addStretch() # Add stretch if needed
        elif not widgets_present and stretch_index != -1:
            layout.takeAt(stretch_index) # Remove stretch if no widgets

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
        use_gradual = gradual and self.current_settings.get("gradual_text_combat_log", True) # Check setting

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
                    from core.base.engine import get_game_engine
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

            # --- ECFA Change: Use unified settings key from self.current_settings ---
            char_delay = self.current_settings.get("display_text_speed_delay", 30) 
            # --- End ECFA Change ---
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
                    from core.base.engine import get_game_engine
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
                    from core.base.engine import get_game_engine
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
        """Opens the settings dialog to customize the combat display."""
        logger.info("Opening Combat Display Settings dialog.")

        if not self.current_settings:
            logger.error("Cannot open settings dialog: current_settings not loaded.")
            self.load_settings() # Try loading defaults if missing

        # Pass a copy of current settings to avoid modifying originals unless saved
        dialog = CombatSettingsDialog(self.current_settings.copy(), IMAGE_DIR, self)

        # Execute the dialog modally
        if dialog.exec(): # Returns True if accepted (e.g., Save clicked)
            new_settings = dialog.get_settings()
            if new_settings != self.current_settings:
                logger.info("Settings changed. Saving and applying...")
                self.current_settings = new_settings
                self.save_settings()
                self.apply_settings() # Re-apply all settings
            else:
                logger.info("Settings dialog closed without changes.")
        else:
            logger.info("Settings dialog cancelled.")

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
        from PySide6.QtGui import QFont, QColor # Local import for safety
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
        Appends orchestrated event content to the combat log, using CombatDisplay's
        own settings for color formatting.
        """
        # Track current event id for logging/diagnostics
        try:
            self._current_text_event_id = event_id
            logger.info(f"CombatDisplay: render string event id={event_id} gradual={bool(is_gradual)} len={len(event_content) if isinstance(event_content, str) else 'N/A'}")
        except Exception:
            pass
        
        # Hide [DEV] lines unless dev mode is enabled
        try:
            if isinstance(event_content, str) and event_content.strip().startswith("[DEV]"):
                settings = QSettings("RPGGame", "Settings")
                if not settings.value("dev/enabled", False, type=bool):
                    # Consider visual complete so orchestrator does not stall
                    self.visualDisplayComplete.emit()
                    # Also directly notify orchestrator in case signal path is disrupted
                    try:
                        from core.base.engine import get_game_engine
                        eng = get_game_engine()
                        if eng and hasattr(eng, '_combat_orchestrator') and eng._combat_orchestrator.is_waiting_for_visual:
                            logger.debug(f"CombatDisplay: Direct notify orchestrator complete for DEV-suppressed id={event_id}")
                            eng._combat_orchestrator._handle_visual_display_complete()
                    except Exception:
                        pass
                    return
        except Exception:
            pass
        # Determine color/format based on event_role, event_content, and self.current_settings
        color_hex = self.current_settings.get("color_log_default", "#E0E0E0") # Default
        is_bold = False
        is_italic = False

        # Standardize role for key lookup
        role_lower = event_role.lower() if event_role else "system"
        content_lower = event_content.lower()

        # Precedence: Specific keywords first, then role-based, then default.
        if "critical hit" in content_lower or "defeated!" in content_lower or "was defeated" in content_lower:
            color_hex = self.current_settings.get("color_log_crit", "#FF0000") # Default red for crit
            is_bold = True
        elif "healed" in content_lower or ("gains" in content_lower and ("hp" in content_lower or "stamina" in content_lower)):
            color_hex = self.current_settings.get("color_log_heal", "#009600") # Default green for heal
        elif "round" in content_lower and "begins" in content_lower:
            color_hex = self.current_settings.get("color_log_round", "#0064FF") # Default blue for round
            is_bold = True
        elif "turn" in content_lower or "'s turn" in content_lower: # General turn info
            color_hex = self.current_settings.get("color_log_turn", "#0064C8") # Default light blue for turn
        elif "combat started" in content_lower or "combat ended" in content_lower or "victory!" in content_lower or "defeat!" in content_lower or "fled!" in content_lower or "surrender" in content_lower:
            color_hex = self.current_settings.get("color_log_combat_event", "#FFFFFF") # Default white for major combat events
            is_bold = True
        elif "misses" in content_lower or "fails" in content_lower or "resisted" in content_lower or "escape fails" in content_lower or "fumble" in content_lower:
            color_hex = self.current_settings.get("color_log_miss", "#969696") # Default gray for miss/fail
            is_italic = True
        elif "damage" in content_lower or ("loses" in content_lower and ("hp" in content_lower or "resolve" in content_lower)):
            color_hex = self.current_settings.get("color_log_damage", "#C80000") # Default dark red for damage
        elif "roll" in content_lower or "vs" in content_lower: # Dice rolls
            color_hex = self.current_settings.get("color_log_roll", "#C87800") # Default orange for rolls
        elif role_lower == "system":
            color_hex = self.current_settings.get("color_log_system_message", self.current_settings.get("color_log_default", "#E0E0E0"))
        elif role_lower == "gm": # Narrative content
            color_hex = self.current_settings.get("color_log_narrative", self.current_settings.get("color_log_default", "#E0E0E0"))
        elif event_content.startswith("[DEV]"): # Dev messages
            color_hex = self.current_settings.get("color_log_dev", "#646464"); is_italic = True;

        text_format = QTextCharFormat()
        try:
            text_format.setForeground(QColor(color_hex))
        except ValueError: # Fallback if color_hex is invalid
            logger.warning(f"Invalid color hex '{color_hex}' for combat log. Using default.")
            text_format.setForeground(QColor(self.current_settings.get("color_log_default", "#E0E0E0")))

        if is_bold: text_format.setFontWeight(QFont.Weight.Bold)
        if is_italic: text_format.setFontItalic(True)
        
        # Use the existing method to append with the determined format
        self._append_formatted_text(event_content, text_format, gradual=is_gradual)