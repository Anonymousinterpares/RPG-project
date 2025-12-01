#!/usr/bin/env python3
"""
Item stat modifier module.

This module provides functionality for modifying individual item stats.
"""

from typing import Optional
import random
import copy

from core.utils.logging_config import get_logger
from core.inventory.item import Item
from core.inventory.item_stat import ItemStat

# Get module logger
logger = get_logger("Inventory")


class ItemStatModifier:
    """
    Handles modifications to individual item stats.
    
    This class provides methods to adjust item stats with various
    scaling factors and constraints.
    """
    
    @staticmethod
    def modify_numeric_stat(
        stat: ItemStat,
        factor: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        round_to: Optional[int] = None
    ) -> ItemStat:
        """
        Modify a numeric stat by a factor with optional constraints.
        
        Args:
            stat: The ItemStat to modify.
            factor: The scaling factor to apply.
            min_value: Optional minimum value for the result.
            max_value: Optional maximum value for the result.
            round_to: Optional decimal places to round to.
            
        Returns:
            A new ItemStat with the modified value.
        """
        # Ensure the stat is numeric
        if not isinstance(stat.value, (int, float)):
            return copy.deepcopy(stat)
        
        # Calculate new value
        new_value = stat.value * factor
        
        # Apply constraints
        if min_value is not None:
            new_value = max(min_value, new_value)
        if max_value is not None:
            new_value = min(max_value, new_value)
        
        # Round if needed
        if round_to is not None:
            if round_to == 0:
                new_value = int(round(new_value))
            else:
                new_value = round(new_value, round_to)
        
        # Create new stat with modified value
        return ItemStat(
            name=stat.name,
            value=new_value,
            display_name=stat.display_name,
            is_percentage=stat.is_percentage
        )
    
    @staticmethod
    def modify_stat_random(
        stat: ItemStat,
        min_factor: float,
        max_factor: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        round_to: Optional[int] = None
    ) -> ItemStat:
        """
        Modify a numeric stat by a random factor within a range.
        
        Args:
            stat: The ItemStat to modify.
            min_factor: The minimum scaling factor to apply.
            max_factor: The maximum scaling factor to apply.
            min_value: Optional minimum value for the result.
            max_value: Optional maximum value for the result.
            round_to: Optional decimal places to round to.
            
        Returns:
            A new ItemStat with the modified value.
        """
        # Calculate random factor
        factor = random.uniform(min_factor, max_factor)
        
        # Apply the factor
        return ItemStatModifier.modify_numeric_stat(
            stat, factor, min_value, max_value, round_to
        )
    
    @staticmethod
    def apply_quality_factor(
        stat: ItemStat,
        quality: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        round_to: Optional[int] = None
    ) -> ItemStat:
        """
        Modify a stat based on an item quality factor (0.0 to 2.0).
        
        Args:
            stat: The ItemStat to modify.
            quality: The quality factor (typically 0.0 to 2.0, where 1.0 is normal).
            min_value: Optional minimum value for the result.
            max_value: Optional maximum value for the result.
            round_to: Optional decimal places to round to.
            
        Returns:
            A new ItemStat with the modified value.
        """
        # Normalize quality (ensure between 0.0 and 2.0)
        normalized_quality = max(0.0, min(2.0, quality))
        
        # Apply quality factor
        return ItemStatModifier.modify_numeric_stat(
            stat, normalized_quality, min_value, max_value, round_to
        )
    
    @staticmethod
    def apply_level_scaling(
        stat: ItemStat,
        item_level: int,
        base_level: int,
        scaling_factor: float,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        round_to: Optional[int] = None
    ) -> ItemStat:
        """
        Scale a stat based on item level compared to a base level.
        
        Args:
            stat: The ItemStat to modify.
            item_level: The level of the item.
            base_level: The base level for comparison.
            scaling_factor: The scaling factor per level difference.
            min_value: Optional minimum value for the result.
            max_value: Optional maximum value for the result.
            round_to: Optional decimal places to round to.
            
        Returns:
            A new ItemStat with the modified value.
        """
        # Calculate level factor
        level_diff = item_level - base_level
        level_factor = 1.0 + (level_diff * scaling_factor)
        
        # Apply level factor
        return ItemStatModifier.modify_numeric_stat(
            stat, level_factor, min_value, max_value, round_to
        )
