#!/usr/bin/env python3
"""
Narrative item creation functionality.

This module provides functions for creating items from narrative text
and LLM commands.
"""

from typing import Any

from core.utils.logging_config import get_logger
from core.inventory import (
    get_inventory_manager, 
    get_item_factory,
    Item, 
    ItemType, 
    ItemRarity, 
    EquipmentSlot,
    ItemStat
)
from core.base.commands import CommandResult

# Get module logger
logger = get_logger("NarrativeItems")

def create_item_from_command(args_text: str, game_state: Any) -> CommandResult:
    """
    Create an item from an ITEM_CREATE command.
    
    Command format: {ITEM_CREATE name rarity:rare type:weapon slot:main_hand [stats]}
    
    Args:
        args_text: The arguments text.
        game_state: The current game state.
            
    Returns:
        CommandResult with the result of the item creation.
    """
    from core.inventory.narrative_item_manager import NarrativeItemManager
    manager = NarrativeItemManager()
    
    # Parse the arguments
    args = manager.parse_command_args(args_text)
    
    if "name" not in args:
        return CommandResult.failure("No item name specified.")
    
    name = args["name"]
    description = args.get("description", f"A {name}.")
    
    # Get type
    item_type = ItemType.MISCELLANEOUS  # Default
    if "type" in args:
        type_str = args["type"].lower()
        item_type = manager._type_mappings.get(type_str, ItemType.MISCELLANEOUS)
    
    # Get rarity
    rarity = ItemRarity.COMMON  # Default
    if "rarity" in args:
        rarity_str = args["rarity"].lower()
        rarity = manager._rarity_mappings.get(rarity_str, ItemRarity.COMMON)
    
    # Equipment-specific properties
    is_equippable = item_type in [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY]
    equip_slots = []
    
    if is_equippable and "slot" in args:
        slot_str = args["slot"].lower()
        slot = manager._slot_mappings.get(slot_str)
        if slot:
            equip_slots.append(slot)
    elif is_equippable:
        # Default slots based on item type
        if item_type == ItemType.WEAPON:
            equip_slots.append(EquipmentSlot.MAIN_HAND)
        elif item_type == ItemType.ARMOR:
            # Default to chest armor if not specified
            equip_slots.append(EquipmentSlot.CHEST)
        elif item_type == ItemType.ACCESSORY:
            # Default to neck accessory if not specified
            equip_slots.append(EquipmentSlot.NECK)
    
    # Set default values based on rarity
    rarity_multiplier = {
        ItemRarity.COMMON: 1.0,
        ItemRarity.UNCOMMON: 1.5,
        ItemRarity.RARE: 2.0,
        ItemRarity.EPIC: 3.0,
        ItemRarity.LEGENDARY: 5.0,
        ItemRarity.ARTIFACT: 8.0,
        ItemRarity.UNIQUE: 10.0
    }.get(rarity, 1.0)
    
    # Base value and weight by item type
    base_values = {
        ItemType.WEAPON: 50,
        ItemType.ARMOR: 40,
        ItemType.SHIELD: 45,
        ItemType.CONSUMABLE: 20,
        ItemType.MATERIAL: 5,
        ItemType.QUEST: 0,  # Quest items have no inherent value
        ItemType.ACCESSORY: 35,
        ItemType.CONTAINER: 25,
        ItemType.DOCUMENT: 15,
        ItemType.KEY: 10,
        ItemType.TOOL: 20,
        ItemType.TREASURE: 100,
        ItemType.MISCELLANEOUS: 5
    }
    
    base_weights = {
        ItemType.WEAPON: 4.0,
        ItemType.ARMOR: 5.0,
        ItemType.SHIELD: 6.0,
        ItemType.CONSUMABLE: 0.5,
        ItemType.MATERIAL: 0.2,
        ItemType.QUEST: 0.1,
        ItemType.ACCESSORY: 0.2,
        ItemType.CONTAINER: 2.0,
        ItemType.DOCUMENT: 1.0,
        ItemType.KEY: 0.1,
        ItemType.TOOL: 1.5,
        ItemType.TREASURE: 0.3,
        ItemType.MISCELLANEOUS: 0.5
    }
    
    # Calculate value and weight based on rarity and type
    base_value = base_values.get(item_type, 5)
    value = int(base_value * rarity_multiplier)
    
    base_weight = base_weights.get(item_type, 0.5)
    weight = base_weight
    
    # Get custom value and weight if specified
    if "value" in args:
        try:
            value = int(args["value"])
        except ValueError:
            pass
    
    if "weight" in args:
        try:
            weight = float(args["weight"])
        except ValueError:
            pass
    
    # Check if item is stackable and set quantity
    is_stackable = item_type in [ItemType.MATERIAL, ItemType.CONSUMABLE, ItemType.TREASURE]
    stack_limit = 20 if is_stackable else 1
    quantity = 1
    
    if "quantity" in args:
        try:
            quantity = int(args["quantity"])
            quantity = max(1, min(quantity, stack_limit))
        except ValueError:
            pass
    
    # Consumable-specific properties
    is_consumable = item_type == ItemType.CONSUMABLE
    
    # Durability for equipment
    durability = 0
    if is_equippable:
        durability = int(100 * rarity_multiplier)
        
        if "durability" in args:
            try:
                durability = int(args["durability"])
            except ValueError:
                pass
    
    # Create stats
    stats = []
    
    # Extract stats from args
    for key, value_str in args.items():
        if key in ["name", "description", "type", "rarity", "slot", "value", "weight", "quantity", "durability"]:
            continue
        
        # Check if this is a valid stat name
        for stat_name, normalized_name in manager._stat_mappings.items():
            if key.lower() == stat_name.lower():
                try:
                    stat_value = float(value_str)
                    stats.append(ItemStat(normalized_name, stat_value))
                    break
                except ValueError:
                    logger.warning(f"Invalid stat value for {key}: {value_str}")
    
    # Create the item
    item_factory = get_item_factory()
    inventory = get_inventory_manager()
    
    item = Item(
        name=name,
        description=description,
        item_type=item_type,
        rarity=rarity,
        weight=weight,
        value=value,
        icon_path="",  # Default icon will be assigned by factory
        is_equippable=is_equippable,
        equip_slots=equip_slots,
        stats=stats,
        is_consumable=is_consumable,
        is_stackable=is_stackable,
        stack_limit=stack_limit,
        quantity=quantity,
        is_quest_item=item_type == ItemType.QUEST,
        durability=durability,
        current_durability=durability,
        tags=[],
        template_id=f"narrative_{item_type.value.lower()}",
        source="narrative",
        custom_properties={}
    )
    
    # Add item to inventory
    item_ids = inventory.add_item(item)
    
    if not item_ids:
        return CommandResult.failure(f"Failed to add {name} to inventory. Check weight and slot limits.")
    
    # Generate response message
    if quantity > 1:
        message = f"You acquired {quantity}x {name}."
    else:
        message = f"You acquired {name}."
    
    return CommandResult.success(message, {"item_ids": item_ids})

