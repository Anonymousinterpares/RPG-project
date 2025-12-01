"""
Complete inventory management system.

This module implements the InventoryManager class which combines all
inventory-related functionality into a single interface.
"""

from typing import Dict, Optional, Any, Tuple
import json
import os
import uuid

from core.utils.logging_config import get_logger
from core.inventory.item import Item
from core.inventory.item_enums import ItemType, EquipmentSlot
from core.inventory.item_serialization import item_to_dict, dict_to_item
from core.inventory.inventory_item_operations import InventoryItemOperations
from core.inventory.inventory_limits import InventoryLimits
from core.inventory.equipment_manager import EquipmentManager
from core.inventory.currency_manager import CurrencyManager
from core.base.config import get_config

# Get module logger
logger = get_logger("Inventory")


class InventoryManager(InventoryItemOperations, InventoryLimits, EquipmentManager):
    """
    Complete inventory manager.
    
    This class combines item operations, weight/slot limits, equipment management,
    and currency handling into a unified interface.
    """
    
    def __init__(self):
        """Initialize the inventory manager."""
        # Check if already initialized (part of some singleton patterns, though get_inventory_manager handles it)
        # For this class, super().__init__() is important to call base initializers.
        super().__init__() # Calls __init__ of InventoryItemOperations, InventoryLimits, EquipmentManager
        
        # Initialize currency manager
        self._currency = CurrencyManager()
        
        # Add an instance ID for logging/debugging
        # This should be set ONCE per actual object instantiation.
        if not hasattr(self, 'instance_id_for_debug'): # Set only if not already set (e.g. by a subclass's super call)
            self.instance_id_for_debug = str(uuid.uuid4())
        
        # Reference to stats manager for equipment modifier synchronization
        self._stats_manager = None
        
        logger.info(f"InventoryManager CLASS __init__ called. Instance ID: {self.instance_id_for_debug}")
    
    @property
    def inventory_id(self) -> Optional[str]:
        """Compatibility identifier for this inventory instance (maps to instance_id_for_debug)."""
        return getattr(self, 'instance_id_for_debug', None)
    
    @property
    def currency(self) -> CurrencyManager:
        """Get the currency manager."""
        return self._currency
    
    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load inventory and equipment state into this existing manager instance.
        This updates items, limits, equipment, and currency in-place.
        """
        try:
            # Clear existing data first
            self._items = {}
            
            # Load items
            for item_id, item_data in data.get("items", {}).items():
                item = dict_to_item(item_data)
                self._items[item_id] = item
            
            # Load inventory limits
            self._weight_limit_base = data.get("weight_limit_base", 100.0)
            self._weight_limit_modifiers = data.get("weight_limit_modifiers", {})
            self._slot_limit_base = data.get("slot_limit_base", 20)
            self._slot_limit_modifiers = data.get("slot_limit_modifiers", {})
            self.update_weight_limits()
            self.update_slot_limits()
            
            # Load equipment mapping (slot names back to enum -> item IDs)
            # Preserve string IDs in _equipment per EquipmentManager's internal representation
            for slot_name, item_id in data.get("equipment", {}).items():
                try:
                    slot = EquipmentSlot(slot_name)
                    self._equipment[slot] = item_id
                except ValueError:
                    logger.warning(f"Invalid equipment slot in saved data: {slot_name}")
            
            # Load currency
            currency_data = data.get("currency", {})
            if "total_copper" in currency_data:
                self._currency.set_currency(currency_data["total_copper"])
            else:
                gold = currency_data.get("gold", 0)
                silver = currency_data.get("silver", 0)
                copper = currency_data.get("copper", 0)
                self._currency.set_mixed_currency(gold, silver, copper)
            
            # Refresh equipment-derived modifiers
            try:
                self._update_equipment_modifiers()
            except Exception:
                pass
            
            logger.info("InventoryManager state loaded from dict (in-place).")
        except Exception as e:
            logger.error(f"Error loading inventory from dict into existing manager: {e}")
    
    def to_dict(self, include_unknown: bool = True) -> Dict[str, Any]:
        """
        Convert the inventory to a dictionary for serialization.
        
        Args:
            include_unknown: Whether to include unknown item properties.
            
        Returns:
            Dictionary representation of the inventory.
        """
        return {
            # Basic inventory data
            "items": {item_id: item_to_dict(item, include_unknown) 
                     for item_id, item in self._items.items()},
            
            # Inventory limits
            "weight_limit_base": self._weight_limit_base,
            "weight_limit_modifiers": self._weight_limit_modifiers,
            "slot_limit_base": self._slot_limit_base,
            "slot_limit_modifiers": self._slot_limit_modifiers,
            
            # Equipment data
            "equipment": {slot.value: item_id for slot, item_id in self._equipment.items() 
                         if item_id is not None},
            
            # Currency data
            "currency": self._currency.get_currency_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InventoryManager':
        """
        Create an inventory manager from a dictionary.
        
        Args:
            data: Dictionary containing inventory data.
            
        Returns:
            An InventoryManager instance.
        """
        inventory = cls()
        
        # Load items
        for item_id, item_data in data.get("items", {}).items():
            item = dict_to_item(item_data)
            inventory._items[item_id] = item
        
        # Load inventory limits
        inventory._weight_limit_base = data.get("weight_limit_base", 100.0)
        inventory._weight_limit_modifiers = data.get("weight_limit_modifiers", {})
        inventory._slot_limit_base = data.get("slot_limit_base", 20)
        inventory._slot_limit_modifiers = data.get("slot_limit_modifiers", {})
        inventory.update_weight_limits()
        inventory.update_slot_limits()
        
        # Load equipment
        for slot_name, item_id in data.get("equipment", {}).items():
            try:
                slot = EquipmentSlot(slot_name)
                inventory._equipment[slot] = item_id
            except ValueError:
                logger.warning(f"Invalid equipment slot in saved data: {slot_name}")
        
        # Load currency
        currency_data = data.get("currency", {})
        if "total_copper" in currency_data:
            inventory._currency.set_currency(currency_data["total_copper"])
        else:
            # Fallback to individual denominations if total not available
            gold = currency_data.get("gold", 0)
            silver = currency_data.get("silver", 0)
            copper = currency_data.get("copper", 0)
            inventory._currency.set_mixed_currency(gold, silver, copper)
        
        return inventory
    
    def set_stats_manager(self, stats_manager) -> None:
        """
        Set the stats manager reference for equipment modifier synchronization.
        
        Args:
            stats_manager: The stats manager instance
        """
        self._stats_manager = stats_manager
        logger.debug("Stats manager reference set in InventoryManager")
        
        # If we already have equipment modifiers, sync them now
        if hasattr(self, '_equipment_modifiers') and self._equipment_modifiers:
            self._sync_stats_modifiers()
    
    def _sync_stats_modifiers(self) -> None:
        """
        Override of EquipmentManager method to trigger stats synchronization.
        In addition to any upstream hooks, this wires equipment-based typed resistances (percent and dice)
        into the StatsManager.
        """
        if not self._stats_manager:
            logger.debug("No stats manager available for equipment modifier sync")
            return
        # Load allowed effect types from combat config (fallback to defaults)
        try:
            cfg = get_config()
            allowed_types = cfg.get("combat.damage.types", []) or []
            if not isinstance(allowed_types, list) or not allowed_types:
                allowed_types = ["slashing","piercing","bludgeoning","fire","cold","lightning","poison","acid","arcane"]
            allowed_types = [str(x).strip().lower() for x in allowed_types if isinstance(x, str)]
        except Exception:
            allowed_types = ["slashing","piercing","bludgeoning","fire","cold","lightning","poison","acid","arcane"]
        # First, clear previous equipment-based contributions for all slots
        try:
            from core.inventory.item_enums import EquipmentSlot
            for slot in EquipmentSlot:
                sid = f"equip_{slot.value}"
                try:
                    self._stats_manager.remove_resistance_contribution(sid)
                except Exception:
                    pass
                try:
                    # Also clear dice-based contributions
                    if hasattr(self._stats_manager, 'remove_resistance_dice_contribution'):
                        self._stats_manager.remove_resistance_dice_contribution(sid)
                except Exception:
                    pass
        except Exception as clr_err:
            logger.debug(f"Error clearing previous resistance contributions: {clr_err}")
        # Apply contributions from currently equipped items that define typed_resistances in custom_properties
        try:
            for slot, item_id in self._equipment.items():
                if not item_id:
                    continue
                it = self.get_item(item_id)
                if not it:
                    continue
                cp = getattr(it, 'custom_properties', {}) if hasattr(it, 'custom_properties') else {}
                if not isinstance(cp, dict):
                    continue
                # Percent-based typed resistances
                typed_map = None
                if 'typed_resistances' in cp and isinstance(cp['typed_resistances'], dict):
                    typed_map = cp['typed_resistances']
                if isinstance(typed_map, dict):
                    sanitized: Dict[str, float] = {}
                    for k, v in typed_map.items():
                        try:
                            dt = str(k or "").strip().lower()
                            if dt in allowed_types:
                                sanitized[dt] = float(v)
                        except Exception:
                            continue
                    if sanitized:
                        try:
                            self._stats_manager.set_resistance_contribution(f"equip_{slot.value}", sanitized)
                            logger.debug(f"Applied typed resistances from {it.name} in {slot.value}: {sanitized}")
                        except Exception as ap_err:
                            logger.debug(f"Failed applying typed resistances for {it.name}: {ap_err}")
                # Dice-based typed resistances
                typed_dice_map = None
                if 'typed_resistances_dice' in cp and isinstance(cp['typed_resistances_dice'], dict):
                    typed_dice_map = cp['typed_resistances_dice']
                if isinstance(typed_dice_map, dict):
                    sanitized_dice: Dict[str, list] = {}
                    for k, v in typed_dice_map.items():
                        try:
                            dt = str(k or "").strip().lower()
                            if dt not in allowed_types:
                                continue
                            if isinstance(v, list):
                                notations = [str(x).strip() for x in v if isinstance(x, (str, int, float)) and str(x).strip()]
                            else:
                                notations = [str(v).strip()] if str(v).strip() else []
                            if notations:
                                sanitized_dice[dt] = notations
                        except Exception:
                            continue
                    if sanitized_dice and hasattr(self._stats_manager, 'set_resistance_dice_contribution'):
                        try:
                            self._stats_manager.set_resistance_dice_contribution(f"equip_{slot.value}", sanitized_dice)
                            logger.debug(f"Applied typed resistance dice from {it.name} in {slot.value}: {sanitized_dice}")
                        except Exception as ap_err:
                            logger.debug(f"Failed applying typed resistance dice for {it.name}: {ap_err}")
        except Exception as apply_err:
            logger.debug(f"Error applying equipment typed resistances: {apply_err}")
        # Upstream hook if present (non-critical)
        if hasattr(self._stats_manager, 'sync_equipment_modifiers'):
            try:
                self._stats_manager.sync_equipment_modifiers()
                logger.debug("Triggered equipment modifier synchronization with stats manager")
            except Exception as e:
                logger.error(f"Error synchronizing equipment modifiers with stats manager: {e}")
    def save_to_file(self, filepath: str, include_unknown: bool = True) -> bool:
        """
        Save the inventory to a JSON file.
        
        Args:
            filepath: Path to the file.
            include_unknown: Whether to include unknown item properties.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Convert to dictionary
            data = self.to_dict(include_unknown)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved inventory to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving inventory to {filepath}: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filepath: str) -> Optional['InventoryManager']:
        """
        Load inventory from a JSON file.
        
        Args:
            filepath: Path to the file.
            
        Returns:
            An InventoryManager instance, or None if loading failed.
        """
        try:
            # Read from file
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Create inventory from data
            inventory = cls.from_dict(data)
            
            logger.info(f"Loaded inventory from {filepath}")
            return inventory
            
        except Exception as e:
            logger.error(f"Error loading inventory from {filepath}: {e}")
            return None
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the inventory.
        
        Returns:
            Dictionary with inventory summary information.
        """
        # Count items by type
        item_counts = {}
        for item_type in ItemType:
            count = len(self.get_items_by_type(item_type))
            if count > 0:
                item_counts[item_type.value] = count
        
        # Count items by rarity
        rarity_counts = {}
        for item in self._items.values():
            rarity = item.rarity.value
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        
        # Get equipment summary
        equipment_summary = {}
        for slot, item_id in self._equipment.items():
            if item_id:
                item = self.get_item(item_id)
                if item:
                    equipment_summary[slot.value] = {
                        "id": item.id,
                        "name": item.name,
                        "rarity": item.rarity.value
                    }
        
        return {
            "total_items": len(self._items),
            "used_slots": self.get_used_slots(),
            "free_slots": self.get_free_slots(),
            "slot_limit": self._slot_limit,
            "current_weight": self.get_current_weight(),
            "weight_limit": self._weight_limit,
            "items_by_type": item_counts,
            "items_by_rarity": rarity_counts,
            "currency": self._currency.get_currency_dict(),
            "equipped_items": equipment_summary
        }
    
    def get_item_discovery_stats(self) -> Dict[str, Any]:
        """
        Get statistics about item property discovery.
        
        Returns:
            Dictionary with discovery statistics.
        """
        # Count number of known properties for each item
        total_properties = 0
        total_known_properties = 0
        items_with_all_known = 0
        
        for item in self._items.values():
            # Get all possible properties
            all_properties = set(dir(item))
            # Filter out private properties and methods
            all_properties = {prop for prop in all_properties 
                              if not prop.startswith('_') and not callable(getattr(item, prop))}
            # Add stat properties
            for stat in item.stats:
                all_properties.add(f"stat_{stat.name}")
            # Add custom properties
            for custom_prop_key in item.custom_properties:
                all_properties.add(f"custom_{custom_prop_key}")
            # Add dice_roll_effects as a single knowable property concept
            if item.dice_roll_effects:
                 all_properties.add("dice_roll_effects")
            
            # Count known properties
            known = len(item.known_properties)
            total = len(all_properties)
            
            total_properties += total
            total_known_properties += known
            
            if known == total:
                items_with_all_known += 1
        
        # Calculate discovery percentage
        discovery_percentage = 0
        if total_properties > 0:
            discovery_percentage = (total_known_properties / total_properties) * 100
        
        return {
            "total_items": len(self._items),
            "total_properties": total_properties,
            "known_properties": total_known_properties,
            "discovery_percentage": discovery_percentage,
            "items_fully_discovered": items_with_all_known
        }
    
    def clear(self) -> None:
        """Clear all inventory data."""
        logger.info(f"InventoryManager ({getattr(self, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}) clear() called.")
        # Clear items
        self._items = {}
        
        # Reset limits
        self._weight_limit_base = 100.0
        self._weight_limit_modifiers = {}
        self._slot_limit_base = 20
        self._slot_limit_modifiers = {}
        self.update_weight_limits()
        self.update_slot_limits()
        
        # Clear equipment
        for slot in self._equipment:
            self._equipment[slot] = None
        
        # Clear currency
        self._currency.set_currency(0)
        
        logger.info(f"InventoryManager ({getattr(self, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')}) Cleared inventory. Item count: {len(self._items)}")
        
    def discover_item_property(self, item_id: str, property_name: str) -> bool:
        """
        Discover a property of an item.
        
        Args:
            item_id: The ID of the item.
            property_name: The name of the property to discover.
            
        Returns:
            True if the property was newly discovered, False otherwise.
        """
        item = self.get_item(item_id)
        if not item:
            logger.warning(f"Cannot discover property: Item {item_id} not found")
            return False
        
        return item.discover_property(property_name)
    
    def discover_item_stat(self, item_id: str, stat_name: str) -> bool:
        """
        Discover a stat of an item.
        
        Args:
            item_id: The ID of the item.
            stat_name: The name of the stat to discover.
            
        Returns:
            True if the stat was newly discovered, False otherwise.
        """
        item = self.get_item(item_id)
        if not item:
            logger.warning(f"Cannot discover stat: Item {item_id} not found")
            return False
        
        return item.discover_stat(stat_name)
    
    def discover_all_item_properties(self, item_id: str) -> int:
        """
        Discover all properties of an item.
        
        Args:
            item_id: The ID of the item.
            
        Returns:
            The number of newly discovered properties.
        """
        item = self.get_item(item_id)
        if not item:
            logger.warning(f"Cannot discover properties: Item {item_id} not found")
            return 0
        
        # Get all possible properties
        all_properties = set(attr for attr in dir(item) if not attr.startswith('_') and not callable(getattr(item, attr)))
        # Add stat properties
        for stat in item.stats:
            all_properties.add(f"stat_{stat.name}")
        # Add custom properties
        for custom_prop_key in item.custom_properties:
            all_properties.add(f"custom_{custom_prop_key}")
        # Add dice_roll_effects as a single knowable "property"
        if item.dice_roll_effects:
            all_properties.add("dice_roll_effects") # Assuming this becomes a knowable string
        
        # Discover all properties
        count = 0
        for prop in all_properties:
            if item.discover_property(prop):
                count += 1
        
        logger.info(f"Discovered {count} properties for item {item.name}")
        return count

    def use_item(self, item_id: str, quantity: int = 1) -> Tuple[bool, str]:
        """
        Use a consumable item. This method assumes the narrative part is handled elsewhere
        and this is the mechanical effect of consumption.

        Args:
            item_id: The ID of the item to use.
            quantity: The quantity to use.

        Returns:
            A tuple (success: bool, message: str).
        """
        item = self.get_item(item_id)
        if not item:
            return False, f"Item '{item_id}' not found."
        if not item.is_consumable:
            return False, f"{item.name} is not a consumable item."
        if item.quantity < quantity:
            return False, f"Not enough {item.name} to use. Have {item.quantity}, need {quantity}."

        # TODO: Apply item effects (healing, mana restore, buffs, etc.)
        # This would involve getting item.stats, interpreting them, and calling StatsManager.
        # For now, just log and remove.
        effects_applied_msg = f"Effects of {item.name} applied (placeholder)."
        logger.info(f"Simulating effects for consuming {quantity}x {item.name}. Item stats: {item.stats}")


        if self.remove_item(item_id, quantity):
            logger.info(f"Consumed {quantity}x {item.name} (ID: {item_id}).")
            return True, f"Used {quantity}x {item.name}. {effects_applied_msg}"
        else:
            # This should ideally not happen if checks above are correct
            logger.error(f"Failed to remove item {item_id} after use confirmation.")
            return False, f"Error consuming {item.name}."

    def get_item_details_for_dialog(self, item_id: str) -> Optional[Item]:
        """
        Retrieves the full Item object for display in an ItemInfoDialog.
        This ensures all data, including known_properties, is available.
        Args:
            item_id: The ID of the item.
        Returns:
            The Item object if found, else None.
        """
        item = self.get_item(item_id)
        if not item:
            logger.warning(f"ItemInfoDialog: Item with ID '{item_id}' not found in inventory.")
            return None
        return item