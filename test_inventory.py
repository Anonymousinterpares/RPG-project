#!/usr/bin/env python3
"""
Test script for the inventory system.

This script demonstrates basic functionality of the inventory system,
including item creation, inventory management, and equipment handling.
"""

import sys
import os
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Test")

# Import inventory system
from core.inventory import (
    get_inventory_manager,
    get_item_factory,
    get_item_template_loader,
    ItemType,
    ItemRarity,
    EquipmentSlot
)

def test_item_factory():
    """Test item factory functionality."""
    logger.info("Testing item factory...")
    
    # Get factory and template loader
    factory = get_item_factory()
    loader = get_item_template_loader()
    
    # Print available templates
    templates = loader.get_all_templates()
    logger.info(f"Loaded {len(templates)} item templates")
    
    # Create an item from template
    logger.info("Creating items from templates...")
    sword = factory.create_item_from_template("template_sword_short", variation=False)
    if sword:
        logger.info(f"Created basic item: {sword.name}, Type: {sword.item_type.value}, Rarity: {sword.rarity.value}")
        
        # Check stats
        for stat in sword.stats:
            logger.info(f"  Stat: {stat}")
    
    # Create a variation
    sword_variation = factory.create_item_from_template("template_sword_short", variation=True)
    if sword_variation:
        logger.info(f"Created variation: {sword_variation.name}, Type: {sword_variation.item_type.value}, Rarity: {sword_variation.rarity.value}")
        
        # Check stats
        for stat in sword_variation.stats:
            logger.info(f"  Stat: {stat}")
    
    # Create a random item
    random_item = factory.create_random_item(item_type=ItemType.WEAPON, variation=True)
    if random_item:
        logger.info(f"Created random item: {random_item.name}, Type: {random_item.item_type.value}, Rarity: {random_item.rarity.value}")
    
    # Generate loot table
    loot = factory.create_loot_table(
        item_count=5,
        rarity_weights={
            ItemRarity.COMMON: 0.6,
            ItemRarity.UNCOMMON: 0.3,
            ItemRarity.RARE: 0.1
        }
    )
    
    logger.info(f"Generated loot table with {len(loot)} items:")
    for item in loot:
        logger.info(f"  {item.name} ({item.rarity.value})")
    
    return True

