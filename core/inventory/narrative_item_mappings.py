#!/usr/bin/env python3
"""
Mappings for narrative item generation.

This module provides mappings between natural language terms and
game enums for item types, rarities, equipment slots, and stats.
"""

from core.inventory import ItemType, ItemRarity, EquipmentSlot

def get_type_mappings() -> dict:
    """
    Get mappings from natural language to ItemType.
    
    Returns:
        Dictionary mapping strings to ItemType enums.
    """
    return {
        "weapon": ItemType.WEAPON,
        "sword": ItemType.WEAPON,
        "axe": ItemType.WEAPON,
        "mace": ItemType.WEAPON,
        "dagger": ItemType.WEAPON,
        "staff": ItemType.WEAPON,
        "wand": ItemType.WEAPON,
        "bow": ItemType.WEAPON,
        "crossbow": ItemType.WEAPON,
        "spear": ItemType.WEAPON,
        "hammer": ItemType.WEAPON,
        
        "armor": ItemType.ARMOR,
        "helmet": ItemType.ARMOR,
        "breastplate": ItemType.ARMOR,
        "greaves": ItemType.ARMOR,
        "boots": ItemType.ARMOR,
        "gauntlets": ItemType.ARMOR,
        "robe": ItemType.ARMOR,
        
        "shield": ItemType.SHIELD,
        "buckler": ItemType.SHIELD,
        "tower shield": ItemType.SHIELD,
        
        "potion": ItemType.CONSUMABLE,
        "elixir": ItemType.CONSUMABLE,
        "flask": ItemType.CONSUMABLE,
        "vial": ItemType.CONSUMABLE,
        
        "consumable": ItemType.CONSUMABLE,
        "food": ItemType.CONSUMABLE,
        "drink": ItemType.CONSUMABLE,
        "scroll": ItemType.CONSUMABLE,
        
        "material": ItemType.MATERIAL,
        "ingredient": ItemType.MATERIAL,
        "ore": ItemType.MATERIAL,
        "cloth": ItemType.MATERIAL,
        "leather": ItemType.MATERIAL,
        "wood": ItemType.MATERIAL,
        "stone": ItemType.MATERIAL,
        "metal": ItemType.MATERIAL,
        "herb": ItemType.MATERIAL,
        
        "quest item": ItemType.QUEST,
        "quest": ItemType.QUEST,
        "artifact": ItemType.QUEST,
        
        "trinket": ItemType.ACCESSORY,
        
        "accessory": ItemType.ACCESSORY,
        "jewelry": ItemType.ACCESSORY,
        "ring": ItemType.ACCESSORY,
        "amulet": ItemType.ACCESSORY,
        "necklace": ItemType.ACCESSORY,
        "pendant": ItemType.ACCESSORY,
        "earring": ItemType.ACCESSORY,
        "bracelet": ItemType.ACCESSORY,
        
        "container": ItemType.CONTAINER,
        "bag": ItemType.CONTAINER,
        "pouch": ItemType.CONTAINER,
        "sack": ItemType.CONTAINER,
        "chest": ItemType.CONTAINER,
        "box": ItemType.CONTAINER,
        
        "book": ItemType.DOCUMENT,
        "tome": ItemType.DOCUMENT,
        "codex": ItemType.DOCUMENT,
        "scroll": ItemType.DOCUMENT,
        
        "note": ItemType.DOCUMENT,
        "letter": ItemType.DOCUMENT,
        "map": ItemType.DOCUMENT,
        "document": ItemType.DOCUMENT,
        
        "key": ItemType.KEY,
        "lockpick": ItemType.KEY,
        
        "tool": ItemType.TOOL,
        "instrument": ItemType.TOOL,
        
        "treasure": ItemType.TREASURE,
        "gem": ItemType.TREASURE,
        "jewel": ItemType.TREASURE,
        
        "miscellaneous": ItemType.MISCELLANEOUS,
        "misc": ItemType.MISCELLANEOUS,
        
        "gold": ItemType.TREASURE,
        "silver": ItemType.TREASURE,
        "copper": ItemType.TREASURE,
        "coin": ItemType.TREASURE,
        "currency": ItemType.TREASURE,
        "money": ItemType.TREASURE,
    }

