#!/usr/bin/env python3
"""
Item serialization module.

This module provides serialization and deserialization functions
for Item objects, handling conversions between Item objects and
dictionaries suitable for JSON storage.
"""

from typing import Dict, List, Any, Optional, Set, Union
import json
import uuid

from core.inventory.item import Item
from core.inventory.item_enums import ItemType, ItemRarity, EquipmentSlot
from core.inventory.item_stat import ItemStat


def item_to_dict(item: Item, include_unknown: bool = False) -> Dict[str, Any]:
    """
    Convert an Item to a dictionary for serialization.
    
    Args:
        item: The Item to convert.
        include_unknown: If True, include all properties regardless of known_properties.
                        If False, only include properties the player knows.
    
    Returns:
        Dictionary representation of the item.
    """
    # Always include these basic properties
    result = {
        "id": item.id,
        "name": item.name,
    }
    
    # Properties that might be known or unknown
    property_map = {
        "description": item.description,
        "item_type": item.item_type.value if item.item_type else None,
        "rarity": item.rarity.value if item.rarity else None,
        "weight": item.weight,
        "value": item.value,
        "icon_path": item.icon_path,
        "is_equippable": item.is_equippable,
        "equip_slots": [slot.value for slot in item.equip_slots] if item.equip_slots else [],
        "is_consumable": item.is_consumable,
        "is_stackable": item.is_stackable,
        "stack_limit": item.stack_limit,
        "quantity": item.quantity,
        "is_quest_item": item.is_quest_item,
        "durability": item.durability,
        "current_durability": item.current_durability,
        "is_destroyed": item.is_destroyed,
        "tags": item.tags,
        "template_id": item.template_id,
        "is_template": item.is_template,
        "source": item.source,
        "custom_properties": item.custom_properties,
        "discovered_at": item.discovered_at
    }
    
    # Add properties based on knowledge or inclusion flag
    for prop_name, prop_value in property_map.items():
        if include_unknown or prop_name in item.known_properties:
            result[prop_name] = prop_value
    
    # Handle stats specially
    if include_unknown:
        # Include all stats
        result["stats"] = [stat.to_dict() for stat in item.stats]
    else:
        # Include only known stats
        result["stats"] = [
            stat.to_dict() for stat in item.stats 
            if f"stat_{stat.name}" in item.known_properties
        ]

    # Handle dice_roll_effects
    if include_unknown or "dice_roll_effects" in item.known_properties: # Assuming "dice_roll_effects" becomes a knowable property
        result["dice_roll_effects"] = [effect.to_dict() for effect in item.dice_roll_effects]
    elif item.dice_roll_effects: # If not explicitly known but effects exist, decide if they should be hidden
        # For now, if not 'include_unknown' and not explicitly known, don't include them.
        # This might need adjustment based on game design (e.g., are dice effects always known once item is ID'd?)
        pass
    
    # Include the known_properties set itself if including all properties
    if include_unknown:
        result["known_properties"] = list(item.known_properties)
    
    return result


