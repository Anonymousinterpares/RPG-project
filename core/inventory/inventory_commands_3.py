#!/usr/bin/env python3
"""
Finalized inventory command handlers for the RPG game.

This module provides the remaining command handlers for inventory-related commands
like 'currency', 'equipment', and 'drop'.
"""

from typing import List, Optional
import logging

from core.utils.logging_config import get_logger
from core.base.state import GameState
from core.base.commands import CommandResult
from core.inventory import get_inventory_manager, EquipmentSlot

# Get module logger
logger = get_logger("INVENTORY")

def currency_command(game_state: GameState, args: List[str]) -> CommandResult:
    """
    Display current currency.
    
    Args:
        game_state: The current game state.
        args: Command arguments (ignored).
            
    Returns:
        CommandResult with currency information.
    """
    inventory = get_inventory_manager()
    
    # Get formatted currency
    currency_str = inventory.currency.get_formatted_currency()
    
    # Show details of each denomination
    gold = inventory.currency.gold
    silver = inventory.currency.silver
    copper = inventory.currency.copper
    
    result_lines = [
        "Your Currency:",
        f"  {currency_str}",
        "",
        f"  Gold: {gold}",
        f"  Silver: {silver}",
        f"  Copper: {copper}"
    ]
    
    return CommandResult.success("\n".join(result_lines))


def equipment_command(game_state: GameState, args: List[str]) -> CommandResult:
    """
    Display currently equipped items.
    
    Args:
        game_state: The current game state.
        args: Command arguments (ignored).
            
    Returns:
        CommandResult with equipment information.
    """
    inventory = get_inventory_manager()
    
    # Group equipment slots by category
    equipment_categories = {
        "Weapons": [EquipmentSlot.MAIN_HAND, EquipmentSlot.OFF_HAND, EquipmentSlot.TWO_HAND, EquipmentSlot.RANGED, EquipmentSlot.AMMUNITION],
        "Armor": [EquipmentSlot.HEAD, EquipmentSlot.SHOULDERS, EquipmentSlot.ARMS, EquipmentSlot.WRISTS, EquipmentSlot.HANDS, EquipmentSlot.CHEST, EquipmentSlot.WAIST, EquipmentSlot.LEGS, EquipmentSlot.FEET],
        "Accessories": [EquipmentSlot.NECK, EquipmentSlot.BACK, EquipmentSlot.FINGER_1, EquipmentSlot.FINGER_2, EquipmentSlot.TRINKET_1, EquipmentSlot.TRINKET_2]
    }
    
    result_lines = ["Your Equipment:"]
    
    # Show equipment by category
    for category, slots in equipment_categories.items():
        result_lines.append(f"\n{category}:")
        
        for slot in slots:
            equipped = inventory.equipment.get(slot)
            item = equipped if equipped is not None else None
            if item:
                # Show item rarity and stats if known
                stats_str = ""
                known_stats = [stat for stat in item.stats 
                               if f"stat_{stat.name}" in item.known_properties]
                
                if known_stats:
                    stats = []
                    for stat in known_stats:
                        stats.append(f"{stat.name.capitalize()}: {stat.value}")
                    stats_str = f" ({', '.join(stats)})"
                
                # Show durability if known
                durability_str = ""
                if getattr(item, "durability", None) and "durability" in item.known_properties:
                    try:
                        durability_percent = (float(item.current_durability or item.durability) / float(item.durability)) * 100
                        durability_str = f" [{durability_percent:.1f}%]"
                    except Exception:
                        pass
                
                result_lines.append(f"  {slot.value}: {item.name} ({item.rarity.value}){stats_str}{durability_str}")
            else:
                result_lines.append(f"  {slot.value}: Empty")
    
    # Add summary stats if the character has any equipment
    if any(inventory.equipment.values()):
        result_lines.append("\nEquipment Stats:")
        
        # Calculate total stats from equipped items
        total_stats = {}
        
        for item_id in inventory.equipment.values():
            if item_id:
                item = inventory.get_item(item_id)
                if item:
                    for stat in item.stats:
                        if f"stat_{stat.name}" in item.known_properties:
                            if stat.name in total_stats:
                                total_stats[stat.name] += stat.value
                            else:
                                total_stats[stat.name] = stat.value
        
        # Display total stats
        for stat_name, stat_value in sorted(total_stats.items()):
            result_lines.append(f"  {stat_name.capitalize()}: {stat_value}")
    
    return CommandResult.success("\n".join(result_lines))