def get_rarity_mappings() -> dict:
    """
    Get mappings from natural language to ItemRarity.
    
    Returns:
        Dictionary mapping strings to ItemRarity enums.
    """
    return {
        "common": ItemRarity.COMMON,
        "uncommon": ItemRarity.UNCOMMON,
        "rare": ItemRarity.RARE,
        "epic": ItemRarity.EPIC,
        "legendary": ItemRarity.LEGENDARY,
        "artifact": ItemRarity.ARTIFACT,
        "unique": ItemRarity.UNIQUE,
        
        # Additional synonyms
        "ordinary": ItemRarity.COMMON,
        "basic": ItemRarity.COMMON,
        "standard": ItemRarity.COMMON,
        
        "unusual": ItemRarity.UNCOMMON,
        "special": ItemRarity.UNCOMMON,
        
        "scarce": ItemRarity.RARE,
        "exceptional": ItemRarity.RARE,
        
        "magnificent": ItemRarity.EPIC,
        "superior": ItemRarity.EPIC,
        
        "mythical": ItemRarity.LEGENDARY,
        "mythic": ItemRarity.LEGENDARY,
        "ancient": ItemRarity.LEGENDARY,
        
        "divine": ItemRarity.ARTIFACT,
        "godly": ItemRarity.ARTIFACT,
        
        "one of a kind": ItemRarity.UNIQUE,
        "singular": ItemRarity.UNIQUE,
    }

def get_slot_mappings() -> dict:
    """
    Get mappings from natural language to EquipmentSlot.
    
    Returns:
        Dictionary mapping strings to EquipmentSlot enums.
    """
    return {
        "main hand": EquipmentSlot.MAIN_HAND,
        "off hand": EquipmentSlot.OFF_HAND,
        "head": EquipmentSlot.HEAD,
        "chest": EquipmentSlot.CHEST,
        "legs": EquipmentSlot.LEGS,
        "feet": EquipmentSlot.FEET,
        "shoulders": EquipmentSlot.SHOULDERS,
        "wrists": EquipmentSlot.WRISTS,
        "hands": EquipmentSlot.HANDS,
        "waist": EquipmentSlot.WAIST,
        "neck": EquipmentSlot.NECK,
        "back": EquipmentSlot.BACK,
        "finger1": EquipmentSlot.FINGER_1,
        "finger2": EquipmentSlot.FINGER_2,
        "finger3": EquipmentSlot.FINGER_3,
        "finger4": EquipmentSlot.FINGER_4,
        "finger5": EquipmentSlot.FINGER_5,
        "finger6": EquipmentSlot.FINGER_6,
        "finger7": EquipmentSlot.FINGER_7,
        "finger8": EquipmentSlot.FINGER_8,
        "finger9": EquipmentSlot.FINGER_9,
        "finger10": EquipmentSlot.FINGER_10,
        "trinket1": EquipmentSlot.TRINKET_1,
        "trinket2": EquipmentSlot.TRINKET_2,
        
        # Common synonyms
        "weapon": EquipmentSlot.MAIN_HAND,
        "sword": EquipmentSlot.MAIN_HAND,
        "axe": EquipmentSlot.MAIN_HAND,
        "mace": EquipmentSlot.MAIN_HAND,
        "dagger": EquipmentSlot.MAIN_HAND,
        "staff": EquipmentSlot.MAIN_HAND,
        "wand": EquipmentSlot.MAIN_HAND,
        "bow": EquipmentSlot.MAIN_HAND,
        
        "shield": EquipmentSlot.OFF_HAND,
        "offhand": EquipmentSlot.OFF_HAND,
        "left hand": EquipmentSlot.OFF_HAND,
        
        "helmet": EquipmentSlot.HEAD,
        "hat": EquipmentSlot.HEAD,
        "crown": EquipmentSlot.HEAD,
        "headpiece": EquipmentSlot.HEAD,
        
        "armor": EquipmentSlot.CHEST,
        "breastplate": EquipmentSlot.CHEST,
        "robe": EquipmentSlot.CHEST,
        "tunic": EquipmentSlot.CHEST,
        "chestpiece": EquipmentSlot.CHEST,
        "torso": EquipmentSlot.CHEST,
        
        "pants": EquipmentSlot.LEGS,
        "greaves": EquipmentSlot.LEGS,
        "leggings": EquipmentSlot.LEGS,
        
        "boots": EquipmentSlot.FEET,
        "shoes": EquipmentSlot.FEET,
        "footwear": EquipmentSlot.FEET,
        
        "pauldrons": EquipmentSlot.SHOULDERS,
        "shoulder pads": EquipmentSlot.SHOULDERS,
        
        "bracers": EquipmentSlot.WRISTS,
        "armguards": EquipmentSlot.WRISTS,
        "sleeves": EquipmentSlot.WRISTS,
        
        "gloves": EquipmentSlot.HANDS,
        "gauntlets": EquipmentSlot.HANDS,
        
        "belt": EquipmentSlot.WAIST,
        "girdle": EquipmentSlot.WAIST,
        "sash": EquipmentSlot.WAIST,
        
        "amulet": EquipmentSlot.NECK,
        "pendant": EquipmentSlot.NECK,
        "necklace": EquipmentSlot.NECK,
        "collar": EquipmentSlot.NECK,
        
        "cloak": EquipmentSlot.BACK,
        "cape": EquipmentSlot.BACK,
        "mantle": EquipmentSlot.BACK,
        
        "ring": EquipmentSlot.FINGER_1,
        "finger": EquipmentSlot.FINGER_1,
        
        "bracelet": EquipmentSlot.WRISTS,
        "wristband": EquipmentSlot.WRISTS,
        "bracer": EquipmentSlot.WRISTS,
    }