def test_inventory_management():
    """Test inventory management functionality."""
    logger.info("Testing inventory management...")
    
    # Get inventory manager and item factory
    inventory = get_inventory_manager()
    factory = get_item_factory()
    
    # Create some items
    sword = factory.create_item_from_template("template_sword_short")
    armor = factory.create_item_from_template("template_armor_leather")
    potions = factory.create_item_from_template("template_potion_health")
    potions.quantity = 5
    gold = factory.create_item_from_template("template_gold_coin")
    gold.quantity = 10
    
    # Add items to inventory
    logger.info("Adding items to inventory...")
    sword_id = inventory.add_item(sword)[0]
    armor_id = inventory.add_item(armor)[0]
    potion_ids = inventory.add_item(potions)
    gold_ids = inventory.add_item(gold)
    
    # Check inventory contents
    logger.info(f"Inventory now contains {len(inventory.items)} items")
    logger.info(f"Current weight: {inventory.get_current_weight()} / {inventory.weight_limit}")
    logger.info(f"Used slots: {inventory.get_used_slots()} / {inventory.slot_limit}")
    
    # Test equipment
    logger.info("Testing equipment functionality...")
    if inventory.equip_item(sword_id):
        logger.info(f"Equipped {sword.name}")
    
    if inventory.equip_item(armor_id):
        logger.info(f"Equipped {armor.name}")
    
    # Check equipped items
    equipped_items = inventory.equipment
    logger.info("Currently equipped items:")
    for slot, item in equipped_items.items():
        if item:
            logger.info(f"  {slot}: {item.name}")
        else:
            logger.info(f"  {slot}: Empty")
    
    # Test item discovery
    logger.info("Testing item discovery...")
    item = inventory.get_item(sword_id)
    if item:
        # Check initial known properties
        logger.info(f"Known properties for {item.name}: {item.known_properties}")
        
        # Discover new property
        if item.discover_property("description"):
            logger.info(f"Discovered 'description' property: {item.description}")
        
        # Discover stat
        if "damage" in [stat.name for stat in item.stats]:
            if item.discover_stat("damage"):
                logger.info("Discovered 'damage' stat!")
        
        # Check known properties again
        logger.info(f"Known properties now: {item.known_properties}")
    
    # Test currency management
    logger.info("Testing currency management...")
    inventory.currency.add_mixed_currency(gold=5, silver=20, copper=50)
    logger.info(f"Current currency: {inventory.currency.get_formatted_currency()}")
    
    # Test saving and loading
    logger.info("Testing inventory serialization...")
    test_file = os.path.join(os.getcwd(), "test_inventory_save.json")
    
    # Save inventory
    if inventory.save_to_file(test_file):
        logger.info(f"Saved inventory to {test_file}")
        
        # Clear inventory
        inventory.clear()
        logger.info(f"Cleared inventory. Item count: {len(inventory.items)}")
        
        # Load inventory
        loaded_inventory = inventory.__class__.load_from_file(test_file)
        if loaded_inventory:
            logger.info(f"Loaded inventory from {test_file}")
            logger.info(f"Loaded {len(loaded_inventory.items)} items")
            
            # Check equipped items in loaded inventory
            equipped_items = loaded_inventory.equipment
            logger.info("Equipped items in loaded inventory:")
            for slot, item in equipped_items.items():
                if item:
                    logger.info(f"  {slot}: {item.name}")
            
            # Check currency in loaded inventory
            logger.info(f"Loaded currency: {loaded_inventory.currency.get_formatted_currency()}")
        
        # Clean up test file
        try:
            os.remove(test_file)
            logger.info(f"Removed test file {test_file}")
        except:
            pass
    
    return True

def test_item_modifications():
    """Test item modification functionality."""
    logger.info("Testing item modifications...")
    
    # Get item factory
    factory = get_item_factory()
    
    # Create a base item
    sword = factory.create_item_from_template("template_sword_short")
    logger.info(f"Created base item: {sword.name}")
    logger.info(f"Base stats:")
    for stat in sword.stats:
        logger.info(f"  {stat}")
    
    # Create upgraded variations
    from core.inventory.item_variation_generator import ItemVariationGenerator
    upgraded_sword = ItemVariationGenerator.create_upgraded_variation(sword, 3)
    logger.info(f"Created upgraded item: {upgraded_sword.name}")
    logger.info(f"Upgraded stats:")
    for stat in upgraded_sword.stats:
        logger.info(f"  {stat}")
    
    # Create damaged variation
    damaged_sword = ItemVariationGenerator.create_damaged_variation(sword, 2)
    logger.info(f"Created damaged item: {damaged_sword.name}")
    logger.info(f"Damaged stats:")
    for stat in damaged_sword.stats:
        logger.info(f"  {stat}")
    
    return True

def main():
    """Run inventory system tests."""
    logger.info("Starting inventory system tests...")
    
    tests = [
        ("Item Factory", test_item_factory),
        ("Inventory Management", test_inventory_management),
        ("Item Modifications", test_item_modifications)
    ]
    
    results = {}
    
    for name, test_func in tests:
        logger.info(f"\n== Running test: {name} ==")
        try:
            result = test_func()
            results[name] = "PASSED" if result else "FAILED"
        except Exception as e:
            logger.exception(f"Error in test {name}")
            results[name] = f"ERROR: {str(e)}"
    
    logger.info("\n== Test Results ==")
    for name, result in results.items():
        logger.info(f"{name}: {result}")

if __name__ == "__main__":
    main()
