#!/usr/bin/env python3
"""
Inventory command handlers for the RPG game.

This module provides command handlers for inventory-related commands
like 'inventory', 'equip', 'unequip', 'examine', etc.
"""

from typing import List

from core.utils.logging_config import get_logger
from core.base.state import GameState
from core.base.commands import CommandResult, get_command_processor
from core.inventory import get_inventory_manager, ItemType

# Import command functions from other modules
from core.inventory.inventory_commands_2 import (
    equip_command,
    unequip_command,
    examine_command
)

from core.inventory.inventory_commands_3 import (
    currency_command,
    equipment_command,
    drop_command
)

# Get module logger
logger = get_logger("INVENTORY")

# Helper to normalize equipped mapping to item ID
from typing import Any as _Any

def equipment_item_id(equipped_entry: _Any) -> str:
    try:
        # EquipmentManager.equipment returns Item objects
        from core.inventory.item import Item as _Item
        if isinstance(equipped_entry, _Item):
            return equipped_entry.id
        # For backward/save compatibility if value is an ID string
        if isinstance(equipped_entry, str):
            return equipped_entry
    except Exception:
        pass
    return ""

def register_inventory_commands():
    """Register all inventory-related commands with the command processor."""
    command_processor = get_command_processor()
    
    # Register the inventory command
    command_processor.register_command(
        name="inventory",
        handler=inventory_command,
        syntax="inventory [category]",
        description="Display the contents of your inventory, optionally filtered by category.",
        examples=["inventory", "inventory weapons", "inventory armor"],
        aliases=["inv", "i", "GET_INVENTORY"]
    )
    
    # Register the equip command
    command_processor.register_command(
        name="equip",
        handler=equip_command,
        syntax="equip <item_id or item_name>",
        description="Equip an item from your inventory.",
        examples=["equip sword", "equip 12345"],
        aliases=["wear", "wield"]
    )
    
    # Register the unequip command
    command_processor.register_command(
        name="unequip",
        handler=unequip_command,
        syntax="unequip <slot or item_id or item_name>",
        description="Unequip an item from a specific slot or by item name/ID.",
        examples=["unequip weapon", "unequip 12345", "unequip sword"],
        aliases=["remove", "unwield"]
    )
    
    # Register the examine command
    command_processor.register_command(
        name="examine",
        handler=examine_command,
        syntax="examine <item_id or item_name>",
        description="Examine an item in your inventory to learn more about it.",
        examples=["examine sword", "examine 12345"],
        aliases=["look", "inspect"]
    )
    
    # Register the currency command
    command_processor.register_command(
        name="currency",
        handler=currency_command,
        syntax="currency",
        description="Display your current currency.",
        examples=["currency"],
        aliases=["gold", "money", "coins"]
    )
    
    # Register the equipment command
    command_processor.register_command(
        name="equipment",
        handler=equipment_command,
        syntax="equipment",
        description="Display your currently equipped items.",
        examples=["equipment"],
        aliases=["equipped", "gear"]
    )
    
    # Register the drop command
    command_processor.register_command(
        name="drop",
        handler=drop_command,
        syntax="drop <item_id or item_name> [quantity]",
        description="Drop an item from your inventory.",
        examples=["drop sword", "drop 12345", "drop potion 5"],
        aliases=["discard"]
    )
    
    # Register the loot command
    command_processor.register_command(
        name="loot",
        handler=loot_command,
        syntax="loot [take <item_id|all>]",
        description="List available loot or take items from defeated enemies.",
        examples=["loot", "loot take sword", "loot take all"],
        aliases=["take", "pickup"]
    )
    
    logger.info("Registered inventory commands")


def inventory_command(game_state: GameState, args: List[str]) -> CommandResult:
    """
    Display the contents of the inventory, optionally filtered by category.
    
    Args:
        game_state: The current game state.
        args: Optional category filter.
            
    Returns:
        CommandResult with inventory information.
    """
    inventory = get_inventory_manager()
    
    # Check if inventory is empty
    if not inventory.items:
        return CommandResult.success("Your inventory is empty.")
    
    # Check for category filter
    category = args[0].lower() if args else None
    
    # Get all items, filtered if necessary
    items = list(inventory.items)
    
    if category:
        # Try to match category to ItemType
        matched_type = None
        for item_type in ItemType:
            if category in item_type.value.lower():
                matched_type = item_type
                break
        
        if matched_type:
            items = [item for item in items if item.item_type == matched_type]
            if not items:
                return CommandResult.success(f"You have no {matched_type.value.lower()} items in your inventory.")
        else:
            # Try to match by item name
            items = [item for item in items if category.lower() in item.name.lower()]
            if not items:
                return CommandResult.success(f"No items matching '{category}' found in your inventory.")
    
    # Sort items by type and name
    items = sorted(items, key=lambda item: (item.item_type.value, item.name))
    
    # Build the inventory display
    result_lines = ["Inventory:"]
    
    # Group by item type
    current_type = None
    
    for item in items:
        # Add type header if this is a new type
        if current_type != item.item_type:
            current_type = item.item_type
            result_lines.append(f"\n{current_type.value}:")
        
        # Check if item is equipped
        equipped = ""
        for slot, equipped_item in inventory.equipment.items():
            if equipped_item and equipment_item_id(equipped_item) == item.id:
                equipped = f" (Equipped: {slot.value})"
                break
        
        # Add quantity for stackable items
        quantity = f" x{item.quantity}" if item.is_stackable and item.quantity > 1 else ""
        
        # Add item with ID
        result_lines.append(f"  {item.name}{quantity} [ID: {item.id}]{equipped}")
    
    # Add inventory stats
    result_lines.append(f"\nInventory: {inventory.get_used_slots()}/{inventory.slot_limit} slots used")
    result_lines.append(f"Weight: {inventory.get_current_weight():.1f}/{inventory.weight_limit:.1f} units")
    result_lines.append(f"Currency: {inventory.currency.get_formatted_currency()}")
    
    return CommandResult.success("\n".join(result_lines))


