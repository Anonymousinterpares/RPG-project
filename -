#!/usr/bin/env python3
"""
Core inventory module.

This module provides the base InventoryManager class with
core properties and query methods.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union
import logging

from core.utils.logging_config import get_logger
from core.inventory.item import Item
from core.inventory.item_enums import ItemType

# Get module logger
logger = get_logger("Inventory")


class InventoryBase:
    """
    Base manager for a player's inventory.
    
    This class provides core inventory properties and query methods.
    """
    
    def __init__(self):
        """Initialize the inventory manager."""
        # Dictionary of items by ID
        self._items: Dict[str, Item] = {}
        
        # Item weight limits
        self._weight_limit: float = 100.0
        self._weight_limit_base: float = 100.0
        self._weight_limit_modifiers: Dict[str, float] = {}
        
        # Storage slot limits
        self._slot_limit: int = 20
        self._slot_limit_base: int = 20
        self._slot_limit_modifiers: Dict[str, int] = {}
        
        logger.info("Inventory manager initialized")
    
    @property
    def items(self) -> List[Item]:
        """Get all items in the inventory."""
        return list(self._items.values())
    
    @property
    def weight_limit(self) -> float:
        """Get the current weight limit."""
        return self._weight_limit
    
    @property
    def slot_limit(self) -> int:
        """Get the current slot limit."""
        return self._slot_limit
    
    def get_current_weight(self) -> float:
        """Get the current total weight of all items."""
        return sum(item.weight * item.quantity for item in self._items.values())
    
    def get_used_slots(self) -> int:
        """Get the number of slots currently used."""
        # Count unstackable items as 1 slot each, stackable items as 1 slot per stack
        return sum(1 for item in self._items.values() if not item.is_stackable) + \
               sum(1 for item in self._items.values() if item.is_stackable)
    
    def get_free_slots(self) -> int:
        """Get the number of free slots."""
        return max(0, self._slot_limit - self.get_used_slots())
    
    def get_item(self, item_id: str) -> Optional[Item]:
        """Get an item by ID."""
        return self._items.get(item_id)
    
    def find_items(self, **criteria) -> List[Item]:
        """
        Find items based on criteria.
        
        Args:
            **criteria: Criteria to match, e.g., name="Sword", item_type=ItemType.WEAPON
            
        Returns:
            List of items matching the criteria.
        """
        results = []
        
        for item in self._items.values():
            matches = True
            
            for key, value in criteria.items():
                # Handle special case for item_type which might be an enum or string
                if key == "item_type" and isinstance(value, str):
                    try:
                        value = ItemType(value)
                    except ValueError:
                        # If it's not a valid enum value, keep as is
                        pass
                
                item_value = getattr(item, key, None)
                
                # Check if the item has the attribute and it matches the value
                if item_value is None or item_value != value:
                    matches = False
                    break
            
            if matches:
                results.append(item)
        
        return results
    
    def is_empty(self) -> bool:
        """Check if the inventory is empty."""
        return len(self._items) == 0
    
    def get_items_by_type(self, item_type: Union[ItemType, str]) -> List[Item]:
        """Get all items of a specific type."""
        if isinstance(item_type, str):
            try:
                item_type = ItemType(item_type)
            except ValueError:
                # If it's not a valid enum value, return empty list
                return []
        
        return [item for item in self._items.values() if item.item_type == item_type]
    
    def get_total_value(self) -> int:
        """Get the total value of all items in the inventory (in copper)."""
        return sum(item.value * item.quantity for item in self._items.values())