def get_stat_mappings() -> dict:
    """
    Get mappings from natural language to stat names.
    
    Returns:
        Dictionary mapping strings to stat names.
    """
    return {
        # Combat stats
        "damage": "damage",
        "attack": "damage",
        "power": "damage",
        "strength": "strength",
        "str": "strength",
        "dexterity": "dexterity",
        "dex": "dexterity",
        "agility": "agility",
        "agi": "agility",
        "intelligence": "intelligence",
        "int": "intelligence",
        "wisdom": "wisdom",
        "wis": "wisdom",
        "constitution": "constitution",
        "con": "constitution",
        "vitality": "vitality",
        "vit": "vitality",
        "charisma": "charisma",
        "cha": "charisma",
        "armor": "armor",
        "defense": "defense",
        "protection": "defense",
        "block": "block",
        "parry": "parry",
        "dodge": "dodge",
        "evasion": "dodge",
        "accuracy": "accuracy",
        "hit": "accuracy",
        "critical": "critical",
        "crit": "critical",
        "speed": "speed",
        "attack speed": "attack_speed",
        "attack_speed": "attack_speed",
        "movement speed": "movement_speed",
        "movement_speed": "movement_speed",
        
        # Health stats
        "health": "health",
        "hp": "health",
        "health regeneration": "health_regen",
        "health_regen": "health_regen",
        "hp regen": "health_regen",
        "healing": "healing",
        
        # Energy stats
        "mana": "mana",
        "mp": "mana",
        "energy": "energy",
        "stamina": "stamina",
        "focus": "focus",
        "mana regeneration": "mana_regen",
        "mana_regen": "mana_regen",
        "energy regeneration": "energy_regen",
        "energy_regen": "energy_regen",
        
        # Resistances
        "fire resistance": "fire_resistance",
        "fire_resistance": "fire_resistance",
        "cold resistance": "cold_resistance",
        "cold_resistance": "cold_resistance",
        "lightning resistance": "lightning_resistance",
        "lightning_resistance": "lightning_resistance",
        "poison resistance": "poison_resistance",
        "poison_resistance": "poison_resistance",
        "magic resistance": "magic_resistance",
        "magic_resistance": "magic_resistance",
        "physical resistance": "physical_resistance",
        "physical_resistance": "physical_resistance",
        
        # Utility
        "luck": "luck",
        "fortune": "luck",
        "stealth": "stealth",
        "lockpicking": "lockpicking",
        "pickpocket": "pickpocket",
        "perception": "perception",
        "crafting": "crafting",
        "gathering": "gathering",
        "bargaining": "bargaining",
    }
