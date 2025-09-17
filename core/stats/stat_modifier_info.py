"""
Module for handling race and class stat modifiers.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

from core.utils.logging_config import get_logger, log_migration_fix

# Log the import fix
log_migration_fix(
    "core.stats.stat_modifier_info", 
    "from core.utils.logging_config import get_logger, LogCategory\nlogger = get_logger(LogCategory.SYSTEM)", 
    "from core.utils.logging_config import get_logger\nlogger = get_logger(\"STATS\")"
)

logger = get_logger("STATS")


class StatModifierInfo:
    """Holds information about stat modifiers from race/class."""
    
    def __init__(self):
        """Initialize the stat modifier info."""
        self.race_name = ""
        self.class_name = ""
        self.race_modifiers = {}
        self.class_modifiers = {}
        self.minimum_requirements = {}
        self.recommended_stats = {}
        self.race_color_bonus = "#4CAF50"  # Default green
        self.race_color_penalty = "#F44336"  # Default red
        self.class_color_bonus = "#2196F3"  # Default blue
        self.class_color_requirement = "#FF9800"  # Default orange
        self.below_minimum_color = "#F44336"  # Default red
        self.race_description = ""
        self.class_description = ""
        self.archetype_presets = {}
        
    def load_modifiers(self, race_name: str, class_name: str) -> None:
        """
        Load racial and class modifiers from config files.
        
        Args:
            race_name: The name of the selected race
            class_name: The name of the selected class
        """
        # Reset and store new names
        self.race_name = race_name
        self.class_name = class_name
        self.race_modifiers = {}
        self.class_modifiers = {}
        self.minimum_requirements = {}
        self.recommended_stats = {}
        self.race_description = ""
        self.class_description = ""
        self.archetype_presets = {}
        
        # Find the config directory
        project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
        race_config_path = os.path.join(project_root, "config", "character", "races.json")
        class_config_path = os.path.join(project_root, "config", "character", "classes.json")
        
        # Debug log paths
        logger.debug(f"Loading modifiers for race: {race_name}, class: {class_name}")
        logger.debug(f"Race config path: {race_config_path}")
        logger.debug(f"Class config path: {class_config_path}")
        
        # Load race data
        if os.path.exists(race_config_path):
            try:
                with open(race_config_path, 'r', encoding='utf-8') as f:
                    race_data = json.load(f)
                
                # Debug log available races
                available_races = list(race_data.get("races", {}).keys())
                logger.debug(f"Available races in config: {available_races}")
                
                if race_name in race_data.get("races", {}):
                    race_info = race_data["races"][race_name]
                    self.race_modifiers = race_info.get("stat_modifiers", {})
                    self.race_description = race_info.get("description", "")
                    
                    # Debug log loaded modifiers
                    logger.debug(f"Loaded race modifiers for {race_name}: {self.race_modifiers}")
                else:
                    logger.warning(f"Race '{race_name}' not found in config. Available races: {available_races}")
                    
                # Load display colors
                if "display_colors" in race_data:
                    self.race_color_bonus = race_data["display_colors"].get("racial_bonus", self.race_color_bonus)
                    self.race_color_penalty = race_data["display_colors"].get("racial_penalty", self.race_color_penalty)
            except Exception as e:
                logger.error(f"Error loading race data: {e}")
                self.race_modifiers = {}
                self.race_description = ""
        else:
            logger.error(f"Race config file not found: {race_config_path}")
        
        # Load class data
        if os.path.exists(class_config_path):
            try:
                with open(class_config_path, 'r', encoding='utf-8') as f:
                    class_data = json.load(f)
                
                # Debug log available classes
                available_classes = list(class_data.get("classes", {}).keys())
                logger.debug(f"Available classes in config: {available_classes}")
                
                if class_name in class_data.get("classes", {}):
                    class_info = class_data["classes"][class_name]
                    self.class_modifiers = class_info.get("stat_modifiers", {})
                    self.minimum_requirements = class_info.get("minimum_stats", {})
                    self.recommended_stats = class_info.get("recommended_stats", {})
                    self.class_description = class_info.get("description", "")
                    self.archetype_presets = class_info.get("archetypes", {})
                    
                    # Debug log loaded data
                    logger.debug(f"Loaded class modifiers for {class_name}: {self.class_modifiers}")
                    logger.debug(f"Loaded minimum requirements: {self.minimum_requirements}")
                    logger.debug(f"Loaded recommended stats: {self.recommended_stats}")
                else:
                    logger.warning(f"Class '{class_name}' not found in config. Available classes: {available_classes}")
                    
                # Load display colors
                if "display_colors" in class_data:
                    self.class_color_bonus = class_data["display_colors"].get("class_bonus", self.class_color_bonus)
                    self.class_color_requirement = class_data["display_colors"].get("class_requirement", self.class_color_requirement)
                    self.below_minimum_color = class_data["display_colors"].get("below_minimum", self.below_minimum_color)
            except Exception as e:
                logger.error(f"Error loading class data: {e}")
                self.class_modifiers = {}
                self.minimum_requirements = {}
                self.recommended_stats = {}
                self.class_description = ""
                self.archetype_presets = {}
        else:
            logger.error(f"Class config file not found: {class_config_path}")
    
    def get_combined_modifier(self, stat_type: str) -> int:
        """
        Get the combined race and class modifier for a stat.
        
        Args:
            stat_type: The stat type to get modifiers for
            
        Returns:
            The combined modifier value
        """
        race_mod = self.race_modifiers.get(stat_type, 0)
        class_mod = self.class_modifiers.get(stat_type, 0)
        return race_mod + class_mod
    
    def get_tooltip_text(self, stat_type: str, current_value: int) -> str:
        """
        Get tooltip text for a stat with modifier info.
        
        Args:
            stat_type: The stat to get tooltip for
            current_value: The current stat value
            
        Returns:
            Formatted tooltip text
        """
        race_mod = self.race_modifiers.get(stat_type, 0)
        class_mod = self.class_modifiers.get(stat_type, 0)
        min_req = self.minimum_requirements.get(stat_type, 0)
        
        # Calculate total value including modifiers
        total_value = current_value + race_mod + class_mod
        
        tooltip = f"<b>{stat_type}</b><hr>"
        
        # Base value
        tooltip += f"Base Value: {current_value}<br>"
        
        # Race modifier
        if race_mod != 0:
            sign = "+" if race_mod > 0 else ""
            tooltip += f"{self.race_name} Modifier: <span style='color: {'#4CAF50' if race_mod > 0 else '#F44336'}'>{sign}{race_mod}</span><br>"
        
        # Class modifier
        if class_mod != 0:
            sign = "+" if class_mod > 0 else ""
            tooltip += f"{self.class_name} Modifier: <span style='color: {'#2196F3' if class_mod > 0 else '#F44336'}'>{sign}{class_mod}</span><br>"
        
        # Total value
        tooltip += f"<b>Total Value: {total_value}</b><br>"
        
        # Minimum requirement
        if min_req > 0:
            tooltip += f"<hr>Minimum Requirement: <span style='color: {'#4CAF50' if total_value >= min_req else '#F44336'}'>{min_req}</span>"
            if total_value < min_req:
                tooltip += " <b>(not met)</b>"
            tooltip += "<br>"
        
        # Primary/secondary stat info
        if stat_type in (self.recommended_stats.get("primary", [])):
            tooltip += "<span style='color: #4CAF50'>This is a primary stat for your class!</span><br>"
        elif stat_type in (self.recommended_stats.get("secondary", [])):
            tooltip += "<span style='color: #FFC107'>This is a secondary stat for your class.</span><br>"
        
        return tooltip
    
    def meets_class_requirements(self, stat_values: Dict[str, int]) -> bool:
        """
        Check if the current stats meet class requirements.
        
        Args:
            stat_values: Dictionary of stat values with modifiers applied
            
        Returns:
            True if all requirements are met, False otherwise
        """
        for stat, min_value in self.minimum_requirements.items():
            if stat_values.get(stat, 0) < min_value:
                return False
        return True
    
    def get_total_stat_value(self, stat_type: str, base_value: int) -> int:
        """
        Calculate the total stat value after applying modifiers.
        
        Args:
            stat_type: The stat to calculate
            base_value: The base value before modifiers
            
        Returns:
            The total value after modifiers
        """
        race_mod = self.race_modifiers.get(stat_type, 0)
        class_mod = self.class_modifiers.get(stat_type, 0)
        return base_value + race_mod + class_mod
    
    def get_stat_modifier_color(self, stat_type: str, source: str = None) -> str:
        """
        Get the color to display a stat modifier.
        
        Args:
            stat_type: The stat type
            source: The modifier source ('race' or 'class')
            
        Returns:
            A color hex code
        """
        if source == 'race':
            mod = self.race_modifiers.get(stat_type, 0)
            return self.race_color_bonus if mod > 0 else (self.race_color_penalty if mod < 0 else "#CCCCCC")
        elif source == 'class':
            mod = self.class_modifiers.get(stat_type, 0)
            return self.class_color_bonus if mod > 0 else (self.race_color_penalty if mod < 0 else "#CCCCCC")
        else:
            # Combined or unknown
            mod = self.get_combined_modifier(stat_type)
            if mod > 0:
                return self.race_color_bonus
            elif mod < 0:
                return self.race_color_penalty
            else:
                return "#CCCCCC"
    
    def apply_preset(self, preset_name: str) -> Optional[Dict[str, int]]:
        """
        Get stat values from a class archetype preset.
        
        Args:
            preset_name: The name of the preset to apply
            
        Returns:
            Dictionary of base stat values, or None if preset not found
        """
        if preset_name in self.archetype_presets:
            return self.archetype_presets[preset_name].get("stat_distribution", None)
        return None
