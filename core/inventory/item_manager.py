"""
Item manager module.

This module provides a global access point to the inventory manager.
"""
import logging # Added for logging within this module
from typing import Optional
import uuid # Added for instance ID

from core.inventory.inventory_manager import InventoryManager
from core.utils.logging_config import get_logger # Ensure get_logger is available

# Get module logger specifically for this file's logs
logger = get_logger("ITEM_MANAGER_SINGLETON")

# Singleton instance
_inventory_manager_singleton_instance: Optional[InventoryManager] = None

def get_inventory_manager() -> InventoryManager:
    """
    Get the global inventory manager instance.
    
    Returns:
        The singleton inventory manager instance.
    """
    global _inventory_manager_singleton_instance
    
    if _inventory_manager_singleton_instance is None:
        logger.info("InventoryManager singleton is None, creating new instance.")
        _inventory_manager_singleton_instance = InventoryManager() # This calls InventoryManager.__init__
        # The __init__ of InventoryManager should set self.instance_id_for_debug
        new_id = getattr(_inventory_manager_singleton_instance, 'instance_id_for_debug', 'NOT_SET_IN_INIT')
        logger.info(f"NEW InventoryManager instance created with ID: {new_id}")
        # Store the ID on the class itself for future calls if needed (though instance_id_for_debug is preferred on the object)
        # setattr(InventoryManager, '_singleton_instance_id_debug', new_id) 
    else:
        instance_id = getattr(_inventory_manager_singleton_instance, 'instance_id_for_debug', 'ID_WAS_NOT_SET')
        # class_stored_id = getattr(InventoryManager, '_singleton_instance_id_debug', 'CLASS_ID_NOT_STORED')
        logger.debug(f"Returning EXISTING InventoryManager instance with ID: {instance_id}")
        
    return _inventory_manager_singleton_instance