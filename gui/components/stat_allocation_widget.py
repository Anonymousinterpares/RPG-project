#!/usr/bin/env python3
"""
Stat allocation widget for character creation and level-up.
"""

import os
from typing import Dict, Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, 
    QFrame, QGroupBox, QPushButton, QToolTip, QDialog, QFrame 
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap, QCursor

from core.stats.stats_base import StatType
from core.stats.stat_allocation import StatPointAllocator
from core.stats.stats_manager import StatsManager
from core.stats.stat_modifier_info import StatModifierInfo
from core.utils.logging_config import get_logger, log_migration_fix
from gui.styles.theme_manager import get_theme_manager

# Log the import fix
log_migration_fix(
    "gui.components.stat_allocation_widget", 
    "from core.utils.logging_config import get_logger, LogCategory\nlogger = get_logger(LogCategory.GUI)", 
    "from core.utils.logging_config import get_logger\nlogger = get_logger(\"GUI\")"
)

logger = get_logger("GUI")
class TooltipLabel(QLabel):
    """A custom label that shows a tooltip when hovered over."""
    
    def __init__(self, text="", tooltip="", parent=None):
        super().__init__(text, parent)
        self.tooltip_text = tooltip
        self.setMouseTracking(True)
    
    def enterEvent(self, event):
        """Show tooltip when mouse enters label area."""
        if self.tooltip_text:
            QToolTip.showText(QCursor.pos(), self.tooltip_text, self)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Hide tooltip when mouse leaves label area."""
        if self.tooltip_text:
            QToolTip.hideText()
        super().leaveEvent(event)
    
    def setTooltipText(self, text):
        """Set the tooltip text."""
        self.tooltip_text = text

class StatInfoDialog(QDialog):
    """Dialog for displaying detailed information about a stat."""
    
    def __init__(self, stat_name: str, stat_value: int, modifier_info: StatModifierInfo, palette: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.palette = palette
        colors = self.palette['colors']

        # Configure dialog
        self.setWindowTitle(f"{stat_name} Stat Information")
        self.setFixedSize(400, 400)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['bg_medium']};
                color: {colors['text_bright']};
            }}
            QLabel {{
                color: {colors['text_bright']};
            }}
            QGroupBox {{
                background-color: {colors['bg_dark']};
                border: 1px solid {colors['border_dark']};
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                color: {colors['text_primary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
            }}
        """)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Stat title
        title_label = QLabel(f"<h2 style='color: {colors['text_primary']};'>{stat_name}</h2>")
        layout.addWidget(title_label)

        # Stat description
        stat_descriptions = {
            "STR": "<b>Strength</b> represents physical power and affects melee damage, carrying capacity, and physical force.",
            "DEX": "<b>Dexterity</b> represents agility, reflexes, and balance. It affects initiative, ranged attacks, and ability to dodge.",
            "CON": "<b>Constitution</b> represents health, stamina, and vital force. It affects hit points, resistance to poison, and fatigue.",
            "INT": "<b>Intelligence</b> represents reasoning, memory, and learning ability. It affects spell power, knowledge skills, and ability to analyze.",
            "WIS": "<b>Wisdom</b> represents intuition, perception, and willpower. It affects magical resistance, perception checks, and survival skills.",
            "CHA": "<b>Charisma</b> represents force of personality, persuasiveness, and leadership. It affects social interactions, prices, and follower loyalty.",
            "WIL": "<b>Willpower</b> represents mental fortitude, focus, and resistance to stress or mental influence. It affects concentration, resisting fear, and pushing through mental challenges.",
            "INS": "<b>Insight</b> represents understanding, intuition, and awareness of subtle details in situations and people. It affects perception checks, reading motives, and making intuitive leaps."
        }

        description = stat_descriptions.get(stat_name, "")
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {colors['text_secondary']}; 
            background-color: {colors['bg_dark']}; 
            padding: 10px; 
            border-radius: 5px;
        """)
        layout.addWidget(desc_label)

        # Current values section
        values_group = QGroupBox("Current Values")
        values_layout = QVBoxLayout(values_group)

        # Base value
        base_value = stat_value
        race_mod = modifier_info.race_modifiers.get(stat_name, 0)
        class_mod = modifier_info.class_modifiers.get(stat_name, 0)
        total_value = base_value + race_mod + class_mod
        ability_mod = (total_value - 10) // 2
        min_req = modifier_info.minimum_requirements.get(stat_name, 0)
        
        pos_color = colors['accent_positive']
        neg_color = colors['accent_negative']
        sec_color = colors['text_secondary']

        values_text = f"""<p><b>Base Value:</b> {base_value}</p>
        <p><b>Race Modifier:</b> <span style='color: {pos_color if race_mod > 0 else (neg_color if race_mod < 0 else sec_color)}'>{'+'+ str(race_mod) if race_mod > 0 else race_mod if race_mod != 0 else '0'}</span> ({modifier_info.race_name})</p>
        <p><b>Class Modifier:</b> <span style='color: {pos_color if class_mod > 0 else (neg_color if class_mod < 0 else sec_color)}'>{'+'+ str(class_mod) if class_mod > 0 else class_mod if class_mod != 0 else '0'}</span> ({modifier_info.class_name})</p>
        <p><b>Total Value:</b> {total_value}</p>
        <p><b>Ability Modifier:</b> <span style='color: {pos_color if ability_mod > 0 else (neg_color if ability_mod < 0 else sec_color)}'>{'+'+ str(ability_mod) if ability_mod > 0 else ability_mod if ability_mod != 0 else '0'}</span></p>"""

        # Add minimum requirement if it exists
        if min_req > 0:
            values_text += f"""<p><b>Minimum Requirement:</b> <span style='color: {pos_color if total_value >= min_req else neg_color}>{min_req}</span> ({modifier_info.class_name})</p>"""

        values_label = QLabel(values_text)
        values_label.setWordWrap(True)
        values_layout.addWidget(values_label)
        layout.addWidget(values_group)

        # Game effects section
        effects_group = QGroupBox("Game Effects")
        effects_layout = QVBoxLayout(effects_group)

        # Effects based on the stat
        effects = {
            "STR": ["Melee attack damage", "Carrying capacity", "Breaking objects", "Grappling"],
            "DEX": ["Ranged attack accuracy", "Initiative in combat", "Dodge chance", "Stealth"],
            "CON": ["Hit points", "Resistance to poison", "Stamina and fatigue", "Survival in harsh conditions"],
            "INT": ["Spell power", "Knowledge and lore", "Language comprehension", "Puzzle solving"],
            "WIS": ["Magical resistance", "Perception", "Survival skills", "Willpower checks"],
            "CHA": ["NPC reactions", "Prices when buying/selling", "Leadership", "Persuasion attempts"],
            "WIL": ["Resisting mental attacks/control", "Maintaining concentration (spells)", "Enduring stress/fear", "Pushing through fatigue"],
            "INS": ["Detecting lies/motives", "Noticing hidden details", "Understanding complex situations", "Making intuitive connections"]
        }

        effects_text = "<p>This stat affects:</p><ul>"
        for effect in effects.get(stat_name, []):
            modifier_text = "+" if ability_mod > 0 else "-" if ability_mod < 0 else "±"
            effects_text += f"<li>{effect} <span style='color: {pos_color if ability_mod > 0 else (neg_color if ability_mod < 0 else sec_color)}'>({modifier_text})</span></li>"
        effects_text += "</ul>"

        effects_label = QLabel(effects_text)
        effects_label.setWordWrap(True)
        effects_layout.addWidget(effects_label)
        layout.addWidget(effects_group)

        # Class importance
        importance = "Unknown"
        importance_color = sec_color

        # Use accent colors for importance
        if stat_name in modifier_info.recommended_stats.get("primary", []):
            importance = "Primary"
            importance_color = colors['accent_positive']
        elif stat_name in modifier_info.recommended_stats.get("secondary", []):
            importance = "Secondary"
            importance_color = colors['text_primary'] # Gold/Amber
        elif stat_name in modifier_info.recommended_stats.get("tertiary", []):
            importance = "Tertiary"
            importance_color = colors['res_health'] # Reddish

        importance_text = f"<p><b>Importance for {modifier_info.class_name}:</b> <span style='color: {importance_color}'>{importance}</span></p>"
        importance_label = QLabel(importance_text)
        importance_label.setWordWrap(True)
        layout.addWidget(importance_label)

        # Close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors['bg_light']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_dark']};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors['state_hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['state_pressed']};
            }}
        """)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, 0, Qt.AlignCenter)
class StatRow:
    """A class to hold UI elements for a stat row."""
    
    def __init__(self):
        self.name_label = None
        self.info_button = None
        self.base_label = None
        self.increase_button = None
        self.decrease_button = None
        self.race_mod_label = None
        self.class_mod_label = None
        self.total_label = None
        self.mod_label = None


class StatAllocationWidget(QWidget):
    """Widget for allocating stat points during character creation or level-up."""
    
    # Signal emitted when stats change
    stats_changed = Signal(dict)
    allocation_complete = Signal()
    
    def __init__(
        self, 
        stats_manager: StatsManager,
        race_name: str = "Human",
        class_name: str = "Warrior",
        total_points: int = 27,
        min_value: int = 8,
        max_value: int = 15,
        parent: Optional[QWidget] = None
    ):
        """Initialize the stat allocation widget."""
        super().__init__(parent)
        
        # --- THEME MANAGEMENT ---
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        # --- END THEME MANAGEMENT ---

        # Set up the stat allocator
        self.stats_manager = stats_manager
        self.allocator = StatPointAllocator(stats_manager, total_points, min_value, max_value)
        
        # Load race and class modifiers
        self.modifier_info = StatModifierInfo()
        self.modifier_info.load_modifiers(race_name, class_name)
        
        # Create UI elements dictionary
        self.stat_rows = {}
        
        # Create the UI elements
        self._setup_ui()
        
        # Initialize preset buttons based on the loaded modifiers
        self._update_preset_buttons()
        
        # Apply initial theme (will also style the preset buttons)
        self._update_theme()
        
        # Update the display
        self._update_all_stat_displays()

    
    def _setup_ui(self):
        """Set up the user interface."""
        # Create the main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Create the stats info header
        header_layout = QHBoxLayout()

        # Points remaining label
        self.points_label = QLabel(f"Points Remaining: {self.allocator.get_remaining_points()}")
        # Styling moved to _update_theme
        header_layout.addWidget(self.points_label)

        # Add spacer
        header_layout.addStretch()

        # Add reset button
        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Reset all stats to minimum values")
        self.reset_button.setFixedWidth(80)
        self.reset_button.clicked.connect(self._reset_stats)
        header_layout.addWidget(self.reset_button)

        # Add header to main layout
        main_layout.addLayout(header_layout)

        # Create the stat grid
        self.stats_group = QGroupBox("Character Stats")
        # Styling moved to _update_theme

        stats_layout = QGridLayout(self.stats_group)
        stats_layout.setContentsMargins(15, 20, 15, 15)
        stats_layout.setHorizontalSpacing(5) 
        stats_layout.setVerticalSpacing(10) 

        col1_start = 0
        col2_start = 8
        separator_col = 7
        num_cols_per_stat = 7
        num_stats_per_col = 4 

        headers = ["Stat", "Base", "Adjust", "Race", "Class", "Total", "Mod"]
        for col_offset in [col1_start, col2_start]:
            for i, header_text in enumerate(headers):
                if header_text == "Mod":
                    header_widget = TooltipLabel(header_text, "") # Tooltip set later
                    header_widget.setProperty("is_mod_header", True) # Mark for styling
                    header_widget.setCursor(Qt.WhatsThisCursor)
                else:
                    header_widget = QLabel(header_text)
                    header_widget.setProperty("is_header", True) # Mark for styling
                stats_layout.addWidget(header_widget, 0, col_offset + i, alignment=Qt.AlignCenter)

        all_stat_types = list(StatType) 
        for index, stat_type in enumerate(all_stat_types):
            stat_name = str(stat_type)
            row = (index % num_stats_per_col) + 1 
            col_offset = col1_start if index < num_stats_per_col else col2_start

            stat_row = StatRow()

            # Stat Name & Icons
            stat_name_layout = QHBoxLayout()
            stat_name_layout.setSpacing(2)
            stat_name_layout.setContentsMargins(0, 0, 0, 0)

            stat_row.name_label = QLabel(stat_name)
            stat_row.name_label.setCursor(Qt.PointingHandCursor)
            stat_row.name_label.mousePressEvent = lambda event, s=stat_type: self._show_stat_info(s)

            # Icons
            impact_icons = {
                "STR": [("⚔️", "Melee Combat Damage"), ("🏋️", "Carrying Capacity")],
                "DEX": [("🏹", "Ranged Attack Accuracy"), ("👟", "Initiative/Dodge")], 
                "CON": [("❤️", "Health Points"), ("🛡️", "Damage Resistance")],
                "INT": [("📚", "Knowledge & Learning"), ("✨", "Spell Power")],
                "WIS": [("👁️", "Perception"), ("🙏", "Magical Resistance")], 
                "CHA": [("💬", "Persuasion"), ("👑", "Leadership/Prices")],
                "WIL": [("🧠", "Mental Fortitude"), ("🛡️", "Resist Influence")],
                "INS": [("💡", "Intuition/Problem Solving"), ("🧐", "Reading People/Situations")] 
            }
            stat_icons = impact_icons.get(stat_name, [])
            icons_layout = QHBoxLayout()
            icons_layout.setSpacing(1)
            icons_layout.setContentsMargins(0, 0, 0, 0)
            for icon, tooltip in stat_icons:
                icon_label = TooltipLabel(icon, tooltip)
                icon_label.setStyleSheet("font-size: 12px;")
                icon_label.setFixedWidth(20)
                icon_label.setAlignment(Qt.AlignCenter)
                icons_layout.addWidget(icon_label)
            icons_widget = QWidget()
            icons_widget.setLayout(icons_layout)
            icons_widget.setFixedWidth(45)
            icons_widget.setMouseTracking(True)

            # Info Button
            stat_row.info_button = QPushButton()
            # Icon set in _update_theme
            stat_row.info_button.setIconSize(QSize(16, 16))
            stat_row.info_button.setFixedSize(20, 20)
            stat_row.info_button.setCursor(Qt.PointingHandCursor)
            stat_row.info_button.setToolTip("Click for detailed information")
            stat_row.info_button.clicked.connect(lambda checked=False, s=stat_type: self._show_stat_info(s))

            stat_name_layout.addWidget(stat_row.name_label)
            stat_name_layout.addWidget(icons_widget)
            stat_name_layout.addWidget(stat_row.info_button)

            # Base Value
            base_value = int(self.stats_manager.get_stat_value(stat_type))
            stat_row.base_label = QLabel(str(base_value))
            stat_row.base_label.setAlignment(Qt.AlignCenter)

            # Adjustment Buttons
            adjust_layout = QHBoxLayout()
            adjust_layout.setSpacing(2)
            
            # Icons loaded in _update_theme or kept here if standard
            project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
            left_arrow_path = os.path.join(project_root, "images", "icons", "left_arrow.svg")
            right_arrow_path = os.path.join(project_root, "images", "icons", "right_arrow.svg")
            
            stat_row.decrease_button = QPushButton()
            stat_row.decrease_button.setIcon(QIcon(left_arrow_path))
            stat_row.decrease_button.setIconSize(QSize(16, 16)); stat_row.decrease_button.setFixedSize(24, 24)
            stat_row.decrease_button.clicked.connect(lambda checked=False, s=stat_type: self._decrease_stat(s))
            
            stat_row.increase_button = QPushButton()
            stat_row.increase_button.setIcon(QIcon(right_arrow_path))
            stat_row.increase_button.setIconSize(QSize(16, 16)); stat_row.increase_button.setFixedSize(24, 24)
            stat_row.increase_button.clicked.connect(lambda checked=False, s=stat_type: self._increase_stat(s))
            
            adjust_layout.addWidget(stat_row.decrease_button)
            adjust_layout.addWidget(stat_row.increase_button)

            # Modifiers
            stat_row.race_mod_label = QLabel("0")
            stat_row.race_mod_label.setAlignment(Qt.AlignCenter)

            stat_row.class_mod_label = QLabel("0")
            stat_row.class_mod_label.setAlignment(Qt.AlignCenter)

            stat_row.total_label = QLabel("0")
            stat_row.total_label.setAlignment(Qt.AlignCenter)

            stat_row.mod_label = QLabel("0")
            stat_row.mod_label.setAlignment(Qt.AlignCenter)

            # Add to grid
            stats_layout.addLayout(stat_name_layout, row, col_offset + 0)
            stats_layout.addWidget(stat_row.base_label, row, col_offset + 1, alignment=Qt.AlignCenter)
            stats_layout.addLayout(adjust_layout, row, col_offset + 2)
            stats_layout.addWidget(stat_row.race_mod_label, row, col_offset + 3, alignment=Qt.AlignCenter)
            stats_layout.addWidget(stat_row.class_mod_label, row, col_offset + 4, alignment=Qt.AlignCenter)
            stats_layout.addWidget(stat_row.total_label, row, col_offset + 5, alignment=Qt.AlignCenter)
            stats_layout.addWidget(stat_row.mod_label, row, col_offset + 6, alignment=Qt.AlignCenter)

            self.stat_rows[stat_type] = stat_row

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.VLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        stats_layout.addWidget(self.separator, 1, separator_col, num_stats_per_col, 1) 

        # Column stretch
        for col_offset in [col1_start, col2_start]:
            stats_layout.setColumnStretch(col_offset + 0, 3) 
            stats_layout.setColumnStretch(col_offset + 1, 1) 
            stats_layout.setColumnStretch(col_offset + 2, 2) 
            stats_layout.setColumnStretch(col_offset + 3, 1) 
            stats_layout.setColumnStretch(col_offset + 4, 1) 
            stats_layout.setColumnStretch(col_offset + 5, 1) 
            stats_layout.setColumnStretch(col_offset + 6, 1) 
        stats_layout.setColumnStretch(separator_col, 0)

        # Explanation Label
        self.stat_colors_explanation = QLabel("* Stat colors: Primary, Secondary, Tertiary for your class")
        stats_layout.addWidget(self.stat_colors_explanation, num_stats_per_col + 1, 0, 1, col2_start + num_cols_per_stat, Qt.AlignLeft)

        main_layout.addWidget(self.stats_group)

        # Quick Presets
        self.presets_group = QGroupBox("Quick Presets")
        presets_layout = QHBoxLayout(self.presets_group)
        presets_layout.setContentsMargins(15, 20, 15, 15); presets_layout.setSpacing(10)
        self.preset_buttons = {}
        # Buttons added dynamically in _update_preset_buttons, styled in _update_theme
        
        main_layout.addWidget(self.presets_group)

        # Info Label
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        main_layout.addWidget(self.info_label)

        main_layout.addStretch(1)

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        """Update styles from the theme palette."""
        if palette:
            self.palette = palette
        
        colors = self.palette['colors']
        
        # Labels
        self.points_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {colors['text_primary']};")
        self.stat_colors_explanation.setText(f"* Stat colors: <span style='color: {colors['accent_positive']}'>Primary</span>, <span style='color: {colors['text_primary']}'>Secondary</span>, <span style='color: {colors['res_health']}'>Tertiary</span> for your class")
        self.stat_colors_explanation.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 10px; font-style: italic;")
        
        self.info_label.setStyleSheet(f"QLabel {{ color: {colors['text_secondary']}; background-color: {colors['bg_dark']}; padding: 10px; border-radius: 5px; }}")

        # Group Boxes
        group_style = f"""
            QGroupBox {{
                background-color: {colors['bg_light']};
                border: 1px solid {colors['border_dark']};
                border-radius: 5px;
                margin-top: 15px;
                font-weight: bold;
                color: {colors['text_primary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding-left: 10px;
                padding-right: 10px;
            }}
        """
        self.stats_group.setStyleSheet(group_style)
        self.presets_group.setStyleSheet(group_style)

        # Buttons Base Styles
        btn_style_base = f"border-radius: 4px; border: none;"
        btn_style_neg = f"QPushButton {{ background-color: {colors['accent_negative']}; {btn_style_base} }} QPushButton:hover {{ background-color: {colors['accent_negative_light']}; }} QPushButton:disabled {{ background-color: {colors['text_disabled']}; }}"
        btn_style_pos = f"QPushButton {{ background-color: {colors['accent_positive']}; {btn_style_base} }} QPushButton:hover {{ background-color: {colors['accent_positive_light']}; }} QPushButton:disabled {{ background-color: {colors['text_disabled']}; }}"
        btn_style_standard = f"""
            QPushButton {{
                background-color: {colors['bg_dark']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_dark']};
                border-radius: 4px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{ background-color: {colors['state_hover']}; }}
        """
        
        self.reset_button.setStyleSheet(btn_style_standard)

        # Style Preset Buttons
        if hasattr(self, 'preset_buttons'):
            for btn in self.preset_buttons.values():
                btn.setStyleSheet(btn_style_standard)

        # Headers in grid
        mod_tooltip_style = (
            f"<div style='background-color: {colors['bg_medium']}; padding: 8px; border: 1px solid {colors['border_dark']}; border-radius: 3px; color: {colors['text_secondary']};'>"
            f"<b style='color: {colors['text_primary']};'>Ability Score Modifier</b><br>"
            "Calculated as: (Total Stat Value - 10) ÷ 2, rounded down.<br><br>"
            "This is the bonus/penalty applied to actions using this stat.<br>"
            "e.g., a Strength of 14 gives a +2 modifier to melee attacks."
            "</div>"
        )
        
        # Iterate children to style headers created in _setup_ui
        for child in self.stats_group.findChildren(QLabel):
            if child.property("is_mod_header"):
                child.setStyleSheet(f"font-weight: bold; color: {colors['text_secondary']}; text-decoration: underline dotted;")
                if isinstance(child, TooltipLabel): child.setTooltipText(mod_tooltip_style)
            elif child.property("is_header"):
                child.setStyleSheet(f"font-weight: bold; color: {colors['text_secondary']};")

        # Separator
        self.separator.setStyleSheet(f"color: {colors['border_dark']};")

        # Update rows
        for stat_type, row in self.stat_rows.items():
            # Info Button
            row.info_button.setIcon(self._create_info_icon()) # Re-create to match theme colors
            row.info_button.setStyleSheet("""
                QPushButton { background-color: transparent; border: none; }
                QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); border-radius: 10px; }
            """)

            # Buttons
            row.decrease_button.setStyleSheet(btn_style_neg)
            row.increase_button.setStyleSheet(btn_style_pos)

            # Labels
            row.base_label.setStyleSheet(f"color: {colors['text_bright']};")
            # Note: total_label, mod_label, etc. colors depend on values, updated in _update_stat_display
            
            # Update stat name color based on importance
            stat_name = str(stat_type)
            name_color = colors['text_bright']
            if stat_name in self.modifier_info.recommended_stats.get("primary", []): name_color = colors['accent_positive']
            elif stat_name in self.modifier_info.recommended_stats.get("secondary", []): name_color = colors['text_primary']
            elif stat_name in self.modifier_info.recommended_stats.get("tertiary", []): name_color = colors['res_health']
            row.name_label.setStyleSheet(f"color: {name_color}; font-weight: bold;")

        # Re-trigger display update to catch value-dependent styling
        self._update_all_stat_displays()

    def _increase_stat(self, stat_type: StatType) -> None:
        """
        Increase a stat by one point.

        Args:
            stat_type: The stat to increase
        """
        if self.allocator.increase_stat(stat_type):
            # Update stat display
            self._update_stat_display(stat_type)

            # Update points remaining label
            remaining_points = self.allocator.get_remaining_points() # Get remaining points
            self.points_label.setText(f"Points Remaining: {remaining_points}")

            # Emit signal with current stats
            self._emit_stats_changed()

            # --- EMIT COMPLETION SIGNAL ---
            if remaining_points == 0:
                self.allocation_complete.emit()
    
    def _decrease_stat(self, stat_type: StatType) -> None:
        """
        Decrease a stat by one point.

        Args:
            stat_type: The stat to decrease
        """
        # --- GET PREVIOUS REMAINING ---
        prev_remaining_points = self.allocator.get_remaining_points()
        # --- END GET PREVIOUS REMAINING ---

        if self.allocator.decrease_stat(stat_type):
            # Update stat display
            self._update_stat_display(stat_type)

            # Update points remaining
            remaining_points = self.allocator.get_remaining_points() # Get remaining points
            self.points_label.setText(f"Points Remaining: {remaining_points}")

            # Emit signal with current stats
            self._emit_stats_changed()

            # --- EMIT COMPLETION SIGNAL (Check if went FROM 0) ---

            if remaining_points == 0 and prev_remaining_points != 0:
                 self.allocation_complete.emit()
            elif remaining_points != 0 and prev_remaining_points == 0:

                 pass 
            # --- END EMIT COMPLETION SIGNAL ---

    def are_points_fully_allocated(self) -> bool:
        """Checks if all available points have been allocated."""
        # Ensure allocator exists before calling its method
        return hasattr(self, 'allocator') and self.allocator.get_remaining_points() == 0

    def get_remaining_points(self) -> int:
        """Returns the number of points remaining to be allocated."""
         # Ensure allocator exists before calling its method
        return self.allocator.get_remaining_points() if hasattr(self, 'allocator') else 0
    
    def _update_stat_display(self, stat_type: StatType) -> None:
        """
        Update the display for a specific stat.
        """
        if stat_type not in self.stat_rows:
            return
        
        stat_row = self.stat_rows[stat_type]
        stat_name = str(stat_type)
        colors = self.palette['colors']
        
        # Get current values
        base_value = int(self.stats_manager.get_stat_value(stat_type))
        race_mod = self.modifier_info.race_modifiers.get(stat_name, 0)
        class_mod = self.modifier_info.class_modifiers.get(stat_name, 0)
        total_value = base_value + race_mod + class_mod
        modifier = (total_value - 10) // 2
        
        # Update labels
        stat_row.base_label.setText(str(base_value))
        stat_row.total_label.setText(str(total_value))
        
        mod_text = f"{modifier:+d}" if modifier != 0 else "0"
        stat_row.mod_label.setText(mod_text)
        stat_row.mod_label.setStyleSheet(f"color: {colors['accent_positive'] if modifier > 0 else (colors['accent_negative'] if modifier < 0 else colors['text_secondary'])};")
        
        # Update modifiers colors
        race_color = colors['accent_positive'] if race_mod > 0 else (colors['accent_negative'] if race_mod < 0 else colors['text_secondary'])
        stat_row.race_mod_label.setStyleSheet(f"color: {race_color};")
        
        class_color = colors['accent_positive'] if class_mod > 0 else (colors['accent_negative'] if class_mod < 0 else colors['text_secondary'])
        stat_row.class_mod_label.setStyleSheet(f"color: {class_color};")

        # Update tooltips with new values
        tooltip_text = self.modifier_info.get_tooltip_text(stat_name, base_value)
        for widget in [stat_row.name_label, stat_row.base_label, stat_row.race_mod_label, 
                      stat_row.class_mod_label, stat_row.total_label, stat_row.mod_label]:
            widget.setToolTip(tooltip_text)
        
        # Update button states
        stat_row.increase_button.setEnabled(self.allocator.can_increase_stat(stat_type))
        stat_row.decrease_button.setEnabled(self.allocator.can_decrease_stat(stat_type))
        
        # Check if total meets minimum requirement
        min_req = self.modifier_info.minimum_requirements.get(stat_name, 0)
        if min_req > 0 and total_value < min_req:
            stat_row.total_label.setStyleSheet(f"color: {colors['accent_negative']}; font-weight: bold;")
        else:
            stat_row.total_label.setStyleSheet(f"color: {colors['text_bright']}; font-weight: bold;")
    
    def _update_all_stat_displays(self) -> None:
        """Update all stat displays."""
        for stat_type in StatType:
            self._update_stat_display(stat_type)
        
        # Update points remaining
        self.points_label.setText(f"Points Remaining: {self.allocator.get_remaining_points()}")
    
    def _reset_stats(self) -> None:
        """Reset all stats to minimum values."""
        self.allocator.reset_to_minimum()
        self._update_all_stat_displays()
        self._emit_stats_changed()
    
    def _apply_preset(self, preset_name: str) -> None:
        """
        Apply a preset stat distribution.
        
        Args:
            preset_name: The name of the preset to apply
        """
        preset_stats = self.modifier_info.apply_preset(preset_name)
        if not preset_stats:
            return
        
        # Reset stats first
        self.allocator.reset_to_minimum()
        
        # Apply preset values
        for stat_name, value in preset_stats.items():
            try:
                stat_type = StatType.from_string(stat_name)
                current_value = int(self.stats_manager.get_stat_value(stat_type))
                
                # Increase the stat until it reaches the preset value or we can't increase anymore
                while current_value < value and self.allocator.can_increase_stat(stat_type):
                    self.allocator.increase_stat(stat_type)
                    current_value = int(self.stats_manager.get_stat_value(stat_type))
            except ValueError:
                logger.warning(f"Unknown stat in preset: {stat_name}")
        
        # Update all displays
        self._update_all_stat_displays()
        self._emit_stats_changed()
    
    def _auto_allocate(self, balanced: bool = True) -> None:
        """
        Automatically allocate points.
        
        Args:
            balanced: If True, use balanced distribution; otherwise prioritize primary stats
        """
        # Get the recommended stats order
        priority_stats = []
        
        if self.modifier_info.recommended_stats:
            # Add primary stats first
            priority_stats.extend([StatType.from_string(s) for s in self.modifier_info.recommended_stats.get("primary", [])])
            
            # Then secondary stats
            priority_stats.extend([StatType.from_string(s) for s in self.modifier_info.recommended_stats.get("secondary", [])])
            
            # Then tertiary stats
            priority_stats.extend([StatType.from_string(s) for s in self.modifier_info.recommended_stats.get("tertiary", [])])
            
        # If no priorities defined, use a standard order
        if not priority_stats:
            priority_stats = list(StatType)
        
        # Reset to minimum first
        self.allocator.reset_to_minimum()
        
        # Apply automatic allocation
        self.allocator.allocate_points_automatically(priority_stats, balanced)
        
        # Update displays
        self._update_all_stat_displays()
        
        # Emit signal with current stats
        self._emit_stats_changed()
    
    def _emit_stats_changed(self) -> None:
        """Emit the stats_changed signal with current stats."""
        # Get current stats with modifiers applied
        stats = {}
        for stat_type in StatType:
            stat_name = str(stat_type)
            base_value = int(self.stats_manager.get_stat_value(stat_type))
            total_value = base_value + self.modifier_info.get_combined_modifier(stat_name)
            stats[stat_name] = {
                "base": base_value,
                "total": total_value,
                "modifier": (total_value - 10) // 2
            }
        
        # Emit the signal
        self.stats_changed.emit(stats)
    
    def update_race_class(self, race_name: str, class_name: str) -> None:
        """
        Update the race and class modifiers.
        
        Args:
            race_name: The new race name
            class_name: The new class name
        """
        logger.info(f"Updating race to {race_name} and class to {class_name}")
        
        # Check if we're already using this race/class combination
        if race_name == self.modifier_info.race_name and class_name == self.modifier_info.class_name:
            logger.debug(f"Race and class already set to {race_name} and {class_name}, skipping update")
            return
        
        # Re-create the modifier info with new race/class to ensure fresh loading
        self.modifier_info = StatModifierInfo()
        self.modifier_info.load_modifiers(race_name, class_name)
        
        # Update UI for each stat
        for stat_type in StatType:
            if stat_type in self.stat_rows:
                stat_name = str(stat_type)
                stat_row = self.stat_rows[stat_type]
                
                # Update race modifier label
                race_mod = self.modifier_info.race_modifiers.get(stat_name, 0)
                mod_text = f"{race_mod:+d}" if race_mod != 0 else "0"
                stat_row.race_mod_label.setText(mod_text)
                stat_row.race_mod_label.setStyleSheet(f"color: {self.modifier_info.get_stat_modifier_color(stat_name, 'race')}; text-align: center;")
                
                # Update class modifier label
                class_mod = self.modifier_info.class_modifiers.get(stat_name, 0)
                mod_text = f"{class_mod:+d}" if class_mod != 0 else "0"
                stat_row.class_mod_label.setText(mod_text)
                stat_row.class_mod_label.setStyleSheet(f"color: {self.modifier_info.get_stat_modifier_color(stat_name, 'class')}; text-align: center;")
                
                # Update stat name color based on importance for current class
                name_color = "#E0E0E0"  # Default color
                if stat_name in self.modifier_info.recommended_stats.get("primary", []):
                    name_color = "#4CAF50"  # Green for primary stats
                elif stat_name in self.modifier_info.recommended_stats.get("secondary", []):
                    name_color = "#FFD700"  # Brighter yellow for secondary stats
                elif stat_name in self.modifier_info.recommended_stats.get("tertiary", []):
                    name_color = "#E65100"  # Darker orange for tertiary stats
                
                # Properly update style
                stat_row.name_label.setStyleSheet(f"color: {name_color}; font-weight: bold;")
                # Make sure cursor is maintained
                stat_row.name_label.setCursor(Qt.PointingHandCursor)
        
        # Update all displays to reflect changes
        self._update_all_stat_displays()
        
        # Update preset buttons
        self._update_preset_buttons()
        
        # Update race/class info
        self._update_race_class_info()
    
    def _update_preset_buttons(self) -> None:
        """Update the preset buttons based on current class."""
        # Clear existing buttons from the layout and dictionary
        if not hasattr(self, 'presets_group') or not self.presets_group.layout():
            return

        layout = self.presets_group.layout()
        
        # Remove all existing items from the layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.preset_buttons = {}
        
        # Add new preset buttons based on archetype presets
        for preset_name in self.modifier_info.archetype_presets:
            preset_button = QPushButton(preset_name)
            preset_button.setToolTip(self.modifier_info.archetype_presets[preset_name].get("description", ""))
            preset_button.clicked.connect(lambda checked=False, p=preset_name: self._apply_preset(p))
            layout.addWidget(preset_button)
            self.preset_buttons[preset_name] = preset_button
        
        # Add balanced/focused buttons if no archetypes found (fallback)
        if not self.preset_buttons:
            balanced_button = QPushButton("Balanced")
            balanced_button.setToolTip("Apply a balanced distribution of stats")
            balanced_button.clicked.connect(lambda: self._auto_allocate(balanced=True))
            layout.addWidget(balanced_button)
            self.preset_buttons["Balanced"] = balanced_button
            
            focused_button = QPushButton("Focused")
            focused_button.setToolTip("Focus on primary stats for your class")
            focused_button.clicked.connect(lambda: self._auto_allocate(balanced=False))
            layout.addWidget(focused_button)
            self.preset_buttons["Focused"] = focused_button
            
        # Apply current theme to the new buttons immediately
        self._update_theme()

    def _update_race_class_info(self) -> None:
        """Update the race/class information label."""
        info_text = f"""
        <p><b>{self.modifier_info.race_name}:</b> {self.modifier_info.race_description}</p>
        <p><b>{self.modifier_info.class_name}:</b> {self.modifier_info.class_description}</p>
        """
        
        # Find the info label
        info_label = None
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.widget() and isinstance(item.widget(), QLabel) and "background-color: #2D2D2D" in item.widget().styleSheet():
                info_label = item.widget()
                break
        
        if info_label:
            info_label.setText(info_text)
    
    def get_current_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get the current stat values.
        
        Returns:
            Dictionary of stat names and their values
        """
        stats = {}
        for stat_type in StatType:
            stat_name = str(stat_type)
            base_value = int(self.stats_manager.get_stat_value(stat_type))
            total_value = base_value + self.modifier_info.get_combined_modifier(stat_name)
            stats[stat_name] = {
                "base": base_value,
                "total": total_value,
                "modifier": (total_value - 10) // 2
            }
        return stats
    
    def meets_requirements(self) -> bool:
        """
        Check if the current stats meet all class minimum requirements.
        
        Returns:
            True if all requirements are met, False otherwise
        """
        for stat_type in StatType:
            stat_name = str(stat_type)
            min_req = self.modifier_info.minimum_requirements.get(stat_name, 0)
            if min_req > 0:
                base_value = int(self.stats_manager.get_stat_value(stat_type))
                total_value = base_value + self.modifier_info.get_combined_modifier(stat_name)
                if total_value < min_req:
                    return False
        return True
        
    def _create_info_icon(self) -> QIcon:
        """
        Create an information icon using theme colors.
        """
        colors = self.palette['colors']
        
        # Create a pixmap
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)

        # Draw an info icon using code
        from PySide6.QtGui import QPainter, QPen, QBrush
        from PySide6.QtCore import QRect

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw circle
        pen = QPen(QColor(colors['info_icon_bg']))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(colors['info_icon_bg_dark'])))
        painter.drawEllipse(2, 2, 20, 20)

        # Draw "i" character
        pen = QPen(QColor("white"))
        painter.setPen(pen)
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRect(0, 0, 24, 24), Qt.AlignCenter, "i")

        painter.end()

        return QIcon(pixmap)
    
    def _show_stat_info(self, stat_type: StatType) -> None:
        """
        Show detailed information about a stat.
        """
        stat_name = str(stat_type)
        base_value = int(self.stats_manager.get_stat_value(stat_type))

        # Create and show the dialog, passing the palette
        dialog = StatInfoDialog(stat_name, base_value, self.modifier_info, self.palette, self)
        dialog.exec_()

    def get_allocated_stats(self) -> Dict[str, int]:
        """
        Retrieves the current base stat values as allocated by the user.

        Returns:
            A dictionary mapping stat names (e.g., "STR") to their current base integer values.
        """
        allocated_stats = {}
        for stat_type in StatType:
            # Get the current BASE value directly from the stats manager
            # as the allocator modifies the manager's state
            base_value = self.stats_manager.get_stat(stat_type).base_value
            allocated_stats[str(stat_type)] = int(base_value) # Ensure it's an integer
        return allocated_stats