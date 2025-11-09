#!/usr/bin/env python3
"""
Combat entity widget for the combat display.
"""
import logging
import re
from typing import Dict, Optional, List, Any

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Slot, QTimer
from PySide6.QtGui import QFont, QColor

from core.base.engine import get_game_engine
from core.utils.logging_config import get_logger

logger = get_logger("GUI")

class CombatEntityWidget(QWidget):
    """Widget for displaying a combat entity status."""

    def __init__(self, entity_id: str, name: str, settings: Optional[dict] = None, is_player: bool = False, parent=None):
        """Initialize the combat entity widget."""
        super().__init__(parent)

        self.entity_id = entity_id
        self.is_player = is_player
        self.palette = settings or {} # Store palette, even if initially empty

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
        self.update_style(self.palette)

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