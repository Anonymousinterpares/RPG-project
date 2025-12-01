#!/usr/bin/env python3
"""
Narrative Item Manager for the RPG game.

This module provides a manager that enables the LLM to create and manage items
through narrative text. It parses narrative text for item references and generates
items based on the LLM's descriptions.
"""

import re
from typing import Dict, List, Any, Tuple

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


class NarrativeItemManager:
    """
    Manager for creating and tracking items described in narrative text.
    
    This class provides methods for parsing item descriptions from narrative
    text, generating items from LLM descriptions, and creating loot drops
    for combat encounters.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(NarrativeItemManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the narrative item manager."""
        if self._initialized:
            return
        
        # Initialize inventory manager and item factory
        self._inventory = get_inventory_manager()
        self._item_factory = get_item_factory()
        
        # Initialize command patterns
        self._item_create_pattern = re.compile(r'\{ITEM_CREATE\s+(.+?)\}')
        self._item_discover_pattern = re.compile(r'\{ITEM_DISCOVER\s+(.+?)\}')
        self._loot_generate_pattern = re.compile(r'\{LOOT_GENERATE\s+(.+?)\}')
        
        # Initialize mappings from the mappings module
        from core.inventory.narrative_item_mappings import (
            get_type_mappings,
            get_rarity_mappings,
            get_slot_mappings,
            get_stat_mappings
        )
        
        self._type_mappings = get_type_mappings()
        self._rarity_mappings = get_rarity_mappings()
        self._slot_mappings = get_slot_mappings()
        self._stat_mappings = get_stat_mappings()
        
        self._initialized = True
        logger.info("Narrative item manager initialized")
    
    def process_narrative_commands(self, text: str, game_state: Any) -> Tuple[str, List[CommandResult]]:
        """
        Process item-related commands in narrative text.
        
        Args:
            text: The narrative text containing commands.
            game_state: The current game state.
            
        Returns:
            A tuple of (processed_text, command_results).
        """
        from core.inventory.narrative_item_creation import create_item_from_command, generate_loot_from_command
        from core.inventory.narrative_item_discovery import discover_item_from_command
        
        results = []
        processed_text = text
        
        # Process ITEM_CREATE commands
        for match in self._item_create_pattern.finditer(text):
            command_text = match.group(0)
            args_text = match.group(1)
            
            try:
                result = create_item_from_command(args_text, game_state)
                results.append(result)
                
                # Replace the command with its result
                replacement = result.message if result.is_success else f"[Item Creation Failed: {result.message}]"
                processed_text = processed_text.replace(command_text, replacement)
            except Exception as e:
                logger.error(f"Error processing ITEM_CREATE command: {e}", exc_info=True)
                processed_text = processed_text.replace(command_text, f"[Item Creation Error: {e}]")
        
        # Process ITEM_DISCOVER commands
        for match in self._item_discover_pattern.finditer(text):
            command_text = match.group(0)
            args_text = match.group(1)
            
            try:
                result = discover_item_from_command(args_text, game_state)
                results.append(result)
                
                # Replace the command with its result
                replacement = result.message if result.is_success else f"[Item Discovery Failed: {result.message}]"
                processed_text = processed_text.replace(command_text, replacement)
            except Exception as e:
                logger.error(f"Error processing ITEM_DISCOVER command: {e}", exc_info=True)
                processed_text = processed_text.replace(command_text, f"[Item Discovery Error: {e}]")
        
        # Process LOOT_GENERATE commands
        for match in self._loot_generate_pattern.finditer(text):
            command_text = match.group(0)
            args_text = match.group(1)
            
            try:
                result = generate_loot_from_command(args_text, game_state)
                results.append(result)
                
                # Replace the command with its result
                replacement = result.message if result.is_success else f"[Loot Generation Failed: {result.message}]"
                processed_text = processed_text.replace(command_text, replacement)
            except Exception as e:
                logger.error(f"Error processing LOOT_GENERATE command: {e}", exc_info=True)
                processed_text = processed_text.replace(command_text, f"[Loot Generation Error: {e}]")
        
        return processed_text, results
    
    def parse_command_args(self, args_text: str) -> Dict[str, str]:
        """
        Parse command arguments into a dictionary.
        
        Args:
            args_text: Space-separated arguments text.
            
        Returns:
            Dictionary of argument key-value pairs.
        """
        args = {}
        parts = args_text.split()
        
        # The first argument is always the item name
        if parts:
            args["name"] = parts[0]
            
            # Process the remaining arguments as key-value pairs
            for i in range(1, len(parts)):
                part = parts[i]
                if ":" in part:
                    key, value = part.split(":", 1)
                    args[key.lower()] = value
        
        return args
