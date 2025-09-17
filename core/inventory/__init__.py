"""
Inventory system package.

This package provides classes and utilities for managing
items, equipment, and currency in the game.
"""

# Import the enums first since they have no dependencies
from core.inventory.item_enums import ItemType, ItemRarity, EquipmentSlot

# Import the base classes next
from core.inventory.item_stat import ItemStat
from core.inventory.item import Item
from core.inventory.item_effect import DiceRollEffect

# Import serialization utilities
from core.inventory.item_serialization import item_to_dict, dict_to_item

# Import inventory base components
from core.inventory.inventory_base import InventoryBase
from core.inventory.inventory_item_operations import InventoryItemOperations
from core.inventory.inventory_limits import InventoryLimits
from core.inventory.equipment_manager import EquipmentManager
from core.inventory.currency_manager import CurrencyManager

# Import item modifiers and generators
from core.inventory.item_stat_modifier import ItemStatModifier
from core.inventory.item_variation_generator import ItemVariationGenerator

# Import higher-level managers and their getters
from core.inventory.item_template_loader import ItemTemplateLoader, get_item_template_loader
from core.inventory.item_factory import ItemFactory, get_item_factory
from core.inventory.inventory_manager import InventoryManager # Import the class for type hinting

# Re-export get_inventory_manager from item_manager.py to ensure a single source for the singleton
from core.inventory.item_manager import get_inventory_manager

# Import narrative item management
from core.inventory.narrative_item_manager import NarrativeItemManager 

# Global instance for NarrativeItemManager - make it a singleton too for consistency
_narrative_item_manager_singleton = None

def get_narrative_item_manager() -> NarrativeItemManager:
    """Get or create a narrative item manager instance."""
    global _narrative_item_manager_singleton
    if _narrative_item_manager_singleton is None:
        _narrative_item_manager_singleton = NarrativeItemManager()
    return _narrative_item_manager_singleton

# Import inventory commands - must be after all getters to avoid circular imports
from core.inventory.inventory_commands import register_inventory_commands