def generate_loot_from_command(args_text: str, game_state: Any) -> CommandResult:
    """
    Generate loot from a LOOT_GENERATE command.
    
    Command format: {LOOT_GENERATE enemy_type:goblin level:5 quality:good count:3}
    
    Args:
        args_text: The arguments text.
        game_state: The current game state.
            
    Returns:
        CommandResult with the result of the loot generation.
    """
    from core.inventory.narrative_item_manager import NarrativeItemManager
    manager = NarrativeItemManager()
    
    # Parse the arguments
    args = manager.parse_command_args(args_text)
    
    # Get enemy type and level
    enemy_type = args.get("enemy_type", "monster")
    
    level = 1
    if "level" in args:
        try:
            level = int(args["level"])
            level = max(1, level)
        except ValueError:
            pass
    
    # Get loot quality
    quality_values = {
        "poor": 0.5,
        "low": 0.75,
        "normal": 1.0,
        "good": 1.5,
        "excellent": 2.0
    }
    
    quality = args.get("quality", "normal").lower()
    quality_multiplier = quality_values.get(quality, 1.0)
    
    # Get item count
    count = 1
    if "count" in args:
        try:
            count = int(args["count"])
            count = max(1, min(count, 10))  # Limit to 10 items max
        except ValueError:
            pass
    
    # Calculate rarity weights based on level and quality
    rarity_weights = {
        ItemRarity.COMMON: max(0.05, 0.8 - (level * 0.05)),
        ItemRarity.UNCOMMON: min(0.6, 0.15 + (level * 0.03)),
        ItemRarity.RARE: min(0.4, 0.03 + (level * 0.02)),
        ItemRarity.EPIC: min(0.2, 0.01 + (level * 0.01)),
        ItemRarity.LEGENDARY: min(0.1, 0.001 + (level * 0.005)),
        ItemRarity.ARTIFACT: min(0.05, 0.0001 + (level * 0.001)),
        ItemRarity.UNIQUE: min(0.01, 0.00001 + (level * 0.0005))
    }
    
    # Adjust weights based on quality
    for rarity in rarity_weights:
        if rarity == ItemRarity.COMMON:
            rarity_weights[rarity] /= quality_multiplier
        else:
            rarity_weights[rarity] *= quality_multiplier
    
    # Normalize weights
    total_weight = sum(rarity_weights.values())
    for rarity in rarity_weights:
        rarity_weights[rarity] /= total_weight
    
    # Generate loot
    item_factory = get_item_factory()
    loot = item_factory.create_loot_table(
        item_count=count,
        rarity_weights=rarity_weights,
        level_range=(max(1, level-2), level+2)
    )
    
    # Add items to inventory
    inventory = get_inventory_manager()
    added_items = []
    
    for item in loot:
        item_ids = inventory.add_item(item)
        if item_ids:
            added_items.append((item, item_ids[0]))
    
    if not added_items:
        return CommandResult.failure(f"No loot could be added to inventory. Check weight and slot limits.")
    
    # Generate response message
    if len(added_items) == 1:
        item, _ = added_items[0]
        message = f"You found {item.name}."
    else:
        message = f"You found {len(added_items)} items:"
        for item, _ in added_items:
            message += f"\n- {item.name}"
    
    return CommandResult.success(message, {"item_count": len(added_items)})