def drop_command(game_state: GameState, args: List[str]) -> CommandResult:
    """
    Drop an item from the inventory.
    If this is called after LLM narration (e.g. via a specific mechanical command),
    it should be silent. If called by player typing "/drop", LLM handles narration,
    so this just does mechanics.
    
    Args:
        game_state: The current game state.
        args: Item ID or name to drop, and optional quantity.
            
    Returns:
        CommandResult indicating success or failure.
    """
    if not args:
        return CommandResult.invalid("Please specify an item to drop.")
    
    inventory = get_inventory_manager()
    item_id_or_name = " ".join(args) # Join all args to handle multi-word item names
    quantity_to_drop = 1 # Default to dropping 1 or whole stack if not specified otherwise

    # Crude check for quantity at the end of the string
    if len(args) > 1 and args[-1].isdigit():
        try:
            quantity_to_drop = int(args[-1])
            item_id_or_name = " ".join(args[:-1]) # Remove quantity from name string
            if quantity_to_drop <= 0:
                return CommandResult.invalid("Quantity must be a positive number.")
        except ValueError:
            # Last arg wasn't a number, assume it's part of the name
            pass
    
    item_to_drop = inventory.get_item(item_id_or_name) # Try ID first
    if not item_to_drop: # Try name
        found_items = inventory.find_items(name=item_id_or_name)
        if found_items:
            if len(found_items) == 1:
                item_to_drop = found_items[0]
            else:
                # If multiple items match name, player needs to be more specific or use ID
                # For now, we won't output this to game window, just log.
                matched_names_log = [f"'{i.name}' (ID: {i.id})" for i in found_items[:3]]
                logger.warning(f"Drop command: Multiple items match '{item_id_or_name}': {', '.join(matched_names_log)}. Aborting mechanical drop.")
                return CommandResult.failure(f"Multiple items match '{item_id_or_name}'. Please use item ID.")
    
    if not item_to_drop:
        logger.warning(f"Drop command: Item '{item_id_or_name}' not found for mechanical drop.")
        return CommandResult.failure(f"Item '{item_id_or_name}' not found in your inventory.")
    
    # Check if item is equipped (this check is also in MainWindow, but good to have here for direct command use)
    if inventory.is_item_equipped(item_to_drop.id):
        logger.warning(f"Drop command: Attempt to drop equipped item '{item_to_drop.name}'. Must be unequipped first.")
        return CommandResult.failure(f"You cannot drop equipped items. Unequip {item_to_drop.name} first.")
    
    actual_quantity_in_stack = item_to_drop.quantity
    quantity_being_dropped = quantity_to_drop

    if item_to_drop.is_stackable and quantity_to_drop < actual_quantity_in_stack:
        # Dropping part of a stack
        success = inventory.remove_item(item_to_drop.id, quantity_being_dropped)
    else:
        # Dropping a non-stackable item or the entire stack
        quantity_being_dropped = actual_quantity_in_stack # Ensure we log the correct amount if dropping whole stack
        success = inventory.remove_item(item_to_drop.id, quantity_being_dropped) # quantity arg will be ignored for non-stackable or if > stack

    if success:
        logger.info(f"Mechanically dropped {quantity_being_dropped}x '{item_to_drop.name}' (ID: {item_to_drop.id}).")
        # The message here will be suppressed by process_direct_command if UI-initiated
        # and LLM narration is expected. If called mechanically post-LLM, this message is fine.
        # For now, let drop_command return a message, and calling context decides to show it.
        # To make it silent for UI flow, InputRouter/CommandHandler needs to know not to echo it.
        # The current refactor in InputRouter should handle suppressing echo for UI-initiated "drop {uuid}".
        # For typed "/drop sword", the LLM provides narration.
        # The core issue is if *this* command's success message gets output *in addition* to LLM.
        #
        # Decision: This mechanical command should be silent. The narration comes from LLM.
        # The CommandResult can still indicate success/failure for internal logic.
        # The `process_direct_command` will now suppress this message if it's a UI-initiated drop.
        return CommandResult.success(f"You dropped {quantity_being_dropped}x {item_to_drop.name}.", data={"dropped_item_id": item_to_drop.id, "quantity": quantity_being_dropped})
    else:
        logger.error(f"Mechanical drop failed for '{item_to_drop.name}' (ID: {item_to_drop.id}).")
        return CommandResult.failure(f"Failed to drop {item_to_drop.name}.")
# Additional functions to integrate with the narrative item manager

def handle_item_discovery(game_state: GameState, item_data: dict) -> CommandResult:
    """
    Handle the discovery of an item in the narrative.
    
    This function would be called by the LLM via the ITEM_DISCOVER command.
    
    Args:
        game_state: The current game state.
        item_data: Item discovery data from the LLM.
            
    Returns:
        CommandResult with discovery information.
    """
    # This function would interface with the NarrativeItemManager
    # to handle item discovery in the game world
    # For now, return a placeholder
    return CommandResult.success("Item discovery placeholder.")
