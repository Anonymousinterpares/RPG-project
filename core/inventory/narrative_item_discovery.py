#!/usr/bin/env python3
"""
Narrative item discovery functionality.

This module provides functions for discovering and examining items
in the narrative context.
"""

import re
import random
import logging
from typing import Dict, List, Optional, Any, Tuple, Set, Union

from core.utils.logging_config import get_logger
from core.inventory import get_inventory_manager
from core.base.commands import CommandResult

# Get module logger
logger = get_logger("NarrativeItems")

def discover_item_from_command(args_text: str, game_state: Any) -> CommandResult:
    """
    Discover an item's properties from an ITEM_DISCOVER command.
    
    Command format: {ITEM_DISCOVER item:item_id_or_name property:description}
    
    Args:
        args_text: The arguments text.
        game_state: The current game state.
            
    Returns:
        CommandResult with the result of the item discovery.
    """
    from core.inventory.narrative_item_manager import NarrativeItemManager
    manager = NarrativeItemManager()
    
    # Parse the arguments
    args = manager.parse_command_args(args_text)
    
    if "item" not in args:
        return CommandResult.failure("No item specified for discovery.")
    
    # Get the item
    inventory = get_inventory_manager()
    item_id_or_name = args["item"]
    
    # Try to find the item by ID first
    item = inventory.get_item(item_id_or_name)
    
    # If not found by ID, try by name (case-insensitive partial match)
    if not item:
        for inv_item in inventory.items.values():
            if item_id_or_name.lower() in inv_item.name.lower():
                item = inv_item
                break
    
    if not item:
        return CommandResult.failure(f"Item '{item_id_or_name}' not found in inventory.")
    
    # Check if we're discovering a specific property
    if "property" in args:
        property_name = args["property"].lower()
        
        # Check if it's a stat
        for stat_name, normalized_name in manager._stat_mappings.items():
            if property_name == stat_name.lower() or property_name == normalized_name.lower():
                # Find the stat in the item
                for stat in item.stats:
                    if stat.name.lower() == normalized_name.lower():
                        if item.discover_stat(stat.name):
                            return CommandResult.success(
                                f"You discover that the {item.name} has {stat.name} of {stat.value}.",
                                {"item_id": item.id, "property": f"stat_{stat.name}"}
                            )
                        else:
                            return CommandResult.success(
                                f"You already knew that the {item.name} has {stat.name} of {stat.value}.",
                                {"item_id": item.id, "property": f"stat_{stat.name}"}
                            )
                
                return CommandResult.failure(f"The {item.name} doesn't have a {property_name} stat.")
        
        # Check if it's a standard property
        standard_properties = ["description", "weight", "value", "durability"]
        for prop in standard_properties:
            if property_name == prop.lower():
                if item.discover_property(prop):
                    value = getattr(item, prop)
                    if prop == "value":
                        from core.inventory.currency_manager import format_currency
                        value = format_currency(value)
                    
                    return CommandResult.success(
                        f"You discover that the {item.name} has a {prop} of {value}.",
                        {"item_id": item.id, "property": prop}
                    )
                else:
                    value = getattr(item, prop)
                    if prop == "value":
                        from core.inventory.currency_manager import format_currency
                        value = format_currency(value)
                    
                    return CommandResult.success(
                        f"You already knew that the {item.name} has a {prop} of {value}.",
                        {"item_id": item.id, "property": prop}
                    )
        
        # Check if it's a custom property
        for custom_prop in item.custom_properties:
            if property_name == custom_prop.lower():
                prop_key = f"custom_{custom_prop}"
                if item.discover_property(prop_key):
                    value = item.custom_properties[custom_prop]
                    return CommandResult.success(
                        f"You discover that the {item.name} has a {custom_prop} of {value}.",
                        {"item_id": item.id, "property": prop_key}
                    )
                else:
                    value = item.custom_properties[custom_prop]
                    return CommandResult.success(
                        f"You already knew that the {item.name} has a {custom_prop} of {value}.",
                        {"item_id": item.id, "property": prop_key}
                    )
        
        # Property not found
        return CommandResult.failure(f"The {item.name} doesn't have a {property_name} property.")
    
    # If no specific property was specified, discover something random
    # Get all discoverable properties that aren't known yet
    all_props = set(dir(item))
    all_props = {prop for prop in all_props 
                if not prop.startswith('_') and not callable(getattr(item, prop))}
    stat_props = {f"stat_{stat.name}" for stat in item.stats}
    custom_props = {f"custom_{key}" for key in item.custom_properties.keys()}
    
    all_discoverable = all_props.union(stat_props).union(custom_props)
    unknown = all_discoverable - set(item.known_properties)
    
    if not unknown:
        return CommandResult.success(
            f"You've already discovered everything about the {item.name}.",
            {"item_id": item.id, "property": None}
        )
    
    # Discover a random unknown property
    prop_to_discover = random.choice(list(unknown))
    
    if prop_to_discover.startswith("stat_"):
        stat_name = prop_to_discover[5:]  # Remove "stat_" prefix
        if item.discover_stat(stat_name):
            # Find the stat value
            for stat in item.stats:
                if stat.name == stat_name:
                    return CommandResult.success(
                        f"You discover that the {item.name} has {stat_name} of {stat.value}.",
                        {"item_id": item.id, "property": f"stat_{stat_name}"}
                    )
    elif prop_to_discover.startswith("custom_"):
        custom_name = prop_to_discover[7:]  # Remove "custom_" prefix
        if item.discover_property(f"custom_{custom_name}"):
            value = item.custom_properties[custom_name]
            return CommandResult.success(
                f"You discover that the {item.name} has a {custom_name} of {value}.",
                {"item_id": item.id, "property": f"custom_{custom_name}"}
            )
    else:
        if item.discover_property(prop_to_discover):
            value = getattr(item, prop_to_discover)
            
            if prop_to_discover == "description":
                return CommandResult.success(
                    f"You examine the {item.name} more closely. {value}",
                    {"item_id": item.id, "property": prop_to_discover}
                )
            elif prop_to_discover == "value":
                from core.inventory.currency_manager import format_currency
                value = format_currency(value)
                return CommandResult.success(
                    f"You assess the {item.name} and determine it's worth about {value}.",
                    {"item_id": item.id, "property": prop_to_discover}
                )
            elif prop_to_discover == "weight":
                return CommandResult.success(
                    f"You heft the {item.name} and estimate it weighs around {value} units.",
                    {"item_id": item.id, "property": prop_to_discover}
                )
            elif prop_to_discover == "durability":
                durability_percent = (item.current_durability / item.durability) * 100
                condition = "excellent"
                if durability_percent < 20:
                    condition = "very poor"
                elif durability_percent < 40:
                    condition = "poor"
                elif durability_percent < 60:
                    condition = "fair"
                elif durability_percent < 80:
                    condition = "good"
                
                return CommandResult.success(
                    f"You inspect the {item.name} and find it's in {condition} condition.",
                    {"item_id": item.id, "property": prop_to_discover}
                )
            else:
                return CommandResult.success(
                    f"You discover that the {item.name} has a {prop_to_discover} of {value}.",
                    {"item_id": item.id, "property": prop_to_discover}
                )
    
    # This should not happen, but just in case
    return CommandResult.success(
        f"You study the {item.name} but don't learn anything new.",
        {"item_id": item.id, "property": None}
    )
