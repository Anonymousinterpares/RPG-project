#!/usr/bin/env python3
"""
Skill allocation widget for character creation and level-up.
"""

from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGroupBox, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, Signal, Slot

from core.stats.stats_manager import StatsManager
from core.stats.skill_allocation import SkillAllocator
from core.stats.stat_modifier_info import StatModifierInfo
from core.stats.skill_manager import get_skill_manager
from gui.styles.theme_manager import get_theme_manager

class SkillRow:
    """A class to hold UI elements for a skill row."""
    def __init__(self):
        self.name_label = None
        self.cost_label = None
        self.base_label = None
        self.increase_button = None
        self.decrease_button = None
        self.row_widget = None

class SkillAllocationWidget(QWidget):
    """Widget for allocating skill points."""
    
    skills_changed = Signal()
    allocation_complete = Signal()
    
    def __init__(
        self, 
        stats_manager: StatsManager,
        modifier_info: StatModifierInfo,
        parent: Optional[QWidget] = None
    ):
        """Initialize the skill allocation widget."""
        super().__init__(parent)
        
        self.stats_manager = stats_manager
        self.modifier_info = modifier_info
        self.skill_manager = get_skill_manager()
        self.theme_manager = get_theme_manager()
        self.palette = self.theme_manager.get_current_palette()
        self.theme_manager.theme_changed.connect(self._update_theme)
        
        # Allocator will be initialized when race/class is set/updated
        self.allocator = None
        
        self.skill_rows = {}
        self._setup_ui()
        self._update_theme()

    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        self.points_label = QLabel("Skill Points Remaining: -")
        header_layout.addWidget(self.points_label)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.setFixedWidth(80)
        self.reset_button.clicked.connect(self._reset_skills)
        header_layout.addWidget(self.reset_button)
        
        main_layout.addLayout(header_layout)

        # Skills List in Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        self.skills_layout = QVBoxLayout(scroll_content)
        self.skills_layout.setSpacing(2)
        self.skills_layout.setContentsMargins(0, 0, 0, 0)
        self.skills_layout.addStretch() # Push items to top
        
        self.scroll_area.setWidget(scroll_content)
        
        self.skills_group = QGroupBox("Skills")
        group_layout = QVBoxLayout(self.skills_group)
        group_layout.addWidget(self.scroll_area)
        
        main_layout.addWidget(self.skills_group)
        
        # Info Label
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        main_layout.addWidget(self.info_label)

    def update_race_class_origin(self, race_name: str, class_name: str, origin_name: str):
        """Update allocator and UI based on new selections."""
        # Ensure modifier info is up to date (it should be updated by parent before calling this)
        # But we can double check or reload if needed. Assuming parent handles load_modifiers.
        
        # Calculate available skill points: Base + INT Mod
        int_stat = int(self.stats_manager.get_stat_value("INT"))
        int_mod = (int_stat - 10) // 2
        total_points = self.modifier_info.skill_points_per_level + int_mod
        if total_points < 1: total_points = 1 # Minimum 1 point

        self.allocator = SkillAllocator(
            self.stats_manager,
            class_skills=self.modifier_info.class_skills,
            origin_skills=self.modifier_info.origin_skills,
            skill_points=total_points
        )
        
        self._rebuild_skill_list()
        self._update_display()

    def _rebuild_skill_list(self):
        """Rebuild the list of skills."""
        # Clear existing rows
        for i in reversed(range(self.skills_layout.count())): 
            item = self.skills_layout.itemAt(i)
            if item.widget(): item.widget().deleteLater()
            elif item.spacerItem(): self.skills_layout.removeItem(item)
            
        self.skill_rows = {}
        self.skills_layout.addStretch() # Re-add stretch at end
        
        # Sort skills alphabetically
        all_skills = sorted(self.stats_manager.skills.items())
        
        for skill_key, stat in all_skills:
            self._create_skill_row(skill_key, stat)
            
        # Move stretch to end
        self.skills_layout.removeItem(self.skills_layout.itemAt(0))
        self.skills_layout.addStretch()

    def _create_skill_row(self, skill_key: str, stat: Any):
        """Create a single skill row."""
        row_widget = QFrame()
        layout = QHBoxLayout(row_widget)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Name & Tooltip
        name_label = QLabel(stat.name)
        skill_data = self.skill_manager.get_skill(skill_key)
        desc = skill_data.get("description", "") if skill_data else ""
        
        # Determine status
        is_class = skill_key.lower() in self.allocator.class_skills
        is_origin = skill_key.lower() in self.allocator.origin_skills
        cost = self.allocator.get_skill_cost(skill_key)
        
        tooltip = f"<b>{stat.name}</b> ({stat.category.name})<br>{desc}<hr>"
        if is_origin: tooltip += "<span style='color:#FFD700'>Origin Skill (Rank 1 Free)</span><br>"
        if is_class: tooltip += "<span style='color:#4CAF50'>Class Skill (Cost: 1)</span>"
        else: tooltip += "<span style='color:#CCCCCC'>Cross-Class Skill (Cost: 2)</span>"
        
        name_label.setToolTip(tooltip)
        
        # Cost Label
        cost_label = QLabel(f"[{cost} pts]")
        cost_label.setFixedWidth(50)
        cost_label.setAlignment(Qt.AlignCenter)
        
        # Rank Label
        base_label = QLabel("0")
        base_label.setFixedWidth(30)
        base_label.setAlignment(Qt.AlignCenter)
        
        # Buttons
        decrease_btn = QPushButton("-")
        decrease_btn.setFixedSize(24, 24)
        decrease_btn.clicked.connect(lambda c, k=skill_key: self._decrease_skill(k))
        
        increase_btn = QPushButton("+")
        increase_btn.setFixedSize(24, 24)
        increase_btn.clicked.connect(lambda c, k=skill_key: self._increase_skill(k))
        
        layout.addWidget(name_label, 1)
        layout.addWidget(cost_label)
        layout.addWidget(decrease_btn)
        layout.addWidget(base_label)
        layout.addWidget(increase_btn)
        
        # Insert before stretch
        self.skills_layout.insertWidget(self.skills_layout.count() - 1, row_widget)
        
        row = SkillRow()
        row.name_label = name_label
        row.cost_label = cost_label
        row.base_label = base_label
        row.increase_button = increase_btn
        row.decrease_button = decrease_btn
        row.row_widget = row_widget
        
        self.skill_rows[skill_key] = row

    def _increase_skill(self, skill_key: str):
        if self.allocator and self.allocator.increase_skill(skill_key):
            scroll_bar = self.scroll_area.verticalScrollBar()
            scroll_position = scroll_bar.value()
            self._update_display()
            scroll_bar.setValue(scroll_position)
            self.skills_changed.emit()
            if self.allocator.get_remaining_points() == 0:
                self.allocation_complete.emit()

    def _decrease_skill(self, skill_key: str):
        if self.allocator and self.allocator.decrease_skill(skill_key):
            scroll_bar = self.scroll_area.verticalScrollBar()
            scroll_position = scroll_bar.value()
            self._update_display()
            scroll_bar.setValue(scroll_position)
            self.skills_changed.emit()

    def _reset_skills(self):
        if self.allocator:
            self.allocator.reset_skills()
            self._update_display()
            self.skills_changed.emit()

    def _update_display(self):
        """Update values and visual states."""
        if not self.allocator: return
        
        colors = self.palette['colors']
        remaining = self.allocator.get_remaining_points()
        self.points_label.setText(f"Skill Points Remaining: {remaining}")
        
        for skill_key, row in self.skill_rows.items():
            rank = int(self.stats_manager.get_skill_value(skill_key))
            row.base_label.setText(str(rank))
            
            # Button states
            row.increase_button.setEnabled(self.allocator.can_increase_skill(skill_key))
            row.decrease_button.setEnabled(self.allocator.can_decrease_skill(skill_key))
            
            # Styling based on status
            is_class = skill_key.lower() in self.allocator.class_skills
            is_origin = skill_key.lower() in self.allocator.origin_skills
            
            name_color = colors['text_primary']
            if is_origin: name_color = "#FFD700" # Gold
            elif is_class: name_color = "#4CAF50" # Green
            
            row.name_label.setStyleSheet(f"color: {name_color}; font-weight: {'bold' if is_class or is_origin else 'normal'};")
            
            if rank > 0:
                row.base_label.setStyleSheet(f"color: {colors['text_bright']}; font-weight: bold;")
            else:
                row.base_label.setStyleSheet(f"color: {colors['text_secondary']};")

    @Slot(dict)
    def _update_theme(self, palette: Optional[dict] = None):
        if palette: self.palette = palette
        colors = self.palette['colors']
        
        self.points_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {colors['text_primary']};")
        
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
        self.skills_group.setStyleSheet(group_style)
        
        btn_style = f"""
            QPushButton {{
                background-color: {colors['bg_dark']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_dark']};
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {colors['state_hover']}; }}
        """
        self.reset_button.setStyleSheet(btn_style)
        
        if self.allocator:
            self._update_display() # Re-apply row styles
