#!/usr/bin/env python3
"""
Additional inventory command handlers for the RPG game.

This module provides more command handlers for inventory-related commands
like 'equip', 'unequip', 'examine', etc.
"""

from typing import List, Optional
import logging

from core.inventory.item import Item
from core.utils.logging_config import get_logger
from core.base.state import GameState
from core.base.commands import CommandResult
from core.inventory import get_inventory_manager, EquipmentSlot, ItemType

# Get module logger
logger = get_logger("INVENTORY")

def equip_command(game_state: GameState, args: List[str]) -> CommandResult:
    """
    Equip an item from the inventory.
    
    Args:
        game_state: The current game state.
        args: Item ID or name to equip, optionally followed by slot name.
            
    Returns:
        CommandResult indicating success or failure.
    """
    if not args:
        return CommandResult.invalid("Usage: equip <item_id_or_name> [slot_name]")
    
    inventory = get_inventory_manager()
    item_id_or_name = args[0]
    preferred_slot_str: Optional[str] = args[1] if len(args) > 1 else None
    preferred_slot_enum: Optional[EquipmentSlot] = None

    if preferred_slot_str:
        try:
            preferred_slot_enum = EquipmentSlot(preferred_slot_str.lower().replace(" ", "_"))
        except ValueError:
            return CommandResult.invalid(f"Invalid slot name: {preferred_slot_str}. Valid slots are: {', '.join([s.value for s in EquipmentSlot])}")
    
    # Try to find the item by ID first
    item = inventory.get_item(item_id_or_name)
    
    # If not found by ID, try by name (case-insensitive partial match)
    if not item:
        # More robust name matching: find items where args[0] is a substring of item name
        # and prefer exact matches if multiple are found.
        found_items = []
        for inv_item_id, inv_item_obj in inventory._items.items(): # Access internal dict
            if item_id_or_name.lower() in inv_item_obj.name.lower():
                if inv_item_obj.name.lower() == item_id_or_name.lower(): # Exact match
                    item = inv_item_obj
                    break
                found_items.append(inv_item_obj)
        
        if not item and found_items: # No exact match, take first partial if any
            item = found_items[0]
            logger.info(f"Equip command: Found item '{item.name}' by partial name match for '{item_id_or_name}'.")

    if not item:
        return CommandResult.failure(f"Item '{item_id_or_name}' not found in your inventory.")
    
    # Check if item is equippable
    if not item.is_equippable:
        return CommandResult.failure(f"You cannot equip {item.name}.")
    
    # Try to equip the item
    if inventory.equip_item(item.id, preferred_slot=preferred_slot_enum):
        # Find which slot it was equipped to for the message
        slot_actually_equipped_to_str = "a suitable slot"
        for slot_enum_loop, item_id_loop in inventory.equipment.items(): # Iterate over current equipment state
            if item_id_loop == item.id:
                slot_actually_equipped_to_str = slot_enum_loop.value.replace("_", " ")
                break
        
        logger.info(f"Equipped {item.name} to {slot_actually_equipped_to_str} via command.")
        return CommandResult.success(f"You equipped {item.name} to your {slot_actually_equipped_to_str}.")
    else:
        # equip_item logs warnings if it fails
        return CommandResult.failure(f"Could not equip {item.name}. Check available slots or item requirements.")


