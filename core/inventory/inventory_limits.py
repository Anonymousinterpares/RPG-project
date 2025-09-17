#!/usr/bin/env python3
"""
Inventory limits module.

This module extends the inventory system with methods to manage
weight and slot limits.
"""

from typing import Dict
import logging

from core.utils.logging_config import get_logger
from core.inventory.inventory_base import InventoryBase

# Get module logger
logger = get_logger("Inventory")


class InventoryLimits(InventoryBase):
    """
    Inventory manager with limit management operations.
    
    This class extends the base inventory with methods for managing
    weight and slot limits.
    """
    
    def update_weight_limits(self) -> None:
        """Update weight limits based on modifiers."""
        # Calculate total weight limit from base + modifiers
        total_modifier = sum(self._weight_limit_modifiers.values())
        self._weight_limit = self._weight_limit_base + total_modifier
        logger.debug(f"Updated weight limit to {self._weight_limit}")
    
    def update_slot_limits(self) -> None:
        """Update slot limits based on modifiers."""
        # Calculate total slot limit from base + modifiers
        total_modifier = sum(self._slot_limit_modifiers.values())
        self._slot_limit = self._slot_limit_base + total_modifier
        logger.debug(f"Updated slot limit to {self._slot_limit}")
    
    def set_weight_limit_base(self, base_limit: float) -> None:
        """
        Set the base weight limit.
        
        Args:
            base_limit: New base weight limit value
        """
        self._weight_limit_base = base_limit
        self.update_weight_limits()
        logger.info(f"Set base weight limit to {base_limit}")
    
    def set_slot_limit_base(self, base_limit: int) -> None:
        """
        Set the base slot limit.
        
        Args:
            base_limit: New base slot limit value
        """
        self._slot_limit_base = base_limit
        self.update_slot_limits()
        logger.info(f"Set base slot limit to {base_limit}")
    
    def add_weight_modifier(self, source: str, value: float) -> None:
        """
        Add a weight limit modifier.
        
        Args:
            source: Identifier for the source of this modifier
            value: The value to add to the weight limit
        """
        self._weight_limit_modifiers[source] = value
        self.update_weight_limits()
        logger.info(f"Added weight modifier '{source}': {value}")
    
    def remove_weight_modifier(self, source: str) -> None:
        """
        Remove a weight limit modifier.
        
        Args:
            source: Identifier for the modifier to remove
        """
        if source in self._weight_limit_modifiers:
            value = self._weight_limit_modifiers.pop(source)
            self.update_weight_limits()
            logger.info(f"Removed weight modifier '{source}': {value}")
    
    def add_slot_modifier(self, source: str, value: int) -> None:
        """
        Add a slot limit modifier.
        
        Args:
            source: Identifier for the source of this modifier
            value: The value to add to the slot limit
        """
        self._slot_limit_modifiers[source] = value
        self.update_slot_limits()
        logger.info(f"Added slot modifier '{source}': {value}")
    
    def remove_slot_modifier(self, source: str) -> None:
        """
        Remove a slot limit modifier.
        
        Args:
            source: Identifier for the modifier to remove
        """
        if source in self._slot_limit_modifiers:
            value = self._slot_limit_modifiers.pop(source)
            self.update_slot_limits()
            logger.info(f"Removed slot modifier '{source}': {value}")
    
    def get_weight_limit_info(self) -> Dict[str, float]:
        """
        Get detailed information about weight limits.
        
        Returns:
            Dictionary with base, modifiers, and total weight limit.
        """
        return {
            "base": self._weight_limit_base,
            "modifiers": dict(self._weight_limit_modifiers),
            "total": self._weight_limit
        }
    
    def get_slot_limit_info(self) -> Dict[str, int]:
        """
        Get detailed information about slot limits.
        
        Returns:
            Dictionary with base, modifiers, and total slot limit.
        """
        return {
            "base": self._slot_limit_base,
            "modifiers": dict(self._slot_limit_modifiers),
            "total": self._slot_limit
        }
