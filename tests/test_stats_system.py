#!/usr/bin/env python3
"""
Test script for the stats system.

This script creates a test character and performs various operations
to verify that the stats system is working correctly.
"""

import os
import sys
import json
import logging

# Add the project root to the path so we can import modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Change the current directory to the project root
os.chdir(project_root)

# Add project root to system path
sys.path.insert(0, project_root)

print(f"Project root: {project_root}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path[0]}")

from core.stats.stats_base import StatType, DerivedStatType
from core.stats.stats_manager import StatsManager
from core.stats.modifier import StatModifier, ModifierGroup, ModifierType, ModifierSource


def run_stats_test():
    """Run a series of tests on the stats system."""
    print("=== Stats System Test ===")
    
    # Create a stats manager
    stats_config_path = 'config/character/stats_config.json'
    if not os.path.exists(stats_config_path):
        print(f"Error: Stats config file not found at {stats_config_path}")
        print(f"Checking absolute path...")
        abs_config_path = os.path.join(project_root, 'config', 'character', 'stats_config.json')
        print(f"Checking for: {abs_config_path}")
        if os.path.exists(abs_config_path):
            print(f"Found config file at absolute path!")
            stats_config_path = abs_config_path
        else:
            print(f"Error: Stats config file not found at absolute path either.")
            return
    
    stats_manager = StatsManager(config_file=stats_config_path)
    print("Stats manager created successfully")
    
    # Verify primary stats were initialized
    for stat_type in StatType:
        stat = stats_manager.get_stat(stat_type)
        if stat:
            print(f"{stat_type.value}: {stat.value}")
        else:
            print(f"Error: Stat {stat_type.value} not found")
    
    print("\n=== Testing Derived Stats ===")
    # Check derived stats
    for stat_type in DerivedStatType:
        stat = stats_manager.get_stat(stat_type)
        if stat:
            print(f"{stat_type.value}: {stat.value}")
        else:
            print(f"Error: Derived stat {stat_type.value} not found")
    
    print("\n=== Testing Stat Modification ===")
    # Test setting a base stat
    stats_manager.set_base_stat(StatType.STRENGTH, 14)
    print(f"Set STR to 14, new value: {stats_manager.get_stat_value(StatType.STRENGTH)}")
    
    # Test adding a modifier
    str_mod = StatModifier(
        stat=StatType.STRENGTH,
        value=2,
        source_type=ModifierSource.EQUIPMENT,
        source_name="Gauntlets of Ogre Power",
        modifier_type=ModifierType.TEMPORARY,
        duration=10
    )
    stats_manager.add_modifier(str_mod)
    print(f"Added STR modifier +2, new value: {stats_manager.get_stat_value(StatType.STRENGTH)}")
    
    # Check if derived stats changed
    print(f"Melee Attack after STR boost: {stats_manager.get_stat_value(DerivedStatType.MELEE_ATTACK)}")
    print(f"Carry Capacity after STR boost: {stats_manager.get_stat_value(DerivedStatType.CARRY_CAPACITY)}")
    
    print("\n=== Testing Modifier Groups ===")
    # Test modifier groups
    buff_group = ModifierGroup(
        name="Blessing of the Warrior",
        source_type=ModifierSource.SPELL,
        modifier_type=ModifierType.TEMPORARY,
        duration=5
    )
    buff_group.add_modifier(StatType.STRENGTH, 1)
    buff_group.add_modifier(StatType.CONSTITUTION, 1)
    buff_group.add_modifier(DerivedStatType.HEALTH, 5)
    
    stats_manager.add_modifier_group(buff_group)
    print(f"Added buff group '{buff_group.name}'")
    print(f"STR after buff: {stats_manager.get_stat_value(StatType.STRENGTH)}")
    print(f"CON after buff: {stats_manager.get_stat_value(StatType.CONSTITUTION)}")
    print(f"Health after buff: {stats_manager.get_stat_value(DerivedStatType.HEALTH)}")
    
    print("\n=== Testing Duration Updates ===")
    # Test duration updates
    print("Before update:")
    print(f"STR modifier count: {len(stats_manager.modifier_manager.get_modifiers_for_stat(StatType.STRENGTH))}")
    
    # Update durations
    expired = stats_manager.update_durations()
    print(f"Updated durations, expired modifiers: {expired}")
    print(f"STR modifier count after update: {len(stats_manager.modifier_manager.get_modifiers_for_stat(StatType.STRENGTH))}")
    
    print("\n=== Testing Serialization ===")
    # Test serialization
    stats_dict = stats_manager.to_dict()
    print(f"Serialized stats to dictionary with {len(stats_dict)} keys")
    
    # Test deserialization
    new_manager = StatsManager.from_dict(stats_dict)
    print(f"Deserialized stats manager")
    print(f"STR from deserialized manager: {new_manager.get_stat_value(StatType.STRENGTH)}")
    
    print("\n=== Testing Get All Stats ===")
    # Test getting all stats organized for display
    all_stats = stats_manager.get_all_stats()
    print("All stats categorized for display:")
    for category, stats in all_stats.items():
        print(f"-- {category.upper()} --")
        for stat_name, stat_info in stats.items():
            print(f"  {stat_name}: {stat_info['value']}")
    
    print("\nStats system test completed.")

if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    run_stats_test()