def unequip_command(game_state: GameState, args: List[str]) -> CommandResult:
    """
    Unequip an item by slot, ID, or name.
    Args:
        game_state: The current game state.
        args: Slot, item ID, or item name to unequip.
            
    Returns:
        CommandResult indicating success or failure.
    """
    if not args:
        return CommandResult.invalid("Usage: unequip <slot_name_or_item_id_or_item_name>")

    inventory = get_inventory_manager()
    target_identifier = args[0] 

    target_slot_to_unequip: Optional[EquipmentSlot] = None
    item_to_unequip_obj: Optional[Item] = None

    # Try to interpret target_identifier as a slot first
    try:
        potential_slot = EquipmentSlot(target_identifier.lower().replace(" ", "_"))
        equipped_val = inventory.equipment.get(potential_slot)  # May be Item or ID string
        if equipped_val:
            if isinstance(equipped_val, Item):
                item_to_unequip_obj = equipped_val
            else:
                item_to_unequip_obj = inventory.get_item(equipped_val)
            if item_to_unequip_obj:
                target_slot_to_unequip = potential_slot
            else:
                return CommandResult.error(f"Item in slot {potential_slot.value} is missing from inventory records.")
        else:
            return CommandResult.failure(f"You have nothing equipped in your {potential_slot.value.replace('_', ' ')}.")
    except ValueError:
        # Not a direct slot name, try to find item by ID or name among equipped items
        # Search all equipped items
        for slot_enum_loop, equipped_val in inventory.equipment.items():  # Iterate over current equipment state
            if not equipped_val:
                continue
            if isinstance(equipped_val, Item):
                item_obj_in_loop = equipped_val
                equipped_id = equipped_val.id
            else:
                equipped_id = equipped_val
                item_obj_in_loop = inventory.get_item(equipped_id)
            if item_obj_in_loop:
                if equipped_id == target_identifier or target_identifier.lower() in (item_obj_in_loop.name or '').lower():
                    item_to_unequip_obj = item_obj_in_loop
                    target_slot_to_unequip = slot_enum_loop
                    break  # Found the item and its slot
        if not item_to_unequip_obj:
            return CommandResult.failure(f"You don't have an item matching '{target_identifier}' equipped, nor is it a valid slot name.")

    if not target_slot_to_unequip or not item_to_unequip_obj:
        return CommandResult.error("Failed to identify item or slot for unequipping.")

    item_name_display = item_to_unequip_obj.name
    slot_name_display = target_slot_to_unequip.value.replace("_", " ")

    unequipped_item_id_returned = inventory.unequip_item(target_slot_to_unequip)

    if unequipped_item_id_returned and unequipped_item_id_returned == item_to_unequip_obj.id:
        logger.info(f"Unequipped {item_name_display} from {slot_name_display} via command.")
        return CommandResult.success(f"You unequipped {item_name_display} from your {slot_name_display}.")
    elif unequipped_item_id_returned: 
        return CommandResult.error(f"An unexpected item was unequipped when trying to unequip {item_name_display}.")
    else: 
        return CommandResult.failure(f"Could not unequip {item_name_display}. Slot might have been empty or an error occurred.")
    
