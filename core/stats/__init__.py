"""
Stats module for the RPG game.

This module contains classes and functions for managing character statistics, 
modifiers, and derived attributes.
"""

from core.stats.stats_base import (
    StatType, DerivedStatType, Stat, StatCategory
)
from core.stats.derived_stats import calculate_derived_stat
from core.stats.stats_manager import StatsManager
from core.stats.modifier import ModifierType, ModifierSource, StatModifier
from core.stats.modifier_manager import ModifierManager
