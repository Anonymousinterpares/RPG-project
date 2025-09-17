#!/usr/bin/env python3
"""
Item variation generator module.

This module provides functionality for creating variations of items
with different stats and properties.
"""

from typing import Dict, List, Optional, Any, Union, Tuple, Set
import random
import logging
import copy
import uuid

from core.utils.logging_config import get_logger
from core.inventory.item import Item
from core.inventory.item_enums import ItemRarity, ItemType
from core.inventory.item_stat_modifier import ItemStatModifier

# Get module logger
logger = get_logger("Inventory")


class ItemVariationGenerator:
    """
    Generator for item variations.
    
    This class provides methods for creating variations of items
    with different stats and properties based on templates.
    """
    
    # Quality variation ranges by rarity
    QUALITY_RANGES = {
        ItemRarity.COMMON: (0.80, 1.20),
        ItemRarity.UNCOMMON: (0.85, 1.25),
        ItemRarity.RARE: (0.90, 1.30),
        ItemRarity.EPIC: (0.95, 1.40),
        ItemRarity.LEGENDARY: (1.00, 1.50),
        ItemRarity.ARTIFACT: (1.10, 1.75),
        ItemRarity.UNIQUE: (1.20, 2.00)
    }
    
    # Prefix/suffix word lists
    PREFIXES = {
        "weapon": [
            "Sharp", "Keen", "Balanced", "Heavy", "Light", "Swift", 
            "Deadly", "Venomous", "Burning", "Frozen", "Shocking",
            "Masterwork", "Ancient", "Enchanted", "Blessed", "Cursed",
            "Runic", "Ornate", "Brutal", "Precise", "Hunter's"
        ],
        "armor": [
            "Sturdy", "Reinforced", "Plated", "Layered", "Durable",
            "Guardian's", "Warden's", "Defender's", "Protective", "Impenetrable",
            "Elven", "Dwarven", "Orcish", "Enchanted", "Blessed",
            "Runic", "Ornate", "Royal", "Ceremonial", "Knight's"
        ],
        "general": [
            "Fine", "Exceptional", "Superior", "Flawless", "Perfect",
            "Artisan's", "Master's", "Exotic", "Arcane", "Mysterious",
            "Forgotten", "Lost", "Hidden", "Recovered", "Preserved",
            "Sacred", "Profane", "Celestial", "Infernal", "Ethereal"
        ]
    }
    
    SUFFIXES = {
        "weapon": [
            "of Slaying", "of Quickness", "of Accuracy", "of Power", "of Might",
            "of Destruction", "of Ruin", "of the Berserker", "of the Assassin", "of the Duelist",
            "of Fire", "of Ice", "of Lightning", "of Venom", "of Decay",
            "of the Hunt", "of the Wild", "of the Night", "of the Dawn", "of Twilight"
        ],
        "armor": [
            "of Protection", "of Warding", "of Shielding", "of Deflection", "of Absorption",
            "of Resilience", "of Endurance", "of Fortitude", "of Vitality", "of Recovery",
            "of Fire Resistance", "of Frost Resistance", "of Lightning Resistance", "of Poison Resistance", "of Magic Resistance",
            "of the Guardian", "of the Sentinel", "of the Knight", "of the Paladin", "of the Defender"
        ],
        "general": [
            "of Quality", "of Excellence", "of Perfection", "of Mastery", "of Craftsmanship",
            "of the Artisan", "of the Master", "of the Adept", "of the Sage", "of the Scholar",
            "of Fortune", "of Luck", "of Fate", "of Destiny", "of Prophecy",
            "of the Ages", "of the Ancients", "of Legends", "of Myths", "of Legacy"
        ]
    }
    
    @classmethod
    def create_variation(cls, template: Item, quality_override: Optional[float] = None) -> Item:
        """
        Create a variation of an item based on a template.
        
        Args:
            template: The template Item to create a variation from.
            quality_override: Optional quality factor override (0.0 to 2.0).
            
        Returns:
            A new Item instance with modified stats.
        """
        # Create a deep copy of the template
        variation = copy.deepcopy(template)
        
        # Generate a new ID
        variation.id = str(uuid.uuid4())
        
        # Remove template flag
        variation.is_template = False
        
        # Set template_id to reference the original
        variation.template_id = template.id
        
        # Set source
        variation.source = "variation"
        
        # Determine quality factor
        quality = cls._determine_quality(template.rarity) if quality_override is None else quality_override
        
        # Modify stats based on quality
        new_stats = []
        for stat in variation.stats:
            new_stat = ItemStatModifier.apply_quality_factor(stat, quality)
            new_stats.append(new_stat)
        
        variation.stats = new_stats
        
        # Add name prefix/suffix based on quality
        if quality > 1.2:
            variation.name = cls._add_name_affixes(variation)
        
        return variation
    
    @classmethod
    def create_variations(cls, template: Item, count: int) -> List[Item]:
        """
        Create multiple variations of an item.
        
        Args:
            template: The template Item to create variations from.
            count: The number of variations to create.
            
        Returns:
            A list of new Item instances with modified stats.
        """
        variations = []
        for _ in range(count):
            variation = cls.create_variation(template)
            variations.append(variation)
        
        return variations
    
    @classmethod
    def create_upgraded_variation(cls, item: Item, upgrade_level: int) -> Item:
        """
        Create an upgraded variation of an existing item.
        
        Args:
            item: The Item to upgrade.
            upgrade_level: The level of upgrade to apply (1-5 typically).
            
        Returns:
            A new Item instance with improved stats.
        """
        # Create a deep copy of the item
        upgraded = copy.deepcopy(item)
        
        # Generate a new ID
        upgraded.id = str(uuid.uuid4())
        
        # Set source
        upgraded.source = f"upgraded_{upgrade_level}"
        
        # Calculate upgrade quality factor (higher levels give better upgrades)
        upgrade_factor = 1.0 + (upgrade_level * 0.1)  # 1.1, 1.2, 1.3, etc.
        
        # Modify stats based on upgrade factor
        new_stats = []
        for stat in upgraded.stats:
            new_stat = ItemStatModifier.apply_quality_factor(stat, upgrade_factor)
            new_stats.append(new_stat)
        
        upgraded.stats = new_stats
        
        # Modify name to indicate upgrade
        if upgrade_level == 1:
            prefix = "Improved"
        elif upgrade_level == 2:
            prefix = "Superior"
        elif upgrade_level == 3:
            prefix = "Exceptional"
        elif upgrade_level == 4:
            prefix = "Exquisite"
        else:
            prefix = "Masterwork"
        
        upgraded.name = f"{prefix} {upgraded.name}"
        
        return upgraded
    
    @classmethod
    def create_damaged_variation(cls, item: Item, damage_level: int) -> Item:
        """
        Create a damaged variation of an existing item.
        
        Args:
            item: The Item to damage.
            damage_level: The level of damage to apply (1-5 typically).
            
        Returns:
            A new Item instance with reduced stats.
        """
        # Create a deep copy of the item
        damaged = copy.deepcopy(item)
        
        # Generate a new ID
        damaged.id = str(uuid.uuid4())
        
        # Set source
        damaged.source = f"damaged_{damage_level}"
        
        # Calculate damage quality factor (higher levels give worse damage)
        damage_factor = 1.0 - (damage_level * 0.1)  # 0.9, 0.8, 0.7, etc.
        
        # Modify stats based on damage factor
        new_stats = []
        for stat in damaged.stats:
            new_stat = ItemStatModifier.apply_quality_factor(stat, damage_factor)
            new_stats.append(new_stat)
        
        damaged.stats = new_stats
        
        # Modify durability if applicable
        if damaged.durability is not None:
            damaged.current_durability = int(damaged.durability * damage_factor)
        
        # Modify name to indicate damage
        if damage_level == 1:
            prefix = "Worn"
        elif damage_level == 2:
            prefix = "Damaged"
        elif damage_level == 3:
            prefix = "Battered"
        elif damage_level == 4:
            prefix = "Broken"
        else:
            prefix = "Ruined"
        
        damaged.name = f"{prefix} {damaged.name}"
        
        return damaged
    
    @classmethod
    def _determine_quality(cls, rarity: ItemRarity) -> float:
        """
        Determine a random quality factor based on item rarity.
        
        Args:
            rarity: The rarity of the item.
            
        Returns:
            A quality factor value.
        """
        min_quality, max_quality = cls.QUALITY_RANGES.get(
            rarity, (0.8, 1.2)  # Default range for unknown rarities
        )
        
        return random.uniform(min_quality, max_quality)
    
    @classmethod
    def _add_name_affixes(cls, item: Item) -> str:
        """
        Add prefix and/or suffix to an item name based on its type.
        
        Args:
            item: The item to modify.
            
        Returns:
            Modified item name.
        """
        # Determine appropriate prefix/suffix category
        if item.item_type == ItemType.WEAPON:
            category = "weapon"
        elif item.item_type in [ItemType.ARMOR, ItemType.SHIELD]:
            category = "armor"
        else:
            category = "general"
        
        # Get prefix and suffix lists
        prefixes = cls.PREFIXES.get(category, cls.PREFIXES["general"])
        suffixes = cls.SUFFIXES.get(category, cls.SUFFIXES["general"])
        
        # Decide whether to add prefix, suffix, or both
        add_type = random.choices(
            ["prefix", "suffix", "both"],
            weights=[0.4, 0.4, 0.2],
            k=1
        )[0]
        
        name = item.name
        
        if add_type == "prefix" or add_type == "both":
            prefix = random.choice(prefixes)
            name = f"{prefix} {name}"
        
        if add_type == "suffix" or add_type == "both":
            suffix = random.choice(suffixes)
            name = f"{name} {suffix}"
        
        return name