def examine_command(game_state: GameState, args: List[str]) -> CommandResult:
    """
    Examine an item to learn more about it.
    This command, when typed by player, will still go to LLM for narrative.
    The UI button will directly open the ItemInfoDialog.
    
    Args:
        game_state: The current game state.
        args: Item ID or name to examine.
            
    Returns:
        CommandResult with item information (or to be processed by LLM).
    """
    if not args:
        return CommandResult.invalid("Please specify an item to examine.")
    
    inventory = get_inventory_manager()
    item_id_or_name = " ".join(args) # Join all args to handle multi-word item names
    
    # Try to find the item by ID first
    item = inventory.get_item(item_id_or_name)
    
    # If not found by ID, try by name (case-insensitive partial match)
    if not item:
        # More robust name matching: find items where args[0] is a substring of item name
        # and prefer exact matches if multiple are found.
        found_items = []
        # Access internal dict for comprehensive search
        all_inventory_items = inventory._items.values() if hasattr(inventory, '_items') else inventory.items

        for inv_item_obj in all_inventory_items:
            if item_id_or_name.lower() in inv_item_obj.name.lower():
                if inv_item_obj.name.lower() == item_id_or_name.lower(): # Exact match
                    item = inv_item_obj
                    break
                found_items.append(inv_item_obj)
        
        if not item and found_items: # No exact match, take first partial if any
            if len(found_items) == 1:
                item = found_items[0]
                logger.info(f"Examine command: Found item '{item.name}' by partial name match for '{item_id_or_name}'.")
            else:
                # Multiple partial matches, ask user to be more specific or list them
                matched_names = [f"'{i.name}' (ID: {i.id})" for i in found_items[:5]] # Show up to 5
                return CommandResult.failure(f"Found multiple items matching '{item_id_or_name}': {', '.join(matched_names)}. Please be more specific or use the item ID.")
    
    if not item:
        return CommandResult.failure(f"Item '{item_id_or_name}' not found in your inventory.")
    
    # If the command originated from UI (e.g. examine {uuid}), InputRouter will handle it directly.
    # If typed by player (e.g. "examine sword"), InputRouter passes it to LLM.
    # This handler, if called by LLM processing (which it might not be directly anymore),
    # would provide structured data to the LLM.
    # For now, we assume LLM handles the narration if it's a typed command.
    # If this is called mechanically (e.g., after an LLM command {EXAMINE_ITEM item_id}),
    # then this structured output is useful.

    # Build the item description string for LLM context or direct display if no LLM
    result_parts = [f"You examine the {item.name}:"]
    
    # Basic properties (always known or become known on first examine)
    item.discover_property("name")
    item.discover_property("item_type")
    item.discover_property("rarity")
    item.discover_property("description") # Discover description on examine

    result_parts.append(f"- Type: {item.item_type.value.capitalize()}")
    result_parts.append(f"- Rarity: {item.rarity.value.capitalize()} (Color: {item.rarity.color})")
    
    if item.is_property_known("description"):
        result_parts.append(f"- Description: {item.description}")
    else:
        result_parts.append("- Description: You can't quite make out the details.")

    if item.is_property_known("weight"):
        result_parts.append(f"- Weight: {item.weight:.2f} units")
    
    if item.is_property_known("value"):
        from core.inventory.currency_manager import CurrencyManager # Local import
        cm_temp = CurrencyManager()
        cm_temp.set_currency(item.value)
        result_parts.append(f"- Value: {cm_temp.get_formatted_currency()}")

    if item.is_equippable and item.is_property_known("equip_slots"):
        slots_str = ", ".join(s.value.replace('_', ' ').title() for s in item.equip_slots) if item.equip_slots else "None"
        result_parts.append(f"- Equip Slots: {slots_str}")

    if item.durability is not None and item.is_property_known("durability"):
        cur_dur = item.current_durability if item.current_durability is not None else item.durability
        result_parts.append(f"- Durability: {cur_dur}/{item.durability}")

    # Stats
    known_stats = [s for s in item.stats if item.is_stat_known(s.name)]
    if known_stats:
        result_parts.append("- Stats:")
        for stat in known_stats:
            val_str = f"{stat.value:+.1f}" if isinstance(stat.value, (int, float)) and stat.value !=0 else str(stat.value)
            if stat.is_percentage and isinstance(stat.value, (int,float)): val_str += "%"
            display_name = stat.display_name if stat.display_name else stat.name.replace('_', ' ').title()
            result_parts.append(f"  - {display_name}: {val_str}")
    
    # Dice Roll Effects
    if item.dice_roll_effects and item.is_property_known("dice_roll_effects"):
        result_parts.append("- Effects:")
        for effect in item.dice_roll_effects:
            effect_desc = f"{effect.dice_notation} {effect.effect_type.replace('_', ' ').title()}"
            if effect.description: effect_desc += f" ({effect.description})"
            result_parts.append(f"  - {effect_desc}")

    # Custom Properties
    known_custom_props = {k: v for k, v in item.custom_properties.items() if item.is_property_known(f"custom_{k}")}
    if known_custom_props:
        result_parts.append("- Properties:")
        for key, value in known_custom_props.items():
            result_parts.append(f"  - {key.replace('_', ' ').title()}: {value}")
            
    if item.is_property_known("tags") and item.tags:
        result_parts.append(f"- Tags: {', '.join(item.tags)}")

    # For the purpose of this command handler returning a string for LLM:
    # If called by a direct "examine sword" from player, the LLM provides narration.
    # If this function is called as a result of an LLM issuing an EXAMINE_MECHANICAL command,
    # this detailed string could be used by another agent or logged.
    # Since UI button directly opens a dialog, this path is less critical for UI.
    
    # The `InputRouter` logic was changed: UI-generated "examine {uuid}" commands
    # are processed by `_process_direct_command`. If that direct command is "examine",
    # this `examine_command` handler is called.
    # For UI-originated "examine", we do NOT want text output to the game window.
    # MainWindow._handle_item_examine_requested should open the dialog.
    # This command handler should just return success for the engine's loop.

    # Check if the command was likely UI-generated (contains UUID)
    # A bit of a hack here, ideally InputRouter would pass a flag.
    is_likely_ui_command = '-' in item_id_or_name and len(item_id_or_name) > 10 

    if is_likely_ui_command:
        # The actual dialog display is handled by MainWindow when it receives item_examine_requested signal
        logger.info(f"Examine command (likely UI initiated) for {item.name} (ID: {item.id}) processed mechanically.")
        return CommandResult.success(message=f"Examined {item.name}.", data={"item_id": item.id, "action": "examine_dialog"})
    else:
        # This is for a typed command, let LLM narrate.
        # The engine will get this text, then pass it to AgentManager.
        # AgentManager's NarratorAgent should use this as part of its context.
        logger.info(f"Examine command (typed) for {item.name}. LLM will narrate.")
        return CommandResult.success("\n".join(result_parts), data={"item_id": item.id, "action": "examine_llm_narrate"})