def dict_to_item(data: Dict[str, Any]) -> Item:
    """
    Create an Item from a dictionary.
    
    Args:
        data: Dictionary containing item data.
    
    Returns:
        An Item object.
    """
    from core.inventory.item_effect import DiceRollEffect # Local import to avoid circularity at module level
    
    # Extract stats first if they exist
    stats = []
    if "stats" in data:
        stats = [ItemStat.from_dict(stat_data) for stat_data in data.get("stats", [])]
    
    # Extract dice_roll_effects
    dice_roll_effects = []
    if "dice_roll_effects" in data:
        dice_roll_effects = [DiceRollEffect.from_dict(effect_data) for effect_data in data.get("dice_roll_effects", [])]

    # Extract known_properties if it exists
    known_properties = set(data.get("known_properties", []))
    
    # Extract equip_slots if they exist
    equip_slots = []
    if "equip_slots" in data:
        raw_slots = data.get("equip_slots", [])
        for slot_val in raw_slots:
            if isinstance(slot_val, str):
                try:
                    equip_slots.append(EquipmentSlot(slot_val))
                except ValueError:
                    # logger.warning(f"Invalid equip_slot string '{slot_val}' in item data, skipping.")
                    pass # Skip invalid slot
            elif isinstance(slot_val, EquipmentSlot): # Should not happen if data is from JSON
                equip_slots.append(slot_val)

    # Ensure item_type is valid or default
    item_type_str = data.get("item_type", ItemType.MISCELLANEOUS.value)
    try:
        item_type_val = ItemType(item_type_str)
    except ValueError:
        # logger.warning(f"Invalid item_type string '{item_type_str}' in item data, defaulting to MISCELLANEOUS.")
        item_type_val = ItemType.MISCELLANEOUS
        
    # Ensure rarity is valid or default
    rarity_str = data.get("rarity", ItemRarity.COMMON.value)
    try:
        rarity_val = ItemRarity(rarity_str)
    except ValueError:
        # logger.warning(f"Invalid rarity string '{rarity_str}' in item data, defaulting to COMMON.")
        rarity_val = ItemRarity.COMMON

    # Create the item with basic properties
    item = Item(
        id=data.get("id", str(uuid.uuid4())), # Ensure ID is generated if missing
        name=data.get("name", ""),
        description=data.get("description", ""),
        item_type=item_type_val,
        rarity=rarity_val,
        weight=data.get("weight", 0.0),
        value=data.get("value", 0),
        icon_path=data.get("icon_path"),
        is_equippable=data.get("is_equippable", False),
        equip_slots=equip_slots,
        stats=stats,
        dice_roll_effects=dice_roll_effects, # Add new field
        is_consumable=data.get("is_consumable", False),
        is_stackable=data.get("is_stackable", False),
        stack_limit=(data.get("stack_limit") if not data.get("is_stackable", False) else data.get("stack_limit", 20)),
        quantity=data.get("quantity", 1),
        is_quest_item=data.get("is_quest_item", False),
        durability=data.get("durability"),
        current_durability=data.get("current_durability"),
        is_destroyed=data.get("is_destroyed", False),
        known_properties=known_properties, # known_properties should be set before __post_init__
        discovered_at=data.get("discovered_at"),
        tags=data.get("tags", []),
        template_id=data.get("template_id"),
        is_template=data.get("is_template", False),
        source=data.get("source", "template"),
        custom_properties=data.get("custom_properties", {})
    )

    # Upgrade stack_limit from template if available and item is stackable
    try:
        # Skip canonical stack limit lookup when we are constructing template objects themselves
        if not getattr(item, 'is_template', False) and getattr(item, 'is_stackable', False):
            canonical_limit = None
            if item.template_id:
                try:
                    from core.inventory.item_template_loader import get_item_template_loader
                    tl = get_item_template_loader()
                    tmpl = tl.get_template(item.template_id)
                    if tmpl and getattr(tmpl, 'is_stackable', False):
                        canonical_limit = getattr(tmpl, 'stack_limit', None)
                except Exception:
                    pass
            if canonical_limit is not None and int(canonical_limit) > int(getattr(item, 'stack_limit', 1) or 1):
                item.stack_limit = int(canonical_limit)
    except Exception:
        pass
    
    # If known_properties was empty in data, __post_init__ would have set defaults.
    # If it was present, ensure the defaults are still there if they were missing from the loaded set.
    if not data.get("known_properties"): # If known_properties was not in data, post_init set defaults
        pass
    else: # If known_properties was in data, ensure defaults are present
        default_known = {"id", "name", "item_type", "weight", "is_stackable", "quantity", "is_quest_item", "tags"}
        item.known_properties.update(default_known.difference(item.known_properties))

    return item


def items_to_json(items: List[Item], include_unknown: bool = False) -> str:
    """
    Convert a list of Items to a JSON string.
    
    Args:
        items: List of Items to convert.
        include_unknown: Whether to include unknown properties.
    
    Returns:
        JSON string representation of the items.
    """
    item_dicts = [item_to_dict(item, include_unknown) for item in items]
    return json.dumps(item_dicts, indent=2)


def json_to_items(json_str: str) -> List[Item]:
    """
    Create a list of Items from a JSON string.
    
    Args:
        json_str: JSON string containing item data.
    
    Returns:
        List of Item objects.
    """
    item_dicts = json.loads(json_str)
    return [dict_to_item(item_dict) for item_dict in item_dicts]
