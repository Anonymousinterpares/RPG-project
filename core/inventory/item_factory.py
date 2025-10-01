#!/usr/bin/env python3
"""
Item factory module.

This module provides the ItemFactory class for creating items
from templates and specifications.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
import logging
import uuid
import random
import json
import os
from pathlib import Path
from datetime import datetime

from core.utils.logging_config import get_logger
from core.inventory.item import Item
from core.inventory.item_enums import ItemType, ItemRarity, EquipmentSlot
from core.inventory.item_stat import ItemStat
from core.inventory.item_template_loader import get_item_template_loader
from core.inventory.item_variation_generator import ItemVariationGenerator

# Get module logger
logger = get_logger("Inventory")


class ItemFactory:
    """
    Factory for creating game items.
    
    This class handles creation of items from templates or
    custom specifications.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ItemFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the item factory."""
        if self._initialized:
            return
            
        logger.info("Initializing ItemFactory")
        
        # Get template loader
        self._template_loader = get_item_template_loader()
        
        self._initialized = True
        
        # Cache for icon directories to avoid repeated filesystem calls
        self._icon_cache = {}
        
        logger.info("ItemFactory initialized")
    
    def create_item_from_template(self, 
                                 template_id: str, 
                                 variation: bool = False,
                                 quality_override: Optional[float] = None) -> Optional[Item]:
        """
        Create an item from a template.
        
        Args:
            template_id: The ID of the template to use.
            variation: Whether to create a variation with randomized stats.
            quality_override: Optional quality factor override (0.0 to 2.0).
            
        Returns:
            A new Item instance, or None if the template was not found.
        """
        # Get the template
        template = self._template_loader.get_template(template_id)
        if not template:
            logger.warning(f"Template not found: {template_id}")
            return None
        
        # Create variation or copy
        if variation:
            item = ItemVariationGenerator.create_variation(template, quality_override)
        else:
            # Create a regular copy
            item = Item(
                name=template.name,
                description=template.description,
                item_type=template.item_type,
                rarity=template.rarity,
                weight=template.weight,
                value=template.value,
                icon_path=template.icon_path,
                is_equippable=template.is_equippable,
                equip_slots=[slot for slot in template.equip_slots] if template.equip_slots else [],
                stats=[ItemStat(
                    name=stat.name,
                    value=stat.value,
                    display_name=stat.display_name,
                    is_percentage=stat.is_percentage
                ) for stat in template.stats],
                is_consumable=template.is_consumable,
                is_stackable=template.is_stackable,
                stack_limit=template.stack_limit,
                quantity=1,
                is_quest_item=template.is_quest_item,
                durability=template.durability,
                current_durability=template.durability,
                tags=template.tags.copy() if template.tags else [],
                template_id=template.id,
                source="template_copy"
            )
        
        # Assign random icon if not specified
        if not item.icon_path:
            self.assign_random_icon(item)
        
        logger.info(f"Created item from template: {template_id}")
        return item
    
    def create_random_item(self, 
                          item_type: Optional[Union[ItemType, str]] = None,
                          rarity: Optional[Union[ItemRarity, str]] = None,
                          min_value: Optional[int] = None,
                          max_value: Optional[int] = None,
                          variation: bool = True) -> Optional[Item]:
        """
        Create a random item with optional constraints.
        
        Args:
            item_type: Optional type constraint.
            rarity: Optional rarity constraint.
            min_value: Optional minimum value constraint.
            max_value: Optional maximum value constraint.
            variation: Whether to create a variation with randomized stats.
            
        Returns:
            A new random Item instance, or None if no template matched the criteria.
        """
        # Convert string types to enums if needed
        if isinstance(item_type, str):
            try:
                item_type = ItemType(item_type)
            except ValueError:
                logger.warning(f"Invalid item type: {item_type}")
                return None
        
        if isinstance(rarity, str):
            try:
                rarity = ItemRarity(rarity)
            except ValueError:
                logger.warning(f"Invalid item rarity: {rarity}")
                return None
        
        # Build criteria dict
        criteria = {}
        if item_type:
            criteria["item_type"] = item_type
        if rarity:
            criteria["rarity"] = rarity
        
        # Get matching templates
        templates = self._template_loader.get_templates_by_criteria(**criteria)
        if not templates:
            logger.warning(f"No templates match the criteria: {criteria}")
            return None
        
        # Filter by value if needed
        if min_value is not None or max_value is not None:
            filtered_templates = {}
            for template_id, template in templates.items():
                if min_value is not None and template.value < min_value:
                    continue
                if max_value is not None and template.value > max_value:
                    continue
                filtered_templates[template_id] = template
            
            templates = filtered_templates
            
            if not templates:
                logger.warning(f"No templates match the value criteria: min={min_value}, max={max_value}")
                return None
        
        # Select a random template
        template_id = random.choice(list(templates.keys()))
        
        # Create item from template
        return self.create_item_from_template(template_id, variation)
    
    def create_loot_table(self, 
                         item_count: int,
                         rarity_weights: Optional[Dict[ItemRarity, float]] = None,
                         type_weights: Optional[Dict[ItemType, float]] = None,
                         value_range: Optional[Tuple[int, int]] = None) -> List[Item]:
        """
        Create a table of random loot items.
        
        Args:
            item_count: Number of items to generate.
            rarity_weights: Optional dictionary mapping rarities to weights.
            type_weights: Optional dictionary mapping types to weights.
            value_range: Optional tuple of (min_value, max_value).
            
        Returns:
            A list of generated items.
        """
        # Default rarity weights if not provided
        if rarity_weights is None:
            rarity_weights = {
                ItemRarity.COMMON: 0.6,
                ItemRarity.UNCOMMON: 0.25,
                ItemRarity.RARE: 0.10,
                ItemRarity.EPIC: 0.04,
                ItemRarity.LEGENDARY: 0.01
            }
        
        # Convert weights to lists for random.choices
        rarity_choices = list(rarity_weights.keys())
        rarity_weights_list = list(rarity_weights.values())
        
        type_choices = None
        type_weights_list = None
        if type_weights:
            type_choices = list(type_weights.keys())
            type_weights_list = list(type_weights.values())
        
        # Generate items
        items = []
        for _ in range(item_count):
            # Select random rarity
            rarity = random.choices(rarity_choices, weights=rarity_weights_list, k=1)[0]
            
            # Select random type if weights provided
            item_type = None
            if type_choices:
                item_type = random.choices(type_choices, weights=type_weights_list, k=1)[0]
            
            # Set value range
            min_value = None
            max_value = None
            if value_range:
                min_value, max_value = value_range
            
            # Create random item
            item = self.create_random_item(
                item_type=item_type,
                rarity=rarity,
                min_value=min_value,
                max_value=max_value,
                variation=True
            )
            
            if item:
                items.append(item)
        
        logger.info(f"Generated loot table with {len(items)} items")
        return items
    
    def create_item_from_spec(self, spec: Dict[str, Any]) -> Optional[Item]:
        """
        Create an item from a specification dictionary.
        
        Args:
            spec: Dictionary with item specifications.
            
        Returns:
            A new Item instance, or None if the specification was invalid.
        """
        try:
            # Check if we should use a template as a base
            template_id = spec.get("template_id")
            if template_id:
                # Create from template first
                template = self._template_loader.get_template(template_id)
                if not template:
                    logger.warning(f"Template not found: {template_id}")
                    return None
                
                base_item = self.create_item_from_template(template_id, False)
                if not base_item:
                    return None
                
                # Update with spec values
                for key, value in spec.items():
                    if key != "template_id" and key != "stats":
                        setattr(base_item, key, value)
                
                # Update stats if provided
                if "stats" in spec:
                    for stat_spec in spec["stats"]:
                        stat_name = stat_spec.get("name")
                        if stat_name:
                            # Check if stat already exists
                            existing_stat = base_item.get_stat(stat_name)
                            if existing_stat:
                                # Update existing stat
                                existing_stat.value = stat_spec.get("value", existing_stat.value)
                                existing_stat.display_name = stat_spec.get("display_name", existing_stat.display_name)
                                existing_stat.is_percentage = stat_spec.get("is_percentage", existing_stat.is_percentage)
                            else:
                                # Add new stat
                                base_item.add_stat(
                                    name=stat_name,
                                    value=stat_spec.get("value", 0),
                                    display_name=stat_spec.get("display_name"),
                                    is_percentage=stat_spec.get("is_percentage", False)
                                )
                
                return base_item
            
            # Create a new item from scratch
            item_type = spec.get("item_type", ItemType.MISCELLANEOUS)
            if isinstance(item_type, str):
                try:
                    item_type = ItemType(item_type)
                except ValueError:
                    logger.warning(f"Invalid item type: {item_type}")
                    item_type = ItemType.MISCELLANEOUS
            
            rarity = spec.get("rarity", ItemRarity.COMMON)
            if isinstance(rarity, str):
                try:
                    rarity = ItemRarity(rarity)
                except ValueError:
                    logger.warning(f"Invalid item rarity: {rarity}")
                    rarity = ItemRarity.COMMON
            
            # Process equipment slots
            equip_slots = []
            if "equip_slots" in spec:
                for slot in spec["equip_slots"]:
                    if isinstance(slot, str):
                        try:
                            equip_slots.append(EquipmentSlot(slot))
                        except ValueError:
                            logger.warning(f"Invalid equipment slot: {slot}")
                    else:
                        equip_slots.append(slot)
            
            # Process stats
            stats = []
            if "stats" in spec:
                for stat_spec in spec["stats"]:
                    stat = ItemStat(
                        name=stat_spec["name"],
                        value=stat_spec["value"],
                        display_name=stat_spec.get("display_name"),
                        is_percentage=stat_spec.get("is_percentage", False)
                    )
                    stats.append(stat)
            
            # Create the item
                item = Item(
                id=spec.get("id", str(uuid.uuid4())),
                name=spec.get("name", "Unknown Item"),
                description=spec.get("description", ""),
                item_type=item_type,
                rarity=rarity,
                weight=spec.get("weight", 0.0),
                value=spec.get("value", 0),
                icon_path=spec.get("icon_path"),
                is_equippable=spec.get("is_equippable", False),
                equip_slots=equip_slots,
                stats=stats,
                is_consumable=spec.get("is_consumable", False),
                is_stackable=spec.get("is_stackable", False),
                stack_limit=(spec.get("stack_limit", 20) if spec.get("is_stackable", False) else spec.get("stack_limit", 1)),
                quantity=spec.get("quantity", 1),
                is_quest_item=spec.get("is_quest_item", False),
                durability=spec.get("durability"),
                current_durability=spec.get("current_durability"),
                tags=spec.get("tags", []),
                source=spec.get("source", "custom")
            )
            
            # Set discovered properties if specified
            if "known_properties" in spec:
                for prop in spec["known_properties"]:
                    item.discover_property(prop)
            
            # Assign random icon if not specified
            if not item.icon_path:
                self.assign_random_icon(item)
            
            logger.info(f"Created custom item: {item.name}")
            return item
            
        except Exception as e:
            logger.error(f"Error creating item from spec: {e}")
            return None
    
    def create_items_from_json(self, json_text: str) -> List[Item]:
        """
        Create items from a JSON string containing specifications.
        
        Args:
            json_text: JSON string with item specifications.
            
        Returns:
            A list of created items.
        """
        try:
            specs = json.loads(json_text)
            
            # Handle both single item and list of items
            if not isinstance(specs, list):
                specs = [specs]
            
            items = []
            for spec in specs:
                item = self.create_item_from_spec(spec)
                if item:
                    items.append(item)
            
            logger.info(f"Created {len(items)} items from JSON")
            return items
            
        except Exception as e:
            logger.error(f"Error creating items from JSON: {e}")
            return []
    
    def assign_random_icon(self, item: Item) -> None:
        """
        Assign a random icon from the pool based on item type and tags.
        Icon path is permanently stored with the item.
        
        Args:
            item: The item to assign an icon to.
        """
        # Skip if already has an icon
        if item.icon_path:
            return
        
        # Determine icon directory based on item type
        type_to_dir = {
            ItemType.WEAPON: "weapon",
            ItemType.ARMOR: "armor",
            ItemType.SHIELD: "shield",
            ItemType.ACCESSORY: "accessory",
            ItemType.CONSUMABLE: "consumable",
            ItemType.QUEST: "quest",
            ItemType.MATERIAL: "material",
            ItemType.CONTAINER: "container",
            ItemType.KEY: "key",
            ItemType.DOCUMENT: "document",
            ItemType.TOOL: "tool",
            ItemType.TREASURE: "treasure",
            ItemType.MISCELLANEOUS: "miscellaneous"
        }
        
        icon_dir = type_to_dir.get(item.item_type, "miscellaneous")
        base_path = Path("images/icons") / icon_dir
        
        # Get candidates from cache or scan directory
        cache_key = str(base_path)
        if cache_key not in self._icon_cache:
            # Scan directory for PNG files
            if base_path.exists():
                self._icon_cache[cache_key] = list(base_path.glob("*.png"))
            else:
                self._icon_cache[cache_key] = []
                logger.warning(f"Icon directory not found: {base_path}")
        
        candidates = []
        
        # Strategy 1: Match by tags (e.g., "dagger" in tags → dagger_*.png)
        if item.tags:
            for tag in item.tags:
                tag_lower = tag.lower()
                matching = [p for p in self._icon_cache.get(cache_key, []) 
                           if tag_lower in p.stem.lower()]
                if matching:
                    candidates.extend(matching)
        
        # Strategy 2: If no tag matches, get all icons in the type directory
        if not candidates:
            candidates = self._icon_cache.get(cache_key, [])
        
        # Strategy 3: Fallback to miscellaneous if type folder empty
        if not candidates:
            misc_path = Path("images/icons/miscellaneous")
            misc_cache_key = str(misc_path)
            if misc_cache_key not in self._icon_cache:
                if misc_path.exists():
                    self._icon_cache[misc_cache_key] = list(misc_path.glob("*.png"))
                else:
                    self._icon_cache[misc_cache_key] = []
            
            candidates = self._icon_cache.get(misc_cache_key, [])
            icon_dir = "miscellaneous"
        
        # Select random icon from candidates
        if candidates:
            selected = random.choice(candidates)
            # Store as web-accessible path (forward slashes for web)
            item.icon_path = f"/images/icons/{icon_dir}/{selected.name}"
            logger.info(f"Assigned random icon to '{item.name}': {item.icon_path}")
        else:
            # No icons available - set None and log warning
            logger.warning(f"No icons available for item type {item.item_type}, item: {item.name}")
            item.icon_path = None


# Convenience function
def get_item_factory() -> ItemFactory:
    """Get the item factory instance."""
    return ItemFactory()
