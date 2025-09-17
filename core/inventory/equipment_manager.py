#!/usr/bin/env python3
"""
Equipment management module.

This module extends the inventory system with methods to manage
equipped items and equipment slots.
"""

from typing import Dict, List, Optional, Any, Set, Union
import logging

from core.utils.logging_config import get_logger
from core.inventory.item import Item
from core.inventory.item_enums import EquipmentSlot
from core.inventory.inventory_base import InventoryBase

# Get module logger
logger = get_logger("Inventory")


class EquipmentManager(InventoryBase):
    """
    Equipment manager for handling equipped items.
    
    This class extends the base inventory with methods for equipping,
    unequipping, and managing equipped items.
    """
    
    def __init__(self):
        """Initialize the equipment manager."""
        super().__init__()
        
        # Equipment slots
        self._equipment: Dict[EquipmentSlot, Optional[str]] = {
            slot: None for slot in EquipmentSlot
        }
        
        # Set of equipment effects/modifiers
        self._equipment_modifiers: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Equipment manager initialized")
    
    @property
    def equipment(self) -> Dict[EquipmentSlot, Optional[Item]]:
        """
        Get the currently equipped items.
        
        Returns:
            Dictionary mapping slots to equipped items (or None if empty).
        """
        result = {}
        for slot, item_id_or_obj in self._equipment.items(): # Iterate over raw _equipment dict
            if isinstance(item_id_or_obj, str): # If it's an ID (older save format compatibility)
                item_obj = self._items.get(item_id_or_obj)
                if item_obj:
                    result[slot] = item_obj
                else:
                    result[slot] = None
                    if item_id_or_obj: # Log if an ID was there but item is missing
                         logger.warning(f"Equipment slot {slot.value} had ID '{item_id_or_obj}' but item not found in _items.")
            elif isinstance(item_id_or_obj, Item): # If it's already an Item object
                result[slot] = item_id_or_obj
            else: # It's None or unexpected type
                result[slot] = None
                
        return result
    
    def get_equipped_item(self, slot: Union[EquipmentSlot, str]) -> Optional[Item]:
        """
        Get the item equipped in a specific slot.
        
        Args:
            slot: The equipment slot to check.
            
        Returns:
            The equipped Item, or None if the slot is empty.
        """
        # Convert string to enum if needed
        if isinstance(slot, str):
            try:
                slot = EquipmentSlot(slot)
            except ValueError:
                logger.error(f"Invalid equipment slot: {slot}")
                return None
                
        item_id = self._equipment.get(slot)
        if item_id:
            return self._items.get(item_id)
            
        return None
    
    def is_slot_empty(self, slot: Union[EquipmentSlot, str]) -> bool:
        """
        Check if an equipment slot is empty.
        
        Args:
            slot: The equipment slot to check.
            
        Returns:
            True if the slot is empty, False otherwise.
        """
        # Convert string to enum if needed
        if isinstance(slot, str):
            try:
                slot = EquipmentSlot(slot)
            except ValueError:
                logger.error(f"Invalid equipment slot: {slot}")
                return True
                
        return self._equipment.get(slot) is None
    
    def can_equip(self, item_id: str) -> bool:
        """
        Check if an item can be equipped.
        
        Args:
            item_id: The ID of the item to check.
            
        Returns:
            True if the item can be equipped, False otherwise.
        """
        item = self.get_item(item_id)
        if not item:
            logger.warning(f"Cannot equip: Item {item_id} not found")
            return False
            
        if not item.is_equippable:
            logger.warning(f"Cannot equip: Item {item_id} is not equippable")
            return False
            
        if not item.equip_slots:
            logger.warning(f"Cannot equip: Item {item_id} has no valid equipment slots")
            return False
            
        # Check if any of the item's slots are available
        for slot in item.equip_slots:
            # Special handling for two-handed weapons
            if slot == EquipmentSlot.TWO_HAND:
                if (self.is_slot_empty(EquipmentSlot.MAIN_HAND) and 
                    self.is_slot_empty(EquipmentSlot.OFF_HAND)):
                    return True
            # Special handling for main hand if two-handed weapon is equipped
            elif slot == EquipmentSlot.MAIN_HAND:
                if self.is_slot_empty(EquipmentSlot.MAIN_HAND):
                    # Check if a two-handed weapon is equipped
                    if not self.is_slot_empty(EquipmentSlot.TWO_HAND):
                        continue  # Can't equip main hand if two-handed is equipped
                    return True
            # Special handling for off hand if two-handed weapon is equipped
            elif slot == EquipmentSlot.OFF_HAND:
                if self.is_slot_empty(EquipmentSlot.OFF_HAND):
                    # Check if a two-handed weapon is equipped
                    if not self.is_slot_empty(EquipmentSlot.TWO_HAND):
                        continue  # Can't equip off hand if two-handed is equipped
                    return True
            # Normal slot check
            elif self.is_slot_empty(slot):
                return True
                
        logger.warning(f"Cannot equip: No available slots for item {item_id}")
        return False
    
    def equip_item(self, item_id: str, preferred_slot: Optional[Union[EquipmentSlot, str]] = None) -> bool:
        """
        Equip an item.
        
        Args:
            item_id: The ID of the item to equip.
            preferred_slot: The preferred slot to equip the item in (if applicable).
            
        Returns:
            True if the item was equipped, False otherwise.
        """
        item = self.get_item(item_id) # This gets the Item object
        if not item:
            logger.warning(f"Cannot equip: Item {item_id} not found")
            return False
            
        if not item.is_equippable:
            logger.warning(f"Cannot equip: Item {item.name} is not equippable")
            return False
            
        if not item.equip_slots:
            logger.warning(f"Cannot equip: Item {item.name} has no valid equipment slots")
            return False
            
        if preferred_slot and isinstance(preferred_slot, str):
            try:
                preferred_slot = EquipmentSlot(preferred_slot.lower().replace(" ","_"))
            except ValueError:
                logger.warning(f"Invalid preferred slot string: {preferred_slot}")
                preferred_slot = None
                
        target_slot = None
        
        if preferred_slot and preferred_slot in item.equip_slots:
            if preferred_slot == EquipmentSlot.TWO_HAND:
                if not self.is_slot_empty(EquipmentSlot.MAIN_HAND): self.unequip_item(EquipmentSlot.MAIN_HAND)
                if not self.is_slot_empty(EquipmentSlot.OFF_HAND): self.unequip_item(EquipmentSlot.OFF_HAND)
                target_slot = preferred_slot
            elif preferred_slot == EquipmentSlot.MAIN_HAND or preferred_slot == EquipmentSlot.OFF_HAND:
                if not self.is_slot_empty(EquipmentSlot.TWO_HAND): self.unequip_item(EquipmentSlot.TWO_HAND)
                if self.is_slot_empty(preferred_slot): target_slot = preferred_slot
                else: self.unequip_item(preferred_slot); target_slot = preferred_slot
            elif self.is_slot_empty(preferred_slot):
                target_slot = preferred_slot
            else:
                self.unequip_item(preferred_slot)
                target_slot = preferred_slot
                
        if not target_slot:
            for slot_option in item.equip_slots:
                if slot_option == EquipmentSlot.TWO_HAND:
                    if self.is_slot_empty(EquipmentSlot.MAIN_HAND) and self.is_slot_empty(EquipmentSlot.OFF_HAND):
                        target_slot = slot_option; break
                    else: # Try to make space
                        if not self.is_slot_empty(EquipmentSlot.MAIN_HAND): self.unequip_item(EquipmentSlot.MAIN_HAND)
                        if not self.is_slot_empty(EquipmentSlot.OFF_HAND): self.unequip_item(EquipmentSlot.OFF_HAND)
                        if self.is_slot_empty(EquipmentSlot.MAIN_HAND) and self.is_slot_empty(EquipmentSlot.OFF_HAND):
                             target_slot = slot_option; break
                elif slot_option == EquipmentSlot.MAIN_HAND or slot_option == EquipmentSlot.OFF_HAND:
                    if not self.is_slot_empty(EquipmentSlot.TWO_HAND): continue 
                    if self.is_slot_empty(slot_option): target_slot = slot_option; break
                elif self.is_slot_empty(slot_option):
                    target_slot = slot_option; break
            
            # If still no empty slot found after first pass, try unequipping existing item in first valid slot
            if not target_slot and item.equip_slots:
                first_valid_slot_for_item = item.equip_slots[0]
                if first_valid_slot_for_item == EquipmentSlot.TWO_HAND:
                    if not self.is_slot_empty(EquipmentSlot.MAIN_HAND): self.unequip_item(EquipmentSlot.MAIN_HAND)
                    if not self.is_slot_empty(EquipmentSlot.OFF_HAND): self.unequip_item(EquipmentSlot.OFF_HAND)
                elif (first_valid_slot_for_item == EquipmentSlot.MAIN_HAND or first_valid_slot_for_item == EquipmentSlot.OFF_HAND) and not self.is_slot_empty(EquipmentSlot.TWO_HAND):
                    self.unequip_item(EquipmentSlot.TWO_HAND)
                
                # Unequip whatever is in the first_valid_slot_for_item if it's occupied
                if not self.is_slot_empty(first_valid_slot_for_item):
                    self.unequip_item(first_valid_slot_for_item)
                target_slot = first_valid_slot_for_item


        if target_slot:
            self._equipment[target_slot] = item.id # Store item ID
            self._update_equipment_modifiers()
            logger.info(f"Equipped {item.name} (ID: {item.id}) in {target_slot.value}")
            return True
        
        logger.warning(f"Failed to equip {item.name}: No suitable slot found or made available.")
        return False
    
    def unequip_item(self, slot: Union[EquipmentSlot, str]) -> Optional[str]:
        """
        Unequip an item from a specific slot.
        
        Args:
            slot: The slot to unequip from.
            
        Returns:
            The ID of the unequipped item, or None if the slot was empty or error.
        """
        if isinstance(slot, str):
            try:
                slot = EquipmentSlot(slot.lower().replace(" ", "_"))
            except ValueError:
                logger.error(f"Invalid equipment slot string: {slot}")
                return None
        
        item_id_in_slot = self._equipment.get(slot) # This should be an item ID (string)
        if not item_id_in_slot or not isinstance(item_id_in_slot, str): # Ensure it's a string ID
            logger.debug(f"Cannot unequip: Slot {slot.value} is already empty or contains invalid data.")
            if slot == EquipmentSlot.TWO_HAND: # Also clear main/off if un-equipping two-hand
                self._equipment[EquipmentSlot.MAIN_HAND] = None
                self._equipment[EquipmentSlot.OFF_HAND] = None
            return None
        
        item_obj = self.get_item(item_id_in_slot) # Fetch Item object using the ID
        
        self._equipment[slot] = None
        # If a two-handed weapon was unequipped, ensure main_hand and off_hand are also cleared
        if slot == EquipmentSlot.TWO_HAND:
            self._equipment[EquipmentSlot.MAIN_HAND] = None
            self._equipment[EquipmentSlot.OFF_HAND] = None
        # If main_hand or off_hand was unequipped, and a two_handed weapon was there, clear two_hand slot
        elif (slot == EquipmentSlot.MAIN_HAND or slot == EquipmentSlot.OFF_HAND) and self._equipment.get(EquipmentSlot.TWO_HAND) == item_id_in_slot :
             self._equipment[EquipmentSlot.TWO_HAND] = None


        self._update_equipment_modifiers()
        
        item_name_for_log = item_obj.name if item_obj else f"Item ID {item_id_in_slot}"
        logger.info(f"Unequipped {item_name_for_log} from {slot.value}")
        
        return item_id_in_slot
    
    def unequip_all(self) -> List[str]:
        """
        Unequip all items.
        
        Returns:
            List of unequipped item IDs.
        """
        unequipped_items = []
        
        for slot in self._equipment:
            item_id = self._equipment[slot]
            if item_id:
                self._equipment[slot] = None
                unequipped_items.append(item_id)
        
        self._update_equipment_modifiers()
        logger.info(f"Unequipped all items ({len(unequipped_items)} items)")
        
        return unequipped_items
    
    def _update_equipment_modifiers(self) -> None:
        """Update the equipment modifiers based on currently equipped items."""
        # Clear existing modifiers
        self._equipment_modifiers = {}
        
        # Add modifiers from each equipped item
        for slot, item_id in self._equipment.items():
            if not item_id:
                continue
                
            item = self.get_item(item_id)
            if not item:
                continue
                
            # Add stat modifiers
            for stat in item.stats:
                source_id = f"{item.id}_{stat.name}"
                self._equipment_modifiers[source_id] = {
                    "stat": stat.name,
                    "value": stat.value,
                    "is_percentage": stat.is_percentage,
                    "source_item": item.id,
                    "source_slot": slot.value
                }
        
        logger.debug(f"Updated equipment modifiers: {len(self._equipment_modifiers)} active modifiers")
    
    def get_stat_modifiers(self, stat_name: str) -> List[Dict[str, Any]]:
        """
        Get all modifiers for a specific stat from equipped items.
        
        Args:
            stat_name: The name of the stat to get modifiers for.
            
        Returns:
            List of modifier dictionaries.
        """
        modifiers = []
        
        for modifier_id, modifier in self._equipment_modifiers.items():
            if modifier["stat"] == stat_name:
                modifiers.append(modifier)
        
        return modifiers
    
    def get_equipped_slots_for_item(self, item_id: str) -> List[EquipmentSlot]:
        """
        Get all slots where a specific item is equipped.
        
        Args:
            item_id: The ID of the item to check.
            
        Returns:
            List of equipment slots where the item is equipped.
        """
        slots = []
        
        for slot, equipped_id in self._equipment.items():
            if equipped_id == item_id:
                slots.append(slot)
        
        return slots
    
    def is_item_equipped(self, item_id: str) -> bool:
        """
        Check if an item is equipped in any slot.
        
        Args:
            item_id: The ID of the item to check.
            
        Returns:
            True if the item is equipped, False otherwise.
        """
        return item_id in self._equipment.values()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the equipment manager to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the equipment manager.
        """
        # Serialize the equipment slots and items
        equipment_dict = {}
        for slot, item_id in self._equipment.items():
            equipment_dict[slot.value] = item_id
        
        # Get all equipped items data
        items_dict = {}
        for item_id, item in self._items.items():
            if item_id in self._equipment.values():  # Only serialize equipped items
                from core.inventory.item_serialization import item_to_dict
                items_dict[item_id] = item_to_dict(item)
        
        return {
            "equipment": equipment_dict,
            "items": items_dict,
            "equipment_modifiers": self._equipment_modifiers
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EquipmentManager':
        """
        Create an equipment manager from a dictionary.
        
        Args:
            data: Dictionary representation of the equipment manager.
            
        Returns:
            New EquipmentManager instance.
        """
        manager = cls()
        
        # Restore items first
        items_data = data.get("items", {})
        for item_id, item_data in items_data.items():
            from core.inventory.item_serialization import dict_to_item
            item = dict_to_item(item_data)
            manager._items[item_id] = item
        
        # Restore equipment slots
        equipment_data = data.get("equipment", {})
        for slot_name, item_id in equipment_data.items():
            try:
                slot = EquipmentSlot(slot_name)
                manager._equipment[slot] = item_id
            except ValueError:
                logger.warning(f"Unknown equipment slot '{slot_name}' during deserialization")
        
        # Restore equipment modifiers
        manager._equipment_modifiers = data.get("equipment_modifiers", {})
        
        return manager