def loot_command(game_state: GameState, args: List[str]) -> CommandResult:
    """
    Handle loot-related commands: list, take, take all.
    
    Usage:
        loot - List available loot
        loot take <item_id> - Take a specific item
        loot take all - Take all available items
    """
    # Check if there's any available loot
    if not hasattr(game_state, 'available_loot') or not game_state.available_loot:
        return CommandResult.success("No loot available.")
    
    if not args:
        # List available loot
        return _list_available_loot(game_state)
    
    command = args[0].lower()
    
    if command == "take":
        if len(args) < 2:
            return CommandResult.error("Usage: loot take <item_id> or loot take all")
        
        if args[1].lower() == "all":
            return _take_all_loot(game_state)
        else:
            item_identifier = args[1]
            return _take_specific_loot(game_state, item_identifier)
    
    return CommandResult.error(f"Unknown loot command: {command}. Use: loot, loot take <item_id>, or loot take all")


def _list_available_loot(game_state: GameState) -> CommandResult:
    """List all available loot items."""
    available_loot = game_state.available_loot
    
    if not available_loot:
        return CommandResult.success("No loot available.")
    
    result_lines = ["Available Loot:"]
    
    for i, loot_entry in enumerate(available_loot):
        try:
            item_data = loot_entry.get('item_data', {})
            item_name = item_data.get('name', 'Unknown Item')
            item_id = item_data.get('id', f'loot_{i}')
            source = loot_entry.get('source', 'Unknown')
            slot = loot_entry.get('slot', 'unknown')
            
            result_lines.append(f"  {item_name} [ID: {item_id}] (from {source}, was equipped in {slot})")
            
        except Exception as e:
            logger.error(f"Error listing loot item {i}: {e}")
            result_lines.append(f"  <Error listing item {i}>")
    
    result_lines.append(f"\nTotal: {len(available_loot)} item(s)")
    result_lines.append("Use 'loot take <item_id>' to take an item or 'loot take all' to take everything.")
    
    return CommandResult.success("\n".join(result_lines))


def _take_specific_loot(game_state: GameState, item_identifier: str) -> CommandResult:
    """Take a specific loot item."""
    available_loot = game_state.available_loot
    
    # Find the loot item
    loot_entry = None
    loot_index = None
    
    for i, entry in enumerate(available_loot):
        item_data = entry.get('item_data', {})
        if (item_data.get('id') == item_identifier or 
            item_data.get('name', '').lower() == item_identifier.lower()):
            loot_entry = entry
            loot_index = i
            break
    
    if not loot_entry:
        return CommandResult.error(f"Loot item '{item_identifier}' not found.")
    
    try:
        # Convert loot to item and add to inventory
        from core.inventory.item_serialization import dict_to_item
        item = dict_to_item(loot_entry['item_data'])
        
        # Get player inventory
        inventory = get_inventory_manager()
        
        # Try to add the item
        if inventory.can_add_item(item):
            inventory.add_item(item)
            
            # Remove from available loot
            del available_loot[loot_index]
            
            source = loot_entry.get('source', 'defeated enemy')
            return CommandResult.success(f"Took {item.name} from {source}.")
        else:
            return CommandResult.error(f"Cannot take {item.name}: not enough inventory space.")
    
    except Exception as e:
        logger.error(f"Error taking loot item {item_identifier}: {e}")
        return CommandResult.error(f"Failed to take item: {e}")


def _take_all_loot(game_state: GameState) -> CommandResult:
    """Take all available loot items."""
    available_loot = game_state.available_loot
    
    if not available_loot:
        return CommandResult.success("No loot to take.")
    
    inventory = get_inventory_manager()
    taken_items = []
    failed_items = []
    
    # Process each loot item
    for loot_entry in available_loot[:]:  # Copy list to avoid modification during iteration
        try:
            from core.inventory.item_serialization import dict_to_item
            item = dict_to_item(loot_entry['item_data'])
            
            if inventory.can_add_item(item):
                inventory.add_item(item)
                taken_items.append(item.name)
                available_loot.remove(loot_entry)
            else:
                failed_items.append(item.name)
                
        except Exception as e:
            logger.error(f"Error processing loot item: {e}")
            failed_items.append(f"<Error: {e}>")
    
    # Generate result message
    result_lines = []
    
    if taken_items:
        result_lines.append(f"Took {len(taken_items)} items:")
        for item_name in taken_items:
            result_lines.append(f"  - {item_name}")
    
    if failed_items:
        result_lines.append(f"\nCould not take {len(failed_items)} items (insufficient space):")
        for item_name in failed_items:
            result_lines.append(f"  - {item_name}")
    
    if not taken_items and not failed_items:
        return CommandResult.success("No loot was available to take.")
    
    return CommandResult.success("\n".join(result_lines))
