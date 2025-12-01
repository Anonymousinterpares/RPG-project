#!/usr/bin/env python3
"""
Combat entity widget for the combat display.
"""
import re
from typing import Dict, Optional, List, Any

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Slot, QTimer
from PySide6.QtGui import QFont

from core.base.engine import get_game_engine
from core.utils.logging_config import get_logger
from gui.styles.theme_manager import get_theme_manager

logger = get_logger("GUI")

class CombatEntityWidget(QWidget):
    """Widget for displaying a combat entity status."""

    def __init__(self, entity_id: str, name: str, settings: dict, is_player: bool = False, parent=None):
        """Initialize the combat entity widget."""
        super().__init__(parent)

        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self.update_style)
        # --- END THEME MANAGEMENT ---

        self.entity_id = entity_id
        self.is_player = is_player
        self.settings = settings # This will be the theme palette

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
        """Helper method to update HP bar color based on theme settings."""
        hp_percent = (current_hp / max_hp) * 100 if max_hp > 0 else 0
        style_sheet = self.hp_bar.styleSheet()
        chunk_style = ""

        pb_styles = self.palette.get('progress_bars', {})
        
        # Thresholds can be added to the theme later if needed
        if hp_percent < 25:
            chunk_color = pb_styles.get("hp_critical", "#990000")
        elif hp_percent < 50:
            chunk_color = pb_styles.get("hp_low", "#cc0000")
        else:
            chunk_color = pb_styles.get("hp_normal", "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff0000, stop:1 #aa0000)")

        chunk_style = f"background: {chunk_color};"

        new_style_sheet = re.sub(r"(QProgressBar::chunk\s*{)[^}]*(})",
                                 r"\1 " + chunk_style + r" \2",
                                 style_sheet, count=1, flags=re.IGNORECASE | re.DOTALL)

        if new_style_sheet != style_sheet:
            self.hp_bar.setStyleSheet(new_style_sheet)

    def setFrameStyle(self, active=False):
        """Set the frame style based on entity type, active state, and theme palette."""
        colors = self.palette.get('colors', {})
        
        if self.is_player:
            if active:
                bg_color = colors.get("entity_player_bg_active", "rgba(200, 220, 255, 80)")
                border_color = colors.get("entity_player_border_active", "#00aaff")
                border_width = 3
            else:
                bg_color = colors.get("entity_player_bg", "rgba(200, 220, 255, 30)")
                border_color = colors.get("entity_player_border", "#0077cc")
                border_width = 2
        else: # Enemy
            if active:
                bg_color = colors.get("entity_enemy_bg_active", "rgba(255, 200, 200, 80)")
                border_color = colors.get("entity_enemy_border_active", "#ff5500")
                border_width = 3
            else:
                bg_color = colors.get("entity_enemy_bg", "rgba(255, 200, 200, 30)")
                border_color = colors.get("entity_enemy_border", "#cc0000")
                border_width = 2

        explicit_text_color = colors.get("combat_panel_title", "#FFFFFF")

        self.setStyleSheet(f"""
            CombatEntityWidget {{
                border: {border_width}px solid {border_color};
                border-radius: 5px;
                background-color: {bg_color};
            }}
        """)
        
        label_style = f"color: {explicit_text_color}; background-color: transparent;"
        self.name_label.setStyleSheet(label_style)
        self.hp_label.setStyleSheet(label_style)
        self.stamina_label.setStyleSheet(label_style)
        self.mana_label.setStyleSheet(label_style)
        self.status_label_title.setStyleSheet(label_style)
        self.status_text.setStyleSheet(label_style)

    def highlight_active(self, active: bool = True):
        """Highlight the entity if it's their turn, using settings."""
        self.setFrameStyle(active=active)

    @Slot(dict)
    def update_style(self, palette: Optional[Dict[str, Any]] = None):
        """Update the widget's style based on the provided theme palette."""
        if palette:
            self.palette = palette
        
        self.settings = self.palette # settings is an alias for palette now
        
        fonts = self.palette.get('fonts', {})
        colors = self.palette.get('colors', {})
        pb_styles = self.palette.get('progress_bars', {})
        
        base_font_family = fonts.get("family_combat_entity", "Garamond")
        base_font_size = fonts.get("size_combat_entity", 12)

        label_text_color = colors.get("combat_panel_title", "#FFFFFF")
        label_style = f"color: {label_text_color}; background-color: transparent;"

        name_font = QFont(base_font_family, base_font_size)
        name_font.setBold(True)
        if self.is_player:
            name_font.setPointSize(base_font_size + fonts.get("font_size_player_name_offset", 1))
        self.name_label.setFont(name_font)
        self.name_label.setStyleSheet(label_style)

        base_font = QFont(base_font_family, base_font_size)
        self.hp_label.setFont(base_font)
        self.hp_label.setStyleSheet(label_style)
        self.stamina_label.setFont(base_font) 
        self.stamina_label.setStyleSheet(label_style)
        self.mana_label.setFont(base_font) 
        self.mana_label.setStyleSheet(label_style)
        self.status_label_title.setFont(base_font)
        self.status_label_title.setStyleSheet(label_style)
        self.status_text.setFont(base_font)
        self.status_text.setStyleSheet(label_style)

        pb_text_color = pb_styles.get("text", "#FFFFFF") 
        pb_bg_color = pb_styles.get("bg", "#555555") 
        hp_chunk = pb_styles.get("hp_normal", "red")
        stamina_chunk = pb_styles.get("stamina", "green")
        mana_chunk = pb_styles.get("mana", "blue")

        pb_base_style = f"""
            QProgressBar {{
                border: 1px solid {colors.get('border_dark', '#444')};
                border-radius: 3px;
                text-align: center;
                height: 18px;
                color: {pb_text_color};
                background-color: {pb_bg_color};
            }}
        """
        self.hp_bar.setStyleSheet(f"{pb_base_style} QProgressBar::chunk {{ background: {hp_chunk}; border-radius: 2px; }}")
        self.stamina_bar.setStyleSheet(f"{pb_base_style} QProgressBar::chunk {{ background: {stamina_chunk}; border-radius: 2px; }}")
        self.mana_bar.setStyleSheet(f"{pb_base_style} QProgressBar::chunk {{ background: {mana_chunk}; border-radius: 2px; }}") 

        self.setFrameStyle(active=False)

        current_hp = self.hp_bar.value()
        max_hp = self.hp_bar.maximum()
        self._update_hp_bar_color(current_hp, max_hp)
        self.update()
        
    @Slot(dict)
    def animate_ui_bar_update_phase1(self, update_data: Dict[str, Any]):
        """
        Handles Phase 1 of a bar update: show impending loss.
        """
        bar_type = update_data.get("bar_type")
        new_value_preview = update_data.get("new_value_preview") 
        max_value = update_data.get("max_value")

        logger.debug(f"EntityWidget {self.entity_id} PHASE 1 ANIM: {bar_type} to preview {new_value_preview}/{max_value}")

        target_bar = None
        bleak_color = "#777777A0" # Default fallback
        pb_styles = self.palette.get('progress_bars', {})

        if bar_type == "hp": 
            target_bar = self.hp_bar
            hp_percent_preview = (new_value_preview / max_value) * 100 if max_value > 0 else 0
            if hp_percent_preview < 25: bleak_color = pb_styles.get("hp_bleak_critical", bleak_color)
            elif hp_percent_preview < 50: bleak_color = pb_styles.get("hp_bleak_low", bleak_color)
            else: bleak_color = pb_styles.get("hp_bleak_normal", bleak_color)
        elif bar_type == "stamina": 
            target_bar = self.stamina_bar
            bleak_color = pb_styles.get("stamina_bleak", bleak_color)
        elif bar_type == "mana":
            target_bar = self.mana_bar
            bleak_color = pb_styles.get("mana_bleak", bleak_color)
        else:
            logger.warning(f"EntityWidget {self.entity_id}: Unknown bar_type '{bar_type}' for phase 1 animation.")
            if hasattr(get_game_engine()._combat_orchestrator, '_handle_visual_display_complete'):
                QTimer.singleShot(0, get_game_engine()._combat_orchestrator._handle_visual_display_complete)
            return

        if target_bar and new_value_preview is not None and max_value is not None:
            original_stylesheet = target_bar.styleSheet()
            
            updated_stylesheet = re.sub(r"(QProgressBar::chunk\s*{)[^}]*(})",
                                        rf"\1 background: {bleak_color}; border-radius: 2px; \2",
                                        original_stylesheet, count=1, flags=re.IGNORECASE | re.DOTALL)

            target_bar.setStyleSheet(updated_stylesheet)
            target_bar.setFormat(f"{new_value_preview} / {max_value} (...)")

            self._pending_bar_update_data = {
                "bar_type": bar_type,
                "final_value": new_value_preview,
                "max_value": max_value,
                "original_stylesheet": original_stylesheet 
            }
        else:
            logger.warning(f"Could not animate phase 1 for {self.entity_id}, bar_type: {bar_type}, data: {update_data}")

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