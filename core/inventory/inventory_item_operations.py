#!/usr/bin/env python3
"""
Inventory item operations module.

This module extends the base inventory with methods
for adding, removing, and managing items.
"""

from typing import Dict, List, Optional, Any, Union
import logging
import copy

from core.utils.logging_config import get_logger
from core.inventory.item import Item
from core.inventory.inventory_base import InventoryBase
# Lazy getter to avoid circular import during module import time
# Do not import get_state_manager at module scope; resolve it when called
def get_state_manager():
    from core.base.state.state_manager import get_state_manager as _get
    return _get()
try:
    from core.game_flow.event_log import record_item_delta
except Exception:
    record_item_delta = lambda *args, **kwargs: None

# Get module logger
logger = get_logger("Inventory")


class InventoryItemOperations(InventoryBase):
    """
    Inventory manager with item manipulation operations.
    
    This class extends the base inventory with methods to add, remove,
    and manage items.
    """
    
    def can_add_item(self, item: Item, quantity: int = 1) -> bool:
        """
        Check if an item can be added to the inventory.
        
        Args:
            item: The item to add.
            quantity: The quantity to add.
            
        Returns:
            True if the item can be added, False otherwise.
        """
        # Check weight limit
        new_weight = self.get_current_weight() + (item.weight * quantity)
        if new_weight > self._weight_limit:
            return False
        
        # Check slot limit for non-stackable items or new stacks
        if not item.is_stackable:
            if self.get_used_slots() + quantity > self._slot_limit:
                return False
        else:
            # For stackable items, check if can be combined with existing items
            existing_item = self.find_stackable_item(item)
            if not existing_item:
                # New stack
                if self.get_used_slots() + 1 > self._slot_limit:
                    return False
            elif existing_item.quantity + quantity > existing_item.stack_limit:
                # Would exceed stack limit, need a new stack
                remaining = (existing_item.quantity + quantity) - existing_item.stack_limit
                if self.get_used_slots() + 1 > self._slot_limit:
                    return False
        
        return True
    
    def find_stackable_item(self, item: Item) -> Optional[Item]:
        """
        Find an existing stackable item that can be combined with the given item.
        
        Args:
            item: The item to find a stack for.
            
        Returns:
            An existing Item that can be stacked with the given item, or None.
        """
        if not item.is_stackable:
            return None
        
        # Look for existing items that can accept more quantity
        for existing_item in self._items.values():
            if not existing_item.is_stackable:
                continue
            if existing_item.quantity >= existing_item.stack_limit:
                continue

            # Primary rule: identical template_id stacks merge
            if existing_item.template_id and item.template_id and existing_item.template_id == item.template_id:
                return existing_item

            # Fallback rule: allow merging by identical properties for items created without template_id
            # This avoids duplicate-name suffixing like "(2)" for functionally identical items
            if self._can_stack_by_properties(existing_item, item):
                return existing_item
        
        return None

    def _can_stack_by_properties(self, a: Item, b: Item) -> bool:
        """
        Determine if two items can stack based on core properties when template_id doesn't match.
        Conservative: requires identical name (ignoring trailing numeric suffix), item_type, rarity,
        consumable flag, tags, weight, value, and no differing stats or custom_properties.
        """
        try:
            # Normalize trailing numeric suffix " (n)" often used for disambiguation
            import re
            def norm(name: str) -> str:
                return re.sub(r" \(\d+\)$", "", (name or "").strip()).lower()

            if norm(a.name) != norm(b.name):
                return False
            if a.item_type != b.item_type:
                return False
            if a.rarity != b.rarity:
                return False
            if bool(a.is_consumable) != bool(b.is_consumable):
                return False
            # Tags as sets must match
            if set(a.tags or []) != set(b.tags or []):
                return False
            # Ensure identical base economics/weight
            if (a.value != b.value):
                return False
            if abs((a.weight or 0.0) - (b.weight or 0.0)) > 1e-6:
                return False
            # Do not merge if either has stats and they differ
            if (a.stats and not b.stats) or (b.stats and not a.stats):
                return False
            if a.stats and b.stats:
                amap = {s.name: (s.value, getattr(s, 'display_name', None), getattr(s, 'is_percentage', False)) for s in a.stats}
                bmap = {s.name: (s.value, getattr(s, 'display_name', None), getattr(s, 'is_percentage', False)) for s in b.stats}
                if amap != bmap:
                    return False
            # Do not merge if custom_properties differ
            if (getattr(a, 'custom_properties', {}) or getattr(b, 'custom_properties', {})):
                if getattr(a, 'custom_properties', {}) != getattr(b, 'custom_properties', {}):
                    return False
            return True
        except Exception:
            return False
    
    def add_item(self, item: Item, quantity: int = 1) -> List[str]:
        """
        Add an item to the inventory. Handles name collision for non-template items.
        
        Args:
            item: The item to add.
            quantity: The quantity to add.
            
        Returns:
            List of item IDs that were added.
        """
        # Instance ID logging at the start of the method
        manager_instance_id = getattr(self, 'instance_id_for_debug', 'UNKNOWN_INSTANCE')
        logger.debug(f"InventoryManager ({manager_instance_id}) add_item called for '{item.name}', qty: {quantity}. Current item count: {len(self._items)}")

        if quantity <= 0:
            return []
        
        # Check if we can add the item
        if not self.can_add_item(item, quantity):
            logger.warning(f"InventoryManager ({manager_instance_id}) Cannot add item '{item.name}' to inventory. Weight or slot limit exceeded.")
            return []
        
        added_item_ids = []
        
        original_item_name_for_collision_check = item.name
        is_new_stackable_instance = item.is_stackable and not self.find_stackable_item(item)
        
        if (not item.is_stackable or is_new_stackable_instance) and not item.is_template:
            current_name = item.name
            name_count = 1
            all_inventory_names = [i.name for i in self._items.values()]
            
            if current_name in all_inventory_names:
                name_count = 2 
                while f"{original_item_name_for_collision_check} ({name_count})" in all_inventory_names:
                    name_count += 1
                item.name = f"{original_item_name_for_collision_check} ({name_count})"
                logger.info(f"InventoryManager ({manager_instance_id}) Item name collision for '{original_item_name_for_collision_check}'. Renamed to '{item.name}'.")

        if item.is_stackable:
            existing_item = self.find_stackable_item(item)
            
            if existing_item:
                # Upgrade stack limit if needed, preferring canonical template value, then the larger of the two
                try:
                    canonical_limit = None
                    if getattr(existing_item, 'template_id', None):
                        try:
                            from core.inventory.item_template_loader import get_item_template_loader
                            tl = get_item_template_loader()
                            tmpl = tl.get_template(existing_item.template_id)
                            if tmpl and getattr(tmpl, 'is_stackable', False):
                                canonical_limit = getattr(tmpl, 'stack_limit', None)
                        except Exception:
                            pass
                    new_limit = max(int(getattr(existing_item, 'stack_limit', 1) or 1),
                                    int(getattr(item, 'stack_limit', 1) or 1),
                                    int(canonical_limit) if canonical_limit is not None else 1)
                    if new_limit != existing_item.stack_limit and getattr(existing_item, 'is_stackable', False):
                        existing_item.stack_limit = new_limit
                except Exception:
                    pass

                space_in_stack = max(0, int(existing_item.stack_limit) - int(existing_item.quantity))
                amount_to_add = min(int(quantity), space_in_stack)
                existing_item.quantity += amount_to_add
                added_item_ids.append(existing_item.id)
                remaining_quantity_to_add = int(quantity) - amount_to_add
                if remaining_quantity_to_add > 0:
                    current_name_for_new_stacks = original_item_name_for_collision_check
                    while remaining_quantity_to_add > 0:
                        temp_new_item_for_naming = self._create_item_copy(item, 1)
                        temp_new_item_for_naming.name = current_name_for_new_stacks
                        all_inventory_names_for_new_stack_check = [i.name for i in self._items.values()]
                        final_name_for_new_stack = temp_new_item_for_naming.name
                        if final_name_for_new_stack in all_inventory_names_for_new_stack_check:
                            new_stack_name_count = 2
                            while f"{current_name_for_new_stacks} ({new_stack_name_count})" in all_inventory_names_for_new_stack_check:
                                new_stack_name_count += 1
                            final_name_for_new_stack = f"{current_name_for_new_stacks} ({new_stack_name_count})"
                        new_item_stack = self._create_item_copy(item, min(remaining_quantity_to_add, item.stack_limit))
                        new_item_stack.name = final_name_for_new_stack
                        self._items[new_item_stack.id] = new_item_stack
                        added_item_ids.append(new_item_stack.id)
                        remaining_quantity_to_add -= new_item_stack.quantity
            else:
                current_name_for_new_stacks = item.name 
                first_stack_quantity = min(quantity, item.stack_limit)
                item_for_first_stack = self._create_item_copy(item, first_stack_quantity) 
                item_for_first_stack.name = item.name 
                self._items[item_for_first_stack.id] = item_for_first_stack
                added_item_ids.append(item_for_first_stack.id)
                remaining_quantity_to_add = quantity - first_stack_quantity
                while remaining_quantity_to_add > 0:
                    all_inventory_names_for_new_stack_check = [i.name for i in self._items.values()]
                    final_name_for_new_stack = original_item_name_for_collision_check
                    if final_name_for_new_stack in all_inventory_names_for_new_stack_check:
                        new_stack_name_count = 2
                        while f"{original_item_name_for_collision_check} ({new_stack_name_count})" in all_inventory_names_for_new_stack_check:
                            new_stack_name_count += 1
                        final_name_for_new_stack = f"{original_item_name_for_collision_check} ({new_stack_name_count})"
                    new_item_further_stack = self._create_item_copy(item, min(remaining_quantity_to_add, item.stack_limit))
                    new_item_further_stack.name = final_name_for_new_stack 
                    self._items[new_item_further_stack.id] = new_item_further_stack
                    added_item_ids.append(new_item_further_stack.id)
                    remaining_quantity_to_add -= new_item_further_stack.quantity
        else:
            item_to_add_name = item.name
            new_item_instance = self._create_item_copy(item, 1)
            new_item_instance.name = item_to_add_name 
            self._items[new_item_instance.id] = new_item_instance
            added_item_ids.append(new_item_instance.id)
            for i in range(1, quantity):
                next_item_for_naming = self._create_item_copy(item, 1)
                next_item_for_naming.name = original_item_name_for_collision_check
                all_inventory_names_for_next_item_check = [i.name for i in self._items.values()]
                final_name_for_next_item = next_item_for_naming.name
                if final_name_for_next_item in all_inventory_names_for_next_item_check:
                    next_item_name_count = 2
                    while f"{original_item_name_for_collision_check} ({next_item_name_count})" in all_inventory_names_for_next_item_check:
                        next_item_name_count += 1
                    final_name_for_next_item = f"{original_item_name_for_collision_check} ({next_item_name_count})"
                actual_new_item_instance = self._create_item_copy(item, 1)
                actual_new_item_instance.name = final_name_for_next_item
                self._items[actual_new_item_instance.id] = actual_new_item_instance
                added_item_ids.append(actual_new_item_instance.id)
        
        logger.info(f"InventoryManager ({manager_instance_id}) Added {quantity}x instances of '{original_item_name_for_collision_check}'. Resulting IDs: {added_item_ids}. Total items now: {len(self._items)}")
        
        # Record event log entry (ItemDelta) for testing/evidence
        try:
            state = get_state_manager().current_state
            if state is not None:
                item_id_for_log = getattr(item, 'template_id', None) or (getattr(item, 'id', None) or original_item_name_for_collision_check)
                record_item_delta(state, item_id=item_id_for_log, delta=int(quantity), source='inventory_add')
        except Exception:
            pass
        
        return added_item_ids
    
    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """
        Remove an item from the inventory.
        
        Args:
            item_id: The ID of the item to remove.
            quantity: The quantity to remove.
            
        Returns:
            True if the item was removed, False otherwise.
        """
        if item_id not in self._items:
            logger.warning(f"Item with ID '{item_id}' not found in inventory")
            return False
        
        item = self._items[item_id]
        
        if quantity <= 0:
            return False
        
        if item.is_stackable:
            if quantity >= item.quantity:
                # Remove the entire stack
                removed_qty = item.quantity
                self._items.pop(item_id)
                logger.info(f"Removed {removed_qty}x '{item.name}' from inventory (entire stack)")
            else:
                # Remove part of the stack
                item.quantity -= quantity
                removed_qty = quantity
                logger.info(f"Removed {quantity}x '{item.name}' from inventory (partial stack)")
        else:
            # Non-stackable items
            removed_qty = 1
            self._items.pop(item_id)
            logger.info(f"Removed '{item.name}' from inventory")
        
        # Record event log entry (ItemDelta) for testing/evidence
        try:
            state = get_state_manager().current_state
            if state is not None:
                item_id_for_log = getattr(item, 'template_id', None) or (getattr(item, 'id', None) or item.name)
                record_item_delta(state, item_id=item_id_for_log, delta=-int(removed_qty), source='inventory_remove')
        except Exception:
            pass
        
        return True
    
    def merge_stacks(self, source_id: str, target_id: str) -> bool:
        """
        Merge two stacks of items.
        
        Args:
            source_id: ID of the source stack to merge from.
            target_id: ID of the target stack to merge into.
            
        Returns:
            True if stacks were merged, False otherwise.
        """
        # Get both items
        source_item = self.get_item(source_id)
        target_item = self.get_item(target_id)
        
        # Check if both items exist and are stackable
        if not source_item or not target_item:
            logger.warning("Cannot merge stacks: One or both items not found")
            return False
        
        if not source_item.is_stackable or not target_item.is_stackable:
            logger.warning("Cannot merge stacks: One or both items are not stackable")
            return False
        
        # Check if items can be stacked together (same template)
        if source_item.template_id != target_item.template_id:
            logger.warning("Cannot merge stacks: Items are of different types")
            return False
        
        # Calculate how much we can move
        space_in_target = target_item.stack_limit - target_item.quantity
        amount_to_move = min(source_item.quantity, space_in_target)
        
        if amount_to_move <= 0:
            logger.warning("Cannot merge stacks: Target stack is already at capacity")
            return False
        
        # Move items
        target_item.quantity += amount_to_move
        
        # Update or remove source stack
        if amount_to_move == source_item.quantity:
            # Source stack is empty, remove it
            self._items.pop(source_id)
        else:
            # Update source stack
            source_item.quantity -= amount_to_move
        
        logger.info(f"Merged {amount_to_move}x '{source_item.name}' from stack {source_id} to {target_id}")
        return True
    
    def split_stack(self, item_id: str, quantity: int) -> Optional[str]:
        """
        Split a stack of items into two stacks.
        
        Args:
            item_id: ID of the stack to split.
            quantity: Amount to put in the new stack.
            
        Returns:
            ID of the new stack if successful, None otherwise.
        """
        # Get the item
        item = self.get_item(item_id)
        
        # Check if item exists and is stackable
        if not item:
            logger.warning(f"Cannot split stack: Item {item_id} not found")
            return None
        
        if not item.is_stackable:
            logger.warning(f"Cannot split stack: Item {item_id} is not stackable")
            return None
        
        # Check if quantity is valid
        if quantity <= 0 or quantity >= item.quantity:
            logger.warning(f"Cannot split stack: Invalid quantity {quantity}")
            return None
        
        # Check if we have a free slot
        if self.get_free_slots() <= 0:
            logger.warning("Cannot split stack: No free slots available")
            return None
        
        # Create new stack
        new_item = self._create_item_copy(item, quantity)
        
        # Update original stack
        item.quantity -= quantity
        
        # Add new stack to inventory
        self._items[new_item.id] = new_item
        
        logger.info(f"Split {quantity}x '{item.name}' from stack {item_id} to new stack {new_item.id}")
        return new_item.id
    
    def _create_item_copy(self, source_item: Item, quantity: int = 1) -> Item:
        """
        Create a copy of an item with a new ID.
        
        Args:
            source_item: The item to copy.
            quantity: The quantity for the new item.
            
        Returns:
            A new Item instance.
        """
        # Create a new item with the same properties
        new_item = Item(
            name=source_item.name,
            description=source_item.description,
            item_type=source_item.item_type,
            rarity=source_item.rarity,
            weight=source_item.weight,
            value=source_item.value,
            icon_path=source_item.icon_path,
            is_equippable=source_item.is_equippable,
            equip_slots=source_item.equip_slots.copy() if source_item.equip_slots else [],
            stats=copy.deepcopy(source_item.stats),
            is_consumable=source_item.is_consumable,
            is_stackable=source_item.is_stackable,
            stack_limit=source_item.stack_limit,
            quantity=quantity,
            is_quest_item=source_item.is_quest_item,
            durability=source_item.durability,
            current_durability=source_item.current_durability,
            tags=source_item.tags.copy() if source_item.tags else [],
            template_id=source_item.template_id,
            source=source_item.source,
            custom_properties=copy.deepcopy(source_item.custom_properties)
        )
        
        # Copy known properties
        new_item.known_properties = source_item.known_properties.copy()
        
        return new_